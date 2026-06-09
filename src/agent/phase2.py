"""Phase 2 of the two-step intake: vector JSON -> IntakeOutput.

Phase 1 (image -> semantic vector JSON) is image-bound perception; phase 2 is
image-blind topology/reasoning. Phase 2 is itself decoupled into three stages so
each is independently swappable and the intermediate is verifiable / diffable:

  phase2a  CORRECTION (LLM)   phase-1 vectors + PartA docs -> CorrectedGeometry
  core     DETERMINISTIC      canonical axis snap + sliver guard (code, no LLM)
  phase2b  MODELING (LLM)     CorrectedGeometry -> IntakeOutput

The CorrectedGeometry checkpoint is materialized (phase2a_geometry*.json) so the
correction error budget is separable from the modeling error budget, and so the
deterministic core can guarantee no cross-floor sliver reaches EnergyPlus.

This module is the single implementation of phase 2. It is called from:
  - `intake_node` (the main graph, two-step flow), and
  - `Tool_scripts/run_phase2_deepseek.py` (thin standalone CLI wrapper).

Per-stage model config: `intake_phase2a` / `intake_phase2b` in llm.yaml if present,
else fall back to `intake_phase2` (so "model switching has one home" still holds).
Why a raw OpenAI client instead of langchain: single-shot calls with DeepSeek
thinking on; langchain's structured-output burns tokens on reasoning_content and
never emits the tool call, so we ask for JSON-only content and parse it ourselves.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from loguru import logger
from openai import OpenAI

from src.agent._share import ensure_schema_initialized
from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.llm import load_llm_section
from src.agent.state import IntakeOutput

_SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "energyplus_mcp_twostep"
_PARTA_DIR = _SKILL_DIR / "1_correction"
_PARTA_DOCS = [
    "README.md",
    "A0_contract.md",
    "A1_coordinate_normalization.md",
    "A2_regularization.md",
    "A3_arbitration.md",
    "A4_priors.md",
]

_PLAN_RE = re.compile(r"^(\d+)f_view\.json$", flags=re.IGNORECASE)
_JS_CONCAT_RE = re.compile(r'"\s*\+\s*\n\s*"', flags=re.MULTILINE)


def discover_phase1_files(vector_dir: Path) -> list[str]:
    """Scan a phase-1 vector dir for ALL vector JSONs, in a stable order.

    Order: numeric floor plans (by floor number) -> facade elevations ->
    supplementary / section / other vector JSONs. `phase1_summary.md` is read
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


def _load_partA() -> str:
    return "\n\n".join(
        f"----- 1_correction/{name} -----\n{_read(_PARTA_DIR / name)}"
        for name in _PARTA_DOCS
    )


def _section(stage: str) -> dict:
    """Load `intake_<stage>` if present, else fall back to `intake_phase2`."""
    try:
        return load_llm_section(f"intake_{stage}")
    except Exception:
        return load_llm_section("intake_phase2")


def _call_json_llm(
    section: dict, system_prompt: str, human: str, *, out_dir: Path | None, prefix: str
) -> dict:
    """One JSON-only LLM call; return the parsed dict. Saves raw/thinking artifacts."""
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
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human},
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
        "{}: finish_reason={} usage={}",
        prefix,
        finish_reason,
        {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
        },
    )
    if out_dir is not None:
        if reasoning:
            (out_dir / f"{prefix}_thinking.txt").write_text(reasoning, encoding="utf-8")
        (out_dir / f"{prefix}_raw.txt").write_text(content, encoding="utf-8")
    if finish_reason == "length":
        logger.warning("{}: hit max_tokens — response likely truncated", prefix)
    if not content.strip():
        raise RuntimeError(f"{prefix}: empty content (finish_reason={finish_reason})")

    payload = _extract_json(content)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        if out_dir is not None:
            (out_dir / f"{prefix}_parse_error.txt").write_text(
                f"json decode: {e}\nfirst 500 chars:\n{payload[:500]}", encoding="utf-8"
            )
        raise RuntimeError(f"{prefix}: JSON decode error: {e}") from e


# --------------------------------------------------------------------------- #
# phase 2a — correction (LLM) -> CorrectedGeometry
# --------------------------------------------------------------------------- #
def _build_phase2a_messages(
    vector_dir: Path, testdata_text: str, *, feedback: str | None = None
) -> tuple[str, str]:
    partA = _load_partA()
    phase1_guide = _read(_SKILL_DIR / "0_reading" / "guide.md")
    phase1_pens = _read(_SKILL_DIR / "0_reading" / "pen_library.md")
    summary = _read(vector_dir / "phase1_summary.md")
    geom_schema = json.dumps(
        CorrectedGeometry.model_json_schema(), indent=2, ensure_ascii=False
    )

    system_prompt = (
        "You are running phase 2a (CORRECTION) of a two-step EnergyPlus intake. "
        "Phase 1 (image -> semantic vector JSON) is done; you DO NOT see drawings. "
        "Apply the PartA correction layer to the phase-1 primitives and emit a "
        "single CorrectedGeometry JSON object: world-frame, wall-centerline, "
        "self-consistent room cells + windows + per-floor z, plus an audit.\n\n"
        "Do the correction (A1 -> A2 -> A3, priors via A4 under A0/A3 gating): put "
        "every coordinate in one world frame at wall CENTERLINE; reconcile the "
        "z-stack; ARBITRATE stroke-vs-dimension conflicts (trust dimensions; make "
        "each elevation window fall entirely within one room); complete missing "
        "values; log every material change in `corrections`, unresolved ambiguity "
        "in `conflicts`, and anything unsafe to fix in `unsupported`.\n\n"
        "Each room is one rectangular cell {id, role, x:[min,max], y:[min,max]}. "
        "Each floor gives z_floor + ceiling_height. Each window gives facade, "
        "along-facade span [min,max], z [sill,head] (absolute world z), and the "
        "room id it belongs to. Do not output zones/surfaces — only the corrected "
        "geometry primitives.\n\n"
        "OUTPUT FORMAT (strict): ONLY the CorrectedGeometry JSON object, starting "
        "with `{` and ending with `}`. No markdown, no prose.\n\n"
        "===== BEGIN CorrectedGeometry JSON SCHEMA =====\n"
        f"{geom_schema}\n"
        "===== END CorrectedGeometry JSON SCHEMA =====\n\n"
        "===== BEGIN RULE DOCUMENT: PartA-correction =====\n"
        f"{partA}\n"
        "===== END RULE DOCUMENT: PartA-correction =====\n\n"
        "===== BEGIN REFERENCE: phase1/guide.md =====\n"
        f"{phase1_guide}\n"
        "===== END REFERENCE: phase1/guide.md =====\n\n"
        "===== BEGIN REFERENCE: phase1/pen_library.md =====\n"
        f"{phase1_pens}\n"
        "===== END REFERENCE: phase1/pen_library.md =====\n\n"
        "===== BEGIN REFERENCE: phase1_summary.md =====\n"
        f"{summary}\n"
        "===== END REFERENCE: phase1_summary.md =====\n"
    )

    chunks = [
        "Project metadata (testdata_prompt.json):\n```json\n" + testdata_text + "\n```\n"
    ]
    for fname in discover_phase1_files(vector_dir):
        chunks.append(f"\n[phase1 vector] {fname}:\n```json\n{_read(vector_dir / fname)}\n```\n")
    if feedback:
        chunks.append(
            "\n\n=== Geometry feedback from a previous attempt — fix these ===\n"
            f"{feedback}\nAddress every item while following PartA rules.\n"
        )
    chunks.append(
        "\nApply the PartA correction now and output ONLY the CorrectedGeometry "
        "JSON object. Use the facade translation formulas in phase1_summary.md §3 "
        "verbatim. Enumerate every room cell and window explicitly."
    )
    return system_prompt, "".join(chunks)


def run_phase2a(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
) -> CorrectedGeometry:
    ensure_schema_initialized()  # safe for standalone stage calls (idempotent)
    system_prompt, human = _build_phase2a_messages(
        vector_dir, testdata_text, feedback=feedback
    )
    parsed = _call_json_llm(
        _section("phase2a"), system_prompt, human, out_dir=out_dir, prefix="phase2a"
    )
    try:
        geom = CorrectedGeometry.model_validate(parsed)
    except Exception as e:
        if out_dir is not None:
            (out_dir / "phase2a_geometry_unvalidated.json").write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        raise RuntimeError(f"phase2a: CorrectedGeometry validation error: {e}") from e
    if out_dir is not None:
        (out_dir / "phase2a_geometry.json").write_text(
            geom.model_dump_json(indent=2), encoding="utf-8"
        )
    return geom


# --------------------------------------------------------------------------- #
# phase 2b — modeling (LLM): CorrectedGeometry -> IntakeOutput
# --------------------------------------------------------------------------- #
def _build_phase2b_messages(
    geom: CorrectedGeometry, testdata_text: str, *, feedback: str | None = None
) -> tuple[str, str]:
    rules = _read(_SKILL_DIR / "phase2" / "rules.md")
    mep = _read(_SKILL_DIR / "4_mep" / "mep.md")
    intake_schema = json.dumps(
        IntakeOutput.model_json_schema(), indent=2, ensure_ascii=False
    )
    geom_json = geom.model_dump_json(indent=2)

    system_prompt = (
        "You are running phase 2b (MODELING) of a two-step EnergyPlus intake. The "
        "geometry has ALREADY been corrected and snapped (deterministic). Build the "
        "IntakeOutput from it. The CorrectedGeometry coordinates are AUTHORITATIVE: "
        "do NOT re-derive, re-snap, or 'improve' coordinates — use the cells, "
        "windows, and per-floor z exactly as given.\n\n"
        "Mapping: each cell = one thermal zone (x/y from the cell, z_floor + "
        "ceiling_height from its floor). For each zone emit 4 walls + floor + "
        "ceiling; a surface on the footprint boundary is Outdoors, otherwise it is "
        "an interzone Surface with the adjacent zone named. Enumerate cross-floor "
        "floor/ceiling split-pairing from cell overlap between stacked floors "
        "(no templates). Attach each window to its room's exterior wall using the "
        "given span + z. Produce the non-geometry specs (material / construction / "
        "schedule / lights / people / hvac / site_location / building) from the "
        "testdata + rules.md.\n\n"
        "OUTPUT FORMAT (strict): ONLY the IntakeOutput JSON object, `{`..`}`, no "
        "markdown, no prose.\n\n"
        "===== BEGIN IntakeOutput JSON SCHEMA =====\n"
        f"{intake_schema}\n"
        "===== END IntakeOutput JSON SCHEMA =====\n\n"
        "===== BEGIN RULE DOCUMENT: phase2/rules.md =====\n"
        f"{rules}\n"
        "===== END RULE DOCUMENT: phase2/rules.md =====\n\n"
        "===== BEGIN REFERENCE: 4_mep/mep.md (default loads/schedules/HVAC) =====\n"
        f"{mep}\n"
        "===== END REFERENCE: 4_mep/mep.md =====\n\n"
        "===== BEGIN CORRECTED GEOMETRY (authoritative — build from this) =====\n"
        f"{geom_json}\n"
        "===== END CORRECTED GEOMETRY =====\n"
    )

    chunks = [
        "Project metadata (testdata_prompt.json):\n```json\n" + testdata_text + "\n```\n"
    ]
    if feedback:
        chunks.append(
            "\n\n=== Validation feedback from a previous attempt — fix these ===\n"
            f"{feedback}\n"
        )
    chunks.append(
        "\nProduce the IntakeOutput JSON now from the corrected geometry. Follow "
        "phase2/rules.md Step 1->7 derivation order and naming rules. Enumerate "
        "every zone / surface / split-pairing / fenestration explicitly — no "
        "templates, no Floor_N_* shorthand. Output ONLY the JSON object."
    )
    return system_prompt, "".join(chunks)


def run_phase2b(
    geom: CorrectedGeometry,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
) -> IntakeOutput:
    ensure_schema_initialized()  # safe for standalone stage calls (idempotent)
    system_prompt, human = _build_phase2b_messages(
        geom, testdata_text, feedback=feedback
    )
    parsed = _call_json_llm(
        _section("phase2b"), system_prompt, human, out_dir=out_dir, prefix="phase2b"
    )
    try:
        result = IntakeOutput.model_validate(parsed)
    except Exception as e:
        if out_dir is not None:
            (out_dir / "intake_output_unvalidated.json").write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            (out_dir / "parse_error.txt").write_text(str(e), encoding="utf-8")
        raise RuntimeError(f"phase2b: Pydantic validation error: {e}") from e
    if out_dir is not None:
        (out_dir / "intake_output.json").write_text(
            result.model_dump_json(indent=2, by_alias=False), encoding="utf-8"
        )
        logger.success("phase2b: wrote {}", out_dir / "intake_output.json")
    return result


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #
def materialize_kernel_geometry(
    geom: CorrectedGeometry, out_dir: Path | None
) -> list[str]:
    """Run the deterministic geometry kernel (2_modelling -> 3_split_pairing) on
    the snapped CorrectedGeometry and materialize the result + a gate report.

    This is the Step-4 wiring: the kernel now runs on every real phase-2 pass,
    so its coverage is exercised on live phase-2a output and the InterZone gate
    gives an early, deterministic geometry signal. It is **advisory** here — the
    geometry it produces is not yet fed into the IntakeOutput (phase2b still
    authors geometry); how the kernel's surfaces become `surface_specs` is the
    Step-5 integration fork. Never raises: a kernel/gate failure must not break a
    run while phase2b remains authoritative.

    Returns the list of InterZone gate issues (empty = clean), or a single-item
    list describing why the kernel could not run.
    """
    # Lazy imports: keep the kernel (shapely/eppy) off the hot path for callers
    # that never reach here, mirroring the run_phase2 import discipline.
    try:
        from src.agent.geometry import build_geometry
        from src.agent.geometry.to_idf import building_to_idf
        from src.validator.interzone import validate_interzone_surface_pairs

        # build_geometry is read-only on `geom` (it constructs new ZoneVolumes /
        # polygons), so the same `geom` is safe to hand to phase2b afterwards.
        bg = build_geometry(geom)
        issues = validate_interzone_surface_pairs(building_to_idf(bg))
    except Exception as e:  # noqa: BLE001 — advisory stage, never fatal
        logger.warning("phase2 kernel: geometry build/gate failed: {}", e)
        err = [f"kernel-error: {type(e).__name__}: {e}"]
        if out_dir is not None:
            (out_dir / "kernel_gate_report.json").write_text(
                json.dumps({"gate_issues": err, "build_notes": []}, indent=2),
                encoding="utf-8",
            )
        return err

    logger.info(
        "phase2 kernel: {} zones, {} surfaces, {} windows; gate issues={} notes={}",
        len(dict.fromkeys(bg.zones)),
        len(bg.surfaces),
        len(bg.windows),
        len(issues),
        len(bg.notes),
    )
    if out_dir is not None:
        (out_dir / "building_geometry.json").write_text(
            json.dumps(
                {
                    "zones": list(dict.fromkeys(bg.zones)),
                    "surfaces": [
                        {
                            "name": s.name,
                            "zone": s.zone,
                            "type": s.stype,
                            "obc": s.obc,
                            "obc_obj": s.obc_obj,
                            "verts": [list(v) for v in s.verts],
                        }
                        for s in bg.surfaces
                    ],
                    "windows": [
                        {"name": w.name, "parent": w.parent,
                         "verts": [list(v) for v in w.verts]}
                        for w in bg.windows
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (out_dir / "kernel_gate_report.json").write_text(
            json.dumps(
                {"gate_issues": issues, "build_notes": bg.notes},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return issues


def run_phase2(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
) -> IntakeOutput:
    """Staged phase 2: 2a correction -> deterministic core -> 2b modeling.

    When `out_dir` is given, artifacts are filed by stage into two subdirs:
      out_dir/partA/   phase2a_geometry.json (pre-snap) + phase2a_geometry_snapped.json
                       (post core) + corrections.json (2a + core audit) + phase2a raw/thinking
                       + building_geometry.json + kernel_gate_report.json (Step-4
                       deterministic geometry kernel, advisory)
      out_dir/partB/   intake_output.json (final) + phase2b raw/thinking
    Signature unchanged so intake_node / CLI callers do not change. `feedback`
    is routed to phase 2a (geometry correction).
    """
    ensure_schema_initialized()
    partA = (out_dir / "partA") if out_dir is not None else None
    partB = (out_dir / "partB") if out_dir is not None else None
    if partA is not None:
        partA.mkdir(parents=True, exist_ok=True)
    if partB is not None:
        partB.mkdir(parents=True, exist_ok=True)

    logger.info("phase2a: correction from {}", vector_dir)
    geom = run_phase2a(vector_dir, testdata_text, out_dir=partA, feedback=feedback)

    n_corr_before = len(geom.corrections)
    geom = apply_deterministic_core(geom)
    logger.info(
        "phase2 core: deterministic snap added {} correction(s), {} unsupported",
        len(geom.corrections) - n_corr_before,
        len(geom.unsupported),
    )
    if partA is not None:
        (partA / "phase2a_geometry_snapped.json").write_text(
            geom.model_dump_json(indent=2), encoding="utf-8"
        )
        (partA / "corrections.json").write_text(
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

    # Step-4 wiring: run the deterministic geometry kernel on the snapped
    # geometry (advisory — phase2b still authors the geometry that ships).
    kernel_issues = materialize_kernel_geometry(geom, partA)
    if kernel_issues:
        hint = "" if partA is None else "; see partA/kernel_gate_report.json"
        logger.warning(
            "phase2 kernel: {} InterZone gate issue(s) on the deterministic build "
            "(advisory{})",
            len(kernel_issues),
            hint,
        )

    logger.info("phase2b: modeling from corrected geometry")
    return run_phase2b(geom, testdata_text, out_dir=partB)
