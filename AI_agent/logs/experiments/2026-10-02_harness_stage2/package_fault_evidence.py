#!/usr/bin/env python3
"""Audit and deterministically package the two retained long-task runs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any


OUTPUT_DIRECTORY = Path(__file__).resolve().parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def audit(case_directory: Path, expected_status: str) -> dict[str, Any]:
    case_directory = case_directory.resolve()
    run = case_directory / "run"
    bim = case_directory / "isolated-bim"
    events_path = run / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    if [event["sequence"] for event in events] != list(range(len(events))):
        raise ValueError("event sequence is not contiguous")
    if [event["event_id"] for event in events] != [
        f"event-{index:06d}" for index in range(len(events))
    ]:
        raise ValueError("event IDs are not contiguous")
    receipt = json.loads((run / "receipt.json").read_bytes())
    if receipt["status"] != expected_status:
        raise ValueError(
            f"expected {expected_status!r}, found {receipt['status']!r} in {case_directory}"
        )

    blob_bytes = 0
    blob_hashes: list[str] = []
    for path in sorted((run / "blobs").iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        data = path.read_bytes()
        if sha256(data) != path.name:
            raise ValueError(f"content-addressed blob mismatch: {path}")
        blob_bytes += len(data)
        blob_hashes.append(path.name)

    checkpoint_ref = json.loads((run / "checkpoint.json").read_bytes())
    checkpoint_path = run / checkpoint_ref["uri"]
    checkpoint = checkpoint_path.read_bytes()
    if sha256(checkpoint) != checkpoint_ref["sha256"]:
        raise ValueError("checkpoint pointer hash mismatch")

    ledger = json.loads((bim / "applied_operations.json").read_bytes())
    if len(ledger) != len(set(ledger)):
        raise ValueError("isolated non-idempotent write ledger contains a duplicate")
    applied_write_ids = [
        event["payload"].get("applied_write_id")
        for event in events
        if event["payload"]["event_type"] == "tool_execution"
        and event["payload"].get("applied_write_id")
    ]
    if len(applied_write_ids) != len(set(applied_write_ids)):
        raise ValueError("runtime event log contains a repeated applied_write_id")

    unknown_inspections = [
        event
        for event in events
        if event["payload"]["event_type"] == "state_inspection"
        and event["payload"].get("purpose") == "unknown_write_recovery"
    ]
    if expected_status == "resume_pending_operation":
        if not unknown_inspections or any(
            event["payload"].get("conclusion") != "inconclusive"
            for event in unknown_inspections
        ):
            raise ValueError("unknown-write evidence lacks an inconclusive state inspection")

    event_types = Counter(event["payload"]["event_type"] for event in events)
    context_actions = Counter(
        event["payload"].get("action")
        for event in events
        if event["payload"]["event_type"] == "context"
    )
    return {
        "status": receipt["status"],
        "event_count": len(events),
        "event_types": dict(sorted(event_types.items())),
        "context_actions": dict(sorted(context_actions.items())),
        "model_calls": receipt["model_calls"],
        "tool_calls": receipt["tool_calls"],
        "ledger_write_count": len(ledger),
        "ledger_unique_write_count": len(set(ledger)),
        "event_applied_write_count": len(applied_write_ids),
        "unknown_state_inspections": len(unknown_inspections),
        "events_sha256": sha256(events_path.read_bytes()),
        "checkpoint_sha256": checkpoint_ref["sha256"],
        "source_bim_sha256": sha256((bim / "source_model.json").read_bytes()),
        "ledger_sha256": sha256((bim / "applied_operations.json").read_bytes()),
        "blob_count": len(blob_hashes),
        "blob_bytes": blob_bytes,
        "blob_set_sha256": sha256("\n".join(blob_hashes).encode("ascii")),
    }


def members(case_directory: Path, archive_root: str):
    for top in ("run", "isolated-bim"):
        root = case_directory / top
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(case_directory)
            if path.name == "writer.lock" or path.name.endswith(".tmp"):
                continue
            yield path, f"{archive_root}/{relative.as_posix()}"


def package(case_directory: Path, archive_path: Path, archive_root: str) -> dict[str, Any]:
    member_manifest: list[dict[str, Any]] = []
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path, name in members(case_directory, archive_root):
                    data = path.read_bytes()
                    info = tarfile.TarInfo(name=name)
                    info.size = len(data)
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(data))
                    member_manifest.append(
                        {"name": name, "byte_size": len(data), "sha256": sha256(data)}
                    )

    # Verify the compressed artifact without extracting or trusting member paths.
    observed: list[dict[str, Any]] = []
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                raise ValueError("evidence archive unexpectedly contains a non-file member")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"cannot read evidence member: {member.name}")
            data = extracted.read()
            observed.append(
                {"name": member.name, "byte_size": len(data), "sha256": sha256(data)}
            )
    if observed != member_manifest:
        raise ValueError("evidence archive member verification differs from source files")
    data = archive_path.read_bytes()
    return {
        "path": archive_path.name,
        "byte_size": len(data),
        "sha256": sha256(data),
        "members": member_manifest,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--complete", type=Path, required=True)
    parser.add_argument("--unknown-write", type=Path, required=True)
    args = parser.parse_args()
    cases = {
        "complete_75_step_recovery": (
            args.complete,
            "completed",
            OUTPUT_DIRECTORY / "evidence_complete75.tar.gz",
            "complete75",
        ),
        "unknown_write_stop": (
            args.unknown_write,
            "resume_pending_operation",
            OUTPUT_DIRECTORY / "evidence_unknown_write.tar.gz",
            "unknown-write",
        ),
    }
    report: dict[str, Any] = {
        "schema": "harness-stage2-fault-evidence/v1",
        "cases": {},
        "exclusions": ["writer.lock", "*.tmp"],
        "archive_normalization": {
            "gzip_mtime": 0,
            "tar_mtime": 0,
            "uid": 0,
            "gid": 0,
            "file_mode": "0644",
            "sorted_members": True,
        },
    }
    for case_id, (source, status, archive_path, archive_root) in cases.items():
        source = source.resolve()
        case_report = audit(source, status)
        case_report["archive"] = package(source, archive_path, archive_root)
        report["cases"][case_id] = case_report
    target = OUTPUT_DIRECTORY / "evidence_archives.json"
    target.write_bytes(json_bytes(report) + b"\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
