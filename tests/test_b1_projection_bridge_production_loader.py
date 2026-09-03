"""B1 production loader locks — the wiring's own teeth (dispatch §四之二).

The fixture-world loader (``cut_lines_from_as_measured_view``) is locked by
the acceptance / fixture files; THIS file locks the production world
(``cut_lines_from_wall_compilation`` + ``opening_spans_from_artifact``),
which had ZERO coverage before the wiring (measured: grep for the loader
names over tests/ = no matches — the previous round wrote the loader and
never exercised it, and the 90° axis transposition lived there undetected).

What is locked, each against the defect it guards:
* the axis VOCABULARY mapping (compiler names the constant axis; CutLineV1
  names the run axis — copying one into the other transposes the floor);
* opening host resolution BY REFERENCE (the wall whose source_refs claim
  the face), with 0 and 2 owners both loud;
* the deref of the bundle's reference-only opening claims, identity-checked
  the way the wall compiler checks face nodes;
* unresolved walls are loud (the W2 discipline: a wall that cannot be
  projected is never silently skipped);
* the real sm25 2f product runs end to end through the production loader
  with the UNROTATED orientation pinned against the signed gt footprint.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import LineString

from src.agent.correction.decision_executor import (
    build_decision_packet,
    compile_wall_ir,
)
from src.agent.correction.evidence_adapters import adapt_as_drawn_plan
from src.agent.correction.projection_bridge import (
    CutLineV1,
    ProjectionBridgeError,
    _line_string,
    cut_lines_from_wall_compilation,
    extend_endpoints,
    opening_spans_from_artifact,
    project_cut_lines,
)
from src.agent.correction.wall_compiler import (
    FixedDecisionV1,
    ResolvedWallV1,
    WallCenterlineV1,
)
from src.agent.correction.evidence_contract import (
    ObservationRefV1,
    source_locator,
)

REPO = Path(__file__).resolve().parents[1]
SRC = (
    REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype"
    / "out/sm25_2f_v2.json"
)
GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json"


# ── synthetic walls (the loader's consumed surface, real model types) ─────── #
def _face_ref(observation_id: str) -> ObservationRefV1:
    return ObservationRefV1(
        input_id="synthetic_input",
        source_contract_id="contract_as_drawn_plan",
        source_output_sha256="0" * 64,
        json_pointer=f"/observations/face_lines/{observation_id}",
        observation_id=observation_id,
        source_locator=source_locator(
            input_id="synthetic_input",
            observation_id=observation_id,
            output_sha256="0" * 64,
        ),
        evidence_resolution="pixel_backed",
        pixel_witness_pointers=(f"/observations/face_lines/{observation_id}",),
    )


def _wall(
    wall_id: str,
    *,
    constant_world_axis: str,
    constant_pos_m: float,
    along,
    thickness_m: float,
    face_ids,
) -> ResolvedWallV1:
    return ResolvedWallV1(
        wall_id=wall_id,
        source_claim_ids=(f"claim_{wall_id}",),
        source_refs=tuple(_face_ref(f) for f in face_ids),
        claim_kind="paired_faces",
        resolved_centerline=WallCenterlineV1(
            constant_world_axis=constant_world_axis,
            constant_pos_m=constant_pos_m,
            p1_m=(constant_pos_m, along[0][0]),
            p2_m=(constant_pos_m, along[-1][1]),
        ),
        resolved_along_intervals=tuple(along),
        observed_face_spacing_m=thickness_m,
        resolved_thickness_m=thickness_m,
        observed_basis="two_observed_faces",
        output_basis="wall_axis",
    )


# ── the axis vocabulary mapping ────────────────────────────────────────────── #
@pytest.mark.parametrize(
    "constant_axis,expected_run_axis",
    [("x", "y"), ("y", "x")],
)
def test_axis_mapping_constant_to_run(constant_axis, expected_run_axis):
    """The compiler names the CONSTANT axis; CutLineV1 names the RUN axis.

    Copying ``constant_world_axis`` straight into ``CutLineV1.axis``
    transposes the whole floor by 90° (the defect this loader carried
    before the wiring measured it: rendered bbox flipped against the
    signed gt footprint x∈[0,25] y∈[0,20]).
    """
    wall = _wall(
        "w_synthetic",
        constant_world_axis=constant_axis,
        constant_pos_m=3.0,
        along=((0.0, 5.0),),
        thickness_m=0.24,
        face_ids=("L1", "L2"),
    )
    (line,) = cut_lines_from_wall_compilation([wall])[0]
    assert line.axis == expected_run_axis
    # the rendered geometry holds the CONSTANT coordinate on the axis the
    # compiler named — not on the other one
    segment = _line_string(line)
    xs = [p[0] for p in segment.coords]
    ys = [p[1] for p in segment.coords]
    if constant_axis == "x":
        assert xs == [3.0, 3.0]
        assert ys == [0.0, 5.0]
    else:
        assert ys == [3.0, 3.0]
        assert xs == [0.0, 5.0]


def test_axis_mapping_mutant_transposes_and_the_lock_goes_red():
    """The mutation this lock exists for: assigning the constant axis
    directly.  Feeding the transposed line to the same renderer flips
    which coordinate is constant — the assertion above must fail on it."""
    wall = _wall(
        "w_synthetic",
        constant_world_axis="x",
        constant_pos_m=3.0,
        along=((0.0, 5.0),),
        thickness_m=0.24,
        face_ids=("L1", "L2"),
    )
    mutant = CutLineV1(
        axis="x",  # ← the transposition: constant axis copied verbatim
        pos_m=3.0,
        along_lo_m=0.0,
        along_hi_m=5.0,
        half_thickness_m=0.12,
        kind="wall",
        origin_id="w_synthetic",
    )
    assert mutant.axis != cut_lines_from_wall_compilation([wall])[0][0].axis
    xs = [p[0] for p in _line_string(mutant).coords]
    assert xs != [3.0, 3.0]


# ── reference-based opening host resolution ────────────────────────────────── #
def _opening_span(face_id: str, lo=1.0, hi=2.0):
    from src.agent.correction.projection_bridge import OpeningSpanV1

    return OpeningSpanV1(
        opening_id="op_test",
        face_observation_id=face_id,
        span_lo_m=lo,
        span_hi_m=hi,
    )


def test_opening_borrows_the_unique_owner_walls_own_numbers():
    host = _wall(
        "w_host",
        constant_world_axis="x",
        constant_pos_m=3.0,
        along=((0.0, 5.0),),
        thickness_m=0.24,
        face_ids=("L1", "L2"),
    )
    other = _wall(
        "w_other",
        constant_world_axis="y",
        constant_pos_m=9.0,
        along=((0.0, 5.0),),
        thickness_m=0.12,
        face_ids=("L3", "L4"),
    )
    lines = cut_lines_from_wall_compilation(
        [host, other], [_opening_span("L1")]
    )[0]
    opening = next(l for l in lines if l.kind == "opening")
    # every number is the HOST wall's own resolution — axis mapped, midline
    # and half thickness borrowed, span extent the claim's own
    assert opening.axis == "y"
    assert opening.pos_m == 3.0
    assert opening.half_thickness_m == pytest.approx(0.12)
    assert (opening.along_lo_m, opening.along_hi_m) == (1.0, 2.0)


def test_opening_with_no_owner_wall_is_loud():
    wall = _wall(
        "w_host",
        constant_world_axis="x",
        constant_pos_m=3.0,
        along=((0.0, 5.0),),
        thickness_m=0.24,
        face_ids=("L1", "L2"),
    )
    with pytest.raises(ProjectionBridgeError) as exc:
        cut_lines_from_wall_compilation([wall], [_opening_span("LX")])
    assert exc.value.code == "OPENING_HOST_UNRESOLVED"
    assert exc.value.detail["n_owner_walls"] == 0


def test_opening_with_two_owner_walls_is_loud():
    """Two walls whose source_refs claim the same face (e.g. a paired claim
    and a single-face claim on one observation) — the reference itself is
    ambiguous, and a guess is forbidden."""
    first = _wall(
        "w_first",
        constant_world_axis="x",
        constant_pos_m=3.0,
        along=((0.0, 5.0),),
        thickness_m=0.24,
        face_ids=("L1", "L2"),
    )
    second = _wall(
        "w_second",
        constant_world_axis="x",
        constant_pos_m=3.1,
        along=((4.0, 8.0),),
        thickness_m=0.24,
        face_ids=("L1",),
    )
    second = second.model_copy(
        update={"claim_kind": "single_face"}
    )
    with pytest.raises(ProjectionBridgeError) as exc:
        cut_lines_from_wall_compilation([first, second], [_opening_span("L1")])
    assert exc.value.code == "OPENING_HOST_UNRESOLVED"
    assert exc.value.detail["n_owner_walls"] == 2


def _mandated_mixed_thickness_walls():
    """Build production IR walls from the existing S-mix data declaration."""
    from tests.test_b1_projection_bridge_fixtures import UPM, smix_view

    source_rows = smix_view()["walls"]
    expected_thicknesses = {
        row["thickness"] / UPM for row in source_rows
    }
    by_thickness = {}
    for index, row in enumerate(source_rows):
        thickness_m = row["thickness"] / UPM
        if thickness_m in by_thickness:
            continue
        by_thickness[thickness_m] = _wall(
            f"w_mix_{index}",
            constant_world_axis="y" if row["axis"] == "x" else "x",
            constant_pos_m=(row["face_lo"] + row["face_hi"]) / 2 / UPM,
            along=((row["along_min"] / UPM, row["along_max"] / UPM),),
            thickness_m=thickness_m,
            face_ids=(f"mix_face_{index}",),
        )
    walls = tuple(by_thickness.values())
    assert {wall.resolved_thickness_m for wall in walls} == expected_thicknesses
    return walls


def test_mixed_thickness_opening_with_no_owner_is_loud():
    """The zero-owner refusal also has teeth on the mandated thickness mix."""
    walls = _mandated_mixed_thickness_walls()
    absent_face = f"absent:{walls[0].source_refs[0].observation_id}"
    with pytest.raises(ProjectionBridgeError) as exc:
        cut_lines_from_wall_compilation(walls, [_opening_span(absent_face)])
    assert exc.value.code == "OPENING_HOST_UNRESOLVED"
    assert exc.value.detail["n_owner_walls"] == 0
    assert exc.value.detail["owner_wall_ids"] == []


def test_mixed_thickness_opening_with_two_owners_is_loud():
    """The multi-owner refusal also has teeth on the mandated thickness mix."""
    walls = _mandated_mixed_thickness_walls()
    shared_ref = walls[0].source_refs[0]
    duplicate_owner = walls[-1].model_copy(
        update={"source_refs": (shared_ref,)}
    )
    with pytest.raises(ProjectionBridgeError) as exc:
        cut_lines_from_wall_compilation(
            walls + (duplicate_owner,),
            [_opening_span(shared_ref.observation_id)],
        )
    assert exc.value.code == "OPENING_HOST_UNRESOLVED"
    assert exc.value.detail["n_owner_walls"] == 2
    assert set(exc.value.detail["owner_wall_ids"]) == {
        walls[0].wall_id,
        duplicate_owner.wall_id,
    }


def test_unresolved_wall_is_loud():
    """W2 discipline: a wall that cannot be projected is never silently
    skipped — a missing wall leaves no geometric signature at all."""
    wall = _wall(
        "w_open",
        constant_world_axis="x",
        constant_pos_m=3.0,
        along=((0.0, 5.0),),
        thickness_m=0.24,
        face_ids=("L1", "L2"),
    )
    broken = wall.model_copy(
        update={
            "resolved_centerline": None,
            "resolved_thickness_m": None,
        }
    )
    with pytest.raises(ProjectionBridgeError) as exc:
        cut_lines_from_wall_compilation([broken])
    assert exc.value.code == "WALL_NOT_PROJECTABLE"


# ── the deref of reference-only opening claims ─────────────────────────────── #
def _real_artifact():
    raw = SRC.read_bytes()
    return adapt_as_drawn_plan(
        raw, input_id=SRC.stem, floor_ref="2f", view_type="plan"
    )


def test_spans_from_the_real_sm25_2f():
    spans = opening_spans_from_artifact(_real_artifact())
    assert len(spans) == 87  # the frozen product's own opening_candidates
    ids = [s.opening_id for s in spans]
    assert len(set(ids)) == len(ids)
    assert all(s.span_lo_m < s.span_hi_m for s in spans)


def test_span_pointer_identity_mismatch_is_loud():
    artifact = _real_artifact()
    claims = list(artifact.bundle.opening_claims)
    tampered = claims[0].model_copy(
        update={
            "source_ref": claims[0].source_ref.model_copy(
                update={"observation_id": "NOT_THE_NODE_ID"}
            )
        }
    )
    artifact = artifact.model_copy(
        update={
            "bundle": artifact.bundle.model_copy(
                update={"opening_claims": [tampered] + claims[1:]}
            )
        }
    )
    with pytest.raises(ProjectionBridgeError) as exc:
        opening_spans_from_artifact(artifact)
    assert exc.value.code == "OPENING_NODE_MISMATCH"


# ── the real product, end to end, orientation pinned ──────────────────────── #
def _all_keep_compilation(artifact):
    """Round-0 compilation with every open item resolved to its first
    candidate (KEEP) — the deterministic stand-in for the model beat."""
    packet0 = build_decision_packet(
        compile_wall_ir(artifact, profile="exploratory"),
        bundle=artifact,
        round_index=0,
    )
    decisions = tuple(
        FixedDecisionV1(
            item_id=item.item_id, candidate_id=item.candidates[0].candidate_id
        )
        for item in packet0.open_items
    )
    return compile_wall_ir(artifact, profile="exploratory", decisions=decisions)


def test_production_chain_on_real_sm25_2f_unrotated():
    artifact = _real_artifact()
    compilation = _all_keep_compilation(artifact)
    spans = opening_spans_from_artifact(artifact)
    lines, _ = cut_lines_from_wall_compilation(compilation.walls, spans)
    gt = json.loads(GT.read_text(encoding="utf-8"))
    floor = next(f for f in gt["floors"] if f["id"] == "F2")
    envelope = project_cut_lines(
        lines,
        resolution_m=0.0,
        resolution_source=(
            "production wiring: as-drawn *_m fields are floating-point "
            "metres with no declared quantisation (N-3 redeclared here; "
            "⛔ the fixture world's 1-unit number is not carried over)"
        ),
        source_resolved_sha256=compilation.content_sha256,
        floor_id="2f",
        floor_name="sm25 2f",
        z_floor_m=float(floor["z_floor_m"]),
        ceiling_height_m=float(floor["ceiling_height_m"]),
        view_id="sm25_2f_v2",
        origin_label="sm25_2f_v2",
    )
    # the frozen real product's measured readout (regression pin on a
    # frozen input): 16 faces, honestly degraded (16 dangling ends — the
    # as-drawn wall set does not close the way the gt facts set does)
    assert envelope.face_count == 16
    assert envelope.completion == "degraded"
    assert len(envelope.dangling_end_debts) == 16
    assert envelope.footprint_provenance == "derived_from_walls"
    # ORIENTATION: the signed gt footprint is x∈[0,25] y∈[0,20]; the
    # production frame must keep x the LONG side.  A 90° transposition
    # (the axis-vocabulary defect this loader carried) flips this.
    fp = envelope.geometry.floors[0].footprint.vertices
    xs = [p[0] for p in fp]
    ys = [p[1] for p in fp]
    x_extent = max(xs) - min(xs)
    y_extent = max(ys) - min(ys)
    assert x_extent - y_extent > 4.0, (x_extent, y_extent)
    # the envelope binds the compilation it was derived from
    assert envelope.source_resolved_sha256 == compilation.content_sha256


def test_real_sm25_host_inventory_is_unique_but_has_no_refusal_stock():
    """T3 inventory: every real opening has one owner; zero/two have no stock.

    The real frame therefore exercises the success direction of host
    resolution, while the refusal directions necessarily remain synthetic.
    """
    artifact = _real_artifact()
    compilation = _all_keep_compilation(artifact)
    spans = opening_spans_from_artifact(artifact)
    owners = {}
    for wall in compilation.walls:
        for ref in wall.source_refs:
            owners.setdefault(ref.observation_id, []).append(wall.wall_id)
    owner_counts = tuple(
        len(owners.get(span.face_observation_id, ())) for span in spans
    )
    assert owner_counts
    assert set(owner_counts) == {1}


def test_real_sm25_inward_candidates_exist_but_extensions_never_shorten():
    """T3 inventory + lock: real inward candidates must not shorten lines."""
    artifact = _real_artifact()
    compilation = _all_keep_compilation(artifact)
    spans = opening_spans_from_artifact(artifact)
    lines, _ = cut_lines_from_wall_compilation(compilation.walls, spans)

    inward_candidates = []
    for line in lines:
        for other in lines:
            if other.axis == line.axis:
                continue
            crosses = (
                other.along_lo_m - line.half_thickness_m <= line.pos_m
                <= other.along_hi_m + line.half_thickness_m
            )
            if not crosses:
                continue
            lo_in_band = (
                line.along_lo_m < other.pos_m
                and abs(line.along_lo_m - other.pos_m)
                <= other.half_thickness_m
            )
            hi_in_band = (
                other.pos_m < line.along_hi_m
                and abs(line.along_hi_m - other.pos_m)
                <= other.half_thickness_m
            )
            if lo_in_band or hi_in_band:
                inward_candidates.append((line.origin_id, other.origin_id))
    assert inward_candidates, "real product lost inward-candidate inventory"

    extended = extend_endpoints(lines, resolution_m=0.0).lines
    assert len(extended) == len(lines)
    for before, after in zip(lines, extended):
        assert after.along_lo_m <= before.along_lo_m
        assert after.along_hi_m >= before.along_hi_m
