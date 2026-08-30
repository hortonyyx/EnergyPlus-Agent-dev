"""Small signed facts fixtures shared by AnswerCompiler acceptance tests."""
from __future__ import annotations

from pathlib import Path

from src.agent.judge.as_measured import (
    AsMeasuredConverterReadoutsV1,
    AsMeasuredFaceLineV1,
    AsMeasuredFootprintV1,
    AsMeasuredRingV1,
    AsMeasuredV1,
    AsMeasuredViewV1,
    AsMeasuredWallV1,
    content_sha256,
    derive_boundary_edges,
)
from src.agent.judge.gt_revisions import (
    AsSignedV1,
    RevisionFindingV1,
    RevisionTargetV1,
    RevisionV1,
    RevisionsLedgerV1,
    TranslateActionV1,
    derive_as_signed,
)
from src.agent.judge.tarch_converter_schema import (
    TarchConversionRequestV1,
    compute_request_sha256,
)

REPO = Path(__file__).resolve().parents[1]
BASE_REQUEST = (
    REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/request_as_measured.json")


def _request() -> TarchConversionRequestV1:
    base = TarchConversionRequestV1.model_validate_json(BASE_REQUEST.read_text())
    raw = base.model_dump(mode="json")
    raw["case"] = "answer-compiler-synthetic"
    raw["source_dxf_label"] = "synthetic.dxf"
    raw["source_dxf_sha256"] = "1" * 64
    raw["normalized_source_id"] = "answer-compiler-synthetic"
    raw["floors"] = raw["floors"][:1]
    raw["plan_views"] = raw["plan_views"][:1]
    raw["plan_views"][0]["id"] = "plan-S"
    raw["plan_views"][0]["floor_id"] = "F1"
    raw["plan_views"][0]["zone_intent"] = {
        "mode": "intent_file",
        "expected_count": 2,
        "entries": [
            {"zone_id": "F1-left", "name": "left", "role": "unspecified"},
            {"zone_id": "F1-right", "name": "right", "role": "unspecified"},
        ],
    }
    raw["elevation_views"] = []
    raw["raster_overlays"] = []
    raw["critical_dimensions"] = []
    raw["request_sha256"] = "0" * 64
    provisional = TarchConversionRequestV1.model_validate(raw)
    raw["request_sha256"] = compute_request_sha256(provisional)
    return TarchConversionRequestV1.model_validate(raw)


def _face(handle: str, axis: str, const: int,
          along_min: int, along_max: int) -> AsMeasuredFaceLineV1:
    return AsMeasuredFaceLineV1(
        id=handle, layer="WALL", axis=axis, const=const,
        along_min=along_min, along_max=along_max)


def _wall(wall_id: str, axis: str, lo: int, hi: int,
          along_min: int, along_max: int,
          lo_handle: str, hi_handle: str) -> AsMeasuredWallV1:
    return AsMeasuredWallV1(
        id=wall_id, axis=axis, face_lo=lo, face_hi=hi,
        thickness=hi - lo, along_min=along_min, along_max=along_max,
        face_line_ids_lo=[lo_handle], face_line_ids_hi=[hi_handle])


def synthetic_signed_facts() -> tuple[
        AsMeasuredV1, RevisionsLedgerV1, AsSignedV1, TarchConversionRequestV1]:
    """Two rooms with a signed two-face correction on the partition.

    Both authoritative actions move a face by 0.2 mm while staying in the
    same D3 millimetre group, so ``derive_as_signed`` accepts the established
    wall identity and the compiled partition axis moves from 50000 to 50002.
    """
    request = _request()
    faces = [
        _face("A1", "x", 0, 0, 100000),
        _face("A2", "x", 2400, 0, 100000),
        _face("A3", "x", 57600, 0, 100000),
        _face("A4", "x", 60000, 0, 100000),
        _face("A5", "y", 0, 0, 60000),
        _face("A6", "y", 2400, 0, 60000),
        _face("A7", "y", 97600, 0, 60000),
        _face("A8", "y", 100000, 0, 60000),
        _face("A9", "y", 49400, 2400, 57600),
        _face("AA", "y", 50600, 2400, 57600),
    ]
    walls = [
        _wall("wall-south", "x", 0, 2400, 0, 100000, "A1", "A2"),
        _wall("wall-north", "x", 57600, 60000, 0, 100000, "A3", "A4"),
        _wall("wall-west", "y", 0, 2400, 0, 60000, "A5", "A6"),
        _wall("wall-east", "y", 97600, 100000, 0, 60000, "A7", "A8"),
        _wall("wall-partition", "y", 49400, 50600, 2400, 57600, "A9", "AA"),
    ]
    readouts = AsMeasuredConverterReadoutsV1(
        dangles=0, cuts=0, invalid=0,
        degenerate_line_count=0, degenerate_line_handles=[],
        s1_nonorthogonal_discarded_handles=[],
        wall_lines_total=len(faces), degenerate_in_wall_lines=0,
        all_wall_handles=sorted(face.id for face in faces),
        non_orthogonal_lines=[], axis_snapped_lines=[],
        unresolved_opening_carriers=[], jamb_cap_bands=[],
        jamb_cap_bands_missing_a_face_line=[],
        face_lines_excluded_as_jamb_caps=[],
        face_lines_not_paired_into_a_wall=[],
        face_groups_with_a_split_const=[], diagnostics=[], gates=[])
    view = AsMeasuredViewV1(
        view_id="plan-S", floor_id="F1", face_lines=faces, walls=walls,
        openings=[],
        footprint=AsMeasuredFootprintV1(
            geom_type="Polygon", is_empty=False,
            rings=[AsMeasuredRingV1(
                polygon_index=0, kind="exterior",
                points=[[0, 0], [100000, 0], [100000, 60000],
                        [0, 60000], [0, 0]])]),
        converter_readouts=readouts)
    view = AsMeasuredViewV1.model_validate({
        **view.model_dump(mode="json"),
        "boundary_edges": [edge.model_dump(mode="json") for edge in
                           derive_boundary_edges(
                               view,
                               min_room_area_m2=float(request.min_room_area_m2))],
    })
    measured = AsMeasuredV1(
        case=request.case, source_dxf_label=request.source_dxf_label,
        source_dxf_sha256=request.source_dxf_sha256,
        request_sha256=request.request_sha256,
        converter_implementation_fingerprint="2" * 64,
        views=[view])
    revisions = []
    for revision_id, handle in (("rev-a9", "A9"), ("rev-aa", "AA")):
        action = TranslateActionV1(field="const", delta_0p1mm=2)
        revisions.append(RevisionV1(
            id=revision_id,
            target=RevisionTargetV1(view_id="plan-S", handle=handle),
            finding=RevisionFindingV1(
                check="synthetic_known_correction",
                magnitude_0p1mm=2,
                detail="synthetic signed correction moves one partition face"),
            verdict="drawing_error", candidate_action=action, action=action,
            reason="known target fixture", signed_by="fixture",
            signed_at="2026-08-30T00:00:00Z"))
    ledger = RevisionsLedgerV1(
        case=measured.case,
        as_measured_content_sha256=content_sha256(measured),
        revisions=revisions)
    signed = derive_as_signed(measured, ledger)
    return measured, ledger, signed, request


def replace_signed_view(signed: AsSignedV1, view_raw: dict) -> AsSignedV1:
    raw = signed.model_dump(mode="json")
    raw["views"] = [view_raw]
    return AsSignedV1.model_validate(raw)


def request_with_affine(request: TarchConversionRequestV1, **updates: float
                        ) -> TarchConversionRequestV1:
    raw = request.model_dump(mode="json")
    raw["plan_views"][0]["world_from_source_m"].update(updates)
    raw["request_sha256"] = "0" * 64
    provisional = TarchConversionRequestV1.model_validate(raw)
    raw["request_sha256"] = compute_request_sha256(provisional)
    return TarchConversionRequestV1.model_validate(raw)


def bind_signed_to_request(signed: AsSignedV1,
                           request: TarchConversionRequestV1) -> AsSignedV1:
    raw = signed.model_dump(mode="json")
    raw["request_sha256"] = request.request_sha256
    raw["source_dxf_sha256"] = request.source_dxf_sha256
    return AsSignedV1.model_validate(raw)
