"""Offline checks for the D1 role-division routing contract."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.runtime_configuration import argv_for, load_configuration
from src.agent.runtime_roles.config import ROLE_NAMES, load_roles


ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_d1/configs"


def role(provider="glm-subscription-anthropic", model="glm-5.3-flash",
         effort="medium", output_tokens=32_000):
    return {
        "provider": provider,
        "model": model,
        "reasoning_effort": effort,
        "output_tokens": output_tokens,
    }


def roles(**overrides):
    value = {name: role() for name in ROLE_NAMES}
    for name, replacement in overrides.items():
        value[name] = replacement
    return value


def case(mode="role_division"):
    value = {
        "case_id": "role-config-test",
        "mode": mode,
        "provider": "glm-subscription-anthropic",
        "model": "glm-5.3-flash",
        "credentials_file": "private-test.env",
        "input_kind": "images",
        "input": "case_tests/e2e_tests/sm24_anchor/case_data",
        "image_kind": "drawings",
        "floor_plan_images": ["1f_view.png"],
        "output": "AI_agent/archive/local_backup/d1/role-config-test",
        "scope": "offline configuration test",
        "limits": {
            "model_calls": 10,
            "tool_calls": 20,
            "tokens": 500_000,
            "seconds": 60,
            "model_retries": 2,
            "retry_backoff_seconds": 1.0,
        },
        "max_candidates": 24,
        "context_tokens": 900_000,
        "compact_at_tokens": 150_000,
        "output_tokens": 32_000,
        "reasoning_effort": "medium",
    }
    if mode == "role_division":
        value["roles"] = roles()
    return value


def configuration(one_case):
    return {
        "schema_version": 1,
        "batch_id": "role-config-test",
        "approval_required_before_launch": True,
        "maximum_seconds_per_case": 60,
        "cases": [one_case],
    }


def load(tmp_path, one_case):
    path = tmp_path / "configuration.json"
    path.write_text(json.dumps(configuration(one_case)), encoding="utf-8")
    return load_configuration(path)


def test_roles_require_all_fixed_identities_and_reject_unknown_identity():
    missing = roles()
    missing.pop("elevation_reader")
    with pytest.raises(ValueError, match="missing roles: elevation_reader"):
        load_roles(missing)
    extra = roles(auditor=role())
    with pytest.raises(ValueError, match="unexpected roles: auditor"):
        load_roles(extra)
    with pytest.raises(ValueError, match="explicit roles object"):
        load_roles(None)


@pytest.mark.parametrize("field", ["provider", "model", "reasoning_effort", "output_tokens"])
def test_role_route_has_no_field_inheritance(field):
    incomplete = role()
    incomplete.pop(field)
    with pytest.raises(ValidationError, match=field):
        load_roles(roles(plan_reader=incomplete))


@pytest.mark.parametrize(("provider", "model", "effort", "tokens"), [
    ("glm-subscription-anthropic", "glm-5.3-flash", "medium", 32_000),
    ("glm-subscription", "glm-5.3-flash", "medium", 32_000),
    ("paratera", "Qwen3.8-27B", "high", 16_384),
])
def test_existing_anthropic_and_openai_compatible_routes_are_accepted(
        provider, model, effort, tokens):
    parsed = load_roles({name: role(provider, model, effort, tokens) for name in ROLE_NAMES})
    assert parsed["plan_reader"].provider == provider
    assert parsed["elevation_reader"].model == model


def test_unreviewed_route_deepseek_and_low_output_are_rejected():
    with pytest.raises(ValidationError, match="reviewed live provider"):
        load_roles(roles(coordinator=role("unknown-route")))
    with pytest.raises(ValidationError, match="DeepSeek"):
        load_roles(roles(coordinator=role("paratera", "DeepSeek-V3.2", "high", 32_000)))
    with pytest.raises(ValidationError, match="recommended minimum 32000"):
        load_roles(roles(coordinator=role(output_tokens=1024)))


def test_scripted_routes_need_the_explicit_offline_switch():
    scripted = {name: role("scripted", "scripted-model", "offline", 128)
                for name in ROLE_NAMES}
    with pytest.raises(ValidationError, match="explicit offline runtime"):
        load_roles(scripted)
    parsed = load_roles(scripted, allow_scripted=True)
    assert parsed["coordinator"].output_tokens == 128
    with pytest.raises(ValidationError, match="explicit offline runtime"):
        load_roles({**scripted, "plan_reader": role(
            "scripted", "glm-5.3-flash", "offline", 128)}, allow_scripted=True)


def test_role_configuration_is_drawing_only_and_coordinator_is_unambiguous(tmp_path):
    mesh = case()
    mesh["input_kind"] = "mesh"
    with pytest.raises(ValueError, match="drawing images only"):
        load(tmp_path, mesh)
    photograph = case()
    photograph["image_kind"] = "photographs"
    with pytest.raises(ValueError, match="drawing images only"):
        load(tmp_path, photograph)
    mismatch = case()
    mismatch["roles"]["coordinator"]["reasoning_effort"] = "high"
    with pytest.raises(ValueError, match="top-level coordinator routing.*reasoning_effort"):
        load(tmp_path, mismatch)


def test_role_argv_carries_canonical_inline_routes_and_default_concurrency(tmp_path):
    selected = load(tmp_path, case())["cases"][0]
    argv = argv_for(selected)
    assert argv[1:3] == ["-m", "src.agent.runtime_roles.entry"]
    encoded = argv[argv.index("--roles-json") + 1]
    assert json.loads(encoded) == roles()
    assert encoded == json.dumps(roles(), ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"))
    assert argv[argv.index("--max-concurrent-readers") + 1] == "8"
    assert argv[argv.index("--max-candidates") + 1] == "24"
    assert argv[argv.index("--context-tokens") + 1] == "900000"
    assert argv[argv.index("--compact-at-tokens") + 1] == "150000"
    assert argv[argv.index("--model-retries") + 1] == "2"
    assert argv[argv.index("--retry-backoff-seconds") + 1] == "1.0"
    from src.agent.runtime_roles.entry import parser
    parsed = parser().parse_args(argv[3:])
    assert parsed.roles_json == encoded and parsed.max_concurrent_readers == 8


def test_invalid_reader_concurrency_is_explicit(tmp_path):
    for value in (0, -1, 1.5, True):
        selected = case()
        selected["max_concurrent_readers"] = value
        with pytest.raises(ValueError, match="positive integer"):
            load(tmp_path, selected)


def test_single_model_argv_remains_the_exact_existing_shape(tmp_path):
    selected = load(tmp_path, case("single_model"))["cases"][0]
    argv = argv_for(selected)
    expected = [
        sys.executable, "-m", "src.agent.runtime_entry",
        "--out", str(ROOT / selected["output"]),
        "--provider", "glm-subscription-anthropic",
        "--model", "glm-5.3-flash",
        "--credentials-file", str((ROOT / "private-test.env").resolve()),
        "--scope", "offline configuration test",
        "--image-kind", "drawings",
        "--model-calls", "10", "--tool-calls", "20", "--seconds", "60",
        "--output-tokens", "32000", "--tokens", "500000",
        "--images", str(ROOT / "case_tests/e2e_tests/sm24_anchor/case_data"),
        "--floor-plan-image", "1f_view.png",
        "--reasoning-history", "all", "--max-candidates", "24",
        "--context-tokens", "900000", "--compact-at-tokens", "150000",
        "--model-retries", "2", "--retry-backoff-seconds", "1.0",
        "--reasoning-effort", "medium",
    ]
    assert argv == expected
    assert "--roles-json" not in argv and "--max-concurrent-readers" not in argv


def test_single_model_ignores_role_only_comparison_metadata(tmp_path):
    selected = case("single_model")
    baseline = argv_for(load(tmp_path, selected)["cases"][0])
    with_metadata = copy.deepcopy(selected)
    with_metadata["max_concurrent_readers"] = 4
    assert argv_for(load(tmp_path, with_metadata)["cases"][0]) == baseline


@pytest.mark.parametrize("case_name", ["sm21", "sm24", "sm25"])
def test_prepared_comparison_pairs_change_only_role_conditions_and_output_identity(case_name):
    single_path = CONFIGS / f"{case_name}_single.json"
    divided_path = CONFIGS / f"{case_name}_role_division.json"
    single = json.loads(single_path.read_bytes())
    divided = json.loads(divided_path.read_bytes())
    assert single["batch_id"] == divided["batch_id"]
    left, right = single["cases"][0], divided["cases"][0]
    assert left["case_id"] == right["case_id"]
    changed = {key for key in set(left) | set(right) if left.get(key) != right.get(key)}
    assert changed == {"mode", "roles", "scope", "output"}
    left_scope, right_scope = left["scope"].splitlines(), right["scope"].splitlines()
    assert left_scope[:2] == right_scope[:2] and left_scope[3:] == right_scope[3:]
    assert left["limits"] == right["limits"] == {
        "model_calls": 400,
        "tool_calls": 800,
        "tokens": 30_000_000,
        "seconds": 10_800,
        "model_retries": 2,
        "retry_backoff_seconds": 1.0,
    }
    assert left["max_concurrent_readers"] == right["max_concurrent_readers"] == 4
    assert left["credentials_file"] == right["credentials_file"] == (
        r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\.env")
    assert Path(left["output"]).is_relative_to(Path("AI_agent/archive/local_backup/d1"))
    assert Path(right["output"]).is_relative_to(Path("AI_agent/archive/local_backup/d1"))
    assert load_configuration(single_path)["cases"][0]["mode"] == "single_model"
    assert load_configuration(divided_path)["cases"][0]["mode"] == "role_division"
