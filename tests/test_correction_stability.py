"""Unit tests for 1_correction stability hardening in src.agent.pipeline:
JSON-parse / semantic retry in `_call_json_llm`, plus the window-completeness
validator that catches the sm21 0-window class. OpenAI is mocked — no network."""

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


def test_reading_window_stroke_count(tmp_path):
    (tmp_path / "a.json").write_text(
        json.dumps({"strokes": [{"pen": "window"}, {"pen": "wall"}, {"pen": "window"}]})
    )
    (tmp_path / "b.json").write_text(json.dumps({"strokes": [{"pen": "window"}]}))
    (tmp_path / "c.json").write_text("{ not json")  # tolerated, skipped
    assert pipeline._reading_window_stroke_count(tmp_path) == 3


def test_window_validator_rejects_zero_when_reading_has_windows():
    v = pipeline._make_window_completeness_validator(5)
    with pytest.raises(ValueError, match="0 windows"):
        v({"windows": []})
    with pytest.raises(ValueError):
        v({})  # missing key == zero
    v({"windows": [{"id": "w"}]})  # non-empty is fine


def test_window_validator_allows_zero_when_reading_has_none():
    v = pipeline._make_window_completeness_validator(0)
    v({"windows": []})  # a genuinely windowless building must not be rejected
