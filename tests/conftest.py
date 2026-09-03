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
