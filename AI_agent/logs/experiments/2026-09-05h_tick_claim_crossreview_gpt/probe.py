"""Independent rework-2 design probes; no production files are changed.

ACTUAL = repository code. SPEC = an explicitly identified reading of draft
equations/field declarations, not an implementation of the proposed types.
The D6 excerpt is executed verbatim first; its signature mismatch is then
bridged explicitly to examine the substantive artifact binding separately.
"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
DRAFT = ROOT / 'AI_agent/logs/reviews/execution/2026-09-05f_tick_claim_design_rework2.md'
BASE = ROOT / 'AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype'
from src.agent.correction import evidence_adapters as ea
from src.agent.correction import evidence_contract as ec
from src.agent.correction import opening_synthesis as osyn


def nearest_function():
    p = BASE / 'tools/as_drawn_elev.py'
    tree = ast.parse(p.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_nearest')
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(p), 'exec'), ns)
    return ns['_nearest']


def draft_branch(doc, witness):
    value = Decimal(str(doc['dimension_witnesses']['x'][str(witness['nearest_tick_px'])]))
    indices = [i for i, v in enumerate(doc['calibration']['x']['cum_mm']) if Decimal(str(v)) == value]
    # Literal ordering in D5:705-716; no invented ALL_S1 override.
    if indices:
        return 'auto_chain', value, indices
    if all(r.endswith('_s1') for r in witness['dimension_refs']):
        return 'pixel_no_debt', value, indices
    return 'pixel_debt', value, indices


def candidates():
    counts = Counter()
    for face in ('south', 'east', 'north', 'west'):
        doc = json.loads((BASE / f'out/sm25_{face}_as_drawn.json').read_text())
        for opening in doc['openings']:
            for edge in ('x0', 'x1'):
                branch, value, indices = draft_branch(doc, opening['edge_witnesses'][edge])
                counts[branch] += 1
                if branch != 'auto_chain' or (face == 'east' and opening['id'] == 'O01'):
                    print('SPEC_D5', face, opening['id'] + ':' + edge, branch, 'value=', value, 'indices=', indices)
    print('SPEC_D5_TOTAL', dict(counts))
    nearest = nearest_function()
    ticks = [0.0, 120.0, 300.0, 520.0]
    values = {0.0: 0, 120.0: 3100, 300.0: 7800, 520.0: 12600}
    picked = [nearest(ticks, p)[0] for p in (176.0, 254.0)]
    print('ACTUAL_NEW_NEAREST unlabelled_raw_px=[176,254]', 'picked=', picked,
          'SPEC_chain_mm=', [values[p] for p in picked], 'ordered=', values[picked[0]] < values[picked[1]])
    # Field-shape witness only: a tuple annotation imposes no completeness relation.
    # Do not claim that the author's promised constructor has been implemented.
    required_ids = {'FacadeR:W07:lo', 'FacadeR:W07:hi'}
    supplied_ids = ('FacadeR:W07:lo',)
    print('SPEC_REVIEW_COVERAGE required=', sorted(required_ids), 'supplied=', supplied_ids,
          'tuple_field_well_typed=True missing=', sorted(required_ids - set(supplied_ids)),
          'draft_has_no_manifest_field_or_consumer_binding=True')
    primary = [0, 2600, 5200, 10400]
    # Different declared boundary values at the SAME raster key; BOTH are
    # members of the primary array. This defeats the author's Q_WINS argument.
    for name, sequence in [('P_LAST', [('Q', 5200), ('P', 2600)]), ('Q_LAST', [('P', 2600), ('Q', 5200)])]:
        flat = {}
        for chain, value in sequence:
            flat['275.0'] = value
        value = flat['275.0']
        print('SPEC_NEW_COLLISION', name, 'true_boundaries=[2600,5200]', 'flat=', value,
              'membership=', value in primary, 'selected_primary_index=', primary.index(value))


def chains():
    def check(values, cum):
        chain = {'values_mm': values, 'cum_mm': cum, 'overall_mm': sum(values)}
        ea._require_chain_closed({'x': chain, 'z': chain}, 'review_prefix')
        # Natural range over every non-origin cum node. Length is separately
        # reported because draft :691 does not specify the range/cardinality.
        prefix = all(Decimal(str(cum[i])) == Decimal(str(cum[i-1])) + Decimal(str(values[i-1]))
                     for i in range(1, len(cum)))
        return prefix
    for name, values, cum in [
        ('INTERIOR_NEW', [900, 1500, 1200], [0, 900, 2450, 3600]),
        ('ZERO_SEGMENT_NEW', [900, 0, 1500], [0, 900, 900, 2400]),
        ('NEGATIVE_SEGMENT_NEW', [1250, -250, 900], [0, 1250, 1000, 1900]),
        ('SHORT_CUM_NONZERO_ORIGIN', [700, 1100, 1800], [1800, 2500, 3600]),
    ]:
        print('ACTUAL_CLOSED=PASS', name, 'SPEC_prefix=', check(values, cum),
              'len_cum=', len(cum), 'len_values_plus_1=', len(values)+1, 'cum=', cum)


def derived():
    cum = [0, 1600, 4300, 7500]
    print('SPEC_SEGMENT_SUM refs=/cum_mm/1,/cum_mm/2 contiguous=True',
          'draft_sum_mm=', sum(cum[1:3]), 'declared_segment_sum_mm=', (cum[1]-cum[0]) + (cum[2]-cum[1]))
    print('SPEC_SEGMENT_DIFF refs=/cum_mm/1,/cum_mm/2', 'difference_mm=', cum[2]-cum[1],
          'node_coordinate_mm=', cum[2], 'anchor_needed_mm=', cum[1])
    from pydantic import BaseModel, ConfigDict
    from typing import Literal
    class OperandFieldShape(BaseModel):
        model_config = ConfigDict(extra='forbid', strict=True)
        role: Literal['axis', 'half_wall_thickness', 'cum_lo', 'cum_hi', 'segment_len']
        ref: ec.ArtifactPointerV1
        derivation: Literal['declared_as_half', 'half_of_declared_full'] | None
    ref = ec.ArtifactPointerV1(input_id='review_other_facade', source_contract_id='as_drawn_elevation_v0',
                              source_output_sha256='b'*64, json_pointer='/measured_wall_gap_mm')
    operand = OperandFieldShape(role='half_wall_thickness', ref=ref, derivation='half_of_declared_full')
    print('SPEC_OPERAND_FIELD_SHAPE', tuple(operand.model_dump()),
          'foreign_input_and_measured_ref_admitted_by_fields=True',
          'not_a_run_of_promised_qualification_guard=True')
    print('SPEC_HALF_GRID full_units=201 reject=', 201 % 2 != 0,
          'full_units=202 half_units=', 202 // 2)
    print('SPEC_EXPLICIT_SIGN axes_mm=[3600,7600] full_wall_mm=220',
          'inside_edges_mm=', [3600+110, 7600-110])


def debt():
    d = ec.EvidenceDebtV1(debt_id='review_nonprimary_R_W07', kind='other_known_missing',
                         affected_refs=(), description='New frozen address available: rerun and upgrade this edge', obligation=None)
    osyn.assert_obligations_backed([d])
    # None is deliberately used as an execution sentinel: the actual code
    # must skip this debt before consulting executed at all.
    redeemed = osyn.redeemable_debt_ids([d], executed=None)
    print('ACTUAL_DEBT', 'obligation=', d.obligation, 'assert_backed=PASS', 'redeemed=', redeemed,
          'description_upgrade_request_does_not_dispatch=True')


def seal():
    raw = (BASE / 'out/sm25_south_as_drawn.json').read_bytes()
    a = ea.adapt_as_drawn_elevation(raw, input_id='review_same_slot', facade_ref='south')
    # A second fully valid finalized bundle, SAME source bytes and source IDs.
    # Only the declared manifest differs. This is not a forged source.
    staged = a.bundle.model_copy(deep=True)
    staged.view_manifest_sha256 = 'b'*64
    b = ec.CorrectionEvidenceBundleArtifactV1(bundle=ec.finalize_bundle(staged), frozen_sources=a.frozen_sources)
    ec.validate_evidence_bundle(a)
    ec.validate_evidence_bundle(b)
    print('ACTUAL_TWO_VALID_ARTIFACTS same_source_bytes=', a.frozen_sources[0].raw_bytes == b.frozen_sources[0].raw_bytes,
          'bundle_ids_differ=', a.bundle.content_sha256 != b.bundle.content_sha256)
    source = DRAFT.read_text()
    excerpt = source[source.index('def _mint_sealed_tick_claims('):source.index('\n```', source.index('def _mint_sealed_tick_claims('))]
    # _derive is unspecified by the draft. A transparent diagnostic reports
    # which artifact reached it; no imaginary tick derivation is implemented.
    ns = {'CorrectionEvidenceBundleArtifactV1': ec.CorrectionEvidenceBundleArtifactV1,
          'EvidenceContractError': ec.EvidenceContractError,
          'validate_evidence_bundle': ec.validate_evidence_bundle,
          '_derive_tick_claims_from_frozen_bytes': lambda artifact: (artifact.bundle.content_sha256,)}
    exec(compile(excerpt, str(DRAFT)+':335', 'exec'), ns)
    carrier = ns['_mint_sealed_tick_claims'](a)
    try:
        tuple(carrier)
    except TypeError as exc:
        print('EXACT_D6_EXCERPT', type(exc).__name__, str(exc))
    def arity_bridge(bundle, frozen_sources):
        ec.validate_evidence_bundle(ec.CorrectionEvidenceBundleArtifactV1(bundle=bundle, frozen_sources=frozen_sources))
    ns['validate_evidence_bundle'] = arity_bridge
    before = tuple(carrier)
    carrier._artifact = b  # ordinary assignment: the printed design has no __setattr__ guard
    after = tuple(carrier)
    print('D6_WITH_ARITY_BRIDGE ordinary_artifact_assignment=PASS', 'derive_received_other_bundle=', before != after,
          'new_bundle_valid=True', 'not_a_production_tick_claim_test=True')


def numbers():
    seen = defaultdict(list)
    for lineno, line in enumerate(DRAFT.read_text().splitlines(), 1):
        for m in re.finditer(r'\d+(?:\.\d+)?(?:e[+-]?\d+)?', line, re.I):
            seen[m.group()].append(lineno)
    for token, locations in seen.items():
        print(token + '\t' + ','.join(map(str, locations)))
    print('TARGET', DRAFT.relative_to(ROOT))
    print('UNIQUE_COUNT', len(seen))
    print('OCCURRENCE_COUNT', sum(map(len, seen.values())))


if __name__ == '__main__':
    if sys.argv[1] == 'all':
        for fn in (candidates, chains, derived, debt, seal):
            fn()
    else:
        globals()[sys.argv[1]]()
