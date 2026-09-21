#!/usr/bin/env python3
"""Offline stdio-MCP and frozen-CV smoke checks; never invokes a model."""

from __future__ import annotations

import asyncio
import base64
from datetime import timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import ImageContent
from PIL import Image

from run_historical_pilot import (
    HERE,
    LABEL_RE,
    PROJECTED_PATHS,
    build_workspace,
    cli_cwd_for,
    command_for,
    digest_file,
    dump,
    implementation_manifest,
)


EXPECTED_TOOLS = {
    "manifest",
    "get_rule",
    "view_original",
    "cv_crop_zoom",
    "cv_wall_line_profiler",
    "cv_storey_line_profiler",
    "cv_px_m_calibrator",
    "cv_window_cc_detector",
    "cv_overlay_logger",
    "list_artifacts",
    "view_artifact",
    "submit_pilot",
}


def _structured(result: Any) -> dict[str, Any]:
    value = getattr(result, "structuredContent", None)
    if value is None:
        value = getattr(result, "structured_content", None)
    if not isinstance(value, dict):
        raise AssertionError("tool result is missing structured content")
    return value


async def verify() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="historical-sm21-offline-") as temp:
        temp_root = Path(temp)
        workspace = temp_root / "workspace"
        manifest = build_workspace(workspace)
        prepared_run = temp_root / "prepared_run"
        prepared_workspace = prepared_run / "workspace"
        build_workspace(prepared_workspace)
        (prepared_run / "invocations").mkdir()
        stable_cli_cwd = cli_cwd_for(prepared_run)
        stable_cli_cwd.mkdir(exist_ok=True)
        dump(
            prepared_run / "cli_cwd.json",
            {"path": str(stable_cli_cwd), "contains_admitted_inputs": False},
        )
        subscription_command = command_for(prepared_run, resume=False)
        assert subscription_command[subscription_command.index("--tools") + 1] == ""
        assert (
            subscription_command[subscription_command.index("--allowedTools") + 1]
            == "mcp__reading__*"
        )
        assert "--strict-mcp-config" in subscription_command
        assert "--disable-slash-commands" in subscription_command
        assert "--fallback-model" not in subscription_command
        assert "Bash" not in subscription_command
        assert not LABEL_RE.fullmatch("../escape")
        sentinel = temp_root / "outside_sentinel.txt"
        sentinel.write_text("must remain unchanged\n", encoding="utf-8")
        sentinel_hash = digest_file(sentinel)

        env = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL")
            if key in os.environ
        }
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[
                str((HERE / "reading_mcp.py").resolve()),
                "serve",
                "--workspace",
                str(workspace),
            ],
            env=env,
            cwd=str(HERE),
        )
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                listed = await session.list_tools()
                tool_names = {tool.name for tool in listed.tools}
                assert tool_names == EXPECTED_TOOLS, sorted(tool_names)

                admitted = await session.call_tool(
                    "manifest", {}, read_timeout_seconds=timedelta(seconds=30)
                )
                assert not admitted.isError
                admitted_data = _structured(admitted)
                assert admitted_data["image"]["name"] == "1f_view.png"
                assert admitted_data["image"]["size"] == [2133, 1345]
                assert "smalloffice_20" not in json.dumps(admitted_data).lower()

                guide = await session.call_tool(
                    "get_rule",
                    {"name": "guide"},
                    read_timeout_seconds=timedelta(seconds=30),
                )
                assert not guide.isError
                guide_data = _structured(guide)
                assert guide_data["text"].startswith("# Reading-stage guide")

                source_view = await session.call_tool(
                    "view_original", {}, read_timeout_seconds=timedelta(seconds=30)
                )
                assert not source_view.isError
                image_parts = [part for part in source_view.content if isinstance(part, ImageContent)]
                assert len(image_parts) == 1
                returned = Image.open(io.BytesIO(base64.b64decode(image_parts[0].data))).convert("RGB")
                original = Image.open(workspace / "case_data/1f_view.png").convert("RGB")
                assert returned.size == original.size
                assert returned.tobytes() == original.tobytes()

                mapped_view = await session.call_tool(
                    "view_original",
                    {"box": [10, 20, 30, 50], "scale": 3},
                    read_timeout_seconds=timedelta(seconds=30),
                )
                assert not mapped_view.isError
                mapped_data = _structured(mapped_view)
                assert mapped_data["box_source_pixels"] == [10, 20, 30, 50]
                assert mapped_data["shown_size"] == [60, 90]
                assert mapped_data["display_scale_xy"] == [3, 3]
                assert mapped_data["local_to_source"] == {
                    "source_x": "10 + local_x / 3",
                    "source_y": "20 + local_y / 3",
                }
                mapped_parts = [
                    part for part in mapped_view.content if isinstance(part, ImageContent)
                ]
                assert len(mapped_parts) == 1
                mapped_image = Image.open(
                    io.BytesIO(base64.b64decode(mapped_parts[0].data))
                ).convert("RGB")
                expected_crop = original.crop((10, 20, 30, 50)).resize(
                    (60, 90), Image.Resampling.NEAREST
                )
                assert mapped_image.size == expected_crop.size
                assert mapped_image.tobytes() == expected_crop.tobytes()

                fractional_box = await session.call_tool(
                    "view_original",
                    {"box": [10.5, 20, 30, 50], "scale": 3},
                    read_timeout_seconds=timedelta(seconds=30),
                )
                assert fractional_box.isError

                crop = await session.call_tool(
                    "cv_crop_zoom",
                    {"bbox": [0, 0, 80, 80], "scale": 2},
                    read_timeout_seconds=timedelta(seconds=120),
                )
                assert not crop.isError
                crop_data = _structured(crop)
                assert crop_data["tool"] == "crop_zoom"
                assert crop_data["sidecar"]["tool"] == "crop_zoom"
                crop_chain = crop_data["sidecar"]["crop_chain"]
                assert crop_chain == [
                    {
                        "op": "crop_zoom",
                        "bbox_px": [0.0, 0.0, 80.0, 80.0],
                        "scale": 2.0,
                        "source_size_px": [2133, 1345],
                        "crop_size_px": [160, 160],
                        "local_to_source": {
                            "source_x": "0.0 + local_x / 2.0",
                            "source_y": "0.0 + local_y / 2.0",
                        },
                        "source_to_local": {
                            "local_x": "(source_x - 0.0) * 2.0",
                            "local_y": "(source_y - 0.0) * 2.0",
                        },
                    }
                ]
                assert any(row["kind"] == "image" for row in crop_data["artifacts"])

                bad_rule = await session.call_tool(
                    "get_rule",
                    {"name": "../guide.md"},
                    read_timeout_seconds=timedelta(seconds=30),
                )
                assert bad_rule.isError
                bad_artifact = await session.call_tool(
                    "view_artifact",
                    {"artifact_id": "../../outside_sentinel.txt"},
                    read_timeout_seconds=timedelta(seconds=30),
                )
                assert bad_artifact.isError
                bad_box = await session.call_tool(
                    "cv_crop_zoom",
                    {"bbox": [-1, 0, 80, 80], "scale": 2},
                    read_timeout_seconds=timedelta(seconds=30),
                )
                assert bad_box.isError

                smoke_reading = {
                    "image_label": "offline interface smoke only",
                    "image_kind": "plan",
                    "facade": None,
                    "strokes": [],
                    "dimensions": [],
                    "ocr_texts": [],
                    "uncaptured": [],
                    "self_check": {
                        "all_dimensions_transcribed": False,
                        "all_visible_strokes_captured": False,
                        "no_topology_inferred": True,
                        "pens_used": [],
                        "unknowns_noted": ["synthetic empty submission for offline wiring test"],
                    },
                }
                submission = await session.call_tool(
                    "submit_pilot",
                    {
                        "reading": smoke_reading,
                        "coordinate_frame": {
                            "x_anchors": [[0, 0], [100, 1]],
                            "y_anchors": [[0, 1], [100, 0]],
                            "basis": "synthetic offline interface smoke; not a case observation",
                        },
                        "candidate_ledger": [],
                        "self_check": {
                            "purpose": "offline interface smoke only",
                            "unexamined": ["entire source image"],
                        },
                    },
                    read_timeout_seconds=timedelta(seconds=120),
                )
                assert not submission.isError
                submission_data = _structured(submission)
                assert submission_data["submission"] == "001"
                assert submission_data["counts_reported_only"] == {
                    "strokes": 0,
                    "dimensions": 0,
                    "candidate_ledger_rows": 0,
                }
                assert "No element-count" in submission_data["note"]

        assert digest_file(sentinel) == sentinel_hash
        all_files = [path.resolve() for path in workspace.rglob("*") if path.is_file()]
        assert all(path.is_relative_to(workspace.resolve()) for path in all_files)
        projected = {
            row["projected_path"]
            if not row["projected_path"].startswith("case_data/")
            else "case_tests/e2e_tests/sm21_anchor/case_data/" + Path(row["projected_path"]).name
            for row in manifest["files"]
        }
        assert projected == set(PROJECTED_PATHS)
        forbidden = ("smalloffice_20", "test_baseline", "score_vs_gt")
        sources = [row["source"] for row in manifest["files"]]
        assert not any(token in source.lower() for source in sources for token in forbidden)
        sidecars = sorted((workspace / "0_reading/cv_evidence").rglob("*.json"))
        assert len(sidecars) == 1
        output_files = sorted(
            str(path.relative_to(workspace))
            for path in (workspace / "0_reading").rglob("*")
            if path.is_file()
        )
        implementation = implementation_manifest()
        record = {
            "schema": "historical_sm21_pilot_offline_verification_v1",
            "model_or_api_called": False,
            "mcp_transport": "actual stdio ClientSession",
            "tool_names": sorted(EXPECTED_TOOLS),
            "tool_allowlist_exact": True,
            "guide_exact_rule_read": True,
            "original_image_pixel_identity": True,
            "view_original_coordinate_mapping": {
                "integer_source_box": [10, 20, 30, 50],
                "display_scale_xy": [3, 3],
                "shown_size": [60, 90],
                "pixels_match_exact_integer_nearest_resize": True,
                "fractional_box_rejected": True,
            },
            "frozen_cv_smoke": {
                "tool": "crop_zoom",
                "sidecars_created": len(sidecars),
                "crop_chain_inverse_transform_exact": True,
            },
            "path_rejections": {
                "rule_traversal": True,
                "artifact_traversal": True,
                "out_of_bounds_crop": True,
            },
            "outside_sentinel_unchanged": True,
            "projected_source_allowlist_exact": True,
            "projected_input_count": len(manifest["files"]),
            "projected_inputs": manifest["files"],
            "implementation": implementation,
            "subscription_command_contract": {
                "native_tools_empty": True,
                "allowed_tools": "mcp__reading__*",
                "strict_single_mcp": True,
                "no_fallback_model": True,
                "stable_cli_cwd": str(stable_cli_cwd),
                "stable_cli_cwd_outside_repository": not stable_cli_cwd.is_relative_to(
                    HERE.parents[3]
                ),
                "label_traversal_rejected": True,
            },
            "output_files_from_smoke": output_files,
            "empty_submission_accepted_without_count_threshold": True,
        }
        stable_cli_cwd.rmdir()
        return record


def main() -> None:
    record = asyncio.run(verify())
    dump(HERE / "offline_verification.json", record)
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
