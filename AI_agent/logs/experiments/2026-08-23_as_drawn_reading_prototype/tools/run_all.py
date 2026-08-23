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

# ⭐ the scoreable denominator (denominator.py) + the reading grade (reading_grade.py):
# answer source, conversion request, plan view id, product name
DEN = [("sm25_F1", "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf",
        "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json",
        "plan-F1", "sm25_1f"),
       ("sm25_F2", "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf",
        "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json",
        "plan-F2", "sm25_2f"),
       ("sm24_F1", "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf",
        "tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json",
        "plan-F1", "sm24_1f")]
GRADE_NEUTERS = ["punch_middle", "shrink_runs", "keep_longest_run", "drop_one_of_each_pair",
                 "duplicate_face", "widen_all", "extend_runs_full"]

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
# ⭐ The third cross-family review's own fixtures (tools/crossreview_mutate_v2.py).
# ⛔ They stay in the matrix permanently: a reviewer's cheat that once worked is
# the most valuable regression fixture there is.
CROSS_NEUTERS = ["missing_wall_middle", "fake_opening_over_missing_wall",
                 "one_pixel_actual_schema", "all_ambiguous", "all_non_wall"]

SHORT = {"reverse_ledger_no_phantom_ink": "phantom",
         "observations_recomputable_from_own_pixels": "recompute",
         "gap_evidence_recomputable_from_original_image": "gaps",
         "face_span_fully_accounted_by_runs_or_gaps": "spanacct",
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
            "gates": {SHORT.get(c2["check"], c2["check"]): c2["status"] for c2 in d["checks"]},
            "gt_side_ok_pct": json.loads(so2)["overall_ok_pct"] if rc2 == 0 else "ERROR"}

    # ⭐ the third review's fixtures, re-run every time
    res["crossreview_neuters"] = {}
    for m in CROSS_NEUTERS:
        doc = OUT / f"sm25_1f_CROSS_{m}.json"
        rc, so, se = run([str(T / "crossreview_mutate_v2.py"), str(OUT / "sm25_1f_v2.json"),
                          str(doc), m])
        if rc:
            res["crossreview_neuters"][m] = {"outcome": "MUTATION_FAILED",
                                             "message": se.strip()[-200:]}
            continue
        rc, _, _ = run([str(T / "checks_as_drawn_v2.py"), str(doc), str(T / "cfg_1f_full.json"),
                        str(OUT / f"sm25_1f_CROSS_{m}_checks.json")])
        d = json.loads((OUT / f"sm25_1f_CROSS_{m}_checks.json").read_text())
        rc2, so2, _ = run([str(T / "reconstruct_check_v2.py"), "sm25-L_anchor",
                           json.dumps({"F1": str(doc)}), str(OUT / f"sm25_1f_CROSS_{m}_gt.json")])
        res["crossreview_neuters"][m] = {
            "mutation": json.loads(doc.read_text()).get("crossreview_mutation"),
            "gates": {SHORT.get(c["check"], c["check"]): c["status"] for c in d["checks"]},
            "gt_side_ok_pct": json.loads(so2)["overall_ok_pct"] if rc2 == 0 else "ERROR"}

    # ⭐ denominator + reading grade
    res["denominator"], res["reading_grade"] = {}, {}
    for key, dxf, req_path, view, product in DEN:
        den_out = OUT / f"denominator_{key}.json"
        rc, so, se = run([str(T / "denominator.py"), dxf, req_path, view, str(den_out)])
        assert rc == 0, se[-400:]
        res["denominator"][key] = json.loads(den_out.read_text())["ledger"]
        g_out = OUT / f"grade_{product}.json"
        rc, so, se = run([str(T / "reading_grade.py"), str(OUT / f"{product}_v2.json"),
                          str(den_out), str(g_out)])
        assert rc == 0, se[-400:]
        g = json.loads(g_out.read_text())
        res["reading_grade"][product] = {"scores": g["scores"], "by_verdict": g["by_verdict"],
                                         "perception": g["perception"]}
    # ⛔ a 100% needs its ruler shaken: every neuter must move the grade the right way
    import copy as _copy
    import importlib.util as _ilu

    def _load(name):
        spec = _ilu.spec_from_file_location(name, T / f"{name}.py")
        mod = _ilu.module_from_spec(spec)
        sys.path.insert(0, str(T))
        spec.loader.exec_module(mod)
        return mod
    RC, RG = _load("reconstruct_check_v2"), _load("reading_grade")
    doc0 = json.loads((OUT / "sm25_1f_v2.json").read_text())
    den0 = json.loads((OUT / "denominator_sm25_F1.json").read_text())
    res["reading_grade_neuters"] = {}
    for m in GRADE_NEUTERS:
        d = _copy.deepcopy(doc0)
        try:
            RC._mutate(d, m)
        except SystemExit:
            continue
        res["reading_grade_neuters"][m] = RG.grade(d, den0)["scores"]

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

    # ⭐ MACHINE-CHECKED, not asserted in prose: a gate that is never red on any
    # fixture has no discriminating power, and one that is never green is
    # structurally unobservable.  The README used to CLAIM this; the third review
    # showed the claim was false for two gates on the matrix it pointed at.
    seen: dict[str, set] = {}
    for v in res["plans"].values():
        if not isinstance(v, dict) or "self_checks" not in v:
            continue
        for c, st in v["self_checks"].items():
            seen.setdefault(SHORT.get(c, c), set()).add(st)
        for mut in v["self_check_neuters"].values():
            if isinstance(mut, dict):
                for c, st in mut.items():
                    seen.setdefault(c, set()).add(st)
    for group in ("perception_neuters", "crossreview_neuters"):
        for v in res[group].values():
            for c, st in (v.get("gates") or {}).items():
                # ⚠️ normalise: one group stored full check names and another the
                # short ones, which split every gate into two half-populated rows
                # and made four gates look NEVER_RED.
                seen.setdefault(SHORT.get(c, c), set()).add(st)
    res["gate_discriminating_power"] = {
        g: {"seen": sorted(st),
            "verdict": ("ok" if {"green", "red"} <= st
                        else "NEVER_RED" if "red" not in st else "NEVER_GREEN")}
        for g, st in sorted(seen.items())}

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
    print("== third-review fixtures (sm25 1f; honest gt=94.6, all gates green) ==")
    for k, v in res["crossreview_neuters"].items():
        if "gates" not in v:
            print(f"  {k:34s} {v['outcome']}")
            continue
        reds = [g for g, st in v["gates"].items() if st == "red"]
        print(f"  {k:34s} gt={v['gt_side_ok_pct']:<6} red_gates={reds or 'NONE ⛔'}")
    print("== denominator + reading grade ==")
    for k, v in res["denominator"].items():
        print(f"  {k}: {v['wall_layer_segments_collected']} segs -> "
              f"caps {v['excluded_jamb_caps_geometric']} (converter's length rule would cut "
              f"{v['would_be_excluded_by_converter_length_rule']}) -> "
              f"{v['scoreable_targets_after_merge']} targets / {v['total_scoreable_length_m']} m")
    for k, v in res["reading_grade"].items():
        s2 = v["scores"]
        print(f"  {k:9s} drawn={s2['C1_C2_targets_drawn_pct']}%  coverage={s2['C2_length_coverage_pct']}%"
              f"  bad_split={s2['C3_bad_split']}  extra={s2['C4_extra_length_m']} m"
              f"  abstained={v['perception']['abstained']}")
    print("  neuters (sm25_1f, honest drawn=100.0 / coverage=98.2):")
    for m, s2 in res["reading_grade_neuters"].items():
        print(f"    {m:24s} drawn={s2['C1_C2_targets_drawn_pct']:>6}  "
              f"coverage={s2['C2_length_coverage_pct']:>6}  split={s2['C3_bad_split']:>4}  "
              f"extra={s2['C4_extra_length_m']:>8}")
    print("== gate discriminating power (machine-checked) ==")
    for g, v in res["gate_discriminating_power"].items():
        mark = "  " if v["verdict"] == "ok" else "⛔"
        print(f"  {mark} {g:12s} seen={','.join(v['seen']):<24} {v['verdict']}")
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
