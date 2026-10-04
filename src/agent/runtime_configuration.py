"""Validate or start an approved whole-case configuration.

This module performs no model call for ``check`` or ``command``.  ``launch``
execs the reviewed runtime entry exactly once and is intended only after the
separate whole-case approval recorded by the project lead.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path

from src.agent.runtime_entry import ROOT
from src.agent_runtime.estimation import get_model_profile
from src.agent_runtime.output_limits import validate_output_limit
from src.agent_runtime.providers import LIVE_PROVIDERS, provider_parameters, validate_provider_model


ALLOWED_ENTRYPOINTS = {
    "single_model": "src.agent.runtime_entry",
    "external_coordinator_mcp": "src.agent.runtime_coordinator",
}


def load_configuration(path: Path, *, low_output_limit_reason: str | None = None) -> dict:
    value = json.loads(path.read_bytes())
    if value.get("schema_version") != 1:
        raise ValueError("unsupported run configuration schema")
    if not value.get("approval_required_before_launch"):
        raise ValueError("whole-case configuration must retain its approval gate")
    cases = value.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("configuration needs at least one case")
    identities = [case.get("case_id") for case in cases]
    if len(set(identities)) != len(identities) or not all(identities):
        raise ValueError("case IDs must be present and unique")
    for case in cases:
        mode = case.get("mode")
        if mode not in ALLOWED_ENTRYPOINTS:
            raise ValueError(f"unsupported run mode {mode!r}")
        if case.get("provider") not in LIVE_PROVIDERS:
            raise ValueError("live configuration requires a reviewed provider")
        model = case.get("model")
        validate_provider_model(case["provider"], model)
        provider_parameters(case["provider"], output_tokens=case.get("output_tokens"),
            temperature=case.get("temperature"), thinking=case.get("thinking", True),
            reasoning_effort=case.get("reasoning_effort"))
        get_model_profile(model, strict=True)
        if low_output_limit_reason is not None:
            case["low_output_limit_reason"] = low_output_limit_reason
        validate_output_limit(model, case.get("output_tokens"), reason=case.get("low_output_limit_reason"))
        if "deepseek" in model.casefold():
            raise ValueError("DeepSeek is outside this approved batch")
        seconds = case.get("limits", {}).get("seconds")
        if type(seconds) not in {int, float} or seconds <= 0:
            raise ValueError("each case needs a positive time ceiling")
        if seconds > value["maximum_seconds_per_case"]:
            raise ValueError("case exceeds the configuration's time ceiling")
        for key in ("input", "output"):
            target = (ROOT / case[key]).resolve()
            if not target.is_relative_to(ROOT):
                raise ValueError(f"{key} escapes the worktree")
            if key == "input" and not target.exists():
                raise ValueError(f"input does not exist: {target}")
        floors = case.get("floor_plan_images")
        if floors is not None and (not isinstance(floors, list) or any(
                not isinstance(name, str) or Path(name).name != name
                or not (ROOT / case["input"] / name).is_file() for name in floors)):
            raise ValueError("floor_plan_images must use admitted input filenames")
        if not isinstance(case.get("credentials_file"), str) or not case["credentials_file"].strip():
            raise ValueError("each case requires an explicit read-only credentials_file")
    return value


def selected_case(configuration: dict, case_id: str) -> dict:
    matches = [case for case in configuration["cases"] if case["case_id"] == case_id]
    if not matches:
        raise ValueError(f"unknown case {case_id!r}")
    return matches[0]


def argv_for(case: dict, *, resume: bool = False) -> list[str]:
    validate_output_limit(case["model"], case.get("output_tokens"), reason=case.get("low_output_limit_reason"))
    limits = case["limits"]
    argv = [sys.executable, "-m", ALLOWED_ENTRYPOINTS[case["mode"]],
            "--out", str(ROOT / case["output"]), "--provider", case["provider"],
            "--model", case["model"], "--credentials-file", case["credentials_file"],
            "--scope", case["scope"], "--image-kind", case["image_kind"],
            "--model-calls", str(limits["model_calls"]),
            "--tool-calls", str(limits["tool_calls"]),
            "--tokens", str(limits["tokens"]), "--seconds", str(limits["seconds"]),
            "--output-tokens", str(case["output_tokens"])]
    source_flag = "--mesh" if case["input_kind"] == "mesh" else "--images"
    if case.get("low_output_limit_reason") is not None:
        argv += ["--low-output-limit-reason", case["low_output_limit_reason"]]
    for name in ("max_consecutive_truncations", "max_total_truncations"):
        if name in limits:
            argv += ["--" + name.replace("_", "-"), str(limits[name])]
    argv += [source_flag, str(ROOT / case["input"])]
    for name in case.get("floor_plan_images", []):
        argv += ["--floor-plan-image", name]
    if case["mode"] == "single_model":
        argv += ["--max-candidates", str(case["max_candidates"]),
                 "--context-tokens", str(case["context_tokens"]),
                 "--compact-at-tokens", str(case.get("compact_at_tokens", 150_000)),
                 "--model-retries", str(limits.get("model_retries", 2)),
                 "--retry-backoff-seconds", str(limits.get("retry_backoff_seconds", 1.0))]
        for name in ("temperature", "reasoning_effort"):
            if case.get(name) is not None:
                argv += ["--" + name.replace("_", "-"), str(case[name])]
    else:
        if case.get("reasoning_effort") is not None:
            argv += ["--reasoning-effort", case["reasoning_effort"]]
        argv += ["--quota-journal", str(ROOT / case["quota_journal"]),
                 "--quota-limit", str(case["quota_limit"]),
                 "--max-concurrent-observers", str(case["max_concurrent_observers"])]
        argv.append("--thinking" if case.get("thinking", True) else "--no-thinking")
    if resume:
        argv.append("--resume")
    return argv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "command", "launch"))
    parser.add_argument("configuration", type=Path)
    parser.add_argument("--case")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--low-output-limit-reason", help="record a reason without editing a historical configuration")
    args = parser.parse_args()
    configuration = load_configuration(args.configuration.resolve(), low_output_limit_reason=args.low_output_limit_reason)
    if args.action == "check":
        print(json.dumps({"status": "ready", "batch_id": configuration["batch_id"],
                          "cases": [case["case_id"] for case in configuration["cases"]]},
                         ensure_ascii=False))
        return
    if not args.case:
        parser.error("--case is required for command or launch")
    case = selected_case(configuration, args.case)
    command = argv_for(case, resume=args.resume)
    if args.action == "command":
        print(shlex.join(command))
        return
    os.execvpe(command[0], command, {**os.environ, "PYTHONPATH": str(ROOT),
                                     "PYTHONDONTWRITEBYTECODE": "1"})


if __name__ == "__main__":
    main()
