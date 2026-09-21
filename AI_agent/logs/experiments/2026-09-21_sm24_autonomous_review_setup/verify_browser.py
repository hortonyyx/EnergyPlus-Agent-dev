"""Reuse the existing offline viewer check for a supplied completed run."""
from pathlib import Path
import argparse
import importlib.util

ROOT = Path(__file__).resolve().parents[4]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    if (run / 'browser_verification.json').exists():
        raise SystemExit('Refusing to overwrite browser verification')
    old = ROOT / 'AI_agent/logs/experiments/2026-09-20_sm24_method_transfer_run01/verify_browser.py'
    spec = importlib.util.spec_from_file_location('existing_bim_browser_check', old)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RUN = run
    module.main()
