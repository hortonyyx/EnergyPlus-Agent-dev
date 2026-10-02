"""Build runtime state references from saved BIM artifacts, without changing tools."""

from __future__ import annotations

import json
from pathlib import Path

from src.agent_runtime.context import StateEntry
from src.harness_contracts import SourceRef


def update_building_context(engine, event, raw_result):
    """Index actual saved values; claims remain interpretations, never verified facts.

    Full dimensions, IDs, and geometry live in hash-addressed original artifacts.
    Current state keeps their references rather than regenerating geometry in text.
    """
    run = Path(engine.tools.run_directory).resolve()
    context, store = engine.context, engine.store

    def save(key, category, value, status, source):
        sources = source if isinstance(source, tuple) else (source,)
        old = next((s for s in context.state if s.key == key), None)
        if old and (old.value, old.epistemic_status, old.source_refs) == (value, status, sources):
            return
        context.set_state(StateEntry(key=key, category=category, value=value,
            epistemic_status=status, source_refs=sources, revision=old.revision + 1 if old else 1))

    def source_for(path):
        path = path.resolve()
        if not path.is_relative_to(run):
            raise ValueError("context artifact escapes run directory")
        ref = store.put_bytes(path.read_bytes(), "application/json")
        return SourceRef(source_id=str(path.relative_to(run)), source_kind="tool",
            locator=str(path.relative_to(run)), blob=ref)

    metadata = raw_result.get("structuredContent")
    if not isinstance(metadata, dict):
        metadata = {}
        for block in raw_result.get("content", []):
            if block.get("type") == "text":
                try:
                    value = json.loads(block["text"])
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict):
                    metadata.update(value)
    event_source = engine._event_source(event)
    if metadata.get("view_id"):
        save("view:" + metadata["view_id"], "evidence_reference", {
            k: metadata[k] for k in ("view_id", "image_sha256", "box_original_pixels",
                "original_pixels_per_returned_pixel") if k in metadata}, "observed", event_source)
    for folder, pattern, status in (("claims", "claim_*.json", "inferred"),
                                    ("inferences", "inference_*.json", "inferred")):
        for path in sorted((run / folder).glob(pattern)):
            source = source_for(path)
            value = json.loads(path.read_bytes())
            save(folder + ":" + path.stem, "evidence_reference",
                {"id": path.stem, "record": source.blob.model_dump(mode="json"),
                 "interpretation_status": "model interpretation; not independently verified"}, status, source)
            claim = value.get("claim", value.get("declaration", value))
            for field in ("unresolved", "uncertain"):
                if isinstance(claim, dict) and claim.get(field):
                    save(path.stem + ":" + field, "unresolved", claim[field], "unresolved", source)
    reviews = sorted((run / "work_reviews").glob("review_*.json"))
    if reviews:
        review_source = source_for(reviews[-1])
        review = json.loads(reviews[-1].read_bytes())
        save("current-work-review", "todo", {"record": review,
            "basis": "latest explicitly saved model review; planned action is not proof of completion"},
            "inferred", review_source)
    candidates = sorted(p for p in run.glob("candidate_*/source_model.json") if p.is_file())
    old = next((s for s in context.state if s.key == "current-source-bim"), None)
    selected = old.value["candidate"] if old else None
    changed_bim = event.payload.tool_name in {"build_bim", "build_plan_bim", "assemble_plan_bim",
        "build_parametric_bim", "revise_bim", "revise_plan_bim", "finish_bim"}
    if changed_bim and not raw_result.get("isError"):
        selected = metadata.get("candidate") or selected
    path = run / str(selected) / "source_model.json" if selected else None
    if path is None or not path.is_file():
        path = candidates[-1] if candidates else run / "seed/source_model.json"
        if not path.is_file():
            path = None
    selection_path = run / "delivery_selection.json"
    if selection_path.is_file():
        selection_source = source_for(selection_path)
        save("selected-source-bim", "artifact_version", json.loads(selection_path.read_bytes()),
            "computed", selection_source)
    if path:
        source = source_for(path)
        saved = json.loads(path.read_bytes())
        save("current-source-bim", "artifact_version", {
            "candidate": path.parent.name, "file": source.blob.model_dump(mode="json"),
            "source_model_sha256": saved.get("source_model_sha256"),
            "source_geometry_sha256": saved.get("source_geometry_sha256")}, "computed", source)
        save("source-bim-geometry", "geometry", {"file": source.blob.model_dump(mode="json"),
            "fields": ["spaces", "boundaries", "openings", "connections"]}, "computed", source)
        save("source-bim-objects", "object_id", {name: [o.get("id") for o in saved.get(name, [])]
            for name in ("spaces", "boundaries", "openings")}, "computed", source)
        save("source-bim-dimensions", "dimension", {"file": source.blob.model_dump(mode="json"),
            "fields": ["spaces", "boundaries", "openings"],
            "basis": "saved values; geometric consistency does not establish observation accuracy"}, "computed", source)
        save("source-bim-assumptions", "general", saved.get("assumptions", []), "assumed", source)
        unresolved = {name: saved.get(name, []) for name in ("conflicts", "unbuilt_openings", "unsupported")}
        unresolved_sources = (source,)
        report_path = path.parent / "report.json"
        if report_path.is_file():
            report_source = source_for(report_path)
            unresolved_sources += (report_source,)
            report = json.loads(report_path.read_bytes())
            unresolved["report_unresolved"] = report.get("unresolved", [])
        else:
            unresolved["report_status"] = "not available"
        save("source-bim-unresolved", "unresolved", unresolved, "unresolved", unresolved_sources)
        save("source-bim-todo", "todo", {"unresolved": unresolved,
            "status": "open items from saved artifacts; empty does not certify whole-case quality"}, "unresolved", unresolved_sources)
