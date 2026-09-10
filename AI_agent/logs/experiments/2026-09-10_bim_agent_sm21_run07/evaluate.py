"""Post-run evaluation only; never provided to the generator's MCP tools."""
from collections import Counter
from dataclasses import asdict
import html
import json
from pathlib import Path
import sys

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
sys.path.insert(0, str(ROOT))

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.judge.gt import load_gt_document, gt_path
from src.agent.judge.partition_evidence import reference_partition
from src.agent.judge.elevation_score import score_correction_elevation_windows
from scripts.tool_scripts.diagnose_partition_evidence import overlay
from scripts.tool_scripts.run_bim_agent import digest, dump


def main():
    if not (RUN / "summary.json").exists():
        raise RuntimeError("evaluation must wait until generator finishes")
    target=RUN / "evaluation"
    target.mkdir(exist_ok=False)
    gt=load_gt_document("sm21_anchor")
    rows=[]; sections=[]
    for candidate in sorted(RUN.glob("candidate_*")):
        if not (candidate/"source_model.json").exists(): continue
        proposal=json.loads((candidate/"proposal.json").read_text())
        source=json.loads((candidate/"source_model.json").read_text())
        geom=ensure_corrected_geometry(proposal["geometry"])
        report=reference_partition(geom,gt,source_spaces=source["spaces"])
        dump(target/f"{candidate.name}_partition.json",report)
        built_window_ids={o["id"] for o in source["openings"] if o["kind"]=="window"}
        built_geom=geom.model_copy(deep=True)
        built_geom.windows=[w for w in geom.windows if w.id in built_window_ids]
        window_score=score_correction_elevation_windows(built_geom,gt.model_dump(mode="json"),
            floor_map=report.get("floor_mapping",{}),evidence=[])
        dump(target/f"{candidate.name}_windows.json",asdict(window_score))
        counts=Counter(o["kind"] for o in source["openings"])
        row={"candidate":candidate.name,"source_sha256":source["source_model_sha256"],
             "partition_status":report["status"],
             "reference_spaces":len(report.get("reference_spaces",[])),
             "candidate_spaces":len(source["spaces"]),"openings":dict(counts),
             "built_window_comparison":window_score.summary(),
             "topology_findings":report.get("topology_findings",[]),
             "internal_boundary_comparison":report.get("internal_boundary_comparison",[])}
        rows.append(row)
        figures="".join(overlay(report["reference_spaces"],report["candidate_spaces"],fid)
            for fid in sorted({s["floor_id"] for s in report.get("reference_spaces",[])}))
        sections.append(f'<section><h2>{html.escape(candidate.name)}</h2>'
            f'<a href="../{candidate.name}/viewer.html">查看三维候选</a>'
            f'<pre>{html.escape(json.dumps(row,ensure_ascii=False,indent=2))}</pre>{figures}</section>')
    result={"mode":"post_generation_evaluation_only","reference_path":str(gt_path("sm21_anchor").relative_to(ROOT)),
            "reference_sha256":digest(gt_path("sm21_anchor")),"candidates":rows,
            "limits":["GT window and door completeness not certified by partition comparison",
                      "GT door list contains exterior doors only; not an internal-door inventory",
                      "Reference-plane differences retain their existing evaluator interpretation",
                      "No evaluation feedback supplied to generating model"]}
    dump(target/"summary.json",result)
    (target/"index.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<title>原图生成后的独立分区对照</title><style>body{font:16px system-ui;margin:30px;max-width:1200px}'
        'pre{white-space:pre-wrap;font-size:13px}figure{max-width:850px}section{margin-bottom:40px}</style>'
        '<h1>原图生成后的独立分区对照</h1><p>本页在生成结束后计算，未送回生成模型。蓝线为参照，橙线为候选。'
        '分区检查不等于门窗或整图验收；详情与限制见 summary.json。</p>'+''.join(sections)+'</html>',encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
