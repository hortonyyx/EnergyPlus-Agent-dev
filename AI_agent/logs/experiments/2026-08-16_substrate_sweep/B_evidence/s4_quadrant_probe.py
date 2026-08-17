#!/usr/bin/env python3
"""S-4 quadrant probe + S-5 §3 writable-face / §5 network (repo root, /opt/venv python).

For every cell: real guard.evaluate (subprocess, staged guard, real _staging_root)
x real wrapper (subprocess, staged tools/run_cv_probe.py). Writes JSON report.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))

from src.agent.execution.isolation import build_isolation_workspace  # noqa: E402

CASE_DIR = REPO / "case_tests" / "e2e_tests" / "sm21_anchor"
OUT = Path(__file__).resolve().parent / "s4_quadrant_report.json"
IMG = "case_data/1f_view.png"

SIX_TOOLS = [
    "crop_zoom",
    "wall_line_profiler",
    "storey_line_profiler",
    "px_m_calibrator",
    "window_cc_detector",
    "overlay_logger",
]

# minimal per-tool extra args (direct form, all inline-safe)
TOOL_EXTRA = {
    "crop_zoom": ["--bbox", "100,100,400,400"],
    "wall_line_profiler": ["--axis", "row"],
    "storey_line_profiler": [],
    "px_m_calibrator": [],  # anchors handled separately (file-path form)
    "window_cc_detector": [],
    "overlay_logger": [],  # candidates handled separately (file-path form)
}

ANCHORS = [
    {
        "axis": "x",
        "px_a": 120.0,
        "px_b": 2300.0,
        "value_m": 15.0,
        "dimension_ref": "example_span",
    }
]
CANDIDATES = [
    {
        "candidate_id": "c001",
        "status": "undecided",
        "reason": "example",
        "geometry": {"kind": "bbox", "bbox_px": [100, 100, 300, 140]},
    }
]


def _env(staging: Path) -> dict:
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": "/tmp",
        "PYTHONPATH": str(staging),
    }


def guard_eval(staging: Path, command: str) -> dict:
    """Real guard.evaluate in a subprocess whose guard.py IS the staged one."""
    driver = (
        "import json,sys; sys.path.insert(0, sys.argv[1]); import guard; "
        "payload = json.loads(sys.stdin.read()); "
        "d, r, p = guard.evaluate(payload); "
        "print(json.dumps({'decision': d, 'reason': r, 'paths': p}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", driver, str(staging)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True, text=True, cwd=staging, check=False,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:500], "rc": proc.returncode}
    return json.loads(proc.stdout)


def guard_eval_tool(staging: Path, payload: dict) -> dict:
    driver = (
        "import json,sys; sys.path.insert(0, sys.argv[1]); import guard; "
        "payload = json.loads(sys.stdin.read()); "
        "d, r, p = guard.evaluate(payload); "
        "print(json.dumps({'decision': d, 'reason': r, 'paths': p}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", driver, str(staging)],
        input=json.dumps(payload),
        capture_output=True, text=True, cwd=staging, check=False,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:500], "rc": proc.returncode}
    return json.loads(proc.stdout)


def run_wrapper(staging: Path, args: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", *args],
        capture_output=True, text=True, cwd=staging, env=_env(staging), check=False,
    )
    return {
        "rc": proc.returncode,
        "stdout_head": proc.stdout.strip()[:400],
        "stderr_head": proc.stderr.strip()[-500:],
    }


def count_files(staging: Path, sub: str) -> int:
    d = staging / "out" / sub
    return sum(1 for p in d.rglob("*") if p.is_file()) if d.exists() else 0


def main() -> None:
    staging_root = Path(tempfile.mkdtemp(prefix="s4probe_", dir="/tmp/ep_isolation"))
    staging = build_isolation_workspace(CASE_DIR, staging_root=staging_root).staging_root
    cells: list[dict] = []

    def cell(cid: str, g: dict, w: dict, note: str = "") -> None:
        cells.append({"cell": cid, "guard": g, "wrapper": w, "note": note})
        print(f"== {cid}\n   guard={g}\n   wrapper_rc={w.get('rc')} err={w.get('stderr_head','')[:160]}", flush=True)

    # shared request fixtures
    (staging / "requests" / "anchors.json").write_text(json.dumps(ANCHORS))
    (staging / "requests" / "cand.json").write_text(json.dumps(CANDIDATES))

    def tool_args(tool: str, out_dir: str, form: str) -> list[str]:
        extra = list(TOOL_EXTRA[tool])
        if tool == "px_m_calibrator":
            extra += ["--anchors-json", "requests/anchors.json"]
        if tool == "overlay_logger":
            extra += ["--candidates-json", "requests/cand.json"]
        if form == "direct":
            return ["--tool", tool, "--image", IMG, "--out-dir", out_dir, *extra]
        req = {"tool": tool, "args": {"image": IMG, "out_dir": out_dir}}
        if tool == "crop_zoom":
            req["args"]["bbox"] = "100,100,400,400"
        if tool == "wall_line_profiler":
            req["args"]["axis"] = "row"
        if tool == "px_m_calibrator":
            req["args"]["anchors_json"] = ANCHORS  # inline array (F-49 shape)
        if tool == "overlay_logger":
            req["args"]["candidates_json"] = CANDIDATES
        name = f"req_{tool}_{form}.json"
        (staging / "requests" / name).write_text(json.dumps(req))
        if form == "request":
            return ["--request", f"requests/{name}"]
        batch = {"requests": [{"id": f"b_{tool}", "tool": tool, "args": req["args"]}]}
        bname = f"batch_{tool}.json"
        (staging / "requests" / bname).write_text(json.dumps(batch))
        return ["--batch", f"requests/{bname}"]

    # ---- G1: six tools x three forms --------------------------------------
    for tool in SIX_TOOLS:
        for form in ("direct", "request", "batch"):
            out_dir = f"out/g1_{tool}_{form}"
            args = tool_args(tool, out_dir, form)
            cmd = "python tools/run_cv_probe.py " + " ".join(args)
            g = guard_eval(staging, cmd)
            w = run_wrapper(staging, args)
            n = count_files(staging, out_dir.removeprefix("out/"))
            cell(f"G1/{form}/{tool}", g, w, f"sidecars={n}")

    # ---- G1b: px_m_calibrator with INLINE anchors json (F-49 shape) --------
    inline = json.dumps(ANCHORS, separators=(",", ":"))
    args = ["--tool", "px_m_calibrator", "--image", IMG, "--out-dir", "out/g1_inline",
            "--anchors-json", inline]
    cmd = "python tools/run_cv_probe.py " + " ".join(args)
    cell("G1b/inline-anchors-direct", guard_eval(staging, cmd), run_wrapper(staging, args))

    # ---- G2: withdrawn prescan tools ---------------------------------------
    for tool in ("prescan-plan", "prescan-elevation"):
        args = ["--tool", tool, "--image", IMG, "--out-dir", "out/g2"]
        cmd = "python tools/run_cv_probe.py " + " ".join(args)
        cell(f"G2/direct/{tool}", guard_eval(staging, cmd), run_wrapper(staging, args))
        req = {"tool": tool, "args": {"image": IMG, "out_dir": "out/g2"}}
        (staging / "requests" / f"g2_{tool}.json").write_text(json.dumps(req))
        args = ["--request", f"requests/g2_{tool}.json"]
        cell(f"G2/request/{tool}", guard_eval(staging, "python tools/run_cv_probe.py " + " ".join(args)),
             run_wrapper(staging, args))

    # ---- G3: out_dir escapes ------------------------------------------------
    for label, od in (("tools", "tools/x"), ("requests", "requests/x"),
                      ("abs-tmp", "/tmp/x"), ("traversal", "out/../tools")):
        args = ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", od]
        cmd = "python tools/run_cv_probe.py " + " ".join(args)
        cell(f"G3/out_dir/{label}", guard_eval(staging, cmd), run_wrapper(staging, args))
    before = count_files(staging, "tools") + count_files(staging, "requests")

    # ---- G4: image escapes ---------------------------------------------------
    (staging / "lnk.png").symlink_to("/etc/hostname")
    for label, im in (("absolute", "/etc/passwd"), ("dotdot", "../x.png"),
                      ("tilde", "~/x.png"), ("symlink", "lnk.png")):
        args = ["--tool", "storey_line_profiler", "--image", im, "--out-dir", "out/g4"]
        cmd = "python tools/run_cv_probe.py " + " ".join(args)
        cell(f"G4/image/{label}", guard_eval(staging, cmd), run_wrapper(staging, args))

    # ---- G5: request file content carrying forbidden tokens ------------------
    for label, img_val in (("dotdot-gt", "../../case_tests/gt.json"),
                           ("repo-abs", "/workspaces/EnergyPlus-Agent-dev/case_tests/e2e_tests/sm21_anchor/case_data/1f_view.png")):
        req = {"tool": "storey_line_profiler", "args": {"image": img_val, "out_dir": "out/g5"}}
        name = f"g5_{label}.json"
        (staging / "requests" / name).write_text(json.dumps(req))
        args = ["--request", f"requests/{name}"]
        cell(f"G5/request-content/{label}",
             guard_eval(staging, "python tools/run_cv_probe.py " + " ".join(args)),
             run_wrapper(staging, args))

    # ---- G6: batch envelope edges --------------------------------------------
    def batch_cell(label: str, requests: list, out_dir: str = "out/g6"):
        name = f"g6_{label}.json"
        (staging / "requests" / name).write_text(json.dumps({"requests": requests}))
        args = ["--batch", f"requests/{name}"]
        g = guard_eval(staging, "python tools/run_cv_probe.py " + " ".join(args))
        w = run_wrapper(staging, args)
        n = count_files(staging, out_dir.removeprefix("out/"))
        cell(f"G6/batch/{label}", g, w, f"sidecars_in_out_g6={n}")

    ok_req = {"tool": "storey_line_profiler",
              "args": {"image": IMG, "out_dir": "out/g6"}}
    bad_req = {"tool": "storey_line_profiler",
               "args": {"image": IMG, "out_dir": "tools/escape"}}
    batch_cell("33-entries", [{"id": f"r{i:02d}", **ok_req} for i in range(33)])
    batch_cell("dup-id", [{"id": "same", **ok_req}, {"id": "same", **ok_req}])
    batch_cell("bad-id", [{"id": "bad id!", **ok_req}])
    batch_cell("empty", [])
    batch_cell("partial-illegal", [{"id": "a", **ok_req}, {"id": "b", **bad_req}])

    # ---- G7: malformed direct args --------------------------------------------
    for label, args in (
        ("bare-arg", ["--tool", "crop_zoom", "crop_zoom", "--image", IMG, "--out-dir", "out/g7"]),
        ("dup-param", ["--tool", "crop_zoom", "--image", IMG, "--image", IMG, "--out-dir", "out/g7"]),
        ("missing-value", ["--tool", "crop_zoom", "--image"]),
        ("no-tool", ["--image", IMG, "--out-dir", "out/g7"]),
        ("no-image", ["--tool", "crop_zoom", "--out-dir", "out/g7"]),
    ):
        cmd = "python tools/run_cv_probe.py " + " ".join(args)
        cell(f"G7/direct/{label}", guard_eval(staging, cmd), run_wrapper(staging, args))

    # ---- G9: same sidecar name twice -------------------------------------------
    for i in (1, 2):
        args = ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", "out/g9",
                "--sidecar-name", "001_g9probe"]
        cell(f"G9/explicit-name/call-{i}", guard_eval(staging, "python tools/run_cv_probe.py " + " ".join(args)),
             run_wrapper(staging, args))
    for i in (1, 2):
        args = ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", "out/g9auto"]
        cell(f"G9/auto/call-{i}", guard_eval(staging, "python tools/run_cv_probe.py " + " ".join(args)),
             run_wrapper(staging, args))
    g9_files = sorted(p.name for p in (staging / "out" / "g9").glob("*.json")) if (staging / "out" / "g9").exists() else []
    g9auto_files = sorted(p.name for p in (staging / "out" / "g9auto").glob("**/*.json")) if (staging / "out" / "g9auto").exists() else []
    cells.append({"cell": "G9/inventory", "explicit_dir": g9_files, "auto_dir": g9auto_files})

    # ---- S-5 §3: writable face (guard Write-tool verdicts) ---------------------
    for label, target in (
        ("out-file", "out/w.txt"), ("requests-file", "requests/w.json"),
        ("staging-root", "w_root.txt"), ("tools", "tools/w.py"),
        ("case_data", "case_data/w.png"), ("guard-py", "guard.py"),
        ("MANIFEST", "MANIFEST.json"),
    ):
        payload = {"tool_name": "Write", "tool_input": {"file_path": target, "content": "x"}}
        cells.append({"cell": f"S5w/{label}", "guard": guard_eval_tool(staging, payload)})
        print(f"== S5w/{label} -> {cells[-1]['guard']}", flush=True)
    # python -c OS-level write to the staging root (guard verdict + real landing)
    code = 'open("rootwrite_probe.txt","w").write("x")'
    g = guard_eval(staging, f"python -c '{code}'")
    proc = subprocess.run([sys.executable, "-c", code], cwd=staging, env=_env(staging),
                          capture_output=True, text=True, check=False)
    landed = (staging / "rootwrite_probe.txt").exists()
    cells.append({"cell": "S5w/python-c-root-write", "guard": g,
                  "os_write_rc": proc.returncode, "file_landed": landed})
    print(f"== S5w/python-c-root-write guard={g} landed={landed}", flush=True)
    # python -c overwrite guard.py itself
    code2 = 'open("guard.py","a").write("#tamper\\n")'
    g2 = guard_eval(staging, f"python -c '{code2}'")
    cells.append({"cell": "S5w/python-c-append-guard", "guard": g2})
    print(f"== S5w/python-c-append-guard -> {g2}", flush=True)

    # ---- S-5 §5: network shapes (verdicts only, NO real egress) -----------------
    for label, code in (
        ("urllib", 'import urllib.request; print("x")'),
        ("socket", 'import socket; print("x")'),
    ):
        cmd = f"python -c '{code}'"
        cells.append({"cell": f"S5net/{label}", "guard": guard_eval(staging, cmd)})
        print(f"== S5net/{label} -> {cells[-1]['guard']}", flush=True)
    cells.append({"cell": "S5net/curl", "guard": guard_eval(staging, "curl http://example.invalid")})
    print(f"== S5net/curl -> {cells[-1]['guard']}", flush=True)

    report = {"staging_root": str(staging), "cells": cells}
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nREPORT ->", OUT)


if __name__ == "__main__":
    main()
