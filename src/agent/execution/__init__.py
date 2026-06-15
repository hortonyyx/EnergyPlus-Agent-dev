"""Execution & audit foundation (M0).

Stage runner + registry, run manifest with append-only attempts, the
invalidation DAG + resume + budget, the geometry-approval digest, and the run
policy. Gates (M2+) and the judge harness (M3) attach to this layer; per the
build plan, no gate is wired before it exists.
"""

from __future__ import annotations

from src.agent.execution.approval import (
    GeometryApproval,
    geometry_checkpoint_digest,
    is_approved,
)
from src.agent.execution.invalidation import (
    BudgetExceeded,
    RouteCycleDetected,
    RunBudget,
    downstream_of,
    invalidate,
    stages_to_run,
)
from src.agent.execution.manifest import (
    RunManifest,
    StageRecord,
    combined_digest,
    hash_file,
    hash_obj,
    hash_text,
    new_attempt_dir,
    next_attempt_index,
)
from src.agent.execution.policy import (
    ConfirmationPolicy,
    RunPolicy,
    ValidationScope,
)
from src.agent.execution.routing import RouteAction, route_stage_failure
from src.agent.execution.validation_run import (
    CaseValidationResult,
    validate_case,
)
from src.agent.execution.stage_runner import (
    STAGE_ORDER,
    STAGE_REGISTRY,
    Capability,
    RecordedAttempt,
    StageRunner,
    StageSpec,
    stage_spec,
)

__all__ = [
    "GeometryApproval",
    "geometry_checkpoint_digest",
    "is_approved",
    "BudgetExceeded",
    "RouteCycleDetected",
    "RunBudget",
    "downstream_of",
    "invalidate",
    "stages_to_run",
    "RunManifest",
    "StageRecord",
    "combined_digest",
    "hash_file",
    "hash_obj",
    "hash_text",
    "new_attempt_dir",
    "next_attempt_index",
    "ConfirmationPolicy",
    "RunPolicy",
    "ValidationScope",
    "RouteAction",
    "route_stage_failure",
    "CaseValidationResult",
    "validate_case",
    "STAGE_ORDER",
    "STAGE_REGISTRY",
    "Capability",
    "RecordedAttempt",
    "StageRunner",
    "StageSpec",
    "stage_spec",
]
