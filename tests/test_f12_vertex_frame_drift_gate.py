"""F-12 followup (2026-08-07 crossreview dispatch, MINOR): unit locks for the
``VERTEX_FRAME_DRIFT`` BEHAVIOR gate (`src/validator/output_coordinates.py`:
`_vertex_drift_issues` / `_live_idf_vertex_drift_issues`).

Background: F-12's existing locks (`tests/test_f12_surface_prompt_transcribe.py`)
are all prompt-text regexes; GLM neuter B showed a reworded-but-still-orders-
recompute prompt sails through all five of them unchanged. The prompt locks
only catch regression to specific old wording — the real defense is this gate,
which compares vertices actually present in ConfigState / the live IDF against
a frozen pre-E4 snapshot, independent of what any prompt said. That gate had
zero unit coverage before this file (only end-to-end runs exercised it) —
`grep` for its distinguishing message text ("vertices differ from the pre-E4
snapshot") across `tests/` before this file returns nothing.

Two call sites, both covered:
  - ConfigState side: `_vertex_drift_issues` (compares `config.surfaces` /
    `config.fenestrations` against the snapshot).
  - Live-IDF side: `_live_idf_vertex_drift_issues` (compares the actual eppy
    IDF objects against the snapshot — the BO-CR5 "never trust ConfigState
    alone" terminal check, since a converter or raw-fragment injection can
    change the live IDF without touching ConfigState).

Each side gets: (1) a negative control — vertices identical to the snapshot
must NOT report VERTEX_FRAME_DRIFT (proves the lock isn't vacuously always
red); (2) a positive case — the *minimal* possible drift (the ring's start
vertex rolled by one position; same point set, same winding, different start
index) must still be caught, landed on the concrete check-id and surface name,
not "count changed" / "not None". Two more tests drive the SAME two scenarios
through the public `validate_output_coordinate_contract` entry point (not the
private helpers directly) to prove both paths are actually wired into the
gate real callers use, and that each side is checked independently of the
other (a clean ConfigState does not mask a drifted live IDF, and vice versa —
this is the BO-CR5 rationale already documented on `_live_idf_vertex_drift_issues`,
reproduced here as a unit lock instead of only an end-to-end story).
"""
from __future__ import annotations

import numpy as np
import pytest

from src.agent._share import IDD_PATH, ensure_schema_initialized
from src.agent.output_coordinates import (
    AcceptedCorrectionRef,
    CoordinateRecordV1,
    OutputCoordinateContract,
    OutputCoordinateSnapshotV1,
    OutputCoordinateValidationContext,
    canonical_json_bytes,
    sha256_bytes,
)
from src.mcp.state import ConfigState
from src.validator import BuildingSchema
from src.validator.data_model import BaseSchema, SurfaceSchema
from src.validator.output_coordinates import (
    _live_idf_vertex_drift_issues,
    _vertex_drift_issues,
    validate_output_coordinate_contract,
)

HEX64 = "a" * 64

# A simple rectangular wall ring — the "pre-E4 snapshot" / canonical values.
_CANON = np.array([
    [0.0, 0.0, 3.0],
    [0.0, 0.0, 0.0],
    [5.0, 0.0, 0.0],
    [5.0, 0.0, 3.0],
])
# The minimal possible drift: same 4 points, same winding, start vertex
# rolled by one position — exactly the shape of drift the F-13 lock2/lock3
# tests use for "start_vertex_rotated" (see test_f13_kernel_canonical_vertex_order.py).
_DRIFTED = np.roll(_CANON, 1, axis=0)


@pytest.fixture(autouse=True)
def _init_schema():
    ensure_schema_initialized()


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _wall_surface(vertices: np.ndarray) -> SurfaceSchema:
    return SurfaceSchema.model_validate({
        "Name": "W1", "Surface Type": "Wall", "Construction Name": "C",
        "Zone Name": "Z1", "Outside Boundary Condition": "Outdoors",
        "Sun Exposure": "SunExposed", "Wind Exposure": "WindExposed",
        "Number of Vertices": 4, "Vertices": vertices,
    })


def _snapshot(vertices: np.ndarray) -> OutputCoordinateSnapshotV1:
    return OutputCoordinateSnapshotV1(
        zone_names=("Z1",),
        records=(CoordinateRecordV1(
            object_type="BuildingSurface:Detailed", name="W1", zone_or_parent="Z1",
            vertices=tuple(tuple(round(float(c), 2) for c in v) for v in vertices),
        ),),
    )


def _config(surfaces: list[SurfaceSchema]) -> ConfigState:
    cfg = ConfigState(building=BuildingSchema(name="B"))
    cfg.surfaces = surfaces
    return cfg


def _idf_with_wall(vertices: np.ndarray):
    """A fresh live eppy IDF carrying exactly one BuildingSurface:Detailed
    'W1' with the given vertices — same reset-per-call pattern as
    `_fresh_idf()`/`_fresh_idf_manager()` in the sibling output-coordinate
    test files (BaseSchema._idf is a process-wide singleton)."""
    BaseSchema.set_idf(IDD_PATH)
    idf = BaseSchema.get_idf()
    idf.newidfobject("ZONE", Name="Z1")
    kwargs = {
        "Name": "W1", "Surface_Type": "Wall", "Zone_Name": "Z1",
        "Outside_Boundary_Condition": "Outdoors", "Number_of_Vertices": 4,
    }
    for i, (x, y, z) in enumerate(vertices, start=1):
        kwargs[f"Vertex_{i}_Xcoordinate"] = float(x)
        kwargs[f"Vertex_{i}_Ycoordinate"] = float(y)
        kwargs[f"Vertex_{i}_Zcoordinate"] = float(z)
    idf.newidfobject("BUILDINGSURFACE:DETAILED", **kwargs)
    return idf


def _contract(raw_snapshot: bytes) -> OutputCoordinateContract:
    return OutputCoordinateContract(
        mode="relative_north_axis",
        source=AcceptedCorrectionRef(
            schema_version="3", output_sha256=HEX64,
            acceptance="integrated_gate1", artifact_contract="correction_e4_orientation_v1",
        ),
        geometry_frame="building_axis_absolute_values",
        global_geometry_coordinate_system="Relative",
        daylighting_reference_point_coordinate_system="Relative",
        rectangular_surface_coordinate_system="Relative",
        zone_origin_policy="all_zero", zone_direction_policy="all_zero",
        north_axis_owner="accepted_correction_orientation", north_axis_deg=0.0,
        orientation_provenance="assumed",
        geometry_snapshot_sha256=sha256_bytes(raw_snapshot),
    )


def _context(raw_snapshot: bytes) -> OutputCoordinateValidationContext:
    return OutputCoordinateValidationContext(
        raw_intake_output_bytes=b"{}", verified_correction=None, raw_snapshot_bytes=raw_snapshot,
    )


# --------------------------------------------------------------------------- #
# ConfigState side — `_vertex_drift_issues`
# --------------------------------------------------------------------------- #
def test_configstate_side_negative_no_drift_when_vertices_match_snapshot():
    """Negative control: vertices identical to the frozen snapshot must NOT
    report VERTEX_FRAME_DRIFT. Without this, a lock that fires unconditionally
    would look identical to a real one (see the F-12 followup dispatch §2.1)."""
    snapshot = _snapshot(_CANON)
    config = _config([_wall_surface(_CANON)])
    assert _vertex_drift_issues(config, snapshot) == []


def test_configstate_side_reports_drift_when_start_vertex_is_rotated():
    """The minimal drift (start vertex rolled by one, same ring) must still be
    caught, landed on the concrete check-id and surface name — not a count or
    non-None check."""
    snapshot = _snapshot(_CANON)  # pre-E4 snapshot
    config = _config([_wall_surface(_DRIFTED)])  # post-E4 ConfigState, rolled
    issues = _vertex_drift_issues(config, snapshot)
    drift = [i for i in issues if i.code == "VERTEX_FRAME_DRIFT"]
    assert drift, f"rotated start vertex was not flagged: {issues}"
    assert any(
        "W1" in i.message and "vertices differ from the pre-E4 snapshot" in i.message
        for i in drift
    ), drift


# --------------------------------------------------------------------------- #
# Live-IDF side — `_live_idf_vertex_drift_issues`
# --------------------------------------------------------------------------- #
def test_idf_side_negative_no_drift_when_vertices_match_snapshot():
    snapshot = _snapshot(_CANON)
    idf = _idf_with_wall(_CANON)
    assert _live_idf_vertex_drift_issues(snapshot, idf) == []


def test_idf_side_reports_drift_when_start_vertex_is_rotated():
    snapshot = _snapshot(_CANON)
    idf = _idf_with_wall(_DRIFTED)
    issues = _live_idf_vertex_drift_issues(snapshot, idf)
    drift = [i for i in issues if i.code == "VERTEX_FRAME_DRIFT"]
    assert drift, f"rotated start vertex was not flagged on the live IDF: {issues}"
    assert any(
        "W1" in i.message and "vertices differ from the pre-E4 snapshot" in i.message
        for i in drift
    ), drift


# --------------------------------------------------------------------------- #
# Wiring — both paths are actually reachable through the public gate, and
# each is checked independently of the other (BO-CR5 rationale as a lock).
# --------------------------------------------------------------------------- #
def test_full_gate_negative_when_both_sides_match_snapshot():
    snapshot = _snapshot(_CANON)
    raw_snapshot = canonical_json_bytes(snapshot)
    contract = _contract(raw_snapshot)
    context = _context(raw_snapshot)
    config = _config([_wall_surface(_CANON)])
    idf = _idf_with_wall(_CANON)
    issues = validate_output_coordinate_contract(config, contract, context, idf=idf)
    assert not [i for i in issues if i.code == "VERTEX_FRAME_DRIFT"], issues


def test_full_gate_reports_live_idf_drift_even_when_configstate_matches():
    """A pristine ConfigState (identity holds) does not mask a drifted live
    IDF — the exact scenario `_live_idf_vertex_drift_issues`'s own docstring
    calls out (a converter or raw-IDF injection changing live fields after
    ConfigState was already validated)."""
    snapshot = _snapshot(_CANON)
    raw_snapshot = canonical_json_bytes(snapshot)
    contract = _contract(raw_snapshot)
    context = _context(raw_snapshot)
    config = _config([_wall_surface(_CANON)])   # ConfigState side: clean
    idf = _idf_with_wall(_DRIFTED)                # live IDF side: drifted
    issues = validate_output_coordinate_contract(config, contract, context, idf=idf)
    drift = [i for i in issues if i.code == "VERTEX_FRAME_DRIFT"]
    assert any(
        "vertices differ from the pre-E4 snapshot" in i.message for i in drift
    ), drift


def test_full_gate_reports_configstate_drift_even_when_live_idf_matches():
    """Mirror of the previous test: the ConfigState-side comparison is checked
    independently of whatever the live IDF says."""
    snapshot = _snapshot(_CANON)
    raw_snapshot = canonical_json_bytes(snapshot)
    contract = _contract(raw_snapshot)
    context = _context(raw_snapshot)
    config = _config([_wall_surface(_DRIFTED)])  # ConfigState side: drifted
    idf = _idf_with_wall(_CANON)                   # live IDF side: clean
    issues = validate_output_coordinate_contract(config, contract, context, idf=idf)
    drift = [i for i in issues if i.code == "VERTEX_FRAME_DRIFT"]
    assert any(
        "vertices differ from the pre-E4 snapshot" in i.message for i in drift
    ), drift
