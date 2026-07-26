"""WP-1 byte-reproducibility locks for converter-produced augmented DXFs."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.gt_extraction import ExtractionInputs, extract_gt_v3
from src.agent.judge.gt_render_model import gt_to_render_model
from src.agent.judge.gt_schema import REPO_ROOT, compute_gt_implementation_hashes
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1, resolve_converter_tooling


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf"
REQUEST = REPO / "logs/experiments/2026-07-25_sm24_gt_review/request_v3_calibrated.json"
ANNOTATIONS = REPO / "logs/experiments/2026-07-25_sm24_gt_review/review_annotations.json"
RASTER_ROOT = REPO / "case_tests/e2e_tests/sm24_anchor/case_data"


def _run(tmp_path: Path, label: str):
    source = tmp_path / "source.dxf"
    if not source.exists():
        source.write_bytes(SOURCE.read_bytes())
    request = TarchConversionRequestV1.model_validate_json(REQUEST.read_text(encoding="utf-8"))
    tooling = resolve_converter_tooling(REPO / "src/configs/judge_gt.yaml", REPO / "src/configs/correction.yaml")
    result = tn.run_p2_conversion(source, request, request.plan_views[0], tooling, tmp_path / label / "work")
    document = extract_gt_v3(ExtractionInputs(result.augmented_dxf_path, result.manifest, tooling,
                                               compute_gt_implementation_hashes(REPO_ROOT)))
    return result, document


def _render_all(document, manifest, out: Path) -> dict[str, bytes]:
    sys.path.insert(0, str(REPO / "scripts/tool_scripts"))
    import render_gt as render_gt
    import render_gt_overlay as overlays

    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))["zone_roles"]
    out.mkdir(parents=True)
    model = gt_to_render_model(document)
    render_gt.render_plan_model(model, review_annotations=annotations).save(out / "gt_plan.png")
    render_gt.render_elevation_model(model).save(out / "gt_elev.png")
    images = overlays.build_gt_overlay_images_v3(document, manifest, raster_root=RASTER_ROOT,
                                                  review_annotations=annotations)
    for view_id, image in images.items():
        image.save(out / f"overlay_{view_id}.png")
    return {path.name: path.read_bytes() for path in sorted(out.iterdir())}


def test_r1_1_augmented_dxf_is_byte_identical_for_two_runs(tmp_path):
    first, _ = _run(tmp_path, "first")
    second, _ = _run(tmp_path, "second")
    assert first.augmented_dxf_path.read_bytes() == second.augmented_dxf_path.read_bytes()


def test_r1_2_neutering_metadata_pin_releases_r1_1(tmp_path, monkeypatch):
    monkeypatch.setattr(tn, "_apply_deterministic_dxf_metadata", lambda *args: None)
    first, _ = _run(tmp_path, "first")
    second, _ = _run(tmp_path, "second")
    assert first.augmented_dxf_path.read_bytes() != second.augmented_dxf_path.read_bytes()


def test_r1_3_metadata_guids_change_with_source_or_request():
    source = hashlib.sha256(b"source-a").hexdigest()
    request = hashlib.sha256(b"request-a").hexdigest()
    baseline = tn._deterministic_dxf_metadata(source, request)
    assert tn._deterministic_dxf_metadata(hashlib.sha256(b"source-b").hexdigest(), request)["$VERSIONGUID"] != baseline["$VERSIONGUID"]
    assert tn._deterministic_dxf_metadata(source, hashlib.sha256(b"request-b").hexdigest())["$FINGERPRINTGUID"] != baseline["$FINGERPRINTGUID"]


def test_r1_4_gt_and_all_seven_renders_are_byte_identical(tmp_path):
    first, gt_first = _run(tmp_path, "first")
    second, gt_second = _run(tmp_path, "second")
    assert gt_first.content_sha256 == gt_second.content_sha256
    assert _render_all(gt_first, first.manifest, tmp_path / "first" / "renders") == _render_all(
        gt_second, second.manifest, tmp_path / "second" / "renders")


def test_ezdxf_default_writer_matches_converter_writer_except_pinned_metadata(tmp_path):
    """MINOR-3: retain ezdxf's writer behaviour apart from the six pinned values."""
    import ezdxf
    default = tmp_path / "default.dxf"; converter = tmp_path / "converter.dxf"
    ezdxf.readfile(SOURCE).saveas(default)
    tn._save_converter_augmented_dxf(ezdxf.readfile(SOURCE), converter, "a" * 64, "b" * 64)
    def strip_pinned(raw: bytes) -> bytes:
        text = raw.decode("utf-8")
        for name in ("$TDCREATE", "$TDUCREATE", "$TDUPDATE", "$TDUUPDATE", "$FINGERPRINTGUID", "$VERSIONGUID"):
            text = re.sub(rf"({re.escape(name)}\n\s*\d+\n)[^\n]+", r"\1<PINNED>", text)
        text = re.sub(r"(WRITTEN_BY_EZDXF\n\s*350\n[0-9A-F]+\n\s*0\nDICTIONARYVAR.*?\n\s*1\n)[^\n]+",
                      r"\1<PINNED>", text, flags=re.S)
        return text.encode("utf-8")
    assert strip_pinned(default.read_bytes()) == strip_pinned(converter.read_bytes())
