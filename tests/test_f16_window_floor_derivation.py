"""F-16 (2026-08-08, orchestrator interface sweep §6 摊一 Step 2): a window's
"which floor am I on" fact used to have TWO independent declarations on a
v3 draw — `WindowV3.floor_id` (the authoritative reference, added when v3
introduced per-floor `id`s) and the inherited `Window.floor` (a name string,
v1/v2's ONLY floor reference, kept required on v3 "just in case" by
inheritance) — with a THIRD door (`CorrectedGeometryV3._v3_integrity`)
enforcing they agreed. A real run crashed exactly this way: the model wrote
`floors[0].id="F1"` / `name="Level 1"`, then wrote a window's `floor="F1"`
(the id) instead of `"Level 1"` (the name the old contract actually wanted)
— a plain, unguided `pydantic.ValidationError`, not a typed, retry-guided
rejection.

The fix (Step 2 of the §6 摊一 dispatch): `WindowV3.floor` becomes optional
and is DERIVED by the schema from `by_id[floor_id].name` the moment
validation succeeds — the model no longer supplies it at all, so the two-
declarations-of-one-fact shape is gone, not just re-validated more strictly.
Base `Window`/`CorrectedGeometry` (v1/v2) are UNTOUCHED: v1 has no
`floor_id` at all, so `floor` remains its one and only, required floor
reference (Groups B below lock that this override is scoped to `WindowV3`
only).

`floor` is marked ``schema.CORRECTION_DRAW_DERIVED`` — a NEW, DISTINCT
marker from F-15's ``CORRECTION_DRAW_FORBIDDEN`` (see that constant's
docstring in schema.py for why: `floor` is unconditionally repopulated by
the schema's own validator the instant construction succeeds, whereas a
CORRECTION_DRAW_FORBIDDEN field like `facade_segment_id` never gets a value
from anywhere until a LATER, separate stage runs. That difference matters
operationally: `_producer_preflight` (window_sources.py) receives an
ALREADY VALIDATED instance, where a CORRECTION_DRAW_DERIVED field is
ALWAYS populated regardless of what the model wrote — checking "is it
populated" there would misfire on every valid v3 draw with windows, not
just a model-authored one. Group G below is the regression lock for
exactly that near-miss (caught during construction of this fix, before it
ever reached a test failure).

Group layout:
  A — schema-level derivation semantics (direct `model_validate`)
  B — v1/v2 completely unaffected (scope lock)
  C — the CORRECTION_DRAW_DERIVED marker itself
  D — JSON-schema stripping (model-facing schema hides `floor`)
  E — the real `parse_correction_draw` door + retry guidance
  F — bidirectional property lock (mark/unmark at runtime, real gate reacts)
  G — `_producer_preflight` does NOT misfire on a legitimately derived floor
      (the near-miss this fix's design had to route around)
  H — `resolve_window_hosts`'s floor-mismatch branch is now unreachable
      through any real construction path (assertion, not a `ValueError`
      conflict) — only fires if something mutates a validated instance
      post-construction
  I — `window_host_claim_issues`'s `floor_identity` check is DELIBERATELY
      left unchanged (orchestrator boundary note #3): it audits
      `resolution.floor_id`, a value from an UNTRUSTED `claims` payload,
      not `window.floor_id` — genuinely not implied by the derivation
"""
from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.parse import correction_target, parse_correction_draw
from src.agent.correction.schema import (
    CORRECTION_DRAW_DERIVED,
    CORRECTION_DRAW_FORBIDDEN,
    CorrectedGeometry,
    CorrectedGeometryV3,
    Window,
    WindowV3,
    nested_draw_derived_fields,
    nested_draw_forbidden_fields,
)
from src.agent.correction.vocab import producer_facing_json_schema, retry_guidance_for_correction
from src.agent.correction.window_host import (
    WindowHostClaimsV1,
    WindowHostResolutionV1,
    resolve_window_hosts,
    window_host_claim_issues,
)
from src.agent.correction.window_sources import (
    WindowResolverInputError,
    build_verified_window_resolver_inputs,
    source_locator,
)

from tests.test_c2_b5_host_resolution import _context, _materialized, _resolve
from tests.test_c2_b5_source_routing import _base, _geom, _reading

V3 = correction_target("orthogonal_polygon")
V1 = correction_target("rectangular")


def _independent_sha256(value) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _valid_v3_payload_no_windows() -> dict:
    """Floor id/name deliberately mirror the ACTUAL F-16 crash shape
    (`id="F1"` / `name="Level 1"`) — a window writing `floor="F1"` (the id)
    instead of `"Level 1"` (the name) is exactly the historical mistake."""
    return {
        "schema_version": "3",
        "footprint_x": [0.0, 4.0],
        "footprint_y": [0.0, 3.0],
        "floors": [
            {
                "name": "Level 1",
                "id": "F1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "footprint": {"vertices": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]},
                "cells": [{"id": "A", "x": [0.0, 4.0], "y": [0.0, 3.0]}],
            }
        ],
        "windows": [],
    }


def _v3_payload_with_window(*, floor_value: str | None = None) -> dict:
    payload = _valid_v3_payload_no_windows()
    window = {
        "id": "W1",
        "floor_id": "F1",
        "facade": "South",
        "span": [1.0, 2.0],
        "z": [0.5, 2.5],
        "room": "A",
    }
    if floor_value is not None:
        window["floor"] = floor_value
    payload["windows"] = [window]
    return payload


# =========================================================================== #
# Group A — schema-level derivation semantics
# =========================================================================== #

def test_floor_derives_from_floor_id_when_omitted():
    geom = CorrectedGeometryV3.model_validate(_v3_payload_with_window())
    assert geom.windows[0].floor == "Level 1"
    assert geom.windows[0].floor != geom.windows[0].floor_id  # name, not id — the actual crash's confusion


def test_floor_accepted_as_is_when_it_already_matches_derived_value():
    """Not the primary door (that's parse_correction_draw's raw-dict gate,
    Group E) — this is the schema's OWN unconditional invariant, exercised
    directly via `model_validate` for a caller that constructs
    `CorrectedGeometryV3` without going through the draw gate at all."""
    geom = CorrectedGeometryV3.model_validate(_v3_payload_with_window(floor_value="Level 1"))
    assert geom.windows[0].floor == "Level 1"


def test_floor_mismatch_raises_plain_valueerror_as_defense_in_depth():
    """The EXACT F-16 crash payload, reproduced directly against
    `CorrectedGeometryV3.model_validate` (bypassing `parse_correction_draw`'s
    earlier, typed door on purpose) — proves the schema's own invariant
    still refuses a genuinely wrong value on its own, for callers that
    construct the model directly instead of going through the draw gate."""
    with pytest.raises(ValidationError, match="floor must match referenced floor name"):
        CorrectedGeometryV3.model_validate(_v3_payload_with_window(floor_value="F1"))


# =========================================================================== #
# Group B — v1/v2 (base `Window`/`CorrectedGeometry`) completely unaffected
# =========================================================================== #

def _v1_payload(*, include_floor: bool) -> dict:
    window = {"id": "w1", "facade": "South", "span": [1, 2], "z": [1, 2]}
    if include_floor:
        window["floor"] = "F1"
    return {
        "schema_version": "1",
        "footprint_x": [0, 4], "footprint_y": [0, 3],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3,
                    "cells": [{"id": "r1", "x": [0, 4], "y": [0, 3]}]}],
        "windows": [window],
    }


def test_v1_window_floor_stays_required():
    """v1 has no `floor_id` at all — `floor` remains its ONLY floor
    reference and must stay exactly as required as before this fix."""
    with pytest.raises(ValidationError):
        CorrectedGeometry.model_validate(_v1_payload(include_floor=False))


def test_v1_window_floor_supplied_is_unaffected():
    geom = CorrectedGeometry.model_validate(_v1_payload(include_floor=True))
    assert geom.windows[0].floor == "F1"


def test_v1_window_floor_field_carries_no_marker():
    """Pins the scope of the override: the base `Window.floor` field itself
    (which v1 uses unmodified) must carry neither F-15's nor F-16's
    marker — if someone moved the override onto the base class instead of
    `WindowV3` by mistake, v1 would silently gain the derived/optional
    behaviour and this test would catch it."""
    field = Window.model_fields["floor"]
    assert field.json_schema_extra is None


# =========================================================================== #
# Group C — the CORRECTION_DRAW_DERIVED marker itself
# =========================================================================== #

def test_floor_marked_correction_draw_derived_not_forbidden():
    field = WindowV3.model_fields["floor"]
    assert field.json_schema_extra == {CORRECTION_DRAW_DERIVED: True}
    assert nested_draw_derived_fields(CorrectedGeometryV3) == {"windows": ("floor",)}
    # not double-counted under the OTHER marker's accessor
    assert "floor" not in nested_draw_forbidden_fields(CorrectedGeometryV3).get("windows", ())


def test_facade_segment_id_still_marked_correction_draw_forbidden_not_derived():
    """Companion sanity: F-15's field keeps its ORIGINAL marker — this fix
    did not accidentally reclassify it."""
    field = WindowV3.model_fields["facade_segment_id"]
    assert field.json_schema_extra == {CORRECTION_DRAW_FORBIDDEN: True}
    assert "facade_segment_id" not in nested_draw_derived_fields(CorrectedGeometryV3).get("windows", ())


# =========================================================================== #
# Group D — JSON-schema stripping (model-facing schema hides `floor`)
# =========================================================================== #

def test_producer_schema_excludes_floor_from_windowv3():
    full = CorrectedGeometryV3.model_json_schema()
    window_def_name = next(k for k in full["$defs"] if k == "WindowV3")
    # sanity: the full schema DOES carry it (else this test is vacuous)
    assert "floor" in full["$defs"][window_def_name]["properties"]

    stripped = producer_facing_json_schema(CorrectedGeometryV3)
    assert "floor" not in stripped["$defs"][window_def_name]["properties"]
    assert "floor" not in stripped["$defs"][window_def_name].get("required", [])
    # sanity: didn't strip everything — facade_segment_id (F-15) still gone,
    # facade_id and other ordinary fields remain
    assert "facade_segment_id" not in stripped["$defs"][window_def_name]["properties"]
    assert "floor_id" in stripped["$defs"][window_def_name]["properties"]


def test_producer_schema_v1_is_still_byte_identical():
    """v1 has no CORRECTION_DRAW_DERIVED-marked field either — its stripped
    schema must remain the untouched, full dump (same claim F-15's own
    v1 test makes; repeated here scoped to this fix's marker so a future
    change to `_strip`'s DERIVED half specifically cannot silently widen
    the v1 path without this test naming it)."""
    full = CorrectedGeometry.model_json_schema()
    stripped = producer_facing_json_schema(CorrectedGeometry)
    assert json.dumps(stripped, sort_keys=True) == json.dumps(full, sort_keys=True)


# =========================================================================== #
# Group E — the real `parse_correction_draw` door + retry guidance
# =========================================================================== #

def test_parse_rejects_draw_that_supplies_floor_even_when_correct():
    """Strict, like facade_segment_id: ANY populated `floor` is rejected,
    even a value that happens to already equal the derived one — the model
    must never even attempt to fill it (schema hides the field; this is the
    door for a model that ignores that and writes it anyway)."""
    payload = _v3_payload_with_window(floor_value="Level 1")
    with pytest.raises(WindowResolverInputError) as exc_info:
        parse_correction_draw(payload, V3)
    assert exc_info.value.code == "producer_window_floor_populated"
    assert exc_info.value.category == "model_draw_error"


def test_parse_rejects_the_actual_historical_crash_value():
    payload = _v3_payload_with_window(floor_value="F1")  # the id, the real crash's mistake
    with pytest.raises(WindowResolverInputError) as exc_info:
        parse_correction_draw(payload, V3)
    assert exc_info.value.code == "producer_window_floor_populated"


def test_parse_accepts_draw_that_omits_floor_and_derives_it():
    payload = _v3_payload_with_window()
    assert "floor" not in payload["windows"][0]
    geom = parse_correction_draw(payload, V3)
    assert geom.windows[0].floor == "Level 1"


def test_retry_guidance_translates_producer_window_floor_populated():
    guide = retry_guidance_for_correction(V3)
    exc = WindowResolverInputError("producer_window_floor_populated", category="model_draw_error")
    msg = guide(exc)
    assert msg is not None
    assert "floor" in msg
    assert "floor_id" in msg
    # must NOT misname the field the way reusing an existing code would have
    assert "facade_segments" not in msg
    assert "facade_segment_id" not in msg


def test_e2e_real_floor_populated_draw_gets_guided_then_recovers(monkeypatch):
    """Mirrors test_f15_producer_schema_scope.py's Group D style: a draw
    that fills `floor` must be rejected via the real validator chain,
    receive corrective guidance naming `floor`/`floor_id`, and recover on
    the very next attempt instead of repeating the mistake blind."""
    from src.agent import pipeline

    outcomes_payloads = [_v3_payload_with_window(floor_value="F1"), _v3_payload_with_window()]

    class _Obj:
        pass

    def _resp(content: str):
        msg = _Obj(); msg.content = content; msg.reasoning_content = None
        choice = _Obj(); choice.message = msg; choice.finish_reason = "stop"
        usage = _Obj(); usage.prompt_tokens = 1; usage.completion_tokens = 1
        resp = _Obj(); resp.choices = [choice]; resp.usage = usage
        return resp

    class _RecordingClient:
        def __init__(self, outcomes):
            self._outcomes = list(outcomes)
            self.received_messages: list[list[dict]] = []
            self.chat = self
            self.completions = self

        def create(self, **kw):
            self.received_messages.append([dict(m) for m in kw.get("messages", [])])
            return self._outcomes.pop(0)

    fc = _RecordingClient([_resp(json.dumps(p)) for p in outcomes_payloads])
    monkeypatch.setattr(pipeline, "OpenAI", lambda **_kw: fc)

    validate = pipeline._make_correction_validator(0, V3)
    out = pipeline._call_json_llm(
        {"api_key": "x", "model_name": "m"}, "sys", "human", out_dir=None, prefix="t", attempts=3,
        validate=validate, retry_guidance=retry_guidance_for_correction(V3),
    )
    assert out["windows"][0].get("floor") is None or out["windows"][0]["floor"] == "Level 1"
    assert len(fc.received_messages) == 2, "must recover on attempt 2, not burn all 3 attempts"

    second = fc.received_messages[1]
    assert len(second) == 3, "a model_draw_error rejection must append corrective guidance"
    guidance = second[2]["content"]
    assert "floor" in guidance
    assert "floor_id" in guidance


# =========================================================================== #
# Group F — bidirectional property lock (real gate follows the marker, live)
#
# ⛔ Gap found by orchestrator's independent neuter (2026-08-08, post-hoc):
# every test below this point that existed in the FIRST version of this file
# exercised ONLY the CORRECTION_DRAW_DERIVED path (`floor`/marking `room`
# DERIVED) — none of them touched the SIBLING `nested_draw_forbidden_fields`
# path (`facade_segment_id`, Step 1's own fix). Reverting Step 1's parse.py
# loop back to a hardcoded `item.get("facade_segment_id") is not None` check
# (the exact drift Step 1 exists to close) left all 22 locks green — Step 1
# itself had ZERO regression protection. `test_unmarking_facade_segment_id_*`
# and `test_marking_an_ordinary_nested_field_forbidden_*` below close that
# gap; verified (in a /tmp copy, not this tree) that reverting the loop
# turns both red.
# =========================================================================== #

def test_unmarking_facade_segment_id_makes_the_forbidden_gate_stop_rejecting_it_live(monkeypatch):
    """FORBIDDEN-path counterpart to `test_unmarking_floor_makes_the_gate_
    stop_rejecting_it_live` below — that test only proves the DERIVED path
    (`nested_draw_derived_fields`) is marker-driven; this one proves the
    SIBLING `nested_draw_forbidden_fields` path (Step 1's own fix,
    `facade_segment_id`) is too, independently."""
    payload = _v3_payload_with_window()
    payload["windows"][0]["facade_segment_id"] = "fake"

    # control: BEFORE un-marking, this is the real, current production
    # behaviour (F-15's original fix, generalized to nested fields by Step 1).
    with pytest.raises(WindowResolverInputError) as exc_info:
        parse_correction_draw(payload, V3)
    assert exc_info.value.code == "producer_segment_ref_prefilled"

    field_info = WindowV3.model_fields["facade_segment_id"]
    monkeypatch.setattr(field_info, "json_schema_extra", None)
    assert "windows" not in nested_draw_forbidden_fields(CorrectedGeometryV3)

    # AFTER un-marking, this SPECIFIC typed door no longer fires. A non-None
    # `facade_segment_id` has no legal value during ANY draw regardless of
    # this marker (it must reference a real entry in `facade_segments`,
    # itself always empty pre-core — a separate, always-on invariant), so a
    # downstream, untyped schema check still rejects it — but via a
    # DIFFERENT exception, proving control has passed out of the gate this
    # test is about, not that the value became legal.
    with pytest.raises(ValidationError, match="unknown facade_segment_id"):
        parse_correction_draw(payload, V3)


def test_marking_an_ordinary_nested_field_forbidden_makes_the_gate_start_rejecting_it_live(monkeypatch):
    """Reverse direction, same FORBIDDEN path: mark an ordinary,
    currently-unmarked field (`room`) CORRECTION_DRAW_FORBIDDEN at runtime
    (zero change to parse.py) and the REAL `nested_draw_forbidden_fields`
    gate must start rejecting a draw that populates it, with the
    FORBIDDEN-path code (`producer_segment_ref_prefilled`) — not the
    DERIVED-path one (`producer_window_floor_populated`), proving the two
    marker kinds route through their own, independent loops in parse.py."""
    payload = _v3_payload_with_window()
    assert payload["windows"][0]["room"] == "A"

    geom = parse_correction_draw(payload, V3)
    assert geom.windows[0].room == "A"
    assert "room" not in nested_draw_forbidden_fields(CorrectedGeometryV3).get("windows", ())

    field_info = WindowV3.model_fields["room"]
    monkeypatch.setattr(field_info, "json_schema_extra", {CORRECTION_DRAW_FORBIDDEN: True})
    assert "room" in nested_draw_forbidden_fields(CorrectedGeometryV3)["windows"]

    with pytest.raises(WindowResolverInputError) as exc_info:
        parse_correction_draw(payload, V3)
    assert exc_info.value.code == "producer_segment_ref_prefilled"


def test_unmarking_floor_makes_the_gate_stop_rejecting_it_live(monkeypatch):
    payload = _v3_payload_with_window(floor_value="Level 1")

    # control: BEFORE un-marking, this IS the real, current production
    # behaviour this whole file is about.
    with pytest.raises(WindowResolverInputError):
        parse_correction_draw(payload, V3)

    field_info = WindowV3.model_fields["floor"]
    monkeypatch.setattr(field_info, "json_schema_extra", None)
    assert "windows" not in nested_draw_derived_fields(CorrectedGeometryV3)

    geom = parse_correction_draw(payload, V3)
    assert geom.windows[0].floor == "Level 1"


def test_marking_an_ordinary_nested_field_makes_the_gate_start_rejecting_it_live(monkeypatch):
    """`room` is an ordinary, currently-unmarked WindowV3 field — nothing
    hardcodes it as forbidden or derived anywhere. Mark it
    CORRECTION_DRAW_DERIVED on the REAL model at runtime (zero change to
    parse.py) and the REAL gate must start rejecting a draw that populates
    it — the 'future new derived field, mark it once, enforcement is
    automatic' half of the proof, inverse of the test above."""
    payload = _v3_payload_with_window()
    assert payload["windows"][0]["room"] == "A"

    # control: BEFORE marking, an ordinary populated `room` is unremarkable.
    geom = parse_correction_draw(payload, V3)
    assert geom.windows[0].room == "A"
    assert "room" not in nested_draw_derived_fields(CorrectedGeometryV3).get("windows", ())

    field_info = WindowV3.model_fields["room"]
    monkeypatch.setattr(field_info, "json_schema_extra", {CORRECTION_DRAW_DERIVED: True})
    assert "room" in nested_draw_derived_fields(CorrectedGeometryV3)["windows"]

    with pytest.raises(WindowResolverInputError) as exc_info:
        parse_correction_draw(payload, V3)
    assert exc_info.value.code == "producer_window_floor_populated"


def test_prompt_stripper_and_gate_agree_after_a_live_marker_change():
    """Cross-consumer proof (mirrors F-15's equivalent): mark `room`
    CORRECTION_DRAW_DERIVED at runtime and BOTH consumers — the prompt-schema
    stripper (JSON-schema-dict based) and the parse-time gate's field-name
    source (pydantic-model based) — must agree it is now excluded/forbidden,
    with no code change to either."""
    field_info = WindowV3.model_fields["room"]
    original = field_info.json_schema_extra
    field_info.json_schema_extra = {CORRECTION_DRAW_DERIVED: True}
    # Both classes need a forced rebuild: WindowV3's OWN cached schema (the
    # `$defs.WindowV3` entry CorrectedGeometryV3's schema references) is
    # keyed at the WindowV3 class level, not merely re-derived whenever the
    # container is rebuilt.
    WindowV3.model_rebuild(force=True)
    CorrectedGeometryV3.model_rebuild(force=True)
    try:
        stripped = producer_facing_json_schema(CorrectedGeometryV3)
        window_def_name = next(k for k in stripped["$defs"] if k == "WindowV3")
        assert "room" not in stripped["$defs"][window_def_name]["properties"]
        assert "room" in nested_draw_derived_fields(CorrectedGeometryV3)["windows"]
    finally:
        field_info.json_schema_extra = original
        WindowV3.model_rebuild(force=True)
        CorrectedGeometryV3.model_rebuild(force=True)
        assert "room" not in nested_draw_derived_fields(CorrectedGeometryV3).get("windows", ())
        full = producer_facing_json_schema(CorrectedGeometryV3)
        window_def_name = next(k for k in full["$defs"] if k == "WindowV3")
        assert "room" in full["$defs"][window_def_name]["properties"]


# =========================================================================== #
# Group G — `_producer_preflight` must NOT misfire on a legitimately
# schema-derived `floor` (the near-miss this fix's design had to route
# around — see this file's module docstring)
# =========================================================================== #

def test_producer_preflight_does_not_misfire_on_derived_floor():
    """Exercises the REAL production entry point
    (`build_verified_window_resolver_inputs`, which calls
    `_producer_preflight` internally on an ALREADY VALIDATED instance) end
    to end: a draw that omitted `floor` (derived by the schema) must pass
    preflight cleanly. If `_producer_preflight` were changed to also loop
    over `nested_draw_derived_fields` (the naive, WRONG generalization of
    Step 1's fix), this would misfire on every v3 draw with windows, not
    just a model-authored one — this test is the regression lock for that
    specific mistake."""
    manifest, raw_manifest, artifacts, fact = _base()
    payload = _geom().model_dump(mode="json")
    for window in payload["windows"]:
        window.pop("floor", None)  # simulate: the model never supplied it
    geom = parse_correction_draw(payload, V3)
    assert geom.windows[0].floor == "F1"  # schema-derived from floor_id

    marker = build_verified_window_resolver_inputs(
        producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,),
    )
    assert marker is not None
    assert marker.producer_draw_canonical_bytes


# =========================================================================== #
# Group H — `resolve_window_hosts`'s floor-mismatch branch: the
# `floor.name != window.floor` half is now provably unreachable through any
# real construction path (converted to an assertion, not a `ValueError`
# conflict) — it can only fire if something mutates an already-validated
# instance afterward, bypassing schema validation entirely
# =========================================================================== #

def test_resolve_window_hosts_never_hits_the_floor_desync_assertion_on_a_real_draw():
    geom, verified = _context(plan_geometry={"x_range_m": [1.0, 2.0], "y_range_m": [0.0, 0.1]})
    # must not raise (AssertionError or otherwise) on an ordinary, untouched draw.
    _resolve(geom, verified)


def test_resolve_window_hosts_floor_desync_assertion_fires_if_geom_mutated_post_construction():
    """Proves the assertion is LIVE code, not dead: bypassing schema
    validation via direct attribute mutation (the only way to desync
    `window.floor` from `by_id[window.floor_id].name` post-construction —
    pydantic does not re-validate on plain attribute assignment) still gets
    caught here, loudly."""
    geom, verified = _context(plan_geometry={"x_range_m": [1.0, 2.0], "y_range_m": [0.0, 0.1]})
    materialized = _materialized(geom)
    materialized.windows[0].floor = "not-the-real-floor-name"
    with pytest.raises(AssertionError, match="floor/floor_id desync"):
        resolve_window_hosts(
            materialized, verified_inputs=verified, tolerances=load_core_tolerances(), commit=False,
        )


# =========================================================================== #
# Group I — `window_host_claim_issues`'s `floor_identity` check: DELIBERATELY
# left unchanged (orchestrator boundary note #3, as-instructed self-audit).
# It audits `resolution.floor_id` — a value from an UNTRUSTED `claims`
# payload this function's own docstring says to audit "without trusting
# record vertices" — not `window.floor_id`, so it is NOT implied by the
# schema derivation and remains a genuine, live check.
# =========================================================================== #

def test_window_host_claim_issues_still_catches_a_forged_floor_id_in_claims():
    geom, verified = _context(plan_geometry={"x_range_m": [1.0, 2.0], "y_range_m": [0.0, 0.1]})
    materialized = _materialized(geom)
    claims = resolve_window_hosts(
        materialized, verified_inputs=verified, tolerances=load_core_tolerances(), commit=False,
    )

    # a second, real floor with a DIFFERENT name — appended by direct
    # mutation (bypasses schema re-validation, same technique
    # test_c2_b5_host_resolution.py's own tamper tests use) purely so the
    # claims-side floor_id lookup below resolves to a real object with a
    # name that provably disagrees with the window's real, derived floor.
    bogus_floor = materialized.floors[0].model_copy(update={"id": "bogus", "name": "Not The Real Floor"})
    materialized.floors = [*materialized.floors, bogus_floor]

    resolution = claims.resolutions[0]
    row_payload = resolution.model_dump(mode="json")
    row_payload["floor_id"] = "bogus"
    unhashed = dict(row_payload)
    unhashed.pop("resolution_sha256")
    row_payload["resolution_sha256"] = _independent_sha256(unhashed)
    tampered_resolution = WindowHostResolutionV1.model_validate_json(json.dumps(row_payload))
    claims_payload = claims.model_dump(mode="json")
    claims_payload["resolutions"] = [tampered_resolution.model_dump(mode="json")]
    claims_payload["aggregate_sha256"] = _independent_sha256([tampered_resolution.resolution_sha256])
    tampered_claims = WindowHostClaimsV1.model_validate_json(json.dumps(claims_payload))

    issues = window_host_claim_issues(materialized, claims=tampered_claims, tolerances=load_core_tolerances())
    reasons = {issue["reason"] for issue in issues}
    assert "floor_identity" in reasons
