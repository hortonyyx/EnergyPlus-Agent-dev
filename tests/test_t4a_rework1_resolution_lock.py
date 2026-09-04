"""T4-a rework 1 (dispatch 2026-09-04o) -- the single-value resolution lock.

WHAT THIS FILE LOCKS
--------------------
The asset the v2 round sold (cross-review 2026-09-04h, blocker B-1).
T3's exact keys + plain dict + closed ``Literal`` domain bought a real
thing: ONE debt can never resolve to MORE THAN ONE registry row, and
the old literal trigger of ``DEBT_TYPE_AMBIGUOUS`` (one ``debt_id``
matching two prefix rows) is structurally unreachable -- that stays.
What was sold WITH it is the regression lock: if someone later
reintroduces an obligation ALIAS / case-or-space NORMALISATION / a
COMPAT table / a ONE-TO-MANY resolver -- so one debt could again get
several candidate rows -- nothing would go red.  This file buys that
direction back:

* the BATTERY (``near_misses``): for every LIVE registry key, the
  shapes a widening exists to accept (case / spacing / prefix / suffix
  / separator variants) must ALL be refused, loudly
  (``OBLIGATION_UNBACKED``), on every runtime entry.  An alias, a
  normalisation or a compat table is BUILT to accept some of these;
  the moment it does, this battery is red.
* the IDENTITY PIN: for every live key the seam resolves to exactly
  ``(key, registry[key])`` -- a resolver that redirects an EXACT
  obligation to another row accepts every refusal and is caught only
  here.
* the MUTATION DEMOS: each of the four canonical widenings, installed
  in process and finally-restored, with the proof that the lock's own
  probes stop being refused / the production teeth fire.  A lock that
  cannot go red is not a lock; the demos are the battery's and the
  pin's discriminating-power proof, ⛔ not fixtures of legal behaviour.

Generated from the LIVE table as rules: a future domain value joins
the battery for free, and no probe may silently collide with a live
key (that coincidence fails the suite loudly instead).
"""
from __future__ import annotations

import pytest

import src.agent.correction.opening_synthesis as osm
from src.agent.correction.evidence_contract import (
    ArtifactPointerV1,
    EvidenceDebtV1,
)
from src.agent.reading.vector_contract import CONTRACT_AS_DRAWN_ELEVATION_V0

SPAN_OBLIGATION = "elevation_chain_spans_whole_building"


# ── probes ──────────────────────────────────────────────────────────────────── #
def _bypass_debt(obligation: object) -> EvidenceDebtV1:
    """A debt whose ``obligation`` BYPASSES the schema
    (``model_construct``).  The closed ``Literal`` domain is separately
    locked (test_o22m2_evidence_contract); the seam is the surface a
    widened lookup would act on, and only a schema-bypassed debt can
    carry a near-miss value to it at runtime."""
    return EvidenceDebtV1.model_construct(
        debt_id="resolution_lock_probe",
        kind="other_known_missing",
        channel=None,
        affected_refs=(),
        description="resolution-lock probe (schema bypass)",
        obligation=obligation,
    )


def _executed() -> osm.ExecutedRedemption:
    """The redemption a healthy run executes, built against the HEALTHY
    registry (before any demo mutates it)."""
    return osm.ExecutedRedemption(
        obligation=SPAN_OBLIGATION,
        row=osm.DEBT_REDEMPTION_REGISTRY[SPAN_OBLIGATION],
        source=None,
    )


def near_misses() -> list[tuple[str, str]]:
    """(label, probe) generated from every LIVE registry key: the
    variants an alias / normalisation / compat / one-to-many widening
    exists to accept.  A probe that collides with a live key fails the
    suite loudly -- the battery must never silently skip one."""
    probes: list[tuple[str, str]] = []
    for key in sorted(osm.DEBT_REDEMPTION_REGISTRY):
        variants = [
            ("upper", key.upper()),
            ("capitalise", key.capitalize()),
            ("cased_spaced", "  " + key.casefold() + "  "),
            ("trailing_space", key + " "),
            ("leading_space", " " + key),
            ("legacy_suffix", key + "_legacy"),
            ("v2_suffix", key + "_v2"),
            ("old_suffix", key + "_old"),
            ("underscore_prefix", "_" + key),
            ("sep_dash", key.replace("_", "-")),
            ("sep_none", key.replace("_", "")),
            ("sep_space", key.replace("_", " ")),
            ("doubled", key + key),
            ("off_by_one_tail", key[:-1]),
            ("off_by_one_head", key[1:]),
        ]
        # proper prefixes at every '_' boundary: the one-to-many shape
        variants += [
            (f"prefix_cut_{cut}", key[:cut])
            for cut in (i for i, ch in enumerate(key) if ch == "_")
            if cut > 0
        ]
        for label, probe in variants:
            assert probe not in osm.DEBT_REDEMPTION_REGISTRY, (
                f"near-miss {label}={probe!r} collides with a live key"
            )
            probes.append((f"{key}:{label}", probe))
    return probes


def _refusal_gone(probe: str) -> bool:
    """True iff EVERY runtime entry ACCEPTS the probe without a loud
    ``OpeningSynthesisError``.  The battery asserts the negation on the
    healthy seam; each demo asserts this under its widening -- the same
    probe function, so a demo literally proves the battery's teeth in
    that direction."""
    debt = _bypass_debt(probe)
    for call in (
        lambda: osm.redemption_row_for_obligation(probe),
        lambda: osm.assert_obligations_backed([debt]),
        lambda: osm.redeemable_debt_ids([debt], executed=_executed()),
    ):
        try:
            call()
        except osm.OpeningSynthesisError:
            return False
    return True


# ── the battery ─────────────────────────────────────────────────────────────── #
@pytest.mark.parametrize("label,probe", near_misses())
def test_near_miss_obligations_are_refused_on_every_entry(label, probe):
    """THE BATTERY: every near-miss must be refused LOUDLY
    (``OBLIGATION_UNBACKED``) at the seam and on both callers.  Any
    widening that accepts a near-miss -- which is what an alias /
    normalisation / compat table / one-to-many resolver is FOR -- turns
    this red."""
    debt = _bypass_debt(probe)
    with pytest.raises(osm.OpeningSynthesisError) as caught:
        osm.redemption_row_for_obligation(probe)
    assert caught.value.code == "OBLIGATION_UNBACKED"
    with pytest.raises(osm.OpeningSynthesisError) as caught:
        osm.assert_obligations_backed([debt])
    assert caught.value.code == "OBLIGATION_UNBACKED"
    with pytest.raises(osm.OpeningSynthesisError) as caught:
        osm.redeemable_debt_ids([debt], executed=_executed())
    assert caught.value.code == "OBLIGATION_UNBACKED"


def test_healthy_control_the_exact_obligation_resolves_and_retires():
    """The control that makes the refusals above the lock's, ⛔ not the
    input's: the EXACT obligation resolves at the seam and -- source
    bound -- retires through the real retirement path."""
    source = osm.ElevationSourceIdentity(
        input_id="input_probe",
        source_contract_id=CONTRACT_AS_DRAWN_ELEVATION_V0,
        source_output_sha256="0" * 64,
    )
    debt = EvidenceDebtV1.model_validate(
        {
            "debt_id": "resolution_lock_control",
            "kind": "other_known_missing",
            "channel": None,
            "affected_refs": (
                {
                    "input_id": source.input_id,
                    "source_contract_id": source.source_contract_id,
                    "source_output_sha256": source.source_output_sha256,
                    "json_pointer": "/calibration",
                },
            ),
            "description": "healthy control",
            "obligation": SPAN_OBLIGATION,
        }
    )
    executed = osm.ExecutedRedemption(
        obligation=SPAN_OBLIGATION,
        row=osm.DEBT_REDEMPTION_REGISTRY[SPAN_OBLIGATION],
        source=source,
    )
    key, row = osm.redemption_row_for_obligation(SPAN_OBLIGATION)
    assert key == SPAN_OBLIGATION
    assert row is osm.DEBT_REDEMPTION_REGISTRY[SPAN_OBLIGATION]
    assert osm.redeemable_debt_ids([debt], executed=executed) == (
        "resolution_lock_control",
    )


# ── the identity pin ────────────────────────────────────────────────────────── #
def test_every_live_key_resolves_to_exactly_its_own_row():
    """THE IDENTITY PIN: for every live registry key (a RULE over the
    live table, ⛔ not a transcript) the seam returns exactly
    ``(key, registry[key])``.  A resolver that redirects an exact
    obligation to another row accepts every battery refusal -- this pin
    is what goes red on it."""
    for key, row in osm.DEBT_REDEMPTION_REGISTRY.items():
        resolved_key, resolved_row = osm.redemption_row_for_obligation(key)
        assert resolved_key == key
        assert resolved_row is row


def test_retirement_never_follows_a_row_the_registry_does_not_hold():
    """The retirement binding uses the SEAM-resolved row: an
    ``executed`` redemption whose row is not the row stored at the
    debt's exact key retires NOTHING (kept open, ⛔ never a silent
    wrong-gate retirement).  With a redirected seam (demo M6) this is
    the second line of defence behind the pin."""
    source = osm.ElevationSourceIdentity(
        input_id="input_probe",
        source_contract_id=CONTRACT_AS_DRAWN_ELEVATION_V0,
        source_output_sha256="0" * 64,
    )
    debt = EvidenceDebtV1.model_validate(
        {
            "debt_id": "resolution_lock_binding",
            "kind": "other_known_missing",
            "channel": None,
            "affected_refs": (
                {
                    "input_id": source.input_id,
                    "source_contract_id": source.source_contract_id,
                    "source_output_sha256": source.source_output_sha256,
                    "json_pointer": "/calibration",
                },
            ),
            "description": "binding pin",
            "obligation": SPAN_OBLIGATION,
        }
    )
    foreign_row = osm.DebtRedemption(
        premise="a premise no registry row holds", gate=osm.span_equality_gate
    )
    executed = osm.ExecutedRedemption(
        obligation=SPAN_OBLIGATION, row=foreign_row, source=source
    )
    assert osm.redeemable_debt_ids([debt], executed=executed) == ()


# ── the canonical widenings (M1–M4) + two costume variants (M5–M6), ─────────── #
# ── each one proving a tooth of this lock ───────────────────────────────────── #
def test_demo_M1_normalisation_widening_would_turn_the_battery_red():
    """M1 归一化: install a normalising seam (strip + casefold -- the
    exact shape a 'robust input handling' change takes) and the
    battery's own probe STOPS being refused on every entry.  The
    mutation is finally-restored; the post-check proves it took and
    un-took."""
    real = osm.redemption_row_for_obligation

    def normalising(obligation: str):
        try:
            return real(obligation)
        except osm.OpeningSynthesisError as exc:
            if exc.code != "OBLIGATION_UNBACKED":
                raise
            return real(obligation.strip().casefold())

    probe = "  " + SPAN_OBLIGATION.upper() + "  "
    osm.redemption_row_for_obligation = normalising
    try:
        assert _refusal_gone(probe), (
            "the normalising seam still refuses every probe -- the "
            "battery has no teeth in the normalisation direction"
        )
    finally:
        osm.redemption_row_for_obligation = real
    with pytest.raises(osm.OpeningSynthesisError):
        real(probe)


def test_demo_M2_compat_table_widening_would_turn_the_battery_red():
    """M2 兼容旧名: a compat table mapping legacy obligation names to
    the canonical one; the legacy-suffix probe stops being refused."""
    real = osm.redemption_row_for_obligation
    compat = {SPAN_OBLIGATION + "_legacy": SPAN_OBLIGATION}

    def compat_seam(obligation: str):
        try:
            return real(obligation)
        except osm.OpeningSynthesisError as exc:
            if exc.code != "OBLIGATION_UNBACKED" or obligation not in compat:
                raise
            return real(compat[obligation])

    probe = SPAN_OBLIGATION + "_legacy"
    osm.redemption_row_for_obligation = compat_seam
    try:
        assert _refusal_gone(probe), (
            "the compat seam still refuses the legacy name -- the "
            "battery has no teeth in the compat direction"
        )
    finally:
        osm.redemption_row_for_obligation = real
    with pytest.raises(osm.OpeningSynthesisError):
        real(probe)


def test_demo_M3_one_to_many_prefix_resolver_would_turn_the_battery_red():
    """M3 一对多 resolver: collect every key the obligation is a prefix
    of (or that is a prefix of it), sort, silently PICK one -- the old
    debt_id-prefix world's exact failure shape reborn on obligations.
    The proper-prefix probe stops being refused."""
    real = osm.redemption_row_for_obligation

    def prefix_resolver(obligation: str):
        try:
            return real(obligation)
        except osm.OpeningSynthesisError as exc:
            if exc.code != "OBLIGATION_UNBACKED":
                raise
            hits = sorted(
                key
                for key in osm.DEBT_REDEMPTION_REGISTRY
                if key.startswith(obligation)
                or obligation.startswith(key)
            )
            if not hits:
                raise
            return real(hits[0])

    probe = "elevation_chain_spans"
    osm.redemption_row_for_obligation = prefix_resolver
    try:
        assert _refusal_gone(probe), (
            "the prefix resolver still refuses the truncated obligation "
            "-- the battery has no teeth in the one-to-many direction"
        )
    finally:
        osm.redemption_row_for_obligation = real
    with pytest.raises(osm.OpeningSynthesisError):
        real(probe)


def test_demo_M4_alias_key_widening_fires_the_debt_side_tooth():
    """M4 别名 without touching the seam: one ``str``-subclass registry
    key whose loose ``__eq__`` claims SEVERAL obligations (one row, many
    names).  The production teeth own this direction: the seam refuses
    with ``DEBT_TYPE_AMBIGUOUS`` -- the DEBT direction that code name
    holds again -- and the import teeth refuse the key outright."""
    assert sorted(osm.DEBT_REDEMPTION_REGISTRY) == [SPAN_OBLIGATION]

    class _AliasKey(str):
        def __eq__(self, other: object) -> bool:
            return isinstance(other, str) and str(other) in (
                str(self),
                str(self) + "_legacy",
            )

        def __ne__(self, other: object) -> bool:
            return not self.__eq__(other)

        __hash__ = str.__hash__

    row = osm.DEBT_REDEMPTION_REGISTRY[SPAN_OBLIGATION]
    original = dict(osm.DEBT_REDEMPTION_REGISTRY)
    executed = _executed()
    debt = EvidenceDebtV1.model_validate(
        {
            "debt_id": "resolution_lock_alias",
            "kind": "other_known_missing",
            "channel": None,
            "affected_refs": (),
            "description": "alias-key demo",
            "obligation": SPAN_OBLIGATION,
        }
    )
    osm.DEBT_REDEMPTION_REGISTRY.clear()
    osm.DEBT_REDEMPTION_REGISTRY[_AliasKey(SPAN_OBLIGATION)] = row
    try:
        with pytest.raises(osm.OpeningSynthesisError) as caught:
            osm.redemption_row_for_obligation(SPAN_OBLIGATION)
        assert caught.value.code == "DEBT_TYPE_AMBIGUOUS"
        # the runtime entries inherit the same debt-side tooth...
        with pytest.raises(osm.OpeningSynthesisError) as caught:
            osm.redeemable_debt_ids([debt], executed=executed)
        assert caught.value.code == "DEBT_TYPE_AMBIGUOUS"
        # ...and the import teeth refuse the alias key outright
        with pytest.raises(osm.OpeningSynthesisError) as caught:
            osm._assert_registry_well_formed()
        assert caught.value.code == "DEBT_REGISTRY_KEY_NOT_PLAIN_STR"
    finally:
        osm.DEBT_REDEMPTION_REGISTRY.clear()
        osm.DEBT_REDEMPTION_REGISTRY.update(original)
    osm._assert_registry_well_formed()  # restored to health


def test_demo_M5_carrier_swap_widening_fires_the_carrier_tooth():
    """M5 载体 swap: the widening that touches neither the seam code nor
    the keys -- replace the CARRIER with a mapping subclass whose
    ``__getitem__`` falls back to an alias.  ``isinstance`` would wave
    it through; the tooth is ``type() is dict``, and this demo is WHY.
    Every entry (seam, alias probe, import teeth) refuses with the
    carrier code."""
    class _AliasDict(dict):
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return dict.__getitem__(self, key + "_legacy")

    original = osm.DEBT_REDEMPTION_REGISTRY
    carrier = _AliasDict(dict(original))
    carrier[SPAN_OBLIGATION + "_legacy"] = original[SPAN_OBLIGATION]
    assert isinstance(carrier, dict)  # the costume the tooth sees through
    osm.DEBT_REDEMPTION_REGISTRY = carrier
    try:
        for what, call in (
            ("seam", lambda: osm.redemption_row_for_obligation(SPAN_OBLIGATION)),
            (
                "alias_probe",
                lambda: osm.redemption_row_for_obligation(
                    SPAN_OBLIGATION + "_legacy"
                ),
            ),
            ("import", osm._assert_registry_well_formed),
        ):
            with pytest.raises(osm.OpeningSynthesisError) as caught:
                call()
            assert caught.value.code == "DEBT_REGISTRY_CARRIER_NOT_PLAIN_DICT", what
    finally:
        osm.DEBT_REDEMPTION_REGISTRY = original
    osm._assert_registry_well_formed()  # restored to health


def test_demo_M6_redirect_widening_is_what_the_identity_pin_locks():
    """M6 重定向: a resolver that accepts ONLY exact keys but redirects
    them to another row.  It refuses every battery probe (so the
    battery alone stays green -- this is the honest boundary of the
    battery); the IDENTITY PIN is the lock that goes red, and the
    retirement binding keeps the debt open underneath it."""
    real = osm.redemption_row_for_obligation
    other = osm.DebtRedemption(
        premise="a redirected premise", gate=osm.span_equality_gate
    )
    source = osm.ElevationSourceIdentity(
        input_id="input_probe",
        source_contract_id=CONTRACT_AS_DRAWN_ELEVATION_V0,
        source_output_sha256="0" * 64,
    )
    debt = EvidenceDebtV1.model_validate(
        {
            "debt_id": "resolution_lock_redirect",
            "kind": "other_known_missing",
            "channel": None,
            "affected_refs": (
                {
                    "input_id": source.input_id,
                    "source_contract_id": source.source_contract_id,
                    "source_output_sha256": source.source_output_sha256,
                    "json_pointer": "/calibration",
                },
            ),
            "description": "redirect demo",
            "obligation": SPAN_OBLIGATION,
        }
    )
    executed = osm.ExecutedRedemption(
        obligation=SPAN_OBLIGATION,
        row=osm.DEBT_REDEMPTION_REGISTRY[SPAN_OBLIGATION],
        source=source,
    )

    def redirecting(obligation: str):
        key, _row = real(obligation)
        return key, other

    osm.redemption_row_for_obligation = redirecting
    try:
        # the battery's refusal survives this widening (honest boundary:
        # a redirect accepts no near-miss)...
        assert not _refusal_gone(SPAN_OBLIGATION + "_legacy")
        # ...the retirement keeps the debt open (no wrong-gate retire)...
        assert osm.redeemable_debt_ids([debt], executed=executed) == ()
        # ...and the identity pin's own assertion is RED under it:
        with pytest.raises(AssertionError):
            for key, row in osm.DEBT_REDEMPTION_REGISTRY.items():
                resolved_key, resolved_row = osm.redemption_row_for_obligation(key)
                assert resolved_key == key
                assert resolved_row is row
    finally:
        osm.redemption_row_for_obligation = real
    # restored: the pin is green again on the real seam
    for key, row in osm.DEBT_REDEMPTION_REGISTRY.items():
        resolved_key, resolved_row = osm.redemption_row_for_obligation(key)
        assert resolved_key == key
        assert resolved_row is row
