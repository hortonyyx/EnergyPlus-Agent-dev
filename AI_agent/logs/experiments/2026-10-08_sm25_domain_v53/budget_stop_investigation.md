# `event-001300` root time budget investigation

## Conclusion

`plan_f1b` was **not** assigned a 45-minute task budget. Its durable
`reader_timing.json` assigns 3,600 seconds. It stopped after about 45.88 minutes
because the shared root ledger had no *uncommitted* seconds at that instant.

The root limit of 10,800 seconds is a shared ledger of model-request durations,
not a 180-minute wall-clock deadline alone. Durations from concurrent roles are
therefore accumulated separately. The ledger also conservatively counts the
full seconds reserved for every request still in flight. Immediately before the
stop, settled request durations across all roles totalled
`10250.12799999999708456` seconds and the in-flight
`plan_f2b:request-23` held the remaining `549.87200000000291544` seconds.
Their sum was exactly `10800.00000000000000000`, leaving `0E-17` available.

The scope label is correct: this was a root-ledger stop, while the child task
still had both local wall-clock time and task-ledger seconds available. The
word `exhausted` should be read as **no root admission capacity after outstanding
holds**, not as proof that 10,800 seconds of settled service or 180 minutes of
wall time had elapsed. The durable behavior exposes a scheduling/fairness edge:
one sibling can stop permanently while another sibling temporarily holds the
last root capacity and later releases most of it.

No work-model call was made for this investigation. The active output and
frozen source tree were read only.

## Bound event and artifacts

- Run: `sm25_role_v53`
- Frozen commit: `b55d47e7c82bb306c7ea838f00985648eef94304`
- Event: `event-001300`, sequence 1300, task `plan_f1b`, parent `coordinator`
- Event time: `2026-10-08T17:11:33.445043Z`
- Event payload: `run_lifecycle / stop / root_time_budget_exhausted`
- Event receipt blob:
  `blobs/35d930b6d2a17e3d4fb24cc52e1d43c4ad6c764009a401683d3f76074985d2c1`
  (SHA-256 equals the filename)
- Reader record blob:
  `blobs/c9eb3765c83d206e9e1b9a4475f217e8f027273f59392fd1ff11222f52359f77`
- Root budget declaration: `journal.json` records `seconds: "10800.0"`; the
  experiment configuration records `maximum_seconds_per_case: 10800` and the
  case limit records `seconds: 10800`.
- Reader timing artifact:
  `tasks/97f2c471dfd10e769ca8e2baed161258dace8e21a450ccdc0f19143fb238194b/reader_timing.json`
  records `started_epoch: 1791476740.510624`,
  `deadline_epoch: 1791480340.510624`, and
  `time_budget_seconds: 3600`.

All run-relative paths in this note are under:

`D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008\AI_agent\archive\local_backup\sm25_v53\sm25_role_v53`

## Ledger reconstruction at the stop

The table below was reconstructed from budget reserve/settle events through
`event-001300`, inclusive. A settled request contributes its actual request
duration. An unsettled request contributes its full reservation.

| Task | Settled request seconds | Outstanding hold | Settled requests | Outstanding requests |
|---|---:|---:|---:|---:|
| coordinator | 50.4680000000 | 0 | 4 | 0 |
| elev_east | 304.8740000000 | 0 | 10 | 0 |
| elev_north | 232.2200000000 | 0 | 8 | 0 |
| elev_south | 153.5180000000 | 0 | 7 | 0 |
| elev_west | 264.4380000000 | 0 | 7 | 0 |
| plan_f1 | 1477.4080000000 | 0 | 12 | 0 |
| plan_f2 | 2764.7190000000 | 0 | 10 | 0 |
| plan_f1b | 2488.5630000000 | 0 | 18 | 0 |
| plan_f2b | 2513.9200000000 | 549.8720000000 | 22 | 1 |
| **Total** | **10250.1280000000** | **549.8720000000** | **98** | **1** |
| **Committed** |  | **10800.0000000000** |  |  |

The decisive in-flight hold is durable `event-001295`:

- reservation: `plan_f2b:request-23`
- reservation seconds: `549.87200000000291544`
- decision evidence blob:
  `blobs/8ec9dc7bc944eb3ff26cba55ad475472668a24b5bb990c2da81a29841080eb58`
- the decision blob itself records root `available.seconds: "0E-17"`
- `event-001296` dispatched that reserved request before F1b stopped

The receipt bound to `event-001300` independently records:

- root `available.seconds: "0E-17"`
- F1b task `available.seconds: "1111.437000000003537"`
- F1b limit `seconds: 3600.0`
- F1b elapsed wall time `2752.467814683914` seconds
- F1b model time `2488.5629999999965` seconds

Using the event timestamp and the reader start, F1b had run about
`2752.934419155121` wall seconds (45.882 minutes) and still had about
`847.065580844879` local wall seconds. The small difference from the receipt's
elapsed value is the time between receipt construction and durable event time.

## Why F2b continued

F2b had already acquired and dispatched request 23 before the F1b check. The
runtime does not cancel an admitted in-flight sibling when another task sees a
zero shared balance. After `event-001300`:

- `event-001302` captured the F2b response.
- `event-001303` settled request 23 at only `33.15600000000086` actual seconds.
- Settlement therefore released exactly
  `549.87200000000291544 - 33.15600000000086 = 516.71600000000205544`
  seconds.
- `event-001311` then reserved those `516.71600000000205544` seconds for
  `plan_f2b:request-24`, again recording root available seconds as zero.

Thus F2b continuing is direct evidence of a transient reservation hold. It does
not imply that F2b had a separate root budget or that F1b reached its own
deadline.

## Runtime semantics checked in frozen source

The frozen source implements the observed behavior as follows:

1. `src/agent/runtime_roles/session.py:75-78` fixes every plan-reader task at
   3,600 seconds. Lines 655-671 cap that allowance only by the root wall-clock
   deadline. The coordinator-facing task schema excludes `budget`, so this was
   not a coordinator-selected 45-minute allowance.
2. `src/agent/runtime_roles/session.py:752` caps each reader request timeout at
   root seconds divided by `max_concurrent_readers + 1`. This run records eight
   concurrent-reader slots, making the usual cap 1,200 seconds; near the end,
   the smaller remaining root-ledger balance controls instead.
3. `src/agent_runtime/loop.py:252-255` rebuilds the root budget from all root and
   child events, while the child budget uses only its task events.
4. `src/agent_runtime/loop.py:348-382` chooses request seconds as the minimum of
   local wall time, root-ledger availability, child-ledger availability and the
   per-request cap, then reserves that amount in the shared root ledger before
   dispatch.
5. `src/harness_contracts/budget.py:276-311` defines committed use as settled
   effective charges plus full outstanding reservations; available budget is
   the configured total minus committed use.
6. `src/agent_runtime/loop.py:586-612` settles seconds using the observed adapter
   request duration. Unused reserved seconds become available again.
7. `src/agent_runtime/loop.py:1251-1297` checks local wall time and child limits
   before the root ledger. For a non-root task, a root-ledger time stop is named
   `root_time_budget_exhausted`; this is why the scope in `event-001300` is
   correct.

This means the 10,800-second setting serves two independent controls: the root
runtime still has a wall-clock deadline, and the shared ledger also limits the
sum of model-request seconds/holds. Under concurrency, the second can reach
zero well before 180 wall minutes.

## `preserve_run.py` end gate

The existing preservation gate is suitable for this run and must remain keyed
to the whole process and coordinator, not to this child stop:

- At investigation time `launch_receipt.json` still says `status: "running"`,
  `input_manifest_after.json` is absent, and the root `receipt.json` is absent.
  `preserve_run.py` therefore refuses to run now.
- On a normal launcher return it requires `process_exited`, an integer exit
  code, start/end times, unchanged before/after/current inputs, a frozen detached
  commit and matching saved code manifest.
- It also requires mutually consistent root `receipt.json`, `bim/summary.json`,
  behavior evidence, launcher exit code, and a terminal **coordinator** stop
  event. A child stop such as `event-001300` neither admits preservation early
  nor improperly blocks preservation after the root run has a coherent terminal
  result.
- The gate accepts a coherently recorded non-`completed` root result only with a
  nonzero launcher exit and `agent_response_completed: false`. That is
  appropriate for evidence preservation; preservation is not a claim that the
  BIM task succeeded.

No change to `preserve_run.py` is indicated by this event.
