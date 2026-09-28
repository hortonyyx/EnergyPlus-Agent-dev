"""Reuse existing post-generation checks while keeping all new reports here."""
import argparse
import importlib
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    previous = importlib.import_module("AI_agent.logs.experiments.2026-09-28_reconstruction_behavior.evaluate_run")
    # The existing adapter patches its lower-level audit's HERE as well. This
    # keeps frozen-condition and comparison files out of historical directories.
    with patch.object(previous, "HERE", HERE):
        previous.audit(args.run.resolve())


if __name__ == "__main__":
    main()
