# Reading Phase A Spec Review

Date: 2026-06-30

Verdict: **APPROVE-WITH-CHANGES**

Finding counts: **BLOCKER 1 / MAJOR 6 / MINOR 3**

Scope: plan-class double-review only. I reviewed `AI_agent/proposals/reading_evolution_dual_channel_cv.md` Phase A A1-A10, the flag/block ruling, and Section 5 decisions against the current code. I did not implement the plan.

Top-line: Phase A is directionally correct and matches the earlier regression review: the current failure is an enforcement gap between prose-level dual-channel evidence requirements and gates that let weak or missing evidence look clean (`AI_agent/logs/review/review/2026-06-30_reading_architecture_regression_review.md:8`). The plan is implementable without rewriting the reading schema, but the spec needs several changes before execution, especially around dimension-chain completeness, run profile plumbing, golden baseline impact, and correction routing.

## Findings

### BLOCKER 1 - A1 cannot be specified as "require chain_id" only

The existing closure checker is not activated merely by requiring `chain_id`. It skips dimensions with no `chain_id` (`src/validator/checks/reading.py:463`), reports `NOT_APPLICABLE` if no tagged chains exist (`src/validator/checks/reading.py:473`), and then silently skips incomplete chains that lack either an overall or segment dimensions (`src/validator/checks/reading.py:479`). It groups by `chain_id` alone (`src/validator/checks/reading.py:465`), not by `(chain_id, axis)`, so mixed X/Y chains can be accidentally combined if ids collide.

The schema currently makes all P1a fields optional: `text_verbatim`, `value_m`, `chain_id`, `role`, and `order` (`src/agent/reading/schema.py:62`, `src/agent/reading/schema.py:67`). A1 must therefore require chain completeness, not just chain ids:

- dimensioned view must have dimensions when the fixture/profile says dimensions are visible;
- new, non-legacy dimensions must include `text_verbatim`, `value_m`, `chain_id`, `role`, and `order`;
- each closure group should be keyed by `(chain_id, axis)`;
- each closure group should contain at least one `overall` or equivalent baseline plus one or more ordered segment dimensions;
- incomplete chains should be evidence debt, not a silent pass.

This matters because a self-consistent wrong digit still closes. The current tests already encode that limitation: a "self_consistent_wrong_dimension" chain passes because arithmetic closure is not semantic truth (`tests/test_checks_reading_correction.py:355`). A1 should say closure turns many silent misreads into detectable failures, not all misreads.

### MAJOR 1 - A3's flag/block-by-profile needs a real run-intent carrier

The plan's ruling is sound: syntax invalid always blocks; evidence incomplete flags in exploratory/dev and blocks in golden/regression (`AI_agent/proposals/reading_evolution_dual_channel_cv.md:81`). But the current code only has `RunPolicy.capability_profile`, not a run intent or evidence policy (`src/agent/execution/policy.py:33`). `validate_case` passes only that capability profile into reading checks (`src/agent/execution/validation_run.py:78`, `src/agent/execution/validation_run.py:113`), and `disposition()` accepts `capability_profile` but does not use it to change outcomes (`src/validator/checks/schema.py:83`).

Minimal addition: add either `RunPolicy.evidence_policy: Literal["flag", "block"]` or `RunPolicy.run_profile: Literal["exploratory", "dev", "golden", "regression"]` with a deterministic mapping to evidence disposition. Thread it through `validate_case`, `run_stage`, `record_baseline`, and report rendering. Relying on `capability_profile="rectangular"` to mean golden/regression would overload a geometry capability as a quality policy.

### MAJOR 2 - A3's four signals need report/baseline plumbing, not just check text

The proposed split maps cleanly at the concept level:

- `0_reading syntax-valid`: invariant/schema parse and well-formedness failures;
- `0_reading evidence-clean`: dimension/provenance/raw-field evidence checks;
- `J0 semantic-clean`: judge attempt verdicts;
- `pipeline-recovered`: downstream correction/audit/recovery state.

But the current data path only rolls checks into pass/flag/block/n/a. `CheckReport.blocking()` and `flagged()` expose dispositions, not signal categories (`src/validator/checks/schema.py:158`, `src/validator/checks/schema.py:166`). `summarize_gates()` aggregates statuses into pass/flag/block buckets (`src/agent/execution/orchestrate.py:66`). Report assembly indexes only blocking and flagged entries (`scripts/tool_scripts/report_assembly.py:301`), while the user-facing facts card is mainly rendered in `record_baseline.py`, not `report_assembly.py` (`scripts/tool_scripts/record_baseline.py:504`).

The implementation should add machine-readable signal fields or a stable check-id allowlist for evidence checks. Otherwise reports will keep saying "0_reading pass" while an evidence-clean sub-signal is red, recreating the old ambiguity.

### MAJOR 3 - Golden/regression baseline impact is larger than the plan says

The plan says Phase A is image-blind and "basically no re-record" while also acknowledging golden expectations may need refresh (`AI_agent/proposals/reading_evolution_dual_channel_cv.md:58`, `AI_agent/proposals/reading_evolution_dual_channel_cv.md:87`). Current golden artifacts show that several Phase A gates will immediately change results if run in block mode.

For the sm21 opus golden, strokes lack provenance/dimension refs in the raw reading (`case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/0_reading/1f_view.json:11`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/0_reading/1f_view.json:122`), dimensions are legacy text-only with no P1a chain fields (`case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/0_reading/1f_view.json:193`), and the current check report treats closure as not applicable (`case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/0_reading/1f_view_checks.json:83`). The baseline currently records `0_reading` as 58 pass, 0 flag, 0 block, 14 n/a (`case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/_run/baseline.json:17`).

The spec should explicitly call out that A1, A4, A5, and A7 will change golden baseline expectations unless legacy artifacts are grandfathered by profile. That is not a blocker for Phase A, but it must be planned rather than discovered during re-record.

### MAJOR 4 - A6 is feasible, but the evidence sources in the plan are partly not present

Extending `_stroke_dimension_consistency` is the right hook. It already builds dimension-chain positions and checks whether visual perimeter walls align with dimension cumulative positions (`src/validator/checks/reading.py:497`, `src/validator/checks/reading.py:530`, `src/validator/checks/reading.py:540`). It also already computes wall-join evidence (`src/validator/checks/reading.py:697`).

However, the A6 wording lists independent evidence that the current plan-view schema/checker does not carry in a direct way: `wall_fill`, thickness, and cross-layer consistency (`AI_agent/proposals/reading_evolution_dual_channel_cv.md:71`). The validator's legal pens are only basic stroke pens (`src/validator/checks/reading.py:27`), and the reading guide says plan walls should have `thickness_m: null` in this stage (`skills/intake_pipeline/0_reading/guide.md:73`). Cross-layer consistency is also not available inside `check_reading_view(view)` because it receives one view at a time (`src/validator/checks/reading.py:86`).

A6 should be scoped to evidence the reading JSON actually carries: window strokes with rect/line geometry, wall axis lines, wall-join evidence, and dimension-chain cumulative positions. If the plan wants cross-floor/cross-layer redundancy, that is a separate run-level check outside the per-view validator.

### MAJOR 5 - A8 needs deterministic routing, not only a correction prompt instruction

The correction schema already has an `unsupported` list (`src/agent/correction/schema.py:75`), and the prompt tells correction to log unresolved/unsafe cases (`src/agent/pipeline.py:298`). But `run_correction` builds its prompt from raw vector data, not from reading check evidence debt (`src/agent/pipeline.py:330`), and the correction checker currently audits correction coverage using corrections/conflicts rather than treating `unsupported` as a reroute/block signal (`src/validator/checks/correction.py:130`).

If A8 is implemented only as prose, it will be brittle. The minimal reliable mechanism is a deterministic preflight before correction or an explicit evidence-debt summary passed into correction. The spec also needs to choose whether missing required evidence stops before producing corrected geometry, or whether correction may emit geometry plus `unsupported` and let the orchestrator route to reread.

### MAJOR 6 - A2's "downgrade to estimated" is not validator behavior today

A2 is implementable as a validator gate: if a stroke claims `provenance="dimension_derived"`, `dimension_refs` must be non-empty and refer to existing dimension ids. The schema already has `provenance` and `dimension_refs` fields (`src/agent/reading/schema.py:43`, `src/agent/reading/schema.py:45`).

But "downgrade to `estimated`" is mutation/normalization, not validation. `check_reading_view()` returns checks and does not rewrite the view (`src/validator/checks/reading.py:86`). The spec should pick one of two mechanisms: either validators flag/block unresolved `dimension_derived`, or a separate normalizer/migration step rewrites provenance before checks. Do not hide that rewrite inside a check.

### MINOR 1 - A9's CLI is close, but `--json` is not a clean machine interface

`score_reading_vs_gt.py` already uses judge-side GT loading (`scripts/tool_scripts/score_reading_vs_gt.py:26`) and therefore fits the GT isolation discipline. But its `--json` mode still prints human-readable rows before the JSON summary (`scripts/tool_scripts/score_reading_vs_gt.py:98`). The regression harness should either add a pure JSON mode or parse the final JSON object deliberately. Keep this on the judge/test side; `reading_score.py` explicitly says it must not be imported by gate checks or stage executors (`src/agent/judge/reading_score.py:10`).

### MINOR 2 - A10's GT anchor wording should be corrected

The E/W sign decision is valid, but the plan's "sm21 gt E2/W1" wording should be tied to actual GT records. The sm21 GT has East Floor 2 windows (`case_tests/test_baseline/gt/sm21_anchor/gt.json:300`) and West Floor 2 windows (`case_tests/test_baseline/gt/sm21_anchor/gt.json:323`); West Floor 1 has zero windows (`case_tests/test_baseline/gt/sm21_anchor/gt.json:315`). Use those actual anchors in the test name/assertions to avoid encoding a nonexistent W1 window.

### MINOR 3 - Report implementation target is broader than `report_assembly.py`

The plan says report vocabulary work is in `report_assembly.py` (`AI_agent/proposals/reading_evolution_dual_channel_cv.md:87`), but baseline/report facts are rendered primarily in `scripts/tool_scripts/record_baseline.py:504`. `report_assembly.py` still matters for marked report aggregation (`scripts/tool_scripts/report_assembly.py:301`), but A3 will need changes in both paths plus whatever writes `baseline.json`.

## Per-Item Review

### A1 - Activate dimension-chain closure

Feasible with changes. Touch `src/validator/checks/reading.py::_chain_closure`, `check_reading_view()`, and related tests. The current closure logic exists (`src/validator/checks/reading.py:459`) but treats missing chains as not applicable (`src/validator/checks/reading.py:473`). It should become an evidence check when the view is dimensioned.

Required spec change: A1 must require chain completeness and axis separation, not only `chain_id`. It should also document closure limitations: self-consistent wrong reads still pass, single-segment chains only help if an independent overall/baseline is present, and plan/elevation chains must not share ids across axes.

### A2 - Enforce `dimension_derived => dimension_refs`

Feasible. Touch `src/validator/checks/reading.py`, likely near `_stroke_dimension_consistency()` or a new provenance check. Build a set of dimension ids and flag/block strokes whose `dimension_refs` are empty or unresolved.

Mis-scope: the "downgrade estimated" branch requires either a normalization step or a writer change. The validator should not silently mutate evidence claims.

### A3 - Four-signal reporting and vocabulary

Feasible with plumbing. Touch `src/agent/execution/policy.py`, `src/agent/execution/validation_run.py`, `src/agent/execution/orchestrate.py`, `src/validator/checks/schema.py`, `scripts/tool_scripts/record_baseline.py`, and `scripts/tool_scripts/report_assembly.py`.

The existing `CheckStatus`/`CheckLayer` structure can carry most raw outcomes (`src/validator/checks/schema.py:39`, `src/validator/checks/schema.py:47`), but it does not distinguish evidence debt from advisory cross-checks. Add an evidence category, signal metadata, or a stable check-id grouping rather than deriving the four signals from prose.

### A4 - Dimensioned fixture requires dimensions and P1a fields

Feasible, but it needs a real fixture/profile source. `ReadingView.dimensions` defaults to an empty list (`src/agent/reading/schema.py:117`), so the validator needs to know whether empty dimensions are acceptable. Current testdata prompts list image paths and floors but do not declare which views are dimensioned (`case_tests/e2e_tests/sm21_anchor/case_data/testdata_prompt.json:7`).

Touch `check_reading_view()` and the run-policy/case metadata path. This does not require a reading schema rewrite because the fields already exist, but it does require policy or fixture metadata to say "dimensions visible here."

### A5 - Provenance coverage upgrade

Feasible. `_stroke_dimension_consistency()` already computes provenance coverage and emits `provenance_mode` as evidence, but currently always adds a pass (`src/validator/checks/reading.py:501`, `src/validator/checks/reading.py:519`). Change that to flag/block under regression/golden evidence policy when provenance is legacy or partial.

Be explicit about legacy artifacts. The legacy loader backfills fields and marks migrated views (`src/agent/reading/legacy.py:50`, `src/agent/reading/legacy.py:131`), so old fixtures can be loadable without being evidence-clean.

### A6 - Window-jamb cross-check

Feasible with narrower evidence. Plan-view window strokes exist in current readings, but there is no dedicated "jamb x" field; derive jamb positions from rect `x_range_m` / `y_range_m` or line endpoints. The existing validator can compare wall axis lines to dimension positions and wall joins (`src/validator/checks/reading.py:540`, `src/validator/checks/reading.py:697`).

Spec change: do not depend on unavailable `wall_fill`, thickness, or cross-layer consistency inside the per-view check. If using cross-layer evidence, make it a separate run-level check that receives multiple views.

### A7 - Raw legacy field presence

Feasible, but it needs raw metadata before Pydantic defaults. The schema defaults `uncaptured` to `[]` (`src/agent/reading/schema.py:122`), and legacy migration also inserts `uncaptured=[]` when the raw field is missing (`src/agent/reading/legacy.py:129`). After loading, absence and explicit empty are indistinguishable unless preserved.

Touch `src/agent/reading/legacy.py` or the validation loader to preserve `raw_has_dimensions`, `raw_has_uncaptured`, and `legacy_migrated` in check evidence. Prefer sidecar metadata over adding output fields unless the project wants those fields persisted.

### A8 - Correction emits unsupported/needs_reread

Feasible, but under-specified. Touch `src/agent/pipeline.py::run_correction`, `scripts/tool_scripts/run_stage.py` correction path, possibly `src/validator/checks/correction.py`, and orchestrator routing. `unsupported` exists in `CorrectedGeometry` (`src/agent/correction/schema.py:75`), but `needs_reread` is not a schema field today.

Recommended change: route required-evidence debt before correction in golden/regression, and pass a compact evidence-debt list into correction in exploratory/dev so it can emit `unsupported` deterministically. Define how `unsupported` affects the final verdict.

### A9 - Reading score harness

Feasible and correctly scoped to judge/test code. Touch `scripts/tool_scripts/score_reading_vs_gt.py`, the sm21 regression harness/tests, and possibly baseline recording. The scoring code already lives on the judge side and imports GT there (`src/agent/judge/reading_score.py:29`), which respects the isolation rule enforced by tests (`tests/test_gt_discipline.py:35`).

Add explicit thresholds using the old phase1 floor: 9/9 walls and 14/15 windows from the prior review (`AI_agent/logs/review/review/2026-06-30_reading_architecture_regression_review.md:24`).

### A10 - E/W sign test and facade constants

Feasible. `src/agent/correction/facade.py` currently sets East sign `-1` and West sign `+1` (`src/agent/correction/facade.py:34`, `src/agent/correction/facade.py:35`), while A1 says East should be `+1` and West `-1` (`skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:45`, `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:49`). The plan's decision matches Section 5 (`AI_agent/proposals/reading_evolution_dual_channel_cv.md:113`).

`derive_facade_frame` appears unwired in production; the known direct call sites are tests (`tests/test_checks_reading_correction.py:8`, `tests/test_checks_reading_correction.py:447`). Because it is dead code for the current pipeline, flipping the constants after a failing test is safe for current golden outputs. The test should assert East/West `to_world_along()` sign, not only axis/base, because the current East test does not catch sign (`tests/test_checks_reading_correction.py:447`).

## Direct Answers to Review Questions

### 1. Feasibility per A1-A10

All A1-A10 are implementable with reasonable effort. The items that need spec changes before execution are A1, A3, A4, A6, A7, and A8. None require rewriting the reading schema, but A3 requires run/report plumbing, A4 requires dimensioned-view metadata, A7 requires raw-load metadata, and A8 may require correction/orchestrator contract clarification.

### 2. Closure activation

Requiring `chain_id` alone does not reliably convert silent digit misreads into detectable failures. It only activates arithmetic checks when dimensions also have roles and there is both an overall and segments. It misses self-consistent wrong reads, incomplete chains, single-segment chains without independent overall dimensions, and any semantic error where the wrong chain still sums. Current `_chain_closure()` also groups by `chain_id` only, so plan/elevation or X/Y ids should be isolated before block mode is trusted (`src/validator/checks/reading.py:465`).

### 3. Flag/block-by-profile

There is no existing exploratory/golden/regression carrier. The closest object is `RunPolicy`, but it has `capability_profile`, not run intent (`src/agent/execution/policy.py:33`). Minimal addition: add an evidence policy to `RunPolicy` and propagate it to validation, baseline recording, and report rendering.

The four-signal split is conceptually clean, but not available as first-class report fields. Existing `CheckStatus`, `CheckLayer`, and `Disposition` can carry raw status (`src/validator/checks/schema.py:39`, `src/validator/checks/schema.py:53`), but the report needs new signal fields or stable check categories.

### 4. A6 jamb cross-check

`_stroke_dimension_consistency()` already covers the first half: it detects walls landing on dimension cumulative positions and records wall join evidence (`src/validator/checks/reading.py:540`, `src/validator/checks/reading.py:697`). Extending it to window-jamb redundancy is sound if jambs are derived from existing window stroke geometry. The reading JSON carries window strokes, not explicit jamb fields, so implementation must derive the coordinates from rect/line geometry and should avoid unavailable `wall_fill`/thickness inputs.

### 5. A10 E/W sign

Confirmed: `facade.py` has East/West signs opposite the A1 table (`src/agent/correction/facade.py:34`, `src/agent/correction/facade.py:35`; `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:45`, `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:49`). Confirmed: production wiring appears absent; direct code call sites are tests.

Test-first flip in Phase A is safe because the helper is currently unwired, and it prevents a known future trap. A GT anchor exists without violating isolation: use judge/test-side GT only, e.g. East Floor 2 and West Floor 2 window world positions in `case_tests/test_baseline/gt/sm21_anchor/gt.json:300` and `case_tests/test_baseline/gt/sm21_anchor/gt.json:323`. Do not import GT from gate/executor code; `reading_score.py` and `gt_discipline` already encode that boundary (`src/agent/judge/reading_score.py:10`, `tests/test_gt_discipline.py:35`).

### 6. Regression/golden impact

If golden runs use `block` for evidence debt, A1, A4, A5, and A7 will change existing sm21 golden baselines. The current opus golden has legacy dimensions, missing P1a chain fields, and missing top-level raw `uncaptured` evidence, while its baseline records no reading flags/blocks. Expect test updates around `tests/test_validation_run_baseline.py` sm21 expectations (`tests/test_validation_run_baseline.py:216`), gate summarization tests (`tests/test_orchestrate_baseline.py:142`), and report/baseline facts tests (`tests/test_orchestrate_baseline.py:224`).

Call out a golden re-record or explicit legacy grandfathering path before execution. Without that, a correct implementation will look like an accidental baseline break.

### 7. Sequencing

The proposed core batch A1/A2/A3/A4/A9 is close, but A3 policy plumbing should happen before block-mode A1/A4/A5 behavior. A7 should move into the core batch because A4/A5 need raw-field presence to distinguish legacy/defaulted clean from real clean. A8 should come after A1/A2/A4 define the evidence-debt facts. A6 can follow once the dimension/provenance helpers exist. A10 is independent and can be done early or late.

Recommended order:

1. A3 policy/signal plumbing.
2. A7 raw evidence metadata.
3. A1/A2/A4 evidence checks.
4. A5 provenance coverage promotion.
5. A9 scoring harness.
6. A6 jamb redundancy.
7. A8 correction routing.
8. A10 E/W test and constant flip.

### 8. Gaps Phase A should include

Phase A should explicitly add:

- dimensioned-view metadata source, either case manifest or `RunPolicy`, because current case prompts do not declare dimensions visible;
- chain completeness rules, including `(chain_id, axis)` grouping and required overall/segment roles;
- machine-readable evidence categories for report signals;
- a fixture for "chain_id present but missing role/overall" because that currently passes too easily;
- pure machine-readable output or parser behavior for `score_reading_vs_gt.py --json`;
- explicit correction routing semantics for `unsupported` and `needs_reread`.

## Final Recommendation

Approve Phase A after revising the spec around the blocker and major findings above. The plan does not wrongly foreclose Phase B/C: it keeps schema-level dual-channel changes and CV/OCR out of this round as intended (`AI_agent/proposals/reading_evolution_dual_channel_cv.md:91`, `AI_agent/proposals/reading_evolution_dual_channel_cv.md:102`). The main risk is not future scope; it is under-specifying the Phase A gates so they appear hardened while still allowing missing or incomplete evidence to pass as clean.
