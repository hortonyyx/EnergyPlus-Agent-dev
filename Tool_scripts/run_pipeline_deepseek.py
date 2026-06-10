"""Standalone CLI for the staged intake pipeline (vector JSON -> IntakeOutput).

Thin wrapper over `src.agent.pipeline` — the same code path intake_node uses, so
the script and the pipeline can never drift. Use it to run the pipeline against a
case dir without spinning up the whole graph (e.g. to iterate on the stage rule
docs or to produce an artifact for comparison).

Usage:
    python Tool_scripts/run_pipeline_deepseek.py \\
        --case test_data/SmallOffice_TwoStep/smalloffice_21

Reads:
    <case>/0_reading/*.json + reading_summary.md
    <case>/testdata_prompt.json
    skills/intake_pipeline/{0_reading, 1_correction, 2_modelling, 3_split_pairing, 4_mep}

Writes (to <case>/pipeline_out/):
    1_correction/ 2_modelling/ 3_split_pairing/ 4_mep/ 5_intakeoutput/
    (each stage's artifacts; 5_intakeoutput/intake_output.json is the final output)
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
from src.agent.pipeline import run_pipeline  # noqa: E402

# Load the EnergyPlus IDD so IntakeOutput.model_validate() can run its custom
# field validators (e.g. validate_terrain reads cls._idf_field...).
ensure_schema_initialized()
load_dotenv()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--case",
        required=True,
        help="case directory containing 0_reading/ + testdata_prompt.json "
        "(rule docs are read from skills/intake_pipeline/)",
    )
    args = ap.parse_args()

    case_dir = Path(args.case).resolve()
    vector_dir = case_dir / "0_reading"
    testdata_text = (case_dir / "testdata_prompt.json").read_text(encoding="utf-8")
    out_dir = case_dir / "pipeline_out"

    try:
        run_pipeline(vector_dir, testdata_text, out_dir=out_dir)
    except RuntimeError as e:
        logger.error("pipeline failed: {}", e)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
