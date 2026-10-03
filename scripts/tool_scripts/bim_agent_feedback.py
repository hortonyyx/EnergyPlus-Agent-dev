"""Thin MCP input/feedback handling; no geometry edits or implicit observations.

T1: GLM sm21/24/25 used measurement labels as image names, sm24 exceeded
the zoom limit and skipped claim adoption, sm25 omitted edit fields. Historical
run53–58/98–100 also need actionable object, crop and note repair messages.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import Field


ImageFilename = Annotated[str, Field(description="Input image filename from inputs() (这里填输入图片的文件名), not a measurement label. Unique case/extension aliases are accepted.")]


def resolve_image_name(images, name):
    """Exact names win; only a unique case/extension alias is safe to resolve."""
    if isinstance(name, str) and name in images:
        return name
    matches = []
    if isinstance(name, str) and name and Path(name).name == name and "\\" not in name:
        matches = [key for key in images if key.casefold() == name.casefold()
                   or (not Path(name).suffix and Path(key).stem.casefold() == name.casefold())]
    if len(matches) == 1:
        return matches[0]
    problem = "ambiguous" if matches else "unknown"
    raise ValueError(f"{problem} input image filename {name!r}; here fill the input image filename, "
                     "not a measurement label. Available filenames: " + json.dumps(sorted(images)))


_NAMED_IMAGE_TOOLS = {"view_image", "pixel_profile", "view_pixel_profile",
                      "view_pixel_region_overview", "view_pixel_region", "preview_space_trace"}


def normalize_images(toolkit, tool, arguments):
    notes = []
    def image(value):
        resolved = resolve_image_name(toolkit.manifest["images"], value)
        if resolved != value:
            notes.append(f"Input image {value!r}: used actual filename {resolved!r}.")
        return resolved
    def visit(value):
        if isinstance(value, list):
            return [visit(row) for row in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, item in value.items():
            if key in {"image", "plan_image", "elevation_image"} and isinstance(item, str) and item:
                result[key] = image(item)
            elif key == "images" and isinstance(item, list):
                result[key] = [image(name) for name in item]
            else:
                result[key] = visit(item)
        return result
    result = visit(copy.deepcopy(arguments))
    if tool in _NAMED_IMAGE_TOOLS and "name" in result:
        result["name"] = image(result["name"])
    for key, value in list(result.items()):
        if key.endswith("_json") and isinstance(value, str):
            try:
                decoded = json.loads(value)
            except ValueError:
                continue  # The tool reports its own format error.
            resolved = visit(decoded)
            if resolved != decoded:
                result[key] = json.dumps(resolved, ensure_ascii=False)
    return result, list(dict.fromkeys(notes))


def repair_hint(toolkit, tool, arguments, message):
    """Explain the rejected operation without guessing geometry or evidence."""
    if "Run deadline reached" in message:
        return ""
    if "input image filename" in message or "Claim kinds use proposal collections" in message:
        return ""  # Already includes exact available choices and the next step.
    if "crop outside" in message:
        name = arguments.get("name")
        size = toolkit.manifest["images"].get(name, {}).get("size")
        return (f"Use ORIGINAL pixels for {name!r}, size {size}; omit box for the whole image, "
                "or use 0 <= left < right <= width and 0 <= top < bottom <= height.")
    if "explicitly adopted" in message:
        return ('Missing step: decide_claim(claim_id, disposition="adopted", reason="your evidence-based decision"); '
                'then retry confirm_claims if values are unchanged, or revise_bim to change them.')
    if "refer to the operation targets" in message:
        return ('Read claim_status(candidate) for exact objects/value_targets; use update_window for kind=window '
                'and update_opening for kind=opening. Record a new claim if its actual target differs.')
    if "differs from current geometry" in message:
        return "Next: send these operations to revise_bim to apply the observed values, or decide_claim(..., disposition=\"deferred\", reason=...)."
    if "stale for this parent" in message:
        return "Next: record_claim on the current candidate, decide_claim adopted, then retry with the new claim ID."
    if tool == "revise_plan_bim":
        try:
            ops = json.loads(arguments.get("operations_json", "[]"))
            index = int(re.search(r"operation (\d+)", message)[1]) if re.search(r"operation (\d+)", message) else 0
            op = ops[index]
        except (ValueError, TypeError, IndexError):
            op = {}
        kind = op.get("op", "update")
        example = dict(op=kind, reason="explain the observed correction", source_refs=["input filename: observed region"])
        if kind == "set":
            example.update(field=op.get("field", "ceiling_height"), value=op.get("value", 3.0))
        else:
            example["collection"] = op.get("collection", "partitions")
            if kind in {"update", "remove"}:
                example["id"] = op.get("id", "existing-wall-id")
            if kind == "update":
                example["changes"] = op.get("changes", {"points": op.get("points", [[10, 20], [100, 20]])})
            elif kind == "add":
                example["value"] = op.get("value", {"id": "new-wall-id", "points": [[10, 20], [100, 20]]})
        return "Minimum operation format (replace evidence placeholders): " + json.dumps([example])
    if "replace_note" in message:
        return ('Read inspect_candidate(candidate, include_geometry=false) for current notes; old must match one '
                'exact saved note, once per batch. Minimum: [{"op":"replace_note","field":"unresolved",'
                '"old":"exact current note","replacement":[],"reason":"why resolved",'
                '"source_refs":["input filename: observed evidence"]}].')
    if "set_notes" in message:
        return 'Minimum: [{"op":"set_notes","assumptions":["complete intended assumptions"],"unresolved":[]}]; omit reason/source_refs for set_notes.'
    if "requires an explicit assumption" in message:
        return ('Minimum: {"op":"set_space_role","space_id":"existing-id","role":"corridor",'
                '"basis":"inferred","assumptions":["explain the inferred use"],"reason":"why",'
                '"source_refs":["input filename: region"]}.')
    if "room_types catalog" in message:
        return "Next: get_bim_reference(topic=\"room_types\") and choose a listed role; inferred uses also need assumptions."
    if "expected exactly one existing id" in message:
        return "Next: inspect_candidate(candidate) for exact IDs; update_window edits windows and update_opening edits doors/passages."
    return "Next: read get_bim_reference(topic=" + json.dumps(
        "claims" if "claim" in tool else "edits" if "revise" in tool else "plan_partition") + ") for the operation format."


class FeedbackMCP(FastMCP):
    """One response boundary shared by successful, image and failed tools."""
    def __init__(self, toolkit, *args, **kwargs):
        self.toolkit = toolkit
        super().__init__(*args, **kwargs)

    async def call_tool(self, name, arguments):
        notes = []
        try:
            from scripts.tool_scripts.bim_agent_budget import time_status
            before = time_status(self.toolkit)
            if before["active"] and before["remaining_seconds"] <= 0:
                raise ValueError("Run deadline reached; no further tool actions. Saved output will be handed off.")
            normalized, notes = normalize_images(self.toolkit, name, arguments)
            result = await super().call_tool(name, normalized)
        except Exception as error:
            message = str(error)
            hint = repair_hint(self.toolkit, name, arguments, message)
            result = CallToolResult(isError=True, content=[TextContent(type="text", text=message + ("\n" + hint if hint else ""))])
        notes.append(time_status(self.toolkit)["line"])
        if notes:
            extra = [TextContent(type="text", text="\n".join(notes))]
            if isinstance(result, CallToolResult):
                result.content.extend(extra)
            elif isinstance(result, tuple):
                result = (list(result[0]) + extra, result[1])
            elif isinstance(result, dict):
                result = (extra + [TextContent(type="text", text=json.dumps(result))], result)
            else:
                result = list(result) + extra
        return result
