"""Model-facing summaries; full immutable replies remain readable through MCP.

A3-T usage audit: five GLM/Qwen/T1 runs reuse IDs, draft hashes, calibration,
partition coordinates and opening heights. Keep those; remove duplicated
provenance, polygon/vertex copies and projection internals from routine replies.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

COMPACT_TOOLS = frozenset({'build_bim', 'build_plan_bim', 'revise_bim', 'revise_plan_bim',
                          'build_parametric_bim', 'assemble_plan_bim', 'check_openings', 'finish_bim'})


def pick(value, keys):
    return {key: value[key] for key in keys if key in value}


def table(rows):
    """Keep every selected value and its column while writing repeated keys once."""
    if not rows:
        return rows
    columns = list(dict.fromkeys(key for row in rows for key in row))
    return dict(columns=columns, rows=[[row.get(key) for key in columns] for row in rows])


def compilation_summary(value, *, inventory_present=False):
    result = pick(value, ('mode', 'floor_id', 'image_name', 'image_size', 'space_count', 'footprint'))
    result['calibration'] = pick(value.get('calibration', {}),
        ('status', 'world_metres_per_pixel', 'x_anchors', 'y_anchors'))
    result['partition_mapping'] = [pick(row, ('id', 'partition_id', 'pixel_points', 'world_points_m'))
                                   for row in value.get('partition_mapping', [])]
    result['space_mapping'] = [pick(row, ('space_id', 'seed', 'source_refs'))
                               for row in value.get('space_mapping', [])]
    result['opening_hosts'] = [pick(row, ('opening_id', 'p1_pixel', 'p2_pixel', 'width_m')) if inventory_present
                               else {k: v for k, v in row.items() if k != 'source_refs'}
                               for row in value.get('opening_hosts', [])]
    for key in ('partition_mapping', 'space_mapping', 'opening_hosts'):
        result[key] = table(result[key])
    return result


def inventory_summary(value):
    result = pick(value, ('counts', 'opening_count', 'scope'))
    result['floors'] = []
    for floor in value.get('floors', []):
        row = pick(floor, ('floor_id', 'counts', 'opening_count'))
        columns = ('id', 'kind', 'space_ids', 'plan_endpoints', 'z_m', 'exterior')
        if any('floor_ids' in opening for opening in floor.get('openings', [])):
            columns += ('floor_ids',)
        row['columns'], row['rows'] = list(columns), []
        for opening in floor.get('openings', []):
            item = dict(opening)
            zs = [v[2] for v in opening.get('vertices', [])]
            if zs:
                item['z_m'] = [min(zs), max(zs)]
            row['rows'].append([item.get(key) for key in columns])
        result['floors'].append(row)
    result['spaces'] = table([pick(row, ('space_id', 'floor_id', 'opening_count', 'counts'))
                             for row in value.get('spaces', [])])
    return result


def projection_summary(value):
    # The image itself is still delivered, so retain its coordinate frame/legend.
    rows = []
    for row in value:
        summary = pick(row, ('candidate', 'floor_id', 'image', 'image_sha256', 'source_model_sha256', 'anchors',
            'box_original_pixels', 'original_size', 'returned_size', 'original_pixels_per_returned_pixel',
            'overlay_image', 'overlay_metadata', 'legend', 'out_of_image', 'calibration_unverified',
            'drawing_fidelity', 'automatic_projection', 'trigger_action'))
        if 'reused_calibration' in row:
            summary['reused_calibration'] = pick(row['reused_calibration'],
                ('calibration_id', 'registered_by_candidate', 'image', 'floor_id'))
        evidence = row.get('wall_evidence_projection', {})
        if evidence.get('endpoints') or evidence.get('walls'):
            summary['wall_evidence_projection'] = evidence
        rows.append(summary)
    return rows



def summarize_reply(result):
    """Pure presentation: errors, findings, IDs, heights and geometry stay explicit."""
    reply = copy.deepcopy(result)
    precision = reply.get('building_precision')
    if isinstance(precision, dict) and precision.get('status') == 'reported':
        precision['items'] = table(precision['items'][:8])
        precision['truncated'] = precision['total'] > 8
        # Exact evidence and all findings are in the ordinary A3-T details file.
        for row in precision.get('tolerances', {}).values():
            row.pop('basis', None)
            row.pop('rule', None)
    if isinstance(precision, dict) and isinstance(precision.get('wall_placement'), dict):
        placement = precision['wall_placement']
        placement['items'] = placement['items'][:4]
        placement['truncated'] = placement['total'] > 4
    for key in ('opening_inventory', 'inventory'):
        if isinstance(reply.get(key), dict):
            reply[key] = inventory_summary(reply[key])
    if isinstance(reply.get('plan_compilation'), dict):
        reply['plan_compilation'] = compilation_summary(reply['plan_compilation'], inventory_present='opening_inventory' in reply)
    if isinstance(reply.get('source_image_projections'), list):
        reply['source_image_projections'] = projection_summary(reply['source_image_projections'])
    if isinstance(reply.get('provenance'), dict):
        # plan_input and assembly already exist at the top level; hash bindings
        # and claim application file references remain in their original places.
        reply['provenance'] = {k: v for k, v in reply['provenance'].items()
                               if k not in {'plan_input', 'plan_assembly'}}
    application = reply.get('claim_application')
    if (isinstance(application, dict) and 'submitted_operations' in application
            and application['submitted_operations'] == application.get('resolved_operations')):
        # Equality only: resolved values/IDs remain, and actual changes remain whole.
        application.pop('submitted_operations')
        application['submitted_operations_equal_resolved'] = True
    return reply


def compact_reply(run: Path, tool: str, result: dict, *, full_result: dict | None = None) -> dict:
    if tool not in COMPACT_TOOLS:
        return result
    reply = summarize_reply(result)
    if reply == result and full_result is None:
        return result
    raw = (json.dumps(result if full_result is None else full_result, ensure_ascii=False, indent=2) + '\n').encode()
    sha = hashlib.sha256(raw).hexdigest()
    relative = f'tool_reports/{tool}_{sha}.json'
    path = run / relative
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        path.write_bytes(raw)
    reply.update(details_file=relative, details_sha256=sha,
        details_read='read_candidate_items(candidate="", collection="report", report_file=details_file); offset/limit page by characters.')
    return reply


def read_report(run: Path, report_file: str, offset: int, limit: int) -> dict:
    """Read only an immutable tool reply; cannot reach arbitrary run/private files."""
    path = (run / report_file).resolve()
    folder = (run / 'tool_reports').resolve()
    if path.parent != folder or path.suffix != '.json' or not path.is_file():
        raise ValueError('report_file must be a saved tool_reports/*.json path from a tool reply')
    if offset < 0 or not 1 <= limit <= 12000:
        raise ValueError('report requires offset >= 0 and limit 1..12000 characters')
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if not path.stem.endswith('_' + sha):
        raise ValueError('saved tool report hash mismatch')
    text = raw.decode()
    page = text[offset:offset + limit]
    return dict(report_file=report_file, sha256=sha, text=page, offset=offset,
                next_offset=offset+len(page) if offset+len(page)<len(text) else None,
                total_characters=len(text), page_is_partial=bool(offset or len(page)<len(text)))
