"""Attach source precision diagnostics to existing saves and delivery replies."""
from functools import lru_cache
import json
from statistics import median

import numpy as np
from PIL import Image, ImageDraw

from src.agent.geometry.building_precision import precision_report
from src.agent.geometry.plan_drawing_differences import _axis, _ink, _strokes, _wall_like


@lru_cache(maxsize=24)
def _drawing_width(path, sha256, x_anchors, y_anchors, footprint):
    # The caller verifies the admitted file hash. Cache includes both that hash
    # and the complete calibration/footprint, so scale changes cannot reuse it.
    _, mx = _axis(x_anchors)
    _, my = _axis(y_anchors)
    def pixel(value, anchors):
        (p0, w0), (p1, w1) = anchors
        return p0 + (value-w0) * (p1-p0) / (w1-w0)
    with Image.open(path) as image:
        ring = [(pixel(p[0], x_anchors), pixel(p[1], y_anchors)) for p in footprint]
        inside = Image.new('L', image.size, 0)
        ImageDraw.Draw(inside).polygon(ring, fill=1)
        mask = _ink(image) & np.asarray(inside, dtype=bool)
    widths = []
    for orientation, along, cross in [('v', my, mx), ('h', mx, my)]:
        widths.extend(width for _, lo, hi, width in _wall_like(_strokes(mask, orientation, 2/along), cross)
                      if .05 <= width <= .45 and (hi-lo)*along >= 2)
    # Image estimate only, not a measured construction attribute.
    return median(widths) if len(widths) >= 3 else None


def building_precision(toolkit, candidate, source=None):
    path = toolkit.candidate_path(candidate)
    source = source or json.loads((path/'source_model.json').read_text())
    proposal = json.loads((path/'proposal.json').read_text())
    floors = {f['id']: f for f in source['floors']}
    evidence, errors = {}, []
    for _, calibration in toolkit.registered_calibrations():
        fid = calibration['floor_id']
        if fid not in floors:
            continue
        try:
            anchors = [tuple(map(tuple, calibration[key])) for key in ('x_anchors', 'y_anchors')]
            mpp = [_axis(a)[1] for a in anchors]
            # Implausible plan scales must not grant a kilometres-wide tolerance.
            extent = floors[fid]['footprint']
            spans = [max(p[i] for p in extent)-min(p[i] for p in extent) for i in (0, 1)]
            if not all(2 <= value <= 300 for value in spans) or max(mpp) > .25:
                errors.append(dict(floor_id=fid, reason='scale outside plan precision-check range'))
                continue
            image_path = toolkit.image_path(calibration['image'])
            wall = _drawing_width(str(image_path), calibration['image_sha256'], *anchors, tuple(map(tuple, extent)))
            evidence[fid] = dict(floor_id=fid, metres_per_pixel=mpp, wall_thickness_m=wall,
                basis=dict(calibration_id=calibration['calibration_id'], image=calibration['image'],
                    image_sha256=calibration['image_sha256'],
                    thickness='median long double-line/band width estimate' if wall else 'unknown'))
        except (ValueError, KeyError, TypeError, OSError) as error:
            errors.append(dict(floor_id=fid, reason=str(error)))
    report = precision_report(source, floor_evidence=list(evidence.values()),
                              wall_references=proposal.get('wall_references', []))
    if errors:
        report['evidence_errors'] = errors
    return report
