"""Replay T1 sm25 evidence against original candidates; no model or image inference."""
from collections import Counter
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil

from scripts.tool_scripts.run_bim_agent import Toolkit, dump
from src.agent.execution.bim_claims import ClaimStore
from src.agent.execution.bim_claims import geometry_state
from src.agent.runtime_behaviour import tool_result_data

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / ".tmp_a2t"
HISTORY = WORK / "history" / "2026-10-03_sm25_glm_tools_t1"
RECORD = HERE.parent / "2026-10-01_behaviour_records/records/2026-10-03_sm25_glm_tools_t1/record.json.gz"


def fixture(name, *, before_step):
    target = WORK / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(HISTORY, target)
    # Preserve only evidence already recorded at that actual point in time.
    shutil.rmtree(target / "claims")
    (target / "claims").mkdir()
    record = json.loads(gzip.decompress(RECORD.read_bytes()))
    steps = record["invocations"][0]["steps"]
    for step in steps:
        if step["index"] >= before_step or step["is_error"]:
            continue
        data = tool_result_data(step["result_text"])
        if step["tool"] in {"record_claim", "decide_claim"}:
            identity = data.get("id")
            source = HISTORY / "claims" / (str(identity) + ".json")
            if source.is_file():
                shutil.copy2(source, target / "claims" / source.name)
    manifest = json.loads((target / "inputs.json").read_text())
    manifest.pop("deadline_epoch", None)
    manifest["max_candidates"] = 24
    dump(target / "inputs.json", manifest)
    return Toolkit(target), steps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    toolkit, steps = fixture("step115", before_step=115)
    step = next(s for s in steps if s["index"] == 115)
    candidate = step["arguments"]["candidate"]
    operations = json.loads(step["arguments"]["operations_json"])
    try:
        ClaimStore(toolkit).resolve_operations(candidate, operations)
    except ValueError as error:
        legacy_error = str(error)
    else:
        raise AssertionError("legacy step115 must fail")
    # The compatibility path uses the same new checked resolver as transactions.
    result = toolkit.confirm_claims(candidate, json.dumps(operations))
    assert result["status"] == "confirmed_unchanged"
    assert len(result["evidence"]["bindings"]) == 32
    grouped = {}
    for op in operations:
        identity = op["changes"]["z"]["claim"]
        grouped.setdefault(identity, []).append(op)
    toolkit, _ = fixture("transaction115", before_step=115)
    transaction = toolkit.claim_transaction(candidate, json.dumps([
        dict(claim_id=identity, action="confirm", reason="Replay the original adopted height decision",
             operations=ops) for identity, ops in grouped.items()]))
    assert transaction["status"] == "completed"
    # Execute the counted replacement, including the unchanged semantic edits.
    bundled, _ = fixture("bundled_sequence", before_step=92)
    for path in list(bundled.run.glob("candidate_*")):
        if int(path.name.split("_")[1]) >= 4:
            shutil.rmtree(path)
    decisions = {s["arguments"]["claim_id"]: s["arguments"] for s in steps
                 if 103 <= s["index"] <= 113}
    entries = []
    for s in steps:
        if not 92 <= s["index"] <= 102:
            continue
        row = tool_result_data(s["result_text"])
        decision = decisions[row["id"]]
        entries.append(dict(claim=json.loads(s["arguments"]["claim_json"]), action="record",
                            disposition=decision["disposition"], reason=decision["reason"]))
    record_batch = bundled.claim_transaction("candidate_03", json.dumps(entries))
    assert record_batch["status"] == "completed"
    original_ops = json.loads(next(s for s in steps if s["index"] == 114)["arguments"]["operations_json"])
    height_ops = [op for op in original_ops if op["op"] == "update_window"]
    other_ops = [op for op in original_ops if op not in height_ops]
    applied_batch = bundled.claim_transaction("candidate_03", json.dumps([
        dict(claim_id="claim_0011", action="apply", operations=height_ops,
             reason=decisions["claim_0011"]["reason"])]))
    assert applied_batch["status"] == "completed"
    changed = bundled.revise(applied_batch["result_candidate"], json.dumps(other_ops))
    final = bundled.claim_transaction(changed["candidate"], json.dumps([
        dict(claim_id=identity, action="confirm", operations=ops,
             reason=decisions[identity]["reason"]) for identity, ops in grouped.items()]))
    assert final["status"] == "completed"
    original = json.loads((HISTORY / "candidate_04/proposal.json").read_text())
    actual = json.loads((bundled.run / final["result_candidate"] / "proposal.json").read_text())
    assert geometry_state(original) == geometry_state(actual)
    # Conservative accounting: retain the eight useful facade-count calls and
    # both queries. Replace 11 geometric records and 11 decisions (including one
    # retraction) with one transaction; group the confirmation into another.
    # Height application adds a third transaction, while the mixed semantic/notes
    # portion of step114 still needs its original ordinary revise_bim call.
    claim_calls = Counter(s["tool"] for s in steps if s["tool"] in {
        "record_claim", "decide_claim", "confirm_claims", "claim_status"})
    from src.agent_runtime.agent_registry import agent_version_record
    output = dict(model_requests=0, agent_version=agent_version_record(ROOT)["version_id"],
        source_record=str(RECORD.relative_to(ROOT)),
        source_record_sha256=hashlib.sha256(RECORD.read_bytes()).hexdigest(),
        original_total_calls=len(steps), original_evidence_calls=dict(claim_calls),
        step115=dict(old_error=legacy_error, new_status=result["status"],
            bound_openings=len(result["evidence"]["bindings"]),
            claims=len(grouped), inheritance=result["evidence"]["inheritance"],
            transaction_status=transaction["status"], transaction_entries=len(transaction["entries"])),
        avoided_reregistration=dict(record_steps=list(range(116,125)), decision_steps=list(range(125,134)),
            confirmation_steps=[134], retraction_steps=list(range(136,145)), calls=28),
        executed_bundled_sequence=dict(transaction_count=3,
            entry_counts=[len(r["entries"]) for r in (record_batch, applied_batch, final)],
            statuses=[r["status"] for r in (record_batch, applied_batch, final)],
            ordinary_semantic_revision_count=1, final_candidate=final["result_candidate"],
            final_geometry_and_roles_equal_original=True),
        accounting=dict(method="No geometry or observation decisions invented; queries and facade-count calls retained. Group compatible entries without crossing an observation dependency.",
            historical_evidence_calls=sum(claim_calls.values()),
            after_inheritance_only=sum(claim_calls.values())-28,
            after_transactions=8+2+3,
            ordinary_revision_extra=1,  # Beyond the transactions, retained from historical step114.
            total_calls_before=len(steps), total_calls_after=len(steps)-(61-13),
            calls_saved=48,
            caveat="Counterfactual orchestration count, not observed model behavior or a wall-clock speed claim. Mixed step114 still needs one ordinary revise_bim for non-height edits."))
    dump(args.output / "claim_replay.json", output)
    dump(args.output / "step115_transaction.json", transaction)
    print(json.dumps({"step115": output["step115"]["new_status"], "bindings":32,
                      "claims":len(grouped), "accounting":output["accounting"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
