"""Dimension correction must not discard already evidenced wall connections."""
from dataclasses import replace
import json
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon

from src.agent.correction.projection_bridge import (
    CutLineV1, ProjectionBridgeError, preserve_endpoint_connections,
    close_collinear_gaps, extend_endpoints, partition_lines,
)


def wall(axis, pos, lo, hi, origin, half=.12):
    return CutLineV1(axis, pos, lo, hi, half, "wall", origin)


@pytest.mark.parametrize("endpoint,host_pos,tip,new_pos", [
    ("lo", .1253, .2452, .12), ("hi", 4.1253, 4.0054, 4.13),
    ("lo", .1253, .1253, .12),
])
def test_tip_follows_preexisting_host_even_when_original_band_is_exceeded(endpoint, host_pos, tip, new_pos):
    host = wall("y", host_pos, 0, 4, "host")
    source = wall("x", 2, tip if endpoint == "lo" else 1,
                  tip if endpoint == "hi" else 3, "partition", .06)
    moved_host = replace(host, pos_m=new_pos)
    fixed, records = preserve_endpoint_connections((host, source), (source, moved_host))
    followed = next(line for line in fixed if line.origin_id == "partition")
    assert getattr(followed, f"along_{endpoint}_m") == new_pos
    assert source.pos_m == followed.pos_m
    assert records[0]["original_gap_m"] <= host.half_thickness_m
    assert records[0]["host_displacement_m"] == new_pos - host_pos


@pytest.mark.parametrize("source", [
    wall("x", 2, .2454, 3, "outside_original_band", .06),
    wall("x", 6, .2452, 3, "beyond_host_extent", .06),
    wall("x", 2, 0, 3, "already_crosses_host", .06),
    replace(wall("x", 2, .2452, 3, "opening", .06), kind="opening"),
])
def test_no_new_connection_or_shortening_without_endpoint_evidence(source):
    host = wall("y", .1253, 0, 4, "host")
    after = (replace(host, pos_m=.12), source)
    fixed, records = preserve_endpoint_connections((host, source), after)
    assert fixed == after
    assert not records


def test_distinct_possible_hosts_refuse_instead_of_choosing_one():
    lines = (wall("y", .12, 0, 4, "one"), wall("y", .13, 0, 4, "two"),
             wall("x", 2, .23, 3, "partition", .06))
    with pytest.raises(ProjectionBridgeError, match="ENDPOINT_FOLLOW_AMBIGUOUS_HOST"):
        preserve_endpoint_connections(lines, (replace(lines[0], pos_m=.11), *lines[1:]))


def test_simultaneous_move_that_breaks_the_junction_refuses():
    host = wall("y", .1253, 0, 2.2, "host")
    source = wall("x", 2, .2452, 3, "partition", .06)
    with pytest.raises(ProjectionBridgeError, match="ENDPOINT_FOLLOW_CONNECTION_BROKEN"):
        preserve_endpoint_connections(
            (host, source), (replace(host, pos_m=.12), replace(source, pos_m=3)))


def test_real_sm25_original_partition_survives_frame_snap():
    from src.agent.correction.chain_provenance import AsDrawnChainProvenanceV1
    from src.agent.correction.wall_compiler import WallCompilationV1
    from src.agent.correction.projection_bridge import (
        cut_lines_from_wall_compilation, snap_exterior_walls_to_declared_frame,
    )
    from src.agent.correction.multifloor import read_declared_exterior_frame

    archive = Path("case_tests/e2e_tests/sm25-L_anchor/run_win_e2e")
    provenance = AsDrawnChainProvenanceV1.model_validate_json(
        (archive / "1_correction/attempts/001/chain_provenance.json").read_bytes())
    row = next(r for r in provenance.floors if r.floor_ref == "2f")
    comp = WallCompilationV1.model_validate_json(row.compilation_bytes)
    source_wall = next(w for w in comp.walls
                       if {"L029", "L030"} <= {r.observation_id for r in w.source_refs})
    lines, _ = cut_lines_from_wall_compilation(comp.walls)
    frame = read_declared_exterior_frame(json.loads((archive / "0_reading" / row.product_filename).read_bytes()), input_id=row.input_id)
    snapped, _ = snap_exterior_walls_to_declared_frame(
        lines, overall_x_m=frame.overall_x_m, overall_y_m=frame.overall_y_m,
        thickness_callouts_mm=frame.thickness_callouts_mm)
    fixed, records = preserve_endpoint_connections(lines, snapped)
    record = next(r for r in records if r["origin_id"] == source_wall.wall_id and r["endpoint"] == "lo")
    assert record["from_m"] == pytest.approx(.2452)
    assert record["host_from_m"] == pytest.approx(.1253)
    assert record["to_m"] == .12

    def faces(ls):
        closed, _ = close_collinear_gaps(ls, resolution_m=0)
        return partition_lines(extend_endpoints(closed, resolution_m=0).lines, resolution_m=0).faces

    # The door span had no boundary after the old snap; now two distinct
    # source spaces share its entire span, just as before dimension correction.
    wall_y = next(line.pos_m for line in lines if line.origin_id == source_wall.wall_id)
    door = LineString([(3.8427, wall_y), (4.6712, wall_y)])
    def hosts(ls):
        return [face for face in faces(ls) if Polygon(face).boundary.intersection(door).length >= door.length - 1e-9]
    assert len(hosts(snapped)) == 0
    assert len(hosts(lines)) == len(hosts(fixed)) == 2


def test_historical_producer_replays_exactly_and_new_recipe_is_distinct():
    from src.agent.correction.chain_provenance import AsDrawnChainProvenanceV1, build_chain_provenance
    from src.agent.correction.chain_replay import derive_as_drawn_chain_producer, replay_as_drawn_chain
    from src.agent.correction.parse import correction_target
    from src.agent.correction.window_sources import verify_window_resolver_inputs_artifact

    attempt = Path("case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/1_correction/attempts/001")
    old = AsDrawnChainProvenanceV1.model_validate_json((attempt / "chain_provenance.json").read_bytes())
    marker = verify_window_resolver_inputs_artifact((attempt / "window_resolver_inputs.json").read_bytes())
    assert derive_as_drawn_chain_producer(marker, old).producer_draw_canonical_bytes == marker.producer_draw_canonical_bytes
    rows = [dict(input_id=r.input_id, product_filename=r.product_filename, floor_ref=r.floor_ref,
                 compilation_bytes=r.compilation_bytes, source_bytes_sha256=r.source_bytes_sha256) for r in old.floors]
    new = build_chain_provenance(rows, endpoint_connection_policy="preserve_endpoint_connections_v1")
    assert new.replay_input_hash != old.replay_input_hash
    rebuilt = derive_as_drawn_chain_producer(marker, new)
    geom = json.loads(rebuilt.producer_draw_canonical_bytes)
    assert [len(f["cells"]) for f in geom["floors"]] == [16, 16]
    # Removing the recipe from a new candidate must fail independent replay.
    with pytest.raises(ValueError, match="chain_replay_producer_drift"):
        replay_as_drawn_chain(rebuilt, old, target=correction_target("orthogonal_polygon"))
