"""C1 (cross-axis calibration disagreement -- legal exit, not a raise) lock,
ported into the suite from a verified scratchpad prototype (``lock_c1.py``,
2026-08-16/17 -- see AI_agent/logs/reviews/execution/
2026-08-17_707_prereq_locks_execution_log.md for the porting record).

Before this fix, ``px_m_calibrator`` raised ``ValueError("cross-axis
calibration disagreement: ...")`` -- before ever blending ``px_per_m`` --
whenever the independently-fitted x/y axis scales disagreed by more than
``calibration_max_axis_relative_deviation`` (0.3%). A hard raise with no
escape had an observed real-world consequence (F-34, see
AI_agent/logs/experiments/2026-08-16_707_repro/
behavioral_change_inventory.md §C1): the reading agent abandoned pixel
calibration entirely and fell back to eyeballing meters in response to the
failure, which is strictly worse than a flagged, low-confidence number. Same
family judgment this project has hit before: a rule with no legal exit
breeds an invented one (立规则不给合法出口 ⇒ 模型自己发明出口).

After this fix, the disagreement is still detected against the SAME 0.3%
limit and is still surfaced loudly -- ``axis_calibration_disagreement=True``,
a ``warnings[]`` entry of type ``cross_axis_disagreement`` carrying
actionable next-step guidance, and ``metric_confidence`` forced to
``"low"`` -- but ``px_m_calibrator`` ALWAYS returns a usable ``px_per_m``
instead of throwing it away. The gate is not removed, only reshaped from a
dead end into a legal exit.

Real entry point discipline: every test below goes through the REAL
``build_isolation_workspace`` + a REAL ``subprocess`` against the staged
``tools/run_cv_probe.py`` -- never a direct import of ``px_m_calibrator``. A
library-layer, direct-import lock of the same behavior already exists at
``tests/test_cv_toolbox.py::
test_px_m_calibrator_flags_cross_axis_disagreement_with_a_legal_exit_not_a_raise``
(recently renamed from ``..._rejects_cross_axis_anisotropy_before_blending``,
which asserted the now-superseded raise); this file exists in addition to
that one because a library-layer test alone would not have caught F-49's
class of defect (a parameter/behavior that works when a toolbox function is
called directly in-process but not through the sandboxed wrapper) -- see
that file's module docstring and ``tests/test_substrate_fix_tools.py``'s for
the full rationale.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent.execution.isolation import build_isolation_workspace

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = Path("case_tests/e2e_tests/sm21_anchor")
REAL_IMAGE = "case_data/1f_view.png"  # 2133x1345 (W x H), staged by every build

# The REAL, tracked source the neuter test targets -- read-only from here on
# (only a THROWAWAY staged COPY under a per-test tmp_path is ever
# overwritten -- see _neuter_into_fresh_staging).
TOOLS_REAL = REPO_ROOT / "src" / "agent" / "reading" / "cv_toolbox" / "tools.py"
TOOLS_STAGED_REL = "src/agent/reading/cv_toolbox/tools.py"
TOOLS_PRE_FIX_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "cross_axis_exit" / "tools_pre_fix.py"

# Same disagreeing/agreeing anchor pairs as
# tests/test_cv_toolbox.py::
# test_px_m_calibrator_flags_cross_axis_disagreement_with_a_legal_exit_not_a_raise
# -- chosen so the library-layer lock and this real-entry-point lock are
# directly comparable against the same known fixture.
DISAGREEING_ANCHORS = [
    {"axis": "x", "px_a": 245, "px_b": 620, "value_m": 10.0},
    {"axis": "y", "px_a": 54, "px_b": 872, "value_m": 20.0},
]
AGREEING_ANCHORS = [
    {"axis": "x", "px_a": 247.5, "px_b": 611.5, "value_m": 10.0},
    {"axis": "y", "px_a": 150.5, "px_b": 877.5, "value_m": 20.0},
]


@pytest.fixture(scope="module")
def staging(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real isolation staging (preview/unbound build), shared read-mostly
    across the positive/negative tests in this file -- each test writes to
    its own ``out/<unique>`` name so nothing collides. The neuter test builds
    its OWN fresh staging instead (see ``_neuter_into_fresh_staging``)."""

    root = tmp_path_factory.mktemp("c1_staging")
    manifest = build_isolation_workspace(CASE_DIR, staging_root=root / "staging")
    return manifest.staging_root


_REQ_COUNTER = {"n": 0}


def _run_calibrator(
    staging_root: Path, anchors: list[dict], *, label: str
) -> tuple[subprocess.CompletedProcess[str], str]:
    _REQ_COUNTER["n"] += 1
    out_dir = f"out/c1_{label}_{_REQ_COUNTER['n']:04d}"
    proc = subprocess.run(
        [sys.executable, "tools/run_cv_probe.py",
         "--tool", "px_m_calibrator", "--image", REAL_IMAGE,
         "--out-dir", out_dir,
         "--anchors-json", json.dumps(anchors, separators=(",", ":"))],
        cwd=staging_root, capture_output=True, text=True,
    )
    return proc, out_dir


def _read_sidecar(staging_root: Path, out_dir: str, image_stem: str, tool: str) -> dict:
    evidence_dir = staging_root / out_dir / "cv_evidence" / image_stem
    assert evidence_dir.is_dir(), f"no evidence directory written: {evidence_dir}"
    candidates = [
        p for p in evidence_dir.glob(f"*_{tool}.json") if not p.name.endswith("_overlay.json")
    ]
    assert len(candidates) == 1, sorted(p.name for p in evidence_dir.iterdir())
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def _neuter_into_fresh_staging(tmp_path: Path) -> Path:
    """Mirrors ``tests/test_substrate_fix_tools.py::_neuter_into_fresh_staging``
    (same shape, narrowed to this file's single target file) -- see that
    function's docstring for the full 2026-08-17 cross-review M-1 rationale
    this shape exists to satisfy: build a FRESH staging from the repo's
    CURRENT (fixed) source tree, then overwrite ONLY the staged COPY of
    ``tools.py`` with the pre-C1-fix fixture's content, before any subprocess
    runs against that staging. Never writes to ``TOOLS_REAL`` or any other
    repository file -- so no other parallel ``pytest -n auto`` worker
    building its own staging (or importing
    ``src/agent/reading/cv_toolbox/tools.py`` directly) can ever observe a
    broken intermediate state.
    """

    real_content = TOOLS_REAL.read_text(encoding="utf-8")
    backup_content = TOOLS_PRE_FIX_FIXTURE.read_text(encoding="utf-8")
    assert real_content != backup_content, (
        f"{TOOLS_REAL} is byte-identical to its pre-fix fixture {TOOLS_PRE_FIX_FIXTURE} -- "
        "this neuter would be a no-op and prove nothing about the lock"
    )
    manifest = build_isolation_workspace(CASE_DIR, staging_root=tmp_path / "neuter_staging")
    staging_root = manifest.staging_root
    target = staging_root / TOOLS_STAGED_REL
    assert target.is_file(), f"expected the build to have staged a copy at {target}"
    # F-55 strips the write bit from every staged file outside out//requests/
    # once the build completes -- restoring it first makes this swap correct
    # independent of whether this container happens to bypass that check
    # (root), and costs nothing since `target` lives inside a per-test
    # throwaway tmp_path discarded with the rest of the staging tree anyway.
    target.chmod(stat.S_IMODE(target.stat().st_mode) | stat.S_IWUSR)
    target.write_text(backup_content, encoding="utf-8")
    return staging_root


# ===========================================================================
# Positive: the disagreeing-anchor call that used to crash the real CLI now
# gets a legal exit -- flagged, warned, confidence-lowered, but a usable
# number.
# ===========================================================================


def test_disagreeing_anchors_get_a_legal_exit_not_a_crash(staging: Path) -> None:
    proc, out_dir = _run_calibrator(staging, DISAGREEING_ANCHORS, label="disagree")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)

    result = _read_sidecar(staging, out_dir, "1f_view", "px_m_calibrator")["results"][0]
    assert result["axis_calibration_disagreement"] is True
    assert result["metric"]["confidence"] == "low", result["metric"]["confidence"]

    warn_types = [w["type"] for w in result["warnings"]]
    assert "cross_axis_disagreement" in warn_types, warn_types
    cross_warning = next(w for w in result["warnings"] if w["type"] == "cross_axis_disagreement")
    assert "re-crop and re-measure" in cross_warning["guidance"], cross_warning["guidance"]
    assert "recalibrate" in cross_warning["guidance"], cross_warning["guidance"]

    assert isinstance(result["px_per_m"], (int, float)) and result["px_per_m"] > 0, result["px_per_m"]
    assert set(result["axis_px_per_m"]) == {"x", "y"}, result["axis_px_per_m"]


# ===========================================================================
# Negative-of-the-negative: the ORIGINAL non-disagreeing case is completely
# unaffected by this change -- same shape as before (high confidence, no
# warnings, flag False).
# ===========================================================================


def test_agreeing_anchors_are_unaffected_by_the_cross_axis_exit(staging: Path) -> None:
    proc, out_dir = _run_calibrator(staging, AGREEING_ANCHORS, label="agree")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)

    result = _read_sidecar(staging, out_dir, "1f_view", "px_m_calibrator")["results"][0]
    assert result["axis_calibration_disagreement"] is False
    assert result["metric"]["confidence"] == "high", result["metric"]["confidence"]
    assert result["warnings"] == [], result["warnings"]


# ===========================================================================
# NEUTER: revert the staged copy of tools.py to its pre-C1-fix content and
# confirm the original scenario fails again -- the ORIGINAL way.
# ===========================================================================


def test_neuter_reverting_the_legal_exit_reproduces_the_original_raise(tmp_path: Path) -> None:
    """Reverting ONLY ``tools.py`` restores the pre-C1 ``raise
    ValueError("cross-axis calibration disagreement: ...")``, but that
    exception still passes through ``src/agent/execution/isolation_templates/
    run_cv_probe.py``'s F-54 backstop (2026-08-16, a different, independent,
    UN-neutered fix in a different file: the whole tool-execution call is
    wrapped in ``try/except (ValueError, OSError)``, and ``ValueError`` is
    exactly one of the two caught types) -- so the pre-C1 behavior that
    resurfaces here is a CLEAN exit code 2 carrying the raise's original
    message text, not a raw traceback. This is the opposite contrast to
    ``tests/test_substrate_fix_tools.py::
    test_f58_neuter_reverting_the_shape_check_reproduces_the_bare_attribute_error``,
    where the reverted exception type (``AttributeError``) is NOT one of
    F-54's caught types and a raw traceback resurfaces instead -- together
    the two neuter tests demonstrate F-54's backstop is exception-TYPE
    selective, not a blanket catch-all, which is exactly what F-54's own
    fix intended (argparse's SystemExit paths must stay untouched too).
    Confirmed empirically while writing this test, not merely reasoned from
    reading the source.
    """

    neuter_staging = _neuter_into_fresh_staging(tmp_path)
    proc, out_dir = _run_calibrator(neuter_staging, DISAGREEING_ANCHORS, label="neuter")

    assert proc.returncode == 2, (
        "expected the pre-C1 raise, caught by F-54's still-active backstop, "
        f"to resurface as a clean exit 2: {proc.stdout!r} {proc.stderr!r}"
    )
    assert "Traceback" not in proc.stderr, proc.stderr
    assert "cross-axis calibration disagreement" in proc.stderr, proc.stderr
    # And the legal-exit artifacts the positive test relies on must be ABSENT
    # -- no sidecar was ever written, because the raise fires before
    # px_m_calibrator returns anything.
    evidence_dir = neuter_staging / out_dir / "cv_evidence" / "1f_view"
    assert not evidence_dir.exists() or not list(evidence_dir.glob("*_px_m_calibrator.json")), (
        "did not expect a sidecar to exist -- the pre-fix raise must fire before any result is written"
    )
