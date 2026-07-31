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
