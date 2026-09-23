"""Repeat run33's local question with cross-axis evidence and endpoint guidance."""
import importlib
import json
from pathlib import Path
import shutil
import time

from scripts.tool_scripts.run_bim_agent import digest, dump, subscription

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OLD = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.run_probe')
RUN = HERE.parent / '2026-09-23_sm24_wall_context_probe_glm_run34'


def main():
    RUN.mkdir(exist_ok=False)
    (RUN / 'images').mkdir()
    shutil.copy2(OLD.HERE / 'inputs/1f_view.png', RUN / 'images/1f_view.png')
    old = json.loads((OLD.RUN / 'inputs.json').read_text())
    manifest = dict(images=old['images'], provider='glm', input_mode='assisted_local_readonly_probe',
                    input_contents=old['input_contents'], scope=OLD.PROMPT, deadline_epoch=time.time()+600,
                    implementation_sha256={p: digest(ROOT/p) for p in old['implementation_sha256']},
                    comparison='Same user question and original bytes as run33; changed tool feedback and generic system guidance.')
    dump(RUN / 'inputs.json', manifest)
    receipt = subscription(RUN, OLD.PROMPT, model='sonnet', name='agent', readonly=True, timeout=600, effort='medium')
    dump(RUN / 'summary.json', dict(input_mode=manifest['input_mode'], subscription_invocations=1,
        actual_model=receipt.get('actual_model'), elapsed_seconds=receipt['elapsed_seconds'],
        completed=receipt.get('returncode') == 0 and 'result' in receipt,
        has_viewable_candidate=False, limits=['Developer selected local region and initial filter.',
        'No whole-case reconstruction or autonomous problem selection tested.',
        'Tools and generic system guidance changed together; not an isolated attribution test.']))
    print(json.dumps(json.loads((RUN/'summary.json').read_text()), indent=2))


if __name__ == '__main__':
    main()
