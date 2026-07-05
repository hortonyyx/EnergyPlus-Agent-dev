# InterZone Pair Gate Review

Date: 2026-05-29
Reviewer: Codex
Scope: Code review of the deterministic InterZone surface-pair validation gate requested in `AI_agent/logs/review/request/2026-05-29_interzone_pair_gate_request.md`.

## Verdict

Partially accepted, with one correctness fix required before treating this as the InterZone contract gate.

The placement is right: checking the assembled eppy IDF after `ConverterManager.convert_all()` and before EnergyPlus is the right layer. It enforces what the pipeline actually generated, independent of prompt compliance, and it successfully blocks the sm21 Sonnet 0.05 m sliver class before EP can segfault.

The current validator is pairwise useful but incomplete: it checks floor/ceiling coplanarity in z, but it does not check coplanarity for vertical InterZone wall pairs. A pair of reciprocal, equal-area, opposite-normal walls on parallel planes can pass even though the two surfaces are not geometrically coincident. That is a false negative for a deterministic InterZone gate.

## Findings

### 1. High - Vertical InterZone wall pairs can be offset and still pass

Evidence:
- `validate_interzone_surface_pairs()` checks target existence, reciprocity, area, and opposite normals for all InterZone pairs (`src/validator/interzone.py` lines 103-161).
- It only checks coplanarity for pairs whose surface types are a subset of `{"Floor", "Ceiling", "Roof"}` by comparing z spans (`src/validator/interzone.py` lines 163-171).
- There is no equivalent plane-coincidence check for `Wall` <-> `Wall` pairs.
- I confirmed with a local mock: two reciprocal wall surfaces, one at `x=0.00` and one at `x=0.05`, with equal area and opposite normals, return `[]` from `validate_interzone_surface_pairs()`.

Risk:
This misses the vertical-wall version of the same geometric defect the gate is meant to catch: two zones can claim an InterZone boundary but place the paired wall surfaces on different parallel planes. EnergyPlus may warn, fatal later, or accept physically wrong geometry depending on the details. The review request specifically asks whether the Newell normal + antiparallel test correctly treats InterZone walls; by itself it does not.

Recommended action:
Add a general coplanarity / plane-coincidence check for every reciprocal InterZone pair, not just horizontal ones:

- Compute a plane from `src` normal and one source vertex.
- Verify all target vertices have point-to-plane distance <= tolerance, and ideally all source vertices also fit their own plane.
- Keep the existing z-plane message for floor/ceiling as a clearer specialized error if desired.
- Add a unit test with two equal-area opposite-normal vertical walls offset by 0.05 m; it should fail.

For axis-aligned SmallOffice surfaces, a simpler interim check is also acceptable: after confirming normals are opposite, verify the coordinate along the normal axis matches within `_Z_TOL`-like tolerance. The general plane-distance version is cleaner and covers non-axis-aligned future cases.

### 2. Medium - The new validator has no focused unit tests for the failure classes it owns

Evidence:
- `pytest` passes 5/5, but `rg` finds no tests for `validate_interzone_surface_pairs()` or `audit_interzone_surface_pairs()`.
- The only exercised validation I found is calibration by running against stored IDFs. That confirms current samples, but not edge cases such as missing target, non-reciprocal target, duplicate target, area mismatch, normal mismatch, vertical offset, and min-edge slivers.

Risk:
The validator is now a hard gate in `run_simulation()` and `export_idf_only()`. Without small deterministic tests, future changes can weaken checks silently. The vertical-wall false negative above is exactly the kind of bug a tiny mock-based unit test would catch without needing a full IDF fixture.

Recommended action:
Add focused unit tests using minimal mock IDF/surface objects or small generated IDFs. Cover at least:

- clean reciprocal wall pair
- clean reciprocal floor/ceiling pair
- missing target
- target not OBC=Surface
- non-reciprocal pair
- duplicate incoming target
- area mismatch
- normals same direction
- horizontal z mismatch
- vertical wall plane offset
- min-edge sliver

### 3. Low - `audit_interzone_surface_pairs()` reports reciprocal pair count from raw OBC count

Evidence:
- `audit_interzone_surface_pairs()` reports `"reciprocal_interzone_pairs": obc_counts.get("Surface", 0) // 2` (`src/validator/interzone.py` lines 185-192).
- That count is accurate for clean calibrated IDFs, but it is not actually the number of reciprocal pairs when the graph is broken, odd, duplicated, or non-reciprocal.

Risk:
This is only an audit field, not a gate decision, so the risk is low. But baseline notes may say "31 reciprocal pairs" even when only 30 are reciprocal plus two broken references. That weakens the diagnostic value of the audit summary.

Recommended action:
Calculate reciprocal pairs by iterating unique frozensets that are actually mutual references, and optionally add separate `surface_obc_count`.

### 4. Low - `_check_interzone_pairs()` runs the validator twice

Evidence:
- `_check_interzone_pairs()` calls `audit_interzone_surface_pairs(idf)`, and the audit calls `validate_interzone_surface_pairs(idf)` internally (`src/validator/interzone.py` lines 176-184; `src/mcp/tools/workflow.py` lines 28-31).
- `_check_interzone_pairs()` then calls `validate_interzone_surface_pairs(idf)` again (`src/mcp/tools/workflow.py` line 31).

Risk:
Low for current IDF sizes, but it duplicates work and duplicate log/debug cost as models grow. More importantly, if validation later becomes more expensive because coverage checks are added, this pattern will matter.

Recommended action:
Let `_check_interzone_pairs()` call `issues = validate_interzone_surface_pairs(idf)` once and pass that into an audit helper, or split audit into a count-only function that does not validate.

## Review Questions

### Validator correctness

Mostly sound for target existence, target type, reciprocity, duplicate incoming target, area mismatch, opposite normals, horizontal z-coplanarity, and the concrete Sonnet sliver class. Not complete for vertical wall coplanarity; fix finding #1 before relying on it as the deterministic gate.

### `_MIN_EDGE = 0.10 m` and degeneracy metric

Acceptable for the current SmallOffice-class regime. The sm21 Sonnet slivers are 0.05 m and are correctly blocked. A shortest-edge guard is a good first detector for the crash class.

False-kill risk exists for future genuinely tiny modeled spaces or facade returns, especially because the guard applies to every `BuildingSurface:Detailed`, not only InterZone surfaces. Given the project currently models zone boundaries, not wall thickness/mullions/detail geometry, I would keep the hard threshold for now but make it easy to tune and document that sub-0.10 m thermal-zone geometry is unsupported unless explicitly revisited.

### Hard gate vs warn

Hard gate is appropriate for missing target, non-Surface target, non-reciprocal references, duplicate target claims, degenerate slivers, and non-coplanar paired surfaces. Area and normal mismatches should also remain hard failures at the current tolerances for this geometry regime; they indicate the paired boundary is not the same physical face.

Once vertical coplanarity is added, the hard gate is safer than letting EP be the first detector.

### `manager._idf` access

Acceptable as a local workaround. The validator must run on the live assembled IDF, and `ConverterManager.idf` currently deep-copies `_idf`. The comment in `_check_interzone_pairs()` explains why `_idf` is used (`src/mcp/tools/workflow.py` lines 17-28).

Recommended cleanup later: add a read-only accessor such as `manager.live_idf` or `manager.get_idf(copy=False)` so workflow code does not reach into a private attribute.

### Deferring coverage completeness

Agree with deferring polygon-intersection coverage completeness. Pairwise validation plus min-edge catches the immediate segfault class and common bad-reference classes. Full stacked-floor coverage is still important because pairwise-valid surfaces can collectively miss or duplicate overlap area, but implementing it well needs polygon operations or a deliberately limited axis-aligned rectangle checker.

If the next few cases remain strictly axis-aligned rectangles, a numpy-only rectangle coverage checker could be a useful interim. I would not block this gate on that, as long as the deferral remains tracked.

## Placement / Integration

The workflow placement is correct:

- `export_idf_only()` runs `_check_interzone_pairs()` after `manager.convert_all()` and before accepting/saving final IDF status (`src/mcp/tools/workflow.py` lines 145-164).
- `run_simulation()` runs the same gate after conversion and before `EnergyPlusRunner.run_idf()` (`src/mcp/tools/workflow.py` lines 209-232).
- On failure, the IDF is still saved for inspection and `ToolResponse(success=False)` returns `interzone_pair_issues` plus `idf_path` (`src/mcp/tools/workflow.py` lines 149-162 and 214-227).

One minor note: `export_idf_only()` does not create `output_dir` before `self.state.export_yaml(temp_yaml)`, unlike `run_simulation()` (`src/mcp/tools/workflow.py` lines 141-145 vs 202-203). That appears pre-existing or at least adjacent; if callers pass a missing output dir, export may fail before the new gate. Not an InterZone validator blocker, but worth cleaning separately.

## Calibration / Verification

I ran the validator locally against the request's evidence IDFs:

```text
sm21 opus:       0 issues, 100 surfaces, 62 Surface OBC, 31 pairs
sm21 deepseek:   0 issues, 100 surfaces, 62 Surface OBC, 31 pairs
sm21 sonnet:     4 issues, all 0.0500 m slivers
sm21 main pass:  0 issues, 100 surfaces, 62 Surface OBC, 31 pairs
sm16 glazingfix: 0 issues, 135 surfaces, 90 Surface OBC, 45 pairs
```

I also ran:

```text
python -m py_compile src/validator/interzone.py src/mcp/tools/workflow.py
pytest -q
```

Result: `pytest` passed 5/5.

## Acceptance Criteria Status

- Validator correctness: partial; fix vertical wall coplanarity.
- 0.10 m threshold / metric: acceptable for current scope, tuneable later.
- Hard-gate behavior: correct for the intended issue classes after coplanarity fix.
- `manager._idf`: acceptable short-term; public accessor preferred later.
- Coverage completeness deferral: acceptable, keep tracked.
- Graded findings: listed above.

---

## Disposition (main dev agent, 2026-05-29)

- **#1 High (vertical wall coplanarity) — FIXED.** Replaced the floor/ceiling-only z check with a
  general point-to-plane coincidence check applied to *every* reciprocal pair
  (`_max_point_to_plane`, `_PLANE_TOL = 0.02 m`) in `src/validator/interzone.py`. Re-calibrated on the
  real IDFs: sm21 opus/deepseek + sm16 glazingfix still 0 issues, sonnet still 4 (the slivers) — no new
  false kills from running coplanarity on wall pairs.
- **#2 Medium (unit tests) — DONE.** Added `tests/test_interzone.py` (12 mock-based tests) covering
  clean wall + floor/ceiling pairs, missing target, non-Surface target, non-reciprocal, duplicate
  incoming, area mismatch, same-direction normals, **vertical wall plane offset (0.05 m)**, horizontal
  z mismatch, min-edge sliver, and the audit mutual-pair count. Full suite 20/20.
- **#3 Low (reciprocal count) — FIXED.** `audit_interzone_surface_pairs` now counts actual mutual
  frozensets, not `Surface//2`; test asserts a broken reference is excluded.
- **#4 Low (double validate) — FIXED.** `_check_interzone_pairs` validates once and passes the result
  to `audit_interzone_surface_pairs(idf, issues=...)`.
- **min-edge 0.10 / hard-gate / `manager._idf` / coverage deferral** — accepted as-is; coverage (#2 of
  the original surface-pairing review) stays tracked in `downstream_agent_changes.md`. Public
  `ConverterManager` accessor noted as later cleanup.

