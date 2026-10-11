"""Current single-runtime timeout and request parity contract."""

import asyncio

def test_single_runtime_keeps_unbounded_per_request_timeout_and_request_bytes(tmp_path):
    from test_agent_runtime import MESSAGES, response, runtime

    engines = []
    for name in ("implicit", "explicit"):
        engine = runtime(tmp_path / name, [response(text="done")])
        if name == "explicit":
            engine.request_timeout_seconds = None
        assert engine.request_timeout_seconds is None
        with engine.store:
            assert asyncio.run(engine.run(MESSAGES))["status"] == "completed"
        engines.append(engine)
    assert engines[0].adapter.requests == engines[1].adapter.requests
