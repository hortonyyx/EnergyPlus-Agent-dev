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
def _mep_dict(hvac_specs: str = "", *, used_constructions: frozenset[str] = frozenset()) -> dict:
    """A minimal MepOutput-shaped dict -- modeled on the equivalent helper in
    tests/test_run_pipeline_self_checks.py (proven to pass BuildingSchema /
    SiteLocationSchema validation). ``used_constructions``, when given, is
    rendered as a one-material-per-construction block (same pattern as that
    helper) -- needed only by callers that drive the full
    run_pipeline_artifacts assembly step, which hard-raises (regardless of
    run_profile -- this is 5_intakeoutput's assembly.contract_backstop, not a
    self-check gate) if the geometry references a construction 4_mep didn't
    define."""
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
        "schedule_specs": "",
        "hvac_specs": hvac_specs,
        "people_specs": "",
        "lights_specs": "",
    }


def _fake_call_json_llm(hvac_specs_from_model: str, *, used_constructions: frozenset[str] = frozenset()):
    """Stub for pipeline._call_json_llm (the LLM network boundary), NOT for
    run_mep. Returns a MepOutput-shaped dict whose hvac_specs is whatever the
    caller wants "the model" to have written -- run_mep's real body must
    discard it regardless of content."""

    def _fake(_section, _system_prompt, _human, *, out_dir, prefix, **_kwargs):
        assert prefix == "mep", f"unexpected _call_json_llm prefix={prefix!r}"
        return _mep_dict(hvac_specs_from_model, used_constructions=used_constructions)

    return _fake


def _run_mep_real(
    monkeypatch,
    *,
    zone_names=_ZONES,
    hvac_specs_from_model: str = "GARBAGE_MODEL_HVAC_TEXT_MUST_NOT_SURVIVE",
    out_dir: Path | None = None,
):
    """Drive the REAL run_mep body end to end, stubbing only the LLM call."""
    monkeypatch.setattr(
        pipeline, "_call_json_llm", _fake_call_json_llm(hvac_specs_from_model)
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


def test_merge_hvac_det_schedules_does_not_duplicate_existing_type_limits():
    """The merge must fold in only the ScheduleTypeLimits the caller's
    schedule_specs doesn't already define -- otherwise concatenating this
    into a downstream bundle that already has e.g. Temperature would produce
    two ScheduleTypeLimits objects with the same name."""
    already = "ScheduleTypeLimits, Temperature, -50, 100, Continuous;\n"
    merged = pipeline._merge_hvac_det_schedules(already)
    idx = parse_idf_text(merged)
    assert idx.ok, idx.parse_error

    temperature_objs = [o for o in idx.of_type("SCHEDULETYPELIMITS") if o.name == "Temperature"]
    assert len(temperature_objs) == 1
    assert "OnOff" in idx.has_name("SCHEDULETYPELIMITS")  # was NOT predefined -> must be added


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
