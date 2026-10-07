"""Scripted, real-MCP fixtures for the D1 role-division integration tests.

The responses deliberately replay accepted 10-01 artifacts.  They exercise the
runtime and tools; they are not evidence of autonomous model reading quality.
"""

from __future__ import annotations

import json
import hashlib
import runpy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from src.agent.runtime_roles.entry import parser
from src.agent.runtime_roles.readers import validate_plan_artifact
from src.agent.runtime_roles.trial import canonical_plan_sha256
from src.agent_runtime.adapter import ScriptedAdapter


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_d1"
VERIFY = runpy.run_path(str(EXPERIMENT / "verify_elevations.py"))
CASES = {
    "sm21": ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm21",
    "sm24": ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm24",
    "sm25": ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25",
}
ELEVATION_SUBMISSION_FIELDS = (
    "orientation",
    "view_direction",
    "x_calibration",
    "elevations",
    "openings",
    "counts",
    "unresolved",
)


def response(*calls, text=None):
    message = {"role": "assistant", "content": text}
    if calls:
        message["tool_calls"] = [
            {
                "id": identity,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)},
            }
            for identity, name, arguments in calls
        ]
    return {
        "id": "d1-scripted-response",
        "model": "scripted-model",
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if calls else "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
    }


def _plan_targets(plan):
    targets = {"plan.x_anchors", "plan.y_anchors", "plan.footprint_pixels"}
    for collection in ("partitions", "openings", "space_seeds"):
        targets.update(
            f"plan.{collection}:{row['id']}" for row in plan.get(collection, [])
        )
    return sorted(targets)


def _plan_artifact(plan_path: Path, image_path: Path):
    plan = json.loads(plan_path.read_bytes())
    with Image.open(image_path) as picture:
        width, height = picture.size
    artifact = {
        "plan": plan,
        "evidence": [
            {
                "item": item,
                "source": image_path.name,
                "bbox": [0, 0, width, height],
                "basis": "accepted 10-01 plan replay; full original retained",
            }
            for item in _plan_targets(plan)
        ],
        "unresolved": plan["unresolved"],
    }
    return validate_plan_artifact(artifact, image_name=image_path.name)


def plan_submission(artifact: dict[str, Any]) -> dict[str, Any]:
    """Tool arguments for the immutable successful trial represented by artifact."""
    evidence_box = artifact["evidence"][0]["bbox"]
    return {
        "trial_id": "latest",
        "wall_reference": {
            category: {
                "convention": "explicit_face", "dimension_basis": "explicit_face",
                "basis": "Accepted 10-01 replay retains declared reference lines and their dimension anchors.",
                "bbox": evidence_box,
            } for category in ("perimeter", "partitions")
        },
        # The accepted sm21/sm24/sm25 plans replay with zero scoped topology
        # warnings. A new warning must fail submission rather than be auto-kept.
        "topology_decisions": [],
    }


def elevation_submission(artifact: dict[str, Any]) -> dict[str, Any]:
    """Strip runtime-owned metadata before calling submit_elevation_reading."""
    return {key: artifact[key] for key in ELEVATION_SUBMISSION_FIELDS}


def _selected_source(case_root: Path):
    selected = json.loads((case_root / "delivery_selection.json").read_bytes())["candidate"]
    source = json.loads((case_root / selected / "source_model.json").read_bytes())
    return selected, source


def _elevation_artifacts(case_name: str, case_root: Path):
    _, source = _selected_source(case_root)
    references = VERIFY["claim_references"](case_root)
    result = {}
    for orientation in ("North", "South", "East", "West"):
        rows, _ = VERIFY["_source_rows"](source, orientation)
        if rows:
            artifact, _ = VERIFY["source_artifact"](
                case_name, case_root, source, orientation, references
            )
            result[orientation] = artifact
    return result


def _reader_tasks(case_name: str, plan_artifacts, elevation_artifacts):
    tasks = []
    for floor_id, artifact in plan_artifacts.items():
        image = "1f_view.png" if floor_id == "F1" else "2f_view.png"
        tasks.append(
            {
                "task_id": f"{case_name}_plan_{floor_id.lower()}",
                "role_id": "plan_reader",
                "image": image,
                "target": floor_id,
                "origin": "Common building southwest footprint corner; ground datum Z=0.",
            }
        )
    for orientation in elevation_artifacts:
        tasks.append(
            {
                "task_id": f"{case_name}_elev_{orientation.lower()}",
                "role_id": "elevation_reader",
                "image": f"{orientation}_view.png",
                "target": orientation,
                "origin": "Common building southwest footprint corner; ground datum Z=0.",
            }
        )
    return tasks


def _latest_candidate(run: Path) -> str:
    candidates = [
        path.name
        for path in run.glob("candidate_[0-9][0-9]")
        if (path / "source_model.json").is_file()
    ]
    if not candidates:
        raise AssertionError("script expected a saved candidate")
    return max(candidates, key=lambda name: int(name.removeprefix("candidate_")))


def reader_record(output: Path, task_id: str) -> dict[str, Any]:
    for path in (output / "tasks").glob("*/reader_record.json"):
        value = json.loads(path.read_bytes())
        if value.get("task_id") == task_id:
            return value
    raise AssertionError(f"script expected a reader record for {task_id}")


def assembly_review(output: Path) -> dict[str, Any] | None:
    current = output / "role_assembly_current.json"
    if not current.is_file():
        return None
    review_id = json.loads(current.read_bytes())["review_id"]
    path = output / "role_assembly_reviews" / f"{review_id}.json"
    if not path.is_file():
        raise AssertionError(f"assembly review pointer has no report: {review_id}")
    return json.loads(path.read_bytes())


class CoordinatorAdapter:
    def __init__(self, *, store, stages: list[Callable[[], dict[str, Any]]]):
        self.store = store
        self.stages = stages
        self.offset = sum(
            event.payload.event_type == "adapter_request" for event in store.events
        )
        self.requests = []

    async def send(self, prepared, *, timeout):
        index = self.offset + len(self.requests)
        self.requests.append(prepared.wire_bytes)
        if index >= len(self.stages):
            raise AssertionError(f"unexpected coordinator request {index}")
        return self.stages[index]()


@dataclass
class D1Fixture:
    case_name: str
    output: Path
    args: Any
    tasks: list[dict[str, Any]]
    plan_artifacts: dict[str, dict[str, Any]]
    elevation_artifacts: dict[str, dict[str, Any]]
    adapters: list[Any]

    def adapter_factory(self, task_id, config, store):
        if task_id == "coordinator":
            adapter = CoordinatorAdapter(store=store, stages=self._coordinator_stages())
        else:
            floor = next(
                (
                    floor_id
                    for floor_id in self.plan_artifacts
                    if task_id == f"{self.case_name}_plan_{floor_id.lower()}"
                ),
                None,
            )
            if floor is not None:
                artifact = self.plan_artifacts[floor]
                submission = plan_submission(artifact)
                responses = [
                    response(
                        (
                            f"{task_id}-trial",
                            "trial_plan_bim",
                            {"plan": artifact["plan"]},
                        )
                    ),
                    response(
                        (
                            f"{task_id}-submit",
                            "submit_plan_reading",
                            submission,
                        )
                    ),
                    response(text="Plan reading submitted from the successful trial."),
                ]
            else:
                orientation = next(
                    orientation
                    for orientation in self.elevation_artifacts
                    if task_id == f"{self.case_name}_elev_{orientation.lower()}"
                )
                responses = [
                    response(
                        (
                            f"{task_id}-submit",
                            "submit_elevation_reading",
                            elevation_submission(self.elevation_artifacts[orientation]),
                        )
                    ),
                    response(text="Elevation reading submitted."),
                ]
            offset = sum(
                event.payload.event_type == "adapter_request" for event in store.events
            )
            adapter = ScriptedAdapter(responses[offset:])
        self.adapters.append(adapter)
        return adapter

    def _coordinator_stages(self):
        run = self.output / "bim"
        sequence: list[Callable[[], dict[str, Any]]] = [
            lambda: response(("coordinator-inputs", "inputs", {})),
            lambda: response(
                ("coordinator-delegate", "delegate_readers", {"tasks": self.tasks})
            ),
            lambda: response(("assemble-readers", "assemble_from_readers", {})),
        ]
        sequence.extend(
            [
                lambda: response(
                    (
                        "check-final-openings",
                        "check_openings",
                        {"candidate": _latest_candidate(run), "heights_only": True},
                    )
                ),
                lambda: response(
                    (
                        "inspect-final-candidate",
                        "inspect_candidate",
                        {"candidate": _latest_candidate(run), "include_geometry": False},
                    )
                ),
                lambda: response(
                    (
                        "finish-final-candidate",
                        "finish_bim",
                        {"candidate": _latest_candidate(run)},
                    )
                ),
                lambda: response(
                    text=(
                        "Offline scripted fixture completed the role pipeline. "
                        "This verifies orchestration and recovery, not model quality."
                    )
                ),
            ]
        )
        return sequence


def make_fixture(case_name: str, base: Path) -> D1Fixture:
    case_root = CASES[case_name]
    plan_paths = sorted((case_root / "plan_drafts").glob("draft_*/plan.json"))
    plan_artifacts = {}
    for path in plan_paths:
        plan = json.loads(path.read_bytes())
        image_name = "1f_view.png" if plan["floor_id"] == "F1" else "2f_view.png"
        plan_artifacts[plan["floor_id"]] = _plan_artifact(
            path, case_root / "images" / image_name
        )
    elevation_artifacts = _elevation_artifacts(case_name, case_root)
    tasks = _reader_tasks(case_name, plan_artifacts, elevation_artifacts)
    output = base / f"{case_name}-role-run"
    marker = base / f"{case_name}-script-marker.json"
    marker.write_text('{"offline_scripted_fixture":true}', encoding="utf-8", newline="\n")
    route = {
        name: {
            "provider": "scripted",
            "model": "scripted-model",
            "reasoning_effort": "medium",
            "output_tokens": 32768,
        }
        for name in ("coordinator", "plan_reader", "elevation_reader")
    }
    argv = [
        "--out",
        str(output),
        "--run-root",
        str(base),
        "--images",
        str(case_root / "images"),
        "--image-kind",
        "drawings",
        "--provider",
        "scripted",
        "--model",
        "scripted-model",
        "--reasoning-effort",
        "medium",
        "--script",
        str(marker),
        "--roles-json",
        json.dumps(route),
        "--scope",
        f"Offline D1 scripted replay for {case_name}; orchestration evidence only.",
        "--seconds",
        "1800",
        "--model-calls",
        "80",
        "--tool-calls",
        "180",
        "--tokens",
        "100000000",
        "--max-candidates",
        "24",
        "--max-concurrent-readers",
        "4",
    ]
    for floor_id in plan_artifacts:
        argv.extend(
            [
                "--floor-plan-image",
                "1f_view.png" if floor_id == "F1" else "2f_view.png",
            ]
        )
    args = parser().parse_args(argv)
    return D1Fixture(
        case_name=case_name,
        output=output,
        args=args,
        tasks=tasks,
        plan_artifacts=plan_artifacts,
        elevation_artifacts=elevation_artifacts,
        adapters=[],
    )


def event_counts(output: Path):
    rows = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    invocations = [row for row in rows if row["payload"]["event_type"] == "tool_invocation"]
    return CounterLike(
        model_requests=sum(row["payload"]["event_type"] == "adapter_request" for row in rows),
        tools=[row["payload"]["tool_name"] for row in invocations],
    )


@dataclass
class CounterLike:
    model_requests: int
    tools: list[str]
