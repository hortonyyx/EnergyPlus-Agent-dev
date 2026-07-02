from __future__ import annotations

from pathlib import Path

from src.agent.runner import run_downstream_ep
from src.agent.state import AgentState


def test_run_downstream_ep_wires_context_and_thread_id(monkeypatch, tmp_path):
    import src.agent.graph as graph_mod
    import src.agent.runner as runner_mod

    fake_graph = object()
    monkeypatch.setattr(graph_mod, "build_graph", lambda: fake_graph)
    seen = {}

    def fake_run_session(graph, initial, context, config, on_interrupt, on_event=None):
        seen["graph"] = graph
        seen["initial"] = initial
        seen["context"] = context
        seen["config"] = config
        seen["on_event"] = on_event
        return {"done": True}

    monkeypatch.setattr(runner_mod, "run_session", fake_run_session)
    initial = AgentState(user_input="x")
    on_event = lambda _node, _update: None

    out = run_downstream_ep(
        initial_state=initial,
        epw=Path("weather.epw"),
        output_dir=tmp_path / "EP",
        ep_run_subdir="EP_run",
        run_simulate=True,
        thread_id="case/run",
        on_event=on_event,
    )

    assert out == {"done": True}
    assert seen["graph"] is fake_graph
    assert seen["initial"] is initial
    assert seen["context"].output_dir == tmp_path / "EP"
    assert seen["context"].ep_run_subdir == "EP_run"
    assert seen["context"].run_simulate is True
    assert seen["config"] == {"configurable": {"thread_id": "case/run"}}
    assert seen["on_event"] is on_event
