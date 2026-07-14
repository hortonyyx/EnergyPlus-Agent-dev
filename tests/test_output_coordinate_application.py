"""E4-output-contract spec v2 §10.3 — GGR A3/A4/A5 schema + converter, seed
application, Zone frame zeroing/audit, late-write rejection, offender listing,
checkpoint/deep-copy survival."""

from __future__ import annotations

import json
import pickle
from types import SimpleNamespace

import pytest

from src.agent._share import ensure_schema_initialized
from src.agent.output_coordinates import (
    AcceptedCorrectionRef,
    LegacyStandaloneIntakeRef,
    OutputCoordinateContract,
    apply_output_coordinate_contract,
    validate_zone_frames_all_zero,
    zero_zone_frames_with_audit,
)
from src.agent.tools.zone_tools import make_zone_tools
from src.mcp.state import ConfigState
from src.validator import BuildingSchema, SiteLocationSchema
from src.validator.data_model import GlobalGeometryRulesSchema, ZoneSchema

HEX64_A = "a" * 64
HEX64_B = "b" * 64


@pytest.fixture(autouse=True)
def _init_schema():
    ensure_schema_initialized()


def _relative_contract(theta: float = 90.0) -> OutputCoordinateContract:
    return OutputCoordinateContract(
        mode="relative_north_axis",
        source=AcceptedCorrectionRef(
            schema_version="3", output_sha256=HEX64_A,
            acceptance="integrated_gate1",
            artifact_contract="correction_e4_orientation_v1",
        ),
        geometry_frame="building_axis_absolute_values",
        global_geometry_coordinate_system="Relative",
        daylighting_reference_point_coordinate_system="Relative",
        rectangular_surface_coordinate_system="Relative",
        zone_origin_policy="all_zero", zone_direction_policy="all_zero",
        north_axis_owner="accepted_correction_orientation",
        north_axis_deg=theta, orientation_provenance="observed",
        orientation_source_ids=("s1",), geometry_snapshot_sha256=HEX64_B,
    )


def _legacy_contract() -> OutputCoordinateContract:
    return OutputCoordinateContract(
        mode="world_legacy",
        source=LegacyStandaloneIntakeRef(intake_output_sha256=HEX64_A),
        geometry_frame="building_axis_absolute_values",
        global_geometry_coordinate_system="World",
        daylighting_reference_point_coordinate_system="Relative",
        rectangular_surface_coordinate_system="Relative",
        zone_origin_policy="preserve_legacy", zone_direction_policy="preserve_legacy",
        north_axis_owner="legacy_mep_placeholder", north_axis_deg=0.0,
    )


def _config_with_zones() -> ConfigState:
    cfg = ConfigState(
        building=BuildingSchema(name="B"),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
    )
    cfg.zones = [
        ZoneSchema.model_validate({"Name": "Z2_high", "X Origin": 10.0, "Y Origin": -3.0,
                                    "Z Origin": 3.6, "Direction of Relative North": 45.0}),
        ZoneSchema.model_validate({"Name": "Z1_ground"}),
        ZoneSchema.model_validate({"Name": "Z3_mid", "Z Origin": 7.2}),
    ]
    return cfg


# --------------------------------------------------------------------------- #
# GGR A3/A4/A5
# --------------------------------------------------------------------------- #
def test_ggr_schema_defaults_match_idd_defaults():
    g = GlobalGeometryRulesSchema()
    assert g.coordinate_system == "World"
    assert g.daylighting_reference_point_coordinate_system == "Relative"
    assert g.rectangular_surface_coordinate_system == "Relative"


def test_ggr_schema_round_trip_with_aliases():
    g = GlobalGeometryRulesSchema.model_validate({
        "Coordinate System": "Relative",
        "Daylighting Reference Point Coordinate System": "Relative",
        "Rectangular Surface Coordinate System": "Relative",
    })
    dumped = g.model_dump(by_alias=True)
    assert dumped["Coordinate System"] == "Relative"
    assert dumped["Daylighting Reference Point Coordinate System"] == "Relative"
    assert dumped["Rectangular Surface Coordinate System"] == "Relative"
    assert "GlobalGeometryRules" in g.to_yaml_dict()


def test_ggr_schema_rejects_bad_choice():
    with pytest.raises(Exception):
        GlobalGeometryRulesSchema.model_validate(
            {"Daylighting Reference Point Coordinate System": "Sideways"})


def _fresh_idf_manager(yaml_path):
    """BaseSchema._idf is a process-wide singleton eppy IDF; two converts in
    one test process would collide ('already exists, skipping'). Reset to a
    blank IDF per conversion, exactly like a fresh production process."""
    from src.agent._share import IDD_PATH
    from src.converter_manager import ConverterManager
    from src.validator.data_model import BaseSchema

    BaseSchema.set_idf(IDD_PATH)
    return ConverterManager(yaml_path)


def test_settings_converter_writes_a3_a4_a5_explicitly(tmp_path):
    cfg = _config_with_zones()
    cfg = apply_output_coordinate_contract(cfg, _relative_contract(90.0))
    yaml_path = tmp_path / "cfg.yaml"
    cfg.export_yaml(yaml_path)
    manager = _fresh_idf_manager(yaml_path)
    manager.convert_all()
    ggr_objs = manager._idf.idfobjects["GLOBALGEOMETRYRULES"]
    assert len(ggr_objs) == 1
    obj = ggr_objs[0]
    assert obj.Coordinate_System == "Relative"
    assert obj.Daylighting_Reference_Point_Coordinate_System == "Relative"
    assert obj.Rectangular_Surface_Coordinate_System == "Relative"
    building = manager._idf.idfobjects["BUILDING"][0]
    assert float(building.North_Axis) == 90.0
    for zone in manager._idf.idfobjects["ZONE"]:
        assert float(zone.X_Origin) == 0.0
        assert float(zone.Y_Origin) == 0.0
        assert float(zone.Z_Origin) == 0.0
        assert float(zone.Direction_of_Relative_North) == 0.0


def test_settings_converter_legacy_world_relative_relative(tmp_path):
    cfg = _config_with_zones()
    cfg = apply_output_coordinate_contract(cfg, _legacy_contract())
    yaml_path = tmp_path / "cfg.yaml"
    cfg.export_yaml(yaml_path)
    manager = _fresh_idf_manager(yaml_path)
    manager.convert_all()
    obj = manager._idf.idfobjects["GLOBALGEOMETRYRULES"][0]
    assert obj.Coordinate_System == "World"
    assert obj.Daylighting_Reference_Point_Coordinate_System == "Relative"
    assert obj.Rectangular_Surface_Coordinate_System == "Relative"
    # legacy preserves zone frames exactly
    zones = {z.Name: z for z in manager._idf.idfobjects["ZONE"]}
    assert float(zones["Z2_high"].Z_Origin) == 3.6
    assert float(zones["Z2_high"].Direction_of_Relative_North) == 45.0


# --------------------------------------------------------------------------- #
# apply / seed
# --------------------------------------------------------------------------- #
def test_apply_relative_sets_theta_ggr_and_zeroes_zones():
    cfg = _config_with_zones()
    out = apply_output_coordinate_contract(cfg, _relative_contract(270.0))
    assert out.building.north_axis == 270.0
    assert out.global_geometry_rules.coordinate_system == "Relative"
    assert validate_zone_frames_all_zero(out) == []
    # input untouched
    assert cfg.building.north_axis == 0.0
    assert cfg.zones[0].z_origin == 3.6


def test_apply_legacy_keeps_zone_frames_and_zero_building():
    cfg = _config_with_zones()
    out = apply_output_coordinate_contract(cfg, _legacy_contract())
    assert out.building.north_axis == 0.0
    assert out.global_geometry_rules.coordinate_system == "World"
    by_name = {z.name: z for z in out.zones}
    assert by_name["Z2_high"].z_origin == 3.6
    assert by_name["Z2_high"].direction_of_relative_north == 45.0


def test_apply_is_idempotent():
    cfg = _config_with_zones()
    once = apply_output_coordinate_contract(cfg, _relative_contract(90.0))
    twice = apply_output_coordinate_contract(once, _relative_contract(90.0))
    assert once.model_dump() == twice.model_dump()


def test_seed_config_applies_contract_before_zone_fanout():
    from src.agent.nodes.intake import _seed_config
    from src.agent.state import AgentState, IntakeOutput

    intake = IntakeOutput(
        building=BuildingSchema(name="B"),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
        zone_specs="z", material_specs="m", schedule_specs="s",
        construction_specs="c", surface_specs="su", fenestration_specs="f",
        hvac_specs="h", people_specs="p", lights_specs="l",
    )
    update = _seed_config(AgentState(), intake, contract=_relative_contract(90.0))
    seeded = update["config_state"]
    assert seeded.building.north_axis == 90.0
    assert seeded.global_geometry_rules.coordinate_system == "Relative"
    # legacy table
    update2 = _seed_config(AgentState(), intake, contract=_legacy_contract())
    assert update2["config_state"].building.north_axis == 0.0
    assert update2["config_state"].global_geometry_rules.coordinate_system == "World"


# --------------------------------------------------------------------------- #
# Zone postprocess + audit + late-write gate
# --------------------------------------------------------------------------- #
def test_zone_postprocess_zeroes_all_and_audits_before_values():
    cfg = _config_with_zones()
    out, entries = zero_zone_frames_with_audit(cfg, _relative_contract())
    assert validate_zone_frames_all_zero(out) == []
    audited = {e.zone_name: e for e in entries}
    assert set(audited) == {"Z2_high", "Z3_mid"}  # Z1_ground was already zero
    assert audited["Z2_high"].before == (10.0, -3.0, 3.6, 45.0)
    assert audited["Z2_high"].after == (0.0, 0.0, 0.0, 0.0)
    # sorted by zone name
    assert [e.zone_name for e in entries] == sorted(e.zone_name for e in entries)


def test_zone_postprocess_idempotent_and_legacy_noop():
    cfg = _config_with_zones()
    out, entries1 = zero_zone_frames_with_audit(cfg, _relative_contract())
    out2, entries2 = zero_zone_frames_with_audit(out, _relative_contract())
    assert entries2 == ()  # nothing left to normalize
    assert out2.model_dump() == out.model_dump()
    legacy_out, legacy_entries = zero_zone_frames_with_audit(cfg, _legacy_contract())
    assert legacy_entries == ()
    assert legacy_out.zones[0].z_origin == 3.6  # untouched


def test_llm_adversarial_frame_normalized_with_audit():
    cfg = ConfigState(building=BuildingSchema(name="B"))
    cfg.zones = [ZoneSchema.model_validate({
        "Name": "Z9", "X Origin": 10.0, "Y Origin": -3.0,
        "Z Origin": 3.6, "Direction of Relative North": 45.0,
    })]
    out, entries = zero_zone_frames_with_audit(cfg, _relative_contract())
    assert entries[0].before == (10.0, -3.0, 3.6, 45.0)
    z = out.zones[0]
    assert (z.x_origin, z.y_origin, z.z_origin, z.direction_of_relative_north) == (0.0, 0.0, 0.0, 0.0)


def test_zone_tools_reject_nonzero_after_postprocess():
    cfg = ConfigState()
    tools = {t.name: t for t in make_zone_tools(cfg, contract=_relative_contract())}
    created = json.loads(tools["create_zone"].invoke({"name": "Z1"}))
    assert created["success"]
    rejected = json.loads(tools["update_zone"].invoke({"name": "Z1", "z_origin": 3.6}))
    assert not rejected["success"]
    assert "rejected_fields" in rejected["data"]
    rejected2 = json.loads(tools["create_zone"].invoke({
        "name": "Z2", "direction_of_relative_north": 45.0}))
    assert not rejected2["success"]


def test_zone_tools_legacy_and_unbound_pass_through():
    cfg = ConfigState()
    tools = {t.name: t for t in make_zone_tools(cfg)}  # no contract: legacy_unbound
    ok = json.loads(tools["create_zone"].invoke({"name": "Z1", "z_origin": 3.0}))
    assert ok["success"]
    cfg2 = ConfigState()
    tools2 = {t.name: t for t in make_zone_tools(cfg2, contract=_legacy_contract())}
    ok2 = json.loads(tools2["create_zone"].invoke({"name": "Z1", "z_origin": 3.0}))
    assert ok2["success"]


def test_final_validator_lists_every_offender_sorted():
    cfg = _config_with_zones()
    offenders = validate_zone_frames_all_zero(cfg)
    assert offenders == ["Z2_high", "Z3_mid"]


def test_final_live_idf_gate_reads_tampered_building_ggr_and_zone_fields(tmp_path):
    """BO-CR5 attack negative: ConfigState can be pristine while a converter
    or raw-IDF injection has changed the live fields. The final gate must read
    the IDF itself, not trust the in-memory model."""
    from src.agent.output_coordinates import (
        OutputCoordinateSnapshotV1,
        OutputCoordinateValidationContext,
        canonical_json_bytes,
        sha256_bytes,
    )
    from src.validator.output_coordinates import validate_output_coordinate_contract

    cfg = apply_output_coordinate_contract(_config_with_zones(), _relative_contract(90.0))
    yaml_path = tmp_path / "cfg.yaml"
    cfg.export_yaml(yaml_path)
    manager = _fresh_idf_manager(yaml_path)
    manager.convert_all()
    raw_snapshot = canonical_json_bytes(OutputCoordinateSnapshotV1(zone_names=(), records=()))
    contract = _relative_contract(90.0).model_copy(
        update={"geometry_snapshot_sha256": sha256_bytes(raw_snapshot)}
    )
    manager._idf.idfobjects["BUILDING"][0].North_Axis = 270.0
    ggr = manager._idf.idfobjects["GLOBALGEOMETRYRULES"][0]
    ggr.Daylighting_Reference_Point_Coordinate_System = "World"
    zone = manager._idf.idfobjects["ZONE"][0]
    zone.X_Origin, zone.Y_Origin = 10.0, -3.0
    context = OutputCoordinateValidationContext(
        raw_intake_output_bytes=b"{}", verified_correction=None,
        raw_snapshot_bytes=raw_snapshot,
    )
    codes = {
        issue.code for issue in validate_output_coordinate_contract(
            cfg, contract, context, idf=manager._idf,
        )
    }
    assert {"BUILDING_NORTH_AXIS", "GGR_COORDINATE_SYSTEM", "ZONE_FRAME_NONZERO"} <= codes


def test_building_tool_rejects_direct_north_axis_rewrite():
    from src.mcp.tools.building import BuildingTool

    cfg = ConfigState(building=BuildingSchema(name="B"))
    tool = BuildingTool(cfg, output_coordinates=_relative_contract(90.0))
    response = tool.update("B", {"North Axis": 45.0})
    assert not response.success
    assert cfg.building.north_axis == 0.0


def test_export_and_ep_audits_are_strict_and_bind_raw_bytes(tmp_path):
    """§7.4: export carries the zone-normalization evidence and simulate
    carries the actual IDF/EIO/ERR byte hashes; neither is a loose dict."""
    from src.agent.output_coordinates import (
        OutputCoordinateSnapshotV1,
        OutputCoordinateValidationContext,
        ZoneFrameNormalizationEntryV1,
        canonical_json_bytes,
        sha256_bytes,
    )
    from src.mcp.tools.workflow import WorkflowTool
    from src.validator.output_coordinates import EpCoordinateAuditV1, ExportCoordinateAuditV1

    cfg = apply_output_coordinate_contract(_config_with_zones(), _relative_contract(90.0))
    snapshot = canonical_json_bytes(OutputCoordinateSnapshotV1(zone_names=(), records=()))
    contract = _relative_contract(90.0).model_copy(
        update={"geometry_snapshot_sha256": sha256_bytes(snapshot)}
    )
    context = OutputCoordinateValidationContext(b"{}", None, snapshot)
    normalization = ZoneFrameNormalizationEntryV1(
        zone_name="Z2_high", before=(10.0, -3.0, 3.6, 45.0), after=(0.0, 0.0, 0.0, 0.0),
    )
    tool = WorkflowTool(
        cfg, output_coordinates=contract, validation_context=context,
        zone_frame_normalizations=(normalization,),
    )
    yaml_path, idf_path = tmp_path / "temp.yaml", tmp_path / "temp.idf"
    yaml_path.write_bytes(b"yaml")
    idf_path.write_bytes(b"idf")
    manager = SimpleNamespace(_idf=SimpleNamespace(idfobjects={"ZONE": []}))
    tool._write_coordinate_audit(tmp_path, yaml_path=yaml_path, idf_path=idf_path, manager=manager)
    export = ExportCoordinateAuditV1.model_validate_json(
        (tmp_path / "output_coordinate_audit.json").read_text(encoding="utf-8")
    )
    assert export.idf_sha256 == sha256_bytes(b"idf")
    assert export.zone_normalizations == (normalization,)
    ep_dir = tmp_path / "EP_run"
    ep_dir.mkdir()
    (ep_dir / "eplusout.eio").write_bytes(b"eio")
    (ep_dir / "eplusout.err").write_bytes(b"clean")
    tool._write_ep_coordinate_audit(ep_run_dir=ep_dir, idf_path=idf_path, completed=True)
    ep = EpCoordinateAuditV1.model_validate_json(
        (ep_dir / "output_coordinate_ep_audit.json").read_text(encoding="utf-8")
    )
    assert ep.idf_sha256 == sha256_bytes(b"idf")
    assert ep.eio_sha256 == sha256_bytes(b"eio")
    assert ep.err_sha256 == sha256_bytes(b"clean")
    assert ep.ignored_warning_hits == 0


def test_high_floor_surface_z_preserved_zone_origin_zeroed():
    import numpy as np

    from src.validator.data_model import SurfaceSchema

    cfg = ConfigState(building=BuildingSchema(name="B"))
    cfg.zones = [ZoneSchema.model_validate({"Name": "Z2_F2", "Z Origin": 3.6})]
    cfg.surfaces = [SurfaceSchema.model_validate({
        "Name": "Z2_F2_W1", "Surface Type": "Wall", "Construction Name": "C",
        "Zone Name": "Z2_F2", "Outside Boundary Condition": "Outdoors",
        "Sun Exposure": "SunExposed", "Wind Exposure": "WindExposed",
        "Number of Vertices": 4,
        "Vertices": np.array([
            [0.0, 0.0, 7.2], [0.0, 0.0, 3.6], [5.0, 0.0, 3.6], [5.0, 0.0, 7.2],
        ]),
    })]
    out = apply_output_coordinate_contract(cfg, _relative_contract())
    assert out.zones[0].z_origin == 0.0
    # surface vertices keep their true absolute z — the elevation was never
    # carried by the Zone origin in the serialized geometry
    assert [v[2] for v in out.surfaces[0].vertices] == [7.2, 3.6, 3.6, 7.2]


# --------------------------------------------------------------------------- #
# survival: pickle / deep copy / AgentState carry
# --------------------------------------------------------------------------- #
def test_contract_survives_pickle_and_agent_state_deep_copy():
    from src.agent.state import AgentState

    contract = _relative_contract(90.0)
    round_tripped = pickle.loads(pickle.dumps(contract))
    assert round_tripped == contract

    state = AgentState(output_coordinate_contract=contract)
    copied = state.model_copy(deep=True)
    assert copied.output_coordinate_contract == contract
    cfg = _config_with_zones()
    applied = apply_output_coordinate_contract(cfg, copied.output_coordinate_contract)
    deep = applied.model_copy(deep=True)
    assert deep.building.north_axis == 90.0
    assert validate_zone_frames_all_zero(deep) == []
