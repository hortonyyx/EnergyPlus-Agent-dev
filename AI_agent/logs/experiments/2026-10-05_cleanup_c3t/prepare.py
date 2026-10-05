"""Extract hash-verified historical runs and baseline code; no checkout or models."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / '.tmp_c3t'
BASE = 'a5baa32d'
EVIDENCE = 'evidence/node-regression-a1-2026-10-04'


def main():
    WORK.mkdir(exist_ok=True)
    rows = []
    for experiment in ('2026-10-04_node_regression_a1', '2026-10-04_qwen27b_probe', '2026-10-04_qwen27b_after_a2'):
        for manifest in sorted((HERE.parent / experiment / 'evidence').glob('*_manifest.json')):
            data = json.loads(manifest.read_bytes())
            archive = manifest.parent / data['archive']
            if archive.is_file():
                raw = archive.read_bytes()
                origin = str(archive.relative_to(ROOT))
            else:
                origin = EVIDENCE + ':' + archive.name
                raw = subprocess.check_output(['git', 'show', origin], cwd=ROOT)
            assert hashlib.sha256(raw).hexdigest() == data['archive_sha256']
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:xz') as tar:
                tar.extractall(WORK / 'history', filter='data')
            root = WORK / 'history' / data['extracted_root']
            for relative, sha in data['files_sha256'].items():
                assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == sha, relative
            rows.append(dict(run=data['extracted_root'], origin=origin, archive_sha256=data['archive_sha256'],
                verified_files=len(data['files_sha256'])))
            print(rows[-1]['run'], rows[-1]['verified_files'], flush=True)
    raw = subprocess.check_output(['git', 'archive', BASE, 'scripts'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        tar.extractall(WORK / 'baseline', filter='data')
    (WORK / 'baseline/scripts/__init__.py').touch()
    # Current offline behaviour readers import the new contract module; fallback
    # only for modules absent in the baseline, never for its existing tool code.
    (WORK / 'baseline/scripts/tool_scripts/__init__.py').write_text(
        '__path__.append(' + repr(str(ROOT / 'scripts/tool_scripts')) + ')\n')
    (HERE / 'evidence_sources.json').write_text(json.dumps(dict(baseline=BASE, model_requests=0, runs=rows), indent=2)+'\n')


if __name__ == '__main__':
    main()
