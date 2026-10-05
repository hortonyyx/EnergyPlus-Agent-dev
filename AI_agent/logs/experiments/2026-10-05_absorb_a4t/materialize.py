"""Restore only the two specified sm25 runs into this worktree, hash checked."""
import importlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def main():
    helper=importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a3t.materialize')
    helper.WORK=ROOT/'.tmp_a4t/history'
    helper.WORK.mkdir(parents=True,exist_ok=True)
    rows=[]
    for folder,name,commit in (
        ('2026-10-04_node_regression_a1','sm25_runtime_anthropic','b88adef5'),
        ('2026-10-04_node_regression_c2','sm25_runtime_subscription','57879421')):
        manifest=HERE.parent/folder/'evidence'/f'{name}_manifest.json'
        rows.append(helper.archive(manifest,commit))
    (HERE/'evidence_sources.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':main()
