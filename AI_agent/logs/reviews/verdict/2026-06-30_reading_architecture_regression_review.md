# 0_reading Architecture Regression Review

Date: 2026-06-30  
Verdict: **REWORK 0_reading evidence gates before treating current 0-5 runs as reading-clean**

Review ask: current 0-5 architecture has visibly weaker `0_reading` than the old `smalloffice_21_pre` phase1/phase2 flow. Investigate whether reading constraints were moved into correction and whether that weakened reading behavior.

Top-line finding: the regression is real. The old `smalloffice_21_pre/phase1` reading is a much stronger baseline than later current-architecture sm21 readings. The current architecture correctly keeps world placement and cross-image reconciliation out of `0_reading`, but it did not leave enough hard evidence-completeness gates in `0_reading`. As a result, `1_correction` often rescues weak or missing reading evidence, and "pipeline green" can hide "reading weak".

Counts: **BLOCKER 4 / MAJOR 4 / FOLLOW-UP 4**

## Evidence Summary

Local scoring command used:

```bash
python scripts/tool_scripts/score_reading_vs_gt.py <reading_dir> --case sm21_anchor --json
```

Observed sm21 plan geometry scores:

| Reading artifact | Walls | Windows | Notes |
| --- | ---: | ---: | --- |
| `case_tests/e2e_tests/smalloffice_21_pre/phase1` | 9/9 | 14/15 | Old phase1 reading baseline; only missed W facade F2 window in the scoring view. |
| `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_sonnet_reading/0_reading` | 9/9 | 12/15 | 1F south windows degraded; extra walls at x=3.44, 7.56, 11.56 and 2F extra x=5.51. |
| `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/0_reading` | 5/9 | 11/15 | Quarantined at `0_reading`; 1F pseudo-wall and 2F wall misses. |
| `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading` | 9/9 | 10/15 | Structurally green but dimension evidence is absent in at least `1f_view.json`. |

Key source anchors:

- Current project terminology and 0-5 ownership: `AI_agent/CLAUDE.md:8`, `AI_agent/CLAUDE.md:55`.
- Current reading guide says two-channel discipline and image-local facade only: `skills/intake_pipeline/0_reading/guide.md:67`, `skills/intake_pipeline/0_reading/guide.md:94`.
- P1a dimension-chain fields are documented in the guide: `skills/intake_pipeline/0_reading/guide.md:207`, `skills/intake_pipeline/0_reading/guide.md:217`.
- P1a fields are optional in schema: `src/agent/reading/schema.py:62`, `src/agent/reading/schema.py:67`.
- Missing `chain_id` makes chain closure `not_applicable`: `src/validator/checks/reading.py:474`.
- Current run report confirms Sonnet quarantine while gate1 stayed all pass/no flag/no block: `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/report/REPORT.md:29`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/report/REPORT.md:81`.

## Findings

### BLOCKER 1 - `0_reading` no longer enforces dimension evidence completeness

Evidence:
- The guide requires explicit P1a dimension chains: `text_verbatim`, `value_m`, `chain_id`, `role`, `order`: `skills/intake_pipeline/0_reading/guide.md:207`, `skills/intake_pipeline/0_reading/guide.md:217`.
- The schema still allows those fields to be absent: `src/agent/reading/schema.py:62`, `src/agent/reading/schema.py:67`.
- `dimensions` defaults to an empty list: `src/agent/reading/schema.py:117`.
- The validator treats missing `chain_id` as `not_applicable`, not as a weak-reading signal: `src/validator/checks/reading.py:474`.
- In `run_2026-06-20_gpt54_reading/0_reading/1f_view.json`, a direct read shows `has_dimensions=False`, `dimensions_len=0`, `strokes_len=17`.
- The corresponding J0 criterion "number copied wrong" still passed: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/attempts/002/judge.json:21`.
- The corresponding deterministic check says `reading.dimension_chain_closure = not_applicable`, not flag/block: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/1f_view_checks.json:83`.

Why this blocks:
- A dimensioned architectural drawing with no `dimensions[]` is not a clean reading; it is an incomplete evidence channel.
- Correction can only make reliable image-blind choices if the redundant channel survives. Missing dimensions force correction into fallback/priors, which is exactly the "correction rescued reading" pattern the architecture was meant to make visible.

Recommendation:
- Add a reading-side evidence gate for dimensioned views: if visible dimensions are expected for the fixture/run profile, `dimensions[]` must be non-empty.
- For non-legacy new readings, require `text_verbatim`, `value_m`, `chain_id`, `role`, and `order` on dimensions.
- Treat "no chain_id-tagged dimensions" as `flag` or fixture-gated `block` when a drawing has visible dimension chains.
- Keep legacy migration loadable, but do not let legacy mode count as clean for regression runs.

### BLOCKER 2 - `dimension_derived` is documented as strict, but not enforced as strict

Evidence:
- The guide says `dimension_derived` requires non-empty `dimension_refs`: `skills/intake_pipeline/0_reading/guide.md:140`, `skills/intake_pipeline/0_reading/guide.md:199`, `skills/intake_pipeline/0_reading/guide.md:371`.
- The current validator reports provenance coverage and stroke/dimension consistency, but provenance mode is an evidence field and missing chain positions become `not_applicable`: `src/validator/checks/reading.py:498`, `src/validator/checks/reading.py:536`.
- The Sonnet quarantine report explicitly attributes the failure to strokes being treated as `dimension_derived` around tick/window boundaries: `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/report/REPORT.md:81`.

Why this blocks:
- The whole "reading-honest" design depends on distinguishing visual strokes from numeric dimension-derived reconstruction.
- If `dimension_derived` can be emitted without strong refs, correction receives a claim that looks more authoritative than it is.

Recommendation:
- Enforce `provenance="dimension_derived" => dimension_refs non-empty`.
- If referenced dimensions do not exist or lack P1a fields, downgrade to `estimated` or flag/block the reading depending on case profile.
- Add a deterministic check that reports counts by provenance mode and treats `legacy` / `partial` provenance as non-clean in sm21 regression.

### BLOCKER 3 - Facade world-axis responsibility moved to correction, but correction has an East/West sign conflict

Evidence:
- Current reading guide intentionally says elevation orientation is image-local and must not state world axis/sign/base: `skills/intake_pipeline/0_reading/guide.md:94`, `skills/intake_pipeline/0_reading/guide.md:323`.
- Correction A1 says East local-x maps to world y increasing north, and West maps to world y increasing south: `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:45`, `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:49`.
- Old `smalloffice_21_pre` phase1 summary agrees with A1: East `local x = world y`, West `local x = -world y`: `case_tests/e2e_tests/smalloffice_21_pre/phase1/phase1_summary.md:37`, `case_tests/e2e_tests/smalloffice_21_pre/phase1/phase1_summary.md:38`.
- Current code disagrees: `src/agent/correction/facade.py:34` maps East with sign `-1`, and `src/agent/correction/facade.py:35` maps West with sign `+1`.

Why this blocks:
- Moving world placement out of reading is architecturally correct only if correction has a single tested canonical transform.
- The sign mismatch means a formerly explicit phase1 contract was moved downstream but not locked by code/docs/tests.

Recommendation:
- Choose one convention and make docs, code, and old baseline interpretation agree.
- If keeping the old/A1 convention, East should map local 0->south/low y and increasing local-x -> north/high y; West should map local 0->north/high y and increasing local-x -> south/low y.
- Add focused tests for East and West `to_world_along()` sign, not only facade axis/base.

### BLOCKER 4 - Current gate1 can be all green while reading is semantically wrong

Evidence:
- Sonnet run: `0_reading` gate1 was `58 pass / 0 flag / 0 block / 14 n/a`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/report/REPORT.md:29`.
- The same run quarantined at `0_reading`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/report/REPORT.md:9`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/report/REPORT.md:45`.
- Report diagnosis says every attempt's structural linter passed while J0 caught over-segmentation and pseudo-wall errors: `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/report/REPORT.md:81`.

Why this blocks:
- It is acceptable that a deterministic linter cannot see the image and needs J0 for semantic mistakes.
- It is not acceptable that missing evidence, missing chains, legacy provenance, and dimension-derived-without-refs are also treated as clean or not applicable. Those are structural evidence issues, not purely semantic image issues.

Recommendation:
- Split gate1 into "syntax-valid" and "evidence-clean" signals.
- Keep syntax failures hard block.
- Make evidence debt visible as flag/block according to fixture profile, so reports cannot say `0_reading` was clean when the reading omitted core evidence.

### MAJOR 1 - Current kickoff is too indirect for weak VLMs compared with old phase1

Evidence:
- Old phase1 prompt put concrete rules directly in the kickoff: core discipline begins at `case_tests/e2e_tests/smalloffice_20/phase1_prompt.md:43`.
- It explicitly listed plan/elevation pen separation, per-floor `wall_fill`, no topology fields, facade sign note, and OCR verbatim: `case_tests/e2e_tests/smalloffice_20/phase1_prompt.md:47`, `case_tests/e2e_tests/smalloffice_20/phase1_prompt.md:49`, `case_tests/e2e_tests/smalloffice_20/phase1_prompt.md:54`, `case_tests/e2e_tests/smalloffice_20/phase1_prompt.md:55`.
- Current session kickoff is intentionally an index/pointer document rather than a full restatement: `skills/intake_pipeline/0_reading/session_kickoff.md:24`.

Impact:
- The current docs are cleaner and less duplicated, but weaker models often follow the first prompt more than a long linked guide.
- This likely contributes to the observed difference between old phase1 and current runs.

Recommendation:
- Add a short generated "execution checklist" to `session_kickoff.md` with the non-negotiable output obligations, especially dimensions/provenance/door-vs-window/wall-vs-tick.
- Keep the detailed source of truth in `guide.md`, but do not rely on pointers alone for weak VLM execution.

### MAJOR 2 - Correction is being used as rescue, not just normalization

Evidence:
- `run_2026-06-23_gpt54mini_reading` completed, but the report calls it a recovery-chain success, not an error-free run; it needed six corrections and still had two non-blocking defects: `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading/report/REPORT.md:55`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading/report/REPORT.md:74`.
- One defect was footprint shrink to `14.8 x 7.8` because the elevation JSON lacked structured total dimensions: `case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading/report/REPORT.md:74`.
- `run_2026-06-20_gpt54_reading` reported `corrections=36, conflicts=2`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/report/REPORT.md:55`.

Impact:
- End-to-end success can mask reading weakness.
- It also confuses ownership: a downstream correction audit may look busy and capable, while the real issue is `0_reading` failing to preserve evidence.

Recommendation:
- Reports should distinguish `0_reading evidence-clean` from `pipeline recovered`.
- Correction should emit `unsupported` / `needs_reread` when required reading evidence is absent for a dimensioned drawing, instead of silently falling back to priors.

### MAJOR 3 - Legacy migration makes absence look intentional

Evidence:
- Legacy migration backfills `value_m` and `text_verbatim` from old `text`: `src/agent/reading/legacy.py:50`, `src/agent/reading/legacy.py:52`.
- If `uncaptured` is missing, legacy migration sets it to `[]`: `src/agent/reading/legacy.py:129`.
- Schema also defaults `uncaptured` to `[]`: `src/agent/reading/schema.py:122`.

Impact:
- A raw missing field can become indistinguishable from an explicit clean empty list after loading.
- This is friendly for backward compatibility but weak for regression gating.

Recommendation:
- Preserve raw-field presence in check evidence, e.g. `raw_has_uncaptured`, `raw_has_dimensions`, `legacy_migrated`.
- In regression runs, fail or flag "defaulted clean" when a required evidence carrier was missing in raw JSON.

### MAJOR 4 - Old world-axis summary was operationally useful even if it should not live in reading now

Evidence:
- Old `smalloffice_21_pre/phase1_summary.md` included a four-facade local/world table: `case_tests/e2e_tests/smalloffice_21_pre/phase1/phase1_summary.md:35`, `case_tests/e2e_tests/smalloffice_21_pre/phase1/phase1_summary.md:38`.
- Current architecture intentionally moves this responsibility to correction: `skills/intake_pipeline/0_reading/guide.md:94`.

Impact:
- Removing world placement from reading is right for stage separation.
- But the old summary gave correction/humans a strong cross-check. The new architecture needs an equivalent deterministic artifact in `1_correction`, with tests and audit.

Recommendation:
- Generate and persist a correction-side facade transform table per run.
- Include source reading facade fields, resolved footprint bounds, local origin, sign, and rejected/ambiguous cases.
- Put that table in correction audit/report so reviewers do not need to reconstruct orientation mentally.

## Follow-up Work

1. Add `score_reading_vs_gt.py` into the sm21 reading regression harness. Treat `smalloffice_21_pre/phase1` as a regression floor, not a ceiling.

2. Re-run sm21 after `6.27_ReadingScaffoldFullRestore` with both reading scoring and report review. Current historical evidence shows the regression and current code gates remain weak, but the latest prompt/doc restoration still needs a fresh empirical score.

3. Add focused tests:
- Missing `dimensions[]` on dimensioned fixture is not clean.
- Dimensions without P1a chain fields are not clean for new readings.
- `dimension_derived` without resolvable `dimension_refs` flags/blocks.
- East and West facade sign conventions are asserted in code.
- Raw missing `uncaptured` is distinguishable from explicitly empty `uncaptured`.

4. Update reporting vocabulary:
- `0_reading syntax-valid`
- `0_reading evidence-clean`
- `J0 semantic-clean`
- `pipeline recovered`

This avoids calling a run clean just because correction and downstream geometry managed to recover.

## Review Ask For Claude

Please verify these before implementation:

1. Confirm the intended East/West convention. Current A1 docs + old phase1 summary disagree with `src/agent/correction/facade.py`.
2. Decide which profiles make dimension evidence mandatory. For sm21 regression, the answer should be "mandatory".
3. Decide whether evidence debt should be `flag` or `block` in normal exploratory runs; for golden/regression runs, prefer `block`.
4. Keep correction image-blind. The fix is not to give correction images; the fix is to make `0_reading` preserve enough evidence or request reread.
5. Do not judge the fix by EP success alone. Judge it by reading score, evidence-clean gate status, correction audit load, and final pipeline result.

## Bottom Line

The architecture split is sound: reading should stay image-local, correction should own world normalization, and J0 should own image-grounded semantic judging. The regression comes from an enforcement gap between prose and gates. The current `0_reading` docs ask for strong dual-channel evidence, but the schema/validator still accept weak or missing evidence as clean enough to proceed. Tighten evidence gates first; then correction can go back to being normalization and reconciliation instead of a quiet reading-repair layer.
