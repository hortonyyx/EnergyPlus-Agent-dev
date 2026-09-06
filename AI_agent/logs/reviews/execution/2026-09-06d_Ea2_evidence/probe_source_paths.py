"""只读源文件；两条源契约绕行探针，不修改生产代码或历史产物。"""
from pathlib import Path
import copy
import json

from src.agent.correction.evidence_adapters import adapt_as_drawn_plan
from src.agent.correction.tick_claim import TickClaimError, TickSession, freeze
from src.agent.reading.vector_contract import classify_vector_json

ROOT = Path(__file__).resolve().parents[5]
source = ROOT / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_1f_v2.json"
doc = json.loads(source.read_bytes())

empty = copy.deepcopy(doc)
empty["hypotheses"]["pairs"] = []
empty["hypotheses"]["pairs_status"] = "SELECTED"
for bucket in ("unpaired_wall_faces", "solid_band_walls", "ambiguous_face_lines"):
    empty["hypotheses"][bucket] = {}
empty["hypotheses"]["non_wall_face_lines"] = {
    face["id"]: "probe: perception accounted for this face as non-wall"
    for face in empty["observations"]["face_lines"]
}
verdict = classify_vector_json(empty)
artifact = adapt_as_drawn_plan(freeze(empty), input_id="empty-selection-probe", floor_ref="1f")
print("EMPTY_SELECTED classifier:", verdict.contract_id, verdict.disposition.value)
print("EMPTY_SELECTED adapter wall_claims:", len(artifact.bundle.wall_claims))
try:
    TickSession(freeze(empty), image_id="empty-selection-probe")
except TickClaimError as exc:
    print("EMPTY_SELECTED current TickSession:", exc.code)

malformed = copy.deepcopy(doc)
del malformed["hypotheses"]
malformed["strokes"] = []
verdict = classify_vector_json(malformed)
print("MISSING_HYPOTHESES_WITH_LEGACY classifier:", verdict.contract_id, verdict.disposition)
print("MISSING_HYPOTHESES_WITH_LEGACY reason:", verdict.reason)
try:
    TickSession(freeze(malformed), image_id="missing-hypotheses-probe")
except TickClaimError as exc:
    print("MISSING_HYPOTHESES_WITH_LEGACY current TickSession:", exc.code)
