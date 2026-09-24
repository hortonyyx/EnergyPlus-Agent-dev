"""Cold start with run36's frozen implementation and run32's original scope."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-24_sm24_cold_context_glm_run37'


def main():
    previous = json.loads((HERE.parent / '2026-09-23_sm24_self_review_glm_run36/inputs.json').read_text())
    checks = {name: digest(ROOT / name) == value
              for name, value in previous['implementation_sha256'].items()}
    assert all(checks.values()), 'Production method must remain frozen'
    baseline = HERE.parent / '2026-09-23_sm24_cold_plan_setup/run_glm.py'
    scopes = [node.value for node in ast.walk(ast.parse(baseline.read_text()))
              if isinstance(node, ast.keyword) and node.arg == 'scope']
    assert len(scopes) == 1
    scope = ast.literal_eval(scopes[0])
    image = HERE.parent / '2026-09-23_sm24_cold_plan_setup/inputs/1f_view.png'
    assert digest(image) == previous['images']['1f_view.png']['sha256']
    assert list(image.parent.glob('*.png')) == [image]
    dump(HERE / 'frozen_method.json', dict(
        implementation_sha256=previous['implementation_sha256'],
        production_hashes_match_run36=checks, image_sha256=digest(image),
        provider='glm', effort='medium', timeout_seconds=1800, scope=scope,
        scope_source=str(baseline.relative_to(ROOT)),
        no_saved_plan_or_candidate=True, no_generation_evaluation_input=True,
        differences_from_run36=['Original-image-only cold start; no inherited plan, calibration or failure notes.',
                               'Same general cold-start scope as run32; current run36 tools and guidance.'],
        limits=['One run does not establish repeatability or a single-tool causal effect.',
                'Only a plan is supplied; vertical heights remain explicit assumptions.']))
    run_experiment(SimpleNamespace(command='run', images=image.parent,
        mesh=None, building_input=None, out=RUN, scope=scope, timeout=1800,
        provider='glm', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
