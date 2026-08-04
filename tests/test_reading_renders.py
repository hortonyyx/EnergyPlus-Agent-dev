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


def _seed_flat_attempt(run_dir: Path, *, attempt: int = 1, views: dict | None = None) -> Path:
    """B-1 (r1): write ``attempts/<NNN>/output.json`` in the FLAT shape that
    StageRunner archives for the blind-re-read recovery path — ``{<stem>: <view>}``
    with NO ``views`` wrapper (StageRunner archives ``_draw_reading``'s
    ``{vj.stem: view}`` verbatim; see
    ``window_sources.verify_reading_stage_root_against_accepted_attempt``).
    This is the OTHER living layout the render path must recognize, distinct from
    the isolated-merge aggregate ``{'views': {...}}`` written by ``_seed_attempt``."""
    adir = run_dir / "0_reading" / "attempts" / f"{attempt:03d}"
    adir.mkdir(parents=True)
    (adir / "output.json").write_text(
        json.dumps(views if views is not None else _agg_views()),
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


def test_L40_flat_flow_blind_reread_renders_and_approves(tmp_path):
    """B-1 (r1 BLOCKER): the blind-re-read recovery path archives a reading draw
    in the FLAT shape ``{<stem>: <view>}`` — StageRunner archives
    ``_draw_reading``'s ``{vj.stem: view}`` with NO ``views`` wrapper (see
    ``window_sources.verify_reading_stage_root_against_accepted_attempt``), and
    both ``judge_rubric.md`` and this CLI's own ``_print_reread_protocol`` command
    the reader to write the flat ``0_reading/*_view.json`` working copy. The
    render path must recognize that shape — NOT only the isolated-merge
    ``{'views': {...}}`` shape — produce per-view renders, finalize status
    ``'complete'`` (NOT ``'unavailable'``), and let ``cmd_approve_review`` through.

    This lock walks the REAL flat-flow path (no isolated fixture, no ``views``
    wrapper): it writes the flat-shape archived artifact and drives the real
    ``_render_stage`` + real ``cmd_approve_review``. The old O-1 code did only
    ``.get('views')`` ⇒ the flat output parsed to zero views ⇒ status
    ``'unavailable'`` ⇒ a completely healthy run was reverse-blocked at review
    (the regression the cross-review reproduced: two PNGs before O-1, zero after).

    Neuter: make the views extractor recognize ONLY the ``{'views': {...}}``
    shape again (revert ``_extract_reading_views`` to ``out_obj.get('views')``) ⇒
    the flat output yields zero views ⇒ no renders, status ``'empty'`` ⇒ this
    lock reds on the render + status assertions."""
    from src.agent.execution.manifest import RunManifestV2, StageRecordV2, save_run_manifest

    run_dir = tmp_path / "case" / "run"
    adir = _seed_flat_attempt(run_dir)  # FLAT {stem: view}, NOT views-wrapped
    raw = json.loads((adir / "output.json").read_text(encoding="utf-8"))
    # pin the flat-flow precondition: archived output is stem-keyed, NOT wrapped
    assert "views" not in raw and {"1f_view", "South_view"} <= set(raw)

    produced = rs._render_stage("0_reading", run_dir, tmp_path / "case")
    produced_names = {Path(p).name for p in produced}
    assert produced_names == {"1f_view.png", "South_view.png"}
    assert all((adir / "renders" / n).exists() for n in produced_names)

    manifest = json.loads((adir / "render_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"  # NOT 'unavailable' — the regression
    assert rs._reading_render_status(adir) == "complete"

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
    args = SimpleNamespace(base_dir=str(tmp_path), case="case", run="run",
                           stage="0_reading", actor="tester", note="", date="")
    assert rs.cmd_approve_review(args) == 0


def test_L41_empty_view_set_is_not_render_failure(tmp_path):
    """B-1 (r1): "no images to render" (a recognized shape with zero views) must
    be a DISTINCT, NON-BLOCKING state from "a render failed". An empty output
    finalizes ``'empty'`` — NOT ``'unavailable'`` (the failure state that blocks
    review) — and ``cmd_approve_review`` lets it through. Cross-review
    requirement: the old ternary ``'complete' if (views and not failed) else
    'unavailable'`` conflated an empty view set with a render failure.

    Neuter: restore that ternary (empty ⇒ 'unavailable') ⇒ status flips to
    'unavailable' and approve-review raises ⇒ this lock reds. The companion fact
    — a real render failure still yields 'unavailable' — is pinned by
    test_L41_render_failure_records_unavailable_not_complete."""
    from src.agent.execution.manifest import RunManifestV2, StageRecordV2, save_run_manifest

    run_dir = tmp_path / "case" / "run"
    adir = run_dir / "0_reading" / "attempts" / "001"
    adir.mkdir(parents=True)
    (adir / "output.json").write_text(json.dumps({}), encoding="utf-8")  # zero views

    manifest = rs._finalize_reading_renders(adir)
    assert manifest["status"] == "empty"
    assert manifest["status"] != "unavailable"
    assert rs._reading_render_status(adir) == "empty"
    assert manifest["views"] == []
    assert (adir / "render_manifest.json").exists()

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
    args = SimpleNamespace(base_dir=str(tmp_path), case="case", run="run",
                           stage="0_reading", actor="tester", note="", date="")
    assert rs.cmd_approve_review(args) == 0  # empty does NOT block review


def test_L41_unreadable_output_records_failure_artifact_not_missing(tmp_path):
    """M-1 (r1 / F-2): when an attempt's output.json is unreadable/corrupt, the
    render path must STILL drop a machine-readable failure artifact — a
    render_manifest with a real-failure status — DISTINCT from 'missing' (no
    manifest = never tried / pre-O-1). The old code let the read/parse exception
    propagate to _render_stage's stage-level except ⇒ NO manifest written ⇒
    _reading_render_status returned 'missing' ⇒ a tried-but-broken run was
    indistinguishable from a pre-O-1 run AND approve-review let it through.

    Drives the REAL _finalize_reading_renders (monkeypatch-free) on a corrupt
    output.json. Neuter: remove the read/parse try/except in
    _finalize_reading_renders (let it raise again) ⇒ no manifest written ⇒
    _reading_render_status returns 'missing' and approve-review does not raise ⇒
    this lock reds."""
    from src.agent.execution.manifest import RunManifestV2, StageRecordV2, save_run_manifest

    run_dir = tmp_path / "case" / "run"
    adir = run_dir / "0_reading" / "attempts" / "001"
    adir.mkdir(parents=True)
    (adir / "output.json").write_text("{ not valid json ", encoding="utf-8")

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

    manifest = rs._finalize_reading_renders(adir)
    # M-1: a failure artifact IS dropped — not swallowed to nothing
    assert (adir / "render_manifest.json").exists()
    assert manifest["status"] == "unavailable"
    assert manifest["views"] == []
    assert manifest["error"]  # machine-readable reason recorded
    # distinct from 'missing' (never tried) — the whole point of M-1
    status = rs._reading_render_status(adir)
    assert status == "unavailable"
    assert status != "missing"
    # M-1: a tried-but-broken run must NOT slip through review (old 'missing' did)
    args = SimpleNamespace(base_dir=str(tmp_path), case="case", run="run",
                           stage="0_reading", actor="tester", note="", date="")
    with pytest.raises(SystemExit, match="review blocked"):
        rs.cmd_approve_review(args)


def test_L41_render_loop_survives_catastrophic_attempt(tmp_path, monkeypatch):
    """M-1 (r1) / F-2: a catastrophic failure in ONE attempt's finalize (beyond
    the read/parse handled inside _finalize_reading_renders) must not kill the
    whole render loop — the accepted attempt's renders must still be returned,
    and the crashed attempt must get a best-effort failure manifest (never
    silently 'missing'). Previously a mid-loop raise dropped the ENTIRE produced
    list, including renders already written for earlier attempts.

    Neuter: drop the per-attempt try/except in _render_reading_attempts (let a
    crash propagate) ⇒ the loop aborts on the crashing attempt ⇒ the accepted
    attempt's renders vanish from `produced` ⇒ this lock reds."""
    run_dir = tmp_path / "run"
    _seed_attempt(run_dir, attempt=1)  # healthy aggregate (rendered first)
    crashed = _seed_attempt(run_dir, attempt=2)
    real = rs._finalize_reading_renders

    def _patched(adir):
        if adir.name == "002":
            raise RuntimeError("injected catastrophic finalize crash")
        return real(adir)

    monkeypatch.setattr(rs, "_finalize_reading_renders", _patched)

    produced = rs._render_reading_attempts(run_dir)
    produced_names = {Path(p).name for p in produced}
    # accepted attempt 001 still rendered despite 002 crashing
    assert {"1f_view.png", "South_view.png"} <= produced_names
    # crashed attempt got a best-effort failure manifest — NOT silently missing
    assert rs._reading_render_status(crashed) == "unavailable"
    assert (crashed / "render_manifest.json").exists()
