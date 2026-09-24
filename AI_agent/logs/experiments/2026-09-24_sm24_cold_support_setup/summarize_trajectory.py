"""Evaluate saved draft outcomes only after the cold-start invocation ends."""
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump
from src.agent.judge.source_partition import compare_partitions

HERE = Path(__file__).resolve().parent
RUN = HERE.parent/'2026-09-24_sm24_cold_support_glm_run39'


def main():
    assert (RUN/'summary.json').exists()
    load = lambda p: json.loads(p.read_text())
    final = load(RUN/'evaluation/declared_frame_diagnostic.json')
    obs = load(HERE.parent/'2026-09-23_sm24_cold_plan_setup/original_observations.json')
    def interpolate(value, anchors):
        (p0, w0), (p1, w1) = anchors
        return w0+(value-p0)*(w1-w0)/(p1-p0)
    rows = []
    for path in sorted(RUN.glob('candidate_*/source_model.json')):
        source = load(path)
        provenance = source['generation']['provenance']
        record = provenance.get('plan_input')
        if not record:
            rows.append(dict(candidate=path.parent.name, status='not_evaluated_no_direct_plan_provenance'))
            continue
        plan = load(RUN/record['plan_file'])
        def reframe(xy):
            return [interpolate(interpolate(v, [(b,a) for a,b in plan[axis+'_anchors']]),
                                obs['calibration'][axis+'_anchors']) for v,axis in zip(xy,'xy')]
        spaces = [dict(s, floor_id='F1', z_floor=0, height=1,
                       polygon=[reframe(p) for p in s['polygon']]) for s in source['spaces']]
        comparison = compare_partitions(final['reference_spaces'], spaces,
            tolerance_m=obs['tolerance']['original_partition_m'])
        rows.append(dict(candidate=path.parent.name, plan_file=record['plan_file'],
            source_spaces=len(source['spaces']), source_openings=len(source['openings']),
            source_connections=len(source['connections']),
            declared_frame_comparison=comparison))
    dump(RUN/'evaluation/candidate_trajectory.json', dict(
        mode='post_generation_only_no_candidate_mutation_or_feedback_to_model',
        comparison_frame='Invert each actual submitted calibration then apply frozen original anchors; no fitting, heights excluded.',
        candidates=rows))
    print(json.dumps([{k:v for k,v in r.items() if k!='declared_frame_comparison'} |
        {'partition_status':r.get('declared_frame_comparison',{}).get('status')} for r in rows], indent=2))


if __name__ == '__main__':
    main()
