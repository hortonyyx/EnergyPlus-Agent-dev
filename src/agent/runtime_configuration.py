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
import subprocess
import sys
from pathlib import Path

from src.agent.runtime_entry import ROOT
from src.agent_runtime.estimation import get_model_profile
from src.agent_runtime.output_limits import validate_output_limit
from src.agent_runtime.accounting import require_cny_price_schedule
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.run_paths import resolve_run_output
from src.agent_runtime.providers import LIVE_PROVIDERS, provider_parameters, validate_provider_model
from src.agent.runtime_roles.config import load_roles


ALLOWED_ENTRYPOINTS = {
    "single_model": "src.agent.runtime_entry",
    "external_coordinator_mcp": "src.agent.runtime_coordinator",
    "role_division": "src.agent.runtime_roles.entry",
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
        role_configurations = None
        if mode == "role_division":
            if case.get("input_kind") != "images" or case.get("image_kind") != "drawings":
                raise ValueError("role_division supports drawing images only; mesh and non-drawing inputs are not admitted")
            role_configurations = load_roles(case.get("roles"))
            concurrency = case.get("max_concurrent_readers", 8)
            if type(concurrency) is not int or concurrency <= 0:
                raise ValueError("max_concurrent_readers must be a positive integer")
        if case.get("reasoning_history", "all") not in {"all", "current_tool_chain"}:
            raise ValueError("unsupported reasoning_history")
        if mode != "single_model" and case.get("reasoning_history", "all") != "all":
            raise ValueError("reasoning_history currently supports single_model only")
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
        if role_configurations is not None:
            coordinator = role_configurations["coordinator"]
            coordinator_fields = {
                "provider": coordinator.provider,
                "model": coordinator.model,
                "reasoning_effort": coordinator.reasoning_effort,
                "output_tokens": coordinator.output_tokens,
            }
            mismatched = [name for name, expected in coordinator_fields.items()
                          if case.get(name) != expected]
            if mismatched:
                raise ValueError("top-level coordinator routing must match roles.coordinator: "
                                 + ", ".join(mismatched))
        if "deepseek" in model.casefold():
            raise ValueError("DeepSeek is outside this approved batch")
        seconds = case.get("limits", {}).get("seconds")
        if type(seconds) not in {int, float} or seconds <= 0:
            raise ValueError("each case needs a positive time ceiling")
        if seconds > value["maximum_seconds_per_case"]:
            raise ValueError("case exceeds the configuration's time ceiling")
        validate_budget(case)
        target = (ROOT / case["input"]).resolve()
        if not target.is_relative_to(ROOT):
            raise ValueError("input escapes the worktree")
        if not target.exists():
            raise ValueError(f"input does not exist: {target}")
        if case.get("run_root") is not None and mode != "single_model":
            raise ValueError("explicit run_root currently supports single_model only")
        if case.get("run_root") is not None:
            case["run_root"] = str(Path(case["run_root"]).expanduser())
        resolve_run_output(ROOT / case["output"] if case.get("run_root") is None else Path(case["output"]), repository_root=ROOT,
                           run_root=case.get("run_root"))
        floors = case.get("floor_plan_images")
        if floors is not None and (not isinstance(floors, list) or any(
                not isinstance(name, str) or Path(name).name != name
                or not (ROOT / case["input"] / name).is_file() for name in floors)):
            raise ValueError("floor_plan_images must use admitted input filenames")
        if not isinstance(case.get("credentials_file"), str) or not case["credentials_file"].strip():
            raise ValueError("each case requires an explicit read-only credentials_file")
    return value


def validate_budget(case: dict) -> RunLimits:
    limits = case["limits"]
    if "tokens" not in limits and limits.get("money_cny") is None:
        raise ValueError("set tokens explicitly (null disables it), or supply a CNY ceiling")
    parsed = RunLimits.model_validate_json(json.dumps({
        name: limits.get(name) for name in
        ("model_calls", "tool_calls", "seconds", "tokens", "money_cny")}))
    if parsed.money_cny is not None:
        require_cny_price_schedule(case["model"], route_id=case["provider"])
    return parsed


def selected_case(configuration: dict, case_id: str) -> dict:
    matches = [case for case in configuration["cases"] if case["case_id"] == case_id]
    if not matches:
        raise ValueError(f"unknown case {case_id!r}")
    return matches[0]


def argv_for(case: dict, *, resume: bool = False) -> list[str]:
    budget = validate_budget(case)
    validate_output_limit(case["model"], case.get("output_tokens"), reason=case.get("low_output_limit_reason"))
    limits = case["limits"]
    output = resolve_run_output(ROOT / case["output"] if case.get("run_root") is None else Path(case["output"]), repository_root=ROOT,
                                run_root=case.get("run_root"))
    argv = [sys.executable, "-m", ALLOWED_ENTRYPOINTS[case["mode"]],
            "--out", str(output), "--provider", case["provider"],
            "--model", case["model"], "--credentials-file", str((ROOT / Path(case["credentials_file"]).expanduser()).resolve()),
            "--scope", case["scope"], "--image-kind", case["image_kind"],
            "--model-calls", str(limits["model_calls"]),
            "--tool-calls", str(limits["tool_calls"]),
            "--seconds", str(limits["seconds"]),
            "--output-tokens", str(case["output_tokens"])]
    if case.get("run_root") is not None:
        if case["mode"] != "single_model":
            raise ValueError("explicit run_root currently supports single_model only")
        argv += ["--run-root", str(case["run_root"])]
    argv += ["--no-token-limit"] if budget.tokens is None else ["--tokens", str(budget.tokens)]
    if budget.money_cny is not None:
        argv += ["--money-cny", str(budget.money_cny)]
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
        argv += ["--reasoning-history", case.get("reasoning_history", "all"),
                 "--max-candidates", str(case["max_candidates"]),
                 "--context-tokens", str(case["context_tokens"]),
                 "--compact-at-tokens", str(case.get("compact_at_tokens", 150_000)),
                 "--model-retries", str(limits.get("model_retries", 2)),
                 "--retry-backoff-seconds", str(limits.get("retry_backoff_seconds", 1.0))]
        for name in ("temperature", "reasoning_effort"):
            if case.get(name) is not None:
                argv += ["--" + name.replace("_", "-"), str(case[name])]
    elif case["mode"] == "external_coordinator_mcp":
        if case.get("reasoning_effort") is not None:
            argv += ["--reasoning-effort", case["reasoning_effort"]]
        argv += ["--quota-journal", str(ROOT / case["quota_journal"]),
                 "--quota-limit", str(case["quota_limit"]),
                 "--max-concurrent-observers", str(case["max_concurrent_observers"])]
        argv.append("--thinking" if case.get("thinking", True) else "--no-thinking")
    else:
        roles = load_roles(case.get("roles"))
        argv += ["--roles-json", json.dumps(
                    {name: configuration.model_dump() for name, configuration in roles.items()},
                    ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                 "--max-concurrent-readers", str(case.get("max_concurrent_readers", 8)),
                 "--max-candidates", str(case["max_candidates"]),
                 "--context-tokens", str(case["context_tokens"]),
                 "--compact-at-tokens", str(case.get("compact_at_tokens", 150_000)),
                 "--model-retries", str(limits.get("model_retries", 2)),
                 "--retry-backoff-seconds", str(limits.get("retry_backoff_seconds", 1.0))]
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
        # Printed commands are for the host shell; launch itself always uses argv.
        print("& " + " ".join("'" + value.replace("'", "''") + "'" for value in command)
              if os.name == "nt" else shlex.join(command))
        return
    environment = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    if os.name == "nt":
        raise SystemExit(subprocess.call(command, env=environment))
    os.execvpe(command[0], command, environment)


if __name__ == "__main__":
    main()
