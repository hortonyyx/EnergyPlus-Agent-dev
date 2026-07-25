"""sm24 v3 named-elevation must-red probes.

Each mutation enters the production converter/extractor path and asserts the
declared target gate, rather than merely checking that another upstream failure
happened to make the fixture red.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import ezdxf
import pytest

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1, compute_request_sha256, resolve_converter_tooling


ROOT = Path("logs/experiments/2026-07-24_sm24_gt_review")
SOURCE = ROOT / "source.dxf"
TOOLING = resolve_converter_tooling(Path("src/configs/judge_gt.yaml"), Path("src/configs/correction.yaml"))


def _request() -> TarchConversionRequestV1:
    return TarchConversionRequestV1.model_validate_json((ROOT / "request_v3.json").read_text())


def _rehash(request: TarchConversionRequestV1) -> TarchConversionRequestV1:
    draft = request.model_copy(update={"request_sha256": "0" * 64})
    return draft.model_copy(update={"request_sha256": compute_request_sha256(draft)})


def _run(tmp_path, request, source=SOURCE):
    return tn.run_p2_conversion(source, request, request.plan_views[0], TOOLING, tmp_path)


def _gate(result, gate):
    return next(item for item in result.gates if item.id == gate)


def _calibrated_request() -> TarchConversionRequestV1:
    return TarchConversionRequestV1.model_validate_json(
        (ROOT / "request_v3_calibrated.json").read_text())


@pytest.fixture(scope="module")
def green_sm24(tmp_path_factory):
    """One shared green sm24 conversion + its extracted GT (the real anchor bundle)."""
    from src.agent.judge.gt_extraction import ExtractionInputs, extract_gt_v3
    from src.agent.judge.gt_schema import REPO_ROOT, compute_gt_implementation_hashes
    request = _calibrated_request()
    result = tn.run_p2_conversion(SOURCE, request, request.plan_views[0], TOOLING,
                                  tmp_path_factory.mktemp("green_sm24"))
    document = extract_gt_v3(ExtractionInputs(result.augmented_dxf_path, result.manifest, TOOLING,
                                              compute_gt_implementation_hashes(REPO_ROOT)))
    return request, result, document


# --------------------------------------------------------------------------- #
# spec §6.5 [S] — converter pairing ledger <-> GT opening_elevation refs
# --------------------------------------------------------------------------- #
def test_pairing_postcheck_is_green_on_the_real_sm24_bundle(green_sm24):
    """Positive lock: the gate must not be red for the wrong reason later."""
    request, result, document = green_sm24
    assert _gate(result, "G9").passed
    assert len(result.elevation_records) == 14
    assert tn._verify_pairing_consistency(document, result.elevation_records, request) == []


def test_gt_side_z_drift_makes_g9_pairing_red(tmp_path, monkeypatch):
    """Production path: make the GT z path disagree with the converter ledger z.

    This is the exact §6.5 risk — audit-table z and authoritative GT z are two
    independent affine paths whose equality nothing else enforces.  Shifting only
    the GT side leaves every other gate satisfiable, so the pairing postcheck is
    the only thing that can catch it.
    """
    from src.agent.judge import gt_extraction as ge
    original = ge._elevation_geometry

    def drifted(msp, evidence, view, manifest):
        along, z, refs = original(msp, evidence, view, manifest)
        return along, z.model_copy(update={"lo": z.lo - 0.05, "hi": z.hi - 0.05}), refs

    monkeypatch.setattr(ge, "_elevation_geometry", drifted)
    result = _run(tmp_path, _calibrated_request())
    assert not _gate(result, "G9").passed
    assert _gate(result, "G9").evidence["v3_code"] == "elevation_pairing_drift"
    assert any(diag.code == "tarch_elevation_pairing_drift" for diag in result.diagnostics)
    assert all(reason.startswith("z_interval_drift:")
               for reason in _gate(result, "G9").evidence["pairing_drift"])


@pytest.mark.parametrize("count", [0, 2])
def test_relevant_pair_without_exactly_one_ref_group_is_pairing_drift(green_sm24, count):
    """`每个 relevant pair 恰一组 refs`: neither an unconsumed ledger entry (0) nor
    one evidence claimed twice (2) may pass."""
    request, result, document = green_sm24
    openings = list(document.openings)
    index = next(i for i, item in enumerate(openings)
                 if any(ref.role == "opening_elevation" for ref in item.source_refs))
    refs = list(openings[index].source_refs)
    elevation = next(ref for ref in refs if ref.role == "opening_elevation")
    if count == 0:
        refs = [ref for ref in refs if ref is not elevation]
    else:
        other = next(i for i, item in enumerate(openings)
                     if i != index and any(r.role == "opening_elevation" for r in item.source_refs))
        openings[other] = openings[other].model_copy(update={
            "source_refs": [*openings[other].source_refs, elevation]})
    openings[index] = openings[index].model_copy(update={"source_refs": refs})
    reasons = tn._verify_pairing_consistency(document.model_copy(update={"openings": openings}),
                                             result.elevation_records, request)
    assert any(reason.startswith(f"evidence_ref_group_count:{elevation.entity_handle}:{count}")
               for reason in reasons), reasons


def test_ledger_kind_and_view_id_drift_are_pairing_drift(green_sm24):
    """kind / view id must be compared, not assumed from construction."""
    request, result, document = green_sm24
    records = list(result.elevation_records)
    target = next(record for record in records if record.kind == "window")
    handle = target.generated_handle
    flipped = [record if record is not target
               else tn._ElevationRecord(**{**record.__dict__, "kind": "door"}) for record in records]
    reasons = tn._verify_pairing_consistency(document, flipped, request)
    assert any(reason.startswith(f"kind_mismatch:{handle}:") for reason in reasons), reasons
    other_view = next(record.view_id for record in records if record.view_id != target.view_id)
    moved = [record if record is not target
             else tn._ElevationRecord(**{**record.__dict__, "view_id": other_view}) for record in records]
    reasons = tn._verify_pairing_consistency(document, moved, request)
    assert any(reason.startswith(f"view_id_mismatch:{handle}:") for reason in reasons), reasons


@pytest.mark.parametrize("mutation", ["sign", "endpoint", "offset", "sign_offset"])
def test_south_datum_partial_mutations_make_g1_red(tmp_path, mutation):
    request = _request(); views = list(request.elevation_views)
    south = next(view for view in views if view.id == "South_view")
    along = south.world_along_from_source_m.model_dump(mode="python")
    datum = south.floor_datums[0].model_dump(mode="python")
    if mutation in {"sign", "sign_offset"}:
        along["scale"] *= -1
    if mutation in {"offset", "sign_offset"}:
        # Preserve the unordered [0,10] span for sign+offset; the unchanged
        # declared endpoint must still trip the directed-anchor gate.
        along["offset"] = 10.0 - along["offset"] if mutation == "sign_offset" else along["offset"] + 0.2
    if mutation == "endpoint":
        datum["world_along_lo_source_endpoint"] = "end"
    changed = south.model_copy(update={"world_along_from_source_m": south.world_along_from_source_m.model_copy(update=along),
                                       "floor_datums": [south.floor_datums[0].model_copy(update=datum)]})
    views[views.index(south)] = changed
    result = _run(tmp_path, _rehash(request.model_copy(update={"elevation_views": views})))
    assert not _gate(result, "G1").passed
    assert any(diag.code == "tarch_elevation_along_direction_mismatch" for diag in result.diagnostics)


def test_door_role_shape_mutation_makes_g3_red(tmp_path):
    request = _request(); dialect = request.plan_views[0].dialect_rules.model_copy(deep=True)
    rule = dialect.elevation_door_block_rules[0]
    roles = list(rule.entity_roles)
    roles[0] = roles[0].model_copy(update={"role": "nonstructural_detail"})
    roles[10] = roles[10].model_copy(update={"role": "structural_outline"})  # CIRCLE 11C
    dialect.elevation_door_block_rules[0] = rule.model_copy(update={"entity_roles": roles})
    plan = request.plan_views[0].model_copy(update={"dialect_rules": dialect})
    result = _run(tmp_path, _rehash(request.model_copy(update={"plan_views": [plan]})))
    assert not _gate(result, "G3").passed
    assert any(diag.code == "tarch_elevation_door_structure_invalid" for diag in result.diagnostics)


def test_door_block_fingerprint_drift_makes_g3_red(tmp_path):
    """A request-bound block fingerprint is an E3 gate, not advisory metadata."""
    request = _request(); dialect = request.plan_views[0].dialect_rules.model_copy(deep=True)
    rule = dialect.elevation_door_block_rules[0]
    dialect.elevation_door_block_rules[0] = rule.model_copy(update={"block_definition_sha256": "0" * 64})
    plan = request.plan_views[0].model_copy(update={"dialect_rules": dialect})
    result = _run(tmp_path, _rehash(request.model_copy(update={"plan_views": [plan]})))
    assert not _gate(result, "G3").passed
    assert any(diag.code == "tarch_elevation_door_block_drift" for diag in result.diagnostics)


@pytest.mark.parametrize(
    ("name", "dx", "dy"),
    [
        ("positive_gap", -100.0, 0.0),
        ("positive_overlap", 100.0, 0.0),
        ("t_shape", 400.0, 1200.0),
        ("different_z", 0.0, 1000.0),
    ],
)
def test_door_structural_union_mutations_make_g3_red(tmp_path, name, dx, dy):
    """North B03/B04 is the real two-module door; corrupt its structural union.

    The mutations retain individually valid closed four-edge ``112`` modules.
    They therefore prove the union gate itself (rather than a malformed block,
    source hash, or later G9 pairing) owns the red result.
    """
    source = tmp_path / f"union_{name}.dxf"
    doc = ezdxf.readfile(str(SOURCE))
    module = next(entity for entity in doc.modelspace()
                  if entity.dxftype() == "INSERT" and entity.dxf.handle == "B04")
    module.translate(dx, dy, 0.0)
    doc.saveas(str(source))
    request = _request().model_copy(update={"source_dxf_sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    result = _run(tmp_path / "run", _rehash(request), source)
    assert not _gate(result, "G3").passed
    assert any(diag.code == "tarch_elevation_door_structure_invalid" for diag in result.diagnostics)


def test_kind_mutation_and_missing_evidence_make_g9_red(tmp_path):
    green = _run(tmp_path / "green", _request())
    manifest = green.manifest.model_copy(deep=True)
    elev = next(view for view in manifest.views if view.kind == "elevation" and view.opening_entities)
    window_index = next(i for i, item in enumerate(elev.opening_entities) if item.kind == "window")
    elev.opening_entities[window_index] = elev.opening_entities[window_index].model_copy(update={"kind": "door"})
    ok, code, _document = tn._run_g9_v3_preflight(green.augmented_dxf_path, manifest, TOOLING)
    assert not ok and code == "elevation_opening_no_candidate"
    manifest = green.manifest.model_copy(deep=True)
    elev = next(view for view in manifest.views if view.kind == "elevation" and view.opening_entities)
    # Remove a real evidence group: plan extraction still succeeds, while full
    # GT completeness rejects the pairing drift at G9.
    elev.opening_entities.pop()
    ok, code, _document = tn._run_g9_v3_preflight(green.augmented_dxf_path, manifest, TOOLING)
    assert not ok and "gt_opening_elevation_evidence_mismatch" in code


def test_raster_lo_hi_control_swap_makes_g10_calibration_red(tmp_path):
    request = TarchConversionRequestV1.model_validate_json(
        (ROOT / "request_v3_calibrated.json").read_text())
    bindings = list(request.raster_overlays)
    south_index = next(i for i, item in enumerate(bindings) if item.view_id == "South_view")
    binding = bindings[south_index].model_copy(deep=True)
    controls = list(binding.calibration_controls)
    lo = next(i for i, item in enumerate(controls) if item.role == "datum_lo")
    hi = next(i for i, item in enumerate(controls) if item.role == "datum_hi")
    # Keep the labels but exchange their source anchors: this is the dangerous
    # symmetric-facade direction mutation, not a malformed request shortcut.
    controls[lo], controls[hi] = (controls[lo].model_copy(update={"source_point_dxf": controls[hi].source_point_dxf}),
                                  controls[hi].model_copy(update={"source_point_dxf": controls[lo].source_point_dxf}))
    bindings[south_index] = binding.model_copy(update={"calibration_controls": controls})
    result = _run(tmp_path, _rehash(request.model_copy(update={"raster_overlays": bindings})))
    assert not _gate(result, "G10").passed
    assert any(diag.code == "tarch_raster_calibration_invalid" for diag in result.diagnostics)


def test_raster_horizontal_mirror_in_bounds_makes_g10_calibration_red(tmp_path):
    """A non-singular, in-image South mirror must still fail G10 calibration.

    Mechanism (corrected 2026-07-25 after the review's directed sub-probe): the red
    result here is owned by the elevation ``residual_ok`` check — a mirrored affine no
    longer back-projects the declared controls onto their declared source points.  The
    directed lo/hi handedness check still passes under a pure mirror; that failure face
    is covered separately by ``test_raster_lo_hi_control_swap_makes_g10_calibration_red``.
    """
    request = TarchConversionRequestV1.model_validate_json(
        (ROOT / "request_v3_calibrated.json").read_text())
    bindings = list(request.raster_overlays)
    south_index = next(i for i, item in enumerate(bindings) if item.view_id == "South_view")
    binding = bindings[south_index]
    # Mirror source(x) about the full original PNG width.  The facade's four
    # projected corners remain in the same image rectangle; only the directed
    # lo/hi controls expose the wrong handedness.
    from PIL import Image
    image_width = Image.open(Path("case_tests/e2e_tests/sm24_anchor/case_data/South_view.png")).width
    affine = binding.pixel_to_source_m.model_copy(update={
        "m00": -binding.pixel_to_source_m.m00,
        "m01": -binding.pixel_to_source_m.m01,
        "m02": binding.pixel_to_source_m.m02 + binding.pixel_to_source_m.m00 * (image_width - 1)
             + binding.pixel_to_source_m.m01 * 0.0,
    })
    bindings[south_index] = binding.model_copy(update={"pixel_to_source_m": affine})
    result = _run(tmp_path, _rehash(request.model_copy(update={"raster_overlays": bindings})))
    assert not _gate(result, "G10").passed
    assert any(diag.code == "tarch_raster_calibration_invalid" for diag in result.diagnostics)


def test_plan_footprint_control_swap_makes_g10_calibration_red(tmp_path):
    """Plan calibration is typed too: a swapped outer-wall corner is not cosmetic."""
    request = TarchConversionRequestV1.model_validate_json(
        (ROOT / "request_v3_calibrated.json").read_text())
    bindings = list(request.raster_overlays)
    plan_index = next(i for i, item in enumerate(bindings) if item.view_id == "plan-F1")
    binding = bindings[plan_index].model_copy(deep=True)
    controls = list(binding.calibration_controls)
    sw = next(i for i, item in enumerate(controls) if item.role == "footprint_sw")
    se = next(i for i, item in enumerate(controls) if item.role == "footprint_se")
    controls[sw], controls[se] = (
        controls[sw].model_copy(update={"source_point_dxf": controls[se].source_point_dxf}),
        controls[se].model_copy(update={"source_point_dxf": controls[sw].source_point_dxf}),
    )
    bindings[plan_index] = binding.model_copy(update={"calibration_controls": controls})
    result = _run(tmp_path, _rehash(request.model_copy(update={"raster_overlays": bindings})))
    assert not _gate(result, "G10").passed
    assert any(diag.code == "tarch_raster_calibration_invalid" for diag in result.diagnostics)


# --------------------------------------------------------------------------- #
# spec §9.3 [S] — z / datum mutations.  Window height is the whole point of this
# batch, so every one of the seven declared mutations must BLOCK, and none of them
# may be waved through merely because the resulting number "still looks like a
# window height".
# --------------------------------------------------------------------------- #
def _south(request):
    return next(view for view in request.elevation_views if view.id == "South_view")


def _with_south(request, changed):
    views = list(request.elevation_views)
    views[views.index(_south(request))] = changed
    return _rehash(request.model_copy(update={"elevation_views": views}))


def test_z_datum_swapped_to_another_line_makes_g1_red(tmp_path):
    """§9.3-1 datum re-pointed at a different horizontal line (e.g. the roof line)."""
    request = _calibrated_request()
    south = _south(request)
    datum = south.floor_datums[0]
    doc = ezdxf.readfile(str(SOURCE))
    current = next(e for e in doc.modelspace() if e.dxf.handle == datum.entity_handle)
    y_now = float(current.dxf.start.y)
    other = next(e for e in doc.modelspace()
                 if e.dxftype() == "LINE" and e.dxf.handle != datum.entity_handle
                 and abs(float(e.dxf.start.y) - float(e.dxf.end.y)) < 1e-6
                 and abs(float(e.dxf.start.y) - y_now) > 500.0
                 and tn._inside(e, south.clip_box_dxf))
    changed = south.model_copy(update={"floor_datums": [
        datum.model_copy(update={"entity_handle": other.dxf.handle})]})
    result = _run(tmp_path, _with_south(request, changed))
    assert not _gate(result, "G1").passed
    assert any(diag.code in {"tarch_elevation_z_transform_mismatch",
                             "tarch_elevation_along_direction_mismatch"}
               for diag in result.diagnostics)


@pytest.mark.parametrize(
    ("name", "update"),
    [
        ("axis_mismatch", {"source_axis": "x"}),      # §9.3-2 z axis == along axis
        ("scale_unit", {"scale": 1.0}),               # §9.3-3 0.001 -> 1.0
        ("offset_shift", {"offset": 0.2}),            # §9.3-4 datum shifted 0.2 m
    ],
)
def test_z_transform_mutations_make_g1_red(tmp_path, name, update):
    request = _calibrated_request()
    south = _south(request)
    z = south.world_z_from_source_m
    if name == "offset_shift":
        update = {"offset": z.offset + 0.2}
    changed = south.model_copy(update={"world_z_from_source_m": z.model_copy(update=update)})
    result = _run(tmp_path, _with_south(request, changed))
    assert not _gate(result, "G1").passed
    assert any(diag.code == "tarch_elevation_z_transform_mismatch" for diag in result.diagnostics)


def test_two_datums_deriving_different_offsets_make_g1_red(tmp_path):
    """§9.3-5: a second datum that disagrees must not be silently outvoted by the first.

    Before this batch only ``floor_datums[0]`` was consulted, so the second datum was
    dead input.  The mutation adds a real second LINE 200 mm above the true datum.
    """
    request = _calibrated_request()
    south = _south(request)
    datum = south.floor_datums[0]
    source = tmp_path / "two_datums.dxf"
    doc = ezdxf.readfile(str(SOURCE))
    original = next(e for e in doc.modelspace() if e.dxf.handle == datum.entity_handle)
    extra = doc.modelspace().add_line(
        (float(original.dxf.start.x), float(original.dxf.start.y) + 200.0),
        (float(original.dxf.end.x), float(original.dxf.end.y) + 200.0),
        dxfattribs={"layer": original.dxf.layer})
    doc.saveas(str(source))
    changed = south.model_copy(update={"floor_datums": [
        datum, datum.model_copy(update={"entity_handle": extra.dxf.handle})]})
    request = request.model_copy(update={"source_dxf_sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    result = _run(tmp_path / "run", _with_south(request, changed), source)
    assert not _gate(result, "G1").passed
    assert any(diag.code == "tarch_elevation_z_transform_mismatch" for diag in result.diagnostics)


@pytest.mark.parametrize(("name", "dy"), [("crosses_floor_top", 2600.0), ("above_ceiling", 4200.0)])
def test_window_z_outside_its_floor_blocks_g9(tmp_path, name, dy):
    """§9.3-6/-7: a window frame straddling the floor top, or entirely above the
    ceiling, must not produce GT.  Both are owned by the extractor's floor-containment
    check (``elevation_opening_floor_ambiguous``), surfaced through G9 as the raw v3
    code — there is no separate converter code for it."""
    request = _calibrated_request()
    south = _south(request)
    source = tmp_path / f"zshift_{name}.dxf"
    doc = ezdxf.readfile(str(SOURCE))
    lines = [e for e in doc.modelspace()
             if e.dxftype() == "LINE" and e.dxf.layer in south.window_selector.layers
             and tn._inside(e, south.clip_box_dxf)]
    group = tn._line_components(lines, 1.0)[0]
    for entity in group:
        entity.translate(0.0, dy, 0.0)
    doc.saveas(str(source))
    request = request.model_copy(update={"source_dxf_sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    result = _run(tmp_path / "run", _rehash(request), source)
    assert not _gate(result, "G9").passed
    codes = {diag.code for diag in result.diagnostics}
    assert "tarch_v3_precondition" in codes or codes & {"tarch_elevation_opening_component_invalid"}


# --------------------------------------------------------------------------- #
# spec §6.4 — the single-channel contract for G9 extraction failures (review MINOR-1)
# --------------------------------------------------------------------------- #
_DECLARED_NOT_EMITTED = (
    "tarch_elevation_opening_no_candidate",
    "tarch_elevation_opening_assignment_ambiguous",
    "tarch_elevation_opening_kind_mismatch",
    "tarch_interior_opening_elevation_not_applicable",
)


def test_declared_not_emitted_elevation_codes_stay_unemitted(tmp_path, monkeypatch):
    """These four registry codes are declared vocabulary with no emitter, by design.

    §6.4 requires G9 extraction failures to surface the RAW extractor code inside
    ``tarch_v3_precondition.context.v3_code`` rather than being re-spelled into a
    converter code (re-spelling lets the two vocabularies drift apart silently).
    This locks both halves: nothing emits them, and the real channel works.
    """
    body = Path("src/agent/judge/tarch_normalize.py").read_text(encoding="utf-8")
    for code in _DECLARED_NOT_EMITTED:
        assert f'_diag("{code}"' not in body, code

    from src.agent.judge import gt_extraction as ge
    original = ge._elevation_geometry

    def displaced(msp, evidence, view, manifest):
        along, z, refs = original(msp, evidence, view, manifest)
        return along.model_copy(update={"lo": along.lo + 5.0, "hi": along.hi + 5.0}), z, refs

    monkeypatch.setattr(ge, "_elevation_geometry", displaced)
    result = _run(tmp_path, _calibrated_request())
    assert not _gate(result, "G9").passed
    precondition = [diag for diag in result.diagnostics if diag.code == "tarch_v3_precondition"]
    assert precondition and precondition[-1].context["v3_code"] == "elevation_opening_no_candidate"
    assert not [diag for diag in result.diagnostics if diag.code in _DECLARED_NOT_EMITTED]


# --------------------------------------------------------------------------- #
# spec §6.6 [S] — sm24 forward e2e post-conditions.
# These are anchor-fixture NUMBERS: the production algorithm must never branch on
# them (there is no `if len(openings) == 14` anywhere), they only pin what the real
# drawing must yield so a future algorithm drift cannot pass unnoticed.
# --------------------------------------------------------------------------- #
def test_sm24_forward_e2e_post_conditions(green_sm24):
    request, result, doc = green_sm24
    source = doc.sources[0]
    plans = [view for view in source.views if view.kind == "plan"]
    elevations = [view for view in source.views if view.kind == "elevation"]
    assert len(plans) == 1 and len(elevations) == 4                       # (1)

    segments = {segment.id: segment for floor in doc.floors for segment in floor.boundary_segments}
    for view in elevations:                                               # (2)
        carriers = [segment for segment in segments.values()
                    if view.projection_surface_key in segment.projection_surface_keys]
        assert carriers, view.id
        assert {segment.facade_family for segment in carriers} == {view.facade_family}

    assert len(doc.openings) == 14                                        # (3)
    windows = [item for item in doc.openings if item.kind == "window"]
    doors = [item for item in doc.openings if item.kind == "door"]
    assert len(windows) == 11 and len(doors) == 3
    assert all(item.z_interval is not None for item in windows)           # (4)
    seen = {(round(item.z_interval.lo, 3), round(item.z_interval.hi, 3)) for item in windows}
    assert seen == {(1.0, 2.8), (1.0, 3.4)}                               # (5)

    # (6) exterior doors carry a SOURCE-OBSERVED z; a floor default would start at z_floor
    floor = doc.floors[0]
    assert all(item.z_interval is not None for item in doors)
    assert {(round(item.z_interval.lo, 3), round(item.z_interval.hi, 3)) for item in doors} == {(0.2, 2.6)}
    assert all(item.z_interval.lo > floor.z_floor_m for item in doors)

    # (7) door z comes from the validated structural outline, and the CIRCLE 11C is
    # explicitly declared non-structural — it must not inflate the head height.
    rule = request.plan_views[0].dialect_rules.elevation_door_block_rules[0]
    roles = {entry.entity_handle: entry.role for entry in rule.entity_roles}
    assert roles["11C"] != "structural_outline"
    assert sum(role == "structural_outline" for role in roles.values()) == 1
    assert all(record.structural_handles for record in result.elevation_records if record.kind == "door")

    # (8) every opening has a plan ref; every relevant opening has an elevation ref
    for opening in doc.openings:
        roles_seen = {ref.role for ref in opening.source_refs}
        assert "opening_plan" in roles_seen, opening.id
        assert "opening_elevation" in roles_seen, opening.id

    # (9) the 7 interior doors stay out of the GT entirely
    interior = [item for item in result.p1.openings if item.classification == "interior_excluded"]
    assert len(interior) == 7
    assert not {f"op_{item.handle.lower()}" for item in interior} & {item.id for item in doc.openings}

    # (10) canonical reload is byte-identical
    from src.agent.judge.gt_schema import GroundTruthV3, canonical_gt_v3_bytes
    payload = canonical_gt_v3_bytes(doc)
    assert canonical_gt_v3_bytes(GroundTruthV3.model_validate_json(payload)) == payload


def test_sm24_boundary_segments_carry_evidenced_wall_thickness(green_sm24):
    """WI-4: exterior wall thickness reaches the GT, sourced from the converter's
    measured jamb-cap evidence (12 outer_skin edges, all 240 mm), never a constant."""
    _request, result, doc = green_sm24
    assert {segment.wall_thickness_m for floor in doc.floors for segment in floor.boundary_segments} == {0.24}
    outer = [edge for zone in result.zones for edge in zone.edges if edge.basis == "outer_skin"]
    assert outer and all(edge.thickness_evidence is not None for edge in outer)
    assert {edge.thickness_evidence.source_kind for edge in outer} == {"wall_cap_or_opening_jamb"}


def test_wall_thickness_is_none_without_complete_evidence(green_sm24):
    """Negative lock: any missing proof or disagreement yields None, never a guess."""
    _request, result, _doc = green_sm24
    zones = result.zones
    assert tn._outer_skin_thickness_m(zones, 0.001) == 0.24
    import copy
    stripped = copy.deepcopy(zones)
    next(edge for zone in stripped for edge in zone.edges
         if edge.basis == "outer_skin").thickness_evidence = None
    assert tn._outer_skin_thickness_m(stripped, 0.001) is None
    disagreeing = copy.deepcopy(zones)
    next(edge for zone in disagreeing for edge in zone.edges
         if edge.basis == "outer_skin").thickness_native = 300.0
    assert tn._outer_skin_thickness_m(disagreeing, 0.001) is None
    assert tn._outer_skin_thickness_m([], 0.001) is None


def test_plan_zone_label_anchors_fall_inside_their_own_polygon(green_sm24):
    """FIX-1: a zone label must be anchored INSIDE its own polygon.

    sm24 is the right fixture precisely because it is not a box of rectangles: z4 is a
    6-vertex L and z5 an 8-vertex C.  The 07-25 bundle anchored labels at the bbox NW
    corner, which for z4 lands inside z5's corridor strip; z5 is filled after z4, so
    z4's label was painted over and the delivered plan carried only 7 of 8 zone names
    — the human sign-off confirms room assignment, so a missing name is a hole in that
    gate, not a cosmetic defect.
    """
    import sys
    sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
    import render_gt_overlay as ov
    from shapely.geometry import Point, Polygon

    _request, _result, doc = green_sm24
    floor = doc.floors[0]
    shapes = {zone.id: Polygon([tuple(v) for v in zone.polygon.exterior.vertices])
              for zone in floor.zones}
    assert len(shapes) == 8
    assert len(shapes["z4"].exterior.coords) - 1 == 6      # the L
    assert len(shapes["z5"].exterior.coords) - 1 == 8      # the C

    for zone_id, polygon in shapes.items():
        anchor = Point(ov._label_anchor([tuple(v) for v in polygon.exterior.coords[:-1]]))
        assert polygon.contains(anchor), f"{zone_id} anchor escaped its own polygon"
        for other_id, other in shapes.items():
            if other_id != zone_id:
                assert not other.contains(anchor), f"{zone_id} anchor landed inside {other_id}"

    # Regression witness: the replaced bbox-NW-corner rule really did put z4's label
    # outside z4 and onto z5's west edge — and PIL fills a polygon boundary-inclusive,
    # so z5 (painted after z4) covered the text.  `covers` is the boundary-inclusive
    # test; `contains` excludes the boundary and would understate the overlap.
    z4 = shapes["z4"]
    xs, ys = zip(*z4.exterior.coords[:-1])
    old_anchor = Point(min(xs), max(ys))
    assert not z4.covers(old_anchor), "witness invalid: old anchor was inside z4 after all"
    assert shapes["z5"].covers(old_anchor), "witness invalid: old anchor missed z5"


def test_elevation_audit_rows_carry_the_contract_mandated_opening_columns(green_sm24):
    """FIX-3 / spec §7.4 [S]: the per-opening audit table is the mandated backstop for
    whole-facade mirror residual, explicitly "not optional auxiliary information".

    It is only usable if each row carries the opening id (the join key to the overlay,
    which labels boxes by GT opening id — evidence ids live in a different handle
    space), the plan-side along interval (without it the "did a mirror swap this
    opening with another one" check has no plan side to compare against), and the host
    zone (what the user actually signs: room assignment).  All three come from the
    extracted GT, never from a second converter-side derivation.
    """
    _request, result, doc = green_sm24
    rows = result.conversion_report.elevation_audit_rows
    assert len(rows) == 14

    for row in rows:
        for column in ("opening_id", "host_zone_id", "plan_world_along_interval"):
            assert row.get(column) not in (None, "", []), (row.get("evidence_id"), column)

    # opening_id is exactly the GT opening set, both directions, no duplicates
    gt_ids = {opening.id for opening in doc.openings}
    row_ids = [row["opening_id"] for row in rows]
    assert len(row_ids) == len(set(row_ids)) == 14
    assert set(row_ids) == gt_ids

    zone_ids = {zone.id for floor in doc.floors for zone in floor.zones}
    opening_by_id = {opening.id: opening for opening in doc.openings}
    for row in rows:
        opening = opening_by_id[row["opening_id"]]
        assert row["host_zone_id"] in zone_ids
        assert row["host_zone_id"] == opening.host_zone_id
        assert row["plan_world_along_interval"] == [opening.world_along_interval.lo,
                                                    opening.world_along_interval.hi]
        assert row["kind"] == opening.kind

    # the overlay labels openings by GT id, so table and picture share one id space
    import sys
    sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
    from src.agent.judge.gt_render_model import gt_to_render_model
    drawn = {opening.id for surface in gt_to_render_model(doc).elevation_surfaces
             for opening in surface.openings if opening.z_interval is not None}
    assert drawn and drawn <= set(row_ids)
