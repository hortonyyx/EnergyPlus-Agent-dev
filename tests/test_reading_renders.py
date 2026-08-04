"""O-1 (batch C) locks for the reading-stage render finalization in run_stage.

Root cause these lock (M-1): hard-isolated merge writes the aggregate reading
views to ``attempts/NNN/output.json`` (shaped ``{'views': {<eid>: <ReadingView>}}``)
and leaves NOTHING at the ``0_reading/`` stage root. But ``_render_stage``'s old
``0_reading`` branch globbed ``0_reading/*_view.json`` at the stage root — so
07-08 onward every reading run rendered zero images and the user saw no product.
The fix reads the aggregate from each attempt's ``output.json`` with the SAME
renderer (``render_vector_to_png.render``), writes per-attempt
``renders/<eid>.png`` + a machine-readable ``render_manifest.json`` (source
output hash + render helper version + per-view status/hash), and never swallows
a render failure into 'complete' — a failed render blocks review approval.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.tool_scripts.run_stage as rs


def _wall(p1=(0, 0), p2=(10, 0)):
    return {"pen": "wall", "geometry": {"kind": "line", "p1": list(p1), "p2": list(p2)}}


def _agg_views() -> dict:
    """A synthetic 2-view aggregate (NOT from GT / any case fixture): each view
    is a minimal per-image vector payload consumable by render_vector_to_png.render."""
    return {
        "1f_view": {"image_kind": "plan", "image_label": "plan", "strokes": [_wall()]},
        "South_view": {"image_kind": "elevation", "image_label": "south", "strokes": [_wall((0, 0), (10, 5))]},
    }


def _seed_attempt(run_dir: Path, *, attempt: int = 1, views: dict | None = None) -> Path:
    """Write ONLY ``attempts/<NNN>/output.json`` (the hard-isolated merge
    product). Critically, NO ``0_reading/*_view.json`` exists at the stage root
    — that is exactly the M-1 condition the old flat glob silently failed on."""
    adir = run_dir / "0_reading" / "attempts" / f"{attempt:03d}"
    adir.mkdir(parents=True)
    (adir / "output.json").write_text(
        json.dumps({"views": views if views is not None else _agg_views()}),
        encoding="utf-8",
    )
    return adir


def test_L40_isolation_aggregate_renders_per_attempt_with_hashes(tmp_path):
    """L-40 (O-1): an isolated reading run produces ONLY ``attempts/001/output.json``
    (aggregate views) and NO ``0_reading/*_view.json`` at the stage root. The
    render path must read that aggregate and produce per-attempt renders, each
    with a source output hash + a per-view render hash in render_manifest.json.

    Neuter: revert the reading render path to the old ``0_reading/*_view.json``
    flat glob (i.e. make ``_render_reading_attempts`` glob the stage root instead
    of reading ``attempts/NNN/output.json``) ⇒ under this M-1 setup the glob
    matches nothing ⇒ no ``renders/`` and no ``render_manifest.json`` produced ⇒
    this lock reds."""
    run_dir = tmp_path / "run"
    adir = _seed_attempt(run_dir)
    # the M-1 condition: nothing at the stage root for the old glob to find
    assert not list((run_dir / "0_reading").glob("*_view.json"))

    rs._render_reading_attempts(run_dir)

    manifest = json.loads((adir / "render_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["render_helper_version"] == rs.READING_RENDER_HELPER_VERSION
    # source_output_hash == hash_text of the attempt's output.json bytes, i.e.
    # the SAME value merge records as the stage's output_hash — cross-referenceable.
    from src.agent.execution.manifest import hash_text
    assert manifest["source_output_hash"] == hash_text(
        (adir / "output.json").read_text(encoding="utf-8"))
    # each declared view rendered to <eid>.png with a render hash + no error
    assert {v["expected_output_id"] for v in manifest["views"]} == {"1f_view", "South_view"}
    for v in manifest["views"]:
        assert v["status"] == "rendered"
        assert v["error"] is None
        png = adir / "renders" / f"{v['expected_output_id']}.png"
        assert png.exists() and png.stat().st_size > 0
        assert v["render_hash"]
        # render_hash is the sha256 of the written png (hash_file), not a placeholder
        from src.agent.execution.manifest import hash_file
        assert v["render_hash"] == hash_file(png)


def test_L40_render_stage_reading_branch_reads_attempts_not_stage_root(tmp_path):
    """L-40 companion (O-1): ``_render_stage('0_reading', ...)`` — the real flow
    entry called after merge — returns the per-attempt render png paths produced
    from the aggregate (NOT from a stage-root glob). With only
    ``attempts/001/output.json`` present, it still renders both views."""
    run_dir = tmp_path / "run"
    _seed_attempt(run_dir)
    produced = rs._render_stage("0_reading", run_dir, tmp_path / "case")
    produced_names = {Path(p).name for p in produced}
    assert produced_names == {"1f_view.png", "South_view.png"}
    assert all((run_dir / "0_reading" / "attempts" / "001" / "renders" / n).exists()
               for n in produced_names)


def test_L41_render_failure_records_unavailable_not_complete(tmp_path, monkeypatch):
    """L-41 (O-1): when the renderer raises (injected exception), the render
    manifest must record ``status='unavailable'`` (NOT ``'complete'``) with each
    view ``status='failed'`` + the error (a machine-readable failure artifact),
    and ``_reading_render_status`` must report unavailable/blocked — never
    complete. No png is written for a failed view.

    Neuter: restore the best-effort swallow — mark a failed view ``'rendered'``
    (or leave the manifest ``status='complete'`` regardless of the exception) ⇒
    ``_reading_render_status`` returns ``'complete'`` and the manifest no longer
    carries a failure record ⇒ this lock reds."""
    sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
    import render_vector_to_png as rv

    def _boom(_data):
        raise RuntimeError("injected render failure")

    monkeypatch.setattr(rv, "render", _boom)

    run_dir = tmp_path / "run"
    adir = _seed_attempt(run_dir)

    manifest = rs._finalize_reading_renders(adir)

    assert manifest["status"] == "unavailable"
    assert rs._reading_render_status(adir) == "unavailable"  # NOT "complete"
    assert len(manifest["views"]) == 2
    for v in manifest["views"]:
        assert v["status"] == "failed"
        assert v["render_hash"] is None
        assert "injected render failure" in (v["error"] or "")
    # the source output hash is still recorded (the failure artifact is complete)
    assert manifest["source_output_hash"]
    # no png was written for the failed views
    assert not list((adir / "renders").glob("*.png"))


def test_L41_failed_render_blocks_review_approval(tmp_path):
    """L-41 (O-1): a review-required reading run whose accepted attempt has an
    UNAVAILABLE render manifest must NOT be markable review-complete —
    ``cmd_approve_review`` refuses (the human would be approving with no visual
    material). The block is machine-readable: it names the manifest status.

    Neuter: drop the ``_reading_render_status == 'unavailable'`` guard in
    ``cmd_approve_review`` ⇒ approve-review succeeds despite the failed render ⇒
    this lock reds. (A 'complete' manifest approves normally — see companion.)"""
    from src.agent.execution.manifest import RunManifestV2, StageRecordV2, save_run_manifest

    run_dir = tmp_path / "case" / "run"
    adir = _seed_attempt(run_dir)  # attempts/001/output.json
    # accepted 0_reading attempt = 001
    h = "a" * 64
    save_run_manifest(
        RunManifestV2(
            case="case", run_id="b" * 32, run_inputs={"view_manifest_sha256": h},
            stages={"0_reading": StageRecordV2(
                stage="0_reading", accepted_attempt=1, output_hash=h,
                artifact_contract="reading_isolated_v2",
                artifact_hashes={"output": h, "checks": h, "isolation_provenance": h})},
        ),
        run_dir,
    )
    # render FAILED for this attempt -> manifest status unavailable
    (adir / "render_manifest.json").write_text(
        json.dumps({
            "source_output_hash": h, "render_helper_version": rs.READING_RENDER_HELPER_VERSION,
            "status": "unavailable",
            "views": [{"expected_output_id": "1f_view", "status": "failed",
                        "render_hash": None, "error": "RuntimeError: boom"}],
        }),
        encoding="utf-8",
    )

    args = SimpleNamespace(base_dir=str(tmp_path), case="case", run="run",
                           stage="0_reading", actor="tester", note="", date="")
    with pytest.raises(SystemExit, match="review blocked: 0_reading renders are unavailable"):
        rs.cmd_approve_review(args)


def test_L41_complete_render_allows_review_approval(tmp_path):
    """L-41 companion (O-1): the review block is precise — a 'complete' render
    manifest does NOT block approval (only 'unavailable' does). This keeps the
    guard from over-blocking healthy runs and pins the 'missing' branch
    (pre-O-1 runs stay approvable)."""
    from src.agent.execution.manifest import RunManifestV2, StageRecordV2, save_run_manifest

    run_dir = tmp_path / "case" / "run"
    adir = _seed_attempt(run_dir)
    h = "a" * 64
    save_run_manifest(
        RunManifestV2(
            case="case", run_id="b" * 32, run_inputs={"view_manifest_sha256": h},
            stages={"0_reading": StageRecordV2(
                stage="0_reading", accepted_attempt=1, output_hash=h,
                artifact_contract="reading_isolated_v2",
                artifact_hashes={"output": h, "checks": h, "isolation_provenance": h})},
        ),
        run_dir,
    )
    # render SUCCEEDED for this attempt -> manifest status complete
    rs._finalize_reading_renders(adir)
    assert rs._reading_render_status(adir) == "complete"

    args = SimpleNamespace(base_dir=str(tmp_path), case="case", run="run",
                           stage="0_reading", actor="tester", note="", date="")
    assert rs.cmd_approve_review(args) == 0
