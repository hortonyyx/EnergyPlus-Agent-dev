"""Append-only event journal and verified content-addressed attachments."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from src.harness_contracts import (
    BlobCapture, BudgetAmounts, EventEnvelope, EventLog, HashedBlobRef,
    InlineCapture, KnownTimestamp, RootTask, SourceRef,
)


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


class EventStore:
    """One writer per run; flushed intent precedes every external operation.

    Torn JSONL tails are rejected unless explicit recovery preserves the exact
    tail and records its repair. Existing complete journals can
    be reopened; a nonblocking file lock prevents two writers using one run.
    """

    def __init__(self, directory: Path, *, run_id: str, task_id: str,
                 budget_limit: BudgetAmounts, recover_tail: bool = False):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "blobs").mkdir(exist_ok=True)
        self.run_id, self.task_id = run_id, task_id
        self.budget_limit = budget_limit
        self.path = self.directory / "events.jsonl"
        self._lock = (self.directory / "writer.lock").open("a+b")
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            repair = self._repair_tail() if recover_tail else None
            self.events = self.read_events(self.path)
            if self.events:
                self.validate()
                if any(e.run_id != run_id or e.task_id != task_id for e in self.events):
                    raise ValueError("journal identity differs from requested run/task")
            metadata = {"run_id": run_id, "task_id": task_id,
                        "budget_limit": budget_limit.model_dump(mode="json")}
            path = self.directory / "journal.json"
            if path.exists() and json.loads(path.read_bytes()) != metadata:
                raise ValueError("journal limits/identity cannot change on resume")
            if not path.exists():
                self.write_json("journal.json", metadata)
            if repair:
                from src.harness_contracts import RunLifecyclePayload
                self.append(RunLifecyclePayload(action="failure", failure_stage="journal_append",
                    reason="explicit torn-tail recovery; original bytes preserved"),
                    source_refs=(self.source("journal-tail-repair", repair),))
        except BaseException:
            self.close()
            raise

    @staticmethod
    def read_events(path: Path) -> list[EventEnvelope]:
        if not path.exists():
            return []
        raw = path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise ValueError("incomplete event journal tail; explicit recovery required")
        return [EventEnvelope.model_validate_json(line) for line in raw.splitlines()]

    def _repair_tail(self):
        if not self.path.exists():
            return None
        raw = self.path.read_bytes()
        if not raw or raw.endswith(b"\n"):
            return None
        boundary = raw.rfind(b"\n") + 1
        prefix, tail = raw[:boundary], raw[boundary:]
        # Verify every completed record before changing even the partial tail.
        events = [EventEnvelope.model_validate_json(line) for line in prefix.splitlines()]
        if events:
            EventLog(mode="complete", events=tuple(events), budget_limit=self.budget_limit)
        saved = self.put_bytes(tail)
        record = {"original_sha256": hashlib.sha256(raw).hexdigest(),
                  "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
                  "offset": boundary, "tail": saved.model_dump(mode="json")}
        # A complete JSON event missing only its newline is retained as an event.
        try:
            last = EventEnvelope.model_validate_json(tail)
            EventLog(mode="complete", events=tuple([*events, last]), budget_limit=self.budget_limit)
        except ValueError:
            repaired, record["action"] = prefix, "archive_incomplete_tail"
        else:
            repaired, record["action"] = raw + b"\n", "complete_newline"
        # The repair intent and removed bytes are durable before replacing JSONL.
        self.write_json("tail_repair.json", record)
        temporary = self.path.with_name(f"events.repair.{os.getpid()}.tmp")
        with temporary.open("wb") as output:
            output.write(repaired)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, self.path)
        self._sync_directory(self.directory)
        return record

    def latest_checkpoint(self):
        for event in reversed(self.events):
            if event.payload.event_type == "checkpoint":
                # Verify the blob now; never silently fall back past corruption.
                return event.payload.state, json.loads(self.get_bytes(event.payload.state)), event.sequence
        pointer = self.directory / "checkpoint.json"
        if not pointer.exists():
            return None
        ref = HashedBlobRef.model_validate_json(pointer.read_bytes())
        snapshot = json.loads(self.get_bytes(ref))
        sequence = next(e.sequence for e in self.events if e.event_id == snapshot["last_event_id"])
        return ref, snapshot, sequence

    def close(self):
        if not self._lock.closed:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_UN)
            self._lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def put_bytes(self, data: bytes, media_type="application/octet-stream") -> HashedBlobRef:
        sha = hashlib.sha256(data).hexdigest()
        relative = f"blobs/{sha}"
        path = self.directory / relative
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("content-addressed blob was corrupted")
        else:
            # Atomic creation inside the run, with a durable directory entry.
            temp = self.directory / f"blobs/.{sha}.{os.getpid()}.tmp"
            with temp.open("xb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, path)
            self._sync_directory(path.parent)
        return HashedBlobRef(uri=relative, sha256=sha, media_type=media_type)

    def put_json(self, value) -> HashedBlobRef:
        return self.put_bytes(json_bytes(value), "application/json")

    def get_bytes(self, ref: HashedBlobRef) -> bytes:
        path = (self.directory / ref.uri).resolve()
        if not path.is_relative_to(self.directory):
            raise ValueError("attachment reference escapes the run directory")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != ref.sha256:
            raise ValueError("attachment hash mismatch")
        return data

    def capture(self, value, *, force_blob=False):
        data = json_bytes(value)
        if force_blob or len(data) > 8192:
            return BlobCapture(blob=self.put_bytes(data, "application/json"))
        return InlineCapture(value=value)

    def resolve(self, capture):
        if capture.kind == "inline":
            return capture.value
        if capture.kind == "blob":
            return json.loads(self.get_bytes(capture.blob))
        raise ValueError(f"capture unavailable: {capture.reason}")

    def source(self, name: str, value, *, kind="runtime") -> SourceRef:
        return SourceRef(source_id=name, source_kind=kind, locator=name,
                         blob=self.put_json(value))

    def append(self, payload, *, source_refs=()) -> EventEnvelope:
        if self._lock.closed:
            raise ValueError("journal is closed")
        seq = self.events[-1].sequence + 1 if self.events else 0
        event = EventEnvelope(event_id=f"event-{seq:06d}", run_id=self.run_id,
            task_id=self.task_id, parent_task=RootTask(), sequence=seq,
            occurred_at=KnownTimestamp(value=datetime.now(UTC)),
            source_refs=tuple(source_refs), payload=payload)
        # Validate before appending. Prefixes with an in-flight request are valid.
        EventLog(mode="complete", events=tuple([*self.events, event]),
                 budget_limit=self.budget_limit)
        with self.path.open("ab") as output:
            output.write(event.model_dump_json().encode("utf-8") + b"\n")
            output.flush()
            os.fsync(output.fileno())
        self._sync_directory(self.directory)
        self.events.append(event)
        return event

    def validate(self) -> EventLog:
        return EventLog(mode="complete", events=tuple(self.events),
                        budget_limit=self.budget_limit)

    def write_json(self, name: str, value):
        path = (self.directory / name).resolve()
        if not path.is_relative_to(self.directory):
            raise ValueError("output path escapes run")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + f".{os.getpid()}.tmp")
        with temp.open("wb") as output:
            output.write(json_bytes(value))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
        self._sync_directory(path.parent)

    @staticmethod
    def _sync_directory(path):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
