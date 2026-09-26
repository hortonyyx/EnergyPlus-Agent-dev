"""Independent original-pixel evaluation after each observation finishes."""
import argparse
from collections import Counter
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw
from scipy.optimize import linear_sum_assignment
from shapely.geometry import LineString, Polygon

from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent
REFERENCE = {
    "image": "1f_view.png",
    "room_polygon_pixels": [[400,753],[459.5,753],[459.5,698.5],[607.5,698.5],[607.5,874],[400,874]],
    "doors": [
        {"id":"interior", "p1":[559,698.5], "p2":[592,698.5], "destination":"interior"},
        {"id":"exterior", "p1":[413,874], "p2":[445,874], "destination":"exterior"},
    ],
    "pixel_tolerance": 6,
    "minimum_iou": .92,
    "basis": "Development review of the original image plus saved x/y profiles; representative wall-band midlines. Reference is not supplied to either model.",
    "qualitative_reference": "Six-turn stepped room, two boundary doors; no partition continuing the east-middle room's west wall through the open circulation above this room.",
    "limitations": ["One development-selected room; not a whole-building GT.",
                    "Developer has historical case context. Exact pixel reference is approximate, not surveyed geometry.",
                    "Numerical correspondence does not establish the correctness of the explanatory prose."],
}


def parse_answer(text):
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "room_polygon_pixels" in value:
            return value
    raise ValueError("No complete observation JSON; preserve answer as failed/incomplete")


def audit(run):
    assert (run / "summary.json").exists(), "wait for model completion"
    manifest = json.loads((run / "inputs.json").read_text())
    assert digest(run / "images/1f_view.png") == manifest["images"]["1f_view.png"]["sha256"]
    answer = parse_answer((run / "answer.txt").read_text())
    dump(run / "parsed_observation.json", answer)
    ref, candidate = Polygon(REFERENCE["room_polygon_pixels"]), Polygon(answer["room_polygon_pixels"])
    valid = candidate.is_valid and candidate.area > 0
    iou = candidate.intersection(ref).area / candidate.union(ref).area if valid else None
    distance = candidate.boundary.hausdorff_distance(ref.boundary) if valid else None
    self_consistency = [dict(id=d['id'], on_own_room_boundary=bool(valid and
        candidate.boundary.buffer(1e-7).covers(LineString([d['p1'], d['p2']]))))
        for d in answer.get('doors', [])]
    costs = [[LineString([a['p1'], a['p2']]).hausdorff_distance(LineString([b['p1'],b['p2']]))
              for b in answer.get('doors', [])] for a in REFERENCE['doors']]
    doors = []
    if answer.get('doors'):
        for i, j in zip(*linear_sum_assignment(costs)):
            expected, actual = REFERENCE['doors'][int(i)], answer['doors'][int(j)]
            doors.append(dict(reference=expected['id'], actual_id=actual['id'],
                endpoint_hausdorff_pixels=costs[i][j],
                within_tolerance=costs[i][j] <= REFERENCE['pixel_tolerance'],
                destination_match=actual['destination'] == expected['destination']))
    actions = [json.loads(line) for line in (run/'tools.jsonl').read_text().splitlines()]
    tool_counts = dict(Counter(row['action'] for row in actions))
    profiles = sorted((run/'pixel_profiles').glob('profile_*.json'))
    regions = sorted((run/'pixel_regions').glob('region_*.json'))
    allowed_visual = {'inputs','view_image'}
    compliance = (not (set(tool_counts) - allowed_visual) if manifest['observation_condition']=='visual'
                  else bool(profiles or regions))
    cited = []
    for row in answer.get('measurements_used', []):
        identity = row.get('record','')
        match = re.fullmatch(r'((?:profile|region|overview)_\d+)(?: \([^\n()]+\))?', identity)
        normalized = match.group(1) if match else None
        candidates = [run/folder/f'{normalized}.json' for folder in ('pixel_profiles','pixel_regions','pixel_region_overviews')]
        cited.append(dict(record=identity, normalized_id=normalized,
            exists=bool(normalized and any(p.is_file() for p in candidates)), use=row.get('use')))
    report = dict(condition=manifest['observation_condition'],
        source_image_sha256=manifest['images']['1f_view.png']['sha256'],
        polygon_valid=valid, vertex_count=len(answer['room_polygon_pixels']), iou=iou,
        boundary_hausdorff_pixels=distance,
        complete_room_boundary_within_tolerance=valid and distance <= REFERENCE['pixel_tolerance'] and iou >= REFERENCE['minimum_iou'],
        door_count=len(answer.get('doors',[])), doors=doors,
        door_self_consistency=self_consistency,
        complete_door_geometry_match=len(answer.get('doors',[]))==len(REFERENCE['doors']) and
            all(row['within_tolerance'] and row['destination_match'] for row in doors),
        tools=tool_counts, tool_usage_condition_met=compliance, cited_measurements=cited,
        tool_usage_limit='Only tool-access restriction / presence of saved numeric evidence is checked; complete method compliance and correct use of evidence require semantic review.',
        semantic_reasoning_review='See separate evaluation/semantic_review.json when completed; numerical checks do not review prose.',
        reference=REFERENCE, generation_already_finished=True)
    output = run/'evaluation';output.mkdir(exist_ok=True)
    dump(output/'local_geometry.json',report)
    original = Image.open(run/'images/1f_view.png').convert('RGB')
    marked=original.copy();draw=ImageDraw.Draw(marked)
    for vertices,color in ((REFERENCE['room_polygon_pixels'],'yellow'),(answer['room_polygon_pixels'],'magenta')):
        pts=[tuple(p) for p in vertices];draw.line([*pts,pts[0]],fill=color,width=2)
    marked.save(output/'boundary_overlay.png')
    dump(HERE/'developer_reference/reference.json',REFERENCE)
    print(json.dumps({k:report[k] for k in ('condition','iou','boundary_hausdorff_pixels','vertex_count',
        'complete_room_boundary_within_tolerance','door_count','complete_door_geometry_match','tools','tool_usage_condition_met')},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path)
    audit(parser.parse_args().run.resolve())
