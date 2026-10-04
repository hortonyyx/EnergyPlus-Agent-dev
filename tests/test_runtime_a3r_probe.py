"""Offline counterexamples for the bounded A3-R experiment, never live calls."""
import copy
import importlib
import json
import pytest

probe=importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a3r.sequence_probe')
audit=importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a3r.audit_prefixes')

def sse(*events):
    return ''.join('data: '+json.dumps(e)+'\n\n' for e in events).encode()

def test_sse_cache_and_cumulative_output_are_counted_once():
    result=probe.sse_usage(sse(
        {'type':'message_start','message':{'model':'glm-5.3-flash','usage':{'input_tokens':10,'cache_read_input_tokens':30000,'output_tokens':1}}},
        {'type':'ping'},
        {'type':'message_delta','delta':{},'usage':{'output_tokens':4}},
        {'type':'message_delta','delta':{'stop_reason':'end_turn'},'usage':{'output_tokens':7}},
        {'type':'message_stop'}))
    assert result['usage']=={'input_tokens':10,'cache_read_input_tokens':30000,'output_tokens':7}
    assert probe.reported_total_tokens(result['usage'])==30017

@pytest.mark.parametrize('events',[
    [{'type':'message_start','message':{'usage':{'input_tokens':1}}}],
    [{'type':'message_delta','delta':{'stop_reason':'end_turn'}}],
    [{'type':'error','error':{'type':'overloaded_error'}}],
    [{'type':'message_start','message':{}},{'type':'message_start','message':{}}],
])
def test_sse_partial_or_error_response_cannot_pass_probe(events):
    with pytest.raises(ValueError):probe.sse_usage(sse(*events))

@pytest.mark.parametrize('rows',[
    [{'event':'attempt'}],
    [{'event':'attempt'},{'event':'result','status':'failed'}],
    [{'event':kind,**({'status':'completed','total_tokens':1} if kind=='result' else {})} for _ in range(80) for kind in ('attempt','result')],
    [{'event':'attempt'},{'event':'result','status':'completed','total_tokens':4_999_000}],
])
def test_uncertain_failed_and_overbudget_batches_stop_before_send(rows):
    with pytest.raises(ValueError):probe.admission(rows,30000)

def test_probe_history_prefix_changes_only_at_status_tail_and_arm_variables():
    spec=probe.design()
    for arm in probe.ARMS:
        left=probe.build_body(spec,arm,0,0)
        right=probe.build_body(spec,arm,0,1)
        assert left['messages'][0]['content'][0]==right['messages'][0]['content'][0]
        assert 'cache_control' not in left['messages'][0]['content'][0]
        assert right['messages'][-1]['content'][-1]['cache_control']=={'type':'ephemeral'}
        assert left['system']==right['system']
    base=probe.build_body(spec,'baseline',0,0)
    for arm in ('identity','stream'):
        other=probe.build_body(spec,arm,0,0)
        other['system']=base['system'];other['stream']=False;other.pop('metadata',None)
        assert other==base
    assert spec['user_ids']['0']!=spec['user_ids']['1']
    assert len(set(spec['sequence_ids'].values()))==6

def test_audit_does_not_hide_mutated_thinking_or_non_tail_state():
    b={'messages':[{'role':'user','content':[{'type':'text','text':'original'}]},
        {'role':'assistant','content':[{'type':'thinking','thinking':'thought','signature':'signed'}]},
        {'role':'user','content':[{'type':'text','text':audit.STATE+'tail'}]}]}
    c=copy.deepcopy(b);c['messages'][-1]['content'][0]['text']=audit.STATE+'new'
    assert audit.prefix_result(b,c)['prefix']
    c['messages'][1]['content'][0]['signature']='mutated'
    assert not audit.prefix_result(b,c,True)['prefix']
    d=copy.deepcopy(b);d['messages'].append({'role':'user','content':[{'type':'text','text':'new message'}]})
    e=copy.deepcopy(d);e['messages'][-2]['content'][0]['text']=audit.STATE+'changed historical state'
    assert not audit.prefix_result(d,e,True)['prefix']
