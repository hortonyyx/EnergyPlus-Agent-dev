"""Actual A6 API counterexamples; fixtures are diagnostic, not visual judgments."""
from pathlib import Path
from dataclasses import replace
import ast
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from src.agent.correction.tick_claim import *
from test_tick_claim_a6 import fixture, response, BASE
from test_opening_adjudication_a6 import make_review, spatial_response


def show(name, fn):
    try:
        result = fn()
        print(name, '=>', result)
    except TickClaimError as exc:
        print(name, '=>', exc.code, exc.detail)


source = BASE / 'tools/as_drawn_elev.py'
fn = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == '_nearest')
ns = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), ns)
nearest = ns['_nearest']
print('ACTUAL_PRODUCER', source.relative_to(ROOT), fn.lineno)
for pxs, ticks in [((800, 950), [0., 500., 1000.]), ((0, 700), [0., 500., 1000.]),
                   ((620, 870), [0., 500., 1000., 1500.]), ((176, 254), [0., 120., 300., 520.])]:
    print('OLD_NEAREST_INPUT', pxs, 'picked', [nearest(ticks, p)[0] for p in pxs])
    raw, sup = fixture(pixels=(pxs[0]/100, pxs[1]/100))
    s = TickSession(raw, image_id='nearest', supplement=sup)
    print('ACTUAL_NEW_ROUTE', s.packet.diagnostics)
    show('NO_FINAL_FACT_BEFORE_MODEL', lambda: s.consume('unmade'))

for face in ('south', 'east', 'north', 'west'):
    raw = (BASE / f'out/sm25_{face}_as_drawn.json').read_bytes()
    sup = freeze_prototype_supplement(raw, (BASE / f'tools/cfg_{face}.json').read_bytes())
    s = TickSession(raw, image_id=face, supplement=sup)
    print('FULL_FROZEN_SCOPE', face, len(s.packet.edges), 'edges; x+z; all SAME_IMAGE_MODEL_REQUIRED')
    for eid in ({'south': ['O02:x0','O02:x1','O04:x0','O04:x1'], 'west':['O05:x0','O05:x1']}.get(face, [])):
        e = next(e for e in s.packet.edges if e.edge_id == eid)
        w = json.loads(e.witness)
        chain, seg = w['dimension_refs'][0].rsplit('_s', 1)
        selected = next(c for c in e.candidates if c.expression.anchor.chain_id == chain and c.expression.anchor.index == int(seg))
        print('OLD_SIX_NONPRIMARY_EDGE', face, eid, chain, 'node', seg, 'value_u', selected.value_u, '=> ADDRESSABLE_MODEL_CANDIDATE')
    if face == 'east':
        b = s.submit(response(s))
        print('EAST_O01_MODEL_PIXEL', [(f.edge_id,f.value_u,f.tier) for f in s.consume(b.batch_id) if f.edge_id in ('O01:x0','O01:x1')])

for values, nodes in [([5000,1930,1800],[0,5000,7000,8730]), ([5000,1930,1800],[0,5000,5000,8730]),
                       ([900,1500,1200],[0,900,2450,3600]), ([900,0,1500],[0,900,900,2400]),
                       ([1250,-250,900],[0,1250,1000,1900]), ([700,1100,1800],[1800,2500,3600])]:
    show(f'CHAIN {values} / {nodes}', lambda: require_chain(dict(values_mm=values, cum_mm=nodes, overall_mm=sum(values))))

for a,b,total,key in [(4700,4900,10000,400.0),(4200,4200,10000,400.),(4000,4050,9000,275.),
                       (2600,5200,10400,275.),(1800,3600,7200,318.5),(2150,6450,8600,407.2)]:
    raw,sup=fixture(values=(a,total-a,1000))
    d,cfg=json.loads(raw),json.loads(sup)
    d['openings'][0]['edge_witnesses']['x0']['dimension_refs']=['P_s1','P_s2','Q_s1','Q_s2']
    for flat in (a,b):
        d['dimension_witnesses']={'x':{str(key):flat}}
        raw=freeze(d); cfg['source_sha']=digest(raw)
        cfg['chains']['Q']=dict(values_mm=[b,total-b],cum_mm=[0,b,total],overall_mm=total,
                                 axis='x',origin_mm=0,direction=1,qualification='drawing_dimension')
        s=TickSession(raw,image_id='collision',supplement=freeze(cfg))
        print('COLLISION',a,b,'pixel_key',key,'flat',flat,'=> SAME_IMAGE_MODEL_REQUIRED',
              [(c.expression.anchor.chain_id,c.expression.anchor.index,c.value_u) for c in s.packet.edges[0].candidates if c.expression.anchor.index==1])

raw,sup=fixture(); node=lambda i:OperandRef(digest(raw),'P','node',i)
seg=lambda i:OperandRef(digest(raw),'P','segment',i)
show('NODE_SUM_1600_PLUS_4300_AS_SEGMENTS',lambda:evaluate(Expression('anchored_sum',node(0),(node(1),node(2))),raw=raw,supplement=sup,axis='x'))
show('ACTUAL_SEGMENT_SUM_1600_PLUS_2700',lambda:evaluate(Expression('anchored_sum',node(0),(seg(0),seg(1))),raw=raw,supplement=sup,axis='x'))
show('ANCHORED_DIFF_1600_PLUS_4300_MINUS_1600',lambda:evaluate(Expression('anchored_diff',node(1),(node(1),node(2))),raw=raw,supplement=sup,axis='x'))
show('CROSS_IMAGE_REF',lambda:evaluate(Expression('node',replace(node(1),source_sha='f'*64)),raw=raw,supplement=sup,axis='x'))
show('WRONG_AXIS_REF',lambda:evaluate(Expression('node',node(1)),raw=raw,supplement=sup,axis='z'))

for axis_value, thickness in [(3000,240),(4000,200),(8000,200),(3600,220),(7600,220),(4200,230)]:
    raw,sup=fixture(values=(axis_value,2000,3000));cfg=json.loads(sup)
    cfg['declarations']=[dict(axis='x',qualification='drawing_dimension',quantity='wall_thickness',kind='full',value_mm=thickness,callout_id='wall')]
    expr=Expression('axis_half_wall',OperandRef(digest(raw),'P','node',1),
                    (OperandRef(digest(raw),'declarations','declaration',0),),'positive','full')
    for direction in ('positive','negative'):
        show(f'AXIS {axis_value} FULL {thickness} {direction}',lambda:evaluate(replace(expr,direction=direction),raw=raw,supplement=freeze(cfg),axis='x'))
    cfg['declarations'][0]['qualification']='pixel_only'
    show('MEASURED_WALL_NOT_DECLARATION',lambda:evaluate(expr,raw=raw,supplement=freeze(cfg),axis='x'))
for full in (20.1,20.2):
    cfg['declarations'][0].update(qualification='drawing_dimension',value_mm=full)
    show(f'FULL_WALL_UNITS {full*10}',lambda:evaluate(expr,raw=raw,supplement=freeze(cfg),axis='x'))
raw,sup=fixture(values=(900,400,100));anchor=OperandRef(digest(raw),'P','node',0)
for lo,hi in ((2,1),(2,3)):
    expr=Expression('anchored_diff',anchor,(OperandRef(digest(raw),'P','node',lo),OperandRef(digest(raw),'P','node',hi)))
    show('NEGATIVE_OR_POSITIVE_DISPLACEMENT_WITH_EXPLICIT_ORIGIN',lambda:evaluate(expr,raw=raw,supplement=sup,axis='x'))

raw,sup=fixture();s=TickSession(raw,image_id='binding',supplement=sup);r=response(s)
show('TRUNCATED_DECISION_UNIVERSE',lambda:s.submit(r.model_copy(update={'choices':r.choices[:-1]})))
b=s.submit(r)
for field in ('value_u','tier','candidate'):
    changed=json.loads(b.record);changed['rows'][0][field]='changed';other=freeze(changed)
    show('REFINALIZED_'+field,lambda:s.consume(b.batch_id,TickBatch(digest(other),other)))
s.reconsider('spatial review overturned edge')
show('OLD_BATCH_AFTER_RETURN_TO_STEP_ONE',lambda:s.consume(b.batch_id))
show('OLD_RESPONSE_AFTER_RETURN_TO_STEP_ONE',lambda:s.submit(r))

raw,sup=fixture();s=TickSession(raw,image_id='debt')
r=TickResponse(packet_id=s.packet.packet_id,choices=tuple(TickChoice(edge_id=e.edge_id,
    action='pixel_pending_evidence' if e.missing_chains else 'pixel',reason='missing declared chain') for e in s.packet.edges))
b=s.submit(r);print('OWNED_DEBT_BEFORE',[(f.edge_id,bool(f.debt_id)) for f in s.consume(b.batch_id)])
s.reconsider('reading added frozen source-linked chain supplement',supplement=sup)
picks={e.edge_id:next(c.candidate_id for c in e.candidates if c.expression.anchor.index==i+1) for i,e in enumerate(s.packet.edges[:2])}
b2=s.submit(response(s,picks));print('AFTER_SUPPLEMENT_RECLAIM_RETIRED',[(r['edge_id'],bool(r['retired_debt_id'])) for r in json.loads(b2.record)['rows']])
for picked in ((0,0),(2,0)):
    raw,sup=fixture();s=TickSession(raw,image_id='interval',supplement=sup)
    choices={e.edge_id:next(c.candidate_id for c in e.candidates if c.expression.anchor.index==picked[i]) for i,e in enumerate(s.packet.edges[:2])}
    show(f'INTERVAL_CHOICE {picked}',lambda:s.submit(response(s,choices)))

review,elev=make_review();result=review.submit(spatial_response(review))
print('FOUR_CLASSES',json.loads(result.record)['outcomes'])
print('SCOREABLE_COUNT',len(review.scoreable_openings(result.result_id)))
elev.reconsider('global review found wrong tick')
show('SPATIAL_RESULT_AFTER_RECONSIDERATION',lambda:review.consume(result.result_id))
print('UNITS_6925_NOT_PROOF_OF_NODE',units(6925))
print('DONE: actual APIs; model choices are explicit diagnostic fixtures, not visual verdicts')
raw,sup=fixture(values=(900,2100,4500));n=lambda i:OperandRef(digest(raw),'P','node',i)
expr=Expression('axis_half_span',n(2),(n(0),n(1)),'negative')
show('ORIGINAL_B1_CENTER_3000_MINUS_HALF_CHAIN_WIDTH_900',lambda:evaluate(expr,raw=raw,supplement=sup,axis='x'))
show('ORIGINAL_B1_CENTER_3000_PLUS_HALF_CHAIN_WIDTH_900',lambda:evaluate(replace(expr,direction='positive'),raw=raw,supplement=sup,axis='x'))
raw,sup=fixture();s=TickSession(raw,image_id='failed-reconsider');r=response(s);b=s.submit(r)
bad=json.loads(sup);bad['source_sha']='f'*64
show('FAILED_SUPPLEMENT_INVALIDATES_CURRENT',lambda:s.reconsider('new source rejected',supplement=freeze(bad)))
show('FAILED_SUPPLEMENT_OLD_RESPONSE',lambda:s.submit(r))
show('FAILED_SUPPLEMENT_OLD_FACTS',lambda:s.consume(b.batch_id))
from test_opening_adjudication_a6 import review_fixture
from src.agent.correction.opening_adjudication import OpeningReview
raw,sup=fixture();operands=[OperandRef(digest(raw),'P','segment',0)]
expr=Expression('anchored_sum',OperandRef(digest(raw),'P','node',0),operands)
s=TickSession(bytearray(raw),image_id='mutable-expression',supplement=bytearray(sup),expressions=(('O:x0',expr),))
c=next(c for c in s.packet.edges[0].candidates if c.expression.operation=='anchored_sum')
operands.append(OperandRef(digest(raw),'P','segment',1))
b=s.submit(response(s,{'O:x0':c.candidate_id}))
print('AFTER_FIX_MUTABLE_OPERANDS preview_u',c.value_u,'final_u',s.consume(b.batch_id)[0].value_u)
p,pb,e,eb,bindings,facades,walls=review_fixture();caller_facades=list(facades)
r=OpeningReview(plan=p,expected_plan_batch_id=pb.batch_id,bindings=list(bindings),facades=caller_facades,walls=walls)
result=r.submit(spatial_response(r));caller_facades.clear();e.reconsider('source invalidated')
show('AFTER_FIX_MUTABLE_FACADES',lambda:r.consume(result.result_id))
for boundary in (1935,2473):
    raw,sup=fixture(values=(boundary,2000,3000));s=TickSession(raw,image_id='immune',supplement=sup)
    picks={e.edge_id:next(c.candidate_id for c in e.candidates if c.expression.anchor.index==i+1) for i,e in enumerate(s.packet.edges[:2])}
    b=s.submit(response(s,picks));print('CHAIN_IMMUNE',boundary,'=>',s.consume(b.batch_id)[0].value_u)
p,pb,e,eb,bindings,facades,walls=review_fixture()
show('TRUNCATED_REVIEW_INPUT',lambda:OpeningReview(plan=p,expected_plan_batch_id=pb.batch_id,bindings=bindings[:-1],facades=facades,walls=walls))
show('MISSING_FACADE_AVAILABILITY',lambda:OpeningReview(plan=p,expected_plan_batch_id=pb.batch_id,bindings=bindings,facades=facades[:-1],walls=walls))
raw,sup=fixture();a=TickSession(raw,image_id='same',supplement=sup);b=TickSession(raw,image_id='same',supplement=sup)
a_batch=a.submit(response(a));edge=b.packet.edges[0];pick=next(c.candidate_id for c in edge.candidates if c.expression.anchor.index==1)
b_batch=b.submit(response(b,{edge.edge_id:pick}))
print('TWO_VALID_BATCHES_SAME_SOURCE',a.packet.source_sha==b.packet.source_sha,'values',a.consume(a_batch.batch_id)[0].value_u,b.consume(b_batch.batch_id)[0].value_u)
show('VALID_ALTERNATE_BATCH_REJECTED',lambda:a.consume(a_batch.batch_id,b_batch))
