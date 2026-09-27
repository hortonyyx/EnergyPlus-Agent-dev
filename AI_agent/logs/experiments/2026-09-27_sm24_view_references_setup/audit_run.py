"""Reuse unchanged original/GT, preservation and receipt checks after generation."""
import argparse
import importlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def audit(run):
    shared = importlib.import_module('AI_agent.logs.experiments.2026-09-27_sm24_claim_regions_setup.audit_run')
    shared.HERE = HERE
    shared.audit(run)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    audit(parser.parse_args().run.resolve())
