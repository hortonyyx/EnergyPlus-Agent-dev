"""One deterministic, resumable assembly from immutable reader deliveries."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath

from src.agent_runtime.store import json_bytes

from .height_writes import apply_heights, saved_application
from .levels import LEVEL_TOLERANCE_M, decision, resolve_levels
from .lineage import candidate_readers, latest_candidate, metadata


def _hash(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def select_deliveries(session, task_ids=None):
    registry = session.registry
    eligible = {key: row for key, row in registry.records.items()
                if row["status"] == "completed" and row.get("artifact")
                and (row.get("validation") or {}).get("validation_passed")}
    replaced = set()
    for key in eligible:
        previous, seen = registry.task(key).get("previous_task_id"), set()
        while previous and previous not in seen:
            replaced.add(previous)
            seen.add(previous)
            previous = registry.task(previous).get("previous_task_id")
    if task_ids is not None:
        if not task_ids or len(task_ids) != len(set(task_ids)):
            raise ValueError("task_ids must be a nonempty list of distinct delivered task IDs")
        if set(task_ids) - set(eligible) or set(task_ids) & replaced:
            raise ValueError("select current validated deliveries; failed, missing and replaced tasks cannot be assembled")
        keys = task_ids
    else:
        keys = sorted(set(eligible) - replaced)
    selected = {}
    for key in keys:
        artifact = registry.read(key)
        role = eligible[key]["role_id"]
        target = artifact["plan"]["floor_id"] if role == "plan_reader" else artifact["orientation"]
        identity = role, target
        path = registry.child(key).task_directory / "reader_record.json"
        row = eligible[key]
        rank = (row.get("delivered_at_ns") or path.stat().st_mtime_ns, key)
        if identity in selected and task_ids is not None:
            raise ValueError("choose one plan per floor and one elevation per facade")
        if identity not in selected or rank > selected[identity][0]:
            selected[identity] = rank, key, artifact
    plans, elevations, references = {}, {}, []
    for (role, target), (_, key, artifact) in sorted(selected.items()):
        references.append({"task_id": key, "role_id": role, "target": target,
                           "sha256": eligible[key]["artifact"]["sha256"]})
        if role == "plan_reader":
            plans[target] = (key, artifact)
        else:
            elevations[key] = artifact
    if not plans:
        raise ValueError("no validated plan delivery; dispatch a plan reader first")
    return plans, elevations, references


def _issues_from_match(value):
    result, issues = value["result"], []
    for kind in ("elevation_only", "source_only", "conflicts"):
        for item in result[kind]:
            issues.append(decision(kind, "The elevation and plan do not yet establish a safe height match.",
                "Inspect both original views and the listed IDs; re-dispatch the affected reader with specific rework_targets, or correct the current candidate and reassemble.",
                task_id=value["task_id"], orientation=result["orientation"], detail=item))
    return issues


def _review_issues(review):
    if not review or review["status"] != "needs_review":
        return []
    return [decision("assembly_change", "Assembly differs from the accepted reader trial.",
            "Inspect this change; call review_role_assembly with a reason for every change before further writes.",
            review_id=review["review_id"], detail=row) for row in review["changes"]]


def _descends(session, candidate, ancestor):
    # Local plan revisions trace parent_draft_id instead of parent_candidate.
    # The verified reader lineage also covers those ordinary editing tools.
    readers = candidate_readers(session, ancestor)
    if readers and candidate_readers(session, candidate) == readers:
        return True
    seen = set()
    while candidate and candidate not in seen:
        if candidate == ancestor:
            return True
        seen.add(candidate)
        report = json.loads((session.run_directory / candidate / "report.json").read_bytes())
        candidate = (report.get("provenance") or {}).get("parent_candidate")
    return False


async def assemble_from_readers(session, *, task_ids=None, level_overrides=()):
    """Caller holds the write lock. Every mutation has a durable _once receipt."""
    plans, elevations, references = select_deliveries(session, task_ids)
    resolutions, issues = resolve_levels(session.registry,
        {floor: artifact["plan"] for floor, (_, artifact) in plans.items()}, elevations, level_overrides)
    inputs = {"deliveries": references, "levels": resolutions}
    identity = _hash(inputs)
    path = "role_assemblies/" + identity + ".json"
    saved_path = session.store.directory / path
    state = json.loads(saved_path.read_bytes()) if saved_path.is_file() else {"inputs": inputs}
    if state["inputs"] != inputs:
        raise ValueError("assembly input receipt changed")

    for ref in references:
        artifact = session.registry.read(ref["task_id"], sha256=ref["sha256"])
        for item in artifact.get("unresolved", []):
            issues.append(decision("reader_unresolved", item,
                "Inspect this reader's original image and decide whether a specific rework task is needed.", task_id=ref["task_id"]))
    for facade in sorted({"North", "South", "East", "West"} - {v["orientation"] for v in elevations.values()}):
        issues.append(decision("missing_elevation", "No selected delivery for this facade; its heights remain provisional.",
            "Dispatch an elevation reader if this original view is available; otherwise retain an explicit height assumption.", orientation=facade))

    def save():
        session.store.write_json(path, state)

    def finish(candidate, *, review=None, matches=(), write=None, status=None):
        from .session import envelope
        pending = [*issues, *_review_issues(review)]
        response = {"status": status or ("needs_decisions" if pending else "completed"),
            "candidate": candidate, "source_geometry_ready": candidate is not None,
            "assembly_id": identity, "deliveries": references, "levels": resolutions,
            "level_tolerance_m": LEVEL_TOLERANCE_M,
            "facades": [{"task_id": v["task_id"], "orientation": v["result"]["orientation"],
                "matched": len(v["result"]["matches"]), "source_only": len(v["result"]["source_only"]),
                "elevation_only": len(v["result"]["elevation_only"]), "conflicts": len(v["result"]["conflicts"])} for v in matches],
            "height_write": write, "assembly_review": None if not review else {
                key: review[key] for key in ("review_id", "status", "checked_floors", "changes")},
            "decisions": pending,
            "saved_candidates": len(list(session.run_directory.glob("candidate_*/report.json")))}
        state["response"] = response
        state["complete"] = status != "assembly_review_required" and candidate is not None
        state["candidate"] = candidate
        if candidate:
            state["source_sha256"] = hashlib.sha256(
                (session.run_directory / candidate / "source_model.json").read_bytes()).hexdigest()
        save()
        return envelope(response)

    candidate = state.get("candidate")
    if state.get("complete"):
        session._source(candidate)
        if hashlib.sha256((session.run_directory / candidate / "source_model.json").read_bytes()).hexdigest() != state["source_sha256"]:
            raise ValueError("completed assembly source changed; saved candidates are immutable")
        latest = latest_candidate(session, candidate)
        if latest == candidate or not _descends(session, latest, candidate):
            from .session import envelope
            return envelope(state["response"])
        # A deliberate candidate-only revision is the new base. Never rebuild
        # unchanged reader plans over the coordinator's local correction.
        state.update(candidate=latest, complete=False, local_revision=True)
        state.pop("height_result", None)
        candidate = latest
    save()
    current = session.assembly.current()
    if current and current["status"] == "needs_review":
        return finish(current["candidate"], review=current, status="assembly_review_required")

    if not state.get("local_revision"):
        builds = []
        for floor in resolutions:
            task_id, _ = plans[floor]
            ref = session.registry.records[task_id]["artifact"]
            result = await session._build_from_artifact(task_id, ref["sha256"], resolved_levels=resolutions[floor])
            meta = metadata(result)
            if not meta.get("source_geometry_ready") or not meta.get("candidate"):
                issues.append(decision("build_failed", "The selected floor could not compile safely.",
                    "Inspect the saved draft/error and re-dispatch this plan reader with the specific defect.",
                    task_id=task_id, floor_id=floor, detail=meta))
                return finish(None, status="build_failed")
            builds.append((floor, meta))
            review = session.assembly.current()
            if review and review["status"] == "needs_review":
                return finish(meta["candidate"], review=review, status="assembly_review_required")
        candidate = builds[0][1]["candidate"]
        if len(builds) > 1:
            floors = []
            for floor, meta in builds:
                bound = meta["plan_input"]
                floors.append({"draft_id": PurePosixPath(bound["plan_file"]).parent.name, "expected_plan_sha256": bound["plan_sha256"],
                    "floor_id": floor, "z_floor": resolutions[floor]["z_floor"]["value_m"],
                    "evidence": json.dumps(resolutions[floor], ensure_ascii=False, sort_keys=True)})
            result = await session._once("assembly:" + _hash(floors), "assemble_plan_bim",
                {"floors_json": json.dumps(floors, ensure_ascii=False)}, reference={"floors": floors})
            meta = metadata(result)
            if not meta.get("source_geometry_ready") or not meta.get("candidate"):
                issues.append(decision("assembly_failed", "Floor assembly did not produce safe geometry.",
                    "Inspect the assembly error and correct the affected floor delivery.", detail=meta))
                return finish(None, status="build_failed")
            candidate = meta["candidate"]
        state["candidate"] = candidate
        save()

    review = session.assembly.check(candidate, require_all=True)
    if review and review["status"] == "needs_review":
        return finish(candidate, review=review, status="assembly_review_required")
    matches = [session.match(task_id, candidate, height_bounds=True) for task_id in sorted(elevations)]
    for value in matches:
        issues.extend(_issues_from_match(value))
    ids = sorted(value["match_id"] for value in matches if value["result"]["can_apply"])
    write = None
    if ids:
        # If killed after a height receipt but before the outer workflow receipt,
        # recover it verbatim. Do not even perform a second evidence confirmation.
        receipt = saved_application(session, ids)
        result = receipt["result"] if receipt is not None else await apply_heights(session, ids, candidate=candidate)
        meta = metadata(result)
        write = {"status": meta.get("status"), "matched_openings": sum(len(v["result"]["matches"]) for v in matches)}
        if meta.get("status") == "completed":
            candidate = (meta.get("claim_application") or {}).get("candidate") or meta.get("candidate", candidate)
        else:
            issues.append(decision("height_write_failed", "The safe height batch was not accepted; the base candidate is retained.",
                "Inspect the height transaction result before making a bounded correction.", detail=meta))
        state["height_result"] = meta
    review = session.assembly.check(candidate, require_all=True)
    return finish(candidate, review=review, matches=matches, write=write)
