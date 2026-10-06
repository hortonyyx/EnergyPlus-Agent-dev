"""Score the D1 fourth passed plan trial and delivered North/East readings."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scoring_bridge import convert_role_artifacts, score_scoped_answer, write_json


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
D1 = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_d1"
D1A = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis"
ARCHIVE = ROOT / "AI_agent/archive/local_backup/d1b/small_test"
PLAN_TASK = "2c8d02b978e4834856efd80855fe3f43921721036eb957f7fc56f70d1c784af4"
EAST_TASK = "470c683aafbba1982252452b12565cc2f27561d0bcc939250aeb9b214af063f5"
NORTH_TASK = "58e9b0befc8caffee48045e9006634474ee0e1b7dc81a1dd98e9e9b07bb55d46"


def _verify_archive() -> dict:
    manifest = json.loads((D1 / "evidence/small_test_manifest.json").read_text(encoding="utf-8"))
    failures = []
    for relative, expected in manifest["files_sha256"].items():
        path = ARCHIVE / Path(relative.replace("\\", "/"))
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})
    if failures:
        raise ValueError(f"D1 small-test archive integrity failed: {failures[:3]}")
    return {
        "archive": manifest["archive"],
        "archive_sha256": manifest["archive_sha256"],
        "files_checked": len(manifest["files_sha256"]),
        "failures": 0,
    }


def main() -> None:
    archive_check = _verify_archive()
    plan_root = ARCHIVE / "tasks" / PLAN_TASK / "bim/trial_workspace"
    conversion = convert_role_artifacts(
        case="sm24_anchor",
        plan_trial_source=plan_root / "candidate_02/source_model.json",
        plan_trial_receipt=plan_root / "trial_receipts/trial_004.json",
        elevation_artifacts=[
            ARCHIVE / "tasks" / NORTH_TASK / "reader_artifact.json",
            ARCHIVE / "tasks" / EAST_TASK / "reader_artifact.json",
        ],
        assigned_plan_floors=["F1"],
        assigned_elevation_facades=["North", "East"],
    )
    scoring = score_scoped_answer(D1A / "references/sm24_anchor.json", conversion)
    write_json(HERE / "historical_role_answer.json", conversion)
    write_json(HERE / "historical_role_score.json", scoring)
    question_by_name = {
        row["question"]: row for row in scoring["assigned_role_score"]["questions"]
    }
    plan_score = question_by_name["F1"]["raw"]["floors"][0]
    east_score = question_by_name["East"]["raw"]["elevations"]
    north_score = question_by_name["North"]["raw"]["elevations"]
    plan_answer = conversion["answer"]["plan_questions"][0]
    elevations = {
        row["facade"]: row for row in conversion["answer"]["elevation_questions"]
    }
    summary = {
        "schema_version": "historical_role_scoring_summary_v1",
        "case": "sm24_anchor",
        "archive_integrity": archive_check,
        "inputs": {
            "plan": "D1 small-test fourth passed isolated trial source; not the rejected final plan answer",
            "elevations": ["North delivered reading", "East delivered reading"],
            "model_or_service_calls": 0,
            "reported_tokens": None,
            "billing": None,
            "usage_note": "Offline conversion and scoring reused existing D1 artifacts; no provider request was made.",
        },
        "neutral_answer_shape": {
            "plan_floors": 1,
            "rooms": len(plan_answer["rooms"]),
            "plan_openings": len(plan_answer["openings"]),
            "elevation_facades": len(elevations),
            "elevation_openings": {
                facade: len(row["openings"]) for facade, row in sorted(elevations.items())
            },
        },
        "assigned_scope": scoring["coverage"]["assigned"],
        "assigned_role_result": {
            "status": scoring["assigned_role_score"]["status"],
            "questions_passed": scoring["assigned_role_score"]["questions_passed"],
            "questions_total": scoring["assigned_role_score"]["questions_total"],
            "questions": [
                {"role": row["role"], "question": row["question"], "status": row["status"]}
                for row in scoring["assigned_role_score"]["questions"]
            ],
            "strict_details": {
                "F1": {
                    "exterior": plan_score["exterior"]["status"],
                    "partitions": plan_score["partitions"]["status"],
                    "rooms": plan_score["rooms"]["status"],
                    "plan_opening_positions": (
                        f"{plan_score['openings']['positions']}/"
                        f"{plan_score['openings']['reference_count']}"
                    ),
                },
                "East": (
                    f"{east_score['within_tolerance']}/{east_score['reference_count']}"
                ),
                "North": (
                    f"{north_score['within_tolerance']}/{north_score['reference_count']}"
                ),
            },
        },
        "complete_reference_result": {
            "status": scoring["complete_reference_score"]["status"],
            "unassigned_reference": scoring["coverage"]["unassigned_reference"],
            "assigned_red_items": ["F1 strict plan geometry"],
        },
        "limits": [
            "The plan input is a passed intermediate trial and remains labelled as such.",
            "South and West were not assigned in this historical three-question test; they are absent from the role denominator and listed in complete coverage.",
            "The D1-A scorer and reference files were read unchanged.",
        ],
        "unresolved": [
            "The passed F1 trial remains severe under the unchanged D1-A strict partition/room boundary score; 15 of 21 plan opening positions are within their frozen tolerances.",
            "This historical run cannot prove the final D1b submit path because its plan final answer was rejected and is intentionally not substituted for a delivery.",
            "Complete-reference status remains severe from the strict F1 plan result and absent unassigned South/West; assigned-role status reports only F1, North, and East.",
        ],
    }
    write_json(HERE / "historical_scoring_summary.json", summary)
    print(json.dumps(summary["assigned_role_result"], ensure_ascii=False))


if __name__ == "__main__":
    main()
