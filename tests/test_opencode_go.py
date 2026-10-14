"""Go subscription isolation and real runtime protocol/tool-image round trips."""
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from src.agent_runtime.connections import resolve_connection
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.failures import ModelServiceError
from src.agent_runtime.opencode_go import BASE_URL, HttpGoAdapter, conversation_id, model_contract
from src.agent_runtime.providers import provider_parameters, validate_provider_model
from test_agent_runtime import MESSAGES, response, runtime


def private(tmp_path):
    path = tmp_path / 'go.env'
    path.write_text(f'OPENCODE_GO_BASE_URL={BASE_URL}\nOPENCODE_GO_API_KEY=private-go-key\n')
    return path


def test_go_credentials_and_public_identity_never_become_paratera(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENCODE_GO_API_KEY', 'environment-key-must-not-be-used')
    connection = resolve_connection('opencode-go', private(tmp_path), model='kimi-k3')
    public = connection.descriptor.model_route('kimi-k3')
    assert public['billing_mode'] == 'subscription'
    assert public['base_url'] == BASE_URL and public['adapter_kind'] == 'openai_chat_completions'
    assert 'private-go-key' not in json.dumps(public) and 'private-go-key' not in repr(connection)
    with pytest.raises(ValueError, match='explicit credentials'):
        resolve_connection('opencode-go', None, model='kimi-k3')
    path = private(tmp_path)
    path.write_text('OPENCODE_GO_BASE_URL=https://opencode.ai/inference/v1\nOPENCODE_GO_API_KEY=private-go-key\n')
    with pytest.raises(ValueError, match='reviewed Go subscription'):
        resolve_connection('opencode-go', path, model='kimi-k3')


def test_go_model_protocol_sampling_and_reasoning_fail_closed():
    for name in ('gpt-6-sol', 'deepseek-v4-pro', 'omen-alpha', 'opencode-go/kimi-k3'):
        with pytest.raises(ValueError, match='no admitted'):
            validate_provider_model('opencode-go', name)
    assert provider_parameters('opencode-go', model='kimi-k3', output_tokens=32000) == {'max_tokens':32000}
    assert provider_parameters('opencode-go', model='gpt-6-luna', output_tokens=32000,
        reasoning_effort='low') == {'max_tokens':32000, 'reasoning_effort':'low'}
    for kwargs in ({'reasoning_effort':'high'}, {'temperature':0}, {'thinking':False}):
        with pytest.raises(ValueError):
            provider_parameters('opencode-go', model='kimi-k3', output_tokens=32000, **kwargs)


@pytest.mark.parametrize('model', ['glm-5.3-flash','minimax-m3','gpt-6-luna'])
def test_go_transport_uses_own_agent_stable_session_exact_wire_and_no_redirect(tmp_path, model):
    async def scenario():
        connection = resolve_connection('opencode-go', private(tmp_path), model=model)
        session = conversation_id(tmp_path / 'run', 'plan-reader')
        assert session == conversation_id(tmp_path / 'run', 'plan-reader')
        assert session != conversation_id(tmp_path / 'run', 'elevation-reader')
        seen=[]
        def handler(request):
            seen.append(request)
            return httpx.Response(307, headers={'location':'https://unapproved.invalid/chat/completions'})
        adapter = HttpGoAdapter(base_url=connection.descriptor.base_url, api_key=connection.api_key,
            protocol=connection.descriptor.adapter_kind, session_id=session, transport=httpx.MockTransport(handler))
        from types import SimpleNamespace
        wire=b'{"model":"synthetic","messages":[]}'
        with pytest.raises(ModelServiceError) as error:
            await adapter.send(SimpleNamespace(wire_bytes=wire),timeout=5)
        assert 'private-go-key' not in str(error.value)
        assert len(seen)==1 and seen[0].content==wire
        assert seen[0].headers['x-opencode-session']==session
        assert seen[0].headers['user-agent']=='Sim-BIM-Agent/work-model'
        assert seen[0].headers['authorization']=='Bearer private-go-key'
        expected={'glm-5.3-flash':'/chat/completions','minimax-m3':'/messages','gpt-6-luna':'/responses'}[model]
        assert str(seen[0].url)==BASE_URL+expected
        assert 'anthropic-beta' not in seen[0].headers
        if model=='minimax-m3':
            assert seen[0].headers['anthropic-version']=='2023-06-01'
        await adapter.close()
    asyncio.run(scenario())


def native_response(model, *, tool=False):
    if model == 'minimax-m3':
        return {'id':'msg-test', 'type':'message','role':'assistant','model':model,
            'content':[{'type':'tool_use','id':'view-1','name':'view','input':{}}] if tool else [{'type':'text','text':'OK'}],
            'stop_reason':'tool_use' if tool else 'end_turn','usage':{'input_tokens':40,'output_tokens':11}}
    return {'id':'resp-test','object':'response','status':'completed','model':model,
        'output':[{'id':'reason-test','type':'reasoning','summary':[],'encrypted_content':'opaque-replay'},
                  {'id':'fc-test','type':'function_call','call_id':'view-1','name':'view','arguments':'{}'}] if tool else
                 [{'id':'message-test','type':'message','role':'assistant','content':[{'type':'output_text','text':'OK'}]}],
        'usage':{'input_tokens':40,'output_tokens':11,'total_tokens':51}}


@pytest.mark.parametrize('model', ['glm-5.3-flash','minimax-m3','gpt-6-luna'])
def test_go_real_runtime_preserves_tool_images_native_history_usage_and_subscription(tmp_path, model):
    replies=[response(('view-1','view',{}),reasoning=True),response(text='OK',reasoning=True)] if model=='glm-5.3-flash' else [native_response(model,tool=True),native_response(model)]
    engine=runtime(tmp_path,replies,limits=RunLimits(model_calls=2,tool_calls=4,seconds=30,tokens=200000))
    engine.model=model
    engine.parameters=provider_parameters('opencode-go',model=model,output_tokens=32000)
    engine.strict_model_profile=True
    engine.versions=engine.versions.model_copy(update={'remote_model':engine.versions.remote_model.model_copy(
        update={'route_id':'opencode-go','remote_alias':model})})
    with engine.store:
        result=asyncio.run(engine.run(MESSAGES))
        assert result['status']=='completed' and result['model_calls']==2
        assert result['usage_accounting']['billing_modes']==['subscription']
        assert result['billing_usd'] is None and result['estimated_cost_cny'] is None
        profile=engine._config()['model_profile']
        assert profile['text_safety_factor']==2.0 and 'unverified_endpoint' in profile['profile_status']
        assert profile['context_window_tokens']==(1050000 if model=='gpt-6-luna' else 1000000)
        requests=[event.payload for event in engine.store.events if event.payload.event_type=='adapter_request']
        assert len(requests[1].images)==1
        for wire,event in zip(engine.adapter.requests,requests):
            assert wire==engine.store.capture_bytes(event.final_request_body)
            body=json.loads(wire)
            assert body['model']==model and body['stream'] is False
            if model=='glm-5.3-flash':
                assert 'n' not in body and 'enable_thinking' not in body
                assert body['max_tokens']==32000
            elif model=='minimax-m3':
                assert body['max_tokens']==32000 and 'context_management' not in body
                assert all(message['role'] in {'user','assistant'} for message in body['messages'])
            else:
                assert body['max_output_tokens']==32000 and body['store'] is False
                assert all(tool['type']=='function' for tool in body['tools'])
        if model=='gpt-6-luna':
            second=json.loads(engine.adapter.requests[1])
            assert any(item.get('encrypted_content')=='opaque-replay' for item in second['input'])
            assert any(item.get('type')=='function_call_output' for item in second['input'])
        engine.store.validate()


def test_go_mixed_role_configuration_preserves_selected_models_and_concurrency(tmp_path):
    from src.agent.runtime_configuration import argv_for, load_configuration
    from test_role_configuration import case, configuration, role
    selected=case()
    selected.update(provider='opencode-go',model='glm-5.3-flash',reasoning_effort=None,
                    max_concurrent_readers=3,credentials_file=str(private(tmp_path)))
    selected['roles']={name:role('opencode-go',model,None,32000) for name,model in
        [('coordinator','glm-5.3-flash'),('plan_reader','kimi-k3'),('elevation_reader','minimax-m3')]}
    path=tmp_path/'run.json'
    path.write_text(json.dumps(configuration(selected)))
    loaded=load_configuration(path)['cases'][0]
    command=argv_for(loaded)
    assert command[command.index('--max-concurrent-readers')+1]=='3'
    routes=json.loads(command[command.index('--roles-json')+1])
    assert routes['plan_reader']['model']=='kimi-k3' and routes['elevation_reader']['model']=='minimax-m3'
    assert model_contract(routes['plan_reader']['model'])[0]!=model_contract(routes['elevation_reader']['model'])[0]


def test_go_messages_lifts_later_system_context_without_glm_beta_extension():
    from src.agent_runtime.anthropic import convert_messages
    from src.agent_runtime.opencode_go import estimate_messages
    messages=[{'role':'system','content':'Initial guide'}, {'role':'user','content':'Original task'},
              {'role':'assistant','content':'Earlier reply'}, {'role':'system','content':'Current runtime context'},
              {'role':'user','content':'Continue'}]
    sources=list(range(len(messages)))
    system, origins, native, native_origins=convert_messages(messages,sources,native_system_only=True)
    assert [block['text'] for block in system]==['Initial guide','Current runtime context']
    assert origins==[0,3] and all(row['role'] in {'user','assistant'} for row in native)
    estimate=estimate_messages(model='minimax-m3',messages=messages,tools=[],parameters={'max_tokens':32000})
    assert estimate.context_window_tokens==1000000 and estimate.reservation_tokens>32000


@pytest.mark.parametrize('change', ['money', 'opaque_history'])
def test_go_direct_runtime_rejects_unreviewed_budget_or_history_before_send(tmp_path, change):
    from decimal import Decimal
    engine=runtime(tmp_path,[response(text='must not send')])
    engine.model='gpt-6-luna'
    engine.parameters=provider_parameters('opencode-go',model=engine.model,output_tokens=32000)
    engine.versions=engine.versions.model_copy(update={'remote_model':engine.versions.remote_model.model_copy(
        update={'route_id':'opencode-go','remote_alias':engine.model})})
    if change=='money':
        engine.limits=engine.limits.model_copy(update={'money_usd':Decimal('1')})
    else:
        engine.reasoning_history='current_tool_chain'
    with engine.store, pytest.raises(ValueError):
        asyncio.run(engine.run(MESSAGES))
    assert not engine.adapter.requests


def test_go_external_coordinator_is_rejected_before_credentials(tmp_path):
    from src.agent.runtime_configuration import load_configuration
    from test_role_configuration import case, configuration
    selected=case('external_coordinator_mcp')
    selected.update(provider='opencode-go',model='kimi-k3',reasoning_effort=None,
                    credentials_file='must-not-read.env')
    path=tmp_path/'external.json'
    path.write_text(json.dumps(configuration(selected)))
    with pytest.raises(ValueError,match='single_model and role_division only'):
        load_configuration(path)
