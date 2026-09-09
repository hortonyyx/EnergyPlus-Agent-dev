"""A reviewed continuous corridor must not acquire a physical cross-wall."""
import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from src.agent.correction.chain_provenance import AsDrawnChainProvenanceV1, build_chain_provenance
from src.agent.correction.chain_replay import derive_as_drawn_chain_producer, replay_as_drawn_chain
from src.agent.correction.parse import correction_target
from src.agent.correction.projection_bridge import CutLineV1, close_collinear_gaps
from src.agent.correction.wall_gap_review import (
    apply_wall_gap_decisions, load_wall_gap_decisions, resolve_wall_gap_decisions,
)
from src.agent.correction.window_sources import verify_window_resolver_inputs_artifact

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "AI_agent/logs/experiments/2026-09-09_m0_wall_gap_review_inputs/reviews.json"
ARCHIVE = ROOT / "case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/1_correction/attempts/001"


@pytest.fixture(scope="module")
def inputs():
    old = AsDrawnChainProvenanceV1.model_validate_json((ARCHIVE / "chain_provenance.json").read_bytes())
    marker = verify_window_resolver_inputs_artifact((ARCHIVE / "window_resolver_inputs.json").read_bytes())
    decisions = load_wall_gap_decisions(REVIEWS, image_root=ROOT)
    rows = [dict(input_id=f.input_id, product_filename=f.product_filename, floor_ref=f.floor_ref,
                 compilation_bytes=f.compilation_bytes, source_bytes_sha256=f.source_bytes_sha256) for f in old.floors]
    return old, marker, decisions, rows


def test_review_changes_continuity_only_keeps_other_openings_and_solid_runs():
    lines = tuple(CutLineV1("x", 2., a, b, .12, "wall", "wall") for a, b in [(0., 2.), (4., 6.), (7., 9.)])
    lines += (CutLineV1("x", 2., 2., 4., .12, "opening", "false_passage"),
              CutLineV1("x", 2., 6., 7., .12, "opening", "real_door"))
    review = [{"wall_id": "wall", "span_m": [2., 4.], "opening_classifications": [{"id": "false_passage"}]}]
    edited = apply_wall_gap_decisions(lines, review)
    assert [(l.pos_m, l.along_lo_m, l.along_hi_m, l.half_thickness_m) for l in edited if l.kind == "wall"] == [
        (l.pos_m, l.along_lo_m, l.along_hi_m, l.half_thickness_m) for l in lines if l.kind == "wall"]
    closed, gaps = close_collinear_gaps(edited, resolution_m=0.)
    assert [(g.from_m, g.to_m) for g in gaps] == [(6., 7.)]
    assert any(l.origin_id == "real_door" for l in closed)
    assert not any(l.along_lo_m < 3. < l.along_hi_m for l in closed)
    with pytest.raises(ValueError, match="would_remove_solid_wall"):
        apply_wall_gap_decisions(lines, [{**review[0], "span_m": [1., 4.]}])


@pytest.mark.parametrize("change,error", [
    ({"source_bytes_sha256": "0" * 64}, "input_drift"),
    ({"compilation_sha256": "0" * 64}, "input_drift"),
    ({"gap_index": 99}, "gap_missing"),
])
def test_stale_or_missing_gap_cannot_change_source(inputs, change, error):
    old, marker, decisions, _ = inputs
    d = decisions[0].model_copy(update=change)
    row = next(f for f in old.floors if f.input_id == d.input_id)
    with pytest.raises(ValueError, match=error):
        resolve_wall_gap_decisions([d], input_id=d.input_id,
                                  raw_reading=dict(marker.raw_reading_artifacts)[d.input_id], raw_compilation=row.compilation_bytes)


def test_duplicate_gap_and_changed_review_image_refuse(inputs, tmp_path):
    old, marker, decisions, _ = inputs
    d = decisions[0]
    row = next(f for f in old.floors if f.input_id == d.input_id)
    with pytest.raises(ValueError, match="duplicate"):
        resolve_wall_gap_decisions([d, d], input_id=d.input_id,
                                  raw_reading=dict(marker.raw_reading_artifacts)[d.input_id], raw_compilation=row.compilation_bytes)
    path = tmp_path / "review.json"
    path.write_text(json.dumps([{**d.model_dump(mode="json"), "image_sha256": "0" * 64}]))
    with pytest.raises(ValueError, match="image_drift"):
        load_wall_gap_decisions(path, image_root=ROOT)


def test_unknown_floor_is_not_silently_ignored(inputs):
    _, _, decisions, rows = inputs
    with pytest.raises(ValueError, match="unknown_plan"):
        build_chain_provenance(rows, wall_gap_decisions=(decisions[0].model_copy(update={"input_id": "unknown"}),))


def test_review_of_other_image_cannot_replay(inputs):
    _, marker, decisions, rows = inputs
    recipe = build_chain_provenance(rows, wall_gap_decisions=(decisions[0].model_copy(update={"image_sha256": "0" * 64}),))
    with pytest.raises(ValueError, match="manifest_image_drift"):
        derive_as_drawn_chain_producer(marker, recipe)


def test_normal_flow_consumes_review_sidecar_and_freezes_it(inputs, tmp_path, monkeypatch):
    import src.agent.pipeline as pipeline
    from scripts.tool_scripts.run_stage import _draw_correction_as_drawn, _make_policy
    from src.agent.correction.parse import ensure_corrected_geometry
    from src.agent.execution.evidence_preflight import EvidenceDebt
    from src.agent.execution.view_manifest import ViewManifest

    old, marker, decisions, _ = inputs
    manifest = ViewManifest.model_validate_json(marker.raw_view_manifest_bytes)
    (tmp_path / "_run").mkdir()
    (tmp_path / "0_reading").mkdir()
    (tmp_path / "_run/view_manifest.json").write_bytes(marker.raw_view_manifest_bytes)
    (tmp_path / "_run/wall_gap_decisions.json").write_bytes(REVIEWS.read_bytes())
    for entry in manifest.required_entries():
        (tmp_path / "0_reading" / f"{entry.expected_output_id}.json").write_bytes(dict(marker.raw_reading_artifacts)[entry.input_id])

    def archived_initial_chain(*args, **kwargs):
        # Replace only the upstream stage with its real archived product;
        # current review application, finalization and checks execute normally.
        for row in old.floors:
            entry = next(e for e in manifest.required_entries() if e.input_id == row.input_id)
            dest = tmp_path / "1_correction" / f"floor_{entry.floor_ref}"
            dest.mkdir()
            (dest / "evidence_chain_compilation.json").write_bytes(row.compilation_bytes)
        kwargs["evidence_debt_path"].write_text(EvidenceDebt().model_dump_json())
        return ensure_corrected_geometry(json.loads(marker.producer_draw_canonical_bytes))

    monkeypatch.setattr(pipeline, "run_multifloor_correction", archived_initial_chain)
    result, report = _draw_correction_as_drawn(
        tmp_path, None, False, _make_policy(capability_profile="orthogonal_polygon", run_profile="exploratory"))
    assert result.chain_provenance.wall_gap_decisions == decisions
    assert [len(f.cells) for f in result.geom.floors] == [14, 15]
    assert len(result.geom.openings) == 29 and len(result.geom.windows) == 31
    assert "correction.plan_opening_completeness" in {r.check_id for r in report.blocking()}
    account = json.loads((tmp_path / "1_correction/as_drawn_opening_account.json").read_text())
    assert [r["observation_ids"] for r in account["reclassified"]] == [["L042g0"]]


def test_real_corridor_rebuild_keeps_windows_and_records_reclassified_passage(inputs):
    from src.agent.correction.chain_provenance import PlanWallOpeningPolicyV1
    from src.agent.judge.gt import load_gt_document
    from src.agent.judge.partition_evidence import partition_evidence

    old, marker, decisions, rows = inputs
    historical_hash = old.replay_input_hash
    assert not old.wall_gap_decisions
    assert "wall_gap_decisions" not in old.model_dump(mode="json")
    assert derive_as_drawn_chain_producer(marker, old).producer_draw_canonical_bytes == marker.producer_draw_canonical_bytes
    before_recipe = build_chain_provenance(rows, endpoint_connection_policy="preserve_endpoint_connections_v1")
    before = json.loads(derive_as_drawn_chain_producer(marker, before_recipe).producer_draw_canonical_bytes)
    recipe = build_chain_provenance(rows, endpoint_connection_policy="preserve_endpoint_connections_v1",
                                    wall_opening_policy=PlanWallOpeningPolicyV1(), wall_gap_decisions=decisions)
    rebuilt = derive_as_drawn_chain_producer(marker, recipe)
    geom = json.loads(rebuilt.producer_draw_canonical_bytes)
    assert [len(f["cells"]) for f in geom["floors"]] == [14, 15]
    assert len(geom["windows"]) == 31 and len(geom["openings"]) == 29
    assert {o["kind"] for o in geom["openings"]} == {"door"}
    for old_floor, new_floor in zip(before["floors"], geom["floors"]):
        old_polys = [Polygon(c["polygon"]) for c in old_floor["cells"]]
        new_polys = [Polygon(c["polygon"]) for c in new_floor["cells"]]
        # Only whole original spaces join; no other source cell gets split.
        assert all(sum(n.buffer(1e-9).covers(p) for n in new_polys) == 1 for p in old_polys)
        assert sum(p.area for p in old_polys) == pytest.approx(sum(p.area for p in new_polys))
    def window_shape(g):
        return sorted((w["id"], w["floor_id"], w["facade"], w["span"], w["z"]) for w in g["windows"])
    assert window_shape(before) == window_shape(geom)
    changed = [r for r in geom["corrections"] if r.get("kind") == "wall_gap_opening_reclassification"]
    assert [r["observation_ids"] for r in changed] == [["L042g0"]]
    assert len([r for r in geom["unsupported"] if r.get("kind") == "as_drawn_opening_unbuilt"]) == 2
    # Independent GT only reaches the evaluator after generation.
    evaluation = partition_evidence(geom, document=load_gt_document("sm25-L_anchor"))["reference_partition"]
    assert not evaluation["topology_findings"]
    assert all(r["missing_length_m"] == r["extra_length_m"] == 0 for r in evaluation["internal_boundary_comparison"])
    assert evaluation["status"] == "not_evaluated"  # envelope/frame offsets still visible
    assert recipe.replay_input_hash != historical_hash
    replay_as_drawn_chain(rebuilt, recipe, target=correction_target("orthogonal_polygon"))
    without_review = build_chain_provenance(rows, endpoint_connection_policy=recipe.endpoint_connection_policy,
                                           wall_opening_policy=recipe.wall_opening_policy)
    with pytest.raises(ValueError, match="producer_drift"):
        replay_as_drawn_chain(rebuilt, without_review, target=correction_target("orthogonal_polygon"))
