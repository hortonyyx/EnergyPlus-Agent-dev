"""gt is judge-only: loader works, and gate① / executors must NOT import it.

The discipline (gt/README.md): the evaluation answer key may only be read by the
gate② judge. gate① ships to prod (no answers) and executors must stay blind, so
they must not depend on src.agent.judge.gt. This test mechanically enforces it by
scanning those modules' source for any gt reference.
"""

from __future__ import annotations


from pathlib import Path
import inspect

from src.agent.judge import gt_render_model

from src.agent.judge.gt import has_gt, load_gt




def test_gt_loader_absent_returns_none(tmp_path):
    assert load_gt("does_not_exist", gt_dir=tmp_path) is None
    assert has_gt("does_not_exist", gt_dir=tmp_path) is False


# --------------------------------------------------------------------------- #
# discipline: gate① + executors must not import gt
# --------------------------------------------------------------------------- #
# opus §8.5: the tarch converter (judge-side answer generator) and its CLIs must
# not be imported by gate① or executor runtime — Tianzheng dialect stays judge-side.
_FORBIDDEN = ("judge.gt", "judge import gt", "load_gt", "test_baseline/gt", "gt.json", "/gt/",
              "tarch_converter", "tarch_normalize", "normalize_tarch_dxf", "tarch_to_gtv3")


def _scan(paths: list[Path]) -> list[str]:
    hits = []
    for p in paths:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for token in _FORBIDDEN:
            if token in text:
                hits.append(f"{p}: contains '{token}'")
    return hits


def test_gate1_checks_do_not_reference_gt():
    checks = list(Path("src/validator/checks").glob("*.py"))
    assert checks  # sanity
    hits = _scan(checks)
    assert not hits, f"gate① must not reference gt: {hits}"


def test_executors_do_not_reference_gt():
    executors = [Path("src/agent/legacy/pipeline.py")]
    executors.extend(sorted(Path("src/agent/execution").rglob("*.py")))
    executors.extend(sorted(Path("src/agent/correction").rglob("*.py")))
    executors.extend(sorted(Path("src/agent/reading").rglob("*.py")))
    executors.append(Path("scripts/tool_scripts/cv_probe.py"))
    hits = _scan(executors)
    assert not hits, f"executors / gate① capstone must not reference gt: {hits}"


def test_pipeline_import_closure_excludes_gt_and_as_drawn_judge():
    """⭐ 2026-08-25 (as-drawn toolbox transplant, dispatch §四): a BEHAVIOURAL
    companion to the lexical scans above, added for the same reason those scans
    exist rather than a single one -- this repo has been bitten repeatedly by
    lexical matching over unbounded text (worklog: F-49 -> F-60 -> N-1/N-2 ->
    F-61 -> F-62), and a lexical grep only proves "the forbidden STRING is not
    present", never "the forbidden MODULE is not reachable" (an indirect import,
    a re-export, or a renamed alias would all slip past ``_scan`` above silently).

    The transplant added a SECOND gt-reading pair -- denominator.py +
    reading_grade.py under src/agent/judge/as_drawn/ -- alongside the existing
    src/agent/judge/gt.py.  ⭐ 2026-08-27 (G1) added a THIRD: gt_raw_layer.py,
    the reader for the gt RAW layer (per-edge basis/thickness inside
    review/conversion_report.json).  All must stay judge-side only: gate① / the
    executor must never import any of them, mirroring the gt iron law
    (CLAUDE.md §1.5#4).  This actually imports src.agent.legacy.pipeline in a FRESH
    subprocess (so an already-populated sys.modules from an earlier test in the
    same session cannot hide a real gap, and a genuinely absent one cannot
    produce a false positive either) and inspects sys.modules for what really
    loaded, rather than grepping source text for a token.
    """
    import json
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    probe = (
        "import sys, json\n"
        "import src.agent.legacy.pipeline\nimport src.agent.runtime_entry\nimport src.agent.runtime_roles.entry\n"
        "hits = sorted(m for m in sys.modules "
        "if m in ('src.agent.judge.gt', 'src.agent.judge.gt_raw_layer') "
        "or m.startswith('src.agent.judge.as_drawn'))\n"
        "print(json.dumps(hits))\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True, text=True, cwd=repo_root,
    )
    assert r.returncode == 0, f"pipeline import failed: {r.stderr}"
    hits = json.loads(r.stdout.strip().splitlines()[-1])
    assert hits == [], f"pipeline import closure reaches judge/gt or judge/as_drawn: {hits}"




def test_prescan_stays_deleted_until_the_reading_专项_decides_otherwise():
    """Sentinel, not a capability lock — and BEHAVIOURAL, not lexical.

    prescan (`prescan-plan` / `prescan-elevation`) was WITHDRAWN FROM THE WORKING TREE on
    2026-08-19 by user ruling — deferred to the reading 专项, NOT abandoned; the code,
    tests and restore steps live in `AI_agent/archive/reading_prescan/`. It had spent 2026-08-15..08-19 half-dead: the implementation shipped while
    `run_cv_probe.ALLOWED_TOOLS` no longer listed it, so the reader could not call it
    and only the orchestrator could pre-stage its output. That half-dead shape is what
    this sentinel prevents from recurring — prescan returns as a DECISION recorded in
    `AI_agent/archive/2026-09-08_management_rebuild/original/AI_agent/capability/reading/`, or it stays archived until one is taken.

    ⚠️ The first draft of this sentinel grepped the source for "prescan_plan" and
    tripped on its own module docstring recording the deletion. This repo has been
    bitten six times by lexical matching over unbounded text (F-49 → F-60 → N-1/N-2 →
    F-61 → F-62); a sentinel that repeats the mistake is worse than none. So this asks
    the code, not the characters.
    """
    import importlib

    toolbox = importlib.import_module("src.agent.reading.cv_toolbox")
    for name in ("prescan_plan", "prescan_elevation"):
        assert not hasattr(toolbox, name), f"cv_toolbox re-exports {name}"

    probe = _load_module_from_path(
        "cv_probe_sentinel", Path("scripts/tool_scripts/cv_probe.py")
    )
    parser = probe.build_parser()
    subparser_actions = [
        a for a in parser._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    tools = set()
    for action in subparser_actions:
        tools.update(action.choices)
    assert not {t for t in tools if "prescan" in t}, f"cv_probe still offers prescan: {sorted(tools)}"

    wrapper = Path("src/agent/execution/isolation_templates/run_cv_probe.py")
    allowed = _load_module_from_path("run_cv_probe_sentinel", wrapper).ALLOWED_TOOLS
    assert not {t for t in allowed if "prescan" in t}, f"wrapper authorizes prescan: {allowed}"


def test_judge_side_gt_readers_remain_confined_to_judge_package():
    judge_gt_readers = [
        Path("src/agent/judge/reading_score.py"),
        Path("src/agent/judge/elevation_score.py"),
    ]
    for path in judge_gt_readers:
        text = path.read_text(encoding="utf-8")
        assert "load_gt" in text or ".gt import" in text
        assert path.is_relative_to(Path("src/agent/judge"))









def _load_module_from_path(name: str, path: Path):
    """Import a standalone script by path (neither is an installed package)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
