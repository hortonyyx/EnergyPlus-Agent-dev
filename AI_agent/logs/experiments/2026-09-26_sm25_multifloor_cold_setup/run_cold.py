"""Original-only whole-building verification of the multi-floor toolkit."""
from pathlib import Path
from types import SimpleNamespace
from scripts.tool_scripts.run_bim_agent import run_experiment, dump, digest
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RUN=HERE.parent/'2026-09-26_sm25_multifloor_cold_claude_run51'
SCOPE="""Reconstruct one inspectable lightweight BIM for the whole building in the supplied original plans and elevations. This is an original-image-only run: no saved plans, generated BIM, prior observations, calibration, reference counts or GT are supplied. Read reconstruction, plan_partition and plan_assembly. Establish a common XY origin/direction and scale from each plan's dimension annotations and their endpoints. Independently interpret each floor's complete physical spaces and door connections. Use pixel wall/opening declarations with build_plan_bim for each distinct floor, then assemble_plan_bim to combine explicitly placed saved drafts without manually copying room vertices or changing aperture dimensions. Determine floor levels, storey heights and opening height families using elevation evidence, and keep floor-relative versus absolute z unambiguous. Do not silently copy one floor's plan to another.
Prioritize correct partitions, shape, opening inventory/hosts and connectivity. Keep real open circulation as one physical space. Inspect the clean original alongside saved full wall-path support and both adjoining complete spaces; use crops/profiles or a narrow review_detail task when an unresolved visual question benefits from it. Sample key same/separate relations and check actual source ownership, investigating conflicts against the original. Geometry validity and consistency with your own observations do not establish fidelity. Correct substantive discrepancies and preserve every unexamined limitation.
For the final whole-building candidate, inspect each source plan and its original-image overlay plus actual source elevations. Match plan opening identities with elevation positions and heights for each floor separately. Use record_claim/confirm/apply where suitable to preserve image-supported heights as distinct from assumptions; a viewed elevation alone covers no height items. Unobserved internal door heights may remain explicit assumptions. Do not invent vertical circulation absent from the input. Deliver the best inspected whole-building candidate and a truthful account of observed, assumed and unverified content. Reassembly uses the listed drafts, so include every intended floor and do not expect later candidate-only edits to survive it."""
def main():
 images=ROOT/'case_tests/e2e_tests/sm25-L_anchor/case_data'
 dump(HERE/'frozen_method.json',dict(scope=SCOPE,mode='original_images_only_whole_building_cold_start',
  image_sha256={p.name:digest(p) for p in sorted(images.glob('*.png'))},
  provider='claude',role='sonnet',effort='medium',timeout_seconds=3000,
  withheld=['saved plans','saved BIM','old observations','GT','building declaration','correct counts'],
  developer_participation='Generic task/tool instruction only; no local answers, error hints, or interventions.'))
 run_experiment(SimpleNamespace(command='run',images=images,mesh=None,building_input=None,
  out=RUN,scope=SCOPE,timeout=3000,provider='claude',exploratory_opus=False,effort='medium',
  resume_candidate=None,resume_plan=None,plan_image=None))
if __name__=='__main__':main()
