"""Offline replay of the actual six-save block; no model or reference answers."""
import json
from pathlib import Path
import shutil
import tempfile

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-27_sm21_current_tools_claude_run69'


def main():
    original = {p.name: digest(p / 'source_model.json') for p in RUN.glob('candidate_*')}
    assert len(original) == 6
    source = json.loads((RUN / 'candidate_06/source_model.json').read_text())
    with tempfile.TemporaryDirectory(prefix='sm21-candidate-budget-') as directory:
        replay = Path(directory)
        shutil.copy2(RUN / 'inputs.json', replay / 'inputs.json')
        for name in original:
            shutil.copytree(RUN / name, replay / name)
        operations = json.dumps([dict(op='set_notes',
            assumptions=source['assumptions'] + ['Offline export-budget replay only; not a model interpretation.'],
            unresolved=source['generation']['unresolved'])])
        blocked = Toolkit(replay).revise('candidate_06', operations)
        assert blocked['candidate_budget'] == dict(limit=6, used=6, remaining=0)
        assert 'candidate budget exhausted' in blocked['error']
        manifest = json.loads((replay / 'inputs.json').read_text())
        manifest['max_candidates'] = 24
        dump(replay / 'inputs.json', manifest)
        saved = Toolkit(replay).revise('candidate_06', operations)
        assert saved['candidate'] == 'candidate_07' and saved['source_geometry_ready']
        assert saved['candidate_budget'] == dict(limit=24, used=7, remaining=17)
        after = json.loads((replay / 'candidate_07/source_model.json').read_text())
        geometry_fields = ('floors','spaces','boundaries','openings','connections','opening_hosts','boundary_relations')
        assert all(source[k] == after[k] for k in geometry_fields)
        assert all(digest(replay / name / 'source_model.json') == sha for name, sha in original.items())
        assert all(digest(RUN / name / 'source_model.json') == sha for name, sha in original.items())
        dump(HERE / 'run69_export_budget_replay.json', dict(
            mode='offline_developer_replay_not_model_recovery', provider_invocations=0,
            source_run=RUN.name, source_hashes=original,
            legacy_result=blocked, configured_budget=saved['candidate_budget'],
            resulting_candidate=saved['candidate'], physical_geometry_and_roles_unchanged=True,
            geometry_fields=list(geometry_fields), prior_candidates_unchanged=True,
            original_run_unchanged=True,
            limit='Only tests saving past six; does not evaluate or fix original-image reading.'))
    print('Actual run69 replay: legacy six blocks; configured 24 saves candidate_07; all physical geometry and prior candidates preserved.')


if __name__ == '__main__':
    main()
