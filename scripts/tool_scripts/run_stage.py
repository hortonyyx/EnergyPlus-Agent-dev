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
then `record_baseline.py <case> <run> --require-ep` for the aggregate report.
"""

from __future__ import annotations

import argparse
import json
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
    StepStatus,
    approve_geometry,
    geometry_is_approved,
    load_state,
    mark_geometry_approved,
    run_one_stage,
    submit_verdict,
    update_state,
)
from src.agent.execution.policy import ConfirmationPolicy  # noqa: E402
from src.agent.judge.executor import rubric_for, run_judge  # noqa: E402
from src.agent.judge.verdict import StageVerdict  # noqa: E402
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus  # noqa: E402

_STAGES = ["0_reading", "1_correction", "2_modelling", "3_split_pairing",
           "4_mep", "5_intakeoutput"]


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
    plans = data.get("Floor plans") or []
    totals = [p.get("thermal_zones") for p in plans if isinstance(p.get("thermal_zones"), int)]
    return sum(totals) if totals else None


# --------------------------------------------------------------------------- #
# stage executors — each returns (output_obj, gate①_report)
# --------------------------------------------------------------------------- #
def _draw_reading(run_dir: Path):
    """0_reading is MANUAL: validate the already-produced view JSONs (no LLM)."""
    from src.agent.reading import load_reading_view
    from src.validator.checks.reading import check_reading_view

    rdir = run_dir / "0_reading"
    views = sorted(rdir.glob("*_view.json"))
    rep = CheckReport(stage="0_reading")
    if not views:
        rep.add("reading.present", CheckStatus.ERROR, CheckLayer.INVARIANT,
                message="no 0_reading/*_view.json found — produce reading first")
        return {}, rep
    out: dict = {}
    for vj in views:
        view = load_reading_view(vj)
        out[vj.stem] = json.loads(vj.read_text(encoding="utf-8"))
        sub = check_reading_view(view)
        for r in sub.results:  # merge per-view results under one stage report
            rep.results.append(r.model_copy(update={"check_id": f"{vj.stem}.{r.check_id}"}))
    return out, rep


def _draw_correction(run_dir: Path, testdata_text: str, expected_zones, relied):
    from src.agent.correction.deterministic import apply_deterministic_core
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
                          draw_validate=_schema_only_correction_validator)

    # Semantic checks on the PRE-core draw. If bad, THIS draw blocks gate① → the
    # outer loop files it as an append-only attempt, counts it, and blind-resamples.
    # Do not run the deterministic core (it may raise on e.g. duplicate cell ids).
    draw_issues = correction_draw_issues(geom, _reading_window_stroke_count(rdir))
    if draw_issues:
        rep = CheckReport(stage="1_correction")
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
                           relied_on_testdata=relied)
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


def _make_draw_fn(stage: str, run_dir: Path, testdata_text: str, td_path: Path):
    if stage == "0_reading":
        return lambda _fb: _draw_reading(run_dir)
    if stage == "1_correction":
        ez = _expected_zone_total(td_path)
        relied = td_path.exists()
        return lambda _fb: _draw_correction(run_dir, testdata_text, ez, relied)
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


def _judge_packet(stage: str, case: str, case_dir: Path, run_dir: Path,
                  attempt_dir: Path, report: CheckReport) -> dict:
    # gt is judge-only — import it inside the judge path, never at module load.
    from src.agent.judge.gt import gt_path, has_gt

    reg = rubric_for(stage)
    rubric_id = reg[0] if reg else "none"
    renders = _render_stage(stage, run_dir, case_dir)
    pkt = {
        "stage": stage,
        "rubric_id": rubric_id,
        "rubric_doc": f"skills/intake_pipeline/{stage}/judge_rubric.md",
        "accepted_attempt_dir": str(attempt_dir),
        "source_images": _source_images(case_dir),
        "renders": renders,
        "gt_path": str(gt_path(case)) if has_gt(case) else None,
        "gate1": {
            "passed": report.passed,
            "flags": [f"{r.check_id}: {r.message}" for r in report.flagged()],
        },
        "note": "You are gate② judge. View the source images + renders (+ gt), then "
                "write a StageVerdict JSON and submit it with `judge ... --verdict`.",
    }
    (attempt_dir / "judge_packet.json").write_text(
        json.dumps(pkt, indent=2, ensure_ascii=False), encoding="utf-8")
    return pkt


# --------------------------------------------------------------------------- #
# verbs
# --------------------------------------------------------------------------- #
def _make_policy() -> RunPolicy:
    # dev baseline: judge on, geometry confirmation REQUIRED (blocking human gate)
    return RunPolicy(confirmation_policy=ConfirmationPolicy.REQUIRED, judge_enabled=True)


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


def cmd_run(args) -> int:
    case_dir, run_dir, td_path = _resolve(args.base_dir, args.case, args.run)
    testdata_text = td_path.read_text(encoding="utf-8") if td_path.exists() else ""
    policy = _make_policy()
    manifest = RunManifest.load(run_dir)
    runner = StageRunner(run_dir, manifest)
    stage = args.stage
    stage_dir = run_dir / stage
    draw_fn = _make_draw_fn(stage, run_dir, testdata_text, td_path)

    def _packet_fn(adir: Path, rep: CheckReport) -> dict:
        return _judge_packet(stage, args.case, case_dir, run_dir, adir, rep)

    outcome = run_one_stage(
        stage=stage, runner=runner, stage_dir=stage_dir, policy=policy,
        draw_fn=draw_fn, packet_fn=_packet_fn, force_draw=args.force,
        geometry_approved=lambda: geometry_is_approved(run_dir, case_dir=case_dir),
    )
    manifest.save(run_dir)
    # 4_mep J4 is a disabled judge — record the explicit disabled verdict (not a PASS).
    if outcome.status == StepStatus.DETERMINISTIC_PASS and stage == "4_mep":
        run_judge("4_mep", {}, judge_fn=None, verdict_dir=run_dir / "verdicts")
    update_state(run_dir, outcome, timestamp=args.date or "")
    _print_outcome(outcome, outcome.packet)
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
    args.force = True
    return cmd_run(args)


def cmd_judge(args) -> int:
    _case_dir, run_dir, _td = _resolve(args.base_dir, args.case, args.run)
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
    )
    update_state(run_dir, outcome, timestamp=args.date or "")
    _print_outcome(outcome)
    if outcome.status == StepStatus.JUDGE_BLOCK:
        # resample the judge-attributed ROOT stage, which may differ from the judged
        # stage (e.g. a J1 verdict rooted in a stochastic upstream stage).
        target = outcome.route_target or stage
        print(f"  ↻ blind resample: `run_stage.py resample {args.case} {args.run} {target}`")
    return 0 if not outcome.terminal_stop else 2


def cmd_approve_geometry(args) -> int:
    case_dir, run_dir, _td = _resolve(args.base_dir, args.case, args.run)
    appr = approve_geometry(run_dir, actor=args.actor, timestamp=args.date,
                            note=args.note or "", case_dir=case_dir)
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

    ps = sub.add_parser("status")
    ps.add_argument("case"); ps.add_argument("run")

    args = ap.parse_args()
    if not hasattr(args, "force"):
        args.force = False
    return {
        "run": cmd_run, "resample": cmd_resample, "judge": cmd_judge,
        "approve-geometry": cmd_approve_geometry, "status": cmd_status,
    }[args.verb](args)


if __name__ == "__main__":
    raise SystemExit(main())
