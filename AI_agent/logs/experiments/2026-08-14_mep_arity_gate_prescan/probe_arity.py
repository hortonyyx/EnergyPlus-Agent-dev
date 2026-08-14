"""READ-ONLY probe: how many historical 4_mep artifacts would an IDD-driven
field-arity / required-field gate turn red?

Self-validation first (memory: 探针零输出 != 目标不存在):
  the known-bad artifact run_2026-08-13_accept_C MUST be flagged (14 thermostats).
If it is not, the probe is broken and the numbers below mean nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/workspaces/EnergyPlus-Agent-dev")

from src.validator.idf_fragments import parse_mep_fragments  # noqa: E402

ROOT = Path("/workspaces/EnergyPlus-Agent-dev")


def idd_fields(obj):
    """Return [(field_name, is_required)] from the IDD entry of this eppy object."""
    out = []
    objidd = getattr(obj, "objidd", None)
    if not objidd:
        return out
    for entry in objidd[1:]:  # entry[0] is the object-level metadata
        fname = entry.get("field")
        if not fname:
            continue
        name = fname[0] if isinstance(fname, (list, tuple)) else fname
        out.append((name, "required-field" in entry))
    return out


def audit_object(io):
    """Return list of findings for one parsed IdfObject."""
    obj = io.raw
    spec = idd_fields(obj)
    authored = list(obj.obj)[1:]  # drop the object-type token
    findings = []
    # (a) required field absent or blank
    for i, (fname, req) in enumerate(spec):
        if not req:
            continue
        val = authored[i] if i < len(authored) else None
        if val is None or str(val).strip() == "":
            findings.append(
                {"kind": "missing_required", "field_index": i + 1, "field": fname}
            )
    # (b) more fields than the IDD defines (extensible objects excluded below)
    if spec and len(authored) > len(spec):
        findings.append(
            {"kind": "too_many_fields", "authored": len(authored), "idd_max": len(spec)}
        )
    return findings, len(authored), len(spec)


def audit_run(mep_json: Path):
    mep = json.loads(mep_json.read_text())
    idx = parse_mep_fragments(mep)
    if not idx.ok:
        return {"parse_error": idx.parse_error}
    per_type = {}
    total_objs = 0
    total_bad = 0
    for io in idx.objects:
        total_objs += 1
        findings, n_auth, n_idd = audit_object(io)
        if findings:
            total_bad += 1
            rec = per_type.setdefault(io.obj_type, {"n": 0, "examples": []})
            rec["n"] += 1
            if len(rec["examples"]) < 2:
                rec["examples"].append(
                    {
                        "name": io.name,
                        "authored_fields": n_auth,
                        "idd_fields": n_idd,
                        "findings": findings,
                    }
                )
    return {"objects": total_objs, "flagged": total_bad, "by_type": per_type}


def main():
    runs = sorted(ROOT.glob("case_tests/e2e_tests/*/*/4_mep/mep_output.json"))
    runs += sorted(ROOT.glob("case_tests/e2e_tests/*/4_mep/mep_output.json"))
    print(f"# artifacts found: {len(runs)}\n")
    summary = []
    for r in runs:
        label = str(r.relative_to(ROOT)).replace("/4_mep/mep_output.json", "")
        try:
            res = audit_run(r)
        except Exception as e:  # noqa: BLE001
            print(f"!! {label}: {type(e).__name__}: {e}")
            continue
        if "parse_error" in res:
            print(f"{label}\n    PARSE ERROR: {res['parse_error']}")
            summary.append((label, -1, -1))
            continue
        print(f"{label}\n    objects={res['objects']}  flagged={res['flagged']}")
        for t, rec in sorted(res["by_type"].items(), key=lambda kv: -kv[1]["n"]):
            ex = rec["examples"][0]
            kinds = ",".join(sorted({f["kind"] for f in ex["findings"]}))
            miss = [f.get("field") for f in ex["findings"] if f["kind"] == "missing_required"]
            print(
                f"      {t}: {rec['n']}  [{kinds}] authored={ex['authored_fields']}"
                f" idd={ex['idd_fields']} missing={miss}"
            )
        summary.append((label, res["objects"], res["flagged"]))
    print("\n# ---- summary ----")
    for label, n, bad in summary:
        print(f"{bad:5d} / {n:5d}   {label}")


if __name__ == "__main__":
    main()
