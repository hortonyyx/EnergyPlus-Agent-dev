"""Read historical evidence through Git; extract selected bytes only in this tree."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / ".tmp_a1t" / "history"
MIGRATION = "6b612d54c0a413d8456bc3eb408e2094b76d2d63"
NODE = "57879421"
T1 = "74e27da33d8f957334b6e77c40e788acf015ea55"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def selected(name):
    p = Path(name)
    return (p.name == "inputs.json" or "plan_drafts" in p.parts and p.suffix == ".json"
            or "plan_revisions" in p.parts or "plan_assemblies" in p.parts
            or p.name in {"proposal.json", "report.json", "record.json.gz", "tools.jsonl"}
            or "images" in p.parts and p.suffix.lower() in {".png", ".jpg", ".jpeg"})


def archive(manifest_path, commit):
    manifest = json.loads(manifest_path.read_bytes())
    target = WORK / manifest["archive"]
    if not target.exists():
        local = manifest_path.parent / manifest["archive"]
        if local.is_file():
            target = local
        else:
            with target.open("wb") as out:
                for name in manifest.get("parts", {manifest["archive"]: manifest["archive_sha256"]}):
                    subprocess.run(["git", "show", f"{commit}:{name}"], cwd=ROOT, stdout=out, check=True)
    assert sha(target) == manifest["archive_sha256"], target
    hashes = {}
    with tarfile.open(target, "r:xz") as handle:
        for member in handle:
            if not member.isfile() or not selected(member.name):
                continue
            destination = (WORK / member.name).resolve()
            assert destination.is_relative_to(WORK.resolve()), member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            raw = handle.extractfile(member).read()
            digest = hashlib.sha256(raw).hexdigest()
            assert digest == manifest["files_sha256"][member.name], member.name
            destination.write_bytes(raw)
            hashes[member.name] = digest
    row = dict(manifest=str(manifest_path.relative_to(ROOT)), commit=commit,
               archive_sha256=manifest["archive_sha256"], extracted_root=manifest["extracted_root"],
               verified_selected_files=hashes, original_file_count=manifest["file_count"]
               if "file_count" in manifest else len(manifest["files_sha256"]))
    print(f"materialized {manifest['extracted_root']}: {len(hashes)} verified files", flush=True)
    return row


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    rows = []
    for experiment, commit in (("2026-10-03_migration_comparison", MIGRATION),
                               ("2026-10-04_node_regression_c2", NODE)):
        for manifest in sorted((HERE.parent / experiment / "evidence").glob("*_manifest.json")):
            rows.append(archive(manifest, commit))
    for case in ("sm24", "sm25"):
        name = f"2026-10-03_{case}_glm_tools_t1"
        prefix = f"AI_agent/logs/experiments/{name}"
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", T1, prefix],
                                        cwd=ROOT, text=True).splitlines()
        hashes = {}
        for path in paths:
            relative = Path(path).relative_to(prefix)
            if not selected(relative.as_posix()) or "runtime_snapshot" in relative.parts:
                continue
            raw = subprocess.check_output(["git", "show", f"{T1}:{path}"], cwd=ROOT)
            target = WORK / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            hashes[str(relative)] = hashlib.sha256(raw).hexdigest()
        rows.append(dict(commit=T1, prefix=prefix, extracted_root=name, verified_selected_files=hashes))
        print(f"materialized {name}: {len(hashes)} verified files", flush=True)
    (HERE / "evidence_sources.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
