"""Verify view reuse against actual CLI image bytes; semantic review stays separate."""
import argparse
import base64
import gzip
import hashlib
import importlib
import io
import json
from pathlib import Path

from PIL import Image

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, coordinate_grid_view
from src.agent.execution.bim_claims import sha


def audit(run):
    assert (run / 'summary.json').is_file()
    # Retain the earlier exact crop exporter and its original-tool transport check.
    importlib.import_module('AI_agent.logs.experiments.2026-09-27_sm24_claim_regions_setup.claim_crops').audit(run)
    toolkit = Toolkit(run)
    seen, calls, returned, replacements = set(), {}, [], []
    streams = [run / 'agent_stream.jsonl.gz', *sorted(run.glob('continuation_*_stream.jsonl.gz'))]
    for stream in streams:
        for line in gzip.decompress(stream.read_bytes()).splitlines():
            event = json.loads(line)
            blocks = event.get('message', {}).get('content', [])
            for block in blocks if isinstance(blocks, list) else []:
                if block.get('type') == 'tool_use':
                    calls[block['id']] = {**block, 'previously_returned_views': sorted(seen)}
                if block.get('type') != 'tool_result':
                    continue
                call = calls.get(block['tool_use_id'], {})
                tool = call.get('name', '').rsplit('__', 1)[-1]
                if tool not in {'view_image', 'record_claim', 'view_claim_evidence', 'replace_claim_sources'}:
                    continue
                if block.get('is_error'):
                    continue  # Errors remain in the complete transport audit; no successful view.
                pictures, metas, structured = [], [], []
                for part in block.get('content', []):
                    if part.get('type') == 'image':
                        pictures.append(part)
                    elif part.get('type') == 'text':
                        try:
                            obj = json.loads(part['text'])
                        except ValueError:
                            continue
                        if isinstance(obj, dict) and 'view_id' in obj and 'returned_png_sha256' in obj:
                            metas.append(obj)
                        if isinstance(obj, dict) and 'evidence_previews' in obj:
                            structured = obj['evidence_previews']
                metas = metas or structured
                assert len(metas) == len(pictures), (tool, len(metas), len(pictures))
                for picture, meta in zip(pictures, metas):
                    raw = base64.b64decode(picture['source']['data'])
                    saved = toolkit.read_image_view(meta['view_id'])
                    assert saved['sha256'] == meta['view_record_sha256']
                    assert hashlib.sha256(raw).hexdigest() == saved['record']['returned_png_sha256']
                    region = saved['record']['box_original_pixels']
                    assert region == meta['box_original_pixels']
                    with Image.open(run / 'images' / meta['name']) as original:
                        expected = original.convert('RGB').crop(region)
                    if meta['display_scale_requested'] == 1:
                        expected.thumbnail((1600, 1600))
                    else:
                        expected = expected.resize(tuple(meta['returned_size']), Image.Resampling.NEAREST)
                    if meta['coordinate_grid']['shown']:
                        expected, _ = coordinate_grid_view(expected, region)
                    actual = Image.open(io.BytesIO(raw)).convert('RGB')
                    assert actual.size == expected.size and actual.tobytes() == expected.tobytes()
                    returned.append(dict(view_id=meta['view_id'], tool=tool,
                        image=meta['name'], box=region, actual_transport_sha256=hashlib.sha256(raw).hexdigest(),
                        pixels_match_original=True, stream=stream.name))
                    seen.add(meta['view_id'])
                if tool == 'replace_claim_sources':
                    ids = call['input']['view_ids']
                    assert set(ids) <= set(call['previously_returned_views'])
                    replacements.append(dict(old_claim=call['input']['claim_id'], view_ids=ids,
                        all_views_returned_before_replacement=True))

    provenance = []
    for path in sorted((run / 'claims').glob('claim_*.json')):
        row = json.loads(path.read_text())
        for ref in row['sources']:
            if 'view_id' in ref:
                assert ref['view_id'] in seen
                assert digest(run / 'image_views' / (ref['view_id'] + '.json')) == ref['view_sha256']
        if 'replaces_claim' not in row:
            continue
        old = toolkit.claims().read(row['replaces_claim'])
        assert sha(old) == row['replaced_claim_sha256']
        for key in ('candidate', 'objects', 'values', 'basis', 'value_targets', 'unresolved', 'observation_mode'):
            assert row['claim'][key] == old['claim'][key]
        assert row['resolved_values'] == old['resolved_values']
        assert row['parent_proposal_sha256'] == old['parent_proposal_sha256']
        provenance.append(dict(old_claim=old['id'], new_claim=row['id'], values_and_objects_preserved=True,
            old_decision=toolkit.claims().decisions().get(old['id']),
            new_decision=toolkit.claims().decisions().get(row['id'])))
    report = dict(returned=returned, replacements=replacements, replacement_provenance=provenance,
        image_count=len(returned), replacement_count=len(replacements),
        actual_transport_bytes_and_pixels_verified=True,
        note='Actual return and deterministic source replacement, not automatic image understanding or semantic acceptance.')
    dump(run / 'evaluation/view_reference_audit.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('returned','replacements','replacement_provenance')}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    audit(parser.parse_args().run.resolve())
