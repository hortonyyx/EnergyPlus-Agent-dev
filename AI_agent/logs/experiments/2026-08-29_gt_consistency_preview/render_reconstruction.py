"""⭐ 复原式渲染 —— 从【事实】把建筑画出来，把待确认的地方标出来。

⛔⛔ 铁律：**渲染器只照搬，不推导。**
    墙带的两条边【就是】量到的那两条面线（`f0` / `f1`），
    ⛔ 绝不「取中轴再 ±半个厚度」重画 —— 那会把生产者的错误抹平，
    渲染器就变成了「同意错误的那一方」。
    同族 [[recompute-gate-must-mirror-producer-definition]] ·
        [[self-consistent-gates-anchor-on-product-chosen-apertures]]

⛔ 探索档：取数暂来自判分器现算的面线，事实层落库后须重接。
"""
from __future__ import annotations
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(Path(__file__).parent))
from consistency_probe import walls, check                      # noqa: E402
from src.agent.judge.as_drawn.denominator import denominator    # noqa: E402

PAD, SCALE, GUT = 56, 34.0, 70          # px 边距 / px per metre / 两层之间的槽


def _svg_floor(name, W, findings, ox, oy, H, opening_targets):
    """画一层。⛔ 每一笔都来自 W / opening_targets，⛔ 渲染器不算任何几何。"""
    o, sus = [], [f for f in findings if f.get("suspicious") and f.get("floor") == name]
    sus_keys = {(f["wall"]["axis"], round(f["wall"]["f0"], 4), round(f["wall"]["f1"], 4))
                for f in sus if f.get("wall")}
    o.append(f'<text x="{ox}" y="{oy-18}" class="ttl">{name}</text>')
    for w in W:
        hot = (w["axis"], round(w["f0"], 4), round(w["f1"], 4)) in sus_keys
        cls = "wall hot" if hot else "wall"
        for lo, hi in w["segs"]:                       # ⭐ 逐【段】画：洞口自然成为缺口
            if w["axis"] == "x":                       # 面线常量在 x ⇒ 墙沿 y 走
                x, y = ox + w["f0"] * SCALE, oy + (H - hi) * SCALE
                bw, bh = (w["f1"] - w["f0"]) * SCALE, (hi - lo) * SCALE
            else:
                x, y = ox + lo * SCALE, oy + (H - w["f1"]) * SCALE
                bw, bh = (hi - lo) * SCALE, (w["f1"] - w["f0"]) * SCALE
            o.append(f'<rect class="{cls}" x="{x:.2f}" y="{y:.2f}" '
                     f'width="{max(bw,1.2):.2f}" height="{max(bh,1.2):.2f}"/>')
    for t in opening_targets:                          # 洞口：门/窗分色
        k = "door" if t.get("kind") == "door" else "win"
        c0, c1 = t["const_range_m"]
        if t["axis"] == "y":
            x, y = ox + t["lo_m"] * SCALE, oy + (H - c1) * SCALE
            bw, bh = (t["hi_m"] - t["lo_m"]) * SCALE, max((c1 - c0) * SCALE, 3)
        else:
            x, y = ox + c0 * SCALE, oy + (H - t["hi_m"]) * SCALE
            bw, bh = max((c1 - c0) * SCALE, 3), (t["hi_m"] - t["lo_m"]) * SCALE
        o.append(f'<rect class="{k}" x="{x:.2f}" y="{y:.2f}" width="{bw:.2f}" height="{bh:.2f}"/>')
    for i, f in enumerate(sus, 1):                     # ⭐ 机器点名：图上打标，⛔ 不指望人去搜
        w = f["wall"]; a, b = f["span"]
        if w["axis"] == "x":
            cx, cy = ox + w["mid"] * SCALE, oy + (H - (a + b) / 2) * SCALE
        else:
            cx, cy = ox + (a + b) / 2 * SCALE, oy + (H - w["mid"]) * SCALE
        o.append(f'<circle class="mk" cx="{cx:.1f}" cy="{cy:.1f}" r="15"/>')
        o.append(f'<text class="mkn" x="{cx:.1f}" y="{cy+5:.1f}">{i}</text>')
        o.append(f'<text class="cal" x="{cx+22:.1f}" y="{cy+5:.1f}">{f["mm"]:.0f} mm</text>')
    return "\n".join(o)


def render(floors, findings, openings, out: Path, w_m, h_m):
    names = list(floors)
    fw = w_m * SCALE
    W = PAD * 2 + fw * len(names) + GUT * (len(names) - 1)
    H = PAD * 2 + h_m * SCALE + 96
    body = []
    for i, n in enumerate(names):
        body.append(_svg_floor(n, floors[n][0], findings,
                               PAD + i * (fw + GUT), PAD + 26, h_m, openings.get(n, [])))
    sus = [f for f in findings if f.get("suspicious")]
    ly = PAD + h_m * SCALE + 58
    body.append(f'<text class="lg" x="{PAD}" y="{ly}">⚠ 待确认 {len(sus)} 条'
                f'（清单共 {len(findings)} 条；其余为「两层布局本就不同」）</text>')
    for i, f in enumerate(sus, 1):
        body.append(f'<text class="lg2" x="{PAD}" y="{ly + 22*i}">'
                    f'{i}. {f["detail"]}</text>')
    css = """.wall{fill:#c8ccd4}.wall.hot{fill:#ff5c5c}.win{fill:#3fc7ff}.door{fill:#ff9f2e}
.mk{fill:none;stroke:#ff2d2d;stroke-width:3}.mkn{fill:#ff2d2d;font:bold 15px sans-serif;text-anchor:middle}
.cal{fill:#ff2d2d;font:bold 14px sans-serif}.ttl{fill:#e8ecf4;font:bold 19px sans-serif}
.lg{fill:#ffd166;font:bold 16px sans-serif}.lg2{fill:#cfd6e4;font:14px sans-serif}
text{font-family:sans-serif}"""
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
                   f'viewBox="0 0 {W:.0f} {H:.0f}"><style>{css}</style>'
                   f'<rect width="100%" height="100%" fill="#10141c"/>'
                   + "\n".join(body) + "</svg>")
    return out


# --------------------------------------------------------------------------- #
# PNG 后端（PIL）—— 与 SVG 后端画的是同一批图元。
# ⛔ 同一条铁律：只照搬 f0/f1 与 segs，⛔ 不推导。
# --------------------------------------------------------------------------- #
def render_png(floors, findings, openings, out: Path, w_m, h_m):
    from PIL import Image, ImageDraw
    names = list(floors)
    fw = w_m * SCALE
    W = int(PAD * 2 + fw * len(names) + GUT * (len(names) - 1))
    H = int(PAD * 2 + h_m * SCALE + 96)
    # ⛔ 本机无任何 CJK 字体、也无 TrueType ⇒ PNG 上【只放编号与数字】，
    # 中文清单走 SVG / markdown。⭐ 这与已定的原则一致：
    # **发现靠数字（清单），确认靠图** —— 图不负责让人读字。
    SS = 2                                     # supersample：放大画再缩回，让默认位图字体清楚些
    im = Image.new("RGB", (W * SS, H * SS), (16, 20, 28))
    d = ImageDraw.Draw(im)
    COL = {"wall": (200, 204, 212), "hot": (255, 92, 92),
           "win": (63, 199, 255), "door": (255, 159, 46)}

    def box(x, y, bw, bh, c):
        d.rectangle([x * SS, y * SS, (x + max(bw, 1.2)) * SS, (y + max(bh, 1.2)) * SS], fill=c)

    def txt(x, y, s, c):
        d.text((x * SS, y * SS), s, fill=c)

    for i, name in enumerate(names):
        ox, oy = PAD + i * (fw + GUT), PAD + 26
        W_, sus = floors[name][0], [f for f in findings
                                    if f.get("suspicious") and f.get("floor") == name]
        keys = {(f["wall"]["axis"], round(f["wall"]["f0"], 4), round(f["wall"]["f1"], 4))
                for f in sus if f.get("wall")}
        txt(ox, oy - 22, name, (232, 236, 244))
        for w in W_:
            c = COL["hot"] if (w["axis"], round(w["f0"], 4), round(w["f1"], 4)) in keys else COL["wall"]
            for lo, hi in w["segs"]:
                if w["axis"] == "x":
                    box(ox + w["f0"] * SCALE, oy + (h_m - hi) * SCALE,
                        (w["f1"] - w["f0"]) * SCALE, (hi - lo) * SCALE, c)
                else:
                    box(ox + lo * SCALE, oy + (h_m - w["f1"]) * SCALE,
                        (hi - lo) * SCALE, (w["f1"] - w["f0"]) * SCALE, c)
        for t in openings.get(name, []):
            c = COL["door"] if t.get("kind") == "door" else COL["win"]
            c0, c1 = t["const_range_m"]
            if t["axis"] == "y":
                box(ox + t["lo_m"] * SCALE, oy + (h_m - c1) * SCALE,
                    (t["hi_m"] - t["lo_m"]) * SCALE, max((c1 - c0) * SCALE, 3), c)
            else:
                box(ox + c0 * SCALE, oy + (h_m - t["hi_m"]) * SCALE,
                    max((c1 - c0) * SCALE, 3), (t["hi_m"] - t["lo_m"]) * SCALE, c)
        for n, f in enumerate(sus, 1):
            w, (a, b) = f["wall"], f["span"]
            cx, cy = ((ox + w["mid"] * SCALE, oy + (h_m - (a + b) / 2) * SCALE)
                      if w["axis"] == "x" else
                      (ox + (a + b) / 2 * SCALE, oy + (h_m - w["mid"]) * SCALE))
            d.ellipse([(cx - 16) * SS, (cy - 16) * SS, (cx + 16) * SS, (cy + 16) * SS],
                      outline=(255, 45, 45), width=3 * SS)
            txt(cx - 4, cy - 7, str(n), (255, 45, 45))
            txt(cx + 22, cy - 7, f"[{n}] {f['mm']:.0f} mm", (255, 45, 45))

    sus = [f for f in findings if f.get("suspicious")]
    ly = PAD + h_m * SCALE + 52
    txt(PAD, ly, f"TO CONFIRM: {len(sus)}   (list total {len(findings)}; "
                 f"the rest = layouts genuinely differ between floors)", (255, 209, 102))
    for i, f in enumerate(sus, 1):
        w = f["wall"]
        txt(PAD, ly + 20 * i,
            f"[{i}] {f['floor']} axis={w['axis']} mid={w['mid']:.4f}m  "
            f"vs other floor: {f['mm']:.0f} mm apart  (band {f.get('band_mm')} mm -> overlaps)",
            (207, 214, 228))
    im = im.resize((W, H), Image.LANCZOS)
    im.save(out)
    return out
