"""Replay saved run90 frames without model calls or changes to old evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageOps

from src.agent.geometry.source_elevation_overlay import render_elevation_overlay

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-29_sm21_elevation_label_recovery_run90"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    source_path = RUN / "seed/source_model.json"
    source = json.loads(source_path.read_text())
    source_before = copy.deepcopy(source)
    frozen = RUN / "runtime_snapshot/src/agent/geometry/source_elevation_overlay.py"
    spec = importlib.util.spec_from_file_location("run90_overlay", frozen)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    protected = {p: sha(p) for p in [source_path, frozen,
        *sorted((RUN / "images").glob("*.png")),
        *sorted((RUN / "elevation_reviews").glob("*.json")),
        *sorted((RUN / "image_overlays").glob("*"))] if p.is_file()}
    rows, panels = [], []
    for review_path in sorted((RUN / "elevation_reviews").glob("*.json")):
        review = json.loads(review_path.read_text())
        original = Image.open(RUN / "images" / review["image"]).convert("RGB")
        original_pixels = original.tobytes()
        frame = dict(facade=review["facade"], horizontal_anchors=review["anchors"]["horizontal"],
                     z_anchors=review["anchors"]["absolute_z"], basis=review["basis"])
        before, before_meta = old.render_elevation_overlay(source, original, **frame)
        actual = Image.open(RUN / review["overlay_image"]).convert("RGB")
        assert ImageChops.difference(before, actual).getbbox() is None
        after, meta = render_elevation_overlay(source, original, **frame)
        assert all(meta[k] == v for k, v in before_meta.items() if k != "limits")
        assert after.size == original.size and original.tobytes() == original_pixels
        old_pixels, new_pixels = np.asarray(before), np.asarray(after)
        # Existing source wall/floor strokes are the only pixels that change.
        expected = old_pixels.copy()
        counts = {}
        for gray, key in ((160, "exterior_wall_edges"), (180, "floor_lines")):
            changed = np.any(old_pixels != new_pixels, axis=2)
            mask = changed & np.all(old_pixels == gray, axis=2)
            expected[mask] = meta["overlay_colours_rgb"][key]
            counts[key] = int(mask.sum())
            assert counts[key] > 0
        assert np.array_equal(expected, new_pixels)
        name = review["facade"]
        after.save(HERE / f"{name}.png")
        save(f"{name}.json", meta)
        rows.append(dict(facade=name, old_pixels_exactly_reproduced=True,
                         only_wall_floor_colour_pixels_changed=True,
                         geometry_calibration_labels_unchanged=True, recoloured_pixels=counts,
                         image_sha256=sha(HERE / f"{name}.png")))
        panels.append(f'<h2>{name}</h2><div class="pair"><figure><figcaption>上次实际送达</figcaption>'
                      f'<img src="../{RUN.name}/{review["overlay_image"]}"></figure>'
                      f'<figure><figcaption>改色后 · 同一模型和标定</figcaption>'
                      f'<a href="{name}.png"><img src="{name}.png"></a></figure></div>')
        if name == "East":
            white, white_meta = render_elevation_overlay(source, ImageOps.invert(original), **frame)
            white.save(HERE / "East_white_background.png")
            assert white_meta["projected_exterior_walls"] == meta["projected_exterior_walls"]
            for key in ("exterior_wall_edges", "floor_lines"):
                assert np.any(np.all(np.asarray(white) == meta["overlay_colours_rgb"][key], axis=2))
    assert source == source_before
    assert all(sha(p) == h for p, h in protected.items())
    save("report.json", dict(model_calls=0, gt_used=False, source_unchanged=True,
        protected_files_unchanged=len(protected), old_renderer_sha256=sha(frozen),
        renderer_sha256=sha(ROOT / "src/agent/geometry/source_elevation_overlay.py"),
        white_background_checked=True, frames=rows))
    (HERE / "comparison.html").write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>立面回叠全部几何着色</title><style>
body{background:#202124;color:#eee;font:16px system-ui;margin:24px}a{color:#72d6ff}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0}img{width:100%}
figcaption{margin:8px 0}@media(max-width:800px){.pair{grid-template-columns:1fr}}
</style><h1>立面回叠：原图灰度，生成几何彩色</h1>
<p>青蓝＝外墙边界（含房间分段）；绿色＝楼层基准；橙色＝窗；紫色＝门/开放通道。</p>
<p>离线重绘，不是新增生成结果。保留上次标定及其误差；东首层窗顶低约19.5厘米的问题仍在。</p>
''' + "\n".join(panels) + '<p><a href="East_white_background.png">白底适配查看</a></p></html>')
    print(json.dumps({"frames": len(rows), "protected_files": len(protected), "model_calls": 0}))


if __name__ == "__main__":
    main()
