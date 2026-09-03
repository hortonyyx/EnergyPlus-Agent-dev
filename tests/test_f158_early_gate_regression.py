"""Permanent regression lock for F-158 B-1: the no-billed-calls gate must catch
connections made **before** it would have installed at ``pytest_configure``, and
references **bound before** the wrap — the two carriers the cross-family review
(verdict ``2026-09-03c_f158_crossreview_gpt`` §三.2) used to bypass the gate.

Why a subprocess, not an in-process test
----------------------------------------
Inside the running suite the gate is already installed (it arms at import, first
in ``addopts``), so there is no "before the gate" moment to reproduce in-process.
This lock therefore spawns a fresh ``python -m pytest`` on a tiny generated tree
where a probe plugin is loaded *after* the real gate plugin (``-p
ep_no_billed_gate -p early_probe`` — the same ordering ``addopts`` pins in the
real suite) and:

  * connects at its own module-import time (carrier 1),
  * binds an **instance** ``sock.connect`` reference at import and calls it in a
    test body (carrier 2 — the reviewer's exact shape),
  * binds the **class** ``socket.socket.connect`` attribute at import and calls
    it in a test body (carrier 3 — a *different* early-bypass shape, acceptance
    #3), and
  * connects via ``socket.create_connection`` at import (carrier 4 — another
    different shape).

The inner tests assert every one of those was BLOCKED. With the fix present the
subprocess exits 0. Remove the fix (move ``_install()`` out of import time back
into ``pytest_configure``) and the probe — imported during pre-parse, before any
``pytest_configure`` — reaches the network / binds the real method, the inner
asserts fail, the subprocess exits non-zero, and this lock goes red.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import textwrap
import tomllib

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_gate_plugin_is_pinned_first_in_addopts():
    """Lock the *wiring position*, not just the mechanism.

    The subprocess lock below proves the import-time install stops both carriers
    *when the gate loads before the probe*. But the real suite gets that ordering
    only because ``pyproject.toml`` ``addopts`` pins ``-p ep_no_billed_gate``
    ahead of every other ``-p`` (ini addopts ``-p`` load before PYTEST_ADDOPTS
    and command-line ``-p``). If someone moved it after another ``-p`` — or
    dropped it — the mechanism lock would still pass while the real suite went
    bypassable again. This closes that gap.
    """
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = data["tool"]["pytest"]["ini_options"]["addopts"]
    # Collect the plugin name after each "-p" token, in order.
    p_plugins = [
        addopts[i + 1]
        for i, tok in enumerate(addopts)
        if tok == "-p" and i + 1 < len(addopts)
    ]
    assert "ep_no_billed_gate" in p_plugins, (
        f"gate plugin missing from addopts -p list: {addopts!r}"
    )
    assert p_plugins[0] == "ep_no_billed_gate", (
        f"gate plugin must be the FIRST -p in addopts so it installs before any "
        f"other plugin can bind a pre-gate socket reference; got {p_plugins!r}"
    )

# A probe plugin loaded AFTER the gate. Everything it does happens at module
# import (pre-parse) or binds a reference then, mirroring the review probe.
_EARLY_PROBE = textwrap.dedent(
    """
    import socket
    from ep_no_billed_gate import ProviderCallBlocked

    _TARGET = ("192.0.2.1", 80)  # RFC 5737 TEST-NET-1, never a real provider


    def _classify(call):
        try:
            call()
        except ProviderCallBlocked:
            return "BLOCKED"
        except Exception as exc:  # any other error => the gate did NOT stop it
            return "NOTBLOCKED(%s: %s)" % (type(exc).__name__, exc)
        return "NOTBLOCKED(returned)"


    # carrier 1: import-time connect_ex
    _s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM); _s1.settimeout(0.2)
    IMPORT_CONNECT_EX = _classify(lambda: _s1.connect_ex(_TARGET)); _s1.close()

    # carrier 4: import-time create_connection (a different call surface)
    IMPORT_CREATE_CONNECTION = _classify(
        lambda: socket.create_connection(_TARGET, timeout=0.2)
    )

    # carrier 2: bind an INSTANCE method reference now (the reviewer's shape)
    _s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM); _s2.settimeout(0.2)
    EARLY_BOUND_INSTANCE = _s2.connect

    # carrier 3: bind the CLASS attribute now (a DIFFERENT early-bypass shape)
    EARLY_BOUND_CLASS = socket.socket.connect
    _s3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM); _s3.settimeout(0.2)
    _S3 = _s3
    """
)

_INNER_TEST = textwrap.dedent(
    """
    import early_probe
    from ep_no_billed_gate import ProviderCallBlocked

    _TARGET = ("192.0.2.1", 80)


    def _classify(call):
        try:
            call()
        except ProviderCallBlocked:
            return "BLOCKED"
        except Exception as exc:
            return "NOTBLOCKED(%s: %s)" % (type(exc).__name__, exc)
        return "NOTBLOCKED(returned)"


    def test_import_time_connections_were_blocked():
        assert early_probe.IMPORT_CONNECT_EX == "BLOCKED", early_probe.IMPORT_CONNECT_EX
        assert early_probe.IMPORT_CREATE_CONNECTION == "BLOCKED", (
            early_probe.IMPORT_CREATE_CONNECTION
        )


    def test_pre_bound_instance_reference_is_blocked():
        # carrier 2 — reviewer's exact shape
        assert _classify(lambda: early_probe.EARLY_BOUND_INSTANCE(_TARGET)) == "BLOCKED"


    def test_pre_bound_class_attribute_is_blocked():
        # carrier 3 — a different early-bypass shape (acceptance #3)
        assert (
            _classify(lambda: early_probe.EARLY_BOUND_CLASS(early_probe._S3, _TARGET))
            == "BLOCKED"
        )
    """
)


def _run_child(tmp_path: pathlib.Path) -> subprocess.CompletedProcess:
    (tmp_path / "early_probe.py").write_text(_EARLY_PROBE, encoding="utf-8")
    (tmp_path / "test_inner.py").write_text(_INNER_TEST, encoding="utf-8")

    env = dict(os.environ)
    # ep_no_billed_gate must resolve in the child; early_probe/test_inner resolve
    # from cwd (the tmp tree). Drop inherited addopts so we control -p ordering
    # and don't drag -n/xdist into this tiny run.
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_REPO_ROOT), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    env.pop("PYTEST_ADDOPTS", None)
    # A key present would let a genuine outbound attempt bind — but the whole
    # point is the gate stops it first; still, keep the child key-free.
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_inner.py",
            "-p",
            "ep_no_billed_gate",  # the REAL gate, first (mirrors addopts order)
            "-p",
            "early_probe",  # probe loaded AFTER the gate
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            "-q",
        ],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_early_and_prebound_carriers_are_blocked(tmp_path):
    proc = _run_child(tmp_path)
    detail = (
        f"child rc={proc.returncode}\n"
        f"--- child stdout ---\n{proc.stdout}\n"
        f"--- child stderr ---\n{proc.stderr}"
    )
    # With the fix, all four carriers are blocked -> inner tests pass -> rc 0.
    # Without the fix, the probe reaches the net / binds the real connect at
    # import (before pytest_configure), the inner asserts fail, rc != 0.
    assert proc.returncode == 0, detail
    assert "3 passed" in proc.stdout, detail
