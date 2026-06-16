"""S23 — 2_modelling + 3_split_pairing geometry gate (M2b, gate ①).

The deterministic geometry kernel's target is the *code* (unit tests + invariants),
so per-run there is NO LLM judge here — gate ① is the whole story. Checks
(contracts §1 2/3 ①), all on the built ``BuildingGeometry``:

  - **zone closure** (block): every zone has a floor, a top (ceiling/roof), and a
    perimeter wall ring whose footprint matches the zone polygon.
  - **normals** (block): floors point −z, ceilings/roofs +z, walls horizontal &
    outward (away from the zone centroid).
  - **pairing gate as block** (block): the InterZone pair gate
    (validate_interzone_surface_pairs) promoted from advisory to a blocking gate
    (reciprocity / area / opposed-normal / coplanar / min-edge / illegal OBC).
  - **coverage completeness** (block, RECTANGULAR profile only — B5 generalises):
    derive the *expected* internal interfaces from cell adjacency (shared interior
    walls + stacked floor/ceiling overlaps) and reconcile their total area against
    the realised reciprocal (OBC=Surface) area. Catches the "both sides Outdoors"
    hole the per-pair gate and EP are both blind to.
  - **spec self-consistency** (block): every surface references an existing zone;
    every ``obc_obj`` target exists.

For the non-rectangular profile the coverage check emits ``not_applicable`` (the
policy then does not block on it) — fact vs policy, no special-casing in policy.
"""

from __future__ import annotations

import numpy as np

from src.agent.geometry.modelling import BuildingGeometry, Surface
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus

_AREA_TOL = 0.10       # m^2 — interface-area reconcile tolerance
_PERIM_TOL = 0.10      # m — perimeter-match tolerance
_MIN_SHARE = 0.05      # m — minimum shared edge to count as an interface


def _newell(verts) -> np.ndarray:
    pts = np.asarray(verts, float)
    n = np.zeros(3)
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    return n


def _poly_area_3d(verts) -> float:
    return float(np.linalg.norm(_newell(verts))) / 2.0


def _unit(n: np.ndarray) -> np.ndarray:
    m = np.linalg.norm(n)
    return n / m if m > 1e-9 else n


def check_kernel(
    bg: BuildingGeometry,
    *,
    capability_profile: str = "rectangular",
    interzone_issues: list[str] | None = None,
) -> CheckReport:
    rep = CheckReport(stage="2_modelling", capability_profile=capability_profile)
    _zone_closure(rep, bg)
    _normals(rep, bg)
    _pairing_gate(rep, bg, interzone_issues)
    _spec_self_consistency(rep, bg)
    _coverage_completeness(rep, bg, capability_profile)
    return rep


def _by_zone(bg: BuildingGeometry) -> dict[str, list[Surface]]:
    out: dict[str, list[Surface]] = {}
    for s in bg.surfaces:
        out.setdefault(s.zone, []).append(s)
    return out


def _wall_base_len(s: Surface) -> float:
    """Horizontal length of a wall face (split-pairing may fragment walls, so we
    reconcile by SUMMED width, not per-face)."""
    xs = [v[0] for v in s.verts]
    ys = [v[1] for v in s.verts]
    return float(np.hypot(max(xs) - min(xs), max(ys) - min(ys)))


def _zone_closure(rep: CheckReport, bg: BuildingGeometry) -> None:
    """Closure by SUMS against each zone's authoritative polygon: split-pairing
    fragments floors/ceilings/walls into sub-faces, so a single face never matches
    the footprint — but the summed floor/ceiling area and wall width must."""
    polys = {zv.zone: zv for zv in bg.zone_volumes}
    bad = []
    for zone, surfs in _by_zone(bg).items():
        floors = [s for s in surfs if s.stype == "Floor"]
        tops = [s for s in surfs if s.stype in ("Ceiling", "Roof")]
        walls = [s for s in surfs if s.stype == "Wall"]
        if not floors:
            bad.append({"zone": zone, "missing": "Floor"})
        if not tops:
            bad.append({"zone": zone, "missing": "Ceiling/Roof"})
        if not walls:
            bad.append({"zone": zone, "missing": "Wall"})
        zv = polys.get(zone)
        if zv is None:
            # A surface references a zone with no ZoneVolume → the zone is not
            # declared; block rather than silently skip its closure checks.
            bad.append({"zone": zone, "reason": "no ZoneVolume (zone not declared)"})
            continue
        if not (floors and tops and walls):
            continue
        area = zv.polygon.area
        perim = zv.polygon.length
        floor_area = sum(_poly_area_3d(s.verts) for s in floors)
        top_area = sum(_poly_area_3d(s.verts) for s in tops)
        wall_width = sum(_wall_base_len(s) for s in walls)
        if abs(floor_area - area) > _AREA_TOL:
            bad.append({"zone": zone, "floor_area": round(floor_area, 3),
                        "footprint_area": round(area, 3)})
        if abs(top_area - area) > _AREA_TOL:
            bad.append({"zone": zone, "top_area": round(top_area, 3),
                        "footprint_area": round(area, 3)})
        if abs(wall_width - perim) > _PERIM_TOL:
            bad.append({"zone": zone, "wall_width_sum": round(wall_width, 3),
                        "footprint_perimeter": round(perim, 3)})
    if bad:
        rep.add_fail("kernel.zone_closure", CheckLayer.INVARIANT,
                     f"{len(bad)} zone-closure defect(s)", evidence={"offenders": bad})
    else:
        rep.add_pass("kernel.zone_closure", CheckLayer.INVARIANT,
                     evidence={"zones": len(_by_zone(bg))})


def _normals(rep: CheckReport, bg: BuildingGeometry) -> None:
    centroids: dict[str, np.ndarray] = {}
    for zone, surfs in _by_zone(bg).items():
        pts = [v for s in surfs for v in s.verts]
        centroids[zone] = np.mean(np.asarray(pts, float), axis=0)
    bad = []
    for s in bg.surfaces:
        n = _unit(_newell(s.verts))
        if s.stype == "Floor":
            if n[2] > -0.5:
                bad.append({"surface": s.name, "type": s.stype, "nz": round(float(n[2]), 3)})
        elif s.stype in ("Ceiling", "Roof"):
            if n[2] < 0.5:
                bad.append({"surface": s.name, "type": s.stype, "nz": round(float(n[2]), 3)})
        elif s.stype == "Wall":
            if abs(n[2]) > 0.1:
                bad.append({"surface": s.name, "type": s.stype, "reason": "wall not vertical",
                            "nz": round(float(n[2]), 3)})
                continue
            mid = np.mean(np.asarray(s.verts, float), axis=0)
            outward = mid - centroids[s.zone]
            if float(n[0] * outward[0] + n[1] * outward[1]) <= 0:
                bad.append({"surface": s.name, "type": s.stype, "reason": "inward normal"})
    if bad:
        rep.add_fail("kernel.normals", CheckLayer.INVARIANT,
                     f"{len(bad)} surface(s) with wrong normal orientation",
                     evidence={"offenders": bad[:20], "count": len(bad)})
    else:
        rep.add_pass("kernel.normals", CheckLayer.INVARIANT,
                     evidence={"surfaces": len(bg.surfaces)})


def _pairing_gate(
    rep: CheckReport, bg: BuildingGeometry, interzone_issues: list[str] | None
) -> None:
    """Promote the InterZone pair gate from advisory to a blocking gate."""
    if interzone_issues is None:
        try:
            from src.agent.geometry.to_idf import building_to_idf
            from src.validator.interzone import validate_interzone_surface_pairs

            interzone_issues = validate_interzone_surface_pairs(building_to_idf(bg))
        except Exception as e:  # noqa: BLE001 — surfaced as a fail-closed error
            rep.add("kernel.pairing_gate", CheckStatus.ERROR, CheckLayer.INVARIANT,
                    message=f"pairing gate could not run: {type(e).__name__}: {e}")
            return
    if interzone_issues:
        rep.add_fail("kernel.pairing_gate", CheckLayer.INVARIANT,
                     f"{len(interzone_issues)} InterZone pairing issue(s)",
                     evidence={"issues": interzone_issues[:20], "count": len(interzone_issues)})
    else:
        rep.add_pass("kernel.pairing_gate", CheckLayer.INVARIANT)


def _spec_self_consistency(rep: CheckReport, bg: BuildingGeometry) -> None:
    # Declared zones come ONLY from the zone declaration (bg.zones / zone_volumes),
    # NOT from the surfaces themselves — otherwise a surface pointing at an
    # undeclared zone would vacuously satisfy `s.zone in zones`.
    zones = set(dict.fromkeys(bg.zones)) | {zv.zone for zv in bg.zone_volumes}
    names = {s.name for s in bg.surfaces}
    bad = []
    for s in bg.surfaces:
        if s.zone not in zones:
            bad.append({"surface": s.name, "reason": f"zone '{s.zone}' undefined"})
        if s.obc == "Surface":
            if not s.obc_obj:
                bad.append({"surface": s.name, "reason": "OBC=Surface with empty obc_obj"})
            elif s.obc_obj not in names:
                bad.append({"surface": s.name, "reason": f"obc_obj '{s.obc_obj}' not found"})
    if bad:
        rep.add_fail("kernel.spec_self_consistency", CheckLayer.INVARIANT,
                     f"{len(bad)} spec reference defect(s)", evidence={"offenders": bad})
    else:
        rep.add_pass("kernel.spec_self_consistency", CheckLayer.INVARIANT)


def _coverage_completeness(
    rep: CheckReport, bg: BuildingGeometry, profile: str
) -> None:
    """Expected internal-interface area (from cell adjacency) vs realised
    reciprocal (OBC=Surface) area. Rectangular profile only."""
    if profile != "rectangular":
        rep.add("kernel.coverage_completeness", CheckStatus.NOT_APPLICABLE,
                CheckLayer.INVARIANT, message=f"profile={profile}: B5 generalises non-rect")
        return
    zvs = bg.zone_volumes
    if not zvs:
        rep.add("kernel.coverage_completeness", CheckStatus.NOT_APPLICABLE,
                CheckLayer.INVARIANT, message="no zone_volumes to derive adjacency")
        return

    expected = 0.0
    # vertical interior walls: same-floor adjacent cells sharing an edge
    by_fi: dict[int, list] = {}
    for zv in zvs:
        by_fi.setdefault(zv.fi, []).append(zv)
    for group in by_fi.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                shared = a.polygon.boundary.intersection(b.polygon.boundary)
                length = getattr(shared, "length", 0.0)
                if length >= _MIN_SHARE:
                    height = min(a.zt - a.zf, b.zt - b.zf)
                    expected += length * height
    # horizontal floor/ceiling: vertically adjacent cells whose polygons overlap
    fis = sorted(by_fi)
    for lo_fi, hi_fi in zip(fis, fis[1:]):
        for a in by_fi[lo_fi]:
            for b in by_fi[hi_fi]:
                if abs(a.zt - b.zf) > 0.05:
                    continue
                ov = a.polygon.intersection(b.polygon).area
                if ov >= _MIN_SHARE:
                    expected += ov

    realised = sum(_poly_area_3d(s.verts) for s in bg.surfaces if s.obc == "Surface")
    realised_half = realised / 2.0  # each interface counted on both sides
    delta = expected - realised_half
    if delta > _AREA_TOL:
        rep.add_fail(
            "kernel.coverage_completeness", CheckLayer.INVARIANT,
            f"internal-interface coverage hole: expected {expected:.2f} m^2 of "
            f"internal interfaces, only {realised_half:.2f} m^2 realised as "
            f"reciprocal pairs (Δ={delta:.2f}) — some internal boundary is modelled "
            f"as Outdoors/Adiabatic",
            evidence={"expected_m2": round(expected, 3),
                      "realised_m2": round(realised_half, 3),
                      "delta_m2": round(delta, 3)})
    else:
        rep.add_pass("kernel.coverage_completeness", CheckLayer.INVARIANT,
                     evidence={"expected_m2": round(expected, 3),
                               "realised_m2": round(realised_half, 3)})
