"""Canonical G1--G10 red fixtures and the converter's one-to-one neuter audit.

Every fixture reads the production GateResult emitted by the real assembly.  The
parametrized audit re-runs all ten fixtures after setting the test-only final-gate
seam; it proves that only the selected fixture is released.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import ConversionDiagnosticV1, resolve_converter_tooling
from tests import test_tarch_converter_p1_geometry as p1
from tests import test_tarch_converter_p2_geometry as p2


def _gate(gates, gate):
    return next(g for g in gates if g.id == gate)


def _p1(tmp_path, **kwargs):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "source.dxf"; p1._make_dxf(path, **kwargs)
    return p1._run(path)


def _p2(tmp_path, *, expected=8):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "source.dxf"; shutil.copyfile(p2.SM24_SOURCE, path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest(); req, pv = p2._sm24_request(sha, expected)
    tooling = resolve_converter_tooling(p2.GT_CONFIG, p2.VG_CONFIG)
    return tn.run_p2_conversion(path, req, pv, tooling, tmp_path), req, pv, tooling


def _g1(tmp): return _gate(_p1(tmp, diagonal=True)[0].gates, "G1")


def _g2(tmp):
    res, _, _, tooling, _ = _p1(tmp)
    collect = tn._WallCollect(wall_lines=[], degenerate=0, caps_v={}, caps_h={},
        cap_handles_v={}, cap_handles_h={}, all_handles=set(), source_x={0.0: [0.0, 2.0]}, source_y={})
    diags: list[ConversionDiagnosticV1] = []
    ok = tn._g2_conservation(collect, tn._tols_from(tooling, 0.001), diags)
    res.gates = []; res.diagnostics = diags
    tn._assemble_gates(res, True, ok, tn._tols_from(tooling, 0.001))
    return _gate(res.gates, "G2")


def _g3(tmp): return _gate(_p1(tmp, unknown_block=True)[0].gates, "G3")


def _g5(tmp): return _gate(_p1(tmp, free_end=True)[0].gates, "G5")


def _g4(tmp):
    res, req, pv, _ = _p2(tmp)
    # Reassemble G4 against the real footprint/zones after removing opening claims.
    res.p1.openings = []
    gates = tn._build_p2_gates(res.p1, res.cavities, res.wall_region, res.footprint,
        res.zones, res.claims, res.near_threshold_faces, req, pv,
        tn._tols_from(resolve_converter_tooling(p2.GT_CONFIG, p2.VG_CONFIG), .001), res.diagnostics)
    return _gate(gates, "G4")


def _g6(tmp): return _gate(_p2(tmp, expected=7)[0].gates, "G6")


def _g7(tmp):
    res, req, pv, tooling = _p2(tmp)
    res.zones[0].polygon = res.zones[0].polygon.buffer(5)
    gates = tn._build_p2_gates(res.p1, res.cavities, res.wall_region, res.footprint,
        res.zones, res.claims, [], req, pv, tn._tols_from(tooling, .001), res.diagnostics)
    return _gate(gates, "G7")


def _g8(tmp):
    res, req, pv, tooling = _p2(tmp)
    edge = next(e for e in res.zones[0].edges if e.basis == "wall_axis")
    edge.basis = "outer_skin"  # deliberately retain forward cache offset_native
    gates = tn._build_p2_gates(res.p1, res.cavities, res.wall_region, res.footprint,
        res.zones, res.claims, [], req, pv, tn._tols_from(tooling, .001), res.diagnostics)
    return _gate(gates, "G8")


def _g9(tmp):
    res, _, _, tooling = _p2(tmp)
    bad = res.manifest.model_copy(deep=True); view = bad.views[0]
    view.footprint_boundary = view.footprint_boundary.model_copy(update={"handles": ["DEADBE"]})
    ok, _ = tn._run_g9_v3_preflight(res.augmented_dxf_path, bad, tooling)
    return tn._apply_test_neuter([tn.GateResultV1(id="G9", name="v3 extraction preflight", passed=ok)])[0]


def _g10(tmp): return _gate(_p2(tmp)[0].gates, "G10")


CANONICAL = {"G1": _g1, "G2": _g2, "G3": _g3, "G4": _g4, "G5": _g5,
             "G6": _g6, "G7": _g7, "G8": _g8, "G9": _g9, "G10": _g10}


@pytest.mark.parametrize("gate", CANONICAL, ids=lambda g: g.lower())
def test_gate_must_red(gate, tmp_path):
    assert not CANONICAL[gate](tmp_path).passed


@pytest.mark.parametrize("neuter", CANONICAL, ids=lambda g: f"neuter_{g.lower()}")
def test_gate_k_is_one_to_one_bound(neuter, tmp_path, monkeypatch):
    monkeypatch.setenv("TARCH_NEUTER_GATE", neuter)
    observed = {}
    for gate, fixture in CANONICAL.items():
        observed[gate] = fixture(tmp_path / gate).passed
    assert observed == {gate: gate == neuter for gate in CANONICAL}
