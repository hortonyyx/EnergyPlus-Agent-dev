"""Phase 2 of the two-step intake: vector JSON -> IntakeOutput.

Phase 1 (image -> semantic vector JSON) is image-bound perception; phase 2 is
image-blind topology/reasoning (zones, surfaces, fenestration). Holding the two
apart is what keeps the error budget separable (perception errors attributable
to phase 1, reasoning errors to phase 2).

This module is the single implementation of phase 2. It is called from:
  - `intake_node` (the main graph, two-step flow), and
  - `Tool_scripts/run_phase2_deepseek.py` (thin standalone CLI wrapper).

Why a raw OpenAI client instead of `create_llm()` / langchain:
  - phase 2 is single-shot (not multi-turn ReAct), and we WANT DeepSeek thinking
    on for the heavy spatial reasoning.
  - langchain_openai's `with_structured_output(method="function_calling")` burns
    all output tokens on reasoning_content when thinking is on and never emits the
    tool call. So we ask for JSON-only content and parse it ourselves.
The model/endpoint/thinking config still comes from the single `llm.yaml` entry
point (the `intake_phase2` section), honoring "model switching has one home".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from loguru import logger
from openai import OpenAI

from src.agent._share import ensure_schema_initialized
from src.agent.llm import load_llm_section
from src.agent.state import IntakeOutput

_SKILL_DIR = (
    Path(__file__).resolve().parents[2] / "skills" / "energyplus_mcp_twostep"
)

# Plan-view filenames look like "<N>f_view.json"; elevations are
# "<Name>_view.json". The capture group is the floor number so plans sort
# numerically (10f after 2f, not before).
_PLAN_RE = re.compile(r"^(\d+)f_view\.json$", flags=re.IGNORECASE)

_JS_CONCAT_RE = re.compile(r'"\s*\+\s*\n\s*"', flags=re.MULTILINE)


def discover_phase1_files(vector_dir: Path) -> list[str]:
    """Scan a phase-1 vector dir for ALL vector JSONs, in a stable order.

    Order: numeric floor plans (by floor number) -> facade elevations ->
    supplementary / section / other vector JSONs. Everything is included (not
    just *_view.json) because phase2/rules.md requires consuming supplements and
    sections too. `phase1_summary.md` is `.md` (not matched) and read separately.
    """
    names = sorted(p.name for p in vector_dir.glob("*.json"))
    if not names:
        raise FileNotFoundError(f"no *.json found under {vector_dir}")
    plans = sorted(
        (n for n in names if _PLAN_RE.match(n)),
        key=lambda n: (int(_PLAN_RE.match(n).group(1)), n),
    )
    elevations = [
        n for n in names if not _PLAN_RE.match(n) and n.lower().endswith("_view.json")
    ]
    others = [
        n
        for n in names
        if not _PLAN_RE.match(n) and not n.lower().endswith("_view.json")
    ]
    return plans + elevations + others


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()


def _fix_js_concat(s: str) -> str:
    """Join DeepSeek's occasional JS-style cross-line string concatenation.

        "spec line 1\\n" +
            "spec line 2\\n"

    is invalid JSON but the intent is obvious — splice the adjacent literals.
    """
    prev = None
    while prev != s:
        prev = s
        s = _JS_CONCAT_RE.sub("", s)
    return s


def _extract_json(text: str) -> str:
    """Strip optional markdown fences / leading prose to get the JSON payload."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if m:
        text = m.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    return _fix_js_concat(text)


def build_phase2_messages(
    vector_dir: Path, testdata_text: str, *, feedback: str | None = None
) -> tuple[str, str]:
    """Return (system_prompt, human_message) for the phase-2 call.

    Rule docs come from the skill library (HEAD spec). phase 2 reads
    phase2/rules.md + phase1/guide.md + phase1/pen_library.md (NOT
    phase1/reading_guide.md — that is image-perception only and phase 2 never
    sees images). phase1_summary.md comes from the vector dir.
    """
    rules = _read(_SKILL_DIR / "phase2" / "rules.md")
    phase1_guide = _read(_SKILL_DIR / "phase1" / "guide.md")
    phase1_pens = _read(_SKILL_DIR / "phase1" / "pen_library.md")
    summary = _read(vector_dir / "phase1_summary.md")

    intake_schema = json.dumps(
        IntakeOutput.model_json_schema(), indent=2, ensure_ascii=False
    )

    system_prompt = (
        "You are an EnergyPlus intake specialist running phase 2 of a two-step "
        "intake pipeline. Phase 1 (image -> semantic vector JSON) is already "
        "done. You DO NOT see the original drawings. Your only inputs are the "
        "phase 1 JSONs + testdata metadata + the rule documents below.\n\n"
        "OUTPUT FORMAT (strict):\n"
        "  Return a single JSON object that validates against the IntakeOutput\n"
        "  Pydantic schema below. Your response content MUST be ONLY that JSON\n"
        "  object — no markdown fences, no prose, no leading/trailing text.\n"
        "  Start your output with `{` and end with `}`. Use spatial reasoning\n"
        "  internally (you have thinking budget) and emit the final JSON as\n"
        "  your visible answer.\n\n"
        "===== BEGIN IntakeOutput JSON SCHEMA =====\n"
        f"{intake_schema}\n"
        "===== END IntakeOutput JSON SCHEMA =====\n\n"
        "===== BEGIN RULE DOCUMENT: phase2/rules.md =====\n"
        f"{rules}\n"
        "===== END RULE DOCUMENT: phase2/rules.md =====\n\n"
        "===== BEGIN REFERENCE: phase1/guide.md (phase 1 output format) =====\n"
        f"{phase1_guide}\n"
        "===== END REFERENCE: phase1/guide.md =====\n\n"
        "===== BEGIN REFERENCE: phase1/pen_library.md (phase 1 pen enum) =====\n"
        f"{phase1_pens}\n"
        "===== END REFERENCE: phase1/pen_library.md =====\n\n"
        "===== BEGIN REFERENCE: phase1_summary.md (phase 1 results + facade formulas) =====\n"
        f"{summary}\n"
        "===== END REFERENCE: phase1_summary.md =====\n"
    )

    human_chunks: list[str] = [
        "Project metadata (testdata_prompt.json):\n```json\n" + testdata_text + "\n```\n"
    ]
    for fname in discover_phase1_files(vector_dir):
        jpath = vector_dir / fname
        human_chunks.append(f"\n[phase1 vector] {fname}:\n```json\n{_read(jpath)}\n```\n")
    if feedback:
        human_chunks.append(
            "\n\n=== Validation feedback from a previous attempt — fix these ===\n"
            f"{feedback}\n"
            "Address every item above while still following phase2/rules.md.\n"
        )
    human_chunks.append(
        "\nProduce the IntakeOutput JSON now. Follow phase2/rules.md Step 1->7 "
        "derivation order. Enumerate every zone / surface / split-pairing / "
        "fenestration explicitly — no templates, no Floor_N_* shorthand. "
        "Use the facade translation formulas in phase1_summary.md §3 verbatim. "
        "Remember: output ONLY the JSON object, nothing else."
    )
    return system_prompt, "".join(human_chunks)


def run_phase2(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
) -> IntakeOutput:
    """Run phase 2 and return a validated IntakeOutput.

    Args:
        vector_dir: directory holding phase-1 vector JSONs + phase1_summary.md.
        testdata_text: project metadata — pass the RAW `testdata_prompt.json`
            content (the prompt labels it as JSON; a human-readable summary
            loses structure the rules rely on).
        out_dir: if given, write raw_response.txt / thinking.txt /
            intake_output.json (or *_unvalidated.json + parse_error.txt on
            failure) here for inspection.
        feedback: optional validation feedback from a previous attempt, appended
            to the human message as repair context (two-step retry/repair).

    Raises:
        RuntimeError on empty content, JSON decode failure, or Pydantic
        validation failure (with artifacts saved to out_dir when provided).
    """
    # Self-contained: every caller (graph node, --intake-only, standalone CLI)
    # gets a usable IDD before IntakeOutput.model_json_schema()/model_validate(),
    # which read BaseSchema._idf_field. Idempotent (guarded in _share).
    ensure_schema_initialized()

    section = load_llm_section("intake_phase2")
    api_key = section.get("api_key")
    base_url = section.get("base_url")
    model_name = section["model_name"]
    max_tokens = section.get("max_tokens", 64000)
    temperature = section.get("temperature", 0.3)
    reasoning_effort = section.get("reasoning_effort")
    extra_body = section.get("extra_body") or {"thinking": {"type": "enabled"}}
    if not api_key:
        raise RuntimeError(
            "intake_phase2 has no api_key (set DEEPSEEK_API_KEY in .env)."
        )

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    system_prompt, human_message = build_phase2_messages(
        vector_dir, testdata_text, feedback=feedback
    )
    logger.info(
        "phase2: model={} vector_dir={} prompt sizes system={} human={} chars",
        model_name,
        vector_dir,
        len(system_prompt),
        len(human_message),
    )

    # reasoning_effort (DeepSeek thinking models: "high" default / "max"). Only
    # forward it when set — passing an explicit None serializes as `null` in the
    # request body, which is not the same as omitting the field.
    optional: dict = {}
    if reasoning_effort is not None:
        optional["reasoning_effort"] = reasoning_effort

    # Bound the call: DeepSeek thinking on a ~100k-char prompt legitimately takes
    # minutes, but a stalled connection must error rather than hang indefinitely.
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=600.0, max_retries=2)
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body=extra_body,
        **optional,
    )

    msg = resp.choices[0].message
    finish_reason = resp.choices[0].finish_reason
    content = msg.content or ""
    reasoning = getattr(msg, "reasoning_content", None)
    usage = resp.usage
    logger.info(
        "phase2: finish_reason={} usage={}",
        finish_reason,
        {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        },
    )
    if out_dir is not None:
        if reasoning:
            (out_dir / "thinking.txt").write_text(reasoning, encoding="utf-8")
        (out_dir / "raw_response.txt").write_text(content, encoding="utf-8")
    if finish_reason == "length":
        logger.warning("phase2: hit max_tokens — response likely truncated")
    if not content.strip():
        raise RuntimeError(f"phase2: empty content (finish_reason={finish_reason})")

    payload = _extract_json(content)
    try:
        parsed_dict = json.loads(payload)
    except json.JSONDecodeError as e:
        if out_dir is not None:
            (out_dir / "parse_error.txt").write_text(
                f"json decode: {e}\nfirst 500 chars:\n{payload[:500]}",
                encoding="utf-8",
            )
        raise RuntimeError(f"phase2: JSON decode error: {e}") from e

    try:
        parsed = IntakeOutput.model_validate(parsed_dict)
    except Exception as e:
        if out_dir is not None:
            (out_dir / "intake_output_unvalidated.json").write_text(
                json.dumps(parsed_dict, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            (out_dir / "parse_error.txt").write_text(str(e), encoding="utf-8")
        raise RuntimeError(f"phase2: Pydantic validation error: {e}") from e

    if out_dir is not None:
        (out_dir / "intake_output.json").write_text(
            parsed.model_dump_json(indent=2, by_alias=False), encoding="utf-8"
        )
        logger.success("phase2: wrote {}", out_dir / "intake_output.json")
    return parsed
