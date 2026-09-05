"""Read-only design review probes. No proposed production schema is implemented here."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from decimal import Decimal
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype'
DESIGN = ROOT / 'AI_agent/logs/reviews/execution/2026-09-05a_tick_claim_design_rework1.md'


def groups(refs):
    result = defaultdict(list)
    for ref in refs:
        chain, seg = ref.rsplit('_s', 1)
        result[chain].append(int(seg))
    return {k: sorted(v) for k, v in result.items()}


def signature(refs):
    g = groups(refs)
    consecutive = all(len(v) == 2 and v[1] == v[0] + 1 for v in g.values())
    if g and all(v == [1] for v in g.values()):
        return 'ALL_S1'
    if len(g) == 1 and consecutive:
        return '1CHAIN-CONSEC'
    if len(g) >= 2 and consecutive:
        return 'MULTI'
    return 'OTHER'


def statistics():
    counts = Counter()
    agreement = Counter()
    for face in ('south', 'east', 'north', 'west'):
        d = json.loads((BASE / f'out/sm25_{face}_as_drawn.json').read_text())
        cfg = json.loads((BASE / f'tools/cfg_{face}.json').read_text())
        local = Counter()
        print(f'FACE {face} primary={cfg["primary_x_chain"]} closure={d["calibration"]["x"]["chain_closure_mm"]}')
        for o in d['openings']:
            for edge in ('x0', 'x1'):
                w = o['edge_witnesses'][edge]
                sig = signature(w['dimension_refs'])
                local[sig] += 1
                counts[sig] += 1
                mapped = Decimal(str(d['dimension_witnesses']['x'][str(w['nearest_tick_px'])]))
                g = groups(w['dimension_refs'])
                # Independent per-chain reconstruction requires cfg, not merely the flattened tick map.
                values = {}
                for cid, segs in g.items():
                    if len(segs) == 2 and segs[1] == segs[0] + 1:
                        c = cfg['chains'][cid]
                        values[f'{cid}:boundary{segs[0]}'] = Decimal(str(c['world_start_mm'])) + Decimal(str(c['direction'])) * sum(Decimal(str(v)) for v in c['values_mm'][:segs[0]])
                same_value = bool(values) and set(values.values()) == {mapped}
                same_symbol = bool(values) and len(set(values)) == 1
                if sig == 'MULTI':
                    agreement['total'] += 1
                    agreement['numeric_equal_to_map'] += same_value
                    agreement['same_symbol'] += same_symbol
                match_indices = [i for i, value in enumerate(d['calibration']['x']['cum_mm']) if Decimal(str(value)) == mapped]
                print(f'  {o["id"]}:{edge} {sig} refs={w["dimension_refs"]} px={w["nearest_tick_px"]} mapped_mm={mapped} chain_values={values} primary_indices={match_indices}')
        print(f'SUMMARY {face} edges={sum(local.values())} {dict(local)}')
    print(f'TOTAL edges={sum(counts.values())} signatures={dict(counts)} MULTI_agreement={dict(agreement)}')
    print('LITERAL_D5_COUNTS auto_one=66 auto_two=2 model=0 auto_total=68')


def counterexamples():
    # Execute only the actual producer's self-contained nearest function, without its imports or image pipeline.
    source = BASE / 'tools/as_drawn_elev.py'
    tree = ast.parse(source.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_nearest')
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), ns)
    nearest = ns['_nearest']
    print(f'ACTUAL_NEAREST_SOURCE {source.relative_to(ROOT)}:{fn.lineno}')
    # Unlabelled edges inside the second segment, plus an exactly identified origin.
    ticks = [0.0, 500.0, 1000.0]
    mm = {0.0: 0, 500.0: 6000, 1000.0: 12000}
    refs = {0.0: ['C_custom_s1'], 500.0: ['C_custom_s1', 'C_custom_s2'], 1000.0: ['C_custom_s2']}
    for label, px in [('unlabelled_second_segment_lo', 800.0), ('unlabelled_second_segment_hi', 950.0), ('chain_origin_edge', 0.0), ('ordinary_interior_nearest', 700.0)]:
        t, distance = nearest(ticks, px)
        sig = signature(refs[t])
        branch = 'auto_one' if sig == '1CHAIN-CONSEC' else 'auto_two' if sig == 'ALL_S1' and mm[t] == 0 else 'model'
        print(f'NEAREST_COUNTEREXAMPLE {label} px={px} nearest={t} distance_px={distance} signature={sig} D5={branch} value_mm={mm[t]}')
    # Separate complete interval: both edges inside an unlabelled middle segment.
    interval_ticks = [0.0, 500.0, 1000.0, 1500.0]
    interval_refs = {500.0: ['C_middle_s1', 'C_middle_s2'], 1000.0: ['C_middle_s2', 'C_middle_s3']}
    picked = [nearest(interval_ticks, p)[0] for p in (620.0, 870.0)]
    print('UNLABELLED_MIDDLE_INTERVAL raw_px=[620,870] picked_px=' + str(picked) + ' signatures=' + str([signature(interval_refs[t]) for t in picked]) + ' D4_order_pass=' + str(picked[0] < picked[1]))
    print('UPSTREAM_HIDDEN_MIDPOINT_PX', (500 + 1000) / 2)
    # Two closed chains sharing a raster key but disagreeing in exact declared values.
    chain_values = {'C_A': [4700, 5300], 'C_B': [4900, 5100]}
    flattened = {}
    accumulated = []
    for cid, vals in chain_values.items():
        flattened['400.0'] = vals[0]  # actual producer line 93: assignment, not a per-chain multimap
        accumulated.extend([cid + '_s1', cid + '_s2'])
    print(f'RASTER_COLLISION refs={accumulated} signature={signature(accumulated)} flattened={flattened} true_boundaries={[v[0] for v in chain_values.values()]}')
    # Contract-level arithmetic witnesses; not executions of nonexistent D2/D4 validators.
    print('DERIVED_SIGN opening_inside_two_wall_faces axis_lo_mm=4000 axis_hi_mm=8000 wall_mm=200 expected_mm=[4100,7900] D4_lo_minus_hi_plus_mm=[3900,8100]')
    print('OPERAND_TIER axis_mm=4200 half_wall_mm=115 wall_tier=pixel_only refs_resolve=True roles_complete=True certificate_units=40850 D4_checks=True evidence_tier_gate=UNSPECIFIED')
    print('NEGATIVE_DIFF lo=(900-1300)=-400 hi=(1400-1300)=100 refs_resolve=True recompute=True interval_order=True interval_width=500 coordinate_frame_gate=UNSPECIFIED')
    print('DUPLICATE_VALUE chains=A:[0,4200,10000],B:[0,4200,10000] exact_value_equal=True identity_equal=False D4_ref_choice=UNSPECIFIED_BY_VALUE D5_equivalence=UNSPECIFIED_WITHOUT_CHAIN_BINDING')
    print('PLAN_ONLY_2b elevation_row=None evidence_ref_to_D2a=UNAVAILABLE pixel_fallback_also_requires_elevation_ref named_rejection=NOT_SPECIFIED')
    print('PLAN_ONLY_3 elevation_artifact=None evidence_ref_to_D2a=UNAVAILABLE inferred_provenance=NOT_IN_auto_or_model named_rejection=NOT_SPECIFIED')
    print('SEAL_SCOPE first_step_runs=A,B authentic_elements=True same_edge_id=True selected_run_manifest_binding=NOT_SPECIFIED does_not_claim_runtime_bypass=True')


def numbers():
    seen = defaultdict(list)
    text = DESIGN.read_text()
    lines = text.splitlines()
    pat = re.compile(r'\d+(?:\.\d+)?(?:e[+-]?\d+)?', re.I)
    for n, line in enumerate(lines, 1):
        for m in pat.finditer(line):
            seen[m.group()].append(n)
    for token, locations in seen.items():
        print(token + '\t' + ','.join(map(str, locations)))
    print('UNIQUE_COUNT', len(seen))
    print('OCCURRENCE_COUNT', sum(map(len, seen.values())))
    table_start = next(i for i, line in enumerate(lines) if line.startswith('| 类别 | 数字 |'))
    table_end = next(i for i in range(table_start + 1, len(lines)) if lines[i].startswith('**结论**'))
    table_tokens = set(pat.findall('\n'.join(lines[table_start:table_end])))
    absent = [t for t in seen if t not in table_tokens]
    print('TOKENS_ABSENT_FROM_CLASSIFICATION_TABLE', absent)
    for token in absent:
        print('ABSENT', token, 'lines=', seen[token])
    print('NOTE numeric token absence is a mechanical coverage check, not an automatic substantive finding.')


def arithmetic():
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    from src.agent.correction import evidence_adapters as adapters
    from src.agent.correction import opening_synthesis as synthesis
    print('IMPORTED', adapters.__file__, synthesis.__file__)
    d = json.loads((BASE / 'out/sm25_south_as_drawn.json').read_text())
    d['calibration']['x']['cum_mm'][2] = 7000.0
    adapters._require_chain_closed(d['calibration'], 'independent-review-probe')
    chain = d['calibration']['x']
    print('INTERIOR_CUM_CHANGED require_chain_closed=PASS lo_mm=', chain['cum_mm'][2], 'hi_mm=', chain['cum_mm'][3], 'width_mm=', chain['cum_mm'][3] - chain['cum_mm'][2], 'declared_segment_mm=', chain['values_mm'][2])
    d['calibration']['x']['cum_mm'][2] = d['calibration']['x']['cum_mm'][1]
    adapters._require_chain_closed(d['calibration'], 'independent-review-probe')
    print('DUPLICATE_NODE_VALUE require_chain_closed=PASS cum_indices_1_2=', d['calibration']['x']['cum_mm'][1:3])
    print('GRID_6925', synthesis.grid_units_from_mm(6925, what='review'))
    print('GRID_NEGATIVE_400', synthesis.grid_units_from_mm(-400, what='review'))
    from src.agent.correction.evidence_contract import ArtifactPointerV1
    pointer = ArtifactPointerV1(input_id='review_south', source_contract_id='as_drawn_elevation_v0', source_output_sha256='a' * 64, json_pointer='/calibration/x/cum_mm/2')
    before = pointer.json_pointer
    pointer.json_pointer = '/calibration/x/cum_mm/3'
    print('NESTED_POINTER_ASSIGNMENT', before, '->', pointer.json_pointer, 'model_config=', ArtifactPointerV1.model_config)


if __name__ == '__main__':
    {'statistics': statistics, 'counterexamples': counterexamples, 'numbers': numbers, 'arithmetic': arithmetic}[sys.argv[1]]()
