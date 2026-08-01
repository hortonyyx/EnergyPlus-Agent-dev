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
