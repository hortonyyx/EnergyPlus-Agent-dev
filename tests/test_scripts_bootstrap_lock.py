"""F-94 A-case bootstrap lock (2026-08-25 dispatch: 2026-08-25_f94_bootstrap_dispatch.md).

Mechanism this guards: an editable install's ``.pth`` file
(``/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth``)
points at this repo's absolute path and gets appended to the END of
``sys.path`` on every Python start-up, regardless of cwd. A script under
``scripts/`` that is bare-run (``python scripts/foo.py``, NOT ``python -m``,
NOT pytest) from a *different* checkout of this repo (a worktree, a sibling
clone, a CI staging copy) will therefore silently resolve ``from src...``
imports against the MAIN tree instead of its own -- ``sys.path[0]`` (the
script's own directory) has no ``src`` package, so Python falls through to
the ``.pth``-injected main-tree entry. pytest itself is unaffected
(``pyproject.toml``'s ``pythonpath = ["."]`` inserts the *rootdir* --
i.e. whichever tree pytest was invoked from -- ahead of the ``.pth`` entry).

The fix (A-case, per the dispatch; B-case root-fix of the ``.pth`` mechanism
itself is registered as maintenance debt D-2 and is explicitly out of scope
here) is the same bootstrap idiom already used by the 6 scripts that had it
before this batch (``cv_probe.py``, ``build_judge_score_inputs.py``,
``run_stage.py``, ``score_reading_vs_gt.py``, ``spawn_isolated_reader.py``,
``run_pipeline_deepseek.py``)::

    _REPO_ROOT = Path(__file__).resolve().parents[N]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

placed textually BEFORE the first ``from src...`` / ``import src...`` line
(module-level or nested inside a function -- a deferred import is still
reachable without any prior bootstrap having run, unless the bootstrap
itself is unconditionally at module top level, which is what this lock
checks for).

This test is the ONLY thing standing between "A-case done" and "A-case
silently regresses the next time someone adds a script with a bare
``from src...`` import and forgets the bootstrap" -- per the dispatch's own
words, an unverified lock is worse than no lock (it manufactures false
confidence). See the dispatch for the mandated red/green two-stage proof:
this file must be run once against the pre-fix tree (git-stash the 16 fixed
scripts) to show it goes red and lists exactly the offending scripts, then
again post-fix to show green. Both outputs are pasted into the completion
report, not just asserted here.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"


def _iter_script_files() -> list[Path]:
    return sorted(
        p for p in SCRIPTS_ROOT.rglob("*.py") if "__pycache__" not in p.parts
    )


def _src_import_lines(tree: ast.AST) -> list[int]:
    """Line numbers of every ``from src...`` / ``import src...`` statement,
    at ANY nesting depth (module level, inside a function, inside a
    try/except -- a deferred import is exactly as vulnerable as an eager
    one, since nothing guarantees the bootstrap ran before the function is
    called from a bare-run entry point)."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module is not None and (
                node.module == "src" or node.module.startswith("src.")
            ):
                lines.append(node.lineno)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "src" or alias.name.startswith("src."):
                    lines.append(node.lineno)
    return lines


def _bootstrap_lines(tree: ast.AST) -> list[int]:
    """Line numbers of every module-level ``sys.path.insert(...)`` call.

    Deliberately restricted to statements that are direct children of the
    Module node (not nested inside a function/if/try) -- a bootstrap that
    only runs conditionally deep inside some other function's body does not
    protect a module-level (or even a differently-scoped function-level)
    ``from src...`` import that executes on a bare run before that function
    is ever called.
    """
    lines: list[int] = []
    for node in ast.iter_child_nodes(tree):
        candidates = [node]
        # sys.path.insert(...) is very commonly guarded by
        # `if str(X) not in sys.path:` -- walk one level into an `If` at
        # module scope so that guarded form still counts.
        if isinstance(node, ast.If):
            candidates = list(node.body)
        for stmt in candidates:
            if not isinstance(stmt, ast.Expr):
                continue
            call = stmt.value
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "insert"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "path"
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "sys"
            ):
                lines.append(stmt.lineno)
    return lines


def _unguarded_scripts() -> dict[str, list[int]]:
    """Map of {relative_posix_path: [offending src-import line numbers]}
    for every script that imports from ``src`` without a module-level
    bootstrap positioned before the earliest such import."""
    offenders: dict[str, list[int]] = {}
    for path in _iter_script_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        src_lines = _src_import_lines(tree)
        if not src_lines:
            continue
        boot_lines = _bootstrap_lines(tree)
        earliest_import = min(src_lines)
        if not boot_lines or min(boot_lines) > earliest_import:
            rel = path.relative_to(REPO_ROOT).as_posix()
            offenders[rel] = sorted(src_lines)
    return offenders


def test_all_scripts_with_src_imports_have_a_bootstrap():
    """Every ``scripts/**/*.py`` that imports ``from src...`` / ``import
    src...`` must sys.path-bootstrap the repo root BEFORE that import, so a
    bare `python scripts/.../foo.py` run from a non-main checkout resolves
    ``src`` to its OWN tree, not to whatever tree the editable-install
    ``.pth`` happens to point at.

    F-94 A-case (2026-08-25). If this goes red, the failure message names
    every offending script + line numbers -- fix by adding, immediately
    before its first ``from src`` / ``import src`` line:

        _REPO_ROOT = Path(__file__).resolve().parents[N]
        if str(_REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(_REPO_ROOT))

    (N = 1 for scripts directly under scripts/, 2 for scripts/tool_scripts/.)
    """
    offenders = _unguarded_scripts()
    assert not offenders, (
        "scripts import `src` without a preceding module-level "
        "sys.path bootstrap -- these will silently resolve `src` against "
        "whatever tree the editable-install .pth points at when bare-run "
        "from a non-main checkout (F-94 A-case). Offenders "
        "{path: [src-import line numbers]}:\n"
        f"{offenders!r}"
    )


def test_lock_has_discriminating_power_on_a_synthetic_offender(tmp_path):
    """Self-check for the scanner itself (not the repo): a script that
    imports `from src.x import y` with NO bootstrap must be caught, and one
    that bootstraps first must NOT be -- proves this lock isn't a
    vacuous/always-pass scan before trusting it against the real tree."""
    bad = tmp_path / "bad.py"
    bad.write_text("from src.agent import AgentState\n", encoding="utf-8")
    good = tmp_path / "good.py"
    good.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "_REPO_ROOT = Path(__file__).resolve().parents[1]\n"
        "if str(_REPO_ROOT) not in sys.path:\n"
        "    sys.path.insert(0, str(_REPO_ROOT))\n"
        "from src.agent import AgentState\n",
        encoding="utf-8",
    )
    deferred_bad = tmp_path / "deferred_bad.py"
    deferred_bad.write_text(
        "def f():\n"
        "    from src.agent import AgentState\n"
        "    return AgentState\n",
        encoding="utf-8",
    )

    def offenders_for(p: Path) -> list[int]:
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        src_lines = _src_import_lines(tree)
        boot_lines = _bootstrap_lines(tree)
        if not src_lines:
            return []
        if not boot_lines or min(boot_lines) > min(src_lines):
            return src_lines
        return []

    assert offenders_for(bad), "unbootstrapped `from src` must be flagged"
    assert not offenders_for(good), "bootstrapped `from src` must NOT be flagged"
    assert offenders_for(deferred_bad), (
        "a deferred (function-body) `from src` import with no module-level "
        "bootstrap anywhere in the file must still be flagged"
    )


if __name__ == "__main__":
    # Ad-hoc CLI for the red/green demonstration the dispatch requires,
    # independent of pytest's collection (so it can be run against a
    # `git stash`-reverted tree without pytest's own import machinery
    # getting in the way).
    result = _unguarded_scripts()
    if result:
        print(f"RED: {len(result)} offending script(s):")
        for rel, lines in sorted(result.items()):
            print(f"  {rel}  (src-import lines: {lines})")
    else:
        print("GREEN: no offending scripts.")
