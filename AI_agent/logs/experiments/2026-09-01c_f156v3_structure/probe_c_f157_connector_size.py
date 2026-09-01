"""F-156 v3 · probe C (⛔ information for F-157, NOT part of F-156's product).

Question: how big is the answer-side ``outer_skin``<->``wall_axis`` basis
switch really, once the facts side is read at PRODUCTION granularity?

The v2 probes merged a cavity's ring segments by ``(axis, const)`` only, so one
support line carrying TWO bases collapsed into one -- which is why they could
build a projected ring at all and reported a 1.800000 m² residual.  Production
keeps the two records apart, so two adjacent projected supports are parallel and
no ring can be built by intersection alone.

This probe inserts, at each such transition, the connector the answer itself
draws (a perpendicular segment at the coordinate where the two records meet) and
reports the residual that remains.
"""
import sys
from pathlib import Path

from shapely.geometry import Polygon

REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))
from src.agent.judge import as_measured as am  # noqa: E402
from src.agent.judge.answer_compiler import read_facts_for_compilation  # noqa: E402
from src.agent.judge.tarch_converter_schema import ConversionReportV1  # noqa: E402

U = am.UNITS_PER_METRE
OFFSET = {"exterior": lambda t: t, "interzone": lambda t: t // 2}
GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor"

_measured, _ledger, signed = read_facts_for_compilation("sm25-L_anchor")
report = ConversionReportV1.model_validate_json(
    (GT / "review/conversion_report.json").read_bytes())

for view in signed.views:
    by_cavity = {}
    for edge in view.boundary_edges:
        by_cavity.setdefault(edge.cavity_id, []).append(edge)
    zones = [zone for zone in report.zones if zone.floor_id == view.floor_id]
    for cavity_id, edges in sorted(by_cavity.items()):
        edges = sorted(edges, key=lambda item: item.sequence)
        if len(edges) <= 4:
            continue
        supports = []
        for edge in edges:
            thickness = edge.evidence.thickness_units
            outward = (edge.evidence.outward_normal[0] if edge.axis == "y"
                       else edge.evidence.outward_normal[1])
            const = (edge.evidence.raw_face_const
                     + outward * OFFSET[edge.boundary_condition](thickness))
            item = (edge.axis, const, edge)
            if not supports or supports[-1][:2] != item[:2]:
                supports.append(item)
        if len(supports) > 1 and supports[0][:2] == supports[-1][:2]:
            supports.pop()
        # insert the answer's own connector wherever two adjacent projected
        # supports are parallel: a perpendicular line at the coordinate where
        # the two records meet along the shared cavity line.
        with_connectors = []
        parallel_transitions = 0
        for index, item in enumerate(supports):
            previous = supports[index - 1]
            if previous[0] == item[0]:
                parallel_transitions += 1
                meeting = item[2].p1[1] if item[0] == "y" else item[2].p1[0]
                with_connectors.append(("x" if item[0] == "y" else "y", meeting,
                                        item[2]))
            with_connectors.append(item)
        vertices = []
        bad = False
        for index, item in enumerate(with_connectors):
            previous = with_connectors[index - 1]
            if previous[0] == item[0]:
                bad = True
                break
            vertices.append((previous[1], item[1]) if previous[0] == "y"
                            else (item[1], previous[1]))
        if bad:
            print(f"{view.view_id} {cavity_id} still parallel after connectors")
            continue
        polygon = Polygon(vertices)
        matches = [zone for zone in zones
                   if Polygon([(round(p[0] * U), round(p[1] * U))
                               for p in zone.polygon_m.exterior.vertices]).intersects(
                       polygon.representative_point())]
        zone = matches[0]
        zone_polygon = Polygon([(round(p[0] * U), round(p[1] * U))
                                for p in zone.polygon_m.exterior.vertices])
        difference = polygon.symmetric_difference(zone_polygon)
        print(f"{view.view_id} {cavity_id} zone={zone.zone_id} "
              f"parallel_transitions={parallel_transitions} "
              f"projected_supports={len(with_connectors)} zone_edges={len(zone.edges)} "
              f"valid={polygon.is_valid} "
              f"SYMDIFF_m2={difference.area / U / U:.6f}")
        for part in getattr(difference, "geoms", [difference]):
            if part.area > 0:
                print(f"    part area_m2={part.area / U / U:.4f} "
                      f"bounds_m={tuple(round(v / U, 4) for v in part.bounds)}")
