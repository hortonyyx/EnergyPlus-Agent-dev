"""Independent, post-run sm24 reconstruction evaluation.

This file is deliberately kept with the experiment rather than the production
agent.  It reads the verified reference only after a run has written its final
``summary.json`` and never produces an input for the generating agent.  A run
that ended by timeout or budget interruption can still have a viewable delivery
candidate, so ``agent_response_completed`` is recorded rather than required.

The sm24 reference is typed GT v3.  In particular, it is *not* sent through the
legacy sm21 elevation scorer.  The opening comparison below is a conservative
coordinate diagnostic: it pairs source and reference rows only in equal-count
floor/facade/kind groups, in their declared world-axis order.  It is useful for
locating a displacement, but is not a full typed opening-claim score and does
not prove visual fidelity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.judge.gt import gt_path, load_gt_document
from src.agent.judge.gt_schema import GroundTruthV3
from src.agent.judge.partition_evidence import reference_partition
from scripts.tool_scripts.diagnose_partition_evidence import overlay


CASE = "sm24_anchor"
EPSILON_M = 1e-6


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_completed_summary(run: Path) -> dict[str, Any]:
    path = run / "summary.json"
    if not path.is_file():
        raise RuntimeError("evaluation must wait until the run writes summary.json")
    summary = json.loads(path.read_text(encoding="utf-8"))
    delivery = summary.get("delivery")
    if not isinstance(delivery, dict) or not isinstance(delivery.get("candidate"), str):
        raise RuntimeError("evaluation requires a completed delivery candidate in summary.json")
    return summary


def _candidate_dirs(run: Path, delivery: str) -> list[Path]:
    candidates = [path for path in sorted(run.glob("candidate_*"))
                  if (path / "source_model.json").is_file() and (path / "proposal.json").is_file()]
    seed = run / "seed"
    if (seed / "source_model.json").is_file() and (seed / "proposal.json").is_file():
        candidates.insert(0, seed)
    if not candidates:
        raise RuntimeError("completed run has no candidate with proposal.json and source_model.json")
    if delivery not in {path.name for path in candidates}:
        raise RuntimeError(f"delivery candidate {delivery!r} has no complete source/proposal pair")
    return candidates


def _floor_extents(source: dict[str, Any]) -> dict[str, tuple[float, float, float, float]]:
    result: dict[str, tuple[float, float, float, float]] = {}
    for floor in source.get("floors", []):
        footprint = floor.get("footprint")
        if not isinstance(floor.get("id"), str) or not isinstance(footprint, list) or not footprint:
            continue
        try:
            xs, ys = zip(*((float(point[0]), float(point[1])) for point in footprint))
        except (IndexError, TypeError, ValueError):
            continue
        result[floor["id"]] = (min(xs), min(ys), max(xs), max(ys))
    return result


def _source_floor(opening: dict[str, Any], spaces: dict[str, dict[str, Any]]) -> str | None:
    ids = opening.get("space_ids")
    if not isinstance(ids, list):
        return None
    floors = {spaces[space_id].get("floor_id") for space_id in ids if space_id in spaces}
    return next(iter(floors)) if len(floors) == 1 and isinstance(next(iter(floors)), str) else None


def _source_exterior_rows(source: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return built exterior openings and rows whose physical facade is unresolved.

    The facade comes from actual 3-D opening vertices and the emitted floor
    footprint, never from an input/proposal facade label.  A malformed or
    non-perimeter host stays visible as unresolved instead of being fitted to a
    reference facade.
    """
    spaces = {space.get("id"): space for space in source.get("spaces", []) if isinstance(space, dict) and isinstance(space.get("id"), str)}
    extents = _floor_extents(source)
    rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for opening in source.get("openings", []):
        if not isinstance(opening, dict) or opening.get("exterior") is not True:
            continue
        item = {"id": opening.get("id"), "kind": opening.get("kind"),
                "host_boundary_id": opening.get("host_boundary_id"),
                "space_ids": opening.get("space_ids", [])}
        floor_id = _source_floor(opening, spaces)
        vertices = opening.get("vertices")
        if floor_id not in extents or opening.get("kind") not in {"window", "door"} or not isinstance(vertices, list):
            unresolved.append({**item, "reason": "floor_or_vertices_unavailable"})
            continue
        try:
            xyz = [(float(point[0]), float(point[1]), float(point[2])) for point in vertices]
        except (IndexError, TypeError, ValueError):
            unresolved.append({**item, "floor_id": floor_id, "reason": "invalid_3d_vertices"})
            continue
        if len(xyz) < 4:
            unresolved.append({**item, "floor_id": floor_id, "reason": "opening_has_fewer_than_four_vertices"})
            continue
        xs, ys, zs = zip(*xyz)
        xmin, ymin, xmax, ymax = extents[floor_id]
        facade: str | None = None
        along: tuple[float, float] | None = None
        if max(xs) - min(xs) <= EPSILON_M:
            along = (min(ys), max(ys))
            if abs(xs[0] - xmin) <= EPSILON_M:
                facade = "West"
            elif abs(xs[0] - xmax) <= EPSILON_M:
                facade = "East"
        elif max(ys) - min(ys) <= EPSILON_M:
            along = (min(xs), max(xs))
            if abs(ys[0] - ymin) <= EPSILON_M:
                facade = "South"
            elif abs(ys[0] - ymax) <= EPSILON_M:
                facade = "North"
        if facade is None or along is None or along[0] >= along[1]:
            unresolved.append({**item, "floor_id": floor_id, "world_vertices": xyz,
                               "reason": "opening_not_on_a_resolved_cardinal_floor_perimeter"})
            continue
        rows.append({**item, "floor_id": floor_id, "facade": facade,
                     "world_along_interval_m": list(along),
                     "z_interval_m": [min(zs), max(zs)], "world_vertices": xyz})
    return rows, unresolved


def _typed_reference_rows(gt: GroundTruthV3) -> list[dict[str, Any]]:
    segments = {segment.id: segment for floor in gt.floors for segment in floor.boundary_segments}
    rows = []
    for opening in gt.openings:
        segment = segments[opening.boundary_segment_id]
        rows.append({"id": opening.id, "kind": opening.kind, "floor_id": opening.floor_id,
                     "facade": segment.facade_family,
                     "boundary_segment_id": opening.boundary_segment_id,
                     "host_zone_id": opening.host_zone_id,
                     "world_along_interval_m": [opening.world_along_interval.lo, opening.world_along_interval.hi],
                     "z_interval_m": None if opening.z_interval is None else [opening.z_interval.lo, opening.z_interval.hi]})
    return rows


def _map_source_rows_to_reference_floors(rows: list[dict[str, Any]], floor_mapping: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Use only reference_partition's explicit map; never match floor list order."""
    mapped, unresolved = [], []
    for row in rows:
        source_floor_id = row["floor_id"]
        reference_floor_id = floor_mapping.get(source_floor_id)
        preserved = {**row, "source_floor_id": source_floor_id}
        if not isinstance(reference_floor_id, str) or reference_floor_id.startswith("unmatched:"):
            unresolved.append({**preserved, "reason": "reference_partition_floor_mapping_unavailable"})
            continue
        mapped.append({**preserved, "floor_id": reference_floor_id})
    return mapped, unresolved


def _coordinate_diagnostic(actual: list[dict[str, Any]], reference: list[dict[str, Any]], *,
                           unmapped_source_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Compare only same-count, same-world-frame grouped rows; never fit or reflect."""
    grouped_actual: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    grouped_reference: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in actual:
        grouped_actual[(row["floor_id"], row["facade"], row["kind"])].append(row)
    for row in reference:
        grouped_reference[(row["floor_id"], row["facade"], row["kind"])].append(row)
    comparisons, unresolved = [], []
    for key in sorted(grouped_actual.keys() | grouped_reference.keys()):
        observed, expected = grouped_actual[key], grouped_reference[key]
        group = {"floor_id": key[0], "facade": key[1], "kind": key[2]}
        if len(observed) != len(expected):
            unresolved.append({**group, "built_count": len(observed), "reference_count": len(expected),
                               "reason": "unequal_counts_no_forced_pairing"})
            continue
        for source_row, reference_row in zip(
                sorted(observed, key=lambda row: (row["world_along_interval_m"], row["id"])),
                sorted(expected, key=lambda row: (row["world_along_interval_m"], row["id"]))):
            span_delta = [source - target for source, target in zip(source_row["world_along_interval_m"], reference_row["world_along_interval_m"])]
            z_delta = (None if source_row["z_interval_m"] is None or reference_row["z_interval_m"] is None else
                       [source - target for source, target in zip(source_row["z_interval_m"], reference_row["z_interval_m"])])
            magnitudes = [abs(value) for value in span_delta] + ([] if z_delta is None else [abs(value) for value in z_delta])
            comparisons.append({**group, "source": source_row, "reference": reference_row,
                                "span_endpoint_delta_m": span_delta, "z_endpoint_delta_m": z_delta,
                                "max_endpoint_delta_m": max(magnitudes)})
    return {
        "status": "coordinate_diagnostic_only",
        "pairing": "source floors first map through reference_partition.floor_mapping; then ordered within equal-count floor/facade/kind groups in declared world coordinates; no reflection, fitting, or cross-facade pairing",
        "not_a_complete_match_score": True,
        "comparisons": comparisons,
        "unresolved_groups": unresolved,
        "unmapped_source_rows": unmapped_source_rows or [],
        "limitations": [
            "Equal-count ordered pairing does not prove image identity or opening correspondence.",
            "Source floor labels are not paired by list order; unavailable reference_partition mappings remain unpaired.",
            "No automatic reflection or candidate-fitted coordinate transform is applied.",
            "This source-model diagnostic has no typed reading-evidence applicability ledger, so it is not the full typed opening-claim score.",
        ],
    }


def _opening_inventory(source: dict[str, Any], exterior_rows: list[dict[str, Any]], unresolved: list[dict[str, Any]]) -> dict[str, Any]:
    built = [opening for opening in source.get("openings", []) if isinstance(opening, dict)]
    internal_doors = [opening for opening in built if opening.get("kind") == "door" and opening.get("exterior") is not True]
    return {
        "all_built_openings_by_kind": dict(Counter(str(opening.get("kind")) for opening in built)),
        "built_exterior_openings_by_kind": dict(Counter(row["kind"] for row in exterior_rows)),
        "built_exterior_openings": exterior_rows,
        "exterior_openings_with_unresolved_facade": unresolved,
        "built_internal_doors": [{"id": opening.get("id"), "space_ids": opening.get("space_ids", []),
                                   "host_boundary_id": opening.get("host_boundary_id")}
                                 for opening in internal_doors],
        "unbuilt_openings_by_kind": dict(Counter(str(opening.get("kind")) for opening in source.get("unbuilt_openings", []) if isinstance(opening, dict))),
        "limits": ["Only source['openings'] are built openings; unbuilt_openings are listed separately.",
                   "Typed sm24 exterior-door rows do not establish an inventory or count of internal doors."],
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evaluate(run: Path, out: Path | None = None) -> dict[str, Any]:
    run = run.resolve()
    summary = _load_completed_summary(run)
    target = (out or run / "evaluation").resolve()
    if target.exists():
        raise FileExistsError(f"evaluation destination already exists: {target}")
    candidate_paths = _candidate_dirs(run, summary["delivery"]["candidate"])
    gt_file = gt_path(CASE).resolve()
    gt = load_gt_document(CASE)
    if not isinstance(gt, GroundTruthV3):
        raise RuntimeError("sm24 evaluation requires its verified typed GT v3 document")
    if gt.verification.status != "human_verified":
        raise RuntimeError("sm24 typed GT is not human verified")
    reference_rows = _typed_reference_rows(gt)
    target.mkdir(parents=True)
    rows, sections = [], []
    for candidate in candidate_paths:
        proposal = json.loads((candidate / "proposal.json").read_text(encoding="utf-8"))
        source = json.loads((candidate / "source_model.json").read_text(encoding="utf-8"))
        geom = ensure_corrected_geometry(proposal["geometry"])
        partition = reference_partition(geom, gt, source_spaces=source["spaces"])
        exterior_rows, unresolved = _source_exterior_rows(source)
        mapped_rows, unmapped_rows = _map_source_rows_to_reference_floors(
            exterior_rows, partition.get("floor_mapping", {}))
        opening_diagnostic = _coordinate_diagnostic(mapped_rows, reference_rows,
                                                    unmapped_source_rows=unmapped_rows)
        windows = _coordinate_diagnostic(
            [row for row in mapped_rows if row["kind"] == "window"],
            [row for row in reference_rows if row["kind"] == "window"],
            unmapped_source_rows=[row for row in unmapped_rows if row["kind"] == "window"])
        inventory = _opening_inventory(source, exterior_rows, unresolved)
        prefix = candidate.name
        _write_json(target / f"{prefix}_partition.json", partition)
        _write_json(target / f"{prefix}_openings.json", {"source_to_reference_floor_mapping": partition.get("floor_mapping", {}),
                                                           "inventory": inventory,
                                                           "typed_exterior_opening_coordinate_diagnostic": opening_diagnostic,
                                                           "typed_window_coordinate_diagnostic": windows})
        row = {
            "candidate": prefix,
            "is_delivery_candidate": prefix == summary["delivery"]["candidate"],
            "source_model_sha256": source.get("source_model_sha256"),
            "partition_status": partition["status"],
            "source_to_reference_floor_mapping": partition.get("floor_mapping", {}),
            "reference_spaces": len(partition.get("reference_spaces", [])),
            "actual_source_spaces": len(source.get("spaces", [])),
            "opening_inventory": {key: inventory[key] for key in (
                "all_built_openings_by_kind", "built_exterior_openings_by_kind",
                "unbuilt_openings_by_kind")},
            "typed_window_coordinate_diagnostic": {
                "status": windows["status"], "comparison_count": len(windows["comparisons"]),
                "unresolved_group_count": len(windows["unresolved_groups"]),
                "not_a_complete_match_score": True,
            },
            "typed_exterior_opening_coordinate_diagnostic": {
                "status": opening_diagnostic["status"], "comparison_count": len(opening_diagnostic["comparisons"]),
                "unresolved_group_count": len(opening_diagnostic["unresolved_groups"]),
                "not_a_complete_match_score": True,
            },
            "topology_findings": partition.get("topology_findings", []),
            "internal_boundary_comparison": partition.get("internal_boundary_comparison", []),
        }
        rows.append(row)
        floors = sorted({space["floor_id"] for space in partition.get("reference_spaces", [])})
        figures = "".join(overlay(partition["reference_spaces"], partition["candidate_spaces"], floor_id)
                          for floor_id in floors)
        sections.append(
            f'<section><h2>{html.escape(prefix)}</h2><p>{"交付候选。" if row["is_delivery_candidate"] else "非交付候选。"}'
            f'<a href="../{html.escape(prefix)}/viewer.html">查看候选</a> · '
            f'<a href="{html.escape(prefix)}_partition.json">分区详情</a> · '
            f'<a href="{html.escape(prefix)}_openings.json">已建门窗与 typed 坐标诊断</a></p>'
            f'<pre>{html.escape(json.dumps(row, ensure_ascii=False, indent=2))}</pre>{figures}</section>')
    result = {
        "mode": "post_generation_evaluation_only",
        "case": CASE,
        "run": str(run),
        "run_summary_sha256": _sha256(run / "summary.json"),
        "run_completion_state": {
            "summary_present": True,
            "agent_response_completed": summary.get("agent_response_completed"),
            "has_viewable_candidate": summary.get("has_viewable_candidate"),
            "candidate_results": summary.get("candidate_results", []),
            "delivery": summary.get("delivery"),
            "reported_not_evaluated": summary.get("not_evaluated", []),
        },
        "reference": {"path": str(gt_file.relative_to(ROOT)), "file_sha256": _sha256(gt_file),
                      "content_sha256": gt.content_sha256, "schema_version": gt.schema_version,
                      "verification_status": gt.verification.status},
        "partition_basis": "reference_partition uses actual source_model spaces; GT never enters generation",
        "candidates": rows,
        "overall_fidelity": "not_automatically_decided",
        "limits": [
            "This is run-completion-only evaluation and was not supplied to the generating model.",
            "Partition comparison evaluates actual emitted source spaces, not a recovered or corrected substitute.",
            "Typed window/exterior-opening rows are coordinate diagnostics, not a complete typed opening-claim score or visual-fidelity verdict.",
            "The typed GT exterior-door data cannot prove an internal-door count or inventory.",
            "No candidate geometry, source model, or reference geometry is mutated.",
        ],
    }
    _write_json(target / "summary.json", result)
    page = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>sm24 生成后独立评价</title>'
            '<style>body{font:16px/1.6 system-ui;margin:30px;max-width:1200px}pre{white-space:pre-wrap;font-size:13px}'
            'section{margin:36px 0}figure{max-width:850px}a{color:#1263ad}</style>'
            '<h1>sm24 生成后独立评价</h1><p>本页只在运行完成后读取独立参照，未送回生成模型。蓝线为参照分区，橙线为实际输出的 source spaces。</p>'
            '<p>门窗部分使用 typed v3 世界坐标；等数量同楼层/立面/类型组才按世界轴顺序列出差值。它不是完整匹配评分，也不自动反射、拟合或判定图像保真。</p>'
            '<p>完整限制、GT 文件 SHA 与各候选汇总见 <a href="summary.json">summary.json</a>。</p>'
            + "".join(sections) + '</html>')
    (target / "index.html").write_text(page, encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="Completed run directory")
    parser.add_argument("--out", type=Path, help="New evaluation directory; defaults to RUN/evaluation")
    args = parser.parse_args()
    result = evaluate(args.run, args.out)
    print(json.dumps({"case": result["case"], "candidates": [
        {"candidate": row["candidate"], "partition_status": row["partition_status"],
         "window_coordinate_comparisons": row["typed_window_coordinate_diagnostic"]["comparison_count"]}
        for row in result["candidates"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
