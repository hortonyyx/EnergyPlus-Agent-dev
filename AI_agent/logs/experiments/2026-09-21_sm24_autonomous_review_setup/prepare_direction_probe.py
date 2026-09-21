"""Developer-selected original-image observations, separate from active model runs."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest

OUT = ROOT / 'AI_agent/logs/experiments/2026-09-21_sm24_facade_direction_probe'
ORIGINAL = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT, help='New independent directory')
    args = parser.parse_args()
    observation_fixture = OUT / 'observations.json'
    OUT = args.out.resolve()
    OUT.mkdir(exist_ok=False)
    (OUT / 'images').mkdir()
    images = {}
    for name in ['1f_view.png', 'East_view.png']:
        target = OUT / 'images' / name
        shutil.copy2(ORIGINAL / name, target)
        images[name] = {'sha256': digest(target)}
    manifest = {'images': images, 'scope': 'Developer-selected original-image direction diagnostic; no model run, no GT, no source BIM',
                'developer_intervention': 'Selected facade, crops, wall/opening identity and scale anchors from original drawings; not autonomous extraction'}
    (OUT / 'inputs.json').write_text(json.dumps(manifest, indent=2) + '\n')
    toolkit = Toolkit(OUT)
    for box in [[598,160,612,235],[598,300,612,365],[598,375,612,565],[560,600,615,680]]:
        toolkit.view_profile('1f_view.png', box, 'y', [0,255,255], 80, 0.05)
    toolkit.view_profile('1f_view.png', [604,598,610,685], 'y', [128,128,128], 40, 0.5)
    toolkit.view_profile('East_view.png', [0,700,2639,850], 'x', [0,255,0], 80, 0.1)
    toolkit.view_profile('East_view.png', [0,700,2639,850], 'x', [0,200,0], 80, 0.3)
    # The separately stored selections remain explicitly developer-provided input.
    if observation_fixture.is_file() and observation_fixture.parent.resolve() != OUT:
        from compare_facade_spans import compare
        shutil.copy2(observation_fixture, OUT / 'observations.json')
        observations = json.loads(observation_fixture.read_text())
        (OUT / 'comparison.json').write_text(json.dumps(compare(observations), indent=2) + '\n')
    print(OUT)
