# Elevation Grade Batch 1 Execution Log

Date: 2026-07-03  
Executor: Codex  
Repo: `/workspaces/EnergyPlus-Agent-dev` local working tree, not GitHub `main`

## Scope Completed

Implemented Batch 1 only: scorer core, correction scoring, policy/config, flow sidecar wiring, and tests. Did not modify `scripts/tool_scripts/render_grade.py`.

## Files Changed

- `src/agent/judge/elevation_score.py` new judge-side elevation scorer.
- `src/agent/judge/correction_score.py` additive correction elevation result.
- `src/agent/judge/score_policy.py` advisory `elevation_windows_placed`.
- `src/agent/execution/run_config.py` elevation grade tolerances in `GradeConfig`.
- `scripts/tool_scripts/run_stage.py` `SCORER_SCHEMA="3"` and sidecar `elevation` writer.
- `tests/test_elevation_score.py` new focused elevation scorer coverage.
- `tests/test_run_config.py` tolerance parsing/default coverage.
- `tests/test_judge_batch_b.py` sidecar/schema/advisory/StageVerdict coverage.
- `tests/test_gt_discipline.py` new scorer covered by judge-side gt discipline.

## Matching and Orientation Algorithm Implemented

Reading extraction:
- Reads only `image_kind=="elevation"` views with `facade.view_facade`.
- Accepts only `pen=="window"` strokes whose `geometry.x_range_m` and `geometry.y_range_m` are numeric pairs.
- Preserves stroke `id` as `source_id`.
- Legacy line windows or missing z are emitted as `unusable_elevation_window` evidence and are never given fabricated z.

GT extraction:
- Builds per-opening truth boxes from `opening.x_m`, `opening.width_m`, `opening.sill_m`, `opening.head_m`.
- Falls back to facade-entry `sill_m/head_m` only if the opening lacks those fields.
- Uses v1 cardinal span limits: `W_m` for North/South, `D_m` for East/West. No world points and no `derive_facade_frame`.

Reading floor assignment:
- Match-first per facade against all gt openings across all floors.
- Candidate relation requires same facade, chosen orientation, along-center delta within `elevation_along_tol_m`, and loose vertical sanity.
- Loose vertical sanity is z-interval overlap or z-center floor band same/adjacent to gt floor band. Bands are half-open `[z_floor,next_z_floor)`, top floor inclusive.
- Matched reading windows take their floor from the matched gt opening. Unmatched extras use z-center band for reporting only.

Four states:
- `placed_hit`: candidate and along center, sill, and head are within tolerance. Width delta is reported only.
- `matched_with_z_drift`: candidate but sill/head out of tolerance. Counts as not placed, but is not double-counted as miss plus extra.
- `miss`: gt opening with no candidate match.
- `extra`: read/correction window not matched to gt.

Pairing:
- For each facade and orientation, a one-to-one candidate assignment is searched to maximize placed hits, then matched pairs, then minimize normalized cost.
- Cost includes normalized along, sill, head, and a small reported-only width term.

Reading orientation:
- Tries `aligned` and interval-reflected `flipped`: `[a0,a1] -> [span_limit-a1, span_limit-a0]`.
- Selects once per facade across floors.
- Maximizes placed hits, then matched pairs, then minimizes normalized cost.
- Ties prefer aligned; same-count near-equal costs within `0.05` are reported as `ambiguous`.
- Vertical z is never flipped. A flipped/ambiguous reading fit is a reconcile signal, not a per-window miss.

Correction elevation scoring:
- Uses `Window.floor` mapped by existing `_map_floors` as primary floor identity.
- Uses `Window.z` as absolute z and does not re-bin correction windows by z.
- Scores aligned world-frame spans only.
- Computes a flipped comparison only to emit `correction_mirrored_model_candidate` evidence in `elevation.evidence`; flipped is not excused.

## Sidecar Schema Emitted

`score_vs_gt.json` now has top-level `elevation` alongside existing plane `scores`:

```json
{
  "elevation": {
    "summary": {
      "gt_total": 15,
      "matched_total": 15,
      "placed_hit_total": 15,
      "z_drift_total": 0,
      "miss_total": 0,
      "extra_total": 0,
      "no_data_floor_facades": 0
    },
    "facades": {
      "South": {
        "orientation": "aligned",
        "span_limit_m": 15.0,
        "floors": {
          "Floor 1": {
            "facade": "South",
            "floor": "Floor 1",
            "orientation": "aligned",
            "no_data": false,
            "gt_count": 3,
            "read_count": 3,
            "matched_total": 3,
            "placed_hit_total": 3,
            "matches": [
              {
                "status": "placed_hit",
                "source_id": "S7",
                "truth": {"id": "South/Floor 1/0", "span": [3.44, 4.64], "z": [1.5, 2.1], "center": 4.04, "width": 1.2},
                "read": {"span": [3.44, 4.64], "z": [1.5, 2.1], "center": 4.04, "width": 1.2, "source_id": "S7", "source_span": [3.44, 4.64]},
                "deltas": {"along_center_m": 0.0, "sill_m": 0.0, "head_m": 0.0, "width_m": 0.0}
              }
            ],
            "extras": []
          }
        }
      }
    },
    "evidence": []
  }
}
```

Zero-window example from sm21:
- `West/Floor 1`: `gt_count=0`, `matches=[]`, `extras=[]`, `no_data=false`.
- If `West_view` is missing, both West floor entries become `no_data=true`.

Every match/extra record carries renderer-ready boxes for present truth/read sides: `truth.span`, `truth.z`, `read.span`, `read.z`, deltas, status, source id, floor, facade, and orientation.

## Schema and Config

- `SCORER_SCHEMA`: `2 -> 3`.
- `GradeConfig.as_tolerances()` now serializes:
  - `wall_tol_m`
  - `window_centre_tol_m`
  - `elevation_along_tol_m`
  - `sill_tol_m`
  - `head_tol_m`
  - `width_tol_m`
- `width_tol_m` is present for identity/cost reporting but not a placement gate.

## Tests

Before: repo-documented baseline was `437 passed, 9 xfailed`.

After:
- Focused: `tests/test_elevation_score.py` passed `8`.
- Full suite: `python -m pytest -q` -> `446 passed, 9 xfailed, 87 warnings`.

Added coverage includes:
- South/Floor 1 `S7` uses per-opening z `[1.5,2.1]` and is a hit.
- Four states: `placed_hit`, `matched_with_z_drift`, `miss`, `extra`.
- East stacked same-along windows are disambiguated by z/floor.
- Interval reflection, per-facade orientation selection, and ambiguous orientation.
- West/Floor 1 zero-window is distinct from missing-view no-data.
- `elevation_windows_placed` appears in `score_criteria`.
- `StageVerdict` rejects `elevation_windows_placed` as a top-level field.
- `test_gt_discipline.py` includes the new judge-side gt reader and reasserts gate①/pipeline/execution/correction have no gt references.

## REVIEW-ASK

- Ambiguous threshold: I used same placed/matched counts plus normalized cost delta `<=0.05` as "near-equal". Please scrutinize whether that threshold should be tighter or config-driven.
- Vertical sanity: implemented as z-overlap or same/adjacent z-center floor band. This follows the spec wording, but adjacent bands are intentionally loose; review whether this is too permissive for future taller buildings.
- Assignment search: brute-force per facade maximizes placed, matched, then cost. This is robust for current small facade counts; review if a Hungarian-style implementation is preferred before larger cases.
- Correction mirror evidence: flipped correction is reported only in `elevation.evidence`, not top-level `evidence`, to avoid triggering the existing generic floor-map completeness criterion. Please confirm that evidence placement is what Batch 2 renderer/judge packet should consume.
- Reading symmetric facades can report `orientation="ambiguous"` while all windows are placed. This is visible on sm21 North/East/West due symmetry. Confirm this is acceptable rather than forcing `aligned` for all-perfect symmetric cases.
