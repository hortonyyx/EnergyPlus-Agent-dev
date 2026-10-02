"""Small lossless and tamper checks for compact stage-2 evidence."""

from __future__ import annotations

import base64
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile

import pytest

from test_runtime_long_task import Run99Sequence


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "AI_agent/logs/experiments/2026-10-02_harness_stage2/compact_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("stage2_compact_evidence", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
compact_evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compact_evidence)
pack = compact_evidence.pack
read_archive = compact_evidence.read_archive


NEW_IMAGE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _write_tar(path: Path, members: dict[str, bytes]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for name, data in sorted(members.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))


def _members(path: Path) -> dict[str, bytes]:
    with tarfile.open(path, "r:gz") as archive:
        return {member.name: archive.extractfile(member).read() for member in archive.getmembers()}


def test_compact_archive_restores_duplicate_and_historical_images_exactly():
    sequence = Run99Sequence()
    historical = next(
        image
        for step in sequence.steps
        for image in step["result"]["images"]
        if image["origin"]["kind"] == "historical_file"
    )
    historical_bytes = (
        ROOT / historical["origin"]["files"][0]["path"]
    ).read_bytes()
    assert compact_evidence._sha256(historical_bytes) == historical["sha256"]
    stream_step = next(
        step
        for step in sequence.steps
        if any(
            image["origin"]["kind"] == "historical_stream"
            for image in step["result"]["images"]
        )
    )
    stream_image = next(
        image
        for image in stream_step["result"]["images"]
        if image["origin"]["kind"] == "historical_stream"
    )
    historical_stream_bytes = base64.b64decode(
        stream_step["raw_result"]["content"][stream_image["response_block"]]["data"],
        validate=True,
    )
    assert compact_evidence._sha256(historical_stream_bytes) == stream_image["sha256"]
    returned_hashes = {
        image["sha256"]
        for step in sequence.steps
        for image in step["result"]["images"]
    }
    inputs_path = (
        ROOT / "AI_agent/logs/experiments/2026-09-30_sm21_instruction_fix_run99/inputs.json"
    )
    inputs = json.loads(inputs_path.read_bytes())
    input_name, input_identity = next(
        (name, identity)
        for name, identity in inputs["images"].items()
        if identity["sha256"] not in returned_hashes
    )
    original_input = (inputs_path.parent / "images" / input_name).read_bytes()
    assert compact_evidence._sha256(original_input) == input_identity["sha256"]
    with tempfile.TemporaryDirectory(prefix=".compact-evidence-test-", dir=ROOT) as temporary:
        directory = Path(temporary)
        source = directory / "source"
        source.mkdir()
        encoded_new = base64.b64encode(NEW_IMAGE).decode("ascii")
        encoded_historical = base64.b64encode(historical_bytes).decode("ascii")
        request = {
            "messages": [
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {
                        "url": "data:image/png;base64," + encoded_new}},
                    {"type": "image", "mimeType": "image/png", "data": encoded_new},
                    {"type": "image", "mimeType": "image/png", "data": encoded_historical},
                    {"type": "image", "mimeType": "image/png", "data":
                        base64.b64encode(historical_stream_bytes).decode("ascii")},
                    {"type": "image", "mimeType": "image/png", "data":
                        base64.b64encode(original_input).decode("ascii")},
                ]}
            ]
        }
        originals = {
            "request.json": json.dumps(request, indent=2).encode() + b"\n",
            "new-image.png": NEW_IMAGE,
            "historical-image.png": historical_bytes,
            "historical-stream-image.png": historical_stream_bytes,
            "unreturned-original-input.png": original_input,
            "notes.txt": b"preserve this ordinary evidence exactly\n",
        }
        for name, data in originals.items():
            (source / name).write_bytes(data)
        (source / "writer.lock").write_text("transient")
        (source / ".harness_tmp").mkdir()
        (source / ".harness_tmp/transport.tmp").write_text("transient")

        archive = directory / "compact.tar.gz"
        manifest = pack(source, archive)
        restored = read_archive(archive)
        assert set(restored) == set(originals)
        assert {name: restored[name] for name in restored} == originals
        new_digest = compact_evidence._sha256(NEW_IMAGE)
        assert manifest["images"][new_digest]["kind"] == "embedded"
        assert manifest["images"][historical["sha256"]]["kind"] == "historical_file"
        assert manifest["images"][stream_image["sha256"]]["kind"] == "historical_stream"
        original_descriptor = manifest["images"][input_identity["sha256"]]
        assert original_descriptor["admission"] == "run99_original_input"
        assert original_descriptor["manifest_sha256"] == compact_evidence.RUN99_INPUTS_SHA256
        members = _members(archive)
        assert list(name for name in members if name == f"images/{new_digest}") == [
            f"images/{new_digest}"
        ]
        assert f"images/{historical['sha256']}" not in members
        assert f"images/{stream_image['sha256']}" not in members
        assert f"images/{input_identity['sha256']}" not in members
        assert encoded_new.encode("ascii") not in members[manifest["files"]["request.json"]["object"]]
        assert "writer.lock" not in restored and ".harness_tmp/transport.tmp" not in restored


def test_read_archive_rejects_wrong_image_hash_and_path_traversal():
    with tempfile.TemporaryDirectory(prefix=".compact-evidence-tamper-", dir=ROOT) as temporary:
        directory = Path(temporary)
        source = directory / "source"
        source.mkdir()
        (source / "image.png").write_bytes(NEW_IMAGE)
        archive = directory / "compact.tar.gz"
        manifest = pack(source, archive)
        digest = compact_evidence._sha256(NEW_IMAGE)
        members = _members(archive)
        members[manifest["images"][digest]["member"]] = NEW_IMAGE + b"tampered"
        tampered = directory / "tampered.tar.gz"
        _write_tar(tampered, members)
        with pytest.raises(ValueError, match="image bytes do not match"):
            read_archive(tampered)

        members = _members(archive)
        members["../escape"] = b"unsafe"
        unsafe = directory / "unsafe.tar.gz"
        _write_tar(unsafe, members)
        with pytest.raises(ValueError, match="unsafe archive member"):
            read_archive(unsafe)


def test_pack_rejects_reserved_marker_collision():
    with tempfile.TemporaryDirectory(prefix=".compact-evidence-marker-", dir=ROOT) as temporary:
        directory = Path(temporary)
        source = directory / "source"
        source.mkdir()
        (source / "collision.json").write_text(
            json.dumps({"value": compact_evidence.MARKER_PREFIX + "literal"})
        )
        with pytest.raises(ValueError, match="reserved image marker"):
            pack(source, directory / "compact.tar.gz")
