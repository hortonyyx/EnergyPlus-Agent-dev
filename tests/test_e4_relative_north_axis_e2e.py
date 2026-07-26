"""E4-output-contract spec v2 §9/§10.7 — EnergyPlus 25.1 end-to-end: the five
probe-anchored assertions on the four canonical variants (world_000 /
rel_000 / rel_090 / rel_270).

The four IDFs are the committed 2026-07-10 probe fixtures (114 HeatTransfer
surfaces / 14 zones): identical building-frame vertices in all four; world_000
keeps the pre-migration nonzero Zone origins (so the "ignored" warning is
deterministically触发-able), the three Relative variants have all-zero Zone
frames and Building.North Axis = 0/90/270.

Each of the five spec assertions is its own test id (§10.7) so a failure
pinpoints the broken property. EIO columns are located dynamically from the
`! <...>` header rows, never by hardcoded index. Skipped (never xfail) when
EnergyPlus 25.1 is not executable in the environment.
"""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_PROBE = _REPO / "AI_agent" / "logs" / "experiments" / "2026-07-10_e4_relative_north_axis_probe"
_EPW = _REPO / "data" / "weather" / "Shenzhen.epw"
_VARIANTS = ("world_000", "rel_000", "rel_090", "rel_270")

# §10.8: E4-only tolerances — deliberately NOT the geometry min-edge/snap ones.
E4_AZIMUTH_ZERO_TOL_DEG = 1e-6
E4_AZIMUTH_ROTATION_TOL_DEG = 1e-3
E4_AREA_VOLUME_TOL = 1e-6

_IGNORED_WARNING = (
    "Any non-zero Building/Zone North Axes or non-zero Zone Origins are ignored"
)


def _ep_exe() -> str | None:
    from src.runner.runner import resolve_energyplus_exe

    exe = resolve_energyplus_exe()
    if Path(exe).is_file() or shutil.which(exe):
        return exe
    return None


_EXE = _ep_exe()
pytestmark = pytest.mark.skipif(
    _EXE is None or not _EPW.is_file() or not all((_PROBE / f"{v}.idf").is_file() for v in _VARIANTS),
    reason="EnergyPlus 25.1 executable / EPW / probe fixtures not available",
)


# --------------------------------------------------------------------------- #
# one EP run per variant, session-cached
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def ep_outputs(tmp_path_factory) -> dict[str, Path]:
    outs: dict[str, Path] = {}
    root = tmp_path_factory.mktemp("e4_ep")
    for variant in _VARIANTS:
        variant_root = root / variant
        input_idf = variant_root / f"{variant}.idf"
        out_dir = variant_root / "output"
        variant_root.mkdir()
        shutil.copy2(_PROBE / f"{variant}.idf", input_idf)
        result = subprocess.run(
            [_EXE, "-d", str(out_dir), "-x", "-w", str(_EPW), str(input_idf)],
            cwd=variant_root,
            capture_output=True, text=True, timeout=300,
        )
        end = out_dir / "eplusout.end"
        assert end.is_file(), (
            f"{variant}: EP produced no eplusout.end (rc={result.returncode}):\n"
            f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
        )
        end_text = end.read_text(encoding="utf-8", errors="replace")
        assert "Completed Successfully" in end_text, f"{variant}: {end_text}"
        assert " 0 Severe Errors" in end_text, f"{variant}: {end_text}"
        outs[variant] = out_dir
    return outs


def _eio_table(eio_path: Path, table: str) -> tuple[list[str], list[list[str]]]:
    """Locate `! <table>,col1,col2,...` dynamically and return (columns, rows)."""
    header: list[str] | None = None
    rows: list[list[str]] = []
    for line in eio_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith(f"! <{table}>"):
            header = [c.strip() for c in stripped.split(",")]
            continue
        if header is not None and stripped.startswith(f"{table},"):
            rows.append([c.strip() for c in stripped.split(",")])
    assert header is not None, f"table {table!r} header not found in {eio_path}"
    return header, rows


def _surface_azimuths(out_dir: Path) -> dict[str, float]:
    header, rows = _eio_table(out_dir / "eplusout.eio", "HeatTransfer Surface")
    name_i = header.index("Surface Name")
    az_i = header.index("Azimuth {deg}")
    return {r[name_i]: float(r[az_i]) for r in rows}


def _zone_area_volume(out_dir: Path) -> dict[str, tuple[float, float]]:
    header, rows = _eio_table(out_dir / "eplusout.eio", "Zone Information")
    name_i = header.index("Zone Name")
    area_i = header.index("Floor Area {m2}")
    vol_i = header.index("Volume {m3}")
    return {r[name_i]: (float(r[area_i]), float(r[vol_i])) for r in rows}


def _circular_diff_deg(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


# --------------------------------------------------------------------------- #
# pre-run fixture sanity (§9.1)
# --------------------------------------------------------------------------- #
def test_world_anchor_keeps_nonzero_zone_origin():
    text = (_PROBE / "world_000.idf").read_text(encoding="utf-8", errors="replace")
    assert "4.85,                     !- Y Origin" in text


def test_relative_variants_have_all_zero_zone_frames(ep_outputs):
    for variant in ("rel_000", "rel_090", "rel_270"):
        header, rows = _eio_table(ep_outputs[variant] / "eplusout.eio", "Zone Information")
        xi = header.index("Origin X-Coordinate {m}")
        yi = header.index("Origin Y-Coordinate {m}")
        zi = header.index("Origin Z-Coordinate {m}")
        ni = header.index("North Axis {deg}")
        for r in rows:
            assert (float(r[xi]), float(r[yi]), float(r[zi]), float(r[ni])) == (0.0, 0.0, 0.0, 0.0)


def test_surface_and_zone_name_sets_identical_across_variants(ep_outputs):
    surface_sets = {v: set(_surface_azimuths(ep_outputs[v])) for v in _VARIANTS}
    zone_sets = {v: set(_zone_area_volume(ep_outputs[v])) for v in _VARIANTS}
    assert len({frozenset(s) for s in surface_sets.values()}) == 1
    assert len({frozenset(z) for z in zone_sets.values()}) == 1
    assert len(surface_sets["world_000"]) == 114
    assert len(zone_sets["world_000"]) == 14


# --------------------------------------------------------------------------- #
# §9.2 the five assertions — one test id each
# --------------------------------------------------------------------------- #
def test_e4_assertion_1_zero_angle_geometric_equivalence(ep_outputs):
    world = _surface_azimuths(ep_outputs["world_000"])
    rel = _surface_azimuths(ep_outputs["rel_000"])
    assert set(world) == set(rel)
    for name, az in world.items():
        assert _circular_diff_deg(rel[name], az) <= E4_AZIMUTH_ZERO_TOL_DEG, name


def test_e4_assertion_2_ninety_degree_rotation(ep_outputs):
    base = _surface_azimuths(ep_outputs["rel_000"])
    rot = _surface_azimuths(ep_outputs["rel_090"])
    for name, az in base.items():
        expected = math.fmod(az + 90.0, 360.0)
        assert _circular_diff_deg(rot[name], expected) <= E4_AZIMUTH_ROTATION_TOL_DEG, name


def test_e4_assertion_3_two_seventy_degree_rotation(ep_outputs):
    base = _surface_azimuths(ep_outputs["rel_000"])
    rot = _surface_azimuths(ep_outputs["rel_270"])
    for name, az in base.items():
        expected = math.fmod(az + 270.0, 360.0)
        assert _circular_diff_deg(rot[name], expected) <= E4_AZIMUTH_ROTATION_TOL_DEG, name


def test_e4_assertion_4_area_volume_invariant(ep_outputs):
    world = _zone_area_volume(ep_outputs["world_000"])
    assert len(world) == 14
    pair_count = 0
    for variant in ("rel_000", "rel_090", "rel_270"):
        other = _zone_area_volume(ep_outputs[variant])
        assert set(other) == set(world)
        for zone, (area, volume) in world.items():
            assert abs(other[zone][0] - area) <= E4_AREA_VOLUME_TOL, (variant, zone)
            assert abs(other[zone][1] - volume) <= E4_AREA_VOLUME_TOL, (variant, zone)
            pair_count += 1
    assert pair_count == 42  # 14 zones x 3 comparisons — the probe's exact ledger


def test_e4_assertion_5_ignored_warning_behavior(ep_outputs):
    for variant in _VARIANTS:
        err_text = (ep_outputs[variant] / "eplusout.err").read_text(
            encoding="utf-8", errors="replace")
        hits = err_text.count(_IGNORED_WARNING)
        if variant == "world_000":
            assert hits == 1, f"{variant}: expected exactly 1 ignored-warning hit, got {hits}"
            assert "Potential mismatch of coordinate specifications" in err_text
        else:
            # rel_000 included: theta==0.0 must ALSO be warning-free, proving
            # the Relative branch is not an `if theta != 0` guess.
            assert hits == 0, f"{variant}: expected no ignored-warning, got {hits}"
