"""Lossless stream archival after invocation; no model-facing edits."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    rows = []
    for p in sorted(args.run.glob('*_stream.jsonl')):
        data = p.read_bytes()
        out = p.with_suffix('.jsonl.gz')
        if out.exists():
            raise SystemExit(f'Archive already exists: {out}')
        out.write_bytes(gzip.compress(data, mtime=0))
        assert gzip.decompress(out.read_bytes()) == data
        rows.append({'path': p.name, 'archive': out.name, 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'roundtrip_verified': True})
        p.unlink()
    (args.run/'stream_archive.json').write_text(json.dumps(rows, indent=2)+'\n')
