#!/usr/bin/env python3
"""reading 重启轮的【过程指标】对账器。

⛔ 这不是判卷器。判卷（对 gt）走 score_vs_gt 侧车；本脚本只量
「读图器是**怎么**得到那些数字的」—— 2026-08-03 定论：reading 的杠杆是
工作模式（量而非看），不是分数本身。

对照基准写死为 run_2026-07-07_haiku_cv_retest（那份好 reading 的出生地）：
    cv 工具调用 92 次（1f 33 · 2f 24 · South 10 · North 9 · East 8 · West 8）
    其中 crop_zoom 55 · prescan 0
    平面墙 provenance 全 dimension_derived（1f 17/17 · 2f 18/18）

用法：
    python AI_agent/logs/experiments/2026-08-15_reading_restart/process_metrics.py <0_reading 目录> [...]
不传参数则默认对照「07-07 基准 vs 本轮 A1」。
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BASELINE = REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading"

SIDECAR_RE = re.compile(r"^\d+_(?P<tool>.+)\.json$")


def tool_calls(reading_dir: Path) -> dict[str, collections.Counter]:
    """每张图的 cv 工具调用直方图。证据可能落在 cv_evidence/ 或 out/ 下。"""
    per_image: dict[str, collections.Counter] = {}
    roots = [reading_dir / "cv_evidence", reading_dir / "out", reading_dir]
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            m = SIDECAR_RE.match(path.name)
            if not m or path in seen:
                continue
            seen.add(path)
            # 图名 = 含该 sidecar 的目录名
            per_image.setdefault(path.parent.name, collections.Counter())[m.group("tool")] += 1
    return per_image


def product_metrics(reading_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(reading_dir.glob("*_view.json")):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # 产物坏了本身就是结果
            out[path.stem] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        strokes = d.get("strokes") or []
        prov = collections.Counter(s.get("provenance") for s in strokes)
        pens = collections.Counter(s.get("pen") for s in strokes)
        so = d.get("scale_origin") or {}
        out[path.stem] = {
            "kind": d.get("image_kind"),
            "strokes": len(strokes),
            "pens": dict(pens),
            "provenance": dict(prov),
            "dimensions": len(d.get("dimensions") or []),
            "ocr_texts": len(d.get("ocr_texts") or []),
            "uncaptured": len(d.get("uncaptured") or []),
            "scale_origin_set": any(so.get(k) is not None for k in ("world_x_m", "world_y_m", "world_z_m")),
            "dim_refs_max": max((len(s.get("dimension_refs") or []) for s in strokes), default=0),
        }
    return out


def report(label: str, reading_dir: Path) -> None:
    print(f"\n{'='*78}\n{label}\n  {reading_dir}\n{'='*78}")
    if not reading_dir.is_dir():
        print("  ⛔ 目录不存在")
        return

    calls = tool_calls(reading_dir)
    total = sum(sum(c.values()) for c in calls.values())
    agg: collections.Counter = collections.Counter()
    for c in calls.values():
        agg.update(c)
    print(f"\n-- CV 工具调用：总 {total} 次 --")
    if not calls:
        print("  ⛔ 零证据 sidecar（= 没量，或证据没被 merge 带进来）")
    for image in sorted(calls):
        c = calls[image]
        detail = " · ".join(f"{t}×{n}" for t, n in sorted(c.items(), key=lambda kv: -kv[1]))
        print(f"  {image:<12} {sum(c.values()):>3}  {detail}")
    if agg:
        print(f"  {'合计':<12} {total:>3}  "
              + " · ".join(f"{t}×{n}" for t, n in sorted(agg.items(), key=lambda kv: -kv[1])))
        print(f"  ⭐ crop_zoom={agg.get('crop_zoom', 0)}  prescan={agg.get('prescan', 0)}"
              f"  px_m_calibrator={agg.get('px_m_calibrator', 0)}")

    print("\n-- 产物 --")
    prod = product_metrics(reading_dir)
    if not prod:
        print("  ⛔ 无 *_view.json")
    for image, m in prod.items():
        if "error" in m:
            print(f"  {image:<12} ⛔ {m['error']}")
            continue
        prov = m["provenance"]
        dd = prov.get("dimension_derived", 0)
        ratio = f"{dd}/{m['strokes']}" if m["strokes"] else "0/0"
        print(f"  {image:<12} {m['kind']:<9} strokes={m['strokes']:<3} "
              f"dimension_derived={ratio:<7} dims={m['dimensions']:<3} "
              f"ocr={m['ocr_texts']:<3} uncap={m['uncaptured']:<3} "
              f"scale_origin={'Y' if m['scale_origin_set'] else 'n'} "
              f"max_dim_refs={m['dim_refs_max']}")
    plans = [m for m in prod.values() if m.get("kind") == "plan"]
    if plans:
        dd = sum(m["provenance"].get("dimension_derived", 0) for m in plans)
        tot = sum(m["strokes"] for m in plans)
        pct = 100.0 * dd / tot if tot else 0.0
        print(f"\n  ⭐ 平面 dimension_derived 占比 = {dd}/{tot} = {pct:.1f}%   (07-07 基准 = 35/35 = 100.0%)")


def main(argv: list[str]) -> int:
    targets: list[tuple[str, Path]]
    if argv:
        targets = [(str(p), Path(p).resolve()) for p in argv]
    else:
        targets = [
            ("对照基准 07-07（那份好 reading）", BASELINE),
            ("本轮 A1", REPO / "case_tests/e2e_tests/sm21_anchor/run_2026-08-15_reading_restart_A1/0_reading"),
        ]
    for label, path in targets:
        report(label, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
