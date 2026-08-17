"""Substrate sweep (Lane A, 2026-08-16): six authorized CV-probe tools x three
invocation forms (direct / --request / --batch), all through the real staged
wrapper (``build_isolation_workspace`` + ``subprocess`` against
``tools/run_cv_probe.py``) -- never a direct import of the toolbox functions.
This project has already been bitten once by "library-layer tests all green"
not transferring to the sandboxed wrapper shape (F-49 lived unnoticed for
five weeks precisely because of that gap).

Companion table with the full 18-cell grid, the parameter-form sweep, the
coordinate-frame findings, and the defect registry:
AI_agent/logs/experiments/2026-08-16_substrate_sweep/grid_A.md.

Fixture geometry (every truth value below is DECIDED BY CONSTRUCTION, never
measured from the image after the fact):

- Two vertical lines (gray 128, width 5 px so the centroid lands on an exact
  integer column) at x=100 and x=700, spanning rows [50, 650). Column span
  600 px assigned to 15.0 m gives an exact 40.0 px/m -- the ground truth for
  both ``wall_line_profiler --axis col`` and ``px_m_calibrator``.
- Two horizontal lines at y=150 and y=550, spanning columns [50, 750) --
  ground truth for ``wall_line_profiler --axis row`` and
  ``storey_line_profiler``. The four lines cross, so the connected-component
  detector sees them as one "plus" blob with bbox [50,50,750,650); that is
  documented, not fought.
- Two small separate rectangles, RECT_A=(900,750,920,765) and
  RECT_B=(960,750,980,765) (20x15, area 300 each), placed far outside the
  lines' bounding region (so their bboxes never touch it: gap >> the 2 px
  default ``merge_gap_px``) and sized so their row/column projection bump
  stays under the clean_vector_v1 prominence threshold of 0.04 (verified
  empirically before this file was written: row bump = 40/1200 = 0.033, col
  bump = 15/900 = 0.017) -- ground truth for ``window_cc_detector`` and the
  candidate geometry fed to ``overlay_logger``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.agent.execution.isolation import build_isolation_workspace

CASE_DIR = Path("case_tests/e2e_tests/sm21_anchor")

# ---------------------------------------------------------------------------
# Synthetic fixture geometry
# ---------------------------------------------------------------------------
SYNTH_NAME = "substrate_probe.png"
W, H = 1200, 900
GRAY = 128
LINE_HALF = 2  # line spans [c-2, c+3) = 5 px; centroid == c exactly

V_LINES = {"A": 100, "B": 700}
V_Y0, V_Y1 = 50, 650
H_LINES = {"A": 150, "B": 550}
H_X0, H_X1 = 50, 750

SPAN_X_PX = V_LINES["B"] - V_LINES["A"]  # 600
VALUE_X_M = 15.0
TRUE_PX_PER_M = SPAN_X_PX / VALUE_X_M  # 40.0

RECT_A = (900, 750, 920, 765)  # x0,y0,x1,y1 half-open; 20x15, area 300
RECT_B = (960, 750, 980, 765)  # 20x15, area 300; x-gap from RECT_A = 40 px

CROSS_BBOX = [50.0, 50.0, 750.0, 650.0]  # the four lines merged, by construction


def _synth_png_bytes() -> bytes:
    arr = np.full((H, W, 3), 255, dtype=np.uint8)
    for x in V_LINES.values():
        arr[V_Y0:V_Y1, x - LINE_HALF : x + LINE_HALF + 1, :] = GRAY
    for y in H_LINES.values():
        arr[y - LINE_HALF : y + LINE_HALF + 1, H_X0:H_X1, :] = GRAY
    for x0, y0, x1, y1 in (RECT_A, RECT_B):
        arr[y0:y1, x0:x1, :] = GRAY
    buf = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def staging(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real isolation staging (preview/unbound build) with the synthetic
    fixture image staged into ``case_data/`` -- the same pattern
    ``tests/test_f51_source_frame_roundtrip.py`` uses."""

    root = tmp_path_factory.mktemp("substrate_staging")
    manifest = build_isolation_workspace(CASE_DIR, staging_root=root / "staging")
    staging_root = manifest.staging_root
    (staging_root / "case_data" / SYNTH_NAME).write_bytes(_synth_png_bytes())
    return staging_root


@pytest.fixture(scope="module")
def doc_staging(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A separate staging for S-1b: the doc's own examples reference the
    case's real images (``case_data/1f_view.png``, ``case_data/South_view.png``),
    which a plain ``build_isolation_workspace`` call already stages."""

    root = tmp_path_factory.mktemp("substrate_doc_staging")
    manifest = build_isolation_workspace(CASE_DIR, staging_root=root / "staging")
    return manifest.staging_root


# ---------------------------------------------------------------------------
# Invocation helpers -- always the staged wrapper via subprocess, never an
# import of the toolbox functions.
# ---------------------------------------------------------------------------
_REQ_COUNTER = {"n": 0}


def _run_direct(staging_root: Path, *cli_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", *cli_args],
        cwd=staging_root, capture_output=True, text=True, check=False,
    )


def _stringify(args: dict) -> dict[str, str]:
    """Form B is always strings (dispatch table: "B 形态下一切都是字符串")."""

    out = {}
    for key, value in args.items():
        if isinstance(value, (list, dict)):
            out[key] = json.dumps(value, separators=(",", ":"))
        else:
            out[key] = str(value)
    return out


def _write_request(
    staging_root: Path, tool: str, args: dict, form: str, request_id: str = "r1"
) -> subprocess.CompletedProcess[str]:
    _REQ_COUNTER["n"] += 1
    name = f"gridA_{_REQ_COUNTER['n']:04d}.json"
    path = staging_root / "requests" / name
    if form == "A":
        path.write_text(json.dumps({"tool": tool, "args": args}), encoding="utf-8")
        flag = "--request"
    else:
        path.write_text(
            json.dumps({"requests": [{"id": request_id, "tool": tool, "args": args}]}),
            encoding="utf-8",
        )
        flag = "--batch"
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", flag, f"requests/{name}"],
        cwd=staging_root, capture_output=True, text=True, check=False,
    )


def _invoke(staging_root: Path, form: str, tool: str, args: dict) -> subprocess.CompletedProcess[str]:
    """``args`` always carries the JSON-native shape (form A/C's "natural
    write" style per dispatch §3.3); form B derives its all-string argv from
    the SAME dict via :func:`_stringify`, so a test never states the same
    fixture value twice in two different spellings."""

    if form == "B":
        cli: list[str] = ["--tool", tool]
        for key, value in _stringify(args).items():
            cli.extend([f"--{key.replace('_', '-')}", value])
        return _run_direct(staging_root, *cli)
    return _write_request(staging_root, tool, args, form)


def _read_sidecar(
    staging_root: Path, out_dir: str, image_stem: str = "substrate_probe", tool: str | None = None
) -> dict:
    """Read back the one sidecar a probe call wrote. ``tool`` disambiguates
    when several DIFFERENT tools share the same ``out_dir`` and ``sidecar_name
    auto`` numbering (the doc examples all literally say ``--out-dir out/cv``,
    so several tools' evidence coexists there -- each still gets its own
    ``NNN_<tool>.json`` name, never colliding, just not unique-by-directory)."""

    evidence_dir = staging_root / out_dir / "cv_evidence" / image_stem
    assert evidence_dir.is_dir(), f"no evidence directory written: {evidence_dir}"
    pattern = f"*_{tool}.json" if tool else "*.json"
    candidates = [p for p in evidence_dir.glob(pattern) if not p.name.endswith("_overlay.json")]
    assert len(candidates) == 1, (out_dir, tool, sorted(p.name for p in evidence_dir.iterdir()))
    return json.loads(candidates[0].read_text(encoding="utf-8"))


FORMS = ["B", "A", "C"]


# ===========================================================================
# S-1 main grid: 6 tools x 3 forms = 18 cells, minimal viable args, pass +
# correct numbers. Each parametrized case below is one grid cell.
# ===========================================================================


@pytest.mark.parametrize("form", FORMS)
def test_grid_wall_line_profiler_col(staging: Path, form: str) -> None:
    out_dir = f"out/grid_wlp_{form}"
    proc = _invoke(staging, form, "wall_line_profiler",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, "axis": "col"})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    positions = sorted(r["position_px"] for r in sidecar["results"])
    assert len(sidecar["results"]) == 2
    assert positions[0] == pytest.approx(V_LINES["A"], abs=0.01)
    assert positions[1] == pytest.approx(V_LINES["B"], abs=0.01)
    assert all(r["axis"] == "col" for r in sidecar["results"])


@pytest.mark.parametrize("form", FORMS)
def test_grid_storey_line_profiler(staging: Path, form: str) -> None:
    out_dir = f"out/grid_slp_{form}"
    proc = _invoke(staging, form, "storey_line_profiler",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    positions = sorted(r["position_px"] for r in sidecar["results"])
    assert len(sidecar["results"]) == 2
    assert positions[0] == pytest.approx(H_LINES["A"], abs=0.01)
    assert positions[1] == pytest.approx(H_LINES["B"], abs=0.01)
    assert all(r["axis"] == "row" for r in sidecar["results"])


@pytest.mark.parametrize("form", FORMS)
def test_grid_px_m_calibrator(staging: Path, form: str) -> None:
    out_dir = f"out/grid_calib_{form}"
    anchors = [{"axis": "x", "px_a": V_LINES["A"], "px_b": V_LINES["B"], "value_m": VALUE_X_M}]
    proc = _invoke(staging, form, "px_m_calibrator",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, "anchors_json": anchors})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    result = sidecar["results"][0]
    assert result["px_per_m"] == pytest.approx(TRUE_PX_PER_M, rel=0.005)
    assert result["axis_px_per_m"] == {"x": pytest.approx(TRUE_PX_PER_M, rel=0.005)}


@pytest.mark.parametrize("form", FORMS)
def test_grid_window_cc_detector(staging: Path, form: str) -> None:
    out_dir = f"out/grid_wcc_{form}"
    proc = _invoke(staging, form, "window_cc_detector",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    boxes = {tuple(r["bbox_px"]): r["area_px"] for r in sidecar["results"]}
    # The two known rectangles must be present with their exact bbox and area
    # (dispatch §4's ambiguity guidance: don't force an exact-count match when
    # a fixture can honestly produce extra candidates -- assert presence of
    # the known ones, not absence of everything else).
    assert boxes.get(tuple(float(v) for v in RECT_A)) == 300
    assert boxes.get(tuple(float(v) for v in RECT_B)) == 300
    # The third candidate (the four lines merged into one "plus" blob) is
    # itself a deterministic consequence of this fixture's construction, not
    # an open question -- pin it too so a real regression in the merge step
    # cannot hide behind "well, extra candidates are expected anyway".
    assert len(sidecar["results"]) == 3
    assert boxes.get(tuple(CROSS_BBOX)) == 12900


@pytest.mark.parametrize("form", FORMS)
def test_grid_crop_zoom(staging: Path, form: str) -> None:
    out_dir = f"out/grid_crop_{form}"
    # bbox is written as the STRING form here (see F-52 below, now fixed, for
    # the native-array form as a separate cell).
    proc = _invoke(staging, form, "crop_zoom",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, "bbox": "880,730,1000,790"})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    result = sidecar["results"][0]
    assert result["crop_size_px"] == [120, 60]
    assert sidecar["source_image"]["width_px"] == W
    assert sidecar["source_image"]["height_px"] == H


@pytest.mark.parametrize("form", FORMS)
def test_grid_overlay_logger(staging: Path, form: str) -> None:
    out_dir = f"out/grid_overlay_{form}"
    candidates = [
        {
            "candidate_id": "c1",
            "status": "accepted",
            "reason": "rectA",
            "geometry": {"kind": "bbox", "bbox_px": list(RECT_A)},
        }
    ]
    proc = _invoke(staging, form, "overlay_logger",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, "candidates_json": candidates})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    decisions = sidecar["results"][0]["decisions"]
    assert len(decisions) == 1
    assert decisions[0]["candidate_id"] == "c1"
    assert decisions[0]["status"] == "accepted"
    assert decisions[0]["reason"] == "rectA"
    overlay_path = Path(sidecar["overlay_path"])
    assert overlay_path.is_file(), "overlay_logger must actually produce the overlay PNG"


# ===========================================================================
# S-1b: every ```bash example in skills/intake_pipeline/0_reading/cv_toolbox.md,
# run byte-for-byte (extracted by hand from the doc immediately before this
# file was written) through the real shell in a real staging, exactly as a
# reading agent copy-pasting the doc into a Bash tool call would experience
# it. F-45's shape was "the doc's own examples don't survive contact with the
# sandbox" -- this is the one grid slice that stares directly at that shape.
# ===========================================================================

DOC_1_WALL_LINE_PROFILER = (
    "python tools/run_cv_probe.py --tool wall_line_profiler \\\n"
    "  --image case_data/1f_view.png \\\n"
    "  --out-dir out/cv \\\n"
    "  --axis col"
)
DOC_2_CROP_ZOOM = (
    "python tools/run_cv_probe.py --tool crop_zoom \\\n"
    "  --image case_data/1f_view.png \\\n"
    "  --out-dir out/cv \\\n"
    "  --bbox 120,80,620,460 \\\n"
    "  --scale 2"
)
DOC_3_PX_M_CALIBRATOR = (
    "python tools/run_cv_probe.py --tool px_m_calibrator \\\n"
    "  --image case_data/1f_view.png \\\n"
    "  --out-dir out/cv \\\n"
    '  --anchors-json \'[{"axis":"x","px_a":100,"px_b":700,"value_m":15.0,'
    '"dimension_ref":"overall_width"}]\''
)
DOC_4_WINDOW_CC_DETECTOR = (
    "python tools/run_cv_probe.py --tool window_cc_detector \\\n"
    "  --image case_data/South_view.png \\\n"
    "  --out-dir out/cv \\\n"
    "  --min-area 30"
)
DOC_5_BATCH_EXAMPLE = "python tools/run_cv_probe.py --batch requests/sweep.json"
DOC_6_PYTHON_DASH_C = (
    "python -c 'import numpy as np; from PIL import Image; "
    'print(np.array(Image.open("case_data/1f_view.png").convert("L")).shape)\''
)
DOC_7_PYTHON_SCRIPT_PLACEHOLDER = "python out/measure_bay_spacing.py"


def _run_doc_block(staging_root: Path, command: str) -> subprocess.CompletedProcess[str]:
    """Run a doc code block through a real shell (``shell=True``) so
    line-continuation backslashes -- and any shell metacharacter the doc text
    happens to contain -- are interpreted exactly as they would be if a
    reading agent pasted the block into the Bash tool."""

    return subprocess.run(
        command, shell=True, cwd=staging_root, capture_output=True, text=True, check=False,
    )


def test_doc_example_wall_line_profiler_runs(doc_staging: Path) -> None:
    proc = _run_doc_block(doc_staging, DOC_1_WALL_LINE_PROFILER)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)


def test_doc_example_crop_zoom_runs_and_crops_correctly(doc_staging: Path) -> None:
    proc = _run_doc_block(doc_staging, DOC_2_CROP_ZOOM)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(doc_staging, "out/cv", image_stem="1f_view", tool="crop_zoom")
    result = sidecar["results"][0]
    # bbox=120,80,620,460 scale=2 -> (620-120)*2=1000, (460-80)*2=760
    assert result["crop_size_px"] == [1000, 760]


def test_doc_example_px_m_calibrator_runs_and_computes_the_documented_scale(doc_staging: Path) -> None:
    """This is the literal doc example F-49 named as broken end to end
    ("文档与 wrapper 自带 usage 写的两种形态全都跑不通"). It must not just
    exit 0 -- the number it produces from the doc's own anchor values
    (px_a=100, px_b=700, value_m=15.0) must be the arithmetically correct
    40.0 px/m, or a "fixed" wrapper that merely stopped crashing without
    computing the right thing would still pass a returncode-only check."""

    proc = _run_doc_block(doc_staging, DOC_3_PX_M_CALIBRATOR)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(doc_staging, "out/cv", image_stem="1f_view", tool="px_m_calibrator")
    result = sidecar["results"][0]
    assert result["px_per_m"] == pytest.approx(40.0, rel=0.005)


def test_doc_example_window_cc_detector_runs(doc_staging: Path) -> None:
    proc = _run_doc_block(doc_staging, DOC_4_WINDOW_CC_DETECTOR)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(doc_staging, "out/cv", image_stem="South_view")
    assert len(sidecar["results"]) > 0


def test_doc_example_batch_placeholder_is_not_shell_safe(doc_staging: Path) -> None:
    """F-53 FIXED (2026-08-16 substrate fix batch II): was xfail(strict=True)
    -- the doc's OLD --batch example used the literal placeholder syntax
    'requests/<name>.json'. Pasted verbatim into a real shell, that is not a
    harmless literal: '<' and '>' are shell redirection operators, so the
    shell read this as 'redirect stdin from a file named name, redirect
    stdout to a file named .json' and the wrapper was invoked with only
    '--batch requests/'. The observed failure ('cannot open name: No such
    file') gave no hint that a placeholder had been copied literally. Fixed
    by naming a concrete file (requests/sweep.json, matching
    run_cv_probe.py's own --help text) instead of a bracketed placeholder --
    doc measurement text: create that file with a minimal valid batch
    request first, matching what a reading agent would actually do before
    running this exact line. Full three-way behavioral verification
    (including a doc-content-scanning sweep of every other code block, and a
    neuter that swaps the real doc file back to its pre-fix text) lives in
    tests/test_substrate_fix_tools.py."""

    request = {
        "requests": [
            {
                "id": "doc5",
                "tool": "wall_line_profiler",
                "args": {"image": "case_data/1f_view.png", "out_dir": "out/doc5_batch", "axis": "col"},
            }
        ]
    }
    (doc_staging / "requests" / "sweep.json").write_text(json.dumps(request), encoding="utf-8")
    proc = _run_doc_block(doc_staging, DOC_5_BATCH_EXAMPLE)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "cannot open name" not in proc.stderr
    out = json.loads(proc.stdout)
    assert out["request_count"] == 1


def test_doc_example_python_dash_c_executes_in_staging(doc_staging: Path) -> None:
    """Environment sanity only: this block never touches tools/run_cv_probe.py
    at all, so it says nothing about the wrapper. It is included because the
    dispatch asked for every ```bash block in the doc to be run and recorded;
    whether Bash-tool calls of this shape are ALLOWED is guard.py's policy
    layer, which is Lane B's territory, not tested here."""

    proc = _run_doc_block(doc_staging, DOC_6_PYTHON_DASH_C)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert proc.stdout.strip() == "(1345, 2133)"


def test_doc_example_script_placeholder_is_illustrative_not_literal(doc_staging: Path) -> None:
    """``measure_bay_spacing.py`` is explicitly framed by the doc as a script
    the READER writes first ("write it, then run it") -- it is not expected
    to exist on a fresh staging. This pins that expectation as a real,
    checked fact instead of leaving it as an unverified reading."""

    proc = _run_doc_block(doc_staging, DOC_7_PYTHON_SCRIPT_PLACEHOLDER)
    assert proc.returncode != 0
    assert "No such file or directory" in proc.stderr


# ===========================================================================
# S-2 parameter-form sweep (priority subset -- see grid_A.md for the full
# accounting of what was and was not covered against the dispatch's 51-cell
# table).
# ===========================================================================


def test_s2_bbox_native_json_array_form_a(staging: Path) -> None:
    """F-52 FIXED (2026-08-16 substrate fix batch II): was xfail(strict=True)
    -- 'bbox' is not in run_cv_probe.JSON_OR_PATH_KEYS, so a native JSON
    array (the natural way to write a bbox: [x0,y0,x1,y1]) fell through to
    the generic 'isinstance(value, (dict, list))' branch in
    _request_to_argv, which json.dumps()'d it into a single CLI token
    '[x0,y0,x1,y1]'; cv_probe._bbox then split that token on commas and
    tried float('[880') first, raising exit code 2. Same family as F-49 (a
    parameter's natural JSON spelling not surviving the wrapper), on the one
    parameter the dispatch flagged as an unverified candidate. Fixed at the
    single point every invocation form converges on: cv_probe.py's own
    --bbox argparse type now also accepts the bracketed JSON spelling, not
    just the comma-separated string. Full three-way behavioral verification
    (positive/negative/neuter) lives in tests/test_substrate_fix_tools.py;
    this is the exact case the substrate sweep pinned as broken, now pinned
    as fixed in place so it stays a real regression lock."""

    out_dir = "out/s2_bbox_arr_a"
    proc = _invoke(staging, "A", "crop_zoom",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, "bbox": [880, 730, 1000, 790]})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    assert sidecar["results"][0]["crop_size_px"] == [120, 60]


def test_s2_bbox_native_json_array_form_c(staging: Path) -> None:
    """F-52 FIXED, batch form: same failure/fix as the --request form above."""

    out_dir = "out/s2_bbox_arr_c"
    proc = _invoke(staging, "C", "crop_zoom",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, "bbox": [880, 730, 1000, 790]})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    assert sidecar["results"][0]["crop_size_px"] == [120, 60]


def test_s2_bbox_string_form_a_is_the_working_spelling(staging: Path) -> None:
    """The contrast case for F-52: the STRING spelling of the same bbox value
    (dispatch's "A/C 形态·字符串写法" column) is unaffected -- this is what
    makes F-52 a wrapper gap rather than crop_zoom being broken outright."""

    out_dir = "out/s2_bbox_str_a"
    proc = _invoke(staging, "A", "crop_zoom",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, "bbox": "880,730,1000,790"})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    assert sidecar["results"][0]["crop_size_px"] == [120, 60]


def test_s2_anchors_json_as_file_path_string_form_a(staging: Path) -> None:
    """dispatch's third anchors_json column: a path to a JSON file, instead of
    an inline array or an inline JSON string."""

    anchors_path = staging / "requests" / "s2_anchors_payload.json"
    anchors_path.write_text(
        json.dumps([{"axis": "x", "px_a": V_LINES["A"], "px_b": V_LINES["B"], "value_m": VALUE_X_M}]),
        encoding="utf-8",
    )
    out_dir = "out/s2_anchors_path_a"
    proc = _invoke(staging, "A", "px_m_calibrator",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir,
                     "anchors_json": "requests/s2_anchors_payload.json"})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    assert sidecar["results"][0]["px_per_m"] == pytest.approx(TRUE_PX_PER_M, rel=0.005)


def test_s2_candidates_json_as_file_path_string_form_a(staging: Path) -> None:
    candidates_path = staging / "requests" / "s2_candidates_payload.json"
    candidates_path.write_text(
        json.dumps([{"candidate_id": "c1", "status": "accepted", "reason": "rectA",
                      "geometry": {"kind": "bbox", "bbox_px": list(RECT_A)}}]),
        encoding="utf-8",
    )
    out_dir = "out/s2_candidates_path_a"
    proc = _invoke(staging, "A", "overlay_logger",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir,
                     "candidates_json": "requests/s2_candidates_payload.json"})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    assert sidecar["results"][0]["decisions"][0]["candidate_id"] == "c1"


@pytest.mark.parametrize(
    "form,scale_value,out_suffix",
    [("A", 2, "int"), ("A", 2.0, "float"), ("A", "2", "string"), ("B", "2", "b_string")],
)
def test_s2_scale_forms_agree(staging: Path, form: str, scale_value, out_suffix: str) -> None:
    """int / float / string spellings of ``scale`` (native JSON in A form,
    and the always-string B form) must all resolve to the identical crop."""

    out_dir = f"out/s2_scale_{out_suffix}"
    proc = _invoke(staging, form, "crop_zoom",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir,
                     "bbox": "880,730,1000,790", "scale": scale_value})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    # bbox is 120x60; scale=2 -> 240x120, regardless of how "2" was spelled.
    assert sidecar["results"][0]["crop_size_px"] == [240, 120]


def test_s2_window_filter_params_native_and_string_forms(staging: Path) -> None:
    """All ten window_cc_detector filter parameters at once, in both native
    JSON numeric form and string form (form A) -- the "everything else" path
    in run_cv_probe._request_to_argv (str(value), uniformly) rather than a
    per-parameter special case, so one representative pair stands in for all
    ten without re-deriving the same code path ten times."""

    native = {
        "image": f"case_data/{SYNTH_NAME}", "out_dir": "out/s2_wfilter_native",
        "min_area": 100, "min_width": 10.0, "min_height": 5.0, "max_width": 500.0,
        "max_height": 500.0, "min_aspect": 0.1, "max_aspect": 20.0,
        "merge_gap": 5.0, "merge_overlap_ratio": 0.5, "merge_iou": 0.3,
    }
    proc_native = _invoke(staging, "A", "window_cc_detector", native)
    assert proc_native.returncode == 0, (proc_native.stdout, proc_native.stderr)

    stringy = dict(native)
    stringy["out_dir"] = "out/s2_wfilter_string"
    for key in list(stringy):
        if key not in ("image", "out_dir"):
            stringy[key] = str(stringy[key])
    proc_string = _invoke(staging, "A", "window_cc_detector", stringy)
    assert proc_string.returncode == 0, (proc_string.stdout, proc_string.stderr)

    both_results = [
        _read_sidecar(staging, native["out_dir"])["results"],
        _read_sidecar(staging, stringy["out_dir"])["results"],
    ]
    assert both_results[0] == both_results[1]


# ===========================================================================
# S-3 coordinate systems.
# ===========================================================================


@pytest.mark.parametrize(
    "tool,args_extra",
    [
        ("crop_zoom", {"bbox": "880,730,1000,790"}),
        ("wall_line_profiler", {"axis": "col"}),
        ("storey_line_profiler", {}),
        ("px_m_calibrator", {"anchors_json": [{"axis": "x", "px_a": 100, "px_b": 700, "value_m": 15.0}]}),
        ("window_cc_detector", {}),
        ("overlay_logger", {"candidates_json": [{"candidate_id": "c1", "status": "accepted", "reason": "r",
                                                   "geometry": {"kind": "bbox", "bbox_px": list(RECT_A)}}]}),
    ],
)
def test_s3_source_size_reported_by_every_tool(staging: Path, tool: str, args_extra: dict) -> None:
    """§3.4(1): all six tools' sidecars must report the SOURCE image's true
    pixel size, regardless of what each tool otherwise does with the image."""

    out_dir = f"out/s3_size_{tool}"
    args = {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, **args_extra}
    proc = _invoke(staging, "B", tool, args)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    assert sidecar["source_image"]["width_px"] == W
    assert sidecar["source_image"]["height_px"] == H


def test_s3_crop_scale_roundtrip_within_one_pixel(staging: Path) -> None:
    """§3.4(2): crop_zoom with --bbox + --scale must still report the SOURCE
    size (checked above); this test additionally proves the crop chain
    itself is invertible -- a detector run against the very same crop+scale
    window must recover the known source-space line positions to within 1 px,
    using the fixture's already-known-true vertical line locations."""

    out_dir = "out/s3_roundtrip"
    bbox = "50,50,750,650"
    proc = _invoke(staging, "B", "wall_line_profiler",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir,
                     "axis": "col", "bbox": bbox, "scale": "3"})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    # crop_zoom itself must still report the SOURCE size even though this
    # cell restricts analysis to a sub-region.
    assert sidecar["source_image"]["width_px"] == W
    assert sidecar["source_image"]["height_px"] == H
    positions = sorted(r["position_px"] for r in sidecar["results"])
    assert len(positions) == 2
    assert positions[0] == pytest.approx(V_LINES["A"], abs=1.0)
    assert positions[1] == pytest.approx(V_LINES["B"], abs=1.0)


@pytest.mark.parametrize(
    "tool,args_extra",
    [
        ("crop_zoom", {"bbox": "880,730,1000,790"}),
        ("wall_line_profiler", {"axis": "col", "bbox": "50,50,750,650", "scale": "3"}),
        ("overlay_logger", {"candidates_json": [{"candidate_id": "c1", "status": "accepted", "reason": "r",
                                                   "geometry": {"kind": "bbox", "bbox_px": list(RECT_A)}}]}),
    ],
)
def test_s3_overlay_png_is_always_in_the_source_frame(staging: Path, tool: str, args_extra: dict) -> None:
    """§3.4(3), the open question the dispatch explicitly did not presume an
    answer to: measured here, not assumed. Every overlay PNG this wrapper
    produces is drawn against the FULL SOURCE image (cv_probe.py's overlay
    calls all pass ``args.image``, never the crop), so its pixel size equals
    ``source_image.width_px/height_px`` regardless of any --bbox/--scale
    restriction on the underlying detection. (crop_zoom additionally writes
    a second PNG, ``..._crop.png``, which IS in the crop-local frame -- that
    one is not the "overlay" and is out of scope for this question.)"""

    out_dir = f"out/s3_overlay_frame_{tool}"
    args = {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, **args_extra}
    proc = _invoke(staging, "B", tool, args)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    with Image.open(sidecar["overlay_path"]) as overlay_img:
        assert overlay_img.size == (W, H)


def test_s3_crop_png_is_in_the_crop_local_frame_not_source(staging: Path) -> None:
    """The counterpart fact to the overlay test above, so the "which frame"
    answer for crop_zoom's TWO PNG outputs is fully pinned rather than half
    of it being left to infer: ``..._crop.png`` (distinct from
    ``..._overlay.png``) is sized to the crop, not the source."""

    out_dir = "out/s3_crop_local_frame"
    proc = _invoke(staging, "B", "crop_zoom",
                    {"image": f"case_data/{SYNTH_NAME}", "out_dir": out_dir, "bbox": "880,730,1000,790"})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir)
    evidence_dir = staging / out_dir / "cv_evidence" / "substrate_probe"
    crop_pngs = list(evidence_dir.glob("*_crop.png"))
    assert len(crop_pngs) == 1
    with Image.open(crop_pngs[0]) as crop_img:
        assert crop_img.size == (120, 60)  # the CROP size, not (1200, 900)
        assert crop_img.size == tuple(sidecar["results"][0]["crop_size_px"])


# ===========================================================================
# F-54: run_cv_probe.py's own main() has no top-level exception handling.
# ===========================================================================


def test_s2_wrapper_validation_errors_are_clean_not_raw_tracebacks(staging: Path) -> None:
    """F-54 FIXED (2026-08-16 substrate fix batch II): was xfail(strict=True)
    -- run_cv_probe.main() did not wrap _direct_to_request / _request_to_argv
    / the --request/--batch file reads in any try/except, unlike
    cv_probe.py's own argparse-based parser.error() paths (clean usage text,
    exit code 2). A ValueError raised inside the wrapper's own validation
    propagated as a raw, uncaught Python traceback (exit code 1) instead.
    Not reachable through the guarded product path (guard.py's own
    PreToolUse validation catches these same exceptions before the wrapper
    ever runs), but real and reproducible against the wrapper's own real
    entry point, which is exactly what this file's methodology exercises
    directly. Fixed by wrapping main()'s body in try/except (ValueError,
    OSError) -- argparse's own SystemExit-based paths are untouched (
    SystemExit is not an Exception subclass). NOTE: this test was NOT
    listed among the dispatch's named 3 xfail-flips (two F-52 + one F-53) --
    fixing F-54 flips this 4th one too, since it directly exercises the
    dispatch's own repro command. Full three-way behavioral verification
    lives in tests/test_substrate_fix_tools.py."""

    # A malformed direct-form call (a bare token where --key value is
    # required) raises ValueError("probe parameter name is empty") deep in
    # _direct_to_request with no surrounding handler in main().
    proc = _run_direct(staging, "--tool", "wall_line_profiler", "--")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr
    assert "probe parameter name is empty" in proc.stderr
