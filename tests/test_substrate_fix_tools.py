"""Substrate fix batch II (2026-08-16): behavioral verification for F-52,
F-54, F-58, F-53 -- tool-face parameter semantics, error operability, and
documentation. Every test in this file goes through the REAL entry point
(``build_isolation_workspace`` + a real ``subprocess`` against the staged
``tools/run_cv_probe.py``), never a direct import of a toolbox function.
This project has already been bitten once by "library-layer tests all green"
not transferring to the sandboxed wrapper shape (F-49 lived unnoticed for
five weeks precisely because of that gap) -- the same discipline that built
``tests/test_substrate_sweep_tools.py`` applies here.

Companion documents:
- Dispatch: AI_agent/logs/reviews/request/2026-08-16_substrate_fix_dispatch_II_tools.md
- Execution log: AI_agent/logs/reviews/execution/2026-08-16_substrate_fix_II_execution_log.md
- Prior sweep (defect registry + repro evidence):
  AI_agent/logs/experiments/2026-08-16_substrate_sweep/{README,grid_A}.md

Each of the four defects gets three kinds of test here:

- **positive**: the call that used to fail now succeeds AND produces the
  arithmetically correct numbers (not just a returncode check -- a "fix"
  that merely stops crashing without computing the right thing must still
  fail these).
- **negative**: a call that already worked keeps working unchanged (no
  regression introduced by the fix).
- **neuter**: temporarily overwrite the REAL, tracked source file with its
  byte-for-byte pre-fix backup (captured under
  ``backup/{src,scripts,Skill}_history/2026-08-16_substrate_fix_II/`` before
  this batch touched anything, per this repo's "back up src/skills before
  editing" discipline), rebuild a FRESH staging so the broken version gets
  copied in (staging copies files at BUILD time, so a staging built before
  the swap would still carry the fix), confirm the exact scenario the
  positive test exercises now fails again the ORIGINAL way, then restore the
  file's exact prior bytes -- verified in Python, not just by inspection --
  even if the test body raises.
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent.execution.isolation import build_isolation_workspace

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = Path("case_tests/e2e_tests/sm21_anchor")
REAL_IMAGE = "case_data/1f_view.png"  # 2133 x 1345 (W x H), staged by every build

BACKUP_DIR = REPO_ROOT / "backup"
F52_REAL = REPO_ROOT / "scripts" / "tool_scripts" / "cv_probe.py"
F52_BACKUP = BACKUP_DIR / "scripts_history" / "2026-08-16_substrate_fix_II" / "cv_probe.py"
F54_REAL = REPO_ROOT / "src" / "agent" / "execution" / "isolation_templates" / "run_cv_probe.py"
F54_BACKUP = BACKUP_DIR / "src_history" / "2026-08-16_substrate_fix_II" / "run_cv_probe.py"
F58_REAL = REPO_ROOT / "src" / "agent" / "reading" / "cv_toolbox" / "tools.py"
F58_BACKUP = BACKUP_DIR / "src_history" / "2026-08-16_substrate_fix_II" / "tools.py"
F53_REAL = REPO_ROOT / "skills" / "intake_pipeline" / "0_reading" / "cv_toolbox.md"
F53_BACKUP = BACKUP_DIR / "Skill_history" / "2026-08-16_substrate_fix_II" / "cv_toolbox.md"


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def staging(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real isolation staging (preview/unbound build), shared read-mostly
    across the positive/negative tests in this file -- each test writes to
    its own ``out/<unique>`` / ``requests/<unique>.json`` names so nothing
    collides. Neuter tests build their OWN fresh staging instead (see
    ``_neutered`` below): this shared one is always built from the FIXED
    source tree and must never be reused after a neuter swap."""

    root = tmp_path_factory.mktemp("f52_54_58_53_staging")
    return build_isolation_workspace(CASE_DIR, staging_root=root / "staging").staging_root


def _fresh_staging(tmp_path: Path) -> Path:
    """A brand-new staging build, for neuter tests: must be called AFTER the
    real source file has been swapped to its pre-fix content, so the copy
    step picks up the broken version."""

    return build_isolation_workspace(CASE_DIR, staging_root=tmp_path / "neuter_staging").staging_root


@contextlib.contextmanager
def _neutered(real_path: Path, backup_path: Path):
    """Temporarily overwrite ``real_path`` with ``backup_path``'s content (the
    pre-fix original), yield, then restore ``real_path``'s CURRENT bytes --
    captured fresh right here, not a hardcoded string -- no matter how the
    ``with`` block exits. Asserts the restore is byte-exact, so a neuter test
    can never leave a dangling repository change even if it fails midway.
    """

    fixed_content = real_path.read_bytes()
    original_content = backup_path.read_bytes()
    assert fixed_content != original_content, (
        f"{real_path} is byte-identical to its pre-fix backup {backup_path} -- "
        "this neuter would be a no-op and prove nothing about the lock"
    )
    real_path.write_bytes(original_content)
    try:
        yield
    finally:
        real_path.write_bytes(fixed_content)
        assert real_path.read_bytes() == fixed_content, (
            f"{real_path} failed to restore to its pre-neuter (fixed) content"
        )


_REQ_COUNTER = {"n": 0}


def _write_request(staging_root: Path, tool: str, args: dict, form: str) -> subprocess.CompletedProcess[str]:
    """``form`` is ``"A"`` (--request, one call) or ``"C"`` (--batch, one
    envelope with a single entry) -- the two forms F-52 names as broken."""

    _REQ_COUNTER["n"] += 1
    name = f"fixII_{_REQ_COUNTER['n']:04d}.json"
    path = staging_root / "requests" / name
    if form == "A":
        path.write_text(json.dumps({"tool": tool, "args": args}), encoding="utf-8")
        flag = "--request"
    else:
        path.write_text(
            json.dumps({"requests": [{"id": "r1", "tool": tool, "args": args}]}),
            encoding="utf-8",
        )
        flag = "--batch"
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", flag, f"requests/{name}"],
        cwd=staging_root, capture_output=True, text=True, check=False,
    )


def _run_direct(staging_root: Path, *cli_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", *cli_args],
        cwd=staging_root, capture_output=True, text=True, check=False,
    )


def _read_sidecar(staging_root: Path, out_dir: str, image_stem: str, tool: str) -> dict:
    evidence_dir = staging_root / out_dir / "cv_evidence" / image_stem
    assert evidence_dir.is_dir(), f"no evidence directory written: {evidence_dir}"
    candidates = [
        p for p in evidence_dir.glob(f"*_{tool}.json") if not p.name.endswith("_overlay.json")
    ]
    assert len(candidates) == 1, sorted(p.name for p in evidence_dir.iterdir())
    return json.loads(candidates[0].read_text(encoding="utf-8"))


# ===========================================================================
# F-52 -- bbox's native JSON array spelling crashes in --request/--batch.
# Fix: scripts/tool_scripts/cv_probe.py::_bbox now also accepts a bracketed
# JSON array, in addition to the existing comma-separated string.
# ===========================================================================


@pytest.mark.parametrize("form", ["A", "C"])
def test_f52_positive_bbox_native_json_array_now_works(staging: Path, form: str) -> None:
    """Was xfail in tests/test_substrate_sweep_tools.py
    (test_s2_bbox_native_json_array_form_a / _form_c): exit code 2,
    'invalid _bbox value'. bbox=[100,80,700,460] -> width 600, height 380."""

    out_dir = f"out/f52_pos_{form}"
    proc = _write_request(
        staging, "crop_zoom",
        {"image": REAL_IMAGE, "out_dir": out_dir, "bbox": [100, 80, 700, 460]},
        form,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir, "1f_view", "crop_zoom")
    assert sidecar["results"][0]["crop_size_px"] == [600, 380]


def test_f52_positive_direct_form_hand_typed_json_array_bracket_also_works(staging: Path) -> None:
    """The fix is at the single point ALL forms converge on (cv_probe.py's
    own --bbox argparse type), not only the wrapper's JSON-serialization
    path -- so a reader who hand-types bracket syntax directly on the CLI
    (a natural thing to try, since --anchors-json/--candidates-json already
    accept this spelling) must also work, not just the --request/--batch
    forms whose native list value happens to route through the same
    json.dumps() output."""

    out_dir = "out/f52_pos_direct_bracket"
    proc = _run_direct(
        staging, "--tool", "crop_zoom", "--image", REAL_IMAGE, "--out-dir", out_dir,
        "--bbox", "[100,80,700,460]",
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, out_dir, "1f_view", "crop_zoom")
    assert sidecar["results"][0]["crop_size_px"] == [600, 380]


def test_f52_negative_bbox_comma_string_form_still_works(staging: Path) -> None:
    """The documented, previously-only-working spelling must be completely
    unaffected: same bbox, string form, both A and C, plus the always-string
    direct form B."""

    for form in ("A", "C"):
        out_dir = f"out/f52_neg_{form}"
        proc = _write_request(
            staging, "crop_zoom",
            {"image": REAL_IMAGE, "out_dir": out_dir, "bbox": "100,80,700,460"},
            form,
        )
        assert proc.returncode == 0, (form, proc.stdout, proc.stderr)
        sidecar = _read_sidecar(staging, out_dir, "1f_view", "crop_zoom")
        assert sidecar["results"][0]["crop_size_px"] == [600, 380]

    out_dir_b = "out/f52_neg_b"
    proc_b = _run_direct(
        staging, "--tool", "crop_zoom", "--image", REAL_IMAGE, "--out-dir", out_dir_b,
        "--bbox", "100,80,700,460",
    )
    assert proc_b.returncode == 0, (proc_b.stdout, proc_b.stderr)
    sidecar_b = _read_sidecar(staging, out_dir_b, "1f_view", "crop_zoom")
    assert sidecar_b["results"][0]["crop_size_px"] == [600, 380]


def test_f52_negative_malformed_bbox_still_gets_argparse_error(staging: Path) -> None:
    """A genuinely bad bbox (wrong element count, non-numeric) must still be
    rejected by cv_probe's own argparse with a clean usage/error (exit code
    2) -- the fix widens ACCEPTANCE, it must not widen what is accepted."""

    proc_len = _run_direct(
        staging, "--tool", "crop_zoom", "--image", REAL_IMAGE, "--out-dir", "out/f52_bad_len",
        "--bbox", "[100,80,700]",
    )
    assert proc_len.returncode == 2, (proc_len.stdout, proc_len.stderr)
    assert "Traceback" not in proc_len.stderr

    proc_nan = _run_direct(
        staging, "--tool", "crop_zoom", "--image", REAL_IMAGE, "--out-dir", "out/f52_bad_nan",
        "--bbox", "not,a,valid,bbox",
    )
    assert proc_nan.returncode == 2, (proc_nan.stdout, proc_nan.stderr)
    assert "Traceback" not in proc_nan.stderr


def test_f52_neuter_reverting_bbox_parser_reproduces_the_original_crash(tmp_path: Path) -> None:
    with _neutered(F52_REAL, F52_BACKUP):
        neuter_staging = _fresh_staging(tmp_path)
        proc = _write_request(
            neuter_staging, "crop_zoom",
            {"image": REAL_IMAGE, "out_dir": "out/f52_neuter", "bbox": [100, 80, 700, 460]},
            "A",
        )
        assert proc.returncode == 2, "expected the pre-fix argparse crash to resurface"
        assert "invalid _bbox value" in proc.stderr, proc.stderr


# ===========================================================================
# F-54 -- run_cv_probe.py::main() has zero exception handling around its own
# parsing/validation. Fix: the whole body (after --help) is wrapped in
# try/except (ValueError, OSError); argparse's own SystemExit paths are
# untouched (SystemExit is not an Exception subclass).
# ===========================================================================


def test_f54_positive_malformed_direct_form_gets_a_clean_error_not_a_traceback(staging: Path) -> None:
    """The dispatch's own repro: a bare '--' token has an empty parameter
    name. Was exit code 1 with a raw Python traceback; must now be exit code
    2 with the SAME message text, no traceback."""

    proc = _run_direct(staging, "--tool", "wall_line_profiler", "--")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr
    assert "probe parameter name is empty" in proc.stderr


@pytest.mark.parametrize(
    "cli_args,expected_message_fragment",
    [
        (("--request", "requests/does_not_exist.json"), "No such file or directory"),
        (("--tool", "crop_zoom", "--image", REAL_IMAGE, "--out-dir", "out/f54_unpaired", "--bbox"),
         "missing its value"),
        (("--tool", "not_a_real_tool", "--image", REAL_IMAGE, "--out-dir", "out/f54_badtool"),
         "unsupported cv_probe tool"),
    ],
)
def test_f54_positive_other_parse_failures_are_also_clean(
    staging: Path, cli_args: tuple[str, ...], expected_message_fragment: str
) -> None:
    """Beyond the dispatch's single repro: every named failure family
    (missing --request file -> OSError from read_text/_resolve, an unpaired
    direct-form flag -> ValueError from _direct_to_request, an unsupported
    tool name -> ValueError from _request_to_argv) must all surface cleanly,
    not just the one exact repro command."""

    proc = _run_direct(staging, *cli_args)
    assert proc.returncode == 2, (cli_args, proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr
    assert expected_message_fragment in proc.stderr, proc.stderr


def test_f54_negative_well_formed_request_still_succeeds(staging: Path) -> None:
    proc = _write_request(
        staging, "wall_line_profiler",
        {"image": REAL_IMAGE, "out_dir": "out/f54_neg_ok", "axis": "col"},
        "A",
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr


def test_f54_negative_argparse_native_errors_are_completely_unaffected(staging: Path) -> None:
    """argparse's own parser.error() path (SystemExit, not one of the two
    caught types) must be byte-for-byte unaffected by wrapping main() in a
    try/except: same usage text, same exit code, same message."""

    proc = _run_direct(staging, "--request")  # missing the required value
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "usage: run_cv_probe.py" in proc.stderr
    assert "expected one argument" in proc.stderr

    proc_help = _run_direct(staging, "--help")
    assert proc_help.returncode == 0, (proc_help.stdout, proc_help.stderr)
    assert "Usage:" in proc_help.stdout


def test_f54_neuter_reverting_the_exception_backstop_reproduces_the_raw_traceback(
    tmp_path: Path,
) -> None:
    with _neutered(F54_REAL, F54_BACKUP):
        neuter_staging = _fresh_staging(tmp_path)
        proc = _run_direct(neuter_staging, "--tool", "wall_line_profiler", "--")
        assert proc.returncode == 1, "expected the pre-fix bare crash (exit 1) to resurface"
        assert "Traceback" in proc.stderr, "expected the pre-fix raw traceback to resurface"
        assert "probe parameter name is empty" in proc.stderr


# ===========================================================================
# F-58 -- overlay_logger raises a bare AttributeError when candidates_json
# has the wrong shape (an envelope dict instead of a bare list, or a list
# containing non-object elements). Fix: src/agent/reading/cv_toolbox/tools.py
# ::overlay_logger validates the shape up front and raises a clean ValueError
# naming what was actually received.
# ===========================================================================


def test_f58_positive_envelope_wrapped_candidates_gets_a_clean_error(staging: Path) -> None:
    """The exact reported shape: {"results": [...]} instead of the documented
    bare [...]. Was a bare 'AttributeError: str object has no attribute get'
    (tools.py:711) with a raw traceback (also exhibiting the F-54 symptom,
    since this exception originates deep inside tool execution) -- must now
    be a clean ValueError naming the actual received type, delivered without
    a traceback thanks to F-54's now-active backstop."""

    wrong_shape = json.dumps(
        {"results": [{"candidate_id": "c1", "status": "accepted", "reason": "x",
                      "geometry": {"kind": "bbox", "bbox_px": [0, 0, 10, 10]}}]}
    )
    proc = _run_direct(
        staging, "--tool", "overlay_logger", "--image", REAL_IMAGE,
        "--out-dir", "out/f58_pos_envelope", "--candidates-json", wrong_shape,
    )
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr
    assert "AttributeError" not in proc.stderr
    assert "must be a JSON array of candidate objects" in proc.stderr
    assert "not a dict" in proc.stderr


def test_f58_positive_non_object_list_element_gets_a_clean_error(staging: Path) -> None:
    """The second failure shape the fix covers: a bare list (correct outer
    shape) whose elements are not objects, e.g. a list of strings."""

    wrong_shape = json.dumps(["not_a_candidate_object"])
    proc = _run_direct(
        staging, "--tool", "overlay_logger", "--image", REAL_IMAGE,
        "--out-dir", "out/f58_pos_nonobject", "--candidates-json", wrong_shape,
    )
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr
    assert "each overlay candidate must be a JSON object" in proc.stderr


def test_f58_negative_valid_candidates_list_still_works(staging: Path) -> None:
    ok_shape = json.dumps(
        [{"candidate_id": "c1", "status": "accepted", "reason": "x",
          "geometry": {"kind": "bbox", "bbox_px": [0, 0, 10, 10]}}]
    )
    proc = _run_direct(
        staging, "--tool", "overlay_logger", "--image", REAL_IMAGE,
        "--out-dir", "out/f58_neg_ok", "--candidates-json", ok_shape,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    sidecar = _read_sidecar(staging, "out/f58_neg_ok", "1f_view", "overlay_logger")
    assert sidecar["results"][0]["decisions"][0]["candidate_id"] == "c1"


def test_f58_negative_existing_no_geometry_check_still_fires_with_its_own_message(
    staging: Path,
) -> None:
    """The PRE-EXISTING deeper validation (a candidate that IS a well-formed
    object but carries no drawable geometry) must keep raising its own
    distinct ValueError, unchanged -- proving the new up-front shape checks
    don't shadow or alter it."""

    no_geometry = json.dumps([{"candidate_id": "c1", "status": "undecided", "reason": "x"}])
    proc = _run_direct(
        staging, "--tool", "overlay_logger", "--image", REAL_IMAGE,
        "--out-dir", "out/f58_neg_nogeom", "--candidates-json", no_geometry,
    )
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "must carry drawable geometry" in proc.stderr


def test_f58_neuter_reverting_the_shape_check_reproduces_the_bare_attribute_error(
    tmp_path: Path,
) -> None:
    """This neuter touches ONLY tools.py -- run_cv_probe.py's F-54 backstop
    stays in its fixed state (a different file, untouched here) but does NOT
    rescue this scenario: AttributeError is not ValueError/OSError, so it is
    not one of the types that backstop catches. The original bare traceback
    must resurface exactly as before, proving F-58's fix -- not F-54's -- is
    what makes this scenario clean, i.e. the two fixes are independent and
    neither is a half-fix riding on the other."""

    with _neutered(F58_REAL, F58_BACKUP):
        neuter_staging = _fresh_staging(tmp_path)
        wrong_shape = json.dumps(
            {"results": [{"candidate_id": "c1", "status": "accepted", "reason": "x",
                          "geometry": {"kind": "bbox", "bbox_px": [0, 0, 10, 10]}}]}
        )
        proc = _run_direct(
            neuter_staging, "--tool", "overlay_logger", "--image", REAL_IMAGE,
            "--out-dir", "out/f58_neuter", "--candidates-json", wrong_shape,
        )
        assert proc.returncode == 1, "expected the pre-fix bare crash (exit 1) to resurface"
        assert "Traceback" in proc.stderr
        assert "AttributeError" in proc.stderr
        assert "'str' object has no attribute 'get'" in proc.stderr


# ===========================================================================
# F-53 -- cv_toolbox.md's --batch example used a `<name>` placeholder that a
# real shell parses as redirection ('<' / '>' are shell metacharacters, not a
# fill-in-the-blank convention). Fix: the doc now names a concrete file
# (requests/sweep.json, matching run_cv_probe.py's own --help text) instead.
# These tests read the doc file DYNAMICALLY from disk on every call (never a
# hardcoded copy of its text), so a neuter of the real file is picked up by
# the SAME test that verifies the fix -- not just by a test-internal
# constant that could silently drift from the file F-53 actually lives in.
# ===========================================================================

_BASH_BLOCK_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)
_BATCH_LINE_RE = re.compile(r"(python tools/run_cv_probe\.py --batch (?P<path>\S+))")
_PLACEHOLDER_RE = re.compile(r"<[a-zA-Z_][a-zA-Z0-9_]*>")


def _read_doc_text() -> str:
    return F53_REAL.read_text(encoding="utf-8")


def _extract_batch_example(doc_text: str) -> tuple[str, str]:
    match = _BATCH_LINE_RE.search(doc_text)
    assert match, "cv_toolbox.md's --batch example line was not found"
    return match.group(1), match.group("path")


def test_f53_positive_doc_batch_example_survives_a_real_shell_and_runs(staging: Path) -> None:
    """Was xfail in tests/test_substrate_sweep_tools.py
    (test_doc_example_batch_placeholder_is_not_shell_safe): the doc's own
    '<name>' text, pasted into a real shell, expanded to '--batch
    requests/' with stdin/stdout redirected to files named 'name' / '.json'
    -- returncode 2, 'cannot open name: No such file'. The fixed doc names a
    concrete file; create it with a minimal valid batch request, then run
    the doc's EXACT current line (read fresh from disk) through a real
    shell, proving both that the shell no longer misparses it AND that the
    resulting invocation actually succeeds end to end."""

    command, referenced_path = _extract_batch_example(_read_doc_text())
    request = {
        "requests": [
            {
                "id": "doc_batch_example",
                "tool": "wall_line_profiler",
                "args": {"image": REAL_IMAGE, "out_dir": "out/f53_pos", "axis": "col"},
            }
        ]
    }
    target = staging / referenced_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(request), encoding="utf-8")

    proc = subprocess.run(command, shell=True, cwd=staging, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, (command, proc.stdout, proc.stderr)
    assert "cannot open name" not in proc.stderr
    out = json.loads(proc.stdout)
    assert out["request_count"] == 1
    assert out["results"][0]["tool"] == "wall_line_profiler"


def test_f53_positive_doc_batch_example_no_longer_contains_a_placeholder() -> None:
    _, referenced_path = _extract_batch_example(_read_doc_text())
    assert not _PLACEHOLDER_RE.search(referenced_path), (
        f"doc's --batch example still references a placeholder-shaped path: {referenced_path!r}"
    )


def test_f53_negative_other_doc_examples_still_run(staging: Path) -> None:
    """A light regression check that fixing the one broken line did not
    disturb the doc's other examples: the wall_line_profiler block (the
    first ```bash block) still runs byte-for-byte as written."""

    blocks = _BASH_BLOCK_RE.findall(_read_doc_text())
    wall_line_block = next(b for b in blocks if "wall_line_profiler" in b)
    proc = subprocess.run(
        wall_line_block, shell=True, cwd=staging, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, (wall_line_block, proc.stdout, proc.stderr)


def test_f53_negative_no_other_bash_block_has_an_unquoted_angle_bracket_placeholder() -> None:
    """The dispatch's 'while you're in there' ask: sweep every OTHER
    executable block in the doc for the same failure shape. A bare
    <name>-shaped token OUTSIDE quotes is exactly F-53's failure mode --
    shell redirection, not fill-in-the-blank. Tokens inside single/double
    quotes are excluded because quoting makes '<'/'>' literal characters,
    not redirection operators (verified against both the fixed doc, where
    this must find nothing, and the pre-fix backup, where it must find
    exactly the one known offender -- see the neuter test below)."""

    for block in _BASH_BLOCK_RE.findall(_read_doc_text()):
        unquoted = re.sub(r"'[^']*'", "", block)
        unquoted = re.sub(r'"[^"]*"', "", unquoted)
        matches = _PLACEHOLDER_RE.findall(unquoted)
        assert not matches, f"unquoted angle-bracket placeholder(s) {matches} in block:\n{block}"


def test_f53_neuter_reverting_the_doc_reproduces_the_shell_misparse(tmp_path: Path) -> None:
    with _neutered(F53_REAL, F53_BACKUP):
        # The doc content is the only thing that changed; the wrapper itself
        # is untouched, so a fresh staging is not required for behavior, but
        # building one anyway keeps this test's shape identical to the
        # others and costs little.
        neuter_staging = _fresh_staging(tmp_path)
        command, _ = _extract_batch_example(_read_doc_text())
        assert "<name>" in command, "neuter did not restore the pre-fix placeholder text"
        proc = subprocess.run(
            command, shell=True, cwd=neuter_staging, capture_output=True, text=True, check=False,
        )
        assert proc.returncode != 0, "expected the pre-fix shell misparse to resurface"
        assert "cannot open name" in proc.stderr, proc.stderr

        # And the general sweep must find exactly this one offender again.
        offenders = []
        for block in _BASH_BLOCK_RE.findall(_read_doc_text()):
            unquoted = re.sub(r"'[^']*'", "", block)
            unquoted = re.sub(r'"[^"]*"', "", unquoted)
            offenders.extend(_PLACEHOLDER_RE.findall(unquoted))
        assert offenders == ["<name>"], offenders
