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

=============================================================================
ROUND 2 (2026-08-13, sol re-review, BLOCKER-1 REOPENED):
=============================================================================
The fix above closed the wrong door. `deterministic_core_stamp` lives INSIDE
a candidate's own bytes -- it is a self-report, writable by anything that can
construct a `CorrectedGeometryV3`. sol proved this two ways: (1) hand-adding
`{"deterministic_core_stamp": {"version": "1"}}` to a real, WRONG,
pre-F-17-fix artifact flips it straight to `trusted=True`; (2) more severely,
a candidate whose footprint/floor-ring/cells were forged together (with every
derived artifact -- Vg, host claims, evidence -- re-materialized FROM the
forged footprint, so everything is internally self-consistent) was ACCEPTED
and PERSISTED by the real `StageRunner.record` writer, because the writer's
own independent core replay was only ever compared against WINDOWS' host-
resolved half, never against the replayed footprint/floors/cells themselves.

"这个字段,被评判的一方能不能自己写?能写 => 最多叫 declared,绝不能叫 trusted"
(2026-08-13 dispatch's guiding question) is the fix's spine:

- `_is_declared_output_convention` is the OLD `_is_trusted_output_convention`
  in full (schema_version / CORRECTION_OUTPUT_CONVENTION / stamp version) --
  a necessary, product-writable self-report. Renamed `declared`.
- `_is_trusted_output_convention` now ALSO requires an externally issued
  `DeterministicCoreProofV1` (deterministic.py), signed by
  `StageRunner.record`'s B5 write path ONLY after it independently replayed
  the core and confirmed the replay's `core_owned_projection_v1` byte-
  matches the candidate's footprint/floor-rings/cells/window
  floor-id-and-z/corrections-conflicts-unsupported (stage_runner.py's new
  `writer_core_projection_drift` gauntlet) -- AND that proof is RE-VERIFIED
  here, against the CURRENT geometry under test, not merely trusted because
  a well-formed object was handed in.
- `score_correction_geometry` gained an optional `core_proof` keyword. A bare
  dict/CorrectedGeometry call with no `core_proof` (every test in this file
  that does not explicitly build and pass one) can therefore NEVER reach
  `trusted` -- at most `declared`. `CorrectionScoreResult.output_convention`
  gained a `declared` key, independent of `trusted`.

`test_neuter_restoring_stamp_flips_judge_back_to_accept` (below,
RENAMED/REWRITTEN as `test_neuter_restoring_stamp_flips_declared_not_trusted`)
was sol's exact BLOCKER-1 finding: it asserted the WRONG (self-report-alone)
behaviour as the positive expectation. New tests
`test_core_proof_from_different_geometry_does_not_grant_trust` and
`test_matching_core_proof_grants_trust` are this round's new Lock 5/6,
proving the external-proof gate is both necessary (a mismatched proof cannot
launder a forged geometry) and sufficient (a genuinely matching proof does
reach `trusted`) -- the scorer-side analogue of the writer-side
`writer_core_projection_drift` lock in `tests/test_c2_b5_artifact_trust.py`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pydantic
import pytest

import src.agent.correction.deterministic as deterministic_module
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.deterministic import (
    DETERMINISTIC_CORE_STAMP_VERSION,
    DeterministicCoreProofV1,
    apply_deterministic_core,
    core_owned_projection_v1,
)
from src.agent.correction.envelope import AuthoritativeEnvelope, EnvelopeAxisResolution, EnvelopeCandidate
from src.agent.correction.parse import parse_correction_draw, correction_target
from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.correction.window_sources import WindowResolverInputError
from src.agent.execution.manifest import hash_obj
import src.agent.judge.correction_score as correction_score_module
from src.agent.judge.correction_score import score_correction_geometry
from src.agent.judge.gt import load_gt
from src.agent.judge.score_policy import reading_score_criteria

_SM21 = Path("case_tests/e2e_tests/sm21_anchor")
_PRE_FLIP_OUTPUT = _SM21 / "run_2026-08-09_f17_e2e_verify/1_correction/attempts/001/output.json"
_POST_FLIP_PRE_STAMP_OUTPUT = _SM21 / "run_2026-08-11_continuous_e2e/1_correction/attempts/001/output.json"


def _matching_core_proof(geom: CorrectedGeometryV3, *, core_version: str | None = None) -> DeterministicCoreProofV1:
    """Build a `DeterministicCoreProofV1` whose `core_projection_hash`
    genuinely matches `geom`'s own `core_owned_projection_v1` -- i.e. the
    proof a real `StageRunner.record` write WOULD have signed had this exact
    geometry come out of a genuine core replay. `input_hash` is not read by
    the scorer (only `core_version`/`core_projection_hash` are) so a fixed
    placeholder is fine here."""
    return DeterministicCoreProofV1(
        core_version=core_version or DETERMINISTIC_CORE_STAMP_VERSION,
        input_hash="0" * 64,
        core_projection_hash=hash_obj(core_owned_projection_v1(geom)),
    )


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

    # FIX: the real, current entry point refuses it. No stamp at all ->
    # neither `declared` (the self-report) nor `trusted` (self-report +
    # verified external proof, round 2) can hold.
    result = score_correction_geometry(output, gt)
    assert result.output_convention == {
        "schema_version": "3", "declared": False, "trusted": False, "identity": None,
    }

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
    assert result.output_convention["declared"] is False
    assert result.output_convention["trusted"] is False
    assert result.scores["Floor 1"].boundary is None


# =========================================================================== #
# Lock 2: a zero-displacement legit v3 product is still DECLARED (the §3
# pitfall guard on the self-report layer), and reaches TRUSTED once a
# genuinely matching external proof is supplied (round 2, 2026-08-13).
# =========================================================================== #
def test_zero_displacement_legit_product_is_still_declared():
    """Lock 2. Constructs a v3 product for which `apply_deterministic_core`
    genuinely runs the full envelope-reconcile machinery (real accepted
    facade evidence on both axes, `resolve_envelope_move_intents` actually
    called), but that evidence agrees exactly with the drawing -- so ZERO
    intents are produced and ZERO `deterministic_core.envelope_atomic_transform`
    audit rows are written (empirically confirmed below: this is the exact
    §3 pitfall, not a hypothetical). If the stamp were implemented as "was
    there a correction/conflict/unsupported row", this product would be
    indistinguishable from one the core never touched.

    Round 2 (2026-08-13): the self-report alone (no `core_proof` argument
    passed here) now caps out at `declared`, not `trusted` -- see
    `test_zero_displacement_legit_product_is_trusted_with_matching_core_proof`
    below for the companion positive case that DOES supply a proof.
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
        "schema_version": "3", "declared": True, "trusted": False, "identity": None,
    }
    # `declared` alone must NOT unblock boundary/wall-extent scoring -- that
    # is exactly the round-2 fix.
    assert result.scores["Floor 1"].boundary is None
    assert any(e["type"] == "unsupported_output_convention" for e in result.evidence)


def test_zero_displacement_legit_product_is_trusted_with_matching_core_proof():
    """Companion to the test above: the SAME product, SAME call, but now
    with a `core_proof` that genuinely matches its own
    `core_owned_projection_v1` -- exactly what `StageRunner.record`'s B5
    write path would have signed for this geometry. This is the positive
    half of round 2: the external-proof gate is not merely a way to make
    trust unreachable, it is reachable given a real, matching proof."""
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon")
    proof = _matching_core_proof(out)

    gt = _minimal_gt(w=15.0, d=8.0)
    result = score_correction_geometry(out.model_dump(mode="json"), gt, core_proof=proof)
    assert result.output_convention == {
        "schema_version": "3", "declared": True, "trusted": True,
        "identity": "outer_skin_exterior_centerline_interior",
    }
    assert result.scores["Floor 1"].boundary is not None
    assert result.scores["Floor 1"].boundary_hits() == (4, 4)
    assert not any(e["type"] == "unsupported_output_convention" for e in result.evidence)


def test_zero_displacement_via_absent_envelope_is_also_still_declared():
    """Companion construction for Lock 2: no facade evidence AT ALL
    (`authoritative_envelope=None`) is a SEPARATE way to reach "the core ran,
    nothing to move" (the envelope-reconcile branch is skipped entirely
    rather than consulted-and-agreeing). Both must be `declared` -- the
    stamp must not accidentally depend on which of the two zero-intent paths
    was taken. (Round 2: `trusted` still requires a matching `core_proof`,
    proven separately above; this fixture is only re-checked at the
    `declared` layer here, plus one supplied-proof spot-check.)"""
    geom = _minimal_v3_geometry()
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=None, capability_profile="orthogonal_polygon")
    assert out.deterministic_core_stamp is not None
    assert out.deterministic_core_stamp.version == DETERMINISTIC_CORE_STAMP_VERSION

    gt = _minimal_gt()
    result = score_correction_geometry(out.model_dump(mode="json"), gt)
    assert result.output_convention["declared"] is True
    assert result.output_convention["trusted"] is False

    trusted_result = score_correction_geometry(
        out.model_dump(mode="json"), gt, core_proof=_matching_core_proof(out),
    )
    assert trusted_result.output_convention["trusted"] is True


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
    # A proof matching the PRISTINE (pre-mutation) geometry -- valid, and
    # `core_owned_projection_v1` is unaffected by any of the `mutate`
    # variants below (they only ever touch `deterministic_core_stamp`, never
    # footprint/floors/cells/windows/corrections). Supplied to every variant
    # below to prove round 2's defense-in-depth: a broken/absent SELF-REPORT
    # denies trust even when a genuinely matching EXTERNAL proof is present
    # -- the two checks are independent, neither substitutes for the other.
    matching_proof = _matching_core_proof(out)
    mutate(payload)

    gt = _minimal_gt(w=15.0, d=8.0)
    result = score_correction_geometry(payload, gt, core_proof=matching_proof)

    assert result.output_convention["declared"] is False
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
    decision, not that some other, unrelated fact happens to also flip.

    Round 2 (2026-08-13): a genuinely matching `core_proof` (built from the
    PRE-mutation `out`, so its `core_projection_hash` is real and correct
    for the geometry both calls share) is supplied to BOTH the before and
    after call -- this proves the stamp-mutation flip is NOT merely an
    artifact of "no core_proof was ever supplied" (which would already force
    `trusted: False` regardless of the stamp); it proves the self-report gate
    independently denies trust even when a valid external proof is present.
    """
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon")
    gt = _minimal_gt(w=15.0, d=8.0)
    proof = _matching_core_proof(out)

    trusted_payload = out.model_dump(mode="json")
    before = score_correction_geometry(trusted_payload, gt, core_proof=proof)
    assert before.output_convention["declared"] is True
    assert before.output_convention["trusted"] is True

    bogus_payload = dict(trusted_payload)
    bogus_payload["deterministic_core_stamp"] = {"version": "bogus"}
    after = score_correction_geometry(bogus_payload, gt, core_proof=proof)

    assert after.output_convention["declared"] is False
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

    Round 2 (2026-08-13): the SAME `core_proof` object (its `core_version`
    frozen at construction time to the then-current "1") is supplied to
    every call. Mutating the live constant defeats trust via
    `_is_declared_output_convention`'s stamp-version comparison (the
    `declared` gate is checked first and short-circuits); the SEPARATE
    `core_proof.core_version` live-comparison in `_is_trusted_output_convention`
    is isolated and tested on its own in
    `test_stale_core_proof_version_alone_does_not_grant_trust` below (a
    fixture where the self-report stays genuinely valid but the PROOF's own
    recorded version is stale).
    """
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon")
    gt = _minimal_gt(w=15.0, d=8.0)
    payload = out.model_dump(mode="json")
    proof = _matching_core_proof(out)

    before = score_correction_geometry(payload, gt, core_proof=proof)
    assert before.output_convention["trusted"] is True

    original = deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION
    deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION = "bogus-declared-version"
    try:
        after = score_correction_geometry(payload, gt, core_proof=proof)
    finally:
        deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION = original

    assert after.output_convention["declared"] is False
    assert after.output_convention["trusted"] is False
    assert after.scores["Floor 1"].boundary is None
    # Restoring the constant restores the original decision -- proves this
    # is a live comparison, not a one-way latch.
    restored = score_correction_geometry(payload, gt, core_proof=proof)
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
    calling code that produces a `declared: True` product in the lock-2/4
    tests above must now produce an undeclared, untrusted one, proving the
    judge's decision is actually driven by whether the core's write
    happened, not merely by the field's schema-level existence.

    Round 2 (2026-08-13): a `core_proof` matching the STAMPED (un-neutered)
    baseline geometry is supplied to the neutered call too -- proving the
    self-report gate alone is enough to deny trust even when an otherwise-
    valid external proof for the SAME underlying geometry is present (a
    neutered writer that stops stamping must not be rescuable by a proof
    that was, hypothetically, signed by a properly-working writer for this
    same footprint).

    Sweep self-check (dispatch's mandatory "遮蔽自查"): this fixture has NO
    second gate ahead of `_is_trusted_output_convention` that could reject
    it for an unrelated reason -- `test_zero_displacement_legit_product_is_trusted_with_matching_core_proof`
    above already proves the UN-neutered version of this exact call scores
    `trusted: True` with `boundary_hits() == (4, 4)` when handed a matching
    proof, so any flip to `trusted: False` here is attributable to the
    neuter alone.
    """
    real_apply = deterministic_module.apply_deterministic_core

    def _apply_without_stamping(*args, **kwargs):
        result = real_apply(*args, **kwargs)
        # Simulate "the writer never learned to stamp": strip whatever the
        # real call just wrote, changing NOTHING else about the geometry.
        result.deterministic_core_stamp = None
        return result

    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()

    # Build the matching proof from a GENUINE, un-neutered replay first (the
    # writer's own bookkeeping, not the judge under test).
    stamped_baseline = real_apply(
        geom.model_copy(deep=True), tol, authoritative_envelope=envelope,
        capability_profile="orthogonal_polygon",
    )
    proof = _matching_core_proof(stamped_baseline)

    monkeypatch.setattr(deterministic_module, "apply_deterministic_core", _apply_without_stamping)
    out = deterministic_module.apply_deterministic_core(
        geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon",
    )
    assert out.deterministic_core_stamp is None  # sanity: neuter actually took effect

    gt = _minimal_gt(w=15.0, d=8.0)
    result = score_correction_geometry(out.model_dump(mode="json"), gt, core_proof=proof)
    assert result.output_convention["declared"] is False
    assert result.output_convention["trusted"] is False
    assert result.scores["Floor 1"].boundary is None


def test_neuter_restoring_stamp_flips_declared_not_trusted():
    """Direction B (reverse / consumer side), REWRITTEN for BLOCKER-1 round 2
    (2026-08-13, sol re-review). The ORIGINAL version of this lock
    (`test_neuter_restoring_stamp_flips_judge_back_to_accept`) asserted that
    restoring JUST the self-reported stamp on a bare dict flips the judge
    back to `trusted: True` -- this was sol's exact re-review finding: "现有
    test_neuter_restoring_stamp_flips_judge_back_to_accept 事实上把这种行为写成了
    正向预期". That assertion documented the bug as the intended behaviour.
    The stamp restored here is EXACTLY the shape a forger can write --
    nothing outside `deterministic_core_stamp` changes -- so it must never,
    on its own, regain `trusted`.

    New, correct expectation: restoring the stamp flips `declared` (the
    self-report) from False to True -- preserving the ORIGINAL property this
    lock always cared about: the decision is a live per-call read, not a
    one-way latch that, once a product has been seen without a stamp,
    refuses to ever recognize a stamped copy of it. But `trusted` stays
    False, because no externally issued `deterministic_core_proof` exists
    for this real, pre-stamp, pre-proof historical artifact. (Deliberately
    NOT forging a "matching" proof for it here: this artifact's footprint
    really is the wrong, pre-F-17-fix `[0.12,14.88]x[0.12,7.88]` value --
    constructing a proof "for" it would only prove the hash machinery is
    self-consistent, not that the geometry is trustworthy. That distinction
    is what `test_core_proof_from_different_geometry_does_not_grant_trust`
    below tests directly.)

    Sweep self-check: `dict(output)` is a shallow copy holding the SAME
    nested `floors`/`windows`/etc. as the untrusted `output` scored just
    above it, with `deterministic_core_stamp` the ONLY key that differs
    between the two calls -- no other second gate is in play, so the flip
    is attributable to the stamp alone.
    """
    gt = load_gt("sm21_anchor")
    output = json.loads(_PRE_FLIP_OUTPUT.read_text(encoding="utf-8"))
    baseline = score_correction_geometry(output, gt)
    assert baseline.output_convention["trusted"] is False  # sanity, same as Lock 1
    assert baseline.output_convention["declared"] is False  # sanity, same as Lock 1

    restored = dict(output)
    restored["deterministic_core_stamp"] = {"version": DETERMINISTIC_CORE_STAMP_VERSION}
    after = score_correction_geometry(restored, gt)
    # The live-read property this lock exists to prove: the SELF-REPORT
    # layer flips on a per-call basis, not a one-way latch.
    assert after.output_convention["declared"] is True
    # The bug this reopened BLOCKER-1: a self-reported stamp alone must
    # NEVER be enough to reach `trusted`.
    assert after.output_convention["trusted"] is False
    assert after.scores["Floor 1"].boundary is None


def test_core_proof_from_different_geometry_does_not_grant_trust():
    """Lock 5 (BLOCKER-1 round 2, 2026-08-13): a `core_proof` is only a bag
    of hashes -- `_is_trusted_output_convention` must independently
    recompute `core_owned_projection_v1` on the ACTUAL geometry under test
    and compare, not merely accept any well-formed proof it is handed. This
    is the scorer-level analogue of sol's forged-candidate reproduction
    against the WRITER (`stage_runner.py`'s `writer_core_projection_drift`,
    exercised at the writer layer in `tests/test_c2_b5_artifact_trust.py`):
    take a proof genuinely signed for one (correct) geometry and try to use
    it to launder a DIFFERENT (tampered-footprint) one that merely carries a
    byte-identical, correctly-versioned self-reported stamp.
    """
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    real_geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()
    real_out = apply_deterministic_core(
        real_geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon",
    )
    real_proof = _matching_core_proof(real_out)

    # A DIFFERENT, tampered geometry (sol's exact reproduction shape: a
    # re-signed, forged footprint) -- same schema, same correctly-versioned
    # self-reported stamp, but NOT what `real_proof` was actually issued for.
    forged_geom = _minimal_v3_geometry(fx=(0.12, 3.88), fy=(0.12, 3.88))
    forged_payload = forged_geom.model_dump(mode="json")
    forged_payload["deterministic_core_stamp"] = {"version": DETERMINISTIC_CORE_STAMP_VERSION}

    gt = _minimal_gt(w=15.0, d=8.0)
    result = score_correction_geometry(forged_payload, gt, core_proof=real_proof)
    assert result.output_convention["declared"] is True  # the self-report alone looks fine
    assert result.output_convention["trusted"] is False  # the proof does not match THIS geometry
    assert result.scores["Floor 1"].boundary is None


def test_stale_core_proof_version_alone_does_not_grant_trust():
    """Isolates the `core_proof.core_version` live-comparison in
    `_is_trusted_output_convention`, independent of the `declared` gate
    (companion to Lock 4b, which mutates the live constant and therefore
    exercises BOTH gates at once via short-circuit): the self-report is
    genuinely valid (current stamp, matching projection hash) but the
    PROOF's own recorded `core_version` is stale/foreign."""
    fx, fy = (0.0, 15.0), (0.0, 8.0)
    geom = _minimal_v3_geometry(fx=fx, fy=fy)
    envelope = _agreeing_envelope(fx=fx, fy=fy)
    tol = load_core_tolerances()
    out = apply_deterministic_core(geom, tol, authoritative_envelope=envelope, capability_profile="orthogonal_polygon")
    stale_proof = _matching_core_proof(out, core_version="0")

    gt = _minimal_gt(w=15.0, d=8.0)
    result = score_correction_geometry(out.model_dump(mode="json"), gt, core_proof=stale_proof)
    assert result.output_convention["declared"] is True
    assert result.output_convention["trusted"] is False


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


# =========================================================================== #
# MINOR-A1 (2026-08-12 sol re-review, §3.1 tail, closed in the 2026-08-13
# aprime dispatch alongside F-24/NIT-F25): a refused product's `boundary_complete`
# criterion must not say `pass`.
# =========================================================================== #
def test_minor_a1_boundary_no_data_does_not_read_as_pass():
    """A floor with `boundary is None` (F-22 BLOCKER-1 refusal) used to
    contribute 0/0 to `total_boundary`/`total_boundary_hits`, so the naive
    `missed = total - hits` formula read ZERO misses and `boundary_complete`
    said `pass` -- the one criterion still saying "fine" on a product that
    `walls_complete`/`score_evidence_completeness` both already correctly
    flag `severe`.

    Self-proving premise (this project's "回归用例必须自证前提" discipline,
    same fixture Lock 1 above uses): first prove, on this exact real on-disk
    pre-F-17-fix artifact, that every scored floor genuinely has no boundary
    data and that the naive missed-count formula genuinely evaluates to 0
    here -- not merely assume it.
    """
    gt = load_gt("sm21_anchor")
    output = json.loads(_PRE_FLIP_OUTPUT.read_text(encoding="utf-8"))
    result = score_correction_geometry(output, gt)

    # PREMISE: this fixture is genuinely all-no-data on boundary, and the old
    # `missed = total - hits` formula genuinely computes 0 misses on it.
    assert len(result.scores) == 2
    assert all(fl.boundary is None for fl in result.scores.values())
    total_boundary_hits = sum(fl.boundary_hits()[0] for fl in result.scores.values())
    total_boundary = sum(fl.boundary_hits()[1] for fl in result.scores.values())
    assert (total_boundary_hits, total_boundary) == (0, 0)
    assert max(0, total_boundary - total_boundary_hits) == 0, (
        "premise: the naive missed-count formula really is 0 misses on this fixture"
    )

    # FIX: `boundary_complete` must not say pass on a refused product -- it
    # must agree with `walls_complete`, a DIFFERENT criterion computed from
    # different data, not be silently corrected by it (sol: "不能靠另一条
    # criterion 替它纠正含义").
    criteria = {c["criterion"]: c for c in reading_score_criteria(result.scores)}
    assert criteria["walls_complete"]["suggested_status"] == "severe"
    assert criteria["boundary_complete"]["suggested_status"] != "pass"
    assert criteria["boundary_complete"]["suggested_status"] == "severe"
    assert "no_data_floors=2" in criteria["boundary_complete"]["evidence"]
