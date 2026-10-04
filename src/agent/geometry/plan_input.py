"""Unambiguous plan field aliases and local format help; no geometry repair."""
from __future__ import annotations

import copy
import re


def normalize_plan_fields(plan):
    """Only partitions[].pixels and space_seeds[].pixels are aliases.

    Do not guess the meaning of any other pixels field, point nesting or units.
    Both spellings in one object are rejected even if their values look equal.
    """
    if not isinstance(plan, dict):
        return plan, []
    result = copy.deepcopy(plan)
    notes = []
    for collection, field in (('partitions', 'points'), ('space_seeds', 'point')):
        rows = result.get(collection, [])
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or 'pixels' not in row:
                continue
            path = f'plan.{collection}[{index}]'
            if field in row:
                raise ValueError(f'{path}: both pixels and {field} supplied; use only {field}')
            row[field] = row.pop('pixels')
            notes.append(f'{path}.pixels accepted as {path}.{field}; coordinates unchanged.')
    return result, notes


def plan_error_hint(plan, message):
    """Offer the smallest correct shape for the rejected item, with placeholders."""
    examples = {
        'partitions': dict(id='wall-id', points=[[10, 20], [40, 20]], source_refs=['image: observed wall']),
        'space_seeds': dict(id='space-id', point=[20, 30]),
        'openings': dict(id='opening-id', kind='window', p1=[10, 20], p2=[30, 20],
                         z=[1.0, 2.4], source_refs=['image: observed opening']),
    }
    if any(word in message for word in ('polygonize', 'overlap', 'outside footprint',
            'full-boundary hosts', 'full space host', 'occupy the same space', 'outside floor vertical bounds')):
        return dict(note='The item shape parsed; inspect the reported geometry in the original. No snapping, host trimming or unit conversion was applied.')
    match = re.search(r'plan\.(partitions|space_seeds|openings)\[(\d+)\]', message)
    collection, index = (match[1], int(match[2])) if match else (None, None)
    if collection is None:
        for prefix, key in (('partition ', 'partitions'), ('opening ', 'openings'), ('space seed ', 'space_seeds')):
            if message.startswith(prefix) and isinstance(plan, dict):
                rows = plan.get(key, [])
                if isinstance(rows, list):
                    for i, row in enumerate(rows):
                        if isinstance(row, dict) and str(row.get('id', '')) and re.match(re.escape(prefix + str(row['id'])) + r'(?:[: .]|$)', message):
                            collection, index = key, i
                            break
    if collection:
        example = examples[collection].copy()
        if isinstance(plan, dict) and isinstance(plan.get(collection), list) and index < len(plan[collection]):
            row = plan[collection][index]
            if isinstance(row, dict) and isinstance(row.get('id'), str):
                example['id'] = row['id']
                if collection == 'openings' and row.get('kind') in {'window', 'door', 'open', 'passage'}:
                    example['kind'] = row['kind']
        return dict(path=f'plan.{collection}[{index}]', example=example,
                    note='Minimum item format only; replace example coordinates and evidence with observations. No geometry was adjusted.')
    fields = {
        'x_anchors': [[10, 0.0], [110, 10.0]], 'y_anchors': [[10, 10.0], [110, 0.0]],
        'footprint_pixels': [[10, 10], [110, 10], [110, 110], [10, 110]],
        'z_floor': 0.0, 'ceiling_height': 3.0, 'assumptions': [], 'unresolved': [],
        'floor_id': 'F1', 'basis': 'observed calibration',
    }
    for field, value in fields.items():
        if field in message:
            return dict(path='plan.' + field, example={field: value},
                        note='Format example only; world values use metres, pixel values use original image coordinates.')
    for key, example in examples.items():
        if f'plan.{key}' in message:
            return dict(path='plan.' + key, example={key: [example]})
    # Do not offer a guessed coordinate correction for a topology/host failure.
    if any(word in message for word in ('polygonize', 'overlap', 'outside footprint', 'scale')):
        return dict(note='Keep declared coordinates; inspect the reported objects in the original. No snapping or unit conversion was applied.')
    return dict(path='plan_json', example={'floor_id':'F1','z_floor':0.0,'ceiling_height':3.0,
        'x_anchors':fields['x_anchors'],'y_anchors':fields['y_anchors'],'basis':'observed calibration',
        'footprint_pixels':fields['footprint_pixels'],'partitions':[],'openings':[],
        'assumptions':[],'unresolved':[]}, note='Minimum plan shape; example coordinates are not observations.')
