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

## R1/R2 (dispatch ②-1b-T): both doors gated, not just the write side

⭐⭐ Both :func:`write_facts_candidate` and :func:`read_facts_candidate` now
call :func:`src.agent.judge.gt_revisions.verify_as_signed_reproduction`
themselves -- WRITE runs it BEFORE the first byte touches disk (a failing
trio leaves zero residual files, not a half-written directory), READ runs it
AFTER parsing (so a file that was placed in this directory by ANY means --
not just through this module -- is re-verified every time it is read, not
merely trusted because it once passed on write).  A reader can therefore
never observe a trio that does not currently reproduce, regardless of how
the bytes got onto disk.

## R3 (dispatch ②-1b-T): no path/directory accessor is public -- structurally, not lexically

⛔ ``FACTS_STAGING_ROOT`` and the ``case -> Path`` helper are deliberately
NOT in ``__all__`` (renamed with a leading underscore).  This module's ONLY
public exits are :func:`write_facts_candidate` (takes three already-typed,
already-*matching* documents) and :func:`read_facts_candidate` (returns
three freshly-verified, already-typed documents) -- neither one hands a
caller a ``Path`` to this directory.

Why that closes off "拷目录" at the type/API level rather than by convention:
a future ``promote_gt_v3`` that wants this case's staged facts cannot get a
``Path`` it could pass to ``shutil.copytree`` from this module's public
surface -- the only thing this module will hand it is a
``tuple[AsMeasuredV1, RevisionsLedgerV1, AsSignedV1]``, already re-verified
by :func:`read_facts_candidate`. To land those facts under ``gt/<case>/facts/``
it has no choice but to re-serialize each object through the SAME canonical
functions this module itself uses (:func:`canonical_as_measured_bytes`,
:func:`canonical_revisions_bytes`, :func:`canonical_as_signed_bytes`) and
write fresh bytes -- i.e. exactly GLM's "读 + verify + 拷内容", never "拷
目录". This is not a grep-able name ban (⛔ the project's own precedent:
"词法匹配判无界输入的防线永远补不完"): nothing stops a determined
re-implementation from independently hardcoding the literal staging path
string and calling ``shutil.copytree`` without ever importing this module at
all -- no in-process API can prevent a caller from bypassing the module
entirely. What this change removes is the *sanctioned, discoverable* way to
get a directory handle from this module: the only names this module exports
that could produce or consume a copy-a-directory operation now do not exist.
Any promotion code that wants the shortcut has to manufacture the path
itself, in its own file, in the open -- not import it from here.

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
                           canonical_as_signed_bytes, canonical_revisions_bytes,
                           verify_as_signed_reproduction)
from .gt_schema import REPO_ROOT

#: ⭐ ②-1b-T R3: ⛔ deliberately just these two -- see the module docstring's
#: "R3" section for why no path/directory accessor is exported.
__all__ = ["write_facts_candidate", "read_facts_candidate"]

_FACTS_STAGING_ROOT = REPO_ROOT / "case_tests/test_baseline/gt_staging"


def _facts_staging_dir(case: str) -> Path:
    return _FACTS_STAGING_ROOT / case / "facts"


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def write_facts_candidate(case: str, as_measured: AsMeasuredV1,
                          revisions: RevisionsLedgerV1, as_signed: AsSignedV1) -> Path:
    """Write the trio into the staging root, atomically, one file at a time.

    ⭐⭐ ②-1b-T R1: runs :func:`src.agent.judge.gt_revisions.
    verify_as_signed_reproduction` FIRST, before a single byte is written.
    A trio that does not reproduce raises loudly and touches the filesystem
    not at all -- ⛔ never a half-written directory a caller has to notice
    and clean up.  "Landed in the staging root" and "passed the
    reproducibility gate" are now one atomic fact, not two the caller could
    forget to keep in sync.
    """
    verify_as_signed_reproduction(as_measured, revisions, as_signed)
    out_dir = _facts_staging_dir(case)
    _write_atomic(out_dir / "as_measured.json", canonical_as_measured_bytes(as_measured))
    _write_atomic(out_dir / "revisions.json", canonical_revisions_bytes(revisions))
    _write_atomic(out_dir / "as_signed.json", canonical_as_signed_bytes(as_signed))
    return out_dir


def read_facts_candidate(case: str) -> tuple[AsMeasuredV1, RevisionsLedgerV1, AsSignedV1]:
    """⭐⭐ ②-1b-T R2: re-verifies AFTER parsing, every call, regardless of who
    or what put the files there.  ⛔ NOT "trust it, it already passed on
    write" -- the write-side gate only proves what THAT write's caller
    handed in; this directory has no filesystem-level write protection
    (module docstring's opening paragraph), so a reader that skipped this
    check would be trusting an unauthenticated claim about what is on disk.
    """
    out_dir = _facts_staging_dir(case)
    as_measured = AsMeasuredV1.model_validate_json(
        (out_dir / "as_measured.json").read_bytes())
    revisions = RevisionsLedgerV1.model_validate_json(
        (out_dir / "revisions.json").read_bytes())
    as_signed = AsSignedV1.model_validate_json((out_dir / "as_signed.json").read_bytes())
    verify_as_signed_reproduction(as_measured, revisions, as_signed)
    return as_measured, revisions, as_signed
