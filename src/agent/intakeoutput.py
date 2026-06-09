"""5_intakeoutput — deterministic assembly of the final IntakeOutput.

Combines the deterministic geometry specs (from the kernel serializer) with the
non-geometry specs the 4_MEP LLM stage authors, then runs a deterministic
contract check before the result leaves the project boundary. The check is an
early, deterministic fail for the one cross-stage hazard the split introduces:
the serializer emits construction names (e.g. `Cons_InterFloor`) that 4_MEP must
define — if 4_MEP omits one, the surfaces referencing it would drop and EnergyPlus
would fatal. We catch that here, by name, not at EP.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.agent.state import IntakeOutput
from src.validator import BuildingSchema, SiteLocationSchema


class MepOutput(BaseModel):
    """The 4_MEP stage's output: everything in IntakeOutput except the three
    geometry spec fields (zone/surface/fenestration), which come from the kernel."""

    building: BuildingSchema = Field(description="Building object")
    site_location: SiteLocationSchema = Field(description="Site location")
    material_specs: str
    construction_specs: str
    schedule_specs: str
    hvac_specs: str
    people_specs: str
    lights_specs: str


def assemble_intake_output(
    *,
    zone_specs: str,
    surface_specs: str,
    fenestration_specs: str,
    mep: MepOutput,
) -> IntakeOutput:
    """Stitch the deterministic geometry specs and the MEP specs into one
    IntakeOutput. Pure mechanical merge — no field is invented here."""
    return IntakeOutput(
        building=mep.building,
        site_location=mep.site_location,
        zone_specs=zone_specs,
        material_specs=mep.material_specs,
        schedule_specs=mep.schedule_specs,
        construction_specs=mep.construction_specs,
        surface_specs=surface_specs,
        fenestration_specs=fenestration_specs,
        hvac_specs=mep.hvac_specs,
        people_specs=mep.people_specs,
        lights_specs=mep.lights_specs,
    )


def _defines(text: str, name: str) -> bool:
    """Case-sensitive whole-token match (names are case-sensitive in EnergyPlus
    and cross-field references must be literally identical). Underscores are word
    chars, so `Default_Ext_Wall` does NOT match inside `Default_Ext_Wall_2`."""
    return re.search(rf"(?<![\w]){re.escape(name)}(?![\w])", text) is not None


def validate_contract(
    intake: IntakeOutput, used_constructions: set[str]
) -> list[str]:
    """Deterministic cross-stage contract check. Returns the list of issues.

    Hard issue (the caller raises on these): a construction the geometry
    serializer referenced is not defined in `construction_specs` — a 4_MEP
    omission that would drop surfaces at EnergyPlus.
    """
    issues: list[str] = []
    for cons in sorted(used_constructions):
        if not _defines(intake.construction_specs, cons):
            issues.append(
                f"construction '{cons}' is referenced by the geometry specs but "
                f"not defined in construction_specs (4_MEP must define it)"
            )
    return issues
