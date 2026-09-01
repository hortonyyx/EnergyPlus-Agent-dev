"""F-156 v3: regenerate the committed ``sm25-L_anchor`` facts trio.

WHY a rebuild is required at all (⛔ not a convenience):
``boundary_edges`` and ``boundary_ring_losses`` are DERIVED values that live
INSIDE ``as_measured`` / ``as_signed``, so they are covered by
``content_sha256``.  F-156 changes how a ring corner is derived and which ring
segments may carry an edge record at all -> the three committed documents
cannot stay byte-identical, and ``tests/test_gt_facts_staging_sm25.py::test_1``
compares them byte-for-byte against a fresh derivation.  Changing the algorithm
therefore REQUIRES redoing the baseline; it is not "just a new field".

Difference from the ②-1b builder
(``AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/``): that one calls
``boundary_audit.assert_consistent()``, i.e. it refuses to write unless the
reconciliation is completely clean.  After F-156 the reconciliation is NOT
completely clean and is not supposed to be: the two corridor cavities now
produce rings that, projected onto the answer's declared per-edge basis, still
differ from their zone by the answer-side ``outer_skin``<->``wall_axis`` basis
switch.  That residual is F-157's, explicitly out of F-156's scope.

So this builder keeps a gate, stated as a RULE rather than a list of cavities:
  * ⛔ any row mismatch  -> refuse to write;
  * ⛔ any structural failure whose code is NOT the projected-ring identity
    failure -> refuse to write.
The projected-ring identity failure is the ONE class this batch hands to F-157,
and it is named -- ⛔ never silently absorbed.

Run by hand:
    python AI_agent/logs/experiments/2026-09-01c_f156v3_baseline/rebuild_sm25_facts_staging.py
"""
from __future__ import annotations

from pathlib import Path

from src.agent.judge.answer_compiler import reconcile_boundary_basis
from src.agent.judge.as_measured import build_as_measured, content_sha256
from src.agent.judge.gt_facts_staging import write_facts_candidate
from src.agent.judge.gt_revisions import (RevisionsLedgerV1,
                                          derive_as_signed,
                                          detect_translate_candidates,
                                          verify_as_signed_reproduction)
from src.agent.judge.tarch_converter_schema import ConversionReportV1

REPO_ROOT = Path(__file__).resolve().parents[4]
ANCHOR = REPO_ROOT / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
CONVERSION_REPORT = (
    REPO_ROOT
    / "case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json")

CHANGED_HANDLES = ("13AD", "13AC", "13AF", "160A", "13AE")

#: The failure readings F-156 hands on to F-157.  Both are the SAME condition
#: -- the answer-side ``outer_skin``<->``wall_axis`` switch partway along one
#: support line -- seen from two distances: either the projected ring is
#: buildable and differs from the zone, or the two bases on one line make two
#: adjacent projected supports parallel so no ring can be built at all.
DEFERRED_STRUCTURAL_CODES = (
    "facts_projected_ring_is_not_the_converter_zone",
    "facts_projected_ring_unavailable",
)
DEFERRED_UNAVAILABLE_REASON = "adjacent_projected_support_lines_are_parallel"


def _named_cavity(failure: str) -> tuple[str, str] | None:
    """``<code>:<view_id>:cavity:<hex>[:...]`` -> ``(view_id, cavity_id)``."""
    parts = failure.split(":")
    if len(parts) < 4 or parts[2] != "cavity":
        return None
    return parts[1], f"{parts[2]}:{parts[3]}"


def main() -> None:
    as_received = build_as_measured(ANCHOR / "sm25-L_t3_as_received.dxf",
                                    ANCHOR / "request_as_measured.json")
    signed_source = build_as_measured(ANCHOR / "sm25-L_t3.dxf",
                                      ANCHOR / "request.json")
    candidates = detect_translate_candidates(
        as_received, signed_source, CHANGED_HANDLES)
    assert len(candidates) == len(CHANGED_HANDLES), (
        f"expected one candidate per handle, got {len(candidates)}")
    ledger = RevisionsLedgerV1(
        case=as_received.case,
        as_measured_content_sha256=content_sha256(as_received),
        revisions=candidates)
    assert all(record.verdict == "unsigned" for record in ledger.revisions), (
        "a builder script must never sign a revision")
    as_signed = derive_as_signed(as_received, ledger)
    verify_as_signed_reproduction(as_received, ledger, as_signed)

    report = ConversionReportV1.model_validate_json(
        CONVERSION_REPORT.read_bytes())
    audit = reconcile_boundary_basis(as_signed, report)
    # RULE (⛔ not a roster of cavity ids): a cavity may be unclean only if
    # this same run also reports that its PROJECTED ring is not its zone --
    # i.e. the F-157 residual is the cause.  Any failure naming any other
    # cavity, or naming no cavity at all, refuses the write.
    deferred_cavities = {
        _named_cavity(item) for item in audit.structural_failures
        if (item.startswith(DEFERRED_STRUCTURAL_CODES[0])
            or (item.startswith(DEFERRED_STRUCTURAL_CODES[1])
                and item.endswith(DEFERRED_UNAVAILABLE_REASON)))} - {None}
    unexpected = [item for item in audit.structural_failures
                  if _named_cavity(item) not in deferred_cavities]
    print(f"boundary audit: passed={audit.passed} "
          f"paired_edges={audit.paired_edges} "
          f"zones={audit.accounted_converter_zones}/{audit.converter_zones} "
          f"mismatches={len(audit.mismatches)}")
    for item in audit.structural_failures:
        print(f"  structural: {item}")
    for item in audit.exclusions:
        print(f"  exclusion: {item.view_id} {item.facts_cavity_id} "
              f"{item.converter_zone_id} evidence={item.evidence} "
              f"loss_reason={item.registered_loss_reason}")
    if audit.mismatches or unexpected:
        raise SystemExit(
            f"refusing to write: mismatches={len(audit.mismatches)} "
            f"unexpected_structural={unexpected}")

    write_facts_candidate("sm25-L_anchor", as_received, ledger, as_signed)
    print("wrote sm25-L_anchor facts trio")


if __name__ == "__main__":
    main()
