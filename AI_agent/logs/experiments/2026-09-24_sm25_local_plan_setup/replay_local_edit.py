"""Offline controlled regression of the new tool on the real saved declaration."""
import json
from pathlib import Path
import shutil
import tempfile

from scripts.tool_scripts.bim_agent_inputs import freeze_plan_input
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / '2026-09-24_sm25_cold_support_glm_run42'


def main():
    parent = OLD / 'plan_drafts/draft_004/plan.json'
    plan = json.loads(parent.read_text())
    with tempfile.TemporaryDirectory(prefix='sm25-local-controlled-') as tmp:
        run = Path(tmp); (run / 'images').mkdir()
        image = run / 'images/1f_view.png'
        shutil.copyfile(OLD / 'images/1f_view.png', image)
        images = {'1f_view.png': dict(size=[1758,1496], sha256=digest(image))}
        dump(run / 'inputs.json', dict(images=images, scope='Developer-controlled replay, not model input',
            plan_recovery=freeze_plan_input(parent, run, images, '1f_view.png')))
        toolkit = Toolkit(run)
        saved = toolkit.inspect_plan('resume')
        common = dict(reason='Developer-controlled known original-image diagnosis', source_refs=['evaluation-only'])
        operations = [dict(common, op='update', collection='partitions', id='P_corr_north_w',
            changes=dict(points=[[513,957],[695,957]])),
            dict(common, op='add', collection='partitions', value=dict(id='P_corr_north_w_right',
                points=[[792,957],[975,957]], source_refs=['evaluation-only']))]
        result = toolkit.revise_plan('resume', saved['plan_sha256'], json.dumps(operations))
        assert result['source_geometry_ready'], result
        source = json.loads((run / result['candidate'] / 'source_model.json').read_text())
        newplan = toolkit.inspect_plan('draft_001')['declaration']
        assert len(source['spaces']) == 14 and len(source['openings']) == 30
        assert newplan['openings'] == plan['openings']
        unchanged = [r for r in plan['partitions'] if r['id'] != 'P_corr_north_w']
        assert all(r in newplan['partitions'] for r in unchanged)
        dump(HERE / 'controlled_replay.json', dict(mode='developer_controlled_not_model_output',
            parent_sha256=digest(parent), operations=operations,
            unchanged_partitions=len(unchanged), unchanged_openings=len(plan['openings']),
            spaces=len(source['spaces']), openings=len(source['openings']),
            revision=result['plan_revision'], compiler_and_source_geometry_ready=True))


if __name__ == '__main__':
    main()
