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
  - `Tool_scripts/run_pipeline_deepseek.py` (thin standalone CLI wrapper).

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
    """Load `intake_<stage>` if present, else fall back to `intake_correction`."""
    try:
        return load_llm_section(f"intake_{stage}")
    except Exception:
        return load_llm_section("intake_correction")


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
# 1_correction — correction (LLM) -> CorrectedGeometry
# --------------------------------------------------------------------------- #
def _build_correction_messages(
    vector_dir: Path, testdata_text: str, *, feedback: str | None = None
) -> tuple[str, str]:
    correction_docs = _load_correction_docs()
    reading_guide = _read(_SKILL_DIR / "0_reading" / "guide.md")
    reading_pens = _read(_SKILL_DIR / "0_reading" / "pen_library.md")
    summary = _read(vector_dir / "reading_summary.md")
    geom_schema = json.dumps(
        CorrectedGeometry.model_json_schema(), indent=2, ensure_ascii=False
    )

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
    for fname in discover_vector_files(vector_dir):
        chunks.append(f"\n[reading vector] {fname}:\n```json\n{_read(vector_dir / fname)}\n```\n")
    if feedback:
        chunks.append(
            "\n\n=== Geometry feedback from a previous attempt — fix these ===\n"
            f"{feedback}\nAddress every item while following the correction rules.\n"
        )
    chunks.append(
        "\nApply the correction now and output ONLY the CorrectedGeometry JSON "
        "object. Use the facade translation formulas in reading_summary.md §3 "
        "verbatim. Enumerate every room cell and window explicitly."
    )
    return system_prompt, "".join(chunks)


def run_correction(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
) -> CorrectedGeometry:
    ensure_schema_initialized()  # safe for standalone stage calls (idempotent)
    system_prompt, human = _build_correction_messages(
        vector_dir, testdata_text, feedback=feedback
    )
    parsed = _call_json_llm(
        _section("correction"), system_prompt, human, out_dir=out_dir, prefix="correction"
    )
    try:
        geom = CorrectedGeometry.model_validate(parsed)
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
        bg = build_geometry(geom)
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


def run_pipeline(
    vector_dir: Path,
    testdata_text: str,
    *,
    out_dir: Path | None = None,
    feedback: str | None = None,
) -> IntakeOutput:
    """Staged intake: 1_correction -> deterministic core -> deterministic geometry
    kernel (2_modelling + 3_split_pairing) -> 4_mep (LLM) -> 5_intakeoutput assembly.

    Geometry is deterministic: the kernel builds + the serializer emits
    zone/surface/fenestration specs; 4_mep authors only the 8 non-geometry fields;
    assembly stitches them and runs a contract check.

    When `out_dir` is given, artifacts are filed into stage-numbered subdirs that
    mirror the 0–5 pipeline:
      out_dir/1_correction/    correction_geometry.json (pre-snap) +
                               correction_geometry_snapped.json (post core) +
                               corrections.json + correction raw/thinking
      out_dir/2_modelling/     building_geometry.json + kernel_gate_report.json
      out_dir/3_split_pairing/ geometry_specs.md (serialized cut+paired specs)
      out_dir/4_mep/           mep_output.json + mep raw/thinking
      out_dir/5_intakeoutput/  intake_output.json (final) + contract_issues.json
    Signature unchanged so intake_node / CLI callers do not change. `feedback`
    is routed to both 1_correction (geometry) and 4_mep (physics) repair.
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

    logger.info("1_correction: correcting from {}", vector_dir)
    geom = run_correction(vector_dir, testdata_text, out_dir=s1, feedback=feedback)

    n_corr_before = len(geom.corrections)
    geom = apply_deterministic_core(geom)
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

    # Deterministic geometry kernel (2_modelling -> 3_split_pairing). This geometry
    # is authoritative; we serialize it into the geometry specs.
    bg, kernel_issues = materialize_kernel_geometry(geom, s2)
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

    # 4_mep (LLM): author the 8 non-geometry fields against the zone list +
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
            "5_intakeoutput contract check failed (4_mep omitted geometry-"
            "referenced definitions):\n- " + "\n- ".join(contract_issues)
        )

    if s5 is not None:
        (s5 / "intake_output.json").write_text(
            intake.model_dump_json(indent=2, by_alias=False), encoding="utf-8"
        )
        logger.success("5_intakeoutput: wrote {}", s5 / "intake_output.json")
    return intake
