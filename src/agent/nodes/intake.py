from __future__ import annotations

from pathlib import Path

from loguru import logger

from src.agent.state import AgentState, AgentStateUpdate, IntakeOutput


def _seed_config(state: AgentState, intake: IntakeOutput) -> AgentStateUpdate:
    """Write building + site_location into config_state and return the update."""
    config = state.config_state.model_copy(deep=True)
    config.building = intake.building
    config.site_location = intake.site_location
    return AgentStateUpdate(
        intake_output=intake, config_state=config, validation_errors=[]
    )


def intake_node(state: AgentState) -> AgentStateUpdate:
    """Produce IntakeOutput and seed config_state. Two dispatch modes:

    1. **Short-circuit** — `state.intake_output` already populated (the
       `--intake-from` flow): skip everything, just seed config_state.
    2. **Pipeline** — `state.reading_vector_dir` set (the half-manual flow:
       `--reading-from`): run the staged intake pipeline (vector JSON ->
       IntakeOutput) via `src.agent.pipeline.run_pipeline`, image-blind. This is
       the mainline.

    The legacy single-step (one multimodal image -> IntakeOutput) path is retired
    (its skill library `skills/energyplus_mcp/` was archived to Skill_history on
    2026-06-10); the staged pipeline is the only supported flow.
    """
    if state.intake_output is not None and not state.validation_errors:
        config = state.config_state.model_copy(deep=True)
        config.building = state.intake_output.building
        config.site_location = state.intake_output.site_location
        logger.info(
            "intake_node: short-circuit (pre-populated IntakeOutput); "
            "building={} site={}",
            state.intake_output.building.name,
            state.intake_output.site_location.name,
        )
        return AgentStateUpdate(config_state=config, validation_errors=[])

    if state.reading_vector_dir:
        # The reading stage already produced vector JSON; run the staged pipeline
        # (1_correction -> deterministic geometry -> 4_mep -> 5_intakeoutput) here.
        # Stay in the pipeline even with validation_errors present (a
        # validate->intake repair): feed the errors in as repair context.
        # Imported lazily so callers/tests that never touch the pipeline don't
        # pull in the OpenAI client.
        from src.agent.pipeline import run_pipeline

        vector_dir = Path(state.reading_vector_dir)
        testdata_text = state.testdata_text or state.user_input
        feedback = "\n".join(f"- {e}" for e in state.validation_errors) or None
        out_dir = Path(state.pipeline_out_dir) if state.pipeline_out_dir else None
        logger.info(
            "intake_node: pipeline from {} (repair={})",
            vector_dir,
            bool(feedback),
        )
        intake = run_pipeline(
            vector_dir, testdata_text, out_dir=out_dir, feedback=feedback
        )
        logger.info(
            "intake_node: pipeline done; building={} site={}",
            intake.building.name,
            intake.site_location.name,
        )
        return _seed_config(state, intake)

    raise RuntimeError(
        "intake_node: no input. The legacy single-step image->IntakeOutput path "
        "is retired. Provide either a pre-built IntakeOutput (--intake-from) or a "
        "reading-stage vector directory (--reading-from) for the staged pipeline."
    )
