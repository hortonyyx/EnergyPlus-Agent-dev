"""Regression anchor for gt_from_dxf.py (CAD→gt extraction, plan §9).

Extracting from the 天正「图形导出」 source.dxf must reconcile with the independently
human-read gt: same footprint, same per-facade/floor window counts, same exterior
doors — and ADD exact per-window openings (x_m, width_m) the human gt lacked. If a
future DXF re-export or extractor change breaks that reconciliation, this fails."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import gt_from_dxf as gfd  # noqa: E402

_HAS_DXF = (gfd.GT_DIR / "sm21_anchor" / "source.dxf").exists()
pytestmark = pytest.mark.skipif(not _HAS_DXF, reason="sm21_anchor/source.dxf not present")


@pytest.fixture(scope="module")
def result():
    return gfd.extract("sm21_anchor")


def test_footprint_matches_gt(result):
    rep = result["report"]
    assert rep["footprint_cad"] == {"W_m": 15.0, "D_m": 8.0}
    assert rep["footprint_cad"]["W_m"] == rep["footprint_gt"]["W_m"]
    assert rep["footprint_cad"]["D_m"] == rep["footprint_gt"]["D_m"]


def test_all_window_counts_reconcile(result):
    rows = result["report"]["rows"]
    assert rows, "no window rows extracted"
    mismatches = [(r["facade"], r["floor"], r["gt_count"], r["cad_count"])
                  for r in rows if not r["match"]]
    assert not mismatches, f"CAD/gt window-count mismatches: {mismatches}"


def test_exterior_doors_match_gt(result):
    # gt: South-F1 (main entrance) + West-F1 (secondary). order-independent.
    assert set(result["report"]["doors_cad"]) == {("South", "Floor 1"), ("West", "Floor 1")}


def test_openings_are_exact_and_sane(result):
    """Every CAD-counted window carries an x_m + width_m; widths are positive metres."""
    rows = result["report"]["rows"]
    for r in rows:
        for o in r["openings"]:
            assert "x_m" in o and "width_m" in o
            assert 0.1 <= o["width_m"] <= 6.0
            assert -0.5 <= o["x_m"] <= 15.0
    # spot-check the verified facts: South-F1 = one small (1.2) + two large (2.4)
    s_f1 = next(r for r in rows if r["facade"] == "South" and r["floor"] == "Floor 1")
    widths = sorted(o["width_m"] for o in s_f1["openings"])
    assert widths == [1.2, 2.4, 2.4]
    # North-F2 = two 3.6 m windows
    n_f2 = next(r for r in rows if r["facade"] == "North" and r["floor"] == "Floor 2")
    assert sorted(o["width_m"] for o in n_f2["openings"]) == [3.6, 3.6]


def test_proposed_gt_is_v2_with_fingerprint(result):
    p = result["proposed"]
    assert p["schema_version"] == 2
    assert p["_source"] == "cad_dxf"
    assert len(p["_cad_sha256"]) == 64
    # openings injected into window entries that had CAD matches
    assert any("openings" in w for w in p["windows"])
