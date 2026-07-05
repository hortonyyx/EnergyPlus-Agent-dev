# Reading Phase A Batch 2 Execution Log

Date: 2026-06-30

Scope implemented: A5, A9, A6, A10 only.

## Summary

- Promoted `reading.stroke_provenance_coverage` from always-pass to evidence debt when provenance mode is `legacy` or `partial`.
- Added pure machine-readable scorer mode: `score_reading_vs_gt.py --json-only`.
- Added sm21 phase1 reading-score regression floor: walls must be 9/9 and windows must be at least 14/15.
- Added advisory per-view `reading.partition_on_window_jamb` cross-check.
- Added GT-anchored E/W facade sign test and flipped latent constants:
  - East: `("y", "x_max", +1)`
  - West: `("y", "x_min", -1)`
- Left `FACADE_NORMAL` unchanged and did not wire `derive_facade_frame` into the pipeline.

## A5 Provenance Coverage Promotion

`_stroke_dimension_consistency()` computes provenance mode from structural strokes with pens in:

- `wall`
- `window`
- `wall_fill`
- `outline`

Mode computation is unchanged:

- `legacy`: no structural strokes, or no structural strokes have `provenance`;
- `partial`: some but not all structural strokes have `provenance`;
- `full`: every structural stroke has `provenance`.

Behavior changed only at emission:

- `legacy` / `partial` now emit `FAIL` for `reading.stroke_provenance_coverage`;
- `full` still emits `PASS`;
- evidence still includes `_evidence_meta(meta)`:
  - `dimensioned`
  - `raw_has_dimensions`
  - `raw_has_uncaptured`
  - `legacy_migrated`

Because `reading.stroke_provenance_coverage` remains in `EVIDENCE_CHECK_IDS`, Batch 1 disposition policy applies:

- exploratory/dev: flag;
- golden/regression: block;
- `legacy_migrated`: grandfathered to flag, never block.

## A9 Reading Score Harness

`scripts/tool_scripts/score_reading_vs_gt.py` now supports:

```bash
python scripts/tool_scripts/score_reading_vs_gt.py --json-only <reading_dir> --case <case>
```

`--json-only` prints only the JSON object, with no human-readable rows before it. Existing human mode remains default, and `--json` still appends JSON after human output for compatibility.

Added judge-side regression test in `tests/test_reading_score.py`:

- scores `case_tests/e2e_tests/smalloffice_21_pre/phase1/`;
- uses `sm21_anchor` GT through `src.agent.judge.gt.load_gt`;
- asserts walls `9/9`;
- asserts windows `>= 14/15`.

This stays judge/test-side and does not import GT from gate① code.

## A6 Window-Jamb Cross-Check

Added `reading.partition_on_window_jamb` from `_stroke_dimension_consistency()`.

Evidence sources are per-view only:

- window stroke geometry;
- wall axis lines;
- wall-join evidence;
- dimension cumulative positions.

No `wall_fill`, no `thickness`, and no cross-floor/cross-layer evidence are used.

Precise heuristic:

- derive window jamb coordinates from:
  - rect `x_range_m` endpoints as x-jambs;
  - rect `y_range_m` endpoints as y-jambs;
  - horizontal line endpoints as x-jambs;
  - vertical line endpoints as y-jambs;
- inspect plan wall line strokes only;
- ignore perimeter wall axes;
- flag when a wall constant coordinate is within `0.20 m` of a same-axis window jamb;
- suppress the flag when either independent support is present:
  - both wall endpoints join other walls; or
  - a dimension cumulative position exists within `0.20 m` of the wall coordinate.

This is advisory only:

- `reading.partition_on_window_jamb` is `CROSS_CHECK`;
- it is not in `EVIDENCE_CHECK_IDS`;
- it flags under regression/golden and does not block.

## A10 Facade Sign

Added test `test_facade_east_west_signs_match_sm21_f2_gt_window_spans` in `tests/test_checks_reading_correction.py`.

GT anchors:

- East, Floor 2, first window opening in `sm21_anchor`;
- West, Floor 2, first window opening in `sm21_anchor`.

The assertions exercise `FacadeWorldFrame.to_world_along()` direction:

- East maps local start/end to the same increasing world-y span;
- West maps local start/end to the reversed world-y span.

This test would fail under the prior constants:

- East `("y", "x_max", -1)`;
- West `("y", "x_min", +1)`.

Then constants were flipped to:

- East `("y", "x_max", +1)`;
- West `("y", "x_min", -1)`.

## Test Changes

- `tests/test_checks_reading_correction.py`
  - strengthened provenance coverage tests for `legacy`, `partial`, `full`;
  - added regression-profile block + legacy-grandfathering provenance test;
  - added advisory-only jamb collision test;
  - added GT-anchored East/West facade sign test.
- `tests/test_reading_score.py`
  - added sm21 phase1 regression floor test.

No existing test was weakened. One facade assertion uses rounded comparison to avoid binary float noise (`8.0 - 4.6`).

## Verification

Targeted:

- `python -m pytest tests/test_checks_reading_correction.py tests/test_reading_score.py tests/test_gt_discipline.py -q`
- Result: `57 passed`

Full suite:

- `python -m pytest -q`
- Result: `363 passed, 9 xfailed, 36 warnings`

Smoke:

```bash
python scripts/tool_scripts/score_reading_vs_gt.py --json-only case_tests/e2e_tests/smalloffice_21_pre/phase1 --case sm21_anchor
```

Output:

```json
{
  "1f_view": {
    "walls": [
      4,
      4
    ],
    "windows": [
      7,
      7
    ],
    "max_wall_offset_m": 0.1
  },
  "2f_view": {
    "walls": [
      5,
      5
    ],
    "windows": [
      7,
      8
    ],
    "max_wall_offset_m": 0.0
  }
}
```

Totals: walls `9/9`, windows `14/15`.

## Golden/Baseline Impact

No existing golden/baseline JSON was changed by this batch.

The worktree already contained Batch 1 and review/proposal artifacts before this batch, so `git status --short` is not clean. Batch 2 did not modify existing run baseline JSONs. Legacy-migrated evidence debt still flags instead of blocking in regression/golden due to the Batch 1 disposition grandfathering rule.

## Follow-Up Fix: A6 Guard Removal

Claude full-review found a real A6 defect: `reading.partition_on_window_jamb` suppressed the motivating phantom-wall case because the offender also had:

- a matching dimension cumulative position; and
- both endpoints joined to other walls.

Those two facts are common to a real partition and a jamb-traced phantom partition, so they are now evidence context only. They no longer suppress the flag.

Updated heuristic:

- still excludes perimeter walls;
- still requires same-axis window-jamb coincidence within `0.20 m`;
- records `matching_dimension_positions`;
- records `joins_walls`;
- flags regardless of dimension-position or endpoint-join support.

Regression coverage added:

- self-contained fixture where the offender is on a window jamb, has a matching dimension cumulative position, and joins walls at both endpoints;
- self-contained clean fixture where an interior partition is not on any window jamb;
- real `sonnet_r2` restore reading fixture assertion for exactly four offenders:
  - `S9` at `3.44`
  - `S11` at `6.30`
  - `S12` at `8.70`
  - `S14` at `11.36`

The real `sonnet_r1` file was inspected but not asserted as clean: its current per-view window geometry includes jamb coordinates at `4.94` and `9.82`, which are within the configured `0.20 m` tolerance of some clean-reading partition coordinates. The self-contained clean fixture covers the intended no-jamb case without encoding that contradictory artifact.

Verification after fix:

- `python -m pytest tests/test_checks_reading_correction.py -q`
- Result: `47 passed`

- `python -m pytest -q`
- Result: `365 passed, 9 xfailed, 36 warnings`

Real r2 smoke:

```text
fail
S9 3.44 True True
S11 6.3 True True
S12 8.7 True True
S14 11.36 True True
```

The final two columns show each offender still carries dimension-position context and both-endpoint-join context.
