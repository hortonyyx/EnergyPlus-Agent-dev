"""F-156 v3 · probe B: what the PRODUCTION derivation now emits for sm25.

Consumes only ``src.agent.judge.as_measured`` public derivations; no
re-implementation of the algorithm under test.
"""
import json
import sys
from pathlib import Path

from shapely.geometry import Polygon

REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))
from src.agent.judge import as_measured as am  # noqa: E402

SRC = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
REQ = SRC / "request_as_measured.json"
MIN = float(json.loads(REQ.read_text())["min_room_area_m2"])
U = am.UNITS_PER_METRE

doc = am.build_as_measured(SRC / "sm25-L_t3_as_received.dxf", REQ)
for view in doc.views:
    by_cavity = {}
    for edge in view.boundary_edges:
        by_cavity.setdefault(edge.cavity_id, []).append(edge)
    print(f"== {view.view_id} edges={len(view.boundary_edges)} "
          f"cavities_with_ring={len(by_cavity)} losses={len(view.boundary_ring_losses)}")
    for cid, edges in sorted(by_cavity.items()):
        edges = sorted(edges, key=lambda e: e.sequence)
        poly = Polygon([e.p1 for e in edges])
        conds = sorted({e.boundary_condition for e in edges})
        print(f"   {cid} edges={len(edges):2d} ring_valid={poly.is_valid} "
              f"area_m2={poly.area/U/U:9.4f} conds={conds}")
    for loss in view.boundary_ring_losses:
        print(f"   LOSS {loss.cavity_id} reason={loss.reason} "
              f"area_m2={loss.area_units2/U/U:.4f} owner_count={loss.owner_count} "
              f"span=({loss.span.axis},{loss.span.const},{loss.span.lo},{loss.span.hi}) "
              f"nearest={loss.span.nearest_same_axis_wall_face_const} "
              f"delta={loss.span.span_to_nearest_same_axis_wall_face_delta}")
