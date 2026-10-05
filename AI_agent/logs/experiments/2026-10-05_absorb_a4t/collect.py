"""Save exact collected IDs, so complete coverage can be checked across reruns."""
import importlib
import json
import os
from pathlib import Path

import pytest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
validation=importlib.import_module('AI_agent.logs.experiments.2026-10-05_absorb_a4t.validate')


class Capture:
    def pytest_collection_finish(self,session):
        selected,direct=validation.files()
        result=dict(model_requests=0,files=selected,direct_reference_files=direct,
            nodeids=[item.nodeid for item in session.items],source_sha256=validation.hashes(selected))
        (HERE/'validation/collection.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    work=ROOT/'.tmp_a4t/collection'
    work.mkdir(parents=True,exist_ok=True)
    os.environ['TMPDIR']=str(work)
    selected,_=validation.files()
    raise SystemExit(pytest.main(['--collect-only','-q','-n','2','-s',*selected,
        '--basetemp='+str(work/'pytest'),'-o','cache_dir='+str(work/'cache')],plugins=[Capture()]))
