"""Compare assembly facts against accepted reader trials, with scoped review receipts."""

from __future__ import annotations

import hashlib
import json

from src.agent_runtime.store import json_bytes

from .lineage import candidate_readers, current_plan_deliveries


def _identity(value, floor):
    return value.removeprefix(floor + ":") if isinstance(value, str) else value


def _ring(points):
    rows = [tuple(round(float(v), 8) for v in point[:2]) for point in points]
    if rows and rows[-1] == rows[0]:
        rows.pop()
    return min(tuple(rows[i:] + rows[:i]) for i in range(len(rows))) if rows else ()


def floor_facts(source, floor):
    spaces = {row["id"]: row for row in source["spaces"] if row["floor_id"] == floor}
    rooms = {_identity(key, floor): _ring(row["polygon"]) for key, row in spaces.items()}
    openings = {}
    for row in source["openings"]:
        if not set(row.get("space_ids", [])) & set(spaces):
            continue
        openings[_identity(row["id"], floor)] = {"kind": row["kind"],
            "xy": sorted({tuple(round(float(v), 8) for v in point[:2]) for point in row["vertices"]}),
            "space_ids": sorted(_identity(key, floor) for key in row["space_ids"]),
            "exterior": row.get("exterior")}
    adjacent = sorted({tuple(sorted(_identity(key, floor) for key in row["space_ids"]))
                       for row in source.get("boundary_relations", [])
                       if len(row["space_ids"]) == 2 and set(row["space_ids"]) <= set(spaces)})
    return {"room_count": len(rooms), "opening_count": len(openings),
            "rooms": rooms, "openings": openings, "adjacency": adjacent}


def compare_floor(expected, actual, floor):
    before, after = floor_facts(expected, floor), floor_facts(actual, floor)
    changes = []
    for key in ("room_count", "opening_count", "adjacency"):
        if before[key] != after[key]:
            changes.append({"floor_id": floor, "item": key, "before": before[key], "after": after[key]})
    for key in ("rooms", "openings"):
        for identity in sorted(set(before[key]) | set(after[key])):
            if before[key].get(identity) != after[key].get(identity):
                changes.append({"floor_id": floor, "item": key + ":" + identity,
                                "before": before[key].get(identity), "after": after[key].get(identity)})
    for row in changes:
        row["change_id"] = hashlib.sha256(json_bytes(row)).hexdigest()[:20]
    return changes


class AssemblyReview:
    def __init__(self, session):
        self.session, self.store = session, session.store

    def _load(self, name, default):
        path = self.store.directory / name
        return json.loads(path.read_bytes()) if path.is_file() else default

    def bind(self, task_id):
        value = self.session.registry.read(task_id, role_id="plan_reader")
        record = self.session.registry.records[task_id]
        if not record.get("validation", {}).get("candidate_source_sha256"):
            raise ValueError("reader trial is missing its source hash")
        floors = self._load("role_floor_sources.json", {})
        floors[value["plan"]["floor_id"]] = {"task_id": task_id,
            "artifact_sha256": record["artifact"]["sha256"],
            "source_sha256": record["validation"]["candidate_source_sha256"]}
        self.store.write_json("role_floor_sources.json", floors)

    @staticmethod
    def _identified(row, field="change_id"):
        row[field] = hashlib.sha256(json_bytes(row)).hexdigest()[:20]
        return row

    def _delivery_coverage(self, candidate, actual_floors):
        current = current_plan_deliveries(self.session)
        used = candidate_readers(self.session, candidate)
        used_by_target = {}
        blockers = []
        for task_id in sorted(used):
            row = self.session.registry.records.get(task_id) or {}
            if row.get("role_id") != "plan_reader":
                continue
            target = row.get("target")
            used_by_target.setdefault(target, []).append(task_id)
            expected = current.get(target)
            if expected and task_id != expected["task_id"]:
                blockers.append(self._identified({
                    "item": "stale_plan_delivery",
                    "target": target,
                    "floor_id": expected["floor_id"],
                    "used_task_id": task_id,
                    "current_task_id": expected["task_id"],
                }, "blocker_id"))

        changes = []
        for target, expected in current.items():
            floor = expected["floor_id"]
            if floor not in actual_floors:
                changes.append(self._identified({
                    "floor_id": floor,
                    "item": "missing_required_floor",
                    "target": target,
                    "before": {
                        "task_id": expected["task_id"],
                        "artifact_sha256": expected["artifact_sha256"],
                    },
                    "after": None,
                }))
            elif not used_by_target.get(target):
                blockers.append(self._identified({
                    "item": "unverified_plan_lineage",
                    "target": target,
                    "floor_id": floor,
                    "current_task_id": expected["task_id"],
                    "used_task_ids": used_by_target.get(target, []),
                }, "blocker_id"))

        scope = [current[target] for target in sorted(current)]
        return scope, sorted(used), changes, blockers

    def check(self, candidate, *, require_all=False):
        bindings = self._load("role_floor_sources.json", {})
        if not bindings and not require_all:
            return None
        source = self.session._source(candidate)
        actual_floors = {row["floor_id"] for row in source["spaces"]}
        changes, checked, blockers = [], [], []
        for floor, binding in bindings.items():
            if floor not in actual_floors and not require_all:
                continue
            task_id = binding["task_id"]
            self.session.registry.read(task_id, sha256=binding["artifact_sha256"], role_id="plan_reader")
            receipt = self.session.registry.records[task_id]["validation"]
            workspace = self.session.registry.child(task_id).task_directory / "bim/trial_workspace"
            path = (workspace / receipt["candidate"] / "source_model.json").resolve()
            if not path.is_relative_to(workspace.resolve()) or not path.is_file():
                raise ValueError("accepted trial source is missing or outside its task")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != binding["source_sha256"]:
                raise ValueError("accepted trial source hash changed")
            changes.extend(compare_floor(json.loads(raw), source, floor))
            checked.append(floor)
        if require_all:
            for floor in sorted(actual_floors - set(bindings)):
                row = {"floor_id": floor, "item": "unexpected_floor", "before": None,
                       "after": floor_facts(source, floor)}
                changes.append({**row, "change_id": hashlib.sha256(json_bytes(row)).hexdigest()[:20]})
            delivery_scope, used_plan_tasks, missing, blockers = self._delivery_coverage(
                candidate, actual_floors
            )
            changes.extend(missing)
        else:
            delivery_scope, used_plan_tasks = [], []
        facts = {"candidate": candidate, "require_all": require_all, "source_sha256": hashlib.sha256(
            (self.session.run_directory / candidate / "source_model.json").read_bytes()).hexdigest(),
            "bindings": bindings, "checked_floors": checked, "changes": changes,
            "delivery_scope": delivery_scope, "used_plan_tasks": used_plan_tasks,
            "blockers": blockers}
        identity = hashlib.sha256(json_bytes(facts)).hexdigest()
        old = self._load("role_assembly_reviews/" + identity + ".json", {})
        status = "blocked" if blockers else ("needs_review" if changes else "unchanged")
        report = {**facts, "review_id": identity, "status": status}
        if not blockers and old.get("decisions") and self._valid_decisions(changes, old["decisions"]):
            report.update(status="reviewed", decisions=old["decisions"])
        self.store.write_json("role_assembly_reviews/" + identity + ".json", report)
        self.store.write_json("role_assembly_current.json", {"review_id": identity})
        return report

    def current(self):
        current = self._load("role_assembly_current.json", {})
        return self._load("role_assembly_reviews/" + current.get("review_id", "missing") + ".json", None)

    @staticmethod
    def _valid_decisions(changes, decisions):
        if not isinstance(decisions, list) or any(
                not isinstance(row, dict) or set(row) != {"change_id", "reason"}
                or not isinstance(row["reason"], str) or not row["reason"].strip() for row in decisions):
            return False
        expected = {row["change_id"] for row in changes}
        supplied = {row["change_id"] for row in decisions}
        return len(supplied) == len(decisions) and supplied == expected

    def guard(self):
        report = self.current()
        if report and report["status"] == "blocked":
            raise ValueError("assembly cannot be delivered because its plan lineage is stale or unverified: "
                             + json.dumps(report["blockers"], ensure_ascii=False, sort_keys=True))
        if report and report["status"] == "needs_review":
            raise ValueError("assembly changed accepted reader facts; inspect changes and call review_role_assembly "
                             "with a reason for each change before continuing: " + report["review_id"])

    def acknowledge(self, review_id, decisions):
        report = self.current()
        if not report or report["review_id"] != review_id:
            raise ValueError("review_id must refer to the current assembly comparison")
        if report.get("blockers"):
            raise ValueError("stale or unverified plan lineage cannot be accepted as partial delivery")
        refreshed = self.check(report["candidate"], require_all=report["require_all"])
        if refreshed["review_id"] != review_id:
            raise ValueError("assembly source or reader references changed; review the new comparison")
        if not self._valid_decisions(report["changes"], decisions):
            raise ValueError("provide exactly one nonempty reason for each assembly change_id")
        report.update(status="reviewed", decisions=decisions)
        self.store.write_json("role_assembly_reviews/" + review_id + ".json", report)
        return report


def finalize_role_building(engine, reason):
    """The timeout/stop fallback cannot silently deliver an unreviewed assembly."""
    from scripts.tool_scripts.bim_agent_budget import fallback_selection
    from scripts.tool_scripts.run_bim_agent import Toolkit
    from src.agent.runtime_delivery import finalize_runtime_building

    try:
        selection = engine.tools.run_directory / "delivery_selection.json"
        forced_fallback = reason.endswith(("time_budget_exhausted", "money_budget_exhausted")) or reason == "money_cny_usage_unavailable"
        if selection.is_file() and not forced_fallback:
            chosen = json.loads(selection.read_bytes())["candidate"]
        else:
            chosen, _ = fallback_selection(Toolkit(engine.tools.run_directory))
        if chosen:
            report = engine.tools.assembly.check(chosen, require_all=True)
            try:
                engine.tools.assembly.guard()
            except ValueError as error:
                if report and report["status"] == "needs_review":
                    return {"status": "assembly_review_required", "delivery": None,
                            "assembly_review": report}
                return {"status": "assembly_delivery_blocked", "delivery": None,
                        "assembly_review": report, "reason": str(error)}
    except (ValueError, OSError, KeyError) as error:
        return {"status": "assembly_review_failed", "delivery": None, "reason": str(error)}
    return finalize_runtime_building(engine, reason)
