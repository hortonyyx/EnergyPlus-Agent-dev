"""2026-08-14 dispatch (摊 A): hvac_specs is rendered deterministically by
code inside run_mep, not authored by the LLM.

Background (F-28, 08-13 accept_C): the LLM wrote ZoneControl:Thermostat with
4 fields instead of the required 5 (Control 1 Name missing) -- every
EnergyPlus \\required-field after the gap silently shifted one position, and
mep.hvac_schedule_refs (which reads IDD-fixed field positions) read a bogus
schedule name out of what was actually the next object's type token. The run
quarantined after burning its resample budget. Same defect, left blank
instead of filled: the gate passes (blank_reference_policy: pass) and the run
proceeds all the way to EnergyPlus -- so "the gate didn't fire" was never
proof the run was correct, only that the model happened to leave that field
empty that time. The fix: the model no longer authors this section at all,
so there is no field position left for it to get wrong.

A1 (anti-false-verification, dispatch §4): every lock in this file drives the
REAL `run_mep` body by stubbing only `pipeline._call_json_llm` (the actual
network boundary run_mep calls internally) -- never by monkeypatching
`run_mep` itself. Patching `run_mep` wholesale is an established pattern
elsewhere in this repo for OTHER concerns (tests/test_a8_evidence_routing.py,
tests/test_checks_mep_assembly.py) but the dispatch explicitly rules it out
for this batch's locks: it would prove the stub returns what we told it to,
not that the real code path renders hvac_specs deterministically.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import scripts.tool_scripts.run_stage as rs
import src.agent.pipeline as pipeline
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution.policy import RunPolicy
from src.validator.checks.mep import check_mep
from src.validator.checks.schema import CheckStatus
from src.validator.idf_fragments import parse_idf_text

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SM21 = _REPO_ROOT / "case_tests" / "e2e_tests" / "sm21_anchor"

_SITE = {"latitude": 22.5, "longitude": 114.0, "time_zone": 8.0, "elevation": 5.0}
_ZONES = ["Z01_F1_Office_NW", "Z02_F1_Office_N", "Z03_F1_Corridor_C"]


# --------------------------------------------------------------------------- #
# shared fixtures / helpers
# --------------------------------------------------------------------------- #
def _mep_dict(
    hvac_specs: str = "",
    *,
    used_constructions: frozenset[str] = frozenset(),
    schedule_specs: str = "",
) -> dict:
    """A minimal MepOutput-shaped dict -- modeled on the equivalent helper in
    tests/test_run_pipeline_self_checks.py (proven to pass BuildingSchema /
    SiteLocationSchema validation). ``used_constructions``, when given, is
    rendered as a one-material-per-construction block (same pattern as that
    helper) -- needed only by callers that drive the full
    run_pipeline_artifacts assembly step, which hard-raises (regardless of
    run_profile -- this is 5_intakeoutput's assembly.contract_backstop, not a
    self-check gate) if the geometry references a construction 4_mep didn't
    define. ``schedule_specs`` lets a caller simulate what "the model" wrote
    for schedules (e.g. a reserved-name collision) -- run_mep's real body
    must fold this through _merge_hvac_det_schedules, not discard it (unlike
    hvac_specs, schedule_specs is the model's own field, just augmented)."""
    construction_specs = "".join(
        f"Construction,\n  {name},\n  Mat_Mass;\n\n" for name in sorted(used_constructions)
    )
    material_specs = (
        "Material,\n  Mat_Mass,\n  MediumRough,\n  0.1,\n  1.4,\n  2200,\n  880;\n"
        if used_constructions
        else ""
    )
    return {
        "building": {"name": "B", "north_axis": 0.0, "terrain": "City"},
        "site_location": {"name": "S", **_SITE},
        "material_specs": material_specs,
        "construction_specs": construction_specs,
        "schedule_specs": schedule_specs,
        "hvac_specs": hvac_specs,
        "people_specs": "",
        "lights_specs": "",
    }


def _fake_call_json_llm(
    hvac_specs_from_model: str,
    *,
    used_constructions: frozenset[str] = frozenset(),
    schedule_specs_from_model: str = "",
):
    """Stub for pipeline._call_json_llm (the LLM network boundary), NOT for
    run_mep. Returns a MepOutput-shaped dict whose hvac_specs is whatever the
    caller wants "the model" to have written -- run_mep's real body must
    discard it regardless of content."""

    def _fake(_section, _system_prompt, _human, *, out_dir, prefix, **_kwargs):
        assert prefix == "mep", f"unexpected _call_json_llm prefix={prefix!r}"
        return _mep_dict(
            hvac_specs_from_model,
            used_constructions=used_constructions,
            schedule_specs=schedule_specs_from_model,
        )

    return _fake


def _run_mep_real(
    monkeypatch,
    *,
    zone_names=_ZONES,
    hvac_specs_from_model: str = "GARBAGE_MODEL_HVAC_TEXT_MUST_NOT_SURVIVE",
    schedule_specs_from_model: str = "",
    out_dir: Path | None = None,
):
    """Drive the REAL run_mep body end to end, stubbing only the LLM call."""
    monkeypatch.setattr(
        pipeline,
        "_call_json_llm",
        _fake_call_json_llm(
            hvac_specs_from_model, schedule_specs_from_model=schedule_specs_from_model
        ),
    )
    return pipeline.run_mep(
        "dummy zone_specs text (free-text LLM guidance, not parsed by run_mep)",
        set(),
        "{}",
        zone_names=zone_names,
        out_dir=out_dir,
        feedback=None,
    )


def _status(report, check_id: str) -> CheckStatus:
    return next(r.status for r in report.results if r.check_id == check_id)


def _write_reading(vector_dir: Path) -> None:
    vector_dir.mkdir(parents=True, exist_ok=True)
    (vector_dir / "reading_summary.md").write_text("summary", encoding="utf-8")
    (vector_dir / "1f_view.json").write_text(
        json.dumps(
            {
                "image_kind": "plan",
                "uncaptured": [],
                "scale_origin": {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None},
                "strokes": [
                    {
                        "id": "S1",
                        "pen": "wall",
                        "provenance": "seen",
                        "confidence": "high",
                        "geometry": {"kind": "line", "p1": [0, 0], "p2": [2, 0]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _geom_3zones() -> CorrectedGeometry:
    """3 zones on one floor -- order matters for A3, so more than 1 zone."""
    return CorrectedGeometry.model_validate(
        {
            "footprint_x": [0.0, 6.0],
            "footprint_y": [0.0, 3.0],
            "floors": [
                {
                    "name": "F1",
                    "z_floor": 0.0,
                    "ceiling_height": 3.0,
                    "cells": [
                        {"id": "C1", "role": "office", "x": [0.0, 2.0], "y": [0.0, 3.0]},
                        {"id": "C2", "role": "office", "x": [2.0, 4.0], "y": [0.0, 3.0]},
                        {"id": "C3", "role": "corridor", "x": [4.0, 6.0], "y": [0.0, 3.0]},
                    ],
                }
            ],
            "windows": [],
            "conflicts": [],
            "corrections": [],
            "unsupported": [],
        }
    )


# --------------------------------------------------------------------------- #
# A1 -- anti-false-verification: the lock must be wired to the real render,
# neutering it must flip the lock red, restoring it must flip it back green.
# --------------------------------------------------------------------------- #
def test_a1_render_wired_neuter_flips_hvac_specs_content(monkeypatch):
    # Green: the real renderer runs, its signature content is present.
    result = _run_mep_real(monkeypatch, zone_names=_ZONES)
    assert "HVACTemplate:Thermostat," in result.hvac_specs
    assert "HVACTemplate:Zone:IdealLoadsAirSystem," in result.hvac_specs
    for zone in _ZONES:
        assert zone in result.hvac_specs

    # Red: neuter ONLY the renderer function (not run_mep) -> the exact same
    # assertions must now fail, proving they are coupled to the real code
    # path executing, not to a stub returning canned content.
    monkeypatch.setattr(pipeline, "_render_hvac_specs", lambda zone_names: "")
    neutered = _run_mep_real(monkeypatch, zone_names=_ZONES)
    assert neutered.hvac_specs == ""
    assert "HVACTemplate:Thermostat," not in neutered.hvac_specs


def test_a1_schedule_merge_wired_neuter_flips_the_real_gate(monkeypatch):
    """Same neuter/restore proof, routed through check_mep's real
    mep.hvac_schedule_refs gate instead of a string assertion we wrote
    ourselves -- ties the lock to a check this repo already trusts."""
    result = _run_mep_real(monkeypatch, zone_names=_ZONES)
    rep = check_mep(json.loads(result.model_dump_json()), zone_names=set(_ZONES))
    assert _status(rep, "mep.hvac_schedule_refs") == CheckStatus.PASS

    # Neuter the schedule merge: hvac_specs still REFERENCES the 3 reserved
    # schedules (the renderer is untouched), but they are no longer DEFINED.
    monkeypatch.setattr(
        pipeline, "_merge_hvac_det_schedules", lambda schedule_specs: schedule_specs
    )
    neutered = _run_mep_real(monkeypatch, zone_names=_ZONES)
    rep2 = check_mep(json.loads(neutered.model_dump_json()), zone_names=set(_ZONES))
    assert _status(rep2, "mep.hvac_schedule_refs") == CheckStatus.FAIL


# --------------------------------------------------------------------------- #
# A2 -- coverage lock: an obviously-wrong model hvac_specs (the literal
# accept_C field-shift shape) must not survive into the result at all.
# --------------------------------------------------------------------------- #
def test_a2_model_hvac_specs_content_is_discarded_even_when_broken(monkeypatch):
    # The literal accept_C defect: ZoneControl:Thermostat authored with 4
    # fields instead of the required 5 (Control 1 Name missing).
    accept_c_shaped_garbage = (
        "ZoneControl:Thermostat,\n"
        "  Z01_F1_Office_NW_Thermostat,\n"
        "  Z01_F1_Office_NW,\n"
        "  ThermostatSetpoint:DualSetpoint,\n"
        "  Z01_F1_Office_NW_DualSetpoint;\n"
    )
    result = _run_mep_real(
        monkeypatch, zone_names=_ZONES, hvac_specs_from_model=accept_c_shaped_garbage
    )
    assert "ZoneControl:Thermostat" not in result.hvac_specs
    assert "ThermostatSetpoint:DualSetpoint" not in result.hvac_specs
    assert accept_c_shaped_garbage.strip() not in result.hvac_specs
    # Exactly the renderer's output, byte for byte -- not merely "different".
    assert result.hvac_specs == pipeline._render_hvac_specs(_ZONES)


def test_a2_pure_garbage_string_is_discarded(monkeypatch):
    result = _run_mep_real(
        monkeypatch, zone_names=_ZONES, hvac_specs_from_model="not even IDF at all !!"
    )
    assert "not even IDF" not in result.hvac_specs
    assert result.hvac_specs == pipeline._render_hvac_specs(_ZONES)


# --------------------------------------------------------------------------- #
# A3 -- the flow call site (pipeline.py run_pipeline_artifacts) and the
# run_stage.py call site (_draw_mep -> real _geometry_zone_meta) must render
# byte-identical hvac_specs, including zone order, off the same corrected
# geometry.
# --------------------------------------------------------------------------- #
def test_a3_flow_and_run_stage_paths_render_identical_hvac_specs(tmp_path, monkeypatch):
    geom = _geom_3zones()
    vector_dir = tmp_path / "0_reading"
    _write_reading(vector_dir)
    monkeypatch.setattr(pipeline, "run_correction", lambda *_a, **_k: geom)
    # _geom_3zones is a single floor, no windows, with an interior partition
    # between zones -> geometry needs exactly these 4 constructions. This is
    # this fixture's own required set (single-floor, window-less), not
    # something run_mep or the renderer under test computes -- unrelated to
    # what A3 actually checks (hvac_specs parity), but 5_intakeoutput's
    # assembly.contract_backstop hard-raises if the geometry references a
    # construction 4_mep didn't define, regardless of run_profile, so the
    # fake LLM response has to satisfy it for run_pipeline_artifacts to reach
    # 4_mep's output at all.
    monkeypatch.setattr(
        pipeline,
        "_call_json_llm",
        _fake_call_json_llm(
            "GARBAGE_MODEL_HVAC_TEXT_MUST_NOT_SURVIVE",
            used_constructions=frozenset(
                {"Default_Ext_Wall", "Default_Int_Wall", "Default_GroundFloor", "Default_Roof"}
            ),
        ),
    )

    # Path A: the flow entry point -- the real call site in
    # run_pipeline_artifacts (src/agent/pipeline.py).
    out_dir_a = tmp_path / "flow_out"
    pipeline.run_pipeline_artifacts(
        vector_dir, "{}", out_dir=out_dir_a, run_profile="exploratory"
    )
    mep_a = json.loads((out_dir_a / "4_mep" / "mep_output.json").read_text())

    # Path B: the run_stage.py entry point -- the real _draw_mep ->
    # _geometry_zone_meta call site (scripts/tool_scripts/run_stage.py).
    # Feed it the EXACT post-snap geometry path A produced (byte-identical),
    # so this test isolates "do the two call sites compute the same zone
    # order from the same geometry", not "does the deterministic core snap
    # the same input the same way twice" (a different, already-covered
    # concern).
    snapped_bytes = (
        out_dir_a / "1_correction" / "correction_geometry_snapped.json"
    ).read_bytes()
    run_dir_b = tmp_path / "run_stage_out"
    (run_dir_b / "1_correction").mkdir(parents=True)
    (run_dir_b / "1_correction" / "correction_geometry_snapped.json").write_bytes(
        snapped_bytes
    )
    policy = RunPolicy(capability_profile="rectangular", run_profile="exploratory")
    mep_b, _rep_b = rs._draw_mep(run_dir_b, "{}", policy)

    assert mep_a["hvac_specs"] != ""
    assert mep_a["hvac_specs"] == mep_b.hvac_specs, (
        "flow and run_stage rendered different hvac_specs text off the same "
        "corrected geometry -- the two call sites' zone ordering diverged"
    )
    assert "HVACTemplate:Thermostat," in mep_a["hvac_specs"]

    # Zone order specifically (not just content/set equality).
    order_a = re.findall(
        r"HVACTemplate:Zone:IdealLoadsAirSystem,\n {2}(\S+),", mep_a["hvac_specs"]
    )
    order_b = re.findall(
        r"HVACTemplate:Zone:IdealLoadsAirSystem,\n {2}(\S+),", mep_b.hvac_specs
    )
    assert len(order_a) == 3
    assert order_a == order_b


# --------------------------------------------------------------------------- #
# A4 -- reference closure (independent lock): every schedule name the
# rendered hvac_specs references must exist in the merged schedule_specs.
# Uses only the project's shared IDF parser (idf_fragments.parse_idf_text),
# not check_mep's own _hvac_schedule_refs implementation -- so this does not
# just re-run the same check twice under a different name.
# --------------------------------------------------------------------------- #
def test_a4_referenced_schedules_exist_in_merged_schedule_specs():
    hvac_specs = pipeline._render_hvac_specs(_ZONES)
    schedule_specs = pipeline._merge_hvac_det_schedules("")  # no model schedules at all

    hvac_idx = parse_idf_text(hvac_specs)
    assert hvac_idx.ok, hvac_idx.parse_error
    sched_idx = parse_idf_text(schedule_specs)
    assert sched_idx.ok, sched_idx.parse_error
    defined = sched_idx.has_name("SCHEDULE:COMPACT")

    referenced = set()
    for obj in hvac_idx.of_type("HVACTEMPLATE:THERMOSTAT"):
        for field_name in ("Heating_Setpoint_Schedule_Name", "Cooling_Setpoint_Schedule_Name"):
            value = str(getattr(obj.raw, field_name, "") or "").strip()
            if value:
                referenced.add(value)
    for obj in hvac_idx.of_type("HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM"):
        value = str(getattr(obj.raw, "System_Availability_Schedule_Name", "") or "").strip()
        if value:
            referenced.add(value)

    assert referenced, "expected at least one hvac schedule reference to test"
    assert referenced <= defined, f"referenced but undefined: {referenced - defined}"


def test_merge_hvac_det_schedules_never_touches_generic_type_limits(monkeypatch):
    """2026-08-14 terra 2nd re-review: the 3 canonical schedules must NOT
    reference the generic Temperature/OnOff names at all (they reference 2
    exclusive reserved names instead) -- so a model definition of the
    generic names, however it's shaped, is simply none of this function's
    business: not read, not overridden, not duplicated. Reproduces terra's
    literal 2nd-pass finding (narrowed Temperature/OnOff that would have put
    the code's 20/24/1 out of range under the old generic-name design) and
    asserts it survives byte-for-byte -- not merely "doesn't duplicate"."""
    narrowed_generic = (
        "ScheduleTypeLimits, Temperature, 30, 40, Continuous;\n"
        "ScheduleTypeLimits, OnOff, 2, 3, Discrete;\n"
    )
    merged = pipeline._merge_hvac_det_schedules(narrowed_generic)
    idx = parse_idf_text(merged)
    assert idx.ok, idx.parse_error

    generic_temperature = [o for o in idx.of_type("SCHEDULETYPELIMITS") if o.name == "Temperature"]
    generic_onoff = [o for o in idx.of_type("SCHEDULETYPELIMITS") if o.name == "OnOff"]
    assert len(generic_temperature) == 1
    assert generic_temperature[0].fields == ["Temperature", "30.0", "40.0", "Continuous"]
    assert len(generic_onoff) == 1
    assert generic_onoff[0].fields == ["OnOff", "2.0", "3.0", "Discrete"]

    # The 2 exclusive reserved type limits are always added, independent of
    # what the model did with the generic names.
    reserved_names = idx.has_name("SCHEDULETYPELIMITS")
    assert pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT in reserved_names
    assert pipeline._HVAC_DET_ONOFF_TYPE_LIMIT in reserved_names

    # And the 3 canonical schedules reference ONLY the reserved names, never
    # the generic ones -- so the model's narrowed range cannot constrain them.
    for obj in idx.of_type("SCHEDULE:COMPACT"):
        if obj.name in (
            pipeline._HVAC_DET_HEATING_SCHEDULE,
            pipeline._HVAC_DET_COOLING_SCHEDULE,
            pipeline._HVAC_DET_AVAILABILITY_SCHEDULE,
        ):
            type_limit_ref = obj.fields[1]
            assert type_limit_ref in (
                pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT,
                pipeline._HVAC_DET_ONOFF_TYPE_LIMIT,
            ), f"{obj.name} references {type_limit_ref!r}, expected a reserved type limit"


def test_merge_hvac_det_reserved_type_limits_are_case_insensitively_owned():
    """The 2 reserved type-limit names get the SAME code-ownership treatment
    as the 3 reserved schedule names: a model-authored same-named definition
    (any case) is excluded, the code's own is appended unconditionally."""
    collision = (
        f"ScheduleTypeLimits, {pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT.lower()}, 5, 6, Continuous;\n"
        f"ScheduleTypeLimits, {pipeline._HVAC_DET_ONOFF_TYPE_LIMIT.upper()}, 7, 8, Discrete;\n"
    )
    merged = pipeline._merge_hvac_det_schedules(collision)
    idx = parse_idf_text(merged)
    assert idx.ok, idx.parse_error

    temp_objs = [
        o for o in idx.of_type("SCHEDULETYPELIMITS")
        if o.name.lower() == pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT.lower()
    ]
    onoff_objs = [
        o for o in idx.of_type("SCHEDULETYPELIMITS")
        if o.name.lower() == pipeline._HVAC_DET_ONOFF_TYPE_LIMIT.lower()
    ]
    assert len(temp_objs) == 1
    assert temp_objs[0].fields == [pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT, "-60.0", "200.0", "Continuous"]
    assert len(onoff_objs) == 1
    assert onoff_objs[0].fields == [pipeline._HVAC_DET_ONOFF_TYPE_LIMIT, "0.0", "1.0", "Discrete"]


# --------------------------------------------------------------------------- #
# REWORK (2026-08-14 terra cross-review, verdict
# logs/reviews/verdict/2026-08-14_seatAB_crossreview_terra.md) -- A's
# blocking finding: the first version of _merge_hvac_det_schedules only
# de-duplicated ScheduleTypeLimits, not the 3 reserved Schedule:Compact
# names themselves. The model is told not to author these (authoring.md,
# the system prompt) but that instruction is not a constraint -- this
# repo's own model-visible-but-not-its-business lesson, cited directly in
# the verdict. terra's reproduction: pre-seed schedule_specs with the 3
# exact reserved names (arbitrary values) and call the merge function --
# parses fine, all 3 names appear twice, mep.hvac_schedule_refs still PASS,
# check_mep still passed=True overall. Fixed in _merge_hvac_det_schedules
# by excluding (via eppy removeidfobject, not string surgery) any
# Schedule:Compact whose name matches a reserved name CASE-INSENSITIVELY
# (EnergyPlus name lookups are case-insensitive) before appending the
# code's own. This lock drives the real run_mep body (not just the merge
# helper in isolation) with a stubbed _call_json_llm returning a
# schedule_specs that collides on all 3 reserved names PLUS extra
# uppercase/lowercase variants (terra's explicit ask: "再加至少一个大小写
# 变体"), and asserts each reserved name appears EXACTLY ONCE with the
# code's canonical value -- not merely that eppy parses the result.
# --------------------------------------------------------------------------- #
def test_reserved_schedule_names_are_truly_code_owned_not_just_deduplicated(monkeypatch):
    # 3 exact-case collisions (terra's literal reproduction) + 2 additional
    # case-variant collisions on the availability schedule (upper-case name,
    # then a second, differently-cased duplicate of the same name) -- 5
    # colliding objects total across 3 reserved names, plus one completely
    # unrelated schedule that must survive untouched.
    model_schedule_specs = (
        "ScheduleTypeLimits, Fraction, 0, 1, Continuous;\n"
        "Schedule:Compact, Sch_HVACDet_HeatingSetpoint, Temperature,\n"
        "  Through: 12/31,\n"
        "  For: AllDays,\n"
        "  Until: 24:00, 99;\n"
        "Schedule:Compact, sch_hvacdet_coolingsetpoint, Temperature,\n"
        "  Through: 12/31,\n"
        "  For: AllDays,\n"
        "  Until: 24:00, 99;\n"
        "Schedule:Compact, SCH_HVACDET_AVAILABILITY, OnOff,\n"
        "  Through: 12/31,\n"
        "  For: AllDays,\n"
        "  Until: 24:00, 99;\n"
        "Schedule:Compact, Sch_HVACDET_Availability, OnOff,\n"
        "  Through: 12/31,\n"
        "  For: AllDays,\n"
        "  Until: 24:00, 5;\n"
        "Schedule:Compact, Sch_Occupancy, Fraction,\n"
        "  Through: 12/31,\n"
        "  For: AllDays,\n"
        "  Until: 24:00, 1.0;\n"
    )
    result = _run_mep_real(
        monkeypatch,
        zone_names=_ZONES,
        schedule_specs_from_model=model_schedule_specs,
    )

    idx = parse_idf_text(result.schedule_specs)
    assert idx.ok, idx.parse_error

    expected_values = {
        pipeline._HVAC_DET_HEATING_SCHEDULE: "20.0",
        pipeline._HVAC_DET_COOLING_SCHEDULE: "24.0",
        pipeline._HVAC_DET_AVAILABILITY_SCHEDULE: "1.0",
    }
    for name, expected_value in expected_values.items():
        matches = [
            o for o in idx.of_type("SCHEDULE:COMPACT") if o.name.lower() == name.lower()
        ]
        assert len(matches) == 1, (
            f"{name}: expected exactly one Schedule:Compact (case-insensitive) "
            f"in the schedule_specs handed to the schedule agent, found "
            f"{len(matches)}: {[m.name for m in matches]}"
        )
        assert matches[0].fields[-1] == expected_value, (
            f"{name}: expected the code's canonical value {expected_value!r}, "
            f"got {matches[0].fields[-1]!r} — a model-authored value must "
            f"never survive under a reserved name"
        )

    # None of the model's absurd values survive anywhere in the merged text
    # (the per-name field assertions above already prove the *reserved*
    # schedules carry the code's values, not the model's -- this additionally
    # rules out the value leaking in some other form, e.g. a stray comment).
    assert "99" not in result.schedule_specs
    # The second availability collision's value (5) is distinctive enough in
    # this fixture (no other "Until:" line uses it) to check directly.
    survivors = [obj.fields[-1] for obj in idx.of_type("SCHEDULE:COMPACT")]
    assert "5" not in survivors and "5.0" not in survivors

    # The one unrelated schedule the model wrote is untouched.
    occupancy = [o for o in idx.of_type("SCHEDULE:COMPACT") if o.name == "Sch_Occupancy"]
    assert len(occupancy) == 1
    assert occupancy[0].fields[-1] == "1.0"

    # And the gate this used to sneak past now sees a clean bundle: run it
    # for real, not just eppy-parses -- terra's explicit "不能只断言 eppy
    # 能解析" instruction.
    rep = check_mep(
        json.loads(result.model_dump_json()),
        zone_names=set(_ZONES),
    )
    assert _status(rep, "mep.hvac_schedule_refs") == CheckStatus.PASS
    assert _status(rep, "mep.schedule_type_refs") == CheckStatus.PASS
    assert _status(rep, "mep.idf_parse") == CheckStatus.PASS


def test_reserved_schedule_ownership_neuter_flips_lock_red(monkeypatch):
    """A1-style wiring proof for the fix above: neuter the exclusion (by
    reverting _merge_hvac_det_schedules to the pre-fix behavior of only
    de-duplicating ScheduleTypeLimits) and confirm the SAME collision
    scenario now produces 2 copies of a reserved name -- i.e. the lock
    above is actually coupled to the exclusion logic, not vacuously true."""

    def _neutered_merge_without_schedule_exclusion(schedule_specs: str) -> str:
        # Faithful reconstruction of the pre-fix behavior: only skip
        # ScheduleTypeLimits already present (case-sensitive, as it
        # originally was); unconditionally append the 3 reserved schedules
        # with no exclusion of same-named model-authored ones.
        idx = parse_idf_text(schedule_specs)
        existing_type_limits = idx.has_name("SCHEDULETYPELIMITS") if idx.ok else set()
        addendum = [
            text
            for name, text in pipeline._HVAC_DET_TYPE_LIMITS.items()
            if name not in existing_type_limits
        ]
        addendum.append(pipeline._hvac_det_schedule_block())
        merged = schedule_specs.rstrip()
        if merged:
            merged += "\n\n"
        merged += "\n".join(addendum)
        return merged

    monkeypatch.setattr(
        pipeline, "_merge_hvac_det_schedules", _neutered_merge_without_schedule_exclusion
    )
    model_schedule_specs = (
        "Schedule:Compact, Sch_HVACDet_HeatingSetpoint, Temperature,\n"
        "  Through: 12/31,\n"
        "  For: AllDays,\n"
        "  Until: 24:00, 99;\n"
    )
    result = _run_mep_real(
        monkeypatch,
        zone_names=_ZONES,
        schedule_specs_from_model=model_schedule_specs,
    )
    idx = parse_idf_text(result.schedule_specs)
    assert idx.ok, idx.parse_error
    matches = [
        o for o in idx.of_type("SCHEDULE:COMPACT")
        if o.name.lower() == pipeline._HVAC_DET_HEATING_SCHEDULE.lower()
    ]
    assert len(matches) == 2, (
        "neutering the exclusion should reproduce the pre-fix duplicate — "
        f"got {len(matches)} copies, expected 2 (proves the real fix's lock "
        "above is coupled to real code, not vacuous)"
    )


# --------------------------------------------------------------------------- #
# REWORK #2 (2026-08-14 terra 2nd re-review, verdict
# logs/reviews/verdict/2026-08-14_seatA_rework_rereview_terra.md) -- the
# rework #1 fix bound the 3 canonical schedules to the GENERIC ScheduleType-
# Limits names Temperature/OnOff (only adding the code's definition if the
# model hadn't already defined that name, deliberately, to avoid tampering
# with unrelated model schedules that might share those names). That left
# the 3 "code-owned" schedules depending on something the model still fully
# controlled: terra reproduced (a) a model response narrowing Temperature
# to `30, 40` / OnOff to `2, 3` silently puts the code's own 20/24/1 values
# out of the declared range (all of mep.idf_parse / mep.schedule_type_refs
# / mep.schedule_completeness / mep.hvac_schedule_refs still PASS,
# check_mep.passed=True — no existing gate catches it), and (b) a model
# response spelling it lower-case `temperature` makes the case-insensitive
# "already defined" check skip adding `Temperature`, while the canonical
# schedules still spell it exact-case `Temperature` — and this repo's
# mep.schedule_type_refs is a case-SENSITIVE set comparison, so THAT
# combination flips mep.schedule_type_refs to FAIL (a regression rework #1
# itself introduced). Fixed by giving the 3 schedules 2 EXCLUSIVE reserved
# type-limit names (HVACDet_Temperature / HVACDet_OnOff) that get the exact
# same code-ownership treatment as the 3 reserved schedule names, so
# nothing the model does to the generic Temperature/OnOff names can affect
# them. This lock drives the real run_mep body, pre-seeding BOTH failure
# shapes simultaneously (terra's explicit ask): a narrowed generic
# Temperature/OnOff, AND a case-collision on the exclusive reserved names.
# --------------------------------------------------------------------------- #
def test_reserved_schedules_immune_to_narrowed_generic_and_exclusive_name_collision(
    monkeypatch,
):
    model_schedule_specs = (
        # (a) narrowed generic type limits -- under the pre-fix design this
        # would have put the code's 20/24 heating/cooling values out of range.
        "ScheduleTypeLimits, Temperature, 30, 40, Continuous;\n"
        "ScheduleTypeLimits, OnOff, 2, 3, Discrete;\n"
        # An unrelated schedule that legitimately depends on the generic
        # Temperature name -- must survive untouched (proves the model's
        # own use of the generic name is not collateral damage).
        "Schedule:Compact, Sch_SomeOtherSetback, Temperature,\n"
        "  Through: 12/31,\n"
        "  For: AllDays,\n"
        "  Until: 24:00, 35;\n"
        # (b) case collision on the exclusive reserved names themselves --
        # under the pre-fix design the case-insensitive "already defined"
        # check would have skipped adding HVACDet_Temperature while the
        # canonical schedules still spelled it exact-case.
        "ScheduleTypeLimits, hvacdet_temperature, -1, 1, Continuous;\n"
        "ScheduleTypeLimits, HVACDET_ONOFF, -1, 1, Discrete;\n"
    )
    result = _run_mep_real(
        monkeypatch,
        zone_names=_ZONES,
        schedule_specs_from_model=model_schedule_specs,
    )
    idx = parse_idf_text(result.schedule_specs)
    assert idx.ok, idx.parse_error

    # 1. The 3 canonical schedules are each unique, still 20/24/1.
    expected_values = {
        pipeline._HVAC_DET_HEATING_SCHEDULE: "20.0",
        pipeline._HVAC_DET_COOLING_SCHEDULE: "24.0",
        pipeline._HVAC_DET_AVAILABILITY_SCHEDULE: "1.0",
    }
    schedules_by_name = {}
    for name, expected_value in expected_values.items():
        matches = [o for o in idx.of_type("SCHEDULE:COMPACT") if o.name.lower() == name.lower()]
        assert len(matches) == 1, f"{name}: expected exactly one, found {len(matches)}"
        assert matches[0].fields[-1] == expected_value
        schedules_by_name[name] = matches[0]

    # 2. They only reference the exclusive canonical type limits, with
    #    correct range/numeric type each -- not the generic or collided names.
    reserved_type_limits = {
        o.name.lower(): o for o in idx.of_type("SCHEDULETYPELIMITS")
        if o.name.lower() in {
            pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT.lower(),
            pipeline._HVAC_DET_ONOFF_TYPE_LIMIT.lower(),
        }
    }
    assert len(reserved_type_limits) == 2, (
        f"expected exactly the 2 reserved type limits (case-insensitive), "
        f"found: {list(reserved_type_limits)}"
    )
    temp_limit = reserved_type_limits[pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT.lower()]
    onoff_limit = reserved_type_limits[pipeline._HVAC_DET_ONOFF_TYPE_LIMIT.lower()]
    # exact-case name (the collision's lower/upper-case copies were excluded)
    assert temp_limit.name == pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT
    assert onoff_limit.name == pipeline._HVAC_DET_ONOFF_TYPE_LIMIT
    # code's own range/type, not the collision's `-1, 1`
    assert temp_limit.fields == [pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT, "-60.0", "200.0", "Continuous"]
    assert onoff_limit.fields == [pipeline._HVAC_DET_ONOFF_TYPE_LIMIT, "0.0", "1.0", "Discrete"]
    for sched_name, sched_obj in schedules_by_name.items():
        type_limit_ref = sched_obj.fields[1]
        assert type_limit_ref in (
            pipeline._HVAC_DET_TEMPERATURE_TYPE_LIMIT,
            pipeline._HVAC_DET_ONOFF_TYPE_LIMIT,
        ), f"{sched_name} references {type_limit_ref!r}, not a reserved type limit"

    # 3. The model's generic type limits (and the unrelated schedule
    #    depending on them) are NOT rewritten.
    generic_temp = [o for o in idx.of_type("SCHEDULETYPELIMITS") if o.name == "Temperature"]
    generic_onoff = [o for o in idx.of_type("SCHEDULETYPELIMITS") if o.name == "OnOff"]
    assert len(generic_temp) == 1
    assert generic_temp[0].fields == ["Temperature", "30.0", "40.0", "Continuous"]
    assert len(generic_onoff) == 1
    assert generic_onoff[0].fields == ["OnOff", "2.0", "3.0", "Discrete"]
    other_setback = [o for o in idx.of_type("SCHEDULE:COMPACT") if o.name == "Sch_SomeOtherSetback"]
    assert len(other_setback) == 1
    assert other_setback[0].fields[1] == "Temperature"  # still the generic name
    # eppy's idfstr() round-trip doesn't force ".0" onto a bare-integer
    # literal, so compare numerically, not by exact string -- the point
    # under test is the VALUE is untouched (35), not its string spelling.
    assert float(other_setback[0].fields[-1]) == 35.0

    # 4. The merged product's check_mep-related gates are PASS.
    rep = check_mep(json.loads(result.model_dump_json()), zone_names=set(_ZONES))
    assert _status(rep, "mep.idf_parse") == CheckStatus.PASS
    assert _status(rep, "mep.schedule_type_refs") == CheckStatus.PASS
    assert _status(rep, "mep.schedule_completeness") == CheckStatus.PASS
    assert _status(rep, "mep.hvac_schedule_refs") == CheckStatus.PASS


# --------------------------------------------------------------------------- #
# REWORK (2026-08-14 terra verdict, pre-acceptance item #5): the zero-zone
# boundary was undefined -- _render_hvac_specs([]) used to unconditionally
# emit a Thermostat with zero IdealLoadsAirSystem objects attached (a
# meaningless, self-orphaning output). Now rejects explicitly.
# --------------------------------------------------------------------------- #
def test_render_hvac_specs_rejects_empty_zone_list():
    with pytest.raises(ValueError, match="zone_names is empty"):
        pipeline._render_hvac_specs([])


def test_run_mep_propagates_zero_zone_rejection(monkeypatch):
    """The real run_mep body, given an empty zone_names, must raise rather
    than silently produce a thermostat-with-nothing-attached output."""
    with pytest.raises(ValueError, match="zone_names is empty"):
        _run_mep_real(monkeypatch, zone_names=[])


# --------------------------------------------------------------------------- #
# A5 -- real historical artifacts: check_mep's 18 checks must show zero
# PASS->FAIL regressions when hvac_specs/schedule_specs are swapped for the
# deterministic render, and mep.hvac_schedule_refs must PASS. accept_C gets
# an extra assertion: its ORIGINAL hvac_schedule_refs is FAIL (this is the
# actual defect the dispatch is about) and the override fixes it.
# --------------------------------------------------------------------------- #
_HISTORICAL_RUNS = [
    "run_2026-08-13_accept_C",
    "run_2026-08-13_post_blocker1_e2e",
    "run_2026-08-13_batchI_accept_02",
    "run_2026-08-13_accept_B",
    "run_2026-08-09_f18_e2e_verify",
]


def _load_historical(run: str):
    run_dir = _SM21 / run
    mep = json.loads((run_dir / "4_mep" / "mep_output.json").read_text())
    bg = json.loads((run_dir / "2_modelling" / "building_geometry.json").read_text())
    zone_names = list(dict.fromkeys(bg["zones"]))
    used = parse_idf_text(mep["construction_specs"]).has_name("CONSTRUCTION")
    return mep, zone_names, used


@pytest.mark.parametrize("run", _HISTORICAL_RUNS)
def test_a5_no_check_regresses_from_pass_to_fail_on_real_artifacts(run):
    if not (_SM21 / run / "4_mep" / "mep_output.json").exists():
        pytest.skip(f"historical artifact not present in this checkout: {run}")
    mep, zone_names, used = _load_historical(run)

    baseline = check_mep(mep, used_constructions=used, zone_names=set(zone_names))
    baseline_status = {r.check_id: r.status for r in baseline.results}

    overridden = dict(mep)
    overridden["hvac_specs"] = pipeline._render_hvac_specs(zone_names)
    overridden["schedule_specs"] = pipeline._merge_hvac_det_schedules(mep["schedule_specs"])
    new = check_mep(overridden, used_constructions=used, zone_names=set(zone_names))
    new_status = {r.check_id: r.status for r in new.results}

    regressions = {
        check_id: (status, new_status.get(check_id))
        for check_id, status in baseline_status.items()
        if status == CheckStatus.PASS and new_status.get(check_id) != CheckStatus.PASS
    }
    assert not regressions, f"{run}: PASS->FAIL/other regression(s): {regressions}"
    assert new_status["mep.hvac_schedule_refs"] == CheckStatus.PASS


def test_a5_accept_c_hvac_schedule_refs_was_broken_and_is_now_fixed():
    """The concrete incident this dispatch is about: accept_C's ORIGINAL
    mep.hvac_schedule_refs is FAIL (the field-shift defect, reproduced from
    the actual archived artifact, not a synthetic fixture) and the
    deterministic override fixes it without touching anything else."""
    run = "run_2026-08-13_accept_C"
    if not (_SM21 / run / "4_mep" / "mep_output.json").exists():
        pytest.skip(f"historical artifact not present in this checkout: {run}")
    mep, zone_names, used = _load_historical(run)

    baseline = check_mep(mep, used_constructions=used, zone_names=set(zone_names))
    assert _status(baseline, "mep.hvac_schedule_refs") == CheckStatus.FAIL, (
        "expected accept_C's archived hvac_specs to reproduce the F-28 "
        "field-shift defect -- if this now passes, the fixture/archive "
        "changed and this test's premise needs re-checking, not deleting"
    )

    overridden = dict(mep)
    overridden["hvac_specs"] = pipeline._render_hvac_specs(zone_names)
    overridden["schedule_specs"] = pipeline._merge_hvac_det_schedules(mep["schedule_specs"])
    fixed = check_mep(overridden, used_constructions=used, zone_names=set(zone_names))
    assert _status(fixed, "mep.hvac_schedule_refs") == CheckStatus.PASS


# --------------------------------------------------------------------------- #
# misc small locks
# --------------------------------------------------------------------------- #
def test_render_hvac_specs_is_a_pure_function_of_zone_names():
    a = pipeline._render_hvac_specs(list(_ZONES))
    b = pipeline._render_hvac_specs(list(_ZONES))
    assert a == b
    reordered = pipeline._render_hvac_specs(list(reversed(_ZONES)))
    assert reordered != a  # order is actually threaded through, not ignored


def test_mep_output_hvac_specs_defaults_to_empty_string():
    """2026-08-14: hvac_specs is now optional on MepOutput so a model
    response that drops the key entirely still validates -- run_mep's
    override runs regardless, this only widens which malformed LLM JSON is
    tolerated before the override gets a chance to run."""
    from src.agent._share import ensure_schema_initialized
    from src.agent.intakeoutput import MepOutput

    ensure_schema_initialized()
    without_hvac = _mep_dict()
    del without_hvac["hvac_specs"]
    parsed = MepOutput.model_validate(without_hvac)
    assert parsed.hvac_specs == ""
