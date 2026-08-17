"""Substrate fix batch I (2026-08-16) — cleanroom write-surface locks.

Scope: F-55 (fix, both mechanisms) and F-56/F-57 (judged "do not fix" — see
the execution log; the locks here PIN the reasoning, not a code change).

Every lock goes through a REAL entry point: a staging tree built by the real
`build_isolation_workspace`, the STAGED `guard.py` run as a real subprocess
(exactly the PreToolUse hook Claude Code invokes), and — where a test needs
to show what actually lands on disk once guard allows a command — a bare
`python -c` subprocess with no hook in the loop, matching the dispatch's own
repro shape. No function-return-only tests, no monkeypatching of guard.py's
internals, no direct `import` of cv_toolbox/cv_probe (摊 II's territory).
"""

from __future__ import annotations

import json
import shutil
import stat
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


# --------------------------------------------------------------------------
# helpers — all real-entry
# --------------------------------------------------------------------------


def _access_log(staging: Path) -> Path:
    """F-55: mirrors guard.py's own `_audit_dir` name-derivation rule — a
    sibling `<staging.name>.audit` directory, never a descendant of staging."""
    return staging.parent / f"{staging.name}.audit" / "access_log.jsonl"


def _guard_hook(staging: Path, payload: dict) -> subprocess.CompletedProcess:
    """Run the STAGED guard.py's `main()` as a real subprocess — the same
    process shape Claude Code's PreToolUse hook invokes (stdin JSON in,
    exit code 0/2, access_log.jsonl appended as a side effect)."""
    return subprocess.run(
        [sys.executable, str(staging / "guard.py")],
        input=json.dumps(payload),
        text=True,
        cwd=staging,
        capture_output=True,
        check=False,
    )


def _guard_bash(staging: Path, command: str) -> subprocess.CompletedProcess:
    return _guard_hook(staging, {"tool_name": "Bash", "tool_input": {"command": command}})


def _raw_python(staging: Path, code: str) -> subprocess.CompletedProcess:
    """What actually executes on disk once guard has allowed a `python -c`
    call — no hook in this call, exactly the shape the dispatch's own repro
    table used to demonstrate F-55 (`guard 判 allow，实跑真的改了 guard.py`).

    This container runs everything as root (verified: `whoami` -> root for
    the controller, the spawned reader, and every guard subprocess alike),
    and root bypasses DAC permission checks on files it owns — so a plain
    `_raw_python` write is NOT bound by the chmod lockdown below. That is a
    real, tested, documented limitation of this fix in THIS environment (see
    `_lock_down_readonly_surface`'s docstring in isolation.py and
    `test_known_limitation_plain_root_bypasses_the_chmod_lockdown`), not a
    bug in this helper — it is deliberately plain so the relocation-based
    tests below exercise the actual repro shape.
    """
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=staging,
        env=clean_spawn_env(staging),
        capture_output=True,
        text=True,
        check=False,
    )


_SETPRIV = shutil.which("setpriv")


def _nonprivileged_python(staging: Path, code: str) -> subprocess.CompletedProcess:
    """Run `code` with dac_override/dac_read_search/fowner/chown dropped from
    both the bounding and inheritable capability sets — verified on this host
    (2026-08-16) to make even a root-uid process obey ordinary file
    permission bits again. This is the realistic shape "关键文件只读"
    protects: a reader that is not, in fact, an unconstrained root principal
    relative to the files the build wrote. Skips (not xfails — this is an
    environment capability, not a code defect) if `setpriv` is unavailable.
    """
    assert _SETPRIV, "setpriv (util-linux) not found on PATH"
    cmd = [
        _SETPRIV,
        "--bounding-set=-dac_override,-dac_read_search,-fowner,-chown",
        "--inh-caps=-dac_override,-dac_read_search,-fowner,-chown",
        sys.executable, "-c", code,
    ]
    return subprocess.run(
        cmd, cwd=staging, env=clean_spawn_env(staging),
        capture_output=True, text=True, check=False,
    )


requires_setpriv = pytest.mark.skipif(_SETPRIV is None, reason="setpriv (util-linux) not on PATH")


@pytest.fixture()
def staging(tmp_path: Path) -> Path:
    """Preview/unbound build — fresh per test, never merge-eligible."""
    return build_isolation_workspace(CASE_DIR, staging_root=tmp_path / "staging").staging_root


@pytest.fixture()
def formal(tmp_path: Path):
    """Formal (run-bound) build on a private case copy, provisioned first —
    the shape `merge_isolated_output` requires."""
    case_dir = tmp_path / "case"
    shutil.copytree(CASE_DIR, case_dir)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text("", encoding="utf-8")
    provision_view_manifest(case_dir, run_dir)
    manifest = build_isolation_workspace(case_dir, run_dir=run_dir, staging_root=tmp_path / "staging")
    return manifest.staging_root, run_dir


# ==========================================================================
# F-55 — positive: the demonstrated repro no longer works
# ==========================================================================


def test_guard_py_mode_bits_lose_write_permission_after_build(staging: Path):
    """Structural half of dispatch repro #1: after `build_isolation_workspace`
    returns, guard.py's own mode bits carry no owner/group/other write bit —
    the state `_lock_down_readonly_surface` is supposed to put every
    protected file into, verified directly rather than inferred from a
    write's outcome (which, in THIS container, is not solely determined by
    mode bits — see `_raw_python`'s docstring)."""
    mode = stat.S_IMODE((staging / "guard.py").stat().st_mode)
    assert not (mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)), oct(mode)
    # It must still be READABLE and EXECUTABLE — the lockdown removes write,
    # nothing else. The hook still has to run guard.py itself.
    assert mode & stat.S_IRUSR and mode & stat.S_IXUSR, oct(mode)


def test_guards_own_decision_for_the_repro_command_is_unchanged(staging: Path):
    """guard's DECISION for `python -c 'open("guard.py","a")...'` is, by
    design, still "allow" — this batch does not add a scanner rule that
    recognizes "code that writes to a protected path" (see the execution log
    for why: that would just be the A3 capability lockdown coming back from a
    different angle). The fix is what happens to the write AFTER guard
    allows it, covered by the OS-level tests below."""
    code = 'open("guard.py","a").write("# tampered\\n")'
    decision = _guard_bash(staging, f"python -c '{code}'")
    assert decision.returncode == 0


@requires_setpriv
def test_python_c_append_to_guard_py_is_refused_under_a_nonprivileged_process(staging: Path):
    """Dispatch repro #1, exercised the way the fix actually defends against
    it: a process that is not itself an unconstrained root principal
    relative to the files the build wrote — which is what "关键文件只读"
    means as a real access-control boundary, not merely a set of mode bits
    nobody enforces. See `_nonprivileged_python`'s docstring for how this is
    constructed and verified on this host."""
    guard_path = staging / "guard.py"
    before = guard_path.read_bytes()
    code = 'open("guard.py","a").write("# tampered\\n")'
    proc = _nonprivileged_python(staging, code)
    assert proc.returncode != 0, proc.stderr
    assert "Permission" in proc.stderr, proc.stderr
    assert guard_path.read_bytes() == before, "guard.py content must be byte-identical after the attempt"


def test_known_limitation_plain_root_bypasses_the_chmod_lockdown(staging: Path):
    """Honest negative control, kept as a PASSING lock (not xfail — this is a
    documented environment property, not a code defect awaiting a fix): in
    THIS dev container everything, including the simulated reader, runs as
    root, and root bypasses DAC checks on files it owns regardless of mode
    bits. `chattr +i` (which even root cannot write through without first
    clearing the flag) was tried and is unavailable — this container's
    filesystem is overlayfs and refuses FS_IOC_SETFLAGS outright. So the
    chmod half of F-55, exactly as specified by the ratified direction, is a
    real, correct, but currently-not-enforced-in-this-container mechanism —
    this test exists so nobody mistakes silence for the gap being closed.
    See isolation.py's `_lock_down_readonly_surface` docstring for the full
    writeup and the registered follow-up (capability-dropping in
    `spawn_command`, out of scope for this batch)."""
    guard_path = staging / "guard.py"
    mode = stat.S_IMODE(guard_path.stat().st_mode)
    assert not (mode & stat.S_IWUSR), "the mode bit itself is correctly absent"
    proc = _raw_python(staging, 'open("guard.py","a").write("# tampered\\n")')
    assert proc.returncode == 0, (
        "if this fails, the environment changed (no longer plain root, or DAC "
        "is enforced some other way) -- re-verify and consider promoting the "
        "chmod mechanism from 'documented gap' to 'closed' in the execution log"
    )


def test_python_c_write_to_access_log_jsonl_in_staging_root_does_not_touch_the_real_log(
    staging: Path,
):
    """Dispatch repro #2, verbatim: `open("access_log.jsonl","w").write("")`
    used to wipe the real audit trail because the log lived inside the tree
    this command can reach. Populate the real log first (a few real hook
    calls), attempt the erase exactly as staged in the dispatch, then prove
    the real log — now outside staging_root — is untouched: same entry
    count, same last line, denial-free of any 'wipe'."""
    for command in ("ls case_data", "cat case_data/1f_view.png"):
        _guard_bash(staging, command)
    real_log = _access_log(staging)
    assert real_log.exists(), "the real log must exist at its relocated home"
    before_entries = real_log.read_text(encoding="utf-8").splitlines()
    assert len(before_entries) >= 2, "the setup calls above must have logged something"

    code = 'open("access_log.jsonl","w").write("")'
    # guard's own decision is out of scope for this fix (see F-56/F-57
    # writeup for the analogous reasoning) — what matters is the real log.
    _raw_python(staging, code)

    after_entries = real_log.read_text(encoding="utf-8").splitlines()
    assert after_entries == before_entries, "the real audit trail must be unaffected by an attempt aimed at staging_root"
    # The attempt's target was a bare name resolved against staging_root
    # (the reader's cwd), so at most a harmless decoy file appears there —
    # never the real log.
    decoy = staging / "access_log.jsonl"
    if decoy.exists():
        assert decoy.resolve() != real_log.resolve()


def test_access_log_lives_outside_staging_root(staging: Path):
    """Structural check: the real log is not a descendant of staging_root at
    all — not merely write-protected, genuinely off the tree the reader's
    cwd and every reader-visible document (MANIFEST.json,
    input_inventory.json, the kickoff prompt) describe."""
    _guard_bash(staging, "ls case_data")
    real_log = _access_log(staging)
    assert real_log.exists()
    assert not real_log.resolve().is_relative_to(staging.resolve())
    assert not (staging / "access_log.jsonl").exists(), (
        "no file of this name should exist inside staging_root after ordinary use"
    )


@pytest.mark.parametrize(
    "target,code_template",
    [
        ("MANIFEST.json", 'open("MANIFEST.json","a").write("x")'),
        ("isolation_settings.json", 'open("isolation_settings.json","a").write("x")'),
        ("tools/run_cv_probe.py", 'open("tools/run_cv_probe.py","a").write("x")'),
        ("skills/intake_pipeline/0_reading/session_kickoff.md", 'open("skills/intake_pipeline/0_reading/session_kickoff.md","a").write("x")'),
        ("case_data/1f_view.png", 'open("case_data/1f_view.png","ab").write(b"x")'),
    ],
    ids=["manifest", "settings", "wrapper", "skill-doc", "source-image"],
)
def test_other_key_files_lose_their_write_bit_too(staging: Path, target: str, code_template: str):
    """The dispatch's repro named guard.py; the ratified direction says
    "guard.py / tools/ 等关键文件" (et cetera) — everything the builder
    places outside out/+requests/ is in scope, not only the one file that
    happened to be demonstrated. Includes a source drawing (case_data/): an
    accidental overwrite there would silently corrupt what the reading is
    graded against, which is at least as severe as the guard.py repro.
    Structural (mode-bit) check — see the plain-root caveat documented on
    `_raw_python` and the dedicated setpriv/known-limitation tests above for
    what "read-only" does and does not mean in this container."""
    path = staging / target
    mode = stat.S_IMODE(path.stat().st_mode)
    assert not (mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)), f"{target}: {oct(mode)}"


@requires_setpriv
@pytest.mark.parametrize(
    "target,code_template",
    [
        ("MANIFEST.json", 'open("MANIFEST.json","a").write("x")'),
        ("isolation_settings.json", 'open("isolation_settings.json","a").write("x")'),
        ("tools/run_cv_probe.py", 'open("tools/run_cv_probe.py","a").write("x")'),
        ("skills/intake_pipeline/0_reading/session_kickoff.md", 'open("skills/intake_pipeline/0_reading/session_kickoff.md","a").write("x")'),
        ("case_data/1f_view.png", 'open("case_data/1f_view.png","ab").write(b"x")'),
    ],
    ids=["manifest", "settings", "wrapper", "skill-doc", "source-image"],
)
def test_other_key_files_are_refused_under_a_nonprivileged_process(staging: Path, target: str, code_template: str):
    """Behavioural counterpart of the structural test above, under the same
    non-root-equivalent process as `test_python_c_append_to_guard_py_is_
    refused_under_a_nonprivileged_process` — this is where "the write
    actually fails" gets verified, honestly scoped to a process the lockdown
    can actually bind."""
    path = staging / target
    before = path.read_bytes()
    proc = _nonprivileged_python(staging, code_template)
    assert proc.returncode != 0, f"{target}: write must fail under a nonprivileged process: {proc.stderr}"
    assert path.read_bytes() == before, f"{target}: content must be unchanged"


# ==========================================================================
# F-55 — negative (reverse): the reader's legitimate surface still works
# ==========================================================================


def test_legitimate_out_and_requests_writes_still_succeed(staging: Path):
    """The lockdown targets everything OUTSIDE out/+requests/ — confirm the
    two directories the reader is actually meant to write into are
    unaffected, via the exact command shape the reader would issue."""
    for rel in ("out/note.txt", "requests/note.json"):
        code = f'open({rel!r}, "w").write("ok")'
        proc = _raw_python(staging, code)
        assert proc.returncode == 0, (rel, proc.stderr)
        assert (staging / rel).read_text(encoding="utf-8") == "ok"


def test_reader_authored_script_under_out_can_still_be_created_and_run(staging: Path):
    """A3 (2026-08-16, same day) is not being rolled back by this fix: the
    reader may still write and run its own measurement script under out/."""
    (staging / "out" / "measure.py").write_text("print('ok')\n", encoding="utf-8")
    proc = _guard_bash(staging, "python out/measure.py")
    assert proc.returncode == 0, proc.stderr
    real = _raw_python(staging, "exec(open('out/measure.py').read())")
    assert real.returncode == 0 and "ok" in real.stdout


def test_request_json_can_still_be_staged_directly_at_root_by_the_test_harness(staging: Path):
    """Existing test fixtures across this suite (`_request()` in
    test_isolation.py) write a NEW file directly at staging root as test
    SETUP, independent of anything the reader itself does. The lockdown only
    removes the write bit from files that existed at the end of the build —
    creating a brand-new file at root must keep working, or a large share of
    the pre-existing regression suite would break for a reason unrelated to
    this fix's actual target."""
    path = staging / "not_present_at_build_time.json"
    assert not path.exists()
    path.write_text("{}", encoding="utf-8")
    assert path.read_text(encoding="utf-8") == "{}"


def test_real_guard_hook_keeps_appending_to_the_relocated_log_across_many_calls(staging: Path):
    """F-44's contract (allow entries carry tool_input_excerpt/executed_code,
    deny entries keep their excerpt) must survive the relocation untouched —
    this is the property F-55 is protecting, not something it may degrade."""
    calls = [
        ("ls case_data", 0),
        ("python -c 'print(1+1)'", 0),
        ("cat case_tests/x", 2),  # DENY_TOKENS hit
    ]
    for command, expected_rc in calls:
        proc = _guard_bash(staging, command)
        assert proc.returncode == expected_rc, (command, proc.stdout, proc.stderr)

    entries = [
        json.loads(line) for line in _access_log(staging).read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(entries) >= len(calls)
    decisions = [e["decision"] for e in entries[-3:]]
    assert decisions == ["allow", "allow", "deny"]
    py_entry = next(e for e in entries if e["reason"] == "allowed python -c program")
    assert py_entry["executed_code"][0]["path"] == "-c"
    deny_entry = next(e for e in entries if e["decision"] == "deny")
    assert deny_entry.get("tool_input_excerpt")


def test_merge_still_archives_the_relocated_log_and_binds_its_hash(formal):
    """End-to-end through the real merge path: a formal build, one real
    guard-mediated command, then merge — the archived copy under
    isolation_archive/ and the isolation_provenance.json hash/entry-count
    fields must reflect the SAME (relocated) log the run actually used."""
    staging, run_dir = formal
    _guard_bash(staging, "ls case_data")
    real_log_before = _access_log(staging).read_text(encoding="utf-8")

    output = staging / "out" / "output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")
    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output, accept=False)

    archived = attempt_dir / "isolation_archive" / "access_log.jsonl"
    assert archived.exists(), "the archived copy must exist even though it now lives outside staging_root"
    assert archived.read_text(encoding="utf-8") == real_log_before
    # F-55's archive-side fix restores a normal writable file under run_dir —
    # that tree was never meant to be locked down.
    assert stat.S_IMODE(archived.stat().st_mode) & stat.S_IWUSR

    provenance = json.loads((attempt_dir / "isolation_provenance.json").read_text(encoding="utf-8"))
    assert provenance["access_log_entries"] >= 1
    assert provenance["access_log_sha256"], "provenance must hash the RELOCATED log, not an empty/missing one"


# ==========================================================================
# F-56 / F-57 — judged "do not fix": sentinel locks pinning the fail-safe
# backstop the judgment relies on. If either of these ever goes red, the
# reasoning in the execution log no longer holds and the item needs
# reopening — these are not fix-verification locks (there is no fix).
# ==========================================================================


def test_f56_guard_allows_withdrawn_prescan_tool_value_but_wrapper_still_refuses(staging: Path):
    """F-56, current (intentionally unchanged) shape: guard does not
    validate --tool's VALUE (PROBE_TOOL_NAMES is documented as wording-only,
    not a second authorization table), so a withdrawn tool name is allowed
    at the gate. The safety property this "do not fix" judgment depends on
    is that run_cv_probe.ALLOWED_TOOLS remains the SOLE authority and still
    refuses the call — pinned here so a future change to either file cannot
    silently drop the backstop without a test noticing.

    m-1 (2026-08-17 cross-review): this exact scenario is also the
    documented access_log blind spot — guard logs decision="allow" for the
    call below, and the wrapper's refusal that follows leaves NO trace in
    access_log at all (guard fires and appends its entry before the wrapper
    subprocess even starts). A reader of access_log.jsonl who checks only
    the `decision` field would misread this call as having executed. The
    assertion on the log entry below makes that gap explicit rather than
    leaving it undocumented: `decision="allow"` means "guard did not block
    this call", never "this call ran successfully" — telling the two apart
    requires evidence outside access_log entirely (here, the wrapper's own
    returncode/stderr, exactly what this test already checks above)."""
    args = ["--tool", "prescan-plan", "--image", IMG, "--out-dir", "out/f56lock"]
    decision = _guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision.returncode == 0, "guard's tool-value-blind decision is the documented status quo"
    wrapper = subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", *args],
        cwd=staging, env=clean_spawn_env(staging), capture_output=True, text=True, check=False,
    )
    assert wrapper.returncode != 0, "wrapper must remain the sole authority and refuse a withdrawn tool"
    assert "unsupported cv_probe tool" in wrapper.stderr
    assert not list((staging / "out" / "f56lock").rglob("*")) if (staging / "out" / "f56lock").exists() else True

    log_entry = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    assert log_entry["decision"] == "allow", (
        "m-1: access_log records decision=allow for the guard call above even "
        "though the wrapper immediately refused it — decision=allow is not "
        "evidence the tool call executed, only that guard did not block it"
    )


def test_f57_guard_allows_key_tool_mismatch_but_wrapper_argparse_still_refuses(staging: Path):
    """F-57, current (intentionally unchanged) shape: guard's parameter-key
    table is a flat union across all six authorized tools, so a key that
    belongs to a DIFFERENT tool (--axis is wall_line_profiler/
    storey_line_profiler's own option) is allowed through for any tool.
    wrapper's per-tool argparse (deliberately not duplicated into guard —
    see run_cv_probe.py's _direct_to_request docstring) is the backstop this
    judgment relies on; pinned here the same way as the F-56 lock above.
    Uses storey_line_profiler + --axis (grid_B's own exact repro shape):
    storey_line_profiler has no extra required parameters, so a missing-
    required-argument error can't mask the unrecognized-argument one.

    m-1 (2026-08-17 cross-review): same access_log blind spot as the F-56
    lock above — guard's decision="allow" entry for this call predates, and
    says nothing about, the wrapper's refusal below. See that test's
    docstring for the full reasoning; asserted again here so the F-57 half
    of the gap is pinned independently of the F-56 half."""
    args = ["--tool", "storey_line_profiler", "--image", IMG, "--out-dir", "out/f57lock", "--axis", "row"]
    decision = _guard_bash(staging, "python tools/run_cv_probe.py " + " ".join(args))
    assert decision.returncode == 0, "guard's flat key table is the documented status quo"
    wrapper = subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", *args],
        cwd=staging, env=clean_spawn_env(staging), capture_output=True, text=True, check=False,
    )
    assert wrapper.returncode != 0, "wrapper's per-tool argparse must remain the backstop"
    assert "unrecognized arguments" in wrapper.stderr or "unrecognized" in wrapper.stderr

    log_entry = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    assert log_entry["decision"] == "allow", (
        "m-1: access_log records decision=allow for the guard call above even "
        "though the wrapper immediately refused it — decision=allow is not "
        "evidence the tool call executed, only that guard did not block it"
    )
