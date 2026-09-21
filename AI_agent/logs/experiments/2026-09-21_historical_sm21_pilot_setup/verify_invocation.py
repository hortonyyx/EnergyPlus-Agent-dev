#!/usr/bin/env python3
"""Verify one historical-pilot invocation without mutating its evidence.

The only write is a new ``verification.json`` beside the selected invocation.
No GT, historical answer, scorer, model, provider, or MCP process is accessed.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import copy
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tempfile
from typing import Any

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
MODEL = "claude-haiku-4-5-20251001"
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
EXPECTED_TOOLS = {
    "mcp__reading__cv_crop_zoom",
    "mcp__reading__cv_overlay_logger",
    "mcp__reading__cv_px_m_calibrator",
    "mcp__reading__cv_storey_line_profiler",
    "mcp__reading__cv_wall_line_profiler",
    "mcp__reading__cv_window_cc_detector",
    "mcp__reading__get_rule",
    "mcp__reading__list_artifacts",
    "mcp__reading__manifest",
    "mcp__reading__submit_pilot",
    "mcp__reading__view_artifact",
    "mcp__reading__view_original",
}
RULE_PATHS = {
    "session_kickoff": "skills/intake_pipeline/0_reading/session_kickoff.md",
    "guide": "skills/intake_pipeline/0_reading/guide.md",
    "reading_guide": "skills/intake_pipeline/0_reading/reading_guide.md",
    "pen_library": "skills/intake_pipeline/0_reading/pen_library.md",
    "cv_toolbox": "skills/intake_pipeline/0_reading/cv_toolbox.md",
}
MCP_ACTIONS = {
    "mcp__reading__manifest": "manifest",
    "mcp__reading__get_rule": "get_rule",
    "mcp__reading__view_original": "view_original",
    "mcp__reading__cv_crop_zoom": "crop_zoom",
    "mcp__reading__cv_wall_line_profiler": "wall_line_profiler",
    "mcp__reading__cv_storey_line_profiler": "storey_line_profiler",
    "mcp__reading__cv_px_m_calibrator": "px_m_calibrator",
    "mcp__reading__cv_window_cc_detector": "window_cc_detector",
    "mcp__reading__cv_overlay_logger": "overlay_logger",
    "mcp__reading__list_artifacts": "list_artifacts",
    "mcp__reading__view_artifact": "view_artifact",
    "mcp__reading__submit_pilot": "submit_pilot",
}


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def dump_exclusive(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )


def inside(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValueError(f"absolute evidence path refused: {relative}")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"evidence path escaped its root: {relative}") from error
    return resolved


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pixel_digest_bytes(data: bytes) -> dict[str, Any]:
    with Image.open(io.BytesIO(data)) as picture:
        rgb = picture.convert("RGB")
        size = list(rgb.size)
        payload = rgb.tobytes()
    prefix = f"{size[0]}x{size[1]}:RGB:".encode("ascii")
    return {"size": size, "sha256": digest_bytes(prefix + payload)}


def pixel_digest_file(path: Path) -> dict[str, Any]:
    return pixel_digest_bytes(path.read_bytes())


def cli_resize_comparison(source_data: bytes, delivered_data: bytes) -> dict[str, Any]:
    """Diagnose a CLI-resized delivery using independent Pillow resamplers.

    Claude Code 2.1.198 resizes an MCP image with a dimension over its vision
    limit before placing it in ``message.content``. This diagnostic never turns
    a pixel mismatch into a match. It records geometry and per-component error
    against every Pillow resampler so the host transform remains visible.
    """
    with Image.open(io.BytesIO(source_data)) as source_file:
        source = source_file.convert("RGB")
    with Image.open(io.BytesIO(delivered_data)) as delivered_file:
        delivered = delivered_file.convert("RGB")
    result: dict[str, Any] = {
        "source_size": list(source.size),
        "delivered_size": list(delivered.size),
    }
    source_over_cli_limit = max(source.size) >= 2000
    delivered_within_cli_limit = max(delivered.size) <= 2000
    source_ratio = source.width / source.height
    delivered_ratio = delivered.width / delivered.height
    aspect_error_pixels = abs(
        delivered.width - delivered.height * source_ratio
    )
    geometry_matches = bool(
        source_over_cli_limit
        and delivered_within_cli_limit
        and delivered.width <= source.width
        and delivered.height <= source.height
        and aspect_error_pixels <= 1.5
    )
    result.update(
        source_over_cli_limit=source_over_cli_limit,
        delivered_within_cli_limit=delivered_within_cli_limit,
        aspect_error_pixels=aspect_error_pixels,
        geometry_matches_cli_resize=geometry_matches,
    )
    if not geometry_matches:
        result["matched"] = False
        return result
    delivered_bytes = delivered.tobytes()
    component_count = len(delivered_bytes)
    samplers = {
        "NEAREST": Image.Resampling.NEAREST,
        "BOX": Image.Resampling.BOX,
        "BILINEAR": Image.Resampling.BILINEAR,
        "HAMMING": Image.Resampling.HAMMING,
        "BICUBIC": Image.Resampling.BICUBIC,
        "LANCZOS": Image.Resampling.LANCZOS,
    }
    comparisons = {}
    for name, sampler in samplers.items():
        reference = source.resize(delivered.size, sampler)
        histogram = ImageChops.difference(reference, delivered).histogram()
        difference_sum = sum(
            value * count
            for channel in range(3)
            for value, count in enumerate(histogram[channel * 256 : (channel + 1) * 256])
        )
        zero_components = sum(histogram[channel * 256] for channel in range(3))
        maximum = max(
            (
                value
                for channel in range(3)
                for value, count in enumerate(
                    histogram[channel * 256 : (channel + 1) * 256]
                )
                if count
            ),
            default=0,
        )
        comparisons[name] = {
            "mean_absolute_error": difference_sum / component_count,
            "maximum_absolute_error": maximum,
            "exact_component_fraction": zero_components / component_count,
        }
    best_name = min(comparisons, key=lambda name: comparisons[name]["mean_absolute_error"])
    best = comparisons[best_name]
    result.update(
        compared_rgb_components=component_count,
        pillow_resamplers=comparisons,
        closest_pillow_resampler=best_name,
        closest_mean_absolute_error=best["mean_absolute_error"],
        closest_exact_component_fraction=best["exact_component_fraction"],
        consistent_with_host_resize=(
            geometry_matches
            and best["mean_absolute_error"] <= 0.05
            and best["exact_component_fraction"] >= 0.98
        ),
        matched=False,
        note="Diagnostic only: a resized stream image remains pixel-different from the saved image.",
    )
    return result


def decoded_image(block: dict[str, Any]) -> bytes:
    source = block.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("data"), str):
        raise ValueError("image return lacks base64 source data")
    return base64.b64decode(source["data"], validate=True)


def parse_result_content(block: dict[str, Any]) -> tuple[list[dict[str, Any]], dict | None, str | None]:
    content = block.get("content")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        return [], parsed if isinstance(parsed, dict) else None, content
    if not isinstance(content, list):
        return [], None, None
    images = [part for part in content if isinstance(part, dict) and part.get("type") == "image"]
    texts = [part.get("text") for part in content if isinstance(part, dict) and part.get("type") == "text"]
    parsed = None
    raw_text = None
    for text in reversed(texts):
        if not isinstance(text, str):
            continue
        raw_text = text
        try:
            candidate = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            parsed = candidate
            break
    return images, parsed, raw_text


def normalize_sidecar(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    if result.get("overlay_path"):
        result["overlay_path"] = Path(result["overlay_path"]).name
    for row in result.get("results", []):
        if isinstance(row, dict) and row.get("output_image"):
            row["output_image"] = Path(row["output_image"]).name
    return result


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, name: str, passed: bool | None, detail: Any = None) -> None:
        status = "unavailable" if passed is None else "pass" if passed else "fail"
        row = {"name": name, "status": status}
        if detail is not None:
            row["detail"] = detail
        self.rows.append(row)

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [row for row in self.rows if row["status"] == "fail"]


def load_events(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    compressed_path = path.with_name(path.name + ".gz")
    if path.is_file():
        source_path = path
        stored_data = path.read_bytes()
        data = stored_data
        compression = "none"
    elif compressed_path.is_file():
        source_path = compressed_path
        stored_data = compressed_path.read_bytes()
        data = gzip.decompress(stored_data)
        compression = "gzip"
    else:
        return [], {
            "exists": False,
            "paths_tried": [str(path), str(compressed_path)],
            "bytes_read": 0,
            "sha256": None,
            "parse_errors": [],
        }
    events = []
    errors = []
    lines = data.splitlines()
    for index, raw in enumerate(lines, start=1):
        try:
            event = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            errors.append({"line": index, "error": str(error), "bytes": len(raw)})
            continue
        if isinstance(event, dict):
            events.append(event)
    return events, {
        "exists": True,
        "path": str(source_path),
        "compression": compression,
        "stored_bytes": len(stored_data),
        "stored_sha256": digest_bytes(stored_data),
        "bytes_read": len(data),
        "sha256": digest_bytes(data),
        "line_count": len(lines),
        "parsed_event_count": len(events),
        "parse_errors": errors,
    }


def command_contract(request: dict[str, Any], workspace: Path) -> dict[str, Any]:
    command = request.get("command")
    result: dict[str, Any] = {"recorded": isinstance(command, list), "errors": []}
    if not isinstance(command, list):
        result["valid"] = False
        return result

    def option(name: str) -> str | None:
        try:
            return command[command.index(name) + 1]
        except (ValueError, IndexError):
            return None

    result.update(
        model=option("--model"),
        native_tools=option("--tools"),
        allowed_tools=option("--allowedTools"),
        permission_mode=option("--permission-mode"),
        strict_mcp_config="--strict-mcp-config" in command,
        setting_sources=option("--setting-sources"),
        slash_commands_disabled="--disable-slash-commands" in command,
        fallback_configured="--fallback-model" in command,
        no_session_persistence="--no-session-persistence" in command,
    )
    raw_mcp = option("--mcp-config")
    try:
        mcp = json.loads(raw_mcp) if raw_mcp else None
    except json.JSONDecodeError as error:
        mcp = None
        result["errors"].append(f"invalid MCP JSON: {error}")
    servers = mcp.get("mcpServers", {}) if isinstance(mcp, dict) else {}
    result["mcp_server_names"] = sorted(servers) if isinstance(servers, dict) else []
    reading = servers.get("reading") if isinstance(servers, dict) else None
    args = reading.get("args", []) if isinstance(reading, dict) else []
    try:
        workspace_arg = args[args.index("--workspace") + 1]
    except (ValueError, IndexError):
        workspace_arg = None
    result["mcp_workspace"] = workspace_arg
    result["mcp_workspace_matches_run"] = bool(
        workspace_arg and Path(workspace_arg).resolve() == workspace.resolve()
    )
    result["valid"] = all(
        [
            result["model"] == MODEL,
            result["native_tools"] == "",
            result["allowed_tools"] == "mcp__reading__*",
            result["permission_mode"] == "dontAsk",
            result["strict_mcp_config"],
            result["setting_sources"] == "",
            result["slash_commands_disabled"],
            not result["fallback_configured"],
            not result["no_session_persistence"],
            result["mcp_server_names"] == ["reading"],
            result["mcp_workspace_matches_run"],
        ]
    )
    return result


def verify_manifest_files(
    manifest: dict[str, Any], root: Path, checks: Checks, prefix: str
) -> list[dict[str, Any]]:
    rows = []
    for row in manifest.get("files", []):
        relative = row.get("projected_path", row.get("path"))
        item = {"path": relative, "expected_sha256": row.get("sha256")}
        try:
            path = inside(root, relative)
            item["exists"] = path.is_file()
            item["actual_sha256"] = digest_file(path) if path.is_file() else None
            item["matches"] = item["actual_sha256"] == item["expected_sha256"]
        except Exception as error:
            item.update(exists=False, actual_sha256=None, matches=False, error=str(error))
        rows.append(item)
    checks.add(f"{prefix}_file_hashes", all(row["matches"] for row in rows), rows)
    return rows


def expected_view_image(
    original: Path, tool_input: dict[str, Any], metadata: dict[str, Any]
) -> bytes:
    box = tool_input.get("box")
    scale = tool_input.get("scale", 1)
    if box is None and scale == 1:
        return original.read_bytes()
    if not isinstance(box, list):
        with Image.open(original) as source:
            box = [0, 0, source.width, source.height]
    with Image.open(original) as source:
        picture = source.convert("RGB").crop(tuple(box))
        if scale != 1:
            picture = picture.resize(
                (round(picture.width * scale), round(picture.height * scale)),
                Image.Resampling.NEAREST,
            )
    output = io.BytesIO()
    picture.save(output, "PNG")
    claimed_size = metadata.get("shown_size")
    if claimed_size is not None and claimed_size != list(picture.size):
        raise ValueError("view_original metadata shown_size disagrees with request")
    return output.getvalue()


def verify_images_for_call(
    *,
    tool: str,
    tool_input: dict[str, Any],
    images: list[dict[str, Any]],
    payload: dict[str, Any] | None,
    evidence_root: Path,
    original: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    uncovered = []
    expected: list[tuple[str, bytes]] = []
    if tool == "mcp__reading__view_original" and payload is not None:
        expected.append(
            ("original_or_requested_crop", expected_view_image(original, tool_input, payload))
        )
    elif tool.startswith("mcp__reading__cv_") and payload is not None:
        for artifact in payload.get("artifacts", []):
            if artifact.get("kind") != "image":
                continue
            try:
                path = inside(evidence_root, artifact["path"])
                expected.append((artifact.get("id", artifact["path"]), path.read_bytes()))
            except Exception as error:
                uncovered.append(f"artifact {artifact.get('id')} unavailable: {error}")
    elif tool == "mcp__reading__view_artifact" and payload is not None:
        registry_path = evidence_root / "artifact_registry.json"
        try:
            registry = read_json(registry_path)
            artifact_id = payload["id"]
            path = inside(evidence_root, registry[artifact_id]["path"])
            expected.append((artifact_id, path.read_bytes()))
        except Exception as error:
            uncovered.append(f"view_artifact source unavailable: {error}")
    elif tool == "mcp__reading__submit_pilot" and payload is not None:
        submission = payload.get("submission")
        for name in ("1f_view_render.png", "1f_view_source_overlay.png"):
            try:
                path = inside(
                    evidence_root,
                    f"0_reading/submissions/{submission}/{name}",
                )
                expected.append((f"submission/{submission}/{name}", path.read_bytes()))
            except Exception as error:
                uncovered.append(f"submission image unavailable: {error}")
    elif images:
        uncovered.append("tool returned images but verifier has no mapping rule")

    if len(images) != len(expected):
        uncovered.append(
            f"image count mismatch: returned {len(images)}, expected {len(expected)}"
        )
    for index, block in enumerate(images):
        row: dict[str, Any] = {"index": index}
        try:
            returned = decoded_image(block)
            row["returned_bytes_sha256"] = digest_bytes(returned)
            row["returned_pixels"] = pixel_digest_bytes(returned)
            if index < len(expected):
                name, expected_bytes = expected[index]
                row["expected"] = name
                row["expected_bytes_sha256"] = digest_bytes(expected_bytes)
                row["expected_pixels"] = pixel_digest_bytes(expected_bytes)
                row["byte_identical"] = returned == expected_bytes
                row["pixel_identical"] = (
                    row["returned_pixels"] == row["expected_pixels"]
                )
                if row["pixel_identical"]:
                    row["transport_verified"] = True
                    row["delivery_mode"] = (
                        "byte_identical"
                        if row["byte_identical"]
                        else "pixel_identical_reencoding"
                    )
                else:
                    resize = cli_resize_comparison(expected_bytes, returned)
                    row["cli_resize_comparison"] = resize
                    row["transport_verified"] = False
                    row["delivery_mode"] = (
                        "claude_cli_resize_diagnosed_but_pixel_different"
                        if resize.get("consistent_with_host_resize")
                        else "unmatched"
                    )
            else:
                row["pixel_identical"] = False
                row["transport_verified"] = False
        except Exception as error:
            row.update(pixel_identical=False, transport_verified=False, error=str(error))
        rows.append(row)
    return rows, uncovered


def verify_sidecar_return(
    payload: dict[str, Any], evidence_root: Path
) -> dict[str, Any] | None:
    returned = payload.get("sidecar")
    if not isinstance(returned, dict):
        return None
    candidates = [
        row
        for row in payload.get("artifacts", [])
        if row.get("kind") == "json" and "cv_evidence/" in row.get("path", "")
    ]
    if len(candidates) != 1:
        return {
            "matched": False,
            "reason": f"expected one sidecar artifact, found {len(candidates)}",
        }
    row = candidates[0]
    try:
        path = inside(evidence_root, row["path"])
        saved = read_json(path)
        return {
            "artifact_id": row.get("id"),
            "path": row["path"],
            "file_sha256_matches_artifact": digest_file(path) == row.get("sha256"),
            "returned_matches_saved_after_path_sanitization": returned
            == normalize_sidecar(saved),
            "matched": (
                digest_file(path) == row.get("sha256")
                and returned == normalize_sidecar(saved)
            ),
        }
    except Exception as error:
        return {"matched": False, "reason": str(error)}


def verify_submission_return(
    payload: dict[str, Any], evidence_root: Path
) -> dict[str, Any] | None:
    submission = payload.get("submission")
    if not isinstance(submission, str):
        return None
    mapping = {
        "reading_sha256": "1f_view.json",
        "coordinate_frame_sha256": "coordinate_frame.json",
        "candidate_ledger_sha256": "candidate_ledger.json",
        "self_check_sha256": "pilot_self_check.json",
    }
    rows = []
    for field, name in mapping.items():
        try:
            path = inside(
                evidence_root, f"0_reading/submissions/{submission}/{name}"
            )
            actual = digest_file(path)
            rows.append(
                {
                    "field": field,
                    "path": str(path.relative_to(evidence_root)),
                    "expected": payload.get(field),
                    "actual": actual,
                    "matches": actual == payload.get(field),
                }
            )
        except Exception as error:
            rows.append({"field": field, "matches": False, "error": str(error)})
    return {"submission": submission, "files": rows, "matched": all(row["matches"] for row in rows)}


def verify_run(run: Path, label: str) -> dict[str, Any]:
    run = run.resolve()
    if not LABEL_RE.fullmatch(label):
        raise ValueError("invalid label")
    invocation = inside(run / "invocations", label)
    workspace = inside(run, "workspace")
    checks = Checks()

    receipt_path = invocation / "receipt.json"
    snapshot_manifest_path = invocation / "snapshot_manifest.json"
    receipt = read_json(receipt_path) if receipt_path.is_file() else None
    snapshot_manifest = (
        read_json(snapshot_manifest_path) if snapshot_manifest_path.is_file() else None
    )
    if receipt is None:
        state = "in_progress"
    elif snapshot_manifest is None:
        state = "finalizing"
    else:
        state = "completed"

    request_path = invocation / "request.json"
    request = read_json(request_path) if request_path.is_file() else {}
    command = command_contract(request, workspace)
    checks.add("recorded_permission_command", command.get("valid", False), command)
    prompt_path = invocation / "prompt.md"
    prompt_hashes = {
        "expected": request.get("prompt_sha256"),
        "actual": digest_file(prompt_path) if prompt_path.is_file() else None,
    }
    checks.add(
        "invocation_prompt_hash",
        prompt_hashes["expected"] == prompt_hashes["actual"]
        and prompt_hashes["actual"] is not None,
        prompt_hashes,
    )

    input_manifest_path = run / "input_manifest.json"
    implementation_manifest_path = run / "implementation_manifest.json"
    projection_manifest_path = workspace / "projection_manifest.json"
    input_manifest = read_json(input_manifest_path) if input_manifest_path.is_file() else {"files": []}
    implementation_manifest = (
        read_json(implementation_manifest_path)
        if implementation_manifest_path.is_file()
        else {"files": []}
    )
    projection_manifest = (
        read_json(projection_manifest_path)
        if projection_manifest_path.is_file()
        else {"files": []}
    )
    verify_manifest_files(input_manifest, workspace, checks, "input_manifest")
    verify_manifest_files(implementation_manifest, HERE, checks, "implementation_manifest")
    checks.add(
        "projection_manifest_matches_run_manifest",
        input_manifest == projection_manifest,
        {
            "input_manifest_sha256": digest_file(input_manifest_path)
            if input_manifest_path.is_file()
            else None,
            "projection_manifest_sha256": digest_file(projection_manifest_path)
            if projection_manifest_path.is_file()
            else None,
        },
    )
    request_hashes = {
        "input_expected": request.get("input_manifest_sha256"),
        "input_actual": digest_file(input_manifest_path)
        if input_manifest_path.is_file()
        else None,
        "implementation_expected": request.get("implementation_manifest_sha256"),
        "implementation_actual": digest_file(implementation_manifest_path)
        if implementation_manifest_path.is_file()
        else None,
    }
    checks.add(
        "request_manifest_hashes",
        request_hashes["input_expected"] == request_hashes["input_actual"]
        and request_hashes["implementation_expected"]
        == request_hashes["implementation_actual"],
        request_hashes,
    )

    snapshot_rows = []
    if snapshot_manifest is not None:
        snapshot_rows = verify_manifest_files(
            snapshot_manifest, invocation / "snapshot", checks, "snapshot_manifest"
        )
    else:
        checks.add("snapshot_manifest_file_hashes", None, f"run state is {state}")

    events, event_record = load_events(invocation / "events.jsonl")
    checks.add(
        "event_stream_parse",
        not event_record["parse_errors"] if state == "completed" else None,
        event_record,
    )
    init_events = [
        event
        for event in events
        if event.get("type") == "system" and event.get("subtype") == "init"
    ]
    init = init_events[0] if init_events else None
    init_contract = {
        "present": init is not None,
        "model": init.get("model") if init else None,
        "tools": init.get("tools") if init else None,
        "permissionMode": init.get("permissionMode") if init else None,
        "mcp_servers": init.get("mcp_servers") if init else None,
        "slash_commands": init.get("slash_commands") if init else None,
        "apiKeySource": init.get("apiKeySource") if init else None,
        "claude_code_version": init.get("claude_code_version") if init else None,
        "cwd": init.get("cwd") if init else None,
    }
    init_valid = bool(
        init
        and init.get("model") == MODEL
        and set(init.get("tools", [])) == EXPECTED_TOOLS
        and init.get("permissionMode") == "dontAsk"
        and init.get("slash_commands") == []
        and init.get("apiKeySource") == "none"
        and init.get("mcp_servers") == [{"name": "reading", "status": "connected"}]
    )
    checks.add("actual_cli_init_contract", init_valid, init_contract)

    calls: list[dict[str, Any]] = []
    results_by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append(
                        {
                            "id": block.get("id"),
                            "name": block.get("name"),
                            "input": block.get("input")
                            if isinstance(block.get("input"), dict)
                            else {},
                        }
                    )
        elif event.get("type") == "user":
            for block in event.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    results_by_id[block.get("tool_use_id")] = block
    unexpected_tools = sorted(
        {call["name"] for call in calls if call["name"] not in EXPECTED_TOOLS}
    )
    checks.add("actual_tool_names_allowlisted", not unexpected_tools, unexpected_tools)

    evidence_root = (
        invocation / "snapshot" if snapshot_manifest is not None else workspace
    )
    original = workspace / "case_data/1f_view.png"
    tool_records = []
    all_image_checks = []
    uncovered_images = []
    sidecar_checks = []
    submission_checks = []
    for call in calls:
        result = results_by_id.get(call["id"])
        row: dict[str, Any] = {
            "id": call["id"],
            "name": call["name"],
            "input": call["input"],
            "result_present": result is not None,
        }
        if result is None:
            row["status"] = "pending" if state != "completed" else "missing_result"
            tool_records.append(row)
            continue
        row["is_error"] = bool(result.get("is_error", False))
        if row["is_error"]:
            content = result.get("content")
            row["status"] = "tool_error"
            row["error"] = content[:2000] if isinstance(content, str) else content
            tool_records.append(row)
            continue
        images, payload, raw_text = parse_result_content(result)
        row["status"] = "success"
        row["returned_image_count"] = len(images)
        row["returned_json"] = isinstance(payload, dict)
        if payload is None and raw_text is not None:
            row["unparsed_text_excerpt"] = raw_text[:1000]
        image_rows, image_uncovered = verify_images_for_call(
            tool=call["name"],
            tool_input=call["input"],
            images=images,
            payload=payload,
            evidence_root=evidence_root,
            original=original,
        )
        for image_row in image_rows:
            image_row.update(call_id=call["id"], tool=call["name"])
        all_image_checks.extend(image_rows)
        uncovered_images.extend(
            f"{call['id']} {call['name']}: {message}" for message in image_uncovered
        )
        if payload is not None and call["name"].startswith("mcp__reading__cv_"):
            sidecar = verify_sidecar_return(payload, evidence_root)
            if sidecar is not None:
                sidecar.update(call_id=call["id"], tool=call["name"])
                sidecar_checks.append(sidecar)
        if payload is not None and call["name"] == "mcp__reading__submit_pilot":
            submission = verify_submission_return(payload, evidence_root)
            if submission is not None:
                submission.update(call_id=call["id"])
                submission_checks.append(submission)
        tool_records.append(row)

    pending_calls = [row for row in tool_records if row["status"] == "pending"]
    missing_results = [row for row in tool_records if row["status"] == "missing_result"]
    tool_errors = [row for row in tool_records if row["status"] == "tool_error"]
    checks.add(
        "completed_calls_have_results",
        not missing_results if state == "completed" else None,
        {"pending": len(pending_calls), "missing_after_completion": len(missing_results)},
    )
    image_matches = all(row.get("transport_verified") for row in all_image_checks)
    resize_rows = [
        {
            "call_id": row.get("call_id"),
            "tool": row.get("tool"),
            "expected": row.get("expected"),
            **row["cli_resize_comparison"],
        }
        for row in all_image_checks
        if "cli_resize_comparison" in row
    ]
    checks.add(
        "all_returned_images_match_admitted_or_saved_pixels",
        image_matches and not uncovered_images if state == "completed" else None,
        {
            "images": all_image_checks,
            "uncovered": uncovered_images,
            "interpretation": (
                "Pass requires exact saved pixels. A host-resized stream image "
                "remains a failure here even when the separate resize diagnostic "
                "shows it closely follows the saved image."
            ),
        },
    )
    checks.add(
        "cli_resize_diagnostic_consistency",
        all(row.get("consistent_with_host_resize") for row in resize_rows)
        if state == "completed" and resize_rows
        else None,
        resize_rows or "no pixel-different image needed a resize diagnostic",
    )
    checks.add(
        "cv_sidecar_returns_match_saved_sidecars",
        all(row.get("matched") for row in sidecar_checks)
        if state == "completed" and sidecar_checks
        else None,
        sidecar_checks,
    )
    checks.add(
        "submission_hashes_match_versioned_files",
        all(row.get("matched") for row in submission_checks)
        if state == "completed" and submission_checks
        else None,
        submission_checks or "no submit_pilot return in this invocation",
    )

    mcp_log_path = evidence_root / "mcp_tools.jsonl"
    mcp_log_actions: Counter[str] = Counter()
    mcp_log_errors = []
    if mcp_log_path.is_file():
        for index, line in enumerate(mcp_log_path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                item = json.loads(line)
                mcp_log_actions[item.get("action")] += 1
            except json.JSONDecodeError as error:
                mcp_log_errors.append({"line": index, "error": str(error)})
    successful_action_counts = Counter(
        MCP_ACTIONS[row["name"]]
        for row in tool_records
        if row["status"] == "success" and row["name"] in MCP_ACTIONS
    )
    mcp_log_covers = all(
        mcp_log_actions[action] >= count
        for action, count in successful_action_counts.items()
    )
    checks.add(
        "mcp_disk_log_covers_successful_calls",
        mcp_log_covers and not mcp_log_errors if state == "completed" else None,
        {
            "successful_current_invocation": dict(successful_action_counts),
            "snapshot_cumulative_actions": dict(mcp_log_actions),
            "parse_errors": mcp_log_errors,
        },
    )

    receipt_check = None
    if receipt is not None:
        final_results = [event for event in events if event.get("type") == "result"]
        receipt_check = {
            "model_requested": receipt.get("model_requested"),
            "actual_models": receipt.get("actual_models"),
            "cli_version": receipt.get("cli_version"),
            "session_id": receipt.get("session_id"),
            "timed_out": receipt.get("timed_out"),
            "returncode": receipt.get("returncode"),
            "channel": receipt.get("channel"),
            "final_result_events": len(final_results),
            "result_matches_last_event": bool(final_results)
            and receipt.get("result") == final_results[-1],
        }
        receipt_valid = bool(
            receipt.get("model_requested") == MODEL
            and receipt.get("actual_models") == [MODEL]
            and receipt.get("channel")
            == "Claude subscription OAuth; no API provider or fallback"
            and receipt_check["result_matches_last_event"]
        )
        checks.add("completed_receipt_matches_stream", receipt_valid, receipt_check)
    else:
        checks.add("completed_receipt_matches_stream", None, "receipt not present")

    reading_paths = []
    if snapshot_manifest is not None:
        reading_paths = [
            row["path"]
            for row in snapshot_manifest.get("files", [])
            if row["path"].endswith("1f_view.json")
        ]
    output_state = {
        "reading_present": bool(reading_paths),
        "reading_paths": reading_paths,
        "submit_call_count": sum(
            call["name"] == "mcp__reading__submit_pilot" for call in calls
        ),
        "tool_error_count": len(tool_errors),
        "tool_errors": tool_errors,
        "pending_call_count": len(pending_calls),
        "note": (
            "No reading is a valid diagnostic state for transport verification; "
            "it is not converted into a reading-quality verdict."
        ),
    }

    if state != "completed":
        overall = "in_progress_diagnostic"
    elif checks.failures:
        overall = "completed_with_integrity_failures"
    else:
        overall = "completed_evidence_verified"
    return {
        "schema": "historical_sm21_invocation_verification_v1",
        "run": str(run),
        "label": label,
        "state": state,
        "overall": overall,
        "evidence_source": (
            "immutable invocation snapshot" if snapshot_manifest is not None else "current live workspace; run not finalized"
        ),
        "checks": checks.rows,
        "failure_count": len(checks.failures),
        "tool_summary": {
            "call_count": len(calls),
            "result_count": len(results_by_id),
            "successful_count": sum(row["status"] == "success" for row in tool_records),
            "error_count": len(tool_errors),
            "pending_count": len(pending_calls),
            "names": dict(Counter(call["name"] for call in calls)),
            "records": tool_records,
        },
        "image_transport": {
            "returned_image_count": len(all_image_checks),
            "checks": all_image_checks,
            "uncovered": uncovered_images,
        },
        "resize_diagnostic": {
            "pixel_different_image_count": len(resize_rows),
            "all_consistent_with_host_resize": bool(resize_rows)
            and all(row.get("consistent_with_host_resize") for row in resize_rows),
            "rows": resize_rows,
            "verdict_scope": (
                "Host/CLI transport diagnosis only; does not pass exact pixel "
                "integrity and does not score reading semantics."
            ),
        },
        "sidecar_transport": sidecar_checks,
        "submission_transport": submission_checks,
        "output_state": output_state,
        "snapshot_files_checked": len(snapshot_rows),
        "receipt": receipt_check,
        "limitations": [
            "Verifies CLI/MCP return payloads against admitted inputs and saved snapshot bytes/pixels; provider-internal visual preprocessing after the recorded CLI event is not observable.",
            "Claude CLI 2.1.198 resizes images at or above its vision dimension limit. The verifier records delivered pixels exactly and compares them component-by-component with every Pillow resampler, but the CLI native resizer is not separately callable. Resized images remain explicit pixel-integrity failures.",
            "Does not judge whether walls, windows, dimensions, calibration anchors, candidate semantics or the final reading are correct.",
            "Does not read GT, scorer inputs, worked examples, prior case answers or model credentials.",
            "A recorded tool error is preserved as an execution fact and is separate from evidence-integrity failures.",
            "When state is in_progress/finalizing, live files may still grow; unavailable checks are diagnostics, not failures.",
        ],
    }


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="historical-verify-invocation-") as temp:
        run = Path(temp) / "run"
        workspace = run / "workspace"
        invocation = run / "invocations" / "pilot_01"
        snapshot = invocation / "snapshot"
        (workspace / "case_data").mkdir(parents=True)
        invocation.mkdir(parents=True)
        snapshot.mkdir()
        image = Image.new("RGB", (4, 3), (240, 240, 240))
        image_path = workspace / "case_data/1f_view.png"
        image.save(image_path)
        input_manifest = {
            "files": [
                {
                    "projected_path": "case_data/1f_view.png",
                    "sha256": digest_file(image_path),
                }
            ]
        }
        projection = copy.deepcopy(input_manifest)
        (workspace / "projection_manifest.json").write_text(
            json.dumps(projection), encoding="utf-8"
        )
        (run / "input_manifest.json").write_text(
            json.dumps(input_manifest), encoding="utf-8"
        )
        implementation = {"files": []}
        (run / "implementation_manifest.json").write_text(
            json.dumps(implementation), encoding="utf-8"
        )
        mcp = {
            "mcpServers": {
                "reading": {
                    "command": "python",
                    "args": ["reading_mcp.py", "serve", "--workspace", str(workspace)],
                }
            }
        }
        command = [
            "claude", "-p", "--model", MODEL, "--tools", "",
            "--allowedTools", "mcp__reading__*", "--permission-mode", "dontAsk",
            "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
            "--mcp-config", json.dumps(mcp), "--system-prompt", "[stored]",
        ]
        prompt_path = invocation / "prompt.md"
        prompt_path.write_text("synthetic offline prompt\n", encoding="utf-8")
        request = {
            "command": command,
            "prompt_sha256": digest_file(prompt_path),
            "input_manifest_sha256": digest_file(run / "input_manifest.json"),
            "implementation_manifest_sha256": digest_file(
                run / "implementation_manifest.json"
            ),
        }
        (invocation / "request.json").write_text(json.dumps(request), encoding="utf-8")
        session = "00000000-0000-4000-8000-000000000001"
        call_id = "toolu_selftest"
        image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        metadata = {
            "source_image": "1f_view.png",
            "source_size": [4, 3],
            "source_sha256": digest_file(image_path),
            "box_source_pixels": None,
            "display_scale": 1,
            "display_scale_xy": [1, 1],
            "shown_size": [4, 3],
            "local_to_source": {"source_x": "local_x", "source_y": "local_y"},
        }
        events = [
            {
                "type": "system", "subtype": "init", "session_id": session,
                "tools": sorted(EXPECTED_TOOLS), "model": MODEL,
                "permissionMode": "dontAsk", "slash_commands": [], "apiKeySource": "none",
                "mcp_servers": [{"name": "reading", "status": "connected"}],
                "claude_code_version": "self-test", "cwd": "/tmp/self-test",
            },
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "id": call_id,
                    "name": "mcp__reading__view_original", "input": {}}]},
            },
            {
                "type": "user",
                "message": {"content": [{"type": "tool_result", "tool_use_id": call_id,
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
                        {"type": "text", "text": json.dumps(metadata)},
                    ]}]},
            },
            {"type": "result", "session_id": session, "is_error": False, "result": "done"},
        ]
        event_path = invocation / "events.jsonl"
        event_path.write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
        )
        receipt = {
            "model_requested": MODEL, "actual_models": [MODEL],
            "cli_version": "self-test", "session_id": session,
            "timed_out": False, "returncode": 0,
            "channel": "Claude subscription OAuth; no API provider or fallback",
            "result": events[-1],
        }
        (invocation / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        (snapshot / "mcp_tools.jsonl").write_text(
            json.dumps({"action": "view_original", "details": {}}) + "\n",
            encoding="utf-8",
        )
        snapshot_files = [
            {
                "path": "mcp_tools.jsonl",
                "sha256": digest_file(snapshot / "mcp_tools.jsonl"),
                "bytes": (snapshot / "mcp_tools.jsonl").stat().st_size,
            }
        ]
        (invocation / "snapshot_manifest.json").write_text(
            json.dumps({"files": snapshot_files}), encoding="utf-8"
        )
        result = verify_run(run, "pilot_01")
        assert result["overall"] == "completed_evidence_verified", result
        assert result["image_transport"]["checks"][0]["pixel_identical"] is True
        with gzip.open(invocation / "events.jsonl.gz", "wb") as stream:
            stream.write(event_path.read_bytes())
        event_path.unlink()
        compressed_result = verify_run(run, "pilot_01")
        assert compressed_result["overall"] == "completed_evidence_verified"
        event_check = next(
            row
            for row in compressed_result["checks"]
            if row["name"] == "event_stream_parse"
        )
        assert event_check["detail"]["compression"] == "gzip"
        return {
            "self_test": "pass",
            "overall": result["overall"],
            "image_pixel_match": True,
            "gzip_event_stream": "pass",
            "model_or_api_called": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--label")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return
    if args.run is None or args.label is None:
        parser.error("--run and --label are required unless --self-test is used")
    result = verify_run(args.run, args.label)
    output = args.run.resolve() / "invocations" / args.label / "verification.json"
    dump_exclusive(output, result)
    print(
        json.dumps(
            {
                "output": str(output),
                "state": result["state"],
                "overall": result["overall"],
                "failure_count": result["failure_count"],
                "tool_calls": result["tool_summary"]["call_count"],
                "returned_images": result["image_transport"]["returned_image_count"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
