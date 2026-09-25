"""Archive the completed, redacted development stream without losing its evidence."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    receipt = json.loads((HERE/'opus_receipt.json').read_text())
    assert 'returncode' in receipt, 'Wait for the development process to stop'
    assert receipt['actual_model'] == 'claude-opus-5-5'
    stream = HERE/'opus_stream.jsonl'
    target = HERE/'opus_stream.jsonl.gz'
    assert not target.exists()
    payload = stream.read_bytes()
    compressed = gzip.compress(payload, mtime=0)
    assert gzip.decompress(compressed) == payload
    target.write_bytes(compressed)
    assert gzip.decompress(target.read_bytes()) == payload
    metadata = {'stream':target.name, 'original_bytes':len(payload),
        'compressed_bytes':len(compressed), 'lossless_after_secret_redaction':True,
        'uncompressed_sha256':hashlib.sha256(payload).hexdigest(),
        'compressed_sha256':hashlib.sha256(compressed).hexdigest(),
        'actual_model':receipt['actual_model'], 'elapsed_seconds':receipt['elapsed_seconds'],
        'returncode':receipt['returncode'], 'timed_out':receipt.get('timed_out',False),
        'is_error':receipt.get('result',{}).get('is_error'),
        'terminal_result':receipt.get('result',{}).get('result'),
        'usage':receipt['result'].get('modelUsage'),
        'subagent_stats':receipt['result'].get('subagent_stats'),
        'estimated_total_cost_usd_not_bill':receipt['result'].get('total_cost_usd')}
    (HERE/'opus_stream_archive.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    stream.unlink()
    print(json.dumps({k:v for k,v in metadata.items() if k not in {'usage','subagent_stats'}},ensure_ascii=False))


if __name__ == '__main__':
    main()
