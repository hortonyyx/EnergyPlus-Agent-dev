"""Bounded trial views; complete evidence remains in the verified receipt."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _child(pointer, key):
    return pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")


def reference(receipt, pointer, value):
    raw = _bytes(value)
    result = {"json_pointer": pointer, "sha256": hashlib.sha256(raw).hexdigest(),
              "hash_encoding": "utf-8-json-sort_keys-compact-ensure_ascii_false",
              "bytes": len(raw), "read": {"tool": "read_plan_draft", "arguments": {
                  "trial_id": receipt.get("trial_id", "latest"), "field": "report:" + pointer}}}
    if receipt.get("receipt_file"):
        result["receipt_file"] = receipt["receipt_file"]
    if isinstance(value, (list, dict)):
        result["item_count"] = len(value)
    return result


def _preview(receipt, pointer, value, *, budget=1800, depth=2, reference_for=None):
    if len(_bytes(value)) <= budget:
        return copy.deepcopy(value)
    result = {"full_record": (reference_for(pointer, value) if reference_for else
                              reference(receipt, pointer, value)), "truncated": True}
    if depth == 0:
        return result
    if isinstance(value, Mapping):
        # Keep verdicts and locations ahead of potentially repeated audit ledgers.
        preferred = ("status", "total", "counts", "reason", "scope", "not_checked", "coverage",
                     "id", "issue_id", "type", "kind", "divider", "opening", "look_box", "bbox",
                     "check", "summary", "grid_step_m", "findings", "items")
        keys = [key for key in preferred if key in value]
        result["summary"] = {key: _preview(receipt, _child(pointer, key), value[key], budget=350,
                                           depth=depth - 1, reference_for=reference_for)
                             for key in keys[:12]}
    elif isinstance(value, list):
        result["items"] = [_preview(receipt, _child(pointer, i), row, budget=350,
                                     depth=depth - 1, reference_for=reference_for)
                           for i, row in enumerate(value[:4])]
        result["remaining"] = max(0, len(value) - 4)
    elif isinstance(value, str):
        result["preview"] = value[:300]
    return result


def report_summary(receipt, field):
    """Keep verdicts and located findings, with all omitted ledger data retrievable."""
    value, pointer = receipt[field], _child("", field)
    if not isinstance(value, Mapping):
        return _preview(receipt, pointer, value)
    keep = ("schema", "status", "total", "counts", "items", "coverage", "scope", "meaning",
            "not_checked", "reason", "wall_placement", "corridor_space_ids", "findings", "hint")
    return {key: _preview(receipt, _child(pointer, key), value[key]) for key in keep if key in value}


def passed_receipt(receipt):
    """Project every field without permitting a nested report to grow unbounded."""
    visible = {}
    audit_refs = {}
    for field, value in receipt.items():
        if field == "returned_images":
            visible[field] = [{key: image[key] for key in ("file", "sha256") if key in image}
                              for image in value if isinstance(image, Mapping)]
            continue
        pointer = _child("", field)
        if field in {"operations", "plan_revision", "measurement_profiles", "length_bindings",
                     "measurement_bindings", "reading_alignment", "alignment"}:
            if value not in (None, [], {}):
                audit_refs[field] = reference(receipt, pointer, value)
            if field not in {"reading_alignment", "alignment"}:
                continue
        if field in {"building_precision", "drawing_differences", "corridor_review"} and isinstance(value, Mapping):
            # A precision report can carry the complete regularization ledger three
            # times. Keep the audit verdict and located findings, not that ledger.
            visible[field] = report_summary(receipt, field)
            audit_refs[field] = reference(receipt, pointer, value)
        else:
            visible[field] = _preview(receipt, pointer, value)
            if len(_bytes(value)) > 1800:
                audit_refs[field] = reference(receipt, pointer, value)
    issues = receipt.get("topology_issues", [])
    visible["submission"] = {"status": "not_submitted", "topology_decisions_required": len(issues),
        "instruction": "Trial passed is a compiled floor draft, not a reader delivery or drawing-fidelity approval."}
    visible["next_action"] = {
        "tool": "submit_plan_reading", "arguments": {"trial_id": receipt.get("trial_id", "latest")},
        "instruction": ("Review the returned overlay and scoped warnings. Resolve every topology_issues entry "
                        "with a located topology_decision (read truncated lists via their reference); include "
                        "north_arrow if orientation_submission requires it, then submit this passed trial. "
                        "Use operations only if the drawing supports a correction; do not repeat the plan or audit ledger.")}
    visible["audit_refs"] = audit_refs
    # This digest binds every original field, including decision obligations.
    # It belongs only to the projection, so the durable receipt is not recursive.
    visible["receipt_audit"] = reference(receipt, "", receipt)
    visible["report_reading"] = ("read_plan_draft(field='report:/building_precision') browses the full receipt. "
        "Large containers return small child references; append /key or /index to inspect one. "
        "Use object_id='page:8' for the next page. No rebuilding occurs.")
    return visible


def bounded_json_view(document, *, pointer="", offset=0, reference_for):
    """Browse verified JSON without returning large nested values in a page.

    The caller verifies the document and provides its own immutable references.
    ``reference_for(pointer, value)`` must return a small JSON reference. Returned
    ``next_offset`` is a child index, or a character offset for long text.
    """
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("report page offset must be a nonnegative integer")
    if not isinstance(pointer, str):
        raise ValueError("report JSON pointer must be text")
    if pointer and not pointer.startswith("/"):
        raise ValueError("report field must use a JSON pointer, e.g. report:/building_precision")
    value = document
    for raw in pointer.split("/")[1:] if pointer else []:
        if re.search(r"~(?![01])", raw):
            raise ValueError("invalid JSON pointer escape")
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, Mapping) and key in value:
            value = value[key]
        elif isinstance(value, list) and key.isdecimal() and str(int(key)) == key and int(key) < len(value):
            value = value[int(key)]
        else:
            raise ValueError("report JSON pointer does not identify a saved value")
    result = {"reference": reference_for(pointer, value)}
    if len(_bytes(value)) <= 3000 and offset == 0:
        result["value"] = copy.deepcopy(value)
    elif isinstance(value, (Mapping, list)):
        keys = list(value) if isinstance(value, Mapping) else list(range(len(value)))
        if offset >= len(keys) and offset != 0:
            raise ValueError("report page offset is beyond the saved value")
        result["entries"] = [{"key": key, "value": _preview(None, _child(pointer, key), value[key],
                                                            budget=350, reference_for=reference_for)}
                             for key in keys[offset:offset + 8]]
        result["total"] = len(keys)
        if offset + 8 < len(keys):
            result["next_offset"] = offset + 8
    elif isinstance(value, str):
        if offset >= len(value) and offset != 0:
            raise ValueError("report page offset is beyond the saved text")
        result["text"] = value[offset:offset + 600]
        if offset + 600 < len(value):
            result["next_offset"] = offset + 600
    else:
        raise ValueError("report page requires a container or text")
    return result


def read_report(receipt, pointer, *, page=None, read_trial_id=None):
    """Read only the selected in-memory receipt; never open a model-supplied path."""
    offset = 0
    if page is not None:
        if not isinstance(page, str) or not page.startswith("page:") or not page[5:].isdecimal():
            raise ValueError("report object_id must be page:<nonnegative offset>")
        offset = int(page[5:])
    target = read_trial_id or receipt.get("trial_id", "latest")

    def make_reference(path, value):
        result = reference(receipt, path, value)
        result["read"]["arguments"]["trial_id"] = target
        return result

    result = {"trial_id": receipt.get("trial_id"), "status": "reported",
              "trial_status": receipt.get("status"), **bounded_json_view(receipt, pointer=pointer,
                  offset=offset, reference_for=make_reference)}
    if "next_offset" in result:
        result["next"] = {"trial_id": target, "field": "report:" + pointer,
                          "object_id": f"page:{result.pop('next_offset')}"}
    return result
