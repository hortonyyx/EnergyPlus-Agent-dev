"""Pack one run directory as evidence: tar.xz, per-file hashes, 90 MB parts when over GitHub's limit.

Usage: python pack_evidence.py <run_dir> <evidence_dir>
Writes <evidence_dir>/<run>_run.tar.xz (or .partNN files) and <evidence_dir>/<run>_manifest.json.
The archive goes to an evidence branch when it is large; the manifest stays on main.
No model calls; the run directory is only read.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[4]
PART_BYTES = 90 * 1024 * 1024
LIMIT_BYTES = 95 * 1024 * 1024


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pack(run, evidence):
    run, evidence = run.resolve(), evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    archive = evidence / f"{run.name}_run.tar.xz"
    assert not archive.exists() and not list(evidence.glob(archive.name + ".part*")), "refusing to overwrite evidence"
    files = sorted(p for p in run.rglob("*") if p.is_file() and p.name != "writer.lock")
    # The container has no xz binary; Python's lzma writes the same .tar.xz format.
    with tarfile.open(archive, "w:xz", preset=6) as bundle:
        for path in files:
            bundle.add(path, arcname=str(path.relative_to(run.parent)), recursive=False)
    manifest = dict(archive=archive.name, archive_sha256=sha256(archive), archive_bytes=archive.stat().st_size,
                    extracted_root=run.name, original_location=str(run.relative_to(ROOT)), file_count=len(files),
                    files_sha256={str(p.relative_to(run)): sha256(p) for p in files})
    if archive.stat().st_size > LIMIT_BYTES:
        subprocess.run(["split", "-b", str(PART_BYTES), "-d", "-a", "2", str(archive), str(archive) + ".part"], check=True)
        archive.unlink()
        manifest["parts"] = {p.name: sha256(p) for p in sorted(evidence.glob(archive.name + ".part*"))}
        manifest["reassemble"] = (f"cat {archive.name}.part* > {archive.name} (archive_sha256 is of the reassembled file); "
                                  "split because GitHub rejects files over 100 MB")
    (evidence / f"{run.name}_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return {k: v for k, v in manifest.items() if k != "files_sha256"}


if __name__ == "__main__":
    print(json.dumps(pack(Path(sys.argv[1]), Path(sys.argv[2])), indent=1))
