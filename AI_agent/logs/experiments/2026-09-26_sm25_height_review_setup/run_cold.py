"""Original-only validation after the bounded height recovery; no saved answer."""
import importlib
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-26_sm25_height_cold_claude_run53"
BASE = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_cold_setup.run_cold").SCOPE
SCOPE = BASE + """
For this experiment work directly through the deterministic/visual tools without
review_detail or other delegation. Use input_view_status to notice relevant supplied
views with no direct view record; it is access feedback, not image understanding.
Before delivery, use check_openings(heights_only=true) and current source elevations
to inspect the exterior height families separately on each floor. Record located
image claims and confirm/apply their heights on the actual whole-building candidate;
report any remaining unlinked heights without pretending that returned pictures
alone constitute review. Read the claims reference when using those operations.
Preserve physical plan partitions and opening connections while resolving heights.
No error identities/counts, target heights or previous run results are supplied."""


def main():
    images = ROOT / "case_tests/e2e_tests/sm25-L_anchor/case_data"
    dump(HERE / "cold_frozen_method.json", {
        "scope": SCOPE, "mode": "original_images_only_whole_building_cold_start",
        "image_sha256": {p.name: digest(p) for p in sorted(images.glob("*.png"))},
        "provider": "claude", "role": "sonnet", "effort": "medium", "timeout_seconds": 3000,
        "withheld": ["saved plans/BIM", "GT", "old observations/calibration", "building declaration",
                     "error identities/counts", "target heights", "previous run outcomes"],
        "developer_participation": "Generic task/tool instruction only; no local answers or live intervention.",
        "development_agents": "Astra only", "runtime_delegation": "prohibited by experiment scope",
    })
    run_experiment(SimpleNamespace(command="run", images=images, mesh=None, building_input=None,
        out=RUN, scope=SCOPE, timeout=3000, provider="claude", exploratory_opus=False, effort="medium",
        resume_candidate=None, resume_plan=None, plan_image=None))


if __name__ == "__main__":
    main()
