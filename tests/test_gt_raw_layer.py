"""G1: the gt RAW layer is readable, and its reproduction gate has teeth.

The raw layer (per-zone-edge ``p1/p2/basis/thickness_m/offset_m/source_handles``
inside ``review/conversion_report.json``) sits OUTSIDE the human signature --
``tarch_review_bundle._RUNTIME_BUNDLE_FILES`` keeps it out of
``review_index.json`` on purpose.  Its only possible trust root is mechanical
reproduction from inputs that ARE signed, so these tests check the gate's
DISCRIMINATING POWER, not merely that it runs:

  * a single tampered ``thickness_m`` must be caught AND named (test_a3);
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


# --------------------------------------------------------------------------- #
# Degradation is explicit, never a silent pass
# --------------------------------------------------------------------------- #
def test_missing_signed_inputs_report_inputs_unavailable(tmp_path):
    root = _clone_gt(tmp_path)
    (root / CASE / "review" / "review_ack.json").unlink()
    verdict = verify_raw_layer_reproduction(CASE, gt_dir=root)
    assert verdict.status == "inputs_unavailable"
    assert verdict.reproduced is False
