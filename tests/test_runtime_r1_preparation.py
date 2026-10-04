from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.agent.runtime_configuration import argv_for, load_configuration


ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "AI_agent/logs/experiments/2026-10-03_runtime_r1/configs"
HISTORICAL_REASON = "Offline check of historical R1 routing; preserve the original small cap as evidence."


def test_migration_configuration_is_directly_routable_with_glm_native_reasoning():
    with pytest.raises(ValueError, match="recommended minimum 32000"):
        load_configuration(CONFIGS / "migration_sm24_glm_paratera.json")
    value = load_configuration(CONFIGS / "migration_sm24_glm_paratera.json",
        low_output_limit_reason=HISTORICAL_REASON)
    case = value["cases"][0]
    argv = argv_for(case)
    assert argv[argv.index("--model") + 1] == "GLM-5.3-Flash"
    assert argv[argv.index("--reasoning-effort") + 1] == "high"
    assert argv[argv.index("--seconds") + 1] == "3000"
    assert argv[argv.index("--max-candidates") + 1] == "24"
    assert argv[argv.index("--model-retries") + 1] == "2"
    assert argv[argv.index("--compact-at-tokens") + 1] == "150000"
    assert "--context-window" not in argv


def test_first_full_cases_retain_per_case_time_and_durable_request_caps():
    value = load_configuration(CONFIGS / "first_full_cases.json",
        low_output_limit_reason=HISTORICAL_REASON)
    assert {case["case_id"] for case in value["cases"]} == {
        "sm24_first_full_case", "voimatalo_first_full_case"}
    for case in value["cases"]:
        argv = argv_for(case)
        assert argv[argv.index("--seconds") + 1] == "6600"
        assert argv[argv.index("--quota-limit") + 1] == str(case["quota_limit"])
        assert argv[argv.index("--max-concurrent-observers") + 1] == "4"
        assert Path(argv[argv.index("--quota-journal") + 1]).is_relative_to(ROOT)


def test_resume_only_adds_explicit_resume_flag():
    value = json.loads((CONFIGS / "migration_sm24_glm_paratera.json").read_bytes())
    value["cases"][0]["low_output_limit_reason"] = HISTORICAL_REASON
    plain = argv_for(value["cases"][0])
    resumed = argv_for(value["cases"][0], resume=True)
    assert resumed == [*plain, "--resume"]
