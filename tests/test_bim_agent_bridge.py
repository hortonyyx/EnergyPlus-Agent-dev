"""Real offline common-tool calls through the development client."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.tool_scripts.bim_agent_bridge import invoke
from scripts.tool_scripts import run_bim_agent as runner
from test_bim_agent_tools import _run_with_one_image


def test_bridge_preserves_images_records_calls_and_excludes_model_delegation(tmp_path):
    run = _run_with_one_image(tmp_path)
    catalog = asyncio.run(invoke(run))
    assert "review_detail" not in {row["name"] for row in catalog["tools"]}
    result = asyncio.run(invoke(run, [{"tool": "view_image", "arguments": {
        "name": "plan.png", "coordinate_grid": False}}]))
    assert result["completed"]
    images = [row for row in result["replies"][0]["content"] if row["type"] == "image"]
    from PIL import Image
    with Image.open(images[0]["path"]) as image:
        assert image.size == (12, 8)
    assert json.loads((Path(result['record']) / 'requests.json').read_text())[0]['tool'] == 'view_image'
    with pytest.raises(ValueError, match="admitted"):
        asyncio.run(invoke(run, [{"tool": "review_detail", "arguments": {}}]))


def test_preparation_never_invokes_model_and_deadline_starts_with_controller(tmp_path, monkeypatch):
    seed = _run_with_one_image(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("preparation must not call a model")
    monkeypatch.setattr(runner, "subscription", forbidden)
    args = SimpleNamespace(out=tmp_path / "prepared", images=seed / "images", mesh=None,
        scope="synthetic", timeout=3600, prepare_only=True)
    result = runner.run_experiment(args)
    manifest = json.loads((args.out / 'inputs.json').read_text())
    assert result['model_calls'] == 0
    assert manifest['deadline_epoch'] is None
    assert (args.out / 'guide.txt').exists() and (args.out / 'task.txt').exists()
    assert not (args.out / 'agent_receipt.json').exists()
