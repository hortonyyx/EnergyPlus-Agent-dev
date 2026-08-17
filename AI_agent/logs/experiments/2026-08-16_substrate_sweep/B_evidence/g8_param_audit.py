#!/usr/bin/env python3
"""G8: exhaustive parameter-key audit between guard.PROBE_DIRECT_PARAM_KEYS and
what cv_probe's six authorized tools actually accept (read off build_parser()).

Direction A: every guard key — is it accepted by at least one authorized tool?
Direction B: every key an authorized tool accepts — is it in the guard's list?
Plus behavioural confirmation: guard verdict + wrapper verdict for the suspected
dead keys and for cross-tool parameter mixing.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))

from src.agent.execution.isolation import build_isolation_workspace  # noqa: E402

CASE_DIR = REPO / "case_tests" / "e2e_tests" / "sm21_anchor"
OUT = Path(__file__).resolve().parent / "g8_param_audit_report.json"
IMG = "case_data/1f_view.png"
AUTHORIZED = [
    "crop_zoom", "wall_line_profiler", "storey_line_profiler",
    "px_m_calibrator", "window_cc_detector", "overlay_logger",
]
WITHDRAWN = ["prescan-plan", "prescan-elevation"]


def cv_probe_tool_keys() -> dict[str, set[str]]:
    """Extract per-tool accepted option keys from cv_probe.py source.

    Linear regex scan in source order — ast.walk() is unordered and mis-attributes
    add_argument calls to the wrong subparser.
    """
    src = (REPO / "scripts" / "tool_scripts" / "cv_probe.py").read_text(encoding="utf-8")
    body = src.split("def build_parser(")[1]
    common_src = src.split("def _common(")[1].split("\n\ndef ")[0]
    common_keys: set[str] = set()
    for m in re.finditer(r'add_argument\("--([a-z0-9-]+)"', common_src):
        common_keys.add(m.group(1).replace("-", "_"))
    per_tool: dict[str, set[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        m = re.search(r'add_parser\("([a-z_-]+)"\)', line)
        if m:
            current = m.group(1)
            per_tool[current] = set(common_keys) | {"tool"}
            continue
        m = re.search(r'add_argument\("--([a-z0-9-]+)"', line)
        if m and current is not None:
            per_tool[current].add(m.group(1).replace("-", "_"))
    return per_tool


def main() -> None:
    per_tool = cv_probe_tool_keys()
    sys.path.insert(0, str(REPO / "src" / "agent" / "execution" / "isolation_templates"))
    import guard as guard_template  # the repo template, only to read the tuple

    guard_keys = list(guard_template.PROBE_DIRECT_PARAM_KEYS)
    accepted_by_authorized: set[str] = set()
    for t in AUTHORIZED:
        accepted_by_authorized |= per_tool[t]
    accepted_by_withdrawn = set()
    for t in WITHDRAWN:
        accepted_by_withdrawn |= per_tool[t]

    dead_vs_authorized = [k for k in guard_keys if k not in accepted_by_authorized]
    missing_in_guard = sorted(k for k in accepted_by_authorized if k not in guard_keys)

    # ---- behavioural confirmation on a REAL staging ------------------------
    staging = build_isolation_workspace(
        CASE_DIR, staging_root=Path(tempfile.mkdtemp(prefix="g8_", dir="/tmp/ep_isolation"))
    ).staging_root

    def guard_eval(command: str) -> dict:
        driver = (
            "import json,sys; sys.path.insert(0, sys.argv[1]); import guard; "
            "payload = json.loads(sys.stdin.read()); "
            "d, r, p = guard.evaluate(payload); "
            "print(json.dumps({'decision': d, 'reason': r}))"
        )
        proc = subprocess.run(
            [sys.executable, "-c", driver, str(staging)],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
            capture_output=True, text=True, cwd=staging, check=False)
        return json.loads(proc.stdout) if proc.returncode == 0 else {"error": proc.stderr[:300]}

    def run_wrapper(args: list[str]) -> int:
        import os
        env = {"PATH": os.environ.get("PATH", ""), "HOME": "/tmp", "PYTHONPATH": str(staging)}
        proc = subprocess.run([sys.executable, "tools/run_cv_probe.py", *args],
                              capture_output=True, text=True, cwd=staging, env=env, check=False)
        return proc.returncode

    behaviour = {}
    # every guard key, on an authorized tool that does NOT accept it (worst case:
    # key is nominally legal) and on one that does where possible
    for key in guard_keys:
        cmd = (f"python tools/run_cv_probe.py --tool storey_line_profiler "
               f"--image {IMG} --out-dir out/g8 --{key.replace('_','-')} 1")
        behaviour[f"guard/{key}/on-storey"] = guard_eval(cmd)
    # dead keys + cross-tool mixing + boolean flag, wrapper side
    for key in ("capability_profile", "no_cc", "min_strength", "min_line_len_px", "label"):
        args = ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", "out/g8",
                "--" + key.replace("_", "-"), "1"]
        behaviour[f"wrapper/{key}/on-storey"] = run_wrapper(args)
    behaviour["wrapper/axis-on-storey"] = run_wrapper(
        ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", "out/g8", "--axis", "row"])
    behaviour["wrapper/bbox-on-wcc"] = run_wrapper(
        ["--tool", "window_cc_detector", "--image", IMG, "--out-dir", "out/g8",
         "--bbox", "1,2,3,4"])  # bbox IS common — cv_probe accepts for wcc? (unused but legal)

    report = {
        "guard_keys": guard_keys,
        "per_tool_keys": {t: sorted(v) for t, v in per_tool.items()},
        "common_keys": sorted(per_tool["crop_zoom"] & per_tool["window_cc_detector"]),
        "dead_vs_authorized": dead_vs_authorized,
        "dead_keys_accepted_only_by_withdrawn": [
            k for k in dead_vs_authorized if k in accepted_by_withdrawn
        ],
        "missing_in_guard (accepted but not allowed)": missing_in_guard,
        "counts": {
            "guard_keys": len(guard_keys),
            "authorized_union": len(accepted_by_authorized),
            "common_plus_tool": len(per_tool["crop_zoom"]),
            "exclusive_union": len(
                set().union(*(per_tool[t] - per_tool["crop_zoom"] - {"tool"}
                              for t in AUTHORIZED if t != "crop_zoom"))
            ),
        },
        "behaviour": behaviour,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "behaviour"}, indent=2))
    print("behaviour guard verdicts:",
          {k: v.get("decision") for k, v in behaviour.items() if k.startswith("guard/")})
    print("behaviour wrapper rcs:",
          {k: v for k, v in behaviour.items() if k.startswith("wrapper/")})


if __name__ == "__main__":
    main()
