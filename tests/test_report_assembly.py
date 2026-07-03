from __future__ import annotations

from pathlib import Path

from PIL import Image

from scripts.tool_scripts.report_assembly import collect_eyeball_assets


def _png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), (250, 250, 248)).save(path)


def test_collect_eyeball_assets_collects_stage_grades(tmp_path):
    run_dir = tmp_path / "run"
    _png(run_dir / "0_reading" / "grade.png")
    _png(run_dir / "1_correction" / "grade.png")

    result = collect_eyeball_assets(run_dir)

    names = {asset["filename"] for asset in result["assets"]}
    assert {"0_reading_grade.png", "1_correction_grade.png"} <= names
    assert (run_dir / "report" / "eyeball" / "0_reading_grade.png").exists()
    assert (run_dir / "report" / "eyeball" / "1_correction_grade.png").exists()
