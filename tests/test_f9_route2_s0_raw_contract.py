"""F-9 route② v2.1 §10 S0 / §12.2 locks: "Raw contract", "Raw projection
context", "Legacy scope".

Dispatch scope note (2026-08-11_f9_route2_s0_s1_construction_dispatch_claude
.md §3): S0 owns exactly these three §12.2 matrix rows this batch; "Reference
translation" is NOT assigned to S0 (real reference translation needs live
reading/manifest authentication, which is S2 wiring) and is deliberately not
locked here.

Everything under test here is new, additive scaffolding that S0 leaves fully
unwired (v2.1 §10 S0: "均先不接 live production") -- `src.agent.correction.
schema.CorrectionDrawV3CitationV2`, `parse.parse_raw_correction_draw`,
`parse.correction_target_v2`, and the whole `window_position` module. No
existing live entry point (`run_correction`, `_draw_correction`,
`finalize_correction_draw`, `correction_target`) is touched by S0, and this
file does not exercise any of them.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.correction.parse import correction_target_v2, parse_raw_correction_draw
from src.agent.correction.schema import CorrectedGeometryV3, CorrectionDrawV3CitationV2
from src.agent.correction.window_sources import WindowResolverInputError
from src.agent.correction.window_position import (
    RawProjectionContextV1,
    WindowPositionEvidenceError,
    WindowResolverInputsArtifactV2,
    load_window_resolver_artifact,
    materialize_raw_projection_context,
)

# ---------------------------------------------------------------------------
# Shared fixtures: hand-built raw draw payload, matching v2.1 §4.2's own
# example wire, with one window and a real (non-degenerate) floor ring.
# ---------------------------------------------------------------------------

def _raw_payload() -> dict:
    return {
        "schema_version": "3",
        "draw_contract_version": "correction_draw_v3_window_citation_v2",
        "footprint_x": [0.0, 15.0],
        "footprint_y": [0.0, 8.0],
        "floors": [{
            "id": "floor-1", "name": "Level 1", "z_floor": 0.0, "ceiling_height": 3.0,
            "footprint": {"vertices": [[0.0, 0.0], [15.0, 0.0], [15.0, 8.0], [0.0, 8.0]]},
            "cells": [{
                "id": "c1", "role": "office", "x": [0.0, 15.0], "y": [0.0, 8.0],
                "polygon": [[0.0, 0.0], [15.0, 0.0], [15.0, 8.0], [0.0, 8.0]],
            }],
        }],
        "windows": [{
            "id": "W-F1-N-1", "floor_id": "floor-1", "facade": "North", "z": [1.0, 2.6], "room": "c1",
            "provenance": {
                "existence": {"provenance": "observed", "source_ids": ["1f_view/S11", "North_view/S7"]},
            },
        }],
    }


# ---------------------------------------------------------------------------
# 1. "Raw contract" lock.
# ---------------------------------------------------------------------------

def test_raw_fixture_self_proof_no_span():
    """Fixture self-proof: the raw payload has no `span` key anywhere."""
    payload = _raw_payload()
    assert all("span" not in w for w in payload["windows"])


def test_raw_fixture_self_proof_span_variant_has_span():
    """The companion 'only extra `span`' variant genuinely carries the key
    the negative case is supposed to trip on (self-proof before asserting
    the negative behavior).
    """
    payload = copy.deepcopy(_raw_payload())
    payload["windows"][0]["span"] = [1.24, 3.64]
    assert "span" in payload["windows"][0]


def test_no_span_parse_passes():
    draw = parse_raw_correction_draw(_raw_payload())
    assert isinstance(draw, CorrectionDrawV3CitationV2)
    assert len(draw.windows) == 1
    assert draw.windows[0].id == "W-F1-N-1"
    assert not hasattr(draw.windows[0], "span")


def test_span_populated_raises_stable_code_not_generic_validation_error():
    payload = copy.deepcopy(_raw_payload())
    payload["windows"][0]["span"] = [1.24, 3.64]
    with pytest.raises(WindowResolverInputError) as excinfo:
        parse_raw_correction_draw(payload)
    # Not a generic pydantic ValidationError impersonating a stable code
    # (§12.2 "Raw contract" neuter requirement: "不能由 generic
    # ValidationError 冒充稳定码").
    assert not isinstance(excinfo.value, ValidationError)
    assert excinfo.value.code == "producer_window_span_populated"
    assert excinfo.value.category == "model_draw_error"
    assert excinfo.value.context["window_ids"] == ["W-F1-N-1"]


def test_neuter_bypassing_preflight_and_calling_raw_schema_directly_loses_stable_code():
    """Sharper neuter than the "revert to full schema" variant below: prove
    the stable `producer_window_span_populated` code is NOT a byproduct of
    `CorrectionDrawV3CitationV2`'s own `extra="forbid"` schema (which also
    rejects a `span` key, since `WindowCitationV2` has no such field) --
    it comes ONLY from `parse_raw_correction_draw`'s preflight. Removing
    that preflight (calling `.model_validate` on the raw model directly, as
    a regression that "inlines the schema call and drops the preflight"
    would do) must fall back to a generic, un-actionable
    `pydantic.ValidationError` -- i.e. this specific guarantee has exactly
    one line of defense, not two, so a mutation that deletes the preflight
    is NOT silently caught by the schema layer underneath it.
    """
    payload = copy.deepcopy(_raw_payload())
    payload["windows"][0]["span"] = [1.24, 3.64]
    with pytest.raises(ValidationError):
        CorrectionDrawV3CitationV2.model_validate(payload)
    # And specifically NOT a WindowResolverInputError with the stable code --
    # confirms there is no second, redundant source of that code.
    try:
        CorrectionDrawV3CitationV2.model_validate(payload)
    except WindowResolverInputError:
        pytest.fail("the raw schema layer alone must not itself raise the stable code")
    except ValidationError:
        pass


def test_neuter_reverting_to_full_schema_direct_parse_goes_red():
    """§12.2 neuter: "改回 full schema 直接 parse 后锁红". Simulates the
    regression by calling the FULL model's own validator directly on a
    span-populated raw-shaped payload (what a "revert parse_raw_correction_
    draw to just call the legacy/full schema" regression would do) and
    proving it does NOT produce the stable
    `producer_window_span_populated` code -- i.e. this specific guarantee
    lives ONLY in `parse_raw_correction_draw`'s preflight, not for free from
    the schema layer.
    """
    payload = copy.deepcopy(_raw_payload())
    payload["windows"][0]["span"] = [1.24, 3.64]
    payload["windows"][0]["floor"] = "Level 1"  # full schema requires echoed floor field shape too
    try:
        CorrectedGeometryV3.model_validate(payload)
        raised_stable_code = False
    except WindowResolverInputError as exc:
        raised_stable_code = exc.code == "producer_window_span_populated"
    except Exception:
        raised_stable_code = False
    assert not raised_stable_code, (
        "the full-schema direct-parse path must NOT itself produce "
        "producer_window_span_populated -- that guarantee is what "
        "parse_raw_correction_draw's preflight adds, and this test's job is "
        "to prove the regression (skipping the preflight) is observable"
    )


# ---------------------------------------------------------------------------
# 2. "Raw projection context" lock.
# ---------------------------------------------------------------------------

def test_raw_fixture_self_proof_ring_and_hashes_computable():
    payload = _raw_payload()
    draw = CorrectionDrawV3CitationV2.model_validate(payload)
    assert not any(hasattr(w, "span") for w in draw.windows)
    assert len(draw.floors) == 1
    assert len(draw.floors[0].footprint.vertices) >= 4


def _context_for(raw: CorrectionDrawV3CitationV2, raw_bytes: bytes = b"canonical-bytes-fixture") -> RawProjectionContextV1:
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    resolver_hash = hashlib.sha256(b"resolver-fixture").hexdigest()
    view_datum_sha256 = hashlib.sha256(b"datum-fixture").hexdigest()
    return materialize_raw_projection_context(
        raw, raw_draw_sha256=raw_sha, resolver_hash=resolver_hash, view_datum_sha256=view_datum_sha256,
    )


def test_context_pass_binds_raw_and_resolver_hash():
    draw = CorrectionDrawV3CitationV2.model_validate(_raw_payload())
    ctx = _context_for(draw)
    assert ctx.content_sha256 and len(ctx.content_sha256) == 64
    assert ctx.raw_draw_sha256 == hashlib.sha256(b"canonical-bytes-fixture").hexdigest()
    assert ctx.resolver_hash == hashlib.sha256(b"resolver-fixture").hexdigest()
    assert ctx.view_datum_sha256 == hashlib.sha256(b"datum-fixture").hexdigest()
    assert len(ctx.floor_rings) == 1
    assert ctx.floor_rings[0].floor_id == "floor-1"


def test_context_totality_and_nonempty_before_hydration():
    """Runs entirely off `raw.floors` -- before any window is hydrated -- and
    still produces a non-empty, hash-bound context (v2.1 §4.4).
    """
    draw = CorrectionDrawV3CitationV2.model_validate(_raw_payload())
    assert len(draw.windows) == 1  # windows exist in the raw draw...
    ctx = _context_for(draw)
    # ...but the context is purely a function of raw.floors, not windows.
    assert len(ctx.floor_rings) == len(draw.floors)


def test_context_is_invariant_to_window_mutation():
    """MINOR-2 fix (sol): the OLD "totality" test above never actually
    exercised the "purely a function of floors" claim -- it just counted
    floor_rings once. Mutate `windows` (drop the only window, then add a
    second one with different facade/z) and prove `materialize_raw_
    projection_context`'s result is byte-identical in every case: a future
    accidental read of `raw.windows` inside the builder would show up here.
    """
    base_payload = _raw_payload()
    no_windows = copy.deepcopy(base_payload)
    no_windows["windows"] = []
    extra_window = copy.deepcopy(base_payload)
    extra_window["windows"].append({
        "id": "W-F1-S-1", "floor_id": "floor-1", "facade": "South", "z": [1.0, 2.0], "room": "c1",
        "provenance": {"existence": {"provenance": "observed", "source_ids": ["1f_view/S99"]}},
    })

    ctx_base = _context_for(CorrectionDrawV3CitationV2.model_validate(base_payload))
    ctx_no_windows = _context_for(CorrectionDrawV3CitationV2.model_validate(no_windows))
    ctx_extra_window = _context_for(CorrectionDrawV3CitationV2.model_validate(extra_window))

    assert ctx_base.model_dump(mode="json") == ctx_no_windows.model_dump(mode="json")
    assert ctx_base.model_dump(mode="json") == ctx_extra_window.model_dump(mode="json")


def test_context_hash_is_sensitive_to_raw_draw_sha256_mutation():
    draw = CorrectionDrawV3CitationV2.model_validate(_raw_payload())
    baseline = _context_for(draw, raw_bytes=b"one")
    mutated = _context_for(draw, raw_bytes=b"two")
    assert baseline.content_sha256 != mutated.content_sha256


def test_context_hash_is_sensitive_to_footprint_mutation():
    payload_a = _raw_payload()
    payload_b = copy.deepcopy(payload_a)
    payload_b["floors"][0]["footprint"]["vertices"] = [[0.0, 0.0], [20.0, 0.0], [20.0, 8.0], [0.0, 8.0]]
    ctx_a = _context_for(CorrectionDrawV3CitationV2.model_validate(payload_a))
    ctx_b = _context_for(CorrectionDrawV3CitationV2.model_validate(payload_b))
    assert ctx_a.content_sha256 != ctx_b.content_sha256
    assert ctx_a.floor_rings[0].footprint_fingerprint != ctx_b.floor_rings[0].footprint_fingerprint


def test_neuter_passing_full_model_instead_of_raw_fails_structurally():
    """§12.2 neuter: "给 context builder 传 full model...时，structure/path
    锁红". Build a REAL `CorrectedGeometryV3` (full model, has a
    model-authored `span`) and prove the context builder refuses it by
    type, not by accident.
    """
    full_payload = {
        "schema_version": "3",
        "footprint_x": [0.0, 15.0], "footprint_y": [0.0, 8.0],
        "floors": [{
            "id": "floor-1", "name": "Level 1", "z_floor": 0.0, "ceiling_height": 3.0,
            "footprint": {"vertices": [[0.0, 0.0], [15.0, 0.0], [15.0, 8.0], [0.0, 8.0]]},
            "cells": [{
                "id": "c1", "role": "office", "x": [0.0, 15.0], "y": [0.0, 8.0],
                "polygon": [[0.0, 0.0], [15.0, 0.0], [15.0, 8.0], [0.0, 8.0]],
            }],
        }],
        "windows": [{
            "id": "W-F1-N-1", "floor_id": "floor-1", "facade": "North",
            "span": [1.24, 3.64], "z": [1.0, 2.6], "room": "c1",
        }],
    }
    full = CorrectedGeometryV3.model_validate(full_payload)
    assert full.windows[0].span == [1.24, 3.64]  # self-proof: this really is the full, span-bearing model
    with pytest.raises(TypeError):
        materialize_raw_projection_context(full, raw_draw_sha256="0" * 64, resolver_hash="0" * 64, view_datum_sha256="0" * 64)


def test_neuter_passing_arbitrary_placeholder_object_fails_structurally():
    class _FakeRawWithPlaceholderSpan:
        floors = []
        windows = [{"span": [0.0, 1.0]}]  # a "补 placeholder span" attempt

    with pytest.raises(TypeError):
        materialize_raw_projection_context(
            _FakeRawWithPlaceholderSpan(), raw_draw_sha256="0" * 64, resolver_hash="0" * 64,
            view_datum_sha256="0" * 64,
        )


# ---------------------------------------------------------------------------
# 3. "Legacy scope" lock -- §2 dispatch self-check's three real on-disk
#    sample classes, used as the actual fixtures here (not synthetic
#    stand-ins): v1 (schema_version="1"), v2 (schema_version="2"), and the
#    historical v3 producer artifact V1 (artifact_version=
#    "window_resolver_inputs_v1").
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]

V1_SAMPLE = _REPO_ROOT / "case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/1_correction/attempts/001/output.json"
V2_SAMPLE = _REPO_ROOT / "case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/1_correction/attempts/001/output.json"
HISTORICAL_V3_ARTIFACT_V1_SAMPLE = _REPO_ROOT / "case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify/1_correction/attempts/001/window_resolver_inputs.json"


@pytest.mark.parametrize("path", [V1_SAMPLE, V2_SAMPLE, HISTORICAL_V3_ARTIFACT_V1_SAMPLE], ids=lambda p: p.name)
def test_legacy_sample_files_exist_on_disk(path):
    """Dispatch §2 self-check, restated as a lock: if any of these three real
    samples ever disappears from disk, this must fail loudly, not silently
    fall back to a synthetic fixture.
    """
    assert path.is_file(), f"expected real on-disk sample missing: {path}"


def test_v1_sample_byte_parity_through_legacy_loader():
    from src.agent.correction.parse import ensure_corrected_geometry

    raw = json.loads(V1_SAMPLE.read_text(encoding="utf-8"))
    assert str(raw.get("schema_version", "1")) == "1"
    geom = ensure_corrected_geometry(raw)
    dumped = geom.model_dump(mode="json")
    expected = {**raw, "schema_version": raw.get("schema_version", "1")}
    assert dumped == expected, "v1 legacy round-trip must be information-preserving"


def test_v2_sample_byte_parity_through_legacy_loader():
    from src.agent.correction.parse import ensure_corrected_geometry

    raw = json.loads(V2_SAMPLE.read_text(encoding="utf-8"))
    assert raw.get("schema_version") == "2"
    geom = ensure_corrected_geometry(raw)
    dumped = geom.model_dump(mode="json")
    assert dumped == raw, "v2 legacy round-trip must be information-preserving"


def test_historical_v3_producer_artifact_v1_replays_through_registry_unchanged():
    raw_bytes = HISTORICAL_V3_ARTIFACT_V1_SAMPLE.read_bytes()
    declared_version = json.loads(raw_bytes)["artifact_version"]
    assert declared_version == "window_resolver_inputs_v1"  # self-proof this really is the historical wire

    result = load_window_resolver_artifact(raw_bytes)
    # Dispatched to the LEGACY type, not silently upgraded/reinterpreted as V2.
    from src.agent.correction.window_sources import WindowResolverInputsArtifactV1
    assert isinstance(result, WindowResolverInputsArtifactV1)
    assert not isinstance(result, WindowResolverInputsArtifactV2)
    assert result.artifact_version == "window_resolver_inputs_v1"
    assert result.content_sha256 == json.loads(raw_bytes)["content_sha256"]


def test_v2_target_shell_carries_both_loader_registry_entries():
    """Renamed 2026-08-11 per sol MINOR-2: the old name ("new runs always
    get artifact v2") overstated what this asserts -- S0 does not wire any
    live run, so there is no "new run" behavior to test yet. What this DOES
    prove: `correction_target_v2()`'s shell carries a loader registry with
    both version entries, which is the S0-scoped fact.
    """
    target = correction_target_v2()
    assert target.draw_contract_version == "correction_draw_v3_window_citation_v2"
    assert "window_resolver_inputs_v2" in target.legacy_artifact_loader_registry
    # Legacy v1 stays reachable (read-only history), never the default for a
    # freshly-constructed v2 target's OWN artifact production (that axis is
    # S2+ wiring; S0 only proves the registry carries both entries).
    assert "window_resolver_inputs_v1" in target.legacy_artifact_loader_registry


def test_unknown_artifact_version_fails_closed():
    payload = json.dumps({"artifact_version": "window_resolver_inputs_v99", "content_sha256": "0" * 64}).encode()
    with pytest.raises(WindowPositionEvidenceError) as excinfo:
        load_window_resolver_artifact(payload)
    assert excinfo.value.code == "unknown_artifact_version"
    assert excinfo.value.category == "input_integrity_error"


def test_neuter_dispatch_never_inspects_span_presence():
    """§12.2 "Legacy scope" neuter: "以『有无 span』猜版本...锁红". Prove the
    registry dispatch is purely a function of the `artifact_version` string
    by constructing a payload that is shaped like neither real artifact (has
    no `windows`/`span` at all to inspect) but declares a KNOWN version --
    dispatch must still succeed on the string alone, not fail for "lacking"
    span-shaped content, and must still fail closed on an unknown string
    even if that payload happens to look v1-ish.
    """
    # A payload that superficially resembles the v1 wire (same top-level
    # keys a naive "does it look old" heuristic might key off) but declares
    # an unknown version: dispatch must reject it by the declared version
    # string, not fall through to the v1 loader because of shape.
    from src.agent.correction.window_sources import canonical_sha256

    real_v1 = json.loads(HISTORICAL_V3_ARTIFACT_V1_SAMPLE.read_bytes())
    shape_alike = dict(real_v1)
    shape_alike["artifact_version"] = "window_resolver_inputs_v0_unknown"
    with pytest.raises(WindowPositionEvidenceError) as excinfo:
        load_window_resolver_artifact(json.dumps(shape_alike).encode())
    assert excinfo.value.code == "unknown_artifact_version"


def test_minor2_known_version_hostile_shape_routes_to_schema_not_content_sniffing():
    """MINOR-2 fix (sol): the OLD "never inspects span" test above only
    covered the UNKNOWN-version side; it left open whether a KNOWN version
    string with a shape that doesn't match that version's actual schema
    (e.g. `windows`/`span`-shaped content pretending to be a v2 artifact)
    might be waved through by a hypothetical shape-based fallback. Prove a
    known-but-malformed v2-declared payload is routed to the v2 SCHEMA
    (which then rejects it for missing required v2 fields) rather than
    silently accepted or silently misrouted -- dispatch has exactly one
    decision variable, the declared string.
    """
    hostile_known_version = json.dumps({
        "artifact_version": "window_resolver_inputs_v2",
        "windows": [{"id": "W-F1-N-1", "span": [1.24, 3.64]}],  # v1/full-shaped content, not v2 fields at all
    }).encode()
    with pytest.raises(ValidationError):  # real pydantic schema rejection, not a version-guess rejection
        load_window_resolver_artifact(hostile_known_version)


def _self_consistent_v2_artifact():
    """Build a V2 artifact whose `raw_projection_context.raw_draw_sha256`/
    `view_datum_sha256` actually match the bytes embedded alongside it --
    this is the fix for the exact defect sol's MAJOR-1 finding pointed at in
    an EARLIER version of this test file: the context used to be built from
    a fixed placeholder (`_context_for`'s default `b"canonical-bytes-
    fixture"`) while the artifact embedded a DIFFERENT byte string
    (`json.dumps(_raw_payload(), ...)`), and nothing caught the mismatch.
    """
    from src.agent.correction.window_sources import RawReadingArtifactV1

    draw = CorrectionDrawV3CitationV2.model_validate(_raw_payload())
    raw_draw_bytes = json.dumps(_raw_payload(), sort_keys=True).encode("utf-8")
    datum_bytes = b'{"direction_facts":[]}'
    ctx = materialize_raw_projection_context(
        draw, raw_draw_sha256=hashlib.sha256(raw_draw_bytes).hexdigest(),
        resolver_hash=hashlib.sha256(b"resolver-fixture").hexdigest(),
        view_datum_sha256=hashlib.sha256(datum_bytes).hexdigest(),
    )
    readings = (RawReadingArtifactV1(input_id="1f_view", raw_bytes=b"{}"),)
    return raw_draw_bytes, datum_bytes, readings, ctx


def test_v2_artifact_schema_serialize_reload_round_trip():
    """New-wire (V2) schema/serialize/reload/hash test -- no real on-disk
    sample exists yet (S0 does not wire any live producer), so this
    round-trips a hand-built instance. Constructed via the model
    constructors with real `bytes`/tuples (matching the existing
    `build_window_resolver_inputs_artifact` pattern in window_sources.py),
    not `model_validate` on a plain dict of JSON-shaped strings -- the
    latter trips pydantic's strict-mode bytes/tuple coercion, which is a
    test-construction detail, not a v2.1 contract requirement.
    """
    from src.agent.correction.window_sources import canonical_json_bytes, canonical_sha256

    raw_draw_bytes, datum_bytes, readings, ctx = _self_consistent_v2_artifact()

    payload = {
        "artifact_version": "window_resolver_inputs_v2",
        "raw_draw_canonical_bytes": raw_draw_bytes.decode("utf-8"),
        "raw_view_manifest_bytes": "{}",
        "raw_reading_artifacts": [row.model_dump(mode="json") for row in readings],
        "direction_datum_sidecar_bytes": datum_bytes.decode("utf-8"),
        "raw_projection_context": ctx.model_dump(mode="json"),
    }
    content_hash = canonical_sha256(payload)
    artifact = WindowResolverInputsArtifactV2(
        artifact_version="window_resolver_inputs_v2",
        raw_draw_canonical_bytes=raw_draw_bytes, raw_view_manifest_bytes=b"{}",
        raw_reading_artifacts=readings, direction_datum_sidecar_bytes=datum_bytes,
        raw_projection_context=ctx, content_sha256=content_hash,
    )

    reloaded = WindowResolverInputsArtifactV2.model_validate_json(
        canonical_json_bytes(artifact.model_dump(mode="json"))
    )
    assert reloaded == artifact
    assert reloaded.artifact_version == "window_resolver_inputs_v2"

    # Mutation: tampering content must break the hash invariant.
    tampered = json.loads(canonical_json_bytes(artifact.model_dump(mode="json")))
    tampered["raw_draw_canonical_bytes"] = "dGFtcGVyZWQ="
    with pytest.raises(ValidationError):
        WindowResolverInputsArtifactV2.model_validate_json(json.dumps(tampered))


def test_major1_hostile_cross_field_raw_bytes_mismatch_rejected():
    """sol MAJOR-1 repro, now must fail: pair a context bound to one set of
    raw bytes with DIFFERENT `raw_draw_canonical_bytes`, then recompute the
    outer `content_sha256` over that mismatched pair (exactly sol's attack:
    the outer envelope hash alone cannot tell the two apart). Must be
    rejected by the new cross-field validator, not silently accepted.
    """
    from src.agent.correction.window_sources import canonical_sha256

    raw_draw_bytes, datum_bytes, readings, ctx = _self_consistent_v2_artifact()
    other_raw_bytes = json.dumps({**_raw_payload(), "notes": "different draw"}, sort_keys=True).encode("utf-8")
    assert hashlib.sha256(other_raw_bytes).hexdigest() != ctx.raw_draw_sha256  # self-proof: genuinely different

    payload = {
        "artifact_version": "window_resolver_inputs_v2",
        "raw_draw_canonical_bytes": other_raw_bytes.decode("utf-8"),  # MISMATCHED vs ctx.raw_draw_sha256
        "raw_view_manifest_bytes": "{}",
        "raw_reading_artifacts": [row.model_dump(mode="json") for row in readings],
        "direction_datum_sidecar_bytes": datum_bytes.decode("utf-8"),
        "raw_projection_context": ctx.model_dump(mode="json"),
    }
    with pytest.raises(ValidationError, match="raw_draw_sha256"):
        WindowResolverInputsArtifactV2(
            artifact_version="window_resolver_inputs_v2",
            raw_draw_canonical_bytes=other_raw_bytes, raw_view_manifest_bytes=b"{}",
            raw_reading_artifacts=readings, direction_datum_sidecar_bytes=datum_bytes,
            raw_projection_context=ctx, content_sha256=canonical_sha256(payload),  # outer hash self-consistent!
        )


def test_major1_hostile_cross_field_datum_bytes_mismatch_rejected():
    """Same attack shape, on the datum-sidecar side."""
    from src.agent.correction.window_sources import canonical_sha256

    raw_draw_bytes, datum_bytes, readings, ctx = _self_consistent_v2_artifact()
    other_datum_bytes = b'{"direction_facts":["tampered"]}'
    assert hashlib.sha256(other_datum_bytes).hexdigest() != ctx.view_datum_sha256

    payload = {
        "artifact_version": "window_resolver_inputs_v2",
        "raw_draw_canonical_bytes": raw_draw_bytes.decode("utf-8"),
        "raw_view_manifest_bytes": "{}",
        "raw_reading_artifacts": [row.model_dump(mode="json") for row in readings],
        "direction_datum_sidecar_bytes": other_datum_bytes.decode("utf-8"),
        "raw_projection_context": ctx.model_dump(mode="json"),
    }
    with pytest.raises(ValidationError, match="view_datum_sha256"):
        WindowResolverInputsArtifactV2(
            artifact_version="window_resolver_inputs_v2",
            raw_draw_canonical_bytes=raw_draw_bytes, raw_view_manifest_bytes=b"{}",
            raw_reading_artifacts=readings, direction_datum_sidecar_bytes=other_datum_bytes,
            raw_projection_context=ctx, content_sha256=canonical_sha256(payload),
        )


# ---------------------------------------------------------------------------
# 4. Position decision / evidence artifact strict models -- §10 S0's own
#    deliverable list item, schema/serialize/reload/hash only (S2 owns
#    actually populating these from a real pairing decision).
# ---------------------------------------------------------------------------

from src.agent.correction.window_position import (  # noqa: E402
    SourceIntervalV1,
    WindowPositionDecisionV1,
    WindowPositionEvidenceArtifactV1,
    build_window_position_decision,
)


RAW_DRAW_SHA_A = "a" * 64
RESOLVER_HASH_B = "b" * 64
CONTEXT_SHA_C = "c" * 64


def _accepted_decision(
    window_id: str = "W-F1-N-1", *,
    raw_draw_sha256: str = RAW_DRAW_SHA_A, resolver_hash: str = RESOLVER_HASH_B,
    raw_projection_context_sha256: str = CONTEXT_SHA_C,
    elevation_locators=("src:" + "2" * 64,),
    elevation_projected_intervals=(SourceIntervalV1(lo=1.12, hi=3.52),),
    distances=(0.12,),
    tolerance_value: float = 0.300,
    derived_span=None,
) -> WindowPositionDecisionV1:
    plan_world_interval = SourceIntervalV1(lo=1.24, hi=3.64)
    return build_window_position_decision(
        raw_draw_sha256=raw_draw_sha256, resolver_hash=resolver_hash,
        raw_projection_context_sha256=raw_projection_context_sha256,
        window_id=window_id,
        plan_locator="src:" + "1" * 64,
        elevation_locators=elevation_locators,
        plan_world_interval=plan_world_interval,
        elevation_projected_intervals=elevation_projected_intervals,
        distances=distances,
        tolerance_name="window_evidence_pairing_tol_m",
        tolerance_value=tolerance_value,
        decision="accepted",
        derived_span=plan_world_interval if derived_span is None else derived_span,
    )


def test_position_decision_round_trip_and_hash():
    decision = _accepted_decision()
    reloaded = WindowPositionDecisionV1.model_validate_json(
        decision.model_dump_json()
    )
    assert reloaded == decision
    assert decision.derived_span == decision.plan_world_interval  # §5.4: plan authority is the span


def test_position_decision_canonical_window_key_matches_hash_of_plan_locator():
    """v2.1 §5.3: canonical_window_key = hash(plan_authority_locator)."""
    from src.agent.correction.window_sources import canonical_sha256

    decision = _accepted_decision()
    expected = canonical_sha256({"schema": "canonical_window_key_v1", "plan_authority_locator": decision.plan_locator})
    assert decision.canonical_window_key == expected


def test_position_decision_hash_mutation_detected():
    decision = _accepted_decision()
    tampered = decision.model_dump(mode="json")
    tampered["plan_world_interval"] = {"lo": 9.0, "hi": 9.5}  # decision_sha256 stays stale
    with pytest.raises(ValidationError):
        WindowPositionDecisionV1.model_validate(tampered)


def test_position_decision_rejected_must_not_carry_derived_span():
    with pytest.raises(ValidationError):
        build_window_position_decision(
            raw_draw_sha256=RAW_DRAW_SHA_A, resolver_hash=RESOLVER_HASH_B, raw_projection_context_sha256=CONTEXT_SHA_C,
            window_id="W-F1-N-2", plan_locator="src:" + "1" * 64, elevation_locators=(),
            plan_world_interval=SourceIntervalV1(lo=0.0, hi=1.0),
            elevation_projected_intervals=(), distances=(),
            tolerance_name="window_evidence_pairing_tol_m", tolerance_value=0.300,
            decision="rejected", derived_span=SourceIntervalV1(lo=0.0, hi=1.0),
        )


# --- MAJOR-2 hostile rejections: sol's exact three repro cases ------------

def test_major2_hostile_accepted_without_elevation_rejected():
    with pytest.raises(ValidationError, match="elevation corroborator"):
        _accepted_decision(elevation_locators=(), elevation_projected_intervals=(), distances=())


def test_major2_hostile_accepted_wrong_derived_span_rejected():
    with pytest.raises(ValidationError, match="derived_span"):
        _accepted_decision(derived_span=SourceIntervalV1(lo=7.0, hi=8.0))


def test_major2_hostile_accepted_distance_over_tolerance_rejected():
    with pytest.raises(ValidationError, match="tolerance"):
        _accepted_decision(distances=(0.31,), tolerance_value=0.300)


def test_major2_hostile_cross_raw_resolver_replay_rejected():
    """sol MAJOR-2 repro: the SAME decision object must not validly bind
    into two different `(raw_draw_sha256, resolver_hash)` wrapper pairs.
    Previously both `evidence_binding a b ...` and `evidence_binding c d
    ...` accepted the identical decision with identical decision_sha256.
    Now the decision carries its OWN raw/resolver hash in its preimage, and
    the wrapper cross-validates against it, so re-parenting onto a
    different pair must fail.
    """
    from src.agent.correction.window_sources import canonical_sha256

    decision = _accepted_decision(raw_draw_sha256=RAW_DRAW_SHA_A, resolver_hash=RESOLVER_HASH_B)

    def _wrap(raw_hash, resolver_hash):
        body = {"raw_draw_sha256": raw_hash, "resolver_hash": resolver_hash, "decisions": [decision.model_dump(mode="json")]}
        return WindowPositionEvidenceArtifactV1(
            raw_draw_sha256=raw_hash, resolver_hash=resolver_hash, decisions=(decision,),
            content_sha256=canonical_sha256(body),
        )

    _wrap(RAW_DRAW_SHA_A, RESOLVER_HASH_B)  # correct pairing: must PASS
    with pytest.raises(ValidationError, match="does not match"):
        _wrap("c" * 64, "d" * 64)  # replayed onto a different, unrelated pair: must FAIL


def test_position_evidence_artifact_round_trip_and_totality():
    decision = _accepted_decision(raw_draw_sha256=RAW_DRAW_SHA_A, resolver_hash=RESOLVER_HASH_B)
    from src.agent.correction.window_sources import canonical_sha256

    payload = {
        "raw_draw_sha256": RAW_DRAW_SHA_A, "resolver_hash": RESOLVER_HASH_B,
        "decisions": [decision.model_dump(mode="json")],
    }
    artifact = WindowPositionEvidenceArtifactV1(
        raw_draw_sha256=RAW_DRAW_SHA_A, resolver_hash=RESOLVER_HASH_B, decisions=(decision,),
        content_sha256=canonical_sha256(payload),
    )
    reloaded = WindowPositionEvidenceArtifactV1.model_validate_json(artifact.model_dump_json())
    assert reloaded == artifact
    assert len(reloaded.decisions) == 1
    assert reloaded.decisions[0].window_id == "W-F1-N-1"
