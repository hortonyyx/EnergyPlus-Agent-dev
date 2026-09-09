"""Offline tests for the explicit, closed-door EnergyPlus adapter."""
from __future__ import annotations

import copy

import pytest

from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.ep_branch import derive_ep_geometry
from src.agent.execution.ep_openings import EPOpeningError, derive_ep_doors, write_ep_doors
from src.agent.geometry.modelling import Surface, _newell, _orient
from src.agent.geometry.source_bim import build_source_bim
from src.agent.geometry.source_model import _digest
from src.agent.geometry.to_idf import building_to_idf


def _resign(source):
    source["source_model_sha256"] = _digest({key: value for key, value in source.items() if key != "source_model_sha256"})


def _source(*, exterior=False, state="unknown", kind="door"):
    payload = {
        "schema_version": "2", "footprint_x": [0, 8], "footprint_y": [0, 4],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "A", "x": [0, 4], "y": [0, 4]}, {"id": "B", "x": [4, 8], "y": [0, 4]},
        ]}],
        "openings": [{"id": "door", "kind": kind, "space_id": "A", "other_space_id": None if exterior else "B",
                      "p1": [1, 0] if exterior else [4, 1], "p2": [3, 0] if exterior else [4, 3],
                      "z": [0, 2.1], "state": state, "source_refs": ["test:door"]}],
    }
    return build_source_bim(CorrectedGeometry.model_validate(payload), capability_profile="orthogonal_polygon")


def _ep_geometry(source):
    # The existing branch deliberately rejects doors.  Remove only the door
    # from this temporary geometry derivation; the resulting base-surface map
    # is still derived from the exact same source spaces and boundaries.
    base = copy.deepcopy(source)
    base["openings"] = []
    base["opening_hosts"] = {}
    base["connections"] = []
    _resign(base)
    return derive_ep_geometry(base, {"A": "Zone_A", "B": "Zone_B"})


def _idf(bg):
    idf = building_to_idf(bg, boundary_validation_only=True)
    idf.newidfobject("MATERIAL", Name="Door_Material", Roughness="MediumSmooth", Thickness=.04,
                     Conductivity=.15, Density=700, Specific_Heat=1000)
    idf.newidfobject("CONSTRUCTION", Name="Default_Door", Outside_Layer="Door_Material")
    return idf


def _policy(**changes):
    value = {"state": "closed", "construction": "Default_Door", "reason": "本次热工模型明确按关闭门处理"}
    value.update(changes)
    return {"door": value}


def test_unknown_internal_door_needs_explicit_closed_policy_and_writes_reciprocal_door():
    source = _source()
    bg, mapping = _ep_geometry(source)
    with pytest.raises(EPOpeningError, match="explicit closed-door policy"):
        derive_ep_doors(source, bg, mapping["surfaces"], {})
    doors, audit = derive_ep_doors(source, bg, mapping["surfaces"], _policy())
    assert len(doors) == audit["door_surfaces"] == 2
    assert audit["source_doors"] == 1
    assert audit["doors"]["door"]["source_connectivity"] == "unknown"
    assert all(door.state == "closed" and door.partner for door in doors)
    idf = _idf(bg)
    write_ep_doors(idf, doors, audit)
    written = {item.Name: item for item in idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]}
    assert {item.Name for item in written.values()} == {door.name for door in doors}
    assert all(item.Surface_Type == "Door" and item.Construction_Name == "Default_Door" for item in written.values())
    assert all(written[door.name].Outside_Boundary_Condition_Object == door.partner for door in doors)


def test_exterior_door_is_single_sided_and_has_no_boundary_object():
    source = _source(exterior=True, state="closed")
    bg, mapping = _ep_geometry(source)
    doors, audit = derive_ep_doors(source, bg, mapping["surfaces"], _policy())
    assert len(doors) == 1 and not doors[0].partner and audit["doors"]["door"]["exterior"]
    idf = _idf(bg)
    write_ep_doors(idf, doors, audit)
    assert idf.idfobjects["FENESTRATIONSURFACE:DETAILED"][0].Outside_Boundary_Condition_Object == ""


@pytest.mark.parametrize(("kind", "state", "match"), [
    ("open", "open", "open passages/open doors"), ("door", "open", "open passages/open doors"),
])
def test_open_source_connection_is_never_represented_as_a_closed_door(kind, state, match):
    source = _source(kind=kind, state=state)
    bg, mapping = _ep_geometry(source)
    with pytest.raises(EPOpeningError, match=match):
        derive_ep_doors(source, bg, mapping["surfaces"], _policy())


@pytest.mark.parametrize("policy_change,match", [
    ({"state": "open"}, "explicit closed state"), ({"reason": ""}, "nonempty reason"),
    ({"construction": ""}, "needs a construction"),
])
def test_policy_must_record_all_closed_door_choices(policy_change, match):
    source = _source()
    bg, mapping = _ep_geometry(source)
    with pytest.raises(EPOpeningError, match=match):
        derive_ep_doors(source, bg, mapping["surfaces"], _policy(**policy_change))


def test_door_crossing_computational_parent_cuts_is_split_and_remains_one_to_one():
    source = _source()
    bg, mapping = _ep_geometry(source)
    paired = [surface for surface in bg.surfaces if surface.stype == "Wall" and surface.obc == "Surface"]
    assert len(paired) == 2
    for surface in paired:
        bg.surfaces.remove(surface)
        old_boundary = mapping["surfaces"].pop(surface.name)
        peers = [other for other in paired if other is not surface]
        partner = peers[0]
        for index, (lo, hi) in enumerate(((0, 2), (2, 4)), 1):
            vertices = _orient([(4, lo, 0), (4, hi, 0), (4, hi, 3), (4, lo, 3)], _newell(surface.verts))
            name = f"{surface.name}_cut{index}"
            bg.surfaces.append(Surface(name, surface.zone, "Wall", vertices, "Surface", f"{partner.name}_cut{index}"))
            mapping["surfaces"][name] = old_boundary
    doors, audit = derive_ep_doors(source, bg, mapping["surfaces"], _policy())
    assert len(doors) == audit["door_surfaces"] == 4
    assert {door.parent.rsplit("_cut", 1)[1] for door in doors} == {"1", "2"}
    assert all(door.partner for door in doors)


def test_derived_door_cannot_overlap_a_window_or_use_glazing_construction():
    source = _source()
    bg, mapping = _ep_geometry(source)
    doors, audit = derive_ep_doors(source, bg, mapping["surfaces"], _policy())
    bg.windows.append(type("Window", (), {"name": "collision", "parent": doors[0].parent, "verts": doors[0].verts})())
    with pytest.raises(EPOpeningError, match="overlapping derived apertures"):
        derive_ep_doors(source, bg, mapping["surfaces"], _policy())
    bg.windows.clear()
    idf = _idf(bg)
    idf.newidfobject("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM", Name="Glass", UFactor=2.5, Solar_Heat_Gain_Coefficient=.5)
    idf.idfobjects["CONSTRUCTION"][0].Outside_Layer = "Glass"
    with pytest.raises(EPOpeningError, match="not opaque"):
        write_ep_doors(idf, doors, audit)
    idf.idfobjects["CONSTRUCTION"][0].Outside_Layer = "unlisted_layer"
    with pytest.raises(EPOpeningError, match="unknown/non-opaque"):
        write_ep_doors(idf, doors, audit)
