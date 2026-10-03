"""Rebuild the accepted R1 GLM calibration checks without new requests."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
HISTORICAL_COMMIT = "fcbbda75"
SUMMARY_PATH = (
    "AI_agent/logs/experiments/2026-10-03_runtime_r1/"
    "glm_calibration/summary.json"
)


def historical_file(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{HISTORICAL_COMMIT}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def historical_profile(model: str):
    from src.agent_runtime.estimation import _profile_from_dict

    profiles = json.loads(historical_file("src/agent_runtime/model_profiles.json"))
    folded = model.casefold()
    row = next(
        row
        for row in profiles["profiles"]
        if folded
        in {
            row["canonical_name"].casefold(),
            *(alias.casefold() for alias in row.get("aliases", ())),
        }
    )
    # The R1 profile predates reasoning allowances. R1b's compatibility
    # defaults reconstruct its original zero allowance and reservation totals.
    return _profile_from_dict(row)


def verify() -> bytes:
    from src.agent_runtime.estimation import estimate_chat_request

    source_path = HERE / "run_calibration.py"
    source_rel = source_path.relative_to(ROOT).as_posix()
    assert source_path.read_bytes() == historical_file(source_rel)
    source = load_module("r1_glm_calibration_verify_source", source_path)

    response_document = json.loads((HERE / "responses.json").read_bytes())
    saved = response_document["rows"]
    quota_rows = [
        json.loads(line) for line in (HERE / "quota.jsonl").read_bytes().splitlines()
    ]
    attempts = [row for row in quota_rows if row["event"] == "attempt"]
    responses = [row for row in quota_rows if row["event"] == "response"]
    assert [row["ticket"] for row in attempts] == list(range(1, 6))
    assert [row["ticket"] for row in responses] == list(range(1, 6))
    assert all(row["limit"] == 5 for row in quota_rows)
    assert response_document["model"] == source.MODEL
    assert response_document["parameters"] == source.PARAMETERS

    profile = historical_profile(source.MODEL)
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    reservations = []
    reported_totals = []
    covered = []
    summary_rows = []
    returned_models = set()
    output_observations = {}
    cases = source.cases()
    assert len(cases) == len(saved) == len(responses) == 5
    for case, record, quota in zip(cases, saved, responses, strict=True):
        body = {
            "model": source.MODEL,
            "messages": case["messages"],
            "stream": False,
            "n": 1,
            **source.PARAMETERS,
        }
        assert record["case"] == case["name"]
        assert record["request"] == source.sanitized_body(body, case.get("image"))
        assert record["image"] == case.get("image")
        raw_response = record["response"]
        usage = raw_response["usage"]
        assert usage == quota["usage"]
        returned_models.add(raw_response["model"])
        estimate = estimate_chat_request(body, profile=profile, strict=True)
        assert estimate.reasoning_token_allowance == 0
        assert estimate.input_tokens_upper_bound >= usage["prompt_tokens"]
        for key in totals:
            totals[key] += usage[key]
        reservations.append(estimate.reservation_tokens)
        reported_totals.append(usage["total_tokens"])
        covered.append(usage["total_tokens"] <= estimate.reservation_tokens)
        row = {
            "case": record["case"],
            "actual_input": usage["prompt_tokens"],
        }
        if estimate.image_tokens:
            row.update(
                estimated_text=estimate.text_tokens,
                estimated_image=estimate.image_tokens,
            )
        row.update(
            estimate=estimate.input_tokens_estimate,
            upper_bound=estimate.input_tokens_upper_bound,
            point_error_percent=round(
                100
                * (estimate.input_tokens_estimate - usage["prompt_tokens"])
                / usage["prompt_tokens"],
                2,
            ),
        )
        summary_rows.append(row)
        if record["case"] in {"text_control", "text_long"}:
            choice = raw_response["choices"][0]
            output_observations[record["case"]] = {
                "completion_tokens": usage["completion_tokens"],
                "reasoning_tokens": usage.get("completion_tokens_details", {}).get(
                    "reasoning_tokens"
                ),
                "finish_reason": choice["finish_reason"],
            }

    expected_bytes = historical_file(SUMMARY_PATH)
    expected = json.loads(expected_bytes)
    assert (HERE / "summary.json").read_bytes() == expected_bytes
    assert expected["model_requested"] == source.MODEL
    assert returned_models == {expected["model_returned"]}
    assert expected["parameters_requested"] == source.PARAMETERS
    assert expected["requests"] == len(attempts) == 5
    assert expected["retries"] == 0
    assert expected["fallbacks"] == 0
    assert expected["reported_usage"] == totals
    observation = expected["output_limit_observation"]
    assert observation["requested_max_tokens_each"] == source.PARAMETERS["max_tokens"]
    assert observation["text_control"] == output_observations["text_control"]
    assert observation["text_long"] == output_observations["text_long"]
    reservation_check = expected["complete_request_reservation_check"]
    assert reservation_check["reserved_totals"] == reservations
    assert reservation_check["reported_totals"] == reported_totals
    assert reservation_check["covered"] == covered
    assert expected["rows"] == summary_rows
    assert expected["schema_version"] == 1
    assert hashlib.sha256(expected_bytes).hexdigest() == (
        "4c685e1303ea6dfc16e22db241cfe1cedfe35dab9ad9114d6f52d5406e2c27f5"
    )
    return expected_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(result)
    print(json.dumps({"status": "passed", "output": str(args.out)}))


if __name__ == "__main__":
    main()
