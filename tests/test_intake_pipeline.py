"""intake_node pipeline dispatch wiring (no network / no LLM).

Monkeypatches `src.agent.pipeline.run_pipeline` to capture how `intake_node` calls
it, asserting the fixes from the 2026-05-29 intake-switch review:
  - the pipeline receives the RAW `testdata_text`, not the human-readable `user_input`
    summary (finding #1);
  - a pipeline run stays in the pipeline under `validation_errors` and forwards them as
    `feedback`, instead of falling through to the legacy single-step branch
    (finding #3);
  - pipeline artifacts go to `pipeline_out_dir` (finding #4).
"""

from __future__ import annotations

import json
from pathlib import Path

import src.agent.pipeline as pipeline_mod
from src.agent._share import ensure_schema_initialized
from src.agent.nodes.intake import intake_node
from src.agent.state import AgentState, IntakeOutput

ensure_schema_initialized()

_ANCHOR = Path(
    "test_data/SmallOffice/smalloffice_20/output_new/intake_output.json"
)


def _load_anchor_intake() -> IntakeOutput:
    return IntakeOutput.model_validate(json.loads(_ANCHOR.read_text(encoding="utf-8")))


def test_two_step_passes_raw_testdata_and_feedback(monkeypatch):
    captured = {}

    def fake_run_pipeline(vector_dir, testdata_text, *, out_dir=None, feedback=None):
        captured.update(
            vector_dir=vector_dir,
            testdata_text=testdata_text,
            out_dir=out_dir,
            feedback=feedback,
        )
        return _load_anchor_intake()

    monkeypatch.setattr(pipeline_mod, "run_pipeline", fake_run_pipeline)

    state = AgentState(
        user_input="HUMAN SUMMARY (must NOT reach the pipeline)",
        testdata_text='{"TestName": "raw_json_here"}',
        reading_vector_dir="/some/0_reading",
        pipeline_out_dir="/some/output/pipeline_out",
        validation_errors=["zone F2_X missing", "window crosses zone"],
    )
    update = intake_node(state)

    # raw testdata, not the user_input summary (finding #1)
    assert captured["testdata_text"] == '{"TestName": "raw_json_here"}'
    # stayed in the pipeline despite validation_errors, forwarding them (finding #3)
    assert captured["feedback"] is not None
    assert "zone F2_X missing" in captured["feedback"]
    # debug artifacts dir honored (finding #4)
    assert captured["out_dir"] == Path("/some/output/pipeline_out")
    # produced a valid IntakeOutput into the update
    assert update["intake_output"] is not None


def test_two_step_no_feedback_when_clean(monkeypatch):
    captured = {}

    def fake_run_pipeline(vector_dir, testdata_text, *, out_dir=None, feedback=None):
        captured["feedback"] = feedback
        return _load_anchor_intake()

    monkeypatch.setattr(pipeline_mod, "run_pipeline", fake_run_pipeline)

    state = AgentState(
        testdata_text="{}",
        reading_vector_dir="/some/0_reading",
    )
    intake_node(state)
    assert captured["feedback"] is None


def test_prefilled_intake_output_short_circuits(monkeypatch):
    # If intake_output is already present and no errors, the pipeline must not run.
    def boom(*a, **k):  # pragma: no cover - must not be called
        raise AssertionError("run_pipeline should not be called on short-circuit")

    monkeypatch.setattr(pipeline_mod, "run_pipeline", boom)
    state = AgentState(
        intake_output=_load_anchor_intake(),
        reading_vector_dir="/some/0_reading",  # present, but short-circuit wins
    )
    update = intake_node(state)
    assert update["config_state"].building.name
