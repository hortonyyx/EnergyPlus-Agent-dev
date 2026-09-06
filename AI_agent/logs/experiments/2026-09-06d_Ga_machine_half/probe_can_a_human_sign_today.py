"""Independent probe: can a human sign the sm25 revisions worklist today?
Three attempts, each a thing a real signer would actually do."""
import json, pathlib, traceback
from src.agent.judge.gt_revisions import (
    RevisionsLedgerV1, derive_as_signed, AsSignedReproductionError)
from src.agent.judge.as_measured import AsMeasuredV1

FACTS = pathlib.Path("case_tests/test_baseline/gt_staging/sm25-L_anchor/facts")
am = AsMeasuredV1.model_validate(json.loads((FACTS/"as_measured.json").read_text()))
led = json.loads((FACTS/"revisions.json").read_text())

SIG = {"signed_by": "orchestrator-probe", "signed_at": "2026-09-06T17:30:00Z"}

def sign(ids):
    d = json.loads(json.dumps(led))
    for r in d["revisions"]:
        if r["id"] in ids:
            if r["candidate_action"] is None:
                raise SystemExit(f"{r['id']}: no candidate_action to promote")
            r["verdict"] = "drawing_error"
            r["action"] = r["candidate_action"]
            r["reason"] = "probe"
            r.update(SIG)
    return RevisionsLedgerV1.model_validate(d)

for label, ids in [("A: 只签 13AD（= committed 锁覆盖的那一半）", {"rev-13ad"}),
                   ("B: 13AD+13AE 一起签（人真正会做的动作）", {"rev-13ad","rev-13ae"}),
                   ("C: 三条全签（含 13AF）", {"rev-13ad","rev-13ae","rev-13af"})]:
    print("="*70); print(label)
    try:
        out = derive_as_signed(am, sign(ids))
        print("  ✅ 派生成功")
    except SystemExit as e:
        print("  ⛔ 连 ledger 都构不出:", e)
    except AsSignedReproductionError as e:
        print("  ⛔ AsSignedReproductionError:", str(e)[:300])
    except Exception as e:
        print(f"  ⛔ {type(e).__name__}:", str(e)[:300])
