"""Controlled errors on temporary copies; preserve all generation evidence."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import tempfile

from .audit_inventory import HERE, audit, load
from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.geometry.source_bim import _digest


def main():
    run = HERE.parent / '2026-09-26_sm25_height_cold_claude_run53'
    delivery = load(run / 'delivery.json')
    path = run / delivery['candidate'] / 'source_model.json'
    frozen = digest(path)
    original = load(path)
    reference = load(HERE / 'original_reference.json')
    door = next(o for o in original['openings'] if o['kind'] == 'door' and not o['exterior'])
    results = {}
    for control in ('shift_internal_door', 'omit_internal_door', 'wrong_connection'):
        source = deepcopy(original)
        target = next(o for o in source['openings'] if o['id'] == door['id'])
        if control == 'shift_internal_door':
            axis = max(range(2), key=lambda d: max(v[d] for v in target['vertices']) - min(v[d] for v in target['vertices']))
            for vertex in target['vertices']:
                vertex[axis] += 0.5
        elif control == 'omit_internal_door':
            source['openings'].remove(target)
        else:
            connection = next(c for c in source['connections'] if c['opening_id'] == target['id'])
            connection['space_ids'] = [connection['space_ids'][0]]
        # These deliberately inconsistent temporary copies are diagnostic inputs,
        # not valid exported BIM or alternative product candidates.
        source['source_model_sha256'] = _digest({k: v for k, v in source.items() if k != 'source_model_sha256'})
        temporary_delivery = dict(delivery, source_model_sha256=source['source_model_sha256'])
        with tempfile.TemporaryDirectory(prefix='sm25-inventory-control-') as temp:
            tmp = Path(temp)
            (tmp / 'images').symlink_to((run / 'images').resolve(), target_is_directory=True)
            (tmp / delivery['candidate']).mkdir()
            dump(tmp / 'summary.json', {})
            dump(tmp / 'delivery.json', temporary_delivery)
            dump(tmp / delivery['candidate'] / 'source_model.json', source)
            with redirect_stdout(StringIO()):
                report = audit(tmp, reference, output=tmp / 'evaluation')
            if control == 'shift_internal_door':
                detected = report['internal_positions'] < 27
            elif control == 'omit_internal_door':
                detected = report['matched'] == 60 and sum(len(f['unmatched_reference']) for f in report['floors']) == 1
            else:
                detected = report['internal_connections'] == 26
            assert detected, control
            results[control] = dict(detected=True, temporary_copy_only=True)
    assert digest(path) == frozen
    dump(HERE / 'verification.json', dict(controls=results, original_source_unchanged=True,
        source_file_sha256=frozen, model_calls=0,
        limits='Checks the diagnostic detects these concrete faults, not automatic correctness of manual reference interpretation.'))


if __name__ == '__main__':
    main()
