"""Replay every saved source and produce clearly post-run inspection views."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.proposal_edits import apply_proposal_edits
from src.agent.geometry.source_image_overlay import render_source_overlay
from src.agent.geometry.source_plan_view import render_source_plan

read = lambda path: json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    summary = read(run/'summary.json')
    rows = []
    for path in sorted(run.glob('candidate_*/source_model.json')):
        candidate = path.parent
        proposal = read(candidate/'proposal.json')
        provenance = read(candidate/'report.json')['provenance']
        row = {'candidate': candidate.name, 'checks': {}}
        if (candidate/'operations.json').exists():
            previous = read(run/provenance['parent_candidate']/'proposal.json')
            row['checks']['operations_reproduce_proposal'] = (
                apply_proposal_edits(previous, read(candidate/'operations.json')) == proposal)
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)/'reexport'
            export_source_proposal(proposal, out, provenance=provenance)
            row['checks']['source_reexport_matches'] = read(out/'source_model.json') == read(path)
        rows.append(row)
    selected = summary['delivery']['candidate']
    source = read(run/selected/'source_model.json')
    folder = run/'post_run_inspection'
    folder.mkdir(exist_ok=False)
    plan, plan_metadata = render_source_plan(source, 'F1')
    plan.save(folder/'source_plan.png')
    image, metadata = render_source_overlay(source, Image.open(run/'images/1f_view.png'),
        floor_id='F1', x_anchors=[[248, 0], [612, 10]], y_anchors=[[880, 0], [150, 20]],
        image_name='1f_view.png',
        basis='Post-run developer inspection only: approximate original exterior endpoints and visible 10000/20000 mm overall labels. Shared with prior assisted inspection; no fitting to the generated source or GT. Pixel face offsets remain unverified. Never returned to generating agent.')
    image.save(folder/'source_on_original.png')
    metadata.update(developer_post_run_only=True, returned_to_generating_agent=False)
    (folder/'source_on_original.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    (folder/'source_plan.json').write_text(json.dumps(plan_metadata, ensure_ascii=False, indent=2)+'\n')
    report = {'selected': selected, 'candidates': rows,
              'all_replays_match': all(all(row['checks'].values()) for row in rows),
              'inspection_views': 'post_run_inspection; developer-only, not runtime feedback or a fidelity verdict'}
    (run/'source_replay.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    assert report['all_replays_match'], report
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
