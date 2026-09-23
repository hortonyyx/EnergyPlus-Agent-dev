"""Independent drawing-side audit after run30 ends; never a generation input."""
import json
from pathlib import Path
from PIL import Image
from scripts.tool_scripts.run_bim_agent import dump, digest
from src.agent.geometry.source_image_overlay import render_source_overlay

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / 'AI_agent/logs/experiments/2026-09-23_sm25_door_extent_glm_run30'


def main():
    assert (RUN/'summary.json').exists()
    delivery = json.loads((RUN/'delivery.json').read_text())
    source = json.loads((RUN/delivery['candidate']/'source_model.json').read_text())
    opening = next(o for o in source['openings'] if o['id'] == '2f-door-c000-c006-junction')
    assert set(opening['space_ids']) == {'2f-c000', '2f-c006'}
    assert sorted({v[2] for v in opening['vertices']}) == [3.6, 5.7]
    xs = sorted({v[0] for v in opening['vertices']})
    # Original full-width 25000 mm annotation: green extension lines at 241/1387.
    # Cyan leaf/arc pixels independently inspected in the original junction crop.
    scale = 25 / (1387 - 241)
    intervals = [[(p-241)*scale for p in pair] for pair in ([704,706],[740,742])]
    matches = [lo <= actual <= hi for actual,(lo,hi) in zip(xs,intervals)]
    image_path = RUN/'images/2f_view.png'
    original = Image.open(image_path).convert('RGB')
    overlay, metadata = render_source_overlay(source, original, floor_id='2f',
        x_anchors=[[241,0],[1387,25]], y_anchors=[[341,20],[1258,0]],
        basis='Post-generation developer reading of original 25000/20000mm overall dimension extension lines. No BIM-derived metre anchors.',
        image_name='2f_view.png')
    overlay.save(RUN/'independent_full_overlay.png')
    box = (660,460,815,625)
    original.crop(box).resize((620,660)).save(RUN/'independent_junction_original.png')
    overlay.crop(box).resize((620,660)).save(RUN/'independent_junction_overlay.png')
    dump(RUN/'independent_full_overlay.json',metadata)
    report = {'mode':'post_generation_original_image_audit','not_returned_to_model':True,
        'source_model_sha256':source['source_model_sha256'],'image_sha256':digest(image_path),
        'full_width_annotation_mm':25000,'full_width_extension_pixels':[241,1387],
        'full_height_annotation_mm':20000,'full_height_extension_pixels':[341,1258],
        'independently_observed_jamb_pixel_intervals':[[704,706],[740,742]],
        'jamb_x_m_intervals_using_full_width':intervals,'actual_jamb_x_m':xs,
        'matches_original_jamb_bands':matches,'actual_door_width_m':xs[1]-xs[0],
        'connection_matches_original_symbol':True,'height_assumed_m':2.1,
        'host_plane_y_m':sorted({v[1] for v in opening['vertices']}),
        'interpretation':'The newly recovered door and its two hosts agree with the original local symbol within pixel uncertainty. This is not whole-building acceptance.',
        'not_evaluated':['all other doors','door height measurement','full floor partition fidelity','vertical circulation','cold-start autonomy']}
    dump(RUN/'independent_endpoint_audit.json',report)
    assert all(matches), 'Door endpoints remain outside independently observed jamb bands'
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
