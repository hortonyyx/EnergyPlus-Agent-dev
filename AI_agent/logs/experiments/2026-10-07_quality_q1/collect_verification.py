"""Summarize existing Q1 evidence; does not run tests, tools or model requests."""
from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPORTS = (
    "pytest_round3_initial.xml",
    "pytest_round3_acceptance.xml",
    "pytest_round3_final.xml",
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def test_summary() -> None:
    latest = {}
    batches = []
    for filename in REPORTS:
        if not (HERE / filename).exists():
            continue
        tree = ET.parse(HERE / filename)
        counts = Counter()
        for case in tree.iter("testcase"):
            status = next((name for name, tag in (
                ("failed", "failure"), ("error", "error"), ("skipped", "skipped"),
            ) if case.find(tag) is not None), "passed")
            key = (case.get("classname"), case.get("name"))
            latest[key] = {"classname": key[0], "name": key[1],
                           "status": status, "report": filename}
            counts[status] += 1
        batches.append({"report": filename, "counts": dict(counts),
                        "wall_time_seconds": sum(float(row.get("time", 0))
                                                 for row in tree.iter("testsuite")),
                        "sha256": hashlib.sha256((HERE / filename).read_bytes()).hexdigest()})
    results = sorted(latest.values(), key=lambda item: (item["classname"], item["name"]))
    write_json(HERE / "verification_summary.json", {
        "schema": "q1-verification-summary-v3",
        "iteration": "2026-10-08 round 3",
        "method": "Latest recorded result per test item across the listed targeted batches; not a single full-suite run.",
        "pytest_options": "-n 2 -p no:cacheprovider",
        "previous_round_evidence": "round2/verification_summary.json; not added to this round's test counts",
        "all_latest_test_results_pass": bool(results) and all(item["status"] == "passed" for item in results),
        "latest_results": dict(Counter(item["status"] for item in results)),
        "batches": batches,
        "package_acceptance": "See README for replay results and product-boundary decisions; pytest results alone are not package acceptance.",
        "authorized_patches_applied": ["source_save_gate.patch", "session_compiled_plan.patch"],
        "results": results,
    })


def itemized_changes() -> None:
    report = json.loads((HERE / "replay_report.json").read_text(encoding="utf-8"))
    lines = [
        "# Q1 A–C 逐项清单", "",
        "从 `replay_report.json` 自动摘出全部 applied_changes、eliminated、rejected；序号对应原数组，未去重。",
        "`floor_regularization_rejected` 是同层明细的汇总封套，不能把它再算作独立缺陷。完整嵌套原因与回滚前状态见原 JSON 的同一位置。",
        "拒绝组没有交付后的几何与精度指标；attempted_changes_not_delivered 是尝试后回滚，不能记作已消除。", "",
    ]
    for index, run in enumerate(report["regularization_replay"]):
        items = run["items"]
        lines.extend([
            f"## {run['run']}", "",
            f"状态 `{run['status']}`；原 JSON `regularization_replay[{index}].items`。",
            f"已应用 {len(items['applied_changes'])}；删除/合并记录 {len(items['eliminated'])}；拒绝记录 {len(items['rejected'])}；尝试后回滚 {len(items['attempted_changes_not_delivered'])}。", "",
            f"其中跨层外轮廓边对齐 {len(items.get('exterior_alignment_changes', []))} 条；"
            f"消除偏差的唯一外皮线对 {len(items.get('eliminated_cross_storey_footprint_overlaps', []))} 对。"
            "外皮对齐不重复计入删除/合并记录。", "",
        ])
        for floor in run.get("floor_stage_outcomes", []):
            counts = floor.get("same_floor_compile_ready_narrow_strip_counts", {})
            lines.extend([
                f"楼层 `{floor['floor_id']}` 的 A 阶段独立结果：严格编译与源模型保存检查 "
                f"`{floor.get('same_floor_delivery_ready', False)}`；墙线合并 {counts.get('wall_merge_changes', 0)}，"
                f"消除窄条空间 {counts.get('eliminated_strip_spaces', 0)}，"
                f"删除种子 {counts.get('removed_space_seeds', 0)}，"
                f"合并重复开口 {counts.get('removed_overlapping_openings', 0)}，"
                f"删除退化接头 {counts.get('collapsed_wall_steps_removed', 0)}。", "",
                f"整楼交付状态 `{floor['whole_building_delivery_status']}`；"
                f"A 阶段独立结果仅作证据、未交付 `{floor.get('evidence_only_not_delivered', False)}`；"
                f"实际计入整楼消除 {floor.get('counted_as_delivered_eliminations', 0)}。", "",
            ])
        for category in ("applied_changes", "eliminated", "rejected"):
            lines.extend([f"### {category}", ""])
            if not items[category]:
                lines.extend(["无。", ""])
                continue
            for ordinal, item in enumerate(items[category]):
                objects = item.get("objects", item.get("lines", []))
                if not objects:
                    objects = [item[key] for key in ("source", "target") if key in item]
                labels = []
                for obj in objects:
                    label = str(obj.get("partition_id", obj.get("id", obj)))
                    if obj.get("floor_id"):
                        label = f"{obj['floor_id']}/{label}"
                    labels.append(label)
                labels.extend(str(seed) for seed in item.get("space_seed_ids", []))
                if item.get("floor_id") and not labels:
                    labels.append(item["floor_id"])
                values = "; ".join(f"{key}={value}"
                                   for key, value in item.items()
                                   if key.endswith("_m") and isinstance(value, (int, float)))
                explanation = " ".join(str(item[key]) for key in ("message", "reason", "fix")
                                       if item.get(key))
                if item.get("changed_legitimate_separations"):
                    explanation += f" 涉及 {len(item['changed_legitimate_separations'])} 对原有 >=30cm 间距；逐对前后值见本条 JSON。"
                if "report" in item:
                    explanation += f" 同层拒绝汇总；完整清单在本条 .report，状态 {item['report'].get('status')}。"
                lines.extend([
                    f"{ordinal + 1}. `{category}[{ordinal}]` · `{item.get('type', 'change')}` · {' / '.join(labels)}",
                    "", f"   {values or '尺寸见对应明细。'} {explanation}", "",
                ])
    (HERE / "itemized_changes.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    test_summary()
    itemized_changes()
