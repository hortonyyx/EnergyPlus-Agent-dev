"""F-158 — make a real, *billed* provider call structurally impossible in the
default test suite.

This gate is a from-scratch reimplementation for task F-158 (dispatch
``2026-09-02x_f158_no_billed_calls_in_suite``). An earlier seat left a partial
``conftest.py`` that never ran; it is archived as a *clue, not evidence*
(``logs/experiments/2026-09-02_f158_orphan_wip``). Every design choice below was
re-derived and answers the five open questions the orchestrator raised on that
archive. Where this file reuses the earlier seam it does so with an explicit
argument (see "Seam" below) and is backed by its own locks in
``tests/test_no_billed_provider_calls.py``.

Seam (why the network-egress point, not "constructing a client")
----------------------------------------------------------------
The gate wraps ``socket.socket.connect`` / ``socket.socket.connect_ex`` — the
point where bytes would leave for a remote host — not the point where an LLM
client object is built. Constructing a client costs nothing and several tests
legitimately build one (schema round-trips, tool wiring); only *emitting a
request to a routable remote* bills the shared DeepSeek balance
(CLAUDE.md §5#10). ``socket.connect`` is also provider- and HTTP-library-
agnostic: the real billed path here is
``langchain_openai → openai SDK → httpx → httpcore → socket.create_connection``,
and ``create_connection`` builds a socket and calls ``.connect()`` on it, so it
funnels through the wrapped class method. requests/urllib/urllib3 do the same.
=> the thing being measured cannot be swapped out from under the gate by
changing the HTTP client library.

Known residual gap (answering orphan question #1, honestly): patching the
*class* attribute does not catch a caller that captured a bound
``sock.connect`` reference before the gate installed, nor a client that reaches
the kernel through a C-level / io_uring path that never calls
``socket.socket.connect``. Neither applies to the provider path above, and the
teeth test in ``test_no_billed_provider_calls.py`` pins the paths that DO
matter (raw ``socket``, ``socket.create_connection``, ``urllib``).

Locality test (answering orphan question #2)
--------------------------------------------
``_is_local`` uses ``ipaddress`` rather than a ``startswith("127.")`` string
prefix, so IPv6 loopback ``::1``, IPv4-mapped ``::ffff:127.0.0.1`` and the whole
127.0.0.0/8 block are all recognised, and a real external address is never
mis-read as local.

Always-on install (answering orphan question #3)
------------------------------------------------
The gate is installed in ``pytest_configure`` and removed in
``pytest_unconfigure`` — it is live for the *whole* session, so a connection
attempted at collection / module-import time is caught too, not only during a
test body. A ``@pytest.mark.live`` test lifts the gate for the duration of that
one test via an autouse fixture.

The only exit is an explicit marker (answering orphan question #4)
-----------------------------------------------------------------
A test that genuinely must reach a live provider opts in with
``@pytest.mark.live``; such tests are excluded from the default suite (run them
with ``-m live``). This marker is human-written and explicit — there is **no**
silent "skip because ``DEEPSEEK_API_KEY`` is unset" path, which is exactly what
acceptance #6 of the dispatch forbids.

The gate is its own scope measurement (answering orphan question #5)
-------------------------------------------------------------------
Every blocked call is appended to an in-memory list and reported in the
terminal summary **unconditionally** — the gate counts itself; it does not
depend on an env var being set. ``EP_NO_BILLED_LOG=<path outside repo>`` is an
*optional additional* machine-readable sink for the T2 enumeration.
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

# Session-wide scope measurement (T2). Populated in-process; under xdist each
# worker keeps its own list and the authoritative enumeration is the set of
# FAILED tests (which xdist reports to the controller) plus, optionally, the
# EP_NO_BILLED_LOG file appended by every worker.
_BLOCKED: list[tuple[str, str]] = []

# Lifted (True) only while a @pytest.mark.live test body runs.
_LIVE_ACTIVE = False


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
    socket.socket.connect = _guarded(_REAL_CONNECT)
    socket.socket.connect_ex = _guarded(_REAL_CONNECT_EX)


def _uninstall() -> None:
    socket.socket.connect = _REAL_CONNECT
    socket.socket.connect_ex = _REAL_CONNECT_EX


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: test may make a real, billed provider call; excluded from the "
        "default suite (select with -m live).",
    )
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
    """The gate reports its own scope (T2) every run, env var or not."""
    if _BLOCKED:
        terminalreporter.section("F-158 no-billed-calls gate: BLOCKED calls")
        for test, dest in _BLOCKED:
            terminalreporter.write_line(f"  BLOCKED {test} -> {dest}")
    else:
        terminalreporter.write_line(
            "F-158 no-billed-calls gate: 0 provider calls blocked "
            "(this process; authoritative scope = FAILED tests across workers)."
        )
