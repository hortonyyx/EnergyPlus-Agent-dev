"""Lossless, deduplicated stage-3 evidence archive checks."""

from __future__ import annotations

import base64
from src.utils import file_lock
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "AI_agent/logs/experiments/2026-10-02_harness_stage3/evidence_pack.py"
)
SPEC = importlib.util.spec_from_file_location("stage3_evidence_pack", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
evidence_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence_pack)


NEW_IMAGE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _directories(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_dir()
    }


def test_multiple_roots_restore_exactly_and_deduplicate_references_and_inline_images():
    with tempfile.TemporaryDirectory(prefix=".stage3-evidence-", dir=ROOT) as temporary:
        work = Path(temporary)
        first, second = work / "first-run", work / "second-run"
        first.mkdir()
        second.mkdir()
        (first / "empty").mkdir()
        (second / "nested").mkdir()

        plan = evidence_pack.STAGE1_PLAN.read_bytes()
        (first / "plan.png").write_bytes(plan)
        role_manifest = json.loads(evidence_pack.ROLE_MANIFEST.read_bytes())
        role_identity = role_manifest["cases"][0]["images"][0]
        role_image = (ROOT / role_identity["path"]).read_bytes()
        (first / "role-source.png").write_bytes(role_image)
        (first / "sent.png").write_bytes(NEW_IMAGE)
        (second / "sent-again.png").write_bytes(NEW_IMAGE)
        encoded = base64.b64encode(NEW_IMAGE).decode("ascii")
        request = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64," + encoded},
                        },
                        {"type": "image", "mimeType": "image/png", "data": encoded},
                    ],
                }
            ]
        }
        request_bytes = json.dumps(request, indent=2).encode("utf-8") + b"\n"
        (first / "request.json").write_bytes(request_bytes)
        lines = (
            json.dumps({"type": "image", "source": {
                "type": "base64", "media_type": "image/png", "data": encoded
            }})
            + "\n"
        ).encode("utf-8")
        (second / "events.jsonl").write_bytes(lines)
        blob_directory = second / "blobs"
        blob_directory.mkdir()
        (blob_directory / _sha(request_bytes)).write_bytes(request_bytes)
        repeated = b"ordinary evidence is retained byte for byte\n"
        (first / "ordinary.txt").write_bytes(repeated)
        (second / "nested/ordinary-copy.txt").write_bytes(repeated)
        (first / "writer.lock").write_bytes(b"")
        (first / "ordinary.txt").chmod(0o640)
        originals = {
            "alpha": _files(first),
            "beta": _files(second),
        }
        original_directories = {
            "alpha": _directories(first),
            "beta": _directories(second),
        }

        archive_path = work / "evidence.tar.xz"
        manifest = evidence_pack.pack(
            {"alpha": first, "beta": second}, archive_path
        )
        repeated_archive = work / "evidence-repeat.tar.xz"
        repeated_manifest = evidence_pack.pack(
            {"alpha": first, "beta": second}, repeated_archive
        )
        assert repeated_manifest == manifest
        assert repeated_archive.read_bytes() == archive_path.read_bytes()
        archive = evidence_pack.read_archive(archive_path)

        assert archive_path.read_bytes().startswith(b"\xfd7zXZ\x00")
        assert len(manifest["roots"]) == 2
        assert set(archive) == {
            f"{name}/{relative}"
            for name, files in originals.items()
            for relative in files
        }
        for name, files in originals.items():
            for relative, expected in files.items():
                logical = f"{name}/{relative}"
                assert archive[logical] == expected
                assert manifest["files"][logical]["sha256"] == _sha(expected)

        plan_digest = _sha(plan)
        role_digest = _sha(role_image)
        derived_digest = _sha(NEW_IMAGE)
        assert manifest["images"][plan_digest]["kind"] == "repository_reference"
        assert manifest["images"][plan_digest]["admission"] == "stage1_offline_input"
        assert manifest["images"][role_digest]["admission"] == "role_cases_manifest"
        assert manifest["images"][role_digest]["manifest_path"] == (
            evidence_pack.ROLE_MANIFEST.relative_to(ROOT).as_posix()
        )
        assert manifest["images"][derived_digest]["kind"] == "embedded"
        members = evidence_pack._archive_members(archive_path)
        assert f"images/{plan_digest}" not in members
        assert f"images/{role_digest}" not in members
        assert list(name for name in members if name == f"images/{derived_digest}") == [
            f"images/{derived_digest}"
        ]
        request_object = manifest["files"]["alpha/request.json"]["object"]
        assert encoded.encode("ascii") not in members[request_object]
        assert len({
            entry["object"]
            for entry in manifest["files"].values()
            if entry["kind"] == "stored" and entry["sha256"] == _sha(repeated)
        }) == 1
        assert "alpha/writer.lock" in archive

        output = work / "restored"
        report = evidence_pack.restore(archive_path, output)
        assert report["file_count"] == sum(len(files) for files in originals.values())
        for name, files in originals.items():
            restored_root = output / name
            assert _files(restored_root) == files
            assert _directories(restored_root) == original_directories[name]
        assert (output / "alpha/ordinary.txt").stat().st_mode & 0o777 == (
            (first / "ordinary.txt").stat().st_mode & 0o777
        )  # Preserve the source mode actually supported by the host filesystem.


def test_generic_repository_reference_is_verified_again_when_archive_is_read():
    with tempfile.TemporaryDirectory(prefix=".stage3-reference-", dir=ROOT) as temporary:
        work = Path(temporary)
        reference = work / "reference.png"
        reference.write_bytes(NEW_IMAGE)
        source = work / "source"
        source.mkdir()
        (source / "same.png").write_bytes(NEW_IMAGE)
        archive_path = work / "reference.tar.xz"
        manifest = evidence_pack.pack(
            {"run": source},
            archive_path,
            references=(reference,),
            include_default_references=False,
        )
        digest = _sha(NEW_IMAGE)
        assert manifest["images"][digest]["kind"] == "repository_reference"
        assert f"images/{digest}" not in evidence_pack._archive_members(archive_path)

        reference.write_bytes(NEW_IMAGE + b"changed")
        with pytest.raises(ValueError, match="repository image no longer matches"):
            evidence_pack.read_archive(archive_path)


def test_archive_tampering_and_unsafe_source_content_fail_loudly():
    with tempfile.TemporaryDirectory(prefix=".stage3-tamper-", dir=ROOT) as temporary:
        work = Path(temporary)
        source = work / "source"
        source.mkdir()
        (source / "image.png").write_bytes(NEW_IMAGE)
        archive_path = work / "original.tar.xz"
        manifest = evidence_pack.pack(
            {"run": source}, archive_path, include_default_references=False
        )
        digest = _sha(NEW_IMAGE)
        members = evidence_pack._archive_members(archive_path)
        members[f"images/{digest}"] += b"tampered"
        tampered = work / "tampered.tar.xz"
        evidence_pack._write_archive(tampered, members)
        with pytest.raises(ValueError, match="image bytes do not match"):
            evidence_pack.read_archive(tampered)

        marker_source = work / "marker-source"
        marker_source.mkdir()
        (marker_source / "collision.txt").write_text(
            evidence_pack.MARKER_PREFIX + "0" * 64 + "__", encoding="utf-8"
        )
        with pytest.raises(ValueError, match="reserved image marker"):
            evidence_pack.pack(
                {"run": marker_source},
                work / "marker.tar.xz",
                include_default_references=False,
            )

        bad_blob_source = work / "bad-blob-source"
        (bad_blob_source / "blobs").mkdir(parents=True)
        (bad_blob_source / "blobs" / ("0" * 64)).write_bytes(b"not that hash")
        with pytest.raises(ValueError, match="wrong hash"):
            evidence_pack.pack(
                {"run": bad_blob_source},
                work / "bad-blob.tar.xz",
                include_default_references=False,
            )

        active = work / "active-source"
        active.mkdir()
        lock_path = active / "writer.lock"
        with lock_path.open("a+b") as lock:
            file_lock.flock(lock, file_lock.LOCK_EX | file_lock.LOCK_NB)
            with pytest.raises(ValueError, match="still active"):
                evidence_pack.pack(
                    {"run": active},
                    work / "active.tar.xz",
                    include_default_references=False,
                )
            file_lock.flock(lock, file_lock.LOCK_UN)


def test_cli_pack_verify_and_restore_uses_named_sources(capsys):
    with tempfile.TemporaryDirectory(prefix=".stage3-cli-", dir=ROOT) as temporary:
        work = Path(temporary)
        source = work / "source"
        source.mkdir()
        (source / "receipt.json").write_text('{"status":"completed"}\n', encoding="utf-8")
        archive = work / "cli.tar.xz"
        restored = work / "restored"

        assert evidence_pack.main([
            "pack",
            "--archive", str(archive),
            "--source", f"offline={source}",
            "--no-default-references",
        ]) == 0
        packed = json.loads(capsys.readouterr().out)
        assert packed == {
            "archive": archive.relative_to(ROOT).as_posix(),
            "files": 1,
            "images": 0,
            "roots": 1,
        }
        assert evidence_pack.main(["verify", "--archive", str(archive)]) == 0
        verified = json.loads(capsys.readouterr().out)
        assert verified["files"] == 1 and verified["roots"] == 1
        assert evidence_pack.main([
            "restore", "--archive", str(archive), "--output", str(restored)
        ]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["file_count"] == 1
        assert (restored / "offline/receipt.json").read_bytes() == (
            source / "receipt.json"
        ).read_bytes()
