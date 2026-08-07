"""Staged intake pipeline: reading-stage vector JSON -> IntakeOutput.

The reading stage (0_reading: image -> semantic vector JSON) is image-bound and
half-manual; this module runs everything after it, image-blind, as ordered
stages each independently swappable and with a verifiable / diffable intermediate:

  1_correction      CORRECTION (LLM)   vectors + correction docs -> CorrectedGeometry
  core              DETERMINISTIC      canonical axis snap + sliver guard (code)
  2_modelling +     GEOMETRY (code)    CorrectedGeometry -> BuildingGeometry, then
  3_split_pairing                      serialized to zone/surface/fenestration specs
  4_mep             PHYSICS (LLM)      the 8 non-geometry IntakeOutput fields
  5_intakeoutput    ASSEMBLY (code)    stitch geometry + MEP specs -> IntakeOutput

The CorrectedGeometry checkpoint is materialized (correction_geometry*.json) so the
correction error budget is separable, and the deterministic core guarantees no
cross-floor sliver reaches EnergyPlus. Geometry is fully deterministic (the kernel
builds + serializes it); the LLM does only correction judgment (1_correction) and
physics semantics (4_mep).

This module is the single implementation. It is called from:
  - `intake_node` (the main graph), and
  - `scripts/run_pipeline_deepseek.py` (thin standalone CLI wrapper).

Per-stage model config: `intake_correction` / `intake_mep` in llm.yaml if present,
else fall back to `intake_correction` (so "model switching has one home" still
holds). Why a raw OpenAI client instead of langchain: single-shot calls with
DeepSeek thinking on; langchain's structured-output burns tokens on
reasoning_content and never emits the tool call, so we ask for JSON-only content
and parse it ourselves.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from openai import OpenAI

from omegaconf import OmegaConf

from src.agent._share import ensure_schema_initialized
from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.envelope import extract_authoritative_envelope
from src.agent.correction.vocab import (
    format_correction_system_vocabulary,
    producer_facing_json_schema,
    retry_guidance_for_correction,
)
from src.agent.execution.evidence_preflight import (
    EvidenceDebt,
    compute_evidence_debt_from_vector_dir,
    compute_reading_report_from_vector_dir,
    project_evidence_debt,
    write_evidence_debt,
)
from src.agent.llm import load_llm_section, resolve_llm_config_path
from src.agent.state import IntakeOutput
from src.validator.checks.schema import Disposition, RunProfile

if TYPE_CHECKING:
    from src.agent.geometry.modelling import BuildingGeometry
    from src.agent.output_coordinates import IntakeArtifactBundle

_SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "intake_pipeline"
_CORRECTION_DIR = _SKILL_DIR / "1_correction"
_CORRECTION_DOCS = [
    "README.md",
    "A0_contract.md",
    "A1_coordinate_normalization.md",
    "A2_regularization.md",
    "A3_arbitration.md",
    "A4_priors.md",
]

_PLAN_RE = re.compile(r"^(\d+)f_view\.json$", flags=re.IGNORECASE)
_JS_CONCAT_RE = re.compile(r'"\s*\+\s*\n\s*"', flags=re.MULTILINE)


def discover_vector_files(vector_dir: Path) -> list[str]:
    """Scan a reading-stage vector dir for ALL vector JSONs, in a stable order.

    Order: numeric floor plans (by floor number) -> facade elevations ->
    supplementary / section / other vector JSONs. `reading_summary.md` is read
    separately.
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
    prev = None
    while prev != s:
        prev = s
        s = _JS_CONCAT_RE.sub("", s)
    return s


def _extract_json(text: str) -> str:
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


def _load_correction_docs() -> str:
    return "\n\n".join(
        f"----- 1_correction/{name} -----\n{_read(_CORRECTION_DIR / name)}"
        for name in _CORRECTION_DOCS
    )


def _section(stage: str) -> dict:
    """Load `intake_<stage>` if present, else fall back to `intake_correction`.

    Only the "section absent from the config file" case triggers fallback.
    Any other error (YAML syntax, env-var interpolation failure, missing
    `default` and missing section) propagates immediately so a misconfigured
    `intake_mep` block never silently masquerades as `intake_correction`.
    """
    section_name = f"intake_{stage}"
    # Read the raw (unresolved) config keys without triggering interpolation —
    # this lets us distinguish "key absent → safe to fall back" from "key
    # present but value is broken → must surface the error".
    raw_keys = set(OmegaConf.load(resolve_llm_config_path()).keys())
    if section_name in raw_keys:
        # Section exists: load and resolve it; any error here is a real config
        # problem and must not be swallowed.
        return load_llm_section(section_name)
    # Section absent: fall back to intake_correction — but ONLY if it is itself
    # present. We must NOT delegate the absence to load_llm_section, which would
    # silently resolve to the downstream `default` ReAct config (wrong model /
    # thinking / temperature). A missing intake_correction is a hard config error.
    if "intake_correction" not in raw_keys:
        raise RuntimeError(
            f"llm.yaml has no 'intake_correction' section (required as the "
            f"fallback for '{section_name}'); refusing to silently use 'default'. "
            f"Add an 'intake_correction' section to the config."
        )
    return load_llm_section("intake_correction")


def _call_json_llm(
    section: dict,
    system_prompt: str,
    human: str,
    *,
    out_dir: Path | None,
    prefix: str,
    attempts: int = 1,
    validate: Callable[[dict], None] | None = None,
    retry_guidance: Callable[[BaseException], str | None] | None = None,
) -> dict:
    """JSON-only LLM call with retry; return the parsed (and optionally validated) dict.

    The staged-intake LLM (DeepSeek) is single-shot per call and occasionally
    returns invalid JSON or a structurally-valid-but-incomplete object (e.g. a
    CorrectedGeometry that dropped all facade windows — the sm21 0-window class).
    With `attempts > 1` a parse/`validate` failure re-issues the call (the model's
    sampling differs each draw), turning an intermittent bad draw from a hard
    pipeline failure into a retry. `validate(parsed)` may raise to reject a draw
    that parses but fails a semantic check. Saves raw/thinking artifacts (last
    attempt). Raises after the final attempt still fails.

    `retry_guidance` (F-4a): when a retry happens AND the failure got far enough
    to receive a model response (i.e. it failed parsing/validation, not the
    network), this callable translates the exception into a FORMAT-ONLY
    corrective message that is appended to the next attempt's messages — so a
    systematic schema misunderstanding (unknown field, off-vocabulary key) is
    corrected instead of repeated verbatim until the budget is gone. Transport
    errors (the `create()` call raised before any response) retry blind, and
    `retry_guidance` returning ``None`` (e.g. for a semantic ValueError) also
    retries blind: the inner retry owns ONLY schema/format robustness, never
    geometry/upstream/numeric values. None/omitted ⇒ fully blind retry (legacy)."""
    api_key = section.get("api_key")
    base_url = section.get("base_url")
    model_name = section["model_name"]
    max_tokens = section.get("max_tokens", 64000)
    temperature = section.get("temperature", 0.3)
    reasoning_effort = section.get("reasoning_effort")
    extra_body = section.get("extra_body") or {"thinking": {"type": "enabled"}}
    if not api_key:
        raise RuntimeError(f"{prefix}: no api_key (set DEEPSEEK_API_KEY in .env).")
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "{}: model={} prompt sizes system={} human={} chars",
        prefix,
        model_name,
        len(system_prompt),
        len(human),
    )
    optional: dict = {}
    if reasoning_effort is not None:
        optional["reasoning_effort"] = reasoning_effort

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=600.0, max_retries=2)
    last_err: Exception | None = None
    # F-4a: corrective message appended to the NEXT attempt's messages. Stays
    # "" (blind retry) unless the previous attempt received a model response
    # that then failed schema validation AND retry_guidance translated that
    # failure into a format-only correction. Transport errors never set this.
    guidance_text = ""
    for attempt in range(1, attempts + 1):
        # Reset per-attempt state so the except branch can always reference
        # `content` even when a transport error fires before the response is
        # unpacked (L2: transport exceptions now consume an attempt and retry).
        content: str = ""
        finish_reason: str | None = None
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human},
        ]
        if guidance_text:
            messages.append({"role": "user", "content": guidance_text})
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,
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
                "{}: attempt {}/{} finish_reason={} usage={}",
                prefix,
                attempt,
                attempts,
                finish_reason,
                {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                },
            )
            if out_dir is not None:
                if reasoning:
                    (out_dir / f"{prefix}_thinking.txt").write_text(
                        reasoning, encoding="utf-8"
                    )
                (out_dir / f"{prefix}_raw.txt").write_text(content, encoding="utf-8")
            if finish_reason == "length":
                logger.warning("{}: hit max_tokens — response likely truncated", prefix)

            if not content.strip():
                raise ValueError(f"empty content (finish_reason={finish_reason})")
            parsed = json.loads(_extract_json(content))
            if validate is not None:
                validate(parsed)
            return parsed
        except Exception as e:  # noqa: BLE001 — transport errors and bad draws both retry
            last_err = e
            if out_dir is not None:
                # `content` is always a str here (initialised "" above); for
                # transport failures it stays "" and the preview reflects that.
                preview = _extract_json(content)[:500] if content.strip() else "(empty)"
                (out_dir / f"{prefix}_parse_error.txt").write_text(
                    f"attempt {attempt}/{attempts}: {type(e).__name__}: {e}\n"
                    f"first 500 chars:\n{preview}",
                    encoding="utf-8",
                )
            if attempt < attempts:
                # F-4a: earn corrective feedback ONLY when we got a model
                # response back that then failed parsing/validation. `content`
                # is non-empty iff create() returned (a transport error raises
                # inside create() before `content` is assigned, so it stays ""
                # and we retry blind). retry_guidance then decides whether the
                # exception is a schema ValidationError worth translating;
                # returning None (semantic ValueError / JSON syntax / etc.)
                # also retries blind. Guidance carries field paths + the
                # schema's legal tokens only, never geometry/upstream/numbers.
                if retry_guidance is not None and content.strip():
                    try:
                        guidance_text = retry_guidance(e) or ""
                    except Exception:  # noqa: BLE001 — guidance must never crash the retry
                        guidance_text = ""
                else:
                    guidance_text = ""
                logger.warning(
                    "{}: attempt {}/{} rejected ({}); retrying",
                    prefix,
                    attempt,
                    attempts,
                    e,
                )
                continue
            raise RuntimeError(
                f"{prefix}: failed after {attempts} attempt(s): {last_err}"
            ) from last_err
    raise RuntimeError(f"{prefix}: no attempts ran")  # unreachable when attempts >= 1


# --------------------------------------------------------------------------- #
# 1_correction — correction (LLM) -> CorrectedGeometry
# --------------------------------------------------------------------------- #
def _build_correction_messages(
    vector_dir: Path,
    testdata_text: str,
    *,
    feedback: str | None = None,
    evidence_debt: EvidenceDebt | None = None,
    target=None,
    observation_reference_catalog: str | None = None,
) -> tuple[str, str]:
    correction_docs = _load_correction_docs()
    reading_guide = _read(_SKILL_DIR / "0_reading" / "guide.md")
    reading_pens = _read(_SKILL_DIR / "0_reading" / "pen_library.md")
    # F-2b: the reading summary is a hard dependency (it carries the
    # cross-image narrative correction assembles its prompt around). A missing
    # summary is a named, localizable failure pointing at the reading stage's
    # kickoff contract — not a bare OSError two layers down in _read.
    summary_path = vector_dir / "reading_summary.md"
    if not summary_path.is_file():
        raise FileNotFoundError(
            f"1_correction requires the 0_reading summary at {summary_path}, but "
            "it is missing — the reading stage must produce reading_summary.md "
            "(kickoff contract); correction cannot assemble its prompt without it "
            "(F-2b)"
        )
    summary = _read(summary_path)
    target = target or __import__("src.agent.correction.parse", fromlist=["correction_target"]).correction_target("rectangular")
    # F-15 (2026-08-07): the PROMPT sees a schema stripped of
    # deterministic-core-only fields (facade_segments / facade_segment_id) —
    # validation elsewhere still uses the full target.schema_model unchanged.
    geom_schema = json.dumps(producer_facing_json_schema(target.schema_model), indent=2, ensure_ascii=False)

    system_prompt = (
        "You are running the CORRECTION stage (1_correction) of a staged "
        "EnergyPlus intake pipeline. The reading stage (image -> semantic vector "
        "JSON) is done; you DO NOT see drawings. Apply the correction layer to the "
        "reading-stage primitives and emit a single CorrectedGeometry JSON object: "
        "world-frame, wall-centerline, self-consistent room cells + windows + "
        "per-floor z, plus an audit.\n\n"
        "Do the correction (A1 -> A2 -> A3, priors via A4 under A0/A3 gating): put "
        "every coordinate in one world frame at wall CENTERLINE; reconcile the "
        "z-stack; ARBITRATE stroke-vs-dimension conflicts (trust dimensions; make "
        "each elevation window fall entirely within one room); complete missing "
        "values; log every material change in `corrections`, unresolved ambiguity "
        "in `conflicts`, and anything unsafe to fix in `unsupported`.\n\n"
        "Each room is exactly one cell; never split a single room into several "
        "cells just to keep them rectangular. A rectangular room is a "
        "rectangular cell {id, role, x:[min,max], y:[min,max]}. Only when a "
        "room's own shape is not a single rectangle (e.g. an L-shaped corridor), "
        f"emit the selected schema_version {target.schema_version!r} and give that cell a CCW orthogonal `polygon` "
        "(exterior ring, first vertex not repeated); keep `x`/`y` as the exact "
        "polygon bbox projection. Polygon is the exception, not the default. "
        "For `role`, prefer the image-observed role from room_labels; fall back "
        "to layout priors ONLY when no observation covers a room. "
        "Each floor gives z_floor + ceiling_height. Each window gives facade, "
        "along-facade span [min,max], z [sill,head] (absolute world z), and the "
        "room id it belongs to. Do not output zones/surfaces — only the corrected "
        "geometry primitives.\n\n"
        "OUTPUT FORMAT (strict): ONLY the CorrectedGeometry JSON object, starting "
        "with `{` and ending with `}`. No markdown, no prose.\n\n"
        "===== BEGIN CorrectedGeometry JSON SCHEMA =====\n"
        f"{geom_schema}\n"
        "===== END CorrectedGeometry JSON SCHEMA =====\n\n"
        + (
            "Note: `corrections`/`conflicts`/`unsupported` are free-form audit "
            "rows for THIS draw's own material changes / ambiguities / unsafe "
            "fixes. Never add a row with `\"kind\": \"window_host_resolution\"` "
            "to any of them — that is a separate audit trail the deterministic "
            "core produces downstream from your draw, not something for you to "
            "pre-fill.\n\n"
            if target.schema_version == "3"
            else ""
        )
        + f"{format_correction_system_vocabulary(target)}"
        "===== BEGIN RULE DOCUMENT: 1_correction =====\n"
        f"{correction_docs}\n"
        "===== END RULE DOCUMENT: 1_correction =====\n\n"
        "===== BEGIN REFERENCE: 0_reading/guide.md =====\n"
        f"{reading_guide}\n"
        "===== END REFERENCE: 0_reading/guide.md =====\n\n"
        "===== BEGIN REFERENCE: 0_reading/pen_library.md =====\n"
        f"{reading_pens}\n"
        "===== END REFERENCE: 0_reading/pen_library.md =====\n\n"
        "===== BEGIN REFERENCE: reading_summary.md =====\n"
        f"{summary}\n"
        "===== END REFERENCE: reading_summary.md =====\n"
    )

    chunks = [
        "Project metadata (testdata_prompt.json):\n```json\n" + testdata_text + "\n```\n"
    ]
    vector_files = discover_vector_files(vector_dir)
    room_label_inputs = _reading_room_label_inputs(vector_dir, vector_files)
    if room_label_inputs:
        chunks.append(
            "\nExplicit room role observations from reading `room_labels` "
            "(image-local anchors):\n```json\n"
            + json.dumps(room_label_inputs, indent=2, ensure_ascii=False)
            + "\n```\n"
        )
    if evidence_debt is not None and evidence_debt.debts:
        chunks.append(
            "\nReading evidence debt from deterministic 0_reading preflight "
            "(A8 handoff; current run_profile disposition already applied):\n"
            "```json\n"
            + evidence_debt.model_dump_json(indent=2)
            + "\n```\n"
            "Correction discipline for evidence debt: do not invent coordinates, "
            "dimensions, or source links for debt items. If the reading artifact "
            "does not contain independent evidence to resolve an item, record the "
            "unresolved item in `conflicts` with the debt check_id/view/offender ids. "
            "Do not write these reading evidence-debt items to `unsupported`; "
            "`unsupported` is reserved for deterministic kernel findings.\n"
        )
    for fname in vector_files:
        chunks.append(f"\n[reading vector] {fname}:\n```json\n{_read(vector_dir / fname)}\n```\n")
    if observation_reference_catalog:
        # F-7 (2026-08-05): source_ids cites what the draw can actually see —
        # a reading-vector observation, not a locator hash it cannot compute
        # (that hash embeds reading-artifact bytes this stage never receives).
        chunks.append(
            "\n===== BEGIN WINDOW SOURCE OBSERVATIONS =====\n"
            "Each window's `provenance.<claim>.source_ids` must cite the "
            "specific reading-stage observations that support that claim, "
            "using the form `<view_file_stem>/<observation_id>` — the "
            "reading vector JSON's filename above (without `.json`) "
            "followed by `/` and the `id` of a `window`-pen stroke from that "
            "file's `strokes` array (e.g. `1f_view/S11`). Cite ONLY ids "
            "listed in the catalog below; never invent an id, and never "
            "write a `src:`-prefixed hash — you cannot compute one and must "
            "not try. Every window's `existence` claim requires at least one "
            "such reference; other claims (`host`/`along`/`width`/`sill`/"
            "`head`/`appearance`) may only cite an observation whose entry "
            "below lists that claim as allowed. For an elevation observation, "
            "when the entry below shows an 'approx world-along interval', that "
            "number is already translated out of image-local into the SAME "
            "world frame as a window's own `span` — pick the elevation "
            "observation whose interval overlaps the window you are citing "
            "for, not the one whose raw on-image position looks similar; do "
            "NOT re-derive or re-flip it yourself (it is informational, not a "
            "substitute for A1 §2.2, and is independently re-verified after "
            "your draw regardless).\n\n"
            "Legal observation references for this run "
            "(view/observation: allowed claims):\n"
            f"{observation_reference_catalog}\n"
            "===== END WINDOW SOURCE OBSERVATIONS =====\n"
        )
    if feedback:
        chunks.append(
            "\n\n=== Geometry feedback from a previous attempt — fix these ===\n"
            f"{feedback}\nAddress every item while following the correction rules.\n"
        )
    chunks.append(
        "\nApply the correction now and output ONLY the CorrectedGeometry JSON "
        "object. Derive each window's world `span` from its elevation's image-local "
        "`facade` block using the per-facade world-axis convention in 1_correction "
        "A1 §2.2 (mind the North/West sign flip); reading does not assert world axes. "
        "Enumerate every room cell and window explicitly."
    )
    return system_prompt, "".join(chunks)


def _reading_room_label_inputs(vector_dir: Path, vector_files: list[str]) -> list[dict]:
    observations = []
    for fname in vector_files:
        try:
            data = json.loads(_read(vector_dir / fname))
        except (json.JSONDecodeError, OSError):
            continue
        room_labels = data.get("room_labels") or []
        if not room_labels:
            continue
        observations.append(
            {
                "view_file": fname,
                "image_label": data.get("image_label", ""),
                "image_kind": data.get("image_kind", ""),
                "room_labels": room_labels,
            }
        )
    return observations


def _reading_window_stroke_count(vector_dir: Path) -> int:
    """Total `window`-pen strokes across all reading-stage vector JSONs.

    A proxy for "this building has windows in the drawings". Used only as a
    presence signal (>0 vs 0), not a 1:1 count — a plan window stroke and its
    elevation counterpart both count, so this over-counts window entities."""
    total = 0
    for p in sorted(vector_dir.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        total += sum(1 for s in d.get("strokes", []) if s.get("pen") == "window")
    return total


def correction_draw_issues(
    geom: "CorrectedGeometry", expected_window_strokes: int
) -> list[str]:
    """Semantic draw-quality issues on a parsed (pre-core) CorrectedGeometry — the
    content checks that decide whether a structurally-valid draw is good enough:

    - Window completeness: reading has windows but correction emitted zero (the
      sm21 0-window instability). Conservative: only the all-or-nothing case (window
      strokes ≠ window entities, so no fuzzy "too few" threshold).
    - Duplicate cell ids across floors: three downstream dicts key on cell id;
      duplicates cause silent last-wins corruption.
    - z-stack discontinuity: adjacent floors whose gap exceeds gap_close_threshold_m
      (gaps ≤ the threshold are auto-closed by the deterministic core, so they are
      NOT issues here — run this on the PRE-core draw).

    Returns a list of messages (empty = clean). It does NOT raise — so the stepwise
    orchestrator can fold these into the stage gate① report (each semantic-bad draw
    then becomes a counted, append-only attempt + a blind resample), instead of
    being silently retried inside the LLM call and bypassing the per-stage budget.
    """
    from src.agent.correction.cell_geometry import (
        cell_has_polygon,
        validate_cell_polygon,
    )
    from src.agent.correction.config import load_core_tolerances
    from src.agent.geometry.capability import FEATURE_CELL_POLYGON, schema_supports

    tol = load_core_tolerances()
    issues: list[str] = []
    if expected_window_strokes > 0 and not geom.windows:
        issues.append(
            f"correction emitted 0 windows but the reading stage has "
            f"{expected_window_strokes} window stroke(s) — facade windows were "
            f"dropped (a known 1_correction instability, not a kernel issue)"
        )

    seen: dict[str, str] = {}  # cell_id -> floor_name
    for floor in geom.floors:
        for cell in floor.cells:
            if cell.id in seen:
                issues.append(
                    f"duplicate cell id '{cell.id}' found in floors "
                    f"'{seen[cell.id]}' and '{floor.name}' — downstream geometry "
                    f"dicts key on cell id, so duplicates cause last-wins corruption"
                )
            else:
                seen[cell.id] = floor.name
            # Polygon crimes are LLM draw defects, not code defects: mirror the
            # deterministic core's polygon raises here (winding-tolerant — the
            # core canonicalizes CW→CCW) so a bad polygon blocks THIS draw and
            # blind-resamples instead of crashing the flow inside the core.
            if cell_has_polygon(cell):
                if not schema_supports(geom, FEATURE_CELL_POLYGON):
                    issues.append(
                        f"cell '{cell.id}' has a polygon but schema_version is "
                        f"not '2' — polygon cells require the v2 contract"
                    )
                    continue
                try:
                    validate_cell_polygon(
                        cell,
                        min_edge_length_m=tol.min_edge_length_m,
                        allow_cw=True,
                        allow_closed=True,
                    )
                except ValueError as exc:
                    issues.append(f"invalid cell polygon in this draw: {exc}")
    gap_limit = tol.gap_close_threshold_m
    sorted_floors = sorted(geom.floors, key=lambda f: f.z_floor)
    for prev, cur in zip(sorted_floors, sorted_floors[1:]):
        expected_z = prev.z_floor + prev.ceiling_height
        gap = abs(cur.z_floor - expected_z)
        if gap > gap_limit:
            issues.append(
                f"z-stack discontinuity between floor '{prev.name}' "
                f"(top={expected_z:.3f}) and '{cur.name}' (z_floor={cur.z_floor}): "
                f"gap={gap:.3f} m > gap_close_threshold={gap_limit} m"
            )
    return issues


def _schema_only_correction_validator(parsed: dict, target=None) -> None:
    """Inner-retry validator for stepwise mode: accept any draw that parses into a
    valid CorrectedGeometry (schema/format robustness only). Semantic draw quality
    is judged by the OUTER gate① (correction_draw_issues), so a content-bad draw is
    counted + filed, not silently re-drawn inside `_call_json_llm`."""
    from src.agent.correction.parse import correction_target, parse_correction_draw
    parse_correction_draw(parsed, target or correction_target("rectangular"))


def _make_correction_validator(
    expected_window_strokes: int,
    target=None,
) -> Callable[[dict], None]:
    """Full inner-retry validator (legacy ``run_pipeline`` path): reject a draw on
    Pydantic schema violation OR any semantic draw issue (0-window / duplicate cell
    id / z-stack discontinuity). Raises ValueError on the first problem, which makes
    `_call_json_llm` log + retry (up to `attempts` draws).

    Stepwise mode uses ``_schema_only_correction_validator`` instead and routes the
    semantic checks through gate① — see ``correction_draw_issues``.
    """
    from src.agent.correction.parse import correction_target
    target = target or correction_target("rectangular")
    def _validate(parsed: dict) -> None:
        from src.agent.correction.parse import parse_correction_draw
        geom = parse_correction_draw(parsed, target)
        issues = correction_draw_issues(geom, expected_window_strokes)
        if issues:
            raise ValueError(issues[0])

    return _validate


_UNSET_VALIDATOR = object()


def run_correction(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
    draw_validate: "Callable[[dict], None] | None | object" = _UNSET_VALIDATOR,
    run_profile: RunProfile = "exploratory",
    capability_profile: str = "rectangular",
    evidence_debt: EvidenceDebt | None = None,
    dimensioned_views: set[str] | None = None,
    fail_closed_evidence_debt: bool = False,
    target=None,
    observation_reference_catalog: str | None = None,
) -> CorrectedGeometry:
    """1_correction LLM stage → CorrectedGeometry (pre-core).

    ``draw_validate`` is the inner-retry validator (a failure re-issues the LLM call
    up to ``attempts`` times). Default = the full ``_make_correction_validator``
    (legacy ``run_pipeline`` path: schema + semantic). Pass
    ``_schema_only_correction_validator`` (stepwise mode) so the inner retry handles
    only schema/format, leaving semantic draw quality to gate① (so a content-bad
    draw is counted + filed as an attempt, not silently re-drawn). Pass ``None`` to
    disable the inner validator entirely."""
    from src.agent.correction.parse import correction_target, parse_correction_draw
    ensure_schema_initialized()  # safe for standalone stage calls (idempotent)
    target = target or correction_target(capability_profile)
    if evidence_debt is None:
        from src.agent.execution.case_metadata import (
            dimensioned_states_from_data,
            parse_testdata_text,
        )
        # R1-3 (派工单 §1.3): parse the structured 4-state declaration from
        # testdata (declared_true/declared_false survive). A caller-provided
        # legacy bool set is promoted to declared_true for pre-R1-3 parity.
        if dimensioned_views:
            dim_states = {stem: "declared_true" for stem in dimensioned_views}
        else:
            dim_states = dimensioned_states_from_data(parse_testdata_text(testdata_text) or {})
        evidence_debt = compute_evidence_debt_from_vector_dir(
            vector_dir,
            run_profile=run_profile,
            capability_profile=capability_profile,
            dimensioned_states=dim_states,
        )
    if out_dir is not None:
        write_evidence_debt(out_dir / "evidence_debt.json", evidence_debt)
    if fail_closed_evidence_debt and evidence_debt.blocking:
        checks = ", ".join(item.check_id for item in evidence_debt.blocking)
        raise RuntimeError(
            "1_correction preflight blocked by reading evidence debt "
            f"under run_profile={run_profile}: {checks}"
        )
    system_prompt, human = _build_correction_messages(
        vector_dir, testdata_text, feedback=feedback, evidence_debt=evidence_debt, target=target,
        observation_reference_catalog=observation_reference_catalog,
    )
    validator = (
        _make_correction_validator(_reading_window_stroke_count(vector_dir), target)
        if draw_validate is _UNSET_VALIDATOR
        else None if draw_validate is None
        else (lambda parsed: draw_validate(parsed, target))
    )
    parsed = _call_json_llm(
        _section("correction"),
        system_prompt,
        human,
        out_dir=out_dir,
        prefix="correction",
        attempts=3,
        validate=validator,
        retry_guidance=retry_guidance_for_correction(target),
    )
    try:
        geom = parse_correction_draw(parsed, target)
    except Exception as e:
        if out_dir is not None:
            (out_dir / "correction_geometry_unvalidated.json").write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        raise RuntimeError(f"1_correction: CorrectedGeometry validation error: {e}") from e
    if out_dir is not None:
        (out_dir / "correction_geometry.json").write_text(
            geom.model_dump_json(indent=2), encoding="utf-8"
        )
    return geom


# --------------------------------------------------------------------------- #
# 4_mep — physical-information authoring (LLM): non-geometry specs only
# --------------------------------------------------------------------------- #
def _build_mep_messages(
    zone_specs: str,
    used_constructions: set[str],
    testdata_text: str,
    *,
    feedback: str | None = None,
):
    from src.agent.intakeoutput import MepOutput

    authoring = _read(_SKILL_DIR / "4_mep" / "authoring.md")
    mep = _read(_SKILL_DIR / "4_mep" / "mep.md")
    mep_schema = json.dumps(
        MepOutput.model_json_schema(), indent=2, ensure_ascii=False
    )
    cons_list = "\n".join(f"- {c}" for c in sorted(used_constructions))

    system_prompt = (
        "You are running the 4_MEP stage of a staged EnergyPlus intake pipeline. "
        "The geometry is ALREADY built and serialized deterministically — you "
        "author ONLY the non-geometry specs and attach them by name. Do NOT "
        "produce zone_specs / surface_specs / fenestration_specs.\n\n"
        "Output a single MepOutput JSON object with exactly these keys: building, "
        "site_location, material_specs, construction_specs, schedule_specs, "
        "hvac_specs, people_specs, lights_specs.\n\n"
        "OUTPUT FORMAT (strict): ONLY the MepOutput JSON object, `{`..`}`, no "
        "markdown, no prose.\n\n"
        "===== BEGIN MepOutput JSON SCHEMA =====\n"
        f"{mep_schema}\n"
        "===== END MepOutput JSON SCHEMA =====\n\n"
        "===== BEGIN RULE DOCUMENT: 4_mep/authoring.md =====\n"
        f"{authoring}\n"
        "===== END RULE DOCUMENT: 4_mep/authoring.md =====\n\n"
        "===== BEGIN REFERENCE: 4_mep/mep.md (default values) =====\n"
        f"{mep}\n"
        "===== END REFERENCE: 4_mep/mep.md =====\n"
    )

    chunks = [
        "Project metadata (testdata_prompt.json):\n```json\n" + testdata_text + "\n```\n",
        "\nZONE LIST (author per-zone people/lights/hvac against these exact "
        "names; do not re-author geometry):\n```\n" + zone_specs + "\n```\n",
        "\nREQUIRED CONSTRUCTIONS — the geometry references these; you MUST define "
        "every one in construction_specs (with its materials in material_specs):\n"
        + cons_list + "\n",
    ]
    if feedback:
        chunks.append(
            "\n\n=== Feedback from a previous attempt — fix these ===\n"
            f"{feedback}\n"
        )
    chunks.append(
        "\nProduce the MepOutput JSON now. Define every required construction, "
        "keep schedule_specs complete (incl. the people activity-level schedule), "
        "and follow the naming rules. Output ONLY the JSON object."
    )
    return system_prompt, "".join(chunks)


def run_mep(
    zone_specs: str,
    used_constructions: set[str],
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
):
    """4_MEP LLM stage: author the 8 non-geometry IntakeOutput fields."""
    from src.agent.intakeoutput import MepOutput

    ensure_schema_initialized()
    system_prompt, human = _build_mep_messages(
        zone_specs, used_constructions, testdata_text, feedback=feedback
    )
    parsed = _call_json_llm(
        _section("mep"), system_prompt, human, out_dir=out_dir, prefix="mep", attempts=3
    )
    try:
        result = MepOutput.model_validate(parsed)
    except Exception as e:
        if out_dir is not None:
            (out_dir / "mep_output_unvalidated.json").write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        raise RuntimeError(f"4_mep: MepOutput validation error: {e}") from e
    if out_dir is not None:
        (out_dir / "mep_output.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
    return result


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #
def materialize_kernel_geometry(
    geom: CorrectedGeometry,
    out_dir: Path | None,
    *,
    capability_profile: str = "rectangular",
    window_host_proof=None,
) -> tuple["BuildingGeometry | None", list[str]]:
    """Run the deterministic geometry kernel (2_modelling -> 3_split_pairing) on
    the snapped CorrectedGeometry and materialize the result + a gate report.

    Returns `(building_geometry, gate_issues)`. The geometry is authoritative —
    `run_pipeline` reuses this object (it does NOT build a second time). On a hard
    kernel error returns `(None, [err])` so the caller can fail loudly. The
    InterZone gate issues are advisory here (the downstream gate re-checks the
    assembled IDF). Never raises.
    """
    # Lazy imports: keep the kernel (shapely/eppy) off the hot path for callers
    # that never reach here, mirroring the run_pipeline import discipline.
    try:
        from src.agent.geometry import build_geometry
        from src.agent.geometry.to_idf import building_to_idf
        from src.validator.interzone import validate_interzone_surface_pairs

        # build_geometry is read-only on `geom` (it constructs new ZoneVolumes /
        # polygons), so the same `geom` is safe to hand to later stages.
        bg = build_geometry(
            geom,
            capability_profile=capability_profile,
            window_host_proof=window_host_proof,
        )
        issues = validate_interzone_surface_pairs(building_to_idf(bg))
    except Exception as e:  # noqa: BLE001 — advisory build, never fatal here
        logger.warning("kernel: geometry build/gate failed: {}", e)
        err = [f"kernel-error: {type(e).__name__}: {e}"]
        if out_dir is not None:
            (out_dir / "kernel_gate_report.json").write_text(
                json.dumps({"gate_issues": err, "build_notes": []}, indent=2),
                encoding="utf-8",
            )
        return None, err

    logger.info(
        "kernel: {} zones, {} surfaces, {} windows; gate issues={} notes={}",
        len(dict.fromkeys(bg.zones)),
        len(bg.surfaces),
        len(bg.windows),
        len(issues),
        len(bg.notes),
    )
    if out_dir is not None:
        from src.agent.geometry.specs import building_geometry_json

        (out_dir / "building_geometry.json").write_text(
            building_geometry_json(bg), encoding="utf-8"
        )
        (out_dir / "kernel_gate_report.json").write_text(
            json.dumps(
                {"gate_issues": issues, "build_notes": bg.notes},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return bg, issues


def _gate_self_check_report(
    *,
    stage_name: str,
    report,
    stage_dir: Path | None,
    filename: str,
    run_profile: RunProfile,
) -> None:
    if stage_dir is not None:
        (stage_dir / filename).write_text(
            report.model_dump_json(indent=2), encoding="utf-8"
        )
    blocking = report.blocking()
    if not blocking:
        return
    blocking_ids = [result.check_id for result in blocking]
    if run_profile in {"golden", "regression"}:
        raise RuntimeError(
            f"{stage_name} self-check blocked under run_profile={run_profile}: "
            + "; ".join(
                f"{result.check_id}: {result.message}" for result in blocking
            )
        )
    logger.warning(
        "{} self-check reported {} blocking check(s) under run_profile={}; "
        "continuing: {}",
        stage_name,
        len(blocking),
        run_profile,
        ", ".join(blocking_ids),
    )


def run_pipeline(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
    run_profile: RunProfile = "exploratory",
    capability_profile: str = "rectangular",
) -> IntakeOutput:
    """Compatibility wrapper (E4-output-contract spec v2 §3.5): identical to
    the historical signature/return, but implemented on top of
    :func:`run_pipeline_artifacts` so a legacy caller and the bundle-aware
    `intake_node` mainline can never drift onto two assembly code paths."""
    intake, _bundle = run_pipeline_artifacts(
        vector_dir, testdata_text, out_dir=out_dir, feedback=feedback,
        run_profile=run_profile, capability_profile=capability_profile,
    )
    return intake


def run_pipeline_artifacts(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
    run_profile: RunProfile = "exploratory",
    capability_profile: str = "rectangular",
) -> "tuple[IntakeOutput, IntakeArtifactBundle | None]":
    """Staged intake: 1_correction -> deterministic core -> deterministic geometry
    kernel (2_modelling + 3_split_pairing) -> 4_mep (LLM) -> 5_intakeoutput assembly.

    Geometry is deterministic: the kernel builds + the serializer emits
    zone/surface/fenestration specs; 4_mep authors only the 8 non-geometry fields;
    assembly stitches them and runs a contract check.

    Returns ``(intake, bundle)``. ``bundle`` is the E4
    :class:`~src.agent.output_coordinates.IntakeArtifactBundle` (IntakeOutput +
    OutputCoordinateContract + coordinate snapshot + validation context) and is
    present whenever gate① accepted the correction; it is ``None`` only for
    the exploratory-profile edge case where a blocking correction result was
    warned-through (no accepted-correction identity exists to bind a contract
    to — assembly then behaves exactly as pre-E4).

    When `out_dir` is given, artifacts are filed into stage-numbered subdirs that
    mirror the 0–5 pipeline:
      out_dir/1_correction/    correction_geometry.json (pre-snap) +
                               correction_geometry_snapped.json (post core) +
                               corrections.json + correction raw/thinking
      out_dir/2_modelling/     building_geometry.json + kernel_gate_report.json +
                               kernel_checks.json
      out_dir/3_split_pairing/ geometry_specs.md (serialized cut+paired specs)
      out_dir/4_mep/           mep_output.json + mep raw/thinking
      out_dir/5_intakeoutput/  intake_output.json (final) + contract_issues.json
                               + output_coordinate_contract.json/_snapshot.json
                               sidecars when a contract was derived
    ``run_profile`` defaults to exploratory for backward compatibility.
    ``feedback`` is routed to both 1_correction (geometry) and 4_mep (physics)
    repair.
    """
    ensure_schema_initialized()

    def _stage(name: str) -> Path | None:
        if out_dir is None:
            return None
        d = out_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    logger.info("1_correction: correcting from {}", vector_dir)
    from src.agent.execution.case_metadata import (
        dimensioned_states_from_data,
        expected_zone_total_from_testdata,
        parse_testdata_text,
    )

    parsed_testdata = parse_testdata_text(testdata_text)
    # R1-3 (派工单 §1.3): per-view 4-state applicability from the structured
    # declaration, not a bool set — declared_true/declared_false survive to
    # checks.json instead of collapsing to legacy_default.
    dimensioned_states = dimensioned_states_from_data(parsed_testdata or {})
    reading_report = compute_reading_report_from_vector_dir(
        vector_dir,
        run_profile=run_profile,
        capability_profile=capability_profile,
        dimensioned_states=dimensioned_states,
    )
    from src.agent.reading import load_reading_view

    reading_views = [
        load_reading_view(path)
        for path in sorted(Path(vector_dir).glob("*_view.json"))
    ]
    s0 = _stage("0_reading")
    if s0 is not None:
        (s0 / "reading_checks.json").write_text(
            reading_report.model_dump_json(indent=2), encoding="utf-8"
        )
    evidence_debt = project_evidence_debt(
        reading_report,
        run_profile=run_profile,
    )
    s1 = _stage("1_correction")
    if s1 is not None:
        write_evidence_debt(s1 / "evidence_debt.json", evidence_debt)
    if evidence_debt.blocking:
        checks = ", ".join(item.check_id for item in evidence_debt.blocking)
        raise RuntimeError(
            "1_correction preflight blocked by reading evidence debt "
            f"under run_profile={run_profile}: {checks}"
        )
    _gate_self_check_report(
        stage_name="0_reading",
        report=reading_report,
        stage_dir=None,
        filename="reading_checks.json",
        run_profile=run_profile,
    )
    observation_reference_catalog = None
    if out_dir is not None:
        from src.agent.correction.parse import correction_target as _correction_target
        from src.agent.correction.window_sources import build_observation_reference_catalog_from_run

        if _correction_target(capability_profile).schema_version == "3":
            observation_reference_catalog = build_observation_reference_catalog_from_run(
                run_dir=out_dir, reading_dir=vector_dir, required_for_v3=True,
            )
    geom = run_correction(
        vector_dir,
        testdata_text,
        out_dir=s1,
        feedback=feedback,
        run_profile=run_profile,
        capability_profile=capability_profile,
        evidence_debt=evidence_debt,
        observation_reference_catalog=observation_reference_catalog,
    )

    from src.validator.checks.correction import check_evidence_debt_coverage

    coverage_report = check_evidence_debt_coverage(
        geom,
        evidence_debt,
        capability_profile=capability_profile,
        run_profile=run_profile,
    )
    if coverage_report.results and s1 is not None:
        (s1 / "evidence_debt_coverage_checks.json").write_text(
            coverage_report.model_dump_json(indent=2), encoding="utf-8"
        )
    blocking_coverage = [
        result
        for result, disp in coverage_report.dispositions()
        if disp == Disposition.BLOCK
    ]
    if blocking_coverage:
        raise RuntimeError(
            "1_correction evidence debt coverage blocked under "
            f"run_profile={run_profile}: "
            + "; ".join(f"{r.check_id}: {r.message}" for r in blocking_coverage)
        )

    from src.agent.correction.finalize import finalize_correction_draw
    from src.agent.correction.parse import correction_target
    verified_window_inputs = None
    if geom.schema_version == "3" and out_dir is not None:
        from src.agent.correction.window_sources import build_verified_window_inputs_from_run

        verified_window_inputs = build_verified_window_inputs_from_run(
            producer_draw=geom,
            run_dir=out_dir,
            reading_dir=vector_dir,
        )
    n_corr_before = len(geom.corrections)
    finalized = finalize_correction_draw(
        geom,
        vector_dir=vector_dir,
        target=correction_target(capability_profile),
        verified_window_inputs=verified_window_inputs,
    )
    geom = finalized.geom
    logger.info(
        "core: deterministic snap added {} correction(s), {} unsupported",
        len(geom.corrections) - n_corr_before,
        len(geom.unsupported),
    )
    if s1 is not None:
        (s1 / "correction_geometry_snapped.json").write_text(
            geom.model_dump_json(indent=2), encoding="utf-8"
        )
        (s1 / "corrections.json").write_text(
            json.dumps(
                {
                    "corrections": geom.corrections,
                    "conflicts": geom.conflicts,
                    "unsupported": geom.unsupported,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    from src.validator.checks.correction import check_correction

    correction_report = check_correction(
        geom,
        window_host_proof=finalized.window_host_claims,
        window_evidence=finalized.window_evidence_ledger,
        expected_zone_total=(
            expected_zone_total_from_testdata(parsed_testdata)
            if parsed_testdata is not None
            else None
        ),
        raw_geom=None,
        relied_on_testdata=bool(parsed_testdata),
        capability_profile=capability_profile,
        run_profile=run_profile,
        evidence_debt=evidence_debt,
        reading_views=reading_views,
    )
    _gate_self_check_report(
        stage_name="1_correction",
        report=correction_report,
        stage_dir=s1,
        filename="correction_checks.json",
        run_profile=run_profile,
    )

    # ----------------------------------------------------------------- #
    # E4 (C2 E4-output-contract spec v2 §3.2bis/§11 steps 1-4): build the
    # verified accepted-correction identity, and for a v3/orthogonal_polygon
    # draw, run orientation resolution unconditionally (this batch's only
    # producer is the trusted-empty evidence-set artifact — B-O does not add
    # any total-plan/north-arrow evidence collector; see spec §0.3). v1/v2
    # rectangular corrections have no orientation concept at all and are
    # verified straight through (they derive `world_legacy` at S5).
    #
    # BO-CR2 (review-ask #1 REJECT): a blocking gate① correction leaves this
    # run with NO accepted identity to bind a contract to — a new E4 run
    # without a contract is a HARD failure under every profile; there is no
    # fall-back to pre-E4 contract-less assembly.
    # ----------------------------------------------------------------- #
    if correction_report.blocking():
        raise RuntimeError(
            "1_correction gate① reported blocking result(s) — no accepted correction "
            "identity exists to bind the E4 output-coordinate contract, and a new run "
            "may not assemble without one (E4-oc v2 §3.4): "
            + "; ".join(f"{r.check_id}: {r.message}" for r in correction_report.blocking())
        )

    from src.agent.correction.feature_state import (
        FeatureStatesArtifactV1,
        derive_feature_state_claims,
    )
    from src.agent.correction.artifact_serialization import serialize_correction_output
    from src.agent.output_coordinates import (
        sha256_bytes,
        verify_integrated_gate1_correction,
    )

    if geom.schema_version == "3":
        from src.agent.correction.orientation import resolve_orientation_from_run_dir
        from src.agent.execution.run_config import load_run_config

        pre_raw = serialize_correction_output(geom)
        pre_hash = sha256_bytes(pre_raw)
        pre_claims = derive_feature_state_claims(correction_target(capability_profile), geom)
        pre_resolver_bytes = None
        pre_hosts_bytes = None
        if finalized.verified_window_resolver_inputs is not None:
            from src.agent.correction.window_host import build_window_hosts_artifact
            from src.agent.correction.window_sources import serialize_window_resolver_inputs_artifact

            assert finalized.prepared_candidate_identity is not None
            assert finalized.window_host_claims is not None
            assert finalized.window_evidence_ledger is not None
            pre_resolver_bytes = serialize_window_resolver_inputs_artifact(
                finalized.verified_window_resolver_inputs
            )
            pre_hosts_bytes = build_window_hosts_artifact(
                output_sha256=finalized.prepared_candidate_identity.output_sha256,
                claims=finalized.window_host_claims,
                evidence=finalized.window_evidence_ledger,
            ).model_dump_json(indent=2).encode("utf-8")
        pre_verified = verify_integrated_gate1_correction(
            raw_output_bytes=pre_raw,
            correction_report=correction_report,
            feature_states=FeatureStatesArtifactV1(output_sha256=pre_hash, claims=pre_claims),
            raw_window_resolver_inputs_bytes=pre_resolver_bytes,
            raw_window_hosts_bytes=pre_hosts_bytes,
        )

        # BO-CR3: completion mode comes from the run's REAL configuration
        # (run_config.yaml `orientation.completion_mode`, default prior_fill),
        # and the evidence set is a content-addressed on-disk artifact — the
        # canonical empty set is explicitly materialized, then re-loaded and
        # hash-verified before resolution. Nothing here is an in-memory
        # pipeline literal.
        if s1 is not None:
            correction_dir = s1
        else:
            import tempfile

            correction_dir = Path(tempfile.mkdtemp(prefix="e4_orientation_"))
        run_config_dir = out_dir if out_dir is not None else correction_dir
        run_cfg = load_run_config(run_config_dir)
        orientation_result, _orientation_artifacts = resolve_orientation_from_run_dir(
            correction_dir=correction_dir,
            base=pre_verified,
            completion_mode=run_cfg.orientation_completion_mode,
            capability_profile=capability_profile,
        )
        geom = orientation_result.geom
        logger.info(
            "1_correction (E4): orientation resolved via {} -> north_axis={}deg "
            "(completion_mode={})",
            orientation_result.audit_payload["orientation"]["resolution_kind"],
            geom.north_axis.value_deg,
            run_cfg.orientation_completion_mode,
        )
        if s1 is not None:
            (s1 / "correction_geometry_snapped.json").write_text(
                geom.model_dump_json(indent=2), encoding="utf-8",
            )
            (s1 / "corrections.json").write_text(
                json.dumps(orientation_result.audit_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            (s1 / "orientation_audit.json").write_text(
                json.dumps(orientation_result.audit_payload["orientation"], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        enriched_raw = serialize_correction_output(geom)
        enriched_hash = sha256_bytes(enriched_raw)
        enriched_resolver_bytes = None
        enriched_hosts_bytes = None
        if orientation_result.verified_window_resolver_inputs is not None:
            from src.agent.correction.window_host import build_window_hosts_artifact

            assert orientation_result.prepared_candidate_identity is not None
            assert orientation_result.window_host_claims is not None
            assert orientation_result.window_evidence_ledger is not None
            enriched_resolver_bytes = orientation_result.verified_window_resolver_inputs.raw_inputs_bytes
            enriched_hosts_bytes = build_window_hosts_artifact(
                output_sha256=orientation_result.prepared_candidate_identity.output_sha256,
                claims=orientation_result.window_host_claims,
                evidence=orientation_result.window_evidence_ledger,
            ).model_dump_json(indent=2).encode("utf-8")
        verified_correction = verify_integrated_gate1_correction(
            raw_output_bytes=enriched_raw,
            correction_report=correction_report,
            feature_states=FeatureStatesArtifactV1(
                output_sha256=enriched_hash, claims=orientation_result.feature_state_claims,
            ),
            raw_window_resolver_inputs_bytes=enriched_resolver_bytes,
            raw_window_hosts_bytes=enriched_hosts_bytes,
        )
    else:
        raw_bytes = serialize_correction_output(geom)
        claims = derive_feature_state_claims(correction_target(capability_profile), geom)
        verified_correction = verify_integrated_gate1_correction(
            raw_output_bytes=raw_bytes, correction_report=correction_report,
            feature_states=FeatureStatesArtifactV1(output_sha256=sha256_bytes(raw_bytes), claims=claims),
        )

    # Deterministic geometry kernel (2_modelling -> 3_split_pairing). This geometry
    # is authoritative; we serialize it into the geometry specs.
    s2 = _stage("2_modelling")
    s3 = _stage("3_split_pairing")
    bg, kernel_issues = materialize_kernel_geometry(
        geom,
        s2,
        capability_profile=capability_profile,
        window_host_proof=verified_correction.window_host_proof,
    )
    if kernel_issues:
        hint = "" if s2 is None else "; see 2_modelling/kernel_gate_report.json"
        logger.warning(
            "kernel: {} InterZone gate issue(s) on the deterministic build "
            "(advisory — the downstream gate re-checks the assembled IDF{})",
            len(kernel_issues),
            hint,
        )

    if bg is None:
        # Hard kernel error: the geometry is required and deterministic, so a
        # build failure is a bug to fix, not something to paper over with an LLM.
        where = " (see 2_modelling/kernel_gate_report.json)" if s2 is not None else ""
        raise RuntimeError(
            f"geometry kernel build failed{where}: " + "; ".join(kernel_issues)
        )

    from src.validator.checks.kernel import check_kernel

    kernel_report = check_kernel(
        bg,
        window_host_proof=verified_correction.window_host_proof,
        capability_profile=capability_profile,
        interzone_issues=kernel_issues,
        run_profile=run_profile,
    )
    _gate_self_check_report(
        stage_name="2_modelling",
        report=kernel_report,
        stage_dir=s2,
        filename="kernel_checks.json",
        run_profile=run_profile,
    )

    # 3_split_pairing (serialization): kernel geometry -> specs text.
    from src.agent.geometry.specs import geometry_specs_markdown, serialize_geometry
    from src.agent.intakeoutput import assemble_intake_output

    zone_specs, surface_specs, fenestration_specs, used_constructions = serialize_geometry(
        bg, frame_label="building_axis" if geom.schema_version == "3" else "world",
    )
    if s3 is not None:
        (s3 / "geometry_specs.md").write_text(
            geometry_specs_markdown(
                zone_specs,
                surface_specs,
                fenestration_specs,
                geometry_contract=bg.geometry_contract,
            ),
            encoding="utf-8",
        )

    # 4_mep (LLM): author the 8 non-geometry fields against the zone list +
    # required construction set.
    logger.info(
        "4_mep: authoring non-geometry specs ({} zones, {} constructions)",
        len(dict.fromkeys(bg.zones)),
        len(used_constructions),
    )
    s4 = _stage("4_mep")
    mep = run_mep(
        zone_specs, used_constructions, testdata_text, out_dir=s4, feedback=feedback
    )

    from src.validator.checks.mep import check_mep

    mep_report = check_mep(
        json.loads(mep.model_dump_json()),
        used_constructions=used_constructions or None,
        zone_names=set(dict.fromkeys(bg.zones)) or None,
        testdata=parsed_testdata,
        capability_profile=capability_profile,
    )
    _gate_self_check_report(
        stage_name="4_mep",
        report=mep_report,
        stage_dir=s4,
        filename="mep_checks.json",
        run_profile=run_profile,
    )

    # 5_intakeoutput (assembly): stitch + deterministic contract check.
    #
    # E4 (spec §3.5/§11 step 6): when this run has a verified accepted
    # correction (gate① clean — see the E4 block above), assemble through
    # `assemble_intake_artifacts` so the final Building.North Axis is the
    # unconditional S5 override from the derived OutputCoordinateContract
    # (0.0/world_legacy for v1/v2, theta/relative_north_axis for v3).
    # `verified_correction is None` (a blocking-gate① exploratory edge case)
    # falls through to the exact pre-E4 call — no output_coordinates at all.
    # BO-CR2: every integrated run reaching S5 has a verified correction (the
    # gate above raised otherwise) — there is no contract-less assembly path.
    from src.agent.output_coordinates import (
        assemble_intake_artifacts,
        build_assembly_coordinate_audit,
        build_output_coordinate_snapshot,
        canonical_json_bytes,
    )

    coordinate_snapshot = build_output_coordinate_snapshot(bg)
    bundle = assemble_intake_artifacts(
        zone_specs=zone_specs,
        surface_specs=surface_specs,
        fenestration_specs=fenestration_specs,
        mep=mep,
        correction=verified_correction,
        coordinate_snapshot=coordinate_snapshot,
    )
    intake = bundle.intake
    output_coordinate_contract = bundle.output_coordinates
    from src.validator.checks.assembly import check_assembly

    s5 = _stage("5_intakeoutput")
    assembly_report = check_assembly(
        intake,
        used_constructions,
        capability_profile=capability_profile,
        run_profile=run_profile,
    )
    if s5 is not None:
        (s5 / "assembly_checks.json").write_text(
            assembly_report.model_dump_json(indent=2), encoding="utf-8"
        )
    contract_issues = []
    for result in assembly_report.results:
        if result.check_id != "assembly.contract_backstop":
            continue
        issues = result.evidence.get("issues")
        if isinstance(issues, list):
            contract_issues.extend(issues)
    if contract_issues:
        if s5 is not None:
            (s5 / "contract_issues.json").write_text(
                json.dumps(contract_issues, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        raise RuntimeError(
            "5_intakeoutput contract check failed (4_mep omitted geometry-"
            "referenced definitions):\n- " + "\n- ".join(contract_issues)
        )
    _gate_self_check_report(
        stage_name="5_intakeoutput",
        report=assembly_report,
        stage_dir=None,
        filename="assembly_checks.json",
        run_profile=run_profile,
    )

    if s5 is not None:
        (s5 / "intake_output.json").write_text(
            intake.model_dump_json(indent=2, by_alias=False), encoding="utf-8"
        )
        logger.success("5_intakeoutput: wrote {}", s5 / "intake_output.json")
        (s5 / "output_coordinate_contract.json").write_text(
            output_coordinate_contract.model_dump_json(indent=2), encoding="utf-8",
        )
        snapshot_bytes = canonical_json_bytes(coordinate_snapshot)
        (s5 / "output_coordinate_snapshot.json").write_bytes(snapshot_bytes)
        # BO-CR7: integrated S5 also files the strict assembly coordinate
        # audit (stepwise files it as the accepted attempt's audit.json).
        assembly_audit = build_assembly_coordinate_audit(
            verified=verified_correction,
            contract=output_coordinate_contract,
            snapshot_bytes=snapshot_bytes,
            mep_placeholder_north_axis=float(mep.building.north_axis),
            final_building_north_axis=float(intake.building.north_axis),
        )
        (s5 / "assembly_coordinate_audit.json").write_text(
            assembly_audit.model_dump_json(indent=2), encoding="utf-8",
        )
    return intake, bundle
