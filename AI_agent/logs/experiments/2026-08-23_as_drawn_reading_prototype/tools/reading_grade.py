"""[RETIRED 2026-08-25 · debt D-1] Forwarding shim -- no logic lives here.

The implementation moved to ``src/agent/judge/as_drawn/reading_grade.py`` when
the toolbox was transplanted into src (toolbox_into_src_08.25).  This file
stays so every historical path into the 2026-08-23 experiment keeps working --
notably the GLM cheat fixtures that load it as ``_load("reading_grade")`` and
the ``python3 tools/reading_grade.py doc den out [kw...]`` CLI -- while
carrying no code of its own -- the two copies can no longer drift apart
because only one copy exists.  Do not add code here; import the src module
instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[5])
if _root not in sys.path:
    sys.path.insert(0, _root)
del sys, Path, _root

import src.agent.judge.as_drawn.reading_grade as _impl  # noqa: E402

for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

if __name__ == "__main__":
    kw = {}
    for i, name in enumerate(("pos_tol", "span_min", "end_tol", "extra_min"), start=4):
        if len(sys.argv) > i:
            kw[{"pos_tol": "pos_tol", "span_min": "span_min",
                "end_tol": "end_tol", "extra_min": "extra_min"}[name]
               + ("_m" if name != "span_min" else "")] = float(sys.argv[i])
    raise SystemExit(_impl.main(sys.argv[1], sys.argv[2], sys.argv[3], **kw))
