"""Copy a terminated frozen run and verify every byte; never delete its source."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    receipt = json.loads((source / "receipt.json").read_bytes())
    if receipt.get("status") not in {"completed", "failed"}:
        raise ValueError("source has no terminal receipt")
    if destination.exists():
        raise ValueError("destination already exists; will not merge or overwrite")
    source_files = sorted(p for p in source.rglob("*") if p.is_file())
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("source contains a symlink")
    shutil.copytree(source, destination)
    rows = []
    for path in source_files:
        relative = path.relative_to(source)
        copied = destination / relative
        original_sha, copied_sha = sha(path), sha(copied)
        if original_sha != copied_sha:
            raise ValueError(f"archive mismatch: {relative}")
        rows.append({"path": relative.as_posix(), "bytes": path.stat().st_size,
                     "sha256": original_sha})
    copied_files = sorted(p for p in destination.rglob("*") if p.is_file())
    if len(copied_files) != len(rows):
        raise ValueError("archive file count mismatch")
    result = {"schema": "frozen_run_archive_v1", "source": str(source),
              "destination": str(destination), "terminal_status": receipt["status"],
              "verified_files": len(rows), "verified_bytes": sum(r["bytes"] for r in rows),
              "mismatches": 0, "files": rows}
    args.manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
