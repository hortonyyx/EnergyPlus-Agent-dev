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

    Torn JSONL tails are rejected, never silently deleted. Crash-tail recovery
    and concurrent scheduling belong to stage 2. Existing complete journals can
    be reopened; a nonblocking file lock prevents two writers using one run.
    """

    def __init__(self, directory: Path, *, run_id: str, task_id: str,
                 budget_limit: BudgetAmounts):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "blobs").mkdir(exist_ok=True)
        self.run_id, self.task_id = run_id, task_id
        self.budget_limit = budget_limit
        self.path = self.directory / "events.jsonl"
        self._lock = (self.directory / "writer.lock").open("a+b")
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
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
