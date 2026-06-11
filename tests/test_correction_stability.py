"""Unit tests for 1_correction stability hardening in src.agent.pipeline:
JSON-parse / semantic retry in `_call_json_llm`, plus the composite correction
validator (_make_correction_validator) that catches the sm21 0-window class,
duplicate cell ids, z-stack gaps, and illegal facade values. OpenAI is
mocked — no network."""

from __future__ import annotations

import json

import pytest

from src.agent import pipeline

SECTION = {"api_key": "x", "model_name": "m"}


def _resp(content: str, finish_reason: str = "stop"):
    class _Obj:
        pass

    msg = _Obj()
    msg.content = content
    msg.reasoning_content = None
    choice = _Obj()
    choice.message = msg
    choice.finish_reason = finish_reason
    usage = _Obj()
    usage.prompt_tokens = 1
    usage.completion_tokens = 1
    resp = _Obj()
    resp.choices = [choice]
    resp.usage = usage
    return resp


class _FakeClient:
    """Mimics the bits of the OpenAI client `_call_json_llm` touches:
    `client.chat.completions.create(...)` returning queued responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, **_kw):
        r = self._responses[self.calls]
        self.calls += 1
        return r


@pytest.fixture
def patch_openai(monkeypatch):
    def _make(responses):
        fc = _FakeClient(responses)
        monkeypatch.setattr(pipeline, "OpenAI", lambda **_kw: fc)
        return fc

    return _make


# ---------------------------------------------------------------------------
# Helpers for building minimal CorrectedGeometry dicts used in validator tests
# ---------------------------------------------------------------------------

def _geom(
    *,
    floors=None,
    windows=None,
) -> dict:
    """Minimal valid CorrectedGeometry dict; callers may override floors/windows."""
    if floors is None:
        floors = [
            {
                "name": "F1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "cells": [{"id": "R1", "role": "office", "x": [0, 10], "y": [0, 8]}],
            }
        ]
    if windows is None:
        windows = []
    return {"footprint_x": [0, 10], "footprint_y": [0, 8], "floors": floors, "windows": windows}


def _window(facade="South", room="R1", floor="F1") -> dict:
    return {"id": "W1", "floor": floor, "facade": facade, "span": [1, 3], "z": [0.5, 2.5], "room": room}


# ---------------------------------------------------------------------------
# Existing _call_json_llm retry tests (unchanged behaviour)
# ---------------------------------------------------------------------------

def test_retry_recovers_from_bad_json(patch_openai):
    fc = patch_openai([_resp("{bad json"), _resp('{"ok": 1}')])
    out = pipeline._call_json_llm(SECTION, "s", "h", out_dir=None, prefix="t", attempts=3)
    assert out == {"ok": 1}
    assert fc.calls == 2  # stopped as soon as a draw parsed


def test_retry_exhausted_raises(patch_openai):
    fc = patch_openai([_resp("{bad"), _resp("{bad"), _resp("{bad")])
    with pytest.raises(RuntimeError, match="after 3 attempt"):
        pipeline._call_json_llm(SECTION, "s", "h", out_dir=None, prefix="t", attempts=3)
    assert fc.calls == 3


def test_validate_failure_triggers_retry(patch_openai):
    fc = patch_openai([_resp('{"windows": []}'), _resp('{"windows": [1]}')])

    def _v(parsed):
        if not parsed.get("windows"):
            raise ValueError("no windows")

    out = pipeline._call_json_llm(
        SECTION, "s", "h", out_dir=None, prefix="t", attempts=2, validate=_v
    )
    assert out == {"windows": [1]}
    assert fc.calls == 2


def test_default_is_single_attempt(patch_openai):
    fc = patch_openai([_resp("{bad")])
    with pytest.raises(RuntimeError):
        pipeline._call_json_llm(SECTION, "s", "h", out_dir=None, prefix="t")
    assert fc.calls == 1


def test_valid_first_draw_no_retry(patch_openai):
    fc = patch_openai([_resp('{"ok": 1}'), _resp('{"never": "used"}')])
    out = pipeline._call_json_llm(SECTION, "s", "h", out_dir=None, prefix="t", attempts=3)
    assert out == {"ok": 1}
    assert fc.calls == 1


# ---------------------------------------------------------------------------
# L2 — transport exception is consumed as an attempt and triggers retry
# ---------------------------------------------------------------------------

def test_transport_error_consumed_as_attempt(patch_openai):
    """A network / transport exception on attempt 1 counts as a retry candidate,
    not an unconditional abort; the second draw (good JSON) is returned."""

    class _ErrorThenOk:
        """Returns an exception on the first call, a good response on the second."""

        def __init__(self):
            self.calls = 0
            self.chat = self
            self.completions = self

        def create(self, **_kw):
            self.calls += 1
            if self.calls == 1:
                raise ConnectionError("simulated 5xx / timeout")
            return _resp('{"ok": 1}')

    import src.agent.pipeline as pl_mod
    from unittest.mock import patch as _patch

    client = _ErrorThenOk()
    with _patch.object(pl_mod, "OpenAI", return_value=client):
        out = pipeline._call_json_llm(
            SECTION, "s", "h", out_dir=None, prefix="t", attempts=3
        )
    assert out == {"ok": 1}
    assert client.calls == 2


def test_transport_error_exhausts_all_attempts(patch_openai):
    """If every attempt raises a transport exception the final RuntimeError is raised."""

    class _AlwaysError:
        def __init__(self):
            self.calls = 0
            self.chat = self
            self.completions = self

        def create(self, **_kw):
            self.calls += 1
            raise ConnectionError("always broken")

    import src.agent.pipeline as pl_mod
    from unittest.mock import patch as _patch

    client = _AlwaysError()
    with _patch.object(pl_mod, "OpenAI", return_value=client):
        with pytest.raises(RuntimeError, match="after 2 attempt"):
            pipeline._call_json_llm(
                SECTION, "s", "h", out_dir=None, prefix="t", attempts=2
            )
    assert client.calls == 2


# ---------------------------------------------------------------------------
# _reading_window_stroke_count (unchanged)
# ---------------------------------------------------------------------------

def test_reading_window_stroke_count(tmp_path):
    (tmp_path / "a.json").write_text(
        json.dumps({"strokes": [{"pen": "window"}, {"pen": "wall"}, {"pen": "window"}]})
    )
    (tmp_path / "b.json").write_text(json.dumps({"strokes": [{"pen": "window"}]}))
    (tmp_path / "c.json").write_text("{ not json")  # tolerated, skipped
    assert pipeline._reading_window_stroke_count(tmp_path) == 3


# ---------------------------------------------------------------------------
# _make_correction_validator — updated tests for the composite validator
# ---------------------------------------------------------------------------

def test_correction_validator_rejects_zero_windows_when_reading_has_windows():
    """Window completeness check: 0 windows emitted when reading saw windows."""
    v = pipeline._make_correction_validator(5)
    with pytest.raises(ValueError, match="0 windows"):
        v(_geom(windows=[]))
    # missing 'windows' key: pydantic default is []
    with pytest.raises(ValueError, match="0 windows"):
        v({**_geom(), "windows": []})
    # non-empty windows list is fine
    v(_geom(windows=[_window()]))


def test_correction_validator_allows_zero_windows_when_reading_has_none():
    """A genuinely windowless building must not be rejected."""
    v = pipeline._make_correction_validator(0)
    v(_geom(windows=[]))  # must not raise


def test_correction_validator_rejects_duplicate_cell_id_triggers_retry(patch_openai):
    """Duplicate cell id across floors: bad draw rejected, clean draw accepted."""
    # Build a good draw (unique ids) and a bad draw (duplicate id)
    bad = _geom(
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
             "cells": [{"id": "Corridor", "role": "office", "x": [0, 5], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.0, "ceiling_height": 3.0,
             "cells": [{"id": "Corridor", "role": "office", "x": [0, 5], "y": [0, 8]}]},
        ]
    )
    good = _geom(
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
             "cells": [{"id": "F1_Corridor", "role": "office", "x": [0, 5], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.0, "ceiling_height": 3.0,
             "cells": [{"id": "F2_Corridor", "role": "office", "x": [0, 5], "y": [0, 8]}]},
        ]
    )

    v = pipeline._make_correction_validator(0)
    with pytest.raises(ValueError, match="duplicate cell id"):
        v(bad)
    # good draw passes
    v(good)


def test_correction_validator_rejects_large_z_gap(patch_openai):
    """z-stack gap > gap_close_threshold_m is rejected (forces a retry)."""
    # 0.5 m gap (F1 top=3.0, F2 z_floor=3.5) — above the 0.3 m threshold
    bad = _geom(
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
             "cells": [{"id": "R1", "role": "office", "x": [0, 10], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.5, "ceiling_height": 3.0,
             "cells": [{"id": "R2", "role": "office", "x": [0, 10], "y": [0, 8]}]},
        ]
    )
    v = pipeline._make_correction_validator(0)
    with pytest.raises(ValueError, match="z-stack discontinuity"):
        v(bad)


def test_correction_validator_accepts_small_z_gap():
    """z-stack gap ≤ gap_close_threshold_m (0.3 m) is auto-closed by the core
    and must NOT be rejected by the validator."""
    # 0.2 m gap — below the threshold, core will auto-snap
    ok = _geom(
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
             "cells": [{"id": "R1", "role": "office", "x": [0, 10], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.2, "ceiling_height": 3.0,
             "cells": [{"id": "R2", "role": "office", "x": [0, 10], "y": [0, 8]}]},
        ]
    )
    v = pipeline._make_correction_validator(0)
    v(ok)  # must not raise


def test_correction_validator_rejects_illegal_facade():
    """facade='Northeast' (not in N/S/E/W) triggers pydantic ValidationError
    via model_validate inside the validator."""
    bad = _geom(windows=[_window(facade="Northeast")])
    v = pipeline._make_correction_validator(0)
    # ValidationError (from pydantic) should propagate — _call_json_llm
    # catches any Exception and retries.
    with pytest.raises(Exception, match="Northeast|facade"):
        v(bad)


# ---------------------------------------------------------------------------
# L1 — _section() does NOT silently fall back on config-broken sections
# ---------------------------------------------------------------------------

def test_section_fallback_when_absent(monkeypatch, tmp_path):
    """When intake_mep is absent from llm.yaml, _section('mep') falls back to
    intake_correction without raising."""
    cfg = tmp_path / "llm.yaml"
    cfg.write_text(
        "intake_correction:\n  model_name: test-model\n  api_key: x\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EP_AGENT_LLM_CONFIG", str(cfg))
    # Force reload of lru_cached OmegaConf if needed
    import importlib
    import src.agent.llm as llm_mod
    importlib.reload(llm_mod)
    # Patch pipeline's imported references to the reloaded module
    monkeypatch.setattr(pipeline, "load_llm_section", llm_mod.load_llm_section)
    monkeypatch.setattr(pipeline, "resolve_llm_config_path", llm_mod.resolve_llm_config_path)

    result = pipeline._section("mep")
    assert result["model_name"] == "test-model"


def test_section_propagates_broken_config_error(monkeypatch, tmp_path):
    """When intake_mep IS present but has a broken env-var interpolation,
    _section('mep') must raise — not silently fall back to intake_correction."""
    cfg = tmp_path / "llm.yaml"
    cfg.write_text(
        "intake_mep:\n  model_name: test-model\n  api_key: ${oc.env:NONEXISTENT_KEY_XYZ}\n"
        "intake_correction:\n  model_name: fallback\n  api_key: y\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EP_AGENT_LLM_CONFIG", str(cfg))
    import importlib
    import src.agent.llm as llm_mod
    importlib.reload(llm_mod)
    monkeypatch.setattr(pipeline, "load_llm_section", llm_mod.load_llm_section)
    monkeypatch.setattr(pipeline, "resolve_llm_config_path", llm_mod.resolve_llm_config_path)

    with pytest.raises(Exception):
        pipeline._section("mep")
