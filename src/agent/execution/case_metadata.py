"""Case manifest helpers for validator-visible, non-GT metadata."""

from __future__ import annotations

import json
from pathlib import Path


def testdata_path(case_dir: Path | str) -> Path | None:
    case_dir = Path(case_dir)
    for candidate in (
        case_dir / "case_data" / "testdata_prompt.json",
        case_dir / "testdata_prompt.json",
    ):
        if candidate.exists():
            return candidate
    return None


def load_case_metadata(case_dir: Path | str) -> dict:
    path = testdata_path(case_dir)
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def parse_testdata_text(text: str) -> dict | None:
    if not text.strip():
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def expected_zone_total_from_testdata(data: dict) -> int | None:
    plans = data.get("Floor plans") or []
    totals = [
        plan.get("thermal_zones")
        for plan in plans
        if isinstance(plan, dict) and isinstance(plan.get("thermal_zones"), int)
    ]
    return sum(totals) if totals else None


def dimensioned_view_names(case_dir: Path | str) -> set[str]:
    data = load_case_metadata(case_dir)
    names: set[str] = set()

    def add(value: object) -> None:
        if not isinstance(value, str) or not value:
            return
        p = Path(value)
        names.add(p.stem if p.suffix else value)

    for value in data.get("dimensioned_views") or []:
        add(value)

    for item in data.get("Floor plans") or []:
        if isinstance(item, dict) and item.get("dimensioned") is True:
            add(item.get("path"))
            add(f"{item.get('floor')}f_view" if item.get("floor") is not None else "")

    views = data.get("views") or {}
    if isinstance(views, dict):
        for key, item in views.items():
            if isinstance(item, dict) and item.get("dimensioned") is True:
                add(key)
                add(item.get("path"))

    return names
