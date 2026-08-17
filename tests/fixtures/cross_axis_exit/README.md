# C1 (cross-axis calibration disagreement) — pre-fix source snapshot

Byte-for-byte pre-fix copy of `src/agent/reading/cv_toolbox/tools.py`, used by
`tests/test_cross_axis_exit.py`'s neuter test to reproduce the ORIGINAL
`px_m_calibrator` behavior (a hard `raise ValueError("cross-axis calibration
disagreement: ...")` before ever blending `px_per_m`) against a real staging
tree + a real subprocess.

## Provenance

Captured directly from git history — **not** from any `backup/` directory —
via:

```
git show 16b247b:src/agent/reading/cv_toolbox/tools.py > tools_pre_fix.py
```

`16b247b` (`08.17_SubstrateSweep_docs_sync_and_crossreview_dispatch`) is the
parent commit of `0ae4b93` (`08.17_707repro_prereq_F51_singleframe_
scaleorigin_crossaxis_exit`), the commit that introduced C1 (and F-51 and the
`scale_origin` optionality change, in the same commit). `git diff 16b247b HEAD
-- src/agent/reading/cv_toolbox/tools.py` is the exact, complete diff this
fixture reverts.

This sidesteps the two problems the sibling fixture directory
(`tests/fixtures/substrate_fix_II/README.md`) documents for a `backup/`-based
capture: `backup/` is gitignored (`**/backup/**/20*_*/`) so it is absent on a
fresh clone (M-2), and hand-copying risks a stale or edited snapshot. Reading
straight out of git history has neither problem — the byte content is
whatever the named commit actually recorded, permanently.

## Where it is read

Only `tests/test_cross_axis_exit.py`'s `test_neuter_*` function, via a local
`_neuter_into_fresh_staging`-style helper mirroring
`tests/test_substrate_fix_tools.py::_neuter_into_fresh_staging` (see that
function's docstring for the full M-1 rationale: it builds a FRESH staging
tree from the repo's current, fixed source, then overwrites *only the staged
copy* of `tools.py` — never the real tracked file — with this fixture's
content, before running a real subprocess against that staging). The real,
tracked `src/agent/reading/cv_toolbox/tools.py` is never touched, so no other
parallel `pytest -n auto` worker building its own staging (or importing that
module directly) can ever observe a broken intermediate state.

## Regeneration

A frozen historical input, not an output the suite rebuilds. If C1 is ever
revisited (reworked or reverted), regenerate from whatever commit predates
that change:

```
git show <parent-of-the-revisiting-commit>:src/agent/reading/cv_toolbox/tools.py \
    > tests/fixtures/cross_axis_exit/tools_pre_fix.py
```

## Fail-closed

The neuter test reads this with `Path.read_text()` and additionally asserts
its content differs from the current real file's content — a missing or
accidentally-identical fixture raises (hard red / explicit `AssertionError`),
never a silent skip.
