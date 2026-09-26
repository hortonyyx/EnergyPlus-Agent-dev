"""Original-only cross-case validation; no earlier plans or local answers admitted."""
import importlib
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent/'2026-09-26_sm24_whole_building_claude_run55'
PREVIOUS = importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm25_height_review_setup.run_cold').SCOPE
SCOPE = PREVIOUS.replace(
    'Use pixel wall/opening declarations with build_plan_bim for each distinct floor, then assemble_plan_bim to combine explicitly placed saved drafts without manually copying room vertices or changing aperture dimensions.',
    'Use pixel wall/opening declarations with build_plan_bim for each distinct floor. '
    'If there are multiple distinct floors, use assemble_plan_bim to combine explicitly placed saved drafts '
    'without manually copying room vertices or changing aperture dimensions. '
    'For a single floor, deliver its candidate directly; do not invent another floor merely to use assembly.'
) + '''
Before final delivery reconcile assumptions and unresolved notes with the ACTUAL saved
candidate and confirmed evidence. Replace obsolete pending-elevation or placeholder
statements when their issue has been resolved; retain genuinely unverified or assumed
items. Do not merely claim in the final answer that old source notes were updated.
No previous case's geometry, counts, measurements or local observation is supplied.'''


def main():
    images=ROOT/'case_tests/e2e_tests/sm24_anchor/case_data'
    assert len(list(images.glob('*.png')))==5
    dump(HERE/'frozen_method.json',dict(scope=SCOPE,mode='original_images_only_whole_building_cross_case',
        image_sha256={p.name:digest(p) for p in sorted(images.glob('*.png'))},
        provider='claude',role='sonnet',effort='medium',timeout_seconds=3000,
        withheld=['previous generated plans/BIM','calibration','GT','building declaration',
                  'prior Haiku observations','developer local references','correct counts/heights'],
        developer_participation='Generic task/tool instructions only; no local answer or live intervention.',
        scope_changes_from_run54=['Assembly conditional on multiple floors, otherwise direct delivery.',
                                 'Explicit final source assumptions/unresolved-note reconciliation.'],
        runtime_delegation='prohibited by experiment scope; later role/concurrency design remains open'))
    run_experiment(SimpleNamespace(command='run',images=images,mesh=None,building_input=None,
        out=RUN,scope=SCOPE,timeout=3000,provider='claude',exploratory_opus=False,effort='medium',
        resume_candidate=None,resume_plan=None,plan_image=None))


if __name__=='__main__': main()
