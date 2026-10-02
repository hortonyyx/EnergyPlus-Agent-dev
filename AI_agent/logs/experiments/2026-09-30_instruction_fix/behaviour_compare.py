"""Phase-by-phase behaviour of BIM agent runs from their public tool log and stream."""
import gzip, json, sys
from collections import Counter
from pathlib import Path

EXP = Path('/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments')
RUNS = {'run57': '2026-09-26_sm21_whole_building_claude_run57', 'run58': '2026-09-27_sm21_whole_building_repeat_claude_run58',
        'run93': '2026-09-29_sm21_aligned_prompt_run93', 'run94': '2026-09-29_sm21_instruction_refactor_run94',
        'run98': '2026-09-30_sm21_instruction_fix_run98'}
PLAN_BUILD = {'build_plan_bim', 'build_bim'}
HEIGHT = {'view_elevation_candidate', 'record_claim', 'decide_claim', 'confirm_claims', 'view_claim_evidence', 'check_openings'}


def stream_calls(run):
    """Tool calls in order with name, input, error flag, and elapsed seconds."""
    path = run / 'agent_stream.jsonl.gz'
    opener = gzip.open(path, 'rt') if path.exists() else open(run / 'agent_stream.jsonl')
    calls, pending, start, out_tokens = [], {}, None, 0
    import datetime
    with opener as f:
        for line in f:
            e = json.loads(line)
            if e.get('type') == 'user' and e.get('timestamp') and start is None:
                start = datetime.datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')).timestamp()
            if e.get('type') == 'assistant':
                for c in e['message']['content']:
                    if c['type'] == 'tool_use':
                        pending[c['id']] = dict(name=c['name'].replace('mcp__bim__', ''), input=c['input'])
            elif e.get('type') == 'user':
                for c in e['message']['content']:
                    if isinstance(c, dict) and c.get('type') == 'tool_result':
                        call = pending.pop(c['tool_use_id'], None)
                        if call is None:
                            continue
                        t = datetime.datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')).timestamp() - start
                        calls.append(dict(**call, t=round(t, 1), error=bool(c.get('is_error'))))
            elif e.get('type') == 'result':
                usage = e.get('usage') or {}
                out_tokens = usage.get('output_tokens') if isinstance(usage, dict) else None
                turns = e.get('num_turns')
    return calls, out_tokens, turns


def views(run):
    rows = [json.loads(l) for l in (run / 'tools.jsonl').read_text().splitlines()]
    t0 = rows[0]['time']
    out = []
    for r in rows:
        if r['action'] == 'view_image':
            d = r['data']
            full = d.get('box_original_pixels') == [0, 0, *d['original_size']]
            out.append(dict(t=round(r['time'] - t0, 1), name=d['name'], full=full,
                            scale=round(min(d['display_scale_actual']), 2)))
    return out


def summary(label):
    run = EXP / RUNS[label]
    calls, out_tokens, turns = stream_calls(run)
    ok = [c for c in calls if not c['error']]
    first = next(c['t'] for c in calls if c['name'] in PLAN_BUILD)
    builds = [c['t'] for c in ok if c['name'] in PLAN_BUILD]
    assembled = next((c['t'] for c in ok if c['name'] == 'assemble_plan_bim'), None)
    height_start = next((c['t'] for c in calls if c['name'] in HEIGHT or
                         (c['name'] == 'view_image' and 'view' in str(c['input'].get('name', '')).lower()
                          and not str(c['input'].get('name', '')).startswith(('1f', '2f')) and c['t'] > (assembled or first))), None)
    finish = max(c['t'] for c in calls if c['name'] == 'finish_bim')
    before = [c for c in calls if c['t'] < first]
    v = views(run)
    v_before = [x for x in v if x['t'] < first]
    crops_before = [x for x in v_before if not x['full']]
    plan_views_after = [x for x in v if x['t'] >= first and x['name'] in ('1f_view.png', '2f_view.png')]
    elev_crops = [x for x in v if not x['full'] and x['name'] not in ('1f_view.png', '2f_view.png')]
    names = Counter(c['name'] for c in calls)
    return dict(
        run=label, total_s=finish, turns=turns, output_tokens=out_tokens, tool_calls=len(calls),
        tool_errors=sum(c['error'] for c in calls),
        references=[c['input'].get('topic') for c in calls if c['name'] == 'get_bim_reference'],
        first_build_s=first, calls_before_first_build=len(before),
        full_views_before=sum(x['full'] for x in v_before), crops_before=len(crops_before),
        crop_scale_before=sorted(x['scale'] for x in crops_before),
        pixel_tools_before=sum('pixel' in c['name'] for c in before),
        plan_builds_s=builds, assembled_s=assembled,
        plan_revisions=names['revise_plan_bim'], plan_views_after_first_build=len(plan_views_after),
        height_phase_start_s=height_start, height_phase_s=round(finish - height_start, 1) if height_start else None,
        elevation_overlays=names['view_elevation_candidate'], elevation_crops=len(elev_crops),
        claims=names['record_claim'], relation_checks=names['check_source_space_relation'],
        wall_support_checks=names['view_plan_wall_support'], overlay_checks=names['overlay_candidate'],
        candidate_revisions=names['revise_bim'], finish_calls=names['finish_bim'])


if __name__ == '__main__':
    rows = [summary(label) for label in (sys.argv[1:] or RUNS)]
    print(json.dumps(rows, ensure_ascii=False, indent=1))
