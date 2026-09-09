"""The actual displayed Stage 2 source version controls confirmation/resume."""
import json
from pathlib import Path
import shutil

import pytest

from scripts.tool_scripts.diagnose_source_checkpoint import CASE, stage_source
from scripts.tool_scripts.run_stage import _auto_start_stage, _draw_split_pairing, _source_review_digest
from src.agent.execution.approval import GeometryApproval
from src.agent.execution.manifest import load_run_manifest
from src.agent.execution.policy import ConfirmationPolicy, RunPolicy
from src.agent.execution.source_checkpoint import current_source_review, inspect_source_checkpoint
from src.agent.execution.stage_runner import StageRunner
from src.agent.execution.step_orchestrator import approve_geometry, geometry_is_approved, run_one_stage, StepStatus


@pytest.fixture(scope="module")
def staged(tmp_path_factory):
    run = tmp_path_factory.mktemp("source_stage") / "run"
    stage_source(run)
    return run


@pytest.fixture
def run(staged, tmp_path):
    target = tmp_path / "run"
    shutil.copytree(staged, target)
    return target


def _approve(run):
    digest = _source_review_digest(run)
    approval = approve_geometry(run, actor="test:auto", policy="auto", timestamp="", expected_digest=digest)
    assert approval is not None
    return approval


def test_stage2_confirmation_then_resume_without_redrawing_source(run):
    assert not (run / "3_split_pairing").exists()
    assert approve_geometry(run, actor="test", timestamp="") is None
    assert approve_geometry(run, actor="test", timestamp="", expected_digest="0" * 64) is None
    approval = _approve(run)
    assert approval.checkpoint_schema == "source_geometry_checkpoint_v1"
    assert geometry_is_approved(run)
    from src.agent.execution.validation_run import validate_case
    audit = validate_case(run, policy=RunPolicy())
    assert audit.geometry_digest == approval.digest and audit.geometry_approved
    assert not audit.reports["3_split_pairing"].passed  # Downstream is still absent.
    manifest = load_run_manifest(run)
    old = {s: manifest.accepted(s).model_dump() for s in ("0_reading", "1_correction", "2_modelling")}
    policy = RunPolicy(confirmation_policy=ConfirmationPolicy.REQUIRED)
    assert _auto_start_stage(manifest=manifest, run_dir=run, case_dir=CASE, policy=policy,
                             review_switches=set(), to_stage="3_split_pairing") == "3_split_pairing"
    outcome = run_one_stage(stage="3_split_pairing", runner=StageRunner(run, manifest), stage_dir=run / "3_split_pairing",
                            policy=policy, draw_fn=lambda _: _draw_split_pairing(run, policy),
                            geometry_approved=lambda: geometry_is_approved(run))
    manifest.save(run)
    assert outcome.status == StepStatus.DETERMINISTIC_PASS
    assert old == {s: manifest.accepted(s).model_dump() for s in old}
    # A downstream serializer changing its files cannot retrospectively alter
    # the source the user approved; its own consistency gate still applies.
    (run / "3_split_pairing/geometry_specs.md").write_text("downstream changed")
    assert geometry_is_approved(run)


@pytest.mark.parametrize("stage", ["3_split_pairing", "4_mep", "5_intakeoutput"])
def test_all_direct_downstream_entries_refuse_before_confirmation(run, stage):
    def forbidden(_):
        pytest.fail("downstream executed without source confirmation")
    outcome = run_one_stage(stage=stage, runner=StageRunner(run, load_run_manifest(run)), stage_dir=run / stage,
                            policy=RunPolicy(confirmation_policy=ConfirmationPolicy.REQUIRED), draw_fn=forbidden)
    assert outcome.status == StepStatus.AWAITING_GEOMETRY_APPROVAL
    assert not (run / stage).exists()


@pytest.mark.parametrize("artifact", ["correction", "geometry", "source", "checks", "viewer", "snapshot", "manifest"])
def test_changed_source_checks_or_display_invalidates_confirmation(run, artifact):
    approval = _approve(run)
    pointer = json.loads((run / "_run/source_geometry_review.json").read_bytes())
    paths = {
        "correction": run / "1_correction/attempts/001/output.json",
        "geometry": run / "2_modelling/attempts/001/output.json",
        "source": run / "2_modelling/source_model.json",
        "checks": run / "2_modelling/attempts/001/checks.json",
        "viewer": run / pointer["viewer"],
        "snapshot": (run / pointer["viewer"]).with_name("source_model.json"),
        "manifest": run / "_run/run_manifest.json",
    }
    path = paths[artifact]
    if artifact == "source":
        data = json.loads(path.read_bytes())
        data["spaces"][0]["role"] = "changed role"
        from src.agent.geometry.source_model import _digest
        data["source_model_sha256"] = _digest({k: v for k, v in data.items() if k != "source_model_sha256"})
        path.write_text(json.dumps(data))
    elif artifact == "manifest":
        data = json.loads(path.read_bytes())
        data["stages"].pop("2_modelling")
        path.write_text(json.dumps(data))
    else:
        path.write_bytes(path.read_bytes() + b" ")
    assert not geometry_is_approved(run)
    assert approve_geometry(run, actor="test", timestamp="", expected_digest=approval.digest) is None


def test_legacy_digest_does_not_authorize_source_checkpoint(run):
    # Even an equal digest is insufficient without the new schema and displayed
    # artifact binding. This is stronger than relying on different hash recipes.
    GeometryApproval(digest=_source_review_digest(run), actor="legacy").save(run)
    assert not geometry_is_approved(run)


def test_missing_snapshot_artifacts_cannot_be_removed_from_pointer_to_bypass_verification(run):
    pointer_path = run / "_run/source_geometry_review.json"
    pointer = json.loads(pointer_path.read_bytes())
    pointer["artifacts"] = {}
    pointer_path.write_text(json.dumps(pointer))
    assert current_source_review(run, policy=RunPolicy()) is None


def test_current_source_checks_consume_requested_tier(run):
    state = inspect_source_checkpoint(run, policy=RunPolicy(run_profile="regression", capability_profile="orthogonal_polygon"))
    assert state["basis"]["run_profile"] == "regression"
    for stage in ("1_correction:current", "2_modelling:current"):
        report = state["basis"]["checks"][stage]
        assert report["run_profile"] == "regression" and report["capability_profile"] == "orthogonal_polygon"
    assert state["digest"] != _source_review_digest(run)


def test_unaccepted_model_can_be_viewed_without_becoming_approvable(tmp_path):
    from scripts.tool_scripts.diagnose_source_checkpoint import SM25
    from scripts.tool_scripts.run_stage import _render_geometry_viewer
    from src.agent.execution.run_policy_freeze import provision_run_policy
    run = tmp_path / "preview"
    for relative in ("_run/run_manifest.json", "2_modelling/building_geometry.json", "2_modelling/source_model.json",
                     "2_modelling/kernel_gate_report.json"):
        dest = run / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SM25 / relative, dest)
    provision_run_policy(run, run_profile="exploratory", capability_profile="orthogonal_polygon")
    viewer = Path(_render_geometry_viewer(run, SM25))
    assert viewer.is_file() and "当前候选仅供查看" in viewer.read_text()
    state = inspect_source_checkpoint(run, policy=RunPolicy(capability_profile="orthogonal_polygon"))
    assert len(state["source_model"]["spaces"]) == 29 and not state["approval_ready"]
    assert len(state["source_model"]["unsupported"]) == 2
    assert approve_geometry(run, actor="test", timestamp="", expected_digest=state["digest"]) is None
    assert not (run / "_run/geometry_approval.json").exists()
