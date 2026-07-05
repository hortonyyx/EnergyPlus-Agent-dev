"""Prototype 6 — grade sheet fixes.

Fixes over proto5:
 1. red dashed overlap bug: interior walls are now drawn ONCE per merged segment
    (dedup zone-shared edges) so dashes have a single clean phase.
 2. missing window gets a light-red fill (not just an empty dashed box).
 3. a "wrong-position window" example: gt slot = miss ghost (light-red), product
    at the wrong place = extra (red solid), linked by a grey 'displaced' connector.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

RUN = Path("case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e")
GT = json.loads(Path("case_tests/test_baseline/gt/sm21_anchor/gt.json").read_text())
RS = json.loads((RUN / "0_reading/attempts/001/score_vs_gt.json").read_text())["scores"]
CS = json.loads((RUN / "1_correction/attempts/001/score_vs_gt.json").read_text())["scores"]

BG = (250, 250, 248); GT_FILL = (238, 238, 234); GT_EDGE = (208, 208, 203)
GREEN = (52, 150, 96); RED = (208, 46, 36)
FILL_G = (224, 240, 230); FILL_R = (250, 226, 222)
BAND = (198, 228, 206); TRUTH = (148, 148, 142)
TEXT = (40, 40, 40); SUBTLE = (112, 112, 106)
SCALE = 50.0; M = 1.15
W = float(GT["footprint"]["W_m"]); D = float(GT["footprint"]["D_m"])
WALL_TOL = 0.30; CUE_EPS = 0.05; EPS = 0.30


def _f(sz):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def dashed(d, p1, p2, fill, w, dash=8, gap=5):
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    L = (dx * dx + dy * dy) ** 0.5
    if not L:
        return
    ux, uy = dx / L, dy / L
    t = 0.0
    while t < L:
        s = min(t + dash, L)
        d.line([(x1 + ux * t, y1 + uy * t), (x1 + ux * s, y1 + uy * s)], fill=fill, width=w)
        t += dash + gap


def dashed_box(d, box, fill_col, edge, w):
    if fill_col:
        d.rectangle(box, fill=fill_col)
    x0, y0, x1, y1 = box
    for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        dashed(d, a, b, edge, w, dash=7, gap=4)


def rct(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]


def merge(iv):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def interior_coords(zones, axis, limit):
    """axis 'v' -> x coords with merged y-segments; 'h' -> y coords with x-segments."""
    coords: dict[float, list] = {}
    for z in zones:
        x0, y0, x1, y1 = z["rect_m"]
        if axis == "v":
            for xv in (x0, x1):
                if EPS < xv < limit - EPS:
                    coords.setdefault(round(xv, 2), []).append((min(y0, y1), max(y0, y1)))
        else:
            for yh in (y0, y1):
                if EPS < yh < limit - EPS:
                    coords.setdefault(round(yh, 2), []).append((min(x0, x1), max(x0, x1)))
    return {c: merge(iv) for c, iv in coords.items()}


def plan_panel(d, ox, oy, sc, floor, boundary, title):
    def px(x, y):
        return (ox + (x + M) * SCALE, oy + (D + M - y) * SCALE)

    for z in floor["zones"]:
        x0, y0, x1, y1 = z["rect_m"]
        d.rectangle(rct(px(x0, y0), px(x1, y1)), fill=GT_FILL, outline=GT_EDGE, width=1)

    for side, (p1, p2) in {"S": (px(0, 0), px(W, 0)), "N": (px(0, D), px(W, D)),
                           "W": (px(0, 0), px(0, D)), "E": (px(W, 0), px(W, D))}.items():
        if boundary.get(side, "hit") == "hit":
            d.line([p1, p2], fill=GREEN, width=6)
        else:
            dashed(d, p1, p2, RED, 6)

    vmap = {round(m["truth"], 2): m for m in sc["vwalls"]}
    hmap = {round(m["truth"], 2): m for m in sc["hwalls"]}

    def draw_axis(axis, coordmap, verdmap):
        for coord, segs in coordmap.items():
            m = verdmap.get(coord)
            if not m:
                continue
            hit = m["read"] is not None
            delta = (m.get("delta") or 0.0) if hit else 0.0
            for lo, hi in segs:
                if not hit:  # miss = red dashed, ONCE per merged segment
                    p1, p2 = (px(coord, lo), px(coord, hi)) if axis == "v" else (px(lo, coord), px(hi, coord))
                    dashed(d, p1, p2, RED, 4)
                    continue
                if abs(delta) > CUE_EPS:  # in-tol drift band + gt hairline
                    if axis == "v":
                        d.rectangle(rct(px(coord - WALL_TOL, lo), px(coord + WALL_TOL, hi)), fill=BAND)
                        d.line([px(coord, lo), px(coord, hi)], fill=TRUTH, width=1)
                    else:
                        d.rectangle(rct(px(lo, coord - WALL_TOL), px(hi, coord + WALL_TOL)), fill=BAND)
                        d.line([px(lo, coord), px(hi, coord)], fill=TRUTH, width=1)
                pc = coord + delta
                p1, p2 = (px(pc, lo), px(pc, hi)) if axis == "v" else (px(lo, pc), px(hi, pc))
                d.line([p1, p2], fill=GREEN, width=4)

    draw_axis("v", interior_coords(floor["zones"], "v", W), vmap)
    draw_axis("h", interior_coords(floor["zones"], "h", D), hmap)
    for x in sc.get("extra_vwalls", []):
        d.line([px(x, 0), px(x, D)], fill=RED, width=5)
    for y in sc.get("extra_hwalls", []):
        d.line([px(0, y), px(W, y)], fill=RED, width=5)

    off = 11
    def lane(fac, a, b):
        if fac == "N":
            return (px(a, D)[0], px(a, D)[1] - off), (px(b, D)[0], px(b, D)[1] - off)
        if fac == "S":
            return (px(a, 0)[0], px(a, 0)[1] + off), (px(b, 0)[0], px(b, 0)[1] + off)
        if fac == "E":
            return (px(W, a)[0] + off, px(W, a)[1]), (px(W, b)[0] + off, px(W, b)[1])
        return (px(0, a)[0] - off, px(0, a)[1]), (px(0, b)[0] - off, px(0, b)[1])
    for fac in ("N", "S", "E", "W"):
        for m in sc.get("windows", {}).get(fac, []):
            p1, p2 = lane(fac, *m["truth"])
            if m["read"] is not None:
                d.line([p1, p2], fill=GREEN, width=7)
            else:
                dashed(d, p1, p2, RED, 7, dash=6, gap=4)
        for (ts, te) in sc.get("extra_windows", {}).get(fac, []):
            d.line([lane(fac, ts, te)[0], lane(fac, ts, te)[1]], fill=RED, width=7)
    d.text((ox, oy - 20), title, font=_f(13), fill=TEXT)


def facade_demo(d, ox, oy, title):
    """Manually-illustrated North elevation: 1 hit, 1 missing (light-red fill),
    1 wrong-position pair (gt ghost + displaced extra + connector)."""
    fw, Htot, m = W, 6.6, 0.9

    def px(u, z):
        return (ox + (u + m) * SCALE, oy + (Htot + m - z) * SCALE)

    d.rectangle(rct(px(0, 0), px(fw, Htot)), fill=GT_FILL, outline=GREEN, width=6)
    d.line([px(0, 3.0), px(fw, 3.0)], fill=GREEN, width=4)

    # Floor 1: three gt slots -> hit, missing, wrong-position(ghost)
    slots = [(1.24, 3.64, "hit"), (6.30, 8.70, "miss"), (11.36, 13.76, "wrong")]
    s1, h1 = 1.0, 2.6
    for x0, x1, kind in slots:
        box = rct(px(x0, h1), px(x1, s1))
        if kind == "hit":
            d.rectangle(box, fill=FILL_G, outline=GREEN, width=3)
        else:  # miss + wrong both show the gt slot as a light-red ghost
            dashed_box(d, box, FILL_R, RED, 3)
    # the wrong-position product window sits displaced (drawn ~2.2 m to the right, solid red)
    wx0, wx1 = 11.36 + 2.4, 13.76 + 2.4
    if wx1 > fw:
        wx0, wx1 = 11.36 - 3.0, 13.76 - 3.0
    wbox = rct(px(wx0, h1), px(wx1, s1))
    d.rectangle(wbox, fill=FILL_R, outline=RED, width=3)
    # displaced connector: gt-slot centre -> product centre
    gc = px((11.36 + 13.76) / 2, (s1 + h1) / 2)
    pc = px((wx0 + wx1) / 2, (s1 + h1) / 2)
    dashed(d, gc, pc, TRUTH, 2, dash=5, gap=4)
    d.text(((gc[0] + pc[0]) / 2 - 30, gc[1] - 14), "displaced", font=_f(10), fill=SUBTLE)

    # Floor 2: two hits
    for x0, x1 in [(1.95, 5.55), (9.45, 13.05)]:
        d.rectangle(rct(px(x0, 5.8), px(x1, 4.0)), fill=FILL_G, outline=GREEN, width=3)
    d.text((ox, oy - 20), title, font=_f(13), fill=TEXT)


def main():
    Path("overlay_proto").mkdir(exist_ok=True)
    floor = GT["floors"][0]
    all_hit = {s: "hit" for s in "NSEW"}
    pw = int((W + 2 * M) * SCALE); ph = int((D + 2 * M) * SCALE)
    gap = 44; head = 100; row_gap = 58
    fw2 = int((W + 1.8) * SCALE); fh2 = int((6.6 + 1.8) * SCALE)
    total_w = 24 + 3 * pw + 2 * gap
    oy1 = head + 24; oy2 = oy1 + ph + row_gap
    total_h = oy2 + fh2 + 24
    img = Image.new("RGB", (total_w, total_h), BG)
    d = ImageDraw.Draw(img)

    d.text((14, 12), "gt grade sheet v2  ·  fixed dashes · missing-window fill · wrong-position example",
           font=_f(17), fill=TEXT)
    lx, ly = 14, 42
    d.line([(lx, ly + 6), (lx + 24, ly + 6)], fill=GREEN, width=5); d.text((lx + 30, ly - 1), "hit", font=_f(11), fill=SUBTLE); lx += 90
    dashed(d, (lx, ly + 6), (lx + 24, ly + 6), RED, 5, dash=6, gap=4); d.text((lx + 30, ly - 1), "miss (red dashed, light-red fill)", font=_f(11), fill=SUBTLE); lx += 250
    d.line([(lx, ly + 6), (lx + 24, ly + 6)], fill=RED, width=5); d.text((lx + 30, ly - 1), "extra / wrong-place (red solid)", font=_f(11), fill=SUBTLE); lx += 240
    d.rectangle([lx, ly, lx + 24, ly + 12], fill=BAND); d.text((lx + 30, ly - 1), "within-tol band", font=_f(11), fill=SUBTLE)
    d.text((14, head - 12), "wrong-position window = gt slot shown as a miss ghost + product drawn at its wrong place as extra, linked by a 'displaced' connector",
           font=_f(11), fill=SUBTLE)

    plan_panel(d, 24, oy1, RS["1f_view"], floor, all_hit, "0_reading grade · Floor 1 (real)")
    plan_panel(d, 24 + pw + gap, oy1, CS["Floor 1"], floor, all_hit, "1_correction grade · Floor 1 (real)")

    demo = copy.deepcopy(RS["1f_view"])
    demo["vwalls"][0]["read"] = 5.22; demo["vwalls"][0]["delta"] = 0.22
    demo["hwalls"][0]["read"] = None
    demo.setdefault("extra_vwalls", []).append(7.5)
    demo["windows"]["N"][1]["read"] = None
    plan_panel(d, 24 + 2 * (pw + gap), oy1, demo, floor, {"N": "hit", "S": "miss", "E": "hit", "W": "hit"},
               "DEMO · errors (note clean single-phase dashes)")

    facade_demo(d, 24, oy2, "DEMO · North elevation — missing (filled) + wrong-position window")

    out = Path("overlay_proto/grade_sheet_v2.png")
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
