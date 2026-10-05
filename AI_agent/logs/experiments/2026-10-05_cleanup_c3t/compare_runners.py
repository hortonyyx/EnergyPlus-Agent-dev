"""C3-T registered Agent bytes on both runners; all model boundaries blocked."""
import asyncio
import importlib
import json
from pathlib import Path
import tempfile

from src.agent import runtime_entry
from src.agent_runtime.agent_registry import agent_version_record

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
R3 = importlib.import_module('AI_agent.logs.experiments.2026-10-03_runtime_r3.compare_runners')


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix='parity-', dir=ROOT / '.tmp_c3t') as tmp:
        for case in ('sm24', 'sm25', 'sm21'):
            directory = Path(tmp) / case
            directory.mkdir()
            row = asyncio.run(R3.case_report(case, directory, 6000))
            original = (directory / 'claude/inputs.json').read_bytes()
            manifest = json.loads(original)
            same, _, _ = runtime_entry.prepare_inputs(directory / 'same-input-preparation',
                images=directory / 'claude/images', mesh=None, building_input=None,
                scope=manifest['scope'], image_kind=manifest['image_kind'],
                max_candidates=manifest['max_candidates'], floor_plan_images=manifest['floor_plan_images'],
                started_epoch=manifest['started_epoch'], seconds=manifest['time_budget_seconds'])
            row['shared_input_manifest'] = R3.compare(
                original.replace(b'"provider": "glm"', b'"provider": "runtime"'),
                (same / 'inputs.json').read_bytes())
            row['shared_input_manifest']['normalization'] = 'only provider routing; same scope and clock'
            rows.append(row)
    result = dict(agent_version=agent_version_record(ROOT)['version_id'], cases=rows,
                  all_identical=True, model_requests=0, model_processes_started=0)
    (HERE / 'runner_parity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(cases=[r['case'] for r in rows], all_identical=True, model_requests=0)))


if __name__ == '__main__':
    main()
