"""Feasibility probe (review only, not product code): compare original plan ink with a
compiled pixel-plan declaration.

Reports, per floor draft:
  UNDECLARED  long straight interior ink runs that touch declared walls/perimeter at both
              ends but lie on no declared partition (candidate missed divider);
  UNSUPPORTED declared partition segments whose strip has little non-background ink;
  GAPS        interior-wall gaps without a declared opening, and declared doors whose
              wall strip is continuous ink.
Background colour is estimated from the image; no caller colour or threshold is needed.
"""
import json, sys, glob, os
from collections import Counter
import numpy as np
from PIL import Image

MIN_RUN_M = 1.2        # shortest straight run treated as a possible wall line
BAND_MERGE_PX = 14     # parallel runs this close form one wall candidate (double line)
COVER_PX = 12          # declared partition within this distance covers the candidate
END_TOUCH_PX = 14      # candidate end must come this close to a declared wall/perimeter
MARGIN_PX = 6          # stay off the footprint edge band


def background_mask(img):
    a = np.asarray(img.convert('RGB')).astype(int)
    q = (a // 16).reshape(-1, 3)
    mode = Counter(map(tuple, q[:: max(1, len(q) // 200000)])).most_common(1)[0][0]
    bg = np.array(mode) * 16 + 8
    return np.linalg.norm(a - bg, axis=2) > 60


def runs(flags):
    out, start = [], None
    for i, f in enumerate(list(flags) + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i - 1)); start = None
    return out


def segments_of(comp):
    segs = []
    for p in comp['partition_mapping']:
        pts = p['pixel_points']
        for a, b in zip(pts, pts[1:]):
            segs.append((p['partition_id'], tuple(a), tuple(b)))
    ring = comp['footprint']['pixel_polygon']
    for a, b in zip(ring, ring[1:] + ring[:1]):
        segs.append(('perimeter', tuple(a), tuple(b)))
    return segs


def near_wall(pt, segs, tol):
    x, y = pt
    for _, a, b in segs:
        if a[0] == b[0]:  # vertical
            if abs(x - a[0]) <= tol and min(a[1], b[1]) - tol <= y <= max(a[1], b[1]) + tol:
                return True
        else:
            if abs(y - a[1]) <= tol and min(a[0], b[0]) - tol <= x <= max(a[0], b[0]) + tol:
                return True
    return False


def probe(image_path, comp):
    img = Image.open(image_path)
    ink = background_mask(img)
    H, W = ink.shape
    ring = comp['footprint']['pixel_polygon']
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    x0, x1, y0, y1 = int(min(xs)) + MARGIN_PX, int(max(xs)) - MARGIN_PX, int(min(ys)) + MARGIN_PX, int(max(ys)) - MARGIN_PX
    mpp = comp['calibration']['world_metres_per_pixel']
    min_run_px = {'v': MIN_RUN_M / abs(mpp['y']), 'h': MIN_RUN_M / abs(mpp['x'])}
    px_per_m = 1 / abs(mpp['x'])
    end_touch = 0.30 * px_per_m      # host wall half-thickness plus reading error
    perim_skip = 0.35 * px_per_m     # exterior wall band and its window symbols
    strip = int(round(0.22 * px_per_m))  # search both faces of a thick wall drawn at its centre
    cover = 0.25 * px_per_m          # a declared centreline covers both faces of a thick wall
    segs = segments_of(comp)
    part_segs = [s for s in segs if s[0] != 'perimeter']
    report = {'undeclared': [], 'unsupported': [], 'door_on_solid_wall': [], 'undeclared_gap': []}

    # 1. long straight runs inside the footprint
    cands = []
    for orient in ('v', 'h'):
        rng = range(x0, x1 + 1) if orient == 'v' else range(y0, y1 + 1)
        lines = []
        for c in rng:
            col = ink[y0:y1 + 1, c] if orient == 'v' else ink[c, x0:x1 + 1]
            off = y0 if orient == 'v' else x0
            for s, e in runs(col):
                if e - s + 1 >= min_run_px[orient]:
                    lines.append((c, s + off, e + off))
        # merge parallel neighbouring runs with overlapping extents into bands
        lines.sort()
        bands = []
        for c, s, e in lines:
            for b in bands:
                if c - b['c1'] <= BAND_MERGE_PX and min(e, b['e']) - max(s, b['s']) > 0.5 * min(e - s, b['e'] - b['s']):
                    b['c1'] = c; b['s'] = min(s, b['s']); b['e'] = max(e, b['e']); b['n'] += 1
                    break
            else:
                bands.append({'c0': c, 'c1': c, 's': s, 'e': e, 'n': 1})
        for b in bands:
            cands.append((orient, (b['c0'] + b['c1']) / 2, b['s'], b['e'], b['c1'] - b['c0'] + 1))

    for orient, c, s, e, width in cands:
        ends = [(c, s), (c, e)] if orient == 'v' else [(s, c), (e, c)]
        if not all(near_wall(p, segs, end_touch) for p in ends):
            continue
        covered = 0
        for _, a, b in part_segs:
            if orient == 'v' and a[0] == b[0] and abs(a[0] - c) <= cover:
                covered += max(0, min(e, max(a[1], b[1])) - max(s, min(a[1], b[1])))
            if orient == 'h' and a[1] == b[1] and abs(a[1] - c) <= cover:
                covered += max(0, min(e, max(a[0], b[0])) - max(s, min(a[0], b[0])))
        if covered < 0.6 * (e - s):
            # skip the perimeter's own inner face lines
            on_perimeter = False
            for a, b in zip(ring, ring[1:] + ring[:1]):
                if orient == 'v' and a[0] == b[0] and abs(a[0] - c) < perim_skip:
                    on_perimeter |= min(e, max(a[1], b[1])) - max(s, min(a[1], b[1])) > 0.5 * (e - s)
                if orient == 'h' and a[1] == b[1] and abs(a[1] - c) < perim_skip:
                    on_perimeter |= min(e, max(a[0], b[0])) - max(s, min(a[0], b[0])) > 0.5 * (e - s)
            if on_perimeter:
                continue
            world = (abs(e - s) * abs(mpp['y' if orient == 'v' else 'x']))
            report['undeclared'].append({'orient': orient, 'at_px': round(c), 'from_px': s, 'to_px': e,
                                         'length_m': round(world, 2), 'band_px': width})

    # 2. declared partition support and gaps (strip of +-6 px)
    openings = [(o['opening_id'], o['kind'], o['p1_pixel'], o['p2_pixel']) for o in comp['opening_hosts']]
    for pid, a, b in part_segs:
        vertical = a[0] == b[0]
        lo, hi = (int(min(a[1], b[1])), int(max(a[1], b[1]))) if vertical else (int(min(a[0], b[0])), int(max(a[0], b[0])))
        c = int(round(a[0] if vertical else a[1]))
        flags = []
        for t in range(lo, hi + 1):
            band = ink[t, max(0, c - strip):c + strip + 1] if vertical else ink[max(0, c - strip):c + strip + 1, t]
            flags.append(bool(band.any()))
        support = sum(flags) / max(1, len(flags))
        if support < 0.5:
            report['unsupported'].append({'partition': pid, 'support': round(support, 2)})
        mpp_along = abs(mpp['y' if vertical else 'x'])
        for s, e in runs([not f for f in flags]):
            gap_m = (e - s + 1) * mpp_along
            if gap_m < 0.55:
                continue
            gs, ge = s + lo, e + lo
            hit = False
            for oid, kind, p1, p2 in openings:
                if (p1[0] == p2[0]) != vertical:
                    continue
                oc = p1[0] if vertical else p1[1]
                if abs(oc - c) > strip:
                    continue
                os_, oe = sorted([p1[1], p2[1]] if vertical else [p1[0], p2[0]])
                if min(ge, oe) - max(gs, os_) > 0.5 * (ge - gs):
                    hit = True
            if not hit:
                report['undeclared_gap'].append({'partition': pid, 'from_px': gs, 'to_px': ge, 'gap_m': round(gap_m, 2)})
        for oid, kind, p1, p2 in openings:
            if kind != 'door':
                continue
            if (p1[0] == p2[0]) != vertical:
                continue
            oc = p1[0] if vertical else p1[1]
            if abs(oc - c) > strip:
                continue
            os_, oe = sorted([p1[1], p2[1]] if vertical else [p1[0], p2[0]])
            if not (lo - 2 <= os_ and oe <= hi + 2):
                continue
            seg = flags[int(os_) - lo:int(oe) - lo + 1]
            if seg and sum(seg) / len(seg) > 0.85:
                report['door_on_solid_wall'].append({'door': oid, 'partition': pid, 'ink_fraction': round(sum(seg) / len(seg), 2)})
    return report


def last_compiled_per_image(run):
    best = {}
    for d in sorted(glob.glob(os.path.join(run, 'plan_drafts', 'draft_*'))):
        c = os.path.join(d, 'compilation.json')
        if os.path.exists(c):
            comp = json.load(open(c))
            best[comp['image_name']] = (d, comp)
    return best


if __name__ == '__main__':
    for run in sys.argv[1:]:
        for image, (d, comp) in sorted(last_compiled_per_image(run).items()):
            rep = probe(os.path.join(run, 'images', image), comp)
            print(f"== {os.path.basename(run)} {image} {os.path.basename(d)}")
            for k, v in rep.items():
                if v:
                    print(f"   {k}: {v}")
