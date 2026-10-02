#!/usr/bin/env python3
"""Hash and replay the seven approved historical runs without altering them.

The replay is deliberately layered:
1. hash every archived file;
2. rebuild the delivered source BIM from its saved proposal with current code;
3. recompile saved plan assemblies where the archive contains their full inputs;
4. compare saved candidate versions and current replay by object, geometry, host,
   and connectivity projections.

It does not call a model and does not claim to reproduce missing provider traffic.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
EXPERIMENTS = ROOT / "AI_agent/logs/experiments"
DEFAULT_OUT = Path(__file__).resolve().parent / "history"
RUNS = {
    "run99": EXPERIMENTS / "2026-09-30_sm21_instruction_fix_run99",
    "run100": EXPERIMENTS / "2026-09-30_sm24_instruction_fix_run100",
    "opus_sm21": EXPERIMENTS / "2026-10-01_opus_dev_sm21",
    "opus_sm24": EXPERIMENTS / "2026-10-01_opus_dev_sm24",
    "opus_sm25": EXPERIMENTS / "2026-10-01_opus_dev_sm25",
    "sol_61": EXPERIMENTS / "2026-10-01_partial_inference_developer_tests/run_61sol",
    "sol_6": EXPERIMENTS / "2026-10-01_partial_inference_developer_tests/run_6sol",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def archive_manifest(run: Path) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in run.rglob("*") if item.is_file()):
        files.append({"path": str(path.relative_to(run)), "bytes": path.stat().st_size,
                      "sha256": sha256(path)})
    return {"archive": str(run.relative_to(ROOT)), "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files), "files": files}


def _keyed(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in rows}


def semantic_projection(source: dict[str, Any]) -> dict[str, Any]:
    """Project only the four requested comparison dimensions."""
    floors = _keyed(source.get("floors", []))
    spaces = _keyed(source.get("spaces", []))
    boundaries = _keyed(source.get("boundaries", []))
    openings = _keyed(source.get("openings", []))
    objects = {
        **{f"floor:{key}": {"kind": "floor"} for key in floors},
        **{f"space:{key}": {"kind": "space"} for key in spaces},
        **{f"boundary:{key}": {"kind": "boundary"} for key in boundaries},
        **{f"opening:{key}": {"kind": "opening", "opening_kind": row.get("kind")}
           for key, row in openings.items()},
    }
    geometry = {
        **{f"floor:{key}": {name: row.get(name) for name in
                             ("footprint", "z_floor", "height")}
           for key, row in floors.items()},
        **{f"space:{key}": {name: row.get(name) for name in
                             ("floor_id", "polygon", "z_floor", "height")}
           for key, row in spaces.items()},
        **{f"boundary:{key}": {name: row.get(name) for name in
                                ("geometry_type", "vertices")}
           for key, row in boundaries.items()},
        **{f"opening:{key}": {name: row.get(name) for name in
                               ("kind", "vertices", "exterior")}
           for key, row in openings.items()},
    }
    hosts = {
        **{f"boundary:{key}": {"space_id": row.get("space_id")}
           for key, row in boundaries.items()},
        **{f"opening:{key}": {"host_boundary_id": row.get("host_boundary_id"),
                               "opening_hosts": (source.get("opening_hosts") or {}).get(key),
                               "space_ids": row.get("space_ids")}
           for key, row in openings.items()},
    }
    connectivity = sorted(source.get("connections", []), key=canonical)
    return {"objects": objects, "geometry": geometry, "hosts": hosts,
            "connectivity": connectivity}


def _mapping_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    common = before.keys() & after.keys()
    return {"added": sorted(after.keys() - before.keys()),
            "removed": sorted(before.keys() - after.keys()),
            "changed": sorted(key for key in common if before[key] != after[key])}


def compare_sources(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left, right = semantic_projection(before), semantic_projection(after)
    connections_left = {canonical(row): row for row in left["connectivity"]}
    connections_right = {canonical(row): row for row in right["connectivity"]}
    return {
        "objects": _mapping_diff(left["objects"], right["objects"]),
        "geometry": _mapping_diff(left["geometry"], right["geometry"]),
        "hosts": _mapping_diff(left["hosts"], right["hosts"]),
        "connectivity": {
            "added": [connections_right[key] for key in sorted(connections_right.keys() - connections_left.keys())],
            "removed": [connections_left[key] for key in sorted(connections_left.keys() - connections_right.keys())],
        },
    }


def _is_equal(diff: dict[str, Any]) -> bool:
    return not any(diff[part][change] for part in ("objects", "geometry", "hosts")
                   for change in ("added", "removed", "changed")) and not any(
                       diff["connectivity"][change] for change in ("added", "removed"))


def _top_level_diff(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    keys = before.keys() | after.keys()
    return sorted(key for key in keys if before.get(key) != after.get(key))


def replay_delivered(run: Path, candidate: str) -> dict[str, Any]:
    """Replay the deterministic proposal exporter under the checked-out version."""
    old_source = load(run / candidate / "source_model.json")
    proposal_path = run / candidate / "proposal.json"
    display_path = run / candidate / "display_geometry.json"
    if not proposal_path.is_file():
        return {"status": "not_replayable", "reason": "delivered candidate has no saved proposal.json"}
    proposal = load(proposal_path)
    from src.agent.execution.source_proposal import export_source_proposal
    with tempfile.TemporaryDirectory(prefix="stage1-history-replay-", dir=DEFAULT_OUT.parent) as temporary:
        target = Path(temporary) / "candidate"
        report = export_source_proposal(proposal, target,
                                        provenance=old_source["generation"]["provenance"])
        new_source = load(target / "source_model.json")
        new_display = load(target / "display_geometry.json")
    semantic = compare_sources(old_source, new_source)
    old_display = load(display_path) if display_path.is_file() else None
    return {
        "status": "exact" if old_source == new_source and old_display == new_display else
                  ("semantic_match" if _is_equal(semantic) else "semantic_difference"),
        "saved_source_sha256": old_source.get("source_model_sha256"),
        "replayed_source_sha256": report.get("source_model_sha256"),
        "source_bytes_equal": old_source == new_source,
        "display_equal": old_display == new_display if old_display is not None else None,
        "top_level_differences": _top_level_diff(old_source, new_source),
        "semantic_comparison": semantic,
    }


def replay_assemblies(run: Path) -> dict[str, Any]:
    paths = sorted((run / "plan_assemblies").glob("assembly_*.json"))
    if not paths:
        return {"status": "not_applicable", "reason": "archive has no saved plan assembly record", "records": []}
    shared = importlib.import_module(
        "AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
    try:
        rows = shared.replay_assemblies(run, load(run / "inputs.json"))
    except Exception as error:
        return {"status": "mismatch", "reason": f"{type(error).__name__}: {error}", "records": []}
    matched = all(row["candidate_replay_matches"] for row in rows)
    return {"status": "exact" if matched else "mismatch", "records": rows,
            "reason": None if matched else "at least one replayed assembly matched no saved candidate"}


def candidate_comparisons(run: Path) -> list[dict[str, Any]]:
    candidates = sorted((path for path in run.glob("candidate_*")
                         if (path / "source_model.json").is_file()), key=lambda path: path.name)
    rows = []
    for before, after in zip(candidates, candidates[1:]):
        diff = compare_sources(load(before / "source_model.json"), load(after / "source_model.json"))
        rows.append({"before": before.name, "after": after.name,
                     "status": "same" if _is_equal(diff) else "changed", "comparison": diff})
    return rows


def historical_gaps(label: str, run: Path) -> list[str]:
    if label in {"run99", "run100"}:
        gaps = [
            "未单独保存服务端最终请求体和原始 MCP 返回字节；现有材料是 CLI 转换后的传输记录。",
            "思考正文不可得；签名块和估算 token 数不能还原思考内容。",
        ]
    elif label.startswith("opus_"):
        gaps = [
            "dev_calls.jsonl 指向的原始桥接调用目录未随历史目录归档。",
            "tools.jsonl 只有返回侧审计行，缺完整调用参数、模型实际所见传输、模型文字、思考和用量。",
            "开发模型桥接调用没有服务端实际型号回执。",
        ]
    else:
        gaps = [
            "协作桥接器只保留请求的型号覆盖，没有服务端实际型号、token 或账单回执。",
            "未归档模型对话文字、思考以及服务端最终请求和响应。",
            "逐步 request/reply JSON 保留了部分桥接操作，但不能证明模型实际所见传输完全相同。",
        ]
    if not (run / "delivery.json").is_file():
        gaps.append("No delivery.json is archived.")
    return gaps


def attachment_status(label: str, run: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    names = {item["path"] for item in manifest["files"]}
    common = {"inputs.json", "tools.jsonl", "delivery.json"}
    if label in {"run99", "run100"}:
        expected = common | {"agent_request.json", "agent_receipt.json", "agent_stream.jsonl.gz"}
    elif label.startswith("opus_"):
        expected = common | {"agent_request.json", "dev_calls.jsonl"}
    else:
        expected = common | {"controller_request.json", "controller_dispatch.json",
                             "controller_receipt.json", "controller_integrity.json"}
    missing = sorted(expected - names)
    delivery = load(run / "delivery.json")
    candidate = delivery["candidate"]
    selected = f"{candidate}/source_model.json"
    if selected not in names:
        missing.append(selected)
    return {"status": "hashed_complete_for_defined_archive_set" if not missing else "incomplete",
            "required_files": sorted(expected | {selected}), "missing_files": missing,
            "scope": "Every regular file currently present in the immutable historical directory is hashed; "
                     "this does not assert that provider-side data absent at capture time can be recovered."}


def inspect_run(label: str, run: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    delivery = load(run / "delivery.json")
    candidate = delivery["candidate"]
    return {
        "label": label, "archive": str(run.relative_to(ROOT)), "delivered_candidate": candidate,
        "attachment_archive": attachment_status(label, run, manifest),
        "deterministic_delivered_replay": replay_delivered(run, candidate),
        "deterministic_plan_assembly_replay": replay_assemblies(run),
        "saved_candidate_version_comparisons": candidate_comparisons(run),
        "historical_gaps": historical_gaps(label, run),
        "non_deterministic_fields": [
            "事件时间戳、耗时和剩余时间", "没有服务端回执时的服务商/实际型号",
            "历史未提供的 token、费用和额度窗口", "历史未捕获的模型文字与思考",
            "渲染库版本变化时的 PNG 编码字节（只有显示重放逐字段一致时才可排除）",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    lines = ["# 阶段 1：七份历史记录分层重放", "",
             "本报告把附件哈希、确定性工具重放、跨版本语义比较分开。"
             "`exact` 只表示保存的建模声明在当前代码下逐字段重建一致；"
             "不表示重新调用模型，也不表示整案质量正确。", "",
             "| 样本 | 归档文件 | 交付重放 | 装配重放 | 候选版本变化 |", "|---|---:|---|---|---:|"]
    for row in report["runs"]:
        manifest = report["archives"][row["label"]]
        changed = sum(item["status"] == "changed" for item in row["saved_candidate_version_comparisons"])
        lines.append(f"| {row['label']} | {manifest['file_count']} | "
                     f"{row['deterministic_delivered_replay']['status']} | "
                     f"{row['deterministic_plan_assembly_replay']['status']} | {changed} |")
    for row in report["runs"]:
        lines += ["", f"## {row['label']}", "",
                  f"交付候选 `{row['delivered_candidate']}`；附件归档："
                  f"`{row['attachment_archive']['status']}`；交付重放："
                  f"`{row['deterministic_delivered_replay']['status']}`；装配重放："
                  f"`{row['deterministic_plan_assembly_replay']['status']}`。", "",
                  "缺口：", ""] + [f"- {gap}" for gap in row["historical_gaps"]]
        lines += ["", "非确定或未核实字段：", ""] + [
            f"- {field}" for field in row["non_deterministic_fields"]
        ]
        replay = row["deterministic_delivered_replay"]
        if replay.get("top_level_differences"):
            lines += ["", "当前版本重建的顶层差异字段：`" +
                      "`, `".join(replay["top_level_differences"]) + "`。"
                      "对象、几何、宿主、连通的逐项差异见 `replay_report.json`。"]
        transitions = row["saved_candidate_version_comparisons"]
        if transitions:
            lines += ["", "保存候选的跨版本比较：", "",
                      "| 前→后 | 对象 +/−/改 | 几何 +/−/改 | 宿主 +/−/改 | 连通 +/− |",
                      "|---|---:|---:|---:|---:|"]
            for item in transitions:
                diff = item["comparison"]
                counts = lambda part: "/".join(str(len(diff[part][name]))
                                                 for name in ("added", "removed", "changed"))
                lines.append(f"| {item['before']}→{item['after']} | {counts('objects')} | "
                             f"{counts('geometry')} | {counts('hosts')} | "
                             f"{len(diff['connectivity']['added'])}/{len(diff['connectivity']['removed'])} |")
    lines += ["", "## 结论边界", "",
              "本次没有模型调用。确定性重放只覆盖保存声明可重建的源 BIM 和完整保存的平面装配；"
              "桥接调用参数或模型上下文缺失的步骤未重做。候选间比较是保存源 BIM 的对象、几何、宿主、"
              "连通差异，不判断这些差异是否符合原图或用户意图。", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    archives = {label: archive_manifest(run) for label, run in RUNS.items()}
    report = {"schema_version": "stage1.history_replay.v1",
              "scope": "seven approved historical samples; offline; historical directories read-only",
              "archives": archives, "runs": []}
    for label, run in RUNS.items():
        report["runs"].append(inspect_run(label, run.resolve(), archives[label]))
    (out / "archive_manifest.json").write_text(json.dumps(archives, ensure_ascii=False, indent=1) + "\n")
    (out / "replay_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    (out / "README.md").write_text(markdown(report))
    print(json.dumps({"runs": len(report["runs"]),
                      "files": sum(row["file_count"] for row in archives.values()),
                      "replay_statuses": dict(Counter(row["deterministic_delivered_replay"]["status"]
                                                      for row in report["runs"]))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
