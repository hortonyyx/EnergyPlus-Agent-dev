"""Extract the four already archived runs; no provider or credential access."""

import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BRANCH = "evidence/node-regression-a1-2026-10-04"
CASES = [
    ("2026-10-04_node_regression_a1", "sm24_runtime_anthropic"),
    ("2026-10-04_node_regression_a1", "sm25_runtime_anthropic"),
    ("2026-10-04_qwen27b_probe", "sm24_qwen27b_paratera"),
    ("2026-10-04_qwen27b_after_a2", "sm24_qwen27b_after_a2"),
]


def main():
    destination = HERE / ".tmp/history"
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for directory, name in CASES:
        manifest_path = HERE.parent / directory / "evidence" / (name + "_manifest.json")
        manifest = json.loads(manifest_path.read_bytes())
        local = manifest_path.parent / manifest["archive"]
        raw = local.read_bytes() if local.is_file() else subprocess.check_output(
            ["git", "show", BRANCH + ":" + manifest["archive"]], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == manifest["archive_sha256"]
        verified = {}
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:xz") as archive:
            for member in archive:
                if member.isdir():
                    continue
                assert member.isfile() and not member.issym() and not member.islnk()
                relative = Path(member.name)
                assert relative.parts[0] == manifest["extracted_root"]
                key = str(Path(*relative.parts[1:]))
                data = archive.extractfile(member).read()
                verified[key] = hashlib.sha256(data).hexdigest()
                assert verified[key] == manifest["files_sha256"][key]
                target = (destination / relative).resolve()
                assert target.is_relative_to(destination.resolve())
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    assert target.read_bytes() == data
                else:
                    target.write_bytes(data)
        assert verified == manifest["files_sha256"]
        row = {"run": name, "archive_sha256": manifest["archive_sha256"],
            "archive_bytes": len(raw), "manifest": str(manifest_path.relative_to(ROOT)),
            "file_count": len(verified), "all_files_match": True,
            "source": str(local.relative_to(ROOT)) if local.is_file() else BRANCH + ":" + manifest["archive"]}
        rows.append(row)
        print(json.dumps(row), flush=True)
    (HERE / "archive_verification.json").write_text(json.dumps({"model_requests": 0, "runs": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
