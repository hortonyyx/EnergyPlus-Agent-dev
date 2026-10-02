"""Verify preserved stage-2 runs directly in archives, without extracting files."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
from types import SimpleNamespace

from src.agent_runtime.context import ContextManager
from src.harness_contracts import BudgetAmounts, EventEnvelope, EventLog, HashedBlobRef
from src.harness_contracts.events import _resolve_json_pointer


DIRECTORY = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
BASELINE = "c5926024"
FROZEN = ("scripts/tool_scripts", "src/agent/geometry", "src/agent/correction",
    "src/agent/execution", "AI_agent/Agent.md", "AI_agent/project",
    "AI_agent/logs/experiments/2026-10-02_harness_stage2/brief.md")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def package_entry(source):
    source = source.resolve()
    if not source.is_relative_to(ROOT):
        raise ValueError("entry evidence must come from this worktree")
    target = DIRECTORY / "evidence_frozen_entry.tar.gz"
    with target.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for path in sorted(source.rglob("*")):
                if not path.is_file() or path.name == "writer.lock" or path.name.endswith(".tmp"):
                    continue
                data = path.read_bytes()
                member = tarfile.TarInfo("frozen-entry/" + path.relative_to(source).as_posix())
                member.size, member.mtime, member.mode = len(data), 0, 0o644
                archive.addfile(member, io.BytesIO(data))
    return target


def audit_archive(path, prefix):
    with tarfile.open(path, "r:gz") as archive:
        files = {}
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            if not member.isfile() or name.is_absolute() or ".." in name.parts:
                raise ValueError("unsafe archive member")
            files[member.name] = archive.extractfile(member).read()

    def read(name):
        return files[f"{prefix}/{name}"]

    refs = set()

    def get_bytes(ref):
        data = read(ref.uri)
        if sha(data) != ref.sha256:
            raise ValueError("attachment hash mismatch")
        refs.add((ref.uri, ref.sha256))
        return data

    def captured(value):
        return value.value if value.kind == "inline" else json.loads(get_bytes(value.blob))

    events = tuple(EventEnvelope.model_validate_json(line) for line in read("events.jsonl").splitlines())
    journal = json.loads(read("journal.json"))
    limit = BudgetAmounts.model_validate_json(json.dumps(journal["budget_limit"]))
    EventLog(mode="complete", events=events, budget_limit=limit)
    by_id = {e.event_id: e for e in events}
    blob_count = 0
    for name, data in files.items():
        if name.startswith(prefix + "/blobs/"):
            if sha(data) != PurePosixPath(name).name:
                raise ValueError("blob filename differs from content hash")
            blob_count += 1
        # Check runtime-local references inside all JSON evidence, not only the
        # event envelopes. Historical external locators remain disclosed inputs.
        try:
            value = json.loads(data)
        except (ValueError, UnicodeError):
            continue
        for row in walk(value):
            if row.get("kind") == "sha256" and str(row.get("uri", "")).startswith("blobs/"):
                get_bytes(HashedBlobRef.model_validate_json(json.dumps(row)))
    for event in events:
        for row in walk(event.model_dump(mode="json")):
            if row.get("kind") == "sha256":
                get_bytes(HashedBlobRef.model_validate_json(json.dumps(row)))

    actual_images, requests = 0, 0
    for event in events:
        payload = event.payload
        if payload.event_type == "adapter_request":
            requests += 1
            body = captured(payload.final_request_body)
            for injection in payload.injected_content:
                assert captured(injection.content) == _resolve_json_pointer(body, injection.request_location)
            for image in payload.images:
                url = _resolve_json_pointer(body, image.request_reference)
                raw = base64.b64decode(url.split(",", 1)[1], validate=True)
                assert raw == get_bytes(image.sent)
                get_bytes(image.original)
                actual_images += 1
        elif payload.event_type == "tool_presentation":
            shown = captured(payload.shown_result)
            body = captured(by_id[payload.request_event_id].payload.final_request_body)
            assert shown["tool_message"] in body["messages"]
            blocks = [b for m in body["messages"] if isinstance(m.get("content"), list)
                for b in m["content"]]
            assert all(b in blocks for b in shown["image_blocks"])

    checkpoint = next(e.payload for e in reversed(events) if e.payload.event_type == "checkpoint")
    saved = json.loads(get_bytes(checkpoint.state))
    manager = ContextManager.load(SimpleNamespace(get_bytes=get_bytes, events=events), saved["context"])
    messages, sources = manager.full_history()
    assert len(messages) == len(sources)
    result = {"archive": path.name, "archive_sha256": sha(path.read_bytes()),
        "archive_bytes": path.stat().st_size, "event_count": len(events),
        "blob_count": blob_count, "verified_distinct_references": len(refs),
        "requests_with_exact_wire_verified": requests, "verified_image_transmissions": actual_images,
        "checkpoint_history_messages": len(messages),
        "state_categories": {k: len(v) for k, v in manager.checklist().categories.items()},
        "context_actions": dict(Counter(e.payload.action for e in events if e.payload.event_type == "context")),
        "receipt_status": json.loads(read("receipt.json"))["status"]}
    if prefix == "frozen-entry":
        first = next(e.payload for e in events if e.payload.event_type == "adapter_request")
        body = captured(first.final_request_body)
        assert body["messages"][0]["content"].encode() == read("guide.txt")
        assert [t["function"] for t in body["tools"]] == [
            {"name": t["name"], "description": t.get("description", ""), "parameters": t["inputSchema"]}
            for t in json.loads(read("frozen/coordinator_tools.json"))["tools"]]
        result["frozen_guidance_characters"] = len(body["messages"][0]["content"])
        result["frozen_tools"] = len(body["tools"])
        manifest = json.loads(read("versions.json"))
        names = ("code_commit", "dependency_lock", "prompt", "tool_definitions",
            "inference_parameters", "model_route")
        assert all(manifest[name]["identifier"] and manifest[name]["evidence"] for name in names)
        result["six_required_versions_verified"] = list(names)
        result["remote_alias_status"] = manifest["remote_model"]["alias_status"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-run", type=Path, help="package the final real frozen-tool pytest run first")
    args = parser.parse_args()
    if args.entry_run:
        package_entry(args.entry_run)
    changed = subprocess.check_output(["git", "diff", "--name-only", BASELINE, "--", *FROZEN], cwd=ROOT, text=True).splitlines()
    if changed:
        raise ValueError(f"frozen files changed: {changed}")
    cases = (("evidence_frozen_entry.tar.gz", "frozen-entry"),
        ("evidence_complete75.tar.gz", "complete75/run"),
        ("evidence_unknown_write.tar.gz", "unknown-write/run"))
    report = {"baseline": BASELINE, "frozen_paths_unchanged": list(FROZEN),
        "cases": [audit_archive(DIRECTORY / name, prefix) for name, prefix in cases if (DIRECTORY / name).exists()],
        "missing_archives": [name for name, _ in cases if not (DIRECTORY / name).exists()]}
    (DIRECTORY / "delivery_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    if report["missing_archives"]:
        raise ValueError("delivery is incomplete: required evidence archives are missing")


if __name__ == "__main__":
    main()
