"""Assisted, read-only colour-filter probe; not a new reconstruction score."""
import json
from pathlib import Path
import shutil
import time
from scripts.tool_scripts.run_bim_agent import digest, dump, subscription
ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-23_sm24_wall_color_probe_glm_run33'
PROMPT = '''Inspect the original plan near pixel box [450,570,615,600] and its adjoining areas. Determine whether a physical partition is present and describe its full endpoints and the areas on either side, with uncertainty where needed. This is a developer-targeted local method probe, not whole-building reconstruction. First reproduce an unverified filter using view_pixel_profile: image 1f_view.png, box [462,578,615,596], axis x, rgb [255,255,255], tolerance 60, min_fraction 0.08. If empty, use its empty_filter_diagnostics to reconsider the colour, axis or support threshold and inspect original-image crops. Neither an empty filter nor a matching colour alone establishes wall absence/presence or a connection. Report evidence, revised interpretation and unresolved details. Do not build a BIM. No candidate geometry or evaluation answer is supplied.'''
def main():
    RUN.mkdir(exist_ok=False)
    (RUN / 'images').mkdir()
    shutil.copy2(HERE / 'inputs/1f_view.png', RUN / 'images/1f_view.png')
    old = json.loads((HERE.parent / '2026-09-23_sm24_cold_plan_glm_run32/inputs.json').read_text())
    manifest = dict(images=old['images'], provider='glm', input_mode='assisted_local_readonly_probe',
                    input_contents=old['input_contents'], scope=PROMPT, deadline_epoch=time.time()+600,
                    implementation_sha256={p:digest(ROOT/p) for p in old['implementation_sha256']})
    dump(RUN / 'inputs.json', manifest)
    receipt = subscription(RUN, PROMPT, model='sonnet', name='agent', readonly=True, timeout=600, effort='medium')
    dump(RUN / 'summary.json', dict(input_mode=manifest['input_mode'], subscription_invocations=1,
        actual_model=receipt.get('actual_model'), elapsed_seconds=receipt['elapsed_seconds'],
        completed=receipt.get('returncode') == 0 and 'result' in receipt,
        has_viewable_candidate=False, limits=['Developer selected local region and initial filter.',
        'No whole-case reconstruction or autonomous problem selection tested.']))
    print(json.dumps(json.loads((RUN/'summary.json').read_text()), indent=2))
if __name__ == '__main__':
    main()
