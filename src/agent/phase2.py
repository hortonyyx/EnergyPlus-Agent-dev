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
from typing import TYPE_CHECKING

from loguru import logger
from openai import OpenAI

from src.agent._share import ensure_schema_initialized
from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.llm import load_llm_section
from src.agent.state import IntakeOutput

if TYPE_CHECKING:
    from src.agent.geometry.modelling import BuildingGeometry

_SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "intake_pipeline"
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
    """LEGACY (pre-Step-5): one LLM call authoring the WHOLE IntakeOutput incl.
    geometry. Superseded by the deterministic-geometry + run_mep + assembly flow
    in run_phase2. Kept callable as a one-line rollback; **remove after the
    Step-8 e2e validates the new flow.**"""
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
# 4_MEP — physical-information authoring (LLM): non-geometry specs only
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
        "You are running stage 4_MEP of a two-step EnergyPlus intake. The geometry "
        "is ALREADY built and serialized deterministically — you author ONLY the "
        "non-geometry specs and attach them by name. Do NOT produce zone_specs / "
        "surface_specs / fenestration_specs.\n\n"
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
        _section("mep"), system_prompt, human, out_dir=out_dir, prefix="mep"
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
    geom: CorrectedGeometry, out_dir: Path | None
) -> tuple["BuildingGeometry | None", list[str]]:
    """Run the deterministic geometry kernel (2_modelling -> 3_split_pairing) on
    the snapped CorrectedGeometry and materialize the result + a gate report.

    Returns `(building_geometry, gate_issues)`. The geometry is the authoritative
    geometry the rest of phase 2 serializes (fork a); `run_phase2` reuses this
    object — it does NOT build a second time. On a hard kernel error, returns
    `(None, [err])` so `run_phase2` can fall back to the legacy phase2b. The
    InterZone gate issues are advisory here (the downstream gate re-checks the
    assembled IDF). Never raises.
    """
    # Lazy imports: keep the kernel (shapely/eppy) off the hot path for callers
    # that never reach here, mirroring the run_phase2 import discipline.
    try:
        from src.agent.geometry import build_geometry
        from src.agent.geometry.to_idf import building_to_idf
        from src.validator.interzone import validate_interzone_surface_pairs

        # build_geometry is read-only on `geom` (it constructs new ZoneVolumes /
        # polygons), so the same `geom` is safe to hand to later stages.
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
        return None, err

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
    return bg, issues


def run_phase2(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
) -> IntakeOutput:
    """Staged phase 2: 2a correction -> deterministic core -> deterministic
    geometry kernel -> 4_MEP (LLM) -> 5_intakeoutput assembly.

    Geometry is deterministic (fork a): the kernel builds + the serializer emits
    zone/surface/fenestration specs; 4_MEP authors only the 8 non-geometry fields;
    assembly stitches them and runs a contract check. Falls back to the legacy
    whole-output phase2b only on a hard kernel build error.

    When `out_dir` is given, artifacts are filed into stage-numbered subdirs that
    mirror the 0–5 pipeline:
      out_dir/1_correction/    phase2a_geometry.json (pre-snap) +
                               phase2a_geometry_snapped.json (post core) +
                               corrections.json + phase2a raw/thinking
      out_dir/2_modelling/     building_geometry.json + kernel_gate_report.json
      out_dir/3_split_pairing/ geometry_specs.md (serialized cut+paired specs)
      out_dir/4_mep/           mep_output.json + mep raw/thinking
      out_dir/5_intakeoutput/  intake_output.json (final) + contract_issues.json
    Signature unchanged so intake_node / CLI callers do not change. `feedback`
    is routed to both phase 2a (geometry) and 4_MEP (physics) repair.
    """
    ensure_schema_initialized()

    def _stage(name: str) -> Path | None:
        if out_dir is None:
            return None
        d = out_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    s1 = _stage("1_correction")
    s2 = _stage("2_modelling")
    s3 = _stage("3_split_pairing")
    s4 = _stage("4_mep")
    s5 = _stage("5_intakeoutput")

    logger.info("phase2a: correction from {}", vector_dir)
    geom = run_phase2a(vector_dir, testdata_text, out_dir=s1, feedback=feedback)

    n_corr_before = len(geom.corrections)
    geom = apply_deterministic_core(geom)
    logger.info(
        "phase2 core: deterministic snap added {} correction(s), {} unsupported",
        len(geom.corrections) - n_corr_before,
        len(geom.unsupported),
    )
    if s1 is not None:
        (s1 / "phase2a_geometry_snapped.json").write_text(
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

    # Deterministic geometry kernel (2_modelling -> 3_split_pairing). Under fork
    # (a) this geometry is authoritative; we serialize it into the geometry specs.
    bg, kernel_issues = materialize_kernel_geometry(geom, s2)
    if kernel_issues:
        hint = "" if s2 is None else "; see 2_modelling/kernel_gate_report.json"
        logger.warning(
            "phase2 kernel: {} InterZone gate issue(s) on the deterministic build "
            "(advisory — the downstream gate re-checks the assembled IDF{})",
            len(kernel_issues),
            hint,
        )

    if bg is None:
        # Hard kernel error: fall back to the legacy whole-output phase2b so the
        # run still produces an IntakeOutput (one-line rollback path).
        logger.warning("phase2: kernel build failed; falling back to legacy phase2b")
        return run_phase2b(geom, testdata_text, out_dir=s5, feedback=feedback)

    # 3_split_pairing (serialization): kernel geometry -> specs text.
    from src.agent.geometry.specs import serialize_geometry
    from src.agent.intakeoutput import assemble_intake_output, validate_contract

    zone_specs, surface_specs, fenestration_specs, used_constructions = (
        serialize_geometry(bg)
    )
    if s3 is not None:
        (s3 / "geometry_specs.md").write_text(
            f"# zone_specs\n\n{zone_specs}\n\n# surface_specs\n\n{surface_specs}\n\n"
            f"# fenestration_specs\n\n{fenestration_specs}\n",
            encoding="utf-8",
        )

    # 4_MEP (LLM): author the 8 non-geometry fields against the zone list +
    # required construction set.
    logger.info(
        "4_mep: authoring non-geometry specs ({} zones, {} constructions)",
        len(dict.fromkeys(bg.zones)),
        len(used_constructions),
    )
    mep = run_mep(
        zone_specs, used_constructions, testdata_text, out_dir=s4, feedback=feedback
    )

    # 5_intakeoutput (assembly): stitch + deterministic contract check.
    intake = assemble_intake_output(
        zone_specs=zone_specs,
        surface_specs=surface_specs,
        fenestration_specs=fenestration_specs,
        mep=mep,
    )
    contract_issues = validate_contract(intake, used_constructions)
    if contract_issues:
        if s5 is not None:
            (s5 / "contract_issues.json").write_text(
                json.dumps(contract_issues, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        raise RuntimeError(
            "5_intakeoutput contract check failed (4_MEP omitted geometry-"
            "referenced definitions):\n- " + "\n- ".join(contract_issues)
        )

    if s5 is not None:
        (s5 / "intake_output.json").write_text(
            intake.model_dump_json(indent=2, by_alias=False), encoding="utf-8"
        )
        logger.success("5_intakeoutput: wrote {}", s5 / "intake_output.json")
    return intake
