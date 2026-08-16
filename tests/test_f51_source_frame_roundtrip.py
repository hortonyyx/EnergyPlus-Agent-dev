"""F-51 source-frame roundtrip locks (L1/L2/L3), all through the real CLI.

F-51 (2026-08-16): the reading VLM sees a possibly downsampled frame of the
source image, so its self-reported pixel coordinates live in a DIFFERENT frame
than ``cv_probe``, which reads the original-resolution file.  A calibration
built from such coordinates can be self-consistent yet globally wrong — the
cross-axis gate passes because the error is a uniform scale, and crops land in
the wrong region as honest false negatives.

Three locks, each executed via ``python tools/run_cv_probe.py ...`` inside a
real staging built by the same builder ``spawn_isolated_reader.py build``
drives (``build_isolation_workspace``).  Calling the toolbox functions
directly in the main tree does not transfer to the sandboxed wrapper shape —
this project has already been bitten by that once, so the locks go through the
staged entrypoint or not at all.

- L1 roundtrip scale: a synthesized image with two vertical lines at known
  pixels, calibrated through the CLI, must report the exact px/m.
- L2 size reporting: every sidecar reports the SOURCE image's true
  ``width_px``/``height_px`` — including ``crop_zoom`` with ``--bbox``, where
  the reported size must still be the source's, never the crop's.
- L3 frame mismatch is self-detectable: anchors uniformly scaled by 0.6 (the
  "reader-style" error: coordinates read off a downsampled frame) must yield a
  px/m clearly different from the truth (>= 20% off).  This lock pins the
  FAILURE SHAPE as observable; it does NOT ask the tool to reject such input
  (that is C1/F-34 territory and is deliberately untouched here).
"""

from __future__ import annotations

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from src.agent.execution.isolation import build_isolation_workspace

CASE_DIR = Path("case_tests/e2e_tests/sm21_anchor")

# The synthesized source image: 1200x600, two vertical gray lines whose centers
# sit at x=100 and x=700.  600 px between them representing 15.0 m makes the
# true scale exactly 40 px/m (an integer, so L1's 0.5% tolerance has margin
# for float noise and nothing else).
SYNTH_NAME = "f51_synth.png"
SYNTH_WIDTH_PX = 1200
SYNTH_HEIGHT_PX = 600
LINE_A_X = 100
LINE_B_X = 700
SPAN_PX = LINE_B_X - LINE_A_X  # 600
TRUE_VALUE_M = 15.0
TRUE_PX_PER_M = SPAN_PX / TRUE_VALUE_M  # 40.0


def _synth_png_bytes() -> bytes:
    """Two full-height vertical lines at the anchor pixel positions.

    Line gray is 128 — inside clean_vector_v1's 60..230 gray band, so the image
    is also a legitimate clean-vector subject (premise check for §6 of the
    dispatch: no applicability-style rejection applies to any of these tools;
    px_m_calibrator and crop_zoom do not mask the image at all).
    """

    img = Image.new("RGB", (SYNTH_WIDTH_PX, SYNTH_HEIGHT_PX), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    for x in (LINE_A_X, LINE_B_X):
        draw.line((x, 0, x, SYNTH_HEIGHT_PX), fill=(128, 128, 128), width=4)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def staging(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real isolation staging (preview/unbound build) with the synthetic
    source image staged into ``case_data/`` — exactly where the wrapper's path
    resolution expects reader inputs to live."""

    root = tmp_path_factory.mktemp("f51_staging")
    manifest = build_isolation_workspace(CASE_DIR, staging_root=root / "staging")
    staging_root = manifest.staging_root
    (staging_root / "case_data" / SYNTH_NAME).write_bytes(_synth_png_bytes())
    return staging_root


def _run_probe(staging_root: Path, *cli_args: str) -> subprocess.CompletedProcess[str]:
    """Run the staged wrapper — the same command shape the reader is told to
    use (``python tools/run_cv_probe.py --tool ... --image ...``)."""

    proc = subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", *cli_args],
        cwd=staging_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    return proc


def _read_sidecar(staging_root: Path, out_dir: str, name: str) -> dict:
    path = staging_root / out_dir / "cv_evidence" / Path(SYNTH_NAME).stem / f"{name}.json"
    assert path.exists(), f"missing sidecar: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _x_anchor(px_a: float, px_b: float) -> str:
    return json.dumps(
        [{"axis": "x", "px_a": px_a, "px_b": px_b, "value_m": TRUE_VALUE_M}],
        separators=(",", ":"),
    )


def test_l1_roundtrip_scale_via_real_cli(staging: Path) -> None:
    """L1: known pixels + known meters through the real CLI give the exact
    px/m — the arithmetic chain (span -> axis_px_per_m) cannot silently rot."""

    _run_probe(
        staging,
        "--tool", "px_m_calibrator",
        "--image", f"case_data/{SYNTH_NAME}",
        "--out-dir", "out/f51_l1",
        "--anchors-json", _x_anchor(LINE_A_X, LINE_B_X),
        "--sidecar-name", "001_px_m_calibrator",
    )
    sidecar = _read_sidecar(staging, "out/f51_l1", "001_px_m_calibrator")
    result = sidecar["results"][0]
    # Field name taken from the real sidecar output (dispatch §3-B: the actual
    # field name of this version wins over any remembered spelling).
    assert set(result["axis_px_per_m"]) == {"x"}
    assert result["axis_px_per_m"]["x"] == pytest.approx(TRUE_PX_PER_M, rel=0.005)
    assert result["px_per_m"] == pytest.approx(TRUE_PX_PER_M, rel=0.005)
    assert result["metric"]["scale_px_per_m"] == pytest.approx(TRUE_PX_PER_M, rel=0.005)


def test_l2_source_size_reported_by_px_m_calibrator(staging: Path) -> None:
    """L2 (a): the sidecar reports the source image's true pixel size, and the
    pre-existing source_image keys (name / sha256) survive alongside."""

    _run_probe(
        staging,
        "--tool", "px_m_calibrator",
        "--image", f"case_data/{SYNTH_NAME}",
        "--out-dir", "out/f51_l2_cal",
        "--anchors-json", _x_anchor(LINE_A_X, LINE_B_X),
        "--sidecar-name", "001_px_m_calibrator",
    )
    sidecar = _read_sidecar(staging, "out/f51_l2_cal", "001_px_m_calibrator")
    source_image = sidecar["source_image"]
    assert source_image["name"] == SYNTH_NAME
    assert len(source_image["sha256"]) == 12
    assert source_image["width_px"] == SYNTH_WIDTH_PX
    assert source_image["height_px"] == SYNTH_HEIGHT_PX


def test_l2_source_size_reported_by_crop_zoom_after_crop(staging: Path) -> None:
    """L2 (b): with ``--bbox``, the crop really happens (crop_size_px is the
    cropped size) yet the reported source_image size is still the SOURCE's —
    the anchor a reader needs to detect a frame mismatch never shrinks."""

    _run_probe(
        staging,
        "--tool", "crop_zoom",
        "--image", f"case_data/{SYNTH_NAME}",
        "--out-dir", "out/f51_l2_crop",
        "--bbox", "200,150,800,450",
        "--sidecar-name", "001_crop_zoom",
    )
    sidecar = _read_sidecar(staging, "out/f51_l2_crop", "001_crop_zoom")
    source_image = sidecar["source_image"]
    assert source_image["width_px"] == SYNTH_WIDTH_PX
    assert source_image["height_px"] == SYNTH_HEIGHT_PX
    # Prove the crop actually happened — otherwise the source-size assertion
    # above would pass vacuously on a tool that ignored --bbox.
    result = sidecar["results"][0]
    assert result["crop_size_px"] == [600, 300]
    assert sidecar["crop_chain"], "crop_zoom sidecar must carry its crop_chain"
    assert sidecar["crop_chain"][0]["source_size_px"] == [SYNTH_WIDTH_PX, SYNTH_HEIGHT_PX]


def test_l3_frame_mismatched_anchors_yield_clearly_wrong_scale(staging: Path) -> None:
    """L3: a "reader-style" error — anchors uniformly scaled by 0.6, i.e.
    coordinates read off a 0.6x downsampled frame — produce a calibration that
    RUNS (returncode 0; rejecting it is C1's job, not this lock's) but is
    clearly wrong: >= 20% off the truth, so the mismatch is self-detectable by
    comparing against the true scale instead of passing silently."""

    scale = 0.6
    _run_probe(
        staging,
        "--tool", "px_m_calibrator",
        "--image", f"case_data/{SYNTH_NAME}",
        "--out-dir", "out/f51_l3",
        "--anchors-json", _x_anchor(LINE_A_X * scale, LINE_B_X * scale),
        "--sidecar-name", "001_px_m_calibrator",
    )
    sidecar = _read_sidecar(staging, "out/f51_l3", "001_px_m_calibrator")
    wrong = sidecar["results"][0]["px_per_m"]
    deviation = abs(wrong - TRUE_PX_PER_M) / TRUE_PX_PER_M
    assert wrong == pytest.approx(TRUE_PX_PER_M * scale, rel=0.005)
    assert deviation >= 0.20, (
        "uniformly rescaled anchors must NOT be able to masquerade as a "
        f"correct calibration: px_per_m={wrong}, truth={TRUE_PX_PER_M}"
    )
