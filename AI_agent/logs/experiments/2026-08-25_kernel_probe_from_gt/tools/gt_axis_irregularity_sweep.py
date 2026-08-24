"""Sweep a gt for "near-miss" axes — boundaries that almost, but not quite, line up.

Motivation (user, 2026-08-25): a hand-drawn CAD plan routinely carries offsets
too small to see.  sm25 has at least one (a 120 partition on 1F drawn 60.3 mm
south of the same partition everywhere else).  Before deciding whether that is a
one-off or a class, count them — mechanically, on the answer itself.

⛔ The judgement is NOT a distance threshold.  A first cut of this sweep used
"cluster axes closer than 0.06 m" and missed the very defect that motivated it
(60.3 mm vs a 60 mm gap — off by 0.3 mm), while any threshold loose enough to
catch it starts swallowing the two faces of a real 120 wall.  Distance cannot
separate the two cases because they overlap in magnitude.

The judgement used here is STRUCTURAL instead:

  * every axis value carries its SUPPORT — the intervals along that axis where
    some zone edge actually lies on it;
  * two near-equal axes whose supports OVERLAP are two sides of something real
    (a wall between two rooms) — not a finding;
  * two near-equal axes whose supports are DISJOINT are one intended line drawn
    in two places, slightly apart — that is the finding.

So the distance parameter only has to be loose enough to bracket "invisible to
the eye" (default 0.30 m); it no longer has to thread a needle.

⛔ Reports only.  It deliberately does not decide which value is "right" — that
judgement belongs to a declared modelling rule, not to a sweep.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

EPS = 1e-6


def _collect(floor: dict):
    """axis direction -> value -> (support intervals, owning zone ids)."""
    table = {"x": defaultdict(lambda: ([], set())), "y": defaultdict(lambda: ([], set()))}
    for zone in floor["zones"]:
        ring = [(float(x), float(y)) for x, y in zone["polygon"]["exterior"]["vertices"]]
        for i in range(len(ring)):
            (x1, y1), (x2, y2) = ring[i], ring[(i + 1) % len(ring)]
            if abs(y1 - y2) < EPS and abs(x1 - x2) > EPS:      # horizontal edge -> a y axis
                spans, zones = table["y"][round(y1, 6)]
                spans.append((min(x1, x2), max(x1, x2)))
                zones.add(zone["id"])
            elif abs(x1 - x2) < EPS and abs(y1 - y2) > EPS:    # vertical edge -> an x axis
                spans, zones = table["x"][round(x1, 6)]
                spans.append((min(y1, y2), max(y1, y2)))
                zones.add(zone["id"])
    return table


def _merge(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for lo, hi in sorted(spans):
        if out and lo <= out[-1][1] + EPS:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out


def _overlap(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    total = 0.0
    for lo1, hi1 in a:
        for lo2, hi2 in b:
            total += max(0.0, min(hi1, hi2) - max(lo1, lo2))
    return total


def _pairs(table, span: float, scope: str, findings: list) -> None:
    values = sorted(table)
    for i, v1 in enumerate(values):
        for v2 in values[i + 1:]:
            gap = v2 - v1
            if gap > span:
                break
            if gap < EPS:
                continue
            s1, z1 = table[v1]
            s2, z2 = table[v2]
            ov = _overlap(_merge(s1), _merge(s2))
            findings.append({
                "scope": scope, "v1": v1, "v2": v2, "gap_mm": gap * 1000,
                "overlap_m": ov, "zones1": sorted(z1), "zones2": sorted(z2),
            })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gt", type=Path, nargs="+")
    ap.add_argument("--span", type=float, default=0.30,
                    help="how far apart two axes may be and still be 'the same intended line'")
    ap.add_argument("--min-overlap", type=float, default=0.05,
                    help="support overlap above which a pair is a real wall, not a finding")
    args = ap.parse_args()

    grand_real, grand_susp = 0, 0
    for gt_path in args.gt:
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        print(f"=== {gt['case']}   span<={args.span} m ===")
        per_floor = {}
        findings: list[dict] = []
        for floor in gt["floors"]:
            table = _collect(floor)
            per_floor[floor["id"]] = table
            for axis in ("x", "y"):
                _pairs(table[axis], args.span, f"{floor['id']} {axis}", findings)
        for axis in ("x", "y"):
            merged = defaultdict(lambda: ([], set()))
            for fid, table in per_floor.items():
                for v, (spans, zones) in table[axis].items():
                    m_spans, m_zones = merged[v]
                    m_spans.extend(spans)
                    m_zones |= {f"{fid}:{z}" for z in zones}
            cross: list[dict] = []
            _pairs(merged, args.span, f"cross-floor {axis}", cross)
            for row in cross:
                floors1 = {z.split(":")[0] for z in row["zones1"]}
                floors2 = {z.split(":")[0] for z in row["zones2"]}
                if floors1 | floors2 != floors1 & floors2 or len(floors1) > 1:
                    findings.append(row)

        susp = [f for f in findings if f["overlap_m"] <= args.min_overlap]
        real = [f for f in findings if f["overlap_m"] > args.min_overlap]
        for f in sorted(susp, key=lambda r: -r["gap_mm"]):
            print(f"  ⚠ [{f['scope']}] {f['v1']:.4f} vs {f['v2']:.4f} "
                  f"= {f['gap_mm']:.1f} mm apart, supports DISJOINT (overlap {f['overlap_m']:.3f} m)")
            print(f"        {f['v1']:.4f} <- {f['zones1']}")
            print(f"        {f['v2']:.4f} <- {f['zones2']}")
        print(f"  -> {len(susp)} suspected drawing offset(s); "
              f"{len(real)} near pair(s) explained by real wall thickness")
        print()
        grand_susp += len(susp)
        grand_real += len(real)
    print(f"TOTAL: {grand_susp} suspected drawing offset(s), "
          f"{grand_real} explained by wall thickness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
