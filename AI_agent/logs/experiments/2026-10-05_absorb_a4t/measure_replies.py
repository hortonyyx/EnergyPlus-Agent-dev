"""Compare actual MCP text replies on identical saved sm25 inputs; no models."""
import hashlib
import importlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from scripts.tool_scripts import run_bim_agent as current
from src.agent.geometry import plan_drawing_differences as differences
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent_runtime.agent_registry import agent_version_record

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
WORK=ROOT/'.tmp_a4t'
BASELINE='aa48d72f'
helper=importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a3t.replay_tools')
measure=helper.measure


def main():
    helper.WORK=WORK
    old=measure.baseline_module('scripts/tool_scripts/run_bim_agent.py','a4t_old_runner',BASELINE)
    old_diff=measure.baseline_module('src/agent/geometry/plan_drawing_differences.py','a4t_old_diff',BASELINE)
    name='sm25_runtime_anthropic'
    origin=WORK/'history'/name/'bim'
    calls=helper.audit.steps(origin.parent/'behaviour/record.json.gz')
    selected=[c for c in calls if c['index'] in (80,96,118,119)]
    selected += [dict(index=120,tool='build_plan_bim',
        arguments=dict(image='1f_view.png',plan_json=(origin/'plan_drafts/draft_011/plan.json').read_text()),
        result_data=dict(candidate='candidate_08',plan_input=dict(plan_file='plan_drafts/draft_014/plan.json'))),
        dict(index=121,tool='build_bim',
        arguments=dict(proposal_json=(origin/'candidate_07/proposal.json').read_text()),
        result_data=dict(candidate='candidate_08'))]
    snapshot=agent_version_record(ROOT,verify=True)
    report=dict(baseline_commit=BASELINE,agent_version=snapshot['version_id'],model_requests=0,
        method='Actual MCP text characters; same saved images/calibrations/claim state on both sides. '
               'Four historical calls, plus raw/plan saves of the final saved proposal/draft. '
               'Inputs and geometry are not model regenerated.',rows=[])
    (HERE/'mcp_replies').mkdir(exist_ok=True)
    for call in selected:
        row=dict(tool=call['tool'],step=call['index'],historical_call=call['index']<120)
        geometries=[];images=[];source_bytes=[]
        for side,module in [('before',old),('after',current)]:
            run,context=helper.fixture(name,call,side)
            patch_values={k:getattr(old_diff,k) if side=='before' else getattr(differences,k)
                          for k in ('drawing_differences','compact_differences')}
            with patch.multiple(differences,**patch_values):
                data,pictures,geometry,texts=helper.capture(module,run,call,compile_plan_partition)
            assert data.get('candidate'),data
            target=HERE/'mcp_replies'/f"{call['tool']}_{side}.json"
            target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            report_path=run/data['details_file'] if data.get('details_file') else None
            row[side]=dict(characters=sum(map(len,texts)),candidate=data['candidate'],
                text_sha256=[hashlib.sha256(t.encode()).hexdigest() for t in texts],
                details_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest() if report_path else None,
                precision_total=data.get('building_precision',{}).get('total'),fixture_context=context)
            geometries.append(geometry);images.append(pictures)
            source_bytes.append((run/data['candidate']/'source_model.json').read_bytes())
        row.update(geometry_equal=geometries[0]==geometries[1],images_equal=images[0]==images[1],
                   source_model_bytes_equal=source_bytes[0]==source_bytes[1])
        assert row['geometry_equal'] and row['images_equal'] and row['source_model_bytes_equal'],row
        report['rows'].append(row)
        print(call['tool'],row['before']['characters'],row['after']['characters'],flush=True)
        (HERE/'reply_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        shutil.rmtree(WORK/'mcp_replay'/name/str(call['index']))
    assert agent_version_record(ROOT,verify=True)==snapshot


if __name__=='__main__':main()
