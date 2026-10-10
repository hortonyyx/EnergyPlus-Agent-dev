# Same-run recovery blocker: missing CNY usage

The first dispatch has stopped and this run cannot legally dispatch another
reader model call. The blocker is the shared root budget ledger, not a lack of
prepared recovery material.

## Current-run evidence

The durable root event journal contains one settlement whose configured CNY
reservation cannot be priced:

- sequence 1261: reserve `plan_f1:request-21`;
- sequence 1263: model-request failure, reason `timeout`;
- sequence 1264: settle `plan_f1:request-21` with
  `estimated_cost_cny = null`;
- sequence 1265: stop `plan_f1` with
  `money_cny_usage_unavailable`.

The final `plan_f1` reader record is failed with the same reason. The settlement
remains in `events.jsonl`, so every reconstruction of the root ledger sees it.

Two contemplated manual recovery layers were not dispatched:

- `tasks_f2_assisted_recovery.json` is `prepared_not_dispatched`. Its six
  dimension-chain transcriptions were checked against this run's original
  `2f_view.png`, but no recovery task or model request was created.
- For F1, the team only reviewed a possible transfer of the byte-identical,
  unverified `trial_005_plan.json` failed declaration. No recovery task was
  created and no model call was made. It was never promoted to an accepted or
  native inherited reference.

## Why the stop persists

`RuntimeBudget.settle` records the settlement and then sets
`money_cny_usage_unavailable` when a reservation contains CNY but no CNY cost
can be calculated (`src/agent_runtime/budget.py:371-376`). On restart,
`RuntimeBudget.from_events` sets the same fatal reason if any reconstructed CNY
settlement lacks `estimated_cost_cny` (`src/agent_runtime/budget.py:439-443`).

All reader runtimes rebuild their root budget from `store.all_events`
(`src/agent_runtime/loop.py:310-321`). `RuntimeBudget.reserve` refuses a new
reservation whenever a fatal reason exists (`src/agent_runtime/budget.py:214-218`),
and the runtime's pre-request budget check stops on either root or task fatal
(`src/agent_runtime/loop.py:1351-1356`). A local delegate operation could create
a task record, but its child cannot emit an adapter request.

The missing amount is already handled conservatively for accounting: effective
charge retains the reservation's full CNY upper bound when the settlement has
no estimated CNY cost (`src/harness_contracts/budget.py:316-343`). That hold
does not clear the fatal flag.

There is no current usage-reconciliation API, CLI, or append-only adjustment
event. `settle` can clear only `unsettled_reported_usage` during the first valid
settlement; it does not clear `money_cny_usage_unavailable`. Attempting another
settlement for the same reservation is itself fatal as
`reservation_settled_twice` (`src/agent_runtime/budget.py:295-298`). The restart
contract is locked by
`tests/test_runtime_a4r_money.py::test_missing_or_unpriceable_usage_stops_and_holds_money_after_restart`:
the resumed runtime returns `money_cny_usage_unavailable`, sends zero adapter
requests, and retains the full charge.

Under the current constraints—do not edit the ledger, invent usage or cost,
alter the frozen runtime, or start a new cold run—the only valid outcome is a
failed closeout. Local finalization and archiving may proceed without a model
request.

## Small future design candidates (not implemented)

Keep the current fail-closed path as the default until one of these explicit,
audited policies exists:

1. **Late evidence reconciliation.** Add a typed append-only reconciliation
   event that references the request, reservation, original settlement, and a
   hash-verified provider usage/billing receipt. Ledger reconstruction consumes
   the original settlement plus this event as one charge. It may clear the
   fatal state only when the evidence is complete and the remaining cap still
   admits a new reservation. The original event is never replaced.
2. **Irrevocable upper-bound settlement.** Define a configured policy under
   which missing usage permanently charges the full reserved CNY upper bound,
   retains `usage_complete=false`, emits a distinct audit decision, and allows
   later requests only from the remaining budget. This treats the hold as a
   conservative charge, not as reported provider cost. It must be selected and
   recorded before the run; it cannot be retrofitted manually into this run.

Both designs need tests for restart, concurrent child reservations, duplicate
or conflicting late receipts, cap exhaustion, and immutable audit linkage.
Until then, fail-closed is the only supported behavior.
