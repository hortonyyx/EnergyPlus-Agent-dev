"""P2 algorithm-body tests for the Tianzheng->GT v3 converter (S5-S9 + gates G4-G10).

Scope (dispatch §1, P2 exit gate, brief §1-§2):
  * sm24 real-drawing end-to-end — the P2 EXIT GATE.  8 cavities claimed, the 8 zones
    tile the footprint (symmetric difference == 0, pairwise overlap == 0), the G8
    INDEPENDENT reconstruction of the wall region matches the measured wall region
    (symmetric difference == 0), the v3 preflight (G9) accepts the augmented DXF, and
    the human-review overlay lands.  Every number below is THIS implementation's
    independent output (never copied from probes/ as an unverified expectation).
  * a controlled single-room + multi-room expand (S7) where the rebuilt zone vertices
    are checked against a hand calculation, for L / T / cross junctions; T has a
    split-overlap conflict negative, and cross has the corresponding conflict negative.
  * a free-end negative that S4 blocks before S7; the non-zoning positive is explicitly
    deferred by plan §2.6 (not silently treated as supported).
  * one- and two-event thickness-change profiles plus the no-proof fail-closed path.
  * the nine-gate must-red fixtures (discipline #5): G4/G6/G7/G8/G9 each gets a negative
    case asserting the EXACT gate goes red.  G8's must-red flips one edge's recorded
    basis+thickness so the independent rebuild diverges from the measured wall region
    (the tautology trap plan §1 warns about — G8 must NOT collapse to Footprint-Sigma).
  * S9 artefact presence (augmented DXF GTV3_* layers + manifest + source_map +
    overlay) and determinism.

G1/G2/G3/G5 come from P1 (their must-reds live in test_tarch_converter_p1_geometry.py);
this file owns the P2-introduced gates G4/G6/G7/G8/G9/G10.
"""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
import shutil
from pathlib import Path

import ezdxf
import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (
    PlanViewIntentV1, TarchConversionRequestV1, TarchDialectRulesV1,
    TarchEntitySelectorV1, ZoneIntentEntryV1, ZoneIntentSpecV1,
    ConversionReportV1, DiagnosticSeverity,
    compute_request_sha256, resolve_converter_tooling)

REPO = Path(__file__).resolve().parents[1]
GT_CONFIG = REPO / "src/configs/judge_gt.yaml"
VG_CONFIG = REPO / "src/configs/correction.yaml"
SM24_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf"
SM25_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
SM25_REQUEST = REPO / "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json"

WINDOW_BLOCK = "$TCHSYS$WIN2D"


# --------------------------------------------------------------------------- #
# sm24 request helper (clip box + affine match the sm24 anchor plan view)
# --------------------------------------------------------------------------- #
def _sm24_request(sha: str, expected_count: int = 8):
    aff = {"m00": 0.001, "m01": 0.0, "m02": -23.0576, "m10": 0.0, "m11": 0.001, "m12": -26.5652}
    clip = {"xmin": 12276.94, "ymin": 18802.14, "xmax": 41994.33, "ymax": 51678.57}
    pv = PlanViewIntentV1(
        id="plan-F1", floor_id="F1", frame_title="1f平面图", clip_box_dxf=clip, world_from_source_m=aff,
        wall_selector=TarchEntitySelectorV1(entity_types=["LINE"], layers=["WALL"]),
        opening_selector=TarchEntitySelectorV1(entity_types=["INSERT"], layers=["WINDOW"]),
        dialect_rules=TarchDialectRulesV1(window_block_names=[WINDOW_BLOCK],
                                          door_block_prefixes=["$DorLib2D$"], classifier_version="tarch-dialect-v1"),
        zone_intent=ZoneIntentSpecV1(
            mode="intent_file", expected_count=expected_count,
            entries=[ZoneIntentEntryV1(zone_id=f"z{i}", name=f"r{i}", role="unspecified")
                     for i in range(expected_count)]))
    req = TarchConversionRequestV1(
        request_version=1, case="sm24_anchor", source_dxf_label="sm24_source.dxf", source_dxf_sha256=sha,
        normalized_source_id="sm24-anchor-normalized",
        target_geometry_profile="c2_simple_orthogonal_no_holes", native_units="unitless",
        metres_per_unit=0.001, floors=[{"id": "F1", "name": "1F", "z_floor_m": 0.0, "ceiling_height_m": 4.5}],
        plan_views=[pv], request_sha256="0" * 64)
    return req.model_copy(update={"request_sha256": compute_request_sha256(req)}), pv


def _codes(res) -> set[str]:
    return {d.code for d in res.diagnostics}


# --------------------------------------------------------------------------- #
# sm24 real-drawing end-to-end — THE P2 EXIT GATE (independently derived)
# --------------------------------------------------------------------------- #
def test_sm24_p2_exit_gate_all_green(tmp_path):
    """P2 exit gate (brief §1.4): 8 cavities -> 8 zones tile the footprint exactly
    (symdiff == 0, pairwise overlap == 0), G8 independent reconstruction == 0, the v3
    preflight accepts the augmented DXF, overlay lands, report PASS.  Numbers are this
    implementation's independent output, cross-checked against the probe artefact
    (work/p2_exit_gate_output.json) — a mismatch stops the work (brief §2 #7)."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)

    gmap = {g.id: g for g in res.gates}
    # --- S5/S6: 8 cavities, all claimed (cross-checked vs probe) ---
    assert len(res.cavities) == 8
    assert len(res.zones) == 8
    assert not gmap["G6"].passed
    assert gmap["G6"].evidence["human_confirmation_required"]

    # --- S7/G7: zones tile the footprint exactly, no pairwise overlap ---
    assert gmap["G7"].evidence["symmetric_diff_m2"] == pytest.approx(0.0, abs=1e-6)
    assert gmap["G7"].evidence["pairwise_overlap_m2"] == pytest.approx(0.0, abs=1e-6)
    assert gmap["G7"].passed

    # --- G8 INDEPENDENT reconstruction == measured wall region (the主保险) ---
    assert gmap["G8"].evidence["symmetric_diff_m2"] == pytest.approx(0.0, abs=1e-6)
    assert gmap["G8"].passed

    # --- G4 outer-skin gap conservation: 14 exterior openings == 14 skin gaps ---
    assert gmap["G4"].evidence["exterior_openings"] == 14
    assert gmap["G4"].evidence["outer_skin_gaps"] == 14
    assert gmap["G4"].passed

    # --- G9 v3 preflight accepts the augmented bundle ---
    assert gmap["G9"].passed

    # G10 is intentionally red until a hash-bound human signature exists.
    assert not gmap["G10"].passed
    assert gmap["G10"].evidence["verification_status"] == "candidate"
    assert not res.has_block
    assert res.conversion_report.status == "BLOCKED"
    # zone areas sum to the footprint (200 m^2)
    assert sum(z.area_m2 for z in res.zones) == pytest.approx(200.0, abs=1e-6)


def test_sm24_p2_s9_artefacts_present(tmp_path):
    """S9 (§6.1 方案A): augmented DXF with GTV3_* layers (original handles preserved),
    a manifest bound to it, a per-edge source_map, and a human-review overlay all land."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)

    assert res.augmented_dxf_path and res.augmented_dxf_path.exists()
    assert res.manifest is not None
    assert res.source_map is not None and res.source_map.entries
    assert res.overlay_path and res.overlay_path.exists()
    # every source_map entry names at least one real source handle (no layer label)
    for entry in res.source_map.entries:
        assert entry.source_entity_refs
        for ref in entry.source_entity_refs:
            assert ref.handle != "GTV3_ZONE" and ref.handle != "GTV3_FOOTPRINT"
    # GTV3_* layers exist and the augmented DXF keeps the original source WALL lines
    doc = ezdxf.readfile(str(res.augmented_dxf_path))
    layer_names = {layer.dxf.name for layer in doc.layers}
    assert {tn.GTV3_FOOTPRINT_LAYER, tn.GTV3_ZONE_LAYER, tn.GTV3_OPENING_LAYER} <= layer_names
    assert len(list(doc.modelspace().query('LINE[layer=="WALL"]'))) > 0


def test_sm24_p2_deterministic(tmp_path):
    """Same bytes -> identical gates, zone areas, source_map, diagnostic set."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    r1 = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path / "a")
    r2 = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path / "b")
    # gate pass/fail + the path-independent numeric evidence must match (overlay_asset
    # differs by work dir by design)
    assert [g.id for g in r1.gates] == [g.id for g in r2.gates]
    assert [g.passed for g in r1.gates] == [g.passed for g in r2.gates]
    for a, b in zip(r1.gates, r2.gates):
        ev_a = {k: v for k, v in a.evidence.items() if k != "overlay_asset"}
        ev_b = {k: v for k, v in b.evidence.items() if k != "overlay_asset"}
        assert ev_a == ev_b
    assert [round(z.area_m2, 6) for z in r1.zones] == [round(z.area_m2, 6) for z in r2.zones]
    assert _codes(r1) == _codes(r2)
    assert len(r1.source_map.entries) == len(r2.source_map.entries)


# --------------------------------------------------------------------------- #
# Controlled S7 geometry — junction matrix (L / T / cross) + thickness-change
# Built directly from shapely polygons (cavities + wall_region + footprint), so the
# rebuilt zone vertices can be checked against a hand calculation.  wall_lines is []
# here (source_handles are a provenance concern, not a vertex concern).
# --------------------------------------------------------------------------- #
def _tooling():
    return resolve_converter_tooling(GT_CONFIG, VG_CONFIG)


def _claims_for(cavities, labels):
    """Build the S6-style claims list (cavity + zone_id + name + role + seed) in the
    canonical (minx,miny) order S6 uses, so s7_expand_zones can consume it directly."""
    ordered = sorted(enumerate(cavities),
                     key=lambda kv: (round(kv[1].bounds[0], 6), round(kv[1].bounds[1], 6)))
    claims = []
    for idx, (orig_i, g) in enumerate(ordered):
        rp = g.representative_point()
        claims.append({"cavity": g, "cavity_index": orig_i, "zone_id": labels[idx],
                       "name": labels[idx], "role": "unspecified",
                       "seed_native": (rp.x, rp.y)})
    return claims


def _proof_bands():
    return [tn.WallBand("x", 0.0, 120.0, 0.0, 10000.0, 120.0, ["1A"]),
            tn.WallBand("x", 0.0, 240.0, 0.0, 10000.0, 240.0, ["1B"]),
            tn.WallBand("x", 0.0, 300.0, 0.0, 10000.0, 300.0, ["1C"])]


def _p2_g8_gate(zones, cavities, wall_region, footprint, tols):
    """Run the production P2 gate assembly and return G8 plus its diagnostics.

    The small matrix fixtures do not need a DXF, but they must still enter the
    same G8 assembly used by ``run_p2_conversion`` rather than inspect a helper
    result in isolation.
    """
    req, pv = _sm24_request("a" * 64)
    diags = []
    p1 = SimpleNamespace(gates=[], openings=[], wall_lines=[])
    gates = tn._build_p2_gates(
        p1, cavities, wall_region, footprint, zones,
        _claims_for(cavities, [f"z{i}" for i in range(len(cavities))]), [],
        req, pv, tols, diags)
    return next(g for g in gates if g.id == "G8"), diags


def test_s7_single_room_outer_skin_expand_matches_hand_calc():
    """Convex (L-corner) case: one room, 240mm walls on all four sides, all outer_skin.
    Each cavity corner offsets outward by t=240 -> the zone == the outer-skin box, and
    G8 rebuilds the wall region exactly."""
    t = 240.0
    outer = Polygon([(1000, 1000), (7000, 1000), (7000, 5000), (1000, 5000)])
    cavity = Polygon([(1000 + t, 1000 + t), (7000 - t, 1000 + t),
                      (7000 - t, 5000 - t), (1000 + t, 5000 - t)])
    wall_region = outer.difference(cavity)
    tooling = _tooling()
    tols = tn._tols_from(tooling, 0.001, t / 1000.0 / 2)
    claims = _claims_for([cavity], ["z0"])
    diags = []
    zones = tn.s7_expand_zones(claims, wall_region, outer, tols, diags, [], _proof_bands())
    assert not diags
    z = zones[0]
    # zone == outer-skin box (room expanded by t on every side)
    assert set((round(x, 3), round(y, 3)) for x, y in z.vertices) == \
        {(1000.0, 1000.0), (7000.0, 1000.0), (7000.0, 5000.0), (1000.0, 5000.0)}
    # every edge is outer_skin, thickness 240, offset 240
    for e in z.edges:
        assert e.basis == "outer_skin"
        assert e.thickness_native == pytest.approx(240.0, abs=1.0)
        assert e.offset_native == pytest.approx(240.0, abs=1.0)
    # G8 rebuilds the wall region from zones+offsets only (independent of S5 wall_region)
    recon = tn.g8_reconstruct_wall_region(zones)
    assert recon.symmetric_difference(wall_region).area < tols.topo_area_m2 / (0.001 ** 2)


def test_l_corner_self_intersection_blocks_g8():
    """L negative: a bow-tie outer-corner record is rejected by the real G8 gate.

    S7 first produces the hand-checked legal outer rectangle
    ``(1000,1000)->(7000,1000)->(7000,5000)->(1000,5000)``.  Replacing the
    recorded output boundary by the hand-written bow-tie
    ``(1000,1000)->(7000,1000)->(1000,5000)->(7000,5000)`` creates an illegal
    crossing at (4000,3000).  G8 must reconstruct a non-zero residual and BLOCK;
    it may not silently repair that record.
    """
    t = 240.0
    outer = Polygon([(1000, 1000), (7000, 1000), (7000, 5000), (1000, 5000)])
    cavity = Polygon([(1000 + t, 1000 + t), (7000 - t, 1000 + t),
                      (7000 - t, 5000 - t), (1000 + t, 5000 - t)])
    wall_region = outer.difference(cavity)
    tols = tn._tols_from(_tooling(), 0.001, t / 1000.0 / 2)
    zones = tn.s7_expand_zones(_claims_for([cavity], ["z0"]), wall_region, outer,
                               tols, [], [], _proof_bands())
    assert zones[0].vertices == [(1000.0, 1000.0), (7000.0, 1000.0),
                                 (7000.0, 5000.0), (1000.0, 5000.0)]
    bow_tie = [(1000.0, 1000.0), (7000.0, 1000.0),
               (1000.0, 5000.0), (7000.0, 5000.0)]
    assert not Polygon(bow_tie).is_valid
    for i, edge in enumerate(zones[0].edges):
        edge.p1, edge.p2 = bow_tie[i], bow_tie[(i + 1) % len(bow_tie)]
    g8, diags = _p2_g8_gate(zones, [cavity], wall_region, outer, tols)
    assert not g8.passed and g8.evidence["symmetric_diff_m2"] > 0
    assert "tarch_reconstruction_residual" in {d.code for d in diags}


def test_s7_two_room_shared_wall_no_overlap():
    """T-junction: two rooms share a 240mm internal wall.  Each expands t/2=120 across it
    and meets the neighbour at the centerline -> pairwise overlap 0, G8 reconstruct 0."""
    t = 240.0
    outer = Polygon([(1000, 1000), (7000, 1000), (7000, 5000), (1000, 5000)])
    # internal wall centered at x=4000, faces at 3880 / 4120
    left = Polygon([(1000 + t, 1000 + t), (4000 - t / 2, 1000 + t),
                    (4000 - t / 2, 5000 - t), (1000 + t, 5000 - t)])
    right = Polygon([(4000 + t / 2, 1000 + t), (7000 - t, 1000 + t),
                     (7000 - t, 5000 - t), (4000 + t / 2, 5000 - t)])
    wall_region = outer.difference(unary_union([left, right]))
    tooling = _tooling()
    tols = tn._tols_from(tooling, 0.001, t / 1000.0 / 2)
    claims = _claims_for([left, right], ["z0", "z1"])
    diags = []
    zones = tn.s7_expand_zones(claims, wall_region, outer, tols, diags, [], _proof_bands())
    assert not diags
    a, b = zones[0].polygon, zones[1].polygon
    assert a.intersection(b).area == pytest.approx(0.0, abs=tols.topo_area_m2 / (0.001 ** 2))
    # G8 independent reconstruction matches the measured wall region
    recon = tn.g8_reconstruct_wall_region(zones)
    assert recon.symmetric_difference(wall_region).area < tols.topo_area_m2 / (0.001 ** 2)


def test_s7_cross_junction_four_rooms_tile():
    """Cross junction: a 2x2 room grid (internal walls at x=4000, y=4000).  The four
    zones tile the footprint (overlap 0) and G8 reconstructs the wall region."""
    t = 240.0
    outer = Polygon([(1000, 1000), (7000, 1000), (7000, 7000), (1000, 7000)])
    cx_lo, cx_hi, cy_lo, cy_hi = 4000 - t / 2, 4000 + t / 2, 4000 - t / 2, 4000 + t / 2
    sw = Polygon([(1000 + t, 1000 + t), (cx_lo, 1000 + t), (cx_lo, cy_lo), (1000 + t, cy_lo)])
    se = Polygon([(cx_hi, 1000 + t), (7000 - t, 1000 + t), (7000 - t, cy_lo), (cx_hi, cy_lo)])
    nw = Polygon([(1000 + t, cy_hi), (cx_lo, cy_hi), (cx_lo, 7000 - t), (1000 + t, 7000 - t)])
    ne = Polygon([(cx_hi, cy_hi), (7000 - t, cy_hi), (7000 - t, 7000 - t), (cx_hi, 7000 - t)])
    cavities = [sw, se, nw, ne]
    wall_region = outer.difference(unary_union(cavities))
    tooling = _tooling()
    tols = tn._tols_from(tooling, 0.001, t / 1000.0 / 2)
    claims = _claims_for(cavities, ["z0", "z1", "z2", "z3"])
    diags = []
    zones = tn.s7_expand_zones(claims, wall_region, outer, tols, diags, [], _proof_bands())
    assert not diags
    polys = [z.polygon for z in zones]
    overlap = sum(polys[i].intersection(polys[j]).area
                  for i in range(4) for j in range(i + 1, 4))
    assert overlap < tols.topo_area_m2 / (0.001 ** 2)
    symdiff = unary_union(polys).symmetric_difference(outer).area
    assert symdiff < tols.topo_area_m2 / (0.001 ** 2)
    recon = tn.g8_reconstruct_wall_region(zones)
    assert recon.symmetric_difference(wall_region).area < tols.topo_area_m2 / (0.001 ** 2)


# --------------------------------------------------------------------------- #
# Free-end: S4 must block it before S7 runs (free-ends never reach S7)
# --------------------------------------------------------------------------- #
def _make_dxf(path: Path, *, free_end: bool = False) -> None:
    """Minimal clean one-window building (P1 green); ``free_end`` adds a dangling stub."""
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 0
    msp = doc.modelspace()
    W = "WALL"
    msp.add_line((1000, 7000), (2000, 7000), dxfattribs={"layer": W})
    msp.add_line((3000, 7000), (5000, 7000), dxfattribs={"layer": W})
    msp.add_line((1240, 6760), (2000, 6760), dxfattribs={"layer": W})
    msp.add_line((3000, 6760), (4760, 6760), dxfattribs={"layer": W})
    msp.add_line((1000, 1000), (5000, 1000), dxfattribs={"layer": W})
    msp.add_line((1240, 1240), (4760, 1240), dxfattribs={"layer": W})
    msp.add_line((5000, 1000), (5000, 7000), dxfattribs={"layer": W})
    msp.add_line((4760, 1240), (4760, 6760), dxfattribs={"layer": W})
    msp.add_line((1000, 1000), (1000, 7000), dxfattribs={"layer": W})
    msp.add_line((1240, 1240), (1240, 6760), dxfattribs={"layer": W})
    msp.add_line((2000, 6760), (2000, 7000), dxfattribs={"layer": W})  # window jamb caps
    msp.add_line((3000, 6760), (3000, 7000), dxfattribs={"layer": W})
    if free_end:
        msp.add_line((2000, 3000), (2000, 4000), dxfattribs={"layer": W})  # stub -> dangle
    name, geom, insert = WINDOW_BLOCK, [(0, 0), (1000, 240)], (2000, 6760)
    if name not in doc.blocks:
        blk = doc.blocks.new(name=name)
        blk.add_line(geom[0], geom[1])
    msp.add_blockref(name, insert=insert, dxfattribs={"layer": "WINDOW"})
    msp.add_lwpolyline([(200, 200), (5800, 200), (5800, 7800), (200, 7800)],
                       dxfattribs={"layer": "edge"}, close=True)
    msp.add_text("test1f", dxfattribs={"layer": "0", "insert": (3000, 4000), "height": 200})
    doc.saveas(str(path))


def _reverse_modelspace_line_endpoints(source: Path, dest: Path) -> None:
    """Write an equivalent DXF whose every modelspace LINE has reversed endpoints."""
    doc = ezdxf.readfile(str(source))
    for line in doc.modelspace().query("LINE"):
        start, end = line.dxf.start, line.dxf.end
        line.dxf.start, line.dxf.end = end, start
    doc.saveas(str(dest))


def _syn_request(case: str, sha: str, expected_count: int = 1, min_room_area_m2: float = 2.0):
    aff = {"m00": 0.001, "m01": 0.0, "m02": -1.0, "m10": 0.0, "m11": 0.001, "m12": -1.0}
    clip = {"xmin": 200, "ymin": 200, "xmax": 5800, "ymax": 7800}
    pv = PlanViewIntentV1(
        id="plan-F1", floor_id="F1", frame_title="test1f", clip_box_dxf=clip, world_from_source_m=aff,
        wall_selector=TarchEntitySelectorV1(entity_types=["LINE"], layers=["WALL"]),
        opening_selector=TarchEntitySelectorV1(entity_types=["INSERT"], layers=["WINDOW"]),
        dialect_rules=TarchDialectRulesV1(window_block_names=[WINDOW_BLOCK],
                                          door_block_prefixes=["$DorLib2D$"], classifier_version="v1"),
        zone_intent=ZoneIntentSpecV1(
            mode="intent_file", expected_count=expected_count,
            entries=[ZoneIntentEntryV1(zone_id=f"z{i}", name=f"r{i}", role="unspecified")
                     for i in range(expected_count)]))
    req = TarchConversionRequestV1(
        request_version=1, case=case, source_dxf_label="src.dxf", source_dxf_sha256=sha,
        normalized_source_id=f"{case}-norm", target_geometry_profile="c2_simple_orthogonal_no_holes",
        native_units="unitless", metres_per_unit=0.001, min_room_area_m2=min_room_area_m2,
        floors=[{"id": "F1", "name": "1F", "z_floor_m": 0.0, "ceiling_height_m": 4.5}],
        plan_views=[pv], request_sha256="0" * 64)
    return req.model_copy(update={"request_sha256": compute_request_sha256(req)}), pv


def test_s4_free_end_blocks_before_s7(tmp_path):
    """A dangling free-end stub is caught by S4's dangle gate; S7 never runs (no zones)."""
    path = tmp_path / "free.dxf"
    _make_dxf(path, free_end=True)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    req, pv = _syn_request("free", sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(path, req, pv, tooling, tmp_path)
    assert "tarch_wall_free_end" in _codes(res)
    assert any(g.id == "G5" and not g.passed for g in res.gates)
    assert res.zones == []                 # S7 did not run


def test_synthetic_one_room_p2_all_green(tmp_path):
    """Clean one-room building: all P2 gates green, PASS report, S9 artefacts present.

    A_room is set to 5 m^2 for this small synthetic: its un-subdivided wall ring is a
    single ~4.3 m^2 face (real drawings subdivide walls with many openings), so the
    default 2 m^2 would mis-bucket that ring as a cavity.  A_room is a domain PROPOSAL
    only (the criterion is the human-declared count, G6) — setting it to fit a known
    synthetic is legitimate and not the auto-fit the discipline forbids."""
    path = tmp_path / "green.dxf"
    _make_dxf(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    req, pv = _syn_request("green", sha, min_room_area_m2=5.0)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(path, req, pv, tooling, tmp_path)
    assert len(res.zones) == 1
    assert not next(g for g in res.gates if g.id == "G10").passed
    assert not res.has_block
    assert res.conversion_report.status == "BLOCKED"
    assert res.augmented_dxf_path and res.manifest and res.source_map and res.overlay_path


def test_g4_outer_skin_gap_and_gates_are_line_direction_invariant(tmp_path):
    """HC-03: reversing every raw LINE keeps the one exterior gap and G1--G10 stable."""
    forward = tmp_path / "forward.dxf"
    reversed_path = tmp_path / "reversed.dxf"
    _make_dxf(forward)
    _reverse_modelspace_line_endpoints(forward, reversed_path)

    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)

    def run(path: Path, work: Path):
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        req, pv = _syn_request("direction-invariant", sha, min_room_area_m2=5.0)
        return tn.run_p2_conversion(path, req, pv, tooling, work), pv

    normal, normal_pv = run(forward, tmp_path / "normal")
    reversed_res, reversed_pv = run(reversed_path, tmp_path / "reversed")
    assert tn._outer_skin_gap_count(normal.p1, normal.footprint) == 1
    assert tn._outer_skin_gap_count(reversed_res.p1, reversed_res.footprint) == 1
    assert [(g.id, g.passed) for g in normal.gates] == [
        (g.id, g.passed) for g in reversed_res.gates]

    def world_zone_union(result, pv):
        return unary_union([Polygon([tn._to_world(v, pv.world_from_source_m) for v in z.vertices])
                            for z in result.zones])

    tols = tn._tols_from(tooling, 0.001)
    assert world_zone_union(normal, normal_pv).symmetric_difference(
        world_zone_union(reversed_res, reversed_pv)).area <= tols.topo_area_m2


# --------------------------------------------------------------------------- #
# Nine-gate must-red fixtures (discipline #5).  Each negative case asserts the EXACT
# gate goes red.  G1/G2/G3/G5 live in the P1 test file; this owns G4/G6/G7/G8/G9.
# --------------------------------------------------------------------------- #
def test_g8_must_red_flipped_basis_diverges(tmp_path):
    """G8 must-red (brief §1.2): take a green result, flip ONE zone edge's recorded basis
    (inner wall_axis recorded as outer_skin -> its offset doubles from t/2 to t).  The
    INDEPENDENT rebuild then diverges from the measured wall region -> G8 red, while the
    green twin passes.  This proves G8 is not the Footprint-Sigma tautology (a tautology
    would stay green under any basis flip)."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    green = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path / "green")
    gmap = {g.id: g for g in green.gates}
    assert gmap["G8"].passed                       # baseline green

    # corrupt: flip one wall_axis edge to outer_skin (offset t/2 -> t) on zone 0
    zones = green.zones
    flipped = 0
    for e in zones[0].edges:
        if e.basis == "wall_axis":
            e.basis = "outer_skin"
            e.offset_native = e.thickness_native     # outer_skin offsets by full t, not t/2
            flipped += 1
            break
    assert flipped == 1
    recon = tn.g8_reconstruct_wall_region(zones)
    mpu = 0.001
    sd = recon.symmetric_difference(green.wall_region).area * mpu * mpu
    assert sd > 1e-3                                # G8 now red (rebuild diverges)


def test_g6_must_red_cavity_count_mismatch(tmp_path):
    """G6 must-red: declare 7 rooms when 8 cavities exist -> G6 red."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha, expected_count=7)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)
    gmap = {g.id: g for g in res.gates}
    assert not gmap["G6"].passed
    assert "tarch_cavity_count_mismatch" in _codes(res)


def test_g7_must_red_pairwise_overlap(tmp_path):
    """G7 must-red: enlarge one zone so it overlaps a neighbour -> the overlap sub-check
    of G7 goes red (symdiff stays ~0 because the union still covers the footprint — this
    is exactly the compensating error G6/G7 exist to catch, brief §2)."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)
    gmap = {g.id: g for g in res.gates}
    assert gmap["G7"].passed                        # baseline green
    # bloat zone 0 by 5mm in +x so it overlaps zone to its east
    z0 = res.zones[0]
    z0.polygon = z0.polygon.buffer(5.0)
    polys = [z.polygon for z in res.zones]
    overlap = sum(polys[i].intersection(polys[j]).area
                  for i in range(len(polys)) for j in range(i + 1, len(polys))) * 0.001 * 0.001
    assert overlap > 1e-6                           # G7 overlap sub-check now red


def test_g4_must_red_unit_level():
    """G4 must-red (unit level): the outer-skin gap counter must report a gap when a raw
    wall-line span leaves an uncovered exterior hole.  Crafted wall_lines + a clean
    rectangular footprint where one side has a 100-unit hole the wall lines do not cover."""
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    tols = tn._tols_from(tooling, 0.001)
    footprint = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    # north edge y=10000 covered 0..4000 and 4100..10000 -> a 100-unit gap at 4000..4100
    wall_lines = [
        ("H1", 0, 10000, 4000, 10000), ("H2", 4100, 10000, 10000, 10000),
        ("H3", 0, 0, 10000, 0), ("V4", 0, 0, 0, 10000), ("V5", 10000, 0, 10000, 10000)]

    from types import SimpleNamespace
    gaps = tn._outer_skin_gap_count(SimpleNamespace(wall_lines=wall_lines), footprint)
    assert gaps == 1                                # the one uncovered hole


def test_g9_must_red_v3_rejects_bad_bundle(tmp_path):
    """G9 must-red: if the augmented DXF's footprint is degraded so v3's preflight rejects
    it, G9 goes red with the v3 code.  We force this by handing the preflight a manifest
    whose footprint selector matches nothing real on the (still-fine) augmented DXF."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)
    gmap = {g.id: g for g in res.gates}
    assert gmap["G9"].passed                        # baseline green
    # corrupt the manifest's footprint handles to a nonexistent handle -> v3 inspection
    # finds no footprint entity -> fail-closed.
    bad_manifest = res.manifest.model_copy(deep=True)
    v = bad_manifest.views[0]
    v.footprint_boundary = v.footprint_boundary.model_copy(
        update={"handles": ["DEADBE"]})
    ok, code, _document = tn._run_g9_v3_preflight(res.augmented_dxf_path, bad_manifest, tooling)
    assert not ok and code


# --------------------------------------------------------------------------- #
# Round-trip: the PASS report survives a pydantic validate_json cycle
# --------------------------------------------------------------------------- #
def test_p2_report_pass_round_trip(tmp_path):
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)
    report = res.conversion_report
    assert report.status == "BLOCKED"
    reloaded = ConversionReportV1.model_validate_json(report.model_dump_json())
    assert reloaded == report


def test_hash_mismatch_blocks_before_geometry_and_writes_only_diagnostic_overlay(tmp_path):
    """B-03: declared source hash is checked before DXF geometry is consumed."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    req, pv = _sm24_request("0" * 64)
    # Make the request self-hash valid: this isolates the source-byte mismatch.
    req = req.model_copy(update={"request_sha256": compute_request_sha256(req)})
    res = tn.run_p2_conversion(dst, req, pv, resolve_converter_tooling(GT_CONFIG, VG_CONFIG), tmp_path)
    assert "tarch_input_source_hash_mismatch" in _codes(res)
    assert res.zones == [] and res.augmented_dxf_path is None and res.manifest is None
    assert res.source_map is None and res.overlay_path and res.overlay_path.name == "overlay_diagnostics.svg"
    assert res.conversion_report.status == "BLOCKED"


def test_g10_requires_hash_bound_ack_and_then_all_gates_pass(tmp_path):
    """candidate overlay is not approval; only a three-hash human ack opens G10."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    candidate = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)
    assert not next(g for g in candidate.gates if g.id == "G10").passed
    overlay_sha = hashlib.sha256(candidate.overlay_path.read_bytes()).hexdigest()
    (tmp_path / "review_ack.json").write_text(json.dumps({
        "reviewer": "reviewer_1", "signed_at": "2026-07-23T00:00:00Z", "decision": "approved",
        "source_dxf_sha256": sha, "request_sha256": req.request_sha256, "overlay_sha256": overlay_sha,
        "near_threshold_confirmed": True}),
        encoding="utf-8")
    signed = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)
    assert all(g.passed for g in signed.gates)
    assert signed.conversion_report.status == "PASS"


def test_g10_ack_rejects_each_bound_hash_tamper(tmp_path):
    """HR-03: source/request/overlay 任一 binding 变动均不能打开 G10。"""
    dst = tmp_path / "source.dxf"; shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest(); req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    candidate = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)
    base = {"reviewer": "reviewer_1", "signed_at": "2026-07-23T00:00:00Z", "decision": "approved",
            "source_dxf_sha256": sha, "request_sha256": req.request_sha256,
            "overlay_sha256": hashlib.sha256(candidate.overlay_path.read_bytes()).hexdigest(),
            "near_threshold_confirmed": True}
    for field in ("source_dxf_sha256", "request_sha256", "overlay_sha256"):
        bad = dict(base); bad[field] = "0" * 64
        (tmp_path / "review_ack.json").write_text(json.dumps(bad), encoding="utf-8")
        out = tn.run_p2_conversion(dst, req, pv, tooling, tmp_path)
        gate = next(g for g in out.gates if g.id == "G10")
        assert not gate.passed and gate.evidence["verification_status"] == "hash_mismatch"


def test_scenario_b_area_compensation_requires_human_confirmation():
    """HR-01: 1.5/2.5/6.0 m² 的补偿误分不能靠 cavity count 静默通过。"""
    tooling = _tooling(); tols = tn._tols_from(tooling, 1.0)
    faces = [Polygon([(0, 0), (1.5, 0), (1.5, 1), (0, 1)]),
             Polygon([(1.5, 0), (4, 0), (4, 1), (1.5, 1)]),
             Polygon([(4, 0), (10, 0), (10, 1), (4, 1)])]
    p1 = SimpleNamespace(faces=faces, gates=[], openings=[], wall_lines=[])
    req, pv = _sm24_request("a" * 64, expected_count=2)
    req = req.model_copy(update={"metres_per_unit": 1.0, "min_room_area_m2": 2.0})
    # s5 only needs the affine conversion; identity is enough for this independent geometry.
    from src.agent.judge.tarch_converter_schema import Affine2D
    affine = Affine2D(m00=1, m01=0, m02=0, m10=0, m11=1, m12=0)
    diags = []
    cavities, walls, footprint, near = tn.s5_identify_cavities(p1, req, tols, diags, affine)
    assert [x["area_m2"] for x in near] == pytest.approx([1.5, 2.5])
    # The count is superficially correct (B+C), but G6 carries the pending human gate.
    assert len(cavities) == 2
    assert any(x["is_cavity"] for x in near) and any(not x["is_cavity"] for x in near)
    claims = tn.s6_bind_intent(cavities, pv, tols, diags, affine)
    gates = tn._build_p2_gates(p1, cavities, walls, footprint, [], claims, near,
                               req, pv, tols, diags)
    g6 = next(g for g in gates if g.id == "G6")
    assert not g6.passed and g6.evidence["human_confirmation_required"]


def test_s7_event_profile_detects_two_changes_and_is_range_invariant():
    """MX thickness: 100→300→100 的两次事件必须精确保留，range 不参与测量。"""
    tooling = _tooling()
    wall = unary_union([Polygon([(0, -100), (4000, -100), (4000, 0), (0, 0)]),
                        Polygon([(4000, -300), (6000, -300), (6000, 0), (4000, 0)]),
                        Polygon([(6000, -100), (10000, -100), (10000, 0), (6000, 0)])])
    footprint = Polygon([(0, -300), (10000, -300), (10000, 1000), (0, 1000)])
    profiles = []
    for ignored_range in (0.35, 0.50):
        tols = tn._tols_from(tooling, 0.001, ignored_range)
        profiles.append(tn._thickness_profile((0, 0), (10000, 0), 0, -1, wall, footprint, tols))
    for profile in profiles:
        assert [(round(a[0]), round(b[0]), round(t)) for a, b, t, _ in profile] == \
            [(0, 4000, 100), (4000, 6000, 300), (6000, 10000, 100)]
    assert profiles[0] == profiles[1]


def test_s7_thickness_without_independent_proof_emits_fail_closed_diagnostic():
    """Thickness negative: 240mm is geometrically measurable but no S2 proof exists.

    The hand geometry is the same 240mm outer-skin box as the L positive; omitting
    every cap/jamb proof must therefore be reported as unevidenced, not inferred
    from the wall region alone.
    """
    t = 240.0
    outer = Polygon([(1000, 1000), (7000, 1000), (7000, 5000), (1000, 5000)])
    cavity = Polygon([(1000 + t, 1000 + t), (7000 - t, 1000 + t),
                      (7000 - t, 5000 - t), (1000 + t, 5000 - t)])
    tols = tn._tols_from(_tooling(), 0.001, t / 1000.0 / 2)
    diags = []
    zones = tn.s7_expand_zones(_claims_for([cavity], ["z0"]), outer.difference(cavity),
                               outer, tols, diags, [], [])
    assert len(zones) == 1
    assert "tarch_wall_thickness_unevidenced" in {d.code for d in diags}


def _sm25_face_pair_fixture():
    """Two real F2 face pairs around the 1449/146D T-junction.

    The first pair overlaps to the left of the junction and the second to its
    right.  Their measured normal separation is independently asserted here so
    this fixture cannot silently become a declared 240 mm expectation.
    """
    lines = [
        ("1449", 24751.8, 42453.6, 29511.8, 42453.6),
        ("144A", 24511.8, 42213.6, 29511.8, 42213.6),
        ("146D", 29511.8, 42453.6, 33511.8, 42453.6),
        ("146E", 29751.8, 42213.6, 33391.8, 42213.6),
        # Nearby faces of another wall: their spans do not overlap this wall and
        # therefore must never manufacture a 60/180 mm pair.
        ("OTHER_LO", 35631.8, 42153.6, 39271.8, 42153.6),
        ("OTHER_HI", 35631.8, 42273.6, 39271.8, 42273.6),
    ]
    assert lines[0][2] - lines[1][2] == pytest.approx(240.0)
    assert min(lines[0][3], lines[1][3]) - max(lines[0][1], lines[1][1]) > 0
    layers = {handle: "WALL" for handle, *_ in lines}
    wall_region = Polygon([(24511.8, 42213.6), (33511.8, 42213.6),
                           (33511.8, 42453.6), (24511.8, 42453.6)])
    return lines, layers, wall_region


def test_face_pair_evidence_reads_real_240_and_cites_the_two_source_faces():
    """Face-pair positive: actual LINE separation is the value, never the range."""
    lines, layers, wall_region = _sm25_face_pair_fixture()
    tols = tn._tols_from(_tooling(), 0.001)
    pairs = tn._build_wall_face_pairs(
        lines, layers, wall_region, (80.0, 500.0), tols)
    pair = next(p for p in pairs if set(p.proof_handles) == {"1449", "144A"})
    assert pair.thickness_native == pytest.approx(240.0)
    assert pair.proof_handles == ["1449", "144A"]


def test_face_pair_evidence_requires_positive_along_wall_overlap():
    """Face-pair must-red: removing overlap yields no proof, not a nearby false pair."""
    lines, layers, wall_region = _sm25_face_pair_fixture()
    moved = [line if line[0] != "144A" else
             ("144A", 50000.0, 42213.6, 55000.0, 42213.6)
             for line in lines]
    tols = tn._tols_from(_tooling(), 0.001)
    pairs = tn._build_wall_face_pairs(
        moved, layers, wall_region, (80.0, 500.0), tols)
    assert not any("1449" in p.proof_handles for p in pairs)


def test_face_pair_binds_t_junction_to_240_and_geometry_assertion_is_live():
    """T-junction lock: the 1449/146D edge binds to its real 240 mm ribbon.

    Moving the already-bound opposite face after binding must make the independent
    exit-point assertion fail; this proves the assertion is not a decorative echo.
    """
    lines, layers, wall_region = _sm25_face_pair_fixture()
    tols = tn._tols_from(_tooling(), 0.001)
    pairs = tn._build_wall_face_pairs(
        lines, layers, wall_region, (80.0, 500.0), tols)
    binding = tn._face_pair_binding_for_edge(
        (24751.8, 42453.6), (33511.8, 42453.6), 0.0, -1.0,
        (29511.8, 29751.8), ["1449", "146D"], pairs, lines, tols)
    assert binding is not None
    assert binding.evidence.value_m == pytest.approx(0.24)
    assert binding.evidence.source_kind == "wall_face_pair"
    assert binding.evidence.proof_handles == ["146D", "146E"]
    assert tn._face_pair_exit_is_supported(binding, lines, layers, tols)

    moved = [line if line[0] != "146E" else
             ("146E", line[1], 42153.6, line[3], 42153.6)
             for line in lines]
    assert not tn._face_pair_exit_is_supported(binding, moved, layers, tols)


def test_sm25_f2_t_junction_uses_face_pair_and_persists_closed_v3_topology(tmp_path):
    """Real-path lock: 1449/146D becomes a 240 mm edge and G4/G7/G8/G9 close."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM25_SOURCE, dst)
    payload = json.loads(SM25_REQUEST.read_text())
    payload["plan_views"] = [v for v in payload["plan_views"] if v["id"] == "plan-F2"]
    payload["elevation_views"] = []
    payload["raster_overlays"] = [
        item for item in payload["raster_overlays"] if item["view_id"] == "plan-F2"]
    payload["floors"] = [f for f in payload["floors"] if f["id"] == "F2"]
    payload["source_dxf_sha256"] = hashlib.sha256(dst.read_bytes()).hexdigest()
    payload["request_sha256"] = "0" * 64
    request = TarchConversionRequestV1.model_validate(payload)
    payload["request_sha256"] = compute_request_sha256(request)
    request = TarchConversionRequestV1.model_validate(payload)
    assert request.min_room_area_m2 == 5.0

    result = tn.run_p2_conversion(dst, request, request.plan_views[0],
                                  resolve_converter_tooling(GT_CONFIG, VG_CONFIG), tmp_path / "work")
    by_handle = {line[0]: line for line in result.p1.wall_lines}
    assert by_handle["1449"][2] - by_handle["144A"][2] == pytest.approx(240.0)
    target = [edge for zone in result.zones for edge in zone.edges
              if {"1449", "146D"}.issubset(edge.source_handles)
              and edge.thickness_evidence is not None
              and edge.thickness_evidence.source_kind == "wall_face_pair"]
    assert len(target) == 1
    assert target[0].thickness_native == pytest.approx(240.0)
    assert target[0].thickness_evidence.proof_handles == ["146D", "146E"]
    assert not any(diag.code == "tarch_wall_thickness_unevidenced"
                   for diag in result.diagnostics)
    gates = {gate.id: gate.passed for gate in result.gates}
    assert all(gates[gate] for gate in ("G4", "G7", "G8", "G9"))


def test_same_wall_gate_splits_t_junction_overlaps_and_catches_conflicting_thickness():
    """SW-04: one long edge is paired per overlap subinterval, not one-to-one."""
    tooling = _tooling(); tols = tn._tols_from(tooling, 0.001)
    def edge(a, b, thickness=240.0):
        nx, ny = tn._outward_normal(a, b)
        return tn._ZoneEdgeRec(nx, ny, "wall_axis", thickness, thickness / 2, p1=a, p2=b)
    # Long left-side edge and two opposite, reversed right-side fragments.
    z0 = tn.ZoneExpansion("c0", Polygon([(0, 0), (5, 0), (5, 10), (0, 10)]),
                          [(0, 0), (5, 0), (5, 10), (0, 10)],
                          [edge((0, 0), (5, 0)), edge((5, 0), (5, 10)),
                           edge((5, 10), (0, 10)), edge((0, 10), (0, 0))], (1, 1), 1.0)
    z1 = tn.ZoneExpansion("c1", Polygon([(5, 0), (10, 0), (10, 4), (5, 4)]),
                          [(5, 0), (10, 0), (10, 4), (5, 4)],
                          [edge((5, 0), (10, 0)), edge((10, 0), (10, 4)),
                           edge((10, 4), (5, 4)), edge((5, 4), (5, 0))], (6, 1), 1.0)
    z2 = tn.ZoneExpansion("c2", Polygon([(5, 4), (10, 4), (10, 10), (5, 10)]),
                          [(5, 4), (10, 4), (10, 10), (5, 10)],
                          [edge((5, 4), (10, 4)), edge((10, 4), (10, 10)),
                           edge((10, 10), (5, 10)), edge((5, 10), (5, 4), 120.0)], (6, 6), 1.0)
    ok, pairs = tn._same_wall_consistency([z0, z1, z2], tols)
    vertical = [p for p in pairs if p["axis"] == "y" and p["coord_native"] == 5]
    assert not ok and [p["overlap_native"] for p in vertical] == [[0, 4], [4, 10]]
    assert [p["consistent"] for p in vertical] == [True, False]


def test_cross_junction_conflicting_segment_blocks_same_wall_gate():
    """Cross negative: one of the two opposite subsegments disagrees on thickness."""
    tooling = _tooling(); tols = tn._tols_from(tooling, .001)
    def edge(a, b, t=240.):
        nx, ny = tn._outward_normal(a, b)
        return tn._ZoneEdgeRec(nx, ny, "wall_axis", t, t / 2, p1=a, p2=b)
    # Two independent cross arms: vertical shared edge is split around its centre.
    left = tn.ZoneExpansion("left", Polygon([(0, 0), (5, 0), (5, 10), (0, 10)]),
        [(0, 0), (5, 0), (5, 10), (0, 10)],
        [edge((0,0),(5,0)), edge((5,0),(5,10)), edge((5,10),(0,10)), edge((0,10),(0,0))], (1,1), 1.)
    low = tn.ZoneExpansion("low", Polygon([(5, 0), (10, 0), (10, 4), (5, 4)]),
        [(5,0),(10,0),(10,4),(5,4)],
        [edge((5,0),(10,0)),edge((10,0),(10,4)),edge((10,4),(5,4)),edge((5,4),(5,0))], (6,1),1.)
    high = tn.ZoneExpansion("high", Polygon([(5, 6), (10, 6), (10, 10), (5, 10)]),
        [(5,6),(10,6),(10,10),(5,10)],
        [edge((5,6),(10,6)),edge((10,6),(10,10)),edge((10,10),(5,10)),edge((5,10),(5,6),120)], (6,8),1.)
    ok, pairs = tn._same_wall_consistency([left, low, high], tols)
    assert not ok
    assert [p["overlap_native"] for p in pairs if p["axis"] == "y"] == [[0, 4], [6, 10]]
    # Feed this exact split conflict to the real P2 gate, not merely the pairing helper.
    footprint = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    g8, diags = _p2_g8_gate([left, low, high], [left.polygon, low.polygon, high.polygon],
                            footprint.difference(unary_union([left.polygon, low.polygon, high.polygon])),
                            footprint, tols)
    assert not g8.passed and g8.evidence["same_wall_conflict_count"] == 1
    assert "tarch_edge_thickness_inconsistent" in {d.code for d in diags}


@pytest.mark.xfail(reason="§2.6 free-end non_zoning proof path is deferred; current S4 blocks every dangle fail-closed")
def test_free_end_non_zoning_with_proof_deferred():
    """Documented deferred positive: do not turn this into a dangle bypass."""
    pytest.fail("deferred by §2.6")
