"""F-158 — stop a real, *billed* provider call in the test suite, installed
**before any test-owned code can run**.

Honesty about the shape of the promise (T2)
-------------------------------------------
Under the **default startup configuration** a billed provider call is structurally
impossible: ``pyproject.toml`` ``addopts`` pins ``-p ep_no_billed_gate`` first and
``tests/conftest.py`` re-imports this module, so the gate is armed before any test
body runs. It is **not** true, however, that *no test can ever* reach the network
regardless of how pytest is started: a different startup config can drop the pin
(``-o addopts=``, a ``PYTEST_ADDOPTS`` override, ``-c <other config>``, a foreign
rootdir with no ``tests/conftest.py`` …). Those do not fail silently — the
behavioural self-check ``tests/test_f158_gate_behavioral_selfcheck.py`` actually
attempts an outbound connection at run time and goes **red** for any run whose
gate is off, naming the startup config as the cause.

That self-check is a **detector, not an interceptor**: it guarantees you *see*
red, but a test that ran *before* it in a gate-off process and truly reached the
network has already spent the money. Preventing that (as opposed to reporting it)
would need a process/OS-layer deny, out of scope for the test harness.

Why this lives in a repo-root plugin instead of ``tests/conftest.py``
--------------------------------------------------------------------
The first version installed the gate in ``pytest_configure`` (from
``tests/conftest.py``). A cross-family review (verdict
``2026-09-03c_f158_crossreview_gpt``) showed that is too late along **two
carriers that are really one root cause — "the gate installs later than some
executable import"**:

  1. a plugin imported *before* ``pytest_configure`` (e.g. ``-p some_probe`` on
     the command line) can open a connection at its own module-import time;
  2. that same early plugin can capture a **bound** ``sock.connect`` reference
     *before* the gate wraps the class attribute, then call it from a test body
     and slip past the wrapper.

Both collapse to timing: a class-attribute wrap only guards calls whose *binding
happens after* the wrap. So the fix is not "block that one probe shape" — it is
**install the gate earlier than any test-owned import can run**, so that:

  * carrier 1 (import-time connect): the wrapper is already live when the later
    plugin imports, so its import-time connect is caught;
  * carrier 2 (pre-bound reference): the later plugin can only ever bind the
    *already-wrapped* method, so a stashed reference still funnels through the
    gate.

Mechanism (pinned load order, per the verdict's own remedy)
-----------------------------------------------------------
pytest imports ``-p`` plugins during *pre-parse*, in this order: ini
``addopts`` first, then ``PYTEST_ADDOPTS``, then the command line — all *before*
any initial ``conftest.py``. ``pyproject.toml`` therefore pins
``addopts = [... "-p", "ep_no_billed_gate"]``, which makes this module the very
first user plugin imported in every run (master **and** each xdist worker). The
gate is installed **at import of this module** (bottom of file), before that
``-p`` list reaches any command-line probe and before any conftest. Empirically
verified: an ``addopts``/``PYTEST_ADDOPTS`` ``-p`` gate imports and installs
before a command-line ``-p`` probe, and a reference the probe binds afterwards
is the wrapped one.

Residual gap (honest): a caller that ran **before this module was imported at
all** — i.e. interpreter start-up code such as a ``sitecustomize`` /
``usercustomize`` / ``.pth`` line, or a plugin pinned *earlier* than this one in
``addopts`` — could still bind the real ``connect``. Nothing test-owned loads
that early once this plugin is first in ``addopts``; defeating start-up-time code
requires a process/OS-layer deny (seccomp / ``LD_PRELOAD``) and is out of scope
for the test harness. Also unaffected: a client that reaches the kernel through
a C-level / io_uring path that never calls ``socket.socket.connect`` — the real
provider path does not.

Seam (why the network-egress point, not "constructing a client")
----------------------------------------------------------------
The gate wraps ``socket.socket.connect`` / ``socket.socket.connect_ex`` — the
point where bytes would leave for a remote host — not the point where an LLM
client object is built. Constructing a client costs nothing and several tests
legitimately build one; only *emitting a request to a routable remote* bills the
shared DeepSeek balance (CLAUDE.md §5#10). ``socket.connect`` is also provider-
and HTTP-library-agnostic: the real billed path is
``langchain_openai -> openai SDK -> httpx -> httpcore -> socket.create_connection``,
and ``create_connection`` builds a socket and calls ``.connect()`` on it;
``urllib``/``urllib3``/``requests``/``httpx`` all funnel through the same class
method. => the thing measured cannot be swapped out by changing HTTP client
library. ``tests/test_no_billed_provider_calls.py`` pins raw ``socket``,
``socket.create_connection`` and ``urllib`` explicitly, and
``tests/test_f158_early_gate_regression.py`` pins the two early-bypass carriers
above.

Locality test
-------------
``_is_local`` uses ``ipaddress`` rather than a ``startswith("127.")`` prefix, so
IPv6 loopback ``::1``, IPv4-mapped ``::ffff:127.0.0.1`` and the whole
127.0.0.0/8 block are recognised, and a real external address is never mis-read
as local.

The only exit is an explicit marker
-----------------------------------
A test that genuinely must reach a live provider opts in with
``@pytest.mark.live`` (excluded from the default suite; run with ``-m live``).
This is human-written and explicit — there is **no** silent "skip because
``DEEPSEEK_API_KEY`` is unset" path.

Scope readout (not authoritative under xdist)
---------------------------------------------
The terminal-summary line is a **per-process readout only**. Under ``-n``
parallelism each worker keeps its own ``_BLOCKED`` list and the master prints its
own (usually empty) count; it does not aggregate workers. The **authoritative**
evidence that no billed call happened is the suite's set of FAILED tests: a
blocked call raises ``ProviderCallBlocked``, which fails the offending test. See
verdict N-1.
"""

from __future__ import annotations

import ipaddress
import os
import socket

import pytest

# Bind the genuine implementations once, at import, before anything wraps them.
_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex

# Hostnames (not yet resolved to an IP) that denote local IPC and never bill.
_LOCAL_NAMES = frozenset(
    {"localhost", "ip6-localhost", "ip6-loopback", "0.0.0.0", "::", ""}
)

# Per-process scope readout (see module docstring / verdict N-1). NOT the
# authoritative "no billed call" evidence — the FAILED-test set is.
_BLOCKED: list[tuple[str, str]] = []

# Lifted (True) only while a @pytest.mark.live test body runs.
_LIVE_ACTIVE = False

# Guard so a second import / a redundant pytest_configure re-install does not
# wrap the wrapper (we always rebuild from the saved real implementations).
_INSTALLED = False


class ProviderCallBlocked(RuntimeError):
    """Raised when a test tries to emit a real, billable network request."""


def _is_local(address: object) -> bool:
    """True iff connecting to *address* cannot bill a remote provider."""
    # AF_UNIX endpoints are a plain str/bytes path -> always local IPC.
    if not isinstance(address, tuple) or not address:
        return True
    host = str(address[0])
    if host in _LOCAL_NAMES:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # A hostname that isn't a known-local name (e.g. api.deepseek.com).
        # connect() usually receives an already-resolved IP, but if a bare
        # hostname reaches here, treat it as remote — fail closed.
        return False
    if ip.is_loopback or ip.is_unspecified:
        return True
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None and (mapped.is_loopback or mapped.is_unspecified):
        return True
    return False


def _current_test() -> str:
    # pytest sets this for the whole life of each test item; absent during
    # collection / import, which we label explicitly rather than as a test.
    raw = os.environ.get("PYTEST_CURRENT_TEST", "<collection/import phase>")
    return raw.split(" (")[0]


def _record(test: str, dest: object) -> None:
    _BLOCKED.append((test, repr(dest)))
    log = os.environ.get("EP_NO_BILLED_LOG")
    if log:
        try:
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(f"{test}\t{dest!r}\n")
        except OSError:
            pass


def _guarded(orig):
    def wrapper(self, address, *args, **kwargs):
        if _LIVE_ACTIVE or _is_local(address):
            return orig(self, address, *args, **kwargs)
        test = _current_test()
        _record(test, address)
        raise ProviderCallBlocked(
            f"F-158 no-billed-calls gate: test '{test}' tried to open a real "
            f"network connection to {address!r}. This would emit a real, billed "
            f"provider request. Give it a fake/stub so it runs offline, or — only "
            f"if it is meant to hit a live provider — mark it @pytest.mark.live "
            f"(excluded from the default suite; run with -m live)."
        )

    return wrapper


def _install() -> None:
    """Idempotent: always rebuilds the wrapper from the saved real methods."""
    global _INSTALLED
    socket.socket.connect = _guarded(_REAL_CONNECT)
    socket.socket.connect_ex = _guarded(_REAL_CONNECT_EX)
    _INSTALLED = True


def _uninstall() -> None:
    global _INSTALLED
    socket.socket.connect = _REAL_CONNECT
    socket.socket.connect_ex = _REAL_CONNECT_EX
    _INSTALLED = False


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: test may make a real, billed provider call; excluded from the "
        "default suite (select with -m live).",
    )
    # Defence in depth: the gate is already installed at import (below), but if
    # some other plugin restored the real methods, re-arm here.
    _install()


def pytest_unconfigure(config):
    _uninstall()


@pytest.fixture(autouse=True)
def _lift_gate_for_live(request):
    """Lift the egress gate for the duration of a @pytest.mark.live test."""
    global _LIVE_ACTIVE
    if request.node.get_closest_marker("live"):
        _LIVE_ACTIVE = True
        try:
            yield
        finally:
            _LIVE_ACTIVE = False
    else:
        yield


def pytest_collection_modifyitems(config, items):
    """Keep `live` tests out of the default suite. When the run explicitly asks
    for them (`-m live`) leave collection alone. This is the explicit-marker
    exit, NOT a no-API-key skip."""
    markexpr = getattr(config.option, "markexpr", "") or ""
    if "live" in markexpr:
        return
    skip_live = pytest.mark.skip(reason="live provider test; select with -m live")
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(skip_live)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Per-process READOUT only (verdict N-1). Under xdist this reflects the
    master process, not workers; it is not the authoritative no-billed-call
    evidence — the FAILED-test set is."""
    if _BLOCKED:
        terminalreporter.section("F-158 no-billed-calls gate: BLOCKED calls")
        for test, dest in _BLOCKED:
            terminalreporter.write_line(f"  BLOCKED {test} -> {dest}")
    else:
        terminalreporter.write_line(
            "F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider "
            "calls blocked in THIS process. Under -n parallelism this is the "
            "master process only, not workers; authoritative evidence that no "
            "billed call happened = the suite's FAILED-test set."
        )


# --- install at import: this is the fix. Everything above is machinery; the
# guarantee ("no test-owned import can bind the real connect") comes from this
# line running before any command-line -p plugin or initial conftest. ---
_install()
