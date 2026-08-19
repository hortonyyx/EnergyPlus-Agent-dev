"""F-51 (single-frame staging resize) lock, ported into the suite from a
verified scratchpad prototype (``lock_f51.py``, 2026-08-16/17 -- see
AI_agent/logs/reviews/execution/2026-08-17_707_prereq_locks_execution_log.md
for the porting record).

Why this exists (AI_agent/logs/experiments/2026-08-16_707_repro/): the Claude
vision API silently downsamples an oversized image before the model ever sees
it (Anthropic docs, "How Claude resizes and pads images"). Before this fix,
the reading agent's self-reported pixel coordinates lived in the POST-resize
frame the model actually saw, while ``cv_probe`` (and the sidecar's
``source_image.width_px/height_px`` echo) read the ORIGINAL file on disk --
mismatched, those two frames disagree in a way that is self-consistent (so it
does not trip the cross-axis calibration check -- see
``tests/test_cross_axis_exit.py``) yet globally wrong. The fix
(``src/agent/execution/vision_resize.py``, wired into
``src/agent/execution/isolation.py::_copy_case_data_image``) resizes the
staged ``case_data/`` copy to the size the vision API would have produced
anyway, per Anthropic's own documented recommendation, so all three readers
(model, disk, ``cv_probe``) see the identical frame by construction.

Real entry point discipline: every staging-dependent test below goes through
the REAL ``build_isolation_workspace`` and, where a tool result is checked, a
REAL ``subprocess`` against the staged ``tools/run_cv_probe.py`` -- never a
direct import of a toolbox function. This project has already been bitten
once by "library-layer tests all green" not transferring to the sandboxed
wrapper shape (F-49 lived unnoticed for five weeks precisely because of that
gap) -- the same discipline ``tests/test_substrate_fix_tools.py`` and
``tests/test_substrate_sweep_tools.py`` already apply.

Anchor case: ``case_tests/e2e_tests/sm21_anchor`` (git-tracked, in-repo --
never anything under a gitignored ``backup/`` path). Ground-truth pixel sizes
below are hardcoded from this specific anchor's real source images (not
solely re-derived from the algorithm under test -- see
``PLAN_VIEW_TARGETS``'s docstring for why both a hardcoded and a computed
comparison are kept).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

import src.agent.execution.isolation as isolation_module
from src.agent.execution.isolation import build_isolation_workspace
from src.agent.execution.vision_resize import (
    DEFAULT_VISION_RESIZE_TIER,
    resized_size,
    resized_size_for_tier,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = Path("case_tests/e2e_tests/sm21_anchor")
CASE_DATA = CASE_DIR / "case_data"

PLAN_VIEWS = ["1f_view.png", "2f_view.png"]
ELEVATIONS = ["East_view.png", "North_view.png", "South_view.png", "West_view.png"]

# Hardcoded ground truth for THIS anchor case's real source images -- verified
# 2026-08-16/17 (see the module docstring's provenance). Deliberately NOT
# solely re-derived by calling resized_size_for_tier on the fly: a test that
# only ever compares the production call site's output against the SAME
# algorithm called a second time cannot catch a bug that corrupts both
# identically (e.g. a wrong tier constant shared by both call sites). Each
# per-view test below asserts BOTH this literal tuple AND the freshly
# computed resized_size_for_tier(*orig_size) value, so the two failure modes
# (wrong algorithm vs. algorithm-drifted-from-this-fixture) are distinguished
# rather than conflated.
PLAN_VIEW_TARGETS: dict[str, tuple[int, int]] = {
    "1f_view.png": (1377, 868),   # orig 2133x1345
    "2f_view.png": (1400, 846),   # orig 2182x1319
}


@pytest.fixture(scope="module")
def staging(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real isolation staging (preview/unbound build) from the repo's
    current source tree, shared read-mostly across the tests in this file --
    each test that runs a subprocess writes to its own ``out/<unique>`` name
    so nothing collides under this repo's default parallel test run."""

    root = tmp_path_factory.mktemp("f51_staging")
    # 2026-08-19: the DEFAULT tier is now "none" (stage the original; user ruling —
    # cost-driven downscaling is off the table and the frame tradeoff is packaged into
    # the reading 专项). These tests exist to lock the RESIZE MECHANISM, so they ask for
    # the tier by name. "default = none" is locked separately below.
    manifest = build_isolation_workspace(
        CASE_DIR, staging_root=root / "staging", vision_resize_tier="standard"
    )
    return manifest.staging_root


_REQ_COUNTER = {"n": 0}


def _read_sidecar(staging_root: Path, out_dir: str, image_stem: str, tool: str) -> dict:
    evidence_dir = staging_root / out_dir / "cv_evidence" / image_stem
    assert evidence_dir.is_dir(), f"no evidence directory written: {evidence_dir}"
    candidates = [
        p for p in evidence_dir.glob(f"*_{tool}.json") if not p.name.endswith("_overlay.json")
    ]
    assert len(candidates) == 1, sorted(p.name for p in evidence_dir.iterdir())
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def _run_wall_line_profiler(staging_root: Path, out_dir: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py",
         "--tool", "wall_line_profiler", "--image", "case_data/1f_view.png",
         "--axis", "row", "--out-dir", out_dir],
        cwd=staging_root, capture_output=True, text=True,
    )


# ===========================================================================
# 0) The pure-function algorithm against Anthropic's OWN worked example --
#    required by dispatch as one of this file's locks, independent of
#    anything this repo staged or wired.
# ===========================================================================


def test_resized_size_matches_anthropic_doc_worked_example() -> None:
    """docs/"How Claude resizes and pads images" worked example: an image of
    1075x1520 must resize to exactly 924x1307 under the standard tier. If
    this ever fails, the defect is in the algorithm itself
    (``vision_resize.resized_size``), independent of ``isolation.py``'s
    wiring -- see the neuter test at the bottom of this file for the wiring
    side of the lock."""

    assert resized_size(1075, 1520) == (924, 1307)


def test_resized_size_half_to_even_boundary_disagrees_with_half_up_rounding() -> None:
    """MINOR-2 (2026-08-17 707-prereq cross-review, GLM): the short-edge
    rounding step this module's docstring documents as "banker's-rounding
    ``round()``" was, before this test, never exercised AT a ``.5`` boundary
    -- every size this file already pinned (the Anthropic worked example
    above, and both of this anchor's real plan views in
    ``PLAN_VIEW_TARGETS``) resolves through arithmetic that lands nowhere
    near a half-integer, so those cases cannot tell Python's native
    round-half-to-even apart from a naive round-half-up "fix". The reviewer
    demonstrated this with an independent ``git worktree`` neuter (swap
    ``round`` -> half-up in ``vision_resize.py``): the whole pre-existing
    suite stayed green.

    This size was picked because at ``max_tokens=160`` the binary search for
    ``width=408, height=289`` lands exactly on a ``.5`` fraction, and the two
    rounding rules disagree by a whole pixel on the LONG edge too (not only
    the short-edge value fed into the search, since the search's own `fits`
    probe consumes the rounded short edge) -- confirmed by shadowing this
    module's ``round`` name with a round-half-up implementation and
    re-running just this assertion: round-half-to-even (what
    ``resized_size`` actually uses, and what the worked example above is
    consistent with) gives ``(396, 280)``; round-half-up gives ``(395,
    280)``. Either frame is internally self-consistent, so a silent switch
    between them is exactly the one-pixel frame misalignment F-51 exists to
    prevent (see the module docstring) -- it is simply invisible to any
    fixture whose arithmetic never crosses a ``.5``.
    """

    assert resized_size(408, 289, max_edge=1568, max_tokens=160) == (396, 280)


# ===========================================================================
# 1) Plan views (oversized source): staged copy is resized to the standard
#    tier's target, and is genuinely different from the original (not a
#    silent no-op).
# ===========================================================================


@pytest.mark.parametrize("name", PLAN_VIEWS)
def test_plan_view_staged_at_vision_resize_target_and_actually_shrunk(
    staging: Path, name: str
) -> None:
    with Image.open(CASE_DATA / name) as orig_im:
        orig_size = orig_im.size
    with Image.open(staging / "case_data" / name) as staged_im:
        staged_size = staged_im.size

    # ask for the same tier the `staging` fixture built with (default is now "none")
    computed_target = resized_size_for_tier(*orig_size, "standard")
    assert staged_size == computed_target, (
        f"staged size disagrees with a fresh resized_size_for_tier call: "
        f"orig={orig_size} staged={staged_size} computed_target={computed_target}"
    )
    assert staged_size == PLAN_VIEW_TARGETS[name], (
        f"staged size disagrees with this anchor's hardcoded ground truth: "
        f"staged={staged_size} expected={PLAN_VIEW_TARGETS[name]}"
    )
    assert staged_size != orig_size, (
        f"expected an oversized source ({orig_size}) to actually be shrunk, "
        f"but the staged copy is still {staged_size}"
    )


# ===========================================================================
# 2) Elevations (already within tier): staged copy round-trips byte-for-byte
#    identical -- a no-op resize must not silently re-encode the file.
# ===========================================================================


@pytest.mark.parametrize("name", ELEVATIONS)
def test_elevation_round_trips_byte_identical_when_already_within_tier(
    staging: Path, name: str
) -> None:
    orig_bytes = (CASE_DATA / name).read_bytes()
    staged_bytes = (staging / "case_data" / name).read_bytes()
    assert staged_bytes == orig_bytes, (
        f"orig_sha={hashlib.sha256(orig_bytes).hexdigest()[:12]} "
        f"staged_sha={hashlib.sha256(staged_bytes).hexdigest()[:12]}"
    )


# ===========================================================================
# 3) The repo's own original case_data is never mutated by a staging build.
# ===========================================================================


def test_repo_original_case_data_untouched_by_staging_build(staging: Path) -> None:
    """Defense in depth against a plausible one-variable mistake (resizing
    ``src`` in place instead of the staged ``dest`` copy) that a pure
    code-reading review might miss -- by construction
    ``_copy_case_data_image`` only ever calls ``shutil.copy2(src, dest)``
    then resizes ``dest``, but this asserts the OBSERVABLE consequence of
    that discipline directly against the real repo working tree, not just
    the source code shape."""

    diff = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--stat", "--",
         "case_tests/e2e_tests/sm21_anchor/case_data/"],
        capture_output=True, text=True, check=True,
    )
    assert diff.stdout.strip() == "", diff.stdout


# ===========================================================================
# 4) MANIFEST.json's recorded hash matches the RESIZED on-disk bytes, not a
#    stale pre-resize hash.
# ===========================================================================


def test_manifest_records_hash_of_resized_bytes_not_a_stale_prefix_hash(staging: Path) -> None:
    mf = json.loads((staging / "MANIFEST.json").read_text(encoding="utf-8"))
    entries = {e["path"]: e for e in mf["files"]}
    actual_sha = hashlib.sha256((staging / "case_data" / "1f_view.png").read_bytes()).hexdigest()
    assert entries["case_data/1f_view.png"]["sha256"] == actual_sha


# ===========================================================================
# 5) THE CRUX: the real cv_probe entry point (subprocess, staged wrapper)
#    reports the SAME (resized) frame the model would see -- not the
#    original 2133x1345.
# ===========================================================================


def test_real_cv_probe_subprocess_sees_the_resized_frame_not_the_original(staging: Path) -> None:
    proc = _run_wall_line_profiler(staging, "out/f51_frame_check")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, "out/f51_frame_check", "1f_view", "wall_line_profiler")
    src_img = sidecar["source_image"]
    got = (src_img["width_px"], src_img["height_px"])
    assert got == PLAN_VIEW_TARGETS["1f_view.png"], f"cv_probe saw {got}, expected the resized frame"


# ===========================================================================
# 6) NEUTER: cut exactly the wiring F-51 added and confirm the pre-fix frame
#    mismatch resurfaces.
# ===========================================================================


def test_neuter_cutting_the_resize_wiring_reproduces_the_original_frame_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F-51 is a brand-new call site, not a changed one -- ``vision_resize.py``
    did not exist before this fix, and the resize call
    (``_copy_case_data_image`` -> ``resize_image_file_to_tier``) runs INSIDE
    ``build_isolation_workspace`` itself, in the orchestrator's own process --
    it is never a file staged for a subprocess to read (unlike F-52/F-54/F-58/
    F-53 in ``tests/test_substrate_fix_tools.py``, all of which patch a
    STAGED COPY via ``_neuter_into_fresh_staging`` because their mechanism
    only runs inside the later subprocess). There is therefore no
    "pre-fix committed version of this file" to swap back in with that
    technique -- the equivalent-strength substitute is a ``monkeypatch`` of
    the exact call site's imported name, scoped to this one test by pytest's
    ``monkeypatch`` fixture (auto-undone at teardown).

    This is at least as safe as the file-swap technique against the M-1
    cross-worker race (2026-08-17 cross-review, see
    ``tests/test_substrate_fix_tools.py::_neuter_into_fresh_staging``'s
    docstring): it is a pure in-memory attribute patch on THIS process's own
    module object, never a filesystem write anywhere (not the repo, not even
    ``tmp_path``) -- a sibling ``pytest -n auto`` WORKER is a separate OS
    process with its own independent Python module state, so it cannot
    observe this patch under any interleaving, a stronger guarantee than "no
    other worker happens to read this exact path during the swap window".

    Still a real-entry-point test throughout: the REAL
    ``build_isolation_workspace()`` runs end to end (never a hand-simulated
    reimplementation) and a REAL subprocess runs against the staged
    ``tools/run_cv_probe.py`` afterward -- only the one function
    ``_copy_case_data_image`` calls to perform the resize is replaced with a
    passthrough that opens the file and returns its size WITHOUT resizing,
    i.e. exactly what every caller observed before F-51 added this call.
    """

    def _passthrough_no_resize(path, tier: str = DEFAULT_VISION_RESIZE_TIER) -> tuple[int, int]:
        with Image.open(path) as img:
            return img.size

    monkeypatch.setattr(isolation_module, "resize_image_file_to_tier", _passthrough_no_resize)

    manifest = build_isolation_workspace(
        CASE_DIR, staging_root=tmp_path / "neuter_staging", vision_resize_tier="standard"
    )
    neuter_staging = manifest.staging_root

    with Image.open(CASE_DATA / "1f_view.png") as orig_im:
        orig_size = orig_im.size
    with Image.open(neuter_staging / "case_data" / "1f_view.png") as staged_im:
        staged_size = staged_im.size
    assert staged_size == orig_size, "expected the pre-F-51 behavior (no resize at all) to resurface"
    assert staged_size != PLAN_VIEW_TARGETS["1f_view.png"], "neuter had no effect -- still resized"

    proc = _run_wall_line_profiler(neuter_staging, "out/f51_neuter")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(neuter_staging, "out/f51_neuter", "1f_view", "wall_line_profiler")
    src_img = sidecar["source_image"]
    got = (src_img["width_px"], src_img["height_px"])
    assert got == orig_size, f"expected cv_probe to see the ORIGINAL unresized frame again, got {got}"
    assert got != PLAN_VIEW_TARGETS["1f_view.png"], (
        "neuter had no effect -- cv_probe still sees the resized frame"
    )


def test_default_tier_stages_the_original_bytes(tmp_path: Path) -> None:
    """⭐ 2026-08-19 user ruling lock: the DEFAULT staging behaviour is to leave the
    drawing alone.

    The rest of this file locks that the resize MECHANISM works when asked for. This
    locks the other half — that it is not asked for by default. Before this ruling the
    default was "standard", which silently shrank every plan to 1377x868; the reason it
    is a lock and not a comment is that the tier had NO entry point at all until today,
    so a default flip was previously indistinguishable from a code change nobody could
    override.
    """
    from src.agent.execution.vision_resize import (
        DEFAULT_VISION_RESIZE_TIER,
        NO_VISION_RESIZE,
    )

    assert DEFAULT_VISION_RESIZE_TIER == NO_VISION_RESIZE

    manifest = build_isolation_workspace(CASE_DIR, staging_root=tmp_path / "default_staging")
    staged = Path(manifest.staging_root) / "case_data" / "1f_view.png"
    source = CASE_DATA / "1f_view.png"

    assert staged.read_bytes() == source.read_bytes(), (
        "default staging must hand the reader the original file byte for byte"
    )
    with Image.open(staged) as a, Image.open(source) as b:
        assert a.size == b.size


def test_standard_tier_still_shrinks_when_asked(tmp_path: Path) -> None:
    """Negative half of the lock above: flipping the default back to a resizing tier
    must still be reachable and must still actually shrink, otherwise the first lock
    would pass simply because the resize broke."""
    manifest = build_isolation_workspace(
        CASE_DIR, staging_root=tmp_path / "standard_staging", vision_resize_tier="standard"
    )
    staged = Path(manifest.staging_root) / "case_data" / "1f_view.png"
    with Image.open(staged) as a, Image.open(CASE_DATA / "1f_view.png") as b:
        assert a.size != b.size
        assert a.size[0] < b.size[0]
