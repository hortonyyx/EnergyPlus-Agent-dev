"""Read-only reproduction of the three unbuilt groups; no GT or model calls."""
import json
from pathlib import Path

from shapely.geometry import LineString, Polygon

from src.agent.correction.projection_bridge import (
    close_collinear_gaps, cut_lines_from_wall_compilation, extend_endpoints,
    snap_exterior_walls_to_declared_frame,
)
from src.agent.correction.wall_compiler import WallCompilationV1


def diagnose():
    run = Path(__file__).resolve().parent
    doc = json.loads((run / "0_reading/2f_view.json").read_text())
    provenance = json.loads((run / "1_correction/attempts/001/chain_provenance.json").read_text())
    raw = next(f["compilation_bytes"] for f in provenance["floors"] if f["floor_ref"] == "2f")
    compilation = WallCompilationV1.model_validate_json(raw)
    wall = next(w for w in compilation.walls
                if {"L029", "L030"} <= {r.observation_id for r in w.source_refs})
    lines, _ = cut_lines_from_wall_compilation(compilation.walls)
    decl = doc["declarations"]
    snapped, _ = snap_exterior_walls_to_declared_frame(
        lines,
        overall_x_m=sum(decl["chains"]["C_top_overall"]["values_mm"]) / 1000,
        overall_y_m=sum(decl["chains"]["C_left_overall"]["values_mm"]) / 1000,
        thickness_callouts_mm=decl["thickness_callouts_mm"],
    )
    positions = {}
    for label, source in (("before_snap", lines), ("after_snap", snapped)):
        closed, _ = close_collinear_gaps(source, resolution_m=0)
        result = extend_endpoints(closed, resolution_m=0)
        positions[label] = min(x.along_lo_m for x in result.lines if x.origin_id == wall.wall_id)
    assert abs(positions["before_snap"] - .1253) < 1e-9
    assert abs(positions["after_snap"] - .2452) < 1e-9

    geom = json.loads((run / "1_correction/attempts/001/output.json").read_text())
    floor = next(f for f in geom["floors"] if f["id"] == "2f")
    spans = []
    for span in ((3.8427, 4.6712), (9.9038, 10.9286), (10.1219, 11.1248)):
        segment = LineString([(span[0], 16.0646), (span[1], 16.0646)])
        hits = []
        for cell in floor["cells"]:
            polygon = Polygon(cell["polygon"])
            hit = segment.intersection(polygon.boundary)
            if hit.length > 0:
                hits.append({"space_id": cell["id"], "boundary_intersection": hit.wkt,
                             "length_m": hit.length})
        spans.append({"span_m": span, "boundary_hits": hits})
    assert not spans[0]["boundary_hits"]
    assert [{r["space_id"] for r in s["boundary_hits"]} for s in spans[1:]] == [
        {"2f-c000", "2f-c001", "2f-c006"}, {"2f-c000", "2f-c006", "2f-c007"},
    ]
    return {"mode": "frozen_observations_read_only_diagnostic", "wall_id": wall.wall_id,
            "endpoint_after_extension_m": positions, "opening_boundary_intersections": spans}


if __name__ == "__main__":
    print(json.dumps(diagnose(), ensure_ascii=False, indent=2))
