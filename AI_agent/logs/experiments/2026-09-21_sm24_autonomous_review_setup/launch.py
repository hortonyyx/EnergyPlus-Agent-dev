"""Run a bounded review without case-specific error hints or evaluation input."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
SETUP = Path(__file__).resolve().parent
BASE = ROOT / 'AI_agent/logs/experiments/2026-09-20_sm24_opening_heights_run04'
OUT = ROOT / 'AI_agent/logs/experiments/2026-09-21_sm24_autonomous_review_run05'
SCOPE = (
    'Review the entire saved building against all supplied original drawings and the '
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
           '--resume-candidate', str(BASE / 'candidate_02'), '--out', str(OUT),
           '--scope', SCOPE, '--timeout', '1800', '--effort', 'medium']
if __name__ == '__main__':
    if OUT.exists():
        raise SystemExit('Refusing to overwrite an existing run')
    record = {'command': command, 'scope': SCOPE,
              'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'input_mode': 'saved_candidate_recovery; not cold start',
              'developer_intervention': 'generic whole-building review goal; no selected error locations or target values',
              'channel': 'existing Claude subscription only; Sonnet; no API or fallback',
              'evaluation': 'only after generation ends; never given to model'}
    (SETUP / 'launch.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    with (SETUP / 'runner_stdout.log').open('x') as stdout, (SETUP / 'runner_stderr.log').open('x') as stderr:
        result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
    print(json.dumps({'returncode': result.returncode, 'run': str(OUT)}), flush=True)
    raise SystemExit(result.returncode)
