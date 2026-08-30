"""R4/F-130: reading questions come from facts with unchanged scores."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from src.agent.judge.as_drawn.denominator import (
    denominator,
    denominator_from_facts,
)
from src.agent.judge.as_drawn.reading_grade import grade
from src.agent.judge.as_measured import AsMeasuredViewV1
from src.agent.judge.gt_facts_staging import read_facts_candidate
from src.agent.judge.gt_manifest import load_gt_tooling_config
from src.agent.judge.gt_schema import REPO_ROOT
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1
from src.agent.judge.tarch_normalize import run_p1_plan_view

SM25 = REPO_ROOT / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
SM24 = REPO_ROOT / "case_tests/test_baseline/gt_sources/sm24_anchor"
GT_CFG = REPO_ROOT / "src/configs/judge_gt.yaml"
VG_CFG = REPO_ROOT / "src/configs/correction.yaml"


def _freeze(items):
    return sorted(json.dumps(item, sort_keys=True, separators=(",", ":"))
                  for item in items)


def _perfect_reading(denominator_doc):
    face_lines = []
    unpaired = {}
    for index, target in enumerate(denominator_doc["targets"]):
        face_id = f"face-{index}"
        face_lines.append({
            "id": face_id,
            "constant_world_axis": target["axis"],
            "pos_m": target["const_m"],
            "runs_m": [[target["lo_m"], target["hi_m"]]],
            "edges_m": [],
        })
        unpaired[face_id] = {"reason": "fixture"}
    return {
        "observations": {"face_lines": face_lines, "opening_candidates": []},
        "hypotheses": {
            "pairs": [], "solid_band_walls": {},
            "unpaired_wall_faces": unpaired,
            "non_wall_face_lines": {}, "ambiguous_face_lines": {},
            "opening_types": {}, "opening_candidates": [],
        },
    }


@pytest.mark.parametrize("view_id", ["plan-F1", "plan-F2"])
def test_facts_adapter_reproduces_the_live_as_received_question_book_and_score(view_id):
    _measured, _ledger, signed = read_facts_candidate("sm25-L_anchor")
    request_path = SM25 / "request_as_measured.json"
    request = TarchConversionRequestV1.model_validate_json(request_path.read_text())
    view = next(item for item in signed.views if item.view_id == view_id)
    live = denominator(SM25 / "sm25-L_t3_as_received.dxf", request_path, view_id)
    frozen = denominator_from_facts(view, request)

    for key in ("targets", "allowed_not_required", "opening_targets"):
        assert _freeze(frozen[key]) == _freeze(live[key])
    assert frozen["ledger"] == live["ledger"]
    reading = _perfect_reading(live)
    assert grade(reading, frozen)["scores"] == grade(reading, live)["scores"]
    assert grade(reading, frozen)["by_verdict"] == grade(reading, live)["by_verdict"]


@pytest.mark.parametrize(
    "root,dxf_name",
    [(SM25, "sm25-L_t3.dxf"), (SM24, "source.dxf")],
)
def test_wall_band_cap_handles_are_exactly_the_direct_cap_map_population(root, dxf_name):
    """The only licensed facts-side use of jamb_cap_bands is proved here.

    ``_build_wall_bands`` partitions the direct cap maps; this real two-building
    lock ensures its carried handle union neither invents nor loses a member.
    It is evidence for an audit counter, not evidence that a band is a wall.
    """
    request = TarchConversionRequestV1.model_validate_json(
        (root / "request.json").read_text())
    tooling = load_gt_tooling_config(GT_CFG, VG_CFG)
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / dxf_name
        shutil.copy2(root / dxf_name, staged)
        for plan_view in request.plan_views:
            geo = run_p1_plan_view(staged, request, plan_view, tooling)
            direct = {
                handle for table in (geo.cap_handles_v, geo.cap_handles_h)
                for spans in table.values() for handles in spans.values()
                for handle in handles}
            through_bands = {handle for band in geo.wall_bands
                             for handle in band.cap_handles}
            assert through_bands == direct
            assert direct, f"fixture {root.name}/{plan_view.id} lost its cap stock"


def test_clearing_jamb_cap_bands_changes_only_its_audit_counter_never_targets():
    _measured, _ledger, signed = read_facts_candidate("sm25-L_anchor")
    request = TarchConversionRequestV1.model_validate_json(
        (SM25 / "request_as_measured.json").read_text())
    view = next(item for item in signed.views if item.view_id == "plan-F1")
    control = denominator_from_facts(view, request)
    raw = view.model_dump(mode="json")
    raw["converter_readouts"]["jamb_cap_bands"] = []
    without_bands = denominator_from_facts(AsMeasuredViewV1.model_validate(raw), request)

    for key in ("targets", "allowed_not_required", "opening_targets"):
        assert without_bands[key] == control[key]
    changed_ledger_keys = {
        key for key in control["ledger"]
        if control["ledger"][key] != without_bands["ledger"][key]}
    assert changed_ledger_keys == {"would_be_excluded_by_converter_length_rule"}
    assert control["ledger"]["would_be_excluded_by_converter_length_rule"] > 0
    assert without_bands["ledger"]["would_be_excluded_by_converter_length_rule"] == 0
