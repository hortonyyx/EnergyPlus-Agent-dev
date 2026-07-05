# Cross-floor wall alignment plan review

## Verdict: REWORK

The diagnosed local root cause is real and the referenced `deterministic.py` lines are mostly accurate: `apply_deterministic_core` builds one global axis pool from the footprint plus every floor cell at `src/agent/correction/deterministic.py:121-129`; `_build_axis_map` is coordinate-only at `src/agent/correction/deterministic.py:44-87`; the identity split at 0.10 m follows from the `axis_jitter_tol_m` comparison at `src/agent/correction/deterministic.py:61`; and the exact-0.10 non-merge follows from the strict sliver guard at `src/agent/correction/deterministic.py:73`. The docstring claim about byte-identical cross-floor walls is also present at `src/agent/correction/deterministic.py:7-8`.

The proposed two-tier idea is directionally useful, but the specific greedy same-floor-exclusion design is not safe enough to approve. It can still silently pick the wrong cross-floor partner, fail to merge the intended partner, and re-collapse same-floor axes during the final provenance-blind sliver pass. The `0.20 m` default is also too broad for a coordinate-only deterministic pass.

## §7.1 Same-floor exclusion + greedy grouping

DISAGREE.

Same-floor exclusion prevents a narrow class of direct same-group merges, but it does not make the algorithm safe.

Counterexample: greedy consumes the wrong floor candidate. Let F1 have wall A at `3.10`. Let F2 have an unrelated true wall at `3.17` and the intended continuation of A at `3.29`. Both F2 candidates are within `cross_floor_align_tol_m=0.20` of F1's `3.10`, and the two F2 axes are `0.12 m` apart, so they are not an invalid sub-`min_edge_length_m` pair. Sorted greedy grouping sees `3.17@F2` first, admits it into the group anchored at `3.10@F1`, then rejects `3.29@F2` because F2 is already present. Result: a real unrelated F2 wall is merged, and the true cross-floor wall is missed. The schema only provides rectangular cell coordinates (`src/agent/correction/schema.py:30-37`, `src/agent/correction/schema.py:59-64`), and the current core only pools coordinates (`src/agent/correction/deterministic.py:121-129`), so this design has no topology/wall identity evidence to break that tie.

Counterexample: Phase C can still merge same-floor true axes. Let F1 have two valid axes at `3.10` and `3.21` (`0.11 m`, greater than both `axis_jitter_tol_m` and `min_edge_length_m`). Let F2 have the intended continuation of the first wall at `3.19`. Phase B without a footprint anchor can produce a mean for `{3.10@F1, 3.19@F2}` of `3.145`, snapped to `3.15`, while `{3.21@F1}` snaps to `3.20`. The proposed Phase C then reuses the existing provenance-blind sliver merge (`src/agent/correction/deterministic.py:69-86`), sees `0.05 < min_edge_length_m`, and collapses the two F1 axes into one. That violates the plan's own invariant that same-floor axes above jitter are not merged (`AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:22`).

The classic sorted-window chain defect is only partly avoided by anchoring each group to its first value. It avoids unbounded single-link drift, but it does not solve one-to-many assignment or ordering bias inside the tolerance window.

## §7.2 Envelope-first representative

AGREE with hard footprint anchors, DISAGREE with high-weight footprint averaging.

The footprint should be a hard canonical axis, not a high-weight participant in a mean. `CorrectedGeometry` has one global rectangular footprint (`src/agent/correction/schema.py:71-72`), and the deterministic core later uses the snapped footprint as the actual boundary for every cell (`src/agent/correction/deterministic.py:149-151`). Averaging it, even with a high weight, can move the envelope and then changes the boundary used by `gap_close`.

However, footprint coordinates should not be normal cross-floor cluster members with a broad `0.20 m` catchment. If a footprint axis is near two adjacent internal axes, the stable behavior is:

1. keep the footprint axis fixed;
2. allow at most one nearest candidate per floor to attach to it, only if that attachment will not collapse a valid cell;
3. if two plausible candidates compete, leave them separate or flag ambiguity instead of choosing by sorted order;
4. rely on the existing directional boundary reach operation for exterior sealing (`src/agent/correction/deterministic.py:98-106`, `src/agent/correction/deterministic.py:183-189`).

Otherwise the footprint becomes a `0.20 m` identity magnet and can erase a real perimeter strip before the later collapsed-cell unsupported check at `src/agent/correction/deterministic.py:197-204`.

## §7.3 Safety of `cross_floor_align_tol_m=0.20`

DISAGREE.

`0.20 m` is too aggressive as a blanket coordinate-only identity tolerance. Real buildings can have intentional internal wall offsets around `0.15 m`: shaft/core thickening, stair or service wall offsets, centerline-vs-face extraction differences, local corridor jogs, partial floor layout changes, and setback/transfer conditions. EnergyPlus can model those offsets; silently flattening them is a semantic geometry error, not merely a robustness cleanup.

The existing config policy explicitly frames values above `axis_jitter_tol_m` as ambiguity when topology evidence says the axes differ: `src/configs/correction.yaml:32-33`. The current validation chain only says identity is finer than connectivity and connectivity is below arbitration (`src/agent/correction/config.py:66-73`). Inserting `cross_floor_align_tol_m` between `axis_jitter_tol_m` and `gap_close_threshold_m` is mechanically plausible, but it does not make `0.20 m` safe.

I would not approve `min_edge_length_m <= cross_floor_align_tol_m` as a semantic invariant. `min_edge_length_m` is the EP sliver floor (`src/agent/correction/config.py:50`, `src/configs/correction.yaml:53-62`), not proof that any larger cross-floor offset is jitter. If offsets above `axis_jitter_tol_m` are auto-aligned, that should be limited to unambiguous one-to-one matches and strongly audited; competing candidates or plausible floor-plan shifts should go to judge/A3 or unsupported rather than being silently aligned.

## §7.4 New function vs changing `_build_axis_map`

AGREE with adding a new function, with one implementation constraint.

Do not change `_build_axis_map` in place. It has a compact contract (`src/agent/correction/deterministic.py:44-52`) and is indirectly covered through `apply_deterministic_core` tests (`tests/test_deterministic_core.py:55-78`). A new `_reconcile_cross_floor(...)` is cleaner because provenance is a different input model.

But the new function must not only emit per-floor reps. It must retain every raw member coordinate through Phase A and return a raw-coordinate-to-canonical map. `_snap` only looks up the rounded raw value (`src/agent/correction/deterministic.py:90-91`), and the current `_build_axis_map` explicitly maps every original cluster member to the final canonical (`src/agent/correction/deterministic.py:81-86`). Losing raw members would make unsnapped raw values fall through unchanged.

If helper reuse is desired, extract small helpers for identity clustering and snap/sliver handling; keep `_build_axis_map(values, tol)` as the compatibility wrapper.

## §7.5 Simpler alternatives

DISAGREE that a single sorted greedy pass is equally correct.

A simpler-looking coordinate sweep is exactly where the unsafe cases arise. The minimum robust alternative is still two-phase, but Phase B should be constrained matching rather than sorted greedy:

1. build per-floor identity clusters while retaining raw members;
2. create candidate cross-floor edges only between different floors within `cross_floor_align_tol_m`, with footprint edges ordered first but footprint axes fixed;
3. accept merges in deterministic nearest-distance order only if the resulting component has at most one candidate per floor and bounded component diameter;
4. when a rejected edge indicates a competing same-floor candidate within the tolerance window, flag ambiguity or leave both components separate;
5. run any final sliver guard with provenance awareness: never collapse two components that contain distinct same-floor axes at or above `min_edge_length_m`; flag instead.

An even stricter variant is mutual-nearest matching per floor pair, then union only conflict-free matches. That is less aggressive but much safer than sorted greedy and still deterministic/image-blind.

## Additional risks / bugs

- BLOCKER: The proposed final "reuse existing grid snap + sliver guard" is provenance-blind and can undo the same-floor protection. The current sliver guard merges solely by canonical distance at `src/agent/correction/deterministic.py:69-86`; the request explicitly proposes reusing it after cross-floor grouping at `AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:36`. This can collapse same-floor axes after cross-floor averaging shifts one component.

- BLOCKER: Greedy cross-floor grouping is order-dependent in one-to-many windows. The current data model has coordinates but no wall identity or adjacency label (`src/agent/correction/schema.py:30-37`, `src/agent/correction/schema.py:59-64`), so sorted order can select the lower nearby axis rather than the intended wall continuation. The core's existing axis collection is coordinate-only (`src/agent/correction/deterministic.py:121-129`).

- MAJOR: The proposed tolerance ordering adds `cross_floor_align_tol_m` but the existing invariant chain at `src/agent/correction/config.py:66-73` has only `axis_jitter_tol_m < gap_close_threshold_m < gap_arbitration_band_m`. The new field must be inserted deliberately in validation and tests; it is not covered by the current invariant.

- MAJOR: `min_edge_length_m <= cross_floor_align_tol_m` is not a safe invariant. `min_edge_length_m` is documented and validated as a sliver/degeneracy floor (`src/agent/correction/config.py:50`, `src/configs/correction.yaml:53-62`), while identity clustering is documented separately as a jitter concept (`src/configs/correction.yaml:26-35`). Tying the cross-floor identity tolerance to be at least the sliver floor encourages erasing valid offsets just because they are modelable without EP slivers.

- MAJOR: The plan conflicts with the current config commentary that offsets above identity tolerance and topology-distinct cases should escalate to A3 rather than silently merge (`src/configs/correction.yaml:32-33`). If the new philosophy is "deterministic robustness may erase up to 0.20 m", that policy needs to be explicitly changed and audited.

- MAJOR: The plan's "product remains `{raw_value: canonical}`" is correct, but Phase A as described only talks about reps. The implementation must carry raw cluster members; otherwise `_snap` will miss values that are not exactly equal to a rep (`src/agent/correction/deterministic.py:90-91`). The current implementation avoids that by mapping every original cluster value at `src/agent/correction/deterministic.py:81-86`.

- MAJOR: Treating footprint coordinates as ordinary cross-floor grouping candidates can silently move or collapse perimeter-adjacent geometry. The snapped footprint becomes the actual boundary (`src/agent/correction/deterministic.py:149-151`) and connectivity then pulls cell edges to it (`src/agent/correction/deterministic.py:183-189`), so footprint matching needs a hard-anchor/ambiguity policy, not weighted averaging or broad greedy attachment.

- MINOR: Adding a required `CoreTolerances` field will break every direct test constructor unless they are updated. The helper constructors are at `tests/test_deterministic_core.py:13-27` and `tests/test_kernel_guards.py:15-29`.

- MINOR: The correction audit label currently reports `"AXIS_JITTER_TOL+SNAP_GRID+MIN_EDGE_LENGTH"` for structural snaps (`src/agent/correction/deterministic.py:145`). If cross-floor reconcile is introduced, audit entries should name the new tolerance so large cross-floor moves are inspectable.

## v2 re-review

## Verdict: APPROVE-WITH-CHANGES

v2 addresses the original blockers in design form: greedy grouping is replaced with mutual-nearest/conflict-flag matching (`AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:76-79`), footprint axes are hard anchors (`AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:75`, `AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:79-80`), Phase A retains raw members (`AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:74`, `AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:82`), and Phase C is provenance-aware (`AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:81`). The remaining issues are implementer-facing precision requirements, not design blockers.

### (a) Mutual-nearest + conflict-flag

No remaining silent greedy-order counterexample if "competition" is implemented strictly as candidate-degree/tie detection over the full candidate graph, not just "two reps on the same other floor." A rep with more than one within-tolerance candidate across all other floors must be ambiguous.

Concrete case that must flag, not merge: `F1=3.10`, `F2=3.20`, `F3=3.30`, `cross_floor_align_tol_m=0.12`. Pairwise, both adjacent gaps are within tolerance. If the implementation allows both `F1-F2` and `F2-F3`, it creates a transitive component spanning `0.20 m`, beyond the tolerance, and can erase a stepped real offset. With strict degree conflict, `F2` has two candidates and the component is flagged.

Concrete conservative false-negative: `F1=3.10`, `F2=3.20` is the true jitter pair, but `F2` also has another rep at `3.00`. The v2 rule should flag rather than merge. That can fail to auto-merge a true pair, but it is the intended safe behavior because the coordinate-only schema has no wall identity beyond rectangular cell axes (`src/agent/correction/schema.py:30-37`, `src/agent/correction/schema.py:59-64`).

Residual unavoidable false-positive class: a real layout offset of `0.10-0.12 m` with no competing axis, e.g. `F1=3.10`, `F2=3.21`, will be mutual-nearest and silently aligned unless there is some additional evidence. That is not fixable with coordinate-only matching and a tolerance above `0.10 m`; it is the tradeoff v2 accepts to fix sm21.

### (b) `cross_floor_align_tol_m=0.12`

I would use `0.11 m` as the default, not `0.12 m`, unless sm21 or broader eval shows legitimate jitter above `0.11 m`. `0.12 m` is materially safer than the original `0.20 m`, but real intentional offsets around `0.10-0.15 m` still occur in shafts, cores, local corridor jogs, stair/service-wall shifts, and floor-plan changes. Because the known target is exactly `0.10 m`, `0.11 m` gives a narrow margin above the failure while reducing the unavoidable false-positive band.

The invariant should be `axis_jitter_tol_m < cross_floor_align_tol_m < gap_close_threshold_m`, inserted explicitly into the existing validation chain (`src/agent/correction/config.py:66-73`). Do not restore `min_edge_length_m <= cross_floor_align_tol_m`; v2 correctly drops that as a semantic invariant.

### (c) Phase C provenance-aware sliver

The Phase C same-floor conflict test is complete if it compares original Phase A reps/supports, not post-merge canonical values. The check should block any sliver merge between two canonical groups when there exists a floor `f` with one original rep in group A and one original rep in group B whose original separation is `>= min_edge_length_m`. That is the condition that preserves a real same-floor wall while still allowing invalid sub-`min_edge` slivers to be merged or flagged.

Two implementation constraints matter:

1. Include footprint hard anchors in provenance. If an internal group is merged into a footprint sliver, the footprint coordinate remains the canonical value; it is not averaged.
2. A residual sub-`min_edge` pair that cannot be merged because of same-floor provenance must be a blocking ambiguity/unsupported outcome, not merely left as two canonical axes. The existing core's promise is that canonical axes do not leave sub-min-edge gaps (`src/agent/correction/deterministic.py:69-86`, `src/configs/correction.yaml:53-62`).

### (d) Remaining blocker/major issues

- MAJOR: Define the ambiguity flag channel and its routing. The plan says `cross_floor_ambiguous` goes to judge② (`AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:78`, `AI_agent/logs/review/request/2026-06-21_cross_floor_wall_alignment_request.md:88`), but the local pipeline currently only writes `conflicts`/`unsupported` artifacts after the core (`src/agent/pipeline.py:704-719`) and then proceeds into geometry materialization (`src/agent/pipeline.py:721-740`). The implementer needs an explicit choice: put ambiguity into `geom.conflicts` for judge-only review, or `geom.unsupported`/gate issue if it must block deterministic geometry use.

- MAJOR: Specify mutual-nearest conflicts as graph-level conflicts: degree > 1, ties, two-to-one, and multi-floor transitive chains all flag. Without this precision, the v2 text can be misread narrowly and reintroduce a chain merge.

- MINOR: Add focused tests for one-to-one merge, one-to-many flag, two-to-one flag, three-floor chain flag, footprint competition, Phase C same-floor conflict, and residual sliver blocking. Existing constructors in `tests/test_deterministic_core.py:13-27` and `tests/test_kernel_guards.py:15-29` must be updated for the new tolerance field.

No remaining BLOCKER before dispatch if the two MAJOR items above are included in the implementation brief.
