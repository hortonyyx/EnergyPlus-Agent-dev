"""T1 time cap and saved floor coverage, derived only from files in one run.

Failure: GLM sm25 spent its 3000 seconds on one floor. No in-memory reminder
latches or assumed room counts: an explicit manifest floor/image scope, source
provenance and immutable successful saves drive reminders and timeout fallback.
"""
from __future__ import annotations

import json
from pathlib import Path
import time


def _read(path):
    return json.loads(path.read_text())


def candidate_floor_images(run, candidate, seen=None):
    seen = set() if seen is None else seen
    if candidate in seen:
        return {}
    seen.add(candidate)
    path = run / candidate / "source_model.json"
    if not path.is_file():
        return {}
    source = _read(path)
    floors = {row["id"] for row in source.get("floors", [])}
    provenance = source.get("generation", {}).get("provenance", {})
    mapping = {}
    if provenance.get("parent_candidate"):
        mapping.update(candidate_floor_images(run, provenance["parent_candidate"], seen))
    plan = provenance.get("plan_input", {})
    if plan.get("image"):
        floor = plan.get("geometry_feedback", {}).get("floor_id")
        if floor is None and len(floors) == 1:
            floor = next(iter(floors))
        mapping[plan["image"]] = [floor] if floor else []
    assembly = provenance.get("plan_assembly", {})
    if assembly.get("file"):
        assembly_path = (run / assembly["file"]).resolve()
        if assembly_path.is_relative_to(run.resolve()) and assembly_path.is_file():
            data = _read(assembly_path)
            for row in data.get("floors", []):
                mapping.setdefault(row["image"], []).append(row["floor_id"])
    return {image: sorted(set(ids) & floors) for image, ids in mapping.items() if set(ids) & floors}


def saved_floor_status(toolkit, candidate=None):
    expected = toolkit.manifest.get("floor_plan_images", [])
    saved = []
    for path in sorted(toolkit.run.glob("candidate_*/source_model.json")):
        report = path.with_name("report.json")
        if report.is_file() and _read(report).get("source_geometry_ready"):
            saved.append(path.parent.name)
    if (toolkit.run / "seed/source_model.json").is_file():
        saved.insert(0, "seed")
    mappings = {name: candidate_floor_images(toolkit.run, name) for name in saved}
    covered = set().union(*(set(value) for value in mappings.values())) if mappings else set()
    complete = [name for name in saved if expected and set(expected) <= set(mappings[name])]
    chosen_images = set(candidate_floor_images(toolkit.run, candidate)) if candidate else set()
    return dict(expected_floor_plan_images=expected,
        floor_scope_source=toolkit.manifest.get("floor_scope_source", "not_declared"),
        saved_draft_images=sorted(covered), missing_draft_images=sorted(set(expected) - covered),
        latest_saved_candidate=saved[-1] if saved else None,
        latest_complete_candidate=complete[-1] if complete else None,
        candidate=candidate, candidate_floor_images=sorted(chosen_images),
        missing_candidate_images=sorted(set(expected) - chosen_images) if candidate else [],
        complete_building=(set(expected) <= chosen_images if expected and candidate else None),
        note="Floor coverage only; rooms, openings and drawing fidelity are not certified. Unspecified floor scope remains unknown.")


def time_status(toolkit, *, now=None):
    manifest = toolkit.manifest
    start, deadline = manifest.get("started_epoch"), manifest.get("deadline_epoch")
    if start is None or deadline is None:
        return dict(active=False, line="已用／剩余分钟：未启用计时。", reminders=[])
    now = time.time() if now is None else now
    total = deadline - start
    elapsed, remaining = max(0, now - start), max(0, deadline - now)
    floor_status = saved_floor_status(toolkit)
    reminders = []
    if total > 0 and elapsed >= total * .5 and floor_status["missing_draft_images"] and not toolkit.readonly:
        reminders.append("时间已过半，尚无草稿的楼层图：" + ", ".join(floor_status["missing_draft_images"]) +
                         "。先按已读信息保存全楼草稿、再细化。")
    if total > 0 and remaining < total * .15:
        reminders.append("剩余不足15%，停止新的读图，只修已列出的问题并交付。" if not toolkit.readonly else
                         "剩余不足15%，停止新的读图，返回已有观察与未核项。")
    if remaining <= 0:
        reminders.append("时间上限已到，停止执行；交最近完整全楼稿，无完整稿则交最近保存稿并标明不完整。")
    return dict(active=True, elapsed_seconds=elapsed, remaining_seconds=remaining,
        line=f"已用 {elapsed / 60:.1f}／剩余 {remaining / 60:.1f} 分钟。" + " ".join(reminders),
        reminders=reminders, floors=floor_status)


def fallback_selection(toolkit):
    status = saved_floor_status(toolkit)
    full = status["latest_complete_candidate"]
    return (full or status["latest_saved_candidate"],
            "latest_complete_fallback_not_agent_selected" if full else "latest_saved_fallback_not_agent_selected")
