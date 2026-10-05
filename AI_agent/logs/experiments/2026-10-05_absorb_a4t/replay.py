"""A4-T offline source and frozen-plan replay; original run bytes are read only."""
import argparse
from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path

from PIL import Image
from shapely.geometry import Polygon

from scripts.tool_scripts.run_bim_agent import Toolkit
from scripts.tool_scripts.bim_agent_precision import building_precision
from src.agent.geometry.plan_drawing_differences import drawing_differences

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
EXPERIMENTS=HERE.parent
BASELINE='aa48d72f'
measure=importlib.import_module('AI_agent.logs.experiments.2026-10-03_tool_package_t1.measure_instructions')
frozen=importlib.import_module('AI_agent.logs.experiments.2026-09-30_instruction_fix.drawing_differences_validation')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name,data):
    (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def matches(item,entry,mpp,polygons):
    # Reuse the frozen spatial rule for an unsupported declared divider. Labels
    # and their geometry are unchanged; only the new diagnostic name is mapped.
    if item['type']=='unsupported_open_separator':
        item={**item,'type':'declared_divider_with_little_ink'}
    return frozen.matches(item,entry,mpp,polygons)


def sources():
    rows=[]
    good=list(EXPERIMENTS.glob('2026-10-01_opus_dev_sm2[145]'))
    good+=list(EXPERIMENTS.glob('2026-09-2*_sm2*run5[3-8]'))
    runs=good+[ROOT/'.tmp_a4t/history'/n/'bim' for n in ('sm25_runtime_anthropic','sm25_runtime_subscription')]
    for run in sorted(runs):
        path=sorted(run.glob('candidate_*/source_model.json'))[-1]
        before=sha(path)
        report=building_precision(Toolkit(run),path.parent.name)
        # Independent source-side arithmetic checks of every claimed deviation.
        source=json.loads(path.read_bytes()); boundaries={b['id']:b for b in source['boundaries']}
        incorrect=[]
        for item in report['items']:
            if item['type']=='storey_wall_offset':
                coordinates=[]
                for line in item['lines']:
                    axis='xy'.index(line['axis'])
                    values={v[axis] for bid in line['boundary_ids'] for v in boundaries[bid]['vertices']}
                    if values!={line['coordinate_m']}:
                        incorrect.append(item)
                    coordinates.append(line['coordinate_m'])
                if abs(abs(coordinates[1]-coordinates[0])-item['deviation_m'])>1e-8:
                    incorrect.append(item)
            elif item['type']=='thin_horizontal_contact':
                region=next(r for r in source['boundary_relations'] if r['boundary_ids']==item['boundary_ids'])['regions'][item['region']]
                spans=[max(v[i] for v in region['vertices'])-min(v[i] for v in region['vertices']) for i in (0,1)]
                if abs(min(spans)-item['width_m'])>1e-8:
                    incorrect.append(item)
        assert sha(path)==before and not incorrect
        row=dict(run=str(run.relative_to(ROOT)), candidate=path.parent.name, source_sha256=before,
                 good_reference=run in good, reported_nonexistent_deviations=len(incorrect), report=report)
        rows.append(row)
        print(run.name,path.parent.name,report['counts'],flush=True)
    save('source_replay.json',dict(model_requests=0,rows=rows,
        note='False deviation count checks literal source coordinates/contact widths; intent of near alignments remains review-only.',
        summary=dict(candidates=len(rows), good_candidates=sum(r['good_reference'] for r in rows),
            nonexistent_deviations=sum(r['reported_nonexistent_deviations'] for r in rows),
            items=dict(sum((Counter(r['report']['counts']) for r in rows),Counter())))))


def plans():
    old=measure.baseline_module('src/agent/geometry/plan_drawing_differences.py','a4t_before_differences',BASELINE)
    labels_path=EXPERIMENTS/'2026-09-30_instruction_fix/drawing_differences_labels.json'
    labels=json.loads(labels_path.read_text())
    inputs=[]
    for row in labels['drafts']:
        run=EXPERIMENTS/row['run'];draft=run/'plan_drafts'/row['draft']
        assert sha(draft/'plan.json')==row['plan_sha256']
        inputs.append((run,draft,row['image'],row))
    # All saved sm25 drafts, including the earlier millimetre failure: no repair.
    for name in ('sm25_runtime_subscription','sm25_runtime_anthropic'):
        run=ROOT/'.tmp_a4t/history'/name/'bim'
        for draft in sorted((run/'plan_drafts').glob('draft_*')):
            if (draft/'compilation.json').exists():
                image=json.loads((draft/'input.json').read_text())['image']
                inputs.append((run,draft,image,None))
    # Explicit double-line failure not part of the older 108 frozen drafts.
    run=EXPERIMENTS/'2026-09-30_sm24_instruction_fix_run100'
    inputs.append((run,run/'plan_drafts/draft_002','1f_view.png',None))
    results=[]
    for run,draft,image,label in inputs:
        plan=json.loads((draft/'plan.json').read_text())
        polygons={r['space_id']:Polygon(r['pixel_polygon']) for r in json.loads((draft/'compilation.json').read_text())['space_mapping']}
        with Image.open(run/'images'/image) as pic:
            before=old.drawing_differences(pic,plan)
            after=drawing_differences(pic,plan)
        novel=[item for item in after['items'] if item not in before['items']]
        record=dict(run=str(run.relative_to(ROOT)),draft=draft.name,image=image,frozen_108=label is not None,
            plan_sha256=sha(draft/'plan.json'),image_sha256=sha(run/'images'/image),
            before=before,after=after,novel_items=novel)
        if label:
            record['labels']=[dict(**entry,before_detected=any(matches(item,entry,label['mpp'],polygons)
                    for item in before['items'] if item.get('scope')!='floor'),
                after_detected=any(matches(item,entry,label['mpp'],polygons)
                    for item in after['items'] if item.get('scope')!='floor')) for entry in label['labels']]
            record['novel_matches']=[any(matches(item,entry,label['mpp'],polygons)
                                         for entry in label['labels']) for item in novel if item.get('scope')!='floor']
        results.append(record)
        print(run.name,draft.name,'old',before['total'],'new',after['total'],'novel',len(novel),flush=True)
        save('plan_replay.json',dict(model_requests=0,baseline_commit=BASELINE,frozen_labels_sha256=sha(labels_path),rows=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('group',choices=['sources','plans'])
    args=parser.parse_args()
    sources() if args.group=='sources' else plans()
