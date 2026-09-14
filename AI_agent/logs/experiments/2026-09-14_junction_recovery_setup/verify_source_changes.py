"""Replay seed/final proposals and report literal source changes, without GT.

The input run is read-only.  All re-exports and reports are written under a new
verification directory.  Counts and source self-consistency are recorded as
mechanical facts only; neither is treated as drawing-fidelity evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent.execution.source_proposal import export_source_proposal


_GEOMETRY_FIELDS = (
    "coordinate_system", "floors", "spaces", "boundaries", "boundary_relations",
    "openings", "opening_hosts", "connections", "unbuilt_openings", "unsupported",
    "conflicts",
)
_SPACE_GEOMETRY_FIELDS = ("floor_id", "z_floor", "height", "polygon")
_OPENING_GEOMETRY_FIELDS = (
    "kind", "vertices", "host_boundary_id", "space_ids", "exterior", "connectivity",
)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _keyed(rows: object, *, key: str, label: str) -> dict[str, dict]:
    if not isinstance(rows, list):
        raise ValueError(f"source {label} must be a list")
    result: dict[str, dict] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"source {label}[{index}] must be an object")
        identity = row.get(key)
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"source {label}[{index}].{key} must be a nonempty string")
        if identity in result:
            raise ValueError(f"source {label} has duplicate {key} {identity!r}")
        result[identity] = row
    return result


def _changed_fields(before: dict, after: dict) -> list[str]:
    return sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))


def _entities(before: object, after: object, *, key: str, label: str) -> dict:
    old = _keyed(before, key=key, label=label)
    new = _keyed(after, key=key, label=label)
    retained = sorted(old.keys() & new.keys())
    changed = [
        {"id": identity, "changed_fields": _changed_fields(old[identity], new[identity]),
         "before": old[identity], "after": new[identity]}
        for identity in retained if old[identity] != new[identity]
    ]
    changed_ids = {row["id"] for row in changed}
    return {
        "before_count": len(old), "after_count": len(new),
        "added": [new[identity] for identity in sorted(new.keys() - old.keys())],
        "removed": [old[identity] for identity in sorted(old.keys() - new.keys())],
        "retained_ids": retained,
        "unchanged_ids": [identity for identity in retained if identity not in changed_ids],
        "changed": changed,
    }


def _subset(row: dict, fields: tuple[str, ...]) -> dict:
    return {field: row.get(field) for field in fields}


def _geometry_changed_ids(before: object, after: object, *, key: str, label: str,
                          fields: tuple[str, ...]) -> list[str]:
    old = _keyed(before, key=key, label=label)
    new = _keyed(after, key=key, label=label)
    return [
        identity for identity in sorted(old.keys() & new.keys())
        if _subset(old[identity], fields) != _subset(new[identity], fields)
    ]


def _resolve_selection(run: Path) -> dict:
    summary_path = run / "summary.json"
    selection_path = run / "delivery_selection.json"
    summary = _read(summary_path) if summary_path.is_file() else None
    explicit = _read(selection_path) if selection_path.is_file() else None
    summary_delivery = summary.get("delivery") if isinstance(summary, dict) else None
    selected = summary_delivery.get("candidate") if isinstance(summary_delivery, dict) else None
    origin = summary_delivery.get("selection_origin") if isinstance(summary_delivery, dict) else None
    if selected is None and isinstance(explicit, dict):
        selected = explicit.get("candidate")
        origin = "delivery_selection_without_summary"
    if selected is not None and (not isinstance(selected, str) or not selected):
        raise ValueError("final selection candidate must be a nonempty string")
    explicit_candidate = explicit.get("candidate") if isinstance(explicit, dict) else None
    return {
        "candidate": selected,
        "selection_origin": origin,
        "summary_file": str(summary_path) if summary_path.is_file() else None,
        "delivery_selection_file": str(selection_path) if selection_path.is_file() else None,
        "summary_and_explicit_selection_agree": (
            None if selected is None or explicit_candidate is None else selected == explicit_candidate
        ),
    }


def _reexport(run: Path, candidate: str, out: Path) -> tuple[dict, dict]:
    source_dir = run / candidate
    proposal_path = source_dir / "proposal.json"
    source_path = source_dir / "source_model.json"
    report_path = source_dir / "report.json"
    for path in (proposal_path, source_path, report_path):
        if not path.is_file():
            raise ValueError(f"selected source input is missing: {path}")
    proposal = _read(proposal_path)
    saved_source = _read(source_path)
    saved_report = _read(report_path)
    exported_report = export_source_proposal(
        proposal, out, provenance=saved_report.get("provenance", {}),
    )
    replay_path = out / "source_model.json"
    replay_source = _read(replay_path) if replay_path.is_file() else None
    differing_fields = [] if replay_source is None else sorted(
        key for key in saved_source.keys() | replay_source.keys()
        if saved_source.get(key) != replay_source.get(key)
    )
    geometry_field_matches = {
        field: replay_source is not None and saved_source.get(field) == replay_source.get(field)
        for field in _GEOMETRY_FIELDS
    }
    checks = {
        "proposal_json_matches": (out / "proposal.json").is_file()
                                and _read(out / "proposal.json") == proposal,
        "source_model_exact_match": replay_source == saved_source,
        "source_model_sha256_field_matches": replay_source is not None
            and replay_source.get("source_model_sha256") == saved_source.get("source_model_sha256"),
        "source_geometry_sha256_field_matches": replay_source is not None
            and replay_source.get("source_geometry_sha256") == saved_source.get("source_geometry_sha256"),
        "source_geometry_fields_match": all(geometry_field_matches.values()),
        "space_ids_match": replay_source is not None and {
            row["id"] for row in replay_source.get("spaces", [])
        } == {row["id"] for row in saved_source.get("spaces", [])},
        "opening_ids_match": replay_source is not None and {
            row["id"] for row in replay_source.get("openings", [])
        } == {row["id"] for row in saved_source.get("openings", [])},
        "connection_opening_ids_match": replay_source is not None and {
            row["opening_id"] for row in replay_source.get("connections", [])
        } == {row["opening_id"] for row in saved_source.get("connections", [])},
    }
    return saved_source, {
        "candidate": candidate,
        "input_files": {
            "proposal": str(proposal_path), "proposal_sha256": _sha256(proposal_path),
            "source_model": str(source_path), "source_model_file_sha256": _sha256(source_path),
            "report": str(report_path), "report_sha256": _sha256(report_path),
        },
        "verification_export": str(out),
        "export_report": exported_report,
        "checks": checks,
        "geometry_field_matches": geometry_field_matches,
        "differing_source_top_level_fields": differing_fields,
        "mechanical_replay_ok": all(checks.values()),
    }


def verify(run: Path, out: Path) -> dict:
    run = run.resolve()
    out = out.resolve()
    if not (run / "seed/proposal.json").is_file():
        raise ValueError("run has no materialized seed proposal")
    if out.exists():
        raise ValueError(f"verification output already exists: {out}")
    out.mkdir(parents=True)

    monitored = [
        path for candidate in [run / "seed", *sorted(run.glob("candidate_*"))]
        for path in (candidate / "proposal.json", candidate / "source_model.json", candidate / "report.json")
        if path.is_file()
    ]
    input_hashes_before = {str(path): _sha256(path) for path in monitored}
    selection = _resolve_selection(run)
    actual_candidates = sorted(path.parent.name for path in run.glob("candidate_*/source_model.json"))
    selected = selection["candidate"]
    if selected is not None and selected != "seed" and selected not in actual_candidates:
        raise ValueError(f"final selection {selected!r} has no source_model.json")

    seed_source, seed_replay = _reexport(run, "seed", out / "seed_reexport")
    selected_source = None
    selected_replay = None
    if selected is not None and selected != "seed":
        selected_source, selected_replay = _reexport(
            run, selected, out / "selected_reexport",
        )
    elif selected == "seed":
        selected_source, selected_replay = seed_source, seed_replay

    comparison = None
    if selected_source is not None and selected != "seed":
        spaces = _entities(seed_source.get("spaces"), selected_source.get("spaces"),
                           key="id", label="spaces")
        openings = _entities(seed_source.get("openings"), selected_source.get("openings"),
                             key="id", label="openings")
        connections = _entities(seed_source.get("connections"), selected_source.get("connections"),
                                key="opening_id", label="connections")
        comparison = {
            "from": "seed", "to": selected,
            "same_source_model_sha256": (
                seed_source.get("source_model_sha256") == selected_source.get("source_model_sha256")
            ),
            "same_source_geometry_sha256": (
                seed_source.get("source_geometry_sha256") == selected_source.get("source_geometry_sha256")
            ),
            "spaces": spaces,
            "space_geometry_changed_ids": _geometry_changed_ids(
                seed_source.get("spaces"), selected_source.get("spaces"),
                key="id", label="spaces", fields=_SPACE_GEOMETRY_FIELDS,
            ),
            "openings": openings,
            "opening_geometry_or_host_changed_ids": _geometry_changed_ids(
                seed_source.get("openings"), selected_source.get("openings"),
                key="id", label="openings", fields=_OPENING_GEOMETRY_FIELDS,
            ),
            "connections": connections,
        }

    input_hashes_after = {str(path): _sha256(path) for path in monitored}
    replay_rows = [seed_replay] + ([selected_replay] if selected_replay is not None
                                  and selected_replay is not seed_replay else [])
    report = {
        "schema_version": "source_change_verification_v1",
        "mode": "offline_deterministic_source_reexport_and_literal_diff",
        "run": str(run),
        "selection": selection,
        "actual_new_candidates": actual_candidates,
        "seed_only": not actual_candidates,
        "comparison_available": comparison is not None,
        "comparison": comparison,
        "reexports": replay_rows,
        "input_files_unchanged": input_hashes_before == input_hashes_after,
        "input_file_sha256": input_hashes_after,
        "mechanical_reexports_match_saved_sources": all(
            row["mechanical_replay_ok"] for row in replay_rows
        ),
        "drawing_fidelity": "not_evaluated",
        "human_confirmation": "not_evaluated",
        "limits": [
            "This compares saved and independently re-exported source data; it does not inspect GT.",
            "Room/opening/connection counts and source self-consistency do not establish drawing fidelity.",
            "Added, removed, changed, retained, and unchanged refer to literal source records and IDs only.",
            "No source proposal, source model, drawing, or ground-truth file is modified.",
        ],
    }
    report_path = out / "source_change_verification.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_index(out, report)
    return report


def _ids(rows: list[dict], field: str = "id") -> str:
    return ", ".join(html.escape(str(row.get(field))) for row in rows) or "无"


def _write_index(out: Path, report: dict) -> None:
    comparison = report["comparison"]
    if comparison is None:
        change_rows = '<tr><td colspan="6">没有最终选择可与 seed 比较；仅核验 seed 重导出。</td></tr>'
    else:
        rendered = []
        for label, key, identity in (("空间", "spaces", "id"),
                                     ("开口", "openings", "id"),
                                     ("连接", "connections", "opening_id")):
            section = comparison[key]
            rendered.append(
                f'<tr><td>{label}</td><td>{_ids(section["added"], identity)}</td>'
                f'<td>{_ids(section["removed"], identity)}</td>'
                f'<td>{html.escape(", ".join(row["id"] for row in section["changed"]) or "无")}</td>'
                f'<td>{html.escape(", ".join(section["retained_ids"]) or "无")}</td>'
                f'<td>{html.escape(", ".join(section["unchanged_ids"]) or "无")}</td></tr>')
        change_rows = "".join(rendered)
    selected_reexport = out / "selected_reexport/viewer.html"
    viewer = "selected_reexport/viewer.html" if selected_reexport.is_file() else "seed_reexport/viewer.html"
    candidate = report["selection"]["candidate"] or "无最终选择"
    document = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>源变化离线核验</title><style>body{{font:15px/1.55 system-ui;max-width:1400px;margin:24px auto;padding:0 16px}}
.notice{{padding:12px;background:#fff3cd;border:1px solid #dbbd54}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:7px;text-align:left;vertical-align:top}}iframe{{width:100%;height:760px;border:1px solid #aaa}}</style>
<h1>源变化离线核验</h1><p class="notice">这里只比较保存的源数据、ID 和确定性重导出。房间数量、几何自洽与 viewer 可打开都不代表图纸保真。</p>
<p>最终选择：{html.escape(candidate)}；实际新候选：{html.escape(", ".join(report["actual_new_candidates"]) or "无，仅 seed")}。</p>
<p><a href="source_change_verification.json">完整 JSON</a> · <a href="{viewer}">独立重导出 viewer</a></p>
<table><thead><tr><th>类别</th><th>新增</th><th>删除</th><th>同 ID 改动</th><th>保留 ID</th><th>完全未变</th></tr></thead><tbody>{change_rows}</tbody></table>
<h2>独立重导出查看</h2><iframe src="{viewer}" title="独立重导出源模型"></iframe></html>'''
    (out / "index.html").write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--out", type=Path,
                        help="new output directory (default: RUN/source_change_verification)")
    args = parser.parse_args()
    run = args.run.resolve()
    result = verify(run, args.out or run / "source_change_verification")
    print(json.dumps({
        "selection": result["selection"],
        "actual_new_candidates": result["actual_new_candidates"],
        "seed_only": result["seed_only"],
        "comparison_available": result["comparison_available"],
        "reexports_match": result["mechanical_reexports_match_saved_sources"],
        "input_files_unchanged": result["input_files_unchanged"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
