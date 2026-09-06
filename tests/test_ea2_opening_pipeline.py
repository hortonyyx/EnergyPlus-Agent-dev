"""E-a′ production entry locks: source bytes -> ticks -> review -> V3 + archive."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import subprocess

import pytest

from src.agent import pipeline
from src.agent.correction.evidence_adapters import adapt_as_drawn_plan, adapt_as_drawn_elevation
from src.agent.correction.opening_adjudication import (
    OpeningReview, PlanBinding, FacadeInput, PlanCandidateChoice, OpeningChoice, SpatialResponse,
)
from src.agent.correction.projection_bridge import CutLineV1, cut_lines_from_wall_compilation, project_cut_lines
from src.agent.correction.tick_claim import TickSession, freeze, digest, verify_tick_archive
from src.agent.correction.wall_compiler import compile_wall_ir, FixedDecisionV1
from test_ea2_native_tick import plan_doc, ROOT
from test_tick_claim_a6 import response, assert_code
from tests.test_b3_elevation_leg import _synthetic_bytes


def native_document():
    """An integer-coordinate building in the REAL producer's native schema.

    Eight observed faces, four model-selected pairs, two face gaps representing
    one model-identified window. This is a synthetic fixture, not a sm25 reading.
    """
    doc=plan_doc(); face_template=doc['observations']['face_lines'][0]
    gap_template=deepcopy(face_template['gaps'][0])
    faces=[]
    for i,(axis,pos,extent) in enumerate((('row',0,8),('row',1,8),('row',5,8),('row',6,8),
                                        ('col',0,6),('col',1,6),('col',7,6),('col',8,6))):
        f=deepcopy(face_template)
        f.update(id=f'L{i}',axis=axis,constant_world_axis='y' if axis=='row' else 'x',
                 pos_m=float(pos),pos_px=float(pos*10),edges_m=[pos-.01,pos+.01],
                 support_cols_px=[pos*10,pos*10+1],support_width_m=.02)
        runs=[[0,2],[4,extent]] if i<2 else [[0,extent]]
        f.update(runs_m=runs,runs_px=[[a*10,b*10] for a,b in runs],
                 ink_coverage_per_run=[1.0]*len(runs), covered_px=sum(b-a for a,b in runs)*10,
                 support_px=extent*10)
        g=deepcopy(gap_template)
        g.update(lo_px=20,hi_px=40,len_px=20,span_m=[2.,4.],len_m=2.)
        f['gaps']=[g] if i<2 else []
        faces.append(f)
    h=doc['hypotheses']
    candidates=[]
    for i,a in enumerate(faces):
        for b in faces[i+1:]:
            if a['axis']!=b['axis']:continue
            candidates.append(dict(face_a=a['id'],face_b=b['id'],spacing_px=abs(a['pos_px']-b['pos_px']),
                                   spacing_m=abs(a['pos_m']-b['pos_m']),matched_declared_mm=[1000],overlap_px=60))
    selected=[dict(p,source='selected') for p in candidates
              if (p['face_a'],p['face_b']) in {('L0','L1'),('L2','L3'),('L4','L5'),('L6','L7')}]
    openings=[dict(id=f"{f['id']}g0",face_line=f['id'],gap_index=0,
                   **{k:f['gaps'][0][k] for k in ('span_m','len_m','len_px','ink_by_family')}) for f in faces[:2]]
    h.update(pair_candidates=candidates,pairs=selected,pairs_status='SELECTED',opening_candidates=openings,
             opening_types={o['id']:'window' for o in openings})
    for bucket in ('non_wall_face_lines','unpaired_wall_faces','solid_band_walls','ambiguous_face_lines'):
        h[bucket]={}
    doc['image']='ea2_native_fixture.png'
    doc['observations']['face_lines']=faces
    doc['observations']['calibration']={a:dict(values_mm=[total],cum_mm=[0,total],overall_mm=total)
                                        for a,total in (('x',8000),('y',6000))}
    doc['observations']['dimension_witnesses']={'x':{},'y':{}}
    doc['declarations']['thickness_callouts_mm']=[1000]
    doc['declarations']['chains']={cid:dict(axis=axis,values_mm=[total],world_start_mm=0,direction=1)
                                  for cid,axis,total in (('P','row',8000),('Y','col',6000))}
    return doc


def setup_review(*, mutate_choices=None, mutate_binding=None, geometry_transform=None):
    plan_art=adapt_as_drawn_plan(freeze(native_document()),input_id='native-plan',floor_ref='1f')
    plan=TickSession.from_artifact(plan_art)
    plan_batch=plan.submit(response(plan))
    comp=compile_wall_ir(plan_art,profile='strict')
    decisions=tuple(FixedDecisionV1(item_id=i.item_id,candidate_id=i.candidates[0].candidate_id) for i in comp.open_items)
    comp=compile_wall_ir(plan_art,profile='strict',decisions=decisions)
    walls,_=cut_lines_from_wall_compilation(comp.walls,())
    geom=project_cut_lines(walls,resolution_m=0.,resolution_source='fixture source exact coordinates',
                           source_resolved_sha256=comp.content_sha256,floor_id='1f',floor_name='1f',
                           z_floor_m=0.,ceiling_height_m=3.).geometry
    if geometry_transform:geom=geometry_transform(geom)
    south=next(w for w in walls if w.axis=='x' and w.pos_m==.5)
    binding=PlanBinding('L0g0','South',south.origin_id,geom.floors[0].cells[0].id,
                        CutLineV1('x',.5,2.,4.,.5,'opening','L0g0'),0)
    if mutate_binding:binding=mutate_binding(binding,walls)
    choices=(PlanCandidateChoice(candidate_id='L0g0',action='bind',reason='model identified window'),
             PlanCandidateChoice(candidate_id='L1g0',action='same_opening',target_id='L0g0',reason='other face of same window'))
    if mutate_choices:choices=mutate_choices(choices)
    elev_doc=json.loads(_synthetic_bytes([3000.],openings=((.5,1.5),)))
    elev_doc['facade_label']='South'
    elev_doc['calibration']['x']=dict(values_mm=[8000],cum_mm=[0,8000],overall_mm=8000)
    elev_doc['openings'][0]['x_range_m']=[2.,4.]
    # This fixture makes pixel-only decisions. B3's synthetic L00 structure
    # labels are not dimension-chain operand references in the tick contract.
    elev_doc['openings'][0]['edge_witnesses']={}
    raw=freeze(elev_doc)
    elev_art=adapt_as_drawn_elevation(raw,input_id='native-south',facade_ref='South')
    supplement=freeze(dict(schema='tick_reading_supplement_v1',source_sha=digest(raw),image=elev_doc.get('image'),
                           chains={},primary={},declarations=[]))
    elev=TickSession.from_artifact(elev_art,supplement=supplement)
    elev_batch=elev.submit(response(elev))
    facades=tuple(FacadeInput(f,elev if f=='South' else None,elev_batch.batch_id if f=='South' else None,
                              False,'image_left_to_right') for f in ('South','North','East','West'))
    review=OpeningReview(plan=plan,expected_plan_batch_id=plan_batch.batch_id,bindings=(binding,),
                          facades=facades,walls=walls,candidate_choices=choices,wall_compilation=comp,
                          geometry=geom,floor_id='1f')
    result=review.submit(SpatialResponse(packet_id=review.packet.packet_id,
                         choices=(OpeningChoice(plan_opening_id='L0g0',action='pair',
                                   elevation_opening_id=elev_doc['openings'][0]['id'],reason='model chose same window'),),
                         whole_building_review='accept',reason='fixture building review'))
    return geom,review,result,plan,plan_batch,elev,elev_batch


def test_ea1_pipeline_rejects_stale_batch(tmp_path):
    geom,review,result,plan,pb,elev,eb=setup_review()
    assembled=pipeline.run_opening_adjudication(geom,review=review,expected_result_id=result.result_id,out_dir=tmp_path/'good')
    assert len(assembled.windows)==1
    assert assembled.windows[0].span==[2.,4.]
    assert assembled.windows[0].z==[.5,1.5]
    elev.reconsider('overall review invalidated elevation')
    assert_code('TICK_BATCH_INVALIDATED',lambda: pipeline.run_opening_adjudication(
        geom,review=review,expected_result_id=result.result_id,out_dir=tmp_path/'stale'))
    assert not (tmp_path/'stale').exists()


def test_ea2_pipeline_archive_rebuilds_every_batch_byte_for_byte(tmp_path):
    geom,review,result,plan,pb,elev,eb=setup_review()
    pipeline.run_opening_adjudication(geom,review=review,expected_result_id=result.result_id,out_dir=tmp_path)
    archive=tmp_path/'opening_batches'/result.result_id
    for session,batch in ((plan,pb),(elev,eb)):
        folder=archive/batch.batch_id
        assert (folder/'source.bin').read_bytes()==session.packet.source_bytes
        if session.packet.supplement_bytes is not None:
            assert (folder/'supplement.bin').read_bytes()==session.packet.supplement_bytes
        else:
            assert json.loads((folder/'manifest.json').read_bytes())['supplement_present'] is False
        assert (folder/'batch.json').read_bytes()==batch.record
        assert verify_tick_archive(folder,expected_batch_id=batch.batch_id)==batch
    assert (archive/'spatial_result.json').read_bytes()==result.record


def test_ea3_no_production_call_to_historical_dict_api():
    scan=subprocess.run(['grep','-rnE',r'\bsynthesize_openings\s*\(','--include=*.py','src','scripts'],
                        cwd=ROOT,capture_output=True,text=True)
    assert scan.returncode in (0,1),scan.stderr
    calls=[line for line in scan.stdout.splitlines() if 'def synthesize_openings(' not in line]
    assert not calls,calls


def test_pipeline_never_treats_historical_json_as_current_review(tmp_path):
    geom,review,result,*_=setup_review()
    assert_code('CURRENT_OPENING_REVIEW_REQUIRED',lambda: pipeline.run_opening_adjudication(
        geom,review=json.loads(result.record),expected_result_id=result.result_id,out_dir=tmp_path))
    assert_code('OPENING_JUDGE_STRICT_REQUIRED',lambda: pipeline.run_opening_adjudication(
        geom,review=review,expected_result_id=result.result_id,out_dir=tmp_path,profile='exploratory'))


def test_every_candidate_requires_a_model_disposition():
    assert_code('PLAN_CANDIDATE_DECISION_COVERAGE_MISMATCH',lambda: setup_review(mutate_choices=lambda choices:choices[:-1]))


def test_host_must_be_the_wall_selected_in_the_native_source():
    def wrong(binding,walls):
        north=next(w for w in walls if w.axis=='x' and w.pos_m==5.5)
        return replace(binding,wall_id=north.origin_id,line=replace(binding.line,pos_m=5.5))
    assert_code('PLAN_HOST_NOT_SELECTED_SOURCE_WALL',lambda: setup_review(mutate_binding=wrong))


def test_b4_retires_only_the_bundle_declared_source_debt():
    _,review,_,_,_,elev,_=setup_review()
    record=json.loads(review.packet.record)
    present=next(f for f in record['facades'] if f['availability']=='present')
    debts=elev.evidence_artifact().bundle.evidence_debts
    expected=[d.debt_id for d in debts if d.obligation=='elevation_chain_spans_whole_building']
    assert expected and present['b4']['retired_debt_ids']==expected


def test_elevation_consumer_rechecks_order_when_upstream_guard_is_bypassed(monkeypatch):
    from test_tick_claim_a6 import fixture
    raw,_=fixture();s=TickSession(raw,image_id='legacy');b=s.submit(response(s))
    facts=list(s.consume(b.batch_id));facts[0]=replace(facts[0],value_u=facts[1].value_u)
    monkeypatch.setattr(s,'consume',lambda expected:tuple(facts))
    assert_code('TICK_ELEVATION_INTERVAL_NOT_ORDERED',lambda:s.elevation_document(b.batch_id))
