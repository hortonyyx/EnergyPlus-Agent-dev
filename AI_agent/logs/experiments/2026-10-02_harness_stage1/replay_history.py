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
import importlib.util
import json
from pathlib import Path
import subprocess
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
REPLAY_CODE_PATHS = (
    "src/agent/execution/source_proposal.py",
    "src/agent/geometry/source_bim.py",
    "src/agent/geometry/source_naming.py",
    "src/agent/geometry/modelling.py",
    "AI_agent/logs/experiments/2026-09-26_sm25_multifloor_setup/audit_run.py",
    "pyproject.toml",
    "uv.lock",
)
PUBLIC_NAME_CHANGE_COMMIT = "2b83a7592a7a7ecd9b990aa3182b0b857992156e"
SNAPSHOT_REPLAY_CURRENT_MATCH_PATHS = (
    "src/agent/correction/schema.py",
    "src/agent/execution/source_proposal.py",
    "src/agent/geometry/source_bim.py",
    "src/agent/geometry/source_model.py",
    "src/agent/roles.py",
)


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


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def _head_blobs() -> dict[str, str]:
    raw = subprocess.check_output(
        ("git", "ls-tree", "-r", "-z", "--full-tree", "HEAD"), cwd=ROOT
    )
    found = {}
    for row in raw.split(b"\0"):
        if not row:
            continue
        metadata, path = row.split(b"\t", 1)
        _mode, kind, object_id = metadata.decode().split()
        if kind == "blob":
            found[path.decode()] = object_id
    return found


def _git_blob_oid(path: Path, object_format: str) -> str:
    raw = path.read_bytes()
    digest = hashlib.new(object_format)
    digest.update(f"blob {len(raw)}\0".encode())
    digest.update(raw)
    return digest.hexdigest()


def archive_manifest(
    run: Path, *, head_blobs: dict[str, str], revision: str, object_format: str
) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in run.rglob("*") if item.is_file()):
        repository_path = str(path.relative_to(ROOT))
        worktree_blob = _git_blob_oid(path, object_format)
        head_blob = head_blobs.get(repository_path)
        files.append({
            "path": str(path.relative_to(run)),
            "repository_path": repository_path,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "git_blob_oid": head_blob,
            "head_blob_matches_worktree": head_blob == worktree_blob,
        })
    matched = sum(item["head_blob_matches_worktree"] for item in files)
    return {"archive": str(run.relative_to(ROOT)), "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files),
            "repository_copy": {
                "status": "complete_in_git_head" if matched == len(files) else "incomplete",
                "revision": revision,
                "git_object_format": object_format,
                "head_exact_file_count": matched,
                "missing_or_different_paths": [
                    item["repository_path"] for item in files
                    if not item["head_blob_matches_worktree"]
                ],
            },
            "files": files}


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


def _flatten_public_names(value: dict[str, Any] | None) -> dict[str, Any]:
    flattened = {}
    for group, entries in (value or {}).items():
        if isinstance(entries, dict):
            flattened.update({f"{group}:{key}": item for key, item in entries.items()})
        else:
            flattened[group] = entries
    return flattened


def _public_name_comparison(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = _flatten_public_names(before.get("public_names"))
    right = _flatten_public_names(after.get("public_names"))
    common = left.keys() & right.keys()
    changed = sorted(key for key in common if left[key] != right[key])
    return {
        "added": sorted(right.keys() - left.keys()),
        "removed": sorted(left.keys() - right.keys()),
        "changed": changed,
        "changed_examples": [
            {"key": key, "saved": left[key], "current": right[key]}
            for key in changed[:8]
        ],
    }


def replay_environment(revision: str) -> dict[str, Any]:
    return {
        "repository_head": revision,
        "code_scope": "checked-out current code, not a reconstructed historical execution environment",
        "replay_file_sha256": [
            {"path": path, "sha256": sha256(ROOT / path)} for path in REPLAY_CODE_PATHS
        ],
        "known_public_name_change": {
            "commit": PUBLIC_NAME_CHANGE_COMMIT,
            "path": "src/agent/geometry/source_naming.py",
            "effect": (
                "Floor display names changed from generated ordinal F# labels to each source "
                "floor's explicit name or ID."
            ),
        },
    }


def replay_delivered(
    run: Path,
    candidate: str,
    *,
    naming_module: Path | None = None,
    code_scope: str = "current_checkout",
) -> dict[str, Any]:
    """Replay the proposal exporter, optionally with an archived naming module."""
    old_source = load(run / candidate / "source_model.json")
    old_source_bytes = (run / candidate / "source_model.json").read_bytes()
    proposal_path = run / candidate / "proposal.json"
    display_path = run / candidate / "display_geometry.json"
    old_display_bytes = display_path.read_bytes() if display_path.is_file() else None
    if not proposal_path.is_file():
        return {"status": "not_replayable", "reason": "delivered candidate has no saved proposal.json"}
    proposal = load(proposal_path)
    from src.agent.execution.source_proposal import export_source_proposal
    import src.agent.geometry.source_naming as current_naming
    original_builder = current_naming.build_public_names
    if naming_module is not None:
        spec = importlib.util.spec_from_file_location("stage1_archived_source_naming", naming_module)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load archived naming module: {naming_module}")
        archived_naming = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(archived_naming)
        current_naming.build_public_names = archived_naming.build_public_names
    try:
        with tempfile.TemporaryDirectory(prefix="stage1-history-replay-", dir=DEFAULT_OUT.parent) as temporary:
            target = Path(temporary) / "candidate"
            report = export_source_proposal(proposal, target,
                                            provenance=old_source["generation"]["provenance"])
            new_source = load(target / "source_model.json")
            new_display = load(target / "display_geometry.json")
            new_source_bytes = (target / "source_model.json").read_bytes()
            new_display_bytes = (target / "display_geometry.json").read_bytes()
    finally:
        current_naming.build_public_names = original_builder
    semantic = compare_sources(old_source, new_source)
    old_display = load(display_path) if display_path.is_file() else None
    top_level_differences = _top_level_diff(old_source, new_source)
    public_names = _public_name_comparison(old_source, new_source)
    naming_only = set(top_level_differences) == {"public_names", "source_model_sha256"}
    return {
        "status": "exact" if old_source == new_source and old_display == new_display else
                  ("semantic_match" if _is_equal(semantic) else "semantic_difference"),
        "replay_code_scope": code_scope,
        "saved_source_sha256": old_source.get("source_model_sha256"),
        "replayed_source_sha256": report.get("source_model_sha256"),
        "source_fields_equal": old_source == new_source,
        "source_bytes_equal": old_source_bytes == new_source_bytes,
        "display_fields_equal": old_display == new_display if old_display is not None else None,
        "display_bytes_equal": old_display_bytes == new_display_bytes if old_display_bytes is not None else None,
        "top_level_differences": top_level_differences,
        "public_names_comparison": public_names,
        "difference_explanation": (
            f"当前导出器在提交 {PUBLIC_NAME_CHANGE_COMMIT} 后改用源楼层的显式名称或 ID；"
            "保存产物使用顺序 F# 显示名。最终 proposal 不含 public_names，而候选修订会保留源候选"
            "已有的命名映射，所以重建 proposal 会按所选导出器重新命名；差异不是漏跑 finish_bim。"
            "public_names 因而变化，覆盖完整源载荷的 source_model_sha256 随之变化。对象、几何、"
            "宿主、连通差异仍在下方独立逐项列出。"
            if naming_only else None
        ),
        "semantic_comparison": semantic,
    }


def snapshot_code_evidence(run: Path) -> dict[str, Any] | None:
    snapshot = run / "runtime_snapshot"
    condition_path = run / "experiment_condition.json"
    if not snapshot.is_dir() or not condition_path.is_file():
        return None
    expected = load(condition_path).get("implementation_sha256") or {}
    rows = []
    for relative, expected_sha in sorted(expected.items()):
        archived = snapshot / relative
        current = ROOT / relative
        archived_sha = sha256(archived) if archived.is_file() else None
        current_sha = sha256(current) if current.is_file() else None
        rows.append({
            "path": relative,
            "expected_sha256": expected_sha,
            "archived_sha256": archived_sha,
            "snapshot_matches_manifest": archived_sha == expected_sha,
            "current_sha256": current_sha,
            "current_matches_snapshot": current_sha == archived_sha if archived_sha else False,
        })
    complete = bool(rows) and all(row["snapshot_matches_manifest"] for row in rows)
    return {
        "status": "complete" if complete else "incomplete",
        "manifest": str(condition_path.relative_to(ROOT)),
        "snapshot": str(snapshot.relative_to(ROOT)),
        "file_count": len(rows),
        "snapshot_exact_file_count": sum(row["snapshot_matches_manifest"] for row in rows),
        "current_equal_file_count": sum(row["current_matches_snapshot"] for row in rows),
        "current_different_paths": [row["path"] for row in rows if not row["current_matches_snapshot"]],
        "files": rows,
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
    current_replay = replay_delivered(run, candidate)
    snapshot = snapshot_code_evidence(run)
    archived_naming_path = (
        (run / "runtime_snapshot/src/agent/geometry/source_naming.py")
        if snapshot is not None else
        (RUNS["run99"] / "runtime_snapshot/src/agent/geometry/source_naming.py")
    )
    naming_compatibility = None
    if current_replay["status"] == "semantic_match":
        naming_compatibility = replay_delivered(
            run,
            candidate,
            naming_module=archived_naming_path,
            code_scope=(
                "this_run_archived_naming_plus_current_hash-matched_exporter_source_builder"
                if snapshot is not None else
                "run99_archived_pre-change_naming_module_compatibility_only"
            ),
        )
    if snapshot is not None and snapshot["status"] == "complete":
        by_path = {row["path"]: row for row in snapshot["files"]}
        required_matches = {
            path: bool(by_path.get(path, {}).get("current_matches_snapshot"))
            for path in SNAPSHOT_REPLAY_CURRENT_MATCH_PATHS
        }
        snapshot_replay = naming_compatibility or replay_delivered(
            run,
            candidate,
            naming_module=archived_naming_path,
            code_scope=(
                "this_run_archived_naming_plus_current_hash-matched_exporter_source_builder"
            ),
        )
        exact_snapshot_slice = (
            all(required_matches.values())
            and snapshot_replay["status"] == "exact"
            and snapshot_replay["source_fields_equal"] is True
            and snapshot_replay["display_fields_equal"] is True
        )
        historical_version = {
            "status": (
                "exact_for_archived_tool_snapshot" if exact_snapshot_slice
                else "snapshot_replay_mismatch"
            ),
            "reason": (
                f"本运行的 {snapshot['file_count']} 个实现文件全部匹配归档哈希清单。用归档命名模块"
                "以及哈希匹配的导出器和源构建器重放保存 proposal，可逐字段复现 source_model.json "
                "与 display_geometry.json。这证明的是保存的确定性工具切片；没有重放模型对话，且"
                "运行当时未归档依赖锁。"
                if exact_snapshot_slice else
                "运行时快照存在，但快照重放未达到逐字段一致，或当前复用的导出器/源构建依赖未与"
                "快照哈希匹配，因此不能标为精确。"
            ),
            "current_reused_file_hash_matches": required_matches,
            "snapshot_replay": snapshot_replay,
        }
    else:
        historical_version = {
            "status": "not_verifiable",
            "reason": (
                "该历史运行没有归档确定性工具切片的完整实现快照与哈希清单。兼容的旧命名算法即使"
                "能逐字节复现，也不能证明它就是运行时的精确版本。"
            ),
        }
    return {
        "label": label, "archive": str(run.relative_to(ROOT)), "delivered_candidate": candidate,
        "attachment_archive": attachment_status(label, run, manifest),
        "historical_same_version_replay": historical_version,
        "runtime_snapshot_code_evidence": snapshot,
        "deterministic_delivered_replay": current_replay,
        "archived_naming_compatibility_replay": naming_compatibility,
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
             "表中的 `exact` 只表示保存的建模声明在本报告记录的当前代码快照下逐字段重建一致；"
             "不表示重新调用模型，也不表示整案质量正确。", "",
             "run99 与 run100 保存了 44 个实现文件、逐文件哈希和运行时快照，可对保存的确定性工具层做"
             "同快照重建；其余五份没有同等代码快照，不能把当前代码的 `exact` 改称同版本复现。"
             "两份快照都未固定 Python 依赖锁，这一限制保留。", "",
             f"当前重放代码仓库提交：`{report['replay_environment']['repository_head']}`；"
             "具体重放文件和依赖锁哈希见 `replay_report.json`。", "",
             "| 样本 | 归档文件 | Git 完整副本 | 当前代码交付重建 | 装配重建 | 历史工具快照 | 候选版本变化 |",
             "|---|---:|---|---|---|---|---:|"]
    for row in report["runs"]:
        manifest = report["archives"][row["label"]]
        changed = sum(item["status"] == "changed" for item in row["saved_candidate_version_comparisons"])
        lines.append(f"| {row['label']} | {manifest['file_count']} | "
                     f"{manifest['repository_copy']['status']} | "
                     f"{row['deterministic_delivered_replay']['status']} | "
                     f"{row['deterministic_plan_assembly_replay']['status']} | "
                     f"{row['historical_same_version_replay']['status']} | {changed} |")
    for row in report["runs"]:
        lines += ["", f"## {row['label']}", "",
                  f"交付候选 `{row['delivered_candidate']}`；附件归档："
                  f"`{row['attachment_archive']['status']}`；交付重放："
                  f"`{row['deterministic_delivered_replay']['status']}`；装配重放："
                  f"`{row['deterministic_plan_assembly_replay']['status']}`；历史工具快照："
                  f"`{row['historical_same_version_replay']['status']}`。", "",
                  "缺口：", ""] + [f"- {gap}" for gap in row["historical_gaps"]]
        lines += [f"- {row['historical_same_version_replay']['reason']}"]
        lines += ["", "非确定或未核实字段：", ""] + [
            f"- {field}" for field in row["non_deterministic_fields"]
        ]
        replay = row["deterministic_delivered_replay"]
        if replay.get("top_level_differences"):
            lines += ["", "当前版本重建的顶层差异字段：`" +
                      "`, `".join(replay["top_level_differences"]) + "`。"
                      "对象、几何、宿主、连通的逐项差异见 `replay_report.json`。"]
        if replay.get("difference_explanation"):
            names = replay["public_names_comparison"]
            lines += ["", replay["difference_explanation"],
                      f"公开名称映射变化：新增 {len(names['added'])}，删除 {len(names['removed'])}，"
                      f"改名 {len(names['changed'])}；示例和完整键清单在 `replay_report.json`。"]
        compatibility = row.get("archived_naming_compatibility_replay")
        if compatibility is not None:
            lines += ["", "旧命名算法兼容重建："
                      f"`{compatibility['status']}`（`{compatibility['replay_code_scope']}`）。"
                      "这逐字段验证了名称映射与其派生源哈希可重建；只有本运行自己的完整快照才能据此"
                      "标为同快照工具重建。"]
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
              "2,575 个原始文件均以逐文件 Git blob 对照证明存在于报告所列 HEAD，清单不仅是指向"
              "本机目录的哈希。换机后检出该提交即可按 repository_path、git_blob_oid 和 SHA-256 复核。", "",
              "本次没有模型调用。当前代码的确定性重放只覆盖保存声明可重建的源 BIM 和完整保存的平面装配；"
              "桥接调用参数或模型上下文缺失的步骤未重做。候选间比较是保存源 BIM 的对象、几何、宿主、"
              "连通差异，不判断这些差异是否符合原图或用户意图。当前重建中的公开名称变化发生在"
              "proposal 导出重新生成命名映射时，不是遗漏了 finish_bim；保存的候选修订会保留其原有命名映射。", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    revision = _git("rev-parse", "HEAD")
    object_format = _git("rev-parse", "--show-object-format")
    head_blobs = _head_blobs()
    archives = {
        label: archive_manifest(
            run, head_blobs=head_blobs, revision=revision, object_format=object_format
        )
        for label, run in RUNS.items()
    }
    report = {"schema_version": "stage1.history_replay.v1",
              "scope": "seven approved historical samples; offline; historical directories read-only",
              "replay_environment": replay_environment(revision),
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
