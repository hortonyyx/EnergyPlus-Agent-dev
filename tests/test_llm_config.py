"""Per-case LLM config override resolution (no network).

Verifies that `$EP_AGENT_LLM_CONFIG` redirects `load_llm_section` to a per-case
config file, so a formal test run can pin its own model combination without
editing the global src/configs/llm.yaml.
"""

from __future__ import annotations

import pytest

from src.agent import llm as llm_mod
from src.agent.llm import (
    LLM_CONFIG_ENV,
    load_llm_section,
    resolve_llm_config_path,
)


def test_default_when_env_unset(monkeypatch):
    monkeypatch.delenv(LLM_CONFIG_ENV, raising=False)
    assert resolve_llm_config_path() == llm_mod._DEFAULT_LLM_CONFIG


def test_env_override_redirects_and_loads(monkeypatch, tmp_path):
    cfg = tmp_path / "llm.yaml"
    cfg.write_text(
        "intake_correction:\n"
        "  provider: openai\n"
        "  model_name: per-case-model\n"
        "  api_key: dummy\n"
        "  max_tokens: 123\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(LLM_CONFIG_ENV, str(cfg))
    assert resolve_llm_config_path() == cfg
    section = load_llm_section("intake_correction")
    assert section["model_name"] == "per-case-model"
    assert section["max_tokens"] == 123


def test_env_override_missing_file_raises(monkeypatch):
    monkeypatch.setenv(LLM_CONFIG_ENV, "/nonexistent/per_case/llm.yaml")
    with pytest.raises(FileNotFoundError):
        resolve_llm_config_path()


# --- pipeline._section strict resolution (review M1, 2026-06-14) ------------
# `intake_<stage>` resolves to its own section; a missing `intake_mep` falls
# back to `intake_correction`, but a missing `intake_correction` must RAISE
# rather than silently inherit the downstream `default` ReAct config.

from src.agent import pipeline as pipeline_mod  # noqa: E402


def _write_cfg(tmp_path, body: str):
    cfg = tmp_path / "llm.yaml"
    cfg.write_text(body, encoding="utf-8")
    return cfg


_CORRECTION_ONLY = (
    "intake_correction:\n"
    "  provider: openai\n"
    "  model_name: correction-model\n"
    "  api_key: dummy\n"
)


def test_section_mep_falls_back_to_correction(monkeypatch, tmp_path):
    """intake_mep absent -> use intake_correction (which is present)."""
    monkeypatch.setenv(LLM_CONFIG_ENV, str(_write_cfg(tmp_path, _CORRECTION_ONLY)))
    section = pipeline_mod._section("mep")
    assert section["model_name"] == "correction-model"


def test_section_correction_missing_raises(monkeypatch, tmp_path):
    """intake_correction absent -> RAISE, never silently fall to `default`."""
    cfg = _write_cfg(
        tmp_path,
        "default:\n  provider: openai\n  model_name: downstream-default\n  api_key: dummy\n",
    )
    monkeypatch.setenv(LLM_CONFIG_ENV, str(cfg))
    with pytest.raises(RuntimeError, match="intake_correction"):
        pipeline_mod._section("correction")
    # mep must also refuse rather than borrow `default`
    with pytest.raises(RuntimeError, match="intake_correction"):
        pipeline_mod._section("mep")


def test_section_present_but_broken_propagates(monkeypatch, tmp_path):
    """Section present but with an unresolvable interpolation -> error surfaces."""
    monkeypatch.delenv("EP_TEST_MISSING_VAR", raising=False)
    cfg = _write_cfg(
        tmp_path,
        "intake_correction:\n"
        "  provider: openai\n"
        "  model_name: correction-model\n"
        "  api_key: ${oc.env:EP_TEST_MISSING_VAR}\n",
    )
    monkeypatch.setenv(LLM_CONFIG_ENV, str(cfg))
    with pytest.raises(Exception):
        pipeline_mod._section("correction")
