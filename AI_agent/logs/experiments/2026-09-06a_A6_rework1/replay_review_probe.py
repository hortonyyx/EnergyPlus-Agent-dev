"""Replay the reviewer's exact probe, relocating only its two worktree paths."""
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.correction import tick_claim, opening_adjudication

original = Path(__file__).with_name('attack_probe_2_chain_reorder.original.py')
source = original.read_bytes()
print('PROBE_OBJECT 6ffb1429:AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/attack_probe_2_chain_reorder.py')
print('ORIGINAL_SHA256', hashlib.sha256(source).hexdigest())
print('IMPORT', tick_claim.__file__)
print('IMPORT', opening_adjudication.__file__)
assert source.count(b'/tmp/a6_review_claude') == 2
relocated = source.decode().replace('/tmp/a6_review_claude', str(ROOT))
print('ONLY_RELOCATION /tmp/a6_review_claude ->', ROOT, '(2 occurrences)')
exec(compile(relocated, str(original), 'exec'), {'__name__': '__main__'})
