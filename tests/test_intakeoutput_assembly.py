"""Step-5 deterministic parts: geometry serializer + 5_intakeoutput assembly +
contract validator. (The 4_MEP LLM stage is exercised e2e in Step 8.)"""

from __future__ import annotations

from src.agent.correction.schema import CorrectedGeometry, Window
from src.agent.geometry import build_geometry
from src.agent.geometry.specs import CONSTRUCTION_VOCAB, serialize_geometry
from src.agent.intakeoutput import (
    MepOutput,
    assemble_intake_output,
    validate_contract,
)
from src.validator import BuildingSchema, SiteLocationSchema


def _two_floor_with_window() -> CorrectedGeometry:
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
                {"id": "F1_L", "x": [0, 5], "y": [0, 8], "role": "office"},
                {"id": "F1_R", "x": [5, 10], "y": [0, 8], "role": "corridor"}]},
            {"name": "F2", "z_floor": 3.0, "ceiling_height": 3.0, "cells": [
                {"id": "F2_L", "x": [0, 4], "y": [0, 8], "role": "office"},
                {"id": "F2_R", "x": [4, 10], "y": [0, 8], "role": "office"}]},
        ],
    )
    g.windows = [Window(id="W1", floor="F1", facade="South",
                        span=[1.0, 3.0], z=[0.9, 2.4], room="F1_L")]
    return g


def test_serialize_geometry_shape():
    bg = build_geometry(_two_floor_with_window())
    zone_specs, surface_specs, fen_specs, used = serialize_geometry(bg)

    # every zone present with its z + role
    for zone in ("F1_L", "F1_R", "F2_L", "F2_R"):
        assert zone in zone_specs
    assert "ceiling_height=3.00" in zone_specs
    assert "role: corridor" in zone_specs  # role carried through ZoneVolume

    # interzone walls name an adjacent zone; ground/roof constructions appear
    assert "adjacent_zone=" in surface_specs
    assert CONSTRUCTION_VOCAB["interfloor"] in surface_specs   # Cons_InterFloor
    assert CONSTRUCTION_VOCAB["ground_floor"] in surface_specs
    assert CONSTRUCTION_VOCAB["roof"] in surface_specs

    # the window is serialized with the window construction
    assert "parent=" in fen_specs
    assert CONSTRUCTION_VOCAB["window"] in fen_specs

    # used set = constructions actually emitted (incl interfloor + window)
    assert CONSTRUCTION_VOCAB["interfloor"] in used
    assert CONSTRUCTION_VOCAB["window"] in used


def test_serialize_no_windows_is_explicit():
    """A model with zero windows must say so unambiguously (else the downstream
    fenestration agent invents windows — sm21 e2e hallucinated 24)."""
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
            {"id": "A", "x": [0, 5], "y": [0, 8]},
            {"id": "B", "x": [5, 10], "y": [0, 8]}]}],
    )  # no windows
    zs, ss, fen, used = serialize_geometry(build_geometry(g))
    assert "NO windows" in fen and "Do NOT create" in fen
    assert CONSTRUCTION_VOCAB["window"] not in used  # no window construction needed
    # the early-return must still yield the full, well-formed geometry tuple
    assert "A" in zs and "B" in zs               # zone_specs complete
    assert "adjacent_zone=" in ss                # surface_specs complete (paired)
    assert CONSTRUCTION_VOCAB["ext_wall"] in used  # structural constructions present


def _mep(construction_specs: str) -> MepOutput:
    return MepOutput(
        building=BuildingSchema(name="T"),
        site_location=SiteLocationSchema(
            name="Shenzhen_CN", latitude=22.5, longitude=114.0,
            time_zone=8.0, elevation=5.0),
        material_specs="Mat_X", construction_specs=construction_specs,
        schedule_specs="Sch", hvac_specs="H", people_specs="P", lights_specs="L",
    )


def test_assembly_and_contract_pass():
    bg = build_geometry(_two_floor_with_window())
    zs, ss, fs, used = serialize_geometry(bg)
    cons_text = "\n".join(f"{c}: defined" for c in used)
    intake = assemble_intake_output(
        zone_specs=zs, surface_specs=ss, fenestration_specs=fs, mep=_mep(cons_text)
    )
    assert intake.surface_specs == ss and intake.zone_specs == zs
    assert validate_contract(intake, used) == []


def test_contract_catches_missing_construction():
    bg = build_geometry(_two_floor_with_window())
    zs, ss, fs, used = serialize_geometry(bg)
    # define everything EXCEPT Cons_InterFloor -> must be flagged
    cons_text = "\n".join(
        f"{c}: defined" for c in used if c != CONSTRUCTION_VOCAB["interfloor"]
    )
    intake = assemble_intake_output(
        zone_specs=zs, surface_specs=ss, fenestration_specs=fs, mep=_mep(cons_text)
    )
    issues = validate_contract(intake, used)
    assert any(CONSTRUCTION_VOCAB["interfloor"] in i for i in issues)


def test_contract_token_match_not_substring():
    """`Default_Ext_Wall` defined must NOT satisfy a need for `Default_Ext_Wall_2`."""
    intake = assemble_intake_output(
        zone_specs="z", surface_specs="s", fenestration_specs="f",
        mep=_mep("Default_Ext_Wall: defined"),
    )
    issues = validate_contract(intake, {"Default_Ext_Wall_2"})
    assert issues  # substring must not count as defined
