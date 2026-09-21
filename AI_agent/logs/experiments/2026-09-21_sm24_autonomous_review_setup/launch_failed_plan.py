"""Independent whole-building recovery from an unchanged historical failed plan."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
SETUP = Path(__file__).resolve().parent
BASE = ROOT / 'AI_agent/logs/experiments/2026-09-20_sm24_method_transfer_run01'
OUT = ROOT / 'AI_agent/logs/experiments/2026-09-21_sm24_autonomous_recovery_run06'
SCOPE = (
    'Review the entire saved draft against all supplied original drawings and the '
    'building declaration. Independently choose what needs checking and which substantive '
    'discrepancies, if any, need revision. Use the existing tools to deliver the most faithful '
    'lightweight source BIM you can, retaining reliable information. Distinguish what you '
    'verified in this run from inherited claims, assumptions and unexamined items. '
    'Tie conclusions and any changes to evidence actually inspected or measured. '
    'Do not treat successful geometry validation as proof of drawing fidelity. '
    'Save and select the final candidate and state remaining limitations.'
)
command = [sys.executable, str(ROOT / 'scripts/tool_scripts/run_bim_agent.py'), 'run',
           '--images', str(BASE / 'images'), '--building-input', str(BASE / 'building_input.json'),
           '--resume-plan', str(BASE / 'plan_drafts/draft_003/plan.json'), '--plan-image', '1f_view.png',
           '--out', str(OUT), '--scope', SCOPE, '--timeout', '1800', '--effort', 'medium']
if __name__ == '__main__':
    if OUT.exists():
        raise SystemExit('Refusing to overwrite an existing run')
    record = {'command': command, 'scope': SCOPE,
              'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'input_mode': 'saved_failed_plan_recovery; not cold start',
              'developer_intervention': 'historical failure selected as diagnostic input; no selected error locations or target values in prompt',
              'channel': 'existing Claude subscription only; Sonnet; no API or fallback',
              'evaluation': 'only after generation ends; never given to model',
              'comparison_limit': 'different starting artifact from run05; not a causal tool ablation'}
    (SETUP / 'failed_plan_launch.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    with (SETUP / 'failed_plan_runner_stdout.log').open('x') as stdout, (SETUP / 'failed_plan_runner_stderr.log').open('x') as stderr:
        result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
    print(json.dumps({'returncode': result.returncode, 'run': str(OUT)}), flush=True)
    raise SystemExit(result.returncode)
