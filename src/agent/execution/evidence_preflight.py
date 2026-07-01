"""A8 correction preflight for reading evidence debt.

The authoritative facts stay in the 0_reading ``CheckReport``. This module only
projects the evidence-check subset into a lightweight handoff artifact for
1_correction, re-evaluating disposition under the *current* run profile.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.agent.reading import load_reading_view
from src.validator.checks.reading import check_reading_view
from src.validator.checks.schema import (
    CheckReport,
    Disposition,
    RunProfile,
    disposition,
    is_evidence_check_id,
)

EVIDENCE_DEBT_SCHEMA_VERSION = "1"
EVIDENCE_DEBT_PRODUCER = "src.agent.execution.evidence_preflight"


class EvidenceDebtItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str
    canonical_check_id: str
    view: str | None = None
    status: str
    layer: str
    disposition: str
    message: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    scope: str = "view_global"
    offender_ids: list[str] = Field(default_factory=list)


class EvidenceDebt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = EVIDENCE_DEBT_SCHEMA_VERSION
    producer: str = EVIDENCE_DEBT_PRODUCER
    run_profile: RunProfile = "exploratory"
    capability_profile: str = "rectangular"
    source_stage: str = "0_reading"
    debts: list[EvidenceDebtItem] = Field(default_factory=list)

    @property
    def blocking(self) -> list[EvidenceDebtItem]:
        return [item for item in self.debts if item.disposition == Disposition.BLOCK.value]


def canonical_evidence_check_id(check_id: str) -> str:
    marker = ".reading."
    if check_id.startswith("reading."):
        return check_id
    if marker in check_id:
        return check_id[check_id.index(marker) + 1 :]
    return check_id


def evidence_view_name(check_id: str) -> str | None:
    marker = ".reading."
    if marker not in check_id:
        return None
    prefix = check_id[: check_id.index(marker)]
    return prefix or None


def _offender_ids(evidence: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    offenders = evidence.get("offenders")
    if isinstance(offenders, list):
        for offender in offenders:
            if not isinstance(offender, dict):
                continue
            value = offender.get("stroke_id")
            if isinstance(value, str) and value:
                ids.append(value)
    return sorted(dict.fromkeys(ids))


def project_evidence_debt(
    report: CheckReport,
    *,
    run_profile: RunProfile = "exploratory",
) -> EvidenceDebt:
    """Project evidence-check failures from a CheckReport under current policy."""
    items: list[EvidenceDebtItem] = []
    for result in report.results:
        if not is_evidence_check_id(result.check_id):
            continue
        disp = disposition(
            result,
            capability_profile=report.capability_profile,
            run_profile=run_profile,
        )
        if disp not in (Disposition.BLOCK, Disposition.FLAG):
            continue
        offender_ids = _offender_ids(result.evidence)
        items.append(
            EvidenceDebtItem(
                check_id=result.check_id,
                canonical_check_id=canonical_evidence_check_id(result.check_id),
                view=evidence_view_name(result.check_id),
                status=result.status.value,
                layer=result.layer.value,
                disposition=disp.value,
                message=result.message,
                evidence=dict(result.evidence),
                scope="element_local" if offender_ids else "view_global",
                offender_ids=offender_ids,
            )
        )
    return EvidenceDebt(
        run_profile=run_profile,
        capability_profile=report.capability_profile,
        source_stage=report.stage,
        debts=items,
    )


def dimensioned_view_names_from_testdata_text(testdata_text: str | None) -> set[str]:
    if not testdata_text:
        return set()
    try:
        data = json.loads(testdata_text)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict):
        return set()

    names: set[str] = set()

    def add(value: object) -> None:
        if not isinstance(value, str) or not value:
            return
        p = Path(value)
        names.add(p.stem if p.suffix else value)

    for value in data.get("dimensioned_views") or []:
        add(value)

    for item in data.get("Floor plans") or []:
        if isinstance(item, dict) and item.get("dimensioned") is True:
            add(item.get("path"))
            floor = item.get("floor")
            if floor is not None:
                add(f"{floor}f_view")

    views = data.get("views") or {}
    if isinstance(views, dict):
        for key, item in views.items():
            if isinstance(item, dict) and item.get("dimensioned") is True:
                add(key)
                add(item.get("path"))

    return names


def compute_evidence_debt_from_vector_dir(
    vector_dir: Path,
    *,
    run_profile: RunProfile = "exploratory",
    capability_profile: str = "rectangular",
    dimensioned_views: set[str] | None = None,
) -> EvidenceDebt:
    """Run reading checks and project only evidence debt for correction."""
    vector_dir = Path(vector_dir)
    dimensioned_views = dimensioned_views or set()
    merged = CheckReport(
        stage="0_reading",
        capability_profile=capability_profile,
        run_profile=run_profile,
    )
    for path in sorted(vector_dir.glob("*_view.json")):
        view = load_reading_view(path)
        sub = check_reading_view(
            view,
            capability_profile=capability_profile,
            run_profile=run_profile,
            view_metadata={"dimensioned": path.stem in dimensioned_views},
        )
        for result in sub.results:
            merged.results.append(
                result.model_copy(update={"check_id": f"{path.stem}.{result.check_id}"})
            )
    return project_evidence_debt(merged, run_profile=run_profile)


def write_evidence_debt(path: Path, debt: EvidenceDebt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(debt.model_dump_json(indent=2), encoding="utf-8")


def load_evidence_debt(path: Path) -> EvidenceDebt | None:
    if not path.exists():
        return None
    return EvidenceDebt.model_validate_json(path.read_text(encoding="utf-8"))
