"""Template expansion must preserve source shapes, apertures and explicit hypotheses."""
import copy
import json

import pytest

from src.agent.geometry.parametric_proposal import expand_parametric_proposal
from src.agent.execution.source_proposal import export_source_proposal


def plan():
    return {
        'templates': {'typical': {
            'footprint': [[0,0],[6,0],[6,2],[3,2],[3,5],[0,5]],
            'spaces': [
                {'id':'hall','role':'corridor_inferred','rect':[0,0,3,5],
                 'source_refs':['hypothesis']},
                {'id':'office','role':'office_inferred','rect':[3,0,6,2],
                 'source_refs':['hypothesis']}],
            'window_rows': [{'id':'west','facade':'West','plane':0,
                'spans':[[1,2],[3,4]],'z':[0.8,2.2], 'source_refs':['synthetic observation']}],
            'doors': [{'id':'d','space':'hall','other_space':'office',
                'p1':[3,0.4],'p2':[3,1.4],'z':[0,2.1],'source_refs':['hypothesis']}] }},
        'instances':[{'id':'F1','template':'typical','z':0,'height':3},
                     {'id':'F2','template':'typical','z':3,'height':3}],
        'assumptions':['Synthetic inference'], 'unresolved':['Actual interiors unknown']}


def test_l_shaped_repeated_floors_export_and_reload_without_false_floor_coverage(tmp_path):
    original=plan()
    before=copy.deepcopy(original)
    proposal=expand_parametric_proposal(original)
    assert original==before
    assert proposal['geometry']['windows'][2]['z']==[3.8,5.2]
    assert proposal['geometry']['openings'][1]['z']==[3,5.1]
    report=export_source_proposal(proposal,tmp_path/'a')
    assert report['source_geometry_ready'], report
    assert report['counts']['spaces']==4
    assert report['counts']['openings']==6
    source=json.loads((tmp_path/'a/source_model.json').read_text())
    assert all(f['footprint']==original['templates']['typical']['footprint'] for f in source['floors'])
    second=export_source_proposal(json.loads((tmp_path/'a/proposal.json').read_text()),tmp_path/'b')
    assert second['source_model_sha256']==report['source_model_sha256']


def test_whole_aperture_cannot_be_clipped_or_split_across_partition():
    value=plan()
    value['templates']['typical']['window_rows']=[{
        'id':'south','facade':'South','plane':0,'spans':[[2,4]],'z':[1,2],
        'source_refs':['synthetic spanning opening']}]
    with pytest.raises(ValueError,match='0 complete hosts'):
        expand_parametric_proposal(value)


def test_source_reports_real_overlap_without_expansion_repair(tmp_path):
    value=plan()
    value['instances'][1]['z']=2
    report=export_source_proposal(expand_parametric_proposal(value),tmp_path/'bad')
    assert not report['source_geometry_ready']
    assert (tmp_path/'bad/source_model.json').exists()


def test_nonrectangular_single_space_survives_without_extra_physical_dividers(tmp_path):
    value=plan()
    template=value['templates']['typical']
    template['spaces']=[{'id':'open','role':'office_inferred',
        'polygon':template['footprint'], 'source_refs':['explicit open-layout hypothesis']}]
    template['doors']=[]
    report=export_source_proposal(expand_parametric_proposal(value),tmp_path/'open')
    assert report['source_geometry_ready'],report
    assert report['counts']['spaces']==2


def test_unknown_row_fields_and_nonfinite_coordinates_are_rejected():
    value=plan()
    value['templates']['typical']['window_rows'][0]['kind']='door'
    with pytest.raises(ValueError,match='unknown fields'):
        expand_parametric_proposal(value)
    value=plan()
    value['instances'][0]['z']=float('nan')
    with pytest.raises(ValueError):
        expand_parametric_proposal(value)
