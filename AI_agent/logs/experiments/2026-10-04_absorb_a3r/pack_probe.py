"""Archive finished, credential-free A3-R evidence with a per-file hash manifest."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent

def main():
    result=json.loads((HERE/'sequence_result.json').read_bytes())
    if not result['complete']:raise ValueError('do not package an unfinished comparison')
    root=HERE/'probe'
    files={p.name:p.read_bytes() for p in root.iterdir() if p.is_file() and p.name!='batch.lock'}
    bundle=io.BytesIO()
    with gzip.GzipFile(fileobj=bundle,mode='wb',filename='',mtime=0) as gz:
        with tarfile.open(fileobj=gz,mode='w') as archive:
            for name,raw in sorted(files.items()):
                entry=tarfile.TarInfo(name);entry.size=len(raw);entry.mode=0o644
                archive.addfile(entry,io.BytesIO(raw))
    data=bundle.getvalue();name='sequence_evidence.tar.gz'
    (HERE/name).write_bytes(data)
    manifest={'archive':name,'archive_sha256':hashlib.sha256(data).hexdigest(),
        'archive_bytes':len(data),'file_count':len(files),
        'files_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}}
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
        read={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    assert files==read
    (HERE/'sequence_evidence_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    fields=['arm','replicate','step','input_tokens','cache_read_input_tokens','cache_creation_input_tokens',
        'output_tokens','total_tokens','seconds','first_byte_seconds','stop_reason']
    with (HERE/'sequence_steps.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader()
        for row in result['steps']:
            values={k:row[k] for k in fields if k in row}
            values.update({k:row['usage'].get(k,0) for k in fields if k.endswith('_tokens') and k!='total_tokens'})
            values['step']+=1
            writer.writerow(values)
    print(json.dumps({k:manifest[k] for k in ('archive','archive_bytes','file_count')}))

if __name__=='__main__':main()
