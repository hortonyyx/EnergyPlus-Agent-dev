# Envelope Facade Priority Proposal Review

Date: 2026-06-23  
Verdict: **REWORK**

The direction is right: a facade-derived envelope should be able to override a wall-centerline footprint when the delta is wall-thickness scale. The landing plan is not safe enough as written. The main failures are anchoring, candidate authority, legacy unit handling, and relying on a second tolerance to move cells.

Counts: **BLOCKER 4 / DISAGREE 4 / NIT 3**

## Findings

### BLOCKER 1 - SW-corner anchoring is wrong for observed sm21 outputs

Evidence:
- The proposal says to fix `footprint[lo]` and set `footprint[hi] = footprint[lo] + outer`: `AI_agent/logs/review/request/2026-06-23_envelope_facade_priority_proposal.md:46`.
- Existing sm21 outputs do not share a reliable `lo == outer origin` assumption. One run has `footprint_x=[0.12,14.88]` and `footprint_y=[0.12,7.88]`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/1_correction/correction_geometry.json:2`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/1_correction/correction_geometry.json:6`.
- Another run has `footprint_x=[-0.12,14.64]` and `footprint_y=[-0.12,7.64]`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/1_correction/correction_geometry.json:2`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/1_correction/correction_geometry.json:6`.
- The canonical project invariant is origin = whole-building SW outer boundary, not "whatever lo the correction model emitted": `AI_agent/CLAUDE.md:70`.
- The gt is explicitly outer envelope 15.0 x 8.0: `case_tests/test_baseline/gt/sm21_anchor/gt.json:13`.

Why this blocks:
- For `[0.12,14.88]`, fixed-lo reconciliation to `15.0` yields `[0.12,15.12]`, shifted 120 mm east/north.
- For `[-0.12,14.64]`, fixed-lo reconciliation yields `[-0.12,14.88]`, still shifted 120 mm west/south and still not the gt `[0,15]`.
- The proposal fixes the span but can preserve or introduce a global-origin error.

Recommendation:
- Do not pass only `{x: span, y: span}`. Pass an `authoritative_envelope` object with source candidates and, when available, facade-local bounds plus their mapped world bounds.
- If authoritative bounds map to `[0,15]` / `[0,8]`, set both `lo` and `hi`.
- If only a span is available and origin is not independently established, do not silently choose an origin. Either apply a symmetric expansion only when both old boundaries are proven half-wall insets, or emit `unsupported` / `conflict` for origin ambiguity.

### BLOCKER 2 - `value_m`-first extraction will fail on current legacy migration

Evidence:
- The proposal says use `value_m` before `from/to`: `AI_agent/logs/review/request/2026-06-23_envelope_facade_priority_proposal.md:34`.
- Legacy dimensions are migrated by parsing `text` into `value_m`: `src/agent/reading/legacy.py:48`.
- That parser returns the numeric text directly, with no mm-to-m conversion: `src/agent/reading/legacy.py:35`.
- The sm21 legacy dimension is `text="15000"` with `from=[0,6.6]` and `to=[15,6.6]`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/South_view.json:119`.

Why this blocks:
- If the helper uses `load_reading_view()` or otherwise sees migrated dimensions, `value_m` can become `15000.0`, not `15.0`.
- A value-first implementation then either rejects the good envelope as over-tolerance or, worse, treats a bad unit as authoritative.

Recommendation:
- For legacy dimensions with endpoints, prefer the axis span from `from/to` over `value_m`.
- Treat `value_m` as authoritative only when it is consistent with `from/to` within a small tolerance or when the source is non-legacy P1a.
- Text fallback must infer units: raw values like `15000` / `8000` in facade dimensions are mm and should become `15.0` / `8.0`.
- Add a regression that loads the exact South `D1` fixture and asserts the extracted value is `15.0`, not `15000.0`.

### BLOCKER 3 - "max span over facade views" needs authority scoring and disagreement handling

Evidence:
- The proposed extractor is `outer_x = max span` over North/South and `outer_y = max span` over East/West: `AI_agent/logs/review/request/2026-06-23_envelope_facade_priority_proposal.md:34`.
- The current data already has stronger signals than "max": explicit `overall` / `total` notes on South and North dimensions: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/South_view.json:124`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/North_view.json:105`.
- East and West likewise mark overall depth: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/East_view.json:74`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading/West_view.json:64`.
- The existing correction check already treats facade width vs footprint as cross-image reconcile data, not blind max selection: `src/validator/checks/correction.py:74`.

Why this blocks:
- The 0.3 m gate rejects a 30 m hallucination, but it does not reject a plausible-looking bad larger span such as roof overhang, tick/reference-line extent, or a cumulative reference line at 15.2 m against a 14.9 m footprint.
- `max` also resolves North/South disagreement in the riskiest direction: it systematically expands to the largest value even when the larger one is the outlier.
- `nearest-to-footprint` is not universally safe either; it can choose the wall-centerline value over the true outer value. The implementation needs candidate authority, not a scalar max/nearest rule.

Recommendation:
- Extract all candidates with `{view, dim_id/stroke_id, span, bounds, role, note, source_kind}`.
- Rank candidates: `role=overall` or note contains `overall|total|总` > outline/wall_fill envelope > untagged max span > text-only fallback.
- Require at least one second signal before reconciling: explicit overall/total note, outline/wall_fill extent agreement, or same-axis opposite-facade agreement.
- If high-authority North/South or East/West candidates disagree by more than a small tolerance, emit `conflict`/`unsupported` and skip reconciliation for that axis. Do not silently take `max`.

### BLOCKER 4 - Moving only the footprint and relying on `gap_close` is too coupled

Evidence:
- `gap_close_threshold_m` is currently `0.300`: `src/configs/correction.yaml:95`.
- The core computes footprint snap first, stores `gthr`, then moves cell edges by `_close_to_boundary`: `src/agent/correction/deterministic.py:551`, `src/agent/correction/deterministic.py:554`, `src/agent/correction/deterministic.py:585`.
- `_close_to_boundary` only pulls a value already inside the current footprint boundary and within threshold: `src/agent/correction/deterministic.py:494`.
- Coverage is a hard correction invariant: cells must tile the footprint without holes/overlaps: `src/agent/correction/geometry_validator.py:8`, implemented against the footprint at `src/agent/correction/geometry_validator.py:53`.

Why this blocks:
- Today `gap_close_threshold_m` happens to cover the half-wall movement, but the proposed envelope tolerance is a new concept. If someone later tunes gap-close down, envelope reconcile silently creates perimeter holes.
- Directly changing footprint first and trusting a later generic connectivity rule makes audit and test intent blurry. This is not just "gap closing"; it is an authoritative envelope basis change.
- If `lo` also needs to move, relying on the directional close becomes even more fragile.

Recommendation:
- In the envelope reconcile step, remember old footprint bounds and directly move cell edges that were on or near the old outer boundary to the new authoritative boundary.
- Log those cell-edge moves under the envelope rule, not only `deterministic_core.gap_close`.
- Either enforce `envelope_reconcile_tol_m <= gap_close_threshold_m` in config validation or remove the dependency by direct edge movement.
- Run `validate_corrected_geometry()` after the core in tests to prove no holes/overlaps were introduced.

### DISAGREE 1 - Dimension-only extraction misses one of the cited sm21 readings

Evidence:
- The GPT-5.4 sm21 South view has exact `wall_fill` / `outline` spans of `[0,15]`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/South_view.json:14`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/South_view.json:45`.
- The same file explicitly says dimension text was seen but not traced into `dimensions[]`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/South_view.json:174`.
- East and West have exact outline depth `[0,8]`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/East_view.json:78`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/West_view.json:63`.

Recommendation:
- If this fix is meant to cover the sm21 batch generally, use outline/wall_fill extents as a corroborating/fallback envelope signal.
- If dimension-only is intentional for this round, document that GPT-5.4-style readings with no `dimensions[]` will no-op and must be handled by reading rework or a follow-up.

### DISAGREE 2 - "Windows auto-follow because facade.py is footprint-derived" is not the production path

Evidence:
- `facade.py` does derive frames from `footprint_x/y`: `src/agent/correction/facade.py:69`.
- The production geometry build path calls `build_zone_volumes()`, `pair_surfaces()`, then `attach_windows()`: `src/agent/geometry/build.py:31`.
- `attach_windows()` places windows on the parent exterior wall selected from built surfaces: `src/agent/geometry/modelling.py:438`.
- Window vertices use the parent wall plane, not `derive_facade_frame()`: `src/agent/geometry/modelling.py:286`.

Recommendation:
- The auto-follow claim should be restated: windows follow only if the parent exterior cell edge moves to the new envelope before geometry build.
- Add an end-to-end unit test where a South/North/East/West window survives envelope reconcile and attaches to the new exterior wall plane.
- Do not assume `facade.py` protects production behavior unless it is actually wired into correction/window translation.

### DISAGREE 3 - The pipeline location is acceptable, but the helper should be shared with gate checks

Evidence:
- `run_pipeline()` currently calls `run_correction()` then `apply_deterministic_core()`: `src/agent/pipeline.py:726`.
- `discover_vector_files()` already owns reading vector discovery order: `src/agent/pipeline.py:68`.
- `check_correction()` already has an `elevation_widths` input for cross-image reconcile: `src/validator/checks/correction.py:55`.

Recommendation:
- Keep raw reading JSON parsing outside `deterministic.py`; the core should receive structured numeric envelope candidates only.
- Put extraction in a small reading/correction utility that both `pipeline.py` and `validator/checks/correction.py` can call. Avoid one implementation for mutation and a second one for checks.
- Do not mutate `dimensions[].role` in-place in `0_reading` artifacts as part of this fix. If role inference is useful, write it into the correction audit/candidate metadata; full role population is correctly listed as backlog.

### DISAGREE 4 - Audit and unsupported handling are underspecified for an authority-changing transform

Evidence:
- A0 requires geometry changes beyond output precision and authority changes to produce `corrections[]` with source provenance: `skills/intake_pipeline/1_correction/A0_contract.md:87`.
- The core currently appends lightweight audit entries for snap/gap-close: `src/agent/correction/deterministic.py:536`.
- The proposal says over-tolerance should record `unsupported`, but does not specify source ids, candidates, tolerance value, or axis disagreement form: `AI_agent/logs/review/request/2026-06-23_envelope_facade_priority_proposal.md:47`.

Recommendation:
- Add a structured audit entry for each accepted axis: source view, source dimension/stroke ids, original footprint bounds/span, resolved bounds/span, tolerance name/value, and candidate class.
- For rejected axes, emit `unsupported` or `conflict` with all near candidates and the reason: over tolerance, cross-facade disagreement, missing origin, or unit ambiguity.

### NIT 1 - Add the tolerance to both config validation and A0 vocabulary

Evidence:
- `CoreTolerances` currently has no envelope tolerance field: `src/agent/correction/config.py:41`.
- Config validation enforces cross-field tolerance ordering for existing concepts: `src/agent/correction/config.py:58`.
- A0's tolerance registry is the named vocabulary consumed by correction rules: `skills/intake_pipeline/1_correction/A0_contract.md:166`.

Recommendation:
- Add `envelope_reconcile_tol_m` to `CoreTolerances`, loader, tests, and `correction.yaml`.
- Add a named A0 tolerance such as `ENVELOPE_RECONCILE_TOL`.
- If the implementation still depends on gap-close, validate the relationship explicitly.

### NIT 2 - Existing strict-xfail/golden tests will not protect this change

Evidence:
- The sm20/sm21 validation baselines are currently strict xfail pending re-record: `tests/test_validation_run_baseline.py:26`, `tests/test_validation_run_baseline.py:216`.
- The live sm21 count test checks only 14 zones / 100 surfaces / 15 windows: `tests/test_validation_run_baseline.py:226`.

Recommendation:
- Add focused unit tests in `tests/test_deterministic_core.py` for accept, reject, missing-envelope no-op, origin ambiguity, direct cell-boundary movement, and window attachment after reconcile.
- Add extraction tests using the exact sm21 South/North/East/West JSONs, including the GPT-5.4 no-`dimensions[]` case if supported.
- Do not rely on the current golden xfails to catch a shifted 15.0 m footprint with the right counts.

### NIT 3 - The cleanest contract is envelope candidates, not a bare dict

Recommendation:
- Define a small internal shape, e.g. `EnvelopeCandidate(axis, span, bounds, source_kind, view, source_id, role, note, confidence)`.
- Pipeline extraction should resolve candidates into an `AuthoritativeEnvelope` with per-axis accepted candidate(s), disagreements, and skipped reasons.
- `apply_deterministic_core()` should receive only that structured object or `None`, keeping `CorrectedGeometry` and `IntakeOutput` schemas unchanged.

## Contract / topology notes

- This does not need to change the `IntakeOutput` 11-field contract; that boundary is explicitly stable: `AI_agent/CLAUDE.md:71`.
- It does change `CorrectedGeometry` coordinates before geometry build, so it is topology-affecting at the correction checkpoint. The hard invariant to preserve is per-floor coverage of the footprint: `src/agent/correction/geometry_validator.py:53`.
- The geometry kernel does not use the footprint to build cell polygons directly; it builds zones from cells: `src/agent/geometry/modelling.py:163`. Therefore a footprint-only correction is insufficient unless cell edges are reconciled too.

## Required changes before landing

1. Replace bare max-span extraction with scored candidates, unit-safe parsing, and explicit disagreement handling.
2. Pass authoritative bounds where available; do not fixed-lo anchor unless origin is independently proven.
3. Move old-boundary cell edges directly inside envelope reconcile, with audit.
4. Add extraction and core tests covering sm21 fixtures, over-tolerance rejection, origin ambiguity, and window attachment.

## Second Pass (v2)

Date: 2026-06-23  
Updated verdict: **REWORK**

V2 closes the original extraction/authority/unit blockers in principle: scored candidates from dimension `from/to` bounds plus outline/wall_fill extents address the legacy `value_m` trap, the GPT-5.4 no-`dimensions[]` fixture class, and the silent `max` rule. Passing bounds rather than spans also closes the fixed-lo anchoring bug at the footprint level. The remaining blockers are in V2-C: the coordinate-motion rule is still under-specified and partly dangerous for the observed sm21 data.

Remaining counts: **BLOCKER 2 / DISAGREE 1 / NIT 0**

### BLOCKER 1 - V2-C still permits a wrong global translation of interior axes and windows

Evidence:
- V2-C says: "origin 移则该轴全体一致平移 + 外边扩到 hi": `AI_agent/logs/review/request/2026-06-23_envelope_facade_priority_proposal.md:114`.
- The observed GPT-5.4 sm21 correction has a centerline-inset footprint `[0.12,14.88]`, but its interior partitions are already on useful world coordinates like `5.0` and `10.0`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/1_correction/correction_geometry.json:2`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/1_correction/correction_geometry.json:19`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/1_correction/correction_geometry.json:31`.
- Window span semantics are along-facade world coordinates: `src/agent/correction/schema.py:40`. Geometry build places the window on the parent wall plane using that span: `src/agent/geometry/modelling.py:286`.

Why this still blocks:
- For `[0.12,14.88] -> [0,15]`, globally translating the x axis by `-0.12` would turn correct interior axes `5.0/10.0` into `4.88/9.88`. That recreates coordinate drift rather than fixing envelope basis.
- The same applies to window spans: many sm21 window spans are already dimension-derived along the outer facade coordinate. They should generally stay at their along-facade positions while the parent wall plane moves via the cell boundary.

Required fix:
- Replace the "origin shift => translate whole axis" rule with an attachment-based rule:
  - move only cell coordinates attached to old low/high footprint boundaries within `envelope_reconcile_tol_m` or a named boundary-attach tolerance;
  - leave interior partition axes unchanged unless there is independent evidence that the whole coordinate frame is globally shifted;
  - do not shift window along-facade spans by default. Windows "follow" because the parent exterior wall plane is rebuilt from moved cell edges. Shift a window span only if a separate global-frame translation is explicitly accepted and audited.

### BLOCKER 2 - V2-C needs a pre-move collision/collapse guard, not only post-validation

Evidence:
- V2-C says to move cell outer edges directly and then run `validate_corrected_geometry()`: `AI_agent/logs/review/request/2026-06-23_envelope_facade_priority_proposal.md:112`, `AI_agent/logs/review/request/2026-06-23_envelope_facade_priority_proposal.md:117`.
- The core's min cell-edge safety is `tol.min_edge_length_m`: `src/agent/correction/deterministic.py:599`.
- The correction validator's nondegenerate threshold is a separate `_MIN_EXTENT = 0.05`, lower than the core's configured `min_edge_length_m = 0.10`: `src/agent/correction/geometry_validator.py:37`.

Why this still blocks:
- A 0.3 m reconciliation can move an exterior boundary inward or across a narrow perimeter cell/interior partition unless explicitly guarded.
- Post-running `validate_corrected_geometry()` is useful but not sufficient as the design rule for an executor. The executor still has to decide whether to clamp, skip, translate, or allow collapse.

Required fix:
- Before applying a boundary move, compute each affected perimeter cell's new extent.
- If the new boundary would cross the nearest interior axis, invert a cell, or leave any affected cell below `tol.min_edge_length_m`, skip that axis and emit `unsupported`/`conflict` with the candidate and offending cell ids.
- Keep post-`validate_corrected_geometry()` as a belt-and-suspenders assertion, not the primary collision policy.

### DISAGREE 1 - The one-facade "second corroborating signal" rule is acceptable but should be made literal

Evidence:
- V2-A says reconciliation requires a second signal: explicit `overall/total` note, outline/wall_fill agreement, or opposite-facade agreement: `AI_agent/logs/review/request/2026-06-23_envelope_facade_priority_proposal.md:102`.

Assessment:
- This is implementable if `role=overall` / `overall|total|总` note is intentionally allowed to count as the corroborating authority signal even when only one facade exists for that axis.
- That is less independent than a second view, but it is a pragmatic rule and covers the current legacy data.

Recommendation:
- Make it explicit in the executor brief: for a single-facade axis, a dimension candidate may reconcile if it has role/note overall authority and passes the footprint tolerance gate; otherwise require same-view outline/wall_fill agreement or skip as insufficient evidence.

## Third Pass (v2.1)

Date: 2026-06-23  
Updated verdict: **APPROVE-WITH-CHANGES**

V2.1 closes the remaining blockers. The design now says to move only old-boundary-attached cell edges, leave interior partitions unchanged, and keep window along-facade spans fixed unless a separately evidenced whole-frame translation is accepted and audited. It also adds the required pre-move collision/collapse guard using `tol.min_edge_length_m`, with post-`validate_corrected_geometry()` reduced to a final assertion rather than the primary policy. The single-facade authority rule is now literal enough for an executor.

Remaining counts: **BLOCKER 0 / DISAGREE 0 / NIT 2**

Final executor nits:
- Define `boundary_attach_tol` explicitly before implementation. Either alias it to `envelope_reconcile_tol_m` or add a separate config/A0 entry; do not leave it as an implicit new tolerance.
- Add tests that assert interior axes and window along-facade spans remain unchanged for `[0.12,14.88] -> [0,15]`, while only boundary-attached cell edges move.
