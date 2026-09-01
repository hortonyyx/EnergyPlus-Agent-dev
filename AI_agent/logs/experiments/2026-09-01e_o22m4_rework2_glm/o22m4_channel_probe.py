"""Channel-inventory probe for the o22m4 rework-2 execution report (GLM seat).

Loaded EXPLICITLY via::

    O22M4_PROBE_LOG=<log> PYTHONPATH=<this dir> \\
        python -m pytest tests/test_o22m4_wall_compiler.py \\
            tests/test_o22m3_evidence_adapters.py -q -n 6 \\
            -p o22m4_channel_probe

It wraps the FOUR per-kind compiler entry points of
``src.agent.correction.wall_compiler`` with call counters and appends one
short line per real invocation to the probe log (xdist-safe: one O_APPEND
write per call, lines far below PIPE_BUF).  The production source is never
touched -- this file lives outside ``src/`` and outside the compiler
module, so the module-4 source-scan lock (``open(`` etc. banned inside
``wall_compiler.py``) cannot fire, unlike the reviewer's first inline
probe attempt on 2026-09-01.

Process-safety: each xdist worker imports this plugin and patches its own
process's module attributes; counts are merged by ``sort | uniq -c`` after
the run, mirroring the cross-review's own methodology.
"""
import os

from src.agent.correction import wall_compiler as _wc

_LOG = os.environ.get("O22M4_PROBE_LOG")
_ENTRY_POINTS = (
    "_compile_paired",
    "_compile_solid_band",
    "_compile_single_face",
    "_compile_legacy_trace",
)


def _wrap(name: str, fn):
    def counted(*args, **kwargs):
        if _LOG:
            with open(_LOG, "a", encoding="utf-8") as fh:
                fh.write(name + "\n")
        return fn(*args, **kwargs)

    return counted


for _name in _ENTRY_POINTS:
    setattr(_wc, _name, _wrap(_name, getattr(_wc, _name)))
