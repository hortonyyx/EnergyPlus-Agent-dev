"""Replay a real failed wall network through full-path support, without a model."""
import json
from pathlib import Path
import shutil

from scripts.tool_scripts.run_bim_agent import Toolkit, dump, digest

HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'2026-09-24_sm24_cold_context_glm_run37'


def main():
    run = HERE/'replay'
    (run/'images').mkdir(parents=True, exist_ok=False)
    shutil.copy2(OLD/'images/1f_view.png', run/'images/1f_view.png')
    dump(run/'inputs.json', dict(images=json.loads((OLD/'inputs.json').read_text())['images'],
        provider='glm', input_mode='developer_offline_tool_replay_no_model'))
    kit = Toolkit(run)
    result = kit.build_plan('1f_view.png', (OLD/'plan_drafts/draft_002/plan.json').read_text())
    assert result['source_geometry_ready']
    source = run/result['candidate']/'source_model.json'
    before = digest(source)
    report = json.loads(kit.plan_wall_support('draft_001', [128]*3, 70, 6, 1)[1])
    assert digest(source) == before
    longest = report['review_intervals'][0]
    assert longest['partition_id'] == 'P_corridor_east'
    assert longest['points'][0][1] <= 595 and longest['points'][1][1] >= 690
    assert set(longest['proposed_adjacent_space_ids']) == {'corridor', 'zoneA'}
    assert any(s['declared_openings'] for s in report['segments'])
    dump(run/'replay_audit.json', dict(source_unchanged=True, longest_unsupported_interval=longest,
        all_paths_measured=len(report['segments']), input_plan_sha256=digest(OLD/'plan_drafts/draft_002/plan.json'),
        no_geometry_repair_or_model_call=True))
    print(json.dumps(longest, indent=2))


if __name__ == '__main__':
    main()
