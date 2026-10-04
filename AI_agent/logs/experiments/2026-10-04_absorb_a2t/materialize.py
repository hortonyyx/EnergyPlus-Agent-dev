"""Extract only T1 replay inputs from immutable Git objects into this worktree."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / ".tmp_a2t" / "history"
COMMIT = "74e27da33d8f957334b6e77c40e788acf015ea55"


def main():
    records = []
    for case in ("sm24", "sm25"):
        name = f"2026-10-03_{case}_glm_tools_t1"
        prefix = "AI_agent/logs/experiments/" + name
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", COMMIT, prefix], cwd=ROOT, text=True).splitlines()
        paths = [p for p in paths if "runtime_snapshot" not in Path(p).parts and
                 (Path(p).suffix == ".json" or "/images/" in p or p.endswith("tools.jsonl"))]
        hashes = {}
        with subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as reader:
            for path in paths:
                reader.stdin.write(f"{COMMIT}:{path}\n".encode())
                reader.stdin.flush()
                header = reader.stdout.readline().decode().split()
                assert len(header) == 3 and header[1] == "blob", header
                raw = reader.stdout.read(int(header[2]))
                assert reader.stdout.read(1) == b"\n"
                relative = Path(path).relative_to(prefix)
                target = WORK / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                hashes[str(relative)] = hashlib.sha256(raw).hexdigest()
            reader.stdin.close()
            assert reader.wait() == 0
        records.append(dict(commit=COMMIT, prefix=prefix, files_sha256=hashes))
        print(name, len(hashes), flush=True)
    (HERE / "evidence_sources.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
