"""Audit the complete stage-3 delivery archive without extracting it.

The report is structural evidence, not an answer-quality score.  It contains
only archive-relative identifiers, hashes, counts and explicit evidence
statuses; prompts, answers, image bytes and credentials are never emitted.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DEFAULT_ARCHIVE = HERE / "evidence_all.compact.tar.xz"
ROLE_MANIFEST = HERE / "role_cases/manifest.json"
CALIBRATION = HERE / "calibration"
REQUIRED_ROOTS = {
    "offline_demo": ".stage3-work/offline_delivery",
    "role_tests": ".stage3-work/roles",
    "offline_driver": ".stage3-work/offline_delivery_driver",
    "role_followup": ".stage3-work/roles_followup",
    "role_final": ".stage3-work/roles_final",
}
SCHEMA = "harness-stage3-delivery-verification/v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

sys.path.insert(0, str(ROOT))
from src.agent.contracts import (  # noqa: E402
    EvidencePackage,
    LocalizedEvidenceResult,
    assert_result_applicable,
)
from src.agent_runtime.adapter import decode_image_url  # noqa: E402
from src.agent_runtime.store import json_bytes  # noqa: E402
from src.harness_contracts import (  # noqa: E402
    AdapterRequestPayload,
    BudgetAmounts,
    BudgetLedger,
    EventEnvelope,
    EventLog,
    ExternalCoordinatorMcpPayload,
)
from src.harness_contracts.events import _resolve_json_pointer  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(data: bytes) -> Any:
    return json.loads(data)


def _safe_logical(path: str) -> str:
    logical = PurePosixPath(path)
    if not path or logical.is_absolute() or ".." in logical.parts or "\\" in path:
        raise ValueError("unsafe archive-relative path")
    return logical.as_posix()


def _safe_detail(error: BaseException) -> str:
    """Return a bounded diagnostic without echoing possibly private values."""

    known = {
        "JSONDecodeError": "invalid JSON",
        "UnicodeDecodeError": "invalid UTF-8",
        "KeyError": "required field is missing",
    }
    return known.get(type(error).__name__, type(error).__name__)


class FindingError(ValueError):
    def __init__(self, code: str, path: str, detail: str) -> None:
        super().__init__(detail)
        self.code, self.path, self.detail = code, path, detail


class Auditor:
    def __init__(self) -> None:
        self.findings: list[dict[str, str]] = []
        self.checks: list[dict[str, Any]] = []

    def finding(self, code: str, path: str, detail: str) -> None:
        self.findings.append({"code": code, "path": path, "detail": detail})

    def require(self, condition: bool, code: str, path: str, detail: str) -> None:
        if not condition:
            raise FindingError(code, path, detail)

    def check(self, name: str, function) -> Any:
        before = len(self.findings)
        value: Any = None
        try:
            value = function()
        except FindingError as error:
            self.finding(error.code, error.path, error.detail)
        except Exception as error:  # a malformed artifact must become a report
            self.finding("check_exception", name, _safe_detail(error))
        row: dict[str, Any] = {
            "name": name,
            "status": "passed" if len(self.findings) == before else "failed",
        }
        if value is not None:
            try:
                json.dumps(value, allow_nan=False)
            except (TypeError, ValueError):
                pass
            else:
                row["evidence"] = value
        self.checks.append(row)
        return value


@dataclass(frozen=True)
class RunEvidence:
    base: str
    journal: dict[str, Any]
    raw_events: tuple[dict[str, Any], ...]
    events: tuple[EventEnvelope, ...]

    @property
    def run_id(self) -> str:
        return str(self.journal["run_id"])

    @property
    def root_task_id(self) -> str:
        return str(self.journal["task_id"])


class ArchiveView:
    """Resolve run-relative files from an already verified archive Mapping."""

    def __init__(self, files: Mapping[str, bytes]) -> None:
        self.files = files
        self.keys = set(files)

    def read(self, logical: str) -> bytes:
        path = _safe_logical(logical)
        try:
            return self.files[path]
        except KeyError as error:
            raise FindingError("missing_archive_file", path, "required file is absent") from error

    def json(self, logical: str) -> Any:
        try:
            return _json(self.read(logical))
        except json.JSONDecodeError as error:
            raise FindingError("invalid_json", logical, "file is not valid JSON") from error

    def blob(self, run_base: str, ref: Any) -> bytes:
        value = ref.model_dump(mode="json") if hasattr(ref, "model_dump") else ref
        if not isinstance(value, dict) or value.get("kind") != "sha256":
            raise FindingError("unverifiable_blob", run_base, "complete evidence needs a SHA-256 blob")
        digest, uri = value.get("sha256"), value.get("uri")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise FindingError("invalid_blob_hash", run_base, "blob SHA-256 is invalid")
        if not isinstance(uri, str) or PurePosixPath(uri).parts != ("blobs", digest):
            raise FindingError("invalid_blob_uri", run_base, "blob URI is not its content address")
        logical = f"{run_base}/{uri}"
        data = self.read(logical)
        if _sha256(data) != digest:
            raise FindingError("blob_hash_mismatch", logical, "blob bytes differ from their SHA-256")
        return data

    def capture(self, run_base: str, capture: Any) -> Any:
        if capture.kind == "inline":
            return capture.value
        if capture.kind == "blob":
            data = self.blob(run_base, capture.blob)
            try:
                return _json(data)
            except json.JSONDecodeError as error:
                raise FindingError(
                    "capture_not_json", run_base, "expected JSON capture is not valid JSON"
                ) from error
        raise FindingError("missing_complete_capture", run_base, "required capture is explicitly missing")


def _load_evidence_pack():
    path = HERE / "evidence_pack.py"
    spec = importlib.util.spec_from_file_location("stage3_evidence_pack", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load evidence archive reader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _parse_events(data: bytes, logical: str) -> tuple[tuple[dict[str, Any], ...], tuple[EventEnvelope, ...]]:
    if data and not data.endswith(b"\n"):
        raise FindingError("torn_event_log", logical, "event log lacks its final newline")
    raw: list[dict[str, Any]] = []
    typed: list[EventEnvelope] = []
    for line_number, line in enumerate(data.splitlines(), 1):
        try:
            value = json.loads(line)
            raw.append(value)
            typed.append(EventEnvelope.model_validate_json(line))
        except Exception as error:
            raise FindingError(
                "invalid_event", logical, f"event line {line_number} fails the event contract"
            ) from error
    return tuple(raw), tuple(typed)


def _load_runs(view: ArchiveView, auditor: Auditor) -> list[RunEvidence]:
    event_paths = sorted(path for path in view.keys if path.endswith("/events.jsonl"))
    auditor.require(bool(event_paths), "no_event_logs", "archive", "archive contains no events.jsonl")
    runs: list[RunEvidence] = []
    for logical in event_paths:
        base = logical.removesuffix("/events.jsonl")
        journal_path = f"{base}/journal.json"
        auditor.require(journal_path in view.keys, "missing_journal", logical, "event log has no journal")
        journal = view.json(journal_path)
        auditor.require(isinstance(journal, dict), "invalid_journal", journal_path, "journal is not an object")
        raw, events = _parse_events(view.read(logical), logical)
        runs.append(RunEvidence(base, journal, raw, events))
    return runs


def _validate_blob_inventory(view: ArchiveView) -> dict[str, int]:
    count, byte_count = 0, 0
    for logical in sorted(view.keys):
        parts = PurePosixPath(logical).parts
        if len(parts) < 3 or parts[-2] != "blobs":
            continue
        digest = parts[-1]
        if not SHA256_RE.fullmatch(digest):
            raise FindingError("invalid_blob_filename", logical, "blob filename is not a SHA-256")
        data = view.read(logical)
        if _sha256(data) != digest:
            raise FindingError("blob_hash_mismatch", logical, "blob filename differs from its bytes")
        count += 1
        byte_count += len(data)
    return {"blobs": count, "bytes": byte_count}


def _iter_sha_refs(value: Any):
    if isinstance(value, dict):
        if (
            value.get("kind") == "sha256"
            and isinstance(value.get("sha256"), str)
            and isinstance(value.get("uri"), str)
            and isinstance(value.get("media_type"), str)
        ):
            yield value
        for child in value.values():
            yield from _iter_sha_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_sha_refs(child)


def _validate_event_logs(view: ArchiveView, runs: list[RunEvidence]) -> dict[str, int]:
    run_ids = [run.run_id for run in runs]
    if len(run_ids) != len(set(run_ids)):
        raise FindingError(
            "duplicate_run_id", "archive", "event roots must keep globally unique run IDs"
        )
    event_count = blob_ref_count = 0
    for run in runs:
        budget = BudgetAmounts.model_validate_json(json.dumps(run.journal.get("budget_limit")))
        EventLog(mode="complete", events=run.events, budget_limit=budget)
        if run.journal.get("run_id") != run.events[0].run_id:
            raise FindingError("run_identity_mismatch", run.base, "journal and event run IDs differ")
        event_count += len(run.events)
        for raw in run.raw_events:
            for ref in _iter_sha_refs(raw):
                view.blob(run.base, ref)
                blob_ref_count += 1
    return {"runs": len(runs), "events": event_count, "blob_references": blob_ref_count}


def _validate_parentage(runs: list[RunEvidence]) -> dict[str, int]:
    task_count = child_count = reservation_count = settlement_count = 0
    for run in runs:
        parents: dict[str, str | None] = {}
        for event in run.events:
            parent = None if event.parent_task.kind == "root" else event.parent_task.task_id
            prior = parents.setdefault(event.task_id, parent)
            if prior != parent:
                raise FindingError("unstable_task_parent", run.base, "one task has multiple parents")
        root = run.root_task_id
        if parents.get(root, "absent") is not None:
            raise FindingError("invalid_root_task", run.base, "journal root task is not a root event task")
        roots = {task for task, parent in parents.items() if parent is None}
        if roots != {root}:
            raise FindingError("multiple_task_roots", run.base, "run must have exactly its journal root")
        for task, parent in parents.items():
            if parent is not None and parent not in parents:
                raise FindingError("missing_parent_task", run.base, "child refers to an absent parent task")
            seen: set[str] = set()
            current: str | None = task
            while current is not None:
                if current in seen:
                    raise FindingError("task_parent_cycle", run.base, "task ancestry contains a cycle")
                seen.add(current)
                current = parents.get(current)
        task_count += len(parents)
        child_count += len(parents) - 1
        reservations = [
            event.payload.reservation
            for event in run.events
            if event.payload.event_type == "budget" and event.payload.reservation is not None
        ]
        settlements = [
            event.payload.settlement
            for event in run.events
            if event.payload.event_type == "budget" and event.payload.settlement is not None
        ]
        BudgetLedger(
            total_limit=BudgetAmounts.model_validate_json(json.dumps(run.journal["budget_limit"])),
            reservations=tuple(reservations),
            settlements=tuple(settlements),
        )
        reservation_count += len(reservations)
        settlement_count += len(settlements)
    return {
        "tasks": task_count,
        "child_tasks": child_count,
        "root_ledger_reservations": reservation_count,
        "root_ledger_settlements": settlement_count,
    }


def _validate_wire_requests(view: ArchiveView, runs: list[RunEvidence]) -> dict[str, int]:
    requests = injections = images = 0
    for run in runs:
        for event in run.events:
            payload = event.payload
            if not isinstance(payload, AdapterRequestPayload):
                continue
            requests += 1
            body = view.capture(run.base, payload.final_request_body)
            if not isinstance(body, dict):
                raise FindingError("request_body_not_object", run.base, "final request is not a JSON object")
            final_blob = payload.final_request_body.blob
            wire = view.blob(run.base, final_blob)
            if json_bytes(body) != wire:
                raise FindingError("wire_bytes_mismatch", run.base, "request JSON differs from exact wire bytes")
            for injection in payload.injected_content:
                actual = _resolve_json_pointer(body, injection.request_location)
                expected = view.capture(run.base, injection.content)
                if actual != expected:
                    raise FindingError(
                        "injection_mismatch", run.base, "injected content differs from final request"
                    )
                if injection.source.blob is not None:
                    view.blob(run.base, injection.source.blob)
                injections += 1
            for image in payload.images:
                original = view.blob(run.base, image.original)
                sent = view.blob(run.base, image.sent)
                url = _resolve_json_pointer(body, image.request_reference)
                if not isinstance(url, str):
                    raise FindingError("image_wire_not_url", run.base, "wire image is not a data URL")
                wire_image, mime = decode_image_url(url)
                if wire_image != sent or _sha256(original) != image.original.sha256:
                    raise FindingError(
                        "image_wire_mismatch", run.base, "original/sent image identity differs from final wire"
                    )
                if image.sent.media_type != mime:
                    raise FindingError("image_media_mismatch", run.base, "wire and sent image media types differ")
                images += 1
    return {"adapter_requests": requests, "injections": injections, "images": images}


def _view_identity(view: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(view["reference"]["reference"]["value"]),
        str(view["original"]["sha256"]),
        str(view["sent"]["sha256"]),
    )


def _validate_child_packages(
    view: ArchiveView, runs: list[RunEvidence], manifest_cases: dict[str, dict[str, Any]]
) -> dict[str, int]:
    packages = results = budget_stops = boxes = 0
    for run in runs:
        task_dirs = sorted(
            PurePosixPath(path).parent.as_posix()
            for path in view.keys
            if path.startswith(run.base + "/tasks/") and path.endswith("/delegation.json")
        )
        event_by_task: dict[str, list[EventEnvelope]] = defaultdict(list)
        for event in run.events:
            event_by_task[event.task_id].append(event)
        for task_dir in task_dirs:
            delegation = view.json(f"{task_dir}/delegation.json")
            observation_path = f"{task_dir}/observation.json"
            if observation_path not in view.keys:
                raise FindingError("missing_observation", task_dir, "delegation has no saved observation")
            observation = view.json(observation_path)
            package = EvidencePackage.model_validate_json(json.dumps(delegation["package"]))
            packages += 1
            if observation.get("package") != delegation["package"]:
                raise FindingError("package_mismatch", task_dir, "delegation and observation packages differ")
            if observation.get("views") != delegation.get("views"):
                raise FindingError("view_delivery_mismatch", task_dir, "delegation and observation views differ")
            views = delegation.get("views")
            if not isinstance(views, list) or not views:
                raise FindingError("missing_delivered_views", task_dir, "child received no recorded views")
            if [row["reference"] for row in views] != delegation["package"]["image_refs"]:
                raise FindingError("package_view_mismatch", task_dir, "package image refs differ from delivered views")
            for row in views:
                view.blob(run.base, row["original"])
                view.blob(run.base, row["sent"])
                if row["reference"]["original_sha256"] != row["original"]["sha256"]:
                    raise FindingError("original_view_mismatch", task_dir, "view original hash differs from evidence ref")

            task_events = sorted(event_by_task.get(package.task_id, []), key=lambda item: item.sequence)
            request_events = [e for e in task_events if isinstance(e.payload, AdapterRequestPayload)]
            if request_events:
                first = request_events[0].payload
                if first.reservation_id != package.budget_reservation_id:
                    raise FindingError(
                        "first_reservation_mismatch", task_dir, "package does not bind the first request reservation"
                    )
                reservations = [
                    e.payload.reservation
                    for e in task_events
                    if e.payload.event_type == "budget" and e.payload.reservation is not None
                ]
                if not any(
                    item.reservation_id == package.budget_reservation_id
                    and item.purpose == "child_task"
                    and item.task_id == package.task_id
                    for item in reservations
                ):
                    raise FindingError(
                        "missing_child_reservation", task_dir, "first child request has no matching root reservation"
                    )
                delivered = Counter(_view_identity(row) for row in views)
                transmitted = Counter(
                    (package.image_refs[index].reference.value, image.original.sha256, image.sent.sha256)
                    for index, image in enumerate(first.images)
                ) if len(first.images) == len(package.image_refs) else Counter()
                if delivered != transmitted:
                    raise FindingError(
                        "transmitted_view_mismatch", task_dir, "child request images differ from delivered views"
                    )
            else:
                status = str(observation.get("status", "")) + " " + str(
                    observation.get("runtime", {}).get("status", "")
                )
                if "budget_exhausted" not in status:
                    raise FindingError(
                        "missing_child_request", task_dir, "no request exists and status is not a budget stop"
                    )
                budget_stops += 1

            limits = delegation["arguments"]["budget"]
            runtime = observation.get("runtime", {})
            if len(request_events) > limits["model_calls"] or runtime.get("tool_calls", 0) > limits["tool_calls"]:
                raise FindingError("child_quota_exceeded", task_dir, "child exceeded its delegated call limit")

            result_value = observation.get("result")
            if result_value is not None:
                result = LocalizedEvidenceResult.model_validate_json(json.dumps(result_value))
                assert_result_applicable(package, result, package.source_model_version_id)
                results += 1
                view_by_ref = {row["reference"]["reference"]["value"]: row for row in views}
                for seen in result.directly_seen:
                    ref = seen.location.image_ref.reference.value
                    row = view_by_ref[ref]
                    left, top, right, bottom = seen.location.box_original_pixels
                    width, height = row["original_size"]
                    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
                        raise FindingError(
                            "box_outside_original", task_dir, "localized box is outside original-image pixels"
                        )
                    crop = row["reference"]["coordinate_relation"].get("crop_original_pixels")
                    if crop is not None:
                        c_left, c_top, c_right, c_bottom = crop
                        if not (c_left <= left < right <= c_right and c_top <= top < bottom <= c_bottom):
                            raise FindingError(
                                "box_outside_crop", task_dir, "localized box is outside the delivered crop"
                            )
                    boxes += 1

            case = manifest_cases.get(package.task_id)
            if run.base.startswith(("role_tests/", "role_followup/", "role_final/")):
                if case is None or package.question != case["question"]:
                    raise FindingError("role_package_mismatch", task_dir, "role task differs from frozen case")
                declared = Counter(row["sha256"] for row in case["images"])
                observed = Counter(row["original"]["sha256"] for row in views)
                if declared != observed:
                    raise FindingError(
                        "role_original_mismatch", task_dir, "role view does not use the manifest original image"
                    )
    return {
        "packages": packages,
        "localized_results": results,
        "budget_stops_before_request": budget_stops,
        "localized_boxes": boxes,
    }


def _validate_external_operations(view: ArchiveView, runs: list[RunEvidence]) -> dict[str, Any]:
    opened = returned = missing_sources = 0
    for run in runs:
        pending: dict[str, deque[int]] = defaultdict(deque)
        for event in run.events:
            payload = event.payload
            if not isinstance(payload, ExternalCoordinatorMcpPayload):
                continue
            view.capture(run.base, payload.request_content)
            if payload.phase in {"operation", "dispatch"}:
                pending[payload.method].append(event.sequence)
                opened += 1
            else:
                view.capture(run.base, payload.result_content)
                if pending[payload.method]:
                    start = pending[payload.method].popleft()
                    if event.sequence <= start:
                        raise FindingError("external_return_order", run.base, "return precedes its operation")
                    returned += 1
            source = next(
                (row for row in event.source_refs if row.source_id == "external-model-request-and-usage"),
                None,
            )
            if source is None or source.blob is None:
                raise FindingError(
                    "outer_evidence_status_missing", run.base, "outer request/usage lacks explicit missing evidence"
                )
            marker = _json(view.blob(run.base, source.blob))
            if marker.get("kind") != "missing":
                raise FindingError(
                    "outer_evidence_not_missing", run.base, "outer request/usage must remain explicitly missing"
                )
            missing_sources += 1
        unmatched = sum(len(queue) for queue in pending.values())
        if unmatched:
            raise FindingError("external_return_missing", run.base, "operation/dispatch has no recorded return")
    return {
        "operations_or_dispatches": opened,
        "matched_returns": returned,
        "outer_missing_markers": missing_sources,
        "outer_model_request": "missing",
        "outer_model_usage": "missing",
    }


def _usage_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for usage in rows:
        for key in totals:
            value = usage.get(key)
            if type(value) is int and value >= 0:
                totals[key] += value
    return totals


def _validate_role_batch(
    view: ArchiveView,
    manifest: dict[str, Any],
    runs: list[RunEvidence],
    *,
    root_name: str,
    expected_case_ids: set[str],
    request_cap: int,
    run_prefix: str = "",
) -> dict[str, Any]:
    protocol_path = f"{root_name}/protocol.json"
    index_path = f"{root_name}/index.json"
    protocol = view.json(protocol_path)
    index = view.json(index_path)
    if not isinstance(index, list):
        raise FindingError("invalid_role_index", index_path, "role index is not a list")
    manifest_bytes = ROLE_MANIFEST.read_bytes()
    if protocol.get("manifest_sha256") != _sha256(manifest_bytes):
        raise FindingError("role_manifest_mismatch", protocol_path, "frozen manifest hash differs")
    models = protocol.get("models")
    if not isinstance(models, list) or len(models) != 2 or len(set(models)) != 2:
        raise FindingError("invalid_role_models", protocol_path, "protocol needs two unique models")
    cases = {row["case_id"]: row for row in manifest["cases"]}
    if not expected_case_ids <= set(cases):
        raise FindingError("unknown_expected_role_case", root_name, "batch expects a case outside the manifest")
    max_model_calls = protocol.get("max_model_calls_per_question")
    if type(max_model_calls) is not int or max_model_calls < 1:
        raise FindingError("role_protocol_model_cap", protocol_path, "per-question model cap is invalid")
    if (
        protocol.get("questions_per_model") != len(expected_case_ids)
        or protocol.get("max_batch_requests") not in {request_cap, 60}
        or protocol.get("retries") != 0
        or protocol.get("fallback") is not False
    ):
        raise FindingError("role_protocol_mismatch", protocol_path, "batch protocol or cap differs")
    if run_prefix:
        if (
            max_model_calls != 3
            or protocol.get("max_requests_this_batch") != request_cap
            or max_model_calls * len(expected_case_ids) * len(models) != request_cap
            or protocol.get("run_prefix") != run_prefix
            or set(protocol.get("case_ids", ())) != expected_case_ids
            or protocol.get("shared_quota")
            != REQUIRED_ROOTS["role_tests"] + "/role_requests.jsonl"
            or protocol.get("baseline_attempts_at_start") != 21
        ):
            raise FindingError(
                "followup_request_cap_mismatch", protocol_path, "follow-up per-question and batch caps disagree"
            )
        budget_limits = protocol.get("budget_limits")
        if not isinstance(budget_limits, dict) or not {
            "model_calls", "tool_calls", "tokens", "seconds"
        } <= set(budget_limits):
            raise FindingError(
                "followup_budget_limits_missing", protocol_path, "follow-up per-question limits are not recorded"
            )
    else:
        budget_limits = None
    expected = {(case_id, model) for case_id in expected_case_ids for model in models}
    observed = [(row.get("case_id"), row.get("model")) for row in index]
    if len(observed) != len(expected) or set(observed) != expected or len(set(observed)) != len(observed):
        raise FindingError("role_coverage_incomplete", index_path, "index is not the exact case/model matrix")
    run_by_base = {run.base: run for run in runs}
    model_request_total = 0
    expected_reports: set[str] = set()
    for row in index:
        case = cases[row["case_id"]]
        for field in ("test_group", "input_kind", "information_sufficiency", "photo_surrogate"):
            if row.get(field) != case[field]:
                raise FindingError("role_index_case_mismatch", index_path, "index differs from manifest")
        run_id = row.get("run_id")
        if run_prefix and not str(run_id).startswith(run_prefix):
            raise FindingError(
                "role_batch_run_prefix", index_path, "role batch run ID lacks its independent prefix"
            )
        base = f"{root_name}/{run_id}"
        if base not in run_by_base:
            raise FindingError("role_run_missing", base, "indexed role run has no event log")
        if run_by_base[base].run_id != run_id:
            raise FindingError("role_run_id_mismatch", base, "directory, index and journal run IDs differ")
        case_path = f"{base}/role_case.json"
        expected_reports.add(case_path)
        report = view.json(case_path)
        for field in ("case_id", "model", "run_id", "test_group", "model_requests"):
            if report.get(field) != row.get(field):
                raise FindingError("role_report_mismatch", case_path, "role report differs from batch index")
        child_ids = {event.task_id for event in run_by_base[base].events} - {
            run_by_base[base].root_task_id
        }
        if child_ids != {row["case_id"]}:
            raise FindingError("role_child_mismatch", base, "role run child task differs from indexed case")
        delegations = sorted(
            path
            for path in view.keys
            if path.startswith(base + "/tasks/") and path.endswith("/delegation.json")
        )
        if len(delegations) != 1:
            raise FindingError("role_delegation_count", base, "role run must have one child delegation")
        delegation = view.json(delegations[0])
        delegated_budget = delegation.get("arguments", {}).get("budget")
        if not isinstance(delegated_budget, dict) or delegated_budget.get("model_calls") != max_model_calls:
            raise FindingError("role_delegated_budget", delegations[0], "delegation differs from protocol model cap")
        if budget_limits is not None and any(
            delegated_budget.get(key) != budget_limits.get(key)
            for key in ("model_calls", "tool_calls", "tokens", "seconds")
        ):
            raise FindingError("followup_delegated_budget", delegations[0], "delegation differs from protocol limits")
        observation = view.json(delegations[0].removesuffix("delegation.json") + "observation.json")
        runtime = observation.get("runtime", {})
        runtime_limits = runtime.get("limits", {})
        if any(
            runtime_limits.get(key) != delegated_budget.get(key)
            for key in ("model_calls", "tool_calls", "tokens", "seconds")
        ):
            raise FindingError("role_runtime_limits", delegations[0], "runtime limits differ from delegation")
        request_events = [
            event
            for event in run_by_base[base].events
            if isinstance(event.payload, AdapterRequestPayload)
        ]
        actual_requests = len(request_events)
        if actual_requests != row["model_requests"]:
            raise FindingError("role_request_count_mismatch", base, "index request count differs from event log")
        if any(
            view.capture(base, event.payload.final_request_body).get("model") != row["model"]
            for event in request_events
        ):
            raise FindingError("role_request_model_mismatch", base, "wire request model differs from batch index")
        actual_tools = sum(
            event.task_id == row["case_id"] and event.payload.event_type == "tool_execution"
            for event in run_by_base[base].events
        )
        if runtime.get("model_calls") != actual_requests or runtime.get("tool_calls") != actual_tools:
            raise FindingError("role_runtime_counts", base, "runtime call counts differ from event log")
        event_usage = [
            event.payload.usage.model_dump(mode="json")
            for event in run_by_base[base].events
            if event.payload.event_type == "model_response"
        ]
        if report.get("usage") != event_usage or row.get("usage") != event_usage:
            raise FindingError("role_usage_mismatch", base, "role usage differs from message events")
        model_request_total += actual_requests
    discovered_reports = {
        path for path in view.keys if path.startswith(root_name + "/") and path.endswith("/role_case.json")
    }
    if discovered_reports != expected_reports:
        raise FindingError(
            "unindexed_role_report", root_name, "role_case files differ from the complete batch index"
        )
    if model_request_total > request_cap:
        raise FindingError("role_batch_cap_exceeded", root_name, "batch exceeded its request allowance")
    groups = Counter(cases[case_id]["test_group"] for case_id in expected_case_ids)
    return {
        "questions": len(index),
        "cases": len(expected_case_ids),
        "models": len(models),
        "groups": dict(sorted(groups.items())),
        "model_requests": model_request_total,
        "request_cap": request_cap,
        "prior_attempts_at_start": protocol.get("prior_attempts_at_start"),
        "semantic_correctness": "not_evaluated",
    }


def _validate_role_coverage(
    view: ArchiveView, manifest: dict[str, Any], runs: list[RunEvidence]
) -> dict[str, Any]:
    cases = {row["case_id"]: row for row in manifest["cases"]}
    groups = Counter(row["test_group"] for row in manifest["cases"])
    expected_groups = Counter({
        "drawing": 3,
        "mesh_render": 3,
        "photo_surrogate": 2,
        "information_insufficient": 2,
    })
    if groups != expected_groups:
        raise FindingError(
            "role_group_coverage", "role_cases/manifest.json", "manifest does not cover four frozen groups"
        )
    baseline = _validate_role_batch(
        view, manifest, runs, root_name="role_tests", expected_case_ids=set(cases), request_cap=60
    )
    drawing = {case_id for case_id, row in cases.items() if row["test_group"] == "drawing"}
    followup = _validate_role_batch(
        view, manifest, runs, root_name="role_followup", expected_case_ids=drawing,
        request_cap=18, run_prefix="followup_",
    )
    final = _validate_role_batch(
        view, manifest, runs, root_name="role_final", expected_case_ids=drawing,
        request_cap=18, run_prefix="final_",
    )
    expected_prior = 21 + followup["model_requests"]
    prior = final["prior_attempts_at_start"]
    if type(prior) is not int or prior < 21 or prior != expected_prior:
        raise FindingError(
            "final_prior_attempt_mismatch", "role_final/protocol.json",
            "final batch start ticket differs from retained baseline and follow-up requests",
        )
    return {
        "baseline": baseline,
        "followup": followup,
        "final": final,
        "questions": baseline["questions"] + followup["questions"] + final["questions"],
        "model_requests": (
            baseline["model_requests"] + followup["model_requests"] + final["model_requests"]
        ),
        "semantic_correctness": "not_evaluated",
    }


def _validate_quota(
    view: ArchiveView, role_requests: int, runs: list[RunEvidence]
) -> dict[str, Any]:
    logical = "role_tests/role_requests.jsonl"
    data = view.read(logical)
    if data and not data.endswith(b"\n"):
        raise FindingError("torn_quota_log", logical, "quota log lacks its final newline")
    rows = [json.loads(line) for line in data.splitlines()]
    attempts = [row for row in rows if row.get("event") == "attempt"]
    completions = [row for row in rows if row.get("event") in {"response", "failure"}]
    if any(row.get("category") != "role_tests" or row.get("limit") != 60 for row in rows):
        raise FindingError("quota_identity_mismatch", logical, "quota category or cap changed")
    tickets = [row.get("ticket") for row in attempts]
    if tickets != list(range(1, len(attempts) + 1)) or len(attempts) > 60:
        raise FindingError("quota_exceeded", logical, "request tickets are not contiguous within the cap")
    if Counter(row.get("ticket") for row in completions) != Counter(tickets):
        raise FindingError("quota_completion_mismatch", logical, "each attempted send needs one completion")
    if len(attempts) != role_requests:
        raise FindingError("quota_request_mismatch", logical, "quota attempts differ from adapter requests")
    event_models = Counter(
        view.capture(run.base, event.payload.final_request_body).get("model")
        for run in runs
        if run.base.startswith(("role_tests/", "role_followup/", "role_final/"))
        for event in run.events
        if isinstance(event.payload, AdapterRequestPayload)
    )
    if Counter(row.get("model") for row in attempts) != event_models:
        raise FindingError("quota_model_mismatch", logical, "quota attempt models differ from wire requests")
    reported = [
        row["usage"]
        for row in completions
        if row.get("event") == "response" and row.get("usage_status") == "reported"
    ]
    event_reported = [
        event.payload.usage.raw_usage
        for run in runs
        if run.base.startswith(("role_tests/", "role_followup/", "role_final/"))
        for event in run.events
        if event.payload.event_type == "model_response" and event.payload.usage.kind == "reported"
    ]
    def canonical(values):
        return Counter(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for value in values
        )
    if canonical(reported) != canonical(event_reported):
        raise FindingError("quota_usage_mismatch", logical, "quota usage differs from model response events")
    missing = sum(
        row.get("event") == "response" and row.get("usage_status") == "missing"
        for row in completions
    )
    failures = sum(row.get("event") == "failure" for row in completions)
    return {
        "attempts": len(attempts),
        "limit": 60,
        "responses": sum(row.get("event") == "response" for row in completions),
        "failures": failures,
        "reported_usage": _usage_counts(reported),
        "missing_usage_responses": missing,
        "attempts_without_reported_usage": failures + missing,
    }


def _validate_calibration() -> dict[str, Any]:
    attempts = json.loads((CALIBRATION / "attempts.json").read_bytes())
    summary = json.loads((CALIBRATION / "summary.json").read_bytes())
    rows = attempts.get("attempts")
    if not isinstance(rows, list):
        raise FindingError("invalid_calibration", "calibration/attempts.json", "attempts is not a list")
    count = len(rows)
    if count > 20 or attempts.get("maximum_attempts", 21) > 20 or attempts.get("attempts_reserved", 21) > 20:
        raise FindingError("calibration_cap_exceeded", "calibration/attempts.json", "calibration exceeds 20 attempts")
    if attempts.get("automatic_retries") != 0 or summary.get("retries") != 0:
        raise FindingError("calibration_retry", "calibration", "calibration contains an automatic retry")
    usages = []
    for row in rows:
        result = row.get("result", {})
        if row.get("state") != "finished" or result.get("requests_logged") != 1:
            raise FindingError("calibration_attempt_incomplete", "calibration/attempts.json", "calibration attempt is incomplete")
        usage = result.get("reported_usage", {})
        if usage.get("kind") != "reported":
            raise FindingError("calibration_usage_missing", "calibration/attempts.json", "calibration usage is missing")
        usages.append(usage["raw_usage"])
    totals = _usage_counts(usages)
    if summary.get("requests") != count or summary.get("reported_usage") != totals:
        raise FindingError("calibration_summary_mismatch", "calibration/summary.json", "summary differs from attempts")
    return {
        "attempts": count,
        "limit": 20,
        "reported_usage": totals,
        "attempts_sha256": _sha256((CALIBRATION / "attempts.json").read_bytes()),
        "summary_sha256": _sha256((CALIBRATION / "summary.json").read_bytes()),
    }


def _validate_protocol_sources(view: ArchiveView) -> dict[str, int]:
    count = current_matches = historical_versions = 0
    roots = ["role_tests", "role_followup", "role_final"]
    for root_name in roots:
        logical = f"{root_name}/protocol.json"
        protocol = view.json(logical)
        sources = protocol.get("source_files")
        if not isinstance(sources, dict) or not sources:
            raise FindingError("missing_protocol_sources", logical, "source hashes are absent")
        for relative, digest in sources.items():
            if (
                not isinstance(relative, str)
                or not isinstance(digest, str)
                or not SHA256_RE.fullmatch(digest)
            ):
                raise FindingError("protocol_source_invalid", logical, "recorded source identity is invalid")
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise FindingError("protocol_source_invalid", logical, "recorded source identity is invalid")
            if _sha256(path.read_bytes()) == digest:
                current_matches += 1
            else:
                # Baseline and follow-up intentionally freeze different code
                # versions. The protocol hash identifies the executed bytes;
                # a later worktree version is not evidence corruption.
                historical_versions += 1
        count += len(sources)
    return {
        "protocols": len(roots),
        "source_file_records": count,
        "current_source_matches": current_matches,
        "recorded_historical_versions": historical_versions,
    }


def verify_mapping(files: Mapping[str, bytes], *, archive_manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify a restored archive Mapping. Used by the CLI and offline tests."""

    auditor = Auditor()
    view = ArchiveView(files)
    manifest = json.loads(ROLE_MANIFEST.read_bytes())
    cases = {row["case_id"]: row for row in manifest["cases"]}

    def archive_identity():
        roots = archive_manifest.get("roots")
        auditor.require(isinstance(roots, dict), "invalid_archive_roots", "archive", "archive roots are absent")
        observed = {name: row.get("source_path") for name, row in roots.items()}
        auditor.require(
            observed == REQUIRED_ROOTS,
            "archive_root_mismatch", "archive", "source roots differ from delivery plan",
        )
        return {"roots": sorted(observed), "files": len(files)}

    auditor.check("archive_roots", archive_identity)
    auditor.check("blob_inventory", lambda: _validate_blob_inventory(view))
    runs = auditor.check("event_inventory", lambda: _load_runs(view, auditor)) or []
    event_detail = auditor.check("complete_event_logs", lambda: _validate_event_logs(view, runs)) or {}
    auditor.check("task_parentage_and_root_ledger", lambda: _validate_parentage(runs))
    wire_detail = auditor.check("request_injections_and_images", lambda: _validate_wire_requests(view, runs)) or {}
    auditor.check("child_evidence_packages", lambda: _validate_child_packages(view, runs, cases))
    external_detail = auditor.check("external_operation_returns", lambda: _validate_external_operations(view, runs)) or {}
    role_detail = auditor.check("role_question_coverage", lambda: _validate_role_coverage(view, manifest, runs)) or {}
    role_requests = int(role_detail.get("model_requests", -1))
    quota_detail = auditor.check(
        "role_request_quota", lambda: _validate_quota(view, role_requests, runs)
    ) or {}
    calibration_detail = auditor.check("calibration_usage", _validate_calibration) or {}
    auditor.check("recorded_protocol_sources", lambda: _validate_protocol_sources(view))

    role_usage = quota_detail.get("reported_usage", {})
    calibration_usage = calibration_detail.get("reported_usage", {})
    combined = {
        key: int(role_usage.get(key, 0)) + int(calibration_usage.get(key, 0))
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    status = "passed" if not auditor.findings else "failed"
    return {
        "schema": SCHEMA,
        "status": status,
        "checks": auditor.checks,
        "findings": auditor.findings,
        "evidence_counts": {
            "runs": event_detail.get("runs", 0),
            "events": event_detail.get("events", 0),
            "adapter_requests": wire_detail.get("adapter_requests", 0),
        },
        "provider_usage": {
            "shared_role_quota": quota_detail,
            "calibration": calibration_detail,
            "combined_attempts": int(quota_detail.get("attempts", 0))
            + int(calibration_detail.get("attempts", 0)),
            "combined_reported": combined,
            "offline_scripted_usage": "excluded",
            "outer_coordinator_request": external_detail.get("outer_model_request", "missing"),
            "outer_coordinator_usage": external_detail.get("outer_model_usage", "missing"),
        },
        "role_coverage": role_detail,
        "semantic_correctness": {
            "status": "not_evaluated",
            "reason": "structural verification does not score architectural answer quality",
        },
        "privacy": {
            "request_content_emitted": False,
            "response_content_emitted": False,
            "credentials_emitted": False,
        },
    }


def verify_delivery(archive_path: Path) -> dict[str, Any]:
    archive = _load_evidence_pack().read_archive(archive_path)
    report = verify_mapping(archive, archive_manifest=archive.manifest)
    report["archive"] = {
        "name": Path(archive_path).name,
        "sha256": _sha256(Path(archive_path).read_bytes()),
        "bytes": Path(archive_path).stat().st_size,
        "restoration": "verified_mapping",
    }
    return report


def _write_report(path: Path, data: bytes) -> None:
    destination = path.resolve()
    if not destination.is_relative_to(ROOT):
        raise ValueError("--out must stay inside this worktree")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--out", type=Path, help="optional JSON path inside this worktree")
    args = parser.parse_args(argv)
    try:
        archive = args.archive.resolve()
        if not archive.is_relative_to(ROOT):
            raise ValueError("archive must stay inside this worktree")
        report = verify_delivery(archive)
    except Exception as error:
        report = {
            "schema": SCHEMA,
            "status": "failed",
            "checks": [{"name": "archive_load", "status": "failed"}],
            "findings": [{
                "code": "archive_unreadable",
                "path": Path(args.archive).name,
                "detail": _safe_detail(error),
            }],
            "semantic_correctness": {"status": "not_evaluated"},
            "privacy": {
                "request_content_emitted": False,
                "response_content_emitted": False,
                "credentials_emitted": False,
            },
        }
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    if args.out is not None:
        _write_report(args.out, encoded)
    sys.stdout.buffer.write(encoded)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
