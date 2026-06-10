"""Serialize deterministic BuildingGeometry -> downstream spec text (fork a).

The geometry kernel produces fully-resolved surfaces (vertices CCW-from-outside,
OBC, reciprocal interzone pairing). This module turns that into the free-text
`zone_specs` / `surface_specs` / `fenestration_specs` the downstream zone /
surface / fenestration agents transcribe verbatim — so geometry is deterministic
end-to-end while the `IntakeOutput` contract and downstream code stay unchanged.

Construction names are assigned here from a fixed vocabulary keyed on surface
type + OBC; the 4_MEP stage must define exactly the constructions this serializer
emits (returned as `used_constructions`). Paired interzone faces both get
`Cons_InterFloor`, so the reverse-layer symmetry EnergyPlus requires holds
trivially (rules.md §5.1).
"""

from __future__ import annotations

from src.agent.geometry.modelling import BuildingGeometry, Surface

# Fixed construction vocabulary — the seam between the geometry serializer and
# the 4_MEP author. Both reference these exact names.
CONSTRUCTION_VOCAB = {
    "ext_wall": "Default_Ext_Wall",
    "int_wall": "Default_Int_Wall",
    "ground_wall": "Default_GroundWall",  # below-grade wall (not emitted by the
                                          # current kernel; defensive)
    "ground_floor": "Default_GroundFloor",
    "ext_floor": "Default_ExtFloor",   # exposed underside (cantilever); rare
    "roof": "Default_Roof",
    "interfloor": "Cons_InterFloor",
    "window": "Default_Window",
}


def _construction_for(s: Surface) -> str:
    if s.stype == "Wall":
        if s.obc == "Outdoors":
            return CONSTRUCTION_VOCAB["ext_wall"]
        if s.obc == "Ground":
            return CONSTRUCTION_VOCAB["ground_wall"]
        return CONSTRUCTION_VOCAB["int_wall"]
    if s.stype == "Floor":
        if s.obc == "Ground":
            return CONSTRUCTION_VOCAB["ground_floor"]
        if s.obc == "Surface":
            return CONSTRUCTION_VOCAB["interfloor"]
        return CONSTRUCTION_VOCAB["ext_floor"]  # Outdoors underside
    if s.stype == "Ceiling":
        return CONSTRUCTION_VOCAB["interfloor"]
    if s.stype == "Roof":
        return CONSTRUCTION_VOCAB["roof"]
    return CONSTRUCTION_VOCAB["ext_wall"]


def _kind_label(s: Surface) -> str:
    if s.stype == "Wall":
        return {"Outdoors": "exterior", "Ground": "ground"}.get(s.obc, "interior")
    if s.stype == "Floor":
        return {"Ground": "ground", "Surface": "interzone"}.get(s.obc, "exterior")
    if s.stype == "Ceiling":
        return "interzone"
    return "roof"


def _fmt_verts(verts) -> str:
    return "-".join(f"({v[0]:.2f},{v[1]:.2f},{v[2]:.2f})" for v in verts)


def _xy_range(bg_zone_volume) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = bg_zone_volume.polygon.bounds
    return minx, miny, maxx, maxy


def serialize_geometry(
    bg: BuildingGeometry,
) -> tuple[str, str, str, set[str]]:
    """Return (zone_specs, surface_specs, fenestration_specs, used_constructions)."""
    surf_by_name = {s.name: s for s in bg.surfaces}

    # ---- zone_specs ----
    z_lines = [
        "Zones (world coordinates, meters, two decimals). Every zone name below "
        "is referenced literally by surface_specs / fenestration_specs / "
        "people_specs / lights_specs / hvac_specs.",
    ]
    by_fi: dict[int, list] = {}
    for zv in bg.zone_volumes:
        by_fi.setdefault(zv.fi, []).append(zv)
    for fi in sorted(by_fi):
        zvs = by_fi[fi]
        zf = zvs[0].zf
        zt = zvs[0].zt
        z_lines.append(f"\nFloor {fi + 1} (z {zf:.2f} to {zt:.2f}):")
        for zv in zvs:
            minx, miny, maxx, maxy = _xy_range(zv)
            z_lines.append(
                f"- {zv.zone}: x[{minx:.2f},{maxx:.2f}], y[{miny:.2f},{maxy:.2f}], "
                f"z_floor={zv.zf:.2f}, ceiling_height={zv.zt - zv.zf:.2f}, "
                f"role: {zv.role}."
            )
    zone_specs = "\n".join(z_lines)

    # ---- surface_specs ----
    used: set[str] = set()
    s_lines = [
        "Surfaces (vertices CCW from outside, absolute world coordinates in "
        "meters). Construction names and adjacent zone names are authoritative — "
        "transcribe them verbatim. Interzone faces are pre-paired: the named "
        "adjacent surface is its reciprocal partner.",
    ]
    surfaces_by_zone: dict[str, list[Surface]] = {}
    for s in bg.surfaces:
        surfaces_by_zone.setdefault(s.zone, []).append(s)
    # keep zone order stable (zone_volumes order)
    zone_order = [zv.zone for zv in bg.zone_volumes]
    for zone in zone_order:
        if zone not in surfaces_by_zone:
            continue
        s_lines.append(f"\n**{zone}**:")
        for s in surfaces_by_zone[zone]:
            cons = _construction_for(s)
            used.add(cons)
            kind = _kind_label(s)
            extra = ""
            if s.obc == "Surface":
                if s.obc_obj in surf_by_name:
                    partner = surf_by_name[s.obc_obj]
                    extra = (
                        f", adjacent_zone={partner.zone}, "
                        f"adjacent_surface={s.obc_obj}"
                    )
                else:
                    # kernel pairing should always set a resolvable partner;
                    # surface this loudly rather than dropping adjacency silently
                    extra = ", adjacent_surface=UNRESOLVED"
            s_lines.append(
                f"- {s.name} ({kind} {s.stype.lower()}, {cons}{extra}): "
                f"{_fmt_verts(s.verts)}"
            )
    surface_specs = "\n".join(s_lines)

    # ---- fenestration_specs ----
    if not bg.windows:
        # Be explicit: an empty list is "zero windows", NOT "decide for yourself".
        # A bare header let the downstream agent invent windows (sm21 e2e: 24
        # hallucinated). State it unambiguously so it creates none.
        fenestration_specs = (
            "This model has NO windows. The geometry contains zero fenestration "
            "surfaces. Do NOT create any FenestrationSurface:Detailed objects and "
            "do NOT invent windows on any facade."
        )
        return zone_specs, surface_specs, fenestration_specs, used

    f_lines = [
        "Windows are FenestrationSurface:Detailed, vertices CCW from outside, "
        f"Construction={CONSTRUCTION_VOCAB['window']}. parent is the exterior "
        "wall surface name (transcribe verbatim). Create EXACTLY the windows "
        "listed below — no more, no fewer.",
    ]
    used.add(CONSTRUCTION_VOCAB["window"])
    for w in bg.windows:
        zs = [v[2] for v in w.verts]
        f_lines.append(
            f"- {w.name}: parent={w.parent}, "
            f"Construction={CONSTRUCTION_VOCAB['window']}, "
            f"z={min(zs):.2f}-{max(zs):.2f}, vertices: {_fmt_verts(w.verts)}"
        )
    fenestration_specs = "\n".join(f_lines)

    return zone_specs, surface_specs, fenestration_specs, used
