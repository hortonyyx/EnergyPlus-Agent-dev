#!/usr/bin/env python3
"""G-c: re-emit BOTH staged facts trios after the S1 ladder landed.

⭐ WHY a re-emit is unavoidable: the ladder changes ``tarch_normalize``'s
bytes, so ``converter_sha256`` moves, and it changes the geometry three
strokes land on, so ``as_measured``'s content hash moves with it.  The trio
is a *derived* artefact -- ⛔ not a signed baseline -- and the dispatch
(§三之 5) requires it to come out again and still reproduce bit for bit.

⭐ The ledger comes out EMPTY, and it must be empty because the DETECTOR
produces no candidate, ⛔ not because anything was deleted here: this script
runs ``detect_translate_candidates`` and asserts the count it got.

Run:  python AI_agent/logs/experiments/2026-09-07a_Gc_snap_ladder/reemit_sm25_facts_staging.py
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.agent.judge.as_measured import build_as_measured, content_sha256  # noqa: E402
from src.agent.judge.gt_facts_staging import (read_facts_candidate,  # noqa: E402
                                              write_facts_candidate)
from src.agent.judge.gt_revisions import (RevisionsLedgerV1,  # noqa: E402
                                          derive_as_signed,
                                          detect_translate_candidates,
                                          verify_as_signed_reproduction)

CASE = "sm25-L_anchor"
ANCHOR = REPO / "case_tests/test_baseline/gt_sources" / CASE
#: the five handles the user ruled into scope 2026-08-28 (plan.md); the list is
#: an INPUT to the detector, ⛔ not an expected answer -- see the assert below.
CHANGED_HANDLES = ("13AD", "13AC", "13AF", "160A", "13AE")


def _reemit_sm24() -> None:
    """⭐ sm24 has to come out again too, and ⛔ for a different reason than
    sm25: its geometry does not move at all (that drawing has zero off-axis
    strokes -- measured), but ``AsMeasuredConverterReadoutsV1`` gained the
    ``axis_snap_arbitrations`` field, so the SERIALISED document changed and
    ``content_sha256`` with it.  Its ledger was already empty and stays empty.
    """
    anchor = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor"
    as_measured = build_as_measured(anchor / "source.dxf", anchor / "request.json")
    revisions = RevisionsLedgerV1(
        case="sm24_anchor",
        as_measured_content_sha256=content_sha256(as_measured), revisions=[])
    as_signed = derive_as_signed(as_measured, revisions)
    verify_as_signed_reproduction(as_measured, revisions, as_signed)
    write_facts_candidate("sm24_anchor", as_measured, revisions, as_signed)
    back_am, back_rev, _ = read_facts_candidate("sm24_anchor")
    assert content_sha256(back_am) == content_sha256(as_measured)
    assert len(back_rev.revisions) == 0
    print("sm24 as_measured content_sha256 =", content_sha256(as_measured))


def main() -> None:
    _reemit_sm24()
    as_measured = build_as_measured(ANCHOR / "sm25-L_t3_as_received.dxf",
                                    ANCHOR / "request_as_measured.json")
    signed_build = build_as_measured(ANCHOR / "sm25-L_t3.dxf",
                                     ANCHOR / "request.json")
    candidates = detect_translate_candidates(as_measured, signed_build,
                                             CHANGED_HANDLES)
    print(f"detect_translate_candidates -> {len(candidates)}")
    for record in candidates:
        print("   ", record.id, record.target.handle, record.verdict)
    revisions = RevisionsLedgerV1(
        case=CASE, as_measured_content_sha256=content_sha256(as_measured),
        revisions=list(candidates))
    as_signed = derive_as_signed(as_measured, revisions)
    verify_as_signed_reproduction(as_measured, revisions, as_signed)
    write_facts_candidate(CASE, as_measured, revisions, as_signed)

    back_am, back_rev, back_signed = read_facts_candidate(CASE)
    assert content_sha256(back_am) == content_sha256(as_measured)
    assert len(back_rev.revisions) == len(candidates)
    print("as_measured content_sha256 =", content_sha256(as_measured))
    print("revisions on disk          =", len(back_rev.revisions))
    print("re-read + verify           = OK")


if __name__ == "__main__":
    main()
