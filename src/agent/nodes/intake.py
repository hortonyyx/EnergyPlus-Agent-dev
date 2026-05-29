from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from loguru import logger

from src.agent._share import language_directive
from src.agent.llm import create_llm
from src.agent.state import AgentState, AgentStateUpdate, IntakeOutput


class TextContentPart(TypedDict):
    """LangChain multimodal text content part."""

    type: Literal["text"]
    text: str


class ImageContentPart(TypedDict):
    """LangChain multimodal image content part (base64-encoded)."""

    type: Literal["image"]
    source_type: Literal["base64"]
    mime_type: str
    data: str


ContentPart = TextContentPart | ImageContentPart

INTAKE_RULES_DIR = Path(__file__).resolve().parents[3] / "skills" / "energyplus_mcp"

INTAKE_SYSTEM_PROMPT = """You are an EnergyPlus building-simulation intake specialist.
Given a building description (text and optional architectural drawings —
floorplan, elevation, section, axonometric, perspective, etc.), extract
structured specifications for every subsystem.

Each attached image is preceded by a `[Next image] <label>` line that names
its role (e.g. `Floor 1 plan view`, `South facade elevation`,
`Supplementary plan / section / axonometric`, or — for legacy single-plan
inputs — `Top view (shared plan for every floor …)`). Trust those labels
to assign each image to the correct floor or facade; do NOT re-infer the
role from picture content.

You MUST invoke the IntakeOutput tool to return the structured JSON.
Do NOT respond with a text/JSON message — always use the tool call.

The full intake rule library is appended below this preamble. Treat every
appended markdown document as mandatory instructions. They jointly define:
- how to read the drawings
- how to preserve geometry and topology
- how to write every `*_specs` field
- which cases must fail fast instead of being silently normalized

Return exactly one structured `IntakeOutput` object with these fields:
- `building`
- `site_location`
- `zone_specs`
- `material_specs`
- `schedule_specs`
- `construction_specs`
- `surface_specs`
- `fenestration_specs`
- `hvac_specs`
- `people_specs`
- `lights_specs`
"""


def _load_intake_rule_library() -> str:
    docs = sorted(INTAKE_RULES_DIR.glob("*.md"))
    if not docs:
        raise RuntimeError(f"No intake rule documents found in {INTAKE_RULES_DIR}")

    rendered_docs = []
    for path in docs:
        rendered_docs.append(
            f"\n\n===== BEGIN RULE DOCUMENT: {path.name} =====\n"
            f"{path.read_text(encoding='utf-8').strip()}\n"
            f"===== END RULE DOCUMENT: {path.name} ====="
        )

    return "".join(rendered_docs)


_IMAGE_SUFFIX_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _load_image_part(path: str) -> ImageContentPart:
    """Load an image file and return a multimodal content part."""
    p = Path(path)
    mime = _IMAGE_SUFFIX_TO_MIME.get(p.suffix.lower(), "image/png")
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return ImageContentPart(
        type="image",
        source_type="base64",
        mime_type=mime,
        data=data,
    )


def _label_for_image(path: str) -> str:
    """Derive a one-line semantic label for an architectural drawing.

    Recognised patterns (case-insensitive, applied to the filename stem):
      - `<k>f_view`         → "Floor <k> plan view"
      - `top_view`          → "Top view (shared plan for every floor)"
      - `<dir>_view` where  → "<Dir> facade elevation"
        dir ∈ {south, north, east, west}
      - `supp_plan`         → "Supplementary plan / section"
      - anything else       → "Architectural drawing: <stem>"
    """
    stem = Path(path).stem.lower()
    floor_match = re.fullmatch(r"(\d+)f_view", stem)
    if floor_match:
        return f"Floor {int(floor_match.group(1))} plan view"
    if stem == "top_view":
        return "Top view (shared plan for every floor — legacy single-plan input)"
    facade_match = re.fullmatch(r"(south|north|east|west)_view", stem)
    if facade_match:
        return f"{facade_match.group(1).capitalize()} facade elevation"
    if stem == "supp_plan":
        return "Supplementary plan / section / axonometric"
    return f"Architectural drawing: {Path(path).name}"


def _seed_config(state: AgentState, intake: IntakeOutput) -> AgentStateUpdate:
    """Write building + site_location into config_state and return the update."""
    config = state.config_state.model_copy(deep=True)
    config.building = intake.building
    config.site_location = intake.site_location
    return AgentStateUpdate(
        intake_output=intake, config_state=config, validation_errors=[]
    )


def intake_node(state: AgentState) -> AgentStateUpdate:
    """Produce IntakeOutput and seed config_state. Three dispatch modes:

    1. **Short-circuit** — `state.intake_output` already populated (the
       `--intake-from` flow): skip everything, just seed config_state.
    2. **Two-step phase 2** — `state.phase1_vector_dir` set (the half-manual
       two-step flow: `--phase1-from`): run phase 2 (vector JSON -> IntakeOutput)
       via `src.agent.phase2.run_phase2`, image-blind. This is the dev default.
    3. **Legacy single-step** — neither of the above: one multimodal
       image -> IntakeOutput call (needs an Anthropic-capable `intake` section).

    The downstream contract is identical in all three modes — the graph always
    receives one validated `IntakeOutput`.
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

    if state.phase1_vector_dir:
        # Two-step: phase 1 (perception) already produced vector JSON; run
        # phase 2 (topology) here. Stay in two-step even when validation_errors
        # are present (a validate->intake repair): falling through to the legacy
        # single-step branch would switch model family + modality and destroy
        # the error-budget separation. Feed the errors in as repair context.
        # Imported lazily so the legacy path / tests that never touch phase 2
        # don't pull in the OpenAI client.
        from src.agent.phase2 import run_phase2

        vector_dir = Path(state.phase1_vector_dir)
        testdata_text = state.testdata_text or state.user_input
        feedback = "\n".join(f"- {e}" for e in state.validation_errors) or None
        out_dir = Path(state.phase2_debug_dir) if state.phase2_debug_dir else None
        logger.info(
            "intake_node: two-step phase 2 from {} (repair={})",
            vector_dir,
            bool(feedback),
        )
        intake = run_phase2(
            vector_dir, testdata_text, out_dir=out_dir, feedback=feedback
        )
        logger.info(
            "intake_node: phase 2 done; building={} site={}",
            intake.building.name,
            intake.site_location.name,
        )
        return _seed_config(state, intake)

    llm = create_llm(node_name="intake").with_structured_output(
        IntakeOutput, include_raw=True
    )

    text = state.user_input
    if state.validation_errors:
        errors = "\n".join(f"- {e}" for e in state.validation_errors)
        text += (
            f"\n\nThe previous attempt had these errors. Please address them:\n{errors}"
        )

    content_parts: list[ContentPart] = [TextContentPart(type="text", text=text)]
    for path in state.image_paths:
        label = _label_for_image(path)
        content_parts.append(
            TextContentPart(type="text", text=f"[Next image] {label}")
        )
        content_parts.append(_load_image_part(path))

    result = cast(
        dict[str, Any],
        llm.invoke(
            [
                SystemMessage(
                    content=INTAKE_SYSTEM_PROMPT
                    + _load_intake_rule_library()
                    + language_directive()
                ),
                HumanMessage(content=cast("list[str | dict[str, Any]]", content_parts)),
            ]
        ),
    )

    parsed: IntakeOutput | None = result.get("parsed")
    if parsed is None:
        raw: BaseMessage | None = result.get("raw")
        parsing_error = result.get("parsing_error")
        raw_preview = repr(raw.content if raw is not None else raw)[:500]
        logger.error(
            "intake_node: structured output parse failed. "
            "parsing_error={} raw preview={}",
            parsing_error,
            raw_preview,
        )
        raise RuntimeError(
            "IntakeOutput parsing returned None. The LLM likely replied with "
            "text instead of a tool call — common on retry turns. "
            f"parsing_error={parsing_error!r}; raw preview: {raw_preview}"
        )

    config = state.config_state.model_copy(deep=True)
    config.building = parsed.building
    config.site_location = parsed.site_location

    return AgentStateUpdate(
        intake_output=parsed,
        config_state=config,
        validation_errors=[],
    )
