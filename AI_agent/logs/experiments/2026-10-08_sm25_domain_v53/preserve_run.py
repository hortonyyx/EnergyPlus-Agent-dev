"""Preserve the one completed sm25 domain-v53 run without Git or deletion.

This script is intentionally pinned to the paths and frozen commit below.  It
refuses an incomplete run, a changed input/code manifest, links/reparse points,
or any existing destination byte that differs.  It never deletes, overwrites,
invokes Git, or accesses the network.

The script is prepared for the project lead to run after the active launch has
fully exited.  It must not be run while ``launch_receipt.json`` says running.
"""

from __future__ import annotations

from datetime import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile
from typing import Any, BinaryIO


EXPECTED_COMMIT = "b55d47e7c82bb306c7ea838f00985648eef94304"
EXPECTED_DOMAIN = "domain-v53-20261008"
EXPECTED_RUNTIME = "runtime-v1-20261007"
EXPECTED_RUN_ID = "sm25_role_v53"

REPOSITORY = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev")
EXPERIMENT = REPOSITORY / "AI_agent/logs/experiments/2026-10-08_sm25_domain_v53"
WORKTREE = Path(r"D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008")
SOURCE = WORKTREE / "AI_agent/archive/local_backup/sm25_v53/sm25_role_v53"
DESTINATION = REPOSITORY / "AI_agent/archive/local_backup/sm25_v53/sm25_role_v53"
STAGING = REPOSITORY / "AI_agent/archive/local_backup/sm25_v53/evidence_staging"
CASE_INPUTS = WORKTREE / "case_tests/e2e_tests/sm25-L_anchor/case_data"

ARCHIVE_NAME = "sm25_v53_run.tar.gz"
ARCHIVE_PREFIX = PurePosixPath("AI_agent/archive/local_backup/sm25_v53/sm25_role_v53")
GITHUB_LIMIT = 100 * 1024 * 1024
PART_BYTES = 90 * 1024 * 1024
CHUNK_BYTES = 8 * 1024 * 1024
REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class PreservationError(RuntimeError):
    """A preservation precondition or byte-integrity check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreservationError(message)


def load_json(path: Path) -> Any:
    require(path.is_file(), f"required JSON is missing: {path}")
    try:
        return json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise PreservationError(f"cannot read JSON {path}: {error}") from error


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def is_reparse(file_stat: os.stat_result) -> bool:
    return bool(getattr(file_stat, "st_file_attributes", 0) & REPARSE_FLAG)


def checked_stat(path: Path, *, kind: str) -> os.stat_result:
    try:
        file_stat = path.stat(follow_symlinks=False)
    except OSError as error:
        raise PreservationError(f"cannot stat {path}: {error}") from error
    require(not stat.S_ISLNK(file_stat.st_mode), f"symbolic link is forbidden: {path}")
    require(not is_reparse(file_stat), f"reparse point is forbidden: {path}")
    if kind == "file":
        require(stat.S_ISREG(file_stat.st_mode), f"ordinary file required: {path}")
    elif kind == "directory":
        require(stat.S_ISDIR(file_stat.st_mode), f"ordinary directory required: {path}")
    else:  # pragma: no cover - internal programming error
        raise AssertionError(kind)
    return file_stat


def assert_chain_no_reparse(root: Path, target: Path) -> None:
    root_resolved = root.resolve(strict=True)
    target_resolved = target.resolve(strict=True)
    require(target_resolved == root_resolved or target_resolved.is_relative_to(root_resolved),
            f"path escapes expected root: {target}")
    checked_stat(root, kind="directory")
    current = root
    for part in target.relative_to(root).parts:
        current = current / part
        checked_stat(current, kind="directory" if current.is_dir() else "file")


def safe_relative_path(text: str) -> PurePosixPath:
    relative = PurePosixPath(text)
    require(not relative.is_absolute(), f"absolute relative path is forbidden: {text}")
    require(relative.parts and all(part not in {"", ".", ".."} for part in relative.parts),
            f"unsafe relative path: {text}")
    return relative


def path_from_relative(root: Path, relative: str, *, must_exist: bool) -> Path:
    parts = safe_relative_path(relative).parts
    target = root.joinpath(*parts)
    if must_exist:
        resolved = target.resolve(strict=True)
        require(resolved.is_relative_to(root.resolve(strict=True)), f"path escapes root: {relative}")
    else:
        resolved_parent = target.parent.resolve(strict=False)
        require(resolved_parent.is_relative_to(root.resolve(strict=True)), f"path escapes root: {relative}")
    return target


def hash_stream(stream: BinaryIO, *, limit: int | None = None) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    while limit is None or total < limit:
        wanted = CHUNK_BYTES if limit is None else min(CHUNK_BYTES, limit - total)
        block = stream.read(wanted)
        if not block:
            break
        digest.update(block)
        total += len(block)
    return digest.hexdigest(), total


def hash_file(path: Path) -> tuple[str, int]:
    before = checked_stat(path, kind="file")
    try:
        with path.open("rb") as stream:
            digest, total = hash_stream(stream)
    except OSError as error:
        raise PreservationError(f"cannot hash {path}: {error}") from error
    after = checked_stat(path, kind="file")
    require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"file changed while hashing: {path}",
    )
    require(total == after.st_size, f"short read while hashing: {path}")
    return digest, total


def scan_tree(root: Path) -> list[dict[str, Any]]:
    root = root.resolve(strict=True)
    checked_stat(root, kind="directory")
    files: list[dict[str, Any]] = []

    def visit(directory: Path, prefix: PurePosixPath) -> None:
        checked_stat(directory, kind="directory")
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda item: item.name)
        except OSError as error:
            raise PreservationError(f"cannot scan {directory}: {error}") from error
        for entry in entries:
            path = Path(entry.path)
            try:
                file_stat = entry.stat(follow_symlinks=False)
            except OSError as error:
                raise PreservationError(f"cannot stat {path}: {error}") from error
            require(not entry.is_symlink(), f"symbolic link is forbidden: {path}")
            require(not is_reparse(file_stat), f"reparse point is forbidden: {path}")
            relative = prefix / entry.name
            safe_relative_path(relative.as_posix())
            if stat.S_ISDIR(file_stat.st_mode):
                visit(path, relative)
            elif stat.S_ISREG(file_stat.st_mode):
                digest, size = hash_file(path)
                files.append({"path": relative.as_posix(), "bytes": size, "sha256": digest})
            else:
                raise PreservationError(f"unsupported filesystem object: {path}")

    visit(root, PurePosixPath())
    files.sort(key=lambda row: row["path"])
    return files


def manifest_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {row["path"]: row["sha256"] for row in rows}


def assert_manifest_rows(rows: list[dict[str, Any]], label: str) -> None:
    paths = [row.get("path") for row in rows]
    require(paths == sorted(paths), f"{label} paths are not sorted")
    require(len(paths) == len(set(paths)), f"{label} contains duplicate paths")
    for row in rows:
        safe_relative_path(str(row.get("path")))
        require(type(row.get("bytes")) is int and row["bytes"] >= 0,
                f"{label} has invalid byte count: {row}")
        digest = row.get("sha256")
        require(isinstance(digest, str) and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest),
                f"{label} has invalid SHA-256: {row}")


def require_same_rows(left: list[dict[str, Any]], right: list[dict[str, Any]], label: str) -> None:
    assert_manifest_rows(left, label + " left")
    assert_manifest_rows(right, label + " right")
    require(left == right, f"manifest mismatch: {label}")


def write_once(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    checked_stat(path.parent, kind="directory")
    if path.exists():
        digest, size = hash_file(path)
        require(size == len(data) and digest == hashlib.sha256(data).hexdigest(),
                f"refusing to overwrite different existing output: {path}")
        return "reused"
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise PreservationError(f"cannot create {path}: {error}") from error
    digest, size = hash_file(path)
    require(size == len(data) and digest == hashlib.sha256(data).hexdigest(),
            f"new output failed readback: {path}")
    return "created"


def parse_timestamp(value: object, label: str) -> datetime:
    require(isinstance(value, str) and value, f"{label} timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PreservationError(f"invalid {label} timestamp: {value}") from error
    require(parsed.tzinfo is not None, f"{label} timestamp has no timezone: {value}")
    return parsed


def require_exact_path(raw: object, expected: Path, label: str) -> None:
    require(isinstance(raw, str), f"{label} path is missing")
    try:
        actual = Path(raw).resolve(strict=True)
        wanted = expected.resolve(strict=True)
    except OSError as error:
        raise PreservationError(f"cannot resolve {label} path: {error}") from error
    require(actual == wanted, f"{label} path changed: {actual} != {wanted}")


def validate_input_manifest(value: Any, label: str) -> dict[str, str]:
    require(isinstance(value, dict), f"{label} must be an object")
    checked: dict[str, str] = {}
    for raw_path, digest in sorted(value.items()):
        require(isinstance(raw_path, str), f"{label} has a non-string path")
        path = safe_relative_path(raw_path).as_posix()
        require(path == raw_path.replace("\\", "/"), f"{label} path is not canonical: {raw_path}")
        require(isinstance(digest, str) and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest),
                f"{label} has invalid hash for {raw_path}")
        checked[path] = digest
    return checked


def read_detached_head() -> str:
    marker = WORKTREE / ".git"
    checked_stat(marker, kind="file")
    text = marker.read_text(encoding="utf-8").strip()
    require(text.startswith("gitdir: "), f"unexpected worktree .git marker: {text!r}")
    git_directory = Path(text.removeprefix("gitdir: "))
    if not git_directory.is_absolute():
        git_directory = (WORKTREE / git_directory).resolve()
    checked_stat(git_directory, kind="directory")
    head = git_directory / "HEAD"
    checked_stat(head, kind="file")
    value = head.read_text(encoding="ascii").strip()
    require(not value.startswith("ref:"), "frozen worktree HEAD is no longer detached")
    require(value == EXPECTED_COMMIT, f"frozen worktree HEAD changed: {value}")
    return value


def validate_code_manifest(versions: dict[str, Any]) -> dict[str, Any]:
    require(versions.get("code_commit", {}).get("identifier") == EXPECTED_COMMIT,
            "versions.json code commit changed")
    require(versions.get("domain_version", {}).get("identifier") == EXPECTED_DOMAIN,
            "versions.json domain version changed")
    require(versions.get("runtime_version", {}).get("identifier") == EXPECTED_RUNTIME,
            "versions.json runtime version changed")
    blob = versions.get("code_commit", {}).get("evidence", {}).get("blob", {})
    uri = blob.get("uri")
    expected_blob_hash = blob.get("sha256")
    require(isinstance(uri, str) and uri.startswith("blobs/"), "code-manifest blob URI is invalid")
    require(isinstance(expected_blob_hash, str), "code-manifest blob SHA is missing")
    blob_path = path_from_relative(SOURCE, uri, must_exist=True)
    blob_hash, _ = hash_file(blob_path)
    require(blob_hash == expected_blob_hash, "saved code-manifest blob hash changed")
    manifest = load_json(blob_path)
    require(isinstance(manifest, dict) and manifest.get("commit") == EXPECTED_COMMIT,
            "saved code manifest commit changed")
    files = manifest.get("files")
    require(isinstance(files, dict) and files, "saved code manifest has no files")
    for raw_path, expected_hash in sorted(files.items()):
        require(isinstance(raw_path, str) and isinstance(expected_hash, str),
                "saved code manifest row is malformed")
        source_path = path_from_relative(WORKTREE, raw_path, must_exist=True)
        assert_chain_no_reparse(WORKTREE, source_path)
        actual_hash, _ = hash_file(source_path)
        require(actual_hash == expected_hash, f"frozen source changed: {raw_path}")
    return {"blob_sha256": blob_hash, "file_count": len(files)}


def validate_terminal_state() -> dict[str, Any]:
    require(Path(__file__).resolve().parent == EXPERIMENT.resolve(strict=True),
            "preservation script moved outside its fixed experiment directory")
    require(WORKTREE.is_dir() and SOURCE.is_dir() and CASE_INPUTS.is_dir(),
            "fixed source/worktree/input path is missing")
    checked_stat(WORKTREE, kind="directory")
    checked_stat(SOURCE, kind="directory")
    require(read_detached_head() == EXPECTED_COMMIT, "frozen HEAD validation failed")

    launch = load_json(EXPERIMENT / "launch_receipt.json")
    require(isinstance(launch, dict), "launch receipt must be an object")
    require(launch.get("status") == "process_exited", "launch has not reached process_exited")
    require(type(launch.get("exit_code")) is int, "launch exit_code is missing")
    started = parse_timestamp(launch.get("started_utc"), "launch start")
    ended = parse_timestamp(launch.get("ended_utc"), "launch end")
    require(ended >= started, "launch end precedes launch start")
    require(launch.get("inputs_unchanged") is True, "launch did not certify unchanged inputs")
    require(launch.get("source_commit") == EXPECTED_COMMIT, "launch source commit changed")
    require_exact_path(launch.get("worktree"), WORKTREE, "launch worktree")
    require_exact_path(launch.get("output"), SOURCE, "launch output")
    config_hash, _ = hash_file(EXPERIMENT / "sm25_v53.json")
    require(launch.get("configuration_sha256") == config_hash, "launch configuration hash changed")

    before = validate_input_manifest(load_json(EXPERIMENT / "input_manifest_before.json"), "input before")
    after = validate_input_manifest(load_json(EXPERIMENT / "input_manifest_after.json"), "input after")
    require(before == after, "before/after input manifests differ")
    current_inputs = {row["path"]: row["sha256"] for row in scan_tree(CASE_INPUTS)}
    require(current_inputs == after, "case inputs changed after launch finalization")

    receipt = load_json(SOURCE / "receipt.json")
    summary = load_json(SOURCE / "bim/summary.json")
    require(isinstance(receipt, dict) and isinstance(receipt.get("status"), str),
            "root receipt has no terminal status")
    require(isinstance(summary, dict), "run summary must be an object")
    runtime_status = receipt["status"]
    require(summary.get("runtime_status") == runtime_status, "summary/receipt runtime status mismatch")
    require(summary.get("agent_response_completed") is (runtime_status == "completed"),
            "summary completion flag contradicts runtime status")
    require(summary.get("receipt") == "../receipt.json", "summary root receipt reference changed")
    require((launch["exit_code"] == 0) is (runtime_status == "completed"),
            "launcher exit code contradicts runtime status")

    for relative in ("behaviour/summary.json", "behaviour/timeline.md", "behaviour/record.json.gz"):
        checked_stat(path_from_relative(SOURCE, relative, must_exist=True), kind="file")

    coordinator_stops: list[dict[str, Any]] = []
    events_path = SOURCE / "events.jsonl"
    checked_stat(events_path, kind="file")
    with events_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            require(line.endswith("\n"), f"events.jsonl has an unterminated line {line_number}")
            require(line.strip(), f"events.jsonl has a blank line {line_number}")
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise PreservationError(f"events.jsonl line {line_number} is invalid: {error}") from error
            payload = event.get("payload", {}) if isinstance(event, dict) else {}
            if (event.get("task_id") == "coordinator"
                    and payload.get("event_type") == "run_lifecycle"
                    and payload.get("action") == "stop"):
                coordinator_stops.append(event)
    require(coordinator_stops, "coordinator has no durable terminal stop event")
    stop = coordinator_stops[-1]
    require(stop["payload"].get("reason") == runtime_status,
            "coordinator stop reason contradicts root receipt")

    versions = load_json(SOURCE / "versions.json")
    require(isinstance(versions, dict), "versions.json must be an object")
    code_manifest = validate_code_manifest(versions)
    return {
        "launch_exit_code": launch["exit_code"],
        "started_utc": launch["started_utc"],
        "ended_utc": launch["ended_utc"],
        "inputs_unchanged": True,
        "input_file_count": len(after),
        "runtime_status": runtime_status,
        "coordinator_stop_event_id": stop.get("event_id"),
        "coordinator_stop_reason": stop["payload"].get("reason"),
        "code_manifest": code_manifest,
    }


def ensure_destination_directory() -> None:
    ignored_rule = REPOSITORY / "AI_agent/archive/.gitignore"
    checked_stat(ignored_rule, kind="file")
    rules = {line.strip() for line in ignored_rule.read_text(encoding="utf-8").splitlines()}
    require("/local_backup/" in rules, "main local_backup is not covered by the expected ignore rule")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    checked_stat(DESTINATION, kind="directory")
    require(DESTINATION.resolve().is_relative_to((REPOSITORY / "AI_agent/archive/local_backup").resolve()),
            "destination escapes main local_backup")
    assert_chain_no_reparse(REPOSITORY, DESTINATION)


def copy_file_once(source: Path, destination: Path, expected: dict[str, Any]) -> str:
    if destination.exists():
        actual_hash, actual_size = hash_file(destination)
        require(actual_size == expected["bytes"] and actual_hash == expected["sha256"],
                f"existing destination differs; refusing overwrite: {destination}")
        return "reused"
    destination.parent.mkdir(parents=True, exist_ok=True)
    checked_stat(destination.parent, kind="directory")
    assert_chain_no_reparse(DESTINATION, destination.parent)
    before = checked_stat(source, kind="file")
    digest = hashlib.sha256()
    total = 0
    try:
        with source.open("rb") as input_stream, destination.open("xb") as output_stream:
            while True:
                block = input_stream.read(CHUNK_BYTES)
                if not block:
                    break
                output_stream.write(block)
                digest.update(block)
                total += len(block)
            output_stream.flush()
            os.fsync(output_stream.fileno())
    except OSError as error:
        raise PreservationError(
            f"copy failed without cleanup; inspect the possibly partial destination {destination}: {error}"
        ) from error
    after = checked_stat(source, kind="file")
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            f"source changed while copying: {source}")
    require(total == expected["bytes"] and digest.hexdigest() == expected["sha256"],
            f"source bytes changed while copying: {source}")
    copied_hash, copied_size = hash_file(destination)
    require(copied_size == expected["bytes"] and copied_hash == expected["sha256"],
            f"destination readback failed: {destination}")
    return "copied"


def copy_tree_once(source_rows: list[dict[str, Any]]) -> dict[str, int]:
    ensure_destination_directory()
    existing_rows = scan_tree(DESTINATION)
    source_paths = {row["path"] for row in source_rows}
    extras = sorted(row["path"] for row in existing_rows if row["path"] not in source_paths)
    require(not extras, f"destination has files absent from source: {extras[:10]}")
    counts = {"copied": 0, "reused": 0}
    for row in source_rows:
        source_path = path_from_relative(SOURCE, row["path"], must_exist=True)
        destination_path = path_from_relative(DESTINATION, row["path"], must_exist=False)
        outcome = copy_file_once(source_path, destination_path, row)
        counts[outcome] += 1
    return counts


def manifest_document(root: Path, pass_number: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "sm25_run_tree_manifest_v1",
        "root": str(root),
        "pass": pass_number,
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "files": rows,
    }


def archive_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    files = [
        {
            "path": (ARCHIVE_PREFIX / row["path"]).as_posix(),
            "bytes": row["bytes"],
            "sha256": row["sha256"],
        }
        for row in rows
    ]
    return {"schema_version": "sm25_run_archive_manifest_v1", "files": files}


def create_archive_once(path: Path, rows: list[dict[str, Any]]) -> str:
    STAGING.mkdir(parents=True, exist_ok=True)
    checked_stat(STAGING, kind="directory")
    require(STAGING.resolve().is_relative_to((REPOSITORY / "AI_agent/archive/local_backup").resolve()),
            "archive staging escapes main local_backup")
    assert_chain_no_reparse(REPOSITORY, STAGING)
    if path.exists():
        checked_stat(path, kind="file")
        return "reused"
    try:
        with path.open("xb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                    for row in rows:
                        source_path = path_from_relative(DESTINATION, row["path"], must_exist=True)
                        information = tarfile.TarInfo((ARCHIVE_PREFIX / row["path"]).as_posix())
                        information.size = row["bytes"]
                        information.mode = 0o644
                        information.mtime = 0
                        information.uid = 0
                        information.gid = 0
                        information.uname = ""
                        information.gname = ""
                        with source_path.open("rb") as stream:
                            archive.addfile(information, stream)
            raw.flush()
            os.fsync(raw.fileno())
    except (OSError, tarfile.TarError) as error:
        raise PreservationError(
            f"archive creation failed without cleanup; inspect the possibly partial archive {path}: {error}"
        ) from error
    return "created"


def validate_archive(path: Path, expected_manifest: dict[str, Any]) -> dict[str, Any]:
    expected = {row["path"]: row for row in expected_manifest["files"]}
    seen: dict[str, dict[str, Any]] = {}
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            for member in archive:
                relative = safe_relative_path(member.name)
                name = relative.as_posix()
                require(member.isfile(), f"archive has a non-regular member: {name}")
                require(name in expected, f"archive has an unexpected member: {name}")
                require(name not in seen, f"archive has a duplicate member: {name}")
                require(member.size == expected[name]["bytes"], f"archive member size differs: {name}")
                stream = archive.extractfile(member)
                require(stream is not None, f"cannot read archive member: {name}")
                with stream:
                    digest, size = hash_stream(stream)
                require(size == expected[name]["bytes"] and digest == expected[name]["sha256"],
                        f"archive member hash differs: {name}")
                seen[name] = {"bytes": size, "sha256": digest}
    except (OSError, tarfile.TarError) as error:
        raise PreservationError(f"cannot read back archive {path}: {error}") from error
    require(set(seen) == set(expected), "archive is missing expected files")
    archive_hash, archive_size = hash_file(path)
    return {
        "file_count": len(seen),
        "source_bytes": sum(row["bytes"] for row in expected.values()),
        "archive_bytes": archive_size,
        "archive_sha256": archive_hash,
        "all_archived_file_hashes_verified": True,
    }


def compare_part_to_archive(archive_stream: BinaryIO, part: Path, expected_bytes: int) -> dict[str, Any]:
    checked_stat(part, kind="file")
    part_stat = part.stat(follow_symlinks=False)
    require(part_stat.st_size == expected_bytes, f"existing archive part has wrong size: {part}")
    digest = hashlib.sha256()
    total = 0
    with part.open("rb") as part_stream:
        while total < expected_bytes:
            wanted = min(CHUNK_BYTES, expected_bytes - total)
            archive_block = archive_stream.read(wanted)
            part_block = part_stream.read(wanted)
            require(archive_block == part_block and len(part_block) == wanted,
                    f"existing archive part differs: {part}")
            digest.update(part_block)
            total += len(part_block)
        require(not part_stream.read(1), f"existing archive part has trailing bytes: {part}")
    return {"path": part.name, "bytes": total, "sha256": digest.hexdigest()}


def create_part_from_archive(archive_stream: BinaryIO, part: Path, expected_bytes: int) -> dict[str, Any]:
    digest = hashlib.sha256()
    total = 0
    try:
        with part.open("xb") as output:
            while total < expected_bytes:
                block = archive_stream.read(min(CHUNK_BYTES, expected_bytes - total))
                require(block, f"archive ended before part {part.name}")
                output.write(block)
                digest.update(block)
                total += len(block)
            output.flush()
            os.fsync(output.fileno())
    except OSError as error:
        raise PreservationError(
            f"part creation failed without cleanup; inspect the possibly partial part {part}: {error}"
        ) from error
    readback_hash, readback_size = hash_file(part)
    require(readback_size == total and readback_hash == digest.hexdigest(),
            f"archive part readback failed: {part}")
    return {"path": part.name, "bytes": total, "sha256": readback_hash}


def split_archive_if_needed(path: Path, archive_record: dict[str, Any]) -> list[dict[str, Any]]:
    existing_parts = sorted(STAGING.glob(ARCHIVE_NAME + ".part-*"), key=lambda item: item.name)
    for part in existing_parts:
        checked_stat(part, kind="file")
    if archive_record["archive_bytes"] <= GITHUB_LIMIT:
        require(not existing_parts, "stale archive parts exist although splitting is not required")
        return []

    part_count = (archive_record["archive_bytes"] + PART_BYTES - 1) // PART_BYTES
    expected_names = [f"{ARCHIVE_NAME}.part-{index:03d}" for index in range(part_count)]
    require(not (set(part.name for part in existing_parts) - set(expected_names)),
            "unexpected stale archive part exists")
    records: list[dict[str, Any]] = []
    with path.open("rb") as archive_stream:
        for index, name in enumerate(expected_names):
            remaining = archive_record["archive_bytes"] - index * PART_BYTES
            expected_bytes = min(PART_BYTES, remaining)
            part = STAGING / name
            if part.exists():
                records.append(compare_part_to_archive(archive_stream, part, expected_bytes))
            else:
                records.append(create_part_from_archive(archive_stream, part, expected_bytes))
        require(not archive_stream.read(1), "archive has trailing bytes beyond expected parts")

    joined = hashlib.sha256()
    joined_bytes = 0
    for record in records:
        part = STAGING / record["path"]
        with part.open("rb") as stream:
            while True:
                block = stream.read(CHUNK_BYTES)
                if not block:
                    break
                joined.update(block)
                joined_bytes += len(block)
    require(joined_bytes == archive_record["archive_bytes"], "archive part byte total differs")
    require(joined.hexdigest() == archive_record["archive_sha256"], "joined archive part hash differs")
    return records


def main() -> None:
    terminal = validate_terminal_state()

    source_pass_1 = scan_tree(SOURCE)
    assert_manifest_rows(source_pass_1, "source pass 1")
    copy_tree_once(source_pass_1)
    copy_pass_1 = scan_tree(DESTINATION)
    require_same_rows(source_pass_1, copy_pass_1, "source pass 1 vs copy pass 1")

    source_pass_2 = scan_tree(SOURCE)
    copy_pass_2 = scan_tree(DESTINATION)
    require_same_rows(source_pass_1, source_pass_2, "source pass 1 vs source pass 2")
    require_same_rows(copy_pass_1, copy_pass_2, "copy pass 1 vs copy pass 2")
    require_same_rows(source_pass_2, copy_pass_2, "source pass 2 vs copy pass 2")

    archived_manifest = archive_manifest(copy_pass_2)
    archived_manifest_bytes = json_bytes(archived_manifest)
    archive_path = STAGING / ARCHIVE_NAME
    create_archive_once(archive_path, copy_pass_2)
    archive_record = validate_archive(archive_path, archived_manifest)
    parts = split_archive_if_needed(archive_path, archive_record)

    manifest_documents = {
        "run_source_manifest_pass1.json": manifest_document(SOURCE, 1, source_pass_1),
        "run_source_manifest_pass2.json": manifest_document(SOURCE, 2, source_pass_2),
        "run_copy_manifest_pass1.json": manifest_document(DESTINATION, 1, copy_pass_1),
        "run_copy_manifest_pass2.json": manifest_document(DESTINATION, 2, copy_pass_2),
    }
    manifest_hashes = {
        name: hashlib.sha256(json_bytes(document)).hexdigest()
        for name, document in manifest_documents.items()
    }
    copy_summary = {
        "schema_version": "sm25_run_copy_summary_v1",
        "source": str(SOURCE),
        "destination": str(DESTINATION),
        "source_commit": EXPECTED_COMMIT,
        "file_count": len(copy_pass_2),
        "source_bytes": sum(row["bytes"] for row in copy_pass_2),
        "manifest_sha256": manifest_hashes,
        "source_two_passes_identical": True,
        "copy_two_passes_identical": True,
        "source_copy_identical": True,
    }
    evidence_payload = parts or [{
        "path": archive_path.name,
        "bytes": archive_record["archive_bytes"],
        "sha256": archive_record["archive_sha256"],
    }]
    archive_summary = {
        "schema_version": "sm25_run_archive_summary_v1",
        "mode": "complete_run",
        "run_id": EXPECTED_RUN_ID,
        "source_commit": EXPECTED_COMMIT,
        "domain_version": EXPECTED_DOMAIN,
        "runtime_version": EXPECTED_RUNTIME,
        "terminal": terminal,
        **archive_record,
        "archive_file": str(archive_path),
        "manifest_sha256": hashlib.sha256(archived_manifest_bytes).hexdigest(),
        "split_threshold_bytes": GITHUB_LIMIT,
        "part_size_bytes": PART_BYTES,
        "parts": parts,
        "evidence_payload_files": evidence_payload,
    }

    for name, document in manifest_documents.items():
        write_once(EXPERIMENT / name, json_bytes(document))
    write_once(EXPERIMENT / "run_copy_summary.json", json_bytes(copy_summary))
    for output_root in (EXPERIMENT, STAGING):
        write_once(output_root / "sm25_v53_run_manifest.json", archived_manifest_bytes)
        write_once(output_root / "sm25_v53_run_summary.json", json_bytes(archive_summary))

    print(json.dumps({
        "status": "preserved",
        "source": str(SOURCE),
        "destination": str(DESTINATION),
        "archive": str(archive_path),
        "archive_sha256": archive_record["archive_sha256"],
        "parts": [row["path"] for row in parts],
        "file_count": archive_record["file_count"],
        "source_bytes": archive_record["source_bytes"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except PreservationError as error:
        raise SystemExit(f"preservation refused: {error}") from error
