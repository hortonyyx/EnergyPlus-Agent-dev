"""B-1' (2026-08-08 interface sweep §5): two independent fail-open shapes in
``src/validator/checks/schema.py``, both "the default direction was wrong"
rather than "a value is missing":

1. ``disposition()``'s ``run_profile`` parameter and ``CheckReport.run_profile``
   both defaulted to ``"exploratory"`` — the MOST lenient profile — so a
   dropped/omitted ``run_profile`` anywhere on the call chain silently judged
   under the loosest policy instead of erroring. Fixed by defaulting to
   ``"regression"`` — the strictest profile — instead (a smaller, pre-
   authorized fallback from "remove the default and make it required": a full
   sweep found ~30 test call sites and zero live production call sites that
   are actually run_profile-sensitive would need touching for the "required"
   version — see the execution log for the count).
2. The evidence-debt and plan-frame block sets were "block whitelists"
   (``run_profile in {"golden", "regression"}``) — a future, stricter profile
   that isn't in the set silently does NOT block. Flipped to "permissive
   whitelists" (``run_profile not in {"exploratory", "dev"}`` ⇒ block), so an
   unknown future profile now defaults to strict instead of lenient.

The OCR-anchor and dimension-endpoint block sets are deliberately NOT given
the same flip — see the long comment on ``_OCR_ANCHOR_BLOCK_PROFILES`` in
schema.py and the execution log's 摊三 §2 for why: those two are advisory on
every profile (including golden/regression) because the underlying heuristic
itself is known unreliable in both directions, not because some profiles are
lenient. This file locks that this deliberate non-flip is what's actually
implemented, so any future edit that mechanically "completes" the flip for
these two shows up as a failing test instead of a silent behavior change.
"""

from src.validator.checks.schema import (
    CheckLayer,
    CheckReport,
    CheckResult,
    CheckStatus,
    Disposition,
    disposition,
)


def _fail_result(check_id: str, layer: CheckLayer = CheckLayer.CROSS_CHECK) -> CheckResult:
    return CheckResult(check_id=check_id, status=CheckStatus.FAIL, layer=layer)


# ---- point 1: default direction (lenient -> strict) ----------------------


def test_disposition_default_run_profile_is_strict_not_lenient():
    """Omitting `run_profile` entirely must fail closed. Before the fix the
    default was "exploratory" and this same call returned FLAG."""
    result = _fail_result("reading.dimension_chain_closure")
    assert disposition(result) == Disposition.BLOCK


def test_checkreport_default_run_profile_is_strict_not_lenient():
    """Same guard at the model-field level: a `CheckReport` built with no
    explicit `run_profile` must block on an evidence-debt failure. Before the
    fix the field default was "exploratory" and `.blocking()` would be empty
    here."""
    rep = CheckReport(stage="0_reading")
    rep.add_fail("reading.dimension_chain_closure", CheckLayer.CROSS_CHECK, "chain does not close")
    assert rep.blocking(), "a CheckReport with no explicit run_profile must fail closed"
    assert rep.blocking()[0].check_id == "reading.dimension_chain_closure"


def test_disposition_default_does_not_change_behavior_for_known_insensitive_callers():
    """Sanity companion to the two locks above: proves the default-value
    change is a no-op for the two call sites that relied on the old default
    (assembly.check_ep_baseline's ERROR/INVARIANT-only checks and
    test_execution_foundation's ERROR-status test) — both are ERROR or plain
    non-evidence INVARIANT/CROSS_CHECK checks, which never consult
    `run_profile` at all."""
    error_result = CheckResult(
        check_id="ep.end_present", status=CheckStatus.ERROR, layer=CheckLayer.INVARIANT
    )
    assert disposition(error_result) == Disposition.BLOCK  # ERROR is unconditional
    invariant_fail = _fail_result("ep.zero_severe", layer=CheckLayer.INVARIANT)
    assert disposition(invariant_fail) == Disposition.BLOCK  # plain INVARIANT is unconditional
    cross_check_fail = _fail_result("ep.warning_threshold", layer=CheckLayer.CROSS_CHECK)
    assert disposition(cross_check_fail) == Disposition.FLAG  # plain CROSS_CHECK is unconditional


# ---- point 2: block-whitelist -> permissive-whitelist flip ----------------


def test_future_run_profile_defaults_to_block_for_evidence_checks():
    """A hypothetical future profile stricter than "regression" isn't a
    Literal member yet, but nothing stops a caller from passing an arbitrary
    string at runtime — this is exactly the "someone adds a 5th profile and
    forgets to update every block-set" shape the interface sweep flagged.
    It must default to BLOCK now, not silently inherit leniency."""
    result = _fail_result("reading.dimension_chain_closure")
    assert disposition(result, run_profile="hypothetical_stricter_profile") == Disposition.BLOCK


def test_future_run_profile_defaults_to_block_for_plan_frame_check():
    result = _fail_result("reading.plan_scale_origin_usable")
    assert disposition(result, run_profile="hypothetical_stricter_profile") == Disposition.BLOCK


def test_known_lenient_profiles_still_flag_not_block_for_evidence_and_plan_frame():
    """The flip must be behavior-preserving for the four profiles that exist
    today: exploratory/dev stay lenient (FLAG), golden/regression stay strict
    (BLOCK) — exactly like before, just expressed as the opposite set."""
    evidence = _fail_result("reading.dimension_chain_closure")
    plan_frame = _fail_result("reading.plan_scale_origin_usable")
    for lenient in ("exploratory", "dev"):
        assert disposition(evidence, run_profile=lenient) == Disposition.FLAG
        assert disposition(plan_frame, run_profile=lenient) == Disposition.FLAG
    for strict in ("golden", "regression"):
        assert disposition(evidence, run_profile=strict) == Disposition.BLOCK
        assert disposition(plan_frame, run_profile=strict) == Disposition.BLOCK


# ---- deliberate non-flip: OCR anchor / dimension endpoint stay advisory ---


def test_ocr_anchor_and_dimension_endpoint_stay_advisory_on_every_profile_including_future():
    """These two checks are advisory (never BLOCK) on every profile, including
    a hypothetical future stricter one — a DELIBERATE deviation from the
    general "future profile defaults to strict" fix above, because the
    heuristic itself (not any profile's leniency) is why it's advisory (2026-
    08-04 downgrade). If a future edit "completes" the whitelist flip for
    these two, this test must catch it."""
    ocr = _fail_result("reading.ocr_anchors_in_bounds")
    dim_ep = _fail_result("reading.dimension_endpoints_in_bounds")
    for profile in ("exploratory", "dev", "golden", "regression", "hypothetical_stricter_profile"):
        assert disposition(ocr, run_profile=profile) == Disposition.FLAG
        assert disposition(dim_ep, run_profile=profile) == Disposition.FLAG
