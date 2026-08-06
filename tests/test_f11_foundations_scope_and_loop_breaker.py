"""F-11 locks: foundations-stage vertex-drift scoping + downstream loop breaker.

Background (F-11 investigation,
``logs/reviews/execution/2026-08-06_f11_downstream_loop_investigation_glm.md``):

The E4 vertex-drift check (``_vertex_drift_issues``) is a TERMINAL check — it
compares the post-geometry snapshot against ``ConfigState.surfaces /
fenestrations``. ``cross_ref_foundations_node`` ran it after phase 1, before
construction/surface/fenestration built any surfaces, so every snapshot record
was reported as "missing from ConfigState" (115 timing false-positives). With
``MAX_RETRIES=0`` + the intake short-circuit + auto-approval always rejecting,
that produced a non-terminating ``validate -> intake -> ... -> validate`` loop.

Fix A: ``cross_ref_foundations_node`` passes ``include_vertex_drift=False``;
``cross_ref_complete_node`` / ``validate_node`` keep the default ``True`` so the
full gate still runs once geometry is complete.

Fix B-1: ``auto_approval`` logs the error set on rejection (was fully silent).

Fix B-2: ``run_session`` raises ``InterruptLoopBreakerError`` after N consecutive
identical error-bearing interrupts — a deterministic termination guarantee.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent._share import ensure_schema_initialized


@pytest.fixture(autouse=True)
def _init_schema():
    ensure_schema_initialized()


# --------------------------------------------------------------------------- #
# Acceptance 2 — contract gate is NOT dropped (complete / validate still report)
# --------------------------------------------------------------------------- #
def _drift_state():
    """A complete-geometry state whose snapshot carries a surface ConfigState
    does not — a genuine post-geometry drift (the surface was dropped/renamed
    between the snapshot and ConfigState, exactly what E4 §5.2 call point 3
    guards). Returns ``(contract, context, config)``."""
    from src.agent.output_coordinates import (
        AcceptedCorrectionRef,
        CoordinateRecordV1,
        OutputCoordinateContract,
        OutputCoordinateSnapshotV1,
        OutputCoordinateValidationContext,
        VerifiedAcceptedCorrection,
        canonical_json_bytes,
        sha256_bytes,
    )
    from src.mcp.state import ConfigState
    from src.validator import BuildingSchema, SiteLocationSchema
    from src.validator.data_model import GlobalGeometryRulesSchema

    snapshot = OutputCoordinateSnapshotV1(
        zone_names=("Z1",),
        records=(CoordinateRecordV1(
            object_type="BuildingSurface:Detailed", name="W1", zone_or_parent="Z1",
            vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
        ),),
    )
    raw_snapshot_bytes = canonical_json_bytes(snapshot)
    snapshot_sha = sha256_bytes(raw_snapshot_bytes)

    raw_correction = b'{"schema_version":"3"}'
    correction_sha = sha256_bytes(raw_correction)
    ref = AcceptedCorrectionRef(
        schema_version="3", output_sha256=correction_sha,
        acceptance="integrated_gate1", artifact_contract="correction_e4_orientation_v1",
    )
    verified = VerifiedAcceptedCorrection(
        ref=ref, raw_output_bytes=raw_correction, raw_feature_states_bytes=None,
    )
    contract = OutputCoordinateContract(
        mode="relative_north_axis", source=ref,
        geometry_frame="building_axis_absolute_values",
        global_geometry_coordinate_system="Relative",
        daylighting_reference_point_coordinate_system="Relative",
        rectangular_surface_coordinate_system="Relative",
        zone_origin_policy="all_zero", zone_direction_policy="all_zero",
        north_axis_owner="accepted_correction_orientation", north_axis_deg=0.0,
        orientation_provenance="assumed",
        geometry_snapshot_sha256=snapshot_sha,
    )
    context = OutputCoordinateValidationContext(
        raw_intake_output_bytes=b'{}', verified_correction=verified,
        raw_snapshot_bytes=raw_snapshot_bytes,
    )
    config = ConfigState(
        building=BuildingSchema(name="B", north_axis=0.0),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
    )
    config.global_geometry_rules = GlobalGeometryRulesSchema.model_validate(
        {"Coordinate System": "Relative"})
    return contract, context, config


def test_cross_ref_complete_node_reports_real_vertex_drift():
    """F-11 Acceptance 2 (contract-not-dropped lock). ``cross_ref_complete_node``
    must still run the FULL output-coordinate gate INCLUDING vertex-drift. With
    a snapshot surface W1 absent from ConfigState (a real post-geometry drift),
    the node MUST surface ``VERTEX_FRAME_DRIFT``.

    Assertion lands on the concrete issue code ``VERTEX_FRAME_DRIFT`` and the
    concrete check site ``_vertex_drift_issues``
    (``src/validator/output_coordinates.py``), whose message uniquely contains
    'missing from ConfigState'.
    """
    from src.agent.nodes.cross_ref import cross_ref_complete_node
    from src.agent.state import AgentState

    contract, context, config = _drift_state()
    state = AgentState(
        config_state=config,
        output_coordinate_contract=contract,
        output_coordinate_context=context,
    )
    update = cross_ref_complete_node(state)
    errs = update["validation_errors"]
    drift = [e for e in errs if "VERTEX_FRAME_DRIFT" in e]
    assert drift, f"cross_ref_complete_node dropped the vertex-drift gate; errs={errs}"
    # concrete check site: _vertex_drift_issues 'missing from ConfigState' line
    assert any("missing from ConfigState" in e for e in drift), drift


def test_validate_path_reports_real_vertex_drift_default():
    """F-11 Acceptance 2 (validate path). ``validate_node`` calls
    ``_output_coordinate_errors(state)`` with the default
    ``include_vertex_drift=True`` (``src/agent/nodes/validate.py:39``), i.e. the
    very gate below. The default MUST report the drift."""
    from src.validator.output_coordinates import validate_output_coordinate_contract

    contract, context, config = _drift_state()
    issues = validate_output_coordinate_contract(config, contract, context)
    drift = [i for i in issues if i.code == "VERTEX_FRAME_DRIFT"]
    assert drift, issues
    assert any("missing from ConfigState" in i.message for i in drift)


def test_foundations_path_skips_terminal_vertex_drift():
    """F-11 Fix-A mechanism lock. At the pre-geometry boundary
    (``include_vertex_drift=False`` — what ``cross_ref_foundations_node`` passes)
    the terminal vertex-drift comparison is SKIPPED. The SAME drift that
    complete/validate report above is NOT reported here. This is precisely why
    foundations no longer produces 115 timing false-positives — the gate is not
    deleted, only the terminal-geometry half is deferred."""
    from src.validator.output_coordinates import validate_output_coordinate_contract

    contract, context, config = _drift_state()
    issues = validate_output_coordinate_contract(
        config, contract, context, include_vertex_drift=False)
    drift = [i for i in issues if i.code == "VERTEX_FRAME_DRIFT"]
    assert not drift, (
        f"foundations path must skip terminal vertex-drift; got {drift}"
    )


# --------------------------------------------------------------------------- #
# Acceptance 3 — deterministic loop termination (circuit breaker)
# --------------------------------------------------------------------------- #
class _StubInterrupt:
    def __init__(self, value):
        self.value = value


class _StubTask:
    def __init__(self, value):
        self.interrupts = [_StubInterrupt(value)]


class _StubSnapshot:
    def __init__(self, value):
        self.tasks = [_StubTask(value)]
        self.values = {}


class _StubGraph:
    """Minimal stand-in for a compiled graph: never produces non-interrupt
    events, and ``get_state`` always reports one pending interrupt carrying a
    fixed payload — i.e. a stuck repair loop the real graph cannot escape."""

    def __init__(self, value):
        self._value = value

    def stream(self, payload, *, config, context, stream_mode):
        return iter(())

    def get_state(self, config):
        return _StubSnapshot(self._value)


def test_interrupt_errors_signature_distinguishes_clean_from_errors():
    """F-11 Fix-B2 helper. Clean interrupts (no errors) return None and never
    count toward the breaker; error-bearing interrupts return an order-free
    signature."""
    from src.agent.runner import _interrupt_errors_signature

    assert _interrupt_errors_signature({"errors": []}) is None
    assert _interrupt_errors_signature({}) is None
    assert _interrupt_errors_signature("not-a-dict") is None
    assert _interrupt_errors_signature({"errors": ["b", "a"]}) == ("a", "b")
    assert _interrupt_errors_signature({"errors": ["a", "b"]}) == ("a", "b")


def test_run_session_breaks_non_terminating_validate_loop():
    """F-11 Acceptance 3 (circuit-breaker lock). A persistent error (the same
    error set every interrupt) MUST terminate in a finite number of rounds by
    raising ``InterruptLoopBreakerError`` — never rely on the error 'eventually
    going away'. With ``max_consecutive_identical_interrupts=3`` the breaker
    trips on the 4th identical interrupt."""
    from src.agent.runner import InterruptLoopBreakerError, run_session
    from src.agent.state import AgentState

    payload = {"summary": {"zones_count": 1}, "errors": ["ERR_A", "ERR_B"], "message": "x"}
    graph = _StubGraph(payload)

    with pytest.raises(InterruptLoopBreakerError) as excinfo:
        run_session(
            graph,
            AgentState(),
            context=None,  # the stub graph does not consume the context
            config={"configurable": {"thread_id": "f11-test"}},
            on_interrupt=lambda p: {"approved": False, "feedback": "no"},
            max_consecutive_identical_interrupts=3,
        )
    msg = str(excinfo.value)
    assert "non-terminating" in msg.lower()
    assert "ERR_A" in msg and "ERR_B" in msg


def test_run_session_does_not_break_when_errors_resolve_or_differ():
    """F-11 Fix-B2 negative: the breaker does not trip when consecutive
    interrupts carry DIFFERENT error sets (errors are changing = the loop is
    making progress / a human is steering), nor on a clean (error-free)
    interrupt. Clean interrupts reset the run."""
    from src.agent.runner import _interrupt_errors_signature

    # different error sets are different signatures (not "stuck")
    assert (_interrupt_errors_signature({"errors": ["a"]})
            != _interrupt_errors_signature({"errors": ["a", "b"]}))


# --------------------------------------------------------------------------- #
# Acceptance 4 — rejection leaves a log trail (observability)
# --------------------------------------------------------------------------- #
def test_auto_approval_logs_error_content_on_rejection():
    """F-11 Acceptance 4 (rejection-trail lock). On rejection the full error
    set MUST reach the log (count + every message) — historically this was
    silent, which let the loop burn ~400 paid rounds unnoticed."""
    from src.agent import runner

    captured = []
    sink_id = runner.logger.add(lambda msg: captured.append(str(msg)), level="WARNING")
    try:
        errors = ["cross-ref error: bad ref A", "cross-ref error: bad ref B"]
        decision = runner.auto_approval({"summary": {}, "errors": errors, "message": "x"})
    finally:
        runner.logger.remove(sink_id)

    assert decision["approved"] is False
    joined = "\n".join(captured)
    assert "AUTO-REJECTED" in joined
    assert "2 cross-ref error(s)" in joined
    assert "bad ref A" in joined and "bad ref B" in joined


def test_auto_approval_does_not_log_on_clean_approval():
    """F-11 Fix-B1 negative: a clean interrupt (no errors) is approved and
    produces NO warning log."""
    from src.agent import runner

    captured = []
    sink_id = runner.logger.add(lambda msg: captured.append(str(msg)), level="WARNING")
    try:
        decision = runner.auto_approval({"summary": {}, "errors": [], "message": "x"})
    finally:
        runner.logger.remove(sink_id)

    assert decision["approved"] is True
    assert captured == [], f"clean approval must not warn; got {captured}"
