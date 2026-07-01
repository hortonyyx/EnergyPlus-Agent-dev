#!/usr/bin/env python3
"""CLI: score a reading (0_reading plan JSONs) against the case ground truth.

The AUTHORITATIVE reading-quality metric (user directive 2026-06-24): match the
reading's wall/window COORDINATES against gt, element by element — counts AND
offsets. Renders are auxiliary; this table is what calls a reading good/bad.

Usage:
  python scripts/tool_scripts/score_reading_vs_gt.py <reading_dir> --case <case>
  python scripts/tool_scripts/score_reading_vs_gt.py <one_view.json> --case <case> --floor "Floor 1"

  <reading_dir>  a dir containing 1f_view.json / 2f_view.json (plan views)
  --case         gt case name under case_tests/test_baseline/gt/<case>/gt.json
  --wall-tol     metres; a gt wall line counts as found within this (default 0.30)
  --win-tol      metres; a gt window counts as found if its centre is within this (default 0.40)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agent.judge.gt import load_gt  # noqa: E402
from src.agent.judge import reading_score as rs  # noqa: E402


def _fmt_walls(matches):
    cells = []
    for m in matches:
        if m.read is None:
            cells.append(f"{m.truth}→MISS")
        else:
            cells.append(f"{m.truth}→{m.read}(Δ{m.delta:+})")
    return ", ".join(cells) if cells else "—"


def _print_floor(stem, sc):
    wh, wt = sc.wall_hits()
    nh, nt = sc.window_hits()
    print(f"\n## {stem}  ({sc.floor})")
    print(f"  walls   {wh}/{wt} hit   (max offset {sc.max_wall_offset()} m)")
    print(f"    vert x : {_fmt_walls(sc.vwalls)}" + (f"  | EXTRA {sc.extra_vwalls}" if sc.extra_vwalls else ""))
    print(f"    horiz y: {_fmt_walls(sc.hwalls)}" + (f"  | EXTRA {sc.extra_hwalls}" if sc.extra_hwalls else ""))
    print(f"  windows {nh}/{nt} hit")
    for f in ("N", "S", "E", "W"):
        ms = sc.windows.get(f, [])
        if not ms and not sc.extra_windows.get(f):
            continue
        parts = []
        for m in ms:
            ts, te = m.truth
            parts.append(f"{ts}-{te}:" + ("MISS" if m.read is None else f"OK(Δc{m.centre_delta:+})"))
        ex = sc.extra_windows.get(f, [])
        extra = f"  EXTRA {ex}" if ex else ""
        print(f"    {f}: {', '.join(parts) if parts else '—'}{extra}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="reading dir, or a single *_view.json")
    ap.add_argument("--case", required=True)
    ap.add_argument("--floor", help="gt floor name (single-file mode)")
    ap.add_argument("--gt-dir")
    ap.add_argument("--wall-tol", type=float, default=rs.DEFAULT_WALL_TOL_M)
    ap.add_argument("--win-tol", type=float, default=rs.DEFAULT_WIN_CENTRE_TOL_M)
    ap.add_argument("--json", action="store_true", help="also emit machine-readable summary after human rows")
    ap.add_argument("--json-only", action="store_true", help="emit only the machine-readable summary")
    args = ap.parse_args()

    target = Path(args.target)
    if target.is_dir():
        scores = rs.score_reading_dir(
            target, args.case, gt_dir=args.gt_dir, wall_tol=args.wall_tol, win_tol=args.win_tol
        )
    else:
        gt = load_gt(args.case, gt_dir=args.gt_dir) if args.gt_dir else load_gt(args.case)
        if gt is None:
            print(f"no gt for case {args.case!r}", file=sys.stderr)
            return 2
        reading = json.loads(target.read_text(encoding="utf-8"))
        fname = args.floor or rs.floor_name_for_image(target.stem, gt)
        if fname is None:
            print("could not map image to a gt floor; pass --floor", file=sys.stderr)
            return 2
        scores = {target.stem: rs.score_floor(reading, gt, fname, wall_tol=args.wall_tol, win_tol=args.win_tol)}

    tot_wh = tot_wt = tot_nh = tot_nt = 0
    summary = {}
    for stem, sc in scores.items():
        wh, wt = sc.wall_hits(); nh, nt = sc.window_hits()
        tot_wh += wh; tot_wt += wt; tot_nh += nh; tot_nt += nt
        summary[stem] = {"walls": [wh, wt], "windows": [nh, nt], "max_wall_offset_m": sc.max_wall_offset()}

    if args.json_only:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"# reading↔gt score — case {args.case}  (wall_tol={args.wall_tol}m, win_tol={args.win_tol}m)")
    for stem, sc in scores.items():
        _print_floor(stem, sc)
    print(f"\n=== TOTAL: walls {tot_wh}/{tot_wt}, windows {tot_nh}/{tot_nt} ===")
    if args.json:
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
