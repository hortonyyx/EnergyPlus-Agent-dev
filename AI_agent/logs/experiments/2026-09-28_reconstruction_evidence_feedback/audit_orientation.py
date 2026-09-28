"""Run86-only post-generation Y-direction diagnostic; preserve official results."""
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
    assert json.loads((run / "summary.json").read_text())["agent_response_completed"]
    assert run.name == "2026-09-28_sm21_evidence_feedback_run86"
    original = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original")
    legacy = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings")
    candidate = original.load(run / "delivery.json")["candidate"]
    source = original.load(run / candidate / "source_model.json")
    protected = [run / candidate / "source_model.json", run / "evaluation/original_openings.json",
                 run / "evaluation/gt" / f"{candidate}_partition.json"]
    before = {str(p.relative_to(run)): digest(p) for p in protected}
    reference_path = original.HERE / "original_reference.json"
    reference = copy.deepcopy(original.load(reference_path))
    plans = [original.load(run / "plan_drafts" / draft / "plan.json")
             for draft in ("draft_003", "draft_004")]
    for floor, plan in zip(reference["floors"], plans):
        assert [a[1] for a in plan["y_anchors"]] == [0, 8]
        assert [a[1] for a in floor["calibration"]["y_anchors"]] == [8, 0]
        floor["calibration"]["y_anchors"] = [[p, 8 - y] for p, y in floor["calibration"]["y_anchors"]]
    output = run / "evaluation/orientation_diagnostic"
    assert not output.exists()
    original_load = original.load
    with tempfile.TemporaryDirectory(prefix="run86-orientation-") as temporary:
        scratch = Path(temporary)
        for name in ("summary.json", "delivery.json", "images", candidate):
            (scratch / name).symlink_to(run / name)
        with patch.object(original, "load", lambda p: reference if p == reference_path else original_load(p)):
            original.audit(scratch)
        shutil.copytree(scratch / "evaluation", output)

    # A rigid reflection only, without fitting, resizing, changing heights or repairing objects.
    reflected = copy.deepcopy(source)
    for collection, field in (("floors", "footprint"), ("spaces", "polygon"),
                              ("boundaries", "vertices"), ("openings", "vertices")):
        for row in reflected[collection]:
            row[field] = [[p[0], 8 - p[1], *p[2:]] for p in row[field]]
    partition = original.load(run / "evaluation/gt" / f"{candidate}_partition.json")
    exterior = legacy.diagnostic(reflected, load_gt_document("sm21_anchor"), partition)
    dump(output / "exterior_parameters.json", exterior)
    assert before == {str(p.relative_to(run)): digest(p) for p in protected}
    dump(output / "scope.json", dict(
        mode="post_generation_direction_only_diagnostic_not_replacement_score",
        transform="y_reference = 8 - y_saved; x and z unchanged",
        basis="Both saved plans explicitly map image top to 0m and bottom to 8m; the independent reference uses the reverse direction. No fit to openings or space geometry.",
        original_reference_sha256=digest(reference_path), original_artifacts_unchanged=before,
        candidate=candidate, source_model_sha256=source["source_model_sha256"],
        limits=["Original official scores remain unchanged. This diagnostic does not repair the model or certify building orientation.",
                "Reference pixel positions, identities, matching algorithm and tolerances are unchanged; only the Y direction is reversed.",
                "Merged reference rooms must still be reported even when both seeds resolve to one host.",
                "17 linked exterior heights do not imply 17 correctly interpreted heights."]
    ))
    print(json.dumps(dict(matched_exterior=len(exterior["matched"]),
        height_mismatches=[r for r in exterior["matched"] if not r["z_within_judge_tolerance"]]), ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run.resolve())
