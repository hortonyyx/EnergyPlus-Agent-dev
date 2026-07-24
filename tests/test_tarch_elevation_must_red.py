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
    ok, code = tn._run_g9_v3_preflight(green.augmented_dxf_path, manifest, TOOLING)
    assert not ok and code == "elevation_opening_no_candidate"
    manifest = green.manifest.model_copy(deep=True)
    elev = next(view for view in manifest.views if view.kind == "elevation" and view.opening_entities)
    # Remove a real evidence group: plan extraction still succeeds, while full
    # GT completeness rejects the pairing drift at G9.
    elev.opening_entities.pop()
    ok, code = tn._run_g9_v3_preflight(green.augmented_dxf_path, manifest, TOOLING)
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
    """A non-singular, in-image South mirror must still fail directed controls."""
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
