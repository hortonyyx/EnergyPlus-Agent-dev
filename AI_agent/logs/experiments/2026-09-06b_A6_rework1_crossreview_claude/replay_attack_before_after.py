"""Independent replay of the reviewer's chain-reorder attack against BOTH the
pre-fix (94e899e5) and post-fix (current tree) tick_claim.py, without checking
out old code into the working tree. The old module is loaded from `git show`
output into an isolated module namespace; the new module is imported normally
from the current working tree (whose __file__ we print to prove provenance).
"""
import importlib.util
import json
import subprocess
import sys
import dataclasses

REPO = "/tmp/a6rw1_review_claude"


def load_module_from_commit(commit, relpath, modname):
    src = subprocess.run(["git", "show", f"{commit}:{relpath}"], cwd=REPO,
                          capture_output=True, check=True, text=True).stdout
    spec = importlib.util.spec_from_loader(modname, loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = f"<git show {commit}:{relpath}>"
    sys.modules[modname] = mod
    exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    return mod


def run_attack(m, label):
    print("=" * 70)
    print(f"{label}: module = {m.__file__}")
    print("=" * 70)
    doc_chain = {
        "schema": "as_drawn_elevation_v0",
        "image": "elev_B",
        "facade_label": "South",
        "calibration": {},
        "openings": [
            {"id": "O02", "x_range_m": [1.0, 2.0], "z_range_m": [0.5, 1.5],
             "edge_witnesses": {"x0": {"dimension_refs": ["cx_s1"]},
                                "x1": {"dimension_refs": ["cx_s2"]}}},
        ],
    }
    raw_chain = m.freeze(doc_chain)
    supplement = m.freeze(dict(
        schema="tick_reading_supplement_v1", source_sha=m.digest(raw_chain), image="elev_B",
        chains={"cx": dict(axis="x", values_mm=[1000, 1000, 1000],
                           cum_mm=[0, 1000, 2000, 3000], overall_mm=3000,
                           origin_mm=0, direction=1, qualification="drawing_dimension")},
        primary={}, declarations=[]))

    s5 = m.TickSession(raw_chain, image_id="elev_B", supplement=supplement)
    x0_candidates = {c.value_u: c.candidate_id for e in s5.packet.edges if e.edge_id == "O02:x0" for c in e.candidates}
    x1_candidates = {c.value_u: c.candidate_id for e in s5.packet.edges if e.edge_id == "O02:x1" for c in e.candidates}
    print(f"O02:x0 legitimate candidate values (u): {sorted(x0_candidates)}")
    print(f"O02:x1 legitimate candidate values (u): {sorted(x1_candidates)}")

    real_resp = m.TickResponse(packet_id=s5.packet.packet_id, choices=(
        m.TickChoice(edge_id="O02:x0", action="select", candidate_id=x0_candidates[10000], reason="node1"),
        m.TickChoice(edge_id="O02:x1", action="select", candidate_id=x1_candidates[20000], reason="node2"),
        m.TickChoice(edge_id="O02:z_low", action="pixel", reason="no chain"),
        m.TickChoice(edge_id="O02:z_high", action="pixel", reason="no chain"),
    ))
    real_batch5 = s5.submit(real_resp)
    legit_rows = json.loads(real_batch5.record)["rows"]
    print("legit submit() rows (x0,x1):", [(r["edge_id"], r["value_u"]) for r in legit_rows if "x" in r["edge_id"]])

    forged_rows = []
    for row in legit_rows:
        row = dict(row)
        if row["edge_id"] == "O02:x0":
            cid = x0_candidates[30000]
            cand = next(c for e in s5.packet.edges if e.edge_id == "O02:x0" for c in e.candidates if c.candidate_id == cid)
            row["choice"] = dict(edge_id="O02:x0", action="select", candidate_id=cid, reason="forged-swap")
            row["candidate"] = json.loads(m.freeze(dataclasses.asdict(cand)).decode())
            row["value_u"] = 30000
        elif row["edge_id"] == "O02:x1":
            cid = x1_candidates[0]
            cand = next(c for e in s5.packet.edges if e.edge_id == "O02:x1" for c in e.candidates if c.candidate_id == cid)
            row["choice"] = dict(edge_id="O02:x1", action="select", candidate_id=cid, reason="forged-swap")
            row["candidate"] = json.loads(m.freeze(dataclasses.asdict(cand)).decode())
            row["value_u"] = 0
        forged_rows.append(row)

    resp_dict = json.loads(real_batch5.record)["response"]
    prec_dict = json.loads(real_batch5.record)["output_precision"]
    forged_record5 = m.freeze(dict(schema="tick_batch_v1", packet_id=s5.packet.packet_id,
                                 source_sha=s5.packet.source_sha, image_id=s5.packet.image_id,
                                 generation=0, response=resp_dict, output_precision=prec_dict,
                                 rows=forged_rows))
    forged_id5 = m.digest(forged_record5)
    s5._current = m.TickBatch(forged_id5, forged_record5)
    try:
        facts5 = {f.edge_id: f.value_u for f in s5.consume(forged_id5)}
        x0v, x1v = facts5["O02:x0"], facts5["O02:x1"]
        print(f"FORGED consume() result: x0={x0v} x1={x1v}  inverted={x0v >= x1v}")
        if x0v >= x1v:
            print("CONFIRMED: consume() accepts an interval-INVERTED chain-backed batch.")
        return "ACCEPTED", None
    except m.TickClaimError as exc:
        print(f"consume() REJECTED forged batch: {exc.code}")
        return "REJECTED", exc.code


if __name__ == "__main__":
    old = load_module_from_commit("94e899e5", "src/agent/correction/tick_claim.py", "tick_claim_old")
    outcome_old, code_old = run_attack(old, "BEFORE (94e899e5)")
    print()
    sys.path.insert(0, REPO)
    import src.agent.correction.tick_claim as new  # noqa: E402
    print(f"current tree module: {new.__file__}")
    outcome_new, code_new = run_attack(new, "AFTER (current tree)")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"before: {outcome_old} {code_old}")
    print(f"after:  {outcome_new} {code_new}")
    assert outcome_old == "ACCEPTED", "expected pre-fix attack to succeed"
    assert outcome_new == "REJECTED" and code_new == "TICK_INTERVAL_NOT_ORDERED", \
        f"expected post-fix rejection by name, got {outcome_new} {code_new}"
    print("PASS: before accepted the inverted interval, after rejects it by name.")
