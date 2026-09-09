"""Offline observation-to-source openings, including the saved two-floor plan."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.agent.correction.as_drawn_openings import populate_as_drawn_openings
from src.agent.correction.evidence_adapters import adapt_as_drawn_plan
from src.agent.correction.schema import CorrectedGeometry, CorrectedGeometryV3, WallOpening, Window
from src.agent.correction.wall_compiler import FixedDecisionV1, compile_wall_ir
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import OpeningEvidence, RequiredViewEntry, ViewManifest
from src.agent.geometry import build_geometry
from src.agent.geometry.source_model import materialize_source_model
from src.agent.reading.as_drawn.schema import SCHEMA


def _document(*observations):
    """Observations are (id, face, span, explicit type), without case semantics."""
    faces = []
    candidates = []
    for fid, pos in (("left", 4.94), ("right", 5.06)):
        gaps = []
        for oid, face, span, _ in observations:
            if face != fid:
                continue
            lo, hi = span
            candidates.append({"id": oid, "face_line": face, "gap_index": len(gaps), "span_m": list(span),
                               "len_m": hi - lo, "len_px": round((hi - lo) * 100), "ink_by_family": {}})
            gaps.append({"lo_px": round(lo * 100), "hi_px": round(hi * 100), "len_px": round((hi - lo) * 100),
                         "span_m": list(span), "len_m": hi - lo, "ink_by_family": {}})
        faces.append({"id": fid, "axis": "col", "constant_world_axis": "x", "pos_px": pos * 100,
                      "pos_m": pos, "support_cols_px": [round(pos * 100), round(pos * 100) + 1],
                      "edges_m": [pos, pos + .01], "support_width_m": .01,
                      "runs_px": [[0, 100], [900, 1000]], "runs_m": [[0., 1.], [9., 10.]], "gaps": gaps,
                      "ink_coverage_per_run": [1., 1.], "covered_px": 200, "support_px": 1000})
    pair = {"face_a": "left", "face_b": "right", "spacing_px": 12., "spacing_m": .12,
            "matched_declared_mm": [120], "overlap_px": 200}
    return {"schema": SCHEMA, "observations": {"face_lines": faces}, "declarations": {},
            "hypotheses": {"pairs": [{**pair, "source": "selected"}], "pair_candidates": [pair],
                           "opening_candidates": candidates,
                           "opening_types": {oid: typ for oid, _, _, typ in observations}}}


def _inputs(doc):
    entry = RequiredViewEntry(input_id="plan", source_image="case_data/plan.png", image_sha256="a" * 64,
                              view_type="plan", floor_ref=1, direction_source="standard_assumption",
                              direction_semantics="building_axis", semantics_source="case_metadata",
                              dimensioned=True, expected_output_id="plan",
                              opening_evidence=OpeningEvidence(potentially_observable_claims=["existence", "host", "along", "width"]))
    payload = {"view_manifest_schema_version": "1", "claims_vocab_version": "1", "generator_version": "1",
               "completeness_ruleset_version": "1", "case_id": "fixture", "case_metadata_sha256": "a" * 64,
               "entries": [entry.model_dump(mode="json")]}
    manifest = ViewManifest(**payload, content_sha256=hash_obj(payload))
    raw = json.dumps(doc).encode()
    artifact = adapt_as_drawn_plan(raw, input_id="plan", floor_ref="f1")
    initial = compile_wall_ir(artifact, profile="strict")
    decisions = tuple(FixedDecisionV1(item_id=i.item_id, candidate_id=next(
        c.candidate_id for c in i.candidates if c.symbolic_operation == "KEEP_OBSERVED_WIDTH"
    )) for i in initial.open_items)
    compilation = compile_wall_ir(artifact, profile="strict", decisions=decisions)
    assert not compilation.open_items and all(w.resolved_thickness_m for w in compilation.walls)
    return {"raw_view_manifest_bytes": manifest.model_dump_json().encode(),
            "raw_reading_artifacts": {"plan": raw},
            "raw_wall_compilations": {"plan": compilation.model_dump_json().encode()}}


def _geom(*, shift=0., cells=None):
    return CorrectedGeometry.model_validate({"footprint_x": [0., 10.], "footprint_y": [0., 10.],
        "floors": [{"name": "f1", "z_floor": 0., "ceiling_height": 3., "cells": cells or [
            {"id": "A", "x": [0., 5. + shift], "y": [0., 10.]},
            {"id": "B", "x": [5. + shift, 10.], "y": [0., 10.]},
        ]}]})


def _pair():
    return _document(("a", "left", (2., 3.), "door"), ("b", "right", (2.02, 3.02), "door"))


def test_paired_faces_one_source_connection_height_assumed_input_immutable_and_idempotent():
    geom, inputs = _geom(shift=.005), _inputs(_pair())
    prior = WallOpening(id="manual", kind="door", space_id="A", other_space_id=None,
                        p1=(0., 6.), p2=(0., 7.), z=(0., 2.), source_refs=["manual:provided"])
    geom.openings.append(prior)
    before, original_inputs = geom.model_dump_json(), copy.deepcopy(inputs)
    result, account = populate_as_drawn_openings(geom, **inputs)
    assert geom.model_dump_json() == before and inputs == original_inputs
    assert account.observations_considered == 2 and account.built_count == 1 and not account.unbuilt
    assert len(account.folded) == 1 and account.folded[0]["observation_id"] == "b"
    assert len(result.openings) == 2 and result.openings[0] == prior
    opening = result.openings[1]
    assert opening.p1 == (5.005, 2.) and opening.p2 == (5.005, 3.)
    assert opening.z == (0., 2.1) and opening.state == "unknown"
    assert len(opening.source_refs) == 2 and "Height assumed" in opening.assumptions[0]
    assert account.host_moves[0]["delta_m"] == pytest.approx(.005)
    model = materialize_source_model(result, build_geometry(result))
    assert model["validation"]["status"] == "pass" and len(model["connections"]) == 2
    repeated, repeated_account = populate_as_drawn_openings(result, **inputs)
    assert repeated == result and repeated_account.to_payload() == account.to_payload()


def test_same_face_distinct_holes_are_not_folded():
    doc = _document(("a", "left", (2., 3.), "door"), ("b", "left", (4., 5.), "door"))
    result, account = populate_as_drawn_openings(_geom(), **_inputs(doc))
    assert len(result.openings) == account.built_count == 2 and not account.folded
    assert [o.p1[1] for o in result.openings] == [2., 4.]


@pytest.mark.parametrize("other_type", ["window", "passage", "not_opening", "ambiguous"])
def test_opposite_face_type_conflict_remains_unbuilt(other_type):
    doc = _document(("a", "left", (2., 3.), "door"), ("b", "right", (2., 3.), other_type))
    result, account = populate_as_drawn_openings(_geom(), **_inputs(doc))
    assert not result.openings and not account.folded
    assert account.unbuilt[0]["reason"] == "paired_observation_type_conflict"
    assert result.unsupported[0]["kind"] == "as_drawn_opening_unbuilt"
    assert result.unsupported[0]["related_observation_ids"] == ["a", "b"]


def test_many_candidates_on_one_face_cannot_be_merged_through_the_opposite_face():
    doc = _document(("a", "left", (2., 3.), "door"), ("b", "left", (2.02, 3.02), "door"),
                    ("c", "right", (2.01, 3.01), "door"))
    result, account = populate_as_drawn_openings(_geom(), **_inputs(doc))
    assert not result.openings and not account.folded
    assert account.unbuilt[0]["observation_ids"] == ["a", "b", "c"]
    assert account.unbuilt[0]["reason"] == "paired_observation_ambiguous"


@pytest.mark.parametrize("cells,reason", [
    ([{"id": "A", "x": [0., 5.], "y": [0., 10.]},
      {"id": "B", "x": [5., 10.], "y": [0., 2.5]},
      {"id": "C", "x": [5., 10.], "y": [2.5, 10.]}], "opening_crosses_room_boundaries"),
    ([{"id": "A", "x": [0., 5.], "y": [0., 10.]}], "missing_interior_neighbor"),
    ([{"id": "A", "x": [0., 5.], "y": [0., 10.]},
      {"id": "B", "x": [5.02, 10.], "y": [0., 10.]}], "final_wall_host_not_unique"),
])
def test_crossing_rooms_missing_neighbor_and_multiple_planes_do_not_guess(cells, reason):
    result, account = populate_as_drawn_openings(_geom(cells=cells), **_inputs(_pair()))
    assert not result.openings and account.unbuilt[0]["reason"] == reason
    assert result.unsupported[0]["observation_ids"] == ["a", "b"]


def test_fold_cannot_hide_opposite_face_crossing_into_another_room():
    # Anchor ends at 3.00, but the opposite face reaches past the 3.01 partition.
    geom = _geom(cells=[{"id": "A", "x": [0., 5.], "y": [0., 10.]},
                        {"id": "B", "x": [5., 10.], "y": [0., 3.01]},
                        {"id": "C", "x": [5., 10.], "y": [3.01, 10.]}])
    result, account = populate_as_drawn_openings(geom, **_inputs(_pair()))
    assert not result.openings and not account.folded
    assert account.unbuilt[0]["reason"] == "opening_crosses_room_boundaries"
    assert account.unbuilt[0]["observation_ids"] == ["a", "b"]


def test_real_exterior_passage_and_height_limit():
    geom = _geom(cells=[{"id": "A", "x": [0., 5.], "y": [0., 10.]}])
    geom.footprint_x = [0., 5.]
    inputs = _inputs(_document(("a", "left", (2., 3.), "passage")))
    result, account = populate_as_drawn_openings(geom, **inputs)
    assert account.built_count == 1
    assert result.openings[0].kind == "open" and result.openings[0].state == "open"
    assert result.openings[0].other_space_id is None and result.openings[0].assumptions
    assert len(build_geometry(result).openings) == 1
    too_tall, account = populate_as_drawn_openings(geom, **inputs, assumed_height_m=3.1)
    assert not too_tall.openings and account.unbuilt[0]["reason"] == "assumed_height_exceeds_room_height"


def test_window_and_existing_opening_overlap_preserve_existing_objects():
    geom = _geom()
    geom.windows = [Window(id="window", floor="f1", room="A", facade="East", span=[2., 3.], z=[1., 2.])]
    result, account = populate_as_drawn_openings(geom, **_inputs(_pair()))
    assert result.windows == geom.windows and not result.openings
    assert account.unbuilt[0]["reason"] == "window_overlap"
    geom.windows = []
    geom.openings = [WallOpening(id="already", kind="open", space_id="A", other_space_id="B",
                                p1=(5., 2.), p2=(5., 3.), z=(0., 2.1), source_refs=["user:opening"])]
    result, account = populate_as_drawn_openings(geom, **_inputs(_pair()))
    assert result.openings == geom.openings and account.unbuilt[0]["reason"] == "opening_overlap"


def test_overlapping_same_face_candidates_reject_both_independent_of_input_order():
    observations = [("a", "left", (2., 3.), "door"), ("b", "left", (2.02, 3.02), "door")]
    for order in (observations, observations[::-1]):
        result, account = populate_as_drawn_openings(_geom(), **_inputs(_document(*order)))
        assert not result.openings and not account.folded
        assert [r["reason"] for r in account.unbuilt] == ["opening_overlap", "opening_overlap"]


def test_missing_compilation_is_persisted_and_stale_compilation_bytes_are_rejected():
    inputs = _inputs(_pair())
    result, account = populate_as_drawn_openings(_geom(), **{**inputs, "raw_wall_compilations": {}})
    assert not result.openings and account.unbuilt[0]["reason"] == "wall_compilation_missing"
    assert result.unsupported[0]["observation_ids"] == ["a", "b"]
    inputs["raw_reading_artifacts"]["plan"] += b" "
    with pytest.raises(ValueError, match="does not match reading bytes"):
        populate_as_drawn_openings(_geom(), **inputs)


def test_legacy_plan_with_only_prose_is_unchanged():
    inputs = _inputs(_pair())
    inputs["raw_reading_artifacts"]["plan"] = b'{"strokes": [], "notes": "door at x=5, y=2..3"}'
    geom = _geom()
    result, account = populate_as_drawn_openings(geom, **inputs)
    assert result == geom and account.observations_considered == account.built_count == 0
    assert not account.unbuilt and account.views[0]["status"] == "no_structured_opening_channel"


def test_manifest_slot_can_differ_from_compiled_product_name():
    inputs = _inputs(_pair())
    payload = json.loads(inputs["raw_view_manifest_bytes"])
    payload["entries"][0]["input_id"] = "ground_plan_slot"
    payload.pop("content_sha256")
    payload["content_sha256"] = hash_obj(payload)
    inputs["raw_view_manifest_bytes"] = json.dumps(payload).encode()
    for key in ("raw_reading_artifacts", "raw_wall_compilations"):
        inputs[key] = {"ground_plan_slot": inputs[key]["plan"]}
    result, account = populate_as_drawn_openings(_geom(), **inputs)
    assert len(result.openings) == account.built_count == 1 and not account.unbuilt
    assert account.built[0]["input_id"] == "ground_plan_slot"


def test_saved_sm25_structured_observations_are_fully_accounted_without_gt_or_manual_groups():
    root = Path("case_tests/e2e_tests/sm25-L_anchor/run_win_e2e")
    geom = CorrectedGeometryV3.model_validate_json((root / "1_correction/correction_geometry_snapped.json").read_bytes())
    inputs = {"raw_view_manifest_bytes": (root / "_run/view_manifest.json").read_bytes(),
              "raw_reading_artifacts": {f"{i}f_view": (root / f"0_reading/{i}f_view.json").read_bytes() for i in (1, 2)},
              "raw_wall_compilations": {f"{i}f_view": (root / f"1_correction/floor_{i}/evidence_chain_compilation.json").read_bytes() for i in (1, 2)}}
    original = geom.model_dump_json()
    result, account = populate_as_drawn_openings(geom, **inputs)
    assert geom.model_dump_json() == original and result.windows == geom.windows and result.floors == geom.floors
    assert account.observations_considered == 61 and account.built_count == 29 and len(account.folded) == 28
    assert sum(o.kind == "door" for o in result.openings) == 28
    assert sum(o.kind == "open" for o in result.openings) == 1
    assert len(account.unbuilt) == 3 and sum(len(r["observation_ids"]) for r in account.unbuilt) == 4
    assert {r["reason"] for r in account.unbuilt} == {"final_wall_host_not_unique", "opening_crosses_room_boundaries"}
    assert len(account.host_moves) == 15
    positives = {(input_id, oid) for input_id, raw in inputs["raw_reading_artifacts"].items()
                 for oid, typ in json.loads(raw)["hypotheses"]["opening_types"].items() if typ in {"door", "passage", "open"}}
    accounted = [(r["input_id"], oid) for r in account.built + account.unbuilt for oid in r["observation_ids"]]
    assert set(accounted) == positives and len(accounted) == len(positives)
    repeated, repeated_account = populate_as_drawn_openings(result, **inputs)
    assert repeated == result and repeated_account == account
