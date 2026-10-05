"""Prove the final naming-reference correction reuses only unchanged checks."""
import hashlib
import json
from pathlib import Path
import subprocess

from src.agent_runtime.agent_registry import agent_version_record

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    broad = json.loads((HERE/'validation/final/related.json').read_bytes())
    followup = json.loads((HERE/'validation/naming_reference/related.json').read_bytes())
    for row in (broad, followup):
        assert row['returncode'] == 0 and row['failures'] == row['errors'] == row['skipped'] == 0
        assert row['source_unchanged_during_run']
    changed = [name for name,sha in broad['source_sha256'].items()
               if digest((ROOT/name).read_bytes()) != sha]
    assert set(changed) == {'scripts/tool_scripts/bim_agent_guidance.py', 'src/agent_runtime/agent_versions.json'}
    guide_path = ROOT/'scripts/tool_scripts/bim_agent_guidance.py'
    old_guide = guide_path.read_text().replace('Public naming (bim_names_v2)', 'Public naming (bim_names_v1)')
    assert digest(old_guide.encode()) == broad['source_sha256']['scripts/tool_scripts/bim_agent_guidance.py']
    old_raw = subprocess.check_output(['git', 'show', '9438b084:src/agent_runtime/agent_versions.json'], cwd=ROOT)
    assert digest(old_raw) == broad['source_sha256']['src/agent_runtime/agent_versions.json']
    old, new = json.loads(old_raw), json.loads((ROOT/'src/agent_runtime/agent_versions.json').read_bytes())
    assert all(new['versions'][k] == v for k,v in old['versions'].items())
    assert set(new['versions']) - set(old['versions']) == {new['current_version']}
    direct = sorted(str(p.relative_to(ROOT)) for p in (ROOT/'tests').rglob('test*.py')
                    if any(name in p.read_text() for name in ('bim_agent_guidance', 'agent_versions')))
    assert followup['files'] == direct and set(direct) <= set(broad['files'])
    assert all(digest((ROOT/name).read_bytes()) == sha for name,sha in followup['source_sha256'].items())
    current = agent_version_record(ROOT)
    assert 'Public naming (bim_names_v2)' in guide_path.read_text()
    result = dict(agent_version=current['version_id'], model_requests=0,
        broad_files=len(broad['files']), broad_passed=broad['passed'],
        broad_direct_reference_files=len(broad['direct_reference_files']),
        followup_files=direct, followup_passed=followup['passed'], changed_since_broad=changed,
        only_source_change='Naming reference label bim_names_v1 -> bim_names_v2; executable behavior unchanged.',
        other_source_and_test_hashes_unchanged=True, both_runs_had_stable_source=True,
        current_registered_files_verified=len(current['files']))
    (HERE/'validation_reuse.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
