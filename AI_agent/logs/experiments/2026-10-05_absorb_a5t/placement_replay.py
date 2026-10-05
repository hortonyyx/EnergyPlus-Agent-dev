"""Separate unchanged-history coverage from developer-supplied annotation replay.

Labels below are transcribed in the 10-01 developer plans, not evaluation GT.
Only this offline fixture matches a sample point to a historical wall ID. The
production checker requires that ID explicitly and never finds/snaps a wall.
"""
import hashlib
import json
from pathlib import Path

from src.agent.geometry.wall_placement import annotation_tolerances, wall_placement_report

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def checks(case, level):
    if case == 'sm21':
        return [('y',3,2),('y',5,2)] + ([('x',5,6),('x',10,6)] if level==0 else [('x',7.5,6)])
    if case == 'sm24':
        return [('y',15.94,2),('y',13,2),('y',8.06,2),('y',14,8),('y',4.94,8)]
    return [('y',v,13) for v in ([18,16,14,12,10,8] if level==0 else [14,12,10,8])]


def annotation(case, level, axis, value):
    """Bind the exact developer-transcribed label/chain, not a reference mesh."""
    spec = dict(lengths=[value*1000], unit='mm', origin_m=0, direction=1, node=1, offset_m=0)
    if case == 'sm21':
        if axis == 'y':
            part = 'P_cor_S' if value == 3 else 'P_cor_N'
            spec.update(lengths=[3000,250,1500,250,3000] if level == 0 else [3000,400,1200,400,3000],
                        node=1 if value == 3 else 4)
        else:
            part = 'P_N7' if level else 'P_N5' if value == 5 else 'P_N10'
    elif case == 'sm24':
        part = {15.94:'P_lobby', 13:'P_W13', 8.06:'P_W806', 14:'P_E14', 4.94:'P_E494'}[value]
        west = value in (15.94,13,8.06)
        spec.update(lengths=[4060,2940,4940,8060] if west else [4060,1940,5940,3120,4940],
                    origin_m=20, direction=-1, node={15.94:1,13:2,8.06:3,14:2,4.94:4}[value])
    else:
        part = f'P_off{value}'
        spec.update(lengths=[2000]*7+[6000] if level == 0 else [3940,2060,2000,2000,2000,2000,2060,3940],
                    origin_m=20, direction=-1, node=int((20-value)/2) if level == 0 else int((14-value)/2)+2)
    return part, spec


def main():
    runs = list(HERE.parent.glob('2026-10-01_opus_dev_sm2[145]'))
    runs += list(HERE.parent.glob('2026-09-2*_sm2*run5[3-8]'))
    runs += [HERE.parent / n for n in ('2026-09-30_sm21_instruction_fix_run99', '2026-09-30_sm24_instruction_fix_run100')]
    runs += [p.parent for p in (ROOT/'.tmp_a5t/history').rglob('inputs.json')
             if 'claude_code' in p.as_posix() and list(p.parent.glob('candidate_*/source_model.json'))]
    rows = []
    for run in sorted(runs):
        path = sorted(run.glob('candidate_*/source_model.json'))[-1]
        raw = path.read_bytes(); source = json.loads(raw)
        proposal = json.loads((path.parent/'proposal.json').read_bytes())
        case = next(case for case in ('sm21','sm24','sm25') if case in str(run))
        direct = wall_placement_report(source, proposal.get('wall_references',[]), proposal.get('wall_dimensions',[]))
        spaces = {s['id']:s for s in source['spaces']}
        positions, unmatched, refs = [], [], []
        for level,floor in enumerate(sorted(source['floors'],key=lambda f:(f['z_floor'],f['id']))):
            reference = HERE.parent/f'2026-10-01_opus_dev_{case}'/'plan_drafts'/f'draft_{level+1:03}'/'plan.json'
            plan = json.loads(reference.read_bytes())
            refs.append(dict(path=str(reference.relative_to(ROOT)),sha256=hashlib.sha256(reference.read_bytes()).hexdigest()))
            for axis, value, cross_sample in checks(case, level):
                index = 'xy'.index(axis); other = 1-index
                candidates = {}
                for b in source['boundaries']:
                    if b['geometry_type'] != 'wall' or b['kind'] != 'physical' or spaces[b['space_id']]['floor_id'] != floor['id']:
                        continue
                    coords = [v[index] for v in b['vertices']]
                    span = [v[other] for v in b['vertices']]
                    if max(coords)-min(coords) < 1e-8 and abs(coords[0]-value) <= .25 and min(span)+.01 < cross_sample < max(span)-.01:
                        candidates.setdefault(coords[0],[]).append(b)
                if len(candidates)!=1:
                    unmatched.append(dict(floor_id=floor['id'],axis=axis,expected=value,reason='no_unique_corresponding_wall_at_sample'))
                    continue
                boundary = sorted(next(iter(candidates.values())),key=lambda b:b['id'])[0]
                part_id, spec = annotation(case, level, axis, value)
                part = next(p for p in plan['partitions'] if p['id'] == part_id)
                assert abs(spec['origin_m'] + spec['direction']*sum(spec['lengths'][:spec['node']])/1000 + spec['offset_m'] - value) < 1e-8
                positions.append(dict(id=f'{floor["id"]}-{axis}-{value}', boundary_id=boundary['id'],axis=axis,
                    **spec,
                    basis='Developer replay: same representative plane as transcribed 10-01 labelled chain; original worker did not supply this structured binding.',
                    source_refs=[str(reference.relative_to(ROOT))+'#partitions/'+part_id, *part['source_refs']]))
        calibrations=[]
        for p in run.glob('plan_drafts/*/plan.json'):
            plan=json.loads(p.read_bytes())
            calibrations.append(plan)
        tolerances=annotation_tolerances(calibrations)
        conditional=wall_placement_report(source, [], [], positions=positions, floor_tolerances=tolerances)
        strict=wall_placement_report(source, [], [], positions=positions)
        assert path.read_bytes()==raw
        rows.append(dict(run=str(run.relative_to(ROOT)),candidate=path.parent.name,case=case,
            source_sha256=hashlib.sha256(raw).hexdigest(),source_unchanged=True,
            negative_control='run99' not in run.name and 'run100' not in run.name,
            annotation_sources=refs,direct_history=direct,developer_supplied_positions=positions,
            conditional_replay=conditional,strict_2cm_diagnostic=strict,unmatched=unmatched))
    summary=dict(candidates=len(rows), direct_checked=sum(r['direct_history']['checked_positions'] for r in rows),
        direct_findings=sum(r['direct_history']['total'] for r in rows),
        conditional_checked=sum(r['conditional_replay']['checked_positions'] for r in rows),
        target_findings=sum(r['conditional_replay']['total'] for r in rows if not r['negative_control']),
        control_findings=sum(r['conditional_replay']['total'] for r in rows if r['negative_control']),
        strict_2cm_target_findings=sum(r['strict_2cm_diagnostic']['total'] for r in rows if not r['negative_control']),
        strict_2cm_control_findings=sum(r['strict_2cm_diagnostic']['total'] for r in rows if r['negative_control']))
    result=dict(model_requests=0, summary=summary, rows=rows,
        limitation='Conditional developer-assisted replay, not unchanged historical model adoption. No prose/OCR inference in production. Missing wall IDs stay unassessed. No claim of whole-case dimensional fidelity.')
    (HERE/'placement_replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary))
    for r in rows:
        print(Path(r['run']).name,r['conditional_replay']['checked_positions'],[(i['axis'],i['actual_coordinate_m'],i['expected_coordinate_m'],i['deviation_m']) for i in r['conditional_replay']['items']])


if __name__=='__main__': main()
