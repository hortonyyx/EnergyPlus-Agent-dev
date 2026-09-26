"""One bounded two-floor extension from the saved F1 pixel plan and six originals."""
from pathlib import Path
from types import SimpleNamespace
from scripts.tool_scripts.run_bim_agent import run_experiment, dump, digest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RUN=HERE.parent/'2026-09-26_sm25_multifloor_claude_run50'
SCOPE = """Extend the supplied previously generated first-floor pixel declaration into one inspectable two-floor building using the original plans and elevations. The saved first floor is an editable starting point, not truth; its vertical heights were assumptions when only that plan was available. Focus on floor identity, distinct upstairs physical spaces/door connections, common XY coordinates, and elevation-supported floor/opening heights. Preserve sound first-floor plan geometry instead of manually rewriting it. No other saved building, successful observation, correct object count or GT is supplied.
Read reconstruction, plan_partition, plan_assembly and the height/evidence portions of claims as needed. Use original annotations and suitable crops/measurements to establish each floor's base, height and the opening height families on each facade. Distinguish floor-relative from world-absolute z. Set or locally revise the pixel declarations from evidence, compile the new upstairs plan with build_plan_bim, and combine the saved drafts using assemble_plan_bim. Its explicit z_floor places a floor but does not change its ceiling height or opening dimensions. A saved resume draft can be inspected and assembled directly, or locally revised first. Reassembling from drafts does not carry later candidate edits, so review the actual final candidate.
Keep complete physical spaces intact, distinguish furniture and door swings from walls, and do not copy a downstairs partition just because floor extents match. After an initial upstairs submission, use view_plan_wall_support and original crops to check full wall paths and their adjacent spaces; choose important same/separate space samples from the original and compare to actual source ownership. Source consistency is not image truth. Check final source plans/overlays and actual elevations, original opening inventories and plan-to-elevation identities. When source heights match observations confirm them; otherwise make evidence-bound local corrections. Use focused lower-cost review_detail only if a small unresolved visual question benefits from it. Unobserved internal door heights may be explicit assumptions. Do not silently omit floors/openings or add imaginary vertical circulation. Deliver the best inspected candidate with an honest account of observed/assumed/unverified content. This is a saved-first-floor extension experiment, not a whole-building cold start."""


def main():
    seed=HERE.parent/'2026-09-25_sm25_relation_cold_claude_run48/plan_drafts/draft_001/plan.json'
    images=ROOT/'case_tests/e2e_tests/sm25-L_anchor/case_data'
    dump(HERE/'frozen_method.json', dict(scope=SCOPE, mode='saved_F1_plan_extension_to_two_floors',
        seed_sha256=digest(seed), image_sha256={p.name:digest(p) for p in sorted(images.glob('*.png'))},
        provider='claude', role='sonnet', effort='medium', timeout_seconds=2400,
        included=['six original PNGs','run48 F1 pixel declaration'],
        excluded=['GT','evaluation','other saved source','building declaration','correct counts'],
        developer_participation='Generic task and saved F1 starting draft; no F2 answer or local defect hint.'))
    run_experiment(SimpleNamespace(command='run',images=images,mesh=None,building_input=None,
        out=RUN,scope=SCOPE,timeout=2400,provider='claude',exploratory_opus=False,effort='medium',
        resume_candidate=None,resume_plan=seed,plan_image='1f_view.png'))

if __name__=='__main__':main()
