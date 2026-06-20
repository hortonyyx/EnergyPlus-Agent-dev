"""Regression anchor for gt_from_dxf.py (DXF-primary gt builder, plan §9).

The DXF-built gt must reconcile with the independently human-read gt: same footprint,
same zonification (counts + layout), same per-facade/floor window counts, same exterior
doors — and ADD machine-exact detail the human gt lacked (per-window x/width and
per-opening sill/head). Roles come from the auxiliary map (DXF has no room labels). If
a DXF re-export or extractor change breaks the reconciliation, this fails."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import gt_from_dxf as gfd  # noqa: E402

_HAS_DXF = (gfd.GT_DIR / "sm21_anchor" / "source.dxf").exists()
pytestmark = pytest.mark.skipif(not _HAS_DXF, reason="sm21_anchor/source.dxf not present")


@pytest.fixture(scope="module")
def built():
    return gfd.build("sm21_anchor")


def test_footprint(built):
    assert built["gt"]["footprint"] == {"W_m": 15.0, "D_m": 8.0}


def test_self_consistent(built):
    assert gfd._self_check(built["gt"]) == []      # zones tile footprint, counts==openings


def test_zones_reconstructed_from_walls(built):
    floors = {f["name"]: f for f in built["gt"]["floors"]}
    assert floors["Floor 1"]["zone_count"] == 7
    assert floors["Floor 2"]["zone_count"] == 7
    f1 = {z["id"]: z for z in floors["Floor 1"]["zones"]}
    # geometry from the wall grid + roles from the auxiliary map
    assert f1["F1_S3"]["role"] == "meeting" and f1["F1_S3"]["rect_m"] == [10.0, 0.0, 15.0, 3.0]
    assert f1["F1_N1"]["role"] == "office" and f1["F1_N1"]["rect_m"] == [0.0, 5.0, 5.0, 8.0]
    assert f1["F1_COR"]["role"] == "corridor" and f1["F1_COR"]["rect_m"] == [0.0, 3.0, 15.0, 5.0]
    f2 = {z["id"]: z for z in floors["Floor 2"]["zones"]}
    assert [z for z in ("F2_N1", "F2_N2") if f2[z]["role"] == "meeting"] == ["F2_N1", "F2_N2"]
    assert f2["F2_S1"]["rect_m"] == [0.0, 0.0, 3.75, 3.0]


def test_floor_heights_from_elevation(built):
    floors = {f["name"]: f for f in built["gt"]["floors"]}
    assert floors["Floor 1"]["z_floor"] == 0.0 and floors["Floor 1"]["ceiling_height"] == 3.0
    assert floors["Floor 2"]["z_floor"] == 3.0 and floors["Floor 2"]["ceiling_height"] == 3.6


def test_window_counts(built):
    counts = {(w["facade"], w["floor"]): w["count"] for w in built["gt"]["windows"]}
    assert counts[("North", "Floor 1")] == 3 and counts[("South", "Floor 1")] == 3
    assert counts[("East", "Floor 1")] == 1 and counts[("West", "Floor 1")] == 0
    assert counts[("North", "Floor 2")] == 2 and counts[("South", "Floor 2")] == 4
    assert counts[("East", "Floor 2")] == 1 and counts[("West", "Floor 2")] == 1


def test_exterior_doors_match(built):
    assert {(d["facade"], d["floor"]) for d in built["gt"]["doors"]} == \
        {("South", "Floor 1"), ("West", "Floor 1")}


def test_openings_carry_exact_x_and_per_opening_z(built):
    wins = {(w["facade"], w["floor"]): w for w in built["gt"]["windows"]}
    # South-F1 = small (1.2) + two large (2.4); the small one has its own raised sill
    sf1 = wins[("South", "Floor 1")]["openings"]
    assert sorted(o["width_m"] for o in sf1) == [1.2, 2.4, 2.4]
    small = min(sf1, key=lambda o: o["width_m"])
    assert small["sill_m"] == 1.5 and small["head_m"] == 2.1     # CAD-precise, not facade-uniform
    # East/West F2 windows are 1.2 m tall (head 5.2), not the human gt's 5.8
    assert wins[("East", "Floor 2")]["openings"][0]["head_m"] == 5.2


def test_gt_is_v2_with_fingerprint(built):
    gt = built["gt"]
    assert gt["schema_version"] == 2 and gt["_source"] == "cad_dxf"
    assert len(gt["_cad_sha256"]) == 64
    assert all("openings" in w for w in gt["windows"] if w["count"])
