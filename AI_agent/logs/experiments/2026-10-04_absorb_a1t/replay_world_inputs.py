"""Supplement pixel-plan replay with saved assemblies and world-coordinate proposals."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
from types import ModuleType

from src.agent.geometry.input_scale import ScaleMismatchError, check_geometry_scale
from src.agent.geometry.plan_assembly import assemble_plan_proposals
from src.agent.execution.source_proposal import _validate_proposal
from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.correction.schema import FootprintRing

from replay import BASELINE, HERE, ROOT, WORK, baseline_compiler, canonical, digest


def label(path):
    return str(path.relative_to(WORK) if path.is_relative_to(WORK) else path.relative_to(ROOT))


def main():
    tracked = subprocess.check_output(["git", "ls-files", "AI_agent/logs/experiments"], cwd=ROOT, text=True).splitlines()
    originals = [ROOT / p for p in tracked if "/runtime_snapshot/" not in p]
    proposals = sorted(set([p for p in originals if p.name == "proposal.json"] + list(WORK.rglob("proposal.json"))))
    assemblies = sorted(set([p for p in originals if p.parent.name == "plan_assemblies"]
                            + list(WORK.rglob("plan_assemblies/*.json"))))
    compiler, _ = baseline_compiler()
    raw = subprocess.check_output(["git", "show", f"{BASELINE}:src/agent/geometry/plan_assembly.py"], cwd=ROOT)
    module = ModuleType("a1t_old_assembly")
    exec(compile(raw, "a1t_old_assembly", "exec"), module.__dict__)
    proposal_rows, assembly_rows = [], []
    for path in proposals:
        value = json.loads(path.read_bytes())
        if not isinstance(value, dict) or not isinstance(value.get("geometry"), dict):
            continue
        row = dict(path=label(path), sha256=digest(path.read_bytes()))
        try:
            geometry, _, _, _ = _validate_proposal(value)
            parsed = ensure_corrected_geometry(geometry)
            for floor in parsed.floors:
                footprint = getattr(floor, "footprint", None)
                if isinstance(footprint, dict):
                    floor.footprint = FootprintRing.model_validate(footprint)
            check_geometry_scale(parsed.model_dump(mode="json"))
            row["outcome"] = "scale_accepted"
        except ScaleMismatchError as error:
            row.update(outcome="scale_rejected", error=str(error))
        except (ValueError, TypeError, KeyError) as error:
            row.update(outcome="existing_schema_rejection", error=f"{type(error).__name__}: {error}")
        old_report = path.with_name("report.json")
        if old_report.is_file():
            row["original_source_geometry_ready"] = json.loads(old_report.read_bytes()).get("source_geometry_ready")
        proposal_rows.append(row)
    for path in assemblies:
        value = json.loads(path.read_bytes())
        run = path.parents[1]
        manifest = json.loads((run / "inputs.json").read_bytes())
        items = []
        for row in value["floors"]:
            plan_path = run / "plan_drafts" / row["draft_id"] / "plan.json"
            assert digest(plan_path.read_bytes()) == row["expected_plan_sha256"]
            image = row["image"]
            plan = json.loads(plan_path.read_bytes())
            proposal, _ = compiler(plan, image_size=tuple(manifest["images"][image]["size"]), image_name=image)
            items.append(dict(proposal=proposal, floor_id=row["floor_id"], z_floor=row["z_floor"], source_ref=row["evidence"]))
        before = module.assemble_plan_proposals(items)
        row = dict(path=label(path), sha256=digest(path.read_bytes()), before_sha256=digest(canonical(before)))
        try:
            after = assemble_plan_proposals(items)
            assert before == after, label(path)
            row.update(outcome="accepted_unchanged", after_sha256=digest(canonical(after)))
        except ScaleMismatchError as error:
            row.update(outcome="scale_rejected", error=str(error))
        assembly_rows.append(row)
    report = dict(model_requests=0, baseline_commit=BASELINE, proposals=proposal_rows, assemblies=assembly_rows,
                  proposal_counts=dict(Counter(r["outcome"] for r in proposal_rows)),
                  assembly_counts=dict(Counter(r["outcome"] for r in assembly_rows)),
                  scope="Proposals: existing schema parsing then read-only scale preflight on parsed values; no rebuild of stored BIM. Assemblies: recompile bound plans and compare pre-A1-T/current deterministic assembly output exactly.")
    (HERE / "world_input_replay.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"proposals", "assemblies"}}, ensure_ascii=False, indent=2))
    for row in proposal_rows + assembly_rows:
        if row["outcome"] == "scale_rejected":
            assert any(run in row["path"] for run in ("sm25_runtime_subscription", "guidance_ablation_run72", "method_control_run85")), row


if __name__ == "__main__":
    main()
