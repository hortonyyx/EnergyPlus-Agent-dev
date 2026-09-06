"""E-a pre-construction measurement attempt; no provider and no source edits.

This is a diagnostic runner, not production wiring or a test that pins a defect.
The pixel responses below are explicitly fixed controls, not image judgments.
An unavailable pairing readout is JSON null, never an invented zero.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent import pipeline
from src.agent.correction.evidence_adapters import (
    adapt_as_drawn_elevation, adapt_as_drawn_plan,
)
from src.agent.correction.opening_adjudication import _elevation_document
from src.agent.correction.tick_claim import (
    TickChoice, TickResponse, TickSession, freeze_prototype_supplement,
)
from src.agent.reading.vector_contract import classify_vector_json

BASE = ROOT / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype"


def emit(event, **values):
    print(json.dumps(dict(event=event, **values), ensure_ascii=False, sort_keys=True))


def capture(call):
    try:
        result = call()
        return result, {"status": "accepted"}
    except Exception as exc:
        return None, dict(status="refused", error_type=type(exc).__name__,
                          code=getattr(exc, "code", None), message=str(exc))


def main():
    paths = [BASE / f"out/sm25_{floor}_{version}.json"
             for floor in ("1f", "2f") for version in ("as_drawn", "v2")]
    paths += [BASE / f"out/sm25_{face}_as_drawn.json"
              for face in ("south", "east", "north", "west")]
    paths += [BASE / f"tools/cfg_{face}.json"
              for face in ("south", "east", "north", "west")]
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in paths}
    emit("source_inventory", sha256=before)
    emit("imports", pipeline=pipeline.__file__,
         tick_claim=sys.modules[TickSession.__module__].__file__)
    with tempfile.TemporaryDirectory(prefix="ea_contract_probe_") as tmp:
        for floor in ("1f", "2f"):
            universes = {}
            for version in ("as_drawn", "v2"):
                filename = f"sm25_{floor}_{version}.json"
                raw = (BASE / "out" / filename).read_bytes()
                doc = json.loads(raw)
                decision = classify_vector_json(doc)
                artifact, adapter = capture(lambda: adapt_as_drawn_plan(
                    raw, input_id=Path(filename).stem, floor_ref=floor))
                # For the live production product, identity is extracted from
                # the bundle, never reconstructed from a label or a filename.
                meta = artifact.bundle.source_artifacts[0] if artifact else None
                session, tick = capture(lambda: TickSession(
                    raw, image_id=meta.input_id if meta else Path(filename).stem))
                if artifact:
                    universes[version] = [c.opening_id for c in artifact.bundle.opening_claims]
                    adapter["source"] = meta.model_dump()
                if session:
                    universes[version] = [e.edge_id[:-3] for e in session.packet.edges
                                          if e.edge_id.endswith(":lo")]
                    tick["edge_count"] = len(session.packet.edges)
                    tick["diagnostics"] = session.packet.diagnostics
                out = Path(tmp) / Path(filename).stem
                out.mkdir()
                # Execute the unmodified REAL pipeline entrance. Empty fixed
                # responses deliberately stop at unresolved decisions, without
                # a provider call. A v2 outcome is not called a finished product.
                outcome, route = capture(lambda: pipeline.run_correction_evidence_chain(
                    BASE / "out", filename, out_dir=out, floor_ref=floor,
                    profile="strict", fixed_responses=()))
                if outcome is not None:
                    route.update(success=outcome.success, exit_reason=outcome.exit_reason)
                route["profile"] = "strict"
                emit("plan_contract", file=filename, schema=doc["schema"],
                     classification=decision.contract_id,
                     disposition=decision.disposition.value,
                     adapter=adapter, tick=tick, pipeline_entry=route)
            emit("plan_scope_comparison", floor=floor,
                 v0_count=len(universes["as_drawn"]), v2_count=len(universes["v2"]),
                 common_ids=sorted(set(universes["as_drawn"]) & set(universes["v2"])),
                 v0_ids=universes["as_drawn"], v2_ids=universes["v2"])
        for family in ("South", "East", "North", "West"):
            face = family.lower()
            raw = (BASE / f"out/sm25_{face}_as_drawn.json").read_bytes()
            doc = json.loads(raw)
            artifact = adapt_as_drawn_elevation(
                raw, input_id=f"sm25_{face}_as_drawn", facade_ref=family)
            meta = artifact.bundle.source_artifacts[0]
            supplement = freeze_prototype_supplement(
                raw, (BASE / f"tools/cfg_{face}.json").read_bytes())
            session = TickSession(raw, image_id=meta.input_id, supplement=supplement)
            _, undecided = capture(lambda: session.consume("not-yet-decided"))
            batch = session.submit(TickResponse(
                packet_id=session.packet.packet_id,
                choices=tuple(TickChoice(edge_id=e.edge_id, action="pixel",
                                         reason="E-a fixed pixel control; not a visual judgment")
                              for e in session.packet.edges)))
            facts = session.consume(batch.batch_id)
            converted = _elevation_document(session, batch.batch_id)
            emit("facade_measurement_attempt", family=family, source=meta.model_dump(),
                 elevation_openings=len(doc["openings"]), pair_count=None,
                 measurement_status="BLOCKED_BEFORE_OPENING_REVIEW",
                 cause="PRODUCTION_PLAN_V2_REJECTED_BY_TICK_SESSION",
                 not_reviewed_openings=[o["id"] for o in doc["openings"]],
                 note="No pairing result exists; not_reviewed is not B4 unmatched.")
            emit("facade_fixed_pixel_control", family=family,
                 before_response=undecided, edges=len(session.packet.edges),
                 edges_with_candidates=sum(bool(e.candidates) for e in session.packet.edges),
                 tiers=dict(Counter(f.tier for f in facts)), batch_id=batch.batch_id,
                 first_opening_id=doc["openings"][0]["id"],
                 source_x_m=doc["openings"][0]["x_range_m"],
                 consumed_x_m=converted["openings"][0]["x_range_m"],
                 decision_source="fixed pixel control; not a model measurement")
    after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in paths}
    emit("source_immutability", unchanged=before == after, files=len(paths))
    if before != after:
        raise RuntimeError("Source files changed during the diagnostic")


if __name__ == "__main__":
    main()
