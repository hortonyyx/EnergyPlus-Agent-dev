#!/usr/bin/env python3
"""S-5 sandbox environment probe (run with /opt/venv/bin/python from repo root).

Builds a REAL staging via build_isolation_workspace and measures, from inside
the reader's own environment (clean_spawn_env):
  1. which interpreter `python` / `python3` resolve to, and their versions
  2. whether numpy / PIL / scipy import, and their versions
  3. the readable surface (directory names + file counts only)
Writes a JSON report to B_evidence/.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))

from src.agent.execution.isolation import build_isolation_workspace, clean_spawn_env  # noqa: E402

CASE_DIR = REPO / "case_tests" / "e2e_tests" / "sm21_anchor"
OUT = Path(__file__).resolve().parent / "s5_env_report.json"


def sh(env: dict, *cmd: str, cwd: Path) -> dict:
    proc = subprocess.run(
        list(cmd), env=env, cwd=cwd, capture_output=True, text=True, check=False
    )
    return {
        "cmd": list(cmd),
        "rc": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> None:
    staging_root = Path(tempfile.mkdtemp(prefix="s5probe_", dir="/tmp/ep_isolation"))
    manifest = build_isolation_workspace(CASE_DIR, staging_root=staging_root)
    staging = manifest.staging_root
    env = clean_spawn_env(staging)

    report: dict = {"staging_root": str(staging), "env_keys": sorted(env.keys())}

    # --- 1. interpreter -----------------------------------------------------
    interp = {}
    for probe_cmd in (
        ["bash", "-lc", "command -v python"],
        ["bash", "-lc", "command -v python3"],
        ["bash", "-lc", "type -a python"],
        ["python", "-c", "import sys; print(sys.executable); print(sys.version)"],
        ["python3", "-c", "import sys; print(sys.executable); print(sys.version)"],
    ):
        interp[" ".join(probe_cmd[:2])] = sh(env, *probe_cmd, cwd=staging)
    # what the PATH actually contains (reader-visible)
    interp["PATH"] = env.get("PATH", "")
    interp["PYTHONPATH"] = env.get("PYTHONPATH", "")
    report["interpreter"] = interp

    # --- 2. libraries, under the reader's own `python` ----------------------
    libs = {}
    for lib in ("numpy", "PIL", "scipy"):
        code = (
            f"import {lib}; print({lib}.__version__)" if lib != "PIL"
            else "import PIL; print(PIL.__version__)"
        )
        libs[lib] = sh(env, "python", "-c", code, cwd=staging)
    report["libraries_reader_python"] = libs

    # same check under the interpreter the pytest harness would use, for contrast
    libs2 = {}
    for lib in ("numpy", "PIL", "scipy"):
        code = f"import {lib}; print({lib}.__version__)"
        libs2[lib] = sh({**env}, sys.executable, "-c", code, cwd=staging)
    report["libraries_sys_executable"] = libs2

    # --- 4. readable surface: dir names + file counts only ------------------
    tree = {}
    for path in sorted(staging.rglob("*")):
        rel = path.relative_to(staging)
        if path.is_dir():
            n = sum(1 for p in path.rglob("*") if p.is_file())
            tree[str(rel) + "/"] = n
        elif rel.parent == Path("."):
            tree.setdefault("<root files>", 0)
    root_files = sorted(p.name for p in staging.iterdir() if p.is_file())
    report["staging_tree_dirs_filecount"] = tree
    report["staging_root_files"] = root_files

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
