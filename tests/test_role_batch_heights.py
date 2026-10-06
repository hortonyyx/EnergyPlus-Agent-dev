"""D1b atomic role-height batches leave ordinary claim transactions intact."""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

from scripts.tool_scripts.bim_agent_role_heights import build_role_height_batch_entry
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.runtime_roles.config import load_roles
from src.agent.runtime_roles.elevation import validate_elevation_artifact
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore
from tests.test_bim_claims import setup_run
from tests.test_source_proposal import _proposal


def _height_entry(
    identity: str,
    height: list[float],
    box: list[float],
    *,
    basis: str = "pixels",
    evidence_type: str = "pixels",
) -> tuple[dict, str]:
    reason = f"Synthetic {evidence_type} height for {identity} at {box}."
    return (
        {
            "claim": {
                "candidate": "seed",
                "objects": [{"kind": "window", "id": identity}],
                "basis": basis,
                "reason": reason,
                "sources": [{"image": "plan.png", "box": box}],
                "values": {
                    "height": {"type": "literal", "value": height, "unit": "m"}
                },
                "observation_mode": (
                    "candidate_review"
                    if evidence_type in {"assumption", "declared"}
                    else "direct"
                ),
                "unresolved": (
                    ["Explicit assumption; not a measured facade value."]
                    if evidence_type == "assumption"
                    else []
                ),
            },
            "action": "apply",
            "reason": reason,
            "operations": [
                {
                    "op": "update_window",
                    "id": identity,
                    "changes": {"z": {"claim": "$claim", "value": "height"}},
                    "reason": reason,
                }
            ],
        },
        evidence_type,
    )


def _two_window_run(tmp_path):
    proposal = _proposal()
    proposal["geometry"]["windows"].append(
        {
            **copy.deepcopy(proposal["geometry"]["windows"][0]),
            "id": "second",
            "span": [4, 5],
        }
    )
    return setup_run(tmp_path, proposal)


def _batch(*rows):
    entries, evidence_types = zip(*rows, strict=True)
    return build_role_height_batch_entry(entries, evidence_types=evidence_types)


def _persisted_trace(claim):
    prefix = "Atomic role elevation height batch: "
    assert claim["reason"].startswith(prefix)
    return json.loads(claim["reason"][len(prefix) :])["per_opening"]


def test_compound_claim_persists_one_value_object_and_bbox_per_opening(tmp_path):
    run, toolkit = _two_window_run(tmp_path)
    batch = _batch(
        _height_entry("window", [0.9, 2.1], [0, 1, 4, 7]),
        _height_entry(
            "second",
            [1.1, 2.3],
            [6, 1, 10, 7],
            basis="inference",
            evidence_type="assumption",
        ),
    )

    result = toolkit.claim_transaction("seed", batch["entries_json"])

    assert result["status"] == "completed"
    assert result["result_candidate"] == "candidate_01"
    assert len(list(run.glob("candidate_*"))) == 1
    proposal = json.loads((run / "candidate_01/proposal.json").read_bytes())
    assert {row["id"]: row["z"] for row in proposal["geometry"]["windows"]} == {
        "window": [0.9, 2.1],
        "second": [1.1, 2.3],
    }

    record = json.loads((run / "claims/claim_0001.json").read_bytes())
    claim = record["claim"]
    assert claim["basis"] == "inference"
    assert claim["observation_mode"] == "candidate_review"
    assert claim["sources"] == [
        {"image": "plan.png", "box": [0.0, 1.0, 4.0, 7.0]},
        {"image": "plan.png", "box": [6.0, 1.0, 10.0, 7.0]},
    ]
    assert claim["values"] == {
        "height_0001": {"type": "literal", "value": [0.9, 2.1], "unit": "m"},
        "height_0002": {"type": "literal", "value": [1.1, 2.3], "unit": "m"},
    }
    assert claim["value_targets"] == {
        "height_0001": [{"kind": "window", "id": "window"}],
        "height_0002": [{"kind": "window", "id": "second"}],
    }
    trace = _persisted_trace(claim)
    assert [row["source_index"] for row in trace] == [0, 1]
    assert [row["object"]["id"] for row in trace] == ["window", "second"]
    assert [row["value"] for row in trace] == ["height_0001", "height_0002"]
    assert [row["evidence_type"] for row in trace] == ["pixels", "assumption"]
    assert trace[0]["source"]["box"] != trace[1]["source"]["box"]
    assert any("window:second" in row for row in claim["unresolved"])

    application = json.loads((run / "claims/application_0001.json").read_bytes())
    assert application["status"] == "applied"
    assert [row["value_field"] for row in application["evidence"]["bindings"]] == [
        "height_0001",
        "height_0002",
    ]
    assert [row["targets"] for row in application["evidence"]["bindings"]] == [
        [["window", "window"]],
        [["window", "second"]],
    ]


def test_batch_preflight_failure_creates_no_partial_candidate(tmp_path):
    run, toolkit = _two_window_run(tmp_path)
    before = (run / "seed/proposal.json").read_bytes()
    batch = _batch(
        _height_entry("window", [0.9, 2.1], [0, 1, 4, 7]),
        _height_entry("second", [1.1, 2.3], [6, 1, 10, 7]),
    )
    # Corrupt only the later operation after constructing a valid compound claim.
    # The existing resolver must reject the whole single entry before any save.
    batch["entry"]["operations"][1]["id"] = "missing"
    entries_json = json.dumps([batch["entry"]], ensure_ascii=False, separators=(",", ":"))

    result = toolkit.claim_transaction("seed", entries_json)

    assert result["status"] == "failed"
    assert result["result_candidate"] == "seed"
    assert result["entries"][0]["status"] == "failed"
    assert "targets" in result["entries"][0]["error"]
    assert not list(run.glob("candidate_*"))
    assert (run / "seed/proposal.json").read_bytes() == before
    # claim_transaction resolves the complete single entry before calling
    # Toolkit.revise, so a preflight failure creates no application or draft.
    assert not list((run / "claims").glob("application_*.json"))


def test_batch_runtime_failure_after_first_in_memory_edit_creates_no_candidate(tmp_path):
    run, toolkit = _two_window_run(tmp_path)
    before = (run / "seed/proposal.json").read_bytes()
    batch = _batch(
        _height_entry("window", [0.9, 2.1], [0, 1, 4, 7]),
        _height_entry("second", [1.1, 2.3], [6, 1, 10, 7]),
    )
    # Both bindings resolve. The first edit is made only to Toolkit.revise's
    # in-memory copy; an invalid later edit must prevent the sole candidate save.
    batch["entry"]["operations"][1]["unexpected"] = True
    entries_json = json.dumps([batch["entry"]], ensure_ascii=False, separators=(",", ":"))

    result = toolkit.claim_transaction("seed", entries_json)

    assert result["status"] == "failed"
    assert result["result_candidate"] == "seed"
    assert result["entries"][0]["status"] == "failed"
    assert "unexpected" in result["entries"][0]["error"]
    assert not list(run.glob("candidate_*"))
    assert (run / "seed/proposal.json").read_bytes() == before
    applications = list((run / "claims").glob("application_*.json"))
    assert len(applications) == 1
    application = json.loads(applications[0].read_bytes())
    assert application["status"] == "failed"
    assert application.get("candidate") is None


def test_observational_mix_uses_weaker_carrier_and_keeps_exact_per_object_types():
    batch = _batch(
        _height_entry(
            "window",
            [0.9, 2.1],
            [0, 1, 4, 7],
            basis="annotation_and_pixels",
            evidence_type="annotation_and_pixels",
        ),
        _height_entry(
            "second",
            [1.1, 2.3],
            [6, 1, 10, 7],
            basis="visual_estimate",
            evidence_type="visual_estimate",
        ),
    )

    claim = batch["entry"]["claim"]
    assert claim["basis"] == "visual_estimate"
    assert claim["observation_mode"] == "direct"
    trace = _persisted_trace(claim)
    assert [(row["object"]["id"], row["basis"], row["evidence_type"]) for row in trace] == [
        ("window", "annotation_and_pixels", "annotation_and_pixels"),
        ("second", "visual_estimate", "visual_estimate"),
    ]


def test_ordinary_multi_entry_claim_transaction_still_commits_independently(tmp_path):
    run, toolkit = _two_window_run(tmp_path)
    first, _ = _height_entry("window", [0.9, 2.1], [0, 1, 4, 7])
    second, _ = _height_entry("second", [1.1, 2.3], [6, 1, 10, 7])

    result = toolkit.claim_transaction(
        "seed", json.dumps([first, second], ensure_ascii=False, separators=(",", ":"))
    )

    assert result["status"] == "completed"
    assert [row["status"] for row in result["entries"]] == ["applied", "applied"]
    assert [row["result_candidate"] for row in result["entries"]] == [
        "candidate_01",
        "candidate_02",
    ]
    assert len(list(run.glob("candidate_*"))) == 2


def test_role_session_reuses_completed_batch_without_a_second_write(tmp_path):
    run, _ = setup_run(tmp_path)
    assert export_source_proposal(_proposal(), run / "candidate_01")[
        "source_geometry_ready"
    ]
    artifact = validate_elevation_artifact(
        {
            "image": "plan.png",
            "orientation": "West",
            "view_direction": "East",
            "x_calibration": {
                "pixel_start": 0,
                "pixel_end": 12,
                "world_start_m": 6,
                "world_end_m": 0,
            },
            "elevations": [
                {
                    "id": "ground",
                    "kind": "ground",
                    "value_m": 0,
                    "evidence_type": "pixels",
                    "bbox": [0, 0, 2, 2],
                }
            ],
            "openings": [
                {
                    "id": "observed-window",
                    "floor_id": "F1",
                    "kind": "window",
                    "x_px": [8, 10],
                    "width_m": 1,
                    "sill_m": 0.9,
                    "head_m": 2.1,
                    "evidence_type": "pixels",
                    "bbox": [8, 1, 10, 7],
                }
            ],
            "counts": [{"floor_id": "F1", "window_count": 1, "door_count": 0}],
            "unresolved": [],
        }
    )
    limits = RunLimits(model_calls=1, tool_calls=4, seconds=30, tokens=10_000)
    routes = load_roles(
        {
            role: {
                "provider": "scripted",
                "model": "scripted-model",
                "reasoning_effort": "medium",
                "output_tokens": 1000,
            }
            for role in ("coordinator", "plan_reader", "elevation_reader")
        },
        allow_scripted=True,
    )

    class Frozen:
        def __init__(self):
            self.run_directory = run
            self.calls = []

        async def call_tool(self, name, arguments):
            self.calls.append((name, copy.deepcopy(arguments)))
            return envelope({"status": "completed", "result_candidate": "candidate_02"})

    frozen = Frozen()
    with EventStore(
        tmp_path / "journal",
        run_id="batch-height",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as store:
        session = RoleSession(
            store=store,
            frozen=frozen,
            routes=routes,
            adapter_factory=lambda *args: None,
            limits=limits,
            root=Path(__file__).resolve().parents[1],
        )
        task = session._task(
            {
                "task_id": "west-elevation",
                "role_id": "elevation_reader",
                "image": "plan.png",
                "target": "West",
                "instructions": "Synthetic facade artifact for atomic batch recovery.",
            }
        )
        session.registry.save(task, status="completed", artifact=artifact)
        match = session.match("west-elevation", "candidate_01")

        first = asyncio.run(session.apply_heights(match["match_id"]))
        second = asyncio.run(session.apply_heights(match["match_id"]))

    assert first == second
    assert len(frozen.calls) == 1
    assert frozen.calls[0][0] == "claim_transaction"
    sent = json.loads(frozen.calls[0][1]["entries_json"])
    assert len(sent) == 1 and len(sent[0]["operations"]) == 1
    assert sent[0]["claim"]["value_targets"] == {
        "height_0001": [{"kind": "window", "id": "window"}]
    }
