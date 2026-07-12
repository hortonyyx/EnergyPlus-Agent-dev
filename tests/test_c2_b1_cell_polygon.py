from __future__ import annotations

import pytest

from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.correction.config import CoreTolerances
from src.agent.geometry import build_geometry
from src.agent.geometry.specs import serialize_geometry
from src.agent.geometry.to_idf import building_to_idf
from src.validator.checks.correction import check_correction
from src.validator.checks.kernel import check_kernel
from src.validator.interzone import validate_interzone_surface_pairs


def _tol(**over) -> CoreTolerances:
    base = dict(
        axis_jitter_tol_m=0.05,
        cross_floor_align_tol_m=0.11,
        structural_snap_grid_m=0.05,
        min_edge_length_m=0.10,
        output_precision_m=0.01,
        window_snap_grid_m=0.01,
        window_clamp_to_parent=True,
        envelope_reconcile_tol_m=0.30,
        coverage_area_tol_m2=0.05,
        gap_close_threshold_m=0.30,
        gap_arbitration_band_m=1.00,
        # Vg rework CR5 (§10.1): these two carry no dataclass default any
        # more — every helper must pass them explicitly; override via `over`
        # when a test needs a different value.
        facade_visibility_depth_epsilon_m=1e-9,
        facade_visibility_endpoint_epsilon_m=1e-9,
    )
    base.update(over)
    t = CoreTolerances(**base)
    t.validate()
    return t


def _l_shape_geom() -> CorrectedGeometry:
    return CorrectedGeometry.model_validate(
        {
            "schema_version": "2",
            "footprint_x": [0.0, 10.0],
            "footprint_y": [0.0, 10.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {
                            "id": "L_corridor",
                            "role": "corridor",
                            "x": [0.0, 10.0],
                            "y": [0.0, 10.0],
                            "polygon": [
                                [0.0, 0.0],
                                [10.0, 0.0],
                                [10.0, 6.0],
                                [6.0, 6.0],
                                [6.0, 10.0],
                                [0.0, 10.0],
                            ],
                        },
                        {
                            "id": "Notch_room",
                            "role": "office",
                            "x": [6.0, 10.0],
                            "y": [6.0, 10.0],
                        },
                    ],
                }
            ],
            "windows": [],
        }
    )


def test_l_shape_polygon_runs_modelling_split_pairing_specs_and_interzone_clean():
    geom = _l_shape_geom()
    rep = check_correction(geom, capability_profile="orthogonal_polygon")
    assert not rep.blocking(), [r.check_id for r in rep.blocking()]

    bg = build_geometry(geom, capability_profile="orthogonal_polygon")
    issues = validate_interzone_surface_pairs(building_to_idf(bg))
    assert issues == []

    zone_specs, surface_specs, fenestration_specs, used = serialize_geometry(bg)
    assert "Corridor" in zone_specs
    assert "interior wall" in surface_specs
    assert fenestration_specs
    assert used

    l_zone = next(zv.zone for zv in bg.zone_volumes if zv.cell_id == "L_corridor")
    l_wall_xy = {
        tuple(sorted({(round(v[0], 2), round(v[1], 2)) for v in s.verts}))
        for s in bg.surfaces
        if s.zone == l_zone and s.stype == "Wall"
    }
    assert ((6.0, 6.0), (10.0, 6.0)) in l_wall_xy
    assert ((6.0, 6.0), (6.0, 10.0)) in l_wall_xy
    assert ((10.0, 6.0), (10.0, 10.0)) not in l_wall_xy


def test_sm24_c_shape_corridor_and_l_shape_office_normals_and_interzone_clean():
    geom = CorrectedGeometry.model_validate(
        {
            "schema_version": "2",
            "footprint_x": [0.1, 9.9],
            "footprint_y": [0.1, 19.9],
            "floors": [
                {
                    "name": "Floor 1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {"id": "conference", "x": [0.1, 4.2], "y": [0.1, 8.05]},
                        {"id": "west_office", "x": [0.1, 4.2], "y": [8.05, 13.0]},
                        {"id": "west_meeting", "x": [0.1, 4.2], "y": [13.0, 15.95]},
                        {"id": "north_office", "x": [0.1, 9.9], "y": [15.95, 19.9]},
                        {
                            "id": "corridor",
                            "role": "corridor",
                            "x": [4.2, 9.9],
                            "y": [3.45, 15.95],
                            "polygon": [
                                [4.2, 3.45],
                                [5.8, 3.45],
                                [5.8, 4.95],
                                [9.9, 4.95],
                                [9.9, 8.05],
                                [5.8, 8.05],
                                [5.8, 15.95],
                                [4.2, 15.95],
                            ],
                        },
                        {"id": "east_office", "x": [5.8, 9.9], "y": [8.05, 14.0]},
                        {"id": "ne_cabinet", "x": [5.8, 9.9], "y": [14.0, 15.95]},
                        {
                            "id": "se_office",
                            "x": [4.2, 9.9],
                            "y": [0.1, 4.95],
                            "polygon": [
                                [4.2, 0.1],
                                [9.9, 0.1],
                                [9.9, 4.95],
                                [5.8, 4.95],
                                [5.8, 3.45],
                                [4.2, 3.45],
                            ],
                        },
                    ],
                }
            ],
            "windows": [],
        }
    )

    bg = build_geometry(geom, capability_profile="orthogonal_polygon")
    kernel = check_kernel(bg, capability_profile="orthogonal_polygon")
    blocking = {r.check_id: r for r in kernel.blocking()}
    assert "kernel.normals" not in blocking
    assert "kernel.pairing_gate" not in blocking
    assert validate_interzone_surface_pairs(building_to_idf(bg)) == []


def test_polygon_snap_updates_vertices_and_rederives_bbox():
    geom = CorrectedGeometry.model_validate(
        {
            "schema_version": "2",
            "footprint_x": [0.0, 10.0],
            "footprint_y": [0.0, 8.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {
                            "id": "P",
                            "x": [0.0, 9.99],
                            "y": [0.0, 8.0],
                            "polygon": [[0.0, 0.0], [9.99, 0.0], [9.99, 8.0], [0.0, 8.0]],
                        }
                    ],
                }
            ],
        }
    )

    out = apply_deterministic_core(geom, _tol(), capability_profile="orthogonal_polygon")

    cell = out.floors[0].cells[0]
    assert cell.x == [0.0, 10.0]
    assert cell.y == [0.0, 8.0]
    assert cell.polygon == [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]]


@pytest.mark.parametrize(
    ("polygon", "match"),
    [
        ([[0, 0], [0, 8], [10, 8], [10, 0]], "CCW"),
        ([[0, 0], [6, 0], [6, 6], [2, 6], [2, 2], [8, 2], [8, 8], [0, 8]], "invalid|self-intersecting"),
        ([[0, 0], [10, 0], [10, 8], [0, 0]], "repeat|degenerate"),
        ([[0, 0], [10, 0], [10, 8], [0, 7]], "not orthogonal"),
    ],
)
def test_invalid_polygons_raise(polygon, match):
    geom = CorrectedGeometry.model_validate(
        {
            "schema_version": "2",
            "footprint_x": [0.0, 10.0],
            "footprint_y": [0.0, 8.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {"id": "Bad", "x": [0.0, 10.0], "y": [0.0, 8.0], "polygon": polygon}
                    ],
                }
            ],
        }
    )

    with pytest.raises(ValueError, match=match):
        build_geometry(geom, capability_profile="orthogonal_polygon")


def test_polygon_bbox_mismatch_blocks_gate_and_raises_kernel():
    geom = CorrectedGeometry.model_validate(
        {
            "schema_version": "2",
            "footprint_x": [0.0, 10.0],
            "footprint_y": [0.0, 8.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {
                            "id": "Bad",
                            "x": [0.0, 9.0],
                            "y": [0.0, 8.0],
                            "polygon": [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]],
                        }
                    ],
                }
            ],
        }
    )

    rep = check_correction(geom, capability_profile="orthogonal_polygon")
    assert "correction.cell_polygon_contract" in {r.check_id for r in rep.blocking()}
    with pytest.raises(ValueError, match="does not match polygon bbox"):
        build_geometry(geom, capability_profile="orthogonal_polygon")


def test_v1_polygon_is_rejected_as_undeclared_shape():
    geom = _l_shape_geom().model_copy(update={"schema_version": "1"})

    rep = check_correction(geom, capability_profile="orthogonal_polygon")
    assert "correction.cell_polygon_contract" in {r.check_id for r in rep.blocking()}
    with pytest.raises(ValueError, match="schema_version '2'"):
        build_geometry(geom, capability_profile="orthogonal_polygon")
