"""Rebuild eight historical behaviour reports from immutable, hash-checked inputs.

No model/network calls. Archives and temporary full reports stay in this worktree.
Only summaries, readable timelines and hashes need to be committed; original
bytes remain in the existing evidence branch/mainline instead of being repacked.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from src.agent.runtime_behaviour import write_behaviour_report

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPERIMENTS = HERE.parent
EVIDENCE = EXPERIMENTS / '2026-10-03_migration_comparison/evidence'
RECORDS = EXPERIMENTS / '2026-10-01_behaviour_records/records'
EVIDENCE_COMMIT = '6b612d54c0a413d8456bc3eb408e2094b76d2d63'
T1_COMMIT = '74e27da33d8f957334b6e77c40e788acf015ea55'
RUNS = ('attempt_01', 'attempt_02', 'attempt_03', 'subscription_01', 'subscription_02', 'subscription_03')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def materialize(work):
    work.mkdir(parents=True, exist_ok=True)
    sources = []
    for case in ('sm24', 'sm25'):
        name = f'2026-10-03_{case}_glm_tools_t1'
        prefix = f'AI_agent/logs/experiments/{name}'
        names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', T1_COMMIT, prefix], cwd=ROOT, text=True).splitlines()
        selected = [n for n in names if '/claims/' in n or n.endswith(('/source_model.json', '/report.json', '/inputs.json'))]
        hashes = {}
        for name_in_git in selected:
            relative = Path(name_in_git).relative_to('AI_agent/logs/experiments')
            target = work / relative
            raw = subprocess.check_output(['git', 'show', f'{T1_COMMIT}:{name_in_git}'], cwd=ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            hashes[str(relative)] = sha(raw)
        source = RECORDS / name / 'record.json.gz'
        sources.append(dict(name=name, path=source, source_root=work/name,
            evidence=dict(record=str(source.relative_to(ROOT)), record_sha256=sha(source.read_bytes()),
                          saved_source_commit=T1_COMMIT, saved_files_sha256=hashes)))
    for label in RUNS:
        manifest_path = EVIDENCE / f'{label}_manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        archive = EVIDENCE / manifest['archive']
        if not archive.is_file():
            archive = work / manifest['archive']
            if not archive.is_file():
                with archive.open('wb') as out:
                    subprocess.run(['git', 'show', f'{EVIDENCE_COMMIT}:{manifest["archive"]}'], cwd=ROOT, stdout=out, check=True)
        assert sha(archive.read_bytes()) == manifest['archive_sha256'], archive
        run = work / manifest['extracted_root']
        if not run.exists():
            with tarfile.open(archive, 'r:xz') as handle:
                handle.extractall(work, filter='data')
        for relative, digest in manifest['files_sha256'].items():
            assert sha((work/relative).read_bytes()) == digest, relative
        sources.append(dict(name=label, path=run, source_root=run,
            evidence=dict(archive=manifest['archive'], archive_sha256=manifest['archive_sha256'],
                          manifest=str(manifest_path.relative_to(ROOT)), verified_files=len(manifest['files_sha256']),
                          evidence_commit=EVIDENCE_COMMIT if archive.parent == work else None)))
    return sources


def rebuild(work, output):
    sources = materialize(work)
    rows = []
    for source in sources:
        full = work / 'regenerated' / source['name']
        summary = write_behaviour_report(source['path'], full, source_root=source['source_root'])
        target = output / 'records' / source['name']
        target.mkdir(parents=True, exist_ok=True)
        for name in ('summary.json', 'timeline.md'):
            shutil.copyfile(full/name, target/name)
        record = full/'record.json.gz'
        rows.append(dict(name=source['name'], input=source['evidence'],
            complete_record_sha256=sha(record.read_bytes()), complete_record_bytes=record.stat().st_size,
            **{key: summary[key] for key in ('tool_calls', 'call_errors', 'domain_failures', 'usable_source_drafts',
                'turns', 'first_build_attempt_s', 'first_draft_s', 'claims_from_saved_files',
                'full_views_before_first_build_attempt', 'crop_scales')}))
        print(json.dumps({key: rows[-1][key] for key in ('name','tool_calls','call_errors','domain_failures','usable_source_drafts')}, ensure_ascii=False), flush=True)
    result = dict(model_requests=0, schema_version='bim.behaviour.v2', runs=rows,
        complete_records='Generated in temporary worktree directory; hashes retained, full records reproducible from referenced immutable inputs. No duplicate archive is committed.')
    (output/'behaviour_rebuild.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE)
    parser.add_argument('--work', type=Path, help='Keep extracted evidence here while doing other offline replays; remove when finished')
    parser.add_argument('--materialize-only', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.work:
        if not args.work.resolve().is_relative_to(ROOT):
            raise ValueError('temporary evidence must stay within this worktree')
        if args.materialize_only:
            print([s['name'] for s in materialize(args.work.resolve())])
        else:
            rebuild(args.work.resolve(), args.output)
    else:
        with tempfile.TemporaryDirectory(prefix='.c2-records-', dir=ROOT) as directory:
            rebuild(Path(directory), args.output)


if __name__ == '__main__':
    main()
