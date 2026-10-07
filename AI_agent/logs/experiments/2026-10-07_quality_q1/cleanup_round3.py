"""Delete only Q1 round-three scratch trees with the user-requested shutil.rmtree."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRATCH = (ROOT / 'AI_agent/archive/local_backup/q1').resolve()
OWNED_NAMES = ('round3-kernel', 'round3-replay', 'round3-pytest', 'round3-snapshot')


def inspect_owned_tree(name: str) -> dict:
    path = SCRATCH / name
    resolved = path.resolve()
    if (not SCRATCH.is_relative_to(ROOT) or not resolved.is_relative_to(SCRATCH)
            or resolved == SCRATCH or resolved.name != name):
        raise ValueError(f'Unsafe cleanup target: {path}')
    result = {'path': str(resolved), 'existed': path.exists(), 'files': 0,
              'directories': 0, 'logical_bytes': 0,
              'verified_internal_pytest_links': []}
    if not path.exists():
        return result

    def check_entry(entry: Path):
        info = entry.lstat()
        if entry.name.casefold() == '.git':
            raise ValueError(f'Cleanup refuses Git metadata: {entry}')
        if getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            target = entry.resolve()
            if not (entry.is_symlink() and entry.name.endswith('current')
                    and target.is_relative_to(resolved) and target != resolved):
                raise ValueError(f'Cleanup refuses an unverified reparse point: {entry}')
            result['verified_internal_pytest_links'].append({
                'path': str(entry), 'target': str(target),
                'within_owned_tree': True, 'traversed': False,
            })
        return info

    def walk_error(error: OSError):
        raise error

    check_entry(path)
    for folder, directories, files in os.walk(path, followlinks=False, onerror=walk_error):
        for child in list(directories):
            info = check_entry(Path(folder) / child)
            if getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                # Python shutil.rmtree unlinks directory symlinks. Do not walk
                # them here or double-count their target files during inspection.
                directories.remove(child)
        for filename in files:
            info = check_entry(Path(folder) / filename)
            result['logical_bytes'] += info.st_size
        result['directories'] += len(directories)
        result['files'] += len(files)
    return result


def main() -> None:
    # Inspect every absolute target before starting any recursive deletion.
    entries = [inspect_owned_tree(name) for name in OWNED_NAMES]
    for entry in entries:
        path = Path(entry['path'])
        try:
            if entry['existed']:
                shutil.rmtree(path)
            entry['status'] = 'deleted' if entry['existed'] else 'not_created'
        except OSError as exc:
            entry['status'] = 'failed'
            entry['error'] = f'{type(exc).__name__}: {exc}'
        entry['absent_after'] = not path.exists()
    report = {
        'schema': 'q1_round3_cleanup_v1', 'method': 'Python shutil.rmtree',
        'scope': 'Only the four Q1 round-three scratch directories listed below',
        'targets': entries,
        'all_targets_absent': all(row['absent_after'] for row in entries),
        'deleted_logical_bytes': sum(row['logical_bytes'] for row in entries
                                     if row['status'] == 'deleted'),
        'preserved': ['Q1 logs and round1/round2 evidence', 'earlier Q1 scratch directories',
                      'other worktrees', 'runs-next', 'runs-cc', 'all Git metadata'],
    }
    (HERE / 'cleanup_round3.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['all_targets_absent']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
