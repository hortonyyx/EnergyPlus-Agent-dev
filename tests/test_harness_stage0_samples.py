"""Connected, real-backed acceptance examples; no model or BIM tool execution."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.contracts import BuildingContractBundle, assert_result_applicable
from src.harness_contracts import EventLog, ModelBinding, RoleDefinition

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests/fixtures/harness_stage0"
CASES = ("reconstruction", "partial_inference", "full_inference", "mixed_inputs", "evidence_conflict", "simplification")


def read(path):
    return json.loads(path.read_text())


def examples(case):
    data = read(FIX / f"{case}.json")
    if case == "simplification":
        return [data["fine"],data["coarse"],data["real_fine_failure"]["sample"]]
    return [data]


def bundle(data):
    return BuildingContractBundle.model_validate_json(json.dumps(data))


def walk(value):
    yield value
    if isinstance(value,dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value,list):
        for child in value:
            yield from walk(child)


@pytest.mark.parametrize("case",CASES)
def test_six_samples_validate_and_reach_exact_saved_objects(case):
    for example in examples(case):
        parsed = bundle(example["building"])
        assert bundle(parsed.model_dump(mode="json")) == parsed
        roles = {r["role_id"]:RoleDefinition.model_validate_json(json.dumps(r)) for r in example["roles"]}
        for binding in example["model_bindings"]:
            assert ModelBinding.model_validate_json(json.dumps(binding)).role_id in roles
        for package,result in zip(parsed.evidence_packages,parsed.evidence_results):
            assert roles[package.role_id].read_only
            assert_result_applicable(package,result,"saved-v1")
            with pytest.raises(ValueError,match="stale"):
                assert_result_applicable(package,result,"changed-v2")
        if example["events"] is not None:
            EventLog.model_validate_json(json.dumps(example["events"]))
        saved = read(ROOT / example["saved_artifact"]["uri"])
        actual = {s["id"]:s for s in saved["spaces"]}
        for coverage in parsed.coverage:
            assert {o.id for o in coverage.actual_objects} <= actual.keys()
        # This independently reads the artifact; a plausible rationale cannot satisfy it.
        geometry = next(c for c in parsed.checks if c.category == "geometry")
        for object_id,values in geometry.after.value.items():
            assert values["height_m"] == actual[object_id]["height"]
            polygon = actual[object_id]["polygon"]
            area = abs(sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(polygon,polygon[1:]+polygon[:1]))) / 2
            assert values["area_m2"] == area > 0
        # Every content-addressed reference in these complete specimens resolves.
        for row in walk(example):
            if isinstance(row,dict) and row.get("kind") == "sha256":
                path = (ROOT / row["uri"]).resolve()
                assert path.is_relative_to(ROOT)
                assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_adapter_image_bytes_and_recovery_state_are_the_recorded_bytes():
    for case in ("reconstruction","partial_inference"):
        example = examples(case)[0]
        events = {e["event_id"]:e["payload"] for e in example["events"]["events"]}
        request = events["request"]
        encoded = request["final_request_body"]["value"]["messages"][1]["content"][0]["image_url"]["url"].split(",",1)[1]
        sent = base64.b64decode(encoded)
        assert hashlib.sha256(sent).hexdigest() == request["images"][0]["sent"]["sha256"]
        before = read(ROOT / events["inspect-write"]["persisted_state"]["uri"])
        after = read(ROOT / events["inspect-resume"]["persisted_state"]["uri"])
        assert before["applied_write_ids"] == []
        assert after["applied_write_ids"] == ["write-2"]
        assert events["write-applied"]["retry_event_id"] == "retry-write"
        assert events["settle-retry"]["settlement"]["actual"]["tokens"] is None
        assert events["settle-retry"]["settlement"]["actual"]["money_usd"] is None


def test_common_interfaces_are_used_by_reconstruction_and_inference():
    left,right = (examples(case)[0] for case in ("reconstruction","partial_inference"))
    for key in ("roles","model_bindings","events"):
        assert left[key] and right[key]
    for key in ("requirements","evidence","calculations","hypotheses","declarations","model_versions",
                "evidence_packages","evidence_results","floor_drafts","checks","normalizations","coverage"):
        assert left["building"][key] and right["building"][key]
    assert {e["payload"]["event_type"] for e in left["events"]["events"]} == {e["payload"]["event_type"] for e in right["events"]["events"]}


def test_sm25_normalization_uses_real_f2_target_and_persisted_snapshot():
    data = examples("reconstruction")[0]["building"]
    normalization = data["normalizations"][0]
    edit = normalization["edits"][0]
    assert edit["before_m"] == 4 and edit["after_m"] == 3.94
    assert edit["target"]["object_ref"] == {"kind":"boundary","id":"space/F2%3AO1/wall/2"}
    source = read(ROOT / examples("reconstruction")[0]["saved_artifact"]["uri"])
    for object_id,distance in ((edit["object_ref"]["id"],4),(edit["target"]["object_ref"]["id"],3.94)):
        wall = next(w for w in source["boundaries"] if w["id"] == object_id)
        assert all(abs(20-v[1]-distance) < 1e-9 for v in wall["vertices"])
    assert normalization["before"]["semantics"] == normalization["after"]["semantics"]
    for side in ("before","after"):
        artifact = read(FIX / f"artifacts/reconstruction/normalization_{side}.json")
        assert artifact["dimensions"] == normalization[side]["dimensions"]
        assert artifact["semantics"] == normalization[side]["semantics"]
    bad = copy.deepcopy(data)
    bad["normalizations"][0]["after"]["semantics"]["room_ids"].pop()
    with pytest.raises(ValidationError):
        bundle(bad)
    bad = copy.deepcopy(data)
    bad["normalizations"][0]["features"][0].update(classification="genuine_narrow",decision="preserve")
    with pytest.raises(ValidationError,match="preserved"):
        bundle(bad)


def test_changed_inherited_evidence_reaches_declarations_and_model_versions():
    for case in ("reconstruction","partial_inference"):
        example = examples(case)[0]
        demo = example["evidence_change_demo"]
        data = copy.deepcopy(example["building"])
        data["evidence"]["items"][0] = demo["after"]
        parsed = bundle(data)
        impact = parsed.evidence_impact_index()[demo["changed_evidence_id"]]
        assert set(impact["declaration_ids"]) == set(demo["affected_declaration_ids"])
        assert set(impact["model_version_ids"]) == set(demo["affected_model_version_ids"])
        assert impact["declaration_ids"] and impact["model_version_ids"]
        for declaration in parsed.declarations:
            assert "ev:observed" not in declaration.evidence_ids  # comes through inheritance


def test_partial_inference_preserves_actual_cross_floor_object_and_door_exception():
    sample = examples("partial_inference")[0]
    saved = read(ROOT / sample["saved_artifact"]["uri"])
    core = next(s for s in saved["spaces"] if s["id"] == "CORE_E")
    assert core["height"] == 27.6 and core["z_floor"] == 0
    parsed = bundle(sample["building"])
    assert parsed.declarations[0].scope.kind == "cross_floor_space"
    assert parsed.declarations[0].repetition.instances[1].exceptions["/doors/D_F2_W_01_CORE_S/pair"] is None
    assert not parsed.normalizations[0].edits
    assert parsed.normalizations[0].before == parsed.normalizations[0].after
    assert set(parsed.evidence.expanded_object_evidence()["space:CORE_E"]) >= {"ev:observed","ev:inferred","ev:simplified","ev:assumed"}


def test_fine_failure_cannot_pass_as_rationale_or_unapproved_coarse_merge():
    data = read(FIX / "simplification.json")
    fine,coarse = data["fine"],data["coarse"]
    assert fine["input_image"] == coarse["input_image"]
    assert fine["building"]["evidence"]["items"][0] == coarse["building"]["evidence"]["items"][0]
    assert fine["building"]["requirements"][0]["kind"] == "fidelity"
    assert coarse["building"]["requirements"][0]["kind"] == "simplification"
    assert coarse["building"]["coverage"][0]["coarse_merge"]
    failure = data["real_fine_failure"]["sample"]
    saved = read(ROOT / failure["saved_artifact"]["uri"])
    windows = [o["id"] for o in saved["openings"] if o["kind"] == "window" and "F1_N04" in o["space_ids"]]
    assert windows == ["F1_NORTH_GLASS_07","F1_NORTH_GLASS_08"]
    bad = copy.deepcopy(failure["building"])
    bad["coverage"][0].update(status="complete",open_issue_ids=[])
    with pytest.raises(ValidationError,match="failing check"):
        bundle(bad)
    bad = copy.deepcopy(coarse["building"])
    bad["requirements"][0]["kind"] = "fidelity"
    with pytest.raises(ValidationError,match="explicit user simplification"):
        bundle(bad)


def test_photo_and_mixed_inputs_keep_inference_and_provenance_honest():
    full = examples("full_inference")[0]
    assert "替代" in full["provenance"]["input_boundary"]
    assert "无图纸" in full["provenance"]["input_boundary"]
    assert full["building"]["calculations"][0]["evidence_ids"] == ["ev:assumed"]
    plan = json.loads(full["building"]["declarations"][0]["tool_call"]["payload"]["plan_json"])
    assert "真实总层数未知" in plan["assumptions"][0]
    mixed = bundle(examples("mixed_inputs")[0]["building"])
    evidence = mixed.evidence.expanded_object_evidence()["space:CORE_E"]
    assert {"ev:observed","ev:photo","ev:inferred"} <= set(evidence)
    assert len(mixed.evidence_packages[0].image_refs) == 2
    conflict = bundle(examples("evidence_conflict")[0]["building"]).evidence.conflicts[0]
    assert conflict.status == "resolved" and len(conflict.evidence_ids) == 2


def test_native_sol_view_ids_match_later_saved_view_records_and_original_pixels():
    prefix = ROOT / "AI_agent/logs/experiments/2026-10-01_partial_inference_developer_tests/run_61sol"
    mixed = examples("mixed_inputs")[0]["building"]
    for reference in mixed["evidence_packages"][0]["image_refs"]:
        assert reference["run_id"] == "run_61sol"
        record = read(prefix / "image_views" / (reference["reference"]["value"]+".json"))
        assert record["view_id"] == reference["reference"]["value"]
        assert record["image_sha256"] == reference["original_sha256"]
        assert hashlib.sha256((prefix/"images"/record["name"]).read_bytes()).hexdigest() == reference["original_sha256"]
        assert reference["coordinate_relation"]["referenced_space"] == "original_image_pixels"
        assert reference["coordinate_relation"]["relation"] == "identity"


def test_sample_generator_is_byte_deterministic_without_touching_history(tmp_path):
    path = ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage0/build_samples.py"
    spec = importlib.util.spec_from_file_location("stage0_samples_builder",path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generated = {}
    real_read,real_digest = module.read,module.digest
    def capture(path,value):
        target = (ROOT / path).resolve()
        assert target.is_relative_to(FIX)
        generated[path] = json.dumps(value,ensure_ascii=False,indent=2)+"\n"
        return path
    module.dump = capture
    module.read = lambda path:json.loads(generated[path]) if path in generated else real_read(path)
    module.digest = lambda path:hashlib.sha256(generated[path].encode()).hexdigest() if path in generated else real_digest(path)
    module.main()
    for relative,content in generated.items():
        assert (ROOT / relative).read_text() == content
