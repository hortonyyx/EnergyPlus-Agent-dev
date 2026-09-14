"""Original-only sm24 whole-building run with automatic source plans; no seed or GT."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

SCOPE = (
    'Reconstruct the target building shown in all supplied drawings into a viewable lightweight BIM. '
    'Preserve actual physical spaces, walls, openings, floor geometry and connectivity. '
    'Choose the observations, measurements and tools that the evidence requires. '
    'Inspect saved source geometry against the original drawings and revise substantive errors. '
    'Record assumptions and unexamined scope, and deliver a useful saved candidate within the budget.'
)

if __name__ == '__main__':
    out = ROOT/'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run14'
    setup = Path(__file__).resolve().parent
    image_dir = ROOT/'case_tests/e2e_tests/sm24_anchor/case_data'
    sources = [ROOT/'scripts/tool_scripts/run_bim_agent.py', *sorted((ROOT/'src/agent/geometry').glob('*.py')),
               ROOT/'src/agent/execution/source_proposal.py', ROOT/'src/agent/execution/subscription_json.py', Path(__file__).resolve()]
    frozen = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources}
    dump(setup/'frozen_with_plan_inputs.json', {
        'scope':SCOPE,'timeout_seconds':600,'effort':'medium','seed':None,
        'input_images':{p.name:digest(p) for p in sorted(image_dir.glob('*.png'))},
        'frozen_code_sha256':{name:digest(ROOT/name) for name in frozen},
        'input_boundary':'Only original PNG copies, generic scope and existing tool guide. No case JSON, prior observations, room/door counts, source candidate, local target/coordinates, GT or evaluation feedback.',
        'development_mode':'One fresh whole-building session with frozen tools; optional local model calls are chosen by the parent, not prefilled by the developer.',
    })
    run_experiment(SimpleNamespace(images=image_dir,out=out,scope=SCOPE,timeout=600,
                                   effort='medium',resume_candidate=None))
    (out/'implementation').mkdir()
    for name,data in frozen.items():
        assert (ROOT/name).read_bytes()==data, f'frozen tool changed during experiment: {name}'
        target=out/'implementation'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    dump(out/'frozen_code_verification.json',{'all_frozen_sources_unchanged':True,
        'files':json.loads((setup/'frozen_with_plan_inputs.json').read_text())['frozen_code_sha256'],
        'scope':'No source file changed during this model run; recursive implementation snapshots are evidence only, not model inputs.'})
