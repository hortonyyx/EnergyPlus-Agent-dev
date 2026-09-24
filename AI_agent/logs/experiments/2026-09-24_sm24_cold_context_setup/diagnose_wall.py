"""Developer-localized post-run replay, never supplied to run37 generation."""
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-24_sm24_cold_context_glm_run37'


def main():
    assert (RUN / 'summary.json').exists()
    target = HERE / 'postrun_tool_replay'
    target.mkdir(exist_ok=False)
    (target / 'images').mkdir()
    source = RUN / 'images/1f_view.png'
    shutil.copy2(source, target / 'images/1f_view.png')
    manifest = json.loads((RUN / 'inputs.json').read_text())
    dump(target / 'inputs.json', dict(images=manifest['images'], provider='glm',
        input_mode='offline_developer_localized_postrun_replay_no_model_call'))
    toolkit = Toolkit(target, readonly=True)
    # Same image, color and tolerance as the model's gray-wall profiles.
    # The full strip contains upper wall, door interruptions, open gap and lower turn.
    toolkit.view_profile('1f_view.png', [449, 290, 472, 760], 'y', [128, 128, 128], 70, .1)
    toolkit.view_profile('1f_view.png', [450, 595, 470, 690], 'y', [128, 128, 128], 70, .1)
    with Image.open(source) as image:
        pixels = np.asarray(image.convert('RGB'))[595:690, 450:470]
        colors, counts = np.unique(pixels.reshape(-1, 3), axis=0, return_counts=True)
        image.crop((385, 550, 625, 780)).resize((720, 690)).save(target / 'original_context.png')
    with Image.open(RUN / 'image_overlays/overlay_002.png') as image:
        image.crop((385, 550, 625, 780)).resize((720, 690)).save(target / 'actual_source_overlay_context.png')
    dump(target / 'diagnosis.json', dict(
        mode='developer_selected_postrun_diagnostic_not_autonomous_recovery',
        original_image_sha256=digest(source),
        false_path=dict(id='P_corridor_east', x=459.5, declared_y=[298.5, 698],
                        unsupported_interior_probe_box=[450, 595, 470, 690]),
        exact_probe_colors=[dict(rgb=c.tolist(), count=int(n)) for c, n in zip(colors, counts)],
        total_probe_pixels=int(pixels.shape[0]*pixels.shape[1]),
        observation='The interior of the proposed extension is blank original background, while the full-context profile shows the real upper wall and lower return separated by a gap.',
        consequences=['Continuous circulation is split into corridor and zoneA.',
                      'D_Rdouble and D7_zoneA_C attach to the spurious zoneA instead of the continuous corridor.'],
        boundary='No model invocation, source mutation, GT coordinate input or changed evaluation tolerance. A blank color filter alone is not a universal wall-absence rule.'))


if __name__ == '__main__':
    main()
