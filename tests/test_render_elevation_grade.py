"""The elevation grade PICTURE — view-only locks.

Tests the renderer at scripts/tool_scripts/render_elevation_grade.py (named
by full path so the affected-tests graph sees the edge it already has in
fact — this file imports and drives the module).

Same contract as the plan picture (``test_render_grade.py`` / the renderer's
own docstring): ⛔ a VIEW, never a source of score.  Every box it draws comes
out of ``grade["detail"]``.  The locks here hold exactly that:

  * it renders the real product + real grade to a non-empty image, including
    under the MIRROR axis hypothesis (the picture must still land on the
    product's own image, answer rows reflected into its frame);
  * it reports the rows the grade already counted (⛔ no recompute): feeding
    it a grade whose detail is emptied yields the emptied tally, not its own
    opinion;
  * a grade report without a detail block is refused (the same guard the plan
    picture has — predates-detail reports must not be silently drawn).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_elevation_grade  # noqa: E402

from src.agent.judge.as_drawn.elevation_grade import elevation_targets, grade

REPO = Path(__file__).resolve().parents[1]
GT = json.loads((REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json").read_text())
PROTOTYPE = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
IMAGE = REPO / "case_tests/e2e_tests/sm25-L_anchor/case_data/East_view.png"


def _render(tmp_path, *, doc, graded, name="grade.png"):
    doc_path = tmp_path / "doc.json"
    grade_path = tmp_path / "grade.json"
    out = tmp_path / name
    doc_path.write_text(json.dumps({**doc, "image": str(IMAGE)}, ensure_ascii=False))
    grade_path.write_text(json.dumps(graded, ensure_ascii=False))
    return render_elevation_grade.render(str(doc_path), str(grade_path), str(out)), out


def test_renders_a_real_grade_with_a_nonempty_picture(tmp_path):
    doc = json.loads((PROTOTYPE / "sm25_east_as_drawn.json").read_text())
    graded = grade(doc, elevation_targets(GT, "East_view"), gt=GT)
    readout, out = _render(tmp_path, doc=doc, graded=graded)
    assert readout["view"] == "East_view"
    assert readout["axis"] == "identity"
    assert readout["openings"]["OK"] == graded["by_verdict"]["OK"]
    with Image.open(out) as im:
        assert im.size[0] > 0 and im.size[1] > 0


def test_renders_under_the_mirror_hypothesis(tmp_path):
    """North's product axis is mirrored: the picture must still land on the
    PRODUCT'S OWN image (answer rows reflected into its frame) and come out
    non-empty.  Goes red if the renderer ignores the axis report and draws
    answer boxes off-image / at wrong ends."""
    doc = json.loads((PROTOTYPE / "sm25_north_as_drawn.json").read_text())
    doc = {**doc, "image": str(REPO / "case_tests/e2e_tests/sm25-L_anchor"
                               "/case_data/North_view.png")}
    graded = grade(doc, elevation_targets(GT, "North_view"), gt=GT)
    assert graded["along_axis"]["assumed"] == "mirror"    # premise, asserted
    readout, out = _render(tmp_path, doc=doc, graded=graded)
    assert readout["axis"] == "mirror"
    with Image.open(out) as im:
        assert im.size[0] > 0


def test_the_picture_reports_the_grades_rows_never_its_own(tmp_path):
    """View-only: empty the detail rows and the renderer's own tally follows
    them to zero.  Goes red the day the renderer recomputes anything (e.g.
    re-matches openings against gt geometry of its own)."""
    doc = json.loads((PROTOTYPE / "sm25_east_as_drawn.json").read_text())
    graded = grade(doc, elevation_targets(GT, "East_view"), gt=GT)
    assert graded["detail"]["openings"]          # premise: rows exist to empty
    emptied = json.loads(json.dumps(graded))
    emptied["detail"]["openings"] = []
    emptied["by_verdict"] = {v: 0 for v in emptied["by_verdict"]}
    readout, _ = _render(tmp_path, doc=doc, graded=emptied, name="empty.png")
    assert readout["openings"]["NOT_FOUND"] == 0
    assert sum(readout["openings"].values()) == 0


def test_a_report_without_detail_is_refused(tmp_path):
    """A predates-detail report must not be silently drawn.  Goes red if the
    guard is dropped (the picture would then show whatever a stale report
    still carried)."""
    doc = json.loads((PROTOTYPE / "sm25_east_as_drawn.json").read_text())
    graded = grade(doc, elevation_targets(GT, "East_view"), gt=GT)
    del graded["detail"]
    with pytest.raises(SystemExit):
        _render(tmp_path, doc=doc, graded=graded, name="stale.png")
