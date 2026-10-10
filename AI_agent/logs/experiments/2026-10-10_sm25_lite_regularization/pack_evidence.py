"""Pack closed local evidence, verify archive bytes, and scan configured secrets."""
from __future__ import annotations
import hashlib
import io
import json
import tarfile
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parent
BASE = ROOT / "AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization"
OUTPUT = BASE / "sm25_lite_20261010_evidence.tar.gz"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    roots = [BASE / name for name in ("manual_dispatch_sm25_lite_v1",
             "implementation_worktree_archive", "offline_grid_replay")]
    files = sorted(path for root in roots for path in root.rglob("*") if path.is_file())
    files += [BASE / "full_pytest.log", BASE / "fixture_recheck.log"]
    if OUTPUT.exists():
        raise ValueError("bundle already exists; will not overwrite")
    secrets = [value.encode() for key, value in dotenv_values(ROOT / ".env").items()
               if value and len(value) >= 12 and any(
                   marker in key.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD"))]
    rows = []
    for path in files:
        raw = path.read_bytes()
        if any(secret in raw for secret in secrets):
            raise ValueError(f"configured secret found in {path.relative_to(BASE)}")
        rows.append({"path": path.relative_to(BASE).as_posix(), "bytes": len(raw), "sha256": digest(raw)})
    manifest = {"schema": "lite_evidence_bundle_v1", "files": rows,
                "file_count": len(rows), "source_bytes": sum(row["bytes"] for row in rows),
                "configured_secret_scan": "passed", "run_terminal": "failed"}
    encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    with tarfile.open(OUTPUT, "w:gz", compresslevel=6) as archive:
        info = tarfile.TarInfo("MANIFEST.json")
        info.size = len(encoded)
        archive.addfile(info, io.BytesIO(encoded))
        for path, row in zip(files, rows, strict=True):
            archive.add(path, arcname=row["path"], recursive=False)
    with tarfile.open(OUTPUT, "r:gz") as archive:
        members = {member.name: member for member in archive.getmembers()}
        if len(members) != len(rows) + 1:
            raise ValueError("archive member count mismatch")
        if archive.extractfile(members["MANIFEST.json"]).read() != encoded:
            raise ValueError("embedded manifest differs")
        for row in rows:
            if digest(archive.extractfile(members[row["path"]]).read()) != row["sha256"]:
                raise ValueError(f"archive hash mismatch: {row['path']}")
    extra_rows = [row for row in rows if not row["path"].startswith("manual_dispatch_sm25_lite_v1/")]
    (EXP / "additional_evidence_manifest.json").write_text(
        json.dumps(extra_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {key: value for key, value in manifest.items() if key != "files"}
    result.update(bundle=str(OUTPUT.relative_to(ROOT)), bundle_bytes=OUTPUT.stat().st_size,
                  bundle_sha256=digest(OUTPUT.read_bytes()), embedded_manifest_sha256=digest(encoded),
                  archive_members_verified=len(rows) + 1, mismatches=0)
    (EXP / "evidence_backup.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
