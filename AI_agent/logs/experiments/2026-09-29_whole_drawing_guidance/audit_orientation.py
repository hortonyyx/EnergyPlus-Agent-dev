"""Post-generation Y-direction diagnostic for a delivered sm21 candidate (0 model calls).

Generalises the run86 diagnostic: when every assembled plan maps the image top to
y=0 m, re-run the unchanged original-image audit with only the reference Y
direction reversed, and score exterior openings on a rigidly reflected copy of the
source. Official results are never modified; nothing is fitted or repaired.
"""
import argparse
import copy
import importlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.judge.gt import load_gt_document


def audit(run):
    load = lambda path: json.loads(Path(path).read_text())
    assert load(run / "summary.json")["agent_response_completed"]
    original = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original")
    legacy = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings")
    candidate = load(run / "delivery.json")["candidate"]
    source = load(run / candidate / "source_model.json")
    assembly = load(sorted((run / "plan_assemblies").glob("assembly_*.json"))[-1])
    drafts = [row["draft_id"] for row in assembly["floors"]]
    plans = [load(run / "plan_drafts" / draft / "plan.json") for draft in drafts]
    assert all([a[1] for a in plan["y_anchors"]] == [0, 8] and plan["y_anchors"][0][0] < plan["y_anchors"][1][0]
               for plan in plans), "diagnostic applies only when every plan maps the image top to y=0"
    protected = [run / candidate / "source_model.json", run / "evaluation/original_openings.json",
                 run / "evaluation/gt" / f"{candidate}_partition.json"]
    before = {str(p.relative_to(run)): digest(p) for p in protected}
    reference_path = original.HERE / "original_reference.json"
    reference = copy.deepcopy(original.load(reference_path))
    for floor in reference["floors"]:
        assert [a[1] for a in floor["calibration"]["y_anchors"]] == [8, 0]
        floor["calibration"]["y_anchors"] = [[p, 8 - y] for p, y in floor["calibration"]["y_anchors"]]
    output = run / "evaluation/orientation_diagnostic"
    assert not output.exists()
    original_load = original.load
    with tempfile.TemporaryDirectory(prefix="orientation-") as temporary:
        scratch = Path(temporary)
        for name in ("summary.json", "delivery.json", "images", candidate):
            (scratch / name).symlink_to(run / name)
        with patch.object(original, "load", lambda p: reference if p == reference_path else original_load(p)):
            original.audit(scratch)
        shutil.copytree(scratch / "evaluation", output)
    reflected = copy.deepcopy(source)
    for collection, field in (("floors", "footprint"), ("spaces", "polygon"),
                              ("boundaries", "vertices"), ("openings", "vertices")):
        for row in reflected[collection]:
            row[field] = [[p[0], 8 - p[1], *p[2:]] for p in row[field]]
    partition = load(run / "evaluation/gt" / f"{candidate}_partition.json")
    exterior = legacy.diagnostic(reflected, load_gt_document("sm21_anchor"), partition)
    dump(output / "exterior_parameters.json", exterior)
    assert before == {str(p.relative_to(run)): digest(p) for p in protected}
    diagnostic = load(output / "original_openings.json")
    dump(output / "scope.json", dict(
        mode="post_generation_direction_only_diagnostic_not_replacement_score",
        transform="y_reference = 8 - y_saved; x and z unchanged", drafts=drafts, candidate=candidate,
        basis="All assembled plans map image top to 0 m and bottom to 8 m; the independent reference uses the reverse.",
        source_model_sha256=source["source_model_sha256"], original_artifacts_unchanged=before,
        limits=["Official scores are unchanged; a mirrored building remains a real orientation error.",
                "Reference positions, identities, matching and tolerances are unchanged; only Y is reversed."]))
    summary = dict(positions=diagnostic["positions"], hosts=diagnostic["hosts"],
                   door_connections=diagnostic["door_connections"], reference_count=diagnostic["reference_count"],
                   space_identity={f["floor_id"]: f["space_identity_by_interior_point"] for f in diagnostic["floors"]},
                   exterior_matched=len(exterior["matched"]),
                   height_mismatches=[r.get("reference_id") for r in exterior["matched"]
                                      if r["z_within_judge_tolerance"] is False])
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run.resolve())
