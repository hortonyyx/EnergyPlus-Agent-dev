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
from src.agent.execution.manifest import RunManifest, StageRecord, hash_text
from src.agent.execution.policy import RunPolicy, ValidationScope
from src.agent.state import IntakeOutput
from src.validator.checks.assembly import check_assembly, check_ep_baseline
from src.validator.checks.correction import check_correction
from src.validator.checks.kernel import check_kernel
from src.validator.checks.mep import check_mep
from src.validator.checks.reading import check_reading_view
from src.validator.checks.schema import CheckReport


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
    plans = data.get("Floor plans") or []
    totals = [p.get("thermal_zones") for p in plans if isinstance(p.get("thermal_zones"), int)]
    return sum(totals) if totals else None


def validate_case(
    case_dir: Path | str,
    *,
    policy: RunPolicy | None = None,
    write_reports: bool = False,
) -> CaseValidationResult:
    case_dir = Path(case_dir)
    policy = policy or RunPolicy()
    res = CaseValidationResult(case=case_dir.name)
    profile = policy.capability_profile

    if policy.validation_scope == ValidationScope.DOWNSTREAM_ONLY:
        _validate_downstream_only(case_dir, res, profile, write_reports)
        _finalize(res)
        return res

    # ---- 0_reading ----
    rdir = case_dir / "0_reading"
    if rdir.exists():
        from src.agent.reading import load_reading_view

        for vj in sorted(rdir.glob("*_view.json")):
            view = load_reading_view(vj)
            rep = check_reading_view(view, capability_profile=profile)
            res.reports[f"0_reading::{vj.stem}"] = rep
            if write_reports:
                _write(rdir / f"{vj.stem}_checks.json", rep)

    # ---- 1_correction (+ rebuild kernel for 2/3) ----
    snapped = case_dir / "1_correction" / "correction_geometry_snapped.json"
    bg = None
    used_constructions: set[str] = set()
    zone_names: set[str] = set()
    if snapped.exists():
        geom = CorrectedGeometry.model_validate_json(snapped.read_text())
        relied = (case_dir / "case_data" / "testdata_prompt.json").exists()
        crep = check_correction(
            geom, expected_zone_total=_expected_zone_total(case_dir),
            relied_on_testdata=relied, capability_profile=profile,
        )
        res.reports["1_correction"] = crep
        if write_reports:
            _write(case_dir / "1_correction" / "correction_checks.json", crep)

        # 2/3 kernel — rebuild the authoritative geometry from the snapped cells.
        try:
            from src.agent.geometry import build_geometry
            from src.agent.geometry.specs import serialize_geometry

            bg = build_geometry(geom)
            krep = check_kernel(bg, capability_profile=profile)
            res.reports["2_modelling"] = krep
            if write_reports:
                _write(case_dir / "2_modelling" / "kernel_checks.json", krep)
            _, _, _, used_constructions = serialize_geometry(bg)
            zone_names = set(dict.fromkeys(bg.zones))
        except Exception as e:  # noqa: BLE001 — recorded as a blocking error report
            res.reports["2_modelling"] = _error_report("2_modelling", profile,
                                                        f"kernel build failed: {e}")

    # ---- 4_mep ----
    mep_path = case_dir / "4_mep" / "mep_output.json"
    if mep_path.exists():
        mep = json.loads(mep_path.read_text())
        mrep = check_mep(mep, used_constructions=used_constructions or None,
                         zone_names=zone_names or None, capability_profile=profile)
        res.reports["4_mep"] = mrep
        if write_reports:
            _write(case_dir / "4_mep" / "mep_checks.json", mrep)

    # ---- 5_intakeoutput backstop ----
    intake_path = case_dir / "5_intakeoutput" / "intake_output.json"
    if intake_path.exists() and used_constructions:
        intake = IntakeOutput.model_validate_json(intake_path.read_text())
        arep = check_assembly(intake, used_constructions, capability_profile=profile)
        res.reports["5_intakeoutput"] = arep
        if write_reports:
            _write(case_dir / "5_intakeoutput" / "assembly_checks.json", arep)

    # ---- EP baseline (if a run exists) ----
    ep_run = case_dir / "EP" / "EP_run"
    if (ep_run / "eplusout.end").exists():
        eprep = check_ep_baseline(ep_run, capability_profile=profile)
        res.reports["downstream"] = eprep

    # ---- geometry approval digest + confirmation policy ----
    if bg is not None and "2_modelling" in res.reports:
        bg_dict = json.loads((case_dir / "2_modelling" / "building_geometry.json").read_text()) \
            if (case_dir / "2_modelling" / "building_geometry.json").exists() else {}
        specs_path = case_dir / "3_split_pairing" / "geometry_specs.md"
        specs = specs_path.read_text() if specs_path.exists() else ""
        kreport = res.reports["2_modelling"].model_dump()
        res.geometry_digest = geometry_checkpoint_digest(
            building_geometry=bg_dict, geometry_specs=specs, kernel_check_report=kreport,
        )
        res.geometry_approved = is_approved(case_dir, res.geometry_digest)

    _finalize(res, policy)
    if write_reports:
        _build_manifest(case_dir, res).save(case_dir)
    return res


def _validate_downstream_only(
    case_dir: Path, res: CaseValidationResult, profile: str, write_reports: bool
) -> None:
    """--intake-from: only the supplied IntakeOutput is validated (Pydantic)."""
    intake_path = case_dir / "5_intakeoutput" / "intake_output.json"
    if not intake_path.exists():
        intake_path = case_dir / "EP" / "intake_output.json"
    rep = CheckReport(stage="5_intakeoutput", capability_profile=profile)
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


def _error_report(stage: str, profile: str, message: str) -> CheckReport:
    from src.validator.checks.schema import CheckLayer, CheckStatus

    rep = CheckReport(stage=stage, capability_profile=profile)
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


def _build_manifest(case_dir: Path, res: CaseValidationResult) -> RunManifest:
    m = RunManifest(case=case_dir.name)
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
