"""Direct geometry proposals stay inspectable without claiming a correction run."""
from __future__ import annotations

import hashlib
import json

import pytest

from src.agent.execution.source_proposal import export_source_proposal


def _proposal():
    return {
        "geometry": {
            "schema_version": "2", "footprint_x": [0, 6], "footprint_y": [0, 6],
            "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
                {"id": "hall", "x": [0, 3], "y": [0, 6]},
                {"id": "room", "x": [3, 6], "y": [0, 6]},
            ]}],
            "windows": [{"id": "window", "floor": "F1", "facade": "West", "span": [1, 2],
                         "z": [1, 2], "room": "hall"}],
            "openings": [{"id": "door", "kind": "door", "space_id": "hall", "other_space_id": "room",
                          "p1": [3, 1], "p2": [3, 2], "z": [0, 2.1], "source_refs": ["proposal:door"]}],
        },
        "assumptions": ["<墙体位置由平面推断>"],
        "unresolved": ["<b>未确认门状态</b>"],
    }


def test_direct_proposal_exports_independent_source_bim_with_openings(tmp_path):
    proposal = _proposal()
    out = tmp_path / "candidate"
    report = export_source_proposal(proposal, out, provenance={"input": "agent"})

    assert report["mode"] == "agent_geometry_proposal"
    assert report["source_geometry_ready"]
    assert report["source_geometry_self_consistency"]["status"] == "pass"
    assert report["drawing_fidelity"] == "not_evaluated"
    assert report["human_confirmation"] == "not_evaluated"
    assert report["counts"]["openings"] == 2
    assert report["provenance"] == {"input": "agent"}
    assert report["proposal_sha256"] == hashlib.sha256((out / "proposal.json").read_bytes()).hexdigest()
    assert report["source_model_sha256"] == json.loads((out / "source_model.json").read_text())["source_model_sha256"]
    source = json.loads((out / "source_model.json").read_text())
    assert proposal["assumptions"][0] in source["assumptions"]
    assert source["generation"]["unresolved"] == proposal["unresolved"]
    assert json.loads((out / "proposal.json").read_text()) == proposal
    assert (out / "display_geometry.json").exists()
    viewer = (out / "viewer.html").read_text(encoding="utf-8")
    assert "&lt;墙体位置由平面推断&gt;" in viewer
    assert "&lt;b&gt;未确认门状态&lt;/b&gt;" in viewer
    assert "<b>未确认门状态</b>" not in viewer


def test_invalid_opening_still_exports_candidate_with_severe_finding(tmp_path):
    proposal = _proposal()
    proposal["geometry"]["openings"][0]["other_space_id"] = "missing"
    out = tmp_path / "severe"
    report = export_source_proposal(proposal, out)

    assert report["status"] == "severe"
    assert not report["source_geometry_ready"]
    assert report["counts"]["spaces"] == 2
    assert report["counts"]["unbuilt_openings"] == 1
    source = json.loads((out / "source_model.json").read_text())
    assert source["unbuilt_openings"][0]["id"] == "door"
    assert (out / "viewer.html").exists()


def test_proposal_output_never_overwrites_or_invents_a_run_record(tmp_path):
    out = tmp_path / "candidate"
    export_source_proposal(_proposal(), out)
    before = (out / "report.json").read_bytes()
    with pytest.raises(FileExistsError):
        export_source_proposal(_proposal(), out)
    assert (out / "report.json").read_bytes() == before
    assert not (out / "_run" / "geometry_approval.json").exists()
    assert "accepted" not in json.loads(before)

    failed = tmp_path / "failed"
    report = export_source_proposal({"geometry": {}, "assumptions": [], "unresolved": [], "windows": []}, failed)
    assert report["status"] == "error"
    assert "unknown windows" in report["error"]
    assert json.loads((failed / "report.json").read_text())["status"] == "error"
