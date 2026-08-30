"""②-1b-T-R R1 (GLM F-1): the ``case`` admission gate in
``src/agent/judge/gt_facts_staging.py``.

Cross-review (and independently, the orchestrator) found that
``_facts_staging_dir`` did ZERO validation on ``case`` before this rework:
``_FACTS_STAGING_ROOT / case / "facts"`` is a plain ``pathlib`` join, and
``pathlib`` has two well-known escape hatches -- ``..`` segments walk back up
the tree, and an absolute right operand DISCARDS the left one entirely
(``Path("/a") / "/b" == Path("/b")``). A single, completely legitimate call
to the PUBLIC API (``write_facts_candidate``/``read_facts_candidate``, verify
included) could therefore land in, or read from, ANYWHERE on the filesystem
-- including ``case_tests/test_baseline/gt/<case>/facts/``, the ANSWER ROOT
this module's own docstring says only ``promote_gt_v3`` may touch.

This file tests the fix: two independent layers in
``_facts_staging_dir``/``_validate_case_literal``.

    layer 1 (literal, on the STRING alone) -- rejects with a NAMED reason
    layer 2 (resolved-path containment)    -- backstops layer 1 for the one
                                               class of escape no amount of
                                               string inspection can see: a
                                               legal bare token that resolves
                                               through a PRE-EXISTING SYMLINK
                                               in the staging root to
                                               somewhere else entirely.

Every fixture below proves BOTH directions: the input is genuinely rejected
by the current code, AND the same input would genuinely have succeeded (or
would have needed a manual bypass of the new validation) before this
rework -- i.e. this test suite would have been RED against the pre-rework
module for every one of these inputs.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

import src.agent.judge.gt_facts_staging as gt_facts_staging
from src.agent.judge.as_measured import content_sha256
from src.agent.judge.gt_facts_staging import (FactsStagingCaseError,
                                              read_facts_candidate,
                                              write_facts_candidate)
from src.agent.judge.gt_revisions import RevisionsLedgerV1, derive_as_signed
from tests.test_gt_revisions_and_as_signed import _minimal_doc

# =========================================================================== #
# the two attacks GLM's F-1 and the orchestrator's independent repro named
# =========================================================================== #
def test_r1_relative_escape_from_the_rework_dispatch_is_rejected(tmp_path, monkeypatch):
    """GLM F-1 / orchestrator's ``case='../gt/sm25-L_anchor'``: a relative
    ``..`` segment walks the join back up and out of the staging root."""
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    case = "../gt/sm25-L_anchor"

    # ⭐ Prove the underlying pathlib behaviour first -- the raw join really
    # does resolve outside tmp_path -- so the negative assertion below is
    # proven to test the real defect class, not a made-up one.
    escaped = (tmp_path / case / "facts").resolve()
    assert tmp_path.resolve() not in escaped.parents and escaped != tmp_path.resolve(), (
        "sanity: the relative escape must actually land outside tmp_path when "
        "resolved via plain pathlib, or this fixture proves nothing")

    with pytest.raises(FactsStagingCaseError) as exc_info:
        gt_facts_staging._facts_staging_dir(case)
    assert "facts_staging_case_contains_a_path_separator" in str(exc_info.value)


def test_r1_absolute_path_from_the_rework_dispatch_is_rejected(tmp_path, monkeypatch):
    """GLM F-1 / orchestrator's ``case='/tmp/evil'``: an absolute right
    operand DISCARDS the staging root entirely under plain ``pathlib`` ``/``
    semantics (``Path("/a") / "/b" == Path("/b")``)."""
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    case = "/tmp/evil"

    # ⭐ Prove the underlying pathlib behaviour first: the staging root is
    # not merely escaped, it is not present in the joined path AT ALL.
    raw_join = tmp_path / case / "facts"
    assert not str(raw_join).startswith(str(tmp_path)), (
        "sanity: the absolute-path attack must actually discard the staging "
        "root via plain pathlib '/' semantics, or this fixture proves nothing")
    assert raw_join == pathlib.Path("/tmp/evil/facts")

    with pytest.raises(FactsStagingCaseError) as exc_info:
        gt_facts_staging._facts_staging_dir(case)
    assert "facts_staging_case_contains_a_path_separator" in str(exc_info.value)


# =========================================================================== #
# the edge tokens the rework dispatch explicitly asked for
# =========================================================================== #
@pytest.mark.parametrize("case, expected_reason", [
    ("", "facts_staging_case_empty"),
    (".", "facts_staging_case_is_a_navigation_token"),
    ("..", "facts_staging_case_is_a_navigation_token"),
    ("a/../../x", "facts_staging_case_contains_a_path_separator"),
    ("a\\evil", "facts_staging_case_contains_a_path_separator"),   # Windows separator
    ("C:\\evil", "facts_staging_case_contains_a_path_separator"),  # Windows drive form
    ("a\x00b", "facts_staging_case_has_illegal_characters"),       # embedded NUL
])
def test_r1_edge_tokens_are_rejected_with_a_named_reason(case, expected_reason, tmp_path, monkeypatch):
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    with pytest.raises(FactsStagingCaseError) as exc_info:
        gt_facts_staging._facts_staging_dir(case)
    assert expected_reason in str(exc_info.value)


def test_r1_edge_tokens_would_not_have_been_caught_by_pathlib_itself(tmp_path):
    """⭐ Self-proving: none of the edge tokens above raise on their own from
    plain ``pathlib`` construction -- MEASURED: not even the embedded NUL
    byte (``pathlib`` on this Python/platform builds the ``Path`` object
    fine; a NUL only ever surfaces as an OS-level error the first time
    something tries to actually open/stat it, and even ``Path.exists()``
    swallows that into a quiet ``False`` rather than raising). I.e. WITHOUT
    ``_validate_case_literal``, every one of these four tokens would have
    been silently accepted by ``_facts_staging_dir`` and turned into SOME
    path (correct or not) -- never a loud, named rejection. This is what
    makes "this door would have been red before the fix" true for this
    whole battery, not just asserted."""
    for case in ("", ".", "a/../../x", "a\x00b"):
        _ = tmp_path / case / "facts"   # plain pathlib join never objects
    # yet every one of them IS rejected, loudly and by name, by our own gate
    # (proven by test_r1_edge_tokens_are_rejected_with_a_named_reason above)


# =========================================================================== #
# ⭐⭐⭐ the THIRD escape this session found on its own (not named by GLM or
# the orchestrator): a symlink already sitting in the staging root, named by
# a case value that is a perfectly legal bare token
# =========================================================================== #
def test_r1_symlink_in_the_staging_root_escapes_layer_1_but_not_layer_2(tmp_path, monkeypatch):
    """⭐⭐⭐ Self-found third escape form: ``case="innocent_case"`` passes
    EVERY literal check (no separators, not ``..``, not absolute, matches
    the character class) -- it is layer 1's job to accept it. But if
    ``<staging_root>/innocent_case`` is itself a symlink to somewhere
    outside the root (planted by anything -- another process, a bad
    checkout, a prior bug), the resolved path escapes anyway. Layer 1
    CANNOT see this: the escape is not in the ``case`` string at all, it is
    in the pre-existing filesystem state the string happens to name. Only
    layer 2 (resolved-path containment) catches it.
    """
    outside = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    case = "innocent_case"

    # Prove layer 1 alone is satisfied -- this is the "would have been green"
    # half: if _facts_staging_dir only ran _validate_case_literal and
    # stopped there (i.e. layer 2 did not exist), this call would return the
    # symlinked-through path with no error at all.
    gt_facts_staging._validate_case_literal(case)  # must not raise

    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / case).symlink_to(outside, target_is_directory=True)

    with pytest.raises(FactsStagingCaseError) as exc_info:
        gt_facts_staging._facts_staging_dir(case)
    assert "facts_staging_case_escapes_root" in str(exc_info.value)
    assert str(outside) in str(exc_info.value)


def test_r1_bare_dot_shows_layer_1_catches_what_layer_2_alone_would_miss(tmp_path, monkeypatch):
    """⭐⭐ The OTHER direction of "两条都要" (both layers are independently
    necessary): ``case="."`` resolves to ``<root>/facts`` -- which IS still
    a descendant of the root, so layer 2 (resolved-path containment) alone
    would happily ACCEPT it. It is not a root escape; it is a silent
    collision -- every caller that ever passed ``"."`` would land in the
    exact same un-namespaced ``<root>/facts`` directory, defeating the
    entire point of a per-``case`` subdirectory. Only layer 1 (rejecting the
    literal navigation token) catches this; layer 2 structurally cannot,
    because nothing about it is actually outside the root.
    """
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)

    # Prove layer 2 alone would accept it (the "would have been green"
    # half): with layer 1 disabled, the resolved path is a genuine,
    # in-bounds descendant of the root -- layer 2 has nothing to object to.
    with pytest.MonkeyPatch.context() as mp2:
        mp2.setattr(gt_facts_staging, "_validate_case_literal", lambda case: None)
        accepted = gt_facts_staging._facts_staging_dir(".")
        assert accepted == tmp_path.resolve() / "facts"

    # With layer 1 restored (the actual current code), it is rejected:
    with pytest.raises(FactsStagingCaseError) as exc_info:
        gt_facts_staging._facts_staging_dir(".")
    assert "facts_staging_case_is_a_navigation_token" in str(exc_info.value)


def test_r1_symlink_escape_also_blocks_the_real_public_api(tmp_path, monkeypatch):
    """The same symlink escape, exercised through the actual public
    ``write_facts_candidate``/``read_facts_candidate`` entry points rather
    than the private helper directly -- proving the block reaches callers,
    not just the internal function."""
    outside = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    case = "innocent_case_2"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / case).symlink_to(outside, target_is_directory=True)

    as_measured = _minimal_doc()
    ledger = RevisionsLedgerV1(case=as_measured.case,
                              as_measured_content_sha256=content_sha256(as_measured),
                              revisions=[])
    as_signed = derive_as_signed(as_measured, ledger)

    with pytest.raises(FactsStagingCaseError):
        write_facts_candidate(case, as_measured, ledger, as_signed)
    assert not any(outside.iterdir()), "the escape must not have written anything outside the root"

    with pytest.raises(FactsStagingCaseError):
        read_facts_candidate(case)


# =========================================================================== #
# not misfired: a real, legitimate case name still works end to end
# =========================================================================== #
def test_r1_a_legitimate_case_name_still_writes_and_reads(tmp_path, monkeypatch):
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    as_measured = _minimal_doc()
    ledger = RevisionsLedgerV1(case=as_measured.case,
                              as_measured_content_sha256=content_sha256(as_measured),
                              revisions=[])
    as_signed = derive_as_signed(as_measured, ledger)
    write_facts_candidate("sm25-L_anchor", as_measured, ledger, as_signed)
    got_am, got_ledger, got_signed = read_facts_candidate("sm25-L_anchor")
    assert content_sha256(got_am) == content_sha256(as_measured)


def test_r1_the_named_attacks_never_touch_the_real_answer_root(monkeypatch):
    """Run the two named attacks against the REAL (unmocked) staging root
    and confirm the real answer root (``case_tests/test_baseline/gt/``) is
    untouched -- the actual scenario the rework dispatch is worried about,
    not just an isolated tmp_path stand-in."""
    real_root = pathlib.Path(__file__).resolve().parents[1] / "case_tests/test_baseline/gt"
    before = {p for p in real_root.rglob("facts") if p.is_dir()} if real_root.is_dir() else set()

    with pytest.raises(FactsStagingCaseError):
        gt_facts_staging._facts_staging_dir("../gt/sm25-L_anchor_INTRUSION_PROBE")
    with pytest.raises(FactsStagingCaseError):
        gt_facts_staging._facts_staging_dir("/tmp/o21bT_intrusion_probe")

    after = {p for p in real_root.rglob("facts") if p.is_dir()} if real_root.is_dir() else set()
    assert before == after
