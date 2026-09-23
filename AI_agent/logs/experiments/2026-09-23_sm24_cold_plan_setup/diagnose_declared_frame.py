"""Separate coordinate convention from room errors; never changes candidate/score."""
import json
from pathlib import Path
from shapely.geometry import Polygon
from scripts.tool_scripts.run_bim_agent import dump
from src.agent.judge.source_partition import compare_partitions
HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-23_sm24_cold_plan_glm_run32'
def main():
    assert (RUN/'summary.json').exists()
    obs = json.loads((HERE/'original_observations.json').read_text())
    plan = json.loads((RUN/'plan_drafts/draft_004/plan.json').read_text())
    source = json.loads((RUN/'candidate_01/source_model.json').read_text())
    def interpolate(v, anchors):
        (a,b),(c,d) = anchors
        return b+(v-a)*(d-b)/(c-a)
    def original(xy):
        return [interpolate(v,obs['calibration'][axis+'_anchors']) for v,axis in zip(xy,'xy')]
    def reframe(xy):
        return original([interpolate(v,[(b,a) for a,b in plan[axis+'_anchors']]) for v,axis in zip(xy,'xy')])
    refs = [dict(id=k, floor_id='F1', z_floor=0, height=1, polygon=[original(p) for p in ring])
            for k,ring in obs['space_polygons_pixels'].items()]
    actual = [dict(s, floor_id='F1', z_floor=0, height=1, polygon=[reframe(p) for p in s['polygon']]) for s in source['spaces']]
    coverage = {r['id']:[dict(candidate=s['id'], reference_area_fraction=Polygon(r['polygon']).intersection(Polygon(s['polygon'])).area/Polygon(r['polygon']).area)
                       for s in actual if Polygon(r['polygon']).intersection(Polygon(s['polygon'])).area > .1] for r in refs}
    report = dict(mode='diagnostic_only_declared_anchor_transform_not_adopted',
        method='Invert submitted pixel-to-world anchors, then apply independently frozen original anchors. No fitted transform. Heights excluded. Raw evaluation and candidate untouched.',
        declared_anchors={a:plan[a] for a in ['x_anchors','y_anchors']}, independent_anchors=obs['calibration'],
        reference_spaces=refs, candidate_spaces=actual, reference_area_coverage=coverage,
        comparison=compare_partitions(refs,actual,tolerance_m=obs['tolerance']['original_partition_m']))
    dump(RUN/'evaluation/declared_frame_diagnostic.json',report)
    print(json.dumps(dict(status=report['comparison']['status'],coverage=coverage),indent=2))
if __name__ == '__main__':
    main()
