"""Stage registry + capability model + the per-stage attempt recorder (M0).

The 0–5 pipeline stages each have a *capability* that decides how a failure is
handled (contracts §0.3 failure classification):

  - ``manual``        — a human produces the artifact (0_reading today). Auto
                        routing can only ask for ``human_redraw_required``.
  - ``stochastic``    — an LLM draw (1_correction, 4_mep). A bad draw is
                        blind-resampled (same input, different sampling).
  - ``deterministic`` — code (core, 2_modelling, 3_split_pairing, 5_intakeoutput).
                        A post-condition failure is fail-closed: a code defect to
                        raise, never an upstream bounce / sample swap.

``StageRunner`` is the thin recorder that ties a produced artifact to an
append-only attempt dir + a CheckReport + the run manifest. It does NOT decide
cross-stage routing or invalidation — that belongs to the orchestrator
(invalidation.py). It deliberately does not reuse the correction-stage
``_make_correction_validator`` as a generic harness (施工 H2): single-stage draw
+ retry is a separate concern (judge/retry.py).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from src.agent.execution.manifest import (
    RunManifest,
    RunManifestV2,
    StageRecord,
    StageRecordV2,
    hash_obj,
    hash_text,
    new_attempt_dir,
)
from src.validator.checks.schema import CheckReport


class Capability(str, Enum):
    MANUAL = "manual"
    STOCHASTIC = "stochastic"
    DETERMINISTIC = "deterministic"


class StageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: str
    capability: Capability
    # Stages whose accepted output this stage consumes (for input-hash recording
    # and the invalidation DAG).
    depends_on: tuple[str, ...] = ()


# The canonical 0–5 stage chain (contracts §0). `core` is the deterministic snap
# folded into 1_correction's dir on disk but is a distinct deterministic step.
STAGE_REGISTRY: dict[str, StageSpec] = {
    s.stage: s
    for s in [
        StageSpec(stage="0_reading", capability=Capability.MANUAL),
        StageSpec(stage="1_correction", capability=Capability.STOCHASTIC,
                  depends_on=("0_reading",)),
        StageSpec(stage="2_modelling", capability=Capability.DETERMINISTIC,
                  depends_on=("1_correction",)),
        StageSpec(stage="3_split_pairing", capability=Capability.DETERMINISTIC,
                  depends_on=("2_modelling",)),
        StageSpec(stage="4_mep", capability=Capability.STOCHASTIC,
                  depends_on=("3_split_pairing",)),
        StageSpec(stage="5_intakeoutput", capability=Capability.DETERMINISTIC,
                  depends_on=("3_split_pairing", "4_mep")),
    ]
}

# Stable pipeline order (manifest / DAG iteration).
STAGE_ORDER: list[str] = list(STAGE_REGISTRY.keys())


def stage_spec(stage: str) -> StageSpec:
    try:
        return STAGE_REGISTRY[stage]
    except KeyError as e:
        raise KeyError(
            f"unknown stage '{stage}'; known: {', '.join(STAGE_REGISTRY)}"
        ) from e


class RecordedAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    attempt_index: int
    attempt_dir: str
    output_hash: str
    accepted: bool
    check_passed: bool


class StageRunner:
    """Files an attempt's artifacts under append-only dirs and updates the
    manifest pointer when the attempt is accepted.

    Usage::

        runner = StageRunner(case_dir, manifest)
        att = runner.record(
            stage="2_modelling",
            stage_dir=case_dir / "2_modelling",
            output_obj=building_geometry_dict,
            report=check_report,
            input_hashes={"1_correction": corr_hash},
        )

    ``record`` writes ``output.json`` + ``checks.json`` into a fresh attempt dir.
    Acceptance follows the failure-classification policy:
      - deterministic / manual: accepted iff the report does not block;
      - stochastic: the caller decides (a retry may supersede), default accept
        iff the report does not block.

    Versioned writer (C2 B-M §5.1, CR-02): the record's wire type follows the
    manifest the runner was constructed with. A :class:`RunManifestV2` gets a
    :class:`StageRecordV2` with ``artifact_contract="base_v2"`` and real,
    recomputed ``artifact_hashes`` for the two files this method just wrote
    (all six stages — this IS the "StageRunner 通用 attempt writer" of the
    contract table). The V1 branch remains only for read-only/legacy paths;
    normal command flows always arrive here holding a V2 manifest because
    run provisioning is V2-by-default and persisted-V1 runs are refused at the
    command entrances (grandfather hard gate).
    """

    def __init__(self, case_dir: Path, manifest: "RunManifest | RunManifestV2") -> None:
        self.case_dir = Path(case_dir)
        self.manifest = manifest

    def record(
        self,
        *,
        stage: str,
        stage_dir: Path,
        output_obj,
        report: CheckReport,
        input_hashes: dict[str, str] | None = None,
        stage_version: str = "1",
        accept: bool | None = None,
    ) -> RecordedAttempt:
        spec = stage_spec(stage)
        stage_dir = Path(stage_dir)
        stage_dir.mkdir(parents=True, exist_ok=True)
        adir = new_attempt_dir(stage_dir)

        from src.agent.correction.finalize import FinalizeResult
        from src.agent.correction.feature_state import (
            FeatureStatesArtifactV1,
            correction_stage_version,
            derive_feature_state_claims,
        )
        from src.agent.correction.config import load_core_tolerances
        from src.agent.correction.facade_visibility import (
            VisibilityTolerances,
            validate_materialized_facade_segments,
        )

        is_b2_correction = isinstance(output_obj, FinalizeResult)
        if is_b2_correction and stage != "1_correction":
            raise ValueError("FinalizeResult may only be written by 1_correction")
        out_text = (output_obj.geom.model_dump_json(indent=2) if is_b2_correction else
                    output_obj if isinstance(output_obj, str) else _to_json(output_obj))
        (adir / "output.json").write_text(out_text, encoding="utf-8")
        output_hash = hash_text(out_text)

        # Stamp the report with the hashes it was computed against, then persist.
        report.attempt_hash = output_hash
        if report.artifact_hash is None:
            report.artifact_hash = output_hash
        checks_text = report.model_dump_json(indent=2)
        (adir / "checks.json").write_text(checks_text, encoding="utf-8")
        artifact_hashes = {"output": output_hash, "checks": hash_text(checks_text)}
        if is_b2_correction:
            # Re-derive at the writer boundary; a frozen dataclass does not make
            # nested caller data trustworthy.
            from src.agent.correction.parse import CorrectionTarget
            target = CorrectionTarget(output_obj.geom.schema_version, type(output_obj.geom), report.capability_profile)
            expected = derive_feature_state_claims(target, output_obj.geom)
            if expected != output_obj.feature_state_claims:
                raise ValueError("INVARIANT: FinalizeResult feature-state claims were altered")
            if output_obj.geom.schema_version == "3":
                # Vg rework CR1 (writer fail-closed, verdict VG-CR1): do not
                # trust that `output_obj.geom.facade_segments` is what
                # `finalize_correction_draw` actually produced — a caller
                # could bypass that function entirely, tamper a real result
                # via `model_copy`, and re-derive `feature_state_claims` from
                # the tampered geom (the claims check above only looks at
                # shape — non-empty, full floor coverage — not values, so it
                # would not catch e.g. a mutated `depth`). Independently
                # recompute every floor's segments straight from the
                # authoritative `floor_footprint` ring and reject on any
                # item-for-item mismatch before this attempt is ever
                # accepted.
                tol = load_core_tolerances()
                visibility_tol = VisibilityTolerances(
                    depth_epsilon_m=tol.facade_visibility_depth_epsilon_m,
                    endpoint_epsilon_m=tol.facade_visibility_endpoint_epsilon_m,
                )
                validate_materialized_facade_segments(output_obj.geom, tolerances=visibility_tol)
            audit_text = _to_json(output_obj.audit_payload)
            (adir / "audit.json").write_text(audit_text, encoding="utf-8")
            states = FeatureStatesArtifactV1(output_sha256=output_hash, claims=expected)
            states_text = states.model_dump_json(indent=2)
            (adir / "feature_states.json").write_text(states_text, encoding="utf-8")
            artifact_hashes.update({"audit": hash_text(audit_text), "feature_states": hash_text(states_text)})

        check_passed = report.passed
        do_accept = check_passed if accept is None else accept
        rec = RecordedAttempt(
            stage=stage,
            attempt_index=int(adir.name),
            attempt_dir=str(adir),
            output_hash=output_hash,
            accepted=do_accept,
            check_passed=check_passed,
        )
        if do_accept:
            if is_b2_correction:
                # Vg rework CR2 (§9.2 central release-map policy): re-derive
                # the wire's stage_version from the same `expected` claims
                # re-derived above for the tamper check — never trust a
                # caller-supplied value, and never hardcode ANY correction
                # stage_version literal here (not "2", not "3"). The release
                # map in feature_state.py is now a single, explicit,
                # fail-closed table over the FULL claims state (schema +
                # helper_versions + all four feature states), so it already
                # has a registered legacy-v1 entry
                # (`("1", (), "not_declared"x4) -> "2"`) — there is no longer
                # a schema-version branch to collapse to a literal here; an
                # unregistered combination raises INVARIANT unconditionally.
                stage_version = correction_stage_version(expected)
            common = dict(
                stage=stage,
                accepted_attempt=rec.attempt_index,
                output_hash=output_hash,
                input_hashes=input_hashes or {},
                stage_version=stage_version,
                check_version=report.results[0].check_version
                if report.results
                else "1",
                capability=spec.capability.value,
                check_passed=check_passed,
            )
            if isinstance(self.manifest, RunManifestV2):
                self.manifest.accept(
                    StageRecordV2(
                        **common,
                        artifact_contract="correction_b2_v1" if is_b2_correction else "base_v2",
                        artifact_hashes=artifact_hashes,
                    )
                )
                if is_b2_correction:
                    # Convenience copies are promoted only after gate acceptance.
                    (stage_dir / "correction_geometry_snapped.json").write_text(out_text, encoding="utf-8")
                    (stage_dir / "corrections.json").write_text(_to_json(output_obj.audit_payload), encoding="utf-8")
            else:
                self.manifest.accept(StageRecord(**common))
        return rec


def _to_json(obj) -> str:
    import json

    from src.agent.correction.finalize import FinalizeResult
    if isinstance(obj, FinalizeResult):
        raise TypeError("FinalizeResult requires the explicit correction writer")
    if hasattr(obj, "model_dump_json"):  # pydantic
        return obj.model_dump_json(indent=2)
    return json.dumps(obj, indent=2, ensure_ascii=False)


# Re-export so callers can hash inputs without importing manifest directly.
__all__ = [
    "Capability",
    "StageSpec",
    "STAGE_REGISTRY",
    "STAGE_ORDER",
    "stage_spec",
    "StageRunner",
    "RecordedAttempt",
    "hash_obj",
]
