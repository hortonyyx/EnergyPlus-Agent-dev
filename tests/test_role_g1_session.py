"""Coordinator can inspect both original position readings with one call."""
import asyncio
import json

from src.agent.runtime_roles.session import envelope
from tests.test_role_d1g import height_session


def test_position_state_returns_two_real_crops_and_saved_view_ids(tmp_path):
    with height_session(tmp_path) as session:
        session.positions.current = lambda: {"items": {"difference": {
            "plan_evidence": {"image": "plan.png", "bbox": [1.2, 1.4, 5.1, 4.2]},
            "elevation_evidence": {"image": "plan.png", "bbox": [6.3, 2.1, 10.8, 6.6]},
        }}}
        async def real_view(name, args):
            assert name == "view_image"
            picture, meta = session.frozen.toolkit.view(**args)
            result = envelope(json.loads(meta))
            result["content"].append(picture.to_image_content().model_dump(mode="json"))
            return result
        session.frozen.call_tool = real_view
        result = asyncio.run(session.call_tool("role_state", {"position_decision_id": "difference"}))
        assert not result["isError"]
        meta = result["structuredContent"]
        assert len([b for b in result["content"] if b["type"] == "image"]) == 2
        assert len(set(meta["view_ids"])) == 2
        expected_boxes = [[1, 1, 6, 5], [6, 2, 11, 7]]
        for preview, view_id, box in zip(meta["evidence_previews"], meta["view_ids"], expected_boxes):
            saved = json.loads((session.run_directory / "image_views" / (view_id + ".json")).read_bytes())
            assert saved["box_original_pixels"] == box
            assert saved["returned_png_sha256"] == preview["returned_png_sha256"]
        assert [p["side"] for p in meta["evidence_previews"]] == ["plan_evidence", "elevation_evidence"]
