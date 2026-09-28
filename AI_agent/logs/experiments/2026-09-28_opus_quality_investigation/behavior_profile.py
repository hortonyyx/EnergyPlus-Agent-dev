"""Per-run behaviour profile from tools.jsonl and first plan declaration (public records only).

Writes behavior_table.json (reference topics read, first build time, pixel/view counts, outcome class)
and first_declaration_basis.json. Needs runs_survey.json, partition_tolerance_reevaluation.json and
sm24_sm25_evaluation.json from the other scripts in this directory.
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)


def main():
    rows = {r["run"]: r for r in json.load(open(os.path.join(HERE, "runs_survey.json")))}
    reev = json.load(open(os.path.join(HERE, "partition_tolerance_reevaluation.json")))
    other = json.load(open(os.path.join(HERE, "sm24_sm25_evaluation.json")))
    table, basis_out = [], {}
    for num in sorted(rows):
        r = rows[num]
        d = os.path.join(EXP, r["dir"])
        topics, first_build, t0, pix_before, view_before = [], None, None, 0, 0
        if os.path.exists(os.path.join(d, "tools.jsonl")):
            for line in open(os.path.join(d, "tools.jsonl")):
                e = json.loads(line)
                t0 = t0 or e["time"]
                a = e["action"]
                if a == "get_bim_reference":
                    topics.append(e["data"].get("topic"))
                if a in ("build_plan_bim", "build_bim") and first_build is None:
                    first_build = round(e["time"] - t0)
                if first_build is None:
                    pix_before += "pixel" in (a or "")
                    view_before += a == "view_image"
        pix = sum(v for k, v in r["tool_actions"].items() if k and "pixel" in k)
        result = ""
        if str(num) in reev:
            e = reev[str(num)]["candidates"].get(reev[str(num)]["delivered"])
            if e:
                result = (",".join(e["0.3"]["object_topology"]) or "topo-ok") + f" hd{e['max_hausdorff_m']}"
        elif f"run{num}" in other and "gt" in other[f"run{num}"]:
            o = other[f"run{num}"]
            result = (",".join(o["gt"]["0.3"][0]) or "topo-ok") + f" hd{o['gt_hd_iou'][0]}"
        rc = r["receipt"]
        table.append(dict(run=num, case=r["case"], seed=r["seeded"], sys=r["system_sha"][:6],
                          reads_recon="reconstruction" in topics, topics=sorted(set(t for t in topics if t)),
                          first_build_s=first_build, view_before=view_before, pix_before=pix_before, pix_total=pix,
                          views=r["tool_actions"].get("view_image", 0), elapsed=rc.get("elapsed_s"),
                          end=rc.get("api_error_status") or rc.get("subtype"), result=result))
        drafts = sorted(glob.glob(os.path.join(d, "plan_drafts", "*", "plan.json")))
        if drafts:
            try:
                basis = json.load(open(drafts[0])).get("basis") or ""
            except ValueError:
                basis = ""
            low = basis.lower()
            tags = [t for t, pat in [("dimchain", r"dimension (chain|line|label)|dims|chains"), ("centre", r"cent(re|er)"),
                                     ("face", r"face"), ("pixel", r"pixel|profile|ink"), ("thickness", r"thick")] if re.search(pat, low)]
            basis_out[num] = dict(tags=tags, basis=basis[:260])
    json.dump(table, open(os.path.join(HERE, "behavior_table.json"), "w"), indent=1)
    json.dump(basis_out, open(os.path.join(HERE, "first_declaration_basis.json"), "w"), indent=1, ensure_ascii=False)
    for row in table:
        print(row["run"], row["case"], "recon" if row["reads_recon"] else "-", row["first_build_s"], row["pix_before"], row["views"], row["result"])


if __name__ == "__main__":
    main()
