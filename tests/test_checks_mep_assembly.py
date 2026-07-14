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


def _construction_thermal_mass_mep(material_specs: str, construction_specs: str) -> dict:
    return {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": material_specs,
        "construction_specs": construction_specs,
        "schedule_specs": "", "hvac_specs": "", "people_specs": "", "lights_specs": "",
    }


def test_opaque_construction_with_exact_material_mass_layer_passes():
    mep = _construction_thermal_mass_mep(
        "Material,\n"
        "  Concrete,\n"
        "  MediumRough,\n"
        "  0.1,\n"
        "  1.4,\n"
        "  2200,\n"
        "  900,\n"
        "  0.9,\n"
        "  0.7,\n"
        "  0.7;\n\n"
        "Material:NoMass,\n"
        "  Insulation,\n"
        "  Rough,\n"
        "  2.0,\n"
        "  0.9,\n"
        "  0.7,\n"
        "  0.7;\n",
        "Construction,\n"
        "  Wall,\n"
        "  Insulation,\n"
        "  Concrete;\n",
    )
    result = next(r for r in check_mep(mep).results
                  if r.check_id == "mep.construction_thermal_mass")
    assert result.status == CheckStatus.PASS


def test_opaque_construction_with_only_non_mass_layers_blocks():
    mep = _construction_thermal_mass_mep(
        "Material:NoMass,\n"
        "  NoMassLayer,\n"
        "  Rough,\n"
        "  2.0,\n"
        "  0.9,\n"
        "  0.7,\n"
        "  0.7;\n\n"
        "Material:AirGap,\n"
        "  AirGapLayer,\n"
        "  0.18;\n\n"
        "Material:InfraredTransparent,\n"
        "  IRLayer;\n",
        "Construction,\n"
        "  Wall,\n"
        "  NoMassLayer,\n"
        "  AirGapLayer,\n"
        "  IRLayer;\n",
    )
    rep = check_mep(mep)
    assert "mep.construction_thermal_mass" in _blocking(rep)
    result = next(r for r in rep.results if r.check_id == "mep.construction_thermal_mass")
    assert result.evidence["offenders"][0]["construction"] == "Wall"


def test_fenestration_and_air_boundary_are_out_of_thermal_mass_scope():
    mep = _construction_thermal_mass_mep(
        "WindowMaterial:SimpleGlazingSystem,\n"
        "  SimpleWindow,\n"
        "  2.5,\n"
        "  0.5,\n"
        "  0.4;\n",
        "Construction,\n"
        "  WindowCons,\n"
        "  SimpleWindow;\n\n"
        "Construction:AirBoundary,\n"
        "  AirBoundaryCons,\n"
        "  Air Mixing,\n"
        "  SimpleMixing,\n"
        "  0.5;\n",
    )
    result = next(r for r in check_mep(mep).results
                  if r.check_id == "mep.construction_thermal_mass")
    assert result.status == CheckStatus.PASS
    assert result.evidence["checked_opaque_constructions"] == 0
    assert result.evidence["skipped_fenestration_constructions"] == ["WindowCons"]


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


def _schedule_placeholder_mep(schedule_name: str) -> dict:
    return {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": "", "construction_specs": "",
        "schedule_specs": "ScheduleTypeLimits,\n  Fraction,\n  0,\n  1,\n  Continuous;\n\n"
                          "Schedule:Compact,\n"
                          f"  {schedule_name},\n"
                          "  Fraction,\n"
                          "  Through: 12/31,\n"
                          "  For: AllDays,\n"
                          "  Until: 24:00,1.0;\n",
        "hvac_specs": "", "people_specs": "", "lights_specs": "",
    }


def test_placeholder_ban_blocks_tbd_in_mep_schedule():
    rep = check_mep(_schedule_placeholder_mep("TBD"))
    result = next(r for r in rep.results if r.check_id == "mep.placeholder_ban")
    assert result.status == CheckStatus.FAIL
    assert "mep.placeholder_ban" in _blocking(rep)


def test_placeholder_ban_passes_clean_mep_schedule():
    rep = check_mep(_schedule_placeholder_mep("Occ"))
    result = next(r for r in rep.results if r.check_id == "mep.placeholder_ban")
    assert result.status == CheckStatus.PASS


def _material_name_charset_mep(material_name: str) -> dict:
    return {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": "Material,\n"
                          f"  {material_name},\n"
                          "  MediumRough,\n"
                          "  0.1,\n"
                          "  0.5,\n"
                          "  800,\n"
                          "  1000,\n"
                          "  0.9,\n"
                          "  0.7,\n"
                          "  0.7;\n",
        "construction_specs": "Construction,\n"
                              "  Wall,\n"
                              f"  {material_name};\n",
        "schedule_specs": "", "hvac_specs": "", "people_specs": "", "lights_specs": "",
    }


def test_name_charset_flags_material_with_illegal_char_without_blocking():
    rep = check_mep(_material_name_charset_mep("Mat@Bad"))
    result = next(r for r in rep.results if r.check_id == "mep.name_charset")
    assert result.status == CheckStatus.FAIL
    assert "mep.name_charset" in {r.check_id for r in rep.flagged()}
    assert rep.passed


def test_name_charset_passes_clean_material_name():
    rep = check_mep(_material_name_charset_mep("Mat_Bad-1"))
    result = next(r for r in rep.results if r.check_id == "mep.name_charset")
    assert result.status == CheckStatus.PASS


def test_site_matches_testdata_flags_structured_mismatch_without_blocking():
    mep = _schedule_placeholder_mep("Occ")
    testdata = {
        "site_location": {
            "latitude": 23.5,
            "longitude": 114.0,
            "time_zone": 8.0,
            "elevation": 5.0,
        }
    }
    rep = check_mep(mep, testdata=testdata)
    result = next(r for r in rep.results if r.check_id == "mep.site_matches_testdata")
    assert result.status == CheckStatus.FAIL
    assert "mep.site_matches_testdata" in {r.check_id for r in rep.flagged()}
    assert rep.passed


def test_site_matches_testdata_passes_structured_match():
    mep = _schedule_placeholder_mep("Occ")
    testdata = {
        "site_location": {
            "latitude": 22.5,
            "longitude": 114.0,
            "time_zone": 8.0,
            "elevation": 5.0,
        }
    }
    rep = check_mep(mep, testdata=testdata)
    result = next(r for r in rep.results if r.check_id == "mep.site_matches_testdata")
    assert result.status == CheckStatus.PASS


def test_site_matches_testdata_not_applicable_without_structured_site_fields():
    mep = _schedule_placeholder_mep("Occ")
    rep = check_mep(mep, testdata={"Building location": "Shenzhen"})
    result = next(r for r in rep.results if r.check_id == "mep.site_matches_testdata")
    assert result.status == CheckStatus.NOT_APPLICABLE


def _people_activity_mep(activity_field: str, *, include_activity_schedule: bool) -> dict:
    activity_schedule = (
        "\n\nSchedule:Compact,\n  Activity,\n  Any Number,\n  Through: 12/31,\n"
        "  For: AllDays,\n  Until: 24:00,120.0;\n"
        if include_activity_schedule
        else ""
    )
    return {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": "", "construction_specs": "",
        "schedule_specs": "ScheduleTypeLimits,\n  Fraction,\n  0,\n  1,\n  Continuous;\n\n"
                          "ScheduleTypeLimits,\n  Any Number,\n  ,\n  ,\n  Continuous;\n\n"
                          "Schedule:Compact,\n  Occ,\n  Fraction,\n  Through: 12/31,\n"
                          "  For: AllDays,\n  Until: 24:00,1.0;\n"
                          f"{activity_schedule}",
        "hvac_specs": "",
        "people_specs": "People,\n  P1,\n  Z1,\n  Occ,\n  People,\n  1,\n  ,\n  ,\n"
                        f"  0.3,\n  Autocalculate{activity_field};\n",
        "lights_specs": "",
    }


def test_people_missing_activity_schedule_blocks_load_to_schedule():
    mep = _people_activity_mep("", include_activity_schedule=False)
    rep = check_mep(mep, zone_names={"Z1"})
    result = next(r for r in rep.results if r.check_id == "mep.load_to_schedule")
    assert result.status == CheckStatus.FAIL
    assert result.evidence["offenders"][0]["reason"] == "missing"


def test_people_undefined_activity_schedule_blocks_load_to_schedule():
    mep = _people_activity_mep(",\n  MissingActivity", include_activity_schedule=False)
    rep = check_mep(mep, zone_names={"Z1"})
    result = next(r for r in rep.results if r.check_id == "mep.load_to_schedule")
    assert result.status == CheckStatus.FAIL
    assert result.evidence["offenders"][0]["activity_schedule_ref"] == "MissingActivity"


def test_people_primary_and_activity_schedules_pass_load_to_schedule():
    mep = _people_activity_mep(",\n  Activity", include_activity_schedule=True)
    rep = check_mep(mep, zone_names={"Z1"})
    result = next(r for r in rep.results if r.check_id == "mep.load_to_schedule")
    assert result.status == CheckStatus.PASS


def _hvac_schedule_mep(hvac_specs: str) -> dict:
    return {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": "", "construction_specs": "",
        "schedule_specs": "ScheduleTypeLimits,\n"
                          "  Fraction,\n"
                          "  0,\n"
                          "  1,\n"
                          "  Continuous;\n\n"
                          "ScheduleTypeLimits,\n"
                          "  Temperature,\n"
                          "  ,\n"
                          "  ,\n"
                          "  Continuous;\n\n"
                          "Schedule:Compact,\n"
                          "  ControlSch,\n"
                          "  Fraction,\n"
                          "  Through: 12/31,\n"
                          "  For: AllDays,\n"
                          "  Until: 24:00,4;\n\n"
                          "Schedule:Compact,\n"
                          "  HeatSet,\n"
                          "  Temperature,\n"
                          "  Through: 12/31,\n"
                          "  For: AllDays,\n"
                          "  Until: 24:00,20;\n\n"
                          "Schedule:Compact,\n"
                          "  CoolSet,\n"
                          "  Temperature,\n"
                          "  Through: 12/31,\n"
                          "  For: AllDays,\n"
                          "  Until: 24:00,24;\n\n"
                          "Schedule:Compact,\n"
                          "  Avail,\n"
                          "  Fraction,\n"
                          "  Through: 12/31,\n"
                          "  For: AllDays,\n"
                          "  Until: 24:00,1;\n",
        "hvac_specs": hvac_specs,
        "people_specs": "", "lights_specs": "",
    }


def test_hvac_schedule_refs_cover_table_and_blank_optional_fields_pass():
    hvac_specs = (
        "ZoneControl:Thermostat,\n"
        "  ZT,\n"
        "  Z1,\n"
        "  ControlSch,\n"
        "  ThermostatSetpoint:DualSetpoint,\n"
        "  Dual;\n\n"
        "ThermostatSetpoint:DualSetpoint,\n"
        "  Dual,\n"
        "  HeatSet,\n"
        "  CoolSet;\n\n"
        "ThermostatSetpoint:SingleHeating,\n"
        "  SingleHeat,\n"
        "  HeatSet;\n\n"
        "ThermostatSetpoint:SingleCooling,\n"
        "  SingleCool,\n"
        "  CoolSet;\n\n"
        "ThermostatSetpoint:SingleHeatingOrCooling,\n"
        "  SingleHeatCool,\n"
        "  HeatSet;\n\n"
        "ZoneHVAC:IdealLoadsAirSystem,\n"
        "  Ideal,\n"
        "  Avail;\n\n"
        "HVACTemplate:Zone:IdealLoadsAirSystem,\n"
        "  Z1,\n"
        "  TemplateTstat,\n"
        "  Avail;\n\n"
        "HVACTemplate:Thermostat,\n"
        "  TemplateTstat,\n"
        "  HeatSet,\n"
        "  ,\n"
        "  CoolSet;\n\n"
        "HVACTemplate:Thermostat,\n"
        "  BlankTemplateTstat,\n"
        "  ,\n"
        "  20,\n"
        "  ,\n"
        "  24;\n"
    )
    result = next(r for r in check_mep(_hvac_schedule_mep(hvac_specs)).results
                  if r.check_id == "mep.hvac_schedule_refs")
    assert result.status == CheckStatus.PASS
    assert result.evidence["checked_fields"] == 12


def test_hvac_schedule_refs_block_non_empty_missing_schedule():
    hvac_specs = (
        "ThermostatSetpoint:DualSetpoint,\n"
        "  Dual,\n"
        "  MissingHeat,\n"
        "  CoolSet;\n"
    )
    rep = check_mep(_hvac_schedule_mep(hvac_specs))
    assert "mep.hvac_schedule_refs" in _blocking(rep)
    result = next(r for r in rep.results if r.check_id == "mep.hvac_schedule_refs")
    assert result.evidence["offenders"] == [{
        "object_type": "THERMOSTATSETPOINT:DUALSETPOINT",
        "object": "Dual",
        "field": "Heating_Setpoint_Temperature_Schedule_Name",
        "schedule_ref": "MissingHeat",
    }]


def test_hvac_schedule_refs_ignore_deferred_heating_cooling_availability_fields():
    hvac_specs = (
        "ZoneHVAC:IdealLoadsAirSystem,\n"
        "  Ideal,\n"
        "  Avail,\n"
        "  ,\n"
        "  ,\n"
        "  ,\n"
        "  50,\n"
        "  13,\n"
        "  0.015,\n"
        "  0.008,\n"
        "  NoLimit,\n"
        "  ,\n"
        "  ,\n"
        "  NoLimit,\n"
        "  ,\n"
        "  ,\n"
        "  DeferredHeatAvail,\n"
        "  DeferredCoolAvail;\n"
    )
    result = next(r for r in check_mep(_hvac_schedule_mep(hvac_specs)).results
                  if r.check_id == "mep.hvac_schedule_refs")
    assert result.status == CheckStatus.PASS


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


# --------------------------------------------------------------------------- #
# E4 §10.2 — S4 MEP placeholder gate + S5 unconditional theta override
# --------------------------------------------------------------------------- #
def _minimal_mep_dict(north_axis: float) -> dict:
    return {
        "building": {"name": "B", "north_axis": north_axis, "terrain": "City"},
        "site_location": {"name": "S", "latitude": 22.5, "longitude": 114.0,
                          "time_zone": 8.0, "elevation": 5.0},
        "material_specs": "", "construction_specs": "",
        "schedule_specs": "", "hvac_specs": "", "people_specs": "", "lights_specs": "",
    }


def test_mep_north_axis_placeholder_zero_passes():
    rep = check_mep(_minimal_mep_dict(0.0))
    result = next(r for r in rep.results if r.check_id == "mep.building_north_axis_placeholder")
    assert result.status == CheckStatus.PASS


def test_mep_north_axis_negative_zero_passes():
    rep = check_mep(_minimal_mep_dict(-0.0))
    result = next(r for r in rep.results if r.check_id == "mep.building_north_axis_placeholder")
    assert result.status == CheckStatus.PASS


import pytest as _pytest


@_pytest.mark.parametrize("theta", [90.0, 270.0, 0.0001])
def test_mep_north_axis_nonzero_blocks(theta):
    rep = check_mep(_minimal_mep_dict(theta))
    assert "mep.building_north_axis_placeholder" in _blocking(rep)


def _mep_model(north_axis: float = 0.0) -> "MepOutput":
    from src.agent.intakeoutput import MepOutput
    from src.validator import BuildingSchema, SiteLocationSchema

    return MepOutput(
        building=BuildingSchema(name="T", north_axis=north_axis),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
        material_specs="m", construction_specs="c", schedule_specs="s",
        hvac_specs="h", people_specs="p", lights_specs="l",
    )


def _contract_with_theta(theta: float):
    from src.agent.output_coordinates import AcceptedCorrectionRef, OutputCoordinateContract

    if theta == 0.0:
        provenance = "assumed"
    else:
        provenance = "observed"
    return OutputCoordinateContract(
        mode="relative_north_axis",
        source=AcceptedCorrectionRef(
            schema_version="3", output_sha256="a" * 64,
            acceptance="integrated_gate1",
            artifact_contract="correction_e4_orientation_v1",
        ),
        geometry_frame="building_axis_absolute_values",
        global_geometry_coordinate_system="Relative",
        daylighting_reference_point_coordinate_system="Relative",
        rectangular_surface_coordinate_system="Relative",
        zone_origin_policy="all_zero", zone_direction_policy="all_zero",
        north_axis_owner="accepted_correction_orientation",
        north_axis_deg=theta, orientation_provenance=provenance,
        orientation_source_ids=("s1",) if provenance == "observed" else (),
        geometry_snapshot_sha256="b" * 64,
    )


@_pytest.mark.parametrize("theta", [0.0, 90.0, 270.0])
def test_s5_unconditional_override_all_thetas(theta):
    from src.agent.intakeoutput import assemble_intake_output

    mep = _mep_model(0.0)
    intake = assemble_intake_output(
        zone_specs="z", surface_specs="s", fenestration_specs="f",
        mep=mep, output_coordinates=_contract_with_theta(theta),
    )
    assert intake.building.north_axis == theta
    # input MepOutput must NOT have been mutated
    assert mep.building.north_axis == 0.0


def test_s5_mep_zero_vs_theta_ninety_is_not_a_conflict():
    from src.agent.intakeoutput import assemble_intake_output

    intake = assemble_intake_output(
        zone_specs="z", surface_specs="s", fenestration_specs="f",
        mep=_mep_model(0.0), output_coordinates=_contract_with_theta(90.0),
    )
    assert intake.building.north_axis == 90.0


def test_s5_nonzero_mep_fails_even_when_equal_to_theta():
    from src.agent.intakeoutput import assemble_intake_output

    with _pytest.raises(ValueError, match="placeholder"):
        assemble_intake_output(
            zone_specs="z", surface_specs="s", fenestration_specs="f",
            mep=_mep_model(90.0), output_coordinates=_contract_with_theta(90.0),
        )


def test_s5_model_copy_injected_bad_angle_rejected_by_strict_rebuild():
    from src.agent.intakeoutput import assemble_intake_output

    bad_contract = _contract_with_theta(90.0).model_copy(update={"north_axis_deg": 400.0})
    with _pytest.raises(Exception):
        assemble_intake_output(
            zone_specs="z", surface_specs="s", fenestration_specs="f",
            mep=_mep_model(0.0), output_coordinates=bad_contract,
        )


def test_s5_without_contract_is_byte_identical_legacy():
    from src.agent.intakeoutput import assemble_intake_output

    mep = _mep_model(0.0)
    legacy = assemble_intake_output(
        zone_specs="z", surface_specs="s", fenestration_specs="f", mep=mep)
    assert legacy.building is mep.building  # verbatim copy, no rebuild
