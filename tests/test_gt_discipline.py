"""gt is judge-only: loader works, and gate① / executors must NOT import it.

The discipline (gt/README.md): the evaluation answer key may only be read by the
gate② judge. gate① ships to prod (no answers) and executors must stay blind, so
they must not depend on src.agent.judge.gt. This test mechanically enforces it by
scanning those modules' source for any gt reference.
"""

from __future__ import annotations

from pathlib import Path

from src.agent.judge.gt import has_gt, load_gt


def test_gt_loader_reads_sm21_draft():
    gt = load_gt("sm21_anchor")
    assert gt is not None and gt["case"] == "sm21_anchor"
    assert has_gt("sm21_anchor")
    # window-count truth sums to 15 (1F 7 + 2F 8)
    total = sum(w["count"] for w in gt["windows"])
    assert total == 15
    # both floors have 7 zones
    assert all(len(f["zones"]) == f["zone_count"] == 7 for f in gt["floors"])


def test_gt_loader_absent_returns_none(tmp_path):
    assert load_gt("does_not_exist", gt_dir=tmp_path) is None
    assert has_gt("does_not_exist", gt_dir=tmp_path) is False


# --------------------------------------------------------------------------- #
# discipline: gate① + executors must not import gt
# --------------------------------------------------------------------------- #
_FORBIDDEN = ("judge.gt", "judge import gt", "load_gt", "test_baseline/gt", "gt.json", "/gt/")


def _scan(paths: list[Path]) -> list[str]:
    hits = []
    for p in paths:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for token in _FORBIDDEN:
            if token in text:
                hits.append(f"{p}: contains '{token}'")
    return hits


def test_gate1_checks_do_not_reference_gt():
    checks = list(Path("src/validator/checks").glob("*.py"))
    assert checks  # sanity
    hits = _scan(checks)
    assert not hits, f"gate① must not reference gt: {hits}"


def test_executors_do_not_reference_gt():
    executors = [Path("src/agent/pipeline.py")]
    executors.extend(sorted(Path("src/agent/execution").rglob("*.py")))
    executors.extend(sorted(Path("src/agent/correction").rglob("*.py")))
    executors.extend(sorted(Path("src/agent/reading").rglob("*.py")))
    executors.append(Path("scripts/tool_scripts/cv_probe.py"))
    hits = _scan(executors)
    assert not hits, f"executors / gate① capstone must not reference gt: {hits}"


def test_prescan_entry_points_stay_gt_blind():
    paths = [
        Path("src/agent/reading/cv_toolbox/recipes.py"),
        Path("scripts/tool_scripts/cv_probe.py"),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "prescan-plan" in text or "prescan_plan" in text
        assert "prescan-elevation" in text or "prescan_elevation" in text
    hits = _scan(paths)
    assert not hits, f"prescan entry points must not reference gt: {hits}"


def test_judge_side_gt_readers_remain_confined_to_judge_package():
    judge_gt_readers = [
        Path("src/agent/judge/reading_score.py"),
        Path("src/agent/judge/elevation_score.py"),
    ]
    for path in judge_gt_readers:
        text = path.read_text(encoding="utf-8")
        assert "load_gt" in text or ".gt import" in text
        assert path.is_relative_to(Path("src/agent/judge"))
