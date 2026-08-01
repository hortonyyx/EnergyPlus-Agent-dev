# 2026-08-01 reading unsupervised enablement — terra execution log

## W1 — standing calibration/measurement requirement

### Changed and why

- Updated only `skills/intake_pipeline/0_reading/session_kickoff.md`.
- The CV-tool bullet now states directly that clean vector CAD PNGs require deterministic probes before drawing.
- Added the first Non-negotiable: calibrate and measure before writing metre coordinates, with a pointer to `cv_toolbox.md` rather than copying its durable rules.
- The degraded-input exception remains a pointer to the toolbox robustness-profile exception.
- Before editing, backed up the touched skill file to
  `backup/Skill_history/2026-08-01_w1_calibrate_kickoff/session_kickoff.md`.

### Source traceability

- `cv_toolbox.md:3`: toolbox is used before semantic reading JSON on clean vector CAD PNGs and documents the degraded-input exception.
- `cv_toolbox.md:50`: calibrate before metre coordinates and use dimension-chain extension-line intersections or ticks.
- `cv_toolbox.md:54`: measure before drawing.

### Evidence commands and outputs

```text
$ python scripts/tool_scripts/affected_tests.py --changed skills/intake_pipeline/0_reading/session_kickoff.md
SCOPE: FULL
python -m pytest -p no:cacheprovider -q
跑测声明：受影响子集 = 全仓（依据 affected_tests.py --changed skills/intake_pipeline/0_reading/session_kickoff.md；原因：path is not a first-class Python file: skills/intake_pipeline/0_reading/session_kickoff.md）

$ git diff --check
(no output; clean)
```

The selected scope is full because a Markdown skill file is fail-closed; the one required full-suite run will be recorded at batch completion.

### Under-specified boundaries

None. Existing unrelated unstaged edits already touched this skill file's Workflow section; they were preserved and excluded from this slice's staged diff and commit.

## W3 — actionable probe-wrapper receipts

### Changed and why

- Added an exact, no-write `python tools/run_cv_probe.py --help` form. Its output includes full usage and directly copyable direct / request / batch examples.
- A bare known tool now names the mechanical repair (`--tool <name>`), and missing direct values state the required `--key <value>` form. The wrapper emits the same repairs when invoked without the hook.
- Every batch-envelope and batch-entry shape error now appends a minimal usable JSON template.
- Replayed shell denials now state an isolation-safe next action: remove a pipe and call the wrapper directly; use the pre-created `out/` / `requests/`; or use the existing allowlisted `ls case_data` instead of `find`.
- No general Bash access was added. The sole authorization addition is the exact three-token `python tools/run_cv_probe.py --help` form: it runs only the staged wrapper, accepts no path/value arguments, and writes nothing. `mkdir` remains denied because workspace construction already creates `out/` and `requests/`; `find` remains denied because `ls case_data` lists the copied inputs; pipes and redirections remain denied because they are shell-boundary syntax, not probe usability.

### Evidence commands and outputs

```text
$ python scripts/tool_scripts/affected_tests.py --changed src/agent/execution/isolation_templates/guard.py src/agent/execution/isolation_templates/run_cv_probe.py tests/test_isolation.py
SCOPE: SUBSET
python -m pytest -p no:cacheprovider -q tests/test_isolation.py
跑测声明：受影响子集 = tests/test_isolation.py（依据 affected_tests.py --changed src/agent/execution/isolation_templates/guard.py src/agent/execution/isolation_templates/run_cv_probe.py tests/test_isolation.py）

$ python -m pytest -p no:cacheprovider -q -n0 tests/test_isolation.py -k 'probe_help or probe_shape_receipts or missing_direct_value or wrapper_direct_shape or real_shell_denials'
10 passed, 192 deselected in 18.66s

$ python -m pytest -p no:cacheprovider -q tests/test_isolation.py
202 passed in 63.53s (0:01:03)

$ [temporary /tmp staging copy] remove the documented --batch example, then run --help and check for it
NEUTER: expected --batch usage assertion would fail
```

The focused locks cover the six groups of real 2026-08-01 denials: bare `px_m_calibrator`, `--help`, malformed batch envelope, malformed batch entry, pipe syntax, and `mkdir`/`find`. They also confirm the corrected `ls case_data` step is actually allowed. The temporary neuter was performed only in a `/tmp` copy of generated staging, never in the worktree.

### Under-specified boundaries

None. I chose not to authorize `mkdir` or `find`: the existing isolated workspace creates the only writable directories, and the manifest/copied `case_data` already supplies the discovery surface. This is a usability receipt improvement, not a permission expansion.

## W4 — run-level reading exam scope

### Changed and why

- Added the optional `reading_exam_scope` declaration to a run's `run_config.yaml`, with exactly `input_ids` and a non-empty `reason`. It contains no answer data.
- At provisioning, a declared scope is frozen into `_run/reading_exam_scope.json`, bound to the unchanged base view-manifest hash and to a canonical declaration hash. Subsequent removal, change, corruption, or mismatch fails verification/build/merge.
- Unscoped runs do not receive a new scope artifact or new binding keys; their manifests, isolation bindings, input inventory, and coverage result bytes retain their previous shape.
- A scoped formal isolation build copies and inventories only the declared images. Coverage continues to BLOCK a missing declared image, while every excluded view is recorded as `not_applicable` with its input id and `run_config.yaml:reading_exam_scope` source.
- Judge score bindings are materialized as a hash-valid in-memory subset at the consumer. The signed/read-only `judge_score_bindings.json` is not modified; denominator derivation consequently contains only the declared plan/elevation bindings.

### Evidence commands and outputs

```text
$ python scripts/tool_scripts/affected_tests.py --changed src/agent/execution/view_manifest.py src/agent/execution/isolation.py src/validator/checks/view_manifest.py src/agent/judge/score_inputs.py scripts/tool_scripts/run_stage.py tests/test_view_manifest_generator.py tests/test_isolation.py tests/test_reading_typed_scoring_slice1.py
SCOPE: SUBSET
python -m pytest -p no:cacheprovider -q [affected test list]
跑测声明：受影响子集 = [affected test list]（依据 affected_tests.py；该改变经 src/agent 枢纽传递，选中 100+ 个测试文件）

$ python -m pytest -p no:cacheprovider -q tests/test_view_manifest_generator.py tests/test_check_view_manifest_coverage.py tests/test_isolation.py tests/test_c2_b4b_score_inputs.py tests/test_reading_typed_scoring_slice1.py tests/test_run_stage_flow.py
305 passed, 11 warnings in 72.33s (0:01:12)

$ python -m pytest -p no:cacheprovider -q -n0 tests/test_isolation.py::test_formal_build_writes_binding_and_input_inventory tests/test_view_manifest_generator.py::test_run_level_exam_scope_is_frozen_without_changing_case_manifest tests/test_isolation.py::test_formal_scope_stages_only_declared_images_and_records_out_of_scope_views tests/test_reading_typed_scoring_slice1.py::test_score_binding_consumer_scope_shrinks_denominator_without_mutating_source_bindings
4 passed in 21.57s

$ [read-only sm24 identity inspection]
case_metadata_sha256=f2efff8614ce6ddce9f975e811435a4936720f37df72cda538e4cd0cf8656701
base_view_manifest_sha256=459513f1377496c2cf79c81f5ecc6860d90408e99053e609f46a977159847b8a
gt_content_sha256=dd32135d81b0ea6eb34aaaec1675840cc46090b0b8eb99c7b140a7a4afd479f2
```

The W4 tests use a temporary copy of `sm24_anchor` with the declared `[1f_view, South_view]` scope. They prove only those two PNGs reach staging; an absent in-scope `South_view` remains a coverage BLOCK; `East_view`, `North_view`, and `West_view` are explicit `not_applicable` scope records; and the consumer binding/denominator excludes the other elevations. The identity values above were read without modifying any case, GT, or historical run artifact.

### Under-specified boundaries

None. I selected `run_config.yaml` because it is already run-local orchestration metadata; freezing its narrow declaration under `_run/` prevents a live config edit from becoming an in-progress regrade. The scope is intentionally a consumer subset, not a rewritten case manifest or GT artifact.

### Delivery blocker

At the W4 commit boundary, `git commit -m "feat(reading): support frozen run exam scopes"` failed with:

```text
fatal: Unable to create '/workspaces/EnergyPlus-Agent-dev/.git/index.lock': File exists.
```

Read-only inspection found a zero-byte `.git/index.lock` with no owning Git process (`fuser` returned no PID). Removing a stale lock is a deletion, and this dispatch separately forbids deletion without authorization. W4 remains staged and uncommitted; the required final full-suite run and batch declaration are paused pending authorization to remove this explicit stale lock.

## W4 返工 r1

### Changed and why

- Added `resolve_frozen_reading_exam_scope(run_dir, base_manifest)` in `view_manifest.py` as the single read-only consumer of the frozen run scope. It distinguishes no declaration/no frozen artifact (unscoped), missing frozen artifact, missing declaration, corrupt frozen artifact, changed declaration, and a frozen artifact bound to another base manifest.
- `verify_view_manifest` now uses that resolver after it rebuilds and compares the on-disk manifest against case metadata. `run_stage.py` uses the same resolver for `0_reading` scoring, then narrows bindings only when it returns a scope.
- This removes the scorer's hard-coded repository case path. It does not construct or require a case directory, so unscoped scratch and `--base-dir` runs do not enter the case-rebuild gate during scoring.
- Added one direct resolver lock covering a valid frozen scope and the frozen-artifact-missing fail-closed path. No existing assertion or fixture was altered.

### Drift-gate reachability answer

- The on-disk-versus-rebuilt-case-manifest drift gate remains in `provision_view_manifest` whenever provisioning/re-provisioning occurs.
- It also remains in `cmd_judge` before judge-only replay (`verify_view_manifest(case_dir, run_dir)`).
- The typed scoring helper no longer performs that case-data rebuild; it validates only the frozen scope's binding to the already-loaded judge base manifest. This is intentional for the under-`--base-dir` scratch consumer path. No additional gate was added.

### Evidence commands and outputs

```text
$ python -m pytest -p no:cacheprovider -q -n0 tests/test_view_manifest_generator.py tests/test_c2_b4b_phase_d.py tests/test_reading_typed_scoring_slice1.py
74 passed in 34.44s

$ grep -n 'case_tests" / "e2e_tests"' scripts/tool_scripts/run_stage.py
(no output)

$ python scripts/tool_scripts/run_stage.py --base-dir /tmp/w4_rework_r1_base_dir judge sm24_anchor run_unscoped 0_reading --verdict .../verdict_001_0_reading.json
[0_reading] judge_pass  (attempts=1, accepted=1)

$ [temporary scoped sm24 run] provision, then invoke the real typed scorer
scope= ['1f_view', 'South_view']
consumer_subset= [['1f_view', 'South_view']]
score_artifact= score_vs_gt.json

$ [same temporary scoped run, frozen reading_exam_scope.json removed] judge ... 0_reading
✗ view manifest INVARIANT fail (judge-only path is read-only): reading exam scope invalid: reading exam scope drift: run_config.yaml declares a scope but the frozen scope artifact is missing

$ [four further temporary run copies] resolve frozen scope after each drift
config_changed: run_config.yaml declaration changed after this run was provisioned
declaration_removed: frozen scope exists but run_config.yaml has no reading_exam_scope declaration
frozen_corrupt: frozen scope artifact is corrupt
base_mismatch: frozen scope is bound to a different base view manifest

$ python -m pytest -n auto
2042 passed, 10 xfailed, 150 warnings in 291.89s (0:04:51)
```

Cells: A is covered by the existing real correction scorer path (the resolver is called only under `stage == "0_reading"`); B is the unscoped temporary `--base-dir` judge run above and the former b4b parity fixture; C is the scoped temporary real scorer invocation, which captured exactly the two declared IDs; D is the missing-frozen-artifact temporary run above. Existing scope tests also preserve changed-declaration drift, scoped staging, explicit out-of-scope checks, and denominator subset behavior.

The full-suite result is +14 green against the 2028-green baseline: W3's parameterized receipt locks, W4's three existing scope locks, and this one resolver lock; there are zero red tests.

Read-only identity and byte checks after the rework:

```text
case_metadata_sha256=f2efff8614ce6ddce9f975e811435a4936720f37df72cda538e4cd0cf8656701
base_view_manifest_sha256=459513f1377496c2cf79c81f5ecc6860d90408e99053e609f46a977159847b8a
gt_content_sha256=dd32135d81b0ea6eb34aaaec1675840cc46090b0b8eb99c7b140a7a4afd479f2
output.json=5a1b79f5782b4fcac7809284a3d862fbcc8592d1e8619a671ae736f4b39b659a
checks.json=680a6cdfab83389dbc4c4f253cad2257857221e64a253eac3bb1b461d37bd394
```

The three identity values equal the pre-rework values recorded above. The two unscoped sm24 artifact hashes equal `git show HEAD` for the same paths, so their bytes are unchanged.

### Under-specified boundaries

None. The only trade-off is the dispatch-recommended separation: case-manifest reconstruction stays at provisioning and `cmd_judge`, while scoring consumes the already-loaded base manifest plus the frozen scope. This avoids silently imposing a repository case layout on an explicitly supported `--base-dir` path.

## W4 返工 r2（补锁）

### Changed and why

- Removed the redundant `declaration_sha256` comparison from the frozen-scope resolver. The authenticated `content_sha256` covers that field, so the content comparison is the single complete drift guard.
- Added direct resolver locks for a removed declaration, a frozen scope bound to a different legal base manifest, and a corrupt frozen artifact.
- Added a real `0_reading` typed-scorer lock that provisions a temporary scoped sm24 run and captures the bindings passed to the scorer. It requires exactly `1f_view` and `South_view` without altering the signed source bindings.

### Neuter self-check

Each mutation ran only in a disposable `/tmp` repository copy with:
`python -m pytest -n auto -q tests/test_view_manifest_generator.py tests/test_isolation.py tests/test_c2_b4b_phase_d.py tests/test_reading_typed_scoring_slice1.py`.

| Lock | Removed guard | Red test | Collateral |
| --- | --- | --- | --- |
| L1 | frozen artifact + missing-declaration raise | `test_frozen_exam_scope_resolver_rejects_removed_declaration` | none (1 failed, 280 passed) |
| L4 | different-base-manifest raise | `test_frozen_exam_scope_resolver_rejects_other_base_manifest` | none (1 failed, 280 passed) |
| L6 | `content_sha256` mismatch raise | `test_run_level_exam_scope_is_frozen_without_changing_case_manifest` | none (1 failed, 280 passed) |
| L7 | corrupt-artifact exception wrapping | `test_frozen_exam_scope_resolver_rejects_corrupt_frozen_artifact` | none (1 failed, 280 passed) |
| L8 | scoped `select_score_view_bindings` consumer narrowing | `test_typed_reading_scorer_consumes_only_frozen_exam_scope_bindings` | none (1 failed, 280 passed) |

For L8, the unmodified scorer received `['1f_view', 'South_view']`; after removing the narrowing branch it received all five bindings, and only the new scorer-boundary test failed.

### Evidence

```text
$ python -m pytest -n auto
2046 passed, 10 xfailed, 150 warnings in 301.36s (0:05:01)

case_metadata_sha256=f2efff8614ce6ddce9f975e811435a4936720f37df72cda538e4cd0cf8656701
base_view_manifest_sha256=459513f1377496c2cf79c81f5ecc6860d90408e99053e609f46a977159847b8a
gt_content_sha256=dd32135d81b0ea6eb34aaaec1675840cc46090b0b8eb99c7b140a7a4afd479f2
```

The three identity values exactly match the r1 pre- and post-rework records above.

### Under-specified boundaries

None.

## GLM findings 窄修 r3

### Changed and why

- S-1: added `test_merge_rejects_reading_exam_scope_changed_since_build`. It builds a temporary scoped workspace, then changes the valid run declaration and rewrites its frozen scope before merge. The resolver therefore still accepts the current scope; merge must reject because the scope hash no longer matches the build binding.
- NIT-1: replaced the copied calibration syntax examples in `guard.py` and `run_cv_probe.py` with deliberately synthetic `px_a=12345`, `px_b=67890`, `value_m=12.345`, and `dimension_ref="example_span"` values. The wrapper copies are the same user-facing hints as the guard template, so they remain aligned without retaining a real building dimension.

### Neuter self-check

The mutation was made only in `/tmp/energyplus-glm-r3-neuter.1w82O3/repo`; the repository source guard was not altered. In that copy, removal of the four physical lines implementing the specified three-line merge-scope conditional produced:

| Lock | Removed guard | Red test | Collateral |
| --- | --- | --- | --- |
| S-1 | `binding[reading_exam_scope_sha256]` vs verified frozen-scope hash rejection | `test_merge_rejects_reading_exam_scope_changed_since_build` | none (1 failed, 244 passed) |

The unmodified affected subset was green: `python -m pytest -n auto tests/test_isolation.py tests/test_view_manifest_generator.py` = `245 passed`.

### Evidence

```text
$ rg -n -F -e '15.0' -e 'overall_width' src/agent/execution/isolation_templates/guard.py
(no output)

$ python -m pytest -n auto
2047 passed, 10 xfailed, 150 warnings in 309.69s (0:05:09)

case_metadata_sha256=f2efff8614ce6ddce9f975e811435a4936720f37df72cda538e4cd0cf8656701
base_view_manifest_sha256=459513f1377496c2cf79c81f5ecc6860d90408e99053e609f46a977159847b8a
gt_content_sha256=dd32135d81b0ea6eb34aaaec1675840cc46090b0b8eb99c7b140a7a4afd479f2
```

The three identities exactly match the r1/r2 records. No guard was loosened and the production merge gate is unchanged.

### Under-specified boundaries

None.
