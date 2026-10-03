import asyncio
import json
from types import SimpleNamespace

import pytest

from src.agent_runtime.call_quota import QuotaAdapter


def _request(model="test-model"):
    return SimpleNamespace(body={"model": model})


class _RecordingAdapter:
    def __init__(self, result=None):
        self.result = result or {
            "model": "test-model",
            "usage": {"total_tokens": 12},
        }
        self.calls = []

    async def send(self, prepared, *, timeout):
        self.calls.append((prepared, timeout))
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _send(adapter):
    return asyncio.run(adapter.send(_request(), timeout=3.0))


def _rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_persistent_cap_does_not_reset_when_adapter_is_recreated(tmp_path):
    journal = tmp_path / "request_quota.jsonl"
    first_client = _RecordingAdapter()
    first = QuotaAdapter(first_client, journal, limit=1, category="role_tests")

    assert _send(first)["usage"]["total_tokens"] == 12

    restarted_client = _RecordingAdapter()
    restarted = QuotaAdapter(restarted_client, journal, limit=1, category="role_tests")
    with pytest.raises(ValueError, match="quota exhausted"):
        _send(restarted)

    assert len(first_client.calls) == 1
    assert restarted_client.calls == []
    assert [row["event"] for row in _rows(journal)] == ["attempt", "response"]
    assert _rows(journal)[0]["ticket"] == 1


def test_failed_request_still_consumes_its_ticket(tmp_path):
    journal = tmp_path / "request_quota.jsonl"
    failed_client = _RecordingAdapter(RuntimeError("provider unavailable"))
    quota = QuotaAdapter(failed_client, journal, limit=1, category="role_tests")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        _send(quota)

    next_client = _RecordingAdapter()
    restarted = QuotaAdapter(next_client, journal, limit=1, category="role_tests")
    with pytest.raises(ValueError, match="quota exhausted"):
        _send(restarted)

    assert len(failed_client.calls) == 1
    assert next_client.calls == []
    rows = _rows(journal)
    assert [row["event"] for row in rows] == ["attempt", "failure"]
    assert rows[0]["ticket"] == rows[1]["ticket"] == 1
    assert rows[1]["error_type"] == "RuntimeError"


def test_torn_quota_journal_rejects_before_calling_adapter(tmp_path):
    journal = tmp_path / "request_quota.jsonl"
    journal.write_bytes(b'{"event":"attempt","ticket":1')
    client = _RecordingAdapter()
    quota = QuotaAdapter(client, journal, limit=2, category="role_tests")

    with pytest.raises(ValueError, match="torn tail"):
        _send(quota)

    assert client.calls == []
    assert journal.read_bytes() == b'{"event":"attempt","ticket":1'


def test_changed_limit_rejects_before_calling_restarted_adapter(tmp_path):
    journal = tmp_path / "request_quota.jsonl"
    initial_client = _RecordingAdapter()
    initial = QuotaAdapter(initial_client, journal, limit=2, category="role_tests")
    _send(initial)

    changed_client = _RecordingAdapter()
    changed = QuotaAdapter(changed_client, journal, limit=3, category="role_tests")
    with pytest.raises(ValueError, match="identity/limit cannot change"):
        _send(changed)

    assert len(initial_client.calls) == 1
    assert changed_client.calls == []
    assert {row["limit"] for row in _rows(journal)} == {2}
