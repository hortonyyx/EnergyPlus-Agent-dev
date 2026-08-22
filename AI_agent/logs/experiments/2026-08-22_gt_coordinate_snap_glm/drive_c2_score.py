#!/usr/bin/env python3
"""S1 lock-2 scratch driver: score the six-image sm25 run against a GT file.

Replicates ``run_stage._grade_typed_attempt_artifacts`` exactly (same service
entry, same sidecar inputs) but reads the run directory READ-ONLY and writes
the score sidecar into this experiment directory — nothing under ``case_tests/``
is written.

Usage:
  python drive_c2_score.py <gt_file> <out_dir> [--expected-kind c2_scored]
Exit 0 iff the payload kind == --expected-kind (default c2_scored).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts/tool_scripts"))

RUN_DIR = REPO / "case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H2_fullcase"


def main() -> int:
    gt_file = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    expected = "c2_scored"
    if "--expected-kind" in sys.argv:
        expected = sys.argv[sys.argv.index("--expected-kind") + 1]
    global RUN_DIR
    if "--run-dir" in sys.argv:
        RUN_DIR = Path(sys.argv[sys.argv.index("--run-dir") + 1]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    import run_stage
    from src.agent.execution.manifest import hash_text
    from src.agent.execution.view_manifest import ViewManifest, resolve_frozen_reading_exam_scope
    from src.agent.judge.score_config import load_judge_score_config
    from src.agent.judge.score_inputs import (load_score_view_bindings, select_score_view_bindings,
                                              validate_score_view_bindings_against_gt)
    from src.agent.judge.score_schema import build_product_identity, load_score_gt_identity
    from src.agent.judge.reading_typed_adapter import identify_reading_contract
    from src.agent.judge.score_service import score_attempt_service, score_criteria_for_payload
    from build_score_view_bindings import build as build_bindings

    attempt_dir = RUN_DIR / "0_reading/attempts/001"
    output_text = (attempt_dir / "output.json").read_text(encoding="utf-8")
    output = json.loads(output_text)
    output = run_stage._as_reading_views_envelope(output)

    base = ViewManifest.model_validate_json((RUN_DIR / "_run/view_manifest.json").read_text(encoding="utf-8"))
    gt_identity, typed_gt = load_score_gt_identity(gt_file)
    if typed_gt is None:
        print("GT is not a scorable c2 v3 document")
        return 2

    # Rebuild the judge-owned binding sidecar against THIS gt (the run's own
    # sidecar pins the pre-S1 gt sha and is intentionally left untouched).
    bindings = build_bindings(RUN_DIR, gt_file, None)
    bindings_path = out_dir / "judge_score_bindings.json"
    bindings_path.write_text(bindings.model_dump_json(indent=1), encoding="utf-8")

    exam_scope = resolve_frozen_reading_exam_scope(RUN_DIR, base)
    if exam_scope is not None:
        bindings = select_score_view_bindings(bindings=bindings, input_ids=set(exam_scope.input_ids))
        validate_score_view_bindings_against_gt(bindings=bindings, base=base, gt=typed_gt,
                                                input_ids=set(exam_scope.input_ids))

    product = build_product_identity(stage="reading", attempt=1,
                                     output_sha256=hash_text(output_text),
                                     output_schema=identify_reading_contract(output).contract_id,
                                     source="attempt_output", accepted_stage_record=None)
    request = {"gt_identity": gt_identity, "gt": typed_gt, "stage": "reading",
               "product_payload": output, "product_identity": product, "base_view_manifest": base,
               "score_bindings": bindings, "completeness_overlay": None,
               "c2_config": load_judge_score_config(REPO / "src/configs/judge_score.yaml"),
               "window_host_proof": None, "run_profile": "exploratory"}
    if exam_scope is not None:
        request["reading_exam_scope_input_ids"] = set(exam_scope.input_ids)
        request["reading_exam_scope_source"] = exam_scope.source
    result = score_attempt_service(typed_request=request)
    (out_dir / "score_vs_gt.json").write_text(result.sidecar.model_dump_json(indent=1), encoding="utf-8")

    payload = result.payload
    print("payload.kind:", payload.kind)
    if payload.kind == "c2_scored":
        applicability = {item.channel: item.status for item in payload.channel_applicability}
        print("channel_applicability:", json.dumps(applicability, default=str))
        criteria = [(item.criterion_id, item.verdict) for item in score_criteria_for_payload(payload)]
        print("criteria:", json.dumps(criteria))
    else:
        print("error_code:", payload.error_code, "| gate:", payload.gate_id)
    return 0 if payload.kind == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
