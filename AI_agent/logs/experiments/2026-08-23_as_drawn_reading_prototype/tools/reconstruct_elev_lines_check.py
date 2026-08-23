"""Do the elevation's as-drawn STRUCTURE LINES land where the answer says?

⭐ Why this exists: the first cross-family review (sol, 2026-08-23) found that
``reconstruct_elev_check.py`` only walks ``gt.openings``, so the 34/34 result
said nothing about the outline / storey line / depth-step line that the same
round had just promoted to first-class output.  The design draft's §5.4 claim
("the elevation side needs no gt change") was therefore unsupported: a layer
cannot be emitted and simultaneously declared out of scope.

⛔ The remedy is NOT to add gt fields.  Every target these lines correspond to
is ALREADY in the answer, in fields put there for other reasons:

  * ground / storey / roof   <- ``floors[].z_floor_m`` and ``ceiling_height_m``
  * left / right silhouette  <- the facade's ``world_along_interval`` extent
  * depth step (R-4)         <- the ``along`` coordinate where two boundary
                                segments of the same facade family change
                                ``depth``

So this check derives the targets and compares.  It reads gt; it does not
change it.  A line the answer does not predict is reported as ``extra``
rather than scored, because "every structure line must be predictable from
gt" is a claim this round has not earned.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.agent.judge.gt import load_gt_document  # noqa: E402

TOL_M = 0.05


def _targets(gt, view_id: str, binding: dict) -> list[dict]:
    """Structure-line targets for one facade, derived from existing gt fields."""
    out = []
    # horizontal: every floor level, plus the top of the topmost floor
    zs = sorted({f.z_floor_m for f in gt.floors} |
                {f.z_floor_m + f.ceiling_height_m for f in gt.floors})
    for z in zs:
        out.append({"kind": "level", "quantity": "z", "value": round(z, 4)})

    fam = binding["facade_family"]
    segs = [s for f in gt.floors for s in f.boundary_segments if s.facade_family == fam]
    if not segs:
        return out
    # vertical: the facade's own extent, plus every along-coordinate where the
    # depth changes (that is the R-4 front/back step line, drawn as a stroke).
    lo = min(s.world_along_interval.lo for s in segs)
    hi = max(s.world_along_interval.hi for s in segs)
    for v in (lo, hi):
        out.append({"kind": "silhouette", "quantity": "x", "value": round(v, 4)})
    depths = {}
    for s in segs:
        for edge in (s.world_along_interval.lo, s.world_along_interval.hi):
            depths.setdefault(round(edge, 4), set()).add(round(s.depth, 4))
    for edge, ds in sorted(depths.items()):
        if len(ds) > 1 and lo < edge < hi:
            out.append({"kind": "depth_step", "quantity": "x", "value": edge,
                        "depths": sorted(ds)})
    # de-duplicate targets that coincide
    seen, uniq = set(), []
    for t in out:
        k = (t["quantity"], t["value"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return uniq


def main(gt_case: str, bindings_path: str, docs: dict[str, str], out_path: str,
         *, mutate: str | None = None) -> int:
    gt = load_gt_document(gt_case)
    binds = {b["input_id"]: b for b in json.loads(Path(bindings_path).read_text())["bindings"]
             if b["kind"] == "elevation"}
    rows, extras = [], []
    for view_id, doc_path in sorted(docs.items()):
        b = binds.get(view_id)
        if b is None:
            continue
        doc = json.loads(Path(doc_path).read_text())
        obs = []
        for line in doc["structure_lines"]:
            v = line["pos_m"]
            if mutate == "shift_lines":
                v += 0.10
            if line["constant_quantity"] == "x":
                v = b["along_origin"] + b["sign"] * v
            obs.append({"id": line["id"], "quantity": line["constant_quantity"],
                        "value": v, "covered_px": line["covered_px"],
                        "span_ratio": line["span_ratio"]})
        used = set()
        for t in _targets(gt, view_id, b):
            same = [o for o in obs if o["quantity"] == t["quantity"]]
            best = min(same, key=lambda o: abs(o["value"] - t["value"]), default=None)
            row = {"view": view_id, "kind": t["kind"], "quantity": t["quantity"],
                   "gt_value": t["value"]}
            if best is None:
                row["verdict"] = "NO_LINE"
            else:
                err = abs(best["value"] - t["value"])
                row.update({"matched": best["id"], "obs_value": round(best["value"], 4),
                            "err_m": round(err, 4),
                            "verdict": "OK" if err <= TOL_M else "OFF_POSITION"})
                if err <= TOL_M:
                    used.add(best["id"])
            rows.append(row)
        for o in obs:
            if o["id"] not in used:
                extras.append({"view": view_id, **o, "value": round(o["value"], 4)})

    ok = [r for r in rows if r["verdict"] == "OK"]
    errs = sorted(r["err_m"] for r in rows if "err_m" in r)
    by_kind: dict[str, list[int]] = {}
    for r in rows:
        s = by_kind.setdefault(r["kind"], [0, 0])
        s[1] += 1
        s[0] += r["verdict"] == "OK"
    summary = {"gt_case": gt_case, "mutation": mutate, "targets": len(rows),
               "ok": len(ok), "ok_pct": round(100.0 * len(ok) / max(1, len(rows)), 1),
               "by_kind": {k: f"{v[0]}/{v[1]}" for k, v in sorted(by_kind.items())},
               "max_abs_err_m": errs[-1] if errs else None,
               # ⛔ NOT scored: gt does not claim to predict every drawn line.
               "unpredicted_lines": len(extras), "tol_m": TOL_M}
    Path(out_path).write_text(json.dumps({"summary": summary, "rows": rows,
                                          "unpredicted": extras},
                                         ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    for r in rows:
        if r["verdict"] != "OK":
            print(f"    {r['verdict']:<14} {r['view']:<11} {r['kind']:<11} "
                  f"{r['quantity']}={r['gt_value']} err={r.get('err_m')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), sys.argv[4],
                          mutate=sys.argv[5] if len(sys.argv) > 5 else None))
