# Reading typed scoring construction execution log

Owner: sol

Date: 2026-07-31

Spec: `AI_agent/proposals/reading_typed_scoring_plan_sol.md`

## Scope guard

This seat owns the proposal, reading-scoring judge/run-stage work, its tests, and this
log. It does not own or modify:

- `src/agent/execution/isolation.py`
- `src/agent/execution/isolation_templates/**`
- `src/agent/reading/cv_toolbox/**`
- `scripts/tool_scripts/cv_probe.py`
- `case_tests/test_baseline/gt/**`

`src/agent/execution/isolation.py` is modified in the shared working tree by the
parallel seat and is deliberately excluded from this seat's staging/commits.

## Slice 0 — RED locks and pre-change evidence

Status: RED locks landed; no production implementation in this Slice.

The cumulative spec now incorporates D-1/D-2 and all U-01–U-15 final boundaries.
No ruling conflict or implementation impossibility was found. In particular:

- U-05 is per-stroke rect exclusion with first-class
  `unmeasurable_observations`, not whole-component NA.
- U-10 is input-scoped elevation xy+z trusted-frame-reporting NA/retain-as-miss with
  raw two-sided witness; North/West are locked and East/South are controls.
- U-13 separates measurement status from denominator disposition. Product-content
  and product-triggered frame NA retain targets as misses; only trusted-input-only
  capability may filter. The pure denominator API cannot receive raw product values.
- U-03 uses additive v9 fields while preserving correction public judgment bytes.

### Protected-tree before snapshot

Command:

```bash
find case_tests/test_baseline/gt/sm24_anchor -type f -print0 \
  | sort -z | xargs -0 sha256sum \
  > /tmp/reading_typed_scoring_sm24_before.sha256
wc -l /tmp/reading_typed_scoring_sm24_before.sha256
sha256sum /tmp/reading_typed_scoring_sm24_before.sha256
```

Result:

```text
14 /tmp/reading_typed_scoring_sm24_before.sha256
e78c6e7e015746c14d8f70521551a71ee77b6e726259000ecf6133f91d61771f
```

### Correction before snapshot

Canonical serialization is sorted compact UTF-8 JSON plus one LF, exactly as defined
in the spec and Slice 0 test.

```text
public_rows.before_sha256=ee2a4d0d3de034417acd76420a9222899d2585d23bbff6f390ebe0ce09b6635b
wall_criteria.before_sha256=65cf6dfb5136df7195b8cfb7811f7a7f666c90084e8743dc3bcbbf68f9a17025
```

The current-v8 self-comparison printed:

```text
public_rows.after_sha256=ee2a4d0d3de034417acd76420a9222899d2585d23bbff6f390ebe0ce09b6635b
wall_criteria.after_sha256=65cf6dfb5136df7195b8cfb7811f7a7f666c90084e8743dc3bcbbf68f9a17025
blocking_change=false
```

The lock remains RED solely because production still emits sidecar schema 8.

### RED command and defects proved

Command:

```bash
python -m pytest -p no:cacheprovider -q \
  tests/test_reading_typed_scoring_slice0.py
```

Result: `6 failed`.

1. Real `{"views":...}` E2E: RED at
   `elevation_observations_not_list` / `score_product_identity_invalid`. Proves the
   run-stage still routes aggregate reading bytes through the flat normalizer.
2. F8 contract lock: RED because `reading_typed_adapter` and its structural detector
   do not exist. Proves there is no non-tautological reading contract guard.
3. U-13 denominator lock: RED because the pure constructor does not exist. The test
   requires a normal product and a product with all geometry malformed plus every
   elevation local-x/mirror declaration flipped to produce identical serialized
   denominator bases, atoms, and hashes while normalization/unmeasurable/frame
   evidence differs.
4. U-05 rect count lock: RED at the live flat-normalizer crash before the
   per-stroke/count assertions. Proves current code cannot consume the real envelope;
   the lock pins applicable component, one witness/count, unchanged denominator, and
   rendered count.
5. U-10 frame witness lock: RED at the same live crash before applicability. The lock
   pins North/West xy+z NA/retain-as-miss plus raw witnesses/count, East/South
   controls, denominator equality against aligned declarations, and eligible
   North/West miss rows.
6. U-03 correction lock: public hashes match the before values, then RED on
   `"8" != "9"`. This makes any later correction judgment-byte change an independent
   blocker.

### D-1 parity preservation

The GT-echo helper now has the required one-line parity-only comment, and the test is
renamed so it is not presented as a reading-scoring E2E. Its substantive assertion is
unchanged.

Command:

```bash
python -m pytest -p no:cacheprovider -q \
  tests/test_c2_b4b_phase_d.py::test_gt_echo_fixture_preserves_runstage_cli_byte_parity
```

Result: `1 passed`.

### Mechanical checks

`git diff --check` passed. `ruff` is not installed in the environment
(`/bin/bash: ruff: command not found`); no formatter rewrite was attempted.

## Next boundary

Slice 1 starts with the detector/v9/total-result RED matrix, then implements only
those contract and totalization seams. Geometry construction remains in later Slices.

## Slice 0 controller correction — U-13

The original cause table incorrectly granted U-10 product/binding frame disagreement
denominator-filtering rights. The tests and spec now treat `trusted_frame` as a
reporting label only. Because `facade.local_x_positive` and `facade.mirrored` are
product bytes, U-10 NA retains answer targets and emits misses.

The strengthened purity lock changes geometry and both facade declarations. The
denominator constructor's fourth argument is now
`trusted_capability_dispositions`, whose strict cause literal permits only
`trusted_input`; the function cannot receive any raw product value.

Re-run:

```bash
python -m pytest -p no:cacheprovider -q \
  tests/test_reading_typed_scoring_slice0.py
```

Result: `6 failed` on the same intended pre-implementation boundaries. The U-13
failure is the absent pure constructor; the U-10 integration failure is the live
`elevation_observations_not_list` crash before the strengthened assertions.

## Slice 1 — contract, v9 wire, and total-result boundary

### RED locks

The Slice 1 locks were committed without production changes in:

- `8923be4` — initial detector/wire/cache/total-result locks;
- `e66174d` — total detector matrix, non-object artifact, strict round-trip, and
  unmapped-stable-error locks;
- `2419bed` — later-attempt continuation lock; and
- `fb331ce` — detector/adapter helper-version capability lock; and
- `f9095f2` — v9 row, rejection-code, and certificate/count cross-validation locks.

Each was re-run from a detached worktree containing only its committed test state.
The initial matrix was `8 failed`; the expanded matrix was `15 failed`. The
continuation lock independently failed because the first injected scorer exception
escaped the attempt loop and emitted no warning. The version lock independently
failed before a reviewed detector/helper tuple could be supplied. The focused wire
invariant run was `2 failed` because no v9 types existed.

These reds prove the pre-Slice-1 tree had no structural reading detector, no strict
v9 result envelope, no v9 cache path, no total scorer boundary, no post-commit strict
profile failure, and no independent-attempt continuation after a scorer exception.

Reproduce any committed RED state without the later implementation:

```bash
red_worktree=$(mktemp -d -p /tmp reading-slice1-red.XXXXXX)
git worktree add --detach "$red_worktree" e66174d
(cd "$red_worktree" && python -m pytest -p no:cacheprovider -q \
  tests/test_reading_typed_scoring_slice1.py)
git worktree remove --force "$red_worktree"
```

Substitute `8923be4` for the initial `8 failed` matrix. For the focused continuation,
version, and wire runs, substitute respectively `2419bed`, `fb331ce`, or `f9095f2`
and append the exact test node(s) named by those lock descriptions.

### Implementation

- Reading identity now comes from a total structural detector. It never reads or
  synthesizes `schema_version`; a JSON-readable non-object reaches an explicit
  `unsupported_reading_contract` artifact rather than the former silent early
  return.
- The capability decision accepts only `reading_views_v1` with the reviewed detector
  and adapter versions. The production capability identity also includes the typed
  GT, effective manifest, and score-binding hashes.
- Strict v9 scored/NA/rejected wires, certificate slots, visibility counts, additive
  reading rows, artifact contracts, finalization, and v8-as-cache-miss behavior are
  present. Correction scoring writes v9 while preserving all pinned public judgment
  values.
- `score_typed_attempt_total` uses a frozen-code ownership table. Product/capability
  failures become NA, trusted request failures become rejected, and unexpected or
  unmapped failures become counted `scorer_internal_failure` NA with a stack log.
  Exploratory/dev warns; golden/regression commits the artifact and then raises the
  stable top-level exception.
- The denominator helper is a pure four-trusted-input function. Its filtered basis
  accepts only `cause_class="trusted_input"`; no product payload, geometry, or facade
  declaration is in its signature or preimage.
- Run-stage and the score CLI use the same detector and payload-kind-safe criteria
  access. One internally failed exploratory attempt no longer aborts the next
  attempt.

### GREEN evidence

```bash
python -m pytest -p no:cacheprovider -q \
  tests/test_reading_typed_scoring_slice1.py
```

Result: `18 passed`.

The existing scorer/correction regression set:

```bash
python -m pytest -p no:cacheprovider -q \
  tests/test_reading_typed_scoring_slice1.py \
  tests/test_c2_b2_v3.py \
  tests/test_c2_b2b_envelope_transform.py \
  tests/test_c2_b4b_contract.py \
  tests/test_c2_b4b_phase_b.py \
  tests/test_c2_b4b_phase_d.py \
  tests/test_c2_b5_parent_and_verts.py \
  tests/test_c2_b5_source_routing.py \
  tests/test_c2_vg_visibility.py
```

Result: `335 passed`, with the pre-existing Pydantic serializer warning in
`test_f3_tampered_v3_and_feature_state_fail_closed`.

The Slice 0 integration locks now report `3 passed, 3 failed`. The three remaining
reds are intentionally the Slice 2/3 geometry-certificate boundaries: U-13 integrated
certificate publication, U-05 per-stroke unmeasurable evidence/count, and U-10
input-scoped NA/witness plus retained misses. The real reading boundary, F8 guard,
and correction preservation locks are green.

### U-03 D-1 before/after proof

Reproducible command:

```bash
python -m pytest -p no:cacheprovider -q -s -n0 \
  tests/test_reading_typed_scoring_slice0.py::\
test_correction_public_judgment_sha_matches_pre_v9_baseline
```

Output:

```text
public_rows.before_sha256=ee2a4d0d3de034417acd76420a9222899d2585d23bbff6f390ebe0ce09b6635b
public_rows.after_sha256=ee2a4d0d3de034417acd76420a9222899d2585d23bbff6f390ebe0ce09b6635b
wall_criteria.before_sha256=65cf6dfb5136df7195b8cfb7811f7a7f666c90084e8743dc3bcbbf68f9a17025
wall_criteria.after_sha256=65cf6dfb5136df7195b8cfb7811f7a7f666c90084e8743dc3bcbbf68f9a17025
blocking_change=false
```

### Mechanical checks

```bash
python -m py_compile \
  src/agent/judge/score_schema.py \
  src/agent/judge/reading_typed_adapter.py \
  src/agent/judge/score_service.py \
  scripts/tool_scripts/run_stage.py \
  scripts/tool_scripts/score_reading_vs_gt.py
git diff --check
```

Both completed with no output.

## Next boundary

Slice 2 begins with elevation adapter RED locks. Slice 1 deliberately does not
manufacture reading geometry or certificates; the remaining Slice 0 reds stay red
until those evidence paths land.

## Slice 2 — elevation ReadingView adapter

### RED locks

`431f01d` commits eight elevation locks before implementation. Reproducible command:

```bash
python -m pytest -p no:cacheprovider -q \
  tests/test_reading_typed_adapter.py
```

Result on that committed tree: `8 failed`, all at the absent
`normalize_reading_attempt` seam.

`635f7b4` adds the horizontal-only lock for a malformed non-null vertical datum.
From a detached worktree at that commit, the focused test is `1 failed`; it proves the
accepted combined elevation audit row could not yet represent applicable horizontal
evidence with an NA z component.

### Implementation

- The adapter joins expected output IDs to trusted manifest input IDs and reviewed
  bindings without importing typed GT.
- It strictly consumes rect/line/polyline metre geometry, filters hidden/dashed
  strokes, namespaces observation IDs with the full output/input/stroke/component
  tuple, and permits finite point intervals.
- East/South use the reviewed projection. North/West emit input-scoped
  `trusted_frame` NA plus exact raw/effective declaration witnesses; neither product
  declaration enters the coordinate transform.
- Missing/malformed views and geometry are product-side retain-as-miss outcomes.
  Empty supported inputs remain applicable with zero observations.
- Single-floor null/missing z uses the ruled
  `project_convention_2026_07_25` datum; declared finite z is distinct; multi-floor is
  trusted-filtered; malformed non-null z leaves horizontal observations present and
  makes only the z component NA.
- To represent that last ruled branch without fabricating a z coordinate,
  `ReadingElevationOpeningAuditV1.z_interval` and
  `vertical_transform_sha256` are a validated nullable pair. The cumulative spec now
  states this exact wire boundary.

### GREEN evidence

```bash
python -m pytest -p no:cacheprovider -q \
  tests/test_reading_typed_adapter.py \
  tests/test_elevation_score.py \
  tests/test_c2_b4b_phase_c.py
```

Result: `46 passed`.

Mechanical checks:

```bash
python -m py_compile \
  src/agent/judge/reading_typed_adapter.py \
  src/agent/judge/score_schema.py \
  src/agent/judge/elevation_score.py
git diff --check
```

Both completed with no output.
