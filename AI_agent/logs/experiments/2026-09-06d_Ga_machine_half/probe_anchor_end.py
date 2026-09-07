#!/usr/bin/env python3
"""「哪一端是对的」有没有【结构性】的判据 —— 零参数，图自己的拓扑说了算。

⭐ 用户 2026-09-07 领域口径：「像这种歪线大概率是**一端**在 cad 的吸附问题，可能吸错了，
一般是一端错，**不能取中点来改**」。
⇒ 那就得能**认出**是哪一端错。本脚本验的就是这件事有没有可执行的判据。

**判据（零参数）**：一条歪线的某一端，若与**另一条【本身已经正交】的笔画**共端点，
那一端就是「吸对了的」；与**同样歪斜**的笔画共端点的那一端，锚不住。

⛔ 注意这里必须要求邻居**自己是正交的** —— 只问「有没有邻居」会两端都成立
（实测：13AD 两端都有共端点邻居，但西端那个 13AF 自己也是歪的）。

跑法： python AI_agent/logs/experiments/2026-09-06d_Ga_machine_half/probe_anchor_end.py
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys

import ezdxf

REPO = pathlib.Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SOURCES = REPO / "case_tests/test_baseline/gt_sources"

#: 端点重合判定。⛔ 不是容差参数：DXF 里同一个吸附点的两条线，坐标是**逐位相同**的
#: （实测 13AD 端B 与 13AC 端点 = 完全相同的 float）。留 1e-6 只为防读入抖动。
COINCIDENT_MM = 1e-6
#: 低于此长度不谈方向（= 量化步长，派生自 tau_node/10）。
QUANT_MM = 0.1


def _resolve(anchor: pathlib.Path, req: dict) -> pathlib.Path | None:
    named = anchor / req["source_dxf_label"]
    if named.is_file():
        return named
    for candidate in sorted(anchor.glob("*.dxf")):
        if hashlib.sha256(candidate.read_bytes()).hexdigest() == req["source_dxf_sha256"]:
            return candidate
    return None


def _collect(doc, view: dict) -> dict[str, tuple[tuple, tuple, bool]]:
    sel, box = view["wall_selector"], view["clip_box_dxf"]
    layers, types = set(sel.get("layers") or []), set(sel.get("entity_types") or [])
    out: dict[str, tuple[tuple, tuple, bool]] = {}
    for e in doc.modelspace():
        if (types and e.dxftype() not in types) or (layers and e.dxf.layer not in layers):
            continue
        if not hasattr(e.dxf, "start"):
            continue
        s, t = e.dxf.start, e.dxf.end
        if not all(box["xmin"] <= p[0] <= box["xmax"] and box["ymin"] <= p[1] <= box["ymax"]
                   for p in (s, t)):
            continue
        dx, dy = abs(t[0] - s[0]), abs(t[1] - s[1])
        skewed = math.hypot(dx, dy) >= QUANT_MM and min(dx, dy) > COINCIDENT_MM
        out[e.dxf.handle] = ((s[0], s[1]), (t[0], t[1]), skewed)
    return out


def _neighbours_at(point, me: str, strokes: dict) -> list[tuple[str, bool]]:
    found = []
    for handle, (p0, p1, skewed) in strokes.items():
        if handle == me:
            continue
        if any(abs(q[0] - point[0]) < COINCIDENT_MM and abs(q[1] - point[1]) < COINCIDENT_MM
               for q in (p0, p1)):
            found.append((handle, skewed))
    return found


def main() -> None:
    for case in sorted(p.name for p in SOURCES.iterdir() if p.is_dir()):
        anchor = SOURCES / case
        req_path = (anchor / "request_as_measured.json"
                    if (anchor / "request_as_measured.json").is_file()
                    else anchor / "request.json")
        if not req_path.is_file():
            continue
        req = json.loads(req_path.read_text(encoding="utf-8"))
        dxf = _resolve(anchor, req)
        if dxf is None:
            continue
        doc = ezdxf.readfile(dxf)
        for view in req.get("plan_views", []):
            strokes = _collect(doc, view)
            skewed = {h: v for h, v in strokes.items() if v[2]}
            if not skewed:
                continue
            print(f"=== {case} / {view['id']}: 歪线 {len(skewed)} 条 ===")
            for handle in sorted(skewed):
                p0, p1, _ = strokes[handle]
                verdict = []
                for label, point in (("端A", p0), ("端B", p1)):
                    nb = _neighbours_at(point, handle, strokes)
                    straight = [h for h, sk in nb if not sk]
                    verdict.append(bool(straight))
                    shown = [f"{h}({'歪斜' if sk else '已正交'})" for h, sk in nb] or ["无"]
                    print(f"  {handle} {label} ({point[0]:12.3f},{point[1]:12.3f}): "
                          f"共端点 {', '.join(shown)}"
                          f"   ⇒ {'✅ 锚得住' if straight else '⛔ 锚不住'}")
                if sum(verdict) == 1:
                    print(f"     ⇒ ⭐ 【唯一确定】锚 {'端A' if verdict[0] else '端B'}，绕它转平")
                elif sum(verdict) == 0:
                    print("     ⇒ ⚠️ 两端都锚不住 ⇒ 必须【按连通组】一起解，⛔ 单条判不了")
                else:
                    print("     ⇒ ⛔ 两端都锚得住 ⇒ 疑似【真斜线】，不该拉平，交人判")
                print()


if __name__ == "__main__":
    main()
