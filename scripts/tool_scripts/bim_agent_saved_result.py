"""One saved-BIM result contract, including reads of pre-contract run archives.

``saved_candidate`` is the final usable source, never a failed attempt or the
transaction's starting candidate. Effects distinguish durable audit writes from
geometry application and retain every committed candidate of a partial batch.
"""
from __future__ import annotations

import json
from pathlib import Path


SAVE_TOOLS = frozenset({"build_bim", "build_plan_bim", "assemble_plan_bim",
    "build_parametric_bim", "revise_bim", "revise_plan_bim", "finish_bim", "claim_transaction"})


def saved_result(result, *, candidate=None, created=(), geometry_applied=False, audit_written=False):
    result["saved_candidate"] = candidate
    result["save_effects"] = dict(created_candidates=list(created),
        geometry_applied=bool(geometry_applied), audit_written=bool(audit_written))
    return result


def _geometry(source):
    """Physical objects only; source roles, notes and provenance are not geometry."""
    fields = {
        "floors": ("id", "footprint", "z_floor", "height", "spanning_space_ids"),
        "spaces": ("id", "floor_id", "polygon", "z_floor", "height", "ceiling_height"),
        "boundaries": ("id", "space_id", "kind", "geometry_type", "vertices", "adjacent_space_ids", "counterpart_ids"),
        "openings": ("id", "kind", "vertices", "space_ids", "host_boundary_id", "exterior", "connectivity"),
        "connections": ("kind", "opening_id", "space_ids", "exterior", "state"),
    }
    result = {collection: sorted((tuple(json.dumps(row.get(k), sort_keys=True) for k in keys)
            for row in source.get(collection, []))) for collection, keys in fields.items()}
    result["opening_hosts"] = source.get("opening_hosts", {})
    result["coordinate_system"] = {k: source.get("coordinate_system", {}).get(k)
                                   for k in ("units", "up_axis", "north_axis")}
    return result


def saved_source_result(run, result, *, parent=None, selection=False):
    candidate = result.get("candidate")
    path = Path(run) / str(candidate) / "source_model.json"
    if not candidate or result.get("source_geometry_ready") is False or not path.is_file():
        return saved_result(result, audit_written=True)
    applied = not selection
    if parent:
        before = Path(run) / parent / "source_model.json"
        if before.is_file():
            applied = _geometry(json.loads(before.read_bytes())) != _geometry(json.loads(path.read_bytes()))
    return saved_result(result, candidate=candidate, created=[] if selection else [candidate],
                        geometry_applied=applied, audit_written=True)


def result_metadata(raw):
    structured = raw.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    content = raw.get("content", [])
    if not isinstance(content, list):
        return {}
    for block in reversed(content):
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        try:
            value = json.loads(block.get("text", ""))
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict):
            return value
    return {}


def read_saved_result(data, *, tool=None, run=None):
    """Read live results directly; one conservative adapter for older archives.

    No consumer maintains its own saving-tool list. Inspection results cannot
    select a candidate merely because they mention one. Failed later entries do
    not discard earlier commits. Legacy geometry application requires evidence.
    """
    if "saved_candidate" in data:
        return saved_result({}, candidate=data["saved_candidate"],
            created=data.get("save_effects", {}).get("created_candidates", []),
            geometry_applied=data.get("save_effects", {}).get("geometry_applied", False),
            audit_written=data.get("save_effects", {}).get("audit_written", False))
    empty = saved_result({})
    if tool not in SAVE_TOOLS:
        return empty
    if tool == "claim_transaction":
        entries = [row for row in data.get("entries", [])
                   if row.get("status") == "applied" and row.get("result_candidate")]
        committed = [row["result_candidate"] for row in entries]
        applied, parent = False, data.get("candidate")
        for row in entries:
            effects = row.get("save_effects")
            if effects is not None:
                applied |= effects.get("geometry_applied", False)
            elif run is not None and parent:
                root = Path(run).resolve()
                paths = [(root / str(c) / "source_model.json").resolve()
                         for c in (parent, row["result_candidate"])]
                if all(p.is_relative_to(root) and p.is_file() for p in paths):
                    applied |= _geometry(json.loads(paths[0].read_bytes())) != _geometry(json.loads(paths[1].read_bytes()))
            parent = row["result_candidate"]
        return saved_result({}, candidate=committed[-1] if committed else None,
            created=committed, geometry_applied=applied, audit_written=bool(data.get("audit_file")))
    candidate = data.get("candidate")
    if not isinstance(candidate, str) or data.get("error") or data.get("status") in {"failed", "error"}:
        return empty
    ready = data.get("source_geometry_ready")
    if ready is None and run is not None:
        root = Path(run).resolve()
        folder = (root / candidate).resolve()
        if folder.parent == root:
            report = folder / "report.json"
            if report.is_file():
                ready = json.loads(report.read_bytes()).get("source_geometry_ready")
            if ready is None and (folder / "source_model.json").is_file():
                ready = True
    if ready is not True:
        # Old returns sometimes named only the attempt; its persisted report
        # still decides domain failure, even when no usable source was saved.
        empty["source_geometry_ready"] = ready
        return empty
    app = data.get("claim_application", {})
    applied = (app.get("status") == "applied" and
        app.get("geometry_before_sha256") != app.get("geometry_after_sha256"))
    if not app and tool not in {"revise_bim", "finish_bim"}:
        applied = True
    return saved_result({}, candidate=candidate, created=[] if tool == "finish_bim" else [candidate],
        geometry_applied=applied, audit_written=True)
