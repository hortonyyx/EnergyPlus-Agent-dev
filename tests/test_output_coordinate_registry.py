"""E4-output-contract spec v2 §10.5 — building-bound coordinate object
registry: IDD completeness double-empty diff, unsupported/unclassified BLOCK
behavior on a live eppy IDF, site-world exemption, host-local gating."""

from __future__ import annotations

import pytest

from src.agent._share import IDD_PATH, ensure_schema_initialized
from src.validator.output_coordinates import (
    EXCLUSIONS,
    REGISTRY,
    final_idf_layer_offenders,
    idd_layer_candidates,
    idd_layer_completeness_diff,
    registered_object_types,
    supported_object_types,
)


@pytest.fixture(autouse=True)
def _init_schema():
    ensure_schema_initialized()


def _fresh_idf():
    from src.validator.data_model import BaseSchema

    BaseSchema.set_idf(IDD_PATH)
    return BaseSchema.get_idf()


# --------------------------------------------------------------------------- #
# completeness
# --------------------------------------------------------------------------- #
def test_idd_candidates_minus_registry_is_empty():
    unregistered, _ghost = idd_layer_completeness_diff()
    assert unregistered == frozenset(), (
        f"IDD coordinate candidates with no registry/exclusion entry: {sorted(unregistered)}"
    )


def test_registry_completeness_all_layers_double_empty():
    """BO-CR6: the four-layer closed-world audit — IDD scan, live schema
    reflection, producer AST scan, and the registry itself — must have EVERY
    diff empty. No standing ghost exemption list exists anymore."""
    from src.validator.output_coordinates import registry_completeness_diffs

    diffs = registry_completeness_diffs()
    non_empty = {name: sorted(values) for name, values in diffs.items() if values}
    assert non_empty == {}, f"registry completeness diffs are not double-empty: {non_empty}"


def test_schema_layer_reflects_live_pydantic_schemas():
    from src.validator.output_coordinates import schema_layer_candidates

    assert schema_layer_candidates() == frozenset({
        "Building", "Zone", "GlobalGeometryRules", "Site:Location",
        "BuildingSurface:Detailed", "FenestrationSurface:Detailed",
    })


def test_producer_scan_finds_every_coordinate_writer():
    from src.validator.output_coordinates import producer_layer_scan

    assert producer_layer_scan() == frozenset({
        "Building", "Zone", "GlobalGeometryRules", "Site:Location",
        "BuildingSurface:Detailed", "FenestrationSurface:Detailed",
    })


def test_supported_set_is_exactly_the_current_producers():
    assert supported_object_types() == frozenset({
        "Building", "Zone", "GlobalGeometryRules",
        "BuildingSurface:Detailed", "FenestrationSurface:Detailed",
    })


def test_every_exclusion_has_a_concrete_reason():
    for rule in EXCLUSIONS:
        assert rule.reason and rule.reason != "*" and len(rule.reason) > 20


def test_registry_rows_have_frame_class_and_ggr_owner():
    for rule in REGISTRY:
        assert rule.frame_class
        assert rule.controlling_ggr_field
        assert rule.current_support in ("supported", "unsupported")


def test_site_shading_is_world_exempt_not_zone_bound():
    by_type = {r.object_type: r for r in REGISTRY}
    assert by_type["Shading:Site"].frame_class == "site_world_exempt"
    assert by_type["Shading:Site:Detailed"].frame_class == "site_world_exempt"
    # and the zone-frame-zero check has nothing to do with them (frame class
    # is the discriminator; they are NOT detailed_zone_bound)
    assert by_type["Shading:Site:Detailed"].frame_class != "detailed_zone_bound"


def test_pvwatts_is_predicate_conditional_not_type_classified():
    by_type = {r.object_type: r for r in REGISTRY}
    assert by_type["Generator:PVWatts"].variant_predicate != "always"
    assert by_type["AirflowNetwork:SimulationControl"].frame_class == "true_north_parameter"


# --------------------------------------------------------------------------- #
# live-IDF layer 4
# --------------------------------------------------------------------------- #
def test_supported_production_objects_walk_through():
    idf = _fresh_idf()
    idf.newidfobject("BUILDING", Name="B")
    idf.newidfobject("GLOBALGEOMETRYRULES",
                     Starting_Vertex_Position="UpperLeftCorner",
                     Vertex_Entry_Direction="Counterclockwise",
                     Coordinate_System="Relative")
    idf.newidfobject("ZONE", Name="Z1")
    idf.newidfobject("MATERIAL", Name="M", Roughness="MediumRough", Thickness=0.1,
                     Conductivity=1.4, Density=2200, Specific_Heat=900)
    assert final_idf_layer_offenders(idf) == []


@pytest.mark.parametrize("obj_type,kwargs", [
    ("WALL:DETAILED", {"Name": "W", "Zone_Name": "Z1"}),
    ("SHADING:ZONE:DETAILED", {"Name": "S", "Base_Surface_Name": "W"}),
    ("SHADING:BUILDING:DETAILED", {"Name": "SB"}),
    ("DAYLIGHTING:REFERENCEPOINT", {"Name": "RP", "Zone_or_Space_Name": "Z1"}),
    ("WINDOW", {"Name": "Win", "Building_Surface_Name": "W"}),
    ("SHADING:OVERHANG", {"Name": "OH", "Window_or_Door_Name": "Win"}),
    ("SHADING:SITE:DETAILED", {"Name": "SS"}),
])
def test_unsupported_coordinate_objects_block(obj_type, kwargs):
    idf = _fresh_idf()
    idf.newidfobject("ZONE", Name="Z1")
    idf.newidfobject(obj_type, **kwargs)
    offenders = final_idf_layer_offenders(idf)
    assert offenders
    assert all(o.code == "UNSUPPORTED_COORDINATE_OBJECT" for o in offenders)
    assert any("registry marks unsupported" in o.message for o in offenders)


def test_excluded_site_location_never_flags():
    idf = _fresh_idf()
    idf.newidfobject("SITE:LOCATION", Name="S", Latitude=22.5, Longitude=114.0,
                     Time_Zone=8.0, Elevation=5.0)
    assert final_idf_layer_offenders(idf) == []


def test_non_spatial_objects_are_not_candidates():
    idf = _fresh_idf()
    idf.newidfobject("SCHEDULETYPELIMITS", Name="Fraction")
    idf.newidfobject("MATERIAL:NOMASS", Name="NM", Roughness="Rough",
                     Thermal_Resistance=2.0)
    idf.newidfobject("PEOPLE", Name="P", Zone_or_ZoneList_or_Space_or_SpaceList_Name="Z")
    assert final_idf_layer_offenders(idf) == []


def test_registry_object_types_are_unique():
    names = [r.object_type for r in REGISTRY] + [r.object_type for r in EXCLUSIONS]
    assert len(names) == len(set(names))


def test_idd_scan_actually_parses_the_bundled_idd():
    candidates = idd_layer_candidates()
    # the \format vertices objects must always be present
    for name in ("Zone", "BuildingSurface:Detailed", "Wall:Detailed",
                 "FenestrationSurface:Detailed", "Shading:Site:Detailed",
                 "Shading:Building:Detailed", "Shading:Zone:Detailed"):
        assert name in candidates
    # every IDD candidate is registered or explicitly excluded — a REAL
    # assertion (the previous `or True` vacuous form was BO-CR6)
    assert candidates <= registered_object_types(), sorted(candidates - registered_object_types())


def test_host_local_window_without_host_blocks():
    idf = _fresh_idf()
    idf.newidfobject("ZONE", Name="Z1")
    idf.newidfobject("WINDOW", Name="Win1")  # no Building_Surface_Name at all
    offenders = final_idf_layer_offenders(idf)
    assert any("no host surface reference" in o.message for o in offenders)


def test_host_local_window_with_unresolvable_host_blocks():
    idf = _fresh_idf()
    idf.newidfobject("ZONE", Name="Z1")
    idf.newidfobject("WINDOW", Name="Win1", Building_Surface_Name="GhostWall")
    offenders = final_idf_layer_offenders(idf)
    assert any("does not exist in the IDF" in o.message for o in offenders)


def test_host_local_window_with_real_host_still_unsupported_but_chain_ok():
    idf = _fresh_idf()
    idf.newidfobject("ZONE", Name="Z1")
    idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="W1", Surface_Type="Wall",
                     Zone_Name="Z1", Outside_Boundary_Condition="Outdoors",
                     Number_of_Vertices=4)
    idf.newidfobject("WINDOW", Name="Win1", Building_Surface_Name="W1")
    offenders = final_idf_layer_offenders(idf)
    # still blocked as an unsupported producer, but with an intact host chain
    assert any(o.code == "UNSUPPORTED_COORDINATE_OBJECT" and "registry marks unsupported" in o.message
               for o in offenders)
    assert not any("host" in o.message and "not exist" in o.message for o in offenders)
