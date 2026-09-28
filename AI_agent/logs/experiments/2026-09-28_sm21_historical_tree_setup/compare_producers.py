"""Feed identical saved declarations to both code versions, without model calls."""
import json
from pathlib import Path
import subprocess
import sys

from run_old import HERE, ROOT, TREE, load, save
from process_compare import RUNS

WORKER = r'''
import hashlib,json,sys,tempfile
from pathlib import Path
from PIL import Image
sys.path.insert(0,sys.argv[1])
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.geometry.plan_assembly import assemble_plan_proposals
sha=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
rows=[]
for value in sys.argv[2:]:
    run=Path(value)
    delivery=json.loads((run/'delivery.json').read_text())
    proposal=json.loads((run/delivery['candidate']/'proposal.json').read_text())
    with tempfile.TemporaryDirectory(prefix='producer-comparison-') as tmp:
        target=Path(tmp)/'candidate'
        export_source_proposal(proposal,target)
        source=json.loads((target/'source_model.json').read_text())
    physical={key:source[key] for key in ['floors','boundaries','openings','connections','opening_hosts','boundary_relations']}
    physical['spaces']=[{k:v for k,v in row.items() if k not in {'role','role_evidence','source_refs','assumptions'}} for row in source['spaces']]
    metadata=dict(room_source_ref_count=sum(len(row.get('source_refs',[])) for row in source['spaces']),
        rooms_with_role_evidence=sum(bool(row.get('role_evidence')) for row in source['spaces']),
        has_public_names='public_names' in source)
    drafts=[]
    for path in sorted((run/'plan_drafts').glob('draft_*/plan.json')):
        plan=json.loads(path.read_text())
        binding=json.loads((path.parent/'input.json').read_text())
        with Image.open(run/'images'/binding['image']) as image:
            try:
                result=compile_plan_partition(plan,image_size=image.size,image_name=binding['image'])
                drafts.append(dict(draft=path.parent.name,compiled_sha256=sha(result)))
            except (ValueError,TypeError) as error:
                drafts.append(dict(draft=path.parent.name,error=str(error)))
    rows.append(dict(run=run.name,candidate=delivery['candidate'],physical_sha256=sha(physical),drafts=drafts,metadata=metadata))
modules={fn.__name__:sys.modules[fn.__module__].__file__ for fn in [export_source_proposal,compile_plan_partition,assemble_plan_proposals]}
print(json.dumps(dict(runs=rows,modules=modules,
    module_sha256={name:hashlib.sha256(Path(path).read_bytes()).hexdigest() for name,path in modules.items()})))
'''


def compare():
    runs = [HERE.parent / name for name in RUNS
            if (HERE.parent / name / "summary.json").exists()
            and load(HERE.parent / name / "summary.json")["agent_response_completed"]]
    reports = []
    for tree in (TREE, ROOT):
        result = subprocess.run([sys.executable, "-c", WORKER, str(tree), *map(str, runs)],
                                text=True, capture_output=True, check=True)
        report = json.loads(result.stdout)
        assert all(Path(path).is_relative_to(tree) for path in report["modules"].values())
        reports.append(report)
    matches = []
    for old, current in zip(reports[0]["runs"], reports[1]["runs"], strict=True):
        assert old["run"] == current["run"]
        matches.append(dict(run=old["run"], candidate=old["candidate"],
            same_final_physical_geometry=old["physical_sha256"] == current["physical_sha256"],
            same_every_saved_plan_compilation_or_error=old["drafts"] == current["drafts"],
            saved_drafts=len(old["drafts"])))
    save(HERE / "producer_comparison.json", dict(matches=matches, producers=reports, model_calls=0,
        limits=["Same declarations, not a new generation experiment.",
            "Physical comparison excludes room role/evidence, source_refs/assumptions, public names and delivery metadata; metadata counts are reported separately.",
            "Equal physical output locates these errors upstream of deterministic conversion; it does not clear prompts/tools of behavioral effects."]))
    print(json.dumps(matches, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    compare()
