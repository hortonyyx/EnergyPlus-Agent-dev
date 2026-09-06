"""Reproducible guard omissions; each changed source is restored in finally.

Run only with no concurrent test/build process in this worktree. This is a
manual acceptance probe, not a member of the ordinary pytest suite.
"""
from pathlib import Path
import json
import os
import re
import subprocess

ROOT = Path('/tmp/ea2_astra')
HERE = ROOT / 'AI_agent/logs/reviews/execution/2026-09-06d_Ea2_evidence'
TICK = 'src/agent/correction/tick_claim.py'
REVIEW = 'src/agent/correction/opening_adjudication.py'
PIPELINE = 'src/agent/pipeline.py'
OPENING_TEST = 'tests/test_ea2_opening_pipeline.py::'
TICK_TEST = 'tests/test_ea2_native_tick.py::'

PROBES = [
    ('E-a-1', REVIEW,
     '''    def _check_current(self):
        self._plan.consume(self._plan_batch)
        for facade in self._facades:
            if facade.session is not None:
                facade.session.consume(facade.expected_batch_id)
''',
     '''    def _check_current(self):
        pass  # mutation: treat the cached review as current
''', OPENING_TEST + 'test_ea1_pipeline_rejects_stale_batch'),
    ('E-a-2', PIPELINE,
     '    review.persist(archive, expected_result_id)',
     '    archive.mkdir(parents=True, exist_ok=True)  # mutation: preview-only output',
     OPENING_TEST + 'test_ea2_pipeline_archive_rebuilds_every_batch_byte_for_byte'),
    ('E-a-3', PIPELINE,
     'def run_opening_adjudication(geometry,',
     'def _ea_mutation_legacy_caller():\n    synthesize_openings(elevation_doc={})\n\n\ndef run_opening_adjudication(geometry,',
     OPENING_TEST + 'test_ea3_no_production_call_to_historical_dict_api'),
    ('E-a-4', TICK,
     '    if not hyp.get("pairs") or hyp.get("pairs_status") != "SELECTED":',
     '    if False and (not hyp.get("pairs") or hyp.get("pairs_status") != "SELECTED"):',
     TICK_TEST + 'test_ea4_model_selection_required'),
    ('E-a-5', TICK,
     '    if decision.contract_id != CONTRACT_AS_DRAWN_PLAN:',
     '    if False and decision.contract_id != CONTRACT_AS_DRAWN_PLAN:',
     TICK_TEST + 'test_ea5_missing_hypotheses_named_refusal'),
    ('visibility', REVIEW,
     '    def _require_visible(self, binding, span_u):\n',
     '''    def _require_visible(self, binding, span_u):
        if binding.family == "South" and binding.line.pos_m != min(
                p[1] for p in json.loads(self._geometry_bytes)["floors"][0]["footprint"]["vertices"]):
            raise TickClaimError("MUTATION_BBOX_EXTREME")
''', OPENING_TEST + 'test_recessed_visible_wall_is_not_replaced_by_bbox_extreme'),
    ('A-6-d1', TICK,
     '                if values[0] >= values[1]:',
     '                if False and values[0] >= values[1]:',
     OPENING_TEST + 'test_elevation_consumer_rechecks_order_when_upstream_guard_is_bypassed'),
]


def main():
    assert Path.cwd() == ROOT
    results = []
    for name, filename, old, new, node in PROBES:
        path = ROOT / filename
        original = path.read_bytes()
        source = original.decode()
        assert source.count(old) == 1, (name, 'mutation anchor is not unique')
        command = ['python', '-m', 'pytest', '-q', '-n', '6', '-p', 'no:cacheprovider',
                   '--basetemp=/var/tmp/ea2_astra_pytest/mutation_' + name, node]
        try:
            path.write_text(source.replace(old, new), encoding='utf-8')
            run = subprocess.run(command, cwd=ROOT, env={**os.environ,
                'TMPDIR': '/var/tmp/ea2_astra_pytest'}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        finally:
            path.write_bytes(original)
        log = run.stdout.decode()
        (HERE / ('red_' + name + '.log')).write_bytes(run.stdout)
        summaries = [line for line in log.splitlines() if re.search(r'\d+ failed.* in ', line)]
        assert summaries and 'FAILED ' + node in log, (name, log[-3000:])
        results.append(dict(guard=name, source=filename, old=old, new=new,
                            command='TMPDIR=/var/tmp/ea2_astra_pytest ' + ' '.join(command),
                            summary=summaries[-1], log='red_' + name + '.log'))
        print(name, summaries[-1], flush=True)
    (HERE / 'red_proofs.json').write_text(json.dumps(results, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    main()
