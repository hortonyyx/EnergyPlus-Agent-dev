"""②-1b R1/R5: build the real facts-layer TRIO for ``sm25-L_anchor`` and write
it into the staging root (``case_tests/test_baseline/gt_staging/``).

Run once, by hand, to (re)generate the committed artefacts:

    python AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/build_sm25_facts_staging.py

``tests/test_gt_facts_staging_sm25.py`` re-derives the same three documents
and asserts they are byte-identical to what is on disk -- that test is the
actual reproducibility PROOF; this script is a one-shot producer, not a lock.
Before writing, the producer also runs the boundary-basis reconciliation gate
against the committed converter report and refuses E3/E4/E2c-style incomplete
populations.  This is the staging/走查接线; the permanent mutation locks live
in ``tests/test_boundary_condition_facts.py``.

The 5 changed DXF handles (13AD 13AC 13AF 160A 13AE) are the ones the
dispatch itself names (ledger §十: signed vs as-received, 916 entities with
the same handle set, exactly these 5 coordinates differ, ~6 mm max).  Which
handles to look at is therefore a given fact, not something this script
detects; what happens to EACH one -- is it a well-formed translate or does it
need an action kind this batch does not implement -- is computed by
``detect_translate_candidates``, not hand-typed.
"""
from __future__ import annotations

from pathlib import Path

from src.agent.judge.answer_compiler import reconcile_boundary_basis
from src.agent.judge.as_measured import build_as_measured, content_sha256
from src.agent.judge.gt_facts_staging import write_facts_candidate
from src.agent.judge.gt_revisions import (RevisionsLedgerV1,
                                          detect_translate_candidates,
                                          derive_as_signed,
                                          verify_as_signed_reproduction)
from src.agent.judge.tarch_converter_schema import ConversionReportV1

REPO_ROOT = Path(__file__).resolve().parents[4]
ANCHOR = REPO_ROOT / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
CONVERSION_REPORT = (
    REPO_ROOT
    / "case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json")

#: The 5 handles the dispatch's own DXF-level diff names (ledger §十).
CHANGED_HANDLES = ("13AD", "13AC", "13AF", "160A", "13AE")


def main() -> None:
    as_received = build_as_measured(ANCHOR / "sm25-L_t3_as_received.dxf",
                                    ANCHOR / "request_as_measured.json")
    signed = build_as_measured(ANCHOR / "sm25-L_t3.dxf", ANCHOR / "request.json")

    candidates = detect_translate_candidates(as_received, signed, CHANGED_HANDLES)
    assert len(candidates) == len(CHANGED_HANDLES), (
        f"expected one candidate per handle, got {len(candidates)} for "
        f"{len(CHANGED_HANDLES)} handles: {[c.id for c in candidates]}")

    ledger = RevisionsLedgerV1(
        case=as_received.case,
        as_measured_content_sha256=content_sha256(as_received),
        revisions=candidates)
    assert all(r.verdict == "unsigned" for r in ledger.revisions), (
        "this script must never sign a revision -- that is the signing "
        "flow's job (ledger §五 step 5), not a builder script's")

    as_signed = derive_as_signed(as_received, ledger)
    verify_as_signed_reproduction(as_received, ledger, as_signed)

    report = ConversionReportV1.model_validate_json(
        CONVERSION_REPORT.read_bytes())
    boundary_audit = reconcile_boundary_basis(as_signed, report)
    boundary_audit.assert_consistent()

    write_facts_candidate("sm25-L_anchor", as_received, ledger, as_signed)
    print(
        "wrote verified sm25-L_anchor facts candidate; "
        f"boundary_basis paired={boundary_audit.paired_edges} "
        f"zones={boundary_audit.accounted_converter_zones}/"
        f"{boundary_audit.converter_zones}")
    for record in candidates:
        action = record.candidate_action
        print(f"  {record.id}: {record.finding.check} "
              f"candidate_action={'none' if action is None else f'{action.field}{action.delta_0p1mm:+d}'}")


if __name__ == "__main__":
    main()
