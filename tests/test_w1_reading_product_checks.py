"""W#1: all reading check entrances dispatch before legacy defaults apply."""
import json
from pathlib import Path

import pytest

from src.agent.execution.evidence_preflight import compute_reading_report_from_vector_dir
from src.agent.execution.validation_run import validate_case
from src.agent.execution.view_manifest import build_view_manifest
from src.agent.reading import parse_reading_view
from src.validator.checks.reading import check_reading_view
from src.validator.checks.reading_product import check_reading_product
from src.validator.checks.schema import CheckStatus
from src.validator.checks.view_manifest import check_reading_stage

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "case_tests/e2e_tests/sm25-L_anchor"
PRODUCTS = ROOT / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
FILES = {"1f_view": "sm25_1f_v2.json", "2f_view": "sm25_2f_v2.json",
         **{f"{v.title()}_view": f"sm25_{v}_as_drawn.json" for v in ("east", "north", "south", "west")}}


def _products():
    return {stem: json.loads((PRODUCTS / name).read_text()) for stem, name in FILES.items()}


@pytest.mark.parametrize("profile", ["exploratory", "dev", "golden", "regression"])
def test_six_real_views_no_legacy_flags_or_vacuous_passes(profile, monkeypatch):
    import src.validator.checks.reading_product as module

    def forbidden(raw):
        pytest.fail("as-drawn product reached the legacy parser")

    monkeypatch.setattr(module, "parse_reading_view", forbidden)
    report = check_reading_stage(build_view_manifest(CASE), _products(),
                                run_profile=profile, run_policy_sha256="a" * 64,
                                run_policy_source="frozen")
    assert report.passed and not report.flagged()
    assert report.run_policy_sha256 == "a" * 64
    for stem in FILES:
        rows = {r.check_id.removeprefix(f"{stem}."): r for r in report.results
                if r.check_id.startswith(f"{stem}.")}
        assert rows["reading.dimensions_present"].status == CheckStatus.PASS
        assert rows["reading.dimension_chain_closure"].status == CheckStatus.PASS
        assert rows["reading.stroke_ids_unique"].status == CheckStatus.NOT_APPLICABLE
        assert rows["reading.plan_scale_origin_usable"].status == CheckStatus.NOT_APPLICABLE
        expected = "plan" if stem[0].isdigit() else "elevation"
        assert rows["reading.product_contract"].evidence["image_kind"] == expected


def test_offline_validation_and_preflight_use_same_dispatch(tmp_path):
    rdir = tmp_path / "0_reading"
    rdir.mkdir()
    for stem, raw in _products().items():
        (rdir / f"{stem}.json").write_text(json.dumps(raw))
    preflight = compute_reading_report_from_vector_dir(
        rdir, run_profile="regression", dimensioned_views=set(FILES))
    assert preflight.passed and not preflight.flagged()
    validation = validate_case(tmp_path, case_dir=CASE)
    for stem in FILES:
        report = validation.reports[f"0_reading::{stem}"]
        assert report.passed and not report.flagged()
        assert any(r.check_id == "reading.product_contract" for r in report.results)


@pytest.mark.parametrize("raw", [
    {"schema": "future_reading", "strokes": []},
    {"schema": "as_drawn_plan_v2", "strokes": []},
    {"schema": None, "strokes": []},
    {"schema": [], "strokes": []},
    {"stage": "0_reading", "results": [], "report_schema_version": "2.2"},
    [],
])
def test_unrecognized_or_nonproduct_payload_blocks(raw):
    assert check_reading_product(raw).blocking()


def test_ambiguous_product_cannot_fall_back_to_legacy():
    raw = _products()["1f_view"]
    raw["strokes"] = []
    report = check_reading_product(raw)
    assert "AMBIGUOUS" in report.blocking()[0].evidence["reason"]


@pytest.mark.parametrize("stem", ["1f_view", "East_view"])
@pytest.mark.parametrize("damage", ["missing_ticks", "false_closure", "bad_frame"])
def test_native_evidence_is_checked_instead_of_blanket_pass(stem, damage):
    raw = _products()[stem]
    calibration = raw.get("observations", raw)["calibration"]
    if damage == "missing_ticks":
        calibration["x"]["cum_mm"] = []
    elif damage == "false_closure":
        calibration["x"]["cum_mm"][-1] += 1000
        calibration["x"]["chain_closure_mm"] = 0
    else:
        calibration["world_zero_px"] = [None, 0]
    report = check_reading_product(raw, dimensioned_state="declared_true", run_profile="regression")
    assert report.blocking()
    assert all("scale_origin" not in r.message for r in report.blocking())


@pytest.mark.parametrize("state", ["declared_false", "unknown", "legacy_default"])
def test_native_dimension_applicability_keeps_all_four_states(state):
    report = check_reading_product(_products()["1f_view"], dimensioned_state=state)
    row = next(r for r in report.results if r.check_id == "reading.dimensions_present")
    assert row.status == CheckStatus.NOT_APPLICABLE
    assert row.evidence["dimensioned_state"] == state


def test_legacy_results_unchanged_and_all_legacy_checks_accounted_for():
    raw = json.loads((CASE / "run_t1_probe2/0_reading/1f_view.json").read_text())
    before = check_reading_view(parse_reading_view(raw), dimensioned_state="declared_true")
    after = check_reading_product(raw, dimensioned_state="declared_true")
    assert before.model_dump() == after.model_dump()
    native = check_reading_product(_products()["1f_view"])
    assert {r.check_id for r in before.results} <= {r.check_id for r in native.results}
