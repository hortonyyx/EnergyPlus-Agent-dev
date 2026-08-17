"""Tests for the IDD-driven field-alignment gate (``mep.idd_field_alignment``).

This gate (摊 B, 2026-08-14) retires the "whack-a-mole" pattern: a missing
required field or a positional shift is caught for EVERY object type off the
authoritative IDD, not just People. Two criteria:

  (1) missing_required — an IDD \\required-field is absent or blank.
  (2) too_many_fields  — authored count > IDD count (extensible objects exempt).

Acceptance coverage:
  - B1 anti-fake-validation: each criterion is neutered once (neutralise the
    criterion → its lock goes red; restore → green).
  - B2 prescan reproduction: the red set over the historical artifacts matches
    the orchestrator's read-only prescan exactly.
  - tiering, extensible exemption, de-dup vs mep.people_field_alignment, and the
    §2.3 disease cross-references on load_to_schedule / hvac_schedule_refs.
"""

from __future__ import annotations

import json
import subprocess
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.validator.checks import mep as mepmod
from src.validator.checks.mep import check_mep
from src.validator.checks.schema import CheckLayer, CheckStatus
from src.validator.idf_fragments import IdfFragmentIndex, IdfObject

_ROOT = Path(__file__).resolve().parents[1]


def _result(rep, check_id):
    return next(r for r in rep.results if r.check_id == check_id)


def _blocking_ids(rep):
    return {r.check_id for r in rep.blocking()}


def _base_mep(*, hvac_specs="", people_specs="", schedule_specs=None) -> dict:
    if schedule_specs is None:
        schedule_specs = (
            "ScheduleTypeLimits,\n  Fr,\n  0,\n  1,\n  Continuous;\n\n"
            "Schedule:Compact,\n  Sch,\n  Fr,\n  Through: 12/31,\n"
            "  For: AllDays,\n  Until: 24:00,1.0;\n"
        )
    return {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": "", "construction_specs": "",
        "schedule_specs": schedule_specs,
        "hvac_specs": hvac_specs, "people_specs": people_specs, "lights_specs": "",
    }


# --------------------------------------------------------------------------- #
# clean / tiering
# --------------------------------------------------------------------------- #
def test_clean_mep_passes_idd_field_alignment():
    rep = check_mep(_base_mep())
    al = _result(rep, "mep.idd_field_alignment")
    assert al.status == CheckStatus.PASS
    assert al.evidence["criteria"]  # pass evidence still documents the criteria


def test_non_blocklist_missing_required_flags_but_does_not_block():
    """ZoneControl:Thermostat (model-authored, NOT on the block list) missing its
    required 'Control 1 Name' → FLAG (CROSS_CHECK), never BLOCK."""
    hvac = (
        "ZoneControl:Thermostat,\n"
        "  T1,\n"          # A1 Name
        "  Z1,\n"          # A2 Zone
        "  Sch,\n"         # A3 Control Type Schedule Name (defined above)
        "  ThermostatSetpoint:DualSetpoint;\n"  # A4 Control 1 Object Type; A5 missing
    )
    rep = check_mep(_base_mep(hvac_specs=hvac))
    al = _result(rep, "mep.idd_field_alignment")
    assert al.status == CheckStatus.FAIL
    assert al.layer == CheckLayer.CROSS_CHECK
    offenders = al.evidence["offenders"]
    assert len(offenders) == 1
    assert offenders[0]["kind"] == "missing_required"
    assert offenders[0]["field"] == "Control 1 Name"
    assert offenders[0]["object_type"] == "ZONECONTROL:THERMOSTAT"
    # advisory → never blocks
    assert "mep.idd_field_alignment" not in _blocking_ids(rep)
    assert rep.passed


def test_blocklist_missing_required_blocks():
    """HVACTemplate:Zone:IdealLoadsAirSystem (deterministic-code, block list)
    missing its required 'Zone Name' → BLOCK (a code bug)."""
    hvac = "HVACTemplate:Zone:IdealLoadsAirSystem,\n  ,\n  Tstat,\n  Sch;\n"
    rep = check_mep(_base_mep(hvac_specs=hvac))
    al = _result(rep, "mep.idd_field_alignment")
    assert al.status == CheckStatus.FAIL
    assert al.layer == CheckLayer.INVARIANT
    assert "mep.idd_field_alignment" in _blocking_ids(rep)
    assert al.evidence["offenders"][0]["field"] == "Zone Name"
    assert al.evidence["block_offenders_count"] == 1


def test_blocklist_and_non_blocklist_mix_chooses_invariant_layer():
    """A run with BOTH a block-list offender and an advisory offender still
    BLOCKs (the block-list offender governs the layer); the advisory offender is
    reported in the same result, not silently dropped."""
    hvac = (
        # block-list type, missing Zone Name
        "HVACTemplate:Zone:IdealLoadsAirSystem,\n  ,\n  Tstat,\n  Sch;\n\n"
        # non-block-list type, missing Control 1 Name
        "ZoneControl:Thermostat,\n  T1,\n  Z1,\n  Sch,\n  ThermostatSetpoint:DualSetpoint;\n"
    )
    rep = check_mep(_base_mep(hvac_specs=hvac))
    al = _result(rep, "mep.idd_field_alignment")
    assert al.layer == CheckLayer.INVARIANT
    assert "mep.idd_field_alignment" in _blocking_ids(rep)
    types = {o["object_type"] for o in al.evidence["offenders"]}
    assert "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM" in types
    assert "ZONECONTROL:THERMOSTAT" in types


# --------------------------------------------------------------------------- #
# extensible exemption + criterion (2) too_many_fields (B1)
# --------------------------------------------------------------------------- #
def test_extensible_object_not_flagged_for_too_many_fields():
    """Schedule:Compact is \\extensible:1 (eppy expands to a 10000-field cap); an
    authored instance with dozens of Through/For/Until rows must NOT be flagged
    too_many_fields — the count is variable by design."""
    schedule = (
        "ScheduleTypeLimits,\n  Fr,\n  0,\n  1,\n  Continuous;\n\n"
        "Schedule:Compact,\n  ManyRows,\n  Fr,\n  Through: 12/31,\n  For: AllDays,\n"
        + "".join(f"  Until: {h:02d}:00,{h % 3},\n" for h in range(1, 24))
        + "  Until: 24:00,1.0;\n"
    )
    rep = check_mep(_base_mep(schedule_specs=schedule))
    al = _result(rep, "mep.idd_field_alignment")
    # only the Schedule:Compact Name is required; it is present → PASS
    assert al.status == CheckStatus.PASS


def test_b1_criterion2_too_many_fields_lock_and_neuter():
    """B1 criterion 2: too_many_fields.

    eppy STRUCTURALLY CANNOT produce an over-field object on the real parse path
    (it silently truncates, e.g. Lights, or raises TypeError → mep.idf_parse
    ERROR, e.g. Material/Construction). So no real artifact can reach this
    branch. We construct an IdfObject directly (SimpleNamespace fake raw) with
    authored=10 > IDD=9, non-extensible, to prove the branch logic AND that
    neutralising it turns the lock red.

    Lock (green): too_many_fields fires. Neuter (force extensible → exempt): the
    finding disappears → the green assertion would fail if the branch were dead.
    """
    fake_raw = SimpleNamespace(objidd=[
        {"group": "g"},  # head: no 'extensible:' key ⇒ non-extensible
        {"field": ["Name"], "required-field": True},
        *({"field": [f"F{i}"]} for i in range(1, 9)),  # 8 optional fields ⇒ IDD = 9
    ])
    obj = IdfObject(
        obj_type="MATERIAL", name="M",
        fields=["M"] + [f"v{i}" for i in range(1, 10)],  # 10 authored (> 9)
        raw=fake_raw,
    )
    idx = IdfFragmentIndex(objects=[obj])

    # lock: too_many_fields fires
    findings, _ = mepmod._idd_field_findings(idx)
    too_many = [f for f in findings if f["kind"] == "too_many_fields"]
    assert len(too_many) == 1
    assert too_many[0]["authored_field_count"] == 10
    assert too_many[0]["idd_field_count"] == 9

    # B1 neuter: force every object to look extensible ⇒ too_many_fields exempt
    real_meta = mepmod._idd_object_meta

    def neutered(raw):
        m = real_meta(raw)
        if m is None:
            return None
        return m[0], m[1], 2  # claim extensible group 2

    orig = mepmod._idd_object_meta
    mepmod._idd_object_meta = neutered
    try:
        findings2, _ = mepmod._idd_field_findings(idx)
        assert not any(f["kind"] == "too_many_fields" for f in findings2), (
            "neutered extensible exemption still reported too_many_fields — branch not gated"
        )
    finally:
        mepmod._idd_object_meta = orig


# --------------------------------------------------------------------------- #
# criterion (1) missing_required (B1) + de-dup vs people_field_alignment (§2.4)
# --------------------------------------------------------------------------- #
def test_b1_criterion1_missing_required_lock_and_neuter(monkeypatch):
    """B1 criterion 1: missing_required.

    Lock (green): a ZoneControl:Thermostat missing 'Control 1 Name' produces a
    missing_required finding. Neuter (mark no field required): the finding
    disappears → the green assertion would fail if criterion 1 were dead code.
    """
    hvac = (
        "ZoneControl:Thermostat,\n  T1,\n  Z1,\n  Sch,\n"
        "  ThermostatSetpoint:DualSetpoint;\n"
    )
    rep = check_mep(_base_mep(hvac_specs=hvac))
    al = _result(rep, "mep.idd_field_alignment")
    assert al.status == CheckStatus.FAIL
    assert any(o["kind"] == "missing_required" and o["field"] == "Control 1 Name"
               for o in al.evidence["offenders"])

    real_meta = mepmod._idd_object_meta

    def neutered(raw):
        m = real_meta(raw)
        if m is None:
            return None
        return [(name, False) for name, _ in m[0]], m[1], m[2]

    monkeypatch.setattr(mepmod, "_idd_object_meta", neutered)
    rep2 = check_mep(_base_mep(hvac_specs=hvac))
    al2 = _result(rep2, "mep.idd_field_alignment")
    assert not any(o["kind"] == "missing_required"
                   for o in al2.evidence.get("offenders", [])), (
        "neutered required-field detection still reported missing_required — criterion 1 not gated"
    )


def test_people_missing_required_does_not_restate_misalignment():
    """§2.4 de-dup: when a People object is misaligned (A4 = schedule name,
    A5 blank), mep.people_field_alignment owns the misalignment DISEASE (A4
    non-enum). mep.idd_field_alignment reports the same root cause from the
    generic IDD angle (A5 required field blank) and does NOT re-state the
    misalignment — different cells, so 'field misalignment' is never counted
    twice for one People object. people_dedup_note makes it explicit."""
    people = (
        # Real LLM failure shape: Sch_Activity occupies A4 (calc method), A5 blank
        "People,\n  P1,\n  Z1,\n  Sch,\n  Sch,\n  Area/Person,\n  10,\n  0.3,\n  ,\n  ;\n"
    )
    sched = (
        "ScheduleTypeLimits,\n  Fr,\n  0,\n  1,\n  Continuous;\n\n"
        "ScheduleTypeLimits,\n  Any,\n  ,\n  ,\n  Continuous;\n\n"
        "Schedule:Compact,\n  Sch,\n  Fr,\n  Through: 12/31,\n  For: AllDays,\n"
        "  Until: 24:00,1.0;\n"
    )
    rep = check_mep(_base_mep(people_specs=people, schedule_specs=sched), zone_names={"Z1"})
    al = _result(rep, "mep.idd_field_alignment")
    pfa = _result(rep, "mep.people_field_alignment")
    # both report the same People, but different cells
    assert al.status == CheckStatus.FAIL
    people_offenders = [o for o in al.evidence["offenders"] if o["object_type"] == "PEOPLE"]
    assert people_offenders and people_offenders[0]["field"] == "Activity Level Schedule Name"
    # the gate does NOT carry the misalignment reason/diagnostic keys
    assert "reason" not in people_offenders[0]
    assert "field_A4_Number_of_People_Calculation_Method" not in people_offenders[0]
    # people_field_alignment still owns the misalignment disease
    assert pfa.status == CheckStatus.FAIL
    assert pfa.evidence["offenders"][0]["reason"] == "activity_schedule_misplaced_into_calc_method_slot"
    assert "people_dedup_note" in al.evidence


# --------------------------------------------------------------------------- #
# §2.3 disease cross-references on the symptom checks
# --------------------------------------------------------------------------- #
def test_load_to_schedule_attaches_disease_ref_for_people():
    """§2.3: when load_to_schedule reports a People symptom AND the same object is
    flagged by idd_field_alignment (the disease), the offender carries a
    disease_ref naming the missing IDD field + the new check id."""
    # People A4 = People (legal), A5 blank (Activity Level Schedule Name missing)
    people = "People,\n  P1,\n  Z1,\n  Sch,\n  People,\n  1,\n  ,\n  ,\n  0.3;\n"
    rep = check_mep(_base_mep(people_specs=people), zone_names={"Z1"})
    load = _result(rep, "mep.load_to_schedule")
    assert load.status == CheckStatus.FAIL
    off = load.evidence["offenders"][0]
    assert off["disease_ref"] == {
        "check_id": "mep.idd_field_alignment",
        "missing_field": "Activity Level Schedule Name",
    }
    assert "disease_cross_ref" in load.evidence


def test_hvac_schedule_refs_attaches_disease_ref_for_shifted_thermostat():
    """§2.3: when hvac_schedule_refs reports an undefined schedule reference that
    is really a positional shift (object-type name in a schedule slot) AND the
    same object is flagged by idd_field_alignment, the offender carries a
    disease_ref. Mirrors the accept_C failure shape."""
    hvac = (
        # Control Type Schedule Name holds an object-type name (shifted), and the
        # shift has dropped Control 1 Name off the end
        "ZoneControl:Thermostat,\n  T1,\n  Z1,\n  ThermostatSetpoint:DualSetpoint,\n"
        "  Dual;\n\n"
        "ThermostatSetpoint:DualSetpoint,\n  Dual,\n  Sch,\n  Sch;\n"
    )
    rep = check_mep(_base_mep(hvac_specs=hvac))
    hvac_res = _result(rep, "mep.hvac_schedule_refs")
    assert hvac_res.status == CheckStatus.FAIL
    tstat_offenders = [o for o in hvac_res.evidence["offenders"]
                       if o["object_type"] == "ZONECONTROL:THERMOSTAT"]
    assert tstat_offenders
    assert tstat_offenders[0]["disease_ref"]["check_id"] == "mep.idd_field_alignment"
    assert tstat_offenders[0]["disease_ref"]["missing_field"] == "Control 1 Name"


# --------------------------------------------------------------------------- #
# B2 — prescan reproduction (the red set over historical artifacts)
# --------------------------------------------------------------------------- #
# Object-level counts from prescan_output.md (flagged = objects with ≥1 finding).
# smalloffice_23 is NOT here: its 4_mep/ is .gitignore'd (line 320), so it exists
# only as an untracked temp file in the orchestrator's main worktree, not in a
# clean checkout. Its 9-People-missing-A5 shape is covered by opus_e2e /
# gpt54_reading / gpt54mini / probe_a_legacy below (same People defect).
# Enumeration is git-tracked only (see _artifact_runs), so smalloffice_23/4_mep
# is never enumerated as a tracked artifact; if it IS present on disk it is
# skipped with a recorded reason (see _untracked_mep_outputs), not hard-failed.
_PRESCAN_OBJECT_LEVEL = {
    "sm20_anchor/run_2026-06-15_baseline": 19,
    "sm21_anchor/run_2026-06-16_opus_e2e": 14,
    "sm21_anchor/run_2026-06-20_gpt54_reading": 14,
    "sm21_anchor/run_2026-06-23_gpt54mini_reading": 14,
    "sm21_anchor/run_2026-07-01_sonnet_e2e_r1": 42,
    "sm21_anchor/run_2026-07-02_sonnet_flow_e2e": 14,
    "sm21_anchor/run_2026-08-05_probe_a_legacy_snapped": 14,
    "sm21_anchor/run_2026-08-09_f18_e2e_verify": 14,
    "sm21_anchor/run_2026-08-13_accept_C": 14,
    "sm21_anchor/run_2026-08-13_batchI_accept_02": 14,
    "sm21_anchor/run_2026-08-13_oneshot_acceptance": 28,
    "sm21_anchor/run_2026-08-13_post_blocker1_e2e": 14,
    "sm21_anchor/run_2026-08-13_surface400_accept_01": 28,
    "sm24_anchor/run_2026-06-24_opus_reading": 22,
}
_PRESCAN_GREEN = {
    "sm21_anchor/run_2026-07-01_sonnet_e2e_r2",
    "sm21_anchor/run_2026-08-06_wall3_a_retest",
    "sm21_anchor/run_2026-08-07_f13_e2e_verify",
    "sm21_anchor/run_2026-08-11_continuous_e2e",
    "sm21_anchor/run_2026-08-13_accept_B",
    "sm21_anchor/run_2026-08-13_batchI_accept_01",
    # accept_D/E/F (F-36): committed in dc7b239 (2026-08-14 acceptance-3/3
    # wrap-up), AFTER this table was last touched (fb171ec, earlier the same
    # day) — the table was simply never updated for them, not a gate drift.
    # Classified GREEN from two independent measurements, not by assumption:
    # (1) the real gate (mep.idd_field_alignment via check_mep) reports PASS,
    #     0 offenders, for all three;
    # (2) the original prescan probe (probe_arity.py, byte-identical to the
    #     08-14 run — no commit has touched src/validator/checks/mep.py's
    #     _idd_field_findings since 1472cfc introduced this gate) reports
    #     flagged=0 / 67 objects clean for all three, re-run standalone.
    # Both agree, so no prescan-vs-gate discrepancy to escalate.
    "sm21_anchor/run_2026-08-14_accept_D",
    "sm21_anchor/run_2026-08-14_accept_E",
    "sm21_anchor/run_2026-08-14_accept_F",
}


_E2E_BASE = _ROOT / "case_tests" / "e2e_tests"


def _artifact_runs():
    """git-TRACKED ``4_mep/mep_output.json`` under ``case_tests/e2e_tests``.

    Enumerated via ``git ls-files``, NOT a filesystem glob, so the fixture set
    is a property of the COMMIT: identical between a clean checkout and a dev
    machine that carries untracked temp artifacts on disk. This is the F-23
    shape (08-12: ``test_c2_b4b_phase_d`` asserted ``git diff`` was empty and so
    tested working-tree state, not commit content) — a plain glob would pick up
    ``smalloffice_23/4_mep/``, which is ``.gitignore``'d (line 320) and exists
    only as an untracked temp file in the orchestrator's main worktree, then
    hard-fail on it. Routing enumeration through git keeps the assertion honest
    in both environments. The label is computed with the same
    ``p.parent.parent.relative_to(base)`` rule as before (so ``<anchor>/<run>``
    or ``<run>``), guaranteeing the existing table keys still match.

    Artifacts that ARE on disk but untracked are surfaced separately by
    ``_untracked_mep_outputs`` so they get an explicit skip-with-reason, never
    a silent drop.
    """
    proc = subprocess.run(
        ["git", "ls-files", "--", "case_tests/e2e_tests"],
        cwd=_ROOT, capture_output=True, text=True, check=True,
    )
    runs: dict[str, Path] = {}
    for line in proc.stdout.splitlines():
        if not line.endswith("4_mep/mep_output.json"):
            continue
        p = _ROOT / line
        runs[p.parent.parent.relative_to(_E2E_BASE).as_posix()] = p
    return runs


def _untracked_mep_outputs(tracked: dict[str, Path]) -> list[Path]:
    """``4_mep/mep_output.json`` present on disk but NOT tracked by git.

    These are dev-machine-only temp artifacts (e.g. ``smalloffice_23/4_mep/``,
    ``.gitignore``'d). The gate's red set is defined over TRACKED artifacts, so
    these are skipped — but never silently: the caller records each via a
    warning so the exclusion is visible in the pytest summary (a plain glob in
    ``_artifact_runs`` would instead hard-fail on them).
    """
    on_disk: set[Path] = set()
    for pat in ("*/*/4_mep/mep_output.json", "*/4_mep/mep_output.json"):
        for p in _E2E_BASE.glob(pat):
            on_disk.add(p.resolve())
    tracked_resolved = {p.resolve() for p in tracked.values()}
    return sorted(on_disk - tracked_resolved)


def test_b2_prescan_reproduction():
    """B2: the gate's red set over the git-TRACKED historical artifacts matches
    the orchestrator's read-only prescan exactly. Object-level counts (objects
    with ≥1 finding) match prescan_output.md; this gate reports field-level
    offenders so sm24 opus_reading (thermostats missing 3 cells each) shows 44
    field-level findings == 22 object-level.

    The fixture set is enumerated off ``git ls-files`` (see ``_artifact_runs``),
    so it is a property of the commit, not the working tree. Untracked
    artifacts present on disk (e.g. ``smalloffice_23/4_mep/``, ``.gitignore``'d)
    are explicitly skipped with a recorded reason — never silently dropped —
    while a TRACKED artifact missing from the table still hard-fails."""
    runs = _artifact_runs()
    assert runs, "no git-tracked 4_mep artifacts found under case_tests/e2e_tests"
    # Untracked dev-machine artifacts are explicitly skipped with a reason
    # (F-23): their presence is a working-tree property, not a commit one, so
    # it must not turn this assertion red — but it must not be invisible either,
    # hence the warning surfacing the skip in the pytest summary.
    untracked = _untracked_mep_outputs(runs)
    if untracked:
        reasons = [
            f"  - {p.relative_to(_E2E_BASE.resolve()).as_posix()} "
            "(untracked dev-only temp artifact; .gitignore'd, not in this commit)"
            for p in untracked
        ]
        warnings.warn(
            "B2: skipped %d untracked 4_mep artifact(s) not part of this "
            "commit:\n%s" % (len(untracked), "\n".join(reasons)),
            stacklevel=2,
        )
    for label, path in runs.items():
        mep = json.loads(path.read_text())
        rep = check_mep(mep)
        al = _result(rep, "mep.idd_field_alignment")
        offenders = al.evidence.get("offenders", [])
        # object-level count = distinct objects with a finding
        obj_level = len({(o["object_type"], o["object"]) for o in offenders})
        if label in _PRESCAN_OBJECT_LEVEL:
            assert al.status == CheckStatus.FAIL, f"{label} should be RED per prescan"
            assert obj_level == _PRESCAN_OBJECT_LEVEL[label], (
                f"{label}: object-level {obj_level} != prescan {_PRESCAN_OBJECT_LEVEL[label]}"
            )
        elif label in _PRESCAN_GREEN:
            assert al.status == CheckStatus.PASS, (
                f"{label} should be GREEN per prescan, got FAIL: {offenders}"
            )
        else:
            pytest.fail(
                f"{label}: tracked but not classified in prescan fixture table"
            )
    # the accept_C thermostat disease (14 × Control 1 Name) MUST be caught
    accept_c = runs["sm21_anchor/run_2026-08-13_accept_C"]
    rep = check_mep(json.loads(accept_c.read_text()))
    al = _result(rep, "mep.idd_field_alignment")
    fields = {o["field"] for o in al.evidence["offenders"]}
    assert "Control 1 Name" in fields
    assert al.evidence["findings_by_kind"]["missing_required"] == 14
