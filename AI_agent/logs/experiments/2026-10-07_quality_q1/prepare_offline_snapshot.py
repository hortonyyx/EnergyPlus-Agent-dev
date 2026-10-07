"""Isolated test hash snapshot; never writes the shared Agent registry."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent_runtime.agent_registry import register_agent_version


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-directory', default='AI_agent/archive/local_backup/q1/offline_snapshot')
    args = parser.parse_args()
    folder = (ROOT / args.snapshot_directory).resolve()
    allowed = (ROOT / 'AI_agent/archive/local_backup/q1').resolve()
    if not folder.is_relative_to(allowed) or folder == allowed:
        raise ValueError('isolated snapshot directory must stay inside the Q1 scratch directory')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'agent_versions.json'
    original = ROOT / 'src/agent_runtime/agent_versions.json'
    original_bytes = original.read_bytes()
    shutil.copyfile(original, path)
    new_files = (
        'scripts/tool_scripts/bim_agent_regularization.py',
        'src/agent/geometry/plan_regularization.py',
        'src/agent/geometry/plan_dimension_alignment.py',
        'src/agent/geometry/plan_ink_alignment.py',
    )
    record = register_agent_version(ROOT, 'q1-offline-verification', registry_path=path,
                                    additional_files={name: 'tool' for name in new_files})
    print(json.dumps({'test_snapshot': str(path), 'version_id': record['version_id'],
                      'registered_files': len(record['files']), 'shared_registry_unchanged': original.read_bytes() == original_bytes}))
