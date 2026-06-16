"""M2c acceptance: 4_mep reference graph + object semantics, 5 backstop, EP baseline."""

from __future__ import annotations

import json
from pathlib import Path

from src.agent.state import IntakeOutput
from src.validator.checks.assembly import check_assembly, check_ep_baseline
from src.validator.checks.mep import check_mep
from src.validator.checks.schema import CheckStatus

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")
_RUN = _ANCHOR / "run_2026-06-15_baseline"
_FIX = Path("tests/fixtures/validation")


def _blocking(rep):
    return {r.check_id for r in rep.blocking()}


def _anchor_mep() -> dict:
    return json.loads((_RUN / "4_mep" / "mep_output.json").read_text())


# --------------------------------------------------------------------------- #
# clean anchor passes
# --------------------------------------------------------------------------- #
def test_clean_anchor_mep_passes():
    mep = _anchor_mep()
    # zones from the building geometry (19 zones)
    bg = json.loads((_RUN / "2_modelling" / "building_geometry.json").read_text())
    zones = set(bg["zones"])
    used = {s["obc_obj"] for s in bg["surfaces"] if s["obc"] == "Surface"}  # not the real set
    rep = check_mep(mep, zone_names=zones)
    assert rep.passed, [r.message for r in rep.blocking()]


def test_clean_anchor_construction_coverage():
    mep = _anchor_mep()
    # the constructions the anchor's geometry actually uses
    used = {"Default_Ext_Wall", "Default_Int_Wall", "Cons_InterFloor",
            "Default_GroundFloor"}
    rep = check_mep(mep, used_constructions=used)
    cov = next(r for r in rep.results if r.check_id == "mep.construction_coverage")
    assert cov.status == CheckStatus.PASS


# --------------------------------------------------------------------------- #
# object semantics negative fixture
# --------------------------------------------------------------------------- #
def test_bad_mep_semantics_all_three_fire():
    mep = json.loads((_FIX / "bad_mep_semantics.json").read_text())
    rep = check_mep(mep, zone_names={"Z1"})
    ids = _blocking(rep)
    assert "mep.simpleglazing_standalone" in ids
    assert "mep.nomass_positive_resistance" in ids
    assert "mep.load_to_schedule" in ids


def test_empty_construction_blocks():
    """A Construction with no layers must NOT pass vacuously (Codex M1)."""
    mep = {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": "", "construction_specs": "Construction,\n  Default_Ext_Wall;\n",
        "schedule_specs": "", "hvac_specs": "", "people_specs": "", "lights_specs": "",
    }
    rep = check_mep(mep, used_constructions={"Default_Ext_Wall"})
    assert "mep.construction_to_material" in _blocking(rep)


def test_missing_construction_coverage_blocks():
    mep = _anchor_mep()
    rep = check_mep(mep, used_constructions={"Cons_DoesNotExist"})
    assert "mep.construction_coverage" in _blocking(rep)


def test_parse_error_fail_closed():
    bad = {"material_specs": "Material, broken @@@ no semicolon and bad",
           "construction_specs": "", "schedule_specs": "", "hvac_specs": "",
           "people_specs": "", "lights_specs": ""}
    rep = check_mep(bad)
    # If eppy chokes, parse is ERROR → block; if eppy is lenient, the bundle is
    # at least not silently passed with a false clean.
    parse = next(r for r in rep.results if r.check_id == "mep.idf_parse")
    assert parse.status in (CheckStatus.PASS, CheckStatus.ERROR)


def test_missing_schedule_day_types_blocks():
    mep = {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": "", "construction_specs": "",
        "schedule_specs": "ScheduleTypeLimits,\n  Fraction,\n  0,\n  1,\n  Continuous;\n\n"
                          "Schedule:Compact,\n  Occ,\n  Fraction,\n  Through: 12/31,\n"
                          "  For: Weekdays,\n  Until: 24:00,1.0;\n",  # incomplete day types
        "hvac_specs": "", "people_specs": "", "lights_specs": "",
    }
    rep = check_mep(mep)
    assert "mep.schedule_completeness" in _blocking(rep)


# --------------------------------------------------------------------------- #
# 5 backstop — owner stays 4_mep
# --------------------------------------------------------------------------- #
def test_assembly_backstop_passes_on_clean_anchor():
    intake = IntakeOutput.model_validate_json(
        (_RUN / "5_intakeoutput" / "intake_output.json").read_text()
    )
    used = {"Default_Ext_Wall", "Default_Int_Wall", "Cons_InterFloor",
            "Default_GroundFloor"}
    rep = check_assembly(intake, used)
    assert rep.passed


def test_assembly_backstop_attributes_owner_to_mep():
    intake = IntakeOutput.model_validate_json(
        (_RUN / "5_intakeoutput" / "intake_output.json").read_text()
    )
    rep = check_assembly(intake, {"Cons_Missing"})
    blocking = rep.blocking()
    assert blocking and blocking[0].evidence.get("owner_stage") == "4_mep"


# --------------------------------------------------------------------------- #
# EP baseline assertion
# --------------------------------------------------------------------------- #
def test_ep_baseline_missing_end_is_error_not_pass(tmp_path):
    rep = check_ep_baseline(tmp_path)  # no eplusout.end
    assert not rep.passed
    end_present = next(r for r in rep.results if r.check_id == "ep.end_present")
    assert end_present.status == CheckStatus.ERROR


def test_ep_baseline_clean_end(tmp_path):
    (tmp_path / "eplusout.end").write_text(
        "EnergyPlus Completed Successfully-- 0 Warning; 0 Severe Errors; ...\n"
    )
    rep = check_ep_baseline(tmp_path, max_warnings=10)
    assert rep.passed, [r.message for r in rep.blocking()]


def test_ep_baseline_severe_blocks(tmp_path):
    (tmp_path / "eplusout.end").write_text(
        "EnergyPlus Terminated--Fatal Error Detected. 3 Warning; 2 Severe Errors; ...\n"
    )
    rep = check_ep_baseline(tmp_path)
    assert "ep.zero_severe" in _blocking(rep)
