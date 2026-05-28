"""Run phase 2 (vector JSON → IntakeOutput) via DeepSeek V4 pro — thinking enabled.

Bypasses langchain entirely. Reasons:
  - langchain_openai's with_structured_output(method="function_calling") burns
    all output tokens on reasoning_content when DeepSeek thinking is on, and
    never gets to emit the tool call.
  - Phase 2 is single-shot (not multi-turn ReAct), so we don't need to feed
    reasoning_content back across turns — the memory feedback about disabling
    thinking only applies to ReAct loops.
  - Spatial topology inference (zone enclosure, surface adjacency, facade
    coord translation) is heavy reasoning — we WANT thinking on.

Approach:
  - Use openai.OpenAI client directly with DeepSeek's OpenAI-compatible endpoint
  - Pass extra_body={"thinking": {"type": "enabled"}} to enable reasoning
  - Embed IntakeOutput JSON schema in the system prompt and ask for JSON-only
    output (no tool / function_calling — final content is the JSON)
  - Parse content as JSON, validate via IntakeOutput.model_validate()

Usage:
    python Tool_scripts/run_phase2_deepseek.py \\
        --case test_data/SmallOffice/smalloffice_20_redraw

Output:
    <case>/phase2_intake/deepseek/intake_output.json   (success)
    <case>/phase2_intake/deepseek/raw_response.txt     (parse failure)
    <case>/phase2_intake/deepseek/run.log              (always)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Ensure project root on sys.path so `src.*` imports work
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Phase-2 rule docs live in the skill library (HEAD spec), not in the case dir.
# phase2 reads: phase2/rules.md + phase1/guide.md + phase1/pen_library.md
# (it does NOT read phase1/reading_guide.md — that is image-perception only and
# phase2 never sees images). Matches the phase 2 "Required reading" in
# AI_agent/new_case_guide_twostep.md Step 4b.
_SKILL_DIR = _PROJECT_ROOT / "skills" / "energyplus_mcp_twostep"

from dotenv import load_dotenv  # noqa: E402
from loguru import logger  # noqa: E402
from openai import OpenAI  # noqa: E402

from src.agent._share import ensure_schema_initialized  # noqa: E402
from src.agent.state import IntakeOutput  # noqa: E402

# Load the EnergyPlus IDD into BaseSchema so IntakeOutput.model_validate()
# can run its custom field validators (e.g. validate_terrain reads
# cls._idf_field.Building.Terrain.key).
ensure_schema_initialized()

load_dotenv()


# Plan-view filenames look like "<N>f_view.json" (1f_view.json, 2f_view.json, …);
# elevations are "<Name>_view.json" (South_view.json, …). The capture group is the
# floor number so plans sort numerically (10f after 2f, not before).
_PLAN_RE = re.compile(r"^(\d+)f_view\.json$", flags=re.IGNORECASE)


def _discover_phase1_files(case_dir: Path) -> list[str]:
    """Scan <case>/phase1_vector/ for ALL phase-1 vector JSONs.

    Order: numeric floor plans (by floor number) → facade elevations →
    supplementary / section / other vector JSONs. We include everything (not just
    *_view.json) because phase2_rules.md requires consuming supplements/sections
    too; dropping them was a silent capability regression. phase1_summary.md is
    .md (not matched by *.json) and is read separately.
    """
    vector_dir = case_dir / "phase1_vector"
    names = sorted(p.name for p in vector_dir.glob("*.json"))
    if not names:
        raise FileNotFoundError(f"no *.json found under {vector_dir}")
    plans = sorted(
        (n for n in names if _PLAN_RE.match(n)),
        key=lambda n: (int(_PLAN_RE.match(n).group(1)), n),
    )
    elevations = [
        n for n in names
        if not _PLAN_RE.match(n) and n.lower().endswith("_view.json")
    ]
    others = [
        n for n in names
        if not _PLAN_RE.match(n) and not n.lower().endswith("_view.json")
    ]
    return plans + elevations + others


MODEL_NAME = "deepseek-v4-pro"
MAX_OUTPUT_TOKENS = 64000


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()


def build_messages(case_dir: Path) -> tuple[str, str]:
    """Return (system_prompt, human_message)."""
    rules = _read(_SKILL_DIR / "phase2" / "rules.md")
    phase1_guide = _read(_SKILL_DIR / "phase1" / "guide.md")
    phase1_pens = _read(_SKILL_DIR / "phase1" / "pen_library.md")
    summary = _read(case_dir / "phase1_vector" / "phase1_summary.md")
    testdata = _read(case_dir / "testdata_prompt.json")

    intake_schema = json.dumps(
        IntakeOutput.model_json_schema(), indent=2, ensure_ascii=False
    )

    system_prompt = (
        "You are an EnergyPlus intake specialist running phase 2 of a two-step "
        "intake pipeline. Phase 1 (image → semantic vector JSON) is already "
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
        "Project metadata (testdata_prompt.json):\n```json\n" + testdata + "\n```\n"
    ]
    for fname in _discover_phase1_files(case_dir):
        jpath = case_dir / "phase1_vector" / fname
        if not jpath.exists():
            raise FileNotFoundError(f"phase1 JSON missing: {jpath}")
        human_chunks.append(
            f"\n[phase1 vector] {fname}:\n```json\n{_read(jpath)}\n```\n"
        )
    human_chunks.append(
        "\nProduce the IntakeOutput JSON now. Follow phase2/rules.md Step 1→7 "
        "derivation order. Enumerate every zone / surface / split-pairing / "
        "fenestration explicitly — no templates, no Floor_N_* shorthand. "
        "Use the facade translation formulas in phase1_summary.md §3 verbatim. "
        "Remember: output ONLY the JSON object, nothing else."
    )
    return system_prompt, "".join(human_chunks)


_JS_CONCAT_RE = re.compile(r'"\s*\+\s*\n\s*"', flags=re.MULTILINE)


def _fix_js_concat(s: str) -> str:
    """DeepSeek sometimes emits JS-style string concatenation across lines:

        "spec line 1\\n" +
            "spec line 2\\n"

    This is invalid JSON but the meaning is obvious — join them. We
    replace `"<ws>+<ws>"` (closing quote, +, newline-bearing whitespace,
    opening quote) with empty, splicing the two adjacent string literals.
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


def run(case_dir: Path) -> None:
    out_dir = case_dir / "phase2_intake" / "deepseek"
    out_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY missing from environment / .env")

    logger.info("phase2 deepseek: case_dir={}", case_dir)
    logger.info("phase2 deepseek: model={} base_url={}", MODEL_NAME, base_url)

    system_prompt, human_message = build_messages(case_dir)
    logger.info(
        "phase2 deepseek: prompt sizes — system={} chars, human={} chars",
        len(system_prompt), len(human_message),
    )

    client = OpenAI(api_key=api_key, base_url=base_url)

    logger.info("phase2 deepseek: invoking (thinking=enabled, max_tokens={})...", MAX_OUTPUT_TOKENS)
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_message},
        ],
        temperature=0.3,           # lower for structural output
        max_tokens=MAX_OUTPUT_TOKENS,
        extra_body={
            "thinking": {"type": "enabled"},
        },
    )

    msg = resp.choices[0].message
    finish_reason = resp.choices[0].finish_reason
    content = msg.content or ""
    reasoning = getattr(msg, "reasoning_content", None)
    usage = resp.usage

    logger.info(
        "phase2 deepseek: finish_reason={} usage={}",
        finish_reason,
        {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
    )
    if reasoning:
        logger.info("phase2 deepseek: reasoning_content {} chars (saved to thinking.txt)", len(reasoning))
        (out_dir / "thinking.txt").write_text(reasoning, encoding="utf-8")
    logger.info("phase2 deepseek: content {} chars", len(content))
    (out_dir / "raw_response.txt").write_text(content, encoding="utf-8")

    if finish_reason == "length":
        logger.warning("phase2 deepseek: hit max_tokens — response likely truncated")

    if not content.strip():
        logger.error("phase2 deepseek: empty content (finish_reason={})", finish_reason)
        raise SystemExit(1)

    payload = _extract_json(content)
    try:
        parsed_dict = json.loads(payload)
    except json.JSONDecodeError as e:
        logger.error("phase2 deepseek: JSON decode error: {}", e)
        (out_dir / "parse_error.txt").write_text(
            f"json decode: {e}\nfirst 500 chars of payload:\n{payload[:500]}",
            encoding="utf-8",
        )
        raise SystemExit(1) from e

    try:
        parsed = IntakeOutput.model_validate(parsed_dict)
    except Exception as e:
        logger.error("phase2 deepseek: Pydantic validation error: {}", e)
        # Still save the dict for inspection
        (out_dir / "intake_output_unvalidated.json").write_text(
            json.dumps(parsed_dict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (out_dir / "parse_error.txt").write_text(str(e), encoding="utf-8")
        raise SystemExit(1) from e

    out_path = out_dir / "intake_output.json"
    out_path.write_text(
        parsed.model_dump_json(indent=2, by_alias=False),
        encoding="utf-8",
    )
    logger.success("phase2 deepseek: wrote {} ({} bytes)", out_path, out_path.stat().st_size)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--case", required=True,
        help="case directory containing phase1_vector/ + testdata_prompt.json "
             "(rule docs are read from skills/energyplus_mcp_twostep/)",
    )
    args = ap.parse_args()
    run(Path(args.case).resolve())


if __name__ == "__main__":
    main()
