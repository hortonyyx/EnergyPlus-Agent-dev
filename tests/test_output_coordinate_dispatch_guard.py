"""E4-output-contract spec v2 §5.3 sentinel — repo-wide lexical guard against
theta-truthiness / value-guessing coordinate-mode dispatch, plus the
WorkflowTool legacy_unbound / contract gate behavior (§5.2/§8.2)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.agent._share import ensure_schema_initialized

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"

# Forbidden mode-dispatch shapes (spec §5.3): deciding World-vs-Relative from a
# theta value, truthiness, or provenance instead of the verified contract.mode.
_FORBIDDEN = (
    re.compile(r"\bif\s+theta\b"),
    re.compile(r"\bif\s+north_axis\b"),
    re.compile(r"\bif\s+\w+\.north_axis\s*:"),
    re.compile(r"north_axis(?:_deg)?\s*!=\s*0[^=]*(?:relative|Relative)"),
    re.compile(r"(?:relative|world)_(?:north_axis|legacy)\s+if\s+\w*(?:theta|north_axis)"),
    re.compile(r'mode\s*=\s*["\']relative_north_axis["\']\s+if'),
    re.compile(r'provenance\s*==\s*["\'](?:observed|assumed)["\'].*mode'),
)


def test_no_theta_truthiness_dispatch_in_src():
    offenders: list[str] = []
    for path in _SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in _FORBIDDEN:
            for match in pattern.finditer(text):
                line_no = text[: match.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(_REPO)}:{line_no}: {match.group(0)!r}")
    assert offenders == [], "theta/value-guessing mode dispatch found:\n" + "\n".join(offenders)


def test_no_schema_version_three_mode_dispatch_outside_owners():
    """`schema_version == "3"` may decide the COORDINATE MODE only inside the
    two owner modules (agent/validator output_coordinates + the orientation
    producer). The correction/geometry stack legitimately branches on v3 for
    schema-shape reasons — this guard only pins modules that mention the
    contract modes."""
    owners = {
        "src/agent/output_coordinates.py",
        "src/validator/output_coordinates.py",
        "src/agent/correction/orientation.py",
        # pipeline.py branches on v3 to select the orientation-enrichment
        # PRODUCER step (enrichment is definitionally v3-only); the resulting
        # coordinate MODE is still derived exclusively by
        # derive_output_coordinate_contract from the verified ref.
        "src/agent/pipeline.py",
    }
    pattern = re.compile(r'schema_version\s*==\s*["\']3["\']')
    offenders = []
    for path in _SRC.rglob("*.py"):
        rel = str(path.relative_to(_REPO))
        if rel in owners:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "relative_north_axis" in text and pattern.search(text):
            offenders.append(rel)
    assert offenders == []


# --------------------------------------------------------------------------- #
# WorkflowTool gates
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _init_schema():
    ensure_schema_initialized()


def _config(north_axis=0.0, coordinate_system="World"):
    from src.mcp.state import ConfigState
    from src.validator import BuildingSchema, SiteLocationSchema
    from src.validator.data_model import GlobalGeometryRulesSchema

    cfg = ConfigState(
        building=BuildingSchema(name="B", north_axis=north_axis),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
    )
    cfg.global_geometry_rules = GlobalGeometryRulesSchema.model_validate(
        {"Coordinate System": coordinate_system})
    return cfg


def test_workflow_legacy_unbound_passes_world_zero():
    from src.mcp.tools.workflow import WorkflowTool

    tool = WorkflowTool(_config())
    assert tool._coordinate_gate() == []


def test_workflow_relative_config_without_contract_hard_fails():
    from src.mcp.tools.workflow import WorkflowTool

    tool = WorkflowTool(_config(coordinate_system="Relative"))
    issues = tool._coordinate_gate()
    assert issues and "Relative" in issues[0]


def test_workflow_legacy_unbound_rejects_nonzero_building_axis():
    from src.mcp.tools.workflow import WorkflowTool

    tool = WorkflowTool(_config(north_axis=45.0))
    issues = tool._coordinate_gate()
    assert issues and "North Axis" in issues[0]


def test_workflow_contract_without_context_refuses():
    from src.agent.output_coordinates import (
        AcceptedCorrectionRef,
        OutputCoordinateContract,
    )
    from src.mcp.tools.workflow import WorkflowTool

    contract = OutputCoordinateContract(
        mode="relative_north_axis",
        source=AcceptedCorrectionRef(
            schema_version="3", output_sha256="a" * 64,
            acceptance="integrated_gate1",
            artifact_contract="correction_e4_orientation_v1",
        ),
        geometry_frame="building_axis_absolute_values",
        global_geometry_coordinate_system="Relative",
        daylighting_reference_point_coordinate_system="Relative",
        rectangular_surface_coordinate_system="Relative",
        zone_origin_policy="all_zero", zone_direction_policy="all_zero",
        north_axis_owner="accepted_correction_orientation",
        north_axis_deg=90.0, orientation_provenance="observed",
        orientation_source_ids=("s1",), geometry_snapshot_sha256="b" * 64,
    )
    tool = WorkflowTool(_config(north_axis=90.0, coordinate_system="Relative"),
                        output_coordinates=contract, validation_context=None)
    issues = tool._coordinate_gate()
    assert issues and "context" in issues[0].lower()


def test_cross_ref_rechecks_contract_identity_before_export():
    from src.agent.nodes.cross_ref import cross_ref_foundations_node
    from src.agent.state import AgentState
    from src.agent.output_coordinates import AcceptedCorrectionRef, OutputCoordinateContract

    contract = OutputCoordinateContract(
        mode="relative_north_axis",
        source=AcceptedCorrectionRef(
            schema_version="3", output_sha256="a" * 64,
            acceptance="integrated_gate1", artifact_contract="correction_e4_orientation_v1",
        ),
        geometry_frame="building_axis_absolute_values",
        global_geometry_coordinate_system="Relative",
        daylighting_reference_point_coordinate_system="Relative",
        rectangular_surface_coordinate_system="Relative",
        zone_origin_policy="all_zero", zone_direction_policy="all_zero",
        north_axis_owner="accepted_correction_orientation", north_axis_deg=90.0,
        orientation_provenance="observed", orientation_source_ids=("s",),
        geometry_snapshot_sha256="b" * 64,
    )
    update = cross_ref_foundations_node(AgentState(output_coordinate_contract=contract))
    assert any("CONTRACT_IDENTITY" in error for error in update["validation_errors"])
