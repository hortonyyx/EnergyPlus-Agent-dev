"""Build offline acceptance examples. Never execute a provider or a BIM tool."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.contracts import BuildingContractBundle
from src.harness_contracts import EventLog, ModelBinding, RoleDefinition

FIX = ROOT / "tests/fixtures/harness_stage0"
SOURCES = FIX / "sources"
EXP = "AI_agent/logs/experiments/"
SM25 = EXP + "2026-10-01_opus_dev_sm25/"
SOL = EXP + "2026-10-01_partial_inference_developer_tests/run_61sol/"
ACCEPTED = EXP + "2026-10-01_voimatalo_door_revision/"
SAMPLE_CODE_COMMIT = "5bb10538"
SAMPLE_CODE_PATH = "scripts/tool_scripts/run_bim_agent.py"


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    # These specimens explicitly identify the frozen code commit. Its code
    # and dependency lock must still hash that commit's bytes, never
    # relabel current tools as historical code or rewrite the original samples.
    raw = (subprocess.check_output(["git", "show", f"{SAMPLE_CODE_COMMIT}:{path}"], cwd=ROOT)
           if str(path) in {SAMPLE_CODE_PATH, "uv.lock"} else (ROOT / path).read_bytes())
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    target = ROOT / path
    assert target.resolve().is_relative_to(FIX)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def artifact(case, name, value):
    return dump(f"tests/fixtures/harness_stage0/artifacts/{case}/{name}.json", value)


def blob(path, media_type="application/json"):
    return dict(kind="sha256", uri=path, media_type=media_type, sha256=digest(path))


def source(path, selector="/", source_kind="history"):
    return dict(source_id=path + "#" + selector, source_kind=source_kind,
                locator=selector, blob=blob(path))


def inline(value):
    return dict(kind="inline", value=value)


def missing(reason):
    return dict(kind="missing", reason=reason)


def obj(id, kind="space"):
    return dict(kind=kind, id=id)


def evidence_ref(run, id, sha, scheme="view_id"):
    return dict(run_id=run, reference=dict(scheme=scheme, value=id),
                original_sha256=sha, coordinate_relation=dict(
                    referenced_space="original_image_pixels", relation="identity"))


def quantity(value, unit="m"):
    return dict(value=value, unit=unit)


def calculation(id, object_ref, field, raw, converted, normalized, evidence_ids):
    values = [quantity(raw, "mm"), quantity(converted), quantity(normalized), quantity(normalized)]
    reasons = ["保留标注或明确假设的原值；来源见依据项", "毫米除以1000，确定性换算到米",
               "按记录的尺寸规整；无偏差时保持换算值", "离线样例保存值与规整值一致"]
    return dict(calculation_id=id, object_ref=object_ref, field_path=field, evidence_ids=evidence_ids,
                steps=[dict(stage=s, input=None if i == 0 else values[i-1], output=values[i], reason=reasons[i])
                       for i, s in enumerate(("raw", "converted", "normalized", "saved"))])


def roles(case):
    budget = dict(tokens=1200, money_usd="0.10", seconds="30", calls=1)
    definitions = [
        dict(role_id="coordinator", responsibilities=["核对版本、依据和保存结果，再应用声明"],
             tool_whitelist=[dict(tool_name="inspect_region", access="read"), dict(tool_name="save_declaration", access="write")],
             input_materials=[dict(name="task", media_type="application/json")],
             return_requirements=[dict(name="delivery", schema_ref="building_contracts_v1")], budget=budget),
        dict(role_id="local_observer", responsibilities=["只读回答局部问题，分别返回所见、解释和不确定项"],
             tool_whitelist=[dict(tool_name="inspect_region", access="read")], read_only=True,
             input_materials=[dict(name="evidence-package", media_type="application/json")],
             return_requirements=[dict(name="observations", schema_ref="localized_evidence_result_v1")], budget=budget),
    ]
    bindings = [dict(role_id=r["role_id"], default_model=dict(route_id="offline-fixture", model_alias="no-model-called"),
                     recommended_models=[dict(route_id="configurable-candidate", model_alias="not-selected")],
                     validated_scopes=[], failure_policy="stop_and_report") for r in definitions]
    return [RoleDefinition.model_validate_json(json.dumps(r)).model_dump(mode="json") for r in definitions], [ModelBinding.model_validate_json(json.dumps(b)).model_dump(mode="json") for b in bindings]


def demo_events(case, image_path, state_path, result):
    """A synthetic boundary trace; every byte-bearing reference resolves locally."""
    image = blob(image_path, "image/png")
    before_state = artifact(case,"operation_before",dict(operation_key="save-1",applied_write_ids=[],saved_artifact=blob(state_path),label="synthetic persisted operation ledger for recovery preflight"))
    after_state = artifact(case,"operation_after",dict(operation_key="save-1",applied_write_ids=["write-2"],saved_artifact=blob(state_path),label="synthetic persisted operation ledger after one application"))
    config_path = artifact(case, "request_configuration", dict(
        prompt="只读检查指定材料，区分所见、解释和不确定项。", parameters=dict(temperature=0.2, max_tokens=200),
        route=dict(model="no-model-called", provider="offline-fixture"),
        tools=[dict(type="function", function=dict(name="inspect_region", description="Read a supplied region", parameters=dict(type="object", properties={}))) ]))
    config = read(config_path)
    body = dict(model="no-model-called", messages=[dict(role="system", content=config["prompt"]),
               dict(role="user", content=[dict(type="image_url", image_url=dict(url="data:image/png;base64," + base64.b64encode((ROOT / image_path).read_bytes()).decode()))])],
               tools=config["tools"], **config["parameters"])
    versions = {k:dict(identifier=digest(p), evidence=source(p, source_kind="runtime")) for k,p in {
        "dependency_lock":"uv.lock", "prompt":config_path, "tool_definitions":config_path,
        "inference_parameters":config_path, "model_route":config_path}.items()}
    versions["code_commit"] = dict(identifier=SAMPLE_CODE_COMMIT, evidence=source(SAMPLE_CODE_PATH, source_kind="runtime"))
    versions["remote_model"] = dict(route_id="offline-fixture", remote_alias="no-model-called", alias_status="unverified")
    events = []

    def add(id, payload, child=False):
        events.append(dict(event_id=id, run_id=case, task_id=case + ("-observe" if child else "-main"),
                           parent_task=dict(kind="known", task_id=case+"-main") if child else dict(kind="root"),
                           sequence=len(events), occurred_at=dict(kind="known", value="2026-10-02T00:00:00Z"), payload=payload))

    add("dispatch", dict(event_type="external_coordinator_mcp", phase="dispatch", coordinator_task_id=case+"-main",
                          method="delegate", request_content=missing("外层CLI完整模型请求未获取；本事件为离线派工示范"),
                          result_content=inline(dict(task_id=case+"-observe"))))
    for name, purpose, child in [("primary", "primary_task", False), ("child", "child_task", True),
                                 ("summary", "context_summary", False), ("retry", "retry", False)]:
        add("reserve-"+name, dict(event_type="budget", action="reserve", reservation=dict(
            reservation_id=name, purpose=purpose, task_id=case+("-observe" if child else "-main"),
            amounts=dict(tokens=1200, money_usd="0.10", seconds="30", calls=1))), child)
    add("request", dict(event_type="adapter_request", adapter="openai-compatible-chat", final_request_body=inline(body),
        injected_content=[dict(request_location="/messages/0/content", content=inline(config["prompt"]), source=source(config_path, "/prompt", "runtime"))],
        images=[dict(original=image, sent=image, request_reference="/messages/1/content/0/image_url/url")],
        parameters=dict(requested=config["parameters"], provider_report=dict(kind="reported", values=dict(temperature=0.2)),
                        effect=dict(kind="unverified", reason="离线示范未向任何服务发送；报告值仅为测试数据")), versions=versions), True)
    add("response", dict(event_type="model_response", request_event_id="request", visible_text=["返回局部观察。此句是离线示范。"],
        tool_calls=[dict(call_id="read-1", tool_name="inspect_region", full_arguments=dict(question=case))],
        thinking=[dict(kind="public_content", content="接口公开内容的示范占位"),dict(kind="summary", summary="服务摘要的示范占位"),
                  dict(kind="reported_token_count", tokens=7),dict(kind="signature", signature="opaque-test-signature")],
        usage=dict(kind="reported", raw_usage=dict(prompt_tokens=100, completion_tokens=20)), raw_response=inline(dict(fixture=True))), True)
    add("read", dict(event_type="tool_execution", call_id="read-1", tool_name="inspect_region", full_arguments=dict(question=case),
                     raw_result=inline(result), shown_result=inline(dict(summary="精简返回，原返回仍完整保留", package_id=result["package_id"])),
                     repeatability="read_only", outcome="succeeded"), True)
    add("settle-child", dict(event_type="budget", action="settle", settlement=dict(reservation_id="child",
        actual=dict(tokens=120, money_usd="0.01", seconds="1", calls=1), usage=dict(kind="reported", raw_usage=dict(prompt_tokens=100, completion_tokens=20)),
        cost=dict(kind="reported", usd="0.01"))), True)
    add("write-unknown", dict(event_type="tool_execution", call_id="write-1", tool_name="save_declaration", full_arguments=dict(artifact=state_path),
        raw_result=missing("传输超时，执行结果不明"), shown_result=missing("没有收到返回"), repeatability="non_idempotent_write", outcome="unknown", operation_key="save-1"))
    add("timeout", dict(event_type="run_lifecycle", action="timeout", reason="离线故障注入", partial_artifacts=[blob(state_path)]))
    add("inspect-write", dict(event_type="state_inspection", purpose="unknown_write_recovery", target_event_id="write-unknown", persisted_state=blob(before_state), conclusion="not_applied"))
    add("retry-write", dict(event_type="run_lifecycle", action="retry", reason="已读取保存状态，确认该操作尚未执行", retry_of_event_id="write-unknown", attempt=2, state_inspection_event_id="inspect-write"))
    add("write-applied", dict(event_type="tool_execution", call_id="write-2", tool_name="save_declaration", full_arguments=dict(artifact=state_path),
        raw_result=inline(dict(artifact=state_path)), shown_result=inline(dict(saved=True)), repeatability="non_idempotent_write", outcome="succeeded", operation_key="save-1", applied_write_id="write-2", retry_event_id="retry-write"))
    add("settle-retry", dict(event_type="budget", action="settle", settlement=dict(reservation_id="retry", actual=dict(seconds="1", calls=1),
        usage=dict(kind="missing", reason="示范服务未返回usage，不计为0"), cost=dict(kind="estimated_upper_bound", usd="0.10", reason="保留本次预留上界，非账单"))))
    add("remove", dict(event_type="context", action="remove_image", reason="当前窗口移出旧图，原件保留", image=image))
    summary_path = artifact(case, "summary", dict(requirements="保留样例要求", source_version="saved-v1", evidence_refs=[image], unresolved=["真实模型待验"]))
    add("compact", dict(event_type="context", action="compact", reason="离线压缩格式示范", summary=blob(summary_path), replaced_event_ids=["response", "read"]))
    add("retrieve", dict(event_type="context", action="retrieve_image", reason="核对局部结论需重新取得同一图", image=image, removal_event_id="remove"))
    add("failure", dict(event_type="run_lifecycle", action="failure", reason="示范进程中断", failure_stage="delivery", partial_artifacts=[blob(state_path)]))
    add("inspect-resume", dict(event_type="state_inspection", purpose="resume", target_event_id="failure", persisted_state=blob(after_state), conclusion="safe_to_resume"))
    add("resume", dict(event_type="run_lifecycle", action="resume", reason="核对已保存文件及已执行一次的写入记录后续接，不重复执行save-1", state_inspection_event_id="inspect-resume", checkpoint=blob(after_state), partial_artifacts=[blob(state_path)]))
    add("cancel", dict(event_type="run_lifecycle", action="cancel", reason="演示主动停止并交付已有材料", partial_artifacts=[blob(state_path)]))
    add("return", dict(event_type="external_coordinator_mcp", phase="return", coordinator_task_id=case+"-main", method="delegate",
                       request_content=missing("外层CLI完整请求未获取"), result_content=inline(result)))
    add("usage-summary", dict(event_type="run_usage_summary",usage=dict(kind="missing",reason="本例没有真实运行，用量仅在单条格式示范中出现"),
                              raw_summary=missing("没有真实账单或运行回执"),notes=["不把单条示范用量汇总成实际费用"]))
    return EventLog.model_validate_json(json.dumps(dict(mode="complete", events=events,
                                      budget_limit=dict(tokens=4800, money_usd="0.40", seconds="120", calls=4)))).model_dump(mode="json")


def semantics(model, ids):
    """Copy a scoped inventory, never infer new geometry or connectivity."""
    openings = [o for o in model["openings"] if set(o["space_ids"]) & set(ids)]
    return dict(floor_ids=sorted({s["floor_id"] for s in model["spaces"] if s["id"] in ids}),
        wall_ids=[w["id"] for w in model["boundaries"] if w["geometry_type"] == "wall" and w["space_id"] in ids],
        room_ids=ids,
        openings=[dict(object_kind="window" if o["kind"] == "window" else "opening", opening_id=o["id"],
            host_ids=[o["host_boundary_id"]], p1=o["vertices"][0][:2], p2=o["vertices"][1][:2],
            z_range=[min(v[2] for v in o["vertices"]), max(v[2] for v in o["vertices"])]) for o in openings],
        connectivity=[dict(connection_id=c["opening_id"], object_ids=(c["space_ids"] + ["exterior"])[:2])
                      for c in model["connections"] if set(c["space_ids"]) & set(ids)])


def base_bundle(case, *, image_path, native_run, saved_path, selected_ids, requirement, observed,
                inferred, raw_mm, field, value_m, scope, tool_call, repetition=None, coarse=False):
    """A connected excerpt, with a persisted artifact and exact native IDs."""
    saved = read(saved_path)
    refs = [obj(id) for id in selected_ids]
    view = evidence_ref(native_run, "view_0001", digest(image_path))
    # These are NEW offline records, not claimed historical tool calls.
    claim = evidence_ref(case + "-offline", "claim_0001", digest(image_path), "claim")
    inference = evidence_ref(case + "-offline", "inference_001", digest(image_path), "record_inference")
    items = [dict(evidence_id="ev:observed", kind="observation", statement=observed, source_refs=[view]),
             dict(evidence_id="ev:inferred", kind="inference", statement=inferred, source_refs=[inference]),
             dict(evidence_id="ev:simplified", kind="simplification", statement="按本样例明确要求选择表达粒度；只核所列对象", source_refs=[claim], requirement_ids=["req:detail"]),
             dict(evidence_id="ev:assumed", kind="assumption", statement="缺少实测室内资料；非直接可见的建筑用途或尺寸须留待确认", source_refs=[inference])]
    declaration = dict(declaration_id="decl:main", scope=scope, tool_call=tool_call,
        field_partition=dict(model_declared=["/declaration/geometry", "/declaration/source_refs"], code_expanded=["/saved/spaces", "/saved/opening_hosts", "/saved/connections"]),
        evidence_ids=["ev:inferred", "ev:simplified"], requirement_ids=["req:detail"],
        hypothesis_ids=["hyp:choice", "hyp:relation", "hyp:function"], repetition=repetition, declared_object_refs=refs)
    version = dict(model_version_id="saved-v1", source_model_sha256=saved.get("source_model_sha256", digest(saved_path)),
                   artifact_sha256=digest(saved_path), declaration_ids=["decl:main"])
    checks = [dict(check_id="check:"+category, category=category, status="passed", involved_objects=refs,
        evidence_ids=["ev:observed", "ev:inferred"], suggested_action=dict(kind="no_action", description="此项只核已保存片段；不代表整楼质量或推断真实"),
        tolerance=None, before=dict(value=dict(requested_objects=selected_ids)), after=dict(value=dict(saved_objects=selected_ids)),
        saved_verification=dict(model_version_id="saved-v1", artifact_sha256=digest(saved_path), inspected_objects=refs))
        for category in ("geometry", "topology", "coverage")]
    selected_spaces = [s for s in saved["spaces"] if s["id"] in selected_ids]
    assert {s["id"] for s in selected_spaces} == set(selected_ids)
    areas = {}
    for space in selected_spaces:
        polygon = space["polygon"]
        area = abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(polygon,polygon[1:]+polygon[:1]))) / 2
        assert area > 0 and space["height"] > 0
        areas[space["id"]] = dict(area_m2=area,height_m=space["height"])
    selected_openings = [o for o in saved["openings"] if set(o["space_ids"]) & set(selected_ids)]
    assert all(o["host_boundary_id"] in {b["id"] for b in saved["boundaries"]} for o in selected_openings)
    checks[0].update(before=dict(value="片段多边形面积和高度为正"),after=dict(value=areas),suggested_action=dict(kind="no_action",description="已读取保存片段核对正面积与高度；未执行整案几何检查"))
    checks[1].update(before=dict(value="片段内已声明开口的宿主必须在保存边界表中"),after=dict(value=dict(opening_ids=[o["id"] for o in selected_openings],all_declared_hosts_exist=True)),suggested_action=dict(kind="no_action",description="只核已声明宿主引用；空开口片段不等于建筑连通可用"))
    package = dict(package_id="package:local", task_id=case+"-observe", role_id="local_observer",
        question="核对指定原图区域，分开返回可见事实、建筑解释和不确定项。不得修改模型。",
        known_evidence_ids=["ev:observed"], image_refs=[view], source_model_version_id="saved-v1",
        budget_reservation_id="budget:local-observer")
    with Image.open(ROOT / image_path) as image_file:
        width, height = image_file.size
    result = dict(package_id=package["package_id"], task_id=package["task_id"], based_on_source_model_version_id="saved-v1",
        directly_seen=[dict(observation_id="seen:1", statement=observed, location=dict(image_ref=view, box_original_pixels=[0,0,width,height]))],
        interpretations=[dict(interpretation_id="interpret:1", statement=inferred, based_on_observation_ids=["seen:1"], confidence="low")],
        uncertain=[dict(uncertainty_id="unknown:1", statement="局部图片不能证明全部室内隔断；样例结论须按来源范围解读", related_observation_ids=["seen:1"])])
    draft = copy.deepcopy(declaration)
    draft.update(declaration_id="decl:floor-draft", scope=dict(kind="floor", ids=[saved["spaces"][0]["floor_id"]]), repetition=None)
    bundle = dict(case_id=case, requirements=[dict(requirement_id="req:detail", kind="simplification" if coarse else "fidelity", statement=requirement, target_objects=refs)],
        evidence=dict(items=items, templates=[dict(template_id="template:local", evidence_ids=["ev:observed", "ev:assumed"])],
                      groups=[dict(group_id="group:local", members=refs, template_ids=["template:local"], evidence_ids=["ev:inferred", "ev:simplified"])],
                      bindings=[dict(object_ref=o, group_ids=["group:local"]) for o in refs], conflicts=[]),
        calculations=[calculation("calc:dimension", refs[0], field, raw_mm, raw_mm/1000, value_m,
                                  ["ev:assumed"] if case == "full_inference" else ["ev:observed"])],
        hypotheses=[dict(hypothesis_id="hyp:"+kind, kind=typ, statement=statement, object_refs=refs if len(refs)>1 else refs+[obj(saved["spaces"][0]["floor_id"], "floor")],
                         requirement_ids=["req:detail"], evidence_ids=["ev:inferred", "ev:simplified"])
                    for kind,typ,statement in [("choice","design_choice",requirement), ("relation","spatial_relation",inferred),
                                               ("function","functional_requirement","阶段0用途需求示范：办公空间；具体用途仍按建筑语境推断")]],
        declarations=[declaration], model_versions=[version],
        budget_ledger=dict(
            total_limit=dict(tokens=1200, seconds="30", calls=1),
            reservations=[dict(
                reservation_id="budget:local-observer",
                purpose="child_task",
                amounts=dict(tokens=1200, seconds="30", calls=1),
                task_id=case+"-observe",
            )],
        ),
        evidence_packages=[package], evidence_results=[result],
        floor_drafts=[dict(floor_id=draft["scope"]["ids"][0], based_on_source_model_version_id="saved-v1", proposed_declaration=draft, open_questions=["仅定接口，不调用楼层出稿者"])],
        checks=checks, normalizations=[], coverage_issues=[],
        coverage=[dict(coverage_id="coverage:detail", requirement_id="req:detail", choice_hypothesis_id="hyp:choice", saved_model_version_id="saved-v1",
                       actual_objects=refs, check_ids=[c["check_id"] for c in checks], status="complete", coarse_merge=coarse)])
    return bundle


def add_normalization(case, bundle, saved_path, first_id, target_id, before_m, after_m):
    """Persist a proposed dimension snapshot; do not generate or revise a BIM."""
    model = read(saved_path)
    ids = sorted({o["id"] for declaration in bundle["declarations"] for o in declaration["declared_object_refs"] if o["kind"]=="space"})
    sem = semantics(model, ids)
    def dimensions(value):
        return [dict(object_ref=obj(first_id,"boundary"), field_path="/derived/distance_from_north_m", value_m=value),
                dict(object_ref=obj(target_id,"boundary"), field_path="/derived/distance_from_north_m", value_m=after_m)]
    snap = dict(model_version_id="snapshot-before", semantics=sem, dimensions=dimensions(before_m))
    before_path = artifact(case, "normalization_before", dict(label="stage0 scoped snapshot copied from saved BIM; dimension derived from cited drawing calibration", source=source(saved_path), **snap))
    after_path = artifact(case, "normalization_after", dict(label="stage0 proposed saved dimension snapshot, NOT an executed BIM correction", source=source(before_path),
        model_version_id="snapshot-after", semantics=sem, dimensions=dimensions(after_m)))
    for version_id, path in [("snapshot-before", before_path), ("snapshot-after", after_path)]:
        bundle["model_versions"].append(dict(model_version_id=version_id, source_model_sha256=digest(path), artifact_sha256=digest(path), declaration_ids=[d["declaration_id"] for d in bundle["declarations"]]))
    tolerance = dict(origin="model_ruling", value=.06, unit="m", source_id="2026-10-02 documented sm25 ruling; specimen only",
                     reason="已记录6厘米差异，选既有3.94米线；不是通用容差或自动最小值策略")
    before = dict(model_version_id="snapshot-before", artifact_sha256=digest(before_path), semantics=sem, dimensions=dimensions(before_m))
    after = dict(model_version_id="snapshot-after", artifact_sha256=digest(after_path), semantics=sem, dimensions=dimensions(after_m))
    bundle["normalizations"] = [dict(proposal_id="normalize:strip", check_ids=["check:geometry"], tolerance=tolerance,
        features=[dict(feature_id="strip:6cm", classification="drawing_noise", decision="normalize", reason="sm25既有跨层接触细条的已记录判断"),
                  dict(feature_id="counterexample:narrow-passage", classification="genuine_narrow", decision="preserve", reason="独立反例：若窄部是真实通道，即使小于容差也保留")],
        edits=[dict(operation="set_dimension", feature_id="strip:6cm", object_ref=obj(first_id,"boundary"), field_path="/derived/distance_from_north_m", before_m=before_m, after_m=after_m,
                    target=dict(object_ref=obj(target_id,"boundary"), field_path="/derived/distance_from_north_m", coordinate_m=after_m, selection_reason="原生wall对应图纸P_off16/P_top；该字段是从北外边20米减wall y得到的派生尺寸，不是源模型原生字段；对齐已有线，不取均值或系统选较小值"))],
        before=before, after=after)]


def wrap(case, bundle, image_path, saved_path, provenance, *, include_events=True):
    parsed = BuildingContractBundle.model_validate_json(json.dumps(bundle))
    role_defs, bindings = roles(case)
    changed = copy.deepcopy(bundle)
    changed["evidence"]["items"][0]["statement"] += "【阶段0替换示范：重新观察后改判，原有声明需重审】"
    impact = parsed.evidence_impact_index()["ev:observed"]
    local_records = artifact(case,"new_evidence_records",dict(label="new offline records using existing claim/record_inference identifier schemes; no tool was executed",
        records=[row for row in bundle["evidence"]["items"] if row["kind"] != "observation"]))
    return dict(case_id=case, fixture_kind="offline_contract_specimen_not_a_model_run", provenance=provenance,
        saved_artifact=blob(saved_path), input_image=blob(image_path, "image/png"),
        new_evidence_records=blob(local_records),
        evidence_record_origin="view_id有历史记录时沿用；case-offline命名空间的claim/inference为新建离线记录，不冒充历史工具调用",
        roles=role_defs, model_bindings=bindings, building=parsed.model_dump(mode="json"),
        events=demo_events(case, image_path, saved_path, bundle["evidence_results"][0]) if include_events else None,
        evidence_change_demo=dict(changed_evidence_id="ev:observed", before=bundle["evidence"]["items"][0], after=changed["evidence"]["items"][0],
                                  affected_declaration_ids=impact["declaration_ids"], affected_model_version_ids=impact["model_version_ids"]))


def main():
    sm = read("tests/fixtures/harness_stage0/sources/sm25_cross_floor_excerpt.json")
    partial = read("tests/fixtures/harness_stage0/sources/partial_inference_excerpt.json")
    sm_path = SM25 + "candidate_04/source_model.json"
    sm_image = SM25 + "images/1f_view.png"
    recon = base_bundle("reconstruction", image_path=sm_image, native_run=sm["historical_identity"], saved_path=sm_path,
        selected_ids=["F1:O2", "F1:O3", "F2:O1"], requirement="本片段保留原图实体隔墙、三间房和两层关系，6厘米接触细条另提尺寸规整建议。",
        observed="两层图的隔墙和尺寸链可定位；F1标定距北边4.00米，F2为3.94米。数字由保存声明和标定核对，非凭局部框猜读。",
        inferred="相应隔墙应跨层对应；工作记录判断6厘米差异为可规整尺寸差，三间房与原连接保留。", raw_mm=4000, value_m=4,
        field="/distance_from_north_m", scope=dict(kind="object_group", ids=["F1:O2", "F1:O3", "F2:O1"]),
        tool_call=dict(tool="build_plan_bim", payload=dict(image="1f_view.png", plan_json=json.dumps(read(SM25+"dev_inputs/plan_f1.json"), ensure_ascii=False))))
    # The second floor is a separate existing-tool declaration, not a second DSL.
    f2 = copy.deepcopy(recon["declarations"][0]); f2.update(declaration_id="decl:f2", scope=dict(kind="floor", ids=["F2"]),
        tool_call=dict(tool="build_plan_bim", payload=dict(image="2f_view.png", plan_json=json.dumps(read(SM25+"dev_inputs/plan_f2.json"), ensure_ascii=False))), declared_object_refs=[obj("F2:O1")])
    recon["declarations"][0]["scope"] = dict(kind="floor", ids=["F1"])
    recon["declarations"][0]["declared_object_refs"] = [obj("F1:O2"), obj("F1:O3")]
    recon["declarations"].append(f2); recon["model_versions"][0]["declaration_ids"].append("decl:f2")
    recorded_assembly = read(SM25+"dev_inputs/req_assemble.json")
    assert len(recorded_assembly) == 1 and recorded_assembly[0]["tool"] == "assemble_plan_bim"
    assembly_rows = json.loads(recorded_assembly[0]["arguments"]["floors_json"])
    assembly = copy.deepcopy(recon["declarations"][0])
    assembly.update(
        declaration_id="decl:assembly",
        scope=dict(kind="object_group", ids=["F1-F2-assembly"]),
        tool_call=dict(tool="assemble_plan_bim", payload=dict(
            floors_json=json.dumps(assembly_rows, ensure_ascii=False)
        )),
        field_partition=dict(
            model_declared=[
                "/assembly/floors/*/floor_id",
                "/assembly/floors/*/z_floor",
                "/assembly/floors/*/evidence",
            ],
            code_expanded=[
                "/saved/spaces",
                "/saved/opening_hosts",
                "/saved/connections",
            ],
        ),
        repetition=None,
        declared_object_refs=[obj("F1:O2"), obj("F1:O3"), obj("F2:O1")],
    )
    recon["declarations"].append(assembly)
    recon["model_versions"][0]["declaration_ids"].append("decl:assembly")
    recon["declarations"][0]["repetition"] = dict(repeat_by="object_group",instances=[
        dict(instance_id="north-F1",scope=dict(kind="object_group",ids=["north-F1"]),exceptions={}),
        dict(instance_id="north-F2",scope=dict(kind="object_group",ids=["north-F2"]),exceptions={"/derived/distance_from_north_m":3.94})])
    recon["evidence"]["items"].append(dict(evidence_id="ev:f2-line",kind="observation",statement="F2对应隔墙距北边3.94米；原图标注与像素标定均保留",source_refs=[evidence_ref(sm["historical_identity"],"view_0002",sm["raw_drawing_views"][1]["raw_image_sha256"])]))
    recon["evidence"]["conflicts"]=[dict(conflict_id="conflict:4_vs_3_94",evidence_ids=["ev:observed","ev:f2-line"],status="resolved",resolution="保留原值与图纸，按已记录判断建议尺寸对齐，不改源空间关系")]
    recon["evidence_results"][0]["directly_seen"][0].update(statement="F1隔墙P_off16可在原图相应区域定位；尺寸结论另由标注链和标定核对。",
        location=dict(image_ref=recon["evidence_packages"][0]["image_refs"][0],box_original_pixels=[780,470,990,515]))
    add_normalization("reconstruction", recon, sm_path, "space/F1%3AO2/wall/0", "space/F2%3AO1/wall/2", 4, 3.94)
    recon["calculations"].append(calculation("calc:proposed-wall-normalization", obj("space/F1%3AO2/wall/0","boundary"), "/derived/distance_from_north_m",4000,4,3.94,["ev:observed","ev:inferred"]))
    dump("tests/fixtures/harness_stage0/reconstruction.json", wrap("reconstruction", recon, sm_image, sm_path,
        dict(source_excerpt="sources/sm25_cross_floor_excerpt.json", artifact_scope="原保存BIM+另存规整建议快照；未执行规整", historical_vs_specimen="原始三间房与两层标定真实；接口声明、检查、事件为阶段0新建")))

    accepted_path = ACCEPTED + "candidate_02/source_model.json"
    sol_image = SOL + "images/parent_top.png"
    ids = ["CORE_E", "F3_W_02", "F3_W_03", "F2_W_01"]
    repeat = dict(repeat_by="floor", instances=[dict(instance_id="F3-pair", scope=dict(kind="floor", ids=["F3"]), exceptions={}),
        dict(instance_id="F2-exception", scope=dict(kind="floor", ids=["F2"]), exceptions={"/doors/D_F2_W_01_CORE_S/pair":None, "/doors/D_F2_W_01_CORE_S/offset_from_partition_line_m":.25})])
    inf = base_bundle("partial_inference", image_path=sol_image, native_run="run_61sol", saved_path=accepted_path, selected_ids=ids,
        requirement="已验收精细档：保留标准层细房间、成对靠隔墙房门及例外；CORE_E为连续跨层交通空间。",
        observed="俯视渲染可见长翼、横翼与核心体量；室内房间不可直接由外观测得。",
        inferred="沿用用户验收的室内推断：CORE_E连续27.6米，F3两间办公室成对开门，F2_W_01单门例外。",
        raw_mm=27600, value_m=27.6, field="/height", scope=dict(kind="cross_floor_space", ids=["CORE_E", "F1", "F2", "F3"]),
        tool_call=dict(tool="revise_bim", payload=dict(candidate="candidate_02", operations_json=json.dumps([dict(op="set_space_role", space_id="CORE_E", role="stairwell", basis="inferred", assumptions=["用户已验收的用途推断"], reason="阶段0接口示范，不执行", source_refs=["2026-09-30 user feedback"])]))), repetition=repeat)
    inf["calculations"][0]["evidence_ids"] = ["ev:inferred"]
    inf["evidence"]["items"].append(dict(evidence_id="ev:repeat-hypothesis",kind="inference",statement="重复标准层门对只是总体推断；若机械应用，会与F2_W_01已验收的单门事实相冲突",source_refs=[evidence_ref("partial_inference-offline","inference_002",digest(sol_image),"record_inference")]))
    inf["evidence"]["conflicts"]=[dict(conflict_id="conflict:repeat-vs-exception",evidence_ids=["ev:inferred","ev:repeat-hypothesis"],status="resolved",resolution="沿用已验收单门例外，不让重复规则覆盖局部结果；两项依据都保留")]
    preserve_snapshot = dict(model_version_id="saved-v1",artifact_sha256=digest(accepted_path),semantics=semantics(read(accepted_path),ids),
        dimensions=[dict(object_ref=obj("CORE_E"),field_path="/height",value_m=27.6)])
    inf["normalizations"] = [dict(proposal_id="normalize:preserve-exception",check_ids=["check:geometry"],
        tolerance=dict(origin="profile_limit",value=.06,unit="m",source_id="stage0 illustrative profile, not a product default",reason="只有尺寸噪声才有资格进入规整，真实门位例外保留"),
        features=[dict(feature_id="D_F2_W_01_CORE_S:offset",classification="genuine_offset",decision="preserve",reason="已验收非成对房门是明确例外，不能向重复模板或中点吸附")],
        edits=[],before=preserve_snapshot,after=copy.deepcopy(preserve_snapshot))]
    dump("tests/fixtures/harness_stage0/partial_inference.json", wrap("partial_inference", inf, sol_image, accepted_path,
        dict(source_excerpt="sources/partial_inference_excerpt.json", native_run_images="run_61sol", artifact_scope="用户已验收revision02的四个对象；图像沿用Sol输入；不是同一次运行", hypotheses="室内用途、空间安排、重复规则均为推断；规则是阶段0归纳，历史仅保存成对门和例外")))

    photo = read("tests/fixtures/harness_stage0/sources/photo_surrogate_excerpt.json")
    photo_image = photo["image"]["path"]
    plan = dict(templates={"office":dict(footprint=[[0,0],[8,0],[8,6],[0,6]], spaces=[dict(id="R1",role="office/enclosed",rect=[0,0,8,6],source_refs=["stage0 functional requirement; assumed dimensions"])])},
                instances=[dict(id="F1",template="office",z=0,height=3),dict(id="F2",template="office",z=3,height=3)],
                assumptions=["8x6米、3米层高和两层片段均为演示假设，不来自照片量测；真实总层数未知"], unresolved=["真实层数、标高、平面与开口待取证"])
    full_saved = artifact("full_inference", "saved_excerpt", dict(label="hand-authored offline declared-object excerpt, not a generated BIM", spaces=[
        dict(id="F1:R1",floor_id="F1",height=3,polygon=[[0,0],[8,0],[8,6],[0,6]]), dict(id="F2:R1",floor_id="F2",height=3,polygon=[[0,0],[8,0],[8,6],[0,6]])], boundaries=[],openings=[],connections=[]))
    full = base_bundle("full_inference", image_path=photo_image, native_run="full_inference-offline", saved_path=full_saved, selected_ids=["F1:R1","F2:R1"],
        requirement="阶段0虚构功能需求：办公用途，先表达两层办公片段；本样例未要求真实房间数量或整楼完成。",
        observed="照片替代渲染中可见塔状立面片段、顶部绿色区域及左侧深色条带；裁切和破碎网格不可当作开口或楼层证据。",
        inferred="仅按办公功能假设每层一个开敞办公空间；不从无内景的照片凭空增加隔墙。", raw_mm=3000,value_m=3,field="/height",scope=dict(kind="wing",ids=["office-excerpt"]),
        tool_call=dict(tool="build_parametric_bim",payload=dict(plan_json=json.dumps(plan,ensure_ascii=False))))
    full["requirements"][0]["kind"] = "functional"
    dump("tests/fixtures/harness_stage0/full_inference.json", wrap("full_inference",full,photo_image,full_saved,
        dict(source_excerpt="sources/photo_surrogate_excerpt.json", input_boundary="模型输入仅此照片替代图及虚构功能需求；无图纸、尺寸、GT、网格数值", limitation="仓库未找到适用的独立实拍，透明使用扫描贴图渲染；仅演示输入不足时的显式假设", hypotheses="参数化声明、尺寸、功能需求和保存片段均为离线样例"),include_events=False))

    mixed = copy.deepcopy(inf); mixed["case_id"]="mixed_inputs"
    mixed["evidence"]["items"].append(dict(evidence_id="ev:photo",kind="observation",statement="Voimatalo的正面贴图渲染可见塔状立面片段；内部空间和CORE_E对应不可直接看出",source_refs=[evidence_ref("run_61sol","view_0003",digest(photo_image))]))
    mixed["evidence"]["items"].append(dict(evidence_id="ev:association",kind="inference",statement="阶段0离线假设将俯视/正面塔体材料供CORE_E用途复核；跨实验对象对应未核实，不能记成历史已绑定",source_refs=[evidence_ref("mixed_inputs-offline","inference_002",digest(photo_image),"record_inference")]))
    mixed["hypotheses"][1]["evidence_ids"].append("ev:association")
    mixed["evidence"]["bindings"][0]["evidence_ids"]=["ev:photo","ev:association"]
    mixed["evidence_packages"][0]["image_refs"].append(mixed["evidence"]["items"][-2]["source_refs"][0])
    mixed["evidence_packages"][0]["known_evidence_ids"].append("ev:photo")
    dump("tests/fixtures/harness_stage0/mixed_inputs.json",wrap("mixed_inputs",mixed,sol_image,accepted_path,
        dict(inputs=["Voimatalo俯视体量渲染view_0001", "同栋正面贴图渲染view_0003", "用户验收的室内用途与门位文字要求"], same_object="CORE_E在本离线样例中关联两种图片供推断复核；不同实验中的对象对应未核实，关联本身为ev:association推断", limitation="体量渲染+立面+文字混合；不同部位的观测/推断共存，但本样例不证明跨实验几何对齐"),include_events=False))
    conflict = copy.deepcopy(recon); conflict["case_id"]="evidence_conflict"
    conflict["evidence"]["conflicts"]=[dict(conflict_id="conflict:4_vs_3_94",evidence_ids=["ev:observed","ev:f2-line"],status="resolved",resolution="保留两份读数和对应原图；按已记录判断只提对齐F2既有线的规整建议，禁止抹去原值")]
    dump("tests/fixtures/harness_stage0/evidence_conflict.json",wrap("evidence_conflict",conflict,sm_image,sm_path,dict(source_excerpt="sources/sm25_cross_floor_excerpt.json",scope="同栋跨层图纸尺寸冲突，保留原值与决策"),include_events=False))

    coarse_saved = artifact("simplification", "coarse_saved_excerpt",dict(label="offline user-authorized coarse declaration specimen; not normalization", spaces=[dict(id="F1:O2_O3_merge",floor_id="F1",height=3.4,polygon=[[11.06,14],[15,14],[15,18],[11.06,18]],members=["F1:O2","F1:O3"])],boundaries=[],openings=[],connections=[]))
    coarse = base_bundle("simplification",image_path=sm_image,native_run=sm["historical_identity"],saved_path=coarse_saved,selected_ids=["F1:O2_O3_merge"],
        requirement="阶段0粗档需求：明确将相邻O2/O3合为一个源空间，记录合并前成员；这是源简化选择。",observed=recon["evidence"]["items"][0]["statement"],
        inferred="源图仍有原隔墙，但用户的粗档表达明确授权合并；精细档下同样合并应判缺项。",raw_mm=3400,value_m=3.4,field="/height",scope=dict(kind="object_group",ids=["F1:O2_O3_merge"]),
        tool_call=dict(tool="revise_bim",payload=dict(candidate="candidate_04",operations_json="[]")),coarse=True)
    # Declaration shape only: no existing operation is invented for a future coarse merge.
    coarse["declarations"][0]["tool_call"] = dict(tool="build_parametric_bim", payload=dict(plan_json=json.dumps(dict(
        templates={"coarse":dict(footprint=[[11.06,14],[15,14],[15,18],[11.06,18]],spaces=[dict(id="O2_O3_merge",role="office/enclosed",rect=[11.06,14,15,18],source_refs=["explicit stage0 coarse requirement; sm25 O2/O3"])])},instances=[dict(id="F1",template="coarse",z=.2,height=3.4)],assumptions=["explicit source simplification"],unresolved=["excerpts omit door/window detail; not full BIM delivery"]))))
    fine = base_bundle("simplification-fine",image_path=sm_image,native_run=sm["historical_identity"],saved_path=sm_path,selected_ids=["F1:O2","F1:O3"],
        requirement="阶段0精细需求：本比较片段保留O2/O3两间源房间与中间实体隔墙。",observed=recon["evidence"]["items"][0]["statement"],
        inferred="根据原图和保存空间保留两间房；房间用途可以由家具推断，但不得以用途相同为理由自动合并。",raw_mm=3400,value_m=3.4,field="/height",scope=dict(kind="object_group",ids=["O2-O3-pair"]),
        tool_call=copy.deepcopy(recon["declarations"][0]["tool_call"]))
    failure_path = SOL + "candidate_04/source_model.json"
    failure = base_bundle("sol-fine-failure",image_path=sol_image,native_run="run_61sol",saved_path=failure_path,selected_ids=["F1_N04"],
        requirement="本轮精细档需保留合理单窗粒度办公室；不得未声明改为每间两窗的粗档。",observed="保存对象F1_N04绑定两个窗F1_NORTH_GLASS_07/08；本项由实际保存源模型核对。",
        inferred="两窗办公室对某些用途可以合理，但未落实本轮精细档偏好；方案理由不能替代验收。",raw_mm=6400,value_m=6.4,field="/height",scope=dict(kind="floor",ids=["F1"]),
        tool_call=dict(tool="revise_bim",payload=dict(candidate="candidate_04",operations_json="[]")))
    failure["coverage_issues"]=[dict(issue_id="issue:fine-grain",statement="真实Sol审查记录：66间封闭办公室没有单窗房，49间为两窗；此对象为两窗实例。")]
    failure["checks"][-1].update(status="failed",before=dict(value=dict(preference="single-window office granularity")),after=dict(value=dict(space="F1_N04",windows=["F1_NORTH_GLASS_07","F1_NORTH_GLASS_08"])),suggested_action=dict(kind="model_review",description="重新裁决空间分隔以落实精细档；不能改要求来补过"))
    failure["coverage"][0].update(status="incomplete",open_issue_ids=["issue:fine-grain"])
    dump("tests/fixtures/harness_stage0/simplification.json",dict(case_id="simplification",fixture_kind="same-input-different-user-requirements",input_image=blob(sm_image,"image/png"),
        fine=wrap("simplification-fine",fine,sm_image,sm_path,dict(scope="细档保留O2/O3；沿用真实源对象"),include_events=False),
        coarse=wrap("simplification",coarse,sm_image,coarse_saved,dict(scope="显式粗档仅核一个合并空间的声明片段", limitation="未运行BIM工具，不声明整案通过"),include_events=False),
        real_fine_failure=dict(source_excerpt="sources/partial_inference_excerpt.json", finding=partial["fine_detail_miss"],
            verdict="两次Sol几何可用不等于精细档达到；精细要求未变时不得补写粗档许可",
            sample=wrap("sol-fine-failure",failure,sol_image,failure_path,dict(scope="真实两窗办公室保存结果+本轮精细偏好失败；仅映射，不运行模型"),include_events=False))))


if __name__ == "__main__":
    main()
