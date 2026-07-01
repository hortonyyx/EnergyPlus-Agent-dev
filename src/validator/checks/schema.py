"""CheckReport v2 — the common schema every per-stage deterministic check emits.

Two ideas drive the design, both from the 2026-06-15 validation architecture
(see AI_agent/architecture/pipeline_stage_contracts.md §0.2/§0.4):

1. **Three layers** (§0.2). Every check declares which layer it belongs to:
     - ``invariant``   — a structural/geometric invariant that MUST hold; a
                         failure is a bug or fatal. Maps to BLOCK.
     - ``cross_check`` — reconciliation against an upstream constraint / another
                         channel / a plausibility band; a failure is a surface
                         for attribution, not a stop. Maps to FLAG.
     - ``perceptual``  — a faithfulness call deterministic code cannot make;
                         handled by a human / VLM judge. Not produced here.

2. **Policy ≠ fact** (§0.4 #8). A check emits a *fact*: ``CheckResult`` with a
   status and machine-readable evidence. Whether a failing fact *blocks* is a
   *policy* decision derived from ``(layer, status, capability_profile)`` by
   :func:`disposition` — kept a pure function so the same fact can map
   differently under different profiles. A check that does not apply under the
   active profile emits ``not_applicable`` (e.g. the rectangular-coverage check
   under a non-rectangular profile), so blocking stays profile-aware without the
   check itself knowing the policy.

The report carries the ``artifact_hash`` / ``attempt_hash`` it was computed
against so an accepted attempt's checks are auditable after the fact (M0
append-only attempts), plus ``check_version`` for golden-test stability.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Bump when the report-level shape changes (golden tests assert on this).
REPORT_SCHEMA_VERSION = "2.1"

RunProfile = Literal["exploratory", "dev", "golden", "regression"]

EVIDENCE_CHECK_IDS = frozenset(
    {
        "reading.dimension_chain_closure",
        "reading.dimension_derived_refs",
        "reading.dimensions_present",
        "reading.dimension_p1a_fields",
        "reading.raw_field_presence",
        "reading.stroke_provenance_coverage",
    }
)

_EVIDENCE_BLOCK_PROFILES = {"golden", "regression"}


def is_evidence_check_id(check_id: str) -> bool:
    return check_id in EVIDENCE_CHECK_IDS or any(
        check_id.endswith(f".{canonical}") for canonical in EVIDENCE_CHECK_IDS
    )


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"          # intentionally not run (e.g. viewer headless)
    NOT_APPLICABLE = "not_applicable"  # does not apply under the active profile
    ERROR = "error"             # the check itself blew up — fail-closed


class CheckLayer(str, Enum):
    INVARIANT = "invariant"      # §0.2 L-不变量 — hard, BLOCK on fail
    CROSS_CHECK = "cross_check"  # §0.2 L-交叉核对 — soft, FLAG on fail
    PERCEPTUAL = "perceptual"    # §0.2 L-肉眼/judge — not produced by det. checks


class Disposition(str, Enum):
    BLOCK = "block"   # stop the pipeline / fail-closed
    FLAG = "flag"     # surface for attribution, do not stop
    INFO = "info"     # pass / not-applicable — informational
    SKIP = "skip"     # intentionally skipped


class CheckResult(BaseModel):
    """One check outcome — a FACT, not a policy decision."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    status: CheckStatus
    layer: CheckLayer
    check_version: str = "1"
    message: str = ""
    # Machine-readable evidence (counts, offending ids, deltas) — never prose
    # only, so a downstream consumer / judge can act on it programmatically.
    evidence: dict = Field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in (
            CheckStatus.PASS,
            CheckStatus.SKIPPED,
            CheckStatus.NOT_APPLICABLE,
        )


def disposition(
    result: CheckResult,
    *,
    capability_profile: str = "rectangular",
    run_profile: RunProfile = "exploratory",
) -> Disposition:
    """Map a check FACT to a policy disposition. Pure function (§0.4 #8).

    ``capability_profile`` is accepted so a future profile can downgrade a
    specific invariant; today the default rules below are profile-agnostic
    because profile applicability is expressed by the check emitting
    ``not_applicable`` rather than by the policy reinterpreting a ``fail``.
    """
    if result.status == CheckStatus.PASS:
        return Disposition.INFO
    if result.status == CheckStatus.NOT_APPLICABLE:
        return Disposition.INFO
    if result.status == CheckStatus.SKIPPED:
        return Disposition.SKIP
    if result.status == CheckStatus.ERROR:
        # A check that errored is fail-closed: we do not know the artifact is
        # clean, so we must not let it pass silently.
        return Disposition.BLOCK
    # status == FAIL
    if is_evidence_check_id(result.check_id):
        if result.evidence.get("legacy_migrated"):
            return Disposition.FLAG
        if run_profile in _EVIDENCE_BLOCK_PROFILES:
            return Disposition.BLOCK
        return Disposition.FLAG
    if result.layer == CheckLayer.INVARIANT:
        return Disposition.BLOCK
    return Disposition.FLAG  # cross_check / perceptual failures flag, don't stop


class CheckReport(BaseModel):
    """All deterministic check results for one stage attempt (gate ①)."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    capability_profile: str = "rectangular"
    run_profile: RunProfile = "exploratory"
    artifact_hash: str | None = None
    attempt_hash: str | None = None
    report_schema_version: str = REPORT_SCHEMA_VERSION
    results: list[CheckResult] = Field(default_factory=list)

    # ---- mutation helpers (checks append as they run) ----
    def add(
        self,
        check_id: str,
        status: CheckStatus,
        layer: CheckLayer,
        *,
        message: str = "",
        evidence: dict | None = None,
        check_version: str = "1",
    ) -> CheckResult:
        r = CheckResult(
            check_id=check_id,
            status=status,
            layer=layer,
            check_version=check_version,
            message=message,
            evidence=evidence or {},
        )
        self.results.append(r)
        return r

    def add_pass(self, check_id: str, layer: CheckLayer, **kw) -> CheckResult:
        return self.add(check_id, CheckStatus.PASS, layer, **kw)

    def add_fail(
        self, check_id: str, layer: CheckLayer, message: str, **kw
    ) -> CheckResult:
        return self.add(check_id, CheckStatus.FAIL, layer, message=message, **kw)

    # ---- policy-aware queries ----
    def dispositions(self) -> list[tuple[CheckResult, Disposition]]:
        return [
            (
                r,
                disposition(
                    r,
                    capability_profile=self.capability_profile,
                    run_profile=self.run_profile,
                ),
            )
            for r in self.results
        ]

    def blocking(self) -> list[CheckResult]:
        """Results whose policy disposition is BLOCK (fail-closed set)."""
        return [
            r
            for r, d in self.dispositions()
            if d == Disposition.BLOCK
        ]

    def flagged(self) -> list[CheckResult]:
        return [r for r, d in self.dispositions() if d == Disposition.FLAG]

    @property
    def passed(self) -> bool:
        """True iff nothing blocks (flags are allowed through gate ①)."""
        return not self.blocking()
