"""Render five admitted historical plan images offline, keeping only QA metadata."""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
REPORT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.tool_scripts.run_bim_agent import Toolkit
from src.agent.runtime_roles.plan_views import view_plan_blocks


async def main():
    base = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup")
    rows = []
    for case, relative in (("sm24", "cmp3/sm24_role"), ("sm21", "cmp3/sm21_role"),
                           ("sm25", "merged/sm25_role_n1")):
        source = base / relative / "bim"
        manifest = json.loads((source / "inputs.json").read_bytes())
        for name in manifest["floor_plan_images"]:
            run = ROOT / "AI_agent/archive/local_backup/d1l/block-proof" / case / Path(name).stem
            (run / "images").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / "images" / name, run / "images" / name)
            (run / "inputs.json").write_text(json.dumps({"images": {name: manifest["images"][name]}},
                ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
            result = await view_plan_blocks(SimpleNamespace(run_directory=run), name)
            payload = result["structuredContent"]
            previews = payload["evidence_previews"]
            assert len(previews) in {4, 6, 8} and payload["coverage"]["complete"]
            for block, view in zip(result["content"][:-1], previews, strict=True):
                raw = base64.b64decode(block["data"])
                assert view["display_scale_actual"] == [3.0, 3.0]
                assert view["coordinate_grid"]["shown"]
                assert hashlib.sha256(raw).hexdigest() == view["returned_png_sha256"]
                assert Toolkit(run).read_image_view(view["view_id"])["sha256"] == view["view_record_sha256"]
            if case == "sm25" and name == "1f_view.png":
                (run / "preview.png").write_bytes(base64.b64decode(result["content"][0]["data"]))
            rows.append({"case": case, "image": name, "image_sha256": payload["image_sha256"],
                         "size": payload["original_size"], "blocks": len(previews), "grid": payload["grid"],
                         "coverage_complete": True, "shared_view_record_readback_passed": True,
                         "views": payload["views"]})
    (REPORT / "block_layout_evidence.json").write_text(json.dumps({"model_requests": 0, "cases": rows},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps([{key: value for key, value in row.items() if key != "views"} for row in rows], ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
