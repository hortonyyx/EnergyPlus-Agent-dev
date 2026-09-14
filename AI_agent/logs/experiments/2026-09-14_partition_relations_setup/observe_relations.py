"""Local wall/space-relation observation; independent of source models."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = "Observe only physical partition relationships in the middle-right part of this original plan.\nYour local scope is original pixel box [360,260,630,610]. View the whole plan for orientation,\nthen a clean magnified crop and any measurements needed. You may look just outside this box\nfor wall junctions. No source BIM, expected room count, wall locations or answers are supplied.\nDo not reconstruct the whole floor or calculate metric coordinates.\n\nWithin this scope identify visible physical dividers and their full path between enclosing\nwall junctions, including continuation through an actual doorway. Distinguish them from\nfurniture edges and door-leaf/swing strokes. For each divider give two clear interior-floor\npoints immediately on opposite sides, away from wall thickness and furniture. Explain\nwhether it separates two actual spaces, is merely a free-ended wall fragment within one\nspace, or is uncertain. Two points on opposite sides of some ink do not by themselves prove\na physical room division; cite the wall's extent, end junctions, and aperture evidence.\nIf needed return multiple observed alternatives instead of guessing.\n\nAlso report any clearly continuous interior passage through this local scope as a short\npath of interior points. Such a path must stay within one actual space; crossing a door\nbetween rooms is connectivity, not continuous-space evidence. Pixel components can leak\nthrough doorways and are never room identity by themselves.\n\nReturn a concise JSON object with image, scope_box, partitions, continuities and unresolved.\nEach partition has id, points (a polyline in original pixels), side_a and side_b (interior\npixel points), relation (separates_spaces, wall_fragment, or uncertain), and evidence (what\nvisible marks, junctions and openings support it, with original pixel locations).\nEach continuity has id, path (original-pixel polyline within one continuous space), evidence.\nOnly state measurements/relations you actually checked. Keep unexamined parts explicit.\nNo full-floor space count, BIM output, heights or windows are requested."


PROFILE_QUESTION = """Classify measured ink candidates in a bounded part of an original floor plan.
The developer selected box [360,260,630,610] and the measurement parameters below.
These are assistance, not an autonomous localization or a list of true walls.
No source BIM, expected room count, known wall coordinates, old observations or GT
are provided. Do not reconstruct the floor or create any new coordinate estimates.

First view the original plan and a clean enlarged local crop (coordinate_grid=false).
Then you MUST call view_pixel_profile twice, once with axis='x' and once axis='y',
using name='1f_view.png', box=[360,260,630,610], rgb=[169,169,169], tolerance=100,
min_fraction=0.3. This filter finds some grey ink, including furniture, intersecting
lines and walls. It does not identify objects or prove that missing ink is absent.
Use the returned candidate IDs, pixels and support_intervals_at_peak as exact
location references. A profile_record plus C## identifies a candidate uniquely.
Each support interval is numbered from 0 in its returned list. Do not replace the
actual disjoint intervals by their enclosing span. A one-pixel interval is usually
an intersecting stroke; it does not establish a wall running along this axis.

Inspect clean magnified original crops as needed to classify every candidate's
substantial intervals. Do not classify by color or length alone: check wall
thickness, junctions, doorway details and furniture context. Distinguish physical
walls from furniture edges, door leaves/arcs, annotation and uncertain marks.
Keep object identity separate from whether it actually divides spaces. A physical
wall with a free end may lie within one space; a door opening can belong to a
divider between two rooms. If parallel ink candidates are faces of the same wall,
group their references instead of counting them as separate room dividers.

Return JSON {image, scope_box, assessments, unresolved}. Each assessment has:
- id;
- refs: [{profile_record, candidate_id, interval_indices}];
- object: physical_wall | not_wall | uncertain;
- relation: separates_spaces | wall_fragment | exterior_boundary | not_applicable | uncertain;
- evidence: explain the actual visual junctions, thickness, opening or furniture
  context, citing measurement references rather than inventing pixel coordinates;
- gaps: explain only visually checked discontinuities, without filling them in.
You may classify disjoint portions separately. Account for all candidates, including
rejected ones; group only with visible evidence. Leave unresolved readings explicit.
Do not invent side points, continuous-space paths, metre coordinates, heights, room
counts or geometry. The result is a local observation, not a verified source model.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", choices=("haiku", "sonnet"), default="haiku")
    parser.add_argument("--mode", choices=("relations", "profile_candidates"), default="relations")
    parser.add_argument("--question-file", type=Path,
                        help="Explicit developer feedback; copied intact into the new run.")
    args = parser.parse_args()
    question = PROFILE_QUESTION if args.mode == "profile_candidates" else QUESTION
    if args.question_file:
        question = args.question_file.read_text()
    run = args.out.resolve()
    run.mkdir(parents=True, exist_ok=False)
    (run / "question.md").write_text(question)
    (run / "images").mkdir()
    original = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data/1f_view.png"
    shutil.copy2(original, run / "images" / original.name)
    with Image.open(original) as picture:
        size = list(picture.size)
    files = [ROOT / "scripts/tool_scripts/run_bim_agent.py",
             ROOT / "scripts/tool_scripts/bim_agent_guidance.py",
             *sorted((ROOT / "src/agent/geometry").glob("*.py")),
             ROOT / "src/agent/execution/subscription_json.py", Path(__file__).resolve()]
    optional = ROOT / "scripts/tool_scripts/bim_agent_inputs.py"
    if optional.exists():
        files.append(optional)
    frozen = {str(path.relative_to(ROOT)): path.read_bytes() for path in files}
    dump(run / "inputs.json", {
        "images": {original.name: {"size": size, "sha256": digest(original)}},
        "input_mode": "developer_scoped_local_feedback" if args.question_file else "developer_scoped_local_" + args.mode,
        "only_input": "One original plan and the exact question.md. Developer-selected crop, schema, measurement parameters or prior-observation feedback are explicit in the question. No building declaration, source BIM or GT. Assistance, not autonomous localization.",
        "question_sha256": digest(run / "question.md"),
        "implementation_sha256": {name: digest(ROOT / name) for name in frozen},
    })
    child, sha = prepare_detail_observation(Toolkit(run), question, [original.name],
                                             "detail_01", timeout_seconds=240)
    deadline = json.loads((child / "inputs.json").read_text())["deadline_epoch"]
    receipt = subscription(child, "Images: [1f_view.png]\nQuestion: " + question,
        model=args.model, effort="medium" if args.model == "sonnet" else None,
        name="detail_01", readonly=True, timeout=max(1, deadline - time.time()), log_run=run,
        receipt_context={"observation_source": {"run": "detail_01", "input_sha256": sha,
                              "images": {original.name: digest(original)}}})
    changed = []
    for name, data in frozen.items():
        if (ROOT / name).read_bytes() != data:
            changed.append(name)
        target = run / "implementation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    result = receipt.get("result", {})
    dump(run / "summary.json", {
        "actual_model": receipt.get("actual_model"), "effort": receipt.get("effort"),
        "elapsed_seconds": receipt["elapsed_seconds"],
        "completed": bool(result) and not result.get("is_error") and not receipt.get("timed_out"),
        "estimated_cost_usd": result.get("total_cost_usd"),
        "frozen_code_unchanged": not changed, "changed_files": changed,
        "limits": "Developer selected a middle-right crop, observation schema and budget; no answer feedback during execution. Not an autonomous BIM run or matched cost comparison. CLI estimate is not a bill.",
    })
    (run / "observation.md").write_text(result.get("result", "No completed answer"))
    print((run / "summary.json").read_text())


if __name__ == "__main__":
    main()
