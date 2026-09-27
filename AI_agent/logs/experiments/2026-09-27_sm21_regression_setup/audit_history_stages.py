"""Evaluate historical complete candidates in temporary runs; originals untouched."""
import importlib
import json
from pathlib import Path
import shutil
import tempfile

from scripts.tool_scripts.run_bim_agent import dump

HERE = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text())


def main():
    original = importlib.import_module(
        'AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original')
    results = []
    for name, candidates in [
        ('2026-09-27_sm21_whole_building_repeat_claude_run58', ['candidate_03','candidate_04']),
        ('2026-09-27_sm21_current_tools_claude_run69', ['candidate_05','candidate_06'])]:
        run = HERE.parent / name
        for candidate in candidates:
            with tempfile.TemporaryDirectory(prefix='bim-history-stage-') as tmp:
                out = Path(tmp)
                (out / 'images').symlink_to(run / 'images', target_is_directory=True)
                (out / candidate).mkdir()
                shutil.copy2(run / candidate / 'source_model.json', out / candidate / 'source_model.json')
                dump(out / 'summary.json', {'mode':'offline_historical_candidate_evaluation'})
                dump(out / 'delivery.json', {'candidate':candidate})
                original.audit(out)
                report = load(out / 'evaluation/original_openings.json')
                results.append(dict(run=name, **report))
    dump(HERE / 'historical_stage_positions.json', dict(results=results,
        reference_unchanged=True, old_runs_modified=False,
        scope='Post-generation original-reference evaluation of already saved historical candidates.'))


if __name__ == '__main__':
    main()
