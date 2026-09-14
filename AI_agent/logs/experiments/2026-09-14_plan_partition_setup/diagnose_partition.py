"""Post-run wall-only diagnostic, never a completed runtime BIM candidate."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.geometry.plan_partition import compile_plan_partition


if __name__ == '__main__':
    run = ROOT / 'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run17'
    assert (run / 'summary.json').exists(), 'Wait until the model run ends'
    out = run / 'post_run_partition_diagnostic'
    out.mkdir(exist_ok=False)
    shutil.copytree(run / 'images', out / 'images')
    shutil.copyfile(run / 'building_input.json', out / 'building_input.json')
    original_path = run / 'plan_drafts/draft_002/plan.json'
    shutil.copyfile(original_path, out / 'original_declaration.json')
    original = json.loads(original_path.read_text())
    manifest = json.loads((run / 'inputs.json').read_text())
    manifest.pop('deadline_epoch', None)
    manifest.update(input_mode='developer_post_generation_wall_only_diagnostic',
        scope='Post-run diagnostic only. Original generated wall network unchanged; ALL apertures explicitly excluded and retained separately. Not a generating-agent candidate or a building restoration.',
        diagnostic_source={'run': run.name, 'plan_file': str(original_path.relative_to(ROOT)),
                           'plan_sha256': digest(original_path)},
        generator='Deterministic developer post-run diagnostic; zero model calls')
    dump(out / 'inputs.json', manifest)
    declaration = deepcopy(original)
    opening_checks = []
    for opening in original['openings']:
        local = deepcopy(original)
        local['openings'] = [opening]
        try:
            _, metadata = compile_plan_partition(local, image_size=(790, 1111), image_name='1f_view.png')
        except (ValueError, TypeError) as error:
            opening_checks.append({'id': opening['id'], 'kind': opening['kind'], 'error': str(error)})
        else:
            opening_checks.append({'id': opening['id'], 'kind': opening['kind'],
                                   'host': metadata['opening_hosts'][0]})
    dump(out / 'excluded_openings.json', {'scope': 'ALL runtime-declared apertures excluded from this diagnostic source; none reclassified, moved or shortened.',
        'openings': original['openings'], 'individual_host_diagnostics': opening_checks})
    declaration['openings'] = []
    declaration['assumptions'].append('DEVELOPER POST-RUN DIAGNOSTIC: original generated walls unchanged. ALL 17 declared openings excluded solely to inspect partitions; retained in excluded_openings.json and original_declaration.json. This is not a runtime BIM candidate.')
    declaration['unresolved'].append('NO openings are built in this diagnostic. Original door/window declarations and failed-host details remain unresolved and are not discarded from the experiment. Do not adopt as restored BIM.')
    toolkit = Toolkit(out)
    result = toolkit.build_plan('1f_view.png', json.dumps(declaration, ensure_ascii=False, indent=2))
    assert result['source_geometry_ready'], result
    delivery = toolkit.delivery(result['candidate'], selection_origin='developer_post_run_diagnostic_not_model_selected')
    dump(out / 'summary.json', {'mode': manifest['input_mode'], 'delivery': delivery,
        'model_calls': 0, 'parent_run_has_bim_candidate': False,
        'all_original_wall_points_unchanged': declaration['partitions'] == original['partitions'],
        'excluded_opening_count': len(original['openings']), 'not_a_restoration_candidate': True})
    print(json.dumps({'diagnostic': str(out.relative_to(ROOT)), 'counts': result['counts'],
                      'opening_host_errors': [row for row in opening_checks if row.get('error')]},ensure_ascii=False,indent=2))
