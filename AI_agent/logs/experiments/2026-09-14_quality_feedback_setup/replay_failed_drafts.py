"""Replay run17's exact rejected declarations through the new feedback path, offline."""
from pathlib import Path
import html
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.geometry.plan_draft_view import render_plan_draft


if __name__ == '__main__':
    setup = Path(__file__).resolve().parent
    old = setup.parent / '2026-09-14_bim_agent_sm24_run17'
    out = setup / 'failed_draft_replay'
    out.mkdir(exist_ok=False)
    (out / 'images').mkdir()
    name = '1f_view.png'
    shutil.copyfile(old / 'images' / name, out / 'images' / name)
    with Image.open(out / 'images' / name) as picture:
        size = list(picture.size)
    dump(out / 'inputs.json', {
        'images': {name: {'size': size, 'sha256': digest(out / 'images' / name)}},
        'input_mode': 'historical_failed_declaration_replay',
        'scope': 'Offline feedback diagnosis only; not a fresh product-model generation.',
    })
    toolkit = Toolkit(out)
    rows, panels = [], []
    for folder in sorted((old / 'plan_drafts').glob('draft_*')):
        raw = (folder / 'plan.json').read_text()
        previous = json.loads((folder / 'result.json').read_text())
        result = toolkit.build_plan(name, raw)
        record = result['plan_input']
        preview = record['draft_view']
        metadata = json.loads((out / preview['metadata_file']).read_text())
        with Image.open(out / 'images' / name) as original:
            replay, replay_metadata = render_plan_draft(original, json.loads(raw),
                image_name=name, image_sha256=record['image_sha256'],
                plan_file=record['plan_file'], plan_sha256=record['plan_sha256'])
        with Image.open(out / preview['image_file']) as saved:
            pixels_match = replay.size == saved.size and ImageChops.difference(
                replay.convert('RGB'), saved.convert('RGB')).getbbox() is None
        checks = {
            'same_original_error': result['error'] == previous['error'],
            'same_raw_input': (out / record['plan_file']).read_bytes() == (folder / 'plan.json').read_bytes(),
            'same_plan_hash': record['plan_sha256'] == previous['plan_input']['plan_sha256'],
            'same_original_image_hash': record['image_sha256'] == previous['plan_input']['image_sha256'],
            'preview_bytes_match_hash': digest(out / preview['image_file']) == preview['image_sha256'],
            'metadata_bytes_match_hash': digest(out / preview['metadata_file']) == preview['metadata_sha256'],
            'preview_replay_matches': pixels_match,
            'metadata_replay_matches': all(metadata.get(key) == value for key, value in replay_metadata.items()),
            'explicitly_unbuilt': result['source_geometry_ready'] is False and not result.get('candidate'),
        }
        rows.append({'original_draft': folder.name, 'error': result['error'], 'checks': checks})
        panels.append(f'<article><h2>{html.escape(folder.name)}</h2><pre>{html.escape(result["error"])}</pre>'
                      f'<img src="{html.escape(preview["image_file"])}" alt="原始失败声明叠图"></article>')
    report = {'mode': 'offline historical failure replay; no model calls', 'drafts': rows,
              'no_source_candidate': not list(out.glob('candidate_*')),
              'all_checks_passed': bool(rows) and all(all(row['checks'].values()) for row in rows),
              'limits': 'Shows the same rejected claims on the original. No corrected geometry, room fidelity, autonomous feedback use or model improvement is established.'}
    dump(out / 'verification.json', report)
    (out / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>失败墙网叠图重放</title>'
        '<style>body{font:16px system-ui;margin:2em;max-width:1200px}img{max-width:100%}pre{white-space:pre-wrap}article{margin:3em 0}</style>'
        '<h1>失败墙网叠图重放</h1><p>两份原始错误完整保留。这里仅显示模型曾声明的墙和开口，不是修正后的BIM，也不是新生成结果。</p>'
        + ''.join(panels), encoding='utf-8')
    assert report['all_checks_passed'] and report['no_source_candidate'], report
    print(json.dumps(report, ensure_ascii=False, indent=2))
