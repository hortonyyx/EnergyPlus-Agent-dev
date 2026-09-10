"""Compare saved BIM candidates with a reference after generation has ended.

Reference data never enters the generating agent. For partial inference, the
reference layout is diagnostic only: unprovided interiors are not reconstruction
targets. This reuses the existing partition/window evaluators without changing
their tolerances or treating a geometry pass as drawing fidelity.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.judge.gt import load_gt_document, gt_path
from src.agent.judge.gt_schema import LegacyGroundTruthV2
from src.agent.judge.partition_evidence import reference_partition
from src.agent.judge.elevation_score import score_correction_elevation_windows
from scripts.tool_scripts.diagnose_partition_evidence import overlay
from scripts.tool_scripts.run_bim_agent import digest, dump


def evaluate(run: Path, reference_case: str, *, modelling_task: str,
             reference_scope: str, out: Path | None = None) -> dict:
    run = run.resolve()
    if not (run / "summary.json").is_file():
        raise RuntimeError("evaluation must wait until generator finishes")
    target = out.resolve() if out is not None else run / "evaluation"
    gt = load_gt_document(reference_case)
    if gt is None:
        raise ValueError(f"no verified reference available for {reference_case}")
    reference_path = gt_path(reference_case).resolve()
    target.mkdir(parents=True, exist_ok=False)
    candidates = ([run / "seed"] if (run / "seed/source_model.json").is_file() else [])
    candidates += sorted(p for p in run.glob("candidate_*") if (p / "source_model.json").is_file())
    rows, sections = [], []
    for candidate in candidates:
        proposal = json.loads((candidate / "proposal.json").read_text())
        source = json.loads((candidate / "source_model.json").read_text())
        geom = ensure_corrected_geometry(proposal["geometry"])
        report = reference_partition(geom, gt, source_spaces=source["spaces"])
        dump(target / f"{candidate.name}_partition.json", report)
        built_window_ids = {o["id"] for o in source["openings"] if o["kind"] == "window"}
        built_geom = geom.model_copy(deep=True)
        built_geom.windows = [w for w in geom.windows if w.id in built_window_ids]
        if isinstance(gt, LegacyGroundTruthV2):
            window_score = score_correction_elevation_windows(
                built_geom, gt.model_dump(mode="json"), floor_map=report.get("floor_mapping", {}), evidence=[])
            dump(target / f"{candidate.name}_windows.json", asdict(window_score))
            window_summary = window_score.summary()
        else:
            # The old elevation scorer accepts v2 only. Do not flatten a typed
            # v3 reference or manufacture an empty denominator from its shape.
            window_summary = {
                "status": "not_evaluated",
                "reason": "typed_v3_window_comparison_not_integrated_in_this_diagnostic",
                "reference_window_count": sum(o.kind == "window" for o in gt.openings),
                "built_window_count": len(built_window_ids),
                "count_is_not_a_match_score": True,
            }
            dump(target / f"{candidate.name}_windows.json", window_summary)
        row = {
            "candidate": candidate.name, "is_recovery_seed": candidate.name == "seed",
            "source_sha256": source["source_model_sha256"],
            "partition_status": report["status"],
            "reference_spaces": len(report.get("reference_spaces", [])),
            "candidate_spaces": len(source["spaces"]),
            "openings": dict(Counter(o["kind"] for o in source["openings"])),
            "built_window_comparison": window_summary,
            "topology_findings": report.get("topology_findings", []),
            "internal_boundary_comparison": report.get("internal_boundary_comparison", []),
        }
        rows.append(row)
        figures = "".join(overlay(report["reference_spaces"], report["candidate_spaces"], fid)
                          for fid in sorted({s["floor_id"] for s in report.get("reference_spaces", [])}))
        sections.append(f'<section><h2>{html.escape(candidate.name)}</h2>'
                        f'<pre>{html.escape(json.dumps(row, ensure_ascii=False, indent=2))}</pre>'
                        f'{figures}</section>')
    caution = (
        "部分推理建模：完整参照只用于事后诊断。未提供的内部格局不能按还原任务判漏房或错分区；"
        "另行检查输入约束、推断合理性、源简化说明和几何可用性。"
        if modelling_task == "partial_inference" else
        "还原建模：以下为独立参照差异，不自动等于原图保真或整案验收。")
    result = {
        "mode": "post_generation_evaluation_only", "modelling_task": modelling_task,
        "reference_scope": reference_scope, "interpretation": caution,
        "input_manifest_sha256": digest(run / "inputs.json"),
        "reference_case": reference_case,
        "reference_path": str(reference_path.relative_to(ROOT)),
        "reference_sha256": digest(reference_path), "candidates": rows,
        "overall_fidelity": "not_automatically_decided",
        "limits": [
            "Reference completeness and original pixel truth require separate evidence.",
            "Partition comparison does not verify doors, connectivity, or vertical voids.",
            "Reference-plane differences retain their existing evaluator interpretation.",
            "No evaluation feedback supplied to the generating model.",
        ],
    }
    dump(target / "summary.json", result)
    (target / "index.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<title>BIM 生成后的独立参照诊断</title><style>body{font:16px system-ui;margin:30px;max-width:1200px}'
        'pre{white-space:pre-wrap;font-size:13px}figure{max-width:850px}section{margin-bottom:40px}</style>'
        '<h1>BIM 生成后的独立参照诊断</h1>'
        f'<p>{html.escape(caution)}</p><p>参照范围：{html.escape(reference_scope)}</p>'
        '<p>本页在生成结束后计算，未送回生成模型。蓝线为参照，橙线为候选。'
        '详情与限制见 <a href="summary.json">summary.json</a>。</p>'
        + ''.join(sections) + '</html>', encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--reference-case", required=True)
    parser.add_argument("--modelling-task", choices=["reconstruction", "partial_inference"], required=True)
    parser.add_argument("--reference-scope", required=True,
                        help="Describe supplied vs withheld evidence and legitimate reference comparisons")
    parser.add_argument("--out", type=Path, help="New output directory; defaults to RUN/evaluation")
    args = parser.parse_args()
    result = evaluate(args.run, args.reference_case, modelling_task=args.modelling_task,
                      reference_scope=args.reference_scope, out=args.out)
    print(json.dumps({"modelling_task": result["modelling_task"],
                      "candidates": [{k: r[k] for k in ("candidate", "partition_status", "built_window_comparison")}
                                     for r in result["candidates"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
