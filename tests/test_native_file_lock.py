"""Real child-process contention and quota accounting on the host OS."""

import subprocess
import sys

from src.utils import file_lock


def test_busy_lock_is_rejected_and_can_be_reacquired_after_close(tmp_path):
    path = tmp_path / "writer.lock"
    child = """
import sys
from src.utils import file_lock
with open(sys.argv[1], 'a+b') as handle:
    try:
        file_lock.flock(handle, file_lock.LOCK_EX | file_lock.LOCK_NB)
    except BlockingIOError:
        print('busy')
    else:
        print('acquired')
"""
    with path.open("a+b") as handle:
        file_lock.flock(handle, file_lock.LOCK_EX)
        result = subprocess.run([sys.executable, "-c", child, str(path)],
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "busy"
    result = subprocess.run([sys.executable, "-c", child, str(path)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "acquired"


def test_concurrent_quota_attempts_never_exceed_the_limit(tmp_path):
    import json
    path = tmp_path / "quota.jsonl"
    child = """
import sys
from pathlib import Path
from src.agent_runtime.call_quota import QuotaAdapter
quota = QuotaAdapter(None, Path(sys.argv[1]), limit=7, category='offline-test')
for _ in range(7):
    try:
        quota._append({'event': 'attempt', 'model': 'fixture'})
    except ValueError as error:
        assert str(error) == 'batch request quota exhausted'
"""
    processes = [subprocess.Popen([sys.executable, "-c", child, str(path)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
    for process in processes:
        _, error = process.communicate(timeout=30)
        assert process.returncode == 0, error.decode(errors="replace")
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    assert [row["ticket"] for row in rows] == list(range(1, 8))
