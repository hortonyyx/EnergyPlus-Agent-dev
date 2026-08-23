"""Information-not-lost proof for the as-drawn ELEVATION layer.

The plan-side counterpart is ``reconstruct_check.py``; the question is the same
and so is the rule -- this one deliberately reads gt, the three self-checks do
not.

For every opening the answer layer carries on a facade, is there an as-drawn
opening on that facade at the same place?  The as-drawn layer emits RAW,
UNSNAPPED, UNCLASSIFIED openings in image-local facade coordinates, so the
comparison applies the run's own score binding (``world_along = along_origin +
sign * local_x``) and nothing else.  ⭐ It does NOT apply the witness-tick snap:
if the raw pixel measurement already lands on the answer, then handing the
snap to 1_correction costs nothing.

⭐ It also does not use gt's ``kind``.  Door-vs-window is exactly the call the
as-drawn layer refuses to make, so scoring it here would smuggle the judgement
back in.  What IS reported per opening is the measured evidence the classifier
will use -- sill height and the gap to the structure line below -- next to gt's
kind, so the separability of the two families can be read off instead of
assumed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.agent.judge.gt import load_gt_document  # noqa: E402

TOL_M = 0.05          # ~3.5 px at these drawings' 13.6 mm/px


def _iv(a, b):
    return (min(a, b), max(a, b))


def _ov(p, q):
    return max(0.0, min(p[1], q[1]) - max(p[0], q[0]))


def main(gt_case: str, bindings_path: str, docs: dict[str, str], out_path: str,
         *, mutate: str | None = None) -> int:
    gt = load_gt_document(gt_case)          # §1.5#4: the only sanctioned gt reader
    binds = {b["input_id"]: b for b in json.loads(Path(bindings_path).read_text())["bindings"]
             if b["kind"] == "elevation"}

    # gt opening -> facade, via the elevation source_ref it was extracted from
    by_view: dict[str, list] = {}
    for op in gt.openings:
        for r in op.source_refs:
            if r.role == "opening_elevation" and r.view_id:
                by_view.setdefault(r.view_id, []).append(op)
                break

    rows, missing = [], []
    for view_id, targets in sorted(by_view.items()):
        b = binds.get(view_id)
        doc_path = docs.get(view_id)
        if b is None or doc_path is None:
            continue
        doc = json.loads(Path(doc_path).read_text())
        obs = []
        for o in doc["openings"]:
            if mutate == "drop_smallest" and o["area_px"] <= 640:
                continue
            xs = o["x_range_m"]
            if mutate == "shift_10cm":
                xs = [v + 0.10 for v in xs]
            along = _iv(b["along_origin"] + b["sign"] * xs[0],
                        b["along_origin"] + b["sign"] * xs[1])
            obs.append((o, along, tuple(o["z_range_m"])))
        for t in targets:
            g_al = (t.world_along_interval.lo, t.world_along_interval.hi)
            g_z = (t.z_interval.lo, t.z_interval.hi)
            best, best_ov = None, 0.0
            for o, al, z in obs:
                ov = _ov(al, g_al) * _ov(z, g_z)
                if ov > best_ov:
                    best, best_ov = (o, al, z), ov
            row = {"view": view_id, "gt_id": t.id, "gt_kind": t.kind,
                   "gt_along": [round(v, 3) for v in g_al], "gt_z": [round(v, 3) for v in g_z]}
            if best is None:
                row["verdict"] = "NO_OPENING_HERE"
                missing.append(row)
            else:
                o, al, z = best
                err = max(abs(al[0] - g_al[0]), abs(al[1] - g_al[1]),
                          abs(z[0] - g_z[0]), abs(z[1] - g_z[1]))
                row.update({"matched": o["id"],
                            "obs_along": [round(v, 3) for v in al],
                            "obs_z": [round(v, 3) for v in z],
                            "max_abs_err_m": round(err, 4),
                            # evidence the door/window classifier will consume,
                            # reported NEXT TO gt's kind rather than scored
                            "sill_m": round(z[0], 3),
                            "gap_to_line_below_m": o["gap_to_line_below_m"],
                            "verdict": "OK" if err <= TOL_M else "OFF_POSITION"})
                if err > TOL_M:
                    missing.append(row)
            rows.append(row)

    ok = [r for r in rows if r["verdict"] == "OK"]
    errs = sorted(r["max_abs_err_m"] for r in rows if "max_abs_err_m" in r)
    summary = {"gt_case": gt_case, "mutation": mutate, "targets": len(rows),
               "ok": len(ok), "ok_pct": round(100.0 * len(ok) / max(1, len(rows)), 1),
               "max_abs_err_m": errs[-1] if errs else None,
               "median_abs_err_m": errs[len(errs) // 2] if errs else None,
               "tol_m": TOL_M}
    # separability of the two families on the measured evidence alone
    fam = {}
    for r in rows:
        if "sill_m" in r:
            fam.setdefault(r["gt_kind"], []).append(r["sill_m"])
    summary["sill_m_range_by_gt_kind"] = {k: [round(min(v), 3), round(max(v), 3)]
                                          for k, v in sorted(fam.items())}
    Path(out_path).write_text(json.dumps({"summary": summary, "rows": rows,
                                          "not_recovered": missing},
                                         ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    for r in missing[:10]:
        print(f"    {r['verdict']:<18} {r['view']:<11} {r['gt_kind']:<7} "
              f"along={r['gt_along']} z={r['gt_z']} err={r.get('max_abs_err_m')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), sys.argv[4],
                          mutate=sys.argv[5] if len(sys.argv) > 5 else None))
