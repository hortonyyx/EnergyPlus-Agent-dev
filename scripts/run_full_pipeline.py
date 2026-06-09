"""End-to-end local run for a SmallOffice case.

Intake flows (pick one):

    Flow TWO-STEP  (default dev flow; no Anthropic API needed):
        # 1) In a Claude Code session, drive phase 1 (image -> vector JSON)
        #    following AI_agent/guides/new_case_guide.md Step 4 (Appendix A); save
        #    the per-image vector JSONs + phase1_summary.md under
        #    test_data/.../<case>/phase1_vector/
        # 2) Then run — intake_node runs phase 2 (vector JSON -> IntakeOutput)
        #    automatically via DeepSeek (intake_phase2 section of llm.yaml):
        python scripts/run_full_pipeline.py <case> \
            --base-dir test_data/SmallOffice_TwoStep \
            --phase1-from phase1_vector

    Flow INTAKE-FROM  (a finished IntakeOutput already on disk):
        python scripts/run_full_pipeline.py <case> \
            --intake-from output/intake_output.json

    Flow AUTO  (legacy single-step image -> IntakeOutput; needs ANTHROPIC_API_KEY):
        python scripts/run_full_pipeline.py <case>

    Optional --intake-only flag stops after intake (also works with --phase1-from
    to run phase 2 only and dump intake_output.json).

Outputs go to <case>/output/:
    intake_output.json     IntakeOutput Pydantic dump (cross-process artifact)
    smalloffice_17.yaml    exported by simulate node
    smalloffice_17.idf     exported by simulate node
    eplusout.*             EnergyPlus run artifacts
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from langchain_core.runnables import RunnableConfig
from loguru import logger

from src.agent import AgentState, SimContext, build_graph
from src.agent._share import ensure_schema_initialized
from src.agent.nodes import intake_node
from src.agent.runner import auto_approval, run_session
from src.agent.state import IntakeOutput
from src.utils.logging import setup_logger


SUPPORTED_FACADES = ("South", "North", "East", "West")


def _collect_images(case_dir: Path, spec: dict) -> list[Path]:
    """Per AI_agent/guides/new_case_guide.md §九 schema A:
    Floor plans (per-floor) -> top_view (back-compat) -> facades -> supp_plan.
    """
    images: list[Path] = []

    for fp in spec.get("Floor plans", []):
        images.append(Path(fp["path"]))

    if not images and spec.get("Top view path of the building"):
        images.append(Path(spec["Top view path of the building"]))

    for facade in SUPPORTED_FACADES:
        v = spec.get(f"{facade} view path of the building", "").strip()
        if v:
            images.append(Path(v))

    supp = spec.get(
        "Path of the supplementary plan example drawing for the building", ""
    ).strip()
    if supp:
        images.append(Path(supp))

    return [p for p in images if p.exists()]


def _build_user_input(spec: dict) -> str:
    """Serialize testdata_prompt.json as a human-readable description."""
    lines = []
    for k, v in spec.items():
        if not v:
            continue
        if k == "Floor plans":
            lines.append("Floor plans:")
            for fp in v:
                lines.append(
                    f"  - Floor {fp['floor']}: {fp['thermal_zones']} thermal zones"
                )
        elif "view path" in k.lower() or "drawing" in k.lower():
            continue  # paths go via image_paths, not user_input text
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)


def _load_intake_from(path: Path) -> IntakeOutput:
    """Load and validate a manually-produced IntakeOutput JSON."""
    ensure_schema_initialized()
    data = json.loads(path.read_text(encoding="utf-8"))
    return IntakeOutput.model_validate(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", help="Case dir name under <base-dir>/")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("test_data/SmallOffice"),
        help="Parent dir containing <case>/. Defaults to test_data/SmallOffice. "
        "Use test_data/SmallOffice_TwoStep for two-step (phase1+phase2) cases.",
    )
    parser.add_argument(
        "--intake-only",
        action="store_true",
        help="Run intake node only; skip the 9 downstream subagents + simulate.",
    )
    parser.add_argument(
        "--intake-from",
        type=Path,
        default=None,
        help=(
            "Load a pre-built IntakeOutput JSON (relative to <case>/) and short-"
            "circuit intake_node. Used by the half-manual flow in new_case_guide.md."
        ),
    )
    parser.add_argument(
        "--phase1-from",
        type=Path,
        default=None,
        help=(
            "Two-step flow: directory (relative to <case>/) of phase-1 vector "
            "JSONs + phase1_summary.md. intake_node runs phase 2 "
            "(vector JSON -> IntakeOutput) automatically. This is the default "
            "two-step dev flow (phase 1 produced half-manually in a Claude Code "
            "session). Mutually exclusive with --intake-from."
        ),
    )
    parser.add_argument(
        "--llm-config",
        type=Path,
        default=None,
        help=(
            "Per-run LLM config file (the model combination for THIS test). "
            "Overrides the global src/configs/llm.yaml for every stage "
            "(phase2 + 9 downstream). If omitted, auto-detects <case>/llm.yaml; "
            "if that is absent too, uses the global default. Lets each formal "
            "test pin its own model combo without editing the shared config."
        ),
    )
    parser.add_argument(
        "--init-llm-config",
        action="store_true",
        help=(
            "Scaffold a per-case config from the simple per-stage template "
            "(src/configs/llm_per_case_template.yaml) to <case>/llm.yaml (if "
            "absent), then exit. Edit it to set this test's model combination, "
            "then run normally."
        ),
    )
    parser.add_argument(
        "--epw",
        default="data/weather/Shenzhen.epw",
        help="EPW weather file (only used in full pipeline).",
    )
    parser.add_argument(
        "--no-simulate",
        action="store_true",
        help="Stop after IDF generation; do not invoke EnergyPlus runner. "
        "Used for B0' surface-bug iteration (2026-05-07).",
    )
    parser.add_argument(
        "--output-subdir",
        default="output",
        help="Subdirectory under <case>/ for all artifacts (intake_output.json, "
        "temp_*.yaml/.idf, eplusout.*, pipeline_run.log). Defaults to 'output'. "
        "Use a different value (e.g. 'output_new') when re-running to compare "
        "against a previous run without overwriting it. "
        "Note: --intake-from is resolved relative to <case>/ as before; copy "
        "intake_output.json into <case>/<output-subdir>/ first if you want the "
        "new subdir to contain everything.",
    )
    args = parser.parse_args()

    setup_logger(level="INFO")

    case_dir = args.base_dir / args.case

    # --- LLM config resolution (per-case model combination) ---
    global_llm_config = Path("src/configs/llm.yaml")
    per_case_template = Path("src/configs/llm_per_case_template.yaml")
    per_case_llm_config = case_dir / "llm.yaml"
    if args.init_llm_config:
        if per_case_llm_config.exists():
            logger.info("per-case LLM config already exists: {}", per_case_llm_config)
        else:
            case_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(per_case_template, per_case_llm_config)
            logger.info(
                "scaffolded per-case LLM config -> {} (edit it to set this test's "
                "model combination, then run without --init-llm-config)",
                per_case_llm_config,
            )
        return
    if args.llm_config is not None:
        llm_config = args.llm_config
        if not llm_config.is_file():
            raise SystemExit(f"--llm-config not found: {llm_config}")
    elif per_case_llm_config.is_file():
        llm_config = per_case_llm_config  # auto-detected per-case config
    else:
        llm_config = global_llm_config
    os.environ["EP_AGENT_LLM_CONFIG"] = str(llm_config.resolve())
    logger.info("LLM config: {}", llm_config)

    output_dir = case_dir / args.output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    testdata_raw = (case_dir / "testdata_prompt.json").read_text(encoding="utf-8")
    spec = json.loads(testdata_raw)
    user_input = _build_user_input(spec)
    image_paths = [str(p) for p in _collect_images(case_dir, spec)]

    if args.intake_from is not None and args.phase1_from is not None:
        raise SystemExit(
            "--intake-from and --phase1-from are mutually exclusive: the first "
            "supplies a finished IntakeOutput, the second runs phase 2 to build "
            "one. Pick one."
        )

    pre_intake: IntakeOutput | None = None
    if args.intake_from is not None:
        intake_path = args.intake_from
        if not intake_path.is_absolute():
            intake_path = case_dir / intake_path
        pre_intake = _load_intake_from(intake_path)
        logger.info(
            "intake_from={} (skipping intake LLM call; building={})",
            intake_path,
            pre_intake.building.name,
        )

    phase1_vector_dir: str | None = None
    if args.phase1_from is not None:
        p1_dir = args.phase1_from
        if not p1_dir.is_absolute():
            p1_dir = case_dir / p1_dir
        if not p1_dir.is_dir():
            raise SystemExit(f"--phase1-from dir not found: {p1_dir}")
        phase1_vector_dir = str(p1_dir)
        logger.info("phase1_from={} (intake_node will run phase 2)", p1_dir)

    # Organized two-step layout (0–5 stage dirs): phase 2 writes stage-numbered
    # subdirs (1_correction / 2_modelling / 3_split_pairing / 4_mep /
    # 5_intakeoutput) directly under <case> (alongside the phase-1 input dir and
    # EP_run); downstream + EP go to <case>/EP_run. Other flows keep the flat
    # <case>/<output-subdir>/ layout for back-compat.
    if phase1_vector_dir is not None and args.output_subdir == "output":
        output_dir = case_dir / "EP_run"
        output_dir.mkdir(parents=True, exist_ok=True)
        phase2_debug_dir = str(case_dir)
    else:
        phase2_debug_dir = (
            str(output_dir / "phase2_intake") if phase1_vector_dir else None
        )

    logger.info(
        "case={} images={} intake_only={} intake_from={}",
        args.case,
        len(image_paths),
        args.intake_only,
        bool(args.intake_from),
    )

    initial = AgentState(
        user_input=user_input,
        image_paths=image_paths,
        intake_output=pre_intake,
        phase1_vector_dir=phase1_vector_dir,
        testdata_text=testdata_raw,
        phase2_debug_dir=phase2_debug_dir,
    )

    if args.intake_only:
        if pre_intake is not None:
            raise SystemExit(
                "--intake-only with --intake-from is a no-op (the file is already "
                "the deliverable). Drop one of the flags."
            )
        update = intake_node(initial)
        intake_output = update["intake_output"]
        if intake_output is None:
            raise RuntimeError("intake_node returned no IntakeOutput")
        out_path = output_dir / "intake_output.json"
        out_path.write_text(intake_output.model_dump_json(indent=2), encoding="utf-8")
        logger.info("intake_output -> {}", out_path)
        return

    epw = Path(args.epw)
    if not epw.exists():
        raise FileNotFoundError(f"EPW not found: {epw}")

    graph = build_graph()
    context = SimContext(
        epw_path=epw, output_dir=output_dir, run_simulate=not args.no_simulate
    )
    cfg: RunnableConfig = {"configurable": {"thread_id": args.case}}

    def on_event(node: str, update: dict) -> None:
        logger.info("[node={}] keys={}", node, list(update.keys()) if update else [])

    state = run_session(
        graph,
        initial,
        context,
        cfg,
        on_interrupt=auto_approval,
        on_event=on_event,
    )

    intake_output = state.get("intake_output")
    if intake_output is not None and pre_intake is None:
        # Save the LLM-produced IntakeOutput; for --intake-from runs the file is
        # already on disk so skip overwriting.
        out_path = output_dir / "intake_output.json"
        out_path.write_text(intake_output.model_dump_json(indent=2), encoding="utf-8")
        logger.info("intake_output -> {}", out_path)

    for m in state.get("messages", [])[-5:]:
        content = m.content if hasattr(m, "content") else str(m)
        logger.info("final: {}", str(content)[:300])


if __name__ == "__main__":
    main()
