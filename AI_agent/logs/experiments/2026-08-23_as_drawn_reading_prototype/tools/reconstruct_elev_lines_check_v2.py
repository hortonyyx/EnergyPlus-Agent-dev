"""Do the elevation's as-drawn STRUCTURE LINES land where the answer says --
AND are they drawn over the extent the answer predicts?

⭐ Why a v2 exists.  The second cross-family review (sol, 2026-08-23) showed the
v1 of this check was position-only and therefore green on products that carry no
drawn extent at all:

    * clearing every ``runs_m`` to ``[]``      -> still 24/24
    * ``covered_px=1, span_ratio=0.001``       -> still 24/24
    * no one-to-one assignment (one observed line could satisfy many targets)
    * ``view_id`` was accepted and then ignored; levels were taken from every
      floor for every facade; depth was aggregated across floors.

v2 fixes all four.  It still reads gt and still changes nothing in it: every
target -- position AND predicted extent -- is derived from fields that are
already in the answer for other reasons.

  target            constant coordinate            predicted extent (the other axis)
  ----------------  -----------------------------  ---------------------------------
  level             z_floor_m / +ceiling_height_m  union of world_along_interval of
                                                   the segments of this facade on the
                                                   floors that meet that z
  silhouette        min/max world_along_interval   union of [z_floor, z_floor+h] over
                                                   the floors whose segment touches it
  depth step (R-4)  along where depth changes      same, over the floors that step

A line the answer does not predict is still reported as ``unpredicted`` rather
than scored -- "gt predicts every drawn line" is a claim this round has not
earned -- but v2 also reports it as a flag, because a product that sprays
lines everywhere would otherwise find a match for every target for free.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scipy.optimize import linear_sum_assignment  # noqa: E402

from src.agent.judge.gt import load_gt_document  # noqa: E402

TOL_M = 0.05          # same position tolerance as v1
MIN_SPAN_COVER = 0.80  # fraction of the predicted extent that must carry ink
EPS = 1e-6


# --------------------------------------------------------------------------- geometry helpers
def _union(iv):
    out = []
    for lo, hi in sorted((min(a, b), max(a, b)) for a, b in iv):
        if out and lo <= out[-1][1] + EPS:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def _cover(runs, lo, hi):
    """Fraction of [lo, hi] covered by the union of ``runs``."""
    if hi - lo <= EPS:
        return 0.0
    tot = 0.0
    for a, b in _union(runs):
        tot += max(0.0, min(b, hi) - max(a, lo))
    return tot / (hi - lo)


# --------------------------------------------------------------------------- targets from gt
def _floor_span(f):
    return float(f.z_floor_m), float(f.z_floor_m) + float(f.ceiling_height_m)


def _targets(gt, binding: dict) -> list[dict]:
    """Structure-line targets for ONE facade, position + predicted extent."""
    fam = binding["facade_family"]
    # ⭐ view-aware: only the floors that actually have this facade
    floors = [f for f in gt.floors
              if any(s.facade_family == fam for s in f.boundary_segments)]
    if not floors:
        return []
    segs_by_floor = {id(f): [s for s in f.boundary_segments if s.facade_family == fam]
                     for f in floors}
    out: list[dict] = []

    # ---- horizontal lines: every slab level this facade actually reaches
    zs: dict[float, list] = {}
    for f in floors:
        z0, z1 = _floor_span(f)
        zs.setdefault(round(z0, 4), []).append(f)
        zs.setdefault(round(z1, 4), []).append(f)
    for z, fs in sorted(zs.items()):
        along = _union([(s.world_along_interval.lo, s.world_along_interval.hi)
                        for f in fs for s in segs_by_floor[id(f)]])
        out.append({"kind": "level", "quantity": "z", "value": z,
                    "extent_quantity": "along",
                    "extent": [round(along[0][0], 4), round(along[-1][1], 4)],
                    "extent_runs": [[round(a, 4), round(b, 4)] for a, b in along]})

    # ---- vertical lines: silhouette + depth step
    lo = min(s.world_along_interval.lo for f in floors for s in segs_by_floor[id(f)])
    hi = max(s.world_along_interval.hi for f in floors for s in segs_by_floor[id(f)])

    def _z_extent(at_along, *, require_step: bool):
        """z runs of the floors whose segments meet ``at_along`` (optionally stepping)."""
        runs = []
        for f in floors:
            edges: dict[float, set] = {}
            for s in segs_by_floor[id(f)]:
                for e in (s.world_along_interval.lo, s.world_along_interval.hi):
                    edges.setdefault(round(e, 4), set()).add(round(s.depth, 4))
            if round(at_along, 4) not in edges:
                continue
            if require_step and len(edges[round(at_along, 4)]) < 2:
                continue
            runs.append(_floor_span(f))
        return _union(runs) if runs else []

    for v in (lo, hi):
        zr = _z_extent(v, require_step=False)
        if not zr:
            continue
        out.append({"kind": "silhouette", "quantity": "x", "value": round(v, 4),
                    "extent_quantity": "z",
                    "extent": [round(zr[0][0], 4), round(zr[-1][1], 4)],
                    "extent_runs": [[round(a, 4), round(b, 4)] for a, b in zr]})

    steps: set[float] = set()
    for f in floors:
        edges: dict[float, set] = {}
        for s in segs_by_floor[id(f)]:
            for e in (s.world_along_interval.lo, s.world_along_interval.hi):
                edges.setdefault(round(e, 4), set()).add(round(s.depth, 4))
        for e, ds in edges.items():
            if len(ds) > 1 and lo + EPS < e < hi - EPS:
                steps.add(e)
    for e in sorted(steps):
        zr = _z_extent(e, require_step=True)
        out.append({"kind": "depth_step", "quantity": "x", "value": round(e, 4),
                    "extent_quantity": "z",
                    "extent": [round(zr[0][0], 4), round(zr[-1][1], 4)],
                    "extent_runs": [[round(a, 4), round(b, 4)] for a, b in zr]})

    # de-duplicate coinciding targets (keep the wider predicted extent)
    best: dict[tuple, dict] = {}
    for t in out:
        k = (t["quantity"], t["value"])
        cur = best.get(k)
        if cur is None or (t["extent"][1] - t["extent"][0]) > (cur["extent"][1] - cur["extent"][0]):
            best[k] = t
    return sorted(best.values(), key=lambda t: (t["quantity"], t["value"]))


# --------------------------------------------------------------------------- product side
def _observed(doc: dict, b: dict) -> list[dict]:
    """Structure lines in WORLD coordinates: constant value + drawn runs."""
    out = []
    for line in doc["structure_lines"]:
        q = line["constant_quantity"]
        runs = [list(map(float, r)) for r in line.get("runs_m", [])]
        if q == "x":                      # vertical line: const is along, runs are z
            val = b["along_origin"] + b["sign"] * float(line["pos_m"])
        else:                             # horizontal line: const is z, runs are along
            val = float(line["pos_m"])
            runs = [sorted((b["along_origin"] + b["sign"] * r[0],
                            b["along_origin"] + b["sign"] * r[1])) for r in runs]
        out.append({"id": line["id"], "quantity": q, "value": val, "runs": runs,
                    "covered_px": line.get("covered_px"),
                    "span_ratio": line.get("span_ratio")})
    return out


# --------------------------------------------------------------------------- mutations
def _mutate(docs: dict[str, dict], kind: str) -> str:
    n = 0
    for doc in docs.values():
        lines = doc["structure_lines"]
        if kind == "shift_lines":
            for ln in lines:
                ln["pos_m"] += 0.10
                n += 1
        elif kind == "clear_runs":                       # sol's exploit #5
            for ln in lines:
                ln["runs_m"] = []
                ln["covered_px"] = 1
                ln["span_ratio"] = 0.001
                n += 1
        elif kind == "shrink_runs":                      # drawn, but only a stub
            for ln in lines:
                new = []
                for a, b in ln["runs_m"]:
                    mid, half = (a + b) / 2.0, (b - a) * 0.15
                    new.append([mid - half, mid + half])
                ln["runs_m"] = new
                n += 1
        elif kind == "spray_lines":                      # spurious near-duplicates
            add = []
            for ln in lines:
                for k in (1, 2, 3):
                    c = json.loads(json.dumps(ln))
                    c["id"] = f"{ln['id']}x{k}"
                    c["pos_m"] = ln["pos_m"] + 0.03 * k
                    add.append(c)
                    n += 1
            lines.extend(add)
        elif kind == "duplicate_line":                   # assignment-reuse probe
            add = []
            for ln in lines:
                c = json.loads(json.dumps(ln))
                c["id"] = ln["id"] + "d"
                c["pos_m"] = ln["pos_m"] + 0.0002       # 0.2 mm apart, as in G-1
                add.append(c)
                n += 1
            lines.extend(add)
        elif kind == "drop_vertical":                    # lose silhouette + depth step
            keep = [ln for ln in lines if ln["constant_quantity"] != "x"]
            n += len(lines) - len(keep)
            doc["structure_lines"] = keep
        else:
            raise SystemExit(f"unknown mutation {kind!r}")
    return f"MUTATED[{kind}]: touched {n} structure lines"


# --------------------------------------------------------------------------- main
def main(gt_case: str, bindings_path: str, docs_arg: dict[str, str], out_path: str,
         *, mutate: str | None = None,
         tol_m: float = TOL_M, min_span_cover: float = MIN_SPAN_COVER) -> int:
    gt = load_gt_document(gt_case)
    binds = {b["input_id"]: b
             for b in json.loads(Path(bindings_path).read_text())["bindings"]
             if b["kind"] == "elevation"}
    docs = {v: json.loads(Path(p).read_text()) for v, p in docs_arg.items()}
    note = _mutate(docs, mutate) if mutate else None

    rows, extras = [], []
    for view_id, doc in sorted(docs.items()):
        b = binds.get(view_id)
        if b is None:
            continue
        obs = _observed(doc, b)
        tgts = _targets(gt, b)
        if not tgts:
            continue

        # ---- ⭐ one-to-one assignment: a line may satisfy at most ONE target
        BIG = 1e6
        cost = [[(abs(o["value"] - t["value"])
                  if o["quantity"] == t["quantity"] and abs(o["value"] - t["value"]) <= tol_m
                  else BIG) for o in obs] for t in tgts]
        pairs: dict[int, int] = {}
        if obs:
            ti, oi = linear_sum_assignment(cost)
            pairs = {int(i): int(j) for i, j in zip(ti, oi) if cost[i][j] < BIG}

        used = set()
        for i, t in enumerate(tgts):
            row = {"view": view_id, "kind": t["kind"], "quantity": t["quantity"],
                   "gt_value": t["value"], "extent": t["extent"]}
            j = pairs.get(i)
            if j is None:
                row["verdict"] = "NO_LINE"
                rows.append(row)
                continue
            o = obs[j]
            used.add(o["id"])
            err = abs(o["value"] - t["value"])
            cov = max(_cover(o["runs"], lo, hi) for lo, hi in t["extent_runs"]) \
                if t["extent_runs"] else 0.0
            row.update({"matched": o["id"], "obs_value": round(o["value"], 4),
                        "err_m": round(err, 4), "span_cover": round(cov, 4),
                        "verdict": "OK" if (err <= tol_m and cov >= min_span_cover)
                        else ("NOT_DRAWN" if err <= tol_m else "OFF_POSITION")})
            rows.append(row)
        for o in obs:
            if o["id"] not in used:
                extras.append({"view": view_id, "id": o["id"], "quantity": o["quantity"],
                               "value": round(o["value"], 4),
                               "runs": [[round(a, 4), round(b, 4)] for a, b in o["runs"]]})

    ok = [r for r in rows if r["verdict"] == "OK"]
    errs = sorted(r["err_m"] for r in rows if "err_m" in r)
    covs = sorted(r["span_cover"] for r in rows if "span_cover" in r)
    by_kind: dict[str, list[int]] = {}
    for r in rows:
        s = by_kind.setdefault(r["kind"], [0, 0])
        s[1] += 1
        s[0] += r["verdict"] == "OK"
    by_verdict: dict[str, int] = {}
    for r in rows:
        by_verdict[r["verdict"]] = by_verdict.get(r["verdict"], 0) + 1
    summary = {"gt_case": gt_case, "schema": "elev_structure_lines_v2",
               "mutation": note, "targets": len(rows), "ok": len(ok),
               "ok_pct": round(100.0 * len(ok) / max(1, len(rows)), 1),
               "by_kind": {k: f"{v[0]}/{v[1]}" for k, v in sorted(by_kind.items())},
               "by_verdict": dict(sorted(by_verdict.items())),
               "max_abs_err_m": errs[-1] if errs else None,
               "min_span_cover_seen": covs[0] if covs else None,
               # ⛔ NOT scored, but FLAGGED: gt does not claim to predict every drawn
               # line, so spraying lines cannot be scored against -- but a consumer
               # must not be able to read "24/24" without seeing that the product
               # also drew 72 lines nobody asked for.
               "unpredicted_lines": len(extras),
               "flags": (["UNPREDICTED_LINES"] if extras else []),
               "params": {"tol_m": tol_m, "min_span_cover": min_span_cover}}
    Path(out_path).write_text(json.dumps({"summary": summary, "rows": rows,
                                          "unpredicted": extras},
                                         ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    for r in rows:
        if r["verdict"] != "OK":
            print(f"    {r['verdict']:<13} {r['view']:<11} {r['kind']:<11} "
                  f"{r['quantity']}={r['gt_value']} err={r.get('err_m')} "
                  f"cover={r.get('span_cover')}")
    return 0


def selftest() -> int:
    """⭐ Show that one-to-one assignment is load-bearing.

    No drawing we own puts two targets within ``TOL_M`` of one line (sm25's
    levels are 3.6 m apart), so the property cannot be exercised by any real
    fixture on hand.  This synthetic pair does exercise it: two targets 4 cm
    apart and ONE observed line between them.  v1's ``min()`` matching would
    call both satisfied; v2 must satisfy exactly one.
    """
    tgts = [{"quantity": "z", "value": 3.60}, {"quantity": "z", "value": 3.64}]
    obs = [{"id": "S05", "quantity": "z", "value": 3.62}]
    v1 = sum(1 for t in tgts
             if min((abs(o["value"] - t["value"]) for o in obs), default=9) <= TOL_M)
    BIG = 1e6
    cost = [[(abs(o["value"] - t["value"])
              if o["quantity"] == t["quantity"] and abs(o["value"] - t["value"]) <= TOL_M
              else BIG) for o in obs] for t in tgts]
    ti, oi = linear_sum_assignment(cost)
    v2 = sum(1 for i, j in zip(ti, oi) if cost[i][j] < BIG)
    print(json.dumps({"selftest": "one_to_one_assignment", "targets": len(tgts),
                      "observed_lines": len(obs), "v1_min_matching_ok": v1,
                      "v2_one_to_one_ok": v2,
                      "verdict": "PASS" if (v1 == 2 and v2 == 1) else "FAIL"}))
    return 0 if (v1 == 2 and v2 == 1) else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        raise SystemExit(selftest())
    kw = {}
    if len(sys.argv) > 5 and sys.argv[5] not in ("", "-"):
        kw["mutate"] = sys.argv[5]
    if len(sys.argv) > 6:
        kw["tol_m"] = float(sys.argv[6])
    if len(sys.argv) > 7:
        kw["min_span_cover"] = float(sys.argv[7])
    raise SystemExit(main(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), sys.argv[4], **kw))
