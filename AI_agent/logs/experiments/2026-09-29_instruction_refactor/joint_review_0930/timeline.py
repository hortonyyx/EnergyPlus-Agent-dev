"""Print a compact behaviour timeline of one BIM agent run from agent_stream.jsonl.gz."""
import gzip, json, sys, datetime
from pathlib import Path

run = Path(sys.argv[1])
full_text = '--full' in sys.argv
width = 700 if full_text else 260

def ts(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()

def summarize(name, inp):
    n = name.replace('mcp__bim__', '')
    try:
        if n == 'view_image':
            return f"{n} {inp.get('name') or inp.get('image')} box={inp.get('box')} scale={inp.get('display_scale')}"
        if n == 'get_bim_reference':
            return f"{n} {inp.get('topic')}"
        if n in ('build_plan_bim',):
            pj = json.loads(inp.get('plan_json', '{}'))
            return (f"{n} {inp.get('image')} floor={pj.get('floor_id')} parts={len(pj.get('partitions', []))} "
                    f"open={len(pj.get('openings', []))} seeds={len(pj.get('space_seeds', []))} unresolved={len(pj.get('unresolved', []))}")
        if n == 'revise_plan_bim':
            ops = json.loads(inp.get('operations_json', '[]'))
            return f"{n} {inp.get('draft_id')} ops=" + ','.join(f"{o.get('op')}:{o.get('collection', o.get('field'))}:{o.get('id', '')}" for o in ops)[:200]
        if n == 'revise_bim':
            ops = json.loads(inp.get('operations_json', '[]'))
            return f"{n} {inp.get('candidate')} ops=" + ','.join(f"{o.get('op')}:{o.get('id', o.get('space_id', ''))}" for o in ops)[:200]
        if n == 'assemble_plan_bim':
            fl = json.loads(inp.get('floors_json', '[]'))
            return f"{n} " + ','.join(f"{f.get('draft_id')}@{f.get('z_floor')}" for f in fl)
        if n in ('view_pixel_profile', 'pixel_profile'):
            return f"{n} {inp.get('image') or inp.get('name')} axis={inp.get('axis')} box={inp.get('box')}"
        if n == 'record_claim':
            cj = json.loads(inp.get('claim_json', '{}'))
            return f"{n} cand={cj.get('candidate')} objs={[o.get('id') for o in cj.get('objects', [])][:6]} basis={cj.get('basis')}"
        if n == 'check_source_space_relation':
            return f"{n} {inp.get('candidate')} {inp.get('image')}"
        if n == 'view_elevation_candidate':
            return f"{n} {inp.get('candidate')} {inp.get('facade')} {inp.get('image')} anchors={'horizontal_anchors' in inp}"
        if n == 'overlay_candidate':
            return f"{n} {inp.get('candidate')} {inp.get('image')}"
        if n == 'finish_bim':
            return f"{n} {inp.get('candidate')}"
        s = json.dumps(inp, ensure_ascii=False)
        return f"{n} {s[:160]}"
    except Exception as exc:  # malformed JSON input from the model
        return f"{n} <unparsed {exc}> {str(inp)[:120]}"

start = None
pending = {}
step = 0
with gzip.open(run / 'agent_stream.jsonl.gz', 'rt') as f:
    for line in f:
        e = json.loads(line)
        t = e.get('type')
        if t == 'user' and e.get('timestamp') and start is None:
            start = ts(e['timestamp'])
        if t == 'assistant':
            for c in e['message']['content']:
                if c['type'] == 'text' and c['text'].strip():
                    txt = c['text'].strip().replace('\n', ' | ')
                    print(f"      TEXT: {txt[:width]}")
                elif c['type'] == 'tool_use':
                    step += 1
                    pending[c['id']] = (step, summarize(c['name'], c['input']))
        elif t == 'user':
            for c in e['message']['content']:
                if isinstance(c, dict) and c.get('type') == 'tool_result':
                    st, summ = pending.pop(c['tool_use_id'], (0, '?'))
                    content = c.get('content')
                    size = 0; imgs = 0
                    if isinstance(content, list):
                        for part in content:
                            if part.get('type') == 'text':
                                size += len(part.get('text', ''))
                            elif part.get('type') == 'image':
                                imgs += 1
                    elif isinstance(content, str):
                        size = len(content)
                    err = ' ERROR' if c.get('is_error') else ''
                    el = ts(e['timestamp']) - start if start and e.get('timestamp') else -1
                    print(f"{st:3d} {el:7.1f}s {summ}  -> {size} chars {imgs} img{err}")
        elif t == 'result':
            print('RESULT duration_ms', e.get('duration_ms'), 'turns', e.get('num_turns'), 'cost', e.get('total_cost_usd'))
            if full_text:
                print(e.get('result', '')[:6000])
