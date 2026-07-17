"""gt is judge-only: loader works, and gate① / executors must NOT import it.

The discipline (gt/README.md): the evaluation answer key may only be read by the
gate② judge. gate① ships to prod (no answers) and executors must stay blind, so
they must not depend on src.agent.judge.gt. This test mechanically enforces it by
scanning those modules' source for any gt reference.
"""

from __future__ import annotations

from pathlib import Path
import inspect

from src.agent.judge import gt_render_model

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


def test_v3_renderer_path_has_no_fixed_four_panel_or_gate_vocabulary():
    """B-03: dynamic surface keys stay isolated from legacy v2's four facades."""
    source = (inspect.getsource(gt_render_model.gt_to_render_model) +
              inspect.getsource(gt_render_model.render_plan_model) +
              inspect.getsource(gt_render_model.render_elevation_model))
    forbidden = ("range(4)", "_FLOOR_OF", "_ROLES", "PLAN_BAND_Y", "largest bbox")
    assert not [token for token in forbidden if token in source]
    assert "elevation_surfaces" in source and "sorted" in source


def test_v3_render_adapter_is_judge_side_and_schema_free_in_renderer():
    source = inspect.getsource(gt_render_model.render_plan_model) + inspect.getsource(gt_render_model.render_elevation_model)
    assert "footprint\", {}" not in source and ".get(\"W_m\")" not in source


def test_render_gt_v3_entry_branch_has_no_fixed_four_or_gate_vocabulary():
    source = Path("scripts/tool_scripts/render_gt.py").read_text(encoding="utf-8")
    v3 = source[source.index("def _model_for_render"):]
    assert not [token for token in ("range(4)", "_FLOOR_OF", "_ROLES", "PLAN_BAND_Y", "largest bbox") if token in v3]


def test_v3_overlay_path_has_no_legacy_density_or_fixed_panel_vocabulary():
    source = Path("scripts/tool_scripts/render_gt_overlay.py").read_text(encoding="utf-8")
    v3 = source[source.index("def build_gt_overlay_images_v3"):source.index("def write_gt_overlay_images_v3")]
    assert not [token for token in ("_calibrate", "_FLOOR_PNG", "_FACADE_PNG", "range(4)", "largest bbox") if token in v3]
