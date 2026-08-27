"""G1: the gt RAW layer is readable, and its reproduction gate has teeth.

The raw layer (per-zone-edge ``p1/p2/basis/thickness_m/offset_m/source_handles``
inside ``review/conversion_report.json``) sits OUTSIDE the human signature --
``tarch_review_bundle._RUNTIME_BUNDLE_FILES`` keeps it out of
``review_index.json`` on purpose.  Its only possible trust root is mechanical
reproduction from inputs that ARE signed, so these tests check the gate's
DISCRIMINATING POWER, not merely that it runs:

  * a single tampered ``thickness_m`` must be caught AND named (test_a3);
  * signed human-review inputs must not hide tampered G6 geometry (test_r2);
  * a drifted implementation must be reported as drift, never as a bad
    artefact (test_a4).

⚠️ A green ``test_a2`` alone proves nothing -- a gate that always returns
"reproduced" would pass it.  a3/a4 are what make a2 meaningful.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import src.agent.judge.gt_raw_layer as raw_layer
from src.agent.judge.gt_raw_layer import (load_gt_raw_layer,
                                          verify_raw_layer_reproduction)

CASE = "sm25-L_anchor"
GT_ROOT = Path("case_tests/test_baseline/gt")


def _clone_gt(tmp_path: Path) -> Path:
    """A writable copy of the case's gt bundle, so mutations never touch the answer."""
    root = tmp_path / "gt"
    root.mkdir()
    shutil.copytree(GT_ROOT / CASE, root / CASE)
    return root


def _report_path(root: Path) -> Path:
    return root / CASE / "review" / "conversion_report.json"


# --------------------------------------------------------------------------- #
# A1 -- the raw layer is readable and complete
# --------------------------------------------------------------------------- #
def test_a1_raw_layer_exposes_every_zone_edge():
    layer = load_gt_raw_layer(CASE)
    assert layer is not None
    assert len(layer.report.zones) == 29
    assert layer.edge_count() == 136
    assert layer.basis_histogram() == {"wall_axis": 90, "outer_skin": 46}
    assert layer.thickness_histogram() == {0.12: 78, 0.24: 58}
    # Every edge must carry the full as-drawn record, not just geometry.
    for raw in layer.edges():
        assert raw.basis in {"wall_axis", "outer_skin"}
        assert raw.thickness_m > 0 and raw.offset_m >= 0
        assert raw.source_handles, f"{raw.zone_id}[{raw.edge_index}] has no source handles"
        # outer skin offsets by the full thickness, a wall axis by half of it.
        expected = raw.thickness_m if raw.basis == "outer_skin" else raw.thickness_m / 2
        assert raw.offset_m == pytest.approx(expected)


def test_a1c_trust_root_is_explicit_and_never_silently_ok():
    """G1-c: the layer states that it is unsigned, and an un-run gate says so."""
    layer = load_gt_raw_layer(CASE)
    assert layer.trust.human_signed is False
    assert layer.trust.human_signed_reason == "not_in_review_index_file_set"
    # ⛔ absent verification must read as "not_attempted", never as a pass.
    assert layer.trust.reproduction is None
    assert layer.trust.reproduction_status == "not_attempted"
    assert layer.trust.trustworthy is False
    # the signed anchors it DOES have are surfaced
    assert layer.trust.signed_source_dxf_sha256 == (
        "1251f65153829c9c4502e401b7962a22172e3b636732d4ddf91a40a7b049f8b9")


def test_a1d_missing_case_returns_none(tmp_path):
    (tmp_path / "gt").mkdir()
    assert load_gt_raw_layer(CASE, gt_dir=tmp_path / "gt") is None


# --------------------------------------------------------------------------- #
# A2 -- the gate is green on an untouched tree
# --------------------------------------------------------------------------- #
def test_a2_reproduces_on_an_unmodified_tree():
    verdict = verify_raw_layer_reproduction(CASE)
    assert verdict.status == "reproduced", verdict.detail
    assert verdict.differing_pointers == ()


# --------------------------------------------------------------------------- #
# A3 -- discriminating power: one tampered field, caught and NAMED
# --------------------------------------------------------------------------- #
def test_a3_single_tampered_thickness_is_caught_and_named(tmp_path):
    root = _clone_gt(tmp_path)
    path = _report_path(root)
    report = json.loads(path.read_text(encoding="utf-8"))

    # Pick a concrete edge and prove the mutation really changed something
    # (a mutation that silently no-ops would make this test a false green).
    zone_index, edge_index = 0, 0
    edge = report["zones"][zone_index]["edges"][edge_index]
    assert edge["thickness_m"] == 0.12
    edge["thickness_m"] = 0.13
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))["zones"][0]["edges"][0]["thickness_m"] == 0.13

    verdict = verify_raw_layer_reproduction(CASE, gt_dir=root)
    assert verdict.status == "content_mismatch", verdict.detail
    # ⭐ named, not merely counted: the pointer must identify that exact edge.
    expected = f"/zones/{zone_index}/edges/{edge_index}/thickness_m"
    assert expected in verdict.differing_pointers, verdict.differing_pointers


def test_r2_signed_review_inputs_do_not_hide_tampered_g6_geometry(tmp_path):
    root = _clone_gt(tmp_path)
    path = _report_path(root)
    report = json.loads(path.read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in report["gates"]}
    face = gates["G6"]["evidence"]["views"][0]["evidence"]["near_threshold_faces"][0]
    recorded = face["area_m2"]
    face["area_m2"] = recorded + 0.001
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    verdict = verify_raw_layer_reproduction(CASE, gt_dir=root)
    expected = "/gates/G6/evidence/views/0/evidence/near_threshold_faces/0/area_m2"
    assert verdict.status == "content_mismatch", verdict.detail
    assert expected in verdict.differing_pointers, verdict.differing_pointers


def test_r4_duplicate_gate_id_is_a_content_mismatch(tmp_path):
    root = _clone_gt(tmp_path)
    path = _report_path(root)
    report = json.loads(path.read_text(encoding="utf-8"))
    report["gates"].append(dict(report["gates"][0]))
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    verdict = verify_raw_layer_reproduction(CASE, gt_dir=root)
    assert verdict.status == "content_mismatch", verdict.detail
    assert verdict.differing_pointers == ("/gates",)


# --------------------------------------------------------------------------- #
# A4 -- the two reds stay apart
# --------------------------------------------------------------------------- #
def test_a4_implementation_drift_is_not_reported_as_content_mismatch(tmp_path):
    root = _clone_gt(tmp_path)
    path = _report_path(root)
    report = json.loads(path.read_text(encoding="utf-8"))

    recorded = report["converter_sha256"]
    # drift it by exactly one hex digit
    flipped = ("1" if recorded[0] != "1" else "2") + recorded[1:]
    assert flipped != recorded
    report["converter_sha256"] = flipped
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    verdict = verify_raw_layer_reproduction(CASE, gt_dir=root)
    assert verdict.status == "implementation_drift", verdict.detail
    assert verdict.drifted_fingerprints == ("converter_sha256",)
    # ⛔ the artefact must NOT be blamed: no content verdict, no pointers.
    assert verdict.differing_pointers == ()


def test_r5_vg_implementation_drift_is_fatal(monkeypatch):
    current = raw_layer.compute_gt_implementation_hashes(raw_layer.REPO_ROOT)
    recorded = current.vg_implementation_sha256
    moved = ("1" if recorded[0] != "1" else "2") + recorded[1:]
    monkeypatch.setattr(
        raw_layer,
        "compute_gt_implementation_hashes",
        lambda _root: current.model_copy(update={"vg_implementation_sha256": moved}),
    )

    verdict = verify_raw_layer_reproduction(CASE)
    assert verdict.status == "implementation_drift", verdict.detail
    assert verdict.drifted_fingerprints == ("vg_implementation_sha256",)
    assert verdict.differing_pointers == ()


# --------------------------------------------------------------------------- #
# Degradation is explicit, never a silent pass
# --------------------------------------------------------------------------- #
def test_missing_signed_inputs_report_inputs_unavailable(tmp_path):
    root = _clone_gt(tmp_path)
    (root / CASE / "review" / "review_ack.json").unlink()
    verdict = verify_raw_layer_reproduction(CASE, gt_dir=root)
    assert verdict.status == "inputs_unavailable"
    assert verdict.reproduced is False


def test_tampered_signed_chain_is_rejected_before_reproduction(tmp_path):
    root = _clone_gt(tmp_path)
    path = root / CASE / "review" / "review_index.json"
    index = json.loads(path.read_text(encoding="utf-8"))
    index["files"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    verdict = verify_raw_layer_reproduction(CASE, gt_dir=root)
    assert verdict.status == "inputs_unavailable"
    assert "review_index_inventory_mismatch" in verdict.detail

    second_parent = tmp_path / "promoted-tamper"
    second_parent.mkdir()
    second_root = _clone_gt(second_parent)
    gt_path = second_root / CASE / "gt.json"
    document = json.loads(gt_path.read_text(encoding="utf-8"))
    document["generator"]["vg_implementation_sha256"] = "0" * 64
    gt_path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    verdict = verify_raw_layer_reproduction(CASE, gt_dir=second_root)
    assert verdict.status == "inputs_unavailable"
    assert "promoted_gt_signed_semantics_mismatch" in verdict.detail


# --------------------------------------------------------------------------- #
# F-111 -- the signed request lives in the case's own persistent directory
#
# Until 2026-08-27 ``find_signed_request`` rglob'd ``request.json`` out of
# ``AI_agent/logs/experiments`` -- a tree ``AI_agent/logs/README.md`` declares to
# be process traces that may be cleaned at any time.  sm24's signed request was
# not in that tree at all, so its gate read ``inputs_unavailable``; sm25's was
# there only as a leftover of the staging run that signed it.  The search now
# resolves BOTH signed inputs (source DXF + request) from ``gt_sources/<case>/``.
#
# ⛔ The tests below are deliberately split into "can it find the real one" and
# four flavours of "does the perfect path buy anything" -- because the point of
# the change is that it buys NOTHING.  Location moved; authority did not.
# --------------------------------------------------------------------------- #
SM24 = "sm24_anchor"
SOURCES_ROOT = Path("case_tests/test_baseline/gt_sources")
# A byte-identical copy of sm24's signed request also lives here -- this is
# where it was recovered from on 2026-08-27.  It is a tracked test fixture, not
# a log, so the path is a stable anchor, and its mere existence is what gives
# "only the case-owned root is consulted" below its teeth: any search face that
# reaches outside gt_sources/<case>/ finds this file and turns that test red.
# (Measured: widening the search to tests/fixtures reds four of these six.)
SM24_REQUEST_ELSEWHERE = Path("tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json")
# Same schema, same bundle family, DIFFERENT request (recomputes to de20e741...).
SM24_DECOY_REQUEST = Path("tests/fixtures/sm24_review/bundle_07_24/request_v3_calibrated.json")


def _signed_request_sha256(case: str) -> str:
    ack = json.loads((GT_ROOT / case / "review" / "review_ack.json").read_text(encoding="utf-8"))
    return ack["request_sha256"]


def _case_sources(tmp_path: Path, case: str) -> Path:
    """A writable stand-in for gt_sources/ carrying only the case's signed DXFs."""
    root = tmp_path / "gt_sources"
    (root / case).mkdir(parents=True)
    for dxf in sorted((SOURCES_ROOT / case).glob("*.dxf")):
        shutil.copyfile(dxf, root / case / dxf.name)
    return root


def test_f111_a_signed_request_resolves_from_the_case_owned_path():
    """1. The real file now lives with the case, and the gate finds it there."""
    for case in (CASE, SM24):
        expected = _signed_request_sha256(case)
        request = raw_layer.find_signed_request(case, expected)
        assert request is not None, f"{case}: signed request not resolved from gt_sources/"
        # ⭐ re-hash rather than read the declared field: same rule as production.
        assert raw_layer.compute_request_sha256(request) == expected
        assert (SOURCES_ROOT / case / "request.json").is_file()


def test_f111_b_sm24_is_no_longer_blocked_on_missing_inputs():
    """1'. sm24 escapes ``inputs_unavailable`` -- the F-111 symptom.

    ⚠️ It is deliberately NOT asserted to be green.  sm24's recorded
    ``converter_sha256`` / ``vg_implementation_sha256`` no longer match this
    tree, so the honest reading is ``implementation_drift`` until the case is
    re-signed by a human.  Asserting only "not inputs_unavailable" keeps this
    test correct on both sides of that re-signing.
    """
    verdict = verify_raw_layer_reproduction(SM24)
    assert verdict.status != "inputs_unavailable", verdict.detail


def test_f111_c_only_the_case_owned_root_is_consulted(monkeypatch, tmp_path):
    """3. Request absent from the case dir ⇒ loud ``inputs_unavailable``.

    ⭐ Discriminating power: a byte-identical copy of this exact request IS
    still on disk elsewhere in the repo, so a search face that reaches beyond
    the case-owned root -- the pre-2026-08-27 shape of this function, or any
    future "let's also look over there" widening -- turns this red.
    """
    assert SM24_REQUEST_ELSEWHERE.is_file()
    monkeypatch.setattr(raw_layer, "GT_SOURCES_ROOT", _case_sources(tmp_path, SM24))

    assert raw_layer.find_signed_request(SM24, _signed_request_sha256(SM24)) is None
    verdict = verify_raw_layer_reproduction(SM24)
    assert verdict.status == "inputs_unavailable", verdict.detail
    assert verdict.reproduced is False
    assert _signed_request_sha256(SM24) in verdict.detail


def test_f111_d_tampered_request_at_the_perfect_path_is_rejected(monkeypatch, tmp_path):
    """2. One changed field ⇒ refused, even with the signed stamp left intact.

    The file is at the canonical path, under the canonical name, and still
    *declares* the signed ``request_sha256``.  Only the recomputation decides.
    """
    root = _case_sources(tmp_path, SM24)
    expected = _signed_request_sha256(SM24)
    payload = json.loads(SM24_REQUEST_ELSEWHERE.read_text(encoding="utf-8"))
    assert payload["request_sha256"] == expected
    assert payload["metres_per_unit"] == 0.001
    payload["metres_per_unit"] = 0.002          # one field; the stamp is untouched
    target = root / SM24 / "request.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # ⛔ prove the mutation is not a no-op, or this test is a false green.
    mutated = raw_layer.TarchConversionRequestV1.model_validate_json(target.read_bytes())
    assert raw_layer.compute_request_sha256(mutated) != expected

    monkeypatch.setattr(raw_layer, "GT_SOURCES_ROOT", root)
    assert raw_layer.find_signed_request(SM24, expected) is None
    assert verify_raw_layer_reproduction(SM24).status == "inputs_unavailable"


def test_f111_e_same_shape_wrong_identity_request_is_rejected(monkeypatch, tmp_path):
    """4. Same-shape input: a genuine, well-formed, *different* signed request.

    Nothing about it is malformed -- it is a real request for the same case from
    the neighbouring review bundle, at the canonical path under the canonical
    name.  It is the wrong one, and only the content hash can say so.
    """
    root = _case_sources(tmp_path, SM24)
    expected = _signed_request_sha256(SM24)
    decoy = raw_layer.TarchConversionRequestV1.model_validate_json(SM24_DECOY_REQUEST.read_bytes())
    assert raw_layer.compute_request_sha256(decoy) != expected     # a real request...
    assert decoy.case == SM24                                       # ...for this very case
    shutil.copyfile(SM24_DECOY_REQUEST, root / SM24 / "request.json")

    monkeypatch.setattr(raw_layer, "GT_SOURCES_ROOT", root)
    assert raw_layer.find_signed_request(SM24, expected) is None
    assert verify_raw_layer_reproduction(SM24).status == "inputs_unavailable"


def test_f111_f_a_malformed_sibling_does_not_hide_the_real_request(monkeypatch, tmp_path):
    """Junk in the case dir must not shadow the genuine request.

    ``gt_sources/<case>/`` is a real working directory: it also holds
    manifest/source_map/conversion_report JSON, and a re-signing round can leave
    a half-written ``request*.json`` behind.  Neither may turn the signed
    request into ``inputs_unavailable``.  ⚠️ This locks tolerance, NOT the
    narrowness of the glob -- widening to ``*.json`` would still pass here.
    """
    root = _case_sources(tmp_path, SM24)
    expected = _signed_request_sha256(SM24)
    shutil.copyfile(SM24_REQUEST_ELSEWHERE, root / SM24 / "request.json")
    (root / SM24 / "request_broken.json").write_text("{not json", encoding="utf-8")
    shutil.copyfile(SOURCES_ROOT / SM24 / "manifest.json", root / SM24 / "manifest.json")

    monkeypatch.setattr(raw_layer, "GT_SOURCES_ROOT", root)
    request = raw_layer.find_signed_request(SM24, expected)
    assert request is not None
    assert raw_layer.compute_request_sha256(request) == expected


# --------------------------------------------------------------------------- #
# F-116 -- the F-111 lock's teeth follow FIXTURE INVENTORY, not the code path
#
# test_f111_c/d/e/f above all use SM24 as the case under test, narrowing
# GT_SOURCES_ROOT to a directory holding only its DXFs. That genuinely proves
# "reaching tests/fixtures/ buys nothing" -- SM24_REQUEST_ELSEWHERE is a real,
# byte-identical copy sitting there, so a resurrected fallback that searched it
# would be caught. It proves NOTHING about a resurrected fallback to
# AI_agent/logs/experiments/: SM24's signed request has ZERO copies there, so
# if such a branch existed, ran, and searched, it would still (correctly, for
# THIS case) come back empty -- indistinguishable on this fixture from the
# branch never having existed at all. That is exactly the "assert ... is None
# can't tell 'rejected' from 'never looked'" trap the dispatch calls out.
#
# Measured 2026-08-27 (re-verified with the production hash-recompute path,
# not text grep -- a file can *contain* a hash string, e.g. in review_ack.json,
# without being a request*.json that recomputes to it):
#
#   case (hash prefix)      gt_sources/   AI_agent/logs/   tests/fixtures/
#   sm25-L_anchor (d738d0ac)      1              4                0
#   sm24_anchor   (ae0fec08)      1              0                1
#
# The two cases' inventories are complementary. A lock built entirely on SM24
# is structurally blind in the logs/ direction; sm25 (CASE) is what gives that
# direction teeth.  ⭐ Gate ② below does not depend on picking the right case at
# all: it asserts the search touches no directory but the one case-owned root,
# which is true or false independent of what happens to be lying around.
# --------------------------------------------------------------------------- #
LOGS_EXPERIMENTS_ROOT = Path("AI_agent/logs")


def _count_matching_requests(root: Path, expected_sha256: str) -> int:
    """Mirrors find_signed_request's own matching rule exactly (recompute, tolerate junk)."""
    count = 0
    for candidate in root.rglob(raw_layer.SIGNED_REQUEST_GLOB):
        try:
            request = raw_layer.TarchConversionRequestV1.model_validate_json(candidate.read_bytes())
        except Exception:
            continue
        if raw_layer.compute_request_sha256(request) == expected_sha256:
            count += 1
    return count


def test_f116_0_the_fixture_inventory_table_above_is_not_stale():
    """⛔ Guards the guard: test_f116_a below only has teeth because sm25 has
    real inventory under AI_agent/logs/. If that inventory is ever cleaned up,
    this fails LOUDLY instead of test_f116_a silently losing its teeth."""
    assert _count_matching_requests(LOGS_EXPERIMENTS_ROOT, _signed_request_sha256(CASE)) == 4
    assert _count_matching_requests(LOGS_EXPERIMENTS_ROOT, _signed_request_sha256(SM24)) == 0
    assert _count_matching_requests(Path("tests/fixtures"), _signed_request_sha256(SM24)) == 1
    assert _count_matching_requests(Path("tests/fixtures"), _signed_request_sha256(CASE)) == 0


def test_f116_a_sm25_logs_direction_narrowing_has_teeth(monkeypatch, tmp_path):
    """① The sm25-case mirror of test_f111_c, for the direction SM24 is blind
    to. A resurrected "also fall back to AI_agent/logs/experiments/" leg would
    find one of the 4 real copies proven above and return non-None here --
    unlike the SM24 fixture, where the same mutation would still (wrongly)
    look green.
    """
    expected = _signed_request_sha256(CASE)
    monkeypatch.setattr(raw_layer, "GT_SOURCES_ROOT", _case_sources(tmp_path, CASE))

    assert raw_layer.find_signed_request(CASE, expected) is None
    verdict = raw_layer.verify_raw_layer_reproduction(CASE)
    assert verdict.status == "inputs_unavailable", verdict.detail
    assert expected in verdict.detail


def test_f116_b_tests_fixtures_direction_narrowing_still_has_teeth():
    """② Documents that the pre-existing test_f111_c already covers this
    direction (SM24_REQUEST_ELSEWHERE is real inventory under tests/fixtures/)
    -- named explicitly here so F-116's three-cell verification has an address
    for it rather than relying on a reader to notice it lives elsewhere."""
    assert SM24_REQUEST_ELSEWHERE.is_file()
    assert raw_layer.compute_request_sha256(
        raw_layer.TarchConversionRequestV1.model_validate_json(SM24_REQUEST_ELSEWHERE.read_bytes())
    ) == _signed_request_sha256(SM24)
    # test_f111_c is the actual lock for this direction; see its docstring.


def test_f116_c_no_directory_other_than_the_case_owned_root_is_ever_opened(monkeypatch, tmp_path):
    """③ Structural lock, not example-based: catches ANY widening, named or
    not -- including ones nobody has thought of yet, e.g. falling back to
    case_gt_dir(case)/review/ (the promoted review tree, which F-117 does NOT
    populate with request.json -- see gt_promotion.py), or widening the root to
    GT_SOURCES_ROOT.parent, or anything else. ①② prove specific historical
    fallbacks buy nothing; this proves no fallback of ANY shape was ever taken,
    by recording every directory pathlib.Path.glob()/.rglob() is invoked on
    during find_signed_request and asserting the set is exactly the one
    case-owned root -- independent of what fixtures happen to exist anywhere.

    ⚠️ Runs the search in TWO shapes, not one: with the real root (finds the
    request immediately) AND with a root narrowed to hold only the DXFs (finds
    nothing). A fallback branch reached only on a failed primary lookup -- the
    realistic shape for "backward compat" code, and exactly what mutation cell
    ① below adds -- is never entered, and so never recorded, if this test only
    ever exercises the already-succeeding path.
    """
    seen: list[Path] = []
    real_glob = Path.glob
    real_rglob = Path.rglob

    def recording_glob(self, pattern, *args, **kwargs):
        seen.append(self)
        return real_glob(self, pattern, *args, **kwargs)

    def recording_rglob(self, pattern, *args, **kwargs):
        seen.append(self)
        return real_rglob(self, pattern, *args, **kwargs)

    monkeypatch.setattr(Path, "glob", recording_glob)
    monkeypatch.setattr(Path, "rglob", recording_rglob)

    for case in (CASE, SM24):
        seen.clear()
        expected = _signed_request_sha256(case)
        raw_layer.find_signed_request(case, expected)
        assert seen == [raw_layer.case_signed_inputs_root(case)], ("real root", case, seen)

    for case in (CASE, SM24):
        narrowed = _case_sources(tmp_path / case, case)
        monkeypatch.setattr(raw_layer, "GT_SOURCES_ROOT", narrowed)
        seen.clear()
        expected = _signed_request_sha256(case)
        raw_layer.find_signed_request(case, expected)
        assert seen == [raw_layer.case_signed_inputs_root(case)], ("narrowed root", case, seen)
