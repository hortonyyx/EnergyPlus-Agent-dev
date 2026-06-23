# Review: Run Dir Tidy + Single REPORT.md

Verdict: **APPROVE-WITH-CHANGES**.

No algorithmic blocker. The `_run/` move is mechanical and the single `REPORT.md` marker merge is implementable. The changes below are guardrails for the executor so this does not become a brittle "mostly moved" layout or an ambiguous marker parser.

## Findings

1. **DISAGREE** - Do not implement `_run/` by only changing filename constants; it needs one shared path helper that also covers manifest filename overrides.

   Evidence: the proposal says `orchestration_state.json` is "改 1 处常量" (`AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:35`) and then says all readers should use `run_dir / RUN_META_DIR / <name>` (`AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:38`). The second sentence is the safe version. `RunManifest.load()` and `RunManifest.save()` currently join directly onto the run root (`src/agent/execution/manifest.py:124`, `src/agent/execution/manifest.py:130`), and `validate_case(write_reports=True)` writes the validation summary via the same save override (`src/agent/execution/validation_run.py:241`). State and approval also join directly onto the root (`src/agent/execution/step_orchestrator.py:497`, `src/agent/execution/step_orchestrator.py:524`, `src/agent/execution/approval.py:67`, `src/agent/execution/approval.py:73`).

   Concrete fix: add a small central helper, e.g. `RUN_META_DIR = "_run"` plus `run_meta_path(run_dir, name)` that creates the parent on writes. Route `RunManifest.load/save`, `GeometryApproval.load/save`, `load_state/update_state/mark_geometry_approved`, `record_baseline`, and report links/sources through it. Add tests proving `RunManifest.save(run_dir)` writes `_run/run_manifest.json`, `RunManifest.save(run_dir, filename="validation_manifest.json")` writes `_run/validation_manifest.json`, validation does not create/overwrite root `run_manifest.json`, and root stale files are not read when `_run/` exists.

2. **DISAGREE** - The marker merge fallback should fail closed on duplicate/nested/unclosed AGENT markers; silent best-effort preservation is too risky.

   Evidence: the proposal defines generated and agent markers (`AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:52`) and asks whether missing/duplicate/nested marker fallback is enough (`AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:62`). Current code has no marker parser yet; it only writes deterministic files and preserves `REPORT.md` create-if-absent (`scripts/tool_scripts/report_assembly.py:635`, `scripts/tool_scripts/report_assembly.py:648`).

   Concrete fix: parse only exact full-line markers for a fixed set of expected `AGENT` keys. Missing AGENT key can become the sentinel/placeholder with a warning. Duplicate, nested, reversed, or unclosed AGENT markers should abort before writing the merged report, or write a clearly named recovery copy and fail. Add regression tests for first run, rerun preservation, idempotent second rerun, deleted marker placeholder, duplicate marker failure, nested marker failure, and marker-like text inside generated payloads.

3. **DISAGREE** - The citation linter must lint the extracted AGENT recommendations block, not rediscover recommendations by scanning the whole merged Markdown.

   Evidence: the proposal says the linter should check "AGENT 建议区引用 vs `baseline.json.evidence_index`" (`AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:56`). Current linting finds an exact `## 建议` heading while scanning the entire report (`scripts/tool_scripts/report_assembly.py:400`, `scripts/tool_scripts/report_assembly.py:411`) and then treats any `###` under it as buckets (`scripts/tool_scripts/report_assembly.py:417`). That was acceptable with a simple authored skeleton; it is less precise once generated and authored regions live in one file.

   Concrete fix: after marker parsing, pass only `AGENT:recommendations` content to `lint_report_citations`, or make the linter take an already-extracted section. Unknown/stale evidence ids after a GEN refresh should fail; that is the right invalidation behavior. The failure message should name the stale id and the AGENT block, not silently drop or rewrite Agent prose.

4. **NIT** - Do not describe the merged file as an "airtight" facts/narrative separation; it is an auditable write-ownership separation.

   Evidence: the proposal says the honesty separation "仍守" because GEN is code-written and AGENT is authored (`AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:56`). That prevents accidental overwrites, but it does not prevent AGENT prose in the conclusion or attribution sections from contradicting generated numbers. Current citation enforcement only covers the recommendation mini-format (`scripts/tool_scripts/report_assembly.py:400`, `scripts/tool_scripts/report_assembly.py:497`).

   Concrete fix: keep generated verdict/model/gate/run-state facts at the top and in marked GEN blocks, but document `baseline.json` / GEN blocks as the numeric authority. Do not claim the linter proves all AGENT prose is semantically consistent; it only grounds actionable recommendations.

5. **NIT** - The committed artifact migration list is underspecified for the current golden anchors.

   Evidence: the proposal mentions "golden baseline + two committed run（gpt54/sonnet）" (`AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:39`). The baseline registry has two current golden anchors, `sm20_anchor/run_2026-06-15_baseline` and `sm21_anchor/run_2026-06-16_opus_e2e` (`case_tests/test_baseline/index.md:8`, `case_tests/test_baseline/index.md:9`), and validation tests still exercise the sm21 opus run as a positive baseline (`tests/test_validation_run_baseline.py:191`, `tests/test_validation_run_baseline.py:199`).

   Concrete fix: either migrate `_run/baseline.json` and `_run/validation_manifest.json` for all current registry/golden runs that still claim the active layout, or explicitly mark older root-level files as historical and update registry/docs/tests so the new contract is only asserted for the intended run set.

6. **NIT** - The model-config wording needs one cleanup while touching the docs.

   Evidence: the proposal's target layout keeps `llm.yaml` at the run root (`AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:21`, `AI_agent/logs/review/request/2026-06-23_rundir_tidy_single_report_proposal.md:23`), and `record_baseline` already reads `run_dir / "llm.yaml"` (`scripts/tool_scripts/record_baseline.py:38`, `scripts/tool_scripts/record_baseline.py:292`). But `new_case_guide` still has a later section saying `<case>/llm.yaml` (`AI_agent/guides/new_case_guide.md:216`).

   Concrete fix: update the guide/contracts to consistently say `<run>/llm.yaml` for run records, while leaving `scripts/run_full_pipeline.py` legacy per-case config behavior alone unless this follow-up intentionally changes that runner.

## Verified Notes

- `orchestration_state.json` executable reads/writes are centralized in `STATE_NAME` users; no separate runtime raw-string reader was found outside tests/docs/report source labels.
- `geometry_approval.json` relocation is safe for the digest-bound check if `GeometryApproval.load/save` and `is_approved()` use the shared `_run` path; the digest still binds `2_modelling/building_geometry.json`, `3_split_pairing/geometry_specs.md`, and the kernel check report, which must not move.
- `FACTS.md` appears machine-consumed only by tests/docs in the current tree; no runtime parser depends on it.
- `_run/` is not broadly ignored by `.gitignore`; the relevant existing ignore is only for generated `manual_review/geometry_viewer.html`.
- No downstream `run_full_pipeline`, graph, or cross-ref runtime consumer of these metadata files was found.
