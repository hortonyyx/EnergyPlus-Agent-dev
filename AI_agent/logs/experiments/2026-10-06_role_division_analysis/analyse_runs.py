"""Extract compact A/B evidence from saved native-runtime runs and evaluations."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from score_role_answers import score_plan_openings
from shapely.geometry import LineString, Point, Polygon

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TEMP = ROOT / "AI_agent/archive/local_backup/d1a/runs_separated"

RUNS = {
    "2026-10-05_qwen27b_sm24": TEMP / "c3/sm24_qwen27b_c3",
    "2026-10-04_qwen27b_sm24": TEMP / "a1/sm24_qwen27b_after_a2",
    "2026-10-05_runtime_glm_sm24": TEMP / "c3/sm24_runtime_anthropic",
    "2026-10-04_runtime_glm_sm24": TEMP / "a1/sm24_runtime_anthropic",
    "2026-10-05_runtime_glm_sm25": TEMP / "c3/sm25_runtime_anthropic",
    "2026-10-04_runtime_glm_sm25": TEMP / "a1/sm25_runtime_anthropic",
}


def blob_json(run: Path, descriptor: dict) -> Any:
    sha = descriptor.get("sha256") or Path(descriptor["uri"]).name
    value = json.loads((run / "blobs" / sha).read_bytes())
    if isinstance(value, dict) and "tree" in value:
        return decode_tree(run, value["tree"])
    if isinstance(value, list) and value and value[0] in {"value", "ref", "object", "array", "list"}:
        return decode_tree(run, value)
    return value


def decode_tree(run: Path, node: Any) -> Any:
    if not isinstance(node, list) or not node:
        return node
    tag = node[0]
    if tag == "value":
        return node[1]
    if tag == "ref":
        return blob_json(run, node[1])
    if tag == "object":
        return {key: decode_tree(run, value) for key, value in node[1]}
    if tag in {"array", "list"}:
        return [decode_tree(run, value) for value in node[1]]
    return node


def shown_result(run: Path, payload: dict) -> Any:
    shown = payload.get("shown_result") or payload.get("raw_result")
    if not isinstance(shown, dict):
        return shown
    if shown.get("kind") == "inline":
        return shown.get("value")
    if shown.get("kind") in {"json_references", "image_references", "blob"}:
        return blob_json(run, shown["blob"])
    return shown


def walk(value: Any):
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def warning_rows(value: Any) -> list[dict]:
    rows = []
    for item in walk(value):
        if isinstance(item, dict) and (item.get("code") == "unsupported_open_separator" or
                                      item.get("type") == "unsupported_open_separator"):
            rows.append(item)
        elif isinstance(item, str) and "unsupported_open_separator" in item:
            try:
                decoder, offset = json.JSONDecoder(), 0
                while offset < len(item):
                    while offset < len(item) and item[offset].isspace():
                        offset += 1
                    if offset >= len(item):
                        break
                    value, offset = decoder.raw_decode(item, offset)
                    rows.extend(warning_rows(value))
            except (ValueError, TypeError):
                pass
    return rows


def difference_rows(value: Any) -> list[dict]:
    kinds = {"unsupported_open_separator", "opening_offset_from_gap",
             "wall_gap_without_opening", "undeclared_wall_line"}
    rows = []
    for item in walk(value):
        if isinstance(item, dict) and item.get("type") in kinds:
            rows.append(item)
        elif isinstance(item, str) and any(kind in item for kind in kinds):
            try:
                decoder, offset = json.JSONDecoder(), 0
                while offset < len(item):
                    while offset < len(item) and item[offset].isspace():
                        offset += 1
                    if offset >= len(item):
                        break
                    decoded, offset = decoder.raw_decode(item, offset)
                    rows.extend(difference_rows(decoded))
            except (ValueError, TypeError):
                pass
    return rows


def plan_summary(arguments: dict) -> dict:
    try:
        plan = json.loads(arguments["plan_json"])
    except (KeyError, TypeError, ValueError):
        return {"parse_error": True}
    suspicious = []
    for part in plan.get("partitions", []):
        text = json.dumps(part, ensure_ascii=False).lower()
        if any(key in text for key in ("partc", "passage", "corridor", "586")):
            suspicious.append(part)
    opens = [row for row in plan.get("openings", []) if row.get("kind") == "open"]
    return {"floor_id": plan.get("floor_id"), "basis": plan.get("basis"),
            "partition_count": len(plan.get("partitions", [])),
            "partitions": plan.get("partitions", []),
            "opening_count": len(plan.get("openings", [])),
            "space_seeds": plan.get("space_seeds", []),
            "corridor_related_partitions": suspicious, "open_passages": opens}


def trace(run: Path) -> dict:
    events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    started = datetime.fromisoformat(events[0]["occurred_at"]["value"].replace("Z", "+00:00"))
    request_no, call_requests, call_thoughts, calls = 0, {}, {}, []
    for event in events:
        payload = event["payload"]
        if payload["event_type"] == "model_response":
            request_no += 1
            thinking = "\n".join(item.get("content", "") for item in payload.get("thinking", [])
                                 if item.get("kind") == "public_content")
            for call in payload.get("tool_calls", []):
                call_requests[call["call_id"]] = request_no
                call_thoughts[call["call_id"]] = thinking
        if payload["event_type"] != "tool_execution":
            continue
        call_id = payload["call_id"]
        result = shown_result(run, payload)
        warnings = warning_rows(result)
        differences = difference_rows(result)
        when = datetime.fromisoformat(event["occurred_at"]["value"].replace("Z", "+00:00"))
        row = {"sequence": event["sequence"], "elapsed_s": round((when - started).total_seconds(), 3),
               "request": call_requests.get(call_id), "tool": payload["tool_name"],
               "outcome": payload.get("outcome"), "thinking": call_thoughts.get(call_id, ""),
               "unsupported_open_separator": warnings, "plan_difference_items": differences}
        if payload["tool_name"] == "build_plan_bim":
            row["plan"] = plan_summary(payload.get("full_arguments", {}))
        calls.append(row)
    builds = [row for row in calls if row["tool"] == "build_plan_bim"]
    first_warning = next((row for row in calls if row["unsupported_open_separator"]), None)
    later = [row for row in calls if first_warning and row["request"] and
             row["request"] > first_warning["request"]]
    reaction = [row for row in later if any(key in row["thinking"].lower() for key in
                ("unsupported_open_separator", "ink_fraction", "almost no ink", "continuous space"))]
    final_build = builds[-1] if builds else None
    return {"event_count": len(events), "request_count": request_no, "tool_count": len(calls),
            "build_plan_bim": builds, "first_warning": first_warning,
            "later_request_count": len({row["request"] for row in later}),
            "requests_after_final_build": request_no - final_build["request"] if final_build else None,
            "warning_tool_executions_after_first": sum(bool(row["unsupported_open_separator"]) for row in later),
            "model_reaction_hits": reaction}


def raw_plan_openings(plan: dict, reference: list[dict]) -> dict:
    def cv(value: float, axis: str) -> float:
        (p0, v0), (p1, v1) = plan[f"{axis}_anchors"]
        return v0 + (value - p0) * (v1 - v0) / (p1 - p0)
    rows = []
    for opening in plan["openings"]:
        if opening["kind"] not in {"door", "window"}:
            continue
        p1, p2 = opening["p1"], opening["p2"]
        axis = "x" if abs(p2[0] - p1[0]) >= abs(p2[1] - p1[1]) else "y"
        dim, cross_dim = (0, 1) if axis == "x" else (1, 0)
        cross_axis = "y" if axis == "x" else "x"
        rows.append({"id": opening["id"], "kind": opening["kind"], "axis": axis,
                     "span_m": sorted((cv(p1[dim], axis), cv(p2[dim], axis))),
                     "cross_m": cv((p1[cross_dim] + p2[cross_dim]) / 2, cross_axis)})
    return score_plan_openings(reference, rows)


def opening_regression() -> dict:
    reference = json.loads((HERE / "references/sm25-L_anchor.json").read_bytes())
    ref_by_floor = {row["floor_id"]: row["openings"] for row in reference["plan_questions"]}
    ref_floors = {row["floor_id"]: row for row in reference["plan_questions"]}
    ref_lookup = {row["id"]: row for floor in reference["plan_questions"] for row in floor["openings"]}

    def host_label(ref: dict) -> str:
        if not ref["exterior"]:
            return "interior:" + "<->".join(ref["host_labels"])
        center = ((sum(ref["span_m"]) / 2, ref["cross_m"]) if ref["axis"] == "x"
                  else (ref["cross_m"], sum(ref["span_m"]) / 2))
        ring = ref_floors[ref["floor_id"]]["exterior_m"]
        polygon = Polygon(ring)
        candidates = []
        for p0, p1 in zip(ring, ring[1:] + ring[:1]):
            candidates.append((LineString([p0, p1]).distance(Point(center)), p0, p1))
        _, p0, p1 = min(candidates)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        nx, ny = (dy, -dx) if polygon.exterior.is_ccw else (-dy, dx)
        return ("East" if nx > 0 else "West") if abs(nx) > abs(ny) else ("North" if ny > 0 else "South")
    runs = {
        "2026-10-04": TEMP / "a1/sm25_runtime_anthropic/bim",
        "2026-10-05": TEMP / "c3/sm25_runtime_anthropic/bim",
    }
    quality = {
        "2026-10-04": HERE / "evaluation/sm25_20261004_runtime/candidate_07_delivery_quality.json",
        "2026-10-05": ROOT / "AI_agent/logs/experiments/2026-10-05_node_regression_c3/evaluation/sm25_runtime_anthropic/candidate_06_delivery_quality.json",
    }
    selected = {"2026-10-04": "candidate_07", "2026-10-05": "candidate_06"}
    result = {"final": {}, "first_plan_drafts": {}}
    for label, path in runs.items():
        report = json.loads(quality[label].read_bytes())["opening_inventory"]
        source = json.loads((path / selected[label] / "source_model.json").read_bytes())
        source_openings = {row["id"]: row for row in source["openings"]}
        first_declaration = {}
        for plan_path in sorted((path / "plan_drafts").glob("draft_*/plan.json")):
            plan = json.loads(plan_path.read_bytes())
            for opening in plan.get("openings", []):
                first_declaration.setdefault(opening["id"], {
                    "draft": plan_path.parent.name, "floor_id": plan["floor_id"],
                    "p1_pixel": opening["p1"], "p2_pixel": opening["p2"],
                    "source_refs": opening.get("source_refs", []), "plan_basis": plan.get("basis")})
        details = []
        for row in report["comparisons"]:
            if row["position_match"]:
                continue
            actual = source_openings[row["opening_id"]]
            refs = actual.get("source_refs", [])
            text = " ".join(refs).lower()
            if text.startswith("correction:"):
                basis = "deterministic_correction_of_prior_declaration"
            elif any(key in text for key in ("arc", "ink gap", "qa", "view_", " px", "~")):
                basis = "image_measurement_or_estimate"
            elif "chain" in text or "dimension" in text:
                basis = "annotated_dimension"
            else:
                basis = "declared_value_basis_not_explicit"
            ref = ref_lookup[row["reference_id"]]
            actual_id = row["opening_id"]
            declared = first_declaration.get(actual_id)
            if declared is None and ":" in actual_id:
                declared = first_declaration.get(actual_id.split(":", 1)[1])
            details.append({**row, "host_or_facade": host_label(ref),
                            "source_refs": actual.get("source_refs", []), "value_basis": basis,
                            "first_declaration": declared})
        result["final"][label] = {
            key: report[key] for key in ("reference_count", "matched", "positions", "hosts", "door_connections")}
        result["final"][label].update({"wrong_positions": details,
            "unmatched_reference": [x for floor in report["floors"] for x in floor["unmatched_reference"]],
            "unmatched_actual": [x for floor in report["floors"] for x in floor["unmatched_actual"]]})
        seen = set()
        draft_rows = []
        for plan_path in sorted((path / "plan_drafts").glob("draft_*/plan.json")):
            plan = json.loads(plan_path.read_bytes())
            fid = plan["floor_id"]
            if fid in seen:
                continue
            seen.add(fid)
            scored = raw_plan_openings(plan, ref_by_floor[fid])
            draft_rows.append({"draft": plan_path.parent.name, "floor_id": fid,
                               "basis": plan.get("basis"), "openings_declared": len(plan["openings"]),
                               "score": {key: scored[key] for key in
                                         ("reference_count", "matched", "positions",
                                          "unmatched_reference", "unmatched_answer")}})
        result["first_plan_drafts"][label] = draft_rows
    return result


def main() -> None:
    evidence = {"schema_version": "d1a_run_evidence_v1",
                "runs": {name: trace(path) for name, path in RUNS.items()},
                "sm25_opening_regression": opening_regression()}
    target = HERE / "analysis_evidence.json"
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = ["# sm25 门窗位置逐项对比", "",
             "评价口径：沿墙端点与垂墙误差分别使用冻结原图清单中的容差；未匹配项单列。", ""]
    regression = evidence["sm25_opening_regression"]
    for label in ("2026-10-05", "2026-10-04"):
        value = regression["final"][label]
        lines += [f"## {label}", "",
                  f"汇总：位置 {value['positions']}/{value['reference_count']}，匹配 {value['matched']}，"
                  f"宿主 {value['hosts']}，门连接 {value['door_connections']}。", "",
                  "| 层 | 参照 → 实际 | 类别 | 墙/立面 | 参照 span / cross (m) | 实际 span / cross (m) | 端点误差 / 垂墙误差 (m) | 依据 | 首次声明 |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for row in value["wrong_positions"]:
            first = row.get("first_declaration") or {}
            lines.append("| {floor_id} | {reference_id} → {opening_id} | {kind} | {host} | {rs} / {rc:.3f} | {cs} / {cc:.3f} | {along:.3f} / {cross:.3f} | {basis} | {draft} {p1}→{p2} |".format(
                floor_id=row["floor_id"], reference_id=row["reference_id"], opening_id=row["opening_id"],
                kind=row["kind"], host=row["host_or_facade"], rs=[round(x, 3) for x in row["reference_span_m"]],
                rc=row["reference_cross_m"], cs=[round(x, 3) for x in row["candidate_span_m"]],
                cc=row["candidate_cross_m"], along=row["max_endpoint_error_m"],
                cross=row["perpendicular_error_m"], basis=row["value_basis"],
                draft=first.get("draft", "—"), p1=first.get("p1_pixel", "—"), p2=first.get("p2_pixel", "—")))
        lines += ["", f"未匹配参照：{value['unmatched_reference'] or '无'}。",
                  f"未匹配实际：{value['unmatched_actual'] or '无'}。", ""]
    lines += ["## 首稿即出现的差异", ""]
    for label, rows in regression["first_plan_drafts"].items():
        for row in rows:
            score = row["score"]
            lines.append(f"- {label} {row['floor_id']} {row['draft']}：位置 {score['positions']}/{score['reference_count']}，"
                         f"声明 {row['openings_declared']} 个；漏配 {score['unmatched_reference']}，多配 {score['unmatched_answer']}。")
    lines += ["", "完整数值、source_refs、容差和首稿 basis 见 `analysis_evidence.json`。", ""]
    (HERE / "sm25_opening_regression.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({name: {key: value[key] for key in
          ("request_count", "tool_count", "later_request_count", "warning_tool_executions_after_first")}
          for name, value in evidence["runs"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
