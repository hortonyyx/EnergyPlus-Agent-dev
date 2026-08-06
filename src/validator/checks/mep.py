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

import re

from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus, RunProfile
from src.validator.idf_fragments import IdfFragmentIndex, parse_mep_fragments
from src.validator.schedules import validate_schedule_completeness

# Object types whose names can appear as a Construction layer.
_MATERIAL_TYPES = (
    "MATERIAL", "MATERIAL:NOMASS", "MATERIAL:AIRGAP",
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM", "WINDOWMATERIAL:GLAZING",
    "WINDOWMATERIAL:GAS", "WINDOWMATERIAL:BLIND", "MATERIAL:INFRAREDTRANSPARENT",
)
_WINDOW_MATERIAL_TYPES = tuple(t for t in _MATERIAL_TYPES if t.startswith("WINDOWMATERIAL:"))
_LOAD_TYPES = ("PEOPLE", "LIGHTS", "ELECTRICEQUIPMENT")
_HVAC_SCHEDULE_REF_FIELDS = {
    "ZONECONTROL:THERMOSTAT": ("Control_Type_Schedule_Name",),
    "THERMOSTATSETPOINT:DUALSETPOINT": (
        "Heating_Setpoint_Temperature_Schedule_Name",
        "Cooling_Setpoint_Temperature_Schedule_Name",
    ),
    "THERMOSTATSETPOINT:SINGLEHEATING": ("Setpoint_Temperature_Schedule_Name",),
    "THERMOSTATSETPOINT:SINGLECOOLING": ("Setpoint_Temperature_Schedule_Name",),
    "THERMOSTATSETPOINT:SINGLEHEATINGORCOOLING": ("Setpoint_Temperature_Schedule_Name",),
    "ZONEHVAC:IDEALLOADSAIRSYSTEM": ("Availability_Schedule_Name",),
    "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM": ("System_Availability_Schedule_Name",),
    "HVACTEMPLATE:THERMOSTAT": (
        "Heating_Setpoint_Schedule_Name",
        "Cooling_Setpoint_Schedule_Name",
    ),
}
_NAME_CHARSET_TYPES = _MATERIAL_TYPES + ("CONSTRUCTION", "SCHEDULE:COMPACT", "SCHEDULETYPELIMITS")
_NAME_CHARSET_RE = re.compile(r"^[A-Za-z0-9_ -]+$")
_SITE_FIELD_ALIASES = {
    "latitude": ("latitude", "Latitude"),
    "longitude": ("longitude", "Longitude"),
    "time_zone": ("time_zone", "time zone", "timezone", "Time Zone", "TimeZone"),
    "elevation": ("elevation", "Elevation"),
}
_SITE_FIELD_TOLERANCES = {
    "latitude": 0.01,
    "longitude": 0.01,
    "time_zone": 0.1,
    "elevation": 1.0,
}
_TESTDATA_SITE_CONTAINERS = ("site_location", "Site Location", "site", "Site")
_PLACEHOLDER_PATTERNS = (
    ("TBD", re.compile(r"(?<![A-Za-z0-9_])tbd(?![A-Za-z0-9_])", re.IGNORECASE)),
    (
        "same as above",
        re.compile(r"(?<![A-Za-z0-9_])same\s+as\s+above(?![A-Za-z0-9_])", re.IGNORECASE),
    ),
    (
        "see above",
        re.compile(r"(?<![A-Za-z0-9_])see\s+above(?![A-Za-z0-9_])", re.IGNORECASE),
    ),
    ("etc.", re.compile(r"(?<![A-Za-z0-9_])etc\.(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("ellipsis", re.compile(r"\.\.\.|…")),
    (
        "angle-placeholder",
        re.compile(
            r"<\s*[A-Za-z0-9_ -]*(?:placeholder|tbd|todo|insert|replace)[A-Za-z0-9_ -]*\s*>",
            re.IGNORECASE,
        ),
    ),
)


def check_mep(
    mep: dict | object,
    *,
    used_constructions: set[str] | None = None,
    zone_names: set[str] | None = None,
    geometry_idf: str = "",
    testdata: dict | None = None,
    capability_profile: str = "rectangular",
    run_profile: RunProfile = "exploratory",
) -> CheckReport:
    rep = CheckReport(
        stage="4_mep",
        capability_profile=capability_profile,
        run_profile=run_profile,
    )
    idx = parse_mep_fragments(mep, extra_idf=geometry_idf)
    if not idx.ok:
        rep.add("mep.idf_parse", CheckStatus.ERROR, CheckLayer.INVARIANT,
                message=f"MEP fragment parse failed: {idx.parse_error}")
        return rep  # fail-closed; nothing else can be trusted
    rep.add_pass("mep.idf_parse", CheckLayer.INVARIANT)

    _placeholder_ban(rep, mep, idx)
    _name_charset(rep, idx)
    _north_axis_placeholder(rep, mep)
    _site_matches_testdata(rep, mep, testdata)
    _construction_coverage(rep, idx, used_constructions)
    _construction_to_material(rep, idx)
    _construction_thermal_mass(rep, idx)
    _schedule_type_refs(rep, idx)
    _schedule_completeness(rep, idx)
    _load_refs(rep, idx, zone_names)
    _hvac_schedule_refs(rep, idx)
    _per_zone_coverage(rep, idx, zone_names)
    _simpleglazing_standalone(rep, idx)
    _nomass_positive_resistance(rep, idx)
    _reasonability_placeholder(rep)
    return rep


def _material_names(idx: IdfFragmentIndex) -> set[str]:
    return idx.has_name(*_MATERIAL_TYPES)


def _material_types_by_name(idx: IdfFragmentIndex) -> dict[str, set[str]]:
    by_name: dict[str, set[str]] = {}
    for obj in idx.of_type(*_MATERIAL_TYPES):
        by_name.setdefault(obj.name, set()).add(obj.obj_type)
    return by_name


def _construction_layers(obj) -> list[str]:
    # Strip trailing empties (eppy pads optional layer fields) before judging.
    layers = [str(layer or "").strip() for layer in obj.fields[1:]]
    while layers and not layers[-1]:
        layers.pop()
    return layers


def _placeholder_ban(rep: CheckReport, mep: dict | object, idx: IdfFragmentIndex) -> None:
    offenders = []
    for obj in idx.objects:
        for i, value in enumerate(obj.fields):
            match = _placeholder_match(value)
            if match:
                offenders.append(
                    {
                        "surface": "parsed_idf_field",
                        "object_type": obj.obj_type,
                        "object": obj.name,
                        "field_index": i,
                        "token": match,
                        "value": value,
                    }
                )
    for path, value in _structured_string_values(mep):
        match = _placeholder_match(value)
        if match:
            offenders.append(
                {"surface": "structured_mep_field", "path": path, "token": match, "value": value}
            )
    evidence = {
        "scanned_surface": (
            "parsed IDF fragment field values plus structured building/site string fields"
        ),
        "guards": (
            "case-insensitive token/phrase patterns use non-word boundaries; ellipsis "
            "requires literal ... or …; angle placeholders require placeholder/tbd/todo/"
            "insert/replace text inside <>"
        ),
    }
    if offenders:
        rep.add_fail(
            "mep.placeholder_ban",
            CheckLayer.INVARIANT,
            f"{len(offenders)} MEP-authored field(s) contain placeholder/template prose",
            evidence=evidence | {"offenders": offenders},
        )
    else:
        rep.add_pass("mep.placeholder_ban", CheckLayer.INVARIANT, evidence=evidence)


def _placeholder_match(value: object) -> str | None:
    text = str(value or "")
    for label, pattern in _PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            return label
    return None


def _structured_string_values(mep: dict | object) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for parent_name in ("building", "site_location"):
        parent = _get_value(mep, parent_name)
        name = _get_value(parent, "name")
        if isinstance(name, str):
            out.append((f"{parent_name}.name", name))
    return out


def _get_value(obj: object, key: str) -> object:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _name_charset(rep: CheckReport, idx: IdfFragmentIndex) -> None:
    offenders = []
    for obj in idx.of_type(*_NAME_CHARSET_TYPES):
        if _NAME_CHARSET_RE.fullmatch(obj.name or ""):
            continue
        offenders.append(
            {
                "object_type": obj.obj_type,
                "name": obj.name,
                "illegal_chars": sorted({c for c in obj.name if not _name_char_allowed(c)}),
            }
        )
    evidence = {
        "allowed_charset": "letters, digits, underscore, hyphen, and space",
        "allowed_pattern": r"^[A-Za-z0-9_ -]+$",
        "scanned_object_types": sorted(set(_NAME_CHARSET_TYPES)),
    }
    if offenders:
        rep.add_fail(
            "mep.name_charset",
            CheckLayer.CROSS_CHECK,
            f"{len(offenders)} MEP-authored object name(s) contain non EP-safe characters",
            evidence=evidence | {"offenders": offenders},
        )
    else:
        rep.add_pass("mep.name_charset", CheckLayer.CROSS_CHECK, evidence=evidence)


def _name_char_allowed(char: str) -> bool:
    return char.isascii() and (char.isalnum() or char in {"_", "-", " "})


def _north_axis_placeholder(rep: CheckReport, mep: dict | object) -> None:
    """S4 (E4-output-contract spec v2 §4.1): 4_MEP's `building.north_axis` is a
    compatibility placeholder ONLY — the single authoritative owner of the
    final `Building.North Axis` is the accepted correction's orientation
    evidence (S5 override, §4.2). MEP may never author a real value here;
    `0.0` (the BuildingSchema default) is the only legal placeholder, for
    every schema_version/capability_profile, so a non-zero LLM guess is
    caught here rather than silently "corrected" downstream. `-0.0` compares
    equal to `0.0` in Python and is accepted."""
    building = _get_value(mep, "building")
    value = _get_value(building, "north_axis")
    evidence = {
        "field": "building.north_axis",
        "required_placeholder": 0.0,
        "observed": value,
        "owner": (
            "the accepted correction's NorthAxisEvidence (S5 unconditional override); "
            "4_mep may not author a real value"
        ),
    }
    is_numeric_zero = isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) == 0.0
    if not is_numeric_zero:
        rep.add_fail(
            "mep.building_north_axis_placeholder", CheckLayer.INVARIANT,
            f"building.north_axis must be the 0.0 compatibility placeholder, got {value!r}",
            evidence=evidence,
        )
    else:
        rep.add_pass("mep.building_north_axis_placeholder", CheckLayer.INVARIANT, evidence=evidence)


def _site_matches_testdata(
    rep: CheckReport, mep: dict | object, testdata: dict | None
) -> None:
    expected, schema_evidence = _extract_testdata_site(testdata)
    evidence = {
        **schema_evidence,
        "tolerances": _SITE_FIELD_TOLERANCES,
    }
    if not expected:
        rep.add(
            "mep.site_matches_testdata",
            CheckStatus.NOT_APPLICABLE,
            CheckLayer.CROSS_CHECK,
            message=(
                "no comparable structured site fields in testdata "
                "(latitude/longitude/time_zone/elevation)"
            ),
            evidence=evidence,
        )
        return

    actual = _extract_mep_site(mep)
    offenders = []
    for field, expected_value in expected.items():
        actual_value = actual.get(field)
        if actual_value is None:
            offenders.append({"field": field, "expected": expected_value, "actual": None})
            continue
        delta = abs(actual_value - expected_value)
        tolerance = _SITE_FIELD_TOLERANCES[field]
        if delta > tolerance:
            offenders.append(
                {
                    "field": field,
                    "expected": expected_value,
                    "actual": actual_value,
                    "delta": delta,
                    "tolerance": tolerance,
                }
            )
    evidence |= {
        "comparison": "real",
        "compared_fields": sorted(expected),
    }
    if offenders:
        rep.add_fail(
            "mep.site_matches_testdata",
            CheckLayer.CROSS_CHECK,
            f"{len(offenders)} MEP site field(s) differ from structured testdata",
            evidence=evidence | {"offenders": offenders},
        )
    else:
        rep.add_pass("mep.site_matches_testdata", CheckLayer.CROSS_CHECK, evidence=evidence)


def _extract_testdata_site(testdata: dict | None) -> tuple[dict[str, float], dict]:
    evidence = {
        "testdata_schema": "none supplied",
        "structured_site_fields": [],
        "location_string_fields": [],
    }
    if not isinstance(testdata, dict):
        return {}, evidence

    candidates = [testdata]
    for key in _TESTDATA_SITE_CONTAINERS:
        value = testdata.get(key)
        if isinstance(value, dict):
            candidates.insert(0, value)

    out: dict[str, float] = {}
    for candidate in candidates:
        for field, aliases in _SITE_FIELD_ALIASES.items():
            if field in out:
                continue
            value = _first_numeric(candidate, aliases)
            if value is not None:
                out[field] = value

    string_fields = [
        key
        for key in ("Building location", "building_location", "location", "Location")
        if isinstance(testdata.get(key), str)
    ]
    evidence = {
        "testdata_schema": (
            "searched top-level keys and nested site/site_location objects for numeric "
            "latitude/longitude/time_zone/elevation"
        ),
        "structured_site_fields": sorted(out),
        "location_string_fields": string_fields,
    }
    return out, evidence


def _extract_mep_site(mep: dict | object) -> dict[str, float]:
    site = _get_value(mep, "site_location")
    out: dict[str, float] = {}
    for field, aliases in _SITE_FIELD_ALIASES.items():
        value = _first_numeric(site, aliases)
        if value is not None:
            out[field] = value
    return out


def _first_numeric(obj: object, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = _get_value(obj, key)
        if value is None:
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                continue
    return None


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
        layers = _construction_layers(c)
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


def _construction_thermal_mass(rep: CheckReport, idx: IdfFragmentIndex) -> None:
    layer_types = _material_types_by_name(idx)
    bad = []
    skipped_fenestration = []
    checked = 0
    for c in idx.of_type("CONSTRUCTION"):
        layers = _construction_layers(c)
        resolved = [
            {"layer": layer, "types": sorted(layer_types.get(layer, set()))}
            for layer in layers
            if layer
        ]
        if any(
            obj_type in _WINDOW_MATERIAL_TYPES
            for item in resolved
            for obj_type in item["types"]
        ):
            skipped_fenestration.append(c.name)
            continue
        checked += 1
        has_mass_layer = any(layer_types.get(layer, set()) == {"MATERIAL"} for layer in layers)
        if not has_mass_layer:
            bad.append(
                {
                    "construction": c.name,
                    "layers": layers,
                    "resolved_layer_types": resolved,
                }
            )
    evidence = {
        "checked_opaque_constructions": checked,
        "skipped_fenestration_constructions": skipped_fenestration,
        "mass_layer_type": "MATERIAL",
        "non_mass_layer_types": [
            "MATERIAL:NOMASS",
            "MATERIAL:AIRGAP",
            "MATERIAL:INFRAREDTRANSPARENT",
        ],
        "out_of_scope_object_types": ["CONSTRUCTION:AIRBOUNDARY"],
    }
    if bad:
        rep.add_fail(
            "mep.construction_thermal_mass",
            CheckLayer.INVARIANT,
            f"{len(bad)} opaque construction(s) have no exact Material mass layer",
            evidence=evidence | {"offenders": bad},
        )
    else:
        rep.add_pass("mep.construction_thermal_mass", CheckLayer.INVARIANT, evidence=evidence)


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
    """People/Lights/Equipment → zone (field 1) and → schedule references."""
    sched_names = idx.has_name("SCHEDULE:COMPACT")
    zone_bad, sched_bad = [], []
    for obj in idx.of_type(*_LOAD_TYPES):
        zref = obj.fields[1] if len(obj.fields) > 1 else ""
        sref = obj.fields[2] if len(obj.fields) > 2 else ""
        if zone_names is not None and zref and zref not in zone_names:
            zone_bad.append({"object": obj.name, "zone_ref": zref})
        if sref and sref not in sched_names:
            sched_bad.append({"object": obj.name, "schedule_ref": sref})
        if obj.obj_type == "PEOPLE":
            activity_ref = _people_activity_schedule_name(obj)
            if not activity_ref:
                sched_bad.append(
                    {"object": obj.name, "activity_schedule_ref": "", "reason": "missing"}
                )
            elif activity_ref not in sched_names:
                sched_bad.append(
                    {"object": obj.name, "activity_schedule_ref": activity_ref}
                )
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
                     f"{len(sched_bad)} load schedule reference(s) are missing or undefined",
                     evidence={"offenders": sched_bad})
    else:
        rep.add_pass("mep.load_to_schedule", CheckLayer.INVARIANT)


def _hvac_schedule_refs(rep: CheckReport, idx: IdfFragmentIndex) -> None:
    sched_names = idx.has_name("SCHEDULE:COMPACT")
    bad = []
    checked = 0
    for obj_type, field_names in _HVAC_SCHEDULE_REF_FIELDS.items():
        for obj in idx.of_type(obj_type):
            for field_name in field_names:
                checked += 1
                schedule_ref = _raw_field_value(obj, field_name)
                if schedule_ref and schedule_ref not in sched_names:
                    bad.append(
                        {
                            "object_type": obj.obj_type,
                            "object": obj.name,
                            "field": field_name,
                            "schedule_ref": schedule_ref,
                        }
                    )
    evidence = {
        "checked_fields": checked,
        "field_table": _HVAC_SCHEDULE_REF_FIELDS,
        "blank_reference_policy": "pass",
        "resolved_schedule_type": "SCHEDULE:COMPACT",
        "deferred_fields": [
            "ZoneHVAC:IdealLoadsAirSystem.Heating_Availability_Schedule_Name",
            "ZoneHVAC:IdealLoadsAirSystem.Cooling_Availability_Schedule_Name",
            "HVACTemplate:Zone:IdealLoadsAirSystem.Heating_Availability_Schedule_Name",
            "HVACTemplate:Zone:IdealLoadsAirSystem.Cooling_Availability_Schedule_Name",
        ],
    }
    if bad:
        rep.add_fail(
            "mep.hvac_schedule_refs",
            CheckLayer.INVARIANT,
            f"{len(bad)} HVAC schedule reference(s) are undefined",
            evidence=evidence | {"offenders": bad},
        )
    else:
        rep.add_pass("mep.hvac_schedule_refs", CheckLayer.INVARIANT, evidence=evidence)


def _raw_field_value(obj, field_name: str) -> str:
    raw = getattr(obj, "raw", None)
    if raw is not None:
        try:
            return str(getattr(raw, field_name, "") or "").strip()
        except Exception:  # noqa: BLE001 - missing/invalid raw fields count as blank
            return ""
    return ""


def _people_activity_schedule_name(obj) -> str:
    """People.Activity Level Schedule Name via eppy raw object, then field 9."""
    raw = getattr(obj, "raw", None)
    if raw is not None:
        try:
            return str(getattr(raw, "Activity_Level_Schedule_Name", "") or "").strip()
        except Exception:  # noqa: BLE001 - fall back to parsed field layout
            pass
    if len(obj.fields) > 9:
        return str(obj.fields[9] or "").strip()
    return ""


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
