"""Thin shim — the F-158 no-billed-calls gate now lives in the earliest-loaded
plugin ``ep_no_billed_gate`` (repo root), pinned first in ``pyproject.toml``
``addopts`` so it installs *before* any command-line ``-p`` plugin or initial
conftest can bind a pre-gate ``socket.connect`` reference (see that module's
docstring and verdict ``2026-09-03c_f158_crossreview_gpt`` B-1).

The gate's hooks, fixture and install all live in the plugin and must NOT be
duplicated here (that would double-fire them). This file only re-exports the
plugin's public names so existing ``from conftest import ...`` keeps working,
and importing it also guarantees the gate is installed even in the degraded case
where ``addopts`` did not load the plugin as ``-p``.
"""

from ep_no_billed_gate import (  # noqa: F401  (re-export for `from conftest import ...`)
    ProviderCallBlocked,
    _is_local,
)

# Fixture-only source copies for the old clean-room tests; no gate replacement.
from tests.isolation_source_fixture import (  # noqa: F401
    isolation_source_copy,
    separate_cleanroom_source,
)

# Classify before importing test modules: historical imports can depend on
# archive scripts that deliberately do not live in the product checkout.
import os
from pathlib import Path

import pytest

from tests.check_selection import GROUPS, ROOT, inventory, unclassified


def pytest_configure(config):
    for group in sorted(GROUPS):
        config.addinivalue_line("markers", f"{group}: classified offline check scope")


def _explicit_file(config, path):
    for argument in config.args:
        candidate = Path(str(argument).split("::", 1)[0])
        if not candidate.is_absolute():
            candidate = Path(config.invocation_params.dir) / candidate
        if candidate.suffix == ".py" and candidate.resolve() == path.resolve():
            return True
    return False


def pytest_sessionstart(session):
    scope = os.environ.get("SIM_BIM_TEST_SCOPE", "fast")
    if scope not in GROUPS:
        raise pytest.UsageError(f"unknown SIM_BIM_TEST_SCOPE: {scope}")
    for argument in session.config.args:
        candidate = Path(str(argument).split("::", 1)[0])
        if not candidate.is_absolute():
            candidate = Path(session.config.invocation_params.dir) / candidate
        if candidate.suffix != ".py":
            continue
        try:
            entry = inventory().get(candidate.resolve().relative_to(ROOT).as_posix())
        except ValueError:
            continue
        if entry and entry["group"] == "historical" and scope != "historical":
            raise pytest.UsageError("Historical checks require explicit archive opt-in: scripts/dev/check.py historical")
    if scope == "historical":
        for key in ("SIM_BIM_TEST_ARCHIVE_ROOT", "SIM_BIM_TEST_CASES_ROOT"):
            value = os.environ.get(key)
            if not value or not Path(value).is_absolute() or not Path(value).is_dir():
                raise pytest.UsageError(f"historical checks require an explicit existing absolute {key}")


def pytest_ignore_collect(collection_path, config):
    path = Path(str(collection_path))
    if not path.name.startswith("test_") or path.suffix != ".py":
        return None
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError:
        return None
    scope = os.environ.get("SIM_BIM_TEST_SCOPE", "fast")
    if scope not in GROUPS:
        raise pytest.UsageError(f"unknown SIM_BIM_TEST_SCOPE: {scope}")
    explicit = _explicit_file(config, path)
    entry = inventory().get(relative)
    if entry is None:
        if explicit:
            import warnings
            warnings.warn(f"Unclassified new test selected explicitly: {relative}; add it to tests/check_groups.json", pytest.PytestWarning)
            return False
        # Pytest also walks siblings while resolving an explicit node id. An
        # unrelated new file must not block a valid targeted check.
        if all(Path(str(arg).split("::", 1)[0]).suffix == ".py" for arg in config.args):
            return True
        raise pytest.UsageError(f"Unclassified test: {relative}; add it to tests/check_groups.json or select its file explicitly")
    group = entry["group"]
    if group == "historical":
        if explicit and scope != "historical":
            raise pytest.UsageError(f"{relative} is an optional historical check; use scripts/dev/check.py historical with explicit archive/cases roots")
        return scope != "historical"
    if explicit:
        return False
    if scope == "historical":
        return True
    if scope == "node":
        return group == "targeted"
    return scope == "fast" and group != "fast"


def pytest_collection_modifyitems(config, items):
    scope = os.environ.get("SIM_BIM_TEST_SCOPE", "fast")
    for item in items:
        path = Path(str(item.path))
        try:
            entry = inventory().get(path.relative_to(ROOT).as_posix())
        except ValueError:
            entry = None
        if entry:
            item.add_marker(getattr(pytest.mark, entry["group"]))
        if (scope not in {"node", "historical"} and item.get_closest_marker("mutation")
                and not _explicit_file(config, path)):
            item.add_marker(pytest.mark.skip(reason="mutation matrix belongs to node/historical checks"))


def pytest_report_header(config):
    scope = os.environ.get("SIM_BIM_TEST_SCOPE", "fast")
    return (f"Sim BIM check scope: {scope}; classified selection, not all test modules. "
            "Historical evidence requires explicit archive opt-in; fast excludes node/optional targeted checks. "
            "The no-billed-calls gate remains active.")


def pytest_terminal_summary(terminalreporter):
    scope = os.environ.get("SIM_BIM_TEST_SCOPE", "fast")
    terminalreporter.write_line(f"Coverage boundary: {scope} / explicitly selected modules only; "
                              "unselected node, optional targeted and historical modules are not covered.")
