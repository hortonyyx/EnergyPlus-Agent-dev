"""Stage-0 building contract examples and deterministic rejection cases.

The public ``make_*_bundle`` factories are intentionally reusable by the six
real-backed stage-0 fixtures.  Their default IDs are small stand-ins, not case
facts or a second object-identity system.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.agent.contracts import (
    BuildingContractBundle,
    BuildingDeclaration,
    BuildingEvidenceLedger,
    BuildingModelVersion,
    BuildingObjectRef,
    CalculationChain,
    CalculationStep,
    CheckResult,
    ConnectivityState,
    CoordinateRelation,
    CoverageEntry,
    CoverageIssue,
    DeclarationScope,
    DimensionEdit,
    DimensionState,
    DirectObservation,
    EvidenceConflict,
    EvidenceGroup,
    EvidenceItem,
    EvidencePackage,
    EvidenceTaskBudget,
    EvidenceTemplate,
    ExistingEvidenceRef,
    ExistingTargetLine,
    ExistingToolCall,
    FeatureDisposition,
    FieldPartition,
    FloorDraftContract,
    InferenceHypothesis,
    LocalInterpretation,
    LocalUncertainty,
    LocalizedEvidenceResult,
    NormalizationProposal,
    ObjectEvidenceBinding,
    OpeningSemanticState,
    PixelLocation,
    Quantity,
    RepetitionInstance,
    RepetitionRule,
    RunQualifiedEvidenceRef,
    SavedModelSnapshot,
    SavedVerification,
    SemanticSnapshot,
    SuggestedAction,
    ToleranceDecision,
    UserRequirement,
    ValueSnapshot,
    assert_result_applicable,
)


SHA_ORIGINAL = "1" * 64
SHA_MODEL_1 = "2" * 64
SHA_MODEL_2 = "3" * 64
SHA_ARTIFACT_1 = "4" * 64
SHA_ARTIFACT_2 = "5" * 64


def make_view_ref(view_id: str = "view_0001") -> RunQualifiedEvidenceRef:
    """A real-shaped crop that was resized before a model saw it."""

    return RunQualifiedEvidenceRef(
        run_id="run-stage0-example",
        reference=ExistingEvidenceRef(scheme="view_id", value=view_id),
        original_sha256=SHA_ORIGINAL,
        coordinate_relation=CoordinateRelation(
            referenced_space="view_pixels",
            relation="crop_and_affine",
            crop_original_pixels=(100.0, 50.0, 500.0, 250.0),
            original_to_referenced_affine=(0.5, 0.0, -50.0, 0.0, 0.5, -25.0),
        ),
    )


def make_record_ref(identity: str, scheme: str) -> RunQualifiedEvidenceRef:
    return RunQualifiedEvidenceRef(
        run_id="run-stage0-example",
        reference=ExistingEvidenceRef(scheme=scheme, value=identity),
        original_sha256=SHA_ORIGINAL,
        coordinate_relation=CoordinateRelation(
            referenced_space="original_image_pixels", relation="identity"
        ),
    )


def make_semantic_snapshot() -> SemanticSnapshot:
    return SemanticSnapshot(
        floor_ids=("F1", "F2"),
        wall_ids=("wall:north", "wall:shared"),
        room_ids=("F1:R1", "F1:R2"),
        openings=(
            OpeningSemanticState(
                object_kind="opening",
                opening_id="F1:D1",
                host_ids=("F1:R1", "F1:R2"),
                p1=(3.94, 1.0),
                p2=(3.94, 2.0),
                z_range=(0.0, 2.1),
            ),
        ),
        connectivity=(
            ConnectivityState(connection_id="conn:D1", object_ids=("F1:R1", "F1:R2")),
        ),
    )


def make_contract_bundle(
    case_id: str,
    *,
    mode: str,
    coarse_merge: bool = False,
    room_id: str = "F1:R1",
    view_id: str = "view_0001",
) -> BuildingContractBundle:
    """Build a connected sample; callers may replace IDs with real case IDs.

    ``mode`` is ``reconstruction``, ``partial_inference`` or ``photo_inference``.
    Every mode exercises the same evidence/calculation/check/coverage interfaces.
    """

    if mode not in {"reconstruction", "partial_inference", "photo_inference"}:
        raise ValueError("unsupported sample mode")
    target = BuildingObjectRef(kind="space", id=room_id)
    second = BuildingObjectRef(kind="space", id="F1:R2")
    view = make_view_ref(view_id)
    inference_ref = make_record_ref("inference_001", "record_inference")
    claim_ref = make_record_ref("claim_0001", "claim")
    requirement_kind = "simplification" if coarse_merge else "fidelity"
    requirement = UserRequirement(
        requirement_id="req:detail",
        kind=requirement_kind,
        statement=(
            "Merge the represented rooms into one coarse source space."
            if coarse_merge
            else "Keep the requested source-space detail in the saved model."
        ),
        target_objects=(target,),
    )
    items = (
        EvidenceItem(
            evidence_id="ev:observed",
            kind="observation",
            statement="A located line or facade feature is directly visible.",
            source_refs=(view,),
        ),
        EvidenceItem(
            evidence_id="ev:inferred",
            kind="inference",
            statement="The missing arrangement is interpreted from architectural context.",
            source_refs=(inference_ref,),
        ),
        EvidenceItem(
            evidence_id="ev:simplified",
            kind="simplification",
            statement="The source-space detail follows the selected delivery preference.",
            source_refs=(claim_ref,),
            requirement_ids=(requirement.requirement_id,),
        ),
        EvidenceItem(
            evidence_id="ev:assumed",
            kind="assumption",
            statement="Unobserved storey height is provisionally 3 m.",
            source_refs=(inference_ref,),
        ),
    )
    ledger = BuildingEvidenceLedger(
        items=items,
        templates=(
            EvidenceTemplate(
                template_id="template:storey",
                evidence_ids=("ev:observed", "ev:assumed"),
            ),
        ),
        groups=(
            EvidenceGroup(
                group_id="group:rooms",
                members=(target, second),
                template_ids=("template:storey",),
                evidence_ids=("ev:inferred", "ev:simplified"),
            ),
        ),
        bindings=(
            ObjectEvidenceBinding(object_ref=target, group_ids=("group:rooms",)),
            ObjectEvidenceBinding(object_ref=second, group_ids=("group:rooms",)),
        ),
        conflicts=(
            EvidenceConflict(
                conflict_id="conflict:line",
                evidence_ids=("ev:observed", "ev:inferred"),
                status="resolved",
                resolution="Retain the annotated existing line and record the differing interpretation.",
            ),
        ),
    )
    if mode == "photo_inference":
        raw_value, converted_value, normalized_value = 3000.0, 3.0, 3.0
        calculation_evidence = ("ev:assumed",)
    else:
        raw_value, converted_value, normalized_value = 6000.0, 6.0, 5.94
        calculation_evidence = ("ev:observed",)
    raw = Quantity(value=raw_value, unit="mm")
    converted = Quantity(value=converted_value, unit="m")
    normalized = Quantity(value=normalized_value, unit="m")
    calculation = CalculationChain(
        calculation_id="calc:dimension",
        object_ref=target,
        field_path="/geometry/floors/0/cells/0/y/1",
        evidence_ids=calculation_evidence,
        steps=(
            CalculationStep(stage="raw", input=None, output=raw, reason="raw annotation or explicit assumption"),
            CalculationStep(stage="converted", input=raw, output=converted, reason="millimetres converted to metres"),
            CalculationStep(stage="normalized", input=converted, output=normalized, reason="align to the existing 3.94 m line"),
            CalculationStep(stage="saved", input=normalized, output=normalized, reason="persist the normalized dimension unchanged"),
        ),
    )
    choice = InferenceHypothesis(
        hypothesis_id="hyp:choice",
        kind="design_choice",
        statement="Use the selected detail strategy for this object group.",
        object_refs=(target,),
        requirement_ids=(requirement.requirement_id,),
        evidence_ids=("ev:inferred", "ev:simplified"),
    )
    relation = InferenceHypothesis(
        hypothesis_id="hyp:relation",
        kind="spatial_relation",
        statement="The two spaces are adjacent across the shared wall.",
        object_refs=(target, second),
        evidence_ids=("ev:inferred",),
    )
    scope = (
        DeclarationScope(kind="cross_floor_space", ids=("atrium:A", "F1", "F2"))
        if mode == "partial_inference"
        else DeclarationScope(kind="floor", ids=("F1",))
    )
    if mode == "reconstruction":
        call = ExistingToolCall(
            tool="build_plan_bim", payload={"image": "plan.png", "plan_json": "{\"floor_id\":\"F1\"}"}
        )
    elif mode == "photo_inference":
        call = ExistingToolCall(
            tool="build_parametric_bim", payload={"plan_json": "{\"geometry\":{\"schema_version\":\"2\"}}"}
        )
    else:
        call = ExistingToolCall(
            tool="revise_bim", payload={"candidate": "candidate_001", "operations_json": "[]"}
        )
    repetition = None
    if mode == "partial_inference":
        repetition = RepetitionRule(
            repeat_by="floor",
            instances=(
                RepetitionInstance(
                    instance_id="repeat:F1",
                    scope=DeclarationScope(kind="floor", ids=("F1",)),
                ),
                RepetitionInstance(
                    instance_id="repeat:F2",
                    scope=DeclarationScope(kind="floor", ids=("F2",)),
                    exceptions={"/openings/F2:D1/width_m": 1.2},
                ),
            ),
        )
    declaration = BuildingDeclaration(
        declaration_id="decl:main",
        scope=scope,
        tool_call=call,
        field_partition=FieldPartition(
            model_declared=("/geometry/floors", "/geometry/openings"),
            code_expanded=("/source_model/spaces", "/source_model/connections"),
        ),
        evidence_ids=("ev:inferred", "ev:simplified"),
        requirement_ids=(requirement.requirement_id,),
        hypothesis_ids=(choice.hypothesis_id, relation.hypothesis_id),
        repetition=repetition,
        declared_object_refs=(target, second),
    )
    versions = (
        BuildingModelVersion(
            model_version_id="model:v1",
            source_model_sha256=SHA_MODEL_1,
            artifact_sha256=SHA_ARTIFACT_1,
            declaration_ids=(declaration.declaration_id,),
        ),
        BuildingModelVersion(
            model_version_id="model:v2",
            source_model_sha256=SHA_MODEL_2,
            artifact_sha256=SHA_ARTIFACT_2,
            declaration_ids=(declaration.declaration_id,),
        ),
    )
    package = EvidencePackage(
        package_id="package:local",
        task_id="task:local",
        role_id="local_observer",
        question="Locate the line and separate direct observation from interpretation.",
        known_evidence_ids=("ev:observed",),
        image_refs=(view,),
        source_model_version_id="model:v1",
        budget=EvidenceTaskBudget(
            max_input_tokens=4000,
            max_output_tokens=1000,
            max_tool_calls=3,
            max_wall_seconds=120.0,
        ),
    )
    direct = DirectObservation(
        observation_id="seen:line",
        statement="A continuous line is visible in the crop.",
        location=PixelLocation(image_ref=view, box_original_pixels=(150.0, 80.0, 160.0, 220.0)),
    )
    result = LocalizedEvidenceResult(
        package_id=package.package_id,
        task_id=package.task_id,
        based_on_source_model_version_id=package.source_model_version_id,
        directly_seen=(direct,),
        interpretations=(
            LocalInterpretation(
                interpretation_id="interpretation:wall",
                statement="The line probably represents a wall face.",
                based_on_observation_ids=(direct.observation_id,),
                confidence="medium",
            ),
        ),
        uncertain=(
            LocalUncertainty(
                uncertainty_id="uncertain:face",
                statement="The crop alone does not establish whether this is the wall face or centreline.",
                related_observation_ids=(direct.observation_id,),
            ),
        ),
    )
    verification = SavedVerification(
        model_version_id="model:v2",
        artifact_sha256=SHA_ARTIFACT_2,
        inspected_objects=(target,),
    )
    checks = (
        CheckResult(
            check_id="check:geometry",
            category="geometry",
            status="passed",
            involved_objects=(target,),
            evidence_ids=("ev:observed",),
            suggested_action=SuggestedAction(
                kind="dimension_normalization", description="Align the noise to the existing 3.94 m line."
            ),
            tolerance=ToleranceDecision(
                origin="profile_limit",
                value=0.12,
                unit="m",
                source_id="detail:default",
                reason="the profile caps alignment at one relevant wall thickness",
            ),
            before=ValueSnapshot(value=4.0, unit="m"),
            after=ValueSnapshot(value=3.94, unit="m"),
            saved_verification=verification,
        ),
        CheckResult(
            check_id="check:coverage",
            category="coverage",
            status="passed",
            involved_objects=(target,),
            evidence_ids=("ev:simplified",),
            suggested_action=SuggestedAction(kind="no_action", description="Saved object satisfies the selected choice."),
            tolerance=None,
            before=ValueSnapshot(value={"saved_objects": []}),
            after=ValueSnapshot(value={"saved_objects": [room_id]}),
            saved_verification=verification,
        ),
    )
    semantics = make_semantic_snapshot()
    normalization = NormalizationProposal(
        proposal_id="normalization:line",
        check_ids=("check:geometry",),
        tolerance=checks[0].tolerance,
        features=(
            FeatureDisposition(
                feature_id="feature:6cm",
                classification="drawing_noise",
                decision="normalize",
                reason="the 6 cm offset is below the chosen alignment limit and conflicts with the established line",
            ),
            FeatureDisposition(
                feature_id="feature:narrow",
                classification="genuine_narrow",
                decision="preserve",
                reason="the narrow service space has its own boundaries and use",
            ),
        ),
        edits=(
            DimensionEdit(
                feature_id="feature:6cm",
                object_ref=target,
                field_path="/geometry/floors/0/cells/0/y/1",
                before_m=4.0,
                after_m=3.94,
                target=ExistingTargetLine(
                    object_ref=BuildingObjectRef(kind="boundary", id="wall:north"),
                    field_path="/source_model/boundaries/wall:north/coordinate",
                    coordinate_m=3.94,
                    selection_reason="the existing cross-floor line serves more rooms and floors",
                ),
            ),
        ),
        before=SavedModelSnapshot(
            model_version_id="model:v1",
            artifact_sha256=SHA_ARTIFACT_1,
            semantics=semantics,
            dimensions=(
                DimensionState(
                    object_ref=target,
                    field_path="/geometry/floors/0/cells/0/y/1",
                    value_m=4.0,
                ),
                DimensionState(
                    object_ref=BuildingObjectRef(kind="boundary", id="wall:north"),
                    field_path="/source_model/boundaries/wall:north/coordinate",
                    value_m=3.94,
                ),
            ),
        ),
        after=SavedModelSnapshot(
            model_version_id="model:v2",
            artifact_sha256=SHA_ARTIFACT_2,
            semantics=semantics,
            dimensions=(
                DimensionState(
                    object_ref=target,
                    field_path="/geometry/floors/0/cells/0/y/1",
                    value_m=3.94,
                ),
                DimensionState(
                    object_ref=BuildingObjectRef(kind="boundary", id="wall:north"),
                    field_path="/source_model/boundaries/wall:north/coordinate",
                    value_m=3.94,
                ),
            ),
        ),
    )
    draft_declaration = declaration.model_copy(update={"declaration_id": "decl:draft"})
    if draft_declaration.scope.kind != "floor":
        draft_declaration = draft_declaration.model_copy(
            update={"scope": DeclarationScope(kind="floor", ids=("F1",)), "repetition": None}
        )
    floor_draft = FloorDraftContract(
        floor_id="F1",
        based_on_source_model_version_id="model:v1",
        proposed_declaration=draft_declaration,
        open_questions=("Confirm the unobserved internal door height.",),
    )
    return BuildingContractBundle(
        case_id=case_id,
        requirements=(requirement,),
        evidence=ledger,
        calculations=(calculation,),
        hypotheses=(choice, relation),
        declarations=(declaration,),
        model_versions=versions,
        evidence_packages=(package,),
        evidence_results=(result,),
        floor_drafts=(floor_draft,),
        checks=checks,
        normalizations=(normalization,),
        coverage_issues=(),
        coverage=(
            CoverageEntry(
                coverage_id="coverage:detail",
                requirement_id=requirement.requirement_id,
                choice_hypothesis_id=choice.hypothesis_id,
                saved_model_version_id="model:v2",
                actual_objects=(target,),
                check_ids=("check:coverage",),
                open_issue_ids=(),
                status="complete",
                coarse_merge=coarse_merge,
            ),
        ),
    )


def make_reconstruction_bundle() -> BuildingContractBundle:
    return make_contract_bundle("sample:reconstruction", mode="reconstruction")


def make_partial_inference_bundle(*, coarse_merge: bool = False) -> BuildingContractBundle:
    return make_contract_bundle(
        "sample:partial-inference", mode="partial_inference", coarse_merge=coarse_merge
    )


def make_photo_inference_bundle() -> BuildingContractBundle:
    return make_contract_bundle("sample:photo-inference", mode="photo_inference")


@pytest.mark.parametrize(
    "factory",
    [make_reconstruction_bundle, make_partial_inference_bundle, make_photo_inference_bundle],
)
def test_public_factories_are_connected_and_round_trip(factory):
    bundle = factory()
    assert BuildingContractBundle.model_validate_json(bundle.model_dump_json()) == bundle
    assert bundle.evidence.expanded_object_evidence()["space:F1:R1"] == (
        "ev:assumed",
        "ev:inferred",
        "ev:observed",
        "ev:simplified",
    )
    assert bundle.evidence_impact_index()["ev:observed"] == {
        "declaration_ids": ("decl:main",),
        "model_version_ids": ("model:v1", "model:v2"),
    }


def test_partial_sample_has_cross_floor_scope_repetition_and_exception():
    declaration = make_partial_inference_bundle().declarations[0]
    assert declaration.scope.kind == "cross_floor_space"
    assert declaration.repetition.instances[1].exceptions == {"/openings/F2:D1/width_m": 1.2}


def test_photo_assumption_calculation_is_explicit_not_an_observation():
    bundle = make_photo_inference_bundle()
    assert bundle.calculations[0].evidence_ids == ("ev:assumed",)
    assert bundle.calculations[0].steps[1].output == Quantity(value=3.0, unit="m")


@pytest.mark.parametrize(
    "scheme,value",
    [("view_id", "view-1"), ("claim", "claim_1"), ("record_inference", "inference_1")],
)
def test_existing_evidence_id_patterns_are_reused_exactly(scheme, value):
    with pytest.raises(ValidationError, match="existing"):
        ExistingEvidenceRef(scheme=scheme, value=value)


def test_cross_run_reference_requires_hash_and_coordinate_relation():
    data = make_view_ref().model_dump()
    data.pop("original_sha256")
    with pytest.raises(ValidationError):
        RunQualifiedEvidenceRef.model_validate(data)
    with pytest.raises(ValidationError, match="both its original crop and affine"):
        CoordinateRelation(
            referenced_space="view_pixels",
            relation="crop_and_affine",
            crop_original_pixels=(0.0, 0.0, 10.0, 10.0),
        )


def test_calculation_rejects_bad_conversion_discontinuity_and_changed_saved_value():
    valid = make_reconstruction_bundle().calculations[0]
    raw, converted, normalized, saved = valid.steps
    bad_converted_value = Quantity(value=600.0, unit="m")
    bad_converted = converted.model_copy(update={"output": bad_converted_value})
    continuous_normalized = normalized.model_copy(update={"input": bad_converted_value})
    with pytest.raises(ValidationError, match="raw-to-converted"):
        CalculationChain.model_validate(
            {**valid.model_dump(), "steps": (raw, bad_converted, continuous_normalized, saved)}
        )
    with pytest.raises(ValidationError, match="previous output"):
        CalculationChain.model_validate(
            {**valid.model_dump(), "steps": (raw, converted, normalized.model_copy(update={"input": Quantity(value=6.1, unit="m")}), saved)}
        )
    changed = CalculationStep(
        stage="saved", input=normalized.output, output=Quantity(value=5.9, unit="m"), reason="silent drift"
    )
    with pytest.raises(ValidationError, match="saved value"):
        CalculationChain.model_validate({**valid.model_dump(), "steps": (raw, converted, normalized, changed)})


def test_pixel_calculation_requires_explicit_scale():
    valid = make_reconstruction_bundle().calculations[0]
    steps = list(valid.steps)
    raw = Quantity(value=100.0, unit="px")
    metre = Quantity(value=2.0, unit="m")
    steps[0] = steps[0].model_copy(update={"output": raw})
    steps[1] = steps[1].model_copy(update={"input": raw, "output": metre})
    steps[2] = steps[2].model_copy(update={"input": metre, "output": metre})
    steps[3] = steps[3].model_copy(update={"input": metre, "output": metre})
    data = {**valid.model_dump(), "steps": tuple(steps), "pixel_scale_m_per_px": None}
    with pytest.raises(ValidationError, match="explicit pixel_scale"):
        CalculationChain.model_validate(data)
    assert CalculationChain.model_validate({**data, "pixel_scale_m_per_px": 0.02}).steps[1].output.value == 2.0


def test_observation_and_inference_require_existing_located_sources():
    with pytest.raises(ValidationError, match="observations require"):
        EvidenceItem(evidence_id="ev:o", kind="observation", statement="seen")
    with pytest.raises(ValidationError, match="record_inference"):
        EvidenceItem(
            evidence_id="ev:i", kind="inference", statement="interpreted", source_refs=(make_view_ref(),)
        )


def test_conflict_keeps_both_sides_and_resolution_state_honest():
    with pytest.raises(ValidationError, match="different sides"):
        EvidenceConflict(
            conflict_id="conflict:x", evidence_ids=("ev:a", "ev:a"), status="unresolved"
        )
    with pytest.raises(ValidationError, match="cannot pretend"):
        EvidenceConflict(
            conflict_id="conflict:x",
            evidence_ids=("ev:a", "ev:b"),
            status="unresolved",
            resolution="silently chose one",
        )


def test_declaration_wraps_only_existing_tools_and_separates_field_ownership():
    with pytest.raises(ValidationError, match="payload must contain exactly"):
        ExistingToolCall(tool="revise_bim", payload={"candidate": "c"})
    with pytest.raises(ValidationError, match="overlaps"):
        FieldPartition(model_declared=("/a",), code_expanded=("/a",))
    with pytest.raises(ValidationError):
        InferenceHypothesis(
            hypothesis_id="hyp:x",
            kind="design_choice",
            statement="choice",
            requirement_ids=("req:x",),
            evidence_ids=("ev:x",),
            hypothesis=False,
        )


def test_localized_results_separate_seen_interpreted_uncertain_and_refuse_stale_apply():
    bundle = make_reconstruction_bundle()
    package, result = bundle.evidence_packages[0], bundle.evidence_results[0]
    assert result.directly_seen and result.interpretations and result.uncertain
    assert_result_applicable(package, result, "model:v1")
    with pytest.raises(ValueError, match="stale"):
        assert_result_applicable(package, result, "model:v2")
    bad = result.model_copy(
        update={
            "interpretations": (
                LocalInterpretation(
                    interpretation_id="interpretation:bad",
                    statement="unsupported",
                    based_on_observation_ids=("seen:missing",),
                    confidence="low",
                ),
            )
        }
    )
    with pytest.raises(ValidationError, match="unseen"):
        LocalizedEvidenceResult.model_validate(bad.model_dump())


def test_localized_result_cannot_cite_an_image_absent_from_its_package():
    bundle = make_reconstruction_bundle()
    result = bundle.evidence_results[0]
    foreign = make_view_ref("view_0002")
    observation = result.directly_seen[0].model_copy(
        update={
            "location": PixelLocation(
                image_ref=foreign,
                box_original_pixels=(150.0, 80.0, 160.0, 220.0),
            )
        }
    )
    foreign_result = result.model_copy(update={"directly_seen": (observation,)})
    with pytest.raises(ValueError, match="not supplied"):
        assert_result_applicable(bundle.evidence_packages[0], foreign_result, "model:v1")
    with pytest.raises(ValidationError, match="absent from its package"):
        BuildingContractBundle.model_validate(
            {**bundle.model_dump(), "evidence_results": (foreign_result,)}
        )


def test_floor_draft_is_scoped_and_cannot_enter_applied_declarations():
    bundle = make_reconstruction_bundle()
    draft = bundle.floor_drafts[0]
    bad_declaration = draft.proposed_declaration.model_copy(
        update={"scope": DeclarationScope(kind="wing", ids=("east",))}
    )
    with pytest.raises(ValidationError, match="scoped to that floor"):
        FloorDraftContract.model_validate(
            {**draft.model_dump(), "proposed_declaration": bad_declaration}
        )
    data = bundle.model_dump()
    data["declarations"] = data["declarations"] + (draft.proposed_declaration.model_dump(),)
    with pytest.raises(ValidationError, match="draft-only declaration"):
        BuildingContractBundle.model_validate(data)


def test_passed_check_requires_saved_artifact_and_inspected_objects():
    bundle = make_reconstruction_bundle()
    check = bundle.checks[0]
    with pytest.raises(ValidationError, match="artifact-bound"):
        CheckResult.model_validate({**check.model_dump(), "saved_verification": None})
    wrong = check.saved_verification.model_copy(
        update={"inspected_objects": (BuildingObjectRef(kind="space", id="elsewhere"),)}
    )
    with pytest.raises(ValidationError, match="every involved"):
        CheckResult.model_validate({**check.model_dump(), "saved_verification": wrong})


def test_normalization_uses_existing_target_and_preserves_real_narrow_space():
    proposal = make_reconstruction_bundle().normalizations[0]
    assert proposal.edits[0].after_m == proposal.edits[0].target.coordinate_m == 3.94
    assert next(row for row in proposal.features if row.feature_id == "feature:narrow").decision == "preserve"
    with pytest.raises(ValidationError, match="genuine"):
        FeatureDisposition(
            feature_id="feature:step",
            classification="genuine_step",
            decision="normalize",
            reason="bad",
        )
    target = proposal.edits[0].target
    with pytest.raises(ValidationError):
        ExistingTargetLine.model_validate({**target.model_dump(), "kind": "computed_midpoint"})


def test_normalization_target_must_exist_in_before_snapshot():
    proposal = make_reconstruction_bundle().normalizations[0]
    before = proposal.before.model_copy(update={"dimensions": proposal.before.dimensions[:1]})
    with pytest.raises(ValidationError, match="not an existing line"):
        NormalizationProposal.model_validate({**proposal.model_dump(), "before": before})


def test_normalization_change_must_not_exceed_declared_metre_tolerance():
    proposal = make_reconstruction_bundle().normalizations[0]
    exact = proposal.tolerance.model_copy(update={"value": 0.06})
    accepted = NormalizationProposal.model_validate(
        {**proposal.model_dump(), "tolerance": exact}
    )
    assert accepted.edits[0].before_m == 4.0
    assert accepted.edits[0].after_m == 3.94

    tight = proposal.tolerance.model_copy(update={"value": 0.01})
    with pytest.raises(ValidationError, match="exceeds"):
        NormalizationProposal.model_validate({**proposal.model_dump(), "tolerance": tight})

    slightly_over_after = 3.939999
    edit = proposal.edits[0]
    target = edit.target.model_copy(update={"coordinate_m": slightly_over_after})
    over_edit = edit.model_copy(update={"after_m": slightly_over_after, "target": target})
    before_dimensions = tuple(
        row.model_copy(update={"value_m": slightly_over_after})
        if row.object_ref == target.object_ref and row.field_path == target.field_path
        else row
        for row in proposal.before.dimensions
    )
    after_dimensions = tuple(
        row.model_copy(update={"value_m": slightly_over_after})
        if row.object_ref == edit.object_ref and row.field_path == edit.field_path
        else row.model_copy(update={"value_m": slightly_over_after})
        if row.object_ref == target.object_ref and row.field_path == target.field_path
        else row
        for row in proposal.after.dimensions
    )
    over_before = proposal.before.model_copy(update={"dimensions": before_dimensions})
    over_after = proposal.after.model_copy(update={"dimensions": after_dimensions})
    with pytest.raises(ValidationError, match="exceeds"):
        NormalizationProposal.model_validate(
            {
                **proposal.model_dump(),
                "tolerance": exact,
                "edits": (over_edit,),
                "before": over_before,
                "after": over_after,
            }
        )

    centimetres = proposal.tolerance.model_copy(update={"unit": "cm", "value": 12.0})
    with pytest.raises(ValidationError, match="expressed in metres"):
        NormalizationProposal.model_validate({**proposal.model_dump(), "tolerance": centimetres})


@pytest.mark.parametrize(
    "mutation",
    ["delete_wall", "merge_room", "move_opening", "change_host", "change_z", "change_connectivity"],
)
def test_normalization_snapshot_rejects_semantic_changes(mutation):
    proposal = make_reconstruction_bundle().normalizations[0]
    semantics = proposal.after.semantics.model_dump()
    if mutation == "delete_wall":
        semantics["wall_ids"] = ("wall:north",)
    elif mutation == "merge_room":
        semantics["room_ids"] = ("F1:R1",)
    elif mutation == "move_opening":
        semantics["openings"][0]["p1"] = (3.95, 1.0)
    elif mutation == "change_host":
        semantics["openings"][0]["host_ids"] = ("F1:R1",)
    elif mutation == "change_z":
        semantics["openings"][0]["z_range"] = (0.0, 2.2)
    else:
        semantics["connectivity"] = ()
    after = proposal.after.model_copy(update={"semantics": SemanticSnapshot.model_validate(semantics)})
    with pytest.raises(ValidationError, match="changed walls"):
        NormalizationProposal.model_validate({**proposal.model_dump(), "after": after})


def test_coverage_rejects_rationale_without_saved_objects_or_verification():
    entry = make_reconstruction_bundle().coverage[0]
    with pytest.raises(ValidationError):
        CoverageEntry.model_validate({**entry.model_dump(), "actual_objects": ()})
    bundle = make_reconstruction_bundle()
    failed = bundle.checks[1].model_copy(update={"status": "failed", "saved_verification": None})
    with pytest.raises(ValidationError, match="unverified or failing"):
        BuildingContractBundle.model_validate(
            {**bundle.model_dump(), "checks": (bundle.checks[0], failed)}
        )


def test_coverage_checks_must_reach_every_saved_object_and_exact_version():
    bundle = make_reconstruction_bundle()
    entry = bundle.coverage[0].model_copy(
        update={"actual_objects": (BuildingObjectRef(kind="space", id="F1:R2"),)}
    )
    with pytest.raises(ValidationError, match="did not inspect"):
        BuildingContractBundle.model_validate({**bundle.model_dump(), "coverage": (entry,)})
    check = bundle.checks[1]
    verification = check.saved_verification.model_copy(
        update={"model_version_id": "model:v1", "artifact_sha256": SHA_ARTIFACT_1}
    )
    wrong_version = check.model_copy(update={"saved_verification": verification})
    with pytest.raises(ValidationError, match="different saved model"):
        BuildingContractBundle.model_validate(
            {**bundle.model_dump(), "checks": (bundle.checks[0], wrong_version)}
        )


def test_check_artifact_hash_must_belong_to_verified_model_version():
    bundle = make_reconstruction_bundle()
    check = bundle.checks[1]
    verification = check.saved_verification.model_copy(update={"artifact_sha256": "6" * 64})
    mismatched = check.model_copy(update={"saved_verification": verification})
    with pytest.raises(ValidationError, match="artifact does not match"):
        BuildingContractBundle.model_validate(
            {**bundle.model_dump(), "checks": (bundle.checks[0], mismatched)}
        )


def test_coarse_merge_requires_explicit_user_simplification_requirement():
    assert make_partial_inference_bundle(coarse_merge=True).coverage[0].coarse_merge
    bundle = make_partial_inference_bundle(coarse_merge=False)
    bad = bundle.coverage[0].model_copy(update={"coarse_merge": True})
    with pytest.raises(ValidationError, match="explicit user simplification"):
        BuildingContractBundle.model_validate({**bundle.model_dump(), "coverage": (bad,)})


def test_incomplete_coverage_names_real_open_issue():
    bundle = make_reconstruction_bundle()
    issue = CoverageIssue(issue_id="issue:door", statement="Door height remains unverified.")
    failed_check = bundle.checks[1].model_copy(
        update={"status": "failed", "saved_verification": None}
    )
    entry = bundle.coverage[0].model_copy(
        update={"status": "incomplete", "open_issue_ids": (issue.issue_id,)}
    )
    updated = BuildingContractBundle.model_validate(
        {
            **bundle.model_dump(),
            "checks": (bundle.checks[0], failed_check),
            "coverage_issues": (issue,),
            "coverage": (entry,),
        }
    )
    assert updated.coverage[0].status == "incomplete"
    assert updated.checks[1].status == "failed"


def test_bundle_rejects_unknown_cross_reference():
    bundle = make_reconstruction_bundle()
    declaration = bundle.declarations[0].model_copy(update={"evidence_ids": ("ev:missing",)})
    with pytest.raises(ValidationError, match="unknown IDs"):
        BuildingContractBundle.model_validate(
            {**bundle.model_dump(), "declarations": (declaration,)}
        )


def test_models_reject_extra_fields_and_non_finite_numbers():
    raw = make_reconstruction_bundle().calculations[0].steps[0].output.model_dump()
    with pytest.raises(ValidationError):
        Quantity.model_validate({**raw, "value": float("nan")})
    with pytest.raises(ValidationError):
        Quantity.model_validate({**raw, "invented": True})
