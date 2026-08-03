"""Validate a case directory through the full per-stage gate ① (M4 capstone).

Non-invasive: this reads the on-disk artifacts a pipeline run already produced
(0_reading/*.json, 1_correction/correction_geometry_snapped.json, 4_mep/
mep_output.json, 5_intakeoutput/intake_output.json, EP/EP_run) and runs every
deterministic check (S0–S5 + EP baseline) over them, producing one CheckReport
per stage, a RunManifest, and the geometry-approval digest. It does NOT modify
``run_pipeline`` — it is the "逐环节约束各阶段输出 + 校验" wiring that sits beside
the pipeline so existing cases can be validated and new ones gated.

Honours the RunPolicy: ``validation_scope=downstream_only`` (``--intake-from``)
skips the 0–4 geometry/MEP checks and only validates the supplied IntakeOutput;
``confirmation_policy`` decides whether an unapproved geometry checkpoint blocks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.approval import geometry_checkpoint_digest, is_approved
from src.agent.execution.case_metadata import (
    dimensioned_view_states,
    expected_zone_total_from_testdata,
)
from src.agent.execution.manifest import RunManifest, StageRecord, hash_text
from src.agent.execution.policy import RunPolicy, ValidationScope
from src.agent.state import IntakeOutput
from src.validator.checks.assembly import check_assembly, check_ep_baseline
from src.validator.checks.correction import check_correction
from src.validator.checks.kernel import check_kernel
from src.validator.checks.mep import check_mep
from src.validator.checks.reading import check_reading_view
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus


@dataclass
class CaseValidationResult:
    case: str
    reports: dict[str, CheckReport] = field(default_factory=dict)
    geometry_digest: str | None = None
    geometry_approved: bool = False
    blocked: bool = False
    blocking_summary: list[str] = field(default_factory=list)

    def all_passed(self) -> bool:
        return not self.blocked


def _expected_zone_total(case_dir: Path) -> int | None:
    td = case_dir / "case_data" / "testdata_prompt.json"
    if not td.exists():
        return None
    try:
        data = json.loads(td.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return expected_zone_total_from_testdata(data) if isinstance(data, dict) else None


def _load_testdata(case_dir: Path) -> dict | None:
    td = case_dir / "case_data" / "testdata_prompt.json"
    if not td.exists():
        return None
    try:
        data = json.loads(td.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def validate_case(
    run_dir: Path | str,
    *,
    case_dir: Path | str | None = None,
    policy: RunPolicy | None = None,
    write_reports: bool = False,
) -> CaseValidationResult:
    """Validate one self-contained RUN (``<case>/run_<note>/``).

    A run dir holds 0_reading + 1..5 + EP (the per-run products); the CASE
    (materials/testdata) is its parent, resolvable via ``case_dir`` (default
    ``run_dir.parent``) — gt is per-case and judge-only, never read here. Reports /
    manifest / approval are written into the run dir."""
    run_dir = Path(run_dir)
    case_dir = Path(case_dir) if case_dir is not None else run_dir.parent
    policy = policy or RunPolicy()
    res = CaseValidationResult(case=case_dir.name)
    profile = policy.capability_profile
    run_profile = policy.run_profile

    if policy.validation_scope == ValidationScope.DOWNSTREAM_ONLY:
        _validate_downstream_only(run_dir, res, profile, run_profile, write_reports)
        _finalize(res)
        return res

    # ---- required-artifact guard (fail-CLOSED: a missing required artifact in
    # full scope is a blocking ERROR, never a silent pass) ----
    snapped = run_dir / "1_correction" / "correction_geometry_snapped.json"
    bg_json = run_dir / "2_modelling" / "building_geometry.json"
    specs_path = run_dir / "3_split_pairing" / "geometry_specs.md"
    mep_path = run_dir / "4_mep" / "mep_output.json"
    intake_path = run_dir / "5_intakeoutput" / "intake_output.json"
    rdir = run_dir / "0_reading"
    ep_run = run_dir / "EP" / "EP_run"
    ep_end = ep_run / "eplusout.end"
    testdata = _load_testdata(case_dir)

    has_reading = rdir.exists() and any(rdir.glob("*_view.json"))
    required = {
        "0_reading": (has_reading, "0_reading/*_view.json"),
        "1_correction": (snapped.exists(), str(snapped.relative_to(run_dir))),
        "2_modelling": (bg_json.exists(), str(bg_json.relative_to(run_dir))),
        "3_split_pairing": (specs_path.exists(), str(specs_path.relative_to(run_dir))),
        "4_mep": (mep_path.exists(), str(mep_path.relative_to(run_dir))),
        "5_intakeoutput": (intake_path.exists(), str(intake_path.relative_to(run_dir))),
    }
    if policy.require_ep:
        required["downstream"] = (ep_end.exists(), "EP/EP_run/eplusout.end")
    for stage_key, (present, where) in required.items():
        if not present:
            res.reports[stage_key] = _error_report(
                stage_key, profile, run_profile, f"required artifact missing: {where}")

    # ---- 0_reading ----
    reading_views = []
    if has_reading:
        from src.agent.reading import load_reading_view

        # R1-3 (派工单 §1.3): per-view 4-state applicability, not a bool set.
        # r0 folded this to view_metadata={"dimensioned": stem in names} and
        # never passed dimensioned_state, so a structured declared_true /
        # declared_false declaration collapsed to legacy_default here (the
        # names add() dropped non-strings). check_reading_view's _view_metadata
        # takes dimensioned_state as the authoritative 4-state signal.
        dimensioned_states = dimensioned_view_states(case_dir)
        for vj in sorted(rdir.glob("*_view.json")):
            view = load_reading_view(vj)
            reading_views.append(view)
            rep = check_reading_view(
                view,
                capability_profile=profile,
                run_profile=run_profile,
                dimensioned_state=dimensioned_states.get(vj.stem, "legacy_default"),
            )
            res.reports[f"0_reading::{vj.stem}"] = rep
            if write_reports:
                _write(rdir / f"{vj.stem}_checks.json", rep)

        # C2 B-M §4.4: validate_case only ever *reads* the view manifest
        # (never provisions). A run that predates this wire — including every
        # existing golden anchor — simply has no `_run/view_manifest.json`;
        # that is reported NOT_APPLICABLE (non-invasive: no new BLOCK for an
        # old anchor that never opted in), not silently skipped. A run that
        # HAS a view manifest is held to it: `reading.view_manifest_coverage`
        # is INVARIANT/always-BLOCK on a genuine miss/extra/drift (§6).
        from src.agent.execution.run_meta import run_meta_path
        from src.agent.execution.view_manifest import VIEW_MANIFEST_NAME, verify_view_manifest
        from src.validator.checks.view_manifest import check_view_manifest_coverage

        vm_rep = CheckReport(stage="0_reading", capability_profile=profile, run_profile=run_profile)
        if not run_meta_path(run_dir, VIEW_MANIFEST_NAME).exists():
            vm_rep.add(
                "reading.view_manifest_coverage", CheckStatus.NOT_APPLICABLE, CheckLayer.INVARIANT,
                message="run predates the view manifest wire (never provisioned)",
            )
        else:
            verification = verify_view_manifest(case_dir, run_dir)
            produced_stems = {vj.stem for vj in rdir.glob("*_view.json")}
            vm_rep = check_view_manifest_coverage(
                verification.on_disk if verification.ok else None,
                produced_stems,
                manifest_missing_reason=verification.reason,
                capability_profile=profile,
                run_profile=run_profile,
            )
        res.reports["0_reading::view_manifest"] = vm_rep
        if write_reports:
            _write(rdir / "view_manifest_checks.json", vm_rep)

    # ---- 1_correction (+ rebuild kernel for 2/3) ----
    bg = None
    used_constructions: set[str] = set()
    zone_names: set[str] = set()
    geometry_consistent = True  # set False if on-disk 2/3 drift from the rebuild
    if snapped.exists():
        from src.agent.execution.evidence_preflight import load_evidence_debt

        from src.agent.correction.parse import ensure_corrected_geometry
        geom = ensure_corrected_geometry(json.loads(snapped.read_text()))
        relied = (case_dir / "case_data" / "testdata_prompt.json").exists()
        evidence_debt = load_evidence_debt(run_dir / "1_correction" / "evidence_debt.json")
        crep = check_correction(
            geom, expected_zone_total=_expected_zone_total(case_dir),
            relied_on_testdata=relied,
            capability_profile=profile,
            run_profile=run_profile,
            evidence_debt=evidence_debt,
            reading_views=reading_views,
        )
        res.reports["1_correction"] = crep
        if write_reports:
            _write(run_dir / "1_correction" / "correction_checks.json", crep)

        # 2/3 kernel — rebuild the authoritative geometry from the snapped cells,
        # AND reconcile the committed on-disk 2/3 artifacts against that rebuild so
        # a stale/garbage building_geometry.json or geometry_specs.md cannot pass.
        try:
            from src.agent.geometry import build_geometry
            from src.agent.geometry.specs import (
                building_geometry_dict,
                geometry_specs_markdown,
                serialize_geometry,
            )

            bg = build_geometry(geom, capability_profile=profile)
            zone_specs, surface_specs, fen_specs, used_constructions = serialize_geometry(bg)
            zone_names = set(dict.fromkeys(bg.zones))

            # S2: kernel check on the authoritative rebuild + on-disk consistency.
            if bg_json.exists():
                krep = check_kernel(
                    bg,
                    capability_profile=profile,
                    run_profile=run_profile,
                )
                try:
                    disk_bg = json.loads(bg_json.read_text())
                except json.JSONDecodeError:
                    disk_bg = None
                if disk_bg != building_geometry_dict(bg):
                    geometry_consistent = False
                    krep.add_fail(
                        "kernel.artifact_consistency", CheckLayer.INVARIANT,
                        "committed building_geometry.json does not match the "
                        "deterministic rebuild from snapped correction geometry "
                        "(stale/garbage artifact)")
                res.reports["2_modelling"] = krep
                if write_reports:
                    _write(run_dir / "2_modelling" / "kernel_checks.json", krep)

            # S3: geometry_specs.md must equal the serializer output.
            if specs_path.exists():
                expected_md = geometry_specs_markdown(zone_specs, surface_specs, fen_specs)
                if specs_path.read_text() != expected_md:
                    geometry_consistent = False
                    res.reports["3_split_pairing"] = _error_report(
                        "3_split_pairing", profile, run_profile,
                        "committed geometry_specs.md does not match the deterministic "
                        "serializer output (stale/garbage artifact)")
        except Exception as e:  # noqa: BLE001 — recorded as a blocking error report
            geometry_consistent = False
            res.reports["2_modelling"] = _error_report("2_modelling", profile, run_profile,
                                                        f"kernel build failed: {e}")

    # ---- 4_mep ----
    if mep_path.exists():
        mep = json.loads(mep_path.read_text())
        mrep = check_mep(mep, used_constructions=used_constructions or None,
                         zone_names=zone_names or None, testdata=testdata,
                         capability_profile=profile)
        res.reports["4_mep"] = mrep
        if write_reports:
            _write(run_dir / "4_mep" / "mep_checks.json", mrep)

    # ---- 5_intakeoutput backstop ----
    if intake_path.exists():
        intake = IntakeOutput.model_validate_json(intake_path.read_text())
        if used_constructions:
            arep = check_assembly(
                intake,
                used_constructions,
                capability_profile=profile,
                run_profile=run_profile,
            )
        else:
            # intake present but no construction set to backstop against (upstream
            # geometry missing) — record an explicit error, do not skip silently.
            arep = _error_report("5_intakeoutput", profile,
                                 run_profile,
                                 "cannot backstop: upstream geometry/used_constructions "
                                 "unavailable")
        res.reports["5_intakeoutput"] = arep
        if write_reports:
            _write(run_dir / "5_intakeoutput" / "assembly_checks.json", arep)

    # ---- EP baseline ----
    if ep_end.exists():
        eprep = check_ep_baseline(ep_run, capability_profile=profile)
        res.reports["downstream"] = eprep
    # (missing EP with require_ep=True is already a blocking ERROR above; with
    #  require_ep=False the EP baseline is intentionally not validated.)

    # E4 §7.4: audits are evidence, not decorative logs.  When an E4 export
    # elected to write them, replay/validate must strict-parse the wires and
    # recompute every available raw hash from the current run tree.
    audit_rep = _validate_coordinate_audits(run_dir, profile, run_profile)
    if audit_rep is not None:
        res.reports["downstream::output_coordinate_audit"] = audit_rep

    # ---- geometry approval digest + confirmation policy ----
    # Only compute a digest from the REAL on-disk geometry artifacts, and ONLY
    # after they passed the consistency check — never bind an approval to stale /
    # unchecked bytes ({}/"" fallback or a drifted artifact).
    if (
        bg_json.exists()
        and specs_path.exists()
        and geometry_consistent
        and "2_modelling" in res.reports
        and res.reports["2_modelling"].passed
    ):
        bg_dict = json.loads(bg_json.read_text())
        specs = specs_path.read_text()
        kreport = res.reports["2_modelling"].model_dump()
        res.geometry_digest = geometry_checkpoint_digest(
            building_geometry=bg_dict, geometry_specs=specs, kernel_check_report=kreport,
        )
        res.geometry_approved = is_approved(run_dir, res.geometry_digest)

    _finalize(res, policy)
    if write_reports:
        # A validation SUMMARY — NOT the M0 audit manifest (which is backed by
        # append-only attempt dirs). Distinct filename so it cannot masquerade as,
        # or overwrite, run_manifest.json.
        _build_manifest(res).save(run_dir, filename="validation_manifest.json")
    return res


def _validate_downstream_only(
    run_dir: Path,
    res: CaseValidationResult,
    profile: str,
    run_profile: str,
    write_reports: bool,
) -> None:
    """--intake-from: only the supplied IntakeOutput is validated (Pydantic)."""
    intake_path = run_dir / "5_intakeoutput" / "intake_output.json"
    if not intake_path.exists():
        intake_path = run_dir / "EP" / "intake_output.json"
    rep = CheckReport(
        stage="5_intakeoutput",
        capability_profile=profile,
        run_profile=run_profile,
    )
    from src.validator.checks.schema import CheckLayer, CheckStatus

    if intake_path.exists():
        try:
            IntakeOutput.model_validate_json(intake_path.read_text())
            rep.add_pass("assembly.pydantic", CheckLayer.INVARIANT)
        except Exception as e:  # noqa: BLE001
            rep.add("assembly.pydantic", CheckStatus.ERROR, CheckLayer.INVARIANT,
                    message=f"IntakeOutput invalid: {e}")
    else:
        rep.add("assembly.pydantic", CheckStatus.ERROR, CheckLayer.INVARIANT,
                message="no intake_output.json found")
    res.reports["5_intakeoutput"] = rep


def _matching_raw_hash(paths: list[Path], expected: str) -> bool:
    from src.agent.output_coordinates import sha256_bytes

    return any(path.is_file() and sha256_bytes(path.read_bytes()) == expected for path in paths)


def _validate_coordinate_audits(run_dir: Path, profile: str, run_profile: str) -> CheckReport | None:
    """Read-only §7.4 replay verifier for accepted export/simulation audits."""
    export_path = run_dir / "EP" / "output_coordinate_audit.json"
    ep_path = run_dir / "EP" / "EP_run" / "output_coordinate_ep_audit.json"
    if not export_path.is_file() and not ep_path.is_file():
        return None

    from src.agent.output_coordinates import canonical_json_bytes, sha256_bytes
    from src.validator.output_coordinates import (
        EpCoordinateAuditV1,
        ExportCoordinateAuditV1,
        registry_candidate_sha256,
    )

    rep = CheckReport(stage="downstream", capability_profile=profile, run_profile=run_profile)
    ep_dir = run_dir / "EP" / "EP_run"
    idf_paths = sorted((run_dir / "EP").glob("*.idf"))
    yaml_paths = sorted((run_dir / "EP").glob("*.yaml"))
    if export_path.is_file():
        try:
            audit = ExportCoordinateAuditV1.model_validate_json(export_path.read_text(encoding="utf-8"))
            failures: list[str] = []
            if not _matching_raw_hash(idf_paths, audit.idf_sha256):
                failures.append("no current EP/*.idf hashes to output_coordinate_audit.idf_sha256")
            if not _matching_raw_hash(yaml_paths, audit.yaml_sha256):
                failures.append("no current EP/*.yaml hashes to output_coordinate_audit.yaml_sha256")
            if audit.registry_candidate_sha256 != registry_candidate_sha256():
                failures.append("registry candidate set hash drifted since export")
            if failures:
                rep.add_fail("output_coordinates.export_audit_replay", CheckLayer.INVARIANT, "; ".join(failures))
            else:
                rep.add_pass("output_coordinates.export_audit_replay", CheckLayer.INVARIANT)
        except Exception as exc:  # noqa: BLE001 - malformed evidence is a finding
            rep.add_fail("output_coordinates.export_audit_replay", CheckLayer.INVARIANT,
                         f"invalid/tampered output_coordinate_audit.json: {exc}")
    if ep_path.is_file():
        try:
            audit = EpCoordinateAuditV1.model_validate_json(ep_path.read_text(encoding="utf-8"))
            failures = []
            if not _matching_raw_hash(idf_paths, audit.idf_sha256):
                failures.append("no current EP/*.idf hashes to EP audit idf_sha256")
            for filename, expected in (("eplusout.eio", audit.eio_sha256), ("eplusout.err", audit.err_sha256)):
                path = ep_dir / filename
                if expected is None:
                    if path.is_file():
                        failures.append(f"EP audit omits hash for present {filename}")
                elif not path.is_file() or sha256_bytes(path.read_bytes()) != expected:
                    failures.append(f"EP audit {filename} hash mismatch")
            if audit.ignored_warning_hits != 0:
                failures.append("EP audit records forbidden World-coordinate ignored warning")
            if not audit.completed:
                failures.append("EP audit is not marked completed")
            if failures:
                rep.add_fail("output_coordinates.ep_audit_replay", CheckLayer.INVARIANT, "; ".join(failures))
            else:
                rep.add_pass("output_coordinates.ep_audit_replay", CheckLayer.INVARIANT)
        except Exception as exc:  # noqa: BLE001
            rep.add_fail("output_coordinates.ep_audit_replay", CheckLayer.INVARIANT,
                         f"invalid/tampered output_coordinate_ep_audit.json: {exc}")
    return rep


def _error_report(stage: str, profile: str, run_profile: str, message: str) -> CheckReport:
    from src.validator.checks.schema import CheckLayer, CheckStatus

    rep = CheckReport(stage=stage, capability_profile=profile, run_profile=run_profile)
    rep.add(f"{stage}.build", CheckStatus.ERROR, CheckLayer.INVARIANT, message=message)
    return rep


def _finalize(res: CaseValidationResult, policy: RunPolicy | None = None) -> None:
    for key, rep in res.reports.items():
        for r in rep.blocking():
            res.blocking_summary.append(f"{key}: {r.check_id} — {r.message}")
    res.blocked = bool(res.blocking_summary)
    # confirmation policy: an unapproved geometry checkpoint may block
    if policy and res.geometry_digest is not None:
        if policy.confirmation_blocks(res.geometry_approved):
            res.blocked = True
            res.blocking_summary.append(
                "geometry checkpoint not approved (confirmation_policy=required)")


def _build_manifest(res: CaseValidationResult) -> RunManifest:
    m = RunManifest(case=res.case)
    for key, rep in res.reports.items():
        stage = key.split("::")[0]
        if stage in m.stages:
            continue
        m.accept(StageRecord(
            stage=stage, accepted_attempt=1,
            output_hash=hash_text(rep.model_dump_json()),
            check_passed=rep.passed,
            check_version=rep.results[0].check_version if rep.results else "1",
        ))
    return m


def _write(path: Path, rep: CheckReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rep.model_dump_json(indent=2), encoding="utf-8")
