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
        "intake_phase2:\n"
        "  provider: openai\n"
        "  model_name: per-case-model\n"
        "  api_key: dummy\n"
        "  max_tokens: 123\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(LLM_CONFIG_ENV, str(cfg))
    assert resolve_llm_config_path() == cfg
    section = load_llm_section("intake_phase2")
    assert section["model_name"] == "per-case-model"
    assert section["max_tokens"] == 123


def test_env_override_missing_file_raises(monkeypatch):
    monkeypatch.setenv(LLM_CONFIG_ENV, "/nonexistent/per_case/llm.yaml")
    with pytest.raises(FileNotFoundError):
        resolve_llm_config_path()
