"""Losslessly compact and restore stage-3 run evidence.

Repository images are retained by checked path and SHA-256 identity. Images
created by a run are stored once by content hash, including images repeated as
base64 in JSON, JSONL, or content-addressed blobs. Every reconstructed file is
checked against its original byte count and SHA-256 before it is exposed.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from src.utils import file_lock
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
ROLE_MANIFEST = HERE / "role_cases/manifest.json"
STAGE1_PLAN = (
    ROOT
    / "AI_agent/logs/experiments/2026-10-02_harness_stage1/offline_inputs/plan.png"
)
SCHEMA = "harness-stage3-evidence-pack/v1"
MANIFEST_MEMBER = "manifest.json"
MARKER_PREFIX = "__STAGE3_IMAGE_SHA256_"
_MARKER_RE = re.compile(rb"__STAGE3_IMAGE_SHA256_([0-9a-f]{64})__")
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


def _safe_root_name(value: str) -> str:
    path = _safe_relative(value, what="source root name")
    if len(path.parts) != 1:
        raise ValueError("source root name must be one path component")
    return value


def _inside_root(path: Path, *, what: str, must_exist: bool = True) -> Path:
    resolved = path.resolve(strict=must_exist)
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"{what} must stay inside this worktree")
    return resolved


def _root_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _repository_path(relative: str) -> Path:
    pure = _safe_relative(relative, what="repository reference")
    return _inside_root(ROOT / Path(*pure.parts), what="repository reference")


def _looks_like_image(data: bytes) -> bool:
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or data.startswith((b"GIF87a", b"GIF89a", b"BM", b"II*\x00", b"MM\x00*"))
        or (len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


def _png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    if data[12:16] != b"IHDR":
        raise ValueError("PNG image has no IHDR at the canonical location")
    width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        raise ValueError("PNG image has invalid dimensions")
    return width, height


def _read_stable(path: Path) -> tuple[bytes, os.stat_result]:
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"evidence member is not a regular file: {path}")
    data = path.read_bytes()
    after = path.stat()
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or len(data) != after.st_size:
        raise ValueError(f"evidence file changed while it was read: {path}")
    return data, after


class ReferenceCatalog:
    """Verified repository images eligible for path-only archive references."""

    def __init__(self) -> None:
        self.descriptors: dict[str, dict[str, Any]] = {}

    def add(
        self,
        path: Path,
        *,
        admission: str,
        declared_sha256: str | None = None,
        declared_size: tuple[int, int] | None = None,
        manifest_path: Path | None = None,
    ) -> str:
        resolved = _inside_root(path, what="image reference")
        if resolved.is_symlink():
            raise ValueError("image references cannot be symlinks")
        data, _ = _read_stable(resolved)
        if not _looks_like_image(data):
            raise ValueError(f"repository reference is not a recognized image: {resolved}")
        digest = _sha256(data)
        if declared_sha256 is not None and digest != declared_sha256:
            raise ValueError(f"repository image differs from declared hash: {resolved}")
        dimensions = _png_size(data)
        if declared_size is not None and dimensions != declared_size:
            raise ValueError(f"repository image differs from declared dimensions: {resolved}")
        descriptor: dict[str, Any] = {
            "kind": "repository_reference",
            "admission": admission,
            "path": _root_relative(resolved),
            "image_sha256": digest,
            "file_sha256": digest,
            "byte_size": len(data),
        }
        if dimensions is not None:
            descriptor["pixel_size"] = list(dimensions)
        if manifest_path is not None:
            checked_manifest = _inside_root(manifest_path, what="reference manifest")
            manifest_bytes, _ = _read_stable(checked_manifest)
            descriptor.update(
                manifest_path=_root_relative(checked_manifest),
                manifest_sha256=_sha256(manifest_bytes),
            )
        existing = self.descriptors.get(digest)
        priority = {"role_cases_manifest": 0, "stage1_offline_input": 1}
        descriptor_key = (priority.get(admission, 2), descriptor["path"])
        existing_key = (
            priority.get(existing.get("admission"), 2), existing["path"]
        ) if existing is not None else None
        if existing_key is None or descriptor_key < existing_key:
            self.descriptors[digest] = descriptor
        return digest

    def add_path(self, path: Path, *, admission: str = "explicit_reference") -> None:
        resolved = _inside_root(path, what="explicit image reference")
        if resolved.is_dir():
            candidates = sorted(item for item in resolved.rglob("*") if item.is_file())
            if not candidates:
                raise ValueError("explicit reference directory has no files")
            admitted = 0
            for candidate in candidates:
                data, _ = _read_stable(candidate)
                if _looks_like_image(data):
                    self.add(candidate, admission=admission)
                    admitted += 1
            if not admitted:
                raise ValueError("explicit reference directory has no recognized images")
        else:
            self.add(resolved, admission=admission)

    @classmethod
    def defaults(cls, extra: Iterable[Path] = ()) -> ReferenceCatalog:
        catalog = cls()
        manifest = json.loads(ROLE_MANIFEST.read_bytes())
        cases = manifest.get("cases")
        if not isinstance(cases, list):
            raise ValueError("role-case manifest has no case list")
        for case in cases:
            for image in case.get("images", ()):
                dimensions = (image.get("width_px"), image.get("height_px"))
                if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
                       for value in dimensions):
                    raise ValueError("role-case image dimensions are invalid")
                catalog.add(
                    ROOT / image["path"],
                    admission="role_cases_manifest",
                    declared_sha256=image["sha256"],
                    declared_size=dimensions,
                    manifest_path=ROLE_MANIFEST,
                )
        catalog.add(STAGE1_PLAN, admission="stage1_offline_input")
        for path in extra:
            catalog.add_path(Path(path))
        return catalog

    def descriptor(self, digest: str) -> dict[str, Any] | None:
        value = self.descriptors.get(digest)
        return dict(value) if value is not None else None


def _read_repository_image(descriptor: Mapping[str, Any]) -> bytes:
    if descriptor.get("kind") != "repository_reference":
        raise ValueError("image descriptor is not a repository reference")
    path = _repository_path(str(descriptor.get("path", "")))
    data, _ = _read_stable(path)
    digest = descriptor.get("image_sha256")
    if (
        not isinstance(digest, str)
        or not _HEX_RE.fullmatch(digest)
        or descriptor.get("file_sha256") != digest
        or _sha256(data) != digest
        or len(data) != descriptor.get("byte_size")
    ):
        raise ValueError("repository image no longer matches its archive identity")
    if not _looks_like_image(data):
        raise ValueError("repository reference is no longer a recognized image")
    dimensions = _png_size(data)
    if "pixel_size" in descriptor and list(dimensions or ()) != descriptor["pixel_size"]:
        raise ValueError("repository image dimensions no longer match")
    if "manifest_path" in descriptor:
        manifest = _repository_path(str(descriptor["manifest_path"]))
        manifest_bytes, _ = _read_stable(manifest)
        if _sha256(manifest_bytes) != descriptor.get("manifest_sha256"):
            raise ValueError("repository image admission manifest changed")
    return data


def _data_url_payload(value: str) -> str | None:
    if value.startswith("data:image/") and ";base64," in value:
        return value.split(",", 1)[1]
    return None


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


def _source_inventory(source: Path) -> tuple[list[Path], list[Path]]:
    directories: list[Path] = [source]
    files: list[Path] = []
    for directory, names, filenames in os.walk(source, topdown=True, followlinks=False):
        parent = Path(directory)
        for name in sorted(names):
            child = parent / name
            if child.is_symlink():
                raise ValueError(f"evidence source contains a directory symlink: {child}")
            directories.append(child)
        for name in sorted(filenames):
            child = parent / name
            if child.is_symlink():
                raise ValueError(f"evidence source contains a file symlink: {child}")
            if not child.is_file():
                raise ValueError(f"evidence source contains a non-regular file: {child}")
            if name == "writer.lock":
                with child.open("a+b") as lock:
                    try:
                        file_lock.flock(lock, file_lock.LOCK_EX | file_lock.LOCK_NB)
                    except BlockingIOError as error:
                        raise ValueError(f"evidence source is still active: {source}") from error
                    finally:
                        try:
                            file_lock.flock(lock, file_lock.LOCK_UN)
                        except OSError:
                            pass
            files.append(child)
    return sorted(set(directories)), sorted(files)


def _write_archive(path: Path, members: Mapping[str, bytes]) -> None:
    if not path.name.endswith(".tar.xz"):
        raise ValueError("stage-3 evidence archive must end in .tar.xz")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as raw:
            with lzma.LZMAFile(raw, mode="wb", format=lzma.FORMAT_XZ, preset=6) as compressed:
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


def pack(
    sources: Mapping[str, Path],
    archive_path: Path,
    *,
    references: Iterable[Path] = (),
    include_default_references: bool = True,
) -> dict[str, Any]:
    """Pack multiple source directories without modifying them."""

    if not sources:
        raise ValueError("at least one evidence source is required")
    parent = _inside_root(Path(archive_path).parent, what="archive parent")
    archive_path = parent / Path(archive_path).name
    catalog = (
        ReferenceCatalog.defaults(references)
        if include_default_references
        else ReferenceCatalog()
    )
    if not include_default_references:
        for reference in references:
            catalog.add_path(Path(reference))

    checked_sources: dict[str, Path] = {}
    for name, source in sources.items():
        _safe_root_name(name)
        if name in checked_sources:
            raise ValueError(f"duplicate source root name: {name}")
        checked = _inside_root(Path(source), what=f"evidence source {name}")
        if not checked.is_dir():
            raise ValueError(f"evidence source is not a directory: {checked}")
        if checked == ROOT:
            raise ValueError("the whole worktree cannot be used as one evidence source")
        if archive_path.is_relative_to(checked):
            raise ValueError("archive cannot be written inside an evidence source")
        checked_sources[name] = checked

    members: dict[str, bytes] = {}
    file_manifest: dict[str, dict[str, Any]] = {}
    image_manifest: dict[str, dict[str, Any]] = {}
    directory_manifest: dict[str, dict[str, int]] = {}
    root_manifest: dict[str, dict[str, str]] = {}

    def register_image(raw: bytes) -> str:
        digest = _sha256(raw)
        if digest in image_manifest:
            return digest
        descriptor = catalog.descriptor(digest)
        if descriptor is not None:
            if _read_repository_image(descriptor) != raw:
                raise ValueError("repository image hash collision")
            image_manifest[digest] = descriptor
        else:
            member = f"images/{digest}"
            members[member] = raw
            descriptor = {
                "kind": "embedded",
                "member": member,
                "image_sha256": digest,
                "byte_size": len(raw),
            }
            dimensions = _png_size(raw)
            if dimensions is not None:
                descriptor["pixel_size"] = list(dimensions)
            image_manifest[digest] = descriptor
        return digest

    for root_name, source in sorted(checked_sources.items()):
        root_manifest[root_name] = {"source_path": _root_relative(source)}
        directories, files = _source_inventory(source)
        for directory in directories:
            relative = directory.relative_to(source).as_posix()
            logical = root_name if relative == "." else f"{root_name}/{relative}"
            mode = stat.S_IMODE(directory.stat().st_mode)
            directory_manifest[logical] = {"mode": mode}
        for path in files:
            relative = path.relative_to(source).as_posix()
            _safe_relative(relative, what="source member")
            logical = f"{root_name}/{relative}"
            data, metadata = _read_stable(path)
            digest = _sha256(data)
            parts = PurePosixPath(relative).parts
            if (
                len(parts) >= 2
                and parts[-2] == "blobs"
                and _HEX_RE.fullmatch(path.name)
                and path.name != digest
            ):
                raise ValueError(f"content-addressed blob has the wrong hash: {logical}")
            if MARKER_PREFIX.encode("ascii") in data:
                raise ValueError(f"source collides with reserved image marker: {logical}")
            common = {
                "byte_size": len(data),
                "sha256": digest,
                "mode": stat.S_IMODE(metadata.st_mode),
            }
            if _looks_like_image(data):
                file_manifest[logical] = {
                    **common,
                    "kind": "image",
                    "image_sha256": register_image(data),
                }
                continue

            payloads = _image_payloads(data)
            if not payloads:
                member = f"objects/{digest}"
                members.setdefault(member, data)
                file_manifest[logical] = {**common, "kind": "stored", "object": member}
                continue

            template = data
            decoded: dict[str, str] = {}
            for payload in payloads:
                try:
                    raw = base64.b64decode(payload, validate=True)
                except (TypeError, ValueError) as error:
                    raise ValueError(f"invalid base64 image in {logical}") from error
                if base64.b64encode(raw).decode("ascii") != payload:
                    raise ValueError(f"non-canonical base64 image in {logical}")
                if not _looks_like_image(raw):
                    raise ValueError(f"declared image payload is not a recognized image: {logical}")
                decoded[payload] = register_image(raw)
            substitutions = []
            for payload in sorted(decoded, key=len, reverse=True):
                marker = _marker(decoded[payload])
                count = template.count(payload.encode("ascii"))
                if count < payloads[payload]:
                    raise ValueError(f"cannot locate every encoded image in {logical}")
                template = template.replace(payload.encode("ascii"), marker.encode("ascii"))
                substitutions.append(
                    {"marker": marker, "image_sha256": decoded[payload], "count": count}
                )
            template_digest = _sha256(template)
            member = f"objects/{template_digest}"
            members.setdefault(member, template)
            file_manifest[logical] = {
                **common,
                "kind": "template",
                "object": member,
                "template_sha256": template_digest,
                "template_bytes": len(template),
                "substitutions": sorted(substitutions, key=lambda item: item["marker"]),
            }

    manifest = {
        "schema": SCHEMA,
        "roots": root_manifest,
        "directories": directory_manifest,
        "files": file_manifest,
        "images": image_manifest,
        "policy": {
            "repository_images": "checked worktree path plus original SHA-256; bytes omitted",
            "derived_images": "one embedded archive member per unique SHA-256",
            "inline_images": "base64 replaced by reversible SHA-256 markers",
            "source_files": "all regular files retained, including writer.lock",
        },
    }
    members[MANIFEST_MEMBER] = _json_bytes(manifest) + b"\n"
    _write_archive(archive_path, members)
    read_archive(archive_path)
    return manifest


def _archive_members(path: Path) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    try:
        with tarfile.open(path, mode="r:xz") as archive:
            for member in archive.getmembers():
                _safe_relative(member.name, what="archive member")
                if not member.isfile():
                    raise ValueError("evidence archive contains a non-file member")
                if member.name in members:
                    raise ValueError("evidence archive contains a duplicate member")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("evidence archive member cannot be read")
                members[member.name] = stream.read()
    except (tarfile.TarError, lzma.LZMAError, EOFError, OSError) as error:
        raise ValueError("invalid stage-3 evidence archive") from error
    return members


class EvidenceArchive(Mapping[str, bytes]):
    """Verified mapping from ``root-name/relative-path`` to original bytes."""

    def __init__(self, archive_path: Path) -> None:
        self.archive_path = _inside_root(archive_path, what="evidence archive")
        self._members = _archive_members(self.archive_path)
        try:
            self.manifest = json.loads(self._members[MANIFEST_MEMBER])
        except (KeyError, json.JSONDecodeError, UnicodeError) as error:
            raise ValueError("evidence archive has no valid manifest") from error
        if self.manifest.get("schema") != SCHEMA:
            raise ValueError("unsupported stage-3 evidence archive schema")
        for table in ("roots", "directories", "files", "images"):
            if not isinstance(self.manifest.get(table), dict):
                raise ValueError(f"archive manifest {table} table is invalid")
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
            raise ValueError("file references an unmanifested image") from error
        if not isinstance(descriptor, dict) or descriptor.get("image_sha256") != digest:
            raise ValueError("image manifest key differs from its descriptor")
        if descriptor.get("kind") == "embedded":
            member = f"images/{digest}"
            if descriptor.get("member") != member or member not in self._members:
                raise ValueError("embedded image member is missing or misnamed")
            data = self._members[member]
        elif descriptor.get("kind") == "repository_reference":
            data = _read_repository_image(descriptor)
        else:
            raise ValueError("image manifest has an unsupported origin")
        if len(data) != descriptor.get("byte_size") or _sha256(data) != digest:
            raise ValueError("image bytes do not match their archive identity")
        self._image_cache[digest] = data
        return data

    def _reconstruct(self, logical: str) -> bytes:
        entry = self.manifest["files"][logical]
        kind = entry.get("kind")
        if kind == "image":
            data = self._image(str(entry.get("image_sha256", "")))
        elif kind in {"stored", "template"}:
            member = entry.get("object")
            if not isinstance(member, str) or not member.startswith("objects/"):
                raise ValueError("file object member is invalid")
            digest = member.removeprefix("objects/")
            if not _HEX_RE.fullmatch(digest) or member not in self._members:
                raise ValueError("file object member is missing or not content-addressed")
            data = self._members[member]
            if _sha256(data) != digest:
                raise ValueError("file object hash mismatch")
            if kind == "template":
                if entry.get("template_sha256") != digest or entry.get("template_bytes") != len(data):
                    raise ValueError("template identity mismatch")
                substitutions = entry.get("substitutions")
                if not isinstance(substitutions, list):
                    raise ValueError("template substitutions are invalid")
                original_template = data
                declared: Counter[bytes] = Counter()
                for substitution in substitutions:
                    image_digest = str(substitution.get("image_sha256", ""))
                    marker = _marker(image_digest)
                    count = substitution.get("count")
                    if substitution.get("marker") != marker:
                        raise ValueError("template marker differs from its image hash")
                    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
                        raise ValueError("template marker count is invalid")
                    encoded = marker.encode("ascii")
                    declared[encoded] += count
                    if original_template.count(encoded) != count:
                        raise ValueError("template marker count mismatch")
                    data = data.replace(encoded, base64.b64encode(self._image(image_digest)))
                observed = Counter(match.group(0) for match in _MARKER_RE.finditer(original_template))
                if observed != declared or MARKER_PREFIX.encode("ascii") in data:
                    raise ValueError("template has undeclared or colliding markers")
        else:
            raise ValueError("file manifest has an unsupported storage kind")
        if len(data) != entry.get("byte_size") or _sha256(data) != entry.get("sha256"):
            raise ValueError("reconstructed file differs from its original SHA-256")
        return data

    def _validate(self) -> None:
        roots = self.manifest["roots"]
        if not roots:
            raise ValueError("archive has no source roots")
        for root_name, descriptor in roots.items():
            _safe_root_name(root_name)
            if not isinstance(descriptor, dict):
                raise ValueError("source root descriptor is invalid")
            _safe_relative(str(descriptor.get("source_path", "")), what="source root path")
            if root_name not in self.manifest["directories"]:
                raise ValueError("source root directory is missing from the manifest")
        for logical, descriptor in self.manifest["directories"].items():
            path = _safe_relative(logical, what="directory path")
            if path.parts[0] not in roots or not isinstance(descriptor, dict):
                raise ValueError("directory belongs to an unknown source root")
            mode = descriptor.get("mode")
            if isinstance(mode, bool) or not isinstance(mode, int) or not 0 <= mode <= 0o7777:
                raise ValueError("directory mode is invalid")
            if len(path.parts) > 1 and path.parent.as_posix() not in self.manifest["directories"]:
                raise ValueError("directory parent is missing from the manifest")

        expected_members = {MANIFEST_MEMBER}
        referenced_images: set[str] = set()
        for logical, entry in self.manifest["files"].items():
            path = _safe_relative(logical, what="file path")
            if path.parts[0] not in roots or len(path.parts) < 2 or not isinstance(entry, dict):
                raise ValueError("file belongs to an unknown source root")
            mode = entry.get("mode")
            if isinstance(mode, bool) or not isinstance(mode, int) or not 0 <= mode <= 0o7777:
                raise ValueError("file mode is invalid")
            if path.parent.as_posix() not in self.manifest["directories"]:
                raise ValueError("file parent is missing from the directory manifest")
            if entry.get("kind") == "image":
                referenced_images.add(str(entry.get("image_sha256", "")))
            elif entry.get("kind") == "template":
                substitutions = entry.get("substitutions")
                if not isinstance(substitutions, list):
                    raise ValueError("template substitutions are invalid")
                referenced_images.update(
                    str(substitution.get("image_sha256", ""))
                    for substitution in substitutions
                    if isinstance(substitution, dict)
                )
            if entry.get("kind") in {"stored", "template"}:
                expected_members.add(entry.get("object"))
        for digest, descriptor in self.manifest["images"].items():
            if not isinstance(descriptor, dict):
                raise ValueError("image descriptor is invalid")
            if descriptor.get("kind") == "embedded":
                expected_members.add(f"images/{digest}")
        if referenced_images != set(self.manifest["images"]):
            raise ValueError("image manifest differs from images referenced by files")
        if not all(isinstance(member, str) for member in expected_members):
            raise ValueError("archive manifest contains a non-string member")
        if set(self._members) != expected_members:
            raise ValueError("archive members differ from its manifest")
        for digest in self.manifest["images"]:
            self._image(digest)
        for logical in self.manifest["files"]:
            self._reconstruct(logical)

    def __getitem__(self, logical: str) -> bytes:
        if logical not in self.manifest["files"]:
            raise KeyError(logical)
        return self._reconstruct(logical)

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self.manifest["files"]))

    def __len__(self) -> int:
        return len(self.manifest["files"])


def read_archive(archive_path: Path) -> EvidenceArchive:
    """Open and eagerly verify an archive without extracting it."""

    path = _inside_root(Path(archive_path), what="evidence archive")
    if not path.is_file():
        raise ValueError("evidence archive must be a file")
    return EvidenceArchive(path)


def restore(archive_path: Path, output: Path) -> dict[str, Any]:
    """Restore all logical source roots beneath a new worktree directory."""

    archive = read_archive(archive_path)
    output = _inside_root(Path(output).parent, what="restore parent") / Path(output).name
    if output.exists():
        raise ValueError("restore output must not already exist")
    output.mkdir()
    directories = sorted(
        archive.manifest["directories"], key=lambda value: len(PurePosixPath(value).parts)
    )
    for logical in directories:
        target = output / Path(*PurePosixPath(logical).parts)
        target.mkdir(parents=True, exist_ok=True)
        target.chmod(archive.manifest["directories"][logical]["mode"])
    restored: dict[str, str] = {}
    for logical in archive:
        target = output / Path(*PurePosixPath(logical).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = archive[logical]
        target.write_bytes(data)
        target.chmod(archive.manifest["files"][logical]["mode"])
        digest = _sha256(target.read_bytes())
        if digest != archive.manifest["files"][logical]["sha256"]:
            raise ValueError("restored file failed its original SHA-256 check")
        restored[logical] = digest
    return {
        "schema": SCHEMA,
        "archive_sha256": _sha256(Path(archive_path).read_bytes()),
        "output": _root_relative(output),
        "root_count": len(archive.manifest["roots"]),
        "file_count": len(restored),
        "files": restored,
    }


def _cli_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _source_argument(value: str) -> tuple[str, Path]:
    if "=" in value:
        name, raw_path = value.split("=", 1)
    else:
        raw_path = value
        name = Path(raw_path).name
    return _safe_root_name(name), _cli_path(raw_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack_command = commands.add_parser("pack", help="pack one or more run directories")
    pack_command.add_argument("--archive", required=True)
    pack_command.add_argument("--source", action="append", required=True,
                              help="NAME=PATH; NAME defaults to PATH basename")
    pack_command.add_argument("--reference", action="append", default=[],
                              help="extra repository image file or directory")
    pack_command.add_argument("--no-default-references", action="store_true")
    verify_command = commands.add_parser("verify", help="eagerly verify an archive")
    verify_command.add_argument("--archive", required=True)
    restore_command = commands.add_parser("restore", help="restore into a new directory")
    restore_command.add_argument("--archive", required=True)
    restore_command.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    if args.command == "pack":
        sources: dict[str, Path] = {}
        for value in args.source:
            name, path = _source_argument(value)
            if name in sources:
                raise ValueError(f"duplicate source root name: {name}")
            sources[name] = path
        manifest = pack(
            sources,
            _cli_path(args.archive),
            references=(_cli_path(value) for value in args.reference),
            include_default_references=not args.no_default_references,
        )
        result = {
            "archive": _root_relative(_inside_root(_cli_path(args.archive), what="archive")),
            "roots": len(manifest["roots"]),
            "files": len(manifest["files"]),
            "images": len(manifest["images"]),
        }
    elif args.command == "verify":
        archive = read_archive(_cli_path(args.archive))
        result = {
            "archive_sha256": _sha256(archive.archive_path.read_bytes()),
            "roots": len(archive.manifest["roots"]),
            "files": len(archive),
            "images": len(archive.manifest["images"]),
        }
    else:
        result = restore(_cli_path(args.archive), _cli_path(args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
