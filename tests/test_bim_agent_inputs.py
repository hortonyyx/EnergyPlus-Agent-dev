"""Offline coverage for explicit building declarations in the BIM-agent CLI."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from PIL import Image

from scripts.tool_scripts import run_bim_agent as runner
from src.agent.execution.source_proposal import export_source_proposal


def _images(folder: Path) -> Path:
    folder.mkdir()
    Image.new("RGB", (12, 8), "white").save(folder / "plan.png")
    Image.new("RGB", (10, 6), "gray").save(folder / "east.png")
    return folder


def _completed_receipt(run: Path) -> dict:
    receipt = {"elapsed_seconds": 0, "result": {"is_error": False, "total_cost_usd": 0}}
    runner.dump(run / "agent_receipt.json", receipt)
    return receipt


def _proposal() -> dict:
    return {
        "geometry": {
            "schema_version": "2",
            "footprint_x": [0, 6],
            "footprint_y": [0, 4],
            "floors": [{
                "name": "F1", "z_floor": 0, "ceiling_height": 3,
                "cells": [{"id": "office", "role": "office", "x": [0, 6], "y": [0, 4]}],
            }],
            "windows": [],
            "openings": [],
        },
        "assumptions": ["test fixture"],
        "unresolved": [],
    }


def test_cli_freezes_exact_json_and_exposes_structured_declaration(tmp_path, monkeypatch):
    images = _images(tmp_path / "images")
    building_path = tmp_path / "formal declaration.json"
    raw = (b'{\n  "TestName": "utf8-\\u5efa\\u7b51",\n'
           b'  "Number of floors": 1,\n'
           b'  "Floor plans": [{"floor": 1, "path": "case/plan.png", "thermal_zones": 8}],\n'
           b'  "East view path of the building": "elsewhere/east.png",\n'
           b'  "Unprovided view path": "private/never-read.png"\n}\n')
    building_path.write_bytes(raw)
    captured = {}

    def offline_subscription(run, prompt, **kwargs):
        captured["prompt"] = prompt
        captured["inputs"] = runner.Toolkit(run).manifest
        return _completed_receipt(run)

    monkeypatch.setattr(runner, "subscription", offline_subscription)
    out = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", [
        str(Path(runner.__file__)), "run", "--images", str(images),
        "--building-input", str(building_path), "--out", str(out), "--timeout", "30",
    ])
    runner.main()

    manifest = captured["inputs"]
    declared = json.loads(raw)
    assert (out / "building_input.json").read_bytes() == raw
    assert manifest["building_input"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert manifest["building_input"]["declaration"] == declared
    assert manifest["source_input_mode"] == "original_images_with_building_declaration"
    assert manifest["input_contents"] == {
        "original_png_images": {"included": True, "count": 2},
        "building_declaration": {"included": True},
        "saved_generated_proposal": {"included": False},
        "ground_truth_or_evaluation": {"included": False},
    }
    associations = {row["json_pointer"]: row for row in
                    manifest["building_input"]["image_path_associations"]}
    assert associations["/Floor plans/0/path"]["authorized_image"] == "plan.png"
    assert associations["/East view path of the building"]["authorized_image"] == "east.png"
    assert associations["/Unprovided view path"]["status"] == "not_in_authorized_image_inventory"
    assert associations["/Unprovided view path"]["authorized_image"] is None
    assert "thermal_zones describes downstream simulation zoning" in captured["prompt"]
    assert manifest["building_input"]["source_path"] == str(building_path.resolve())
    assert "scripts/tool_scripts/bim_agent_inputs.py" in manifest["implementation_sha256"]

    summary = json.loads((out / "summary.json").read_text())
    assert summary["building_input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert summary["source_input_mode"] == "original_images_with_building_declaration"


def test_omitted_building_input_stays_png_only_and_does_not_read_neighbor_json(tmp_path, monkeypatch):
    images = _images(tmp_path / "images")
    sentinel = "MUST_NOT_ENTER_PNG_ONLY_RUN"
    (images / "testdata_prompt.json").write_text(json.dumps({"secret": sentinel}))
    captured = {}

    def offline_subscription(run, prompt, **kwargs):
        captured["prompt"] = prompt
        captured["manifest"] = runner.Toolkit(run).manifest
        return _completed_receipt(run)

    monkeypatch.setattr(runner, "subscription", offline_subscription)
    args = SimpleNamespace(images=images, out=tmp_path / "run", scope="PNG-only probe",
                           timeout=30, effort="low", resume_candidate=None,
                           building_input=None)
    runner.run_experiment(args)

    manifest = captured["manifest"]
    assert manifest["source_input_mode"] == "original_images_only"
    assert manifest["input_contents"]["building_declaration"] == {"included": False}
    assert "building_input" not in manifest
    assert "No structured building declaration was supplied" in captured["prompt"]
    assert not (args.out / "building_input.json").exists()
    assert set(path.name for path in (args.out / "images").iterdir()) == {"plan.png", "east.png"}
    assert sentinel not in (args.out / "inputs.json").read_text()


def test_building_declaration_and_saved_candidate_recovery_are_independent_modes(tmp_path, monkeypatch):
    images = _images(tmp_path / "images")
    building_path = tmp_path / "building.json"
    building_path.write_text(json.dumps({
        "Building type": "Office",
        "Floor plans": [{"path": "plan.png", "thermal_zones": 3}],
    }))
    seed = tmp_path / "candidate"
    export_source_proposal(_proposal(), seed)

    def offline_subscription(run, prompt, **kwargs):
        manifest = runner.Toolkit(run).manifest
        assert manifest["input_mode"] == "saved_candidate_recovery"
        assert manifest["source_input_mode"] == "original_images_with_building_declaration"
        assert manifest["input_contents"]["saved_generated_proposal"] == {"included": True}
        assert manifest["building_input"]["declaration"]["Building type"] == "Office"
        assert (run / "seed/source_model.json").exists()
        return _completed_receipt(run)

    monkeypatch.setattr(runner, "subscription", offline_subscription)
    args = SimpleNamespace(
        images=images, building_input=building_path, out=tmp_path / "recovery",
        scope="resume with declarations", timeout=30, effort="medium", resume_candidate=seed,
    )
    runner.run_experiment(args)

    summary = json.loads((args.out / "summary.json").read_text())
    assert summary["input_mode"] == "saved_candidate_recovery"
    assert summary["source_input_mode"] == "original_images_with_building_declaration"
    assert summary["delivery"]["candidate"] == "seed"


def test_opus_is_explicit_experimental_choice_and_not_a_fallback(tmp_path, monkeypatch):
    images=_images(tmp_path/'images')
    captured={}
    def offline_subscription(run,prompt,**kwargs):
        captured.update(kwargs)
        return _completed_receipt(run)
    monkeypatch.setattr(runner,'subscription',offline_subscription)
    args=SimpleNamespace(images=images,out=tmp_path/'run',scope='migration test',
        timeout=30,effort='medium',resume_candidate=None,building_input=None,exploratory_opus=True)
    runner.run_experiment(args)
    assert captured['model']=='opus' and captured['exploratory_opus'] is True
    assert runner.Toolkit(args.out).manifest['exploratory_opus'] is True
