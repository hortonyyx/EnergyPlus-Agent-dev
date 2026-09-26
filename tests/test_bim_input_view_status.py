"""Direct image access must not become a claim of reviewed geometry."""
import asyncio
import json

from scripts.tool_scripts.run_bim_agent import Toolkit
from tests.test_bim_agent_tools import _add_image, _json_result, _server_session
from tests.test_bim_claims import setup_run


def test_views_distinguish_crop_whole_missing_and_do_not_cover_heights(tmp_path):
    run, toolkit = setup_run(tmp_path)
    _add_image(run, "north.png")
    _add_image(run, "west.png")
    toolkit = Toolkit(run)
    toolkit.view("plan.png", [0, 0, 6, 4])
    toolkit.view("north.png", coordinate_grid=False)
    # A returned model elevation and a legacy/unbound view are not direct evidence.
    toolkit.log("view_elevation_candidate", {"name": "west.png"})
    toolkit.log("view_image", {"name": "west.png", "box_original_pixels": [0, 0, 12, 8]})
    toolkit.log("view_image", {"name": "west.png", "image_sha256": "different",
                               "box_original_pixels": [0, 0, 12, 8]})
    status = Toolkit(run).input_view_status()
    assert status["no_direct_view_images"] == ["west.png"]
    assert status["crop_only_images"] == ["plan.png"]
    assert status["delivery_blocked"] is False
    assert status["drawing_fidelity"] == "not_evaluated"
    delivery = toolkit.delivery("seed", selection_origin="agent_selected")
    assert delivery["input_view_status"] == status
    assert delivery["height_coverage"]["summary"]["image_linked_count"] == 0
    assert "本次原图直接查看记录" in (run / "delivery.html").read_text()
    # Access survives geometry revisions without asserting any height review.
    proposal = json.loads((run / "seed/proposal.json").read_text())
    built = toolkit.build(proposal)
    assert built["input_view_status"] == status


def test_input_and_height_tools_return_current_access_status(tmp_path):
    async def scenario():
        run, _ = setup_run(tmp_path)
        async with _server_session(run, readonly=False) as session:
            before = _json_result(await session.call_tool("inputs", {}))
            assert before["input_view_status"]["no_direct_view_images"] == ["plan.png"]
            await session.call_tool("view_image", {"name": "plan.png"})
            result = _json_result(await session.call_tool("check_openings", {
                "candidate": "seed", "heights_only": True}))
            assert result["input_view_status"]["no_direct_view_images"] == []
            assert result["height_coverage"]["summary"]["image_linked_count"] == 0
            finished = _json_result(await session.call_tool("finish_bim", {"candidate": "seed"}))
            assert finished["input_view_status"] == result["input_view_status"]
    asyncio.run(scenario())
