"""Substrate sweep B — policy-side locks (S-4 guard<->wrapper consistency,
S-5 sandbox environment, S-6 evidence retention).

Every lock goes through the REAL entry points: a staging built by
``build_isolation_workspace``, the STAGED ``guard.py`` evaluated in a subprocess
(so ``_staging_root()`` is the real staging root), and the STAGED
``tools/run_cv_probe.py`` executed by subprocess. No function-return-only tests.

xfail(strict=True) locks assert the CORRECT behaviour that the current defect
violates: while the defect stands the assertion fails (xfail); once it is fixed
the assertion passes and strict mode turns the test red to demand promotion to a
plain lock. Current buggy behaviour is never asserted as expected.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.agent.execution.isolation import (  # noqa: E402
    build_isolation_workspace,
    clean_spawn_env,
    merge_isolated_output,
)
from src.agent.execution.view_manifest import provision_view_manifest  # noqa: E402

CASE_DIR = REPO / "case_tests" / "e2e_tests" / "sm21_anchor"
IMG = "case_data/1f_view.png"
SIX_TOOLS = (
    "crop_zoom",
    "wall_line_profiler",
    "storey_line_profiler",
    "px_m_calibrator",
    "window_cc_detector",
    "overlay_logger",
)
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


# --------------------------------------------------------------------------
# helpers — all real-entry
# --------------------------------------------------------------------------


def _env(staging: Path) -> dict:
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": "/tmp",
        "PYTHONPATH": str(staging),
    }


def guard_eval(staging: Path, payload: dict) -> tuple[str, str]:
    """Run the STAGED guard.evaluate in a subprocess (real _staging_root)."""
    driver = (
        "import json,sys; sys.path.insert(0, sys.argv[1]); import guard; "
        "payload = json.loads(sys.stdin.read()); "
        "d, r, p = guard.evaluate(payload); "
        "print(json.dumps({'decision': d, 'reason': r}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", driver, str(staging)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=staging,
        check=False,
    )
    assert proc.returncode == 0, f"guard driver failed: {proc.stderr}"
    out = json.loads(proc.stdout)
    return out["decision"], out["reason"]


def guard_bash(staging: Path, command: str) -> tuple[str, str]:
    return guard_eval(
        staging, {"tool_name": "Bash", "tool_input": {"command": command}}
    )


def run_wrapper(staging: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", *args],
        capture_output=True,
        text=True,
        cwd=staging,
        env=_env(staging),
        check=False,
    )


def access_log(staging: Path) -> Path:
    """F-55: access_log.jsonl no longer lives under staging_root — relocated
    to a sibling `<staging.name>.audit` directory so the reader's own
    OS-level writes cannot reach it (see guard.py's `_audit_dir`)."""
    return staging.parent / f"{staging.name}.audit" / "access_log.jsonl"


@pytest.fixture(scope="module")
def staging(tmp_path_factory):
    root = tmp_path_factory.mktemp("substrateB") / "staging"
    # strict: these assert the guard POLICY's judgment (deny shapes, F-44's
    # deny-entry contract). The shipping default is "observe", which computes
    # the same verdict and declines to enforce it (CLAUDE.md §0.4#1).
    manifest = build_isolation_workspace(
        CASE_DIR, staging_root=root, guard_profile="strict"
    )
    s = manifest.staging_root
    (s / "requests" / "anchors.json").write_text(json.dumps(ANCHORS))
    (s / "requests" / "cand.json").write_text(json.dumps(CANDIDATES))
    return s


@pytest.fixture()
def formal_staging(tmp_path: Path):
    """Formal (run-bound) build on a private case copy, provisioned first."""
    case_dir = tmp_path / "case"
    shutil.copytree(CASE_DIR, case_dir)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text("", encoding="utf-8")
    provision_view_manifest(case_dir, run_dir)
    manifest = build_isolation_workspace(
        case_dir, run_dir=run_dir, staging_root=tmp_path / "staging"
    )
    return manifest.staging_root, run_dir


def _real_views() -> dict:
    return json.loads(
        (
            CASE_DIR
            / "run_2026-06-20_gpt54_reading"
            / "0_reading"
            / "attempts"
            / "002"
            / "output.json"
        ).read_text(encoding="utf-8")
    )


# --------------------------------------------------------------------------
# G1 — six authorized tools x three forms: both sides pass
# --------------------------------------------------------------------------


def test_g1_six_tools_three_forms_guard_and_wrapper_agree(staging: Path):
    for tool in SIX_TOOLS:
        extra = ["--anchors-json", "requests/anchors.json"] if tool == "px_m_calibrator" else []
        if tool == "overlay_logger":
            extra = ["--candidates-json", "requests/cand.json"]
        if tool == "crop_zoom":
            extra = ["--bbox", "100,100,400,400"]
        if tool == "wall_line_profiler":
            extra = ["--axis", "row"]
        out_dir = f"out/g1lock_{tool}"
        args = ["--tool", tool, "--image", IMG, "--out-dir", out_dir, *extra]
        decision, _ = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
        assert decision == "allow", f"{tool}: guard must allow the authorized direct form"
        proc = run_wrapper(staging, args)
        assert proc.returncode == 0, f"{tool}: wrapper failed: {proc.stderr[-400:]}"
        sidecar_dir = staging / "out" / Path(out_dir).relative_to("out")
        sidecars = list(sidecar_dir.rglob("*.json")) if sidecar_dir.exists() else []
        assert sidecars, f"{tool}: wrapper rc=0 but no sidecar landed under {out_dir}"


def test_g1_request_and_batch_forms_pass(staging: Path):
    for form in ("request", "batch"):
        req_args = {"image": IMG, "out_dir": f"out/g1_{form}"}
        req_args["bbox"] = "100,100,400,400"
        payload = {"tool": "crop_zoom", "args": req_args}
        name = f"g1lock_{form}.json"
        if form == "request":
            (staging / "requests" / name).write_text(json.dumps(payload))
            args = ["--request", f"requests/{name}"]
        else:
            (staging / "requests" / name).write_text(
                json.dumps({"requests": [{"id": "lock1", **payload}]})
            )
            args = ["--batch", f"requests/{name}"]
        decision, _ = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
        assert decision == "allow", f"{form}: guard must allow"
        proc = run_wrapper(staging, args)
        assert proc.returncode == 0, f"{form}: wrapper failed: {proc.stderr[-400:]}"


def test_g1b_inline_anchors_json_direct_form_passes(staging: Path):
    """F-49 regression shape: inline JSON anchors on the direct form must run
    on BOTH sides (guard allow + wrapper rc=0)."""
    inline = json.dumps(ANCHORS, separators=(",", ":"))
    args = [
        "--tool", "px_m_calibrator", "--image", IMG, "--out-dir", "out/g1b_inline",
        "--anchors-json", inline,
    ]
    decision, _ = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision == "allow"
    proc = run_wrapper(staging, args)
    assert proc.returncode == 0, f"inline anchors form broken: {proc.stderr[-400:]}"


# --------------------------------------------------------------------------
# G3/G4 — escapes denied by BOTH sides
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "out_dir",
    ["tools/x", "requests/x", "/tmp/x", "out/../tools"],
    ids=["tools", "requests", "abs-tmp", "traversal"],
)
def test_g3_out_dir_escapes_denied_by_both_sides(staging: Path, out_dir: str):
    args = ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", out_dir]
    decision, reason = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision == "deny", f"guard must deny out_dir={out_dir}"
    assert reason
    proc = run_wrapper(staging, args)
    assert proc.returncode != 0, f"wrapper must refuse out_dir={out_dir}"


@pytest.mark.parametrize(
    "image,prepare",
    [
        ("/etc/passwd", None),
        ("../x.png", None),
        ("~/x.png", None),
        ("lnk4.png", "symlink"),
    ],
    ids=["absolute", "dotdot", "tilde", "symlink"],
)
def test_g4_image_escapes_denied_by_both_sides(staging: Path, image: str, prepare):
    if prepare == "symlink":
        (staging / "lnk4.png").symlink_to("/etc/hostname")
    args = ["--tool", "storey_line_profiler", "--image", image, "--out-dir", "out/g4lock"]
    decision, _ = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision == "deny", f"guard must deny image={image}"
    proc = run_wrapper(staging, args)
    assert proc.returncode != 0, f"wrapper must refuse image={image}"


# --------------------------------------------------------------------------
# G6 — batch envelope edges: both deny, zero sidecars
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "requests",
    [
        pytest.param([{"id": f"r{i:02d}", "tool": "storey_line_profiler",
                       "args": {"image": IMG, "out_dir": "out/g6lock"}} for i in range(33)],
                     id="33-entries"),
        pytest.param([{"id": "same", "tool": "storey_line_profiler",
                       "args": {"image": IMG, "out_dir": "out/g6lock"}},
                      {"id": "same", "tool": "storey_line_profiler",
                       "args": {"image": IMG, "out_dir": "out/g6lock"}}], id="dup-id"),
        pytest.param([{"id": "bad id!", "tool": "storey_line_profiler",
                       "args": {"image": IMG, "out_dir": "out/g6lock"}}], id="bad-id"),
        pytest.param([], id="empty"),
        pytest.param([{"id": "a", "tool": "storey_line_profiler",
                       "args": {"image": IMG, "out_dir": "out/g6lock"}},
                      {"id": "b", "tool": "storey_line_profiler",
                       "args": {"image": IMG, "out_dir": "tools/escape"}}], id="partial-illegal"),
    ],
)
def test_g6_batch_edges_denied_and_zero_sidecars(staging: Path, requests: list):
    name = f"g6lock_{requests and abs(id(requests)) % 100000 or 0}.json"
    (staging / "requests" / name).write_text(json.dumps({"requests": requests}))
    args = ["--batch", f"requests/{name}"]
    decision, _ = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision == "deny", "guard must deny a malformed/oversized batch"
    g6_dir = staging / "out" / "g6lock"
    proc = run_wrapper(staging, args)
    assert proc.returncode != 0, "wrapper must refuse the batch too"
    produced = list(g6_dir.rglob("*.json")) if g6_dir.exists() else []
    assert not produced, f"invalid batch must produce ZERO sidecars, found {produced}"


# --------------------------------------------------------------------------
# G7 — malformed direct args: both deny
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "args",
    [
        ["--tool", "crop_zoom", "crop_zoom", "--image", IMG, "--out-dir", "out/g7lock"],
        ["--tool", "crop_zoom", "--image", IMG, "--image", IMG, "--out-dir", "out/g7lock"],
        ["--tool", "crop_zoom", "--image"],
        ["--image", IMG, "--out-dir", "out/g7lock"],
        ["--tool", "crop_zoom", "--out-dir", "out/g7lock"],
    ],
    ids=["bare-arg", "dup-param", "missing-value", "no-tool", "no-image"],
)
def test_g7_malformed_direct_args_denied_by_both_sides(staging: Path, args: list):
    decision, _ = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision == "deny", f"guard must deny malformed args {args}"
    proc = run_wrapper(staging, args)
    assert proc.returncode != 0, f"wrapper must refuse malformed args {args}"


# --------------------------------------------------------------------------
# G8 — parameter-key audit, both directions, mechanically derived
# --------------------------------------------------------------------------


def _cv_probe_tool_keys() -> dict[str, set[str]]:
    src = (REPO / "scripts" / "tool_scripts" / "cv_probe.py").read_text(encoding="utf-8")
    common_src = src.split("def _common(")[1].split("\n\ndef ")[0]
    common = {m.group(1).replace("-", "_")
              for m in re.finditer(r'add_argument\("--([a-z0-9-]+)"', common_src)}
    body = src.split("def build_parser(")[1]
    per_tool: dict[str, set[str]] = {}
    current = None
    for line in body.splitlines():
        m = re.search(r'add_parser\("([a-z_-]+)"\)', line)
        if m:
            current = m.group(1)
            per_tool[current] = set(common) | {"tool"}
            continue
        m = re.search(r'add_argument\("--([a-z0-9-]+)"', line)
        if m and current is not None:
            per_tool[current].add(m.group(1).replace("-", "_"))
    return per_tool


def _guard_direct_keys() -> tuple[str, ...]:
    src = (
        REPO / "src" / "agent" / "execution" / "isolation_templates" / "guard.py"
    ).read_text(encoding="utf-8")
    m = re.search(r"PROBE_DIRECT_PARAM_KEYS = \((.*?)\n\)", src, re.DOTALL)
    return tuple(re.findall(r'"([a-z0-9_]+)"', m.group(1)))


def test_g8_dead_keys_and_no_missing_keys():
    per_tool = _cv_probe_tool_keys()
    guard_keys = set(_guard_direct_keys())
    authorized = {"crop_zoom", "wall_line_profiler", "storey_line_profiler",
                  "px_m_calibrator", "window_cc_detector", "overlay_logger"}
    withdrawn = {"prescan-plan", "prescan-elevation"}
    accepted = set().union(*(per_tool[t] for t in authorized))

    # Direction B first: every key an authorized tool accepts must be guard-known.
    missing = sorted(accepted - guard_keys)
    assert not missing, f"authorized tools accept keys the guard denies: {missing}"

    # Direction A: the guard-only keys are exactly the five prescan leftovers.
    dead = sorted(guard_keys - accepted)
    assert dead == ["capability_profile", "label", "min_line_len_px",
                    "min_strength", "no_cc"], (
        f"guard dead-key surface changed: {dead}"
    )
    withdrawn_only = set().union(*(per_tool[t] for t in withdrawn))
    assert set(dead) <= withdrawn_only, "dead keys must belong only to withdrawn tools"


def test_g8_wrapper_boolean_flag_keys_are_dead_surface():
    src = (
        REPO / "src" / "agent" / "execution" / "isolation_templates" / "run_cv_probe.py"
    ).read_text(encoding="utf-8")
    m = re.search(r"BOOLEAN_FLAG_KEYS = \{(.*?)\}", src, re.DOTALL)
    flags = set(re.findall(r'"([a-z0-9_]+)"', m.group(1)))
    per_tool = _cv_probe_tool_keys()
    authorized = {"crop_zoom", "wall_line_profiler", "storey_line_profiler",
                  "px_m_calibrator", "window_cc_detector", "overlay_logger"}
    accepted = set().union(*(per_tool[t] for t in authorized))
    assert flags <= {"no_cc"}, f"BOOLEAN_FLAG_KEYS grew: {flags}"
    assert not (flags & accepted), "boolean flags should only serve withdrawn prescan"


# --------------------------------------------------------------------------
# G9 — sidecar semantics on repeated calls
# --------------------------------------------------------------------------


def test_g9_sidecar_semantics(staging: Path):
    args = ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", "out/g9lock",
            "--sidecar-name", "001_g9lock"]
    decision, _ = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision == "allow"
    assert run_wrapper(staging, args).returncode == 0
    second = run_wrapper(staging, args)
    assert second.returncode != 0
    assert "sidecar already exists" in second.stderr

    auto_args = ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", "out/g9auto"]
    assert run_wrapper(staging, auto_args).returncode == 0
    assert run_wrapper(staging, auto_args).returncode == 0
    names = sorted(p.name for p in (staging / "out" / "g9auto").rglob("*.json"))
    assert names == [
        "001_storey_line_profiler.json",
        "002_storey_line_profiler.json",
    ], f"auto allocation must be append-only, got {names}"


# --------------------------------------------------------------------------
# G2 / F-53B — withdrawn prescan: guard SHOULD deny (currently allows -> xfail)
# --------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="F-53B: guard allows withdrawn prescan tools "
                                       "(no --tool value check; prescan keys still listed)")
@pytest.mark.parametrize("form", ["direct", "request"])
def test_f53b_withdrawn_prescan_should_be_denied_by_guard(staging: Path, form: str):
    if form == "direct":
        args = ["--tool", "prescan-plan", "--image", IMG, "--out-dir", "out/g2lock"]
    else:
        (staging / "requests" / "g2lock.json").write_text(json.dumps(
            {"tool": "prescan-plan", "args": {"image": IMG, "out_dir": "out/g2lock"}}))
        args = ["--request", "requests/g2lock.json"]
    decision, _ = guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision == "deny", (
        "guard should refuse what the wrapper refuses (withdrawn prescan)"
    )


def test_f53b_wrapper_still_refuses_prescan(staging: Path):
    """The wrapper side of G2 (current, correct behaviour — a plain lock)."""
    args = ["--tool", "prescan-elevation", "--image", IMG, "--out-dir", "out/g2lock"]
    proc = run_wrapper(staging, args)
    assert proc.returncode != 0
    assert "unsupported cv_probe tool" in proc.stderr


# --------------------------------------------------------------------------
# S-5 — environment
# --------------------------------------------------------------------------


def test_s5_interpreter_and_libraries_in_reader_env(staging: Path):
    env = clean_spawn_env(staging)
    proc = subprocess.run(
        ["python", "-c", "import sys; print(sys.executable)"],
        capture_output=True, text=True, cwd=staging, env=env, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    reader_python = proc.stdout.strip()
    # Locks the measured fact (2026-08-16): the reader's PATH resolves python to
    # the working /opt/venv interpreter. Red here = environment changed —
    # re-verify rather than blindly updating.
    assert reader_python == "/opt/venv/bin/python", (
        f"reader env python changed to {reader_python} — the repo .venv has a "
        "broken numpy; re-run B_evidence/s5_env_probe.py and re-check"
    )
    for lib in ("numpy", "PIL", "scipy"):
        check = subprocess.run(
            ["python", "-c", f"import {lib}"],
            capture_output=True, text=True, cwd=staging, env=env, check=False,
        )
        assert check.returncode == 0, (
            f"cv_toolbox.md declares {lib} available but reader env fails: {check.stderr}"
        )


@pytest.mark.parametrize(
    "command",
    [
        "python -c 'import urllib.request; print(1)'",
        "python -c 'import socket; print(1)'",
        "curl http://example.invalid",
    ],
    ids=["urllib", "socket", "curl"],
)
def test_s5_network_shapes_denied(staging: Path, command: str):
    decision, reason = guard_bash(staging, command)
    assert decision == "deny", f"network shape must be denied: {command}"
    assert "network" in reason or "allowlisted" in reason


@pytest.mark.parametrize(
    "target,expected",
    [
        ("out/w.txt", "allow"),
        ("requests/w.json", "allow"),
        ("w_root.txt", "deny"),
        ("tools/w.py", "deny"),
        ("case_data/w.png", "deny"),
        ("guard.py", "deny"),
        ("MANIFEST.json", "deny"),
    ],
)
def test_s5_write_tool_surface(staging: Path, target: str, expected: str):
    decision, reason = guard_eval(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": target, "content": "x"}},
    )
    assert decision == expected, f"Write {target}: expected {expected}, got {reason}"


@pytest.mark.xfail(strict=True, reason="F-52B: guard allows python -c to write the "
                                       "staging root (OS-level write surface unguarded)")
def test_f52b_python_c_root_write_should_be_denied(staging: Path):
    code = 'open("f52b_probe.txt","w").write("x")'
    target = staging / "f52b_probe.txt"
    target.unlink(missing_ok=True)
    decision, _ = guard_bash(staging, f"python -c '{code}'")
    assert decision == "deny", "python -c writing outside out/ and requests/ should be denied"
    proc = subprocess.run([sys.executable, "-c", code], cwd=staging, env=_env(staging),
                          capture_output=True, text=True, check=False)
    assert not (target.exists() and proc.returncode == 0), "file must not land in staging root"
    target.unlink(missing_ok=True)


# --------------------------------------------------------------------------
# S-6 — evidence retention
# --------------------------------------------------------------------------


def test_f44_access_log_allow_carries_excerpt_and_executed_code(staging: Path):
    log = access_log(staging)
    hooks = [
        {"tool_name": "Bash", "tool_input": {
            "command": f"python tools/run_cv_probe.py --tool storey_line_profiler "
                       f"--image {IMG} --out-dir out/f44lock"}},
        {"tool_name": "Bash", "tool_input": {"command": "python -c 'print(1+1)'"}},
        {"tool_name": "Write", "tool_input": {"file_path": "out/f44.md", "content": "hello"}},
        {"tool_name": "Bash", "tool_input": {"command": "cat case_tests/x"}},
    ]
    for payload in hooks:
        subprocess.run(
            [sys.executable, str(staging / "guard.py")],
            input=json.dumps(payload), text=True, cwd=staging,
            capture_output=True, check=False,
        )
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    assert len(entries) >= 4
    by_reason = {e["reason"]: e for e in entries}
    wrapper_entry = next(e for e in entries
                         if e["decision"] == "allow" and "run_cv_probe" in e["reason"])
    assert wrapper_entry.get("tool_input_excerpt"), "allow entries must carry the excerpt (F-44)"
    py_entry = next(e for e in entries if e["reason"] == "allowed python -c program")
    executed = py_entry.get("executed_code") or []
    assert executed and executed[0]["path"] == "-c" and executed[0]["sha256"], (
        "python -c allow entries must carry executed_code sha256 (F-44)"
    )
    write_entry = next(e for e in entries if e["reason"] == "allowed")
    assert "hello" in (write_entry.get("tool_input_excerpt") or ""), (
        "Write allow entries must record the content"
    )
    deny_entry = next(e for e in entries if e["decision"] == "deny")
    assert deny_entry.get("tool_input_excerpt"), "deny entries keep their excerpt"


@pytest.mark.xfail(strict=True, reason="F-35: CV sidecars do not reach the attempt "
                                       "after merge (only 4 whitelist files archived)")
def test_f35_cv_evidence_should_reach_attempt(formal_staging):
    staging, run_dir = formal_staging
    proc = run_wrapper(staging, ["--tool", "storey_line_profiler",
                                 "--image", IMG, "--out-dir", "out/cv"])
    assert proc.returncode == 0, proc.stderr[-300:]
    sidecars = list((staging / "out" / "cv").rglob("*.json"))
    assert sidecars, "probe produced no sidecar — fixture broken"
    (staging / "out" / "output.json").write_text(
        json.dumps({"views": _real_views()}), encoding="utf-8")
    (staging / "out" / "reading_summary.md").write_text("s", encoding="utf-8")
    attempt_dir = merge_isolated_output(staging, run_dir)
    archived = list(attempt_dir.rglob("*storey_line_profiler*.json"))
    assert archived, (
        "CV evidence produced during the isolated run must be archived into the "
        "attempt, otherwise it is lost with the staging tree (F-35)"
    )


def test_f50_partial_archive_gates(formal_staging):
    """Per-image partial shape is refused whole; aggregate partial shape is
    filed but NOT accepted. These gates themselves are designed behaviour —
    F-50's gap is that the kickoff-taught per-image form has NO mid-state
    archive channel at all."""
    staging, run_dir = formal_staging
    (staging / "out" / "1f_view.json").write_text(
        json.dumps(_real_views()["1f_view"]), encoding="utf-8")
    with pytest.raises(ValueError, match="missing per-image view files"):
        merge_isolated_output(staging, run_dir)
    assert not (run_dir / "0_reading" / "attempts").exists() or \
        not list((run_dir / "0_reading" / "attempts").iterdir()), \
        "refused merge must leave zero attempts behind"

    # same staging, now the aggregate shape with one view
    (staging / "out" / "1f_view.json").unlink()
    (staging / "out" / "output.json").write_text(
        json.dumps({"views": {"1f_view": _real_views()["1f_view"]}}), encoding="utf-8")
    attempt_dir = merge_isolated_output(staging, run_dir)
    checks = json.loads((attempt_dir / "checks.json").read_text(encoding="utf-8"))
    cov = next(r for r in checks["results"]
               if r["check_id"] == "reading.view_manifest_coverage")
    assert cov["status"] == "fail"
    assert len(cov["evidence"]["missing_expected_output_ids"]) == 5
    from src.agent.execution.manifest import load_run_manifest
    assert load_run_manifest(run_dir).accepted("0_reading") is None, \
        "coverage-failing merge must be filed but never accepted"
