from __future__ import annotations

import json
from types import SimpleNamespace

import scripts.run_full_pipeline as rfp


class _FakeAgentState:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _case(tmp_path):
    case_dir = tmp_path / "case"
    case_data = case_dir / "case_data"
    case_data.mkdir(parents=True)
    (case_data / "testdata_prompt.json").write_text(
        json.dumps({"Building name": "B", "Floor plans": []}),
        encoding="utf-8",
    )
    epw = tmp_path / "weather.epw"
    epw.write_text("epw", encoding="utf-8")
    return case_dir, epw


def test_run_full_pipeline_reading_from_preserves_ep_layout(monkeypatch, tmp_path):
    case_dir, epw = _case(tmp_path)
    (case_dir / "0_reading").mkdir()
    seen = {}
    monkeypatch.setattr(rfp, "setup_logger", lambda **_kwargs: None)
    monkeypatch.setattr(rfp, "AgentState", _FakeAgentState)
    monkeypatch.setattr(
        rfp,
        "run_downstream_ep",
        lambda **kwargs: seen.update(kwargs) or {},
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_full_pipeline.py",
            "case",
            "--base-dir",
            str(tmp_path),
            "--reading-from",
            "0_reading",
            "--epw",
            str(epw),
        ],
    )

    rfp.main()

    assert seen["output_dir"] == case_dir / "EP"
    assert seen["ep_run_subdir"] == "EP_run"
    assert seen["run_simulate"] is True
    assert seen["thread_id"] == "case"
    assert seen["initial_state"].reading_vector_dir == str(case_dir / "0_reading")
    assert seen["initial_state"].pipeline_out_dir == str(case_dir)


def test_run_full_pipeline_intake_from_preserves_flat_no_simulate_layout(
    monkeypatch, tmp_path
):
    case_dir, epw = _case(tmp_path)
    intake = case_dir / "output" / "intake_output.json"
    intake.parent.mkdir()
    intake.write_text("{}", encoding="utf-8")
    fake_intake = SimpleNamespace(building=SimpleNamespace(name="B"))
    seen = {}
    monkeypatch.setattr(rfp, "setup_logger", lambda **_kwargs: None)
    monkeypatch.setattr(rfp, "AgentState", _FakeAgentState)
    monkeypatch.setattr(rfp, "load_intake_from", lambda path: fake_intake)
    monkeypatch.setattr(
        rfp,
        "run_downstream_ep",
        lambda **kwargs: seen.update(kwargs) or {},
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_full_pipeline.py",
            "case",
            "--base-dir",
            str(tmp_path),
            "--intake-from",
            "output/intake_output.json",
            "--no-simulate",
            "--epw",
            str(epw),
        ],
    )

    rfp.main()

    assert seen["output_dir"] == case_dir / "output"
    assert seen["ep_run_subdir"] is None
    assert seen["run_simulate"] is False
    assert seen["initial_state"].intake_output is fake_intake
    assert seen["initial_state"].pipeline_out_dir is None
