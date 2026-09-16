"""Correct mixed reference bases without changing raw observations or geometry."""
from pathlib import Path
import hashlib, json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
source=HERE/'assembly_observations.json'
out=HERE/'assembly_observations_04.json'
assert not out.exists()
value=json.loads(source.read_text())
changes=[]
for row in value['openings']:
    refs=row.get('source_refs',[])
    resolved=[]
    for ref in refs:
        options=[ROOT/ref,HERE/ref,HERE/'openings'/ref]
        existing=[p.resolve() for p in options if p.is_file()]
        assert existing, f'Missing observation reference: {ref}'
        path=str(existing[0].relative_to(ROOT))
        resolved.append(path)
        if path!=ref:changes.append({'opening_id':row['id'],'before':ref,'after':path})
    if refs:row['source_refs']=resolved
value['reference_resolution']={'root':'repository root','parent_file_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'changes':changes,'geometry_changed':False,'raw_observations_changed':False,
 'scope':'Opening source_refs were relative to mixed observation directories; resolve their existing files to repository-relative paths. Inherited legacy evidence retains its recorded root.'}
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(f'Resolved {len(changes)} references; physical opening coordinates unchanged')
