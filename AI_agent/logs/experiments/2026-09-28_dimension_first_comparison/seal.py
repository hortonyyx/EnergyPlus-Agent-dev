"""Verify the single reference difference and freeze the reviewable pilot."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
arms = {name: json.loads((HERE / f"preflight_{name}.json").read_text()) for name in ("A", "B")}
a, b = [arms[name]["conditions"] for name in ("A", "B")]
assert arms["A"]["tool_names"] == arms["B"]["tool_names"]
file_changes = [name for name in a["implementation_sha256"]
                if a["implementation_sha256"][name] != b["implementation_sha256"][name]]
reference_changes = [name for name in a["references_sha256"]
                     if a["references_sha256"][name] != b["references_sha256"][name]]
assert file_changes == ["scripts/tool_scripts/bim_agent_guidance.py"]
assert reference_changes == ["reconstruction"]
assert {k:v for k,v in a.items() if k not in {"implementation_sha256", "references_sha256"}} == {
    k:v for k,v in b.items() if k not in {"implementation_sha256", "references_sha256"}}
proposal = dict(status="prepared_pending_user_decision", base_commit="c07967d0",
    total_primary_invocations=2, execution_order=["B", "A"], sequential=True, arms=arms,
    verified_only_differences=dict(files=file_changes, references=reference_changes),
    withheld=["old plans/BIM", "GT/evaluation", "developer-selected crops/measurements",
              "correct coordinates/counts/heights", "live developer corrections"],
    behavior_evaluation=[
        "Record actual reference exposure; an unread reference is not evidence that its method failed.",
        "Trace physical divider acceptance/rejection, crop-to-original coordinates and dimensional reference planes into saved declarations.",
        "Trace distinct opening identities and height families into actual saved values, including local repairs and preservation.",
        "Report genuine split/merge/omission, hosts/connections and units separately from continuous geometric offsets.",
        "Keep original strict scores, drawing comparisons, elapsed time and tokens; tool counts and speed are descriptive, not quality gates."],
    stop_rules=["Inspect the real B receipt before starting A in a separate command.",
                "On quota/interruption/error stop; no continuation, automatic retry, API fallback or extra case.",
                "No local model delegation by the unchanged experiment scope."],
    limits="One run per arm is an adoption/behavior pilot, not a causal test with statistical power or proof of stability. Both arms contain the same unvalidated optional measurement-binding feature. No working-model call has been made. Additional repetitions/cases need a new concrete user decision.")
with (HERE / "proposed_batch.json").open("x") as output:
    output.write(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(dict(model_calls=0, total_proposed_calls=2, only_reference_changed=reference_changes)))
