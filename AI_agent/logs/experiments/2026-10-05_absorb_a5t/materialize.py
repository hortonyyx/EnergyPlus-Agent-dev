"""Restore hash-verified history inside this worktree; no model requests."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / '.tmp_a5t/history'


def main():
    rows = []
    for folder, commit in (
        ('2026-10-04_node_regression_a1', 'b88adef5'),
        ('2026-10-04_node_regression_c2', '57879421'),
        ('2026-10-04_qwen27b_probe', 'b88adef5'),
        ('2026-10-04_qwen27b_after_a2', None),
    ):
        work = WORK / folder
        work.mkdir(parents=True, exist_ok=True)
        for path in sorted((HERE.parent / folder / 'evidence').glob('*_manifest.json')):
            manifest = json.loads(path.read_bytes())
            archive = path.parent / manifest['archive']
            if not archive.is_file():
                archive = work / manifest['archive']
                with archive.open('wb') as stream:
                    for name in manifest.get('parts', {manifest['archive']: None}):
                        subprocess.run(['git', 'show', f'{commit}:{name}'], cwd=ROOT, stdout=stream, check=True)
            with archive.open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == manifest['archive_sha256']
            hashes = {}
            with tarfile.open(archive, 'r:xz') as tar:
                for member in tar:
                    p = Path(member.name)
                    if not member.isfile() or 'runtime_snapshot' in p.parts:
                        continue
                    if not (p.name in {'record.json.gz', 'tools.jsonl', 'inputs.json', 'source_model.json', 'proposal.json'}
                            or p.name == 'events.jsonl' and folder == '2026-10-04_qwen27b_after_a2'
                            or p.suffix == '.json' and any(s in p.parts for s in ('plan_drafts', 'plan_assemblies', 'claims'))):
                        continue
                    target = (work / p).resolve()
                    assert target.is_relative_to(work.resolve())
                    raw = tar.extractfile(member).read()
                    digest = hashlib.sha256(raw).hexdigest()
                    expected = manifest['files_sha256'].get(member.name,
                        manifest['files_sha256'].get(str(Path(*p.parts[1:]))))
                    assert digest == expected, member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                    hashes[member.name] = digest
            rows.append(dict(manifest=str(path.relative_to(ROOT)), commit=commit,
                archive_sha256=manifest['archive_sha256'], verified_files=hashes))
            (HERE / 'evidence_sources.json').write_text(json.dumps(rows, indent=2)+'\n')
            print(folder, manifest['extracted_root'], len(hashes), flush=True)


if __name__ == '__main__':
    main()
