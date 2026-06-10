"""Standalone CLI for phase 2 (vector JSON -> IntakeOutput) via DeepSeek.

Thin wrapper over `src.agent.phase2` — the same code path intake_node uses in the
two-step flow, so the script and the pipeline can never drift. Use it to run
phase 2 against a case dir without spinning up the whole graph (e.g. to iterate
on phase2/rules.md or to produce a phase-2 artifact for comparison).

Usage:
    python Tool_scripts/run_phase2_deepseek.py \\
        --case test_data/SmallOffice_TwoStep/smalloffice_21

Reads:
    <case>/phase1_vector/*.json + phase1_summary.md
    <case>/testdata_prompt.json
    skills/intake_pipeline/{1_correction, 0_reading, 2_modelling, 3_split_pairing, 4_mep}

Writes (to <case>/phase2_intake/deepseek/):
    intake_output.json     on success
    raw_response.txt / thinking.txt        always (when available)
    intake_output_unvalidated.json + parse_error.txt   on failure
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from loguru import logger  # noqa: E402

from src.agent._share import ensure_schema_initialized  # noqa: E402
from src.agent.phase2 import run_phase2  # noqa: E402

# Load the EnergyPlus IDD so IntakeOutput.model_validate() can run its custom
# field validators (e.g. validate_terrain reads cls._idf_field...).
ensure_schema_initialized()
load_dotenv()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--case",
        required=True,
        help="case directory containing phase1_vector/ + testdata_prompt.json "
        "(rule docs are read from skills/intake_pipeline/)",
    )
    args = ap.parse_args()

    case_dir = Path(args.case).resolve()
    vector_dir = case_dir / "phase1_vector"
    testdata_text = (case_dir / "testdata_prompt.json").read_text(encoding="utf-8")
    out_dir = case_dir / "phase2_intake" / "deepseek"

    try:
        run_phase2(vector_dir, testdata_text, out_dir=out_dir)
    except RuntimeError as e:
        logger.error("phase2 failed: {}", e)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
