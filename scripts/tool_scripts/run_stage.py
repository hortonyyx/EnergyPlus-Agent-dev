"""Stepwise judge-in-the-loop driver (backlog #1, 2026-06-19).

The main Agent (orchestrator + judge②) drives a case ONE stage at a time, so each
stage gets its own judge report and a failing stage STOPS the run (new_case_guide
§2 ideal). This CLI is the thin wiring around src/agent/execution/step_orchestrator:
it owns the real stage executors + gate① checks + visual renders + the judge
packet, while the orchestrator owns the decision logic.

Verbs (one stage / action per call — the Agent invokes them in order):

    run    <case> <run> <stage>        draw + gate① (+ blind resample on block) → stop
    judge  <case> <run> <stage> --verdict v.json   record the Agent's StageVerdict → classify
    resample <case> <run> <stage>      force a fresh blind draw (judge-driven), same budget
    approve-geometry <case> <run> --actor X --date ISO   record the human geometry confirm
    status <case> <run>                print the orchestration ledger

Stages: 0_reading 1_correction 2_modelling 3_split_pairing 4_mep 5_intakeoutput.
After 5_intakeoutput passes, run downstream + EP with the existing driver:
    python scripts/run_full_pipeline.py <case> --base-dir <bd> \
        --intake-from <run>/5_intakeoutput/intake_output.json
then `record_baseline.py <case> <run> --require-ep` for _run/baseline.json
and report/REPORT.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Be robust to CWD: make `import src...` work whether or not the package is
# installed editable (mirrors how the repo runs scripts from the root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.agent.execution import (  # noqa: E402
    RunManifest,
    RunPolicy,
    StageRunner,
    StageOutcome,
    StepStatus,
    approve_geometry,
    geometry_is_approved,
    invalidate,
    load_state,
    mark_geometry_approved,
    mark_review_approved,
    record_review,
    review_is_current,
    run_one_stage,
    submit_verdict,
    update_state,
    GEOMETRY_CHECKPOINT_STAGE,
)
from src.agent.execution.case_metadata import (  # noqa: E402
    dimensioned_view_names,
    expected_zone_total_from_testdata,
)
from src.agent.execution.policy import ConfirmationPolicy  # noqa: E402
from src.agent.execution.approval import GeometryApproval  # noqa: E402
from src.agent.execution.run_config import GradeConfig, RunConfig, load_run_config  # noqa: E402
from src.agent.judge.executor import rubric_for, run_judge  # noqa: E402
from src.agent.judge.verdict import StageVerdict  # noqa: E402
from src.agent.runner import load_intake_from, run_downstream_ep  # noqa: E402
from src.agent.state import AgentState  # noqa: E402
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus  # noqa: E402

_STAGES = ["0_reading", "1_correction", "2_modelling", "3_split_pairing",
           "4_mep", "5_intakeoutput"]
FLOW_EXIT_OK = 0
FLOW_EXIT_CHECKPOINT = 10
FLOW_EXIT_STOP = 20
FLOW_EXIT_EP_RECORD = 30


# --------------------------------------------------------------------------- #
# path + metadata resolution
# --------------------------------------------------------------------------- #
def _resolve(base_dir: str, case: str, run: str):
    case_dir = Path(base_dir) / case
    run_dir = case_dir / run
    td = case_dir / "case_data" / "testdata_prompt.json"
    if not td.exists():
        td = case_dir / "testdata_prompt.json"
    return case_dir, run_dir, td


def _expected_zone_total(testdata_path: Path) -> int | None:
    if not testdata_path.exists():
        return None
    try:
        data = json.loads(testdata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return expected_zone_total_from_testdata(data) if isinstance(data, dict) else None


# --------------------------------------------------------------------------- #
# stage executors — each returns (output_obj, gate①_report)
# --------------------------------------------------------------------------- #
def _draw_reading(run_dir: Path, policy: RunPolicy, dimensioned_views: set[str]):
    """0_reading is MANUAL: validate the already-produced view JSONs (no LLM)."""
    from src.agent.reading import load_reading_view
    from src.validator.checks.reading import check_reading_view

    rdir = run_dir / "0_reading"
    views = sorted(rdir.glob("*_view.json"))
    rep = CheckReport(
        stage="0_reading",
        capability_profile=policy.capability_profile,
        run_profile=policy.run_profile,
    )
    if not views:
        rep.add("reading.present", CheckStatus.ERROR, CheckLayer.INVARIANT,
                message="no 0_reading/*_view.json found — produce reading first")
        return {}, rep
    out: dict = {}
    for vj in views:
        view = load_reading_view(vj)
        out[vj.stem] = json.loads(vj.read_text(encoding="utf-8"))
        sub = check_reading_view(
            view,
            capability_profile=policy.capability_profile,
            run_profile=policy.run_profile,
            view_metadata={"dimensioned": vj.stem in dimensioned_views},
        )
        for r in sub.results:  # merge per-view results under one stage report
            rep.results.append(r.model_copy(update={"check_id": f"{vj.stem}.{r.check_id}"}))
    return out, rep


def _draw_correction(
    run_dir: Path,
    testdata_text: str,
    expected_zones,
    relied,
    policy: RunPolicy,
):
    from src.agent.correction.deterministic import apply_deterministic_core
    from src.agent.execution.evidence_preflight import load_evidence_debt
    from src.agent.pipeline import (
        _reading_window_stroke_count,
        _schema_only_correction_validator,
        correction_draw_issues,
        run_correction,
    )
    from src.validator.checks.correction import check_correction

    s1 = run_dir / "1_correction"
    s1.mkdir(parents=True, exist_ok=True)
    rdir = run_dir / "0_reading"
    # Inner retry handles ONLY schema/format robustness; semantic draw quality is
    # gate①'s job (so a content-bad draw is counted + filed, not silently re-drawn
    # inside the LLM call, bypassing the per-stage budget — review 2026-06-19 High-2).
    geom = run_correction(rdir, testdata_text, out_dir=s1, feedback=None,
                          draw_validate=_schema_only_correction_validator,
                          run_profile=policy.run_profile,
                          capability_profile=policy.capability_profile,
                          dimensioned_views=dimensioned_view_names(run_dir.parent))
    evidence_debt = load_evidence_debt(s1 / "evidence_debt.json")

    # Semantic checks on the PRE-core draw. If bad, THIS draw blocks gate① → the
    # outer loop files it as an append-only attempt, counts it, and blind-resamples.
    # Do not run the deterministic core (it may raise on e.g. duplicate cell ids).
    draw_issues = correction_draw_issues(geom, _reading_window_stroke_count(rdir))
    if draw_issues:
        rep = CheckReport(
            stage="1_correction",
            capability_profile=policy.capability_profile,
            run_profile=policy.run_profile,
        )
        for msg in draw_issues:
            rep.add_fail("correction.draw_quality", CheckLayer.INVARIANT, msg)
        return geom, rep

    geom = apply_deterministic_core(geom)
    (s1 / "correction_geometry_snapped.json").write_text(
        geom.model_dump_json(indent=2), encoding="utf-8")
    # Mirror run_pipeline's post-core audit artifact (stage-dir shape parity).
    (s1 / "corrections.json").write_text(
        json.dumps({"corrections": geom.corrections, "conflicts": geom.conflicts,
                    "unsupported": geom.unsupported}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    rep = check_correction(geom, expected_zone_total=expected_zones,
                           relied_on_testdata=relied,
                           capability_profile=policy.capability_profile,
                           run_profile=policy.run_profile,
                           evidence_debt=evidence_debt)
    return geom, rep


def _load_snapped(run_dir: Path):
    from src.agent.correction.schema import CorrectedGeometry

    p = run_dir / "1_correction" / "correction_geometry_snapped.json"
    if not p.exists():
        raise SystemExit(f"missing {p}; run 1_correction first")
    return CorrectedGeometry.model_validate_json(p.read_text(encoding="utf-8"))


def _draw_modelling(run_dir: Path):
    from src.agent.geometry.specs import building_geometry_dict
    from src.agent.pipeline import materialize_kernel_geometry
    from src.validator.checks.kernel import check_kernel

    geom = _load_snapped(run_dir)
    s2 = run_dir / "2_modelling"
    s2.mkdir(parents=True, exist_ok=True)
    bg, issues = materialize_kernel_geometry(geom, s2)
    if bg is None:
        rep = CheckReport(stage="2_modelling")
        rep.add("kernel.build", CheckStatus.ERROR, CheckLayer.INVARIANT,
                message="geometry kernel build failed: " + "; ".join(issues))
        return {}, rep
    rep = check_kernel(bg, interzone_issues=issues)
    return building_geometry_dict(bg), rep


def _draw_split_pairing(run_dir: Path):
    from src.agent.geometry import build_geometry
    from src.agent.geometry.specs import (
        building_geometry_dict,
        geometry_specs_markdown,
        serialize_geometry,
    )

    geom = _load_snapped(run_dir)
    bg = build_geometry(geom)
    zone_specs, surface_specs, fen_specs, _ = serialize_geometry(bg)
    md = geometry_specs_markdown(zone_specs, surface_specs, fen_specs)
    s3 = run_dir / "3_split_pairing"
    s3.mkdir(parents=True, exist_ok=True)
    (s3 / "geometry_specs.md").write_text(md, encoding="utf-8")

    rep = CheckReport(stage="3_split_pairing")
    bg_disk = run_dir / "2_modelling" / "building_geometry.json"
    if bg_disk.exists() and json.loads(bg_disk.read_text()) == building_geometry_dict(bg):
        rep.add_pass("split_pairing.serialize_consistent", CheckLayer.INVARIANT,
                     evidence={"surfaces": len(bg.surfaces), "windows": len(bg.windows)})
    else:
        rep.add_fail("split_pairing.serialize_consistent", CheckLayer.INVARIANT,
                     "serialized specs do not match the committed 2_modelling geometry")
    return md, rep


def _geometry_zone_meta(run_dir: Path):
    """Rebuild zone_specs + used_constructions + zone_names for 4_mep / 5."""
    from src.agent.geometry import build_geometry
    from src.agent.geometry.specs import serialize_geometry

    geom = _load_snapped(run_dir)
    bg = build_geometry(geom)
    zone_specs, surface_specs, fen_specs, used = serialize_geometry(bg)
    zone_names = set(dict.fromkeys(bg.zones))
    return zone_specs, surface_specs, fen_specs, used, zone_names


def _draw_mep(run_dir: Path, testdata_text: str):
    from src.agent.pipeline import run_mep
    from src.validator.checks.mep import check_mep

    zone_specs, _, _, used, zone_names = _geometry_zone_meta(run_dir)
    s4 = run_dir / "4_mep"
    s4.mkdir(parents=True, exist_ok=True)
    mep = run_mep(zone_specs, used, testdata_text, out_dir=s4, feedback=None)
    rep = check_mep(mep.model_dump(), used_constructions=used, zone_names=zone_names)
    return mep, rep


def _draw_assembly(run_dir: Path):
    from src.agent._share import ensure_schema_initialized
    from src.agent.intakeoutput import (
        MepOutput,
        assemble_intake_output,
        validate_contract,
    )
    from src.validator.checks.assembly import check_assembly

    # MepOutput / IntakeOutput embed IDD-backed schemas (e.g. BuildingSchema's
    # terrain validator reads BaseSchema._idf_field). The integrated pipeline inits
    # the IDD; this stepwise driver must do the same before deserializing them.
    ensure_schema_initialized()

    zone_specs, surface_specs, fen_specs, used, _ = _geometry_zone_meta(run_dir)
    mep_path = run_dir / "4_mep" / "mep_output.json"
    if not mep_path.exists():
        rep = CheckReport(stage="5_intakeoutput")
        rep.add("assembly.mep_present", CheckStatus.ERROR, CheckLayer.INVARIANT,
                message="missing 4_mep/mep_output.json; run 4_mep first")
        return {}, rep
    mep = MepOutput.model_validate_json(mep_path.read_text(encoding="utf-8"))
    intake = assemble_intake_output(zone_specs=zone_specs, surface_specs=surface_specs,
                                    fenestration_specs=fen_specs, mep=mep)
    s5 = run_dir / "5_intakeoutput"
    s5.mkdir(parents=True, exist_ok=True)
    issues = validate_contract(intake, used)
    if issues:
        (s5 / "contract_issues.json").write_text(
            json.dumps(issues, indent=2, ensure_ascii=False), encoding="utf-8")
    (s5 / "intake_output.json").write_text(
        intake.model_dump_json(indent=2, by_alias=False), encoding="utf-8")
    rep = check_assembly(intake, used)
    return intake, rep


def _make_draw_fn(stage: str, run_dir: Path, testdata_text: str, td_path: Path, policy: RunPolicy):
    if stage == "0_reading":
        return lambda _fb: _draw_reading(run_dir, policy, dimensioned_view_names(run_dir.parent))
    if stage == "1_correction":
        ez = _expected_zone_total(td_path)
        relied = td_path.exists()
        return lambda _fb: _draw_correction(run_dir, testdata_text, ez, relied, policy)
    if stage == "2_modelling":
        return lambda _fb: _draw_modelling(run_dir)
    if stage == "3_split_pairing":
        return lambda _fb: _draw_split_pairing(run_dir)
    if stage == "4_mep":
        return lambda _fb: _draw_mep(run_dir, testdata_text)
    if stage == "5_intakeoutput":
        return lambda _fb: _draw_assembly(run_dir)
    raise SystemExit(f"unknown stage '{stage}'; known: {', '.join(_STAGES)}")


# --------------------------------------------------------------------------- #
# visual renders (best-effort) + judge packet
# --------------------------------------------------------------------------- #
def _render_stage(stage: str, run_dir: Path, case_dir: Path) -> list[str]:
    """Render the stage's visual artifacts for the judge / eyeball gate. Best-
    effort: a render failure (e.g. headless 3D) is logged, never fatal."""
    sys.path.insert(0, str(_REPO_ROOT / "scripts" / "tool_scripts"))
    produced: list[str] = []

    def _save(img, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        produced.append(str(path))

    try:
        if stage == "0_reading":
            import render_vector_to_png as rv
            for vj in sorted((run_dir / "0_reading").glob("*_view.json")):
                data = json.loads(vj.read_text(encoding="utf-8"))
                _save(rv.render(data), run_dir / "0_reading" / f"{vj.stem}_render.png")
        elif stage == "1_correction":
            import render_corrected_geometry as rc
            import render_elevation_windows as re_
            snapped = run_dir / "1_correction" / "correction_geometry_snapped.json"
            if snapped.exists():
                data = json.loads(snapped.read_text(encoding="utf-8"))
                _save(rc.render(data), run_dir / "1_correction" / "zones.png")
                _save(re_.render(data), run_dir / "1_correction" / "elev.png")
        # 2_modelling / 3_split_pairing geometry is handled by the dedicated
        # offline 3D viewer at the confirmation gate (_render_geometry_viewer),
        # not here — those are not judge stages.
    except Exception as e:  # noqa: BLE001 — renders are best-effort
        produced.append(f"(render error for {stage}: {type(e).__name__}: {e})")
    return produced


def _render_geometry_viewer(run_dir: Path, case_dir: Path) -> str | None:
    """Generate the self-contained offline interactive 3D viewer for the geometry
    confirmation gate (backlog #3). Returns its path, or None / an error string.
    The GLB exporter (render_building_3d.py) is kept as a tool but no longer wired
    into the main flow."""
    sys.path.insert(0, str(_REPO_ROOT / "scripts" / "tool_scripts"))
    bg = run_dir / "2_modelling" / "building_geometry.json"
    if not bg.exists():
        return None
    try:
        import render_geometry_viewer as rgv

        data = json.loads(bg.read_text(encoding="utf-8"))
        # Human geometry-confirmation artifact lives in its own manual_review/
        # folder (not a pipeline-stage output); role-coloured from the sibling
        # 1_correction so the reviewer sees room types. (backlog: edit-writeback.)
        out = run_dir / "manual_review" / "geometry_viewer.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            rgv.build_viewer_html(
                data, title=f"{case_dir.name} / {run_dir.name}",
                roles=rgv.discover_roles(bg)),
            encoding="utf-8")
        return str(out)
    except Exception as e:  # noqa: BLE001 — viewer is best-effort, never fatal
        return f"(geometry viewer render failed: {type(e).__name__}: {e})"


def _source_images(case_dir: Path) -> list[str]:
    cd = case_dir / "case_data"
    imgs = sorted(cd.glob("*_view.png")) + sorted(cd.glob("*.png"))
    seen, out = set(), []
    for p in imgs:
        if p.name not in seen:
            seen.add(p.name)
            out.append(str(p))
    return out


def _line_match_dict(m) -> dict:
    return {"truth": m.truth, "read": m.read, "delta": m.delta}


def _win_match_dict(m) -> dict:
    return {"truth": list(m.truth), "read": list(m.read) if m.read else None,
            "centre_delta": m.centre_delta}


def _floor_score_dict(score) -> dict:
    wh, wt = score.wall_hits()
    winh, wint = score.window_hits()
    return {
        "floor": score.floor,
        "wall_hits": wh,
        "wall_total": wt,
        "window_hits": winh,
        "window_total": wint,
        "max_wall_offset_m": score.max_wall_offset(),
        "vwalls": [_line_match_dict(m) for m in score.vwalls],
        "hwalls": [_line_match_dict(m) for m in score.hwalls],
        "extra_vwalls": score.extra_vwalls,
        "extra_hwalls": score.extra_hwalls,
        "windows": {
            facade: [_win_match_dict(m) for m in matches]
            for facade, matches in score.windows.items()
        },
        "extra_windows": {
            facade: [list(span) for span in spans]
            for facade, spans in score.extra_windows.items()
        },
    }


def _score_reading_attempt_output(output: dict, gt: dict, *, wall_tol: float, win_tol: float):
    from src.agent.judge.reading_score import floor_name_for_image, score_floor

    scores = {}
    evidence: list[dict] = []
    for stem, view in sorted(output.items()):
        if not isinstance(view, dict) or view.get("image_kind") not in (None, "plan"):
            continue
        floor_name = floor_name_for_image(stem, gt)
        if floor_name is None:
            evidence.append(
                {"type": "unmatched_reading_view", "view": stem,
                 "reason": "could not map view stem to gt floor"}
            )
            continue
        scores[stem] = score_floor(view, gt, floor_name, wall_tol=wall_tol, win_tol=win_tol)
    return scores, evidence, {}


def _score_attempt_output(
    stage: str,
    output: dict,
    gt: dict,
    *,
    grade: GradeConfig,
):
    from src.agent.judge.correction_score import score_correction_geometry
    from src.agent.judge.score_policy import reading_score_criteria

    wall_tol = grade.wall_tol_m
    win_tol = grade.window_centre_tol_m
    if stage == "0_reading":
        scores, evidence, floor_map = _score_reading_attempt_output(
            output, gt, wall_tol=wall_tol, win_tol=win_tol
        )
    elif stage == "1_correction":
        result = score_correction_geometry(output, gt, wall_tol=wall_tol, win_tol=win_tol)
        scores, evidence, floor_map = result.scores, result.evidence, result.floor_map
    else:
        return None
    return {
        "scores": scores,
        "evidence": evidence,
        "floor_map": floor_map,
        "score_criteria": reading_score_criteria(
            scores,
            wall_tol_m=wall_tol,
            window_centre_tol_m=win_tol,
            extra_evidence=evidence,
        ),
    }


def _load_valid_score_sidecar(
    sidecar: Path,
    *,
    stage: str,
    attempt: int,
    output_hash: str,
    tolerances: dict[str, float],
) -> dict | None:
    if not sidecar.exists():
        return None
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if (
        data.get("stage") == stage
        and data.get("attempt") == attempt
        and data.get("output_hash") == output_hash
        and data.get("source") == "attempt_output"
        and data.get("tolerances") == tolerances
    ):
        return data
    return None


def _judge_gt_artifacts(
    stage: str,
    case: str,
    run_dir: Path,
    attempt_dir: Path,
    gt: dict,
    *,
    manifest: RunManifest | None = None,
    grade: GradeConfig | None = None,
) -> dict:
    from src.agent.execution.manifest import attempt_index_of, hash_text

    if stage not in {"0_reading", "1_correction"}:
        return {"score_vs_gt": None, "overlay": None, "score_criteria": []}

    active_manifest = manifest or RunManifest.load(run_dir)
    rec = active_manifest.accepted(stage)
    attempt = attempt_index_of(attempt_dir)
    if rec is None or rec.accepted_attempt != attempt:
        return {"score_vs_gt": None, "overlay": None, "score_criteria": []}

    output_path = attempt_dir / "output.json"
    output_text = output_path.read_text(encoding="utf-8")
    if hash_text(output_text) != rec.output_hash:
        raise RuntimeError(
            f"{stage} attempt output hash does not match manifest accepted hash"
        )

    score_path = attempt_dir / "score_vs_gt.json"
    grade = grade or GradeConfig()
    tolerances = grade.as_tolerances()
    sidecar = _load_valid_score_sidecar(
        score_path,
        stage=stage,
        attempt=attempt,
        output_hash=rec.output_hash,
        tolerances=tolerances,
    )
    if sidecar is None:
        output = json.loads(output_text)
        scored = _score_attempt_output(stage, output, gt, grade=grade)
        if scored is None:
            return {"score_vs_gt": None, "overlay": None, "score_criteria": []}
        sidecar = {
            "stage": stage,
            "attempt": attempt,
            "output_hash": rec.output_hash,
            "source": "attempt_output",
            "case": case,
            "tolerances": tolerances,
            "scores": {
                key: _floor_score_dict(score)
                for key, score in scored["scores"].items()
            },
            "floor_map": scored["floor_map"],
            "evidence": scored["evidence"],
            "score_criteria": scored["score_criteria"],
        }
        score_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")

    overlay_path = attempt_dir / "overlay.png"
    if not overlay_path.exists():
        sys.path.insert(0, str(_REPO_ROOT / "scripts" / "tool_scripts"))
        import render_overlay

        output = json.loads(output_text)
        render_overlay.render_overlay_to_path(stage, output, gt, overlay_path)

    return {
        "score_vs_gt": str(score_path),
        "overlay": str(overlay_path),
        "score_criteria": sidecar.get("score_criteria", []),
    }


def _judge_packet(stage: str, case: str, case_dir: Path, run_dir: Path,
                  attempt_dir: Path, report: CheckReport,
                  *, manifest: RunManifest | None = None,
                  run_config: RunConfig | None = None) -> dict:
    # gt is judge-only — import it inside the judge path, never at module load.
    from src.agent.judge.gt import gt_path, has_gt, load_gt

    reg = rubric_for(stage)
    rubric_id = reg[0] if reg else "none"
    renders = _render_stage(stage, run_dir, case_dir)
    gt = load_gt(case) if has_gt(case) else None
    cfg = run_config or RunConfig.defaults(path=run_dir / "run_config.yaml", present=False)
    gt_artifacts = (
        _judge_gt_artifacts(
            stage,
            case,
            run_dir,
            attempt_dir,
            gt,
            manifest=manifest,
            grade=cfg.grade_for(stage),
        )
        if gt is not None
        else {"score_vs_gt": None, "overlay": None, "score_criteria": []}
    )
    pkt = {
        "stage": stage,
        "rubric_id": rubric_id,
        "rubric_doc": f"skills/intake_pipeline/{stage}/judge_rubric.md",
        "accepted_attempt_dir": str(attempt_dir),
        "source_images": _source_images(case_dir),
        "renders": renders,
        "gt_path": str(gt_path(case)) if has_gt(case) else None,
        "score_vs_gt": gt_artifacts["score_vs_gt"],
        "score_criteria": gt_artifacts["score_criteria"],
        "overlay": gt_artifacts["overlay"],
        "gate1": {
            "passed": report.passed,
            "flags": [f"{r.check_id}: {r.message}" for r in report.flagged()],
        },
        "note": "You are gate② judge. View the source images + renders (+ gt), then "
                "write a StageVerdict JSON and submit it with `judge ... --verdict`. "
                "score_criteria is machine-readable gt reconciliation evidence only; "
                "StageVerdict remains the authoritative checklist decision. "
                "Use the reconciliation first, images second; tolerances are relaxed.",
    }
    (attempt_dir / "judge_packet.json").write_text(
        json.dumps(pkt, indent=2, ensure_ascii=False), encoding="utf-8")
    return pkt


# --------------------------------------------------------------------------- #
# verbs
# --------------------------------------------------------------------------- #
def _make_policy(
    *,
    reading_runner_available: bool = False,
    run_profile: str = "exploratory",
    judge_enabled: bool = True,
    confirmation_policy: ConfirmationPolicy = ConfirmationPolicy.REQUIRED,
) -> RunPolicy:
    # dev baseline: judge on, geometry confirmation REQUIRED (blocking human gate)
    return RunPolicy(
        confirmation_policy=confirmation_policy,
        judge_enabled=judge_enabled,
        reading_runner_available=reading_runner_available,
        run_profile=run_profile,
    )


def _stage_index(stage: str) -> int:
    try:
        return _STAGES.index(stage)
    except ValueError as e:
        raise SystemExit(f"unknown stage '{stage}'; known: {', '.join(_STAGES)}") from e


def _enabled_judge(stage: str, policy: RunPolicy) -> bool:
    reg = rubric_for(stage)
    return bool(reg is not None and reg[1] and policy.judge_enabled)


def _accepted_attempt_dir(run_dir: Path, stage: str, attempt: int) -> Path:
    return run_dir / stage / "attempts" / f"{attempt:03d}"


def _accepted_verdict(run_dir: Path, stage: str, attempt: int) -> StageVerdict | None:
    p = _accepted_attempt_dir(run_dir, stage, attempt) / "judge.json"
    if not p.exists():
        return None
    try:
        return StageVerdict.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — malformed means not safely advanceable
        return None


def _stage_advance_ready(
    *,
    stage: str,
    manifest: RunManifest,
    run_dir: Path,
    case_dir: Path,
    policy: RunPolicy,
    review_switches: set[str],
) -> bool:
    rec = manifest.accepted(stage)
    if rec is None:
        return False
    if _enabled_judge(stage, policy):
        verdict = _accepted_verdict(run_dir, stage, rec.accepted_attempt)
        if verdict is None or verdict.blocking:
            return False
    if stage in review_switches and not review_is_current(
        run_dir, stage=stage, output_hash=rec.output_hash
    ):
        return False
    if stage == GEOMETRY_CHECKPOINT_STAGE and policy.confirmation_policy == ConfirmationPolicy.REQUIRED:
        if not geometry_is_approved(run_dir, case_dir=case_dir):
            return False
    return True


def _auto_start_stage(
    *,
    manifest: RunManifest,
    run_dir: Path,
    case_dir: Path,
    policy: RunPolicy,
    review_switches: set[str],
    to_stage: str,
) -> str:
    end = _stage_index(to_stage)
    state = load_state(run_dir)
    if state.get("stop_reason"):
        print(f"  pending hint from state: {state['stop_reason']} (manifest remains authoritative)")
    for stage in _STAGES[: end + 1]:
        if not _stage_advance_ready(
            stage=stage,
            manifest=manifest,
            run_dir=run_dir,
            case_dir=case_dir,
            policy=policy,
            review_switches=review_switches,
        ):
            return stage
    return to_stage


def _parse_review_switches(raw: str) -> set[str]:
    mapping = {
        "reading": "0_reading",
        "0_reading": "0_reading",
        "correction": "1_correction",
        "1_correction": "1_correction",
    }
    out: set[str] = set()
    for item in [x.strip() for x in raw.split(",") if x.strip()]:
        if item not in mapping:
            raise SystemExit(
                f"unknown review checkpoint '{item}'; use reading,correction"
            )
        out.add(mapping[item])
    return out


def _print_review_checkpoint(run_dir: Path, stage: str, attempt: int) -> None:
    adir = _accepted_attempt_dir(run_dir, stage, attempt)
    overlay = adir / "overlay.png"
    score = adir / "score_vs_gt.json"
    print("  human review checkpoint:")
    if overlay.exists():
        print(f"     overlay: {overlay}")
    else:
        print("     overlay: not generated yet (Batch B 未落地)")
    if score.exists():
        print(f"     score_vs_gt: {score}")
    else:
        print("     score_vs_gt: not generated yet (Batch B 未落地)")
    print("     approve after review:")
    print(f"        run_stage.py approve-review <case> <run> {stage} --actor <you>")


def _resolve_flow_llm_config(args, case_dir: Path, run_dir: Path) -> Path:
    global_cfg = _REPO_ROOT / "src" / "configs" / "llm.yaml"
    if args.llm_config is not None:
        cfg = Path(args.llm_config)
        if not cfg.is_absolute():
            cfg = Path.cwd() / cfg
        if not cfg.is_file():
            raise SystemExit(f"--llm-config not found: {cfg}")
        return cfg
    for cfg in (run_dir / "llm.yaml", case_dir / "llm.yaml", global_cfg):
        if cfg.is_file():
            return cfg
    return global_cfg


def _flow_ep(run_dir: Path, testdata_text: str, args, case_dir: Path) -> int:
    cfg = _resolve_flow_llm_config(args, case_dir, run_dir)
    os.environ["EP_AGENT_LLM_CONFIG"] = str(cfg.resolve())
    print(f"  LLM config: {cfg}")
    epw = Path(args.epw)
    if not epw.is_absolute():
        epw = _REPO_ROOT / epw
    if not epw.exists():
        print(f"✗ EPW not found: {epw}")
        return FLOW_EXIT_EP_RECORD
    intake_path = run_dir / "5_intakeoutput" / "intake_output.json"
    if not intake_path.exists():
        print(f"✗ missing intake output: {intake_path}")
        return FLOW_EXIT_EP_RECORD
    try:
        intake = load_intake_from(intake_path)
        initial = AgentState(
            user_input="",
            image_paths=[],
            intake_output=intake,
            reading_vector_dir=None,
            testdata_text=testdata_text,
            pipeline_out_dir=None,
        )

        def on_event(node: str, update: dict) -> None:
            print(f"  [EP node={node}] keys={list(update.keys()) if update else []}")

        run_downstream_ep(
            initial_state=initial,
            epw=epw,
            output_dir=run_dir / "EP",
            ep_run_subdir="EP_run",
            run_simulate=True,
            thread_id=f"{args.case}/{args.run}",
            on_event=on_event,
        )
    except Exception as e:  # noqa: BLE001 — flow owns EP failure code
        print(f"✗ EP downstream run failed: {type(e).__name__}: {e}")
        return FLOW_EXIT_EP_RECORD
    end = run_dir / "EP" / "EP_run" / "eplusout.end"
    if not end.exists():
        print(f"✗ EP downstream run did not produce {end}")
        return FLOW_EXIT_EP_RECORD
    print(f"  EP complete: {end}")
    return FLOW_EXIT_OK


def _print_outcome(outcome, packet: dict | None = None) -> None:
    print(f"[{outcome.stage}] {outcome.status.value}  "
          f"(attempts={outcome.attempts_used}, accepted={outcome.accepted_attempt})")
    print(f"  → {outcome.message}")
    if outcome.report is not None:
        s = {"passed": outcome.report.passed,
             "block": len(outcome.report.blocking()),
             "flag": len(outcome.report.flagged())}
        print(f"  gate①: {s}")
        for r in outcome.report.blocking():
            print(f"    ⛔ {r.check_id}: {r.message}")
        for r in outcome.report.flagged():
            print(f"    ⚠️  {r.check_id}: {r.message}")
    if packet is not None:
        print(f"  📋 judge packet → {packet['accepted_attempt_dir']}/judge_packet.json")
        print(f"     原图: {packet['source_images']}")
        print(f"     渲染: {packet['renders']}")
        if packet.get("gt_path"):
            print(f"     gt(judge-only): {packet['gt_path']}")


def _print_reread_protocol(args, outcome) -> None:
    target = outcome.route_target or "0_reading"
    date_arg = f" --date {args.date}" if args.date else ""
    print("  ↻ blind re-read protocol:")
    print("     1. Spawn a fresh isolated cold-start sub-agent for 0_reading.")
    print("     2. Give it ONLY case_data/*.png, testdata_prompt.json, and the 0_reading skill.")
    print("        Do NOT give prior strokes, prior attempts, judge commentary, or gt.")
    print("     3. Use original-resolution images / crops and any predeclared model-effort ladder; log the runner config out-of-band.")
    print("     4. Have it write/replace the flat working copy: 0_reading/*_view.json plus reading_summary.md.")
    print("     5. Then record and re-gate that flat copy:")
    print(
        "        python scripts/tool_scripts/run_stage.py"
        f" --base-dir {args.base_dir}{date_arg} resample {args.case} {args.run} {target} --force"
    )


def cmd_run(args) -> int:
    case_dir, run_dir, td_path = _resolve(args.base_dir, args.case, args.run)
    testdata_text = td_path.read_text(encoding="utf-8") if td_path.exists() else ""
    run_config = load_run_config(run_dir)
    policy = _make_policy(
        reading_runner_available=args.reading_runner_available,
        run_profile=args.run_profile,
    )
    manifest = RunManifest.load(run_dir)
    runner = StageRunner(run_dir, manifest)
    stage = args.stage
    stage_dir = run_dir / stage
    draw_fn = _make_draw_fn(stage, run_dir, testdata_text, td_path, policy)

    def _packet_fn(adir: Path, rep: CheckReport) -> dict:
        return _judge_packet(
            stage,
            args.case,
            case_dir,
            run_dir,
            adir,
            rep,
            manifest=manifest,
            run_config=run_config,
        )

    outcome = run_one_stage(
        stage=stage, runner=runner, stage_dir=stage_dir, policy=policy,
        draw_fn=draw_fn, packet_fn=_packet_fn, force_draw=args.force,
        geometry_approved=lambda: geometry_is_approved(run_dir, case_dir=case_dir),
        stage_dir_for=lambda target: run_dir / target,
    )
    manifest.save(run_dir)
    # 4_mep J4 is a disabled judge — record the explicit disabled verdict (not a PASS).
    if outcome.status == StepStatus.DETERMINISTIC_PASS and stage == "4_mep":
        run_judge("4_mep", {}, judge_fn=None, verdict_dir=run_dir / "verdicts")
    update_state(run_dir, outcome, timestamp=args.date or "")
    _print_outcome(outcome, outcome.packet)
    if outcome.status == StepStatus.AWAITING_REREAD:
        _print_reread_protocol(args, outcome)
    # geometry confirmation gate: produce the interactive offline 3D viewer for the
    # human to inspect (orbit / 半透明 / 截面 / explode / measure) before approving.
    if (stage in ("2_modelling", "3_split_pairing")
            and outcome.report is not None and outcome.report.passed):
        vpath = _render_geometry_viewer(run_dir, case_dir)
        if vpath:
            print(f"  🧊 3D viewer (open in a browser to inspect, then "
                  f"`approve-geometry`): {vpath}")
    return 0 if not outcome.terminal_stop else 2


def cmd_resample(args) -> int:
    _case_dir, run_dir, _td = _resolve(args.base_dir, args.case, args.run)
    manifest = RunManifest.load(run_dir)
    dropped = invalidate(manifest, args.stage)
    manifest.save(run_dir)
    if dropped:
        print(f"  invalidated downstream accepted pointers: {dropped}")
    args.force = True
    return cmd_run(args)


def cmd_judge(args) -> int:
    _case_dir, run_dir, _td = _resolve(args.base_dir, args.case, args.run)
    policy = _make_policy(
        reading_runner_available=args.reading_runner_available,
        run_profile=args.run_profile,
    )
    stage = args.stage
    stage_dir = run_dir / stage
    manifest = RunManifest.load(run_dir)
    accepted = manifest.accepted(stage)
    if accepted is None:
        raise SystemExit(f"{stage} has no gate①-accepted attempt; run it first")
    verdict = StageVerdict.model_validate_json(Path(args.verdict).read_text(encoding="utf-8"))
    verdict.stage = stage
    if not verdict.rubric_id:
        reg = rubric_for(stage)
        verdict.rubric_id = reg[0] if reg else "none"
    outcome = submit_verdict(
        stage=stage, stage_dir=stage_dir, attempt_index=accepted.accepted_attempt,
        verdict=verdict, verdict_dir=run_dir / "verdicts",
        policy=policy, stage_dir_for=lambda target: run_dir / target,
    )
    update_state(run_dir, outcome, timestamp=args.date or "")
    _print_outcome(outcome)
    if outcome.status == StepStatus.JUDGE_BLOCK:
        # resample the judge-attributed ROOT stage, which may differ from the judged
        # stage (e.g. a J1 verdict rooted in a stochastic upstream stage).
        target = outcome.route_target or stage
        print(f"  ↻ blind resample: `run_stage.py resample {args.case} {args.run} {target}`")
    elif outcome.status == StepStatus.AWAITING_REREAD:
        _print_reread_protocol(args, outcome)
    return 0 if not outcome.terminal_stop else 2


def cmd_approve_geometry(args) -> int:
    case_dir, run_dir, _td = _resolve(args.base_dir, args.case, args.run)
    appr = approve_geometry(run_dir, actor=args.actor, timestamp=args.date,
                            policy=args.policy, note=args.note or "", case_dir=case_dir)
    if appr is None:
        print("✗ no consistent geometry checkpoint to approve "
              "(build 2_modelling + 3_split_pairing first)")
        return 2
    # reflect approval in the ledger so a pending geometry stop_reason is cleared
    mark_geometry_approved(run_dir, timestamp=args.date or "")
    print(f"✓ geometry approved by {appr.actor} @ {appr.timestamp}")
    print(f"  digest={appr.digest}")
    print(f"  → 4_mep is now unblocked: run_stage.py run {args.case} {args.run} 4_mep")
    return 0


def cmd_approve_review(args) -> int:
    _case_dir, run_dir, _td = _resolve(args.base_dir, args.case, args.run)
    manifest = RunManifest.load(run_dir)
    rec = manifest.accepted(args.stage)
    if rec is None:
        raise SystemExit(f"{args.stage} has no accepted attempt; run it first")
    appr = record_review(
        run_dir,
        stage=args.stage,
        output_hash=rec.output_hash,
        actor=args.actor,
        timestamp=args.date or "",
        note=args.note or "",
    )
    mark_review_approved(run_dir, args.stage, timestamp=args.date or "")
    print(f"✓ review approved by {appr.actor} @ {appr.timestamp}")
    print(f"  stage={appr.stage}")
    print(f"  output_hash={appr.output_hash}")
    return 0


def cmd_flow(args) -> int:
    case_dir, run_dir, td_path = _resolve(args.base_dir, args.case, args.run)
    testdata_text = td_path.read_text(encoding="utf-8") if td_path.exists() else ""
    run_config = load_run_config(run_dir)
    review_switches = (
        _parse_review_switches(args.review or "")
        if args.review
        else run_config.review_stages()
    )
    judge_mode = run_config.judge_mode if run_config.present else args.judge
    to_stage = args.to_stage
    if run_config.present and args.to_stage == "5_intakeoutput" and run_config.scope_stages:
        to_stage = run_config.scope_stages[-1]
    policy = _make_policy(
        reading_runner_available=args.reading_runner_available,
        run_profile=args.run_profile,
        judge_enabled=(judge_mode != "off"),
        confirmation_policy=ConfirmationPolicy.REQUIRED,
    )
    manifest = RunManifest.load(run_dir)
    start_stage = (
        _auto_start_stage(
            manifest=manifest,
            run_dir=run_dir,
            case_dir=case_dir,
            policy=policy,
            review_switches=review_switches,
            to_stage=to_stage,
        )
        if args.from_stage == "auto"
        else args.from_stage
    )
    start = _stage_index(start_stage)
    end = _stage_index(to_stage)
    if start > end:
        raise SystemExit(f"--from {start_stage} is after --to {to_stage}")

    runner = StageRunner(run_dir, manifest)
    force_next: set[str] = set()
    i = start
    while i <= end:
        stage = _STAGES[i]
        stage_dir = run_dir / stage
        draw_fn = _make_draw_fn(stage, run_dir, testdata_text, td_path, policy)

        def _packet_fn(adir: Path, rep: CheckReport, *, _stage=stage) -> dict:
            return _judge_packet(
                _stage,
                args.case,
                case_dir,
                run_dir,
                adir,
                rep,
                manifest=manifest,
                run_config=run_config,
            )

        outcome = run_one_stage(
            stage=stage,
            runner=runner,
            stage_dir=stage_dir,
            policy=policy,
            draw_fn=draw_fn,
            packet_fn=_packet_fn,
            force_draw=stage in force_next,
            geometry_approved=lambda: geometry_is_approved(run_dir, case_dir=case_dir),
            stage_dir_for=lambda target: run_dir / target,
        )
        force_next.discard(stage)
        manifest.save(run_dir)
        if outcome.status == StepStatus.DETERMINISTIC_PASS and stage == "4_mep":
            run_judge("4_mep", {}, judge_fn=None, verdict_dir=run_dir / "verdicts")
        update_state(run_dir, outcome, timestamp=args.date or "")
        _print_outcome(outcome, outcome.packet)

        if outcome.status in (StepStatus.DETERMINISTIC_PASS, StepStatus.JUDGE_PASS):
            rec = manifest.accepted(stage)
            if rec is not None and stage in review_switches and not review_is_current(
                run_dir, stage=stage, output_hash=rec.output_hash
            ):
                review_outcome = StageOutcome(
                    stage=stage,
                    status=StepStatus.AWAITING_HUMAN_REVIEW,
                    attempts_used=outcome.attempts_used,
                    accepted_attempt=outcome.accepted_attempt,
                    report=outcome.report,
                    message="stage passed — awaiting durable human review approval",
                )
                update_state(run_dir, review_outcome, timestamp=args.date or "")
                _print_outcome(review_outcome)
                _print_review_checkpoint(run_dir, stage, rec.accepted_attempt)
                return FLOW_EXIT_CHECKPOINT
            i += 1
            continue

        if outcome.status == StepStatus.AWAITING_JUDGE:
            print("  submit a verdict, then rerun flow to resume:")
            print(
                "     run_stage.py"
                f" --base-dir {args.base_dir} judge {args.case} {args.run} {stage}"
                " --verdict <verdict.json>"
            )
            return FLOW_EXIT_CHECKPOINT

        if outcome.status == StepStatus.AWAITING_GEOMETRY_APPROVAL:
            vpath = _render_geometry_viewer(run_dir, case_dir)
            if vpath:
                print(f"  3D viewer: {vpath}")
            if args.geometry == "auto":
                appr = approve_geometry(
                    run_dir,
                    actor="flow:auto",
                    timestamp=args.date or "",
                    policy="auto",
                    note="flow --geometry auto",
                    case_dir=case_dir,
                )
                if appr is None:
                    print("✗ geometry auto-approval failed: no consistent checkpoint")
                    return FLOW_EXIT_STOP
                mark_geometry_approved(run_dir, timestamp=args.date or "")
                print(f"  geometry auto-approved digest={appr.digest}")
                continue
            print("  approve after inspection:")
            print(
                "     run_stage.py"
                f" --base-dir {args.base_dir} approve-geometry {args.case} {args.run}"
                " --actor <you>"
            )
            return FLOW_EXIT_CHECKPOINT

        if outcome.status == StepStatus.AWAITING_REREAD:
            _print_reread_protocol(args, outcome)
            return FLOW_EXIT_CHECKPOINT

        if outcome.status == StepStatus.JUDGE_BLOCK:
            target = outcome.route_target
            if target not in _STAGES:
                print(f"  cannot auto-resample judge route target: {target!r}")
                return FLOW_EXIT_CHECKPOINT
            if _stage_index(target) > end:
                print(f"  judge route target {target} is beyond --to {to_stage}")
                return FLOW_EXIT_CHECKPOINT
            dropped = invalidate(manifest, target)
            manifest.save(run_dir)
            if dropped:
                print(f"  invalidated downstream accepted pointers: {dropped}")
            print(f"  auto blind-resample target: {target}")
            force_next.add(target)
            i = _stage_index(target)
            continue

        if outcome.terminal_stop:
            return FLOW_EXIT_STOP

        print(f"  unhandled flow status: {outcome.status.value}")
        return FLOW_EXIT_CHECKPOINT

    if args.with_ep:
        code = _flow_ep(run_dir, testdata_text, args, case_dir)
        if code:
            return code

    if args.record:
        state = load_state(run_dir)
        if state.get("stop_reason") and not args.record_partial:
            print(f"✗ refusing record with pending stop_reason={state['stop_reason']}")
            return FLOW_EXIT_EP_RECORD
        if not args.orchestrator:
            print("✗ --record requires --orchestrator")
            return FLOW_EXIT_EP_RECORD
        if args.run_profile == "golden":
            appr = GeometryApproval.load(run_dir)
            if appr is not None and appr.actor == "flow:auto" and appr.policy == "auto":
                print("⚠ golden record with flow:auto geometry approval; human HTML review is recommended")
        try:
            sys.path.insert(0, str(_REPO_ROOT / "scripts" / "tool_scripts"))
            from record_baseline import record_baseline

            record_baseline(
                run_dir,
                date=args.date or "",
                orchestrator=args.orchestrator,
                require_ep=args.with_ep,
                run_profile=args.run_profile,
            )
        except Exception as e:  # noqa: BLE001 — flow owns record failure code
            print(f"✗ record failed: {type(e).__name__}: {e}")
            return FLOW_EXIT_EP_RECORD
        print(f"  baseline recorded: {run_dir / '_run' / 'baseline.json'}")

    return FLOW_EXIT_OK


def cmd_status(args) -> int:
    _case_dir, run_dir, _td = _resolve(args.base_dir, args.case, args.run)
    state = load_state(run_dir)
    print(f"orchestration state — {args.case}/{args.run}")
    print(f"  stop_reason: {state.get('stop_reason')}")
    for stage in _STAGES:
        st = state.get("stages", {}).get(stage)
        if st:
            g = st.get("gate1", {})
            print(f"  {stage:16s} {st['status']:28s} "
                  f"attempts={st['attempts_used']} gate①={g}")
        else:
            print(f"  {stage:16s} (not run)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-dir", default="case_tests/e2e_tests")
    ap.add_argument("--date", default="", help="ISO date stamp for state/approval")
    ap.add_argument("--reading-runner-available", action="store_true",
                    help="enable awaiting_reread decisions; the main Agent still runs the sub-agent protocol")
    ap.add_argument(
        "--run-profile",
        choices=("exploratory", "dev", "golden", "regression"),
        default="exploratory",
        help="evidence gate policy: exploratory/dev flag, golden/regression block",
    )
    sub = ap.add_subparsers(dest="verb", required=True)

    for verb in ("run", "resample"):
        p = sub.add_parser(verb)
        p.add_argument("case"); p.add_argument("run"); p.add_argument("stage")
        p.add_argument("--force", action="store_true")

    pj = sub.add_parser("judge")
    pj.add_argument("case"); pj.add_argument("run"); pj.add_argument("stage")
    pj.add_argument("--verdict", required=True, help="path to a StageVerdict JSON")

    pa = sub.add_parser("approve-geometry")
    pa.add_argument("case"); pa.add_argument("run")
    pa.add_argument("--actor", required=True); pa.add_argument("--note")
    pa.add_argument("--policy", choices=("required", "auto"), default="required")

    pr = sub.add_parser("approve-review")
    pr.add_argument("case"); pr.add_argument("run"); pr.add_argument("stage", choices=_STAGES)
    pr.add_argument("--actor", required=True); pr.add_argument("--note")

    pf = sub.add_parser("flow")
    pf.add_argument("case"); pf.add_argument("run")
    pf.add_argument("--from", dest="from_stage", default="auto",
                    choices=["auto", *_STAGES])
    pf.add_argument("--to", dest="to_stage", default="5_intakeoutput",
                    choices=_STAGES)
    pf.add_argument("--judge", choices=("stop", "off"), default="stop")
    pf.add_argument("--review", default="",
                    help="comma-separated human checkpoints: reading,correction")
    pf.add_argument("--geometry", choices=("required", "auto"), default="required")
    pf.add_argument("--with-ep", action="store_true")
    pf.add_argument("--record", action="store_true")
    pf.add_argument("--record-partial", action="store_true")
    pf.add_argument("--orchestrator", default="")
    pf.add_argument("--llm-config", type=Path, default=None)
    pf.add_argument("--epw", default="data/weather/Shenzhen.epw")

    ps = sub.add_parser("status")
    ps.add_argument("case"); ps.add_argument("run")

    args = ap.parse_args()
    if not hasattr(args, "force"):
        args.force = False
    return {
        "run": cmd_run, "resample": cmd_resample, "judge": cmd_judge,
        "approve-geometry": cmd_approve_geometry,
        "approve-review": cmd_approve_review,
        "flow": cmd_flow,
        "status": cmd_status,
    }[args.verb](args)


if __name__ == "__main__":
    raise SystemExit(main())
