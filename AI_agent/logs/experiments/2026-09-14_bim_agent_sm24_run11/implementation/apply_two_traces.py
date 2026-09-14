"""Deterministically apply two reviewed east-room traces to one source proposal.

This is a bounded developer-orchestrated observation replay.  It never calls a
model, API, GT, or a live application: it consumes two already saved trace JSON
records and writes a new candidate only when the normal source-BIM checks pass.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shapely.geometry import LineString, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.geometry.proposal_edits import apply_proposal_edits
from src.agent.execution.source_proposal import export_source_proposal


HISTORIC_APPLY = ROOT / "AI_agent/logs/experiments/2026-09-13_space_trace_setup/apply_trace.py"
DEFAULT_SEED = ROOT / "AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run07/candidate_01"
EPS = 1e-7


def _load_historic_normalizers():
    """Use the prior audited implementation rather than recreating its snapping rule."""
    spec = importlib.util.spec_from_file_location("historic_apply_trace", HISTORIC_APPLY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load historic trace application at {HISTORIC_APPLY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.normalize_trace_ring, module.normalize_trace_point


normalize_trace_ring, normalize_trace_point = _load_historic_normalizers()


def _shape(cell: dict) -> Polygon:
    return Polygon(cell["polygon"]) if cell.get("polygon") else box(
        cell["x"][0], cell["y"][0], cell["x"][1], cell["y"][1]
    )


def _ring(shape: Polygon) -> list[list[float]]:
    return [[float(x), float(y)] for x, y in list(orient(shape, sign=1.0).exterior.coords)[:-1]]


def _single_polygon(shape, *, label: str) -> Polygon:
    if (shape.geom_type != "Polygon" or shape.is_empty or not shape.is_valid
            or shape.interiors or shape.area <= EPS):
        raise ValueError(f"{label} must be one valid hole-free polygon")
    return shape


def _trace_path(observation: Path, trace_id: str) -> Path:
    path = observation / "detail_01" / "space_traces" / f"{trace_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing trace {trace_id!r}: expected {path}")
    return path


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _read_trace(observation: Path, trace_id: str) -> tuple[dict, Path, str]:
    path = _trace_path(observation, trace_id)
    trace = json.loads(path.read_text())
    if not isinstance(trace, dict):
        raise ValueError(f"trace {trace_id!r} is not an object")
    if trace.get("trace_id") != trace_id:
        raise ValueError(f"trace filename/id mismatch for {trace_id!r}")
    if trace.get("geometrically_executable") is not True or trace.get("geometry_errors") not in ([], None):
        raise ValueError(f"trace {trace_id!r} is not geometrically valid")
    ring = trace.get("world_polygon")
    if not isinstance(ring, list) or len(ring) < 4:
        raise ValueError(f"trace {trace_id!r} has no complete world_polygon")
    try:
        _single_polygon(Polygon(ring), label=f"trace {trace_id!r} polygon")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"trace {trace_id!r} has invalid world polygon: {exc}") from exc
    if not isinstance(trace.get("world_openings"), list):
        raise ValueError(f"trace {trace_id!r} has invalid world_openings")
    for opening in trace["world_openings"]:
        if not isinstance(opening, dict) or not isinstance(opening.get("id"), str):
            raise ValueError(f"trace {trace_id!r} has malformed opening")
        if not all(isinstance(opening.get(key), list) and len(opening[key]) == 2 for key in ("p1", "p2")):
            raise ValueError(f"trace {trace_id!r} opening {opening.get('id')!r} lacks endpoints")
    return trace, path, digest(path)


def _same_frame(a: dict, b: dict) -> None:
    for field in ("name", "x_anchors", "y_anchors"):
        if field not in a or field not in b or _canonical(a[field]) != _canonical(b[field]):
            raise ValueError(f"two traces must use the same {field}")
    for trace in (a, b):
        if not isinstance(trace.get("basis"), str) or not trace["basis"].strip():
            raise ValueError("each trace must explain its reference planes")


def _floor_and_cells(proposal: dict, ids: set[str]) -> tuple[dict, dict[str, dict]]:
    matches = []
    for floor in proposal["geometry"].get("floors", []):
        cells = {cell.get("id"): cell for cell in floor.get("cells", [])}
        if ids <= set(cells):
            matches.append((floor, cells))
    if len(matches) != 1:
        raise ValueError(f"selected spaces must occur together on exactly one floor: {sorted(ids)}")
    return matches[0]


def _shared_trace_opening(trace: dict, room: Polygon, corridor: Polygon, mappings: dict,
                          tolerance_m: float, *, trace_id: str):
    """Return the one observed corridor aperture after the ring coordinate maps."""
    normalized = []
    audit = []
    for opening in trace["world_openings"]:
        p1, a1 = normalize_trace_point(opening["p1"], mappings, tolerance_m,
                                       kind="trace_opening_endpoint", index=f"{opening['id']}:p1")
        p2, a2 = normalize_trace_point(opening["p2"], mappings, tolerance_m,
                                       kind="trace_opening_endpoint", index=f"{opening['id']}:p2")
        audit.extend((a1, a2))
        line = LineString([p1, p2])
        if room.boundary.buffer(EPS).covers(line) and corridor.boundary.buffer(EPS).covers(line):
            # This bounded replay is specifically for the west corridor door.
            # Do not silently accept another internal aperture if the corridor
            # happens to touch a different side after a bad trace.
            if abs(p1[0] - p2[0]) > EPS or abs(p1[0] - room.bounds[0]) > EPS:
                raise ValueError(f"trace {trace_id!r} corridor opening {opening['id']!r} is not on the room's west boundary")
            normalized.append({"trace_opening_id": opening["id"], "p1": p1, "p2": p2})
    if len(normalized) != 1:
        raise ValueError(f"trace {trace_id!r} requires exactly one opening shared by its room and {corridor}; found {len(normalized)}")
    return normalized[0], audit


def _source_corridor_door(proposal: dict, room_id: str, corridor_id: str) -> dict:
    matches = [opening for opening in proposal["geometry"].get("openings", [])
               if {opening.get("space_id"), opening.get("other_space_id")} == {room_id, corridor_id}]
    if len(matches) != 1:
        raise ValueError(f"source requires exactly one existing {room_id}/{corridor_id} opening; found {len(matches)}")
    return matches[0]


def _copy(path: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)


def _append_once(rows: list[str], note: str) -> list[str]:
    return [*rows, note] if note not in rows else list(rows)


def _self_check() -> None:
    """Small synthetic geometry check; no source candidate or application is run."""
    region = unary_union([box(0, 0, 2, 2), box(2, 0, 4, 2)])
    ring = [[.03, .02], [3.97, .02], [3.97, 1.98], [2.02, 1.98], [2.02, 1.2], [.03, 1.2]]
    normalized, mappings, _, _ = normalize_trace_ring(ring, region, .05)
    assert normalized[0][1] == normalized[1][1] == 0.0
    assert normalized[1][0] == normalized[2][0] == 4.0
    assert normalized[3][0] == normalized[4][0] == 2.02
    point, _ = normalize_trace_point([3.97, .7], mappings, .05, kind="synthetic", index=0)
    assert point == [4.0, .7]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--trace-a")
    parser.add_argument("--trace-b")
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--boundary-snap-m", type=float, default=.05)
    parser.add_argument("--space-a", default="TopRightRoom")
    parser.add_argument("--space-b", default="MeetingRoomBig")
    parser.add_argument("--neighbor", default="Corridor")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        _self_check()
        print("synthetic two-trace normalization check passed")
        return
    if any(value is None for value in (args.observation, args.trace_a, args.trace_b, args.out)):
        parser.error("--observation, --trace-a, --trace-b, and --out are required unless --self-check")
    if not 0 <= args.boundary_snap_m <= .2:
        raise ValueError("boundary snap must be explicit, between 0 and 0.2m")
    if len({args.space_a, args.space_b, args.neighbor}) != 3:
        raise ValueError("--space-a, --space-b, and --neighbor must be distinct")

    observation = args.observation.resolve()
    seed = args.seed.resolve()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(f"output must be a new directory: {out}")
    if not (seed / "proposal.json").is_file():
        raise FileNotFoundError(f"seed proposal not found: {seed / 'proposal.json'}")
    trace_a, trace_a_path, trace_a_sha = _read_trace(observation, args.trace_a)
    trace_b, trace_b_path, trace_b_sha = _read_trace(observation, args.trace_b)
    _same_frame(trace_a, trace_b)

    proposal = json.loads((seed / "proposal.json").read_text())
    floor, cells = _floor_and_cells(proposal, {args.space_a, args.space_b, args.neighbor})
    old_a, old_b, old_neighbor = (_shape(cells[args.space_a]), _shape(cells[args.space_b]), _shape(cells[args.neighbor]))
    old_two = _single_polygon(unary_union([old_a, old_b]), label="seed rooms A+B union")
    old_three = _single_polygon(unary_union([old_a, old_b, old_neighbor]), label="seed rooms A+B+corridor union")
    if old_a.intersection(old_b).area > EPS or old_two.area <= EPS:
        raise ValueError("seed A/B rooms must be non-overlapping valid rooms")

    new_a_ring, map_a, edges_a, points_a = normalize_trace_ring(trace_a["world_polygon"], old_two, args.boundary_snap_m)
    new_b_ring, map_b, edges_b, points_b = normalize_trace_ring(trace_b["world_polygon"], old_two, args.boundary_snap_m)
    new_a = _single_polygon(Polygon(new_a_ring), label="normalized trace A")
    new_b = _single_polygon(Polygon(new_b_ring), label="normalized trace B")
    if new_a.intersection(new_b).area > EPS:
        raise ValueError("normalized trace rooms overlap")
    if new_a.boundary.intersection(new_b.boundary).length <= EPS:
        raise ValueError("normalized trace rooms must share a boundary")
    # This experiment changes the two horizontal divisions and their doors.
    # A failed frame match must not silently become a new corridor strip along
    # the preserved west/north edges merely because subtraction can conserve area.
    stack = _single_polygon(unary_union([new_a, new_b]), label="new east-room stack")
    for index, label in ((0, "west"), (2, "east"), (3, "north")):
        if abs(stack.bounds[index] - old_two.bounds[index]) > EPS:
            raise ValueError(f"preserved {label} source frame was not matched; review reference planes or explicit boundary tolerance")
    if not stack.equals(box(*stack.bounds)) or not old_two.equals(box(*old_two.bounds)):
        raise ValueError("this bounded application requires a rectangular two-room stack; no inferred corridor strips")
    new_neighbor = _single_polygon(old_three.difference(unary_union([new_a, new_b])), label="derived corridor remainder")
    final_union = unary_union([new_a, new_b, new_neighbor])
    if final_union.symmetric_difference(old_three).area > EPS:
        raise ValueError("three-space replacement does not preserve coverage")

    trace_door_a, opening_points_a = _shared_trace_opening(trace_a, new_a, new_neighbor, map_a,
                                                             args.boundary_snap_m, trace_id=args.trace_a)
    trace_door_b, opening_points_b = _shared_trace_opening(trace_b, new_b, new_neighbor, map_b,
                                                             args.boundary_snap_m, trace_id=args.trace_b)
    old_door_a = _source_corridor_door(proposal, args.space_a, args.neighbor)
    old_door_b = _source_corridor_door(proposal, args.space_b, args.neighbor)
    if old_door_a["id"] == old_door_b["id"]:
        raise ValueError("two trace openings cannot map to the same source door")

    refs_a = [f"{trace_a['name']}:{args.trace_a} complete room contour and corridor opening; trace sha256 {trace_a_sha}"]
    refs_b = [f"{trace_b['name']}:{args.trace_b} complete room contour and corridor opening; trace sha256 {trace_b_sha}"]
    limitation = (f"Developer-scoped deterministic replay of model-selected traces {args.trace_a} and {args.trace_b}; "
                  f"only the A/B outer union was normalized within {args.boundary_snap_m}m. "
                  "Calibration and drawing fidelity remain unverified; windows and all other openings were retained unchanged and were not validated by this local replay.")
    unresolved = "East-side room boundaries and corridor doors remain model observations pending independent original-plan evaluation; this replay is not a fidelity verdict."
    operations = [
        {"op": "reshape_spaces", "spaces": [
            {"id": args.space_a, "polygon": _ring(new_a)},
            {"id": args.space_b, "polygon": _ring(new_b)},
            {"id": args.neighbor, "polygon": _ring(new_neighbor)},
        ], "reason": "Apply two complete model-traced rooms and the exact old three-space-union remainder for the corridor; preserve coverage without inventing partitions.",
         "source_refs": [*refs_a, *refs_b]},
        {"op": "update_opening", "id": old_door_a["id"], "changes": {"p1": trace_door_a["p1"], "p2": trace_door_a["p2"]},
         "reason": "Move the uniquely corresponding existing corridor door to the traced jamb segment, retaining its ID, height, state, and connectivity.", "source_refs": refs_a},
        {"op": "update_opening", "id": old_door_b["id"], "changes": {"p1": trace_door_b["p1"], "p2": trace_door_b["p2"]},
         "reason": "Move the uniquely corresponding existing corridor door to the traced jamb segment, retaining its ID, height, state, and connectivity.", "source_refs": refs_b},
        {"op": "set_notes", "assumptions": _append_once(proposal["assumptions"], limitation),
         "unresolved": _append_once(proposal["unresolved"], unresolved)},
    ]
    result = apply_proposal_edits(proposal, operations)

    out.mkdir(parents=True)
    source_image = observation / "images" / trace_a["name"]
    if not source_image.is_file():
        raise FileNotFoundError(f"observed original image is unavailable for delivery: {source_image}")
    source_image_sha = digest(source_image)
    for trace, label in ((trace_a, "A"), (trace_b, "B")):
        if trace.get("image_sha256") not in (None, source_image_sha):
            raise ValueError(f"trace {label} image hash does not match the delivered original image")
    _copy(source_image, out / "images" / trace_a["name"])
    for label, path, trace in (("trace_a", trace_a_path, trace_a), ("trace_b", trace_b_path, trace_b)):
        _copy(path, out / f"{label}.json")
        png = path.with_suffix(".png")
        if not png.is_file():
            raise FileNotFoundError(f"trace image missing: {png}")
        _copy(png, out / f"{label}.png")

    snapshots = [Path(__file__), HISTORIC_APPLY, ROOT / "src/agent/geometry/proposal_edits.py",
                 ROOT / "scripts/tool_scripts/run_bim_agent.py"]
    implementation = out / "implementation"
    implementation.mkdir()
    for path in snapshots:
        _copy(path, implementation / path.name)
    observed_manifest = json.loads((observation / "inputs.json").read_text())
    observed_image = observed_manifest.get("images", {}).get(trace_a["name"], {})
    manifest = {
        "images": {trace_a["name"]: {"size": observed_image.get("size"), "sha256": source_image_sha}},
        "input_mode": "developer_orchestrated_two_trace_local_replay",
        "only_input": "one named seed proposal plus two already saved model trace records and their original image; no new model/API/application call and no GT",
        "scope": "two named rooms plus their existing corridor neighbor; windows and unrelated openings are retained unchanged",
        "developer_selected_ids": {"space_a": args.space_a, "space_b": args.space_b, "neighbor": args.neighbor},
        "auxiliary_mode": "developer_scoped continuation using independently saved model observations; not autonomous cold start",
        "observation_run": {"absolute_path": str(observation), "trace_a": {"id": args.trace_a, "sha256": trace_a_sha},
                            "trace_b": {"id": args.trace_b, "sha256": trace_b_sha}},
        "seed": {"source": str(seed), "proposal_sha256": digest(seed / "proposal.json")},
        "application_implementation_sha256": {str(path.relative_to(ROOT)): digest(path) for path in snapshots},
    }
    dump(out / "inputs.json", manifest)
    export_source_proposal(proposal, out / "seed", provenance=manifest["seed"])
    all_point_audit = [*points_a, *opening_points_a, *points_b, *opening_points_b]
    dump(out / "normalization_audit.json", {
        "mode": "whole_axis_edge_to_outer_union_boundary_per_trace",
        "boundary_snap_tolerance_m": args.boundary_snap_m,
        "target": "exterior boundary of seed space A + space B union only; never their old internal wall",
        "trace_a": {"id": args.trace_a, "coordinate_mappings": map_a, "edge_mappings": edges_a,
                    "point_mappings": [*points_a, *opening_points_a]},
        "trace_b": {"id": args.trace_b, "coordinate_mappings": map_b, "edge_mappings": edges_b,
                    "point_mappings": [*points_b, *opening_points_b]},
        "max_final_displacement_m": max((row["displacement_m"] for row in all_point_audit), default=0),
        "outer_boundary_only": True, "not_snapped_to_old_internal_partition": True,
        "opening_endpoints_use_their_trace_coordinate_mappings": True,
        "source_ring_orientation": "All three rings reordered counterclockwise for the source contract; coordinates and geometry are unchanged by this orientation step.",
    })
    dump(out / "operations.json", operations)
    toolkit = Toolkit(out)
    report = toolkit.build(result, action="apply_two_selected_traces", parent="seed", operations=operations)
    candidate = out / report["candidate"]
    if not (candidate / "source_model.json").is_file() or not report.get("source_geometry_ready"):
        dump(out / "application_failure.json", report)
        dump(out / "summary.json", {
            "input_mode": manifest["input_mode"], "agent_response_completed": False,
            "deterministic_application_completed": False, "has_viewable_candidate": False,
            "model_invocations_in_application": 0, "error": report.get("error", "source geometry checks failed"),
        })
        raise RuntimeError("source geometry checks failed; candidate retained without successful delivery")
    toolkit.project_overlay(report["candidate"], trace_a["name"], floor["name"], trace_a["x_anchors"], trace_a["y_anchors"],
                            trace_a["basis"] + " | " + trace_b["basis"], trigger_action="post_application_two_trace_projection")
    delivery = toolkit.delivery(report["candidate"], selection_origin="developer_selected_deterministic_trace_replay",
                                generation_status={"state": "completed", "agent_response_completed": False})
    dump(out / "summary.json", {
        "input_mode": manifest["input_mode"], "agent_response_completed": False,
        "deterministic_application_completed": True, "has_viewable_candidate": True,
        "model_invocations_in_application": 0, "gt_used": False, "drawing_fidelity": "not_evaluated",
        "delivery": {"candidate": report["candidate"], "selection_origin": delivery["selection_origin"]},
        "counts": report["counts"], "operations": [operation["op"] for operation in operations],
    })
    print(json.dumps({"candidate": report["candidate"], "counts": report["counts"],
                      "operations": [operation["op"] for operation in operations]}, indent=2))


if __name__ == "__main__":
    main()
