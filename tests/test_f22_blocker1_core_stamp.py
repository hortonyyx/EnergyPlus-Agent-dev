"""F-22 BLOCKER-1 (2026-08-12): the deterministic core's UNCONDITIONAL
"I ran, version is X" stamp, and the judge's verification of it.

Dispatch: `AI_agent/logs/reviews/request/2026-08-12_e_unconditional_core_stamp_dispatch_claude.md`.
sol re-review that reopened BLOCKER-1: `AI_agent/logs/reviews/verdict/2026-08-12_f22_f9s0s1_rework_rereview_sol.md`.

The bug this closes: `_is_trusted_output_convention` (correction_score.py)
used to trust a product on `schema_version == "3"` alone. A bug fix to the
deterministic core's transform logic (F-17, 2026-08-09) does not bump
`schema_version` -- by this project's own convention, fixing a bug never
changes a version number -- so the SAME `schema_version == "3"` spans real
runs both before and after that fix. `run_2026-08-09_f17_e2e_verify` (before)
and `run_2026-08-11_continuous_e2e` (after) are both on disk, same declared
`capability_profile`, both `schema_version == "3"`, but the pre-fix run's
footprint sits at `[0.12,14.88]x[0.12,7.88]` (0.12 m off every side) while
the post-fix run sits at `[0,15]x[0,8]` (correct) -- yet the old check scored
BOTH five-for-five `pass`.

The fix: `apply_deterministic_core` (deterministic.py) now writes a SEPARATE,
UNCONDITIONAL `deterministic_core_stamp` (schema.py's `DeterministicCoreStampV1`)
on every schema-v3 completion, regardless of whether anything actually moved
-- the critical property, since a conditional `corrections[].envelope_atomic_transform`
record (the natural-seeming alternative) is ABSENT both when the core never
ran AND when it ran and had nothing to do (envelope_transform.py's
`if not intents: return ... # no record left at all`), so absence alone
cannot distinguish "untrustworthy" from "fully trustworthy". The judge now
additionally requires this stamp's version to exactly match
`deterministic.DETERMINISTIC_CORE_STAMP_VERSION`.

User-ratified consequence (no historical whitelist): EVERY existing artifact,
including `run_2026-08-11_continuous_e2e` (produced by the F-17-fixed core,
but before this stamp existed), lacks the stamp and is therefore untrusted
until rerun. That is locked as an explicit, expected fact below (not merely
implied), matching this project's own "回归用例必须自证前提" discipline: a
lock must first prove the condition it depends on genuinely holds on this
exact fixture, not assume it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pydantic
import pytest

import src.agent.correction.deterministic as deterministic_module
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.deterministic import DETERMINISTIC_CORE_STAMP_VERSION, apply_deterministic_core
from src.agent.correction.envelope import AuthoritativeEnvelope, EnvelopeAxisResolution, EnvelopeCandidate
from src.agent.correction.parse import parse_correction_draw, correction_target
from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.correction.window_sources import WindowResolverInputError
import src.agent.judge.correction_score as correction_score_module
from src.agent.judge.correction_score import score_correction_geometry
from src.agent.judge.gt import load_gt

_SM21 = Path("case_tests/e2e_tests/sm21_anchor")
_PRE_FLIP_OUTPUT = _SM21 / "run_2026-08-09_f17_e2e_verify/1_correction/attempts/001/output.json"
_POST_FLIP_PRE_STAMP_OUTPUT = _SM21 / "run_2026-08-11_continuous_e2e/1_correction/attempts/001/output.json"


# =========================================================================== #
# Shared construction helpers
# =========================================================================== #
def _minimal_v3_geometry(*, fx=(0.0, 15.0), fy=(0.0, 8.0)) -> CorrectedGeometryV3:
    """The smallest legal schema-v3 (`orthogonal_polygon`) geometry: one
    floor, one rectangular cell exactly filling the footprint, no windows."""
    return CorrectedGeometryV3.model_validate({
        "schema_version": "3",
        "footprint_x": list(fx),
        "footprint_y": list(fy),
        "floors": [{
            "id": "floor-1", "name": "Floor 1", "z_floor": 0.0, "ceiling_height": 3.0,
            "footprint": {"vertices": [[fx[0], fy[0]], [fx[1], fy[0]], [fx[1], fy[1]], [fx[0], fy[1]]]},
            "cells": [{
                "id": "A", "role": "office", "x": [fx[0], fx[1]], "y": [fy[0], fy[1]],
                "polygon": [[fx[0], fy[0]], [fx[1], fy[0]], [fx[1], fy[1]], [fx[0], fy[1]]],
            }],
        }],
        "windows": [],
    })


def _agreeing_envelope(*, fx=(0.0, 15.0), fy=(0.0, 8.0)) -> AuthoritativeEnvelope:
    """An AuthoritativeEnvelope whose accepted bounds on BOTH axes are
    EXACTLY the current footprint -- i.e. real facade evidence exists (it is
    `status="accepted"`, not absent) and it agrees with the drawing (the
    outer skin was already what got drawn), so `resolve_envelope_move_intents`
    produces ZERO intents on either axis (every `abs(new-old) <=
    output_precision_m` -> `continue`, no intent appended).

    This is the literal §3 pitfall scenario from the dispatch: "图纸本来就按
    外皮标注时,核什么都不用改 -- 合法产物同样没有记录". Constructed via
    direct dataclass construction (`EnvelopeCandidate`/`EnvelopeAxisResolution`/
    `AuthoritativeEnvelope` are plain frozen dataclasses, envelope.py) rather
    than real facade image files -- deliberately, so this fixture is fast,
    hermetic, and does not depend on any 0_reading artifact.
    """
    # NOTE: `view` must contain a facade word with a proper regex \b word
    # boundary around it (envelope.py's `_FACADE_RE`) -- "north_elevation"
    # does NOT match (underscore is a \w character, so there is no boundary
    # between "north" and "_elevation"); real 0_reading view ids use a space
    # or hyphen, e.g. "north elevation.json". Use "north view"/"east view"
    # here to stay clear of that trap.
    x_candidate = EnvelopeCandidate(
        axis="x", bounds=fx, span=fx[1] - fx[0], source_kind="outline",
        view="north view", source_id="src:" + "0" * 64, role="overall",
    )
    y_candidate = EnvelopeCandidate(
        axis="y", bounds=fy, span=fy[1] - fy[0], source_kind="outline",
        view="east view", source_id="src:" + "1" * 64, role="overall",
    )
    return AuthoritativeEnvelope(axes={
        "x": EnvelopeAxisResolution(axis="x", status="accepted", bounds=fx, span=fx[1] - fx[0], source=x_candidate),
        "y": EnvelopeAxisResolution(axis="y", status="accepted", bounds=fy, span=fy[1] - fy[0], source=y_candidate),
    })


def _minimal_gt(*, w=15.0, d=8.0) -> dict:
    return {
        "footprint": {"W_m": w, "D_m": d},
        "floors": [{"name": "Floor 1", "zones": [{"rect_m": [0, 0, w, d]}]}],
        "windows": [],
    }


# =========================================================================== #
# Lock 1: pre-flip real artifact rejected (self-proving premise).
# =========================================================================== #
def _old_one_check_trust_formula(schema_version) -> bool:
    """Re-derivation of the PRE-FIX `_is_trusted_output_convention` (before
    2026-08-12): `schema_version == "3"` was the ONLY fact checked.
    Reproduced here ONLY to prove this lock's premise -- production code no
    longer contains this formula (it now also requires the stamp; see
    `_is_trusted_output_convention` in correction_score.py)."""
    return schema_version == "3"


def test_pre_flip_real_artifact_is_rejected_and_premise_self_proven():
    """Lock 1. Uses the REAL, on-disk `run_2026-08-09_f17_e2e_verify`
    artifact -- sol's exact BLOCKER-1 reproduction (verdict table row 1):
    schema-v3, `capability_profile: orthogonal_polygon`, footprint
    `[0.12,14.88]x[0.12,7.88]` (0.12 m off every side vs. gt's true outer
    skin), produced BEFORE the F-17 envelope-transform fix.
    """
    gt = load_gt("sm21_anchor")
    output = json.loads(_PRE_FLIP_OUTPUT.read_text(encoding="utf-8"))

    # PREMISE: under the pre-fix, schema-version-only trust formula, this
    # exact real artifact WOULD have been treated as trusted -- reproducing
    # sol's finding that it scored five-for-five `pass` with zero refusal
    # evidence despite every boundary side actually differing by 0.12 m.
    assert output.get("schema_version") == "3"
    assert _old_one_check_trust_formula(output.get("schema_version")) is True
    assert output.get("footprint_x") == [0.12, 14.88]
    assert output.get("footprint_y") == [0.12, 7.88]
    # This artifact predates the stamp's existence entirely -- not merely a
    # None value, the key itself is absent from the real, on-disk JSON.
    assert "deterministic_core_stamp" not in output

    # FIX: the real, current entry point refuses it.
    result = score_correction_geometry(output, gt)
    assert result.output_convention == {"schema_version": "3", "trusted": False, "identity": None}

    # Refusal must not "look like" a pass on either scored floor.
    # `boundary` has a dedicated "no data" representation (None ->
    # boundary_hits() == (0, 0)). Interior wall extents do NOT: `vwalls`/
    # `hwalls` are always populated one-per-gt-truth-wall (from
    # `_match_wall_segments`, matching against GT truth regardless of
    # whether anything was read) -- an untrusted product's READ side is
    # empty (`_extract_correction_wall_segments` returns `[], []`), so every
    # one of those gt-truth-anchored entries comes back a "miss" with
    # `read is None`, not an empty list. Assert the STRONGER property: zero
    # HITS (not e.g. the pre-fix bug's asymmetric 2-of-4 "pass" shape) and
    # every entry genuinely unmatched.
    for floor_name in ("Floor 1", "Floor 2"):
        floor = result.scores[floor_name]
        assert floor.boundary is None
        assert floor.boundary_hits() == (0, 0)
        hit, total = floor.wall_hits()
        assert hit == 0
        assert total > 0  # sanity: gt genuinely has interior walls on this floor
        assert all(m.read is None for m in floor.vwalls + floor.hwalls)
    assert any(e["type"] == "unsupported_output_convention" for e in result.evidence)

    # Window matching is a DIFFERENT code path, untouched by this gate (see
    # `_extract_correction_wall_segments`'s docstring) -- sanity that the fix
    # is scoped to boundary/wall-extent, not a blanket "untrusted -> no
    # score at all".
    assert result.scores["Floor 1"].window_hits() != (0, 0) or result.scores["Floor 2"].window_hits() != (0, 0)


def test_post_flip_pre_stamp_real_artifact_also_rejected():
    """Companion to Lock 1, second row of sol's reproduction table: a real
    run produced AFTER the F-17 fix landed (footprint correctly at
    `[0,15]x[0,8]`) but BEFORE this stamp existed. User-ratified: this run
    is ALSO untrusted as committed to disk today -- it needs a rerun to
    regain a score, which is the intended enforcement, not a gap. (The
    `CORRECTION_OUTPUT_CONVENTION`-mutation self-test in
    test_judge_batch_b.py injects a stamp into a COPY of this same fixture
    to keep testing that separate guard; this lock instead asserts the
    as-committed, unmodified behaviour.)
    """
    gt = load_gt("sm21_anchor")
    output = json.loads(_POST_FLIP_PRE_STAMP_OUTPUT.read_text(encoding="utf-8"))
    assert output.get("schema_version") == "3"
    assert output.get("footprint_x") == [0.0, 15.0]  # sanity: this IS the post-F-17-fix run
    assert output.get("footprint_y") == [0.0, 8.0]
    assert "deterministic_core_stamp" not in output

    result = score_correction_geometry(output, gt)
    assert result.output_convention["trusted"] is False
    assert result.scores["Floor 1"].boundary is None


# =========================================================================== #
# Lock 2: a zero-displacement legit v3 product is still trusted (the §3
# pitfall guard).
# =========================================================================== #
def test_zero_displacement_legit_product_is_still_trusted():
    """Lock 2. Constructs a v3 product for which `apply_deterministic_core`
    genuinely runs the full envelope-reconcile machinery (real accepted
    facade evidence on both axes, `resolve_envelope_move_intents` actually
    called), but that evidence agrees exactly with the drawing -- so ZERO
    intents are produced and ZERO `deterministic_core.envelope_atomic_transform`
    audit rows are written (empirically confirmed below: this is the exact
    §3 pitfall, not a hypothetical). If the stamp were implemented as "was
    there a correction/conflict/unsupported row", this product would be
    indistinguishable from one the core never touched. It must still be
    trusted.
    """
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()

    out = apply_deterministic_core(geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon")

    # Self-proving premise: real evidence was consulted, and it produced NO
    # audit trail entry of any kind -- the exact ambiguity the stamp exists
    # to resolve.
    assert out.corrections == []
    assert out.conflicts == []
    assert out.unsupported == []
    assert out.deterministic_core_stamp is not None
    assert out.deterministic_core_stamp.version == DETERMINISTIC_CORE_STAMP_VERSION

    gt = _minimal_gt(w=15.0, d=8.0)
    result = score_correction_geometry(out.model_dump(mode="json"), gt)
    assert result.output_convention == {
        "schema_version": "3", "trusted": True,
        "identity": "outer_skin_exterior_centerline_interior",
    }
    assert result.scores["Floor 1"].boundary is not None
    assert result.scores["Floor 1"].boundary_hits() == (4, 4)
    assert not any(e["type"] == "unsupported_output_convention" for e in result.evidence)


def test_zero_displacement_via_absent_envelope_is_also_still_trusted():
    """Companion construction for Lock 2: no facade evidence AT ALL
    (`authoritative_envelope=None`) is a SEPARATE way to reach "the core ran,
    nothing to move" (the envelope-reconcile branch is skipped entirely
    rather than consulted-and-agreeing). Both must be trusted -- the stamp
    must not accidentally depend on which of the two zero-intent paths was
    taken."""
    geom = _minimal_v3_geometry()
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=None, capability_profile="orthogonal_polygon")
    assert out.deterministic_core_stamp is not None
    assert out.deterministic_core_stamp.version == DETERMINISTIC_CORE_STAMP_VERSION

    gt = _minimal_gt()
    result = score_correction_geometry(out.model_dump(mode="json"), gt)
    assert result.output_convention["trusted"] is True


# =========================================================================== #
# Lock 3: missing / None / unrecognized-version stamp -> fail closed, and the
# refusal does not "look like" a pass.
# =========================================================================== #
@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda d: d.pop("deterministic_core_stamp", None), id="key_absent"),
        pytest.param(lambda d: d.__setitem__("deterministic_core_stamp", None), id="explicit_none"),
        pytest.param(lambda d: d.__setitem__("deterministic_core_stamp", {"version": "0"}), id="unrecognized_version_0"),
        pytest.param(lambda d: d.__setitem__("deterministic_core_stamp", {"version": "bogus"}), id="unrecognized_version_bogus"),
        pytest.param(lambda d: d.__setitem__("deterministic_core_stamp", {"version": "2"}), id="unrecognized_version_future"),
    ],
)
def test_fail_closed_variants_do_not_look_like_a_pass(mutate):
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon")
    assert out.deterministic_core_stamp is not None  # sanity: starts genuinely trusted

    payload = out.model_dump(mode="json")
    assert payload["deterministic_core_stamp"] == {"version": DETERMINISTIC_CORE_STAMP_VERSION}  # sanity
    mutate(payload)

    gt = _minimal_gt(w=15.0, d=8.0)
    result = score_correction_geometry(payload, gt)

    assert result.output_convention["trusted"] is False
    assert result.output_convention["identity"] is None
    floor = result.scores["Floor 1"]
    assert floor.boundary is None
    assert floor.boundary_hits() == (0, 0)
    # (unlike Lock 1's real sm21_anchor fixture) this floor's gt has a
    # single full-footprint zone -> zero interior walls in gt truth at all,
    # so vwalls/hwalls are genuinely empty here regardless of trust status
    # (nothing to produce a "miss" entry against). Not the stronger
    # zero-hits-out-of-a-real-total property Lock 1 asserts.
    assert floor.vwalls == [] and floor.hwalls == []
    evidence_types = [e["type"] for e in result.evidence]
    assert "unsupported_output_convention" in evidence_types
    # The refusal reason must be diagnostic and TRUTHFUL: this product's
    # schema_version genuinely IS "3" (qualifies), so a message that only
    # ever blames "schema_version does not qualify" (the stale,
    # pre-2026-08-12 text) would be FALSE for every one of this
    # parametrization's variants. It must instead name the actual cause
    # (the core stamp).
    reason = next(e["reason"] for e in result.evidence if e["type"] == "unsupported_output_convention")
    assert "deterministic_core_stamp" in reason
    assert "schema_version does not qualify" not in reason


def test_malformed_stamp_inner_shape_raises_at_parse_not_silently_untrusted():
    """Documents (not merely asserts) a deliberate design choice: a stamp
    object PRESENT but missing its own required `version` key is a
    structurally malformed v3 artifact -- like any other required-field
    violation on `CorrectedGeometryV3`, it fails LOUD at parse time (a
    pydantic ValidationError), the same as every other strict v3 field. It
    does not silently degrade to "absent -> untrusted"; a caller must not be
    able to construct a syntactically-broken stamp and have the judge treat
    it as merely "no stamp"."""
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    payload = geom.model_dump(mode="json")
    payload["deterministic_core_stamp"] = {}  # present, but missing required "version"

    with pytest.raises(pydantic.ValidationError, match="deterministic_core_stamp"):
        score_correction_geometry(payload, _minimal_gt(w=15.0, d=8.0))


# =========================================================================== #
# Lock 4: the stamp is load-bearing, not a comment wearing a field name.
# =========================================================================== #
def test_stamp_value_mutation_on_product_changes_scoring_behavior():
    """Lock 4a: mutate the PRODUCT's own stamp value to `bogus` (holding
    schema_version, CORRECTION_OUTPUT_CONVENTION, and every geometry byte
    fixed) and confirm scoring changes. This is the most direct reading of
    "把印章值改成 bogus,判卷行为必须变" -- it proves `_is_trusted_output_convention`
    genuinely READS `geom.deterministic_core_stamp.version` as part of its
    decision, not that some other, unrelated fact happens to also flip."""
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon")
    gt = _minimal_gt(w=15.0, d=8.0)

    trusted_payload = out.model_dump(mode="json")
    before = score_correction_geometry(trusted_payload, gt)
    assert before.output_convention["trusted"] is True

    bogus_payload = dict(trusted_payload)
    bogus_payload["deterministic_core_stamp"] = {"version": "bogus"}
    after = score_correction_geometry(bogus_payload, gt)

    assert after.output_convention["trusted"] is False
    assert before.scores["Floor 1"].boundary is not None
    assert after.scores["Floor 1"].boundary is None


def test_declared_trusted_version_mutation_changes_scoring_behavior():
    """Lock 4b: the SAME self-test pattern this module already required for
    `CORRECTION_OUTPUT_CONVENTION`
    (test_judge_batch_b.py::test_output_convention_declaration_mutation_changes_scoring_behavior,
    "sol 上一轮点名的自测判据"), applied to the NEW declared-trusted-version
    constant: mutate `deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION`
    itself (not the product) and confirm a real, otherwise-trusted product's
    score changes. Mutating the SOURCE module's attribute (not a
    `from ... import NAME`-bound local copy) is what makes this observable
    at all -- `correction_score.py` reads it via
    `deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION` (module-qualified,
    resolved fresh on every call), the same "single declared source, no
    drift" discipline as `CORRECTION_OUTPUT_CONVENTION`.
    """
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon")
    gt = _minimal_gt(w=15.0, d=8.0)
    payload = out.model_dump(mode="json")

    before = score_correction_geometry(payload, gt)
    assert before.output_convention["trusted"] is True

    original = deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION
    deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION = "bogus-declared-version"
    try:
        after = score_correction_geometry(payload, gt)
    finally:
        deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION = original

    assert after.output_convention["trusted"] is False
    assert after.scores["Floor 1"].boundary is None
    # Restoring the constant restores the original decision -- proves this
    # is a live comparison, not a one-way latch.
    restored = score_correction_geometry(payload, gt)
    assert restored.output_convention["trusted"] is True


# =========================================================================== #
# Wiring neuters (>= 2 directions, BEHAVIORAL not shape-matching per dispatch
# §5's XOR/double-negation warning): does the JUDGE's decision actually track
# whether the CORE produced/preserved the stamp, end to end through the real
# entry points on both sides -- not just "the field exists and is read
# somewhere".
# =========================================================================== #
def test_neuter_writer_stops_stamping_judge_flips_to_reject(monkeypatch):
    """Direction A (production side): monkeypatch the REAL
    `apply_deterministic_core` so it does EVERYTHING it normally does except
    the one line that writes the stamp (simulating "the core never learned
    to stamp at all", i.e. reverting to pre-2026-08-12 core behaviour) --
    `correction_score.py` itself is completely untouched. The exact same
    calling code that produces a trusted product in the lock-2/4 tests above
    must now produce an untrusted one, proving the judge's decision is
    actually driven by whether the core's write happened, not merely by the
    field's schema-level existence.

    Sweep self-check (dispatch's mandatory "遮蔽自查"): this fixture has NO
    second gate ahead of `_is_trusted_output_convention` that could reject
    it for an unrelated reason -- `test_zero_displacement_legit_product_is_still_trusted`
    above already proves the UN-neutered version of this exact call scores
    `trusted: True` with `boundary_hits() == (4, 4)`, so any flip to
    `trusted: False` here is attributable to the neuter alone.
    """
    real_apply = deterministic_module.apply_deterministic_core

    def _apply_without_stamping(*args, **kwargs):
        result = real_apply(*args, **kwargs)
        # Simulate "the writer never learned to stamp": strip whatever the
        # real call just wrote, changing NOTHING else about the geometry.
        result.deterministic_core_stamp = None
        return result

    monkeypatch.setattr(deterministic_module, "apply_deterministic_core", _apply_without_stamping)

    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()

    out = deterministic_module.apply_deterministic_core(
        geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon",
    )
    assert out.deterministic_core_stamp is None  # sanity: neuter actually took effect

    gt = _minimal_gt(w=15.0, d=8.0)
    result = score_correction_geometry(out.model_dump(mode="json"), gt)
    assert result.output_convention["trusted"] is False
    assert result.scores["Floor 1"].boundary is None


def test_neuter_restoring_stamp_flips_judge_back_to_accept():
    """Direction B (reverse / consumer side): start from a real product with
    NO stamp (the current, as-shipped `run_2026-08-09_f17_e2e_verify`
    artifact -- genuinely untrusted, per Lock 1) and, WITHOUT touching
    `correction_score.py`, restore a valid stamp on a copy of it. The
    (unmodified) judge must flip back to trusting it. This is the
    complementary direction to Direction A: A proves "removing production
    causes rejection"; B proves the gate is not a one-way latch that, once a
    product has been seen without a stamp, refuses to trust ANY copy of
    it -- the decision is a live per-call read of the field's value, in
    both directions.

    Sweep self-check: `dict(output)` is a shallow copy holding the SAME
    nested `floors`/`windows`/etc. as the untrusted `output` scored just
    above it, with `deterministic_core_stamp` the ONLY key that differs
    between the two calls -- no other second gate is in play, so the flip
    from `False` to `True` is attributable to the stamp alone.
    """
    gt = load_gt("sm21_anchor")
    output = json.loads(_PRE_FLIP_OUTPUT.read_text(encoding="utf-8"))
    baseline = score_correction_geometry(output, gt)
    assert baseline.output_convention["trusted"] is False  # sanity, same as Lock 1

    restored = dict(output)
    restored["deterministic_core_stamp"] = {"version": DETERMINISTIC_CORE_STAMP_VERSION}
    after = score_correction_geometry(restored, gt)
    assert after.output_convention["trusted"] is True
    assert after.scores["Floor 1"].boundary is not None


# =========================================================================== #
# Belt-and-suspenders: the raw-draw preflight rejects a model that pre-fills
# the stamp (CORRECTION_DRAW_FORBIDDEN), via the SAME marker-driven mechanism
# `facade_segments`/`north_axis` already use -- confirms zero edits were
# needed in parse.py/window_sources.py (both outside this fix's file
# ownership) for this protection to apply to the new field.
# =========================================================================== #
def test_producer_draw_prefilling_stamp_is_rejected_at_preflight():
    target = correction_target("orthogonal_polygon")
    payload = {
        "schema_version": "3",
        "footprint_x": [0.0, 15.0], "footprint_y": [0.0, 8.0],
        "floors": [{
            "id": "floor-1", "name": "Floor 1", "z_floor": 0.0, "ceiling_height": 3.0,
            "footprint": {"vertices": [[0, 0], [15, 0], [15, 8], [0, 8]]},
            "cells": [{"id": "A", "role": "office", "x": [0, 15], "y": [0, 8],
                       "polygon": [[0, 0], [15, 0], [15, 8], [0, 8]]}],
        }],
        "windows": [],
        "deterministic_core_stamp": {"version": DETERMINISTIC_CORE_STAMP_VERSION},
    }
    with pytest.raises(WindowResolverInputError) as exc_info:
        parse_correction_draw(payload, target)
    assert "deterministic_core_stamp" in str(exc_info.value)
