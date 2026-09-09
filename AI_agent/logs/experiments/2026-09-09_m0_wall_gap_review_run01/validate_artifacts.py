"""Offline artifact verification and independent judge report; no model calls."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.diagnose_partition_evidence import overlay
from src.agent.judge.gt import gt_path, load_gt_document
from src.agent.judge.partition_evidence import attempt_partition_evidence


def validate():
    run = Path(__file__).resolve().parent
    html = (run / "viewer.html").read_text()
    match = re.search(r"window\.GEO\s*=\s*", html)
    geo, _ = json.JSONDecoder().raw_decode(html[match.end():])
    surfaces = {s["name"]: s for s in geo["surfaces"]}
    errors = []
    for parent, parts in geo["visible_wall_parts"].items():
        surface = surfaces[parent]
        axis = max((0, 1), key=lambda i: max(p[i] for p in surface["verts"]) - min(p[i] for p in surface["verts"]))
        def ring(vertices):
            return [(p[axis], p[2]) for p in vertices]
        full = Polygon(ring(surface["verts"]))
        holes = unary_union([Polygon(ring(o["verts"])) for o in geo["openings"] if o["parent"] == parent])
        visible = unary_union([Polygon(ring(p["verts"]), [ring(h) for h in p.get("holes", [])]) for p in parts])
        errors.append(visible.symmetric_difference(full.difference(holes)).area)
        assert visible.intersection(holes).area < 1e-9
    assert max(errors) < 1e-9
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    with tempfile.TemporaryDirectory() as temp:
        for i, script in enumerate(scripts):
            path = Path(temp) / f"script{i}.js"
            path.write_text(script)
            subprocess.run(["node", "--check", str(path)], check=True, capture_output=True)
    report = json.loads((run / "report.json").read_text())
    assert len(geo["source_model"]["spaces"]) == report["building"]["spaces"] == 29
    assert len(geo["windows"]) == 31
    previous = json.loads((run.parent / "2026-09-09_m0_endpoint_connections_run01/2_modelling/building_geometry.json").read_text())
    def window_vertices(model):
        return sorted(tuple(sorted(tuple(v) for v in w["verts"])) for w in model["windows"])
    assert window_vertices(previous) == window_vertices(geo)
    assert len(geo["source_model"]["openings"]) == 60  # 31 windows + 29 doors
    assert len(geo["openings"]) == 55
    assert not report["correction"]["accepted"]
    assert report["building"]["source_mapping"]["status"] == "pass"
    account = report["opening_account"]
    assert account["observations_considered"] == 61 and len(account["unbuilt"]) == 2
    assert [r["observation_ids"] for r in account["reclassified"]] == [["L042g0"]]
    ids = [(r["input_id"], oid) for r in account["built"] + account["unbuilt"] + account["reclassified"] for oid in r["observation_ids"]]
    assert len(ids) == len(set(ids)) == 61
    for row in report["manifest"]["inputs"]:
        assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"]
    evidence = attempt_partition_evidence(run, run / "1_correction/attempts/001",
                                         document=load_gt_document("sm25-L_anchor"), reference_path=gt_path("sm25-L_anchor"))
    ref = evidence["reference_partition"]
    assert ref["status"] == "not_evaluated" and not ref["topology_findings"]
    assert all(r["missing_length_m"] == r["extra_length_m"] == 0 for r in ref["internal_boundary_comparison"])
    (run / "partition_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    figures = "".join(overlay(ref["reference_spaces"], ref["candidate_spaces"], f) for f in ("F1", "F2"))
    (run / "partition.html").write_text('''<!doctype html><html lang="zh"><meta charset="utf-8"><title>辅助重建后的分区对照</title>
<style>body{font:16px/1.8 system-ui;max-width:1100px;margin:32px auto;padding:20px}figure{display:inline-block;width:46%;margin:1%}svg{width:100%}@media(max-width:650px){figure{width:98%}}</style>
<h1>辅助重建后的分区对照</h1><p>原图辅助核对三处墙缺口后，29 个空间与参照逐空间对照；未再发现内部拆并和额外隔墙。外边界参考面差异仍保留，整体未判为全部通过。</p>
<p>蓝线：独立 GT；橙线：新候选。GT 只进入本页的事后评价，不进入重建。</p>''' + figures +
'''<p><a href="viewer.html">查看三维源模型</a> · <a href="partition_evidence.json">完整评价证据</a> · <a href="index.html">开口及未完成项</a></p></html>''', encoding="utf-8")
    result = {"status": "pass", "spaces": 29, "windows": 31, "doors": 29, "derived_openings": 55,
              "window_world_vertices_unchanged": True, "cut_parent_faces": len(errors),
              "max_wall_difference_area_error_m2": max(errors), "inline_scripts_checked": len(scripts),
              "positive_observations_accounted_once": 61, "reclassified_observations": 1,
              "internal_partition_findings": 0, "overall_partition_status": ref["status"],
              "not_evaluated": ["browser rendering", "complete opening reading", "EnergyPlus", "source approval"]}
    (run / "artifact_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False))
