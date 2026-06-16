"""S4 — 4_mep deterministic check adapter (M2c, gate ①).

4_mep OWNS the entire MEP reference graph + object semantics (contracts §0.4 #7,
§1 5 attribution): everything is checked here, off the SINGLE unified parse
(idf_fragments.py) — no check writes its own regex. 5_intakeoutput only re-runs a
backstop.

Reference graph (two graphs, block):
  - ``geometry → construction → material``: every used construction is defined;
    every construction layer is a defined material.
  - ``people/lights/hvac → zone / schedule``: per-zone loads reference an existing
    zone and a defined schedule.

Object semantics (block):
  - ``WindowMaterial:SimpleGlazingSystem`` must be a STANDALONE construction layer
    (single-layer construction — the sm_16 NaN-fatal class).
  - ``Material:NoMass`` thermal resistance must be positive.
  - ``Schedule:Compact`` must reference a defined ``ScheduleTypeLimits``.
  - ``Schedule:Compact`` day-type completeness (reuses validator/schedules.py).

Reasonability bands (LPD / people density / setpoints / U-value) are a FLAG
placeholder — filled in once MEP input is richer (§5.2). A parse failure is an
ERROR (fail-closed → block + resample).
"""

from __future__ import annotations

from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus
from src.validator.idf_fragments import IdfFragmentIndex, parse_mep_fragments
from src.validator.schedules import validate_schedule_completeness

# Object types whose names can appear as a Construction layer.
_MATERIAL_TYPES = (
    "MATERIAL", "MATERIAL:NOMASS", "MATERIAL:AIRGAP",
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM", "WINDOWMATERIAL:GLAZING",
    "WINDOWMATERIAL:GAS", "WINDOWMATERIAL:BLIND", "MATERIAL:INFRAREDTRANSPARENT",
)
_LOAD_TYPES = ("PEOPLE", "LIGHTS", "ELECTRICEQUIPMENT")


def check_mep(
    mep: dict | object,
    *,
    used_constructions: set[str] | None = None,
    zone_names: set[str] | None = None,
    geometry_idf: str = "",
    capability_profile: str = "rectangular",
) -> CheckReport:
    rep = CheckReport(stage="4_mep", capability_profile=capability_profile)
    idx = parse_mep_fragments(mep, extra_idf=geometry_idf)
    if not idx.ok:
        rep.add("mep.idf_parse", CheckStatus.ERROR, CheckLayer.INVARIANT,
                message=f"MEP fragment parse failed: {idx.parse_error}")
        return rep  # fail-closed; nothing else can be trusted
    rep.add_pass("mep.idf_parse", CheckLayer.INVARIANT)

    _construction_coverage(rep, idx, used_constructions)
    _construction_to_material(rep, idx)
    _schedule_type_refs(rep, idx)
    _schedule_completeness(rep, idx)
    _load_refs(rep, idx, zone_names)
    _per_zone_coverage(rep, idx, zone_names)
    _simpleglazing_standalone(rep, idx)
    _nomass_positive_resistance(rep, idx)
    _reasonability_placeholder(rep)
    return rep


def _material_names(idx: IdfFragmentIndex) -> set[str]:
    return idx.has_name(*_MATERIAL_TYPES)


def _construction_coverage(
    rep: CheckReport, idx: IdfFragmentIndex, used: set[str] | None
) -> None:
    if not used:
        rep.add("mep.construction_coverage", CheckStatus.NOT_APPLICABLE,
                CheckLayer.INVARIANT, message="no used_constructions supplied")
        return
    defined = idx.has_name("CONSTRUCTION")
    missing = sorted(c for c in used if c not in defined)
    if missing:
        rep.add_fail("mep.construction_coverage", CheckLayer.INVARIANT,
                     f"{len(missing)} geometry-referenced construction(s) undefined",
                     evidence={"missing": missing})
    else:
        rep.add_pass("mep.construction_coverage", CheckLayer.INVARIANT,
                     evidence={"used": len(used)})


def _construction_to_material(rep: CheckReport, idx: IdfFragmentIndex) -> None:
    mats = _material_names(idx)
    bad = []
    for c in idx.of_type("CONSTRUCTION"):
        # Strip trailing empties (eppy pads optional layer fields) before judging.
        layers = list(c.fields[1:])
        while layers and not str(layers[-1]).strip():
            layers.pop()
        if not layers:
            bad.append({"construction": c.name, "reason": "no layers (empty construction)"})
            continue
        for layer in layers:
            if not str(layer).strip():
                bad.append({"construction": c.name, "reason": "blank layer field (gap)"})
            elif layer not in mats:
                bad.append({"construction": c.name, "missing_layer": layer})
    if bad:
        rep.add_fail("mep.construction_to_material", CheckLayer.INVARIANT,
                     f"{len(bad)} construction layer(s) reference undefined materials",
                     evidence={"offenders": bad})
    else:
        rep.add_pass("mep.construction_to_material", CheckLayer.INVARIANT)


def _schedule_type_refs(rep: CheckReport, idx: IdfFragmentIndex) -> None:
    types = idx.has_name("SCHEDULETYPELIMITS")
    bad = []
    for s in idx.of_type("SCHEDULE:COMPACT"):
        type_name = s.fields[1] if len(s.fields) > 1 else ""
        if type_name and type_name not in types:
            bad.append({"schedule": s.name, "missing_type": type_name})
    if bad:
        rep.add_fail("mep.schedule_type_refs", CheckLayer.INVARIANT,
                     f"{len(bad)} schedule(s) reference undefined ScheduleTypeLimits",
                     evidence={"offenders": bad})
    else:
        rep.add_pass("mep.schedule_type_refs", CheckLayer.INVARIANT)


def _schedule_completeness(rep: CheckReport, idx: IdfFragmentIndex) -> None:
    issues = validate_schedule_completeness(idx.idf)
    if issues:
        rep.add_fail("mep.schedule_completeness", CheckLayer.INVARIANT,
                     f"{len(issues)} incomplete Schedule:Compact day-type coverage",
                     evidence={"issues": issues})
    else:
        rep.add_pass("mep.schedule_completeness", CheckLayer.INVARIANT)


def _load_refs(
    rep: CheckReport, idx: IdfFragmentIndex, zone_names: set[str] | None
) -> None:
    """People/Lights/Equipment → zone (field 1) and → schedule (field 2)."""
    sched_names = idx.has_name("SCHEDULE:COMPACT")
    zone_bad, sched_bad = [], []
    for obj in idx.of_type(*_LOAD_TYPES):
        zref = obj.fields[1] if len(obj.fields) > 1 else ""
        sref = obj.fields[2] if len(obj.fields) > 2 else ""
        if zone_names is not None and zref and zref not in zone_names:
            zone_bad.append({"object": obj.name, "zone_ref": zref})
        if sref and sref not in sched_names:
            sched_bad.append({"object": obj.name, "schedule_ref": sref})
    if zone_names is None:
        rep.add("mep.load_to_zone", CheckStatus.NOT_APPLICABLE, CheckLayer.INVARIANT,
                message="no zone list supplied")
    elif zone_bad:
        rep.add_fail("mep.load_to_zone", CheckLayer.INVARIANT,
                     f"{len(zone_bad)} load(s) reference an unknown zone",
                     evidence={"offenders": zone_bad})
    else:
        rep.add_pass("mep.load_to_zone", CheckLayer.INVARIANT)
    if sched_bad:
        rep.add_fail("mep.load_to_schedule", CheckLayer.INVARIANT,
                     f"{len(sched_bad)} load(s) reference an undefined schedule",
                     evidence={"offenders": sched_bad})
    else:
        rep.add_pass("mep.load_to_schedule", CheckLayer.INVARIANT)


def _per_zone_coverage(
    rep: CheckReport, idx: IdfFragmentIndex, zone_names: set[str] | None
) -> None:
    """Each zone should carry People + Lights (flag — soft coverage)."""
    if not zone_names:
        rep.add("mep.per_zone_coverage", CheckStatus.NOT_APPLICABLE,
                CheckLayer.CROSS_CHECK, message="no zone list supplied")
        return
    people_zones = {o.fields[1] for o in idx.of_type("PEOPLE") if len(o.fields) > 1}
    lights_zones = {o.fields[1] for o in idx.of_type("LIGHTS") if len(o.fields) > 1}
    missing = {}
    for z in sorted(zone_names):
        gaps = [k for k, s in (("people", people_zones), ("lights", lights_zones)) if z not in s]
        if gaps:
            missing[z] = gaps
    if missing:
        rep.add_fail("mep.per_zone_coverage", CheckLayer.CROSS_CHECK,
                     f"{len(missing)} zone(s) missing a load object",
                     evidence={"missing": missing})
    else:
        rep.add_pass("mep.per_zone_coverage", CheckLayer.CROSS_CHECK,
                     evidence={"zones": len(zone_names)})


def _simpleglazing_standalone(rep: CheckReport, idx: IdfFragmentIndex) -> None:
    glaz = idx.has_name("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM")
    bad = []
    for c in idx.of_type("CONSTRUCTION"):
        layers = [x for x in c.fields[1:] if x]
        if any(layer in glaz for layer in layers) and len(layers) != 1:
            bad.append({"construction": c.name, "layers": layers})
    if bad:
        rep.add_fail("mep.simpleglazing_standalone", CheckLayer.INVARIANT,
                     f"{len(bad)} construction(s) embed SimpleGlazingSystem in a "
                     f"multi-layer construction (must be standalone — EP NaN fatal)",
                     evidence={"offenders": bad})
    else:
        rep.add_pass("mep.simpleglazing_standalone", CheckLayer.INVARIANT)


def _nomass_positive_resistance(rep: CheckReport, idx: IdfFragmentIndex) -> None:
    bad = []
    for m in idx.of_type("MATERIAL:NOMASS"):
        # fields = [name, roughness, thermal_resistance, ...]
        try:
            r = float(m.fields[2]) if len(m.fields) > 2 else 0.0
        except ValueError:
            r = 0.0
        if r <= 0:
            bad.append({"material": m.name, "thermal_resistance": m.fields[2] if len(m.fields) > 2 else None})
    if bad:
        rep.add_fail("mep.nomass_positive_resistance", CheckLayer.INVARIANT,
                     f"{len(bad)} Material:NoMass with non-positive thermal resistance",
                     evidence={"offenders": bad})
    else:
        rep.add_pass("mep.nomass_positive_resistance", CheckLayer.INVARIANT)


def _reasonability_placeholder(rep: CheckReport) -> None:
    """Placeholder: LPD/density/setpoint/U-value bands — filled once MEP input is
    richer (§5.2). Recorded as NOT_APPLICABLE so the framework slot is visible."""
    rep.add("mep.reasonability_bands", CheckStatus.NOT_APPLICABLE,
            CheckLayer.CROSS_CHECK,
            message="reasonability bands deferred until MEP input is richer (§5.2)")
