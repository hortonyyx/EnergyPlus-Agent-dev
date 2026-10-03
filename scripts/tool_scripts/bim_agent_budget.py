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
    saved, ready, mappings, unreadable = [], set(), {}, []
    for path in sorted(toolkit.run.glob("candidate_*/source_model.json")):
        report = path.with_name("report.json")
        try:
            if not report.is_file():
                continue
            report_data = _read(report)
            # A deadline can interrupt file writes. Never let a torn last save
            # prevent handing off an earlier complete candidate (sm25 hard stop).
            _read(path.with_name("proposal.json"))
            mapping = candidate_floor_images(toolkit.run, path.parent.name)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            unreadable.append(dict(candidate=path.parent.name, reason=str(error)))
            continue
        saved.append(path.parent.name)
        mappings[path.parent.name] = mapping
        if report_data.get("source_geometry_ready"):
            ready.add(path.parent.name)
    if (toolkit.run / "seed/source_model.json").is_file():
        try:
            _read(toolkit.run / "seed/proposal.json")
            mappings["seed"] = candidate_floor_images(toolkit.run, "seed")
            saved.insert(0, "seed")
            seed_report = toolkit.run / "seed/report.json"
            if seed_report.is_file() and _read(seed_report).get("source_geometry_ready"):
                ready.add("seed")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            unreadable.append(dict(candidate="seed", reason=str(error)))
    covered = set().union(*(set(mappings[name]) for name in ready)) if ready else set()
    complete = [name for name in saved if name in ready and expected and set(expected) <= set(mappings[name])]
    chosen_images = set(candidate_floor_images(toolkit.run, candidate)) if candidate else set()
    return dict(expected_floor_plan_images=expected,
        floor_scope_source=toolkit.manifest.get("floor_scope_source", "not_declared"),
        saved_draft_images=sorted(covered), missing_draft_images=sorted(set(expected) - covered),
        latest_saved_candidate=saved[-1] if saved else None,
        latest_complete_candidate=complete[-1] if complete else None,
        unreadable_saved_candidates=unreadable,
        candidate=candidate, candidate_floor_images=sorted(chosen_images),
        missing_candidate_images=sorted(set(expected) - chosen_images) if candidate else [],
        candidate_source_geometry_ready=candidate in ready if candidate else None,
        complete_building=(candidate in ready and set(expected) <= chosen_images if expected and candidate else None),
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
        # C2: the time tail must use the same bounded review rule as FINISHING.
        reminders.append("剩余不足15%，停止新范围探索；仅有界复核已列严重问题，来不及就交付并列未决。" if not toolkit.readonly else
                         "剩余不足15%，停止新范围探索，返回已有观察与未核项。")
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
