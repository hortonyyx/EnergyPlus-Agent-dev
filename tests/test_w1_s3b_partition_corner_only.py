"""W-1 S3b locks: corner-only reduction is a PARTITION-PRODUCER invariant.

Ruling 2026-09-07x §二: the W-1 S3 fix applied ``_corner_only_ring`` to the
footprint ring only, while the cells kept the same batch of collinear
subdivision vertices (measured on the real chain: cell min edges
1.62 / 0.55 cm — unpassable downstream).  The promotion moves the reduction
to ``partition_lines`` so EVERY ring it emits (each face AND the footprint)
leaves in corner-only form and no consumer can forget it.

These locks pin the class, not the example:
  * the synthetic T-junction fixture reds pre-promotion (the face carried
    the landing vertex) and greens after — discriminating power, not just
    "the new code produces what the new code produces";
  * the REAL chain probe products (git-tracked) stay geometrically
    identical under the production helper — the reduction is lossless,
    asserted as exact curve equality (zero tolerance), and the reduced
    rings clear the downstream min-edge floor with margin;
  * the helper is NOT an edge-length filter: a genuine jog corner survives
    however short the edges it creates.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from shapely.geometry import LineString

from src.agent.correction.projection_bridge import (
    CutLineV1,
    _corner_only_ring,
    partition_lines,
    project_cut_lines,
)

REPO = Path(__file__).resolve().parents[1]
PROBE = (
    REPO / "AI_agent/logs/experiments/2026-09-07h_w1_t1_probe/newleg_probe"
)
#: gate①'s ``_MIN_EXTENT`` family (parse._ring_checks refuses shorter
#: edges); the finalize gate is 0.10 m — the stricter floor here is 0.05.
MIN_EDGE_FLOOR_M = 0.05


def _t_junction_lines() -> list[CutLineV1]:
    """A 10×6 rectangle, a full-height wall at x=5 and a wall along y=3
    from the left skin to x=7 (its far end dangles inside the right
    region).  The x=5 wall is crossed at (5, 3): the RIGHT face's straight
    left edge gets a collinear subdivision vertex there, and the footprint
    skin carries the landings (5, 0) / (5, 6) / (0, 3) mid-edge."""
    outer = [
        CutLineV1(axis="x", pos_m=0.0, along_lo_m=0.0, along_hi_m=10.0,
                  half_thickness_m=0.1, kind="wall", origin_id="bottom"),
        CutLineV1(axis="x", pos_m=6.0, along_lo_m=0.0, along_hi_m=10.0,
                  half_thickness_m=0.1, kind="wall", origin_id="top"),
        CutLineV1(axis="y", pos_m=0.0, along_lo_m=0.0, along_hi_m=6.0,
                  half_thickness_m=0.1, kind="wall", origin_id="left"),
        CutLineV1(axis="y", pos_m=10.0, along_lo_m=0.0, along_hi_m=6.0,
                  half_thickness_m=0.1, kind="wall", origin_id="right"),
    ]
    inner = [
        CutLineV1(axis="y", pos_m=5.0, along_lo_m=0.0, along_hi_m=6.0,
                  half_thickness_m=0.1, kind="wall", origin_id="mid-v"),
        CutLineV1(axis="x", pos_m=3.0, along_lo_m=0.0, along_hi_m=7.0,
                  half_thickness_m=0.1, kind="wall", origin_id="mid-h"),
    ]
    return outer + inner


def _is_corner(ring, index: int) -> bool:
    pts = ring if ring[0] != ring[-1] else ring[:-1]
    n = len(pts)
    prev = pts[index - 1]
    point = pts[index]
    nxt = pts[(index + 1) % n]
    cross = ((point[0] - prev[0]) * (nxt[1] - point[1])
             - (point[1] - prev[1]) * (nxt[0] - point[0]))
    return cross != 0.0


def _min_edge_m(ring) -> float:
    pts = list(ring)
    if pts and tuple(pts[0]) == tuple(pts[-1]):
        pts = pts[:-1]
    return min(
        ((pts[i][0] - pts[(i + 1) % len(pts)][0]) ** 2
         + (pts[i][1] - pts[(i + 1) % len(pts)][1]) ** 2) ** 0.5
        for i in range(len(pts))
    )


def test_partition_emits_corner_only_rings_faces_and_footprint():
    """Every ring leaving ``partition_lines`` is corner-only — the right
    face's (5, 3) landing and the footprint's three skin landings are
    GONE.  Pre-promotion this reds: the right face carried 5 vertices and
    the footprint 7."""
    part = partition_lines(
        _t_junction_lines(), resolution_m=0.0, origin_label="s3b-synthetic"
    )
    assert len(part.faces) == 3
    for face in part.faces:
        assert all(_is_corner(face, i) for i in range(len(face))), face
    assert all(_is_corner(part.footprint_ring, i)
               for i in range(len(part.footprint_ring)))
    assert (5.0, 3.0) not in set(part.footprint_ring)
    # the footprint skin landings are dropped, the 4 real corners stay
    assert len(part.footprint_ring) == 4


def test_envelope_cells_inherit_the_producer_invariant():
    """``project_cut_lines`` passes the faces through VERBATIM — the cells
    in the emitted envelope are corner-only because the partition made
    them so, ⛔ not because a consumer re-derived the reduction."""
    envelope = project_cut_lines(
        _t_junction_lines(),
        resolution_m=0.0,
        resolution_source="synthetic S3b fixture (N-3 redeclared)",
        source_resolved_sha256="0" * 64,
        floor_id="S3b",
        floor_name="S3b",
        z_floor_m=0.0,
        ceiling_height_m=3.6,
        origin_label="s3b-synthetic",
    )
    cells = envelope.geometry.floors[0].cells
    assert len(cells) == 3
    for cell in cells:
        ring = [tuple(v) for v in cell.polygon]
        assert all(_is_corner(ring, i) for i in range(len(ring))), cell.id
    assert min(_min_edge_m(c.polygon) for c in cells) >= MIN_EDGE_FLOOR_M


def test_helper_is_not_an_edge_length_filter():
    """A REAL jog corner survives however short its edges: the helper drops
    exactly-collinear vertices only (cross == 0.0, zero tolerance), ⛔ it
    never shortens a wall by trimming a genuine bend."""
    ring = [(0.0, 0.0), (10.0, 0.0), (10.005, 0.012), (10.0, 0.2), (0.0, 0.2)]
    reduced = _corner_only_ring(ring)
    # the 13 mm jog at (10.005, 0.012) is a genuine corner — kept verbatim
    assert (10.005, 0.012) in reduced
    assert _min_edge_m(reduced) < 0.05  # and its short edges are NOT trimmed
    # the whole point of the drop is EXACT collinearity: an almost-flat
    # vertex (cross == 1e-18 ≠ 0.0) survives too — a tolerance band here
    # would quietly flatten real (sub-pixel) jogs
    flat_kept = _corner_only_ring(
        [(0.0, 0.0), (5.0, 1e-18), (10.0, 0.0), (5.0, 5.0)]
    )
    assert (5.0, 1e-18) in flat_kept


@pytest.mark.parametrize("floor", ["floor_1", "floor_2"])
def test_real_chain_products_reduce_losslessly_and_clear_the_floor(floor):
    """The git-tracked REAL chain probe envelopes (pre-promotion bytes: the
    cells still carry the collinear batch).  Running them through the
    PRODUCTION helper is exactly what the promoted producer now emits
    (``_cells_from_faces`` passes faces through verbatim, and the stored
    cells ARE the emitted faces), so this reads the fix on the real chain:

      * lossless — the reduced polyline is the SAME CURVE as the stored
        one (exact symmetric difference, zero tolerance: any moved or
        dropped real geometry reds here);
      * idempotent — a second pass is a no-op (one pass is confluent);
      * the downstream min-edge floor clears on every cell with margin,
        where the stored rings measure 1.62 / 0.55 cm.
    """
    from src.agent.correction.projection_bridge import (
        CorrectedGeometryProjectionEnvelopeV1,
    )

    env = CorrectedGeometryProjectionEnvelopeV1.model_validate_json(
        (PROBE / floor / "projection_envelope.json").read_text("utf-8")
    )
    cells = env.geometry.floors[0].cells
    assert len(cells) == 16  # the pinned real-chain cell count per floor
    for cell in cells:
        stored = [tuple(v) for v in cell.polygon]
        reduced = _corner_only_ring(stored)
        assert len(reduced) < len(stored)  # the collinear batch was there
        assert _corner_only_ring(reduced) == reduced
        stored_curve = LineString(stored + [stored[0]])
        reduced_curve = LineString(list(reduced) + [reduced[0]])
        assert stored_curve.difference(reduced_curve).length == 0.0
        assert reduced_curve.difference(stored_curve).length == 0.0
        assert _min_edge_m(reduced) >= MIN_EDGE_FLOOR_M
