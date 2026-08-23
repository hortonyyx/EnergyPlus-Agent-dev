"""Re-run every v2 measurement and write one results file.

⭐ Exists because the second cross-family review rejected a design draft whose
numbers could not be traced to a product ("every number must be one I can point
at a run for").  Every figure quoted in the README must come out of this file.

    python3 tools/run_all.py            # -> out/RESULTS_v2.json  + a table
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
T, OUT = EXP / "tools", EXP / "out"
REPO = EXP.parents[3]
BIND = ("case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H2_fullcase"
        "/_run/judge_score_bindings.json")

PLANS = [("sm25_1f", "cfg_1f_full", "sm25-L_anchor", "F1"),
         ("sm25_2f", "cfg_2f_full", "sm25-L_anchor", "F2"),
         ("sm24_1f", "cfg_sm24", "sm24_anchor", "F1")]
PLAN_NEUTERS_GT = ["punch_middle", "punch_middle_one_pixel", "duplicate_face", "shrink_runs",
                   "keep_longest_run", "drop_one_of_each_pair", "misname_opening_family",
                   "drop_opening_role", "widen_all", "extend_runs_full"]
PLAN_NEUTERS_SELF = ["merge_runs", "extend_runs_full", "fabricate_pair_from_midline",
                     "swap_structure_role", "duplicate_face", "widen_all"]
ELEV_NEUTERS = ["shift_lines", "clear_runs", "shrink_runs", "spray_lines",
                "duplicate_line", "drop_vertical"]


# ⚠️ Short names must stay DISTINCT: an earlier version abbreviated by the first
# token, so `pair_hypothesis_*` and `pair_spacing_*` both became "pair" and the
# dict silently kept only the last one -- the table showed "green" for a gate
# that was red.  A display bug is still a wrong number on the page.
SHORT = {"reverse_ledger_no_phantom_ink": "phantom",
         "observations_recomputable_from_own_pixels": "recompute",
         "opening_role_matches_where_the_ink_sits": "openrole",
         "pair_hypothesis_reconciles_with_observations": "reconcile",
         "pair_spacing_explicable_by_callouts": "spacing",
         "forward_ledger_structural_ink_claimed": "forward"}


def run(args: list[str]) -> tuple[int, str, str]:
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=REPO)
    return r.returncode, r.stdout, r.stderr


def main() -> int:
    res: dict = {"generated_from": "tools/run_all.py", "plans": {}, "elevation": {}}

    for name, cfg, gt_case, floor in PLANS:
        rc, so, se = run([str(T / "as_drawn_v2.py"), str(T / f"{cfg}.json"), str(OUT / f"{name}_v2.json")])
        assert rc == 0, se
        doc = json.loads((OUT / f"{name}_v2.json").read_text())
        rc, so, se = run([str(T / "checks_as_drawn_v2.py"), str(OUT / f"{name}_v2.json"),
                          str(T / f"{cfg}.json"), str(OUT / f"{name}_checks_v2.json")])
        chk = json.loads((OUT / f"{name}_checks_v2.json").read_text())
        res["plans"][name] = {
            "ledger": doc["ledger"],
            "self_checks": {c["check"]: c["status"] for c in chk["checks"]},
            "self_check_detail": {c["check"]: {k: v for k, v in c.items()
                                               if k in ("violation_count", "worst_coverage",
                                                        "unclaimed_pct", "share_of_gap_ink",
                                                        "degraded_reason")}
                                  for c in chk["checks"]},
            "self_check_neuters": {},
        }
        for m in PLAN_NEUTERS_SELF:
            rc, so, se = run([str(T / "checks_as_drawn_v2.py"), str(OUT / f"{name}_v2.json"),
                              str(T / f"{cfg}.json"), str(OUT / f"{name}_checks_v2_MUT_{m}.json"), m])
            if rc:
                res["plans"][name]["self_check_neuters"][m] = "ERROR"
                continue
            d = json.loads((OUT / f"{name}_checks_v2_MUT_{m}.json").read_text())
            res["plans"][name]["self_check_neuters"][m] = {SHORT.get(c["check"], c["check"]):
                                                           c["status"] for c in d["checks"]}

    # gt-side reconstruction, whole case
    for gt_case, docs, key in (("sm25-L_anchor", {"F1": "sm25_1f", "F2": "sm25_2f"}, "sm25"),
                               ("sm24_anchor", {"F1": "sm24_1f"}, "sm24")):
        argmap = json.dumps({k: str(OUT / f"{v}_v2.json") for k, v in docs.items()})
        rc, so, se = run([str(T / "reconstruct_check_v2.py"), gt_case, argmap,
                          str(OUT / f"{key}_reconstruct_v2.json")])
        assert rc == 0, se
        base = json.loads(so)
        muts = {}
        for m in PLAN_NEUTERS_GT:
            rc, so2, se2 = run([str(T / "reconstruct_check_v2.py"), gt_case, argmap,
                                str(OUT / f"{key}_recon_v2_MUT_{m}.json"), m])
            muts[m] = json.loads(so2)["overall_ok_pct"] if rc == 0 else "ERROR"
        res["plans"].setdefault("_gt_side", {})[key] = {
            "honest": {k: base[k] for k in ("overall_ok_pct", "exterior", "interior",
                                            "matched_by_kind", "targets")},
            "neuters": muts}

    # ⭐ bad fixtures on PERCEPTION itself: does a wrong recognition go red?
    import copy
    base_p = json.loads((EXP / "perception/sm25_1f.json").read_text())
    base_c = json.loads((T / "cfg_1f_full.json").read_text())
    VARIANTS = {
        "honest": lambda q: None,
        "pair_the_callout_text": lambda q: q["wall_pairs"].append(["L033", "L035"]),
        "forget_a_face_line": lambda q: q["non_wall_face_lines"].pop("L018"),
        "pair_two_faces_of_different_walls": lambda q: (q["wall_pairs"].remove(["L005", "L007"]),
                                                        q["wall_pairs"].append(["L005", "L008"])),
        "call_the_windows_furniture": lambda q: q["family_roles"].update(
            {"fenestration": q["family_roles"]["furniture"], "furniture": "F3"}),
        "reference_a_line_that_does_not_exist": lambda q: q["wall_pairs"].append(["L001", "L999"]),
    }
    res["perception_neuters"] = {}
    scratch = EXP / "perception/_neuters"
    scratch.mkdir(exist_ok=True)
    for name, mut in VARIANTS.items():
        q = copy.deepcopy(base_p)
        mut(q)
        pf = scratch / f"{name}.json"
        pf.write_text(json.dumps(q, ensure_ascii=False, indent=1))
        c = dict(base_c)
        c["perception"] = str(pf)
        cf = scratch / f"cfg_{name}.json"
        cf.write_text(json.dumps(c, ensure_ascii=False, indent=1))
        doc = scratch / f"{name}_product.json"
        rc, so, se = run([str(T / "as_drawn_v2.py"), str(cf), str(doc)])
        if rc:
            res["perception_neuters"][name] = {"outcome": "LOUD_FAILURE",
                                               "message": se.strip().splitlines()[-1][:160]}
            continue
        rc, so, se = run([str(T / "checks_as_drawn_v2.py"), str(doc), str(cf),
                          str(scratch / f"{name}_checks.json")])
        d = json.loads((scratch / f"{name}_checks.json").read_text())
        rc2, so2, _ = run([str(T / "reconstruct_check_v2.py"), "sm25-L_anchor",
                           json.dumps({"F1": str(doc)}), str(scratch / f"{name}_gt.json")])
        res["perception_neuters"][name] = {
            "pairs_status": json.loads(doc.read_text())["hypotheses"]["pairs_status"],
            "gates": {c2["check"]: c2["status"] for c2 in d["checks"]},
            "gt_side_ok_pct": json.loads(so2)["overall_ok_pct"] if rc2 == 0 else "ERROR"}

    # elevation structure lines
    docs = json.dumps({f"{v}_view": str(OUT / f"sm25_{v.lower()}_as_drawn.json")
                       for v in ("East", "North", "South", "West")})
    rc, so, se = run([str(T / "reconstruct_elev_lines_check_v2.py"), "sm25-L_anchor", BIND,
                      docs, str(OUT / "sm25_elev_lines_v2.json")])
    assert rc == 0, se
    res["elevation"]["honest"] = json.loads(so.splitlines()[0])
    res["elevation"]["neuters"] = {}
    for m in ELEV_NEUTERS:
        rc, so2, _ = run([str(T / "reconstruct_elev_lines_check_v2.py"), "sm25-L_anchor", BIND,
                          docs, str(OUT / f"sm25_elev_lines_v2_MUT_{m}.json"), m])
        d = json.loads(so2.splitlines()[0])
        res["elevation"]["neuters"][m] = {"ok_pct": d["ok_pct"],
                                          "unpredicted_lines": d["unpredicted_lines"]}
    rc, so2, _ = run([str(T / "reconstruct_elev_lines_check_v2.py"), "--selftest"])
    res["elevation"]["one_to_one_selftest"] = json.loads(so2)

    (OUT / "RESULTS_v2.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")

    print("== plans ==")
    for k, v in res["plans"].items():
        if k == "_gt_side":
            continue
        L = v["ledger"]
        print(f"  {k:9s} faces={L['face_lines']:3d} cand={L['pair_candidates']:5d} "
              f"pairs={L['pairs_selected']} [{L['pairs_status']}]  "
              + " ".join(f"{SHORT.get(c, c)}={s}" for c, s in v["self_checks"].items()))
    print("== gt side ==")
    for k, v in res["plans"]["_gt_side"].items():
        print(f"  {k}: honest={v['honest']['overall_ok_pct']}  neuters="
              + " ".join(f"{m}:{s}" for m, s in v["neuters"].items()))
    print("== perception neuters (sm25 1f) ==")
    for k, v in res["perception_neuters"].items():
        if "gates" not in v:
            print(f"  {k:38s} {v['outcome']}")
            continue
        print(f"  {k:38s} gt={v['gt_side_ok_pct']:<6} "
              + " ".join(f"{SHORT.get(c, c)}={st}" for c, st in v["gates"].items()))
    print("== elevation ==")
    e = res["elevation"]
    print(f"  honest {e['honest']['ok']}/{e['honest']['targets']} "
          f"max_err={e['honest']['max_abs_err_m']} min_cover={e['honest']['min_span_cover_seen']}")
    print("  neuters " + " ".join(f"{m}:{d['ok_pct']}%/unpred{d['unpredicted_lines']}"
                                  for m, d in e["neuters"].items()))
    print(f"  -> {OUT / 'RESULTS_v2.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
