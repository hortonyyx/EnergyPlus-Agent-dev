# Substrate fix batch II — pre-fix source snapshots

Byte-for-byte pre-fix copies of the four files `tests/test_substrate_fix_tools.py`'s
neuter tests reproduce the original F-52/F-54/F-58/F-53 crashes against. They used to
live only under `backup/{scripts,src,Skill}_history/2026-08-16_substrate_fix_II/`,
which `.gitignore`'s `**/backup/**/20*_*/` rule excludes from version control — so on
a fresh clone `test_f52_neuter_reverting_bbox_parser_reproduces_the_original_crash`
(and its three siblings) raised `FileNotFoundError` before ever reaching an assertion
(2026-08-17 cross-review finding M-2). Moving trimmed copies here makes the dependency
explicit and tracked; the `backup/` originals are untouched (they remain this repo's
ordinary "back up before editing" local safety copies, per `AI_agent/CLAUDE.md` §5#4).

## Layout

| file | pre-fix state of | real (fixed) counterpart |
|---|---|---|
| `f52_cv_probe_pre_fix.py` | `_bbox()`'s argparse type callable before F-52 | `scripts/tool_scripts/cv_probe.py` |
| `f54_run_cv_probe_pre_fix.py` | `main()` before F-54's try/except backstop | `src/agent/execution/isolation_templates/run_cv_probe.py` |
| `f58_tools_pre_fix.py` | `overlay_logger()` before F-58's shape validation | `src/agent/reading/cv_toolbox/tools.py` |
| `f53_cv_toolbox_pre_fix.md` | the doc's `--batch` example before F-53's placeholder fix | `skills/intake_pipeline/0_reading/cv_toolbox.md` |

Each is an untouched copy of the corresponding `backup/.../2026-08-16_substrate_fix_II/`
file captured by that batch before it edited anything — diffed byte-for-byte against
the `backup/` source at copy time (2026-08-17).

## Where they are read

Only `tests/test_substrate_fix_tools.py`'s four `test_*_neuter_*` functions, via
`_neuter_into_fresh_staging()`. Per M-1 of the same review, this helper never writes
to a repository file: it builds a staging tree from the repo's current (fixed) source
as normal, then overwrites *only the staged copy* of one of these four files with the
matching fixture's content (applying the same text substitution
`build_isolation_workspace` itself would have applied at copy time, where one exists —
see `_F52_PATH_REWRITE`) before running a subprocess against that staging. The real,
tracked source files are never touched, so nothing another `pytest -n auto` worker
building its own staging (or importing `src/agent/reading/cv_toolbox/tools.py`
directly) at the same moment can ever observe a broken intermediate state.

## Regeneration

These are frozen historical inputs, not outputs the suite rebuilds. If F-52/F-54/
F-58/F-53 are ever revisited (e.g. reworked or reverted), regenerate by copying the
then-current pre-change file — the same discipline the original `backup/` snapshots
were captured under.

## Fail-closed

`_neuter_into_fresh_staging()` reads these with `Path.read_text()` and additionally
asserts the fixture's content differs from the current real file's content — a missing
or accidentally-identical fixture raises (hard red / explicit `AssertionError`), never
a silent skip.
