"""M0 acceptance tests (build plan §2.1 row M0).

Covers: append-only attempts (rejected drafts never overwrite, accepted pointer
+ hashes correct); full invalidation DAG (0→1-5 … 4→5) + global budget + route
cycle detection; approval-after-resume does not re-run 1/2/3 and the digest goes
stale on drift; CheckReport v2 policy-vs-fact separation (same check id can be
not_applicable under a profile rather than blocking).
"""

from __future__ import annotations

import pytest

from src.agent.execution import (
    BudgetExceeded,
    Capability,
    GeometryApproval,
    RouteCycleDetected,
    RunBudget,
    RunManifest,
    RunPolicy,
    StageRecord,
    StageRunner,
    downstream_of,
    geometry_checkpoint_digest,
    invalidate,
    is_approved,
    run_meta_path,
    stages_to_run,
)
from src.agent.execution.manifest import next_attempt_index
from src.agent.execution.policy import ConfirmationPolicy
from src.validator.checks import (
    CheckLayer,
    CheckReport,
    CheckStatus,
    Disposition,
    disposition,
)


# --------------------------------------------------------------------------- #
# append-only attempts
# --------------------------------------------------------------------------- #
def test_append_only_rejected_does_not_overwrite(tmp_path):
    manifest = RunManifest(case="t")
    runner = StageRunner(tmp_path, manifest)
    sdir = tmp_path / "2_modelling"

    # A failing (blocking) deterministic attempt — recorded but not accepted.
    bad = CheckReport(stage="2_modelling")
    bad.add_fail("zone_closed", CheckLayer.INVARIANT, "missing ceiling")
    r1 = runner.record(
        stage="2_modelling", stage_dir=sdir, output_obj={"v": 1}, report=bad
    )
    assert r1.attempt_index == 1
    assert r1.accepted is False
    assert manifest.accepted("2_modelling") is None  # not pointed at

    # A clean attempt — fresh dir (002), accepted, pointer set.
    good = CheckReport(stage="2_modelling")
    good.add_pass("zone_closed", CheckLayer.INVARIANT)
    r2 = runner.record(
        stage="2_modelling", stage_dir=sdir, output_obj={"v": 2}, report=good
    )
    assert r2.attempt_index == 2
    assert r2.accepted is True

    # Both attempt dirs survive on disk (append-only).
    assert (sdir / "attempts" / "001" / "output.json").read_text().strip() != ""
    assert (sdir / "attempts" / "002" / "output.json").read_text().strip() != ""
    rec = manifest.accepted("2_modelling")
    assert rec is not None and rec.accepted_attempt == 2
    assert rec.output_hash == r2.output_hash
    assert next_attempt_index(sdir) == 3  # monotonic


def test_manifest_roundtrip(tmp_path):
    (tmp_path / "run_manifest.json").write_text('{"case":"stale_root","stages":{}}')
    m = RunManifest(case="t")
    m.accept(StageRecord(stage="1_correction", accepted_attempt=1, output_hash="abc"))
    path = m.save(tmp_path)
    assert path == run_meta_path(tmp_path, "run_manifest.json")
    assert path.exists()
    m2 = RunManifest.load(tmp_path)
    assert m2.accepted("1_correction").output_hash == "abc"
    assert m2.case == "t"


def test_manifest_filename_override_uses_run_meta_dir(tmp_path):
    m = RunManifest(case="t")
    path = m.save(tmp_path, filename="validation_manifest.json")
    assert path == run_meta_path(tmp_path, "validation_manifest.json")
    assert path.exists()
    assert not (tmp_path / "validation_manifest.json").exists()


# --------------------------------------------------------------------------- #
# invalidation DAG
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "stage,expected",
    [
        ("0_reading", ["1_correction", "2_modelling", "3_split_pairing", "4_mep", "5_intakeoutput"]),
        ("1_correction", ["2_modelling", "3_split_pairing", "4_mep", "5_intakeoutput"]),
        ("2_modelling", ["3_split_pairing", "4_mep", "5_intakeoutput"]),
        ("3_split_pairing", ["4_mep", "5_intakeoutput"]),
        ("4_mep", ["5_intakeoutput"]),
        ("5_intakeoutput", []),
    ],
)
def test_full_invalidation_dag(stage, expected):
    assert downstream_of(stage) == expected


def test_invalidate_drops_downstream_pointers():
    m = RunManifest(case="t")
    for s in ["0_reading", "1_correction", "2_modelling", "3_split_pairing", "4_mep", "5_intakeoutput"]:
        m.accept(StageRecord(stage=s, accepted_attempt=1, output_hash=s))
    dropped = invalidate(m, "1_correction")
    assert dropped == ["2_modelling", "3_split_pairing", "4_mep", "5_intakeoutput"]
    assert set(m.stages) == {"0_reading", "1_correction"}


def test_resume_reuses_unchanged_does_not_rerun_geometry():
    """After approving geometry, a resume with unchanged inputs must NOT re-run
    1_correction / 2_modelling / 3_split_pairing (re-verify must-fix)."""
    m = RunManifest(case="t")
    inputs = {
        "1_correction": {"0_reading": "h0"},
        "2_modelling": {"1_correction": "h1"},
        "3_split_pairing": {"2_modelling": "h2"},
        "4_mep": {"3_split_pairing": "h3"},
        "5_intakeoutput": {"3_split_pairing": "h3", "4_mep": "h4"},
    }
    for s, ih in inputs.items():
        m.accept(StageRecord(stage=s, accepted_attempt=1, output_hash=s, input_hashes=ih))
    m.accept(StageRecord(stage="0_reading", accepted_attempt=1, output_hash="r0"))
    # Nothing drifted → nothing re-runs.
    assert stages_to_run(m, {"0_reading": {}, **inputs}) == []

    # Drift only 4_mep's own input set (e.g. re-author MEP) → only 4 and 5 re-run,
    # geometry stays cached.
    inputs2 = dict(inputs)
    inputs2["4_mep"] = {"3_split_pairing": "h3-DIFFERENT"}
    rerun = stages_to_run(m, {"0_reading": {}, **inputs2})
    assert rerun == ["4_mep", "5_intakeoutput"]


def test_resume_upstream_drift_contaminates_downstream():
    m = RunManifest(case="t")
    inputs = {
        "1_correction": {"0_reading": "h0"},
        "2_modelling": {"1_correction": "h1"},
        "3_split_pairing": {"2_modelling": "h2"},
        "4_mep": {"3_split_pairing": "h3"},
        "5_intakeoutput": {"3_split_pairing": "h3", "4_mep": "h4"},
    }
    for s, ih in inputs.items():
        m.accept(StageRecord(stage=s, accepted_attempt=1, output_hash=s, input_hashes=ih))
    m.accept(StageRecord(stage="0_reading", accepted_attempt=1, output_hash="r0"))
    # 1_correction's input changed → 1 and everything downstream re-run (contagion).
    drift = {"0_reading": {}, "1_correction": {"0_reading": "h0-DIFFERENT"}, **{
        k: v for k, v in inputs.items() if k != "1_correction"}}
    rerun = stages_to_run(m, drift)
    assert rerun == ["1_correction", "2_modelling", "3_split_pairing", "4_mep", "5_intakeoutput"]


# --------------------------------------------------------------------------- #
# budget + cycle
# --------------------------------------------------------------------------- #
def test_per_stage_and_global_draw_budget():
    b = RunBudget(per_stage_draws=3, global_draws=5)
    for _ in range(3):
        b.charge_draw("1_correction")
    with pytest.raises(BudgetExceeded):
        b.charge_draw("1_correction")  # 4th on same stage
    # global cap
    b2 = RunBudget(per_stage_draws=10, global_draws=2)
    b2.charge_draw("a")
    b2.charge_draw("b")
    with pytest.raises(BudgetExceeded):
        b2.charge_draw("c")


def test_route_cycle_detection():
    b = RunBudget(max_routes_to_stage=2)
    b.charge_route("1_correction")
    b.charge_route("1_correction")
    with pytest.raises(RouteCycleDetected):
        b.charge_route("1_correction")


def test_judge_budget():
    b = RunBudget(global_judges=1)
    b.charge_judge()
    with pytest.raises(BudgetExceeded):
        b.charge_judge()


# --------------------------------------------------------------------------- #
# geometry approval digest
# --------------------------------------------------------------------------- #
def test_approval_digest_stable_and_drift_sensitive(tmp_path):
    bg = {"zones": ["A", "B"]}
    specs = "# zone_specs\nA\nB\n"
    report = {"results": []}
    d1 = geometry_checkpoint_digest(
        building_geometry=bg, geometry_specs=specs, kernel_check_report=report
    )
    d2 = geometry_checkpoint_digest(
        building_geometry=bg, geometry_specs=specs, kernel_check_report=report
    )
    assert d1 == d2  # deterministic

    GeometryApproval(digest=d1, actor="op").save(tmp_path)
    assert is_approved(tmp_path, d1)

    # Drift the geometry → approval is automatically stale.
    d_drift = geometry_checkpoint_digest(
        building_geometry={"zones": ["A", "B", "C"]},
        geometry_specs=specs,
        kernel_check_report=report,
    )
    assert d_drift != d1
    assert not is_approved(tmp_path, d_drift)


def test_confirmation_policy_blocking():
    req = RunPolicy(confirmation_policy=ConfirmationPolicy.REQUIRED)
    assert req.confirmation_blocks(approved=False) is True
    assert req.confirmation_blocks(approved=True) is False
    for p in (ConfirmationPolicy.OPTIONAL, ConfirmationPolicy.DISABLED):
        assert RunPolicy(confirmation_policy=p).confirmation_blocks(approved=False) is False


# --------------------------------------------------------------------------- #
# CheckReport v2 — policy vs fact separation
# --------------------------------------------------------------------------- #
def test_invariant_fail_blocks_crosscheck_flags():
    rep = CheckReport(stage="2_modelling")
    rep.add_fail("zone_closed", CheckLayer.INVARIANT, "missing face")
    rep.add_fail("dim_chain", CheckLayer.CROSS_CHECK, "sum != total")
    rep.add_pass("normals", CheckLayer.INVARIANT)
    assert len(rep.blocking()) == 1
    assert rep.blocking()[0].check_id == "zone_closed"
    assert len(rep.flagged()) == 1
    assert rep.passed is False


def test_not_applicable_does_not_block_same_check_id():
    """Same check id: blocks when it FAILs (rectangular), informational when
    NOT_APPLICABLE (non-rectangular profile) — policy ≠ fact."""
    rect = CheckReport(stage="2_modelling", capability_profile="rectangular")
    rect.add_fail("coverage_completeness", CheckLayer.INVARIANT, "hole")
    assert rect.blocking() and not rect.passed

    nonrect = CheckReport(stage="2_modelling", capability_profile="nonrectangular")
    nonrect.add("coverage_completeness", CheckStatus.NOT_APPLICABLE, CheckLayer.INVARIANT)
    assert not nonrect.blocking() and nonrect.passed


def test_error_status_is_fail_closed():
    r = CheckReport(stage="4_mep")
    r.add("idf_parse", CheckStatus.ERROR, CheckLayer.INVARIANT, message="parser crashed")
    assert disposition(r.results[0]) == Disposition.BLOCK
    assert not r.passed
