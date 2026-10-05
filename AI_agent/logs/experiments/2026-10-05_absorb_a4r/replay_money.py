"""Exercise the new CNY ledger over fixed historical Qwen requests and receipts."""

from decimal import Decimal
import json
from pathlib import Path

from replay_compaction import MemoryStore
from src.agent_runtime.accounting import request_accounting_from_store, require_cny_price_schedule
from src.agent_runtime.budget import RequestEstimate, RuntimeBudget
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts

HERE = Path(__file__).resolve().parent


def replay(name):
    store = MemoryStore(HERE / ".tmp/history" / name)
    store._all_events = EventStore.read_events(store.directory / "events.jsonl")
    requests = [e for e in store.all_events if e.payload.event_type == "adapter_request"]
    reservations = {e.payload.reservation.reservation_id: e for e in store.all_events
                    if e.payload.event_type == "budget" and e.payload.action == "reserve"}
    settlements = {e.payload.settlement.reservation_id: e.payload.settlement for e in store.all_events
                   if e.payload.event_type == "budget" and e.payload.action == "settle"}
    pricing = require_cny_price_schedule("Qwen3.8-27B", route_id="paratera")
    records = []
    for request in requests:
        key = request.payload.reservation_id
        reservation = reservations[key]
        evidence = json.loads(store.get_bytes(reservation.source_refs[0].blob))
        estimate = RequestEstimate.model_validate_json(json.dumps(evidence["effective_estimate"]))
        estimate = estimate.model_copy(update={
            "additional_image_tokens_estimate": estimate.image_input_tokens_estimate,
            "money_cny_upper_bound": pricing.upper_bound(
                input_tokens=estimate.input_token_upper_bound,
                output_tokens=estimate.output_token_limit + estimate.reasoning_token_allowance,
                image_tokens=estimate.image_input_tokens_estimate)})
        accounting = request_accounting_from_store(store, request.event_id).accounting
        assert accounting.estimated_cost_cny is not None
        records.append((key, estimate, settlements[key], accounting))
    outcomes = []
    for money in ("8", "10", "12", "15"):
        budget = RuntimeBudget(BudgetAmounts(money_cny=Decimal(money)))
        steps = []
        for key, estimate, old, accounting in records:
            decision = budget.reserve(key, estimate)
            row = {"request": len(steps) + 1, "conservative_hold_cny": str(estimate.money_cny_upper_bound),
                "sent": decision.action != "stop"}
            if decision.action == "stop":
                row.update(reason=decision.reason, available_cny=str(budget.available.money_cny))
                steps.append(row)
                break
            settled = budget.settle(key, actual=old.actual, usage=old.usage,
                estimated_cost_cny=accounting.estimated_cost_cny,
                image_tokens_estimate=accounting.image_tokens_estimate,
                reported_usage_includes_image_tokens=accounting.reported_usage_includes_image_tokens,
                additional_image_tokens=accounting.additional_image_tokens)
            assert settled.settlement is not None
            row.update(charge_cny=str(accounting.estimated_cost_cny),
                committed_cny=str(budget.ledger.committed.money_cny), action=settled.action)
            steps.append(row)
            if settled.action == "stop":
                break
        sent = sum(step["sent"] for step in steps)
        outcomes.append({"ceiling_cny": money, "token_ceiling": None, "admitted_requests": sent,
            "reached_recorded_end": sent == len(records),
            "committed_estimate_cny": str(budget.ledger.committed.money_cny), "steps": steps})
    return {"run": name, "recorded_requests": len(records),
        "recorded_charge_cny": str(sum((a.estimated_cost_cny for _, _, _, a in records), Decimal(0))),
        "recorded_budget_tokens": sum(a.budget_charge_tokens for _, _, _, a in records),
        "outcomes": outcomes}


def main():
    result = {"model_requests": 0,
        "method": "Fixed historical requests and raw receipts; new CNY reservations assume zero cache. Monetary admission is evaluated with no total token ceiling; token totals are reported separately. Elapsed time and future model behavior are not evaluated. Reaching the recorded end is not building completion or evidence of what another request would produce.",
        "runs": [replay(name) for name in ("sm24_qwen27b_paratera", "sm24_qwen27b_after_a2")]}
    (HERE / "money_replay.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps([{k: r[k] for k in ("run", "recorded_requests", "recorded_charge_cny", "recorded_budget_tokens")}
                      for r in result["runs"]]))


if __name__ == "__main__":
    main()
