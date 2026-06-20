"""Extract a maximal gt from a 天正「图形导出」 plain DXF (CAD→gt, plan §4 / P2).

Reads `gt/<case>/source.dxf` (天正 objects must be exploded to plain entities first —
see inspect_dxf.py / the plan) and pulls the geometry gt couldn't get from human
reading: exact per-window along-facade position + width, plus footprint and exterior
doors. It does NOT silently overwrite the verified answer key — it writes a PROPOSED
`gt/<case>/gt_from_cad.json` and prints a reconciliation report against the existing
`gt.json` (counts per facade/floor MUST match), for a human to review (via the overlay
render) before promoting.

Offline judge/human-side tool: reads the answer-key source DXF; never imported by
gate① or executors (test_gt_discipline enforces).

What maps to what (verified on sm21, 2026-06-20):
  * view segmentation : 图名 TEXT anchors ('1f平面图' / '南立面' …); plan band y>-9000.
  * footprint         : WALL-layer line bbox per plan view (mm → m).
  * window            : INSERT '$TCHSYS$WIN2D' — insert pt = centre, |xscale| = width;
                        facade = which perimeter wall it sits on; floor = which plan.
  * door              : INSERT '$DorLib2D$' — exterior if on a perimeter wall.
  * sill/head z       : kept from the existing verified gt for v1 (elevation-derived
                        z is a v2 enhancement — see plan §4 S4).

Usage:
    python scripts/tool_scripts/gt_from_dxf.py sm21_anchor
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import ezdxf

GT_DIR = Path("case_tests/test_baseline/gt")
EDGE_TOL = 400.0          # mm: how close to a perimeter wall counts as "on" that facade
PLAN_BAND_Y = -9000.0     # model-space y above this = plan views, below = elevations

_FLOOR_OF = {"1f平面图": "Floor 1", "2f平面图": "Floor 2"}
_FACADE_OF = {"北立面": "North", "南立面": "South", "东立面": "East", "西立面": "West"}


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _titles(msp) -> dict[str, tuple[float, float]]:
    out = {}
    for e in msp.query("TEXT"):
        t = e.dxf.text.strip()
        if t in _FLOOR_OF or t in _FACADE_OF:
            out[t] = (e.dxf.insert.x, e.dxf.insert.y)
    return out


def _plan_split_x(titles: dict) -> float:
    xs = sorted(titles[t][0] for t in _FLOOR_OF if t in titles)
    return sum(xs) / len(xs) if len(xs) == 2 else float("inf")


def _facade_of(cx, cy, minx, miny, maxx, maxy) -> str | None:
    """Which perimeter wall the point sits on (None = interior)."""
    if abs(cy - miny) <= EDGE_TOL:
        return "South"
    if abs(cy - maxy) <= EDGE_TOL:
        return "North"
    if abs(cx - minx) <= EDGE_TOL:
        return "West"
    if abs(cx - maxx) <= EDGE_TOL:
        return "East"
    return None


def _plan_footprints(msp, titles) -> dict[str, dict]:
    """Per plan-view floor: WALL-line bbox -> footprint + origin."""
    split = _plan_split_x(titles)
    acc: dict[str, list] = {"Floor 1": [], "Floor 2": []}
    for e in msp.query("LINE[layer=='WALL']"):
        mx = (e.dxf.start.x + e.dxf.end.x) / 2
        my = (e.dxf.start.y + e.dxf.end.y) / 2
        if my <= PLAN_BAND_Y:
            continue
        floor = "Floor 1" if mx < split else "Floor 2"
        acc[floor] += [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
    out = {}
    for floor, pts in acc.items():
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        out[floor] = {"minx": min(xs), "miny": min(ys), "maxx": max(xs), "maxy": max(ys)}
    return out


def _openings(msp, fps) -> tuple[list, list]:
    """Plan windows ($TCHSYS$WIN2D) + exterior doors ($DorLib2D$)."""
    windows, doors = [], []
    for e in msp.query("INSERT"):
        name = e.dxf.name
        is_win = "WIN2D" in name
        is_door = "DorLib" in name or "DorLib2D" in name
        if not (is_win or is_door):
            continue
        cx, cy = e.dxf.insert.x, e.dxf.insert.y
        if cy <= PLAN_BAND_Y:                       # plan band only
            continue
        floor = None
        for fl, fp in fps.items():
            if fp["minx"] - EDGE_TOL <= cx <= fp["maxx"] + EDGE_TOL and \
               fp["miny"] - EDGE_TOL <= cy <= fp["maxy"] + EDGE_TOL:
                floor = fl
                break
        if floor is None:
            continue
        fp = fps[floor]
        facade = _facade_of(cx, cy, fp["minx"], fp["miny"], fp["maxx"], fp["maxy"])
        if facade is None:
            continue                                 # interior door — not a gt opening
        # along-facade centre (mm, local to the facade's start corner) + width
        if facade in ("North", "South"):
            centre = cx - fp["minx"]
        else:
            centre = cy - fp["miny"]
        rec = {"facade": facade, "floor": floor, "centre_mm": round(centre, 1)}
        if is_win:
            rec["width_mm"] = round(abs(e.dxf.xscale), 1)
            windows.append(rec)
        else:
            doors.append(rec)
    return windows, doors


def _to_openings_m(wins: list[dict]) -> dict[tuple, list]:
    """(facade, floor) -> sorted [{x_m, width_m}] (x_m = left edge, facade-local)."""
    out: dict[tuple, list] = {}
    for w in wins:
        x0 = (w["centre_mm"] - w["width_mm"] / 2) / 1000.0
        out.setdefault((w["facade"], w["floor"]), []).append(
            {"x_m": round(x0, 3), "width_m": round(w["width_mm"] / 1000.0, 3)})
    for k in out:
        out[k].sort(key=lambda o: o["x_m"])
    return out


def extract(case: str) -> dict:
    bundle = GT_DIR / case
    dxf_path = bundle / "source.dxf"
    gt = json.loads((bundle / "gt.json").read_text(encoding="utf-8"))

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    titles = _titles(msp)
    fps = _plan_footprints(msp, titles)
    wins, doors = _openings(msp, fps)
    openings = _to_openings_m(wins)

    # footprint (m) from Floor 1 plan
    fp1 = fps.get("Floor 1") or next(iter(fps.values()))
    footprint = {"W_m": round((fp1["maxx"] - fp1["minx"]) / 1000.0, 3),
                 "D_m": round((fp1["maxy"] - fp1["miny"]) / 1000.0, 3)}

    # reconcile vs existing gt + inject openings into a proposed v2
    proposed = copy.deepcopy(gt)
    proposed["schema_version"] = 2
    proposed["_source"] = "cad_dxf"
    proposed["_cad_file"] = "source.dxf"
    proposed["_cad_sha256"] = _sha256(dxf_path)
    proposed["_extractor"] = "gt_from_dxf v1"

    report = {"case": case, "footprint_cad": footprint, "footprint_gt": gt["footprint"],
              "doors_cad": [(d["facade"], d["floor"]) for d in doors], "rows": []}
    for w in proposed.get("windows", []):
        key = (w["facade"], w["floor"])
        ops = openings.get(key, [])
        cad_n, gt_n = len(ops), int(w.get("count", 0))
        if ops:
            w["openings"] = ops
        report["rows"].append({"facade": w["facade"], "floor": w["floor"],
                               "gt_count": gt_n, "cad_count": cad_n,
                               "match": cad_n == gt_n,
                               "openings": ops})
    return {"report": report, "proposed": proposed, "bundle": bundle}


def _print_report(r: dict) -> None:
    rep = r["report"]
    print(f"case: {rep['case']}")
    print(f"footprint  CAD {rep['footprint_cad']}  vs gt {rep['footprint_gt']}")
    print(f"exterior doors (CAD): {rep['doors_cad']}")
    print("\nwindow reconciliation (facade/floor : gt vs CAD count):")
    all_match = True
    for row in rep["rows"]:
        mark = "OK " if row["match"] else "!! "
        all_match &= row["match"]
        ops = "  ".join(f"x{o['x_m']:g}/w{o['width_m']:g}" for o in row["openings"])
        print(f"  {mark}{row['facade']:<6} {row['floor']:<8} gt={row['gt_count']} cad={row['cad_count']}   {ops}")
    print(f"\nall counts match gt: {all_match}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract maximal gt (exact window openings) from a 天正 plain DXF.")
    ap.add_argument("case", help="case name, e.g. sm21_anchor")
    ap.add_argument("--write", action="store_true",
                    help="write the proposed gt to gt/<case>/gt_from_cad.json (default: report only)")
    args = ap.parse_args()

    r = extract(args.case)
    _print_report(r)
    if args.write:
        out = r["bundle"] / "gt_from_cad.json"
        out.write_text(json.dumps(r["proposed"], ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nwrote proposed gt -> {out}  (review via overlay, then promote to gt.json)")


if __name__ == "__main__":
    main()
