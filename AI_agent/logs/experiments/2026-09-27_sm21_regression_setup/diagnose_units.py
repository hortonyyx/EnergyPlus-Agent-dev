"""Post-generation XY-unit diagnosis; never replace or deliver the model result."""
import copy
import importlib
import json
from pathlib import Path
import tempfile

from scripts.tool_scripts.run_bim_agent import dump, digest
from scripts.tool_scripts.evaluate_bim_agent import evaluate
from src.agent.execution.source_proposal import export_source_proposal

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-27_sm21_guidance_ablation_run72'
load = lambda p: json.loads(p.read_text())


def main():
    original = load(RUN / 'candidate_06/proposal.json')
    proposal = copy.deepcopy(original)
    geom = proposal['geometry']
    factor = 0.001  # Based on the MODEL'S stated millimetres vs metre field contract.
    pair = lambda values: [v * factor for v in values]
    points = lambda values: [pair(p) for p in values]
    for key in ('footprint_x','footprint_y'):
        geom[key] = pair(geom[key])
    for floor in geom['floors']:
        floor['footprint']['vertices'] = points(floor['footprint']['vertices'])
        for cell in floor['cells']:
            cell['polygon'] = points(cell['polygon'])
            for key in ('x','y'):
                cell[key] = pair(cell[key])
    for opening in geom['windows'] + geom['openings']:
        for key in ('p1','p2','span'):
            if key in opening:
                opening[key] = pair(opening[key])
        if 'width_m' in opening:
            opening['width_m'] *= factor
    original_audit = importlib.import_module(
        'AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original')
    with tempfile.TemporaryDirectory(prefix='bim-unit-diagnosis-') as tmp:
        out = Path(tmp)
        dump(out / 'summary.json', {'mode':'offline_diagnostic_not_a_model_result'})
        dump(out / 'inputs.json', {'xy_scale':factor,'basis':'original model says mm in basis; anchors require metres',
                                  'original_proposal_sha256':digest(RUN / 'candidate_06/proposal.json')})
        (out / 'images').symlink_to(RUN / 'images', target_is_directory=True)
        report = export_source_proposal(proposal, out / 'candidate_01', provenance={
            'mode':'developer_unit_diagnosis_only', 'not_delivered':True,
            'claim_status':'Original claims not revalidated by this diagnostic.'})
        assert report['source_geometry_ready']
        dump(out / 'delivery.json', {'candidate':'candidate_01'})
        original_audit.audit(out)
        evaluate(out, 'sm21_anchor', modelling_task='reconstruction',
                 reference_scope='Offline unit-only diagnosis; raw result remains rejected.', out=out/'gt')
        partitions = load(out/'gt/candidate_01_partition.json')
        openings = load(out/'evaluation/original_openings.json')
    assert load(RUN / 'candidate_06/proposal.json') == original
    result = dict(mode='post_generation_unit_diagnosis_not_delivered', xy_scale=factor,
        selection_basis='Model plan basis explicitly says 15000x8000mm; same numbers wrongly entered in metre anchors. No best-fit registration or GT fitting.',
        original_proposal_sha256=digest(RUN/'candidate_06/proposal.json'),
        raw_run_unchanged=True, heights_and_roles_unchanged=True,
        original_openings=openings, partition=partitions,
        limits=['Developer diagnostic, not autonomous correction or a successful reconstruction.',
                'Raw scores remain unchanged. Missing south door and wrong height families are not repaired.'])
    dump(RUN/'evaluation/unit_diagnostic.json', result)
    print('Diagnostic partition:', partitions['comparison']['status'])


if __name__ == '__main__':
    main()
