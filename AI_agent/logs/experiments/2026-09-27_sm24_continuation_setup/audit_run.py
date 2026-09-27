"""Post-run evaluation and lossless multi-turn transport audit; never model input."""
import argparse
import base64
from collections import Counter
import gzip
import importlib
import io
import json
from pathlib import Path

from PIL import Image

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.execution.bim_height_coverage import height_coverage
from src.agent.roles import room_use_review

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
load = lambda path: json.loads(path.read_text())


def archive_streams(run):
    reports = []
    for request in sorted(run.glob('*_request.json')):
        name = request.name.removesuffix('_request.json')
        stream = run / f'{name}_stream.jsonl'
        archive = stream.with_suffix('.jsonl.gz')
        raw = stream.read_bytes() if stream.exists() else gzip.decompress(archive.read_bytes())
        calls, images, errors, finishes, decisions = {}, [], [], [], []
        for line in raw.splitlines():
            event = json.loads(line)
            content = event.get('message', {}).get('content', [])
            for block in content if isinstance(content, list) else []:
                if block.get('type') == 'tool_use':
                    calls[block['id']] = block['name']
                if block.get('type') != 'tool_result':
                    continue
                tool = calls.get(block['tool_use_id'], 'unknown')
                value = block.get('content', [])
                parts = [{'type': 'text', 'text': value}] if isinstance(value, str) else value
                for part in parts:
                    if part.get('type') == 'image':
                        data = base64.b64decode(part['source']['data'])
                        with Image.open(io.BytesIO(data)) as image:
                            image.load()
                            images.append(dict(tool=tool, size=list(image.size), bytes=len(data)))
                    if part.get('type') != 'text':
                        continue
                    text = part['text']
                    if block.get('is_error'):
                        errors.append(dict(tool=tool, text=text))
                    if tool.endswith(('finish_bim', 'record_work_review')):
                        try:
                            payload = json.loads(text)
                        except ValueError:
                            payload = {}
                        row = dict(tool=tool, characters=len(text), candidate=payload.get('candidate'),
                            detached_output_notice='persisted-output' in text or 'Full output saved to' in text,
                            room_use_review=payload.get('room_use_review'),
                            height_summary=payload.get('height_coverage', {}).get('summary'))
                        (finishes if tool.endswith('finish_bim') else decisions).append(row)
        compressed = gzip.compress(raw, mtime=0)
        assert gzip.decompress(compressed) == raw
        archive.write_bytes(compressed)
        import hashlib
        reports.append(dict(turn=name, tools=dict(Counter(calls.values())), errors=errors,
            images=images, image_count=len(images), all_images_decode=True, finishes=finishes,
            decisions=decisions, archive=archive.name, original_bytes=len(raw), gzip_bytes=len(compressed),
            original_sha256=hashlib.sha256(raw).hexdigest(), gzip_sha256=digest(archive), lossless_verified=True))
        if stream.exists():
            stream.unlink()
    dump(run / 'transport_audit.json', dict(turns=reports,
        image_count=sum(row['image_count'] for row in reports),
        note='Actual CLI replies, not just server logs. Transport/coverage is not semantic acceptance.'))
    return reports


def audit(run):
    assert (run / 'summary.json').is_file()
    frozen = load(HERE / f'{run.name}_frozen.json')
    manifest, summary, delivery = [load(run / name) for name in ('inputs.json', 'summary.json', 'delivery.json')]
    assert manifest['scope'] == frozen['scope']
    assert digest(run / 'seed/proposal.json') == frozen['seed_proposal_sha256']
    assert manifest['continuation_rounds'] == frozen['continuation_rounds']
    assert not manifest['input_contents']['ground_truth_or_evaluation']['included']
    assert not manifest['input_contents']['building_declaration']['included']
    producer = run / 'runtime_snapshot' if (run / 'runtime_snapshot').exists() else ROOT
    assert all(digest(producer / name) == sha for name, sha in manifest['implementation_sha256'].items())
    assert all(digest(run / 'images' / name) == sha == manifest['images'][name]['sha256']
               for name, sha in frozen['image_sha256'].items())
    receipts = [load(p) for p in sorted(run.glob('*_receipt.json'))]
    assert len(receipts) == summary['subscription_invocations']
    assert all(r['actual_model'].startswith('claude-sonnet-') and r['provider'] == 'claude'
               and not r.get('timed_out') and not r.get('routing_error') and r.get('returncode') == 0
               and not r['result'].get('is_error') for r in receipts)
    toolkit = Toolkit(run)
    assert toolkit.input_view_status() == delivery['input_view_status']
    assert height_coverage(toolkit.claims(), delivery['candidate']) == delivery['height_coverage']
    shared = importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run')
    source, _, _ = shared.replay_final(run, delivery['candidate'])
    assert room_use_review(source) == delivery['room_use_review']
    seed = load(run / 'seed/source_model.json')
    fields = ('floors', 'boundaries', 'openings', 'connections', 'opening_hosts', 'boundary_relations')
    preserved = {key: seed[key] == source[key] for key in fields}
    physical = lambda value: [{key: row[key] for key in ('id', 'floor_id', 'polygon', 'z_floor', 'height')}
                              for row in value['spaces']]
    preserved['space_geometry'] = physical(seed) == physical(source)
    original = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.audit_run')
    original.audit(run)
    from src.agent.judge.gt import load_gt_document
    partition = load(run / 'evaluation/partition.json')
    opening = shared._opening_diagnostic(source, load_gt_document('sm24_anchor'), partition)
    dump(run / 'evaluation/exterior_opening_diagnostic.json', opening)
    transports = archive_streams(run)
    actions = [json.loads(line) for line in (run / 'tools.jsonl').read_text().splitlines()]
    assert not any(row['action'] == 'review_detail' for row in actions)
    identity_codes = {'source_space_split', 'source_spaces_merged', 'missing_source_space',
                      'extra_source_space', 'floor_assignment_changed', 'candidate_spaces_overlap'}
    report = dict(candidate=delivery['candidate'], source_model_sha256=source['source_model_sha256'],
        input_and_producer_hashes_verified=True, source_display_replay_exact=True,
        counts={key: len(source[key]) for key in ('spaces', 'boundaries', 'openings', 'connections')},
        preserved_vs_seed=preserved, continuation=summary['continuation'],
        invocations=len(receipts), actual_models=[r['actual_model'] for r in receipts],
        elapsed_seconds=summary['elapsed_seconds'], estimated_usd_not_bill=summary['estimated_cost_usd'],
        room_use=delivery['room_use_review'], height_coverage=delivery['height_coverage']['summary'],
        roles=[{key: space[key] for key in ('id', 'role', 'role_evidence')} for space in source['spaces']],
        source_assumptions=source['assumptions'], unresolved=source['generation']['unresolved'],
        original_plan=load(run / 'postrun_audit.json'),
        strict_partition=partition['comparison']['status'],
        identity_findings=[r for r in partition['comparison']['findings'] if r['code'] in identity_codes],
        exterior_match_count=sum(all(r.get(key) is True for key in
            ('along_within_judge_tolerance', 'width_within_judge_tolerance', 'z_within_judge_tolerance', 'host_zone_match'))
            for r in opening['matched']),
        tool_counts=dict(Counter(row['action'] for row in actions)),
        transported_images=sum(row['image_count'] for row in transports),
        limits=['Saved-proposal recovery with bounded main-agent follow-ups, not cold generation.',
                'Structured roles and height bindings do not certify interpretation or image truth.',
                'Existing seed geometry errors are not made correct by metadata review.',
                'A model stop is not an independent verdict that all scope is complete.'])
    dump(run / 'continuation_audit.json', report)
    print(json.dumps({k: report[k] for k in ('candidate', 'counts', 'preserved_vs_seed', 'invocations',
        'elapsed_seconds', 'room_use', 'height_coverage', 'strict_partition', 'exterior_match_count')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    audit(parser.parse_args().run.resolve())
