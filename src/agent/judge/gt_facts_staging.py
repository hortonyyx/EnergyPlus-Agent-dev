"""Where the facts-layer TRIO lives before it has a promotion path (dispatch
②-1b R5).

⛔ NOT ``case_tests/test_baseline/gt/<case>/facts/`` (that is the ANSWER ROOT;
only ``promote_gt_v3`` -- untouched by this dispatch -- may write there) and
⛔ NOT ``case_tests/test_baseline/gt_sources/<case>/`` (F-117: promotion is
the only writer there too, and ``revisions``/``as_signed`` are a different
KIND of thing from the raw signed inputs that root holds).  This is a THIRD,
brand-new directory with no existing write-protection discipline attached,
precisely because it holds nothing signed yet:

    case_tests/test_baseline/gt_staging/<case>/facts/
        as_measured.json
        revisions.json      -- ⛔ UNSIGNED here (every ``verdict`` is
                                "unsigned"); the signing flow (ledger §五
                                step 5) is what would ever populate a real
                                one
        as_signed.json      -- mechanically derived from the two above;
                                identical to as_measured plus a derivation
                                key while nothing is signed (no
                                ``drawing_error`` record exists to apply)

## The seam into promotion (dispatch R5's "接缝说明")

``promote_gt_v3`` (untouched by this dispatch) does not read this directory
today.  The intended hookup (ledger §八): once ``revisions.json`` here is
REPLACED by a genuinely signed one (ledger §五 step 5 -- a human judges each
``verdict``), promotion should additionally copy this staging case's three
files into ``gt/<case>/facts/`` alongside the five it already copies, AFTER
running :func:`src.agent.judge.gt_revisions.verify_as_signed_reproduction` as
a pre-promotion gate (ledger §八: "晋升前先跑...那道可复现门，不过不许晋
升"). That change lives in ``promote_gt_v3`` itself and is explicitly out of
this dispatch's scope (dispatch §〇#1, §四).

F-128 (promotion's rollback asymmetry: its ``except`` only cleans the ``gt/``
side, not ``gt_sources/``) is UNCHANGED by this staging root -- it is a
defect in ``promote_gt_v3``, not in anything this module writes, and this
dispatch does not touch it either (ledger §八: "顺带处理" -- named, deferred,
not silently dropped).
"""
from __future__ import annotations

from pathlib import Path

from .as_measured import AsMeasuredV1
from .as_measured import canonical_bytes as canonical_as_measured_bytes
from .gt_revisions import (AsSignedV1, RevisionsLedgerV1,
                           canonical_as_signed_bytes, canonical_revisions_bytes)
from .gt_schema import REPO_ROOT

__all__ = ["FACTS_STAGING_ROOT", "facts_staging_dir", "write_facts_candidate",
          "read_facts_candidate"]

FACTS_STAGING_ROOT = REPO_ROOT / "case_tests/test_baseline/gt_staging"


def facts_staging_dir(case: str) -> Path:
    return FACTS_STAGING_ROOT / case / "facts"


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def write_facts_candidate(case: str, as_measured: AsMeasuredV1,
                          revisions: RevisionsLedgerV1, as_signed: AsSignedV1) -> Path:
    """Write the trio into the staging root, atomically, one file at a time.

    ⛔ Does not itself run :func:`src.agent.judge.gt_revisions.
    verify_as_signed_reproduction` -- the caller is expected to have already
    proven the trio reproduces.  Conflating "is this a valid, reproducible
    trio" with "where do the bytes land" would make the write itself
    something a reader has to separately trust; keeping them apart means a
    reader can re-run the gate against exactly what is on disk.
    """
    out_dir = facts_staging_dir(case)
    _write_atomic(out_dir / "as_measured.json", canonical_as_measured_bytes(as_measured))
    _write_atomic(out_dir / "revisions.json", canonical_revisions_bytes(revisions))
    _write_atomic(out_dir / "as_signed.json", canonical_as_signed_bytes(as_signed))
    return out_dir


def read_facts_candidate(case: str) -> tuple[AsMeasuredV1, RevisionsLedgerV1, AsSignedV1]:
    out_dir = facts_staging_dir(case)
    as_measured = AsMeasuredV1.model_validate_json(
        (out_dir / "as_measured.json").read_bytes())
    revisions = RevisionsLedgerV1.model_validate_json(
        (out_dir / "revisions.json").read_bytes())
    as_signed = AsSignedV1.model_validate_json((out_dir / "as_signed.json").read_bytes())
    return as_measured, revisions, as_signed
