"""Run documented Bash examples in Bash, including native Git Bash on Windows."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def run_bash(command, **kwargs):
    if os.name == "nt":
        git = shutil.which("git")
        bash = Path(git).resolve().parents[1] / "bin/bash.exe" if git else None
        if bash is None or not bash.is_file():
            raise RuntimeError("These Bash examples require native Git for Windows (Git Bash)")
    else:
        bash = shutil.which("bash")
        if not bash:
            raise RuntimeError("These documented examples require Bash")
    env = dict(kwargs.pop("env", os.environ))
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    return subprocess.run([str(bash), "-c", command], env=env, **kwargs)
