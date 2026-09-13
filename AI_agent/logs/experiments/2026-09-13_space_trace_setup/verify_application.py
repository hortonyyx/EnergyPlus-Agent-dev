"""Offline replay of local application; no observation/model/GT calls."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from src.agent.geometry.proposal_edits import apply_proposal_edits
from src.agent.execution.source_proposal import export_source_proposal
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path)
r=parser.parse_args().run
seed=json.loads((r/'seed/proposal.json').read_text());ops=json.loads((r/'operations.json').read_text());after=json.loads((r/'candidate_01/proposal.json').read_text())
replay=apply_proposal_edits(seed,ops)
assert replay['geometry']==after['geometry']
assert all(x in after['assumptions'] for x in seed['assumptions'])
assert all(x in after['unresolved'] for x in seed['unresolved'])
def shapes(p):
    return {c['id']:Polygon(c['polygon']) if c.get('polygon') else box(c['x'][0],c['y'][0],c['x'][1],c['y'][1]) for f in p['geometry']['floors'] for c in f['cells']}
a=shapes(seed);b=shapes(after);ids=[ops[0]['space_id'],ops[0]['neighbor_space_id']]
delta=unary_union([a[i] for i in ids]).symmetric_difference(unary_union([b[i] for i in ids])).area
assert delta<1e-10
assert all(a[k].equals(b[k]) for k in a if k not in ids)
with tempfile.TemporaryDirectory() as d:
    out=Path(d)/'reexport'
    provenance=json.loads((r/'candidate_01/report.json').read_text())['provenance']
    export_source_proposal(after,out,provenance=provenance)
    rebuilt=json.loads((out/'source_model.json').read_text());saved=json.loads((r/'candidate_01/source_model.json').read_text())
    assert rebuilt['source_model_sha256']==saved['source_model_sha256']
result={'operations_reproduce_geometry':True,'original_notes_preserved':True,'two_space_union_difference_m2':delta,'other_space_shapes_unchanged':True,'source_reexport_sha256_matches':True,'source_model_sha256':saved['source_model_sha256'],'scope':'Deterministic operations, coverage and source reproducibility only; not drawing fidelity.'}
(r/'evaluation/application_replay_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
