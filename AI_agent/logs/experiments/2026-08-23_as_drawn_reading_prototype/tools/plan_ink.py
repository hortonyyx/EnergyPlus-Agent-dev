"""[RETIRED 2026-08-25 · debt D-1] Forwarding shim -- no logic lives here.

The implementation moved to ``src/agent/reading/as_drawn/_plan_ink.py`` when the
toolbox was transplanted into src (toolbox_into_src_08.25).  This file stays so
every historical path into the 2026-08-23 experiment keeps working (``from
plan_ink import ...`` in the neighbouring tools, path-based loads) while
carrying no code of its own -- the two copies can no longer drift apart because
only one copy exists.  Do not add code here; import the src module instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[5])
if _root not in sys.path:
    sys.path.insert(0, _root)
del sys, Path, _root

import src.agent.reading.as_drawn._plan_ink as _impl  # noqa: E402

for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value
