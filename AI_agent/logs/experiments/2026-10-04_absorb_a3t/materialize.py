"""Extract hash-verified historical inputs inside this worktree; no model calls."""
import hashlib
import subprocess
import tarfile
import importlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / '.tmp_a3t' / 'history'

def archive(manifest_path, commit):
    manifest = json.loads(manifest_path.read_bytes())
    target = WORK / manifest['archive']
    if not target.exists():
        local = manifest_path.parent / manifest['archive']
        if local.is_file():
            target = local
        else:
            with target.open('wb') as out:
                for name in manifest.get('parts', {manifest['archive']: None}):
                    subprocess.run(['git', 'show', f'{commit}:{name}'], cwd=ROOT, stdout=out, check=True)
    with target.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == manifest['archive_sha256']
    hashes = {}
    with tarfile.open(target, 'r:xz') as handle:
        for member in handle:
            path = Path(member.name)
            if not member.isfile() or 'runtime_snapshot' in path.parts:
                continue
            if not (path.suffix in {'.json', '.png', '.jpg', '.jpeg'} or path.name in {'record.json.gz','tools.jsonl'}):
                continue
            destination = (WORK / path).resolve()
            assert destination.is_relative_to(WORK.resolve())
            raw = handle.extractfile(member).read()
            digest = hashlib.sha256(raw).hexdigest()
            expected = manifest['files_sha256'].get(member.name, manifest['files_sha256'].get(str(Path(*path.parts[1:]))))
            assert digest == expected, member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            hashes[member.name] = digest
    print(manifest['extracted_root'], len(hashes), flush=True)
    return dict(manifest=str(manifest_path.relative_to(ROOT)), commit=commit,
                archive_sha256=manifest['archive_sha256'], verified_selected_files=hashes)

def main():
    base = importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a1t.materialize')
    base.HERE = HERE
    base.WORK = WORK
    base.archive = archive
    # All JSON is useful for deterministic result replay, images for real MCP.
    selected = base.selected
    base.selected = lambda name: selected(name) or name.endswith('.json') and 'runtime_snapshot' not in Path(name).parts
    WORK.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in ('2026-10-04_node_regression_a1', '2026-10-04_qwen27b_probe'):
        for manifest in sorted((HERE.parent / name / 'evidence').glob('*_manifest.json')):
            if 'claude_code' in manifest.name:
                continue
            rows.append(base.archive(manifest, 'b88adef5'))
    (HERE / 'target_evidence_sources.json').write_text(json.dumps(rows, indent=2) + '\n')
    # A1-T corpus includes migration, subscription, C2 and T1 evidence.
    base.main()

if __name__ == '__main__':
    main()
