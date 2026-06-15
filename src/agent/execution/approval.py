"""Geometry approval gate — accepted-checkpoint digest binding (M0).

The user geometry-confirmation gate is a *calling policy*, not an
un-bypassable interactive step (contracts §1 2/3 ②a; §0.4 #9). This module owns
the durable record of an approval: ``geometry_approval.json`` binds an approval
to the **accepted geometry checkpoint digest** =

    hash( building_geometry.json
        + geometry_specs.md
        + kernel check report
        + stage/check version )

so that:
  - approving once and resuming reuses that exact geometry — 1_correction is NOT
    re-drawn (re-verify must-fix);
  - if any of those inputs drift after approval, the digest no longer matches and
    the approval is automatically stale (must re-approve).

``confirmation_policy`` (required | optional | disabled) is held in policy.py and
decides whether an *unapproved* checkpoint blocks; batch / CI / ``--intake-from``
(``validation_scope=downstream_only``) run with ``disabled`` so they are never
strapped to an interactive prompt.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from src.agent.execution.manifest import combined_digest, hash_obj, hash_text

APPROVAL_NAME = "geometry_approval.json"


def geometry_checkpoint_digest(
    *,
    building_geometry: dict,
    geometry_specs: str,
    kernel_check_report: dict,
    stage_version: str = "1",
    check_version: str = "1",
) -> str:
    """Deterministic digest of the four things an approval binds to. Order of the
    parts does not matter (combined_digest sorts)."""
    return combined_digest(
        [
            hash_obj(building_geometry),
            hash_text(geometry_specs),
            hash_obj(kernel_check_report),
            hash_text(f"stage={stage_version};check={check_version}"),
        ]
    )


class GeometryApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    digest: str
    actor: str                 # who approved (operator id / "ci" / "auto")
    policy: str = "required"   # the confirmation_policy in force at approval time
    timestamp: str = ""        # ISO; stamped by caller (scripts pass it in)
    note: str = ""

    # ---- io ----
    @classmethod
    def load(cls, case_dir: Path) -> "GeometryApproval | None":
        p = Path(case_dir) / APPROVAL_NAME
        if not p.exists():
            return None
        return cls.model_validate_json(p.read_text(encoding="utf-8"))

    def save(self, case_dir: Path) -> Path:
        p = Path(case_dir) / APPROVAL_NAME
        p.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return p


def is_approved(case_dir: Path, current_digest: str) -> bool:
    """True iff a stored approval matches the current geometry digest. A drifted
    checkpoint (digest mismatch) is treated as unapproved — fail-closed."""
    appr = GeometryApproval.load(case_dir)
    return appr is not None and appr.digest == current_digest
