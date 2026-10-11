# Offline checks

`python scripts/dev/check.py` runs the classified fast checks with zero pytest
workers. `--list` prints the static selection without collecting tests.

- `targeted tests/test_name.py`: current checks for a specific change; explicitly
  selected current node files are also allowed.
- `targeted --changed src/agent_runtime/budget.py`: import/path-based selection.
  An uncertain mapping falls back to current node checks, not archived evidence.
- `node`: fast checks plus explicitly classified current integration acceptance.
  Optional module checks remain targeted; this does not cover every historical or
  legacy feature. Add relevant targeted files when their interfaces change.
- `historical --archive-root D:/Sim-BIM-Agent/repo --cases-root D:/Sim-BIM-Agent/repo/case_tests`:
  optional archived experiments and case compatibility. This is not a promise that
  every superseded experiment remains compatible with today's implementation.

The small `check_groups.json` inventory classifies every test module by its
contract/dependencies. Do not classify by filename date or old project label.
Add new modules to it; default discovery reports missing classifications rather
than silently omitting them. Explicit new-file selection is permitted during
implementation. Some files retain targeted checks for optional legacy features.

The early `ep_no_billed_gate` remains installed in every scope. Live-model
checks still require separate explicit authorization; the check command does not
enable them. Mutation matrices belong to node/historical scopes.

Outputs go to `D:/Sim-BIM-Agent/cache/pytest/test-slim` by default, in a fresh
subdirectory per invocation. `TEMP`, `TMP`, basetemp and JUnit output share that
development cache; bytecode and pytest's repository cache are disabled. At most
two workers may be selected explicitly.

`fixtures/role_current` contains only the selected 17 original images and validated
plan/elevation artifacts needed for local geometry, orchestration and recovery.
It does not contain full runs, simulation results or model streams, and it does
not establish autonomous reading quality.

Retired one-off constraints include old source byte/AST equality, migration
configuration comparison pairs, fixed historical registry ordering, captured
parameter equality, and renderer source-vocabulary locks. Current timeout,
route/schema, budget, recovery and no-answer import boundaries remain checked.
