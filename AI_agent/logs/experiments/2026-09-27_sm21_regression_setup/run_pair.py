"""Isolate top-level guidance; all tools, references and feedback stay current."""
import argparse
import ast
import difflib
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

from scripts.tool_scripts import run_bim_agent as runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPE = importlib.import_module(
    'AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.run_cold').SCOPE


def guides():
    old = subprocess.check_output(['git', 'show',
        '468d83f7:scripts/tool_scripts/bim_agent_guidance.py'], cwd=ROOT, text=True)
    tree = ast.parse(old)
    baseline = next(ast.literal_eval(n.value) for n in tree.body
                    if isinstance(n, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == 'GUIDE' for t in n.targets))
    # Keep the current product policy, but omit newly added proactive evidence/
    # room-use follow-up instructions. On-demand references remain current.
    current = runner.GUIDE
    policy = current.split("Read get_bim_reference('room_types')", 1)[1].split(
        'After physical spaces exist,', 1)[0]
    policy = "Read get_bim_reference('room_types')" + policy
    anchor = 'Work from the physical partition layout before assigning detailed room uses.\n'
    assert baseline.count(anchor) == 1
    reduced = baseline.replace(anchor, anchor + policy)
    anchor = 'Prioritize faithful physical partitions and openings over an early first draft.\n'
    quota_note = current.split(anchor, 1)[1].split('Use the available budget', 1)[0]
    reduced = reduced.replace(anchor, anchor + quota_note)
    anchor = 'Parameter details are available through get_bim_reference(topic):\n'
    reduced = reduced.replace(anchor, anchor +
        '- room_types: required controlled room-use catalog, Chinese labels and fixed colors.\n'
        '- naming: automatic names for all viewer levels, blocks, faces, apertures and edges.\n')
    return {'current': current, 'baseline_policy': reduced}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('variant', choices=['current', 'baseline_policy'])
    parser.add_argument('--run', required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    assert Path(args.run).name == args.run
    variants = guides()
    for name, guide in variants.items():
        path = HERE / f'{name}_guide.txt'
        if path.exists():
            assert path.read_text() == guide, 'Frozen guide changed'
        else:
            path.write_text(guide)
    (HERE / 'guidance.diff').write_text(''.join(difflib.unified_diff(
        variants['current'].splitlines(True), variants['baseline_policy'].splitlines(True),
        fromfile='current', tofile='baseline_policy')))
    if args.prepare_only:
        return
    run = HERE.parent / args.run
    frozen = HERE / f'{args.run}_frozen.json'
    assert not run.exists() and not frozen.exists(), 'Never overwrite a prior experiment'
    images = ROOT / 'case_tests/e2e_tests/sm21_anchor/case_data'
    guide = variants[args.variant]
    runner.dump(frozen, dict(scope=SCOPE, mode='original_only_guidance_comparison',
        variant=args.variant, guide_sha256=hashlib.sha256(guide.encode()).hexdigest(),
        image_sha256={p.name: runner.digest(p) for p in sorted(images.glob('*.png'))},
        provider='claude', role='sonnet', effort='medium', timeout_seconds=3000,
        max_candidates=24, continuation_rounds=0,
        producer_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT,text=True).strip(),
        runner_sha256=runner.digest(Path(__file__)),
        controlled_difference='Top-level GUIDE only; same current tools, schemas, references, feedback, images, scope, quota and model settings.',
        withheld=['saved BIM/plans', 'old observations/calibrations', 'GT/evaluation',
                  'building declaration', 'correct counts/heights', 'developer local answers'],
        limits=['Not a full historical-runtime repeat.',
                'Single pair cannot establish a statistical cause; several new guide paragraphs are ablated as one group.',
                'Continuations disabled in both arms; does not test continuation effectiveness.']))
    runner.GUIDE = guide
    runner.run_experiment(SimpleNamespace(command='run', images=images, mesh=None,
        building_input=None, out=run, scope=SCOPE, timeout=3000,
        continuation_rounds=0, max_candidates=24, provider='claude', exploratory_opus=False,
        effort='medium', resume_candidate=None, resume_plan=None, plan_image=None))
    request = json.loads((run / 'agent_request.json').read_text())
    assert request['system_prompt'] == guide
    manifest = json.loads((run / 'inputs.json').read_text())
    for name, sha in manifest['implementation_sha256'].items():
        source = ROOT / name
        assert runner.digest(source) == sha, name
        target = run / 'runtime_snapshot' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


if __name__ == '__main__':
    main()
