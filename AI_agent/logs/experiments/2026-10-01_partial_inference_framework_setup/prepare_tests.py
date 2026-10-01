"""Freeze the same common runtime, raw evidence and task for two developer tests.

No model is called here. Accepted BIMs, case scripts and measured window tables
are not copied. Temporary workspaces are later archived by the coordinator.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/ep-partial-developer-tests-20261001')

TASK = """Develop a complete viewable lightweight BIM for the target single building
in the admitted original textured GLB, using the common BIM framework. This is
partial inference at a fine space-detail level for an office building. The
additional four raw, unlabeled parent-tile context crops can help interpret the
target's missing surfaces; neighboring buildings are context, not BIM targets.
Infer useful plausible physical rooms, circulation, openings and roof ancillary
spaces where interior or exterior evidence is missing. Keep observed, inferred
and simplified decisions explicit. Use reasonable architectural dimensions;
do not chase noisy texture pixels. Fine detail does not require inventing
partitions in physically continuous spaces. Choose simpler interpretations
where evidence supports several equally plausible alternatives.
The target is a complete architecturally plausible building, not a quick shell.
No fixed expected space/opening count or preselected building coordinates is given.
"""

INSTRUCTIONS = """You are independently testing the initial partial-inference framework.
Your permitted input/code area is {runtime} and your OWN run {run}.
Do not read any repository, history, sibling run, prior BIM, prior observations,
case builders, evaluation files or this conversation's other agents. Do not use
network, other models, subagents or an external API. No human corrections will be
fed into this run. This separation is instruction-based, not a filesystem sandbox.
Only create/modify files under your own run. The frozen runtime is read-only.
Keep inputs.json, task.txt, guide.txt, DEVELOPER_TASK.txt, preparation.json and
controller files unchanged; they are fixed experiment inputs/records.

Read task.txt and guide.txt in your run. The same BIM MCP tools are accessible by:
/opt/venv/bin/python {runtime}/scripts/tool_scripts/bim_agent_bridge.py --run {run}
This lists tool schemas. To call tools, write a JSON list of
[{{"tool":"inputs","arguments":{{}}}},{{"tool":"get_bim_reference","arguments":{{"topic":"partial_inference"}}}}]
and pass that file after --run PATH, or '-' for stdin. Each batch shares one MCP
session, executes sequentially and stops at a tool error. Exact requests/replies
and returned images are saved in your run/bridge. Inspect those image files with
your image tool. Python assembly scripts for your OWN interpretation are allowed;
all source builds/revisions and views must use the common tool interface.
Read tool references as useful (partial_inference, geometry, parametric, room_types,
edits). No model delegation is available. You may read frozen generic source code
to understand an interface; do not modify it or bypass a failed source check.

Choose your own observations, frame, architectural interpretation and revisions.
Use saved mesh observations and measurements to constrain geometry; then inspect
the actual source plans/overlays and repair material discrepancies before finishing.
Use record_inference to preserve key hypotheses, audit_inference_candidate to
review actual source facts, and finish_bim to select the completed candidate.
These tools do not substitute for your architectural and visual judgment.
Keep final files, errors, scripts and tool history. Write a concise RESULT.md in
your run naming the selected candidate, checks, observation basis, unresolved
limitations, framework issues and any prohibited-input exposure (if any).
Budget: up to 60 minutes, quality takes priority over fast first output. One run,
no automatic restart or fallback. Save partial work honestly if blocked. Do not
change the model or claim user acceptance. Return the result and paths to root.
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    WORK.mkdir(exist_ok=False)
    runtime = WORK / 'runtime'
    for relative in ('src', 'scripts/tool_scripts'):
        shutil.copytree(ROOT / relative, runtime / relative,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for relative in ('scripts/__init__.py',):
        if (ROOT / relative).exists():
            shutil.copy2(ROOT / relative, runtime / relative)
    code = {str(path.relative_to(runtime)): digest(path)
            for path in sorted(runtime.rglob('*')) if path.is_file()}
    originals = WORK / 'context'; originals.mkdir()
    previous = ROOT / 'AI_agent/logs/experiments/2026-09-10_showcase_voimatalo_revision'
    evidence = {}
    for relative, name in (('context/courtyard.png', 'parent_courtyard.png'),
                           ('context/top.png', 'parent_top.png'),
                           ('missing_measurements/core_front.png', 'parent_detail_front.png'),
                           ('missing_measurements/core_side.png', 'parent_detail_side.png')):
        source = previous / relative
        shutil.copy2(source, originals / name)
        evidence[name] = {'source': str(source.relative_to(ROOT)), 'sha256': digest(source),
                          'interpretation': 'unlabeled historical raw parent-tile crop; selected supplemental view, not BIM or measurements'}
    mesh = ROOT / 'showcase/2026-09-11-research-report/demos/textured-mass/input.glb'
    runs = []
    for name, model in [('run_61sol', 'gpt-6.1-sol'), ('run_6sol', 'gpt-6-sol')]:
        run = WORK / name
        agent_runtime = WORK / name.replace('run_', 'runtime_')
        shutil.copytree(runtime, agent_runtime)
        command = [sys.executable, str(agent_runtime / 'scripts/tool_scripts/run_bim_agent.py'),
                   'run', '--prepare-only', '--images', str(originals), '--mesh', str(mesh),
                   '--out', str(run), '--scope', TASK, '--timeout', '3600', '--max-candidates', '24']
        prepared = subprocess.run(command, capture_output=True, text=True)
        if prepared.returncode:
            (HERE / 'preparation_failure.txt').write_text(prepared.stderr)
            raise RuntimeError(prepared.stderr)
        manifest = json.loads((run / 'inputs.json').read_text())
        # An external development controller is not the Claude default runtime route.
        manifest['provider'] = 'external_development_agent'
        manifest['development_model'] = model
        manifest['effort'] = 'max'
        manifest['supplemental_evidence'] = {name: {key: value for key, value in row.items() if key != 'source'}
                                             for name, row in evidence.items()}
        manifest['mesh_input']['source_path'] = 'admitted original single-building GLB'
        manifest['execution_channel'] = 'collaboration.spawn_agent; clean fork; common MCP bridge; instruction-based file scope'
        (run / 'inputs.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        instructions = INSTRUCTIONS.format(runtime=agent_runtime, run=run)
        (run / 'DEVELOPER_TASK.txt').write_text(instructions)
        runs.append({'run': name, 'model': model, 'effort': 'max', 'status': 'prepared_not_started',
                     'prompt_sha256': digest(run / 'DEVELOPER_TASK.txt'),
                     'task_sha256': digest(run / 'task.txt'), 'guide_sha256': digest(run / 'guide.txt'),
                     'prepared_inputs_sha256': digest(run / 'inputs.json'),
                     'preparation_sha256': digest(run / 'preparation.json')})
    with tarfile.open(HERE / 'frozen_runtime.tar.gz', 'w:gz') as archive:
        archive.add(runtime, arcname='runtime')
    result = {'status': 'prepared_not_run', 'user_authorization': '好的，继续推进；一会儿开发模型测试用6.1sol和6sol',
              'models': runs, 'max_seconds_each': 3600, 'max_candidates_each': 24,
              'model_calls_in_preparation': 0, 'mesh_sha256': digest(mesh),
              'supplemental_evidence': evidence, 'runtime_files': code,
              'runtime_archive_sha256': digest(HERE / 'frozen_runtime.tar.gz'),
              'python_environment': {'executable': sys.executable, 'version': sys.version,
                  'packages': {name: importlib.metadata.version(name)
                               for name in ('mcp', 'Pillow', 'trimesh', 'numpy', 'shapely', 'pydantic')}},
              'shared_task': TASK, 'shared_developer_instructions': INSTRUCTIONS,
              'isolation': 'separate clean agent contexts and run directories; instruction-based allowed paths, no OS read isolation',
              'usage_limit': 'orchestrator tool does not expose token or billing receipts; do not estimate missing figures',
              'evaluation_only': 'accepted fine-detail BIM, historical proposals/builders/measurements; never copied into generator input',
              'not_in_scope': ['working-model experiments', 'reconstruction B/C regression', 'paid API', 'DeepSeek', 'automatic retries/fallback']}
    (HERE / 'test_manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'work': str(WORK), 'runs': runs, 'runtime_files': len(code)}, indent=2))


if __name__ == '__main__':
    main()
