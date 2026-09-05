"""The ONE declaration of which projected-ring structural failures this
batch treats as known deferred debt — and who retires them.

A-11 rework-1 root cause B: two test files each stated a position on the
SAME invariant against the SAME substrate.  ``test_boundary_condition_facts``
was updated to accept ``deferred == 4`` while the zero-threshold test in
``test_f156_ring_from_intersection`` still asserted ``residuals == []`` —
green in one file, red in the other, on one batch of data.  The rework
verdict's ruling: this is ONE adjudication with ONE declaration point, ⛔
not two files voting separately.  Both files import every name below from
here and define nothing of their own.

═══ THE ADJUDICATION (2026-09-05, A-11 rework-1) ═══

F-153 form B IS a known debt of this batch — ⛔ NOT a new error exposed by
the 1 mm ingest snap.  Measured, not narrated (both sides of the swap):

* PRE-A11  (basepoint c7c6831a): the B-1 wall sits at ``along_min=52401``
  (0.1 mm off its siblings), the cavity behind it cannot ring, and the
  producer writes ONE ledger entry — ``endcap_const_not_a_measured_parallel_face``,
  ``span.const=52401``, ``area_units2=2868321200`` (28.683212 m²).  That
  producer-written loss is locked fail-loud by ``tests/test_o21d_exclusion_gap.py``
  ("the sole surviving ledger entry is F-153 form B ... delta=1").
* POST-A11 (this tree): the snap moves the wall to ``52400``, the 286.8 m²
  cavity closes into two REAL rooms, their rings become buildable — and the
  SAME endcap geometry difference becomes COMPARABLE for the first time,
  surfacing as two ``facts_projected_ring_is_not_the_converter_zone`` rows
  (F1-z4 / F1-z5, symmetric_difference_units2=1182000 each) with BOTH sides
  compared on the same 1 mm grid, so 0.1 mm representation noise can no
  longer hide there.

Same defect, different visibility.  The snap did not create it; it replaced
a "cannot compare" with a "compares, and differs".

The other two deferred entries are F-157's (answer-side ``outer_skin`` ←→
``wall_axis`` basis switch part way along a single support line): one per
plan, pre-A11 debt, untouched by the snap.

WHO RETIRES WHAT, AND WHEN:

* the two F-153 form B rows retire when the upstream converter endcap
  geometry fix lands — the projected ring then equals the zone bit-for-bit
  and the rows stop being emitted;
* the two F-157 rows retire when the basis-switch fix lands;
* membership below is computed from EACH RUN's own structural failures
  (⛔ not a roster baked in here), so the ledger empties BY ITSELF as the
  fixes land.  ``SM25_DEFERRED_CAVITY_COUNT`` is a pinned READOUT: when a
  fix lands it reddens (4 → 2 → 0), which is the readout lock doing its
  job — update the count here, once, in the same commit as the fix.

⛔ This is not an amnesty.  Every cavity NOT in this ledger must still show
a residual of exactly zero — that half of each consumer's assertion is
unchanged and zero-threshold ([[invalidation-blast-radius-must-be-scoped]]:
these locks are not held hostage by a defect they do not own).
"""
from __future__ import annotations

#: Both readings of the ONE deferred condition (answer-side basis switch part
#: way along a single support line): either the projected ring is buildable
#: and is not the zone, or the two bases make two adjacent projected supports
#: parallel so no ring can be built.
DEFERRED_PROJECTION_CODES = (
    "facts_projected_ring_is_not_the_converter_zone",
    "facts_projected_ring_unavailable",
)

#: ⛔ Owned by another lock, ⛔ not an amnesty.  ②-1d rework3 made a
#: producer-written ``registered_ring_loss`` fail-loud, so an honest sm25
#: substrate carries one such red per converter zone parked in an endcap-loss
#: cavity (F-153 form B, a known-unfixed defect — see the adjudication
#: above).  Those reds belong to the F-153 form B lock in
#: ``tests/test_o21d_exclusion_gap.py``, ⛔ not to the E2c/E3/E4/basis locks,
#: which must not be held hostage by a defect they do not own.
KNOWN_DEFECT_CODES = (
    "converter_zone_excluded_by_producer_written_ring_loss",
)

#: The pinned readout on the current honest sm25 substrate: 4 deferred
#: cavities = 2 × F-157 (``..._unavailable``) + 2 × F-153 form B
#: (``..._is_not_the_converter_zone``).  Every consumer asserts THIS number
#: from THIS module, so the two files cannot drift apart again.  When an
#: upstream fix lands this count drops and the pins redden — update it here,
#: once, in the same commit as the fix.
SM25_DEFERRED_CAVITY_COUNT = 4


def deferred_cavities(audit) -> set[tuple[str, str]]:
    """(view_id, cavity:<opaque>) for every projected-ring failure this batch
    defers.  Computed from THIS audit's own failures — ⛔ not a roster, so it
    empties by itself once the underlying defects are fixed."""
    return {(item.split(":")[1], f"cavity:{item.split(':')[3]}")
            for item in audit.structural_failures
            if item.startswith(DEFERRED_PROJECTION_CODES)}


def failures_not_from_deferred_cavities(audit) -> list[str]:
    """Every structural failure that is neither a deferred projected-ring
    failure nor owned by another lock's known-defect code.  This is the
    zero-threshold half: on the honest substrate it must be ``[]`` — no new
    unexplained failure may hide behind the declared deferrals."""
    deferred = deferred_cavities(audit)
    kept = []
    for item in audit.structural_failures:
        if item.startswith(KNOWN_DEFECT_CODES):
            continue
        parts = item.split(":")
        named = ((parts[1], f"cavity:{parts[3]}")
                 if len(parts) >= 4 and parts[2] == "cavity" else None)
        if named not in deferred:
            kept.append(item)
    return kept
