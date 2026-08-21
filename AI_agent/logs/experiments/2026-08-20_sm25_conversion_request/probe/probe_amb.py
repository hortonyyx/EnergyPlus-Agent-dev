import sys, json
from pathlib import Path
REPO=Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0,str(REPO))
import src.agent.judge.reading_typed_score as rts
orig = rts._plan_opening_candidates
def spy(audit, *, boundaries, position_tolerance):
    out = orig(audit, boundaries=boundaries, position_tolerance=position_tolerance)
    print(f"  obs={audit.observation_id} src={audit.source_input_id} -> {len(out)} 候选 "
          f"{[getattr(c,'id',c) for c in out][:4]}")
    return out
rts._plan_opening_candidates = spy
A=REPO/"case_tests/e2e_tests/sm25-L_anchor/run_2026-08-21_c2_first_sonnet_T1/0_reading/attempts/001"
# 走真实判卷入口
import subprocess
print("=== 逐洞口候选数 ===")
sys.argv=["run_stage.py","flow","sm25-L_anchor","run_2026-08-21_c2_first_sonnet_T1","--from","0_reading","--to","0_reading","--judge","stop"]
(A/"score_vs_gt.json").unlink(missing_ok=True)
import importlib.util
spec=importlib.util.spec_from_file_location("rs", REPO/"scripts/tool_scripts/run_stage.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
try:
    m.main()
except SystemExit:
    pass
