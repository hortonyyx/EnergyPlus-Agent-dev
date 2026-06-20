"""Ground-truth (evaluation answer) loader — judge② side ONLY.

Per-case bundle `gt/<case>/` under `case_tests/test_baseline/gt/` holds all gt
content for a case together: `gt.json` (the EVALUATION answer key — true
zonification / per-facade window counts / dimension truth), the `source.dxf` it
was derived from, and `renders/`. The answer key is read ONLY by the gate② judge
(the main Agent's judging path). It must NEVER be read by:
  - gate① deterministic checks (`src/validator/checks/*`) — they ship to
    production, which has no answer key; depending on gt would make dev and prod
    behave differently;
  - stage executors (`src/agent/pipeline.py` run_correction / run_mep) — feeding
    the answer would collapse the error budget.

`tests/test_gt_discipline.py` mechanically enforces that those modules do not
import this one. See `case_tests/test_baseline/gt/README.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_GT_DIR = Path("case_tests/test_baseline/gt")


def gt_path(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> Path:
    return Path(gt_dir) / case / "gt.json"


def case_gt_dir(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> Path:
    """The per-case gt bundle dir holding gt.json + source.dxf + renders/."""
    return Path(gt_dir) / case


def has_gt(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> bool:
    return gt_path(case, gt_dir=gt_dir).exists()


def load_gt(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> dict | None:
    """Load the evaluation ground truth for a case, or None if absent.

    A judge with no gt simply judges against the original drawings + testdata
    (more subjective); gt makes the call objective. Returns the parsed dict."""
    p = gt_path(case, gt_dir=gt_dir)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
