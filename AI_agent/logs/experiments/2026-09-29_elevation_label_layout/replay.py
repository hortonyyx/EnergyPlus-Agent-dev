"""Offline layout comparison using the unchanged run89 source and model frames."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

from src.agent.geometry import source_elevation_overlay as current
from src.agent.geometry.source_elevation_overlay import render_elevation_overlay

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-29_sm21_calibrated_elevation_recovery_run89"


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    frozen = RUN / "runtime_snapshot/src/agent/geometry/source_elevation_overlay.py"
    spec = importlib.util.spec_from_file_location("previous_elevation_overlay", frozen)
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    spec = importlib.util.spec_from_file_location("label_only_overlay", HERE / "label_only_renderer.py")
    label_only = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(label_only)
    reviews = sorted((RUN / "elevation_reviews").glob("*.json"))
    protected = {path: sha(path) for path in [
        *reviews, *sorted((RUN / "images").glob("*.png")),
        *sorted((RUN / "image_overlays").glob("*.png")),
        RUN / "seed/source_model.json", RUN / "candidate_01/source_model.json"]}
    records = []
    panels = []
    for review_path in reviews:
        review = load(review_path)
        for candidate in ("seed", "candidate_01"):
            source = load(RUN / candidate / "source_model.json")
            original = Image.open(RUN / "images" / review["image"]).convert("RGB")
            before_source, before_pixels = copy.deepcopy(source), original.tobytes()
            frame = dict(facade=review["facade"], horizontal_anchors=review["anchors"]["horizontal"],
                         z_anchors=review["anchors"]["absolute_z"], basis=review["basis"])
            old, old_meta = previous.render_elevation_overlay(source, original, **frame)
            if candidate == "seed":
                actual = Image.open(RUN / review["overlay_image"]).convert("RGB")
                assert ImageChops.difference(old, actual).getbbox() is None
            with patch.object(previous, "_label", lambda *a, **k: None):
                geometry_only, _ = previous.render_elevation_overlay(source, original, **frame)
            coloured, _ = label_only.render_elevation_overlay(source, original, **frame)
            with patch.object(current, "_opening_labels", lambda *a, **k: []):
                grey_geometry_only, _ = render_elevation_overlay(source, original, **frame)
            new, metadata = render_elevation_overlay(source, original, **frame)
            assert source == before_source and original.tobytes() == before_pixels
            assert old.size == new.size == original.size
            assert all(metadata[k] == v for k, v in old_meta.items() if k != "limits")
            base = np.asarray(geometry_only)
            ink = base.max(axis=2) > 32  # All real CAD samples have a black background.
            old_hidden = int((np.any(np.asarray(old) != base, axis=2) & ink).sum())
            grey_base = np.asarray(grey_geometry_only)
            new_hidden = int((np.any(np.asarray(new) != grey_base, axis=2) & (grey_base.max(axis=2) > 32)).sum())
            assert new_hidden == 0, (review_path.name, candidate, new_hidden)
            assert metadata["reference_background"] == "grayscale_copy_original_file_unchanged"
            # All remaining chromatic pixels belong to generated opening
            # outlines/labels, since reference pixels are now neutral grey.
            # Anti-aliased text blends with its black backing; check geometry
            # independently, where only exact assigned colours are present.
            geometry_chromatic = grey_base.max(axis=2) - grey_base.min(axis=2) > 12
            assert all(tuple(c) in {tuple(v) for v in metadata["opening_colours_rgb"].values()}
                       for c in np.unique(grey_base[geometry_chromatic], axis=0))
            name = f"{review_path.stem}_{review['facade']}_{candidate}"
            old.save(HERE / f"{name}_before.png")
            coloured.save(HERE / f"{name}_colour_base.png")
            new.save(HERE / f"{name}_after.png")
            save(f"{name}.json", metadata)
            records.append(dict(review=review_path.name, candidate=candidate, facade=review["facade"],
                                old_annotation_covered_ink_pixels=old_hidden,
                                new_annotation_covered_ink_pixels=new_hidden,
                                placed=sum(x["status"] == "placed" for x in metadata["opening_labels"]),
                                omitted=[x["id"] for x in metadata["opening_labels"] if x["status"] != "placed"],
                                same_frame_geometry_and_source=True, output=f"{name}_after.png"))
            panels.append(f'<h2>{review["facade"]} · {candidate} · {review_path.stem}</h2>'
                          f'<div class="pair"><figure><figcaption>旧标签</figcaption><a href="{name}_before.png">'
                          f'<img src="{name}_before.png"></a></figure><figure><figcaption>侧面标签 · 原彩色底</figcaption>'
                          f'<a href="{name}_colour_base.png"><img src="{name}_colour_base.png"></a></figure>'
                          f'<figure><figcaption>侧面标签 · 灰度底 · 橙窗紫门</figcaption>'
                          f'<a href="{name}_after.png"><img src="{name}_after.png"></a></figure></div>')
            if review["facade"] == "East" and candidate == "seed":
                row = next(o for o in metadata["projected_openings"] if o["id"] == "F1:W7")
                x = min(p[0] for p in row["pixel_vertices"])
                y = min(p[1] for p in row["pixel_vertices"])
                box = (int(x) - 45, int(y) - 45, int(x) + 200, int(y) + 115)
                for label, picture in (("before", old), ("colour_base", coloured), ("after", new)):
                    picture.crop(box).resize((735, 480), Image.Resampling.NEAREST).save(HERE / f"east_detail_{label}.png")
                assert old_hidden > 0
                assert next(x for x in metadata["opening_labels"] if x["id"] == "F1:W7")["status"] == "placed"
            if review["facade"] == "West" and review_path.stem == "review_0004" and candidate == "seed":
                row = next(o for o in metadata["projected_openings"] if o["kind"] == "door")
                xs, ys = zip(*row["pixel_vertices"])
                box = (int(min(xs)) - 25, int(min(ys)) - 25, int(max(xs)) + 115, int(max(ys)) + 25)
                for label, picture in (("before", old), ("colour_base", coloured), ("after", new)):
                    crop = picture.crop(box)
                    crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.NEAREST).save(HERE / f"door_detail_{label}.png")

    # Check the layout's conservative fallback and light-background behavior,
    # without adding synthetic constraints to the production reading task.
    source = load(RUN / "seed/source_model.json")
    frame = dict(facade="East", horizontal_anchors=[[287, 0], [746, 8]],
                 z_anchors=[[554, 0], [174, 6.6]], basis="Replay of model-selected frame")
    original = Image.open(RUN / "images/East_view.png").convert("RGB")
    white = ImageOps.invert(original)
    with patch.object(current, "_opening_labels", lambda *a, **k: []):
        base_white, _ = render_elevation_overlay(source, white, **frame)
    result_white, white_meta = render_elevation_overlay(source, white, **frame)
    base_array = np.asarray(base_white)
    changed = np.any(np.asarray(result_white) != base_array, axis=2)
    assert not (changed & (base_array.min(axis=2) < 223)).any()
    assert all(x["status"] == "placed" for x in white_meta["opening_labels"])
    result_white.save(HERE / "east_white_background.png")
    busy = Image.new("RGB", original.size, "white")
    draw = ImageDraw.Draw(busy)
    for y in range(0, busy.height, 4):
        draw.line((0, y, busy.width - 1, y), fill="black")
    _, busy_meta = render_elevation_overlay(source, busy, **frame)
    assert all(x["status"] == "omitted" for x in busy_meta["opening_labels"])
    assert {x["id"] for x in busy_meta["opening_labels"]} == {x["id"] for x in busy_meta["projected_openings"]}
    from src.agent.geometry.source_model import _digest
    from tests.test_source_elevation_view import _source
    passage = _source()
    next(o for o in passage["openings"] if o["id"] == "north-door")["kind"] = "open"
    passage["source_model_sha256"] = _digest({k: v for k, v in passage.items() if k != "source_model_sha256"})
    _, passage_meta = render_elevation_overlay(passage, Image.new("RGB", (500, 700)), facade="North",
        horizontal_anchors=[[50, 4], [450, 0]], z_anchors=[[650, 0], [50, 6]], basis="Synthetic open-passage check")
    assert any(o["kind"] == "open" for o in passage_meta["projected_openings"])
    assert all(sha(path) == value for path, value in protected.items())
    save("report.json", dict(model_calls=0, gt_used=False, protected_files_unchanged=len(protected),
                             old_renderer_sha256=sha(frozen),
                             new_renderer_sha256=sha(ROOT / "src/agent/geometry/source_elevation_overlay.py"),
                             real_replays=records, white_background_ink_preserved=True,
                             grayscale_reference_and_fixed_opening_colours=True, open_passage_supported=True,
                             dense_background_omits_labels_but_retains_ids=True,
                             limitations="Offline display correction only; window heights and model recognition are unchanged/unverified."))
    (HERE / "comparison.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>立面编号与配色对照</title>'
        '<style>body{background:#202124;color:#eee;font:16px sans-serif;margin:24px}.pair{display:flex;gap:16px}'
        'figure{margin:0;flex:1;min-width:0}img{width:100%;height:auto}figcaption{padding:10px}a{color:#acf}</style>'
        '<h1>立面编号与配色：同源、同标定离线对照</h1>'
        '<p>原文件保持彩色；对照底图转灰度，生成窗为橙色，门及开放通道为紫色，编号避让图线。窗高、投影和画布不变。'
        '未调用模型，未证明识读或质量恢复。点击全图查看原分辨率。</p>'
        '<div class="pair"><figure><figcaption>门局部：旧图</figcaption><img src="door_detail_before.png"></figure>'
        '<figure><figcaption>仅改标签 · 彩色底</figcaption><img src="door_detail_colour_base.png"></figure>'
        '<figure><figcaption>灰度底 · 紫色生成门</figcaption><img src="door_detail_after.png"></figure></div>'
        '<div class="pair"><figure><figcaption>东窗局部：旧标签</figcaption><img src="east_detail_before.png"></figure>'
        '<figure><figcaption>东窗局部：新标签</figcaption><img src="east_detail_after.png"></figure></div>' + ''.join(panels))
    print(json.dumps(dict(replays=len(records), covered_ink_before=sum(r["old_annotation_covered_ink_pixels"] for r in records),
                          covered_ink_after=0, placed=sum(r["placed"] for r in records),
                          omitted=sum(len(r["omitted"]) for r in records)), ensure_ascii=False))


if __name__ == "__main__":
    main()
