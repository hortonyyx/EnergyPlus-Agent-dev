"""Bounded image-to-height recovery; no evaluation fed to the working model."""
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-26_sm25_height_review_claude_run52"
SEED = HERE.parent / "2026-09-26_sm25_multifloor_cold_claude_run51/candidate_03"
SCOPE = """Review and, where the supplied original drawings justify it, correct the saved
whole-building candidate's exterior opening heights. This is a bounded continuation,
not a new plan reconstruction. Preserve all floor/space geometry, opening inventories,
horizontal positions, hosts and connections. Internal door heights without evidence
may remain explicit assumptions. Work directly with the supplied originals and the
tools; do not call review_detail or delegate this experiment.

Read reconstruction and claims. Use input_view_status as a reminder of direct original
views and check_openings(heights_only=true) to inspect each floor/facade's actual
heights and linked evidence. Independently identify the relevant supplied elevations
and match each distinct opening family to its plan identity; no proposed height or
claimed typical family in the saved draft is an observation. Establish each floor's
absolute elevation origin and use the original annotations/pixels to resolve height
families. Record located image claims with computable values. Confirm matching
heights before revising differing heights via claim references on the same parent.
Preserve uncertainty where evidence is incomplete and replace only obsolete notes.

Inspect actual source elevations after revision and the current height coverage.
Deliver the best checked candidate using finish_bim. State exactly which heights are
image-linked, assumed, deferred or still unchecked. Returned images and current claim
bindings do not certify that the original was read correctly. You are not supplied
GT, evaluation results, a list/count of errors, desired heights or previous reviews."""


def main():
    images = ROOT / "case_tests/e2e_tests/sm25-L_anchor/case_data"
    dump(HERE / "frozen_method.json", {
        "scope": SCOPE, "mode": "saved_candidate_exterior_height_review",
        "seed_proposal_sha256": digest(SEED / "proposal.json"),
        "image_sha256": {p.name: digest(p) for p in sorted(images.glob("*.png"))},
        "provider": "claude", "role": "sonnet", "effort": "medium", "timeout_seconds": 2400,
        "withheld": ["GT", "evaluation", "error identities/counts", "target heights", "old reviews"],
        "developer_participation": "Height scope and generic method only; no local answers or live intervention.",
        "development_agents": "Astra only", "runtime_delegation": "prohibited by experiment scope",
    })
    run_experiment(SimpleNamespace(command="run", images=images, mesh=None, building_input=None,
        out=RUN, scope=SCOPE, timeout=2400, provider="claude", exploratory_opus=False, effort="medium",
        resume_candidate=SEED, resume_plan=None, plan_image=None))


if __name__ == "__main__":
    main()
