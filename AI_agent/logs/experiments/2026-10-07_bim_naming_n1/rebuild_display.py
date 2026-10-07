"""N1 offline evidence: copy four deliveries, then redraw their saved sources.

Run from the activated worktree root. No providers, solvers or main-tree writes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.tool_scripts.bim_agent_delivery_display import render_delivery_html
from src.agent.execution.source_proposal import build_source_viewer_html
from src.agent.geometry.source_bim import source_view_geometry
from src.agent.geometry.source_naming import public_names_for_display, viewer_names
from src.agent.geometry.source_plan_view import render_source_plan

RUNS = ("sm24_single", "sm24_role", "sm21_role", "sm21_single")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(
        r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\cmp3"))
    parser.add_argument("--output-root", type=Path, default=ROOT / "AI_agent/archive/local_backup/n1")
    args = parser.parse_args()
    source_root, output_root = args.source_root.resolve(), args.output_root.resolve()
    allowed_root = (ROOT / "AI_agent/archive/local_backup/n1").resolve()
    if not output_root.is_relative_to(allowed_root) or output_root == source_root:
        raise ValueError("Outputs must stay inside this worktree's N1 artifact directory")
    output_root.mkdir(parents=True, exist_ok=True)
    manifest, comparisons, cards = [], [], []
    for run in RUNS:
        original = source_root / run / "bim"
        delivery = read(original / "delivery.json")
        candidate = delivery["candidate"]
        selection = read(original / "delivery_selection.json")
        assert selection["candidate"] == candidate
        # First preserve selected inputs verbatim; never redraw in the main tree.
        snapshot = output_root / "snapshots" / run / "bim"
        paths = [p.relative_to(original) for p in (original / candidate).rglob("*") if p.is_file()]
        paths += [Path("delivery.json"), Path("delivery_selection.json")]
        paths += [Path(p["overlay_image"]) for p in delivery["source_image_feedback"]["current_source_projections"]]
        original_hashes = {}
        for relative in paths:
            src, dst = original / relative, snapshot / relative
            assert src.resolve().is_relative_to(original.resolve())
            assert dst.resolve().is_relative_to(snapshot.resolve())
            original_hashes[relative.as_posix()] = digest(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                assert digest(dst) == digest(src), f"Saved snapshot differs: {dst}"
            else:
                shutil.copyfile(src, dst)
        source_path = snapshot / candidate / "source_model.json"
        source = read(source_path)
        before = copy.deepcopy(source)
        assert source["source_model_sha256"] == selection["source_model_sha256"] == delivery["source_model_sha256"]
        names = public_names_for_display(source)
        display = source_view_geometry(source)
        mapped = viewer_names(display, display["display_surface_parts"])
        assert mapped["spaces"] == names["spaces"]
        assert all(len(name.split("_")) == 4 for name in names["spaces"].values())
        assert len(names["spaces"]) == len(set(names["spaces"].values()))
        output = output_root / "rendered" / run / "bim"
        candidate_out = output / candidate
        candidate_out.mkdir(parents=True, exist_ok=True)
        for relative in [Path("delivery.json"), Path("delivery_selection.json")]:
            shutil.copyfile(snapshot / relative, output / relative)
        for filename in ("source_model.json", "report.json", "proposal.json"):
            shutil.copyfile(snapshot / candidate / filename, candidate_out / filename)
        for row in delivery["source_image_feedback"]["current_source_projections"]:
            target = output / row["overlay_image"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(snapshot / row["overlay_image"], target)
        write(candidate_out / "public_names.json", names)
        report = read(snapshot / candidate / "report.json")
        viewer = build_source_viewer_html(display, source_geometry_ready=report["source_geometry_ready"],
                                         assumptions=report["agent_assumptions"], unresolved=report["unresolved"])
        (candidate_out / "viewer.html").write_text(viewer, encoding="utf-8", newline="\n")
        (output / "delivery.html").write_text(render_delivery_html(delivery, source), encoding="utf-8", newline="\n")
        plans = []
        for floor_id, floor_name in names["floors"].items():
            image, metadata = render_source_plan(source, floor_id)
            image.save(candidate_out / f"plan_{floor_name}.png")
            write(candidate_out / f"plan_{floor_name}.json", metadata)
            assert all(mapped["spaces"][sid] == name for sid, name in metadata["space_names"].items())
            plans.append(f"{candidate}/plan_{floor_name}.png")
        for sid, name in names["spaces"].items():
            comparisons.append({"run": run, "source_id": sid,
                                "before": source["public_names"]["spaces"][sid], "after": name})
        southern = [name for sid, name in names["spaces"].items()
                    if "_F2_Office" in name and name.rsplit("_", 1)[-1].startswith(("SW", "SE"))]
        if run.startswith("sm21"):
            assert [name.rsplit("_", 1)[-1] for name in southern] == ["SW1", "SW2", "SE1", "SE2"]
        assert source == before
        assert digest(candidate_out / "source_model.json") == digest(source_path)
        assert read(output / "delivery.json") == delivery
        assert all(digest(original / path) == value for path, value in original_hashes.items())
        manifest.append({"run": run, "candidate": candidate, "source_model_sha256": source["source_model_sha256"],
                         "source_file_sha256": digest(source_path), "naming_scheme": names["scheme_version"],
                         "source_and_delivery_unchanged": True, "original_files_sha256": original_hashes,
                         "space_count": len(names["spaces"]), "plan_viewer_names_match": True,
                         "south_offices_F2": southern, "plans": plans})
        base = f"{run}/bim/"
        card = (f'<section><h2>{run} · {candidate}</h2>'
                f'<p><a href="{base}{candidate}/viewer.html">查看页</a> · '
                f'<a href="{base}delivery.html">交付报告</a> · '
                f'<a href="{base}{candidate}/public_names.json">v3 名字映射</a></p>')
        card += "".join(f'<a href="{base}{p}"><img src="{base}{p}" alt="{run} {Path(p).stem}"></a>' for p in plans)
        cards.append(card + "</section>")
    write(output_root / "verification.json", {"model_calls": 0, "solver_calls": 0, "runs": manifest})
    write(output_root / "name_comparison.json", comparisons)
    markdown = "# N1 四份交付稿公开名对照\n\n| 稿件 | 原内部编号（仅追溯） | 改前 | 改后 |\n|---|---|---|---|\n"
    markdown += "".join(f'| {r["run"]} | `{r["source_id"]}` | `{r["before"]}` | `{r["after"]}` |\n' for r in comparisons)
    (output_root / "name_comparison.md").write_text(markdown, encoding="utf-8", newline="\n")
    (output_root / "rendered/index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>N1 命名离线验收</title>'
        '<style>body{font:16px system-ui;margin:24px auto;max-width:1200px}img{width:48%;border:1px solid #ddd}'
        'section{border-top:1px solid #ddd;padding:12px 0}a{color:#245ab8}</style>'
        '<h1>N1 命名离线验收</h1><p>四份已保存交付稿的 v3 显示。源几何、分类和旧检查记录未改；未重新评价原图保真。</p>'
        + "".join(cards), encoding="utf-8", newline="\n")
    print(json.dumps({"runs": len(manifest), "spaces": len(comparisons),
                      "plans": sum(len(row["plans"]) for row in manifest), "index": str(output_root / "rendered/index.html")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
