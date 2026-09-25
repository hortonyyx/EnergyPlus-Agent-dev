"""Same input and scope as GLM run46; controlled Claude working-model comparison."""
import importlib
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent/'2026-09-25_sm25_space_relation_claude_run47'


def main():
    assert not RUN.exists()
    base = importlib.import_module('AI_agent.logs.experiments.2026-09-25_sm25_space_relation_setup.run_recovery')
    import json
    frozen = json.loads((base.HERE/'frozen_method.json').read_text())
    assert all(digest(ROOT/path) == sha for path,sha in frozen['implementation_sha256'].items())
    frozen.update(provider='claude', comparison='Same failed draft, image, scope, implementation and budget as run46; provider changes to Claude Sonnet. No run46 observations or results supplied.')
    dump(HERE/'frozen_method.json',frozen)
    run_experiment(SimpleNamespace(command='run',images=base.INPUTS,mesh=None,
        building_input=None,out=RUN,scope=base.SCOPE,timeout=1800,provider='claude',
        exploratory_opus=False,effort='medium',resume_candidate=None,
        resume_plan=base.PREVIOUS/'plan_drafts/draft_003/plan.json',plan_image='1f_view.png'))


if __name__ == '__main__':
    main()
