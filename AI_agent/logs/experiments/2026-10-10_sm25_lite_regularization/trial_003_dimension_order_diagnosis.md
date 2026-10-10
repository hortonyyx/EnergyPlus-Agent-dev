# F1 trial_003 dimension/Q1 order diagnosis

Scope: current run `plan_f1` trial_003 only. This review used its immutable
plan and receipt plus the frozen implementation. It did not read ground truth,
an older BIM, or model output outside this trial. All replays were offline and
wrote nothing into the active run or frozen tree.

## Evidence

- `trial_003_plan.json` declares `wall-col-left` as `[791,310] -> [785,960]`
  and `wall-col-bottom` as `[785,960] -> [972,960]`. The former is only 6 px
  off vertical over 650 px, but it is still non-orthogonal under the exact
  plan contract.
- YL2 accepts its dimension chain and proposes moving the horizontal bottom
  from y=960 to y=962.125. At the active y scale this is 0.045946 m.
- The first rejection is therefore:
  `would detach partition wall-col-left from partition:wall-col-bottom`.
  The receipt contains three total dimension rejections; the later two involve
  YR1 and are not the cause of this first failure.
- Main and frozen copies of `trial.py`, `plan_dimension_alignment.py`,
  `plan_ink_alignment.py`, `plan_regularization.py`, and
  `lite_bim_regularization.py` had identical SHA256 values during the replay.

## Exact cause

The pipeline preflights `prepare_plan_junctions` on a copy, without applying
its changes to the returned plan. It then runs dimension alignment and only
after that runs the Lite Q1 regularizer. Dimension alignment's segment reader
recognizes exact horizontal or vertical segments only. Consequently the
slightly leaning `wall-col-left` is absent from the movable straight-wall set.

When YL2 moves `wall-col-bottom`, `move_straight_wall` carries a connected
partition endpoint only when that partition is already exactly perpendicular.
For this endpoint the x difference to its neighbour is 6 px, so the carry rule
does not fire. The post-move topology comparison correctly observes that the
previous exact junction `[785,960]` was lost and rolls back the move.

This is a missing bounded near-axis normalization/atomic-junction step. It is
not evidence that a 0.045946 m YL2 move must break the topology. The topology
guard is doing the right thing with the geometry it receives.

Merely moving today's Q1 call before dimension alignment is insufficient. An
offline replay of `prepare_plan_junctions` on the dimension-free baseline
returned `status=unchanged`, kept both wall coordinates unchanged, and retained
the compiler error:

```text
partition wall-col-left segment 0 is not orthogonal:
[791.0, 310.0] -> [785.0, 960.0]
```

There is also a separate annotation interaction: YL2 targets y=962.125 while
YR1 later targets y=957.5, exactly 0.1 m apart under the adopted y calibration.
Both chains pass their own closure/scale checks. The current loop applies them
sequentially to nearby geometry. That later precedence deserves explicit audit,
but it does not make the first YL2 junction rejection valid or unavoidable.

## Smallest safe candidate change

Add one bounded pre-dimension normalization for two-point, almost-axis-aligned
partitions, then keep the existing topology guard:

1. Admit a candidate only when its minor-axis deviation is within the existing
   dimension move bound, its dominant direction is unambiguous, and exactly one
   orthogonal candidate preserves the declared footprint, junction, opening,
   and room relationships.
2. Choose among observed endpoint/host/opening coordinates; do not average a
   new unsupported line. For this trial, x=791 is corroborated by the upper
   endpoint, all seven D8-D14 opening lines, and the six horizontal room-wall
   ends, while x=785 supplies the bottom corner. This evidence makes the
   intended vertical carrier unambiguous without asking the reader to tune a
   few pixels.
3. When a subsequent dimension tick moves that carrier just beyond a connected
   perpendicular host endpoint, include the nearby host endpoint in the same
   candidate transaction. Validate the complete transaction with the current
   attachment/opening/topology checks; reject it if any relation changes.
4. Preserve an audit row for the original endpoints, adopted axis coordinate,
   movement, corroborating objects, and tolerance. Genuine diagonals or
   ambiguous candidates remain hard failures.

A narrower change that only relaxes the detach check is unsafe: the diagonal
would survive into Lite Q1 and the compiler would still reject it. Likewise,
blindly moving the endpoint without checking openings and perpendicular walls
can turn a real diagonal into an invented wall. The bounded normalization plus
atomic endpoint move removes this mechanical reader correction while retaining
the topology guard.

## Offline replay observations

- Original input: dimension report reproduced all 3 receipt rejections.
- Q1 preparation before dimensions: unchanged; same non-orthogonal compiler
  error.
- Hand-straightening only the upper endpoint to x=785 removed dimension
  rejections but later left all six room dividers dangling, showing why a
  single-coordinate shortcut is not sufficient.
- Hand-straightening the lower endpoint to x=791 allowed the first YL2 move,
  but a later x-chain exposed a 0.452 px bottom-end gap before Lite compilation.
  This is the evidence for the atomic nearby-host endpoint part of the proposed
  fix rather than a reason to ask the reader for another pixel edit.
