"""Losslessly compact stage-2 evidence without copying historical images."""

from __future__ import annotations

import base64
from collections import Counter
from collections.abc import Iterator, Mapping
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DIRECTORY = Path(__file__).resolve().parent
FIXTURE_PATH = DIRECTORY / "run99_long_fixture.json"
SOURCE_MANIFEST_PATH = DIRECTORY / "source_manifest.json"
SCHEMA = "harness-stage2-compact-evidence/v1"
MANIFEST_MEMBER = "manifest.json"
MARKER_PREFIX = "__STAGE2_IMAGE_SHA256_"
_MARKER_RE = re.compile(
    rb"__STAGE2_IMAGE_SHA256_([0-9a-f]{64})__"
)
_HEX_RE = re.compile(r"[0-9a-f]{64}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _safe_relative(value: str, *, what: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or path == PurePosixPath(".")
        or ".." in path.parts
        or "\\" in value
    ):
        raise ValueError(f"unsafe {what}: {value!r}")
    return path


def _root_path(relative: str) -> Path:
    pure = _safe_relative(relative, what="repository path")
    path = (ROOT / Path(*pure.parts)).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("historical image path escapes this worktree")
    return path


def _checked_root_path(path: Path, *, what: str, must_exist: bool) -> Path:
    resolved = path.resolve(strict=must_exist)
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"{what} must be inside this worktree")
    return resolved


def _at_path(value: Any, path: list[Any]) -> Any:
    for component in path:
        if isinstance(component, bool) or not isinstance(component, (str, int)):
            raise ValueError("historical JSON path contains an invalid component")
        value = value[component]
    return value


class _HistoricalImages:
    """Resolve only image origins admitted by the checked-in run99 fixture."""

    def __init__(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_bytes())
        source_manifest = json.loads(SOURCE_MANIFEST_PATH.read_bytes())
        stream = source_manifest["sources"]["agent_stream"]
        self._stream_source = {
            "path": stream["path"],
            "byte_size": stream["byte_size"],
            "sha256": stream["sha256"],
        }
        self._descriptors: dict[str, dict[str, Any]] = {}
        self._stream_lines: list[Any] | None = None
        for step in fixture["steps"]:
            for image in step["result"]["images"]:
                digest = image["sha256"]
                if not _HEX_RE.fullmatch(digest):
                    raise ValueError("run99 fixture has an invalid image hash")
                origin = image["origin"]
                if origin["kind"] == "historical_file":
                    for item in sorted(origin["files"], key=lambda value: value["path"]):
                        descriptor = {
                            "kind": "historical_file",
                            "path": item["path"],
                            "file_sha256": digest,
                            "image_sha256": digest,
                            "byte_size": image["byte_size"],
                        }
                        current = self._descriptors.get(digest)
                        if current is None or current["kind"] != "historical_file":
                            self._descriptors[digest] = descriptor
                        break
                elif origin["kind"] == "historical_stream":
                    if origin["path"] != self._stream_source["path"]:
                        raise ValueError("run99 image names an unmanifested historical stream")
                    descriptor = {
                        "kind": "historical_stream",
                        "path": origin["path"],
                        "container_sha256": self._stream_source["sha256"],
                        "container_bytes": self._stream_source["byte_size"],
                        "line": origin["line"],
                        "json_path": origin["json_path"],
                        "image_sha256": digest,
                        "byte_size": image["byte_size"],
                    }
                    self._descriptors.setdefault(digest, descriptor)
                else:
                    raise ValueError("run99 fixture has an unsupported image origin")

    def descriptor(self, digest: str) -> dict[str, Any] | None:
        descriptor = self._descriptors.get(digest)
        return dict(descriptor) if descriptor is not None else None

    def read(self, descriptor: Mapping[str, Any]) -> bytes:
        digest = descriptor.get("image_sha256")
        expected = self._descriptors.get(str(digest))
        if expected is None or dict(descriptor) != expected:
            raise ValueError("archive names an image origin not admitted by run99")
        path = _root_path(expected["path"])
        if expected["kind"] == "historical_file":
            data = path.read_bytes()
            if _sha256(data) != expected["file_sha256"]:
                raise ValueError("historical image file hash mismatch")
        else:
            if self._stream_lines is None:
                container = path.read_bytes()
                if len(container) != expected["container_bytes"]:
                    raise ValueError("historical gzip container size mismatch")
                if _sha256(container) != expected["container_sha256"]:
                    raise ValueError("historical gzip container hash mismatch")
                with gzip.open(io.BytesIO(container), "rt", encoding="utf-8") as stream:
                    self._stream_lines = [None, *(json.loads(line) for line in stream)]
            line = expected["line"]
            if isinstance(line, bool) or not isinstance(line, int) or line <= 0:
                raise ValueError("historical stream line is invalid")
            try:
                block = _at_path(self._stream_lines[line], expected["json_path"])
                encoded = block["source"]["data"]
                data = base64.b64decode(encoded, validate=True)
            except (IndexError, KeyError, TypeError, ValueError) as error:
                raise ValueError("historical stream image cannot be resolved") from error
        if len(data) != expected["byte_size"] or _sha256(data) != digest:
            raise ValueError("historical image bytes differ from their fixture identity")
        return data


def _looks_like_image(data: bytes) -> bool:
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or data.startswith((b"GIF87a", b"GIF89a", b"BM", b"II*\x00", b"MM\x00*"))
        or (len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


def _data_url_payload(value: str) -> str | None:
    if not value.startswith("data:image/") or ";base64," not in value:
        return None
    return value.split(",", 1)[1]


def _collect_image_payloads(value: Any, found: Counter[str]) -> None:
    if isinstance(value, str):
        payload = _data_url_payload(value)
        if payload is not None:
            found[payload] += 1
        return
    if isinstance(value, list):
        for child in value:
            _collect_image_payloads(child, found)
        return
    if not isinstance(value, dict):
        return
    block_type = value.get("type")
    if block_type == "image" and isinstance(value.get("data"), str):
        found[value["data"]] += 1
    source = value.get("source")
    if (
        block_type == "image"
        and isinstance(source, dict)
        and source.get("type") == "base64"
        and str(source.get("media_type", "")).startswith("image/")
        and isinstance(source.get("data"), str)
    ):
        found[source["data"]] += 1
    for child in value.values():
        _collect_image_payloads(child, found)


def _image_payloads(data: bytes) -> Counter[str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return Counter()
    values: list[Any]
    try:
        values = [json.loads(text)]
    except json.JSONDecodeError:
        values = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError:
                return Counter()
    found: Counter[str] = Counter()
    for value in values:
        _collect_image_payloads(value, found)
    return found


def _marker(digest: str) -> str:
    return f"{MARKER_PREFIX}{digest}__"


def _source_files(source: Path) -> tuple[list[Path], list[dict[str, str]]]:
    files: list[Path] = []
    exclusions: list[dict[str, str]] = []
    for directory, names, filenames in os.walk(source, topdown=True, followlinks=False):
        parent = Path(directory)
        retained_names = []
        for name in sorted(names):
            path = parent / name
            relative = path.relative_to(source).as_posix()
            if path.is_symlink():
                raise ValueError(f"evidence source contains a directory symlink: {relative}")
            if name == ".harness_tmp":
                exclusions.append({"path": relative, "reason": "transport temporary directory"})
            else:
                retained_names.append(name)
        names[:] = retained_names
        for name in sorted(filenames):
            path = parent / name
            relative = path.relative_to(source).as_posix()
            if path.is_symlink():
                raise ValueError(f"evidence source contains a file symlink: {relative}")
            mode = path.stat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError(f"evidence source contains a non-regular file: {relative}")
            if name == "writer.lock":
                exclusions.append({"path": relative, "reason": "EventStore process lock"})
            else:
                files.append(path)
    return sorted(files, key=lambda path: path.relative_to(source).as_posix()), sorted(
        exclusions, key=lambda item: item["path"]
    )


def _write_archive(path: Path, members: Mapping[str, bytes]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    for name, data in sorted(members.items()):
                        info = tarfile.TarInfo(name)
                        info.size = len(data)
                        info.mtime = 0
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        info.mode = 0o644
                        archive.addfile(info, io.BytesIO(data))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def pack(source: Path, archive_path: Path) -> dict[str, Any]:
    """Pack a directory and return its manifest without changing the source."""

    source = _checked_root_path(Path(source), what="evidence source", must_exist=True)
    if not source.is_dir():
        raise ValueError("evidence source must be a directory")
    archive_path = _checked_root_path(
        Path(archive_path).parent, what="archive parent", must_exist=True
    ) / Path(archive_path).name
    if archive_path.is_relative_to(source):
        raise ValueError("compact archive cannot be written inside its evidence source")

    historical = _HistoricalImages()
    files, exclusions = _source_files(source)
    members: dict[str, bytes] = {}
    file_manifest: dict[str, dict[str, Any]] = {}
    image_manifest: dict[str, dict[str, Any]] = {}

    def register_image(raw: bytes) -> str:
        digest = _sha256(raw)
        if digest in image_manifest:
            return digest
        descriptor = historical.descriptor(digest)
        if descriptor is not None:
            if historical.read(descriptor) != raw:
                raise ValueError("historical image hash collision")
            image_manifest[digest] = descriptor
        else:
            member = f"images/{digest}"
            members[member] = raw
            image_manifest[digest] = {
                "kind": "embedded",
                "member": member,
                "image_sha256": digest,
                "byte_size": len(raw),
            }
        return digest

    for path in files:
        relative = path.relative_to(source).as_posix()
        _safe_relative(relative, what="source member")
        data = path.read_bytes()
        digest = _sha256(data)
        relative_parts = PurePosixPath(relative).parts
        if (
            len(relative_parts) >= 2
            and relative_parts[-2] == "blobs"
            and _HEX_RE.fullmatch(path.name)
            and path.name != digest
        ):
            raise ValueError(f"content-addressed blob has the wrong hash: {relative}")
        if MARKER_PREFIX.encode("ascii") in data:
            raise ValueError(f"source collides with the reserved image marker: {relative}")
        if _looks_like_image(data):
            image_digest = register_image(data)
            file_manifest[relative] = {
                "kind": "image",
                "image_sha256": image_digest,
                "byte_size": len(data),
                "sha256": digest,
            }
            continue

        payloads = _image_payloads(data)
        if payloads:
            template = data
            substitutions = []
            decoded: dict[str, tuple[str, bytes]] = {}
            for payload in payloads:
                try:
                    raw = base64.b64decode(payload, validate=True)
                except (ValueError, TypeError) as error:
                    raise ValueError(f"invalid base64 image in {relative}") from error
                if base64.b64encode(raw).decode("ascii") != payload:
                    raise ValueError(f"non-canonical base64 image in {relative}")
                decoded[payload] = (register_image(raw), raw)
            for payload in sorted(decoded, key=len, reverse=True):
                image_digest, _ = decoded[payload]
                marker = _marker(image_digest)
                count = template.count(payload.encode("ascii"))
                if count < payloads[payload]:
                    raise ValueError(f"cannot locate every encoded image in {relative}")
                template = template.replace(payload.encode("ascii"), marker.encode("ascii"))
                substitutions.append(
                    {"marker": marker, "image_sha256": image_digest, "count": count}
                )
            template_digest = _sha256(template)
            member = f"objects/{template_digest}"
            members.setdefault(member, template)
            file_manifest[relative] = {
                "kind": "template",
                "object": member,
                "template_sha256": template_digest,
                "template_bytes": len(template),
                "substitutions": sorted(substitutions, key=lambda item: item["marker"]),
                "byte_size": len(data),
                "sha256": digest,
            }
        else:
            member = f"objects/{digest}"
            members.setdefault(member, data)
            file_manifest[relative] = {
                "kind": "stored",
                "object": member,
                "byte_size": len(data),
                "sha256": digest,
            }

    manifest = {
        "schema": SCHEMA,
        "files": file_manifest,
        "images": image_manifest,
        "exclusions": exclusions,
        "policy": {
            "historical_images": "repository locator plus checked file/container and image sha256",
            "embedded_images": "one member per unique sha256",
            "excluded": ["writer.lock", ".harness_tmp"],
        },
    }
    members[MANIFEST_MEMBER] = _json_bytes(manifest) + b"\n"
    _write_archive(archive_path, members)
    # Read it back through the public verifier before reporting success.
    read_archive(archive_path)
    return manifest


def _archive_members(path: Path) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            for member in archive.getmembers():
                _safe_relative(member.name, what="archive member")
                if not member.isfile():
                    raise ValueError("compact archive contains a non-file member")
                if member.name in members:
                    raise ValueError("compact archive contains a duplicate member")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("compact archive member cannot be read")
                members[member.name] = stream.read()
    except (tarfile.TarError, EOFError, OSError) as error:
        raise ValueError("invalid compact evidence archive") from error
    return members


class CompactArchive(Mapping[str, bytes]):
    """Verified, extraction-free mapping from source-relative paths to bytes."""

    def __init__(self, archive_path: Path) -> None:
        self.archive_path = archive_path
        self._members = _archive_members(archive_path)
        try:
            self.manifest = json.loads(self._members[MANIFEST_MEMBER])
        except (KeyError, json.JSONDecodeError, UnicodeError) as error:
            raise ValueError("compact archive has no valid manifest") from error
        if self.manifest.get("schema") != SCHEMA:
            raise ValueError("unsupported compact evidence schema")
        if not isinstance(self.manifest.get("files"), dict) or not isinstance(
            self.manifest.get("images"), dict
        ):
            raise ValueError("compact archive manifest tables are invalid")
        self._historical = _HistoricalImages()
        self._image_cache: dict[str, bytes] = {}
        self._validate()

    def _image(self, digest: str) -> bytes:
        if digest in self._image_cache:
            return self._image_cache[digest]
        if not _HEX_RE.fullmatch(digest):
            raise ValueError("manifest has an invalid image hash")
        try:
            descriptor = self.manifest["images"][digest]
        except KeyError as error:
            raise ValueError("file references an image missing from the manifest") from error
        if descriptor.get("image_sha256") != digest:
            raise ValueError("image manifest key differs from its hash")
        if descriptor.get("kind") == "embedded":
            expected_member = f"images/{digest}"
            if descriptor.get("member") != expected_member:
                raise ValueError("embedded image member is not content-addressed")
            try:
                data = self._members[expected_member]
            except KeyError as error:
                raise ValueError("embedded image member is missing") from error
        elif descriptor.get("kind") in {"historical_file", "historical_stream"}:
            data = self._historical.read(descriptor)
        else:
            raise ValueError("image manifest has an unsupported origin")
        if len(data) != descriptor.get("byte_size") or _sha256(data) != digest:
            raise ValueError("image bytes do not match their manifest")
        self._image_cache[digest] = data
        return data

    def _reconstruct(self, relative: str) -> bytes:
        entry = self.manifest["files"][relative]
        kind = entry.get("kind")
        if kind == "image":
            data = self._image(entry.get("image_sha256", ""))
        elif kind in {"stored", "template"}:
            member = entry.get("object")
            if not isinstance(member, str):
                raise ValueError("file object member is invalid")
            try:
                data = self._members[member]
            except KeyError as error:
                raise ValueError("file object member is missing") from error
            object_digest = member.removeprefix("objects/")
            if member != f"objects/{object_digest}" or not _HEX_RE.fullmatch(object_digest):
                raise ValueError("file object is not content-addressed")
            if _sha256(data) != object_digest:
                raise ValueError("file object hash mismatch")
            if kind == "template":
                if entry.get("template_sha256") != object_digest or entry.get(
                    "template_bytes"
                ) != len(data):
                    raise ValueError("template identity mismatch")
                substitutions = entry.get("substitutions")
                if not isinstance(substitutions, list):
                    raise ValueError("template substitutions are invalid")
                declared: Counter[bytes] = Counter()
                for substitution in substitutions:
                    digest = substitution.get("image_sha256", "")
                    marker = _marker(digest)
                    if substitution.get("marker") != marker:
                        raise ValueError("template marker differs from its image hash")
                    encoded_marker = marker.encode("ascii")
                    count = substitution.get("count")
                    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
                        raise ValueError("template marker count is invalid")
                    declared[encoded_marker] += count
                    if data.count(encoded_marker) != count:
                        raise ValueError("template marker count mismatch")
                    payload = base64.b64encode(self._image(digest))
                    data = data.replace(encoded_marker, payload)
                observed = Counter(
                    match.group(0) for match in _MARKER_RE.finditer(self._members[member])
                )
                if observed != declared or MARKER_PREFIX.encode("ascii") in data:
                    raise ValueError("template contains an undeclared or colliding marker")
        else:
            raise ValueError("file manifest has an unsupported storage kind")
        if len(data) != entry.get("byte_size") or _sha256(data) != entry.get("sha256"):
            raise ValueError("reconstructed file differs from its original hash")
        return data

    def _validate(self) -> None:
        expected_members = {MANIFEST_MEMBER}
        files = self.manifest["files"]
        for relative, entry in files.items():
            _safe_relative(relative, what="manifest file path")
            if not isinstance(entry, dict):
                raise ValueError("file manifest entry is invalid")
            if entry.get("kind") in {"stored", "template"}:
                expected_members.add(entry.get("object"))
        for digest, descriptor in self.manifest["images"].items():
            if not isinstance(descriptor, dict):
                raise ValueError("image manifest entry is invalid")
            if descriptor.get("kind") == "embedded":
                expected_members.add(f"images/{digest}")
        if not all(isinstance(name, str) for name in expected_members):
            raise ValueError("manifest contains a non-string archive member")
        if set(self._members) != expected_members:
            raise ValueError("archive members differ from the manifest")
        for digest in self.manifest["images"]:
            self._image(digest)
        exclusions = self.manifest.get("exclusions")
        if not isinstance(exclusions, list):
            raise ValueError("archive exclusion record is invalid")
        for exclusion in exclusions:
            if not isinstance(exclusion, dict):
                raise ValueError("archive exclusion entry is invalid")
            _safe_relative(exclusion.get("path", ""), what="excluded source path")
        # Eager verification makes read_archive itself reject tampering; bytes
        # remain reconstructed on demand for callers after this pass.
        for relative in files:
            self._reconstruct(relative)

    def __getitem__(self, relative: str) -> bytes:
        if relative not in self.manifest["files"]:
            raise KeyError(relative)
        return self._reconstruct(relative)

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self.manifest["files"]))

    def __len__(self) -> int:
        return len(self.manifest["files"])


def read_archive(archive_path: Path) -> Mapping[str, bytes]:
    """Open and verify a compact archive without extracting it to disk."""

    path = _checked_root_path(Path(archive_path), what="compact archive", must_exist=True)
    if not path.is_file():
        raise ValueError("compact archive must be a file")
    return CompactArchive(path)
