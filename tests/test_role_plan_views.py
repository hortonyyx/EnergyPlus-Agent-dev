from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json

import pytest
from PIL import Image

from src.agent.runtime_roles.plan_views import (
    DISPLAY_SCALE,
    MAX_RETURNED_SIDE,
    PLAN_VIEWS_TOOL,
    _bounded_scale,
    plan_block_boxes,
    view_plan_blocks,
)
from src.agent.runtime_tools import FrozenBimTools, local_observer_role
from src.harness_contracts import BudgetAmounts


def _assert_complete_cores(boxes, width, height):
    area = 0
    for row in boxes:
        left, top, right, bottom = row["core_bbox_original_pixels"]
        assert 0 <= left < right <= width
        assert 0 <= top < bottom <= height
        area += (right - left) * (bottom - top)
    assert area == width * height
    for index, first in enumerate(boxes):
        a = first["core_bbox_original_pixels"]
        for second in boxes[index + 1:]:
            b = second["core_bbox_original_pixels"]
            assert min(a[2], b[2]) <= max(a[0], b[0]) or min(a[3], b[3]) <= max(a[1], b[1])


@pytest.mark.parametrize(
    ("size", "count", "grid"),
    [
        ((900, 700), 4, (2, 2)),
        ((1450, 800), 6, (3, 2)),
        ((2200, 800), 8, (4, 2)),
        ((800, 2200), 8, (2, 4)),
    ],
)
def test_layout_chooses_four_six_or_eight_blocks_and_covers_the_original(size, count, grid):
    boxes = plan_block_boxes(*size)

    assert len(boxes) == count
    assert (boxes[0]["grid"]["columns"], boxes[0]["grid"]["rows"]) == grid
    _assert_complete_cores(boxes, *size)
    if grid[0] > 1:
        assert boxes[0]["bbox_original_pixels"][2] > boxes[1]["bbox_original_pixels"][0]


def test_extreme_strip_and_tiny_image_boundaries_are_explicit():
    horizontal = plan_block_boxes(2000, 1)
    assert len(horizontal) == 4
    assert (horizontal[0]["grid"]["columns"], horizontal[0]["grid"]["rows"]) == (4, 1)
    _assert_complete_cores(horizontal, 2000, 1)

    with pytest.raises(ValueError, match="at least four pixels"):
        plan_block_boxes(1, 3)


class Frozen:
    def __init__(self, run_directory):
        self.run_directory = run_directory


def _run(tmp_path, size=(900, 700)):
    images = tmp_path / "images"
    images.mkdir()
    path = images / "plan.png"
    Image.new("RGB", size, "white").save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "inputs.json").write_text(
        json.dumps({"images": {"plan.png": {"sha256": digest, "size": list(size)}}}),
        encoding="utf-8",
    )
    return path


def test_batch_renders_signed_views_and_preserves_all_image_provenance(tmp_path):
    async def scenario():
        from scripts.tool_scripts.run_bim_agent import Toolkit

        source = _run(tmp_path)
        records = tmp_path / "image_views"
        records.mkdir()
        sentinel = records / "view_0001.json"
        sentinel.write_text('{"existing":true}\n', encoding="utf-8")
        frozen = Frozen(tmp_path)

        result = await view_plan_blocks(frozen, "plan.png")

        assert not result["isError"]
        payload = result["structuredContent"]
        assert payload["status"] == "completed"
        assert payload["block_count"] == 4
        assert payload["coverage"] == {
            "bbox_original_pixels": [0, 0, 900, 700], "complete": True
        }
        assert [row["view_id"] for row in payload["evidence_previews"]] == [
            "view_0002", "view_0003", "view_0004", "view_0005"
        ]
        assert [row["view_id"] for row in payload["views"]] == [
            "view_0002", "view_0003", "view_0004", "view_0005"
        ]
        assert all(row["display_scale_actual"] == [3.0, 3.0] for row in payload["views"])
        assert [block["type"] for block in result["content"]] == [
            "image", "image", "image", "image", "text"
        ]
        assert sentinel.read_text(encoding="utf-8") == '{"existing":true}\n'

        for block, preview in zip(result["content"][:-1], payload["evidence_previews"], strict=True):
            returned = base64.b64decode(block["data"], validate=True)
            assert hashlib.sha256(returned).hexdigest() == preview["returned_png_sha256"]
            with Image.open(io.BytesIO(returned)) as picture:
                assert list(picture.size) == preview["returned_size"]
            left, top, right, bottom = preview["box_original_pixels"]
            assert preview["returned_size"] == [3 * (right - left), 3 * (bottom - top)]
            assert preview["coordinate_grid"]["shown"] is True
            record_path = records / f'{preview["view_id"]}.json'
            record = json.loads(record_path.read_text(encoding="utf-8"))
            assert record["returned_png_sha256"] == preview["returned_png_sha256"]
            assert record["image_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
            assert hashlib.sha256(record_path.read_bytes()).hexdigest() == preview["view_record_sha256"]
            reopened = Toolkit(tmp_path).read_image_view(preview["view_id"])
            assert reopened == {"record": record, "sha256": preview["view_record_sha256"]}

        # The aggregate keeps the exact metadata key used by the runtime's
        # provenance mapper, so every image retains its own crop and view_id.
        mapper = FrozenBimTools(
            None,
            local_observer_role(BudgetAmounts(calls=10)),
            run_directory=tmp_path,
        )
        origins = mapper.image_origins(result)
        assert len(origins) == 4
        assert {row["view_id"] for row in origins.values()} == {
            "view_0002", "view_0003", "view_0004", "view_0005"
        }
        assert all(row["original_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
                   for row in origins.values())

    asyncio.run(scenario())


def test_common_large_plan_keeps_eight_blocks_at_true_three_x(tmp_path):
    async def scenario():
        _run(tmp_path, size=(2133, 1345))
        result = await view_plan_blocks(Frozen(tmp_path), "plan.png")

        views = result["structuredContent"]["views"]
        assert len(views) == 8
        assert result["structuredContent"]["grid"] == {"columns": 4, "rows": 2}
        assert all(row["display_scale_actual"] == [3.0, 3.0] for row in views)
        assert all(max(row["returned_size"]) < MAX_RETURNED_SIDE for row in views)

    asyncio.run(scenario())


def test_render_scale_cap_is_pure_and_avoids_allocating_an_extreme_bitmap():
    assert _bounded_scale((500, 400)) == DISPLAY_SCALE
    scale = _bounded_scale((2000, 500))
    assert scale == pytest.approx(MAX_RETURNED_SIDE / 2000)
    assert max(round(length * scale) for length in (2000, 500)) <= MAX_RETURNED_SIDE


def test_batch_rejects_an_admitted_image_whose_bytes_changed(tmp_path):
    source = _run(tmp_path)
    Image.new("RGB", (900, 700), "black").save(source)

    with pytest.raises(ValueError, match="image changed"):
        asyncio.run(view_plan_blocks(Frozen(tmp_path), "plan.png"))


def test_tool_contract_has_no_model_selected_image_or_box():
    assert PLAN_VIEWS_TOOL["name"] == "view_plan_blocks"
    assert PLAN_VIEWS_TOOL["inputSchema"] == {
        "type": "object", "properties": {}, "additionalProperties": False
    }
