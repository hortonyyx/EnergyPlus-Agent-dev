"""Isolated build_plan_bim trials for plan-reader deliverables."""

from __future__ import annotations

import base64
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any

from src.agent.geometry.plan_feedback import resolve_plan_lengths
from src.agent.geometry.plan_input import normalize_plan_fields, plan_error_hint
from src.agent.geometry.profile_observation_binding import resolve_plan_pixels
from .plan_review import review_changes, topology_issues


ROOT = Path(__file__).resolve().parents[3]
CORRIDOR_REVIEW_HINT = (
    "A corridor bend or continuation without a physical separator is one space. "
    "Several doors into a claimed single space are a reason to recheck the original "
    "for dividers; do not add a closing wall only to host a passage."
)


def _plan_bytes(plan: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError(f"plan cannot be encoded as canonical JSON: {error}") from error


def _canonical_plan_bytes(plan: Mapping[str, Any]) -> bytes:
    normalized, _ = normalize_plan_fields(dict(plan))
    return _plan_bytes(normalized)


def canonical_plan_sha256(plan: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_plan_bytes(plan)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(base: Path, relative: str) -> Path:
    target = (base / relative).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError as error:
        raise ValueError(f"trial receipt path escapes workspace: {relative!r}") from error
    return target


def _payload(result: object) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise ValueError("build_plan_bim returned a non-object MCP envelope")
    structured = result.get("structuredContent")
    if isinstance(structured, Mapping):
        return dict(structured)
    content = result.get("content", [])
    if isinstance(content, list):
        for block in content:
            if isinstance(block, Mapping) and block.get("type") == "text" and isinstance(block.get("text"), str):
                try:
                    decoded = json.loads(block["text"])
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, Mapping):
                    return dict(decoded)
    raise ValueError("build_plan_bim MCP envelope has no structured object result")


def _verified_report(workspace: Path | None, summary: object) -> object:
    if workspace is None or not isinstance(summary, Mapping):
        return summary
    relative, expected = summary.get("file"), summary.get("sha256")
    if not isinstance(relative, str) or not isinstance(expected, str):
        return summary
    path = _inside(workspace, relative)
    if not path.is_file() or _file_sha256(path) != expected:
        raise ValueError(f"trial report changed or is missing: {relative}")
    return json.loads(path.read_bytes())


def _corridor_review(workspace: Path | None, result: Mapping[str, Any],
                     precision: object, differences: object) -> dict[str, Any]:
    review: dict[str, Any] = {
        "status": "not_assessed",
        "source": "actual trial source, building_precision and drawing_differences",
        "corridor_space_ids": [],
        "precision_items": [],
        "drawing_difference_items": [],
        "hint": CORRIDOR_REVIEW_HINT,
    }
    candidate = result.get("candidate")
    if workspace is None or not isinstance(candidate, str):
        review["reason"] = "trial produced no saved source candidate"
        return review
    source_path = _inside(workspace, f"{candidate}/source_model.json")
    if not source_path.is_file():
        review["reason"] = "saved trial source_model.json is unavailable"
        return review
    source = json.loads(source_path.read_bytes())
    corridor_ids = sorted(
        row["id"] for row in source.get("spaces", [])
        if isinstance(row, Mapping) and row.get("role") == "corridor" and isinstance(row.get("id"), str)
    )
    review["corridor_space_ids"] = corridor_ids
    boundary_spaces = {
        row.get("id"): row.get("space_id") for row in source.get("boundaries", [])
        if isinstance(row, Mapping)
    }
    precision_items = precision.get("items", []) if isinstance(precision, Mapping) else []
    review["precision_items"] = [
        row for row in precision_items if isinstance(row, Mapping) and (
            row.get("space_id") in corridor_ids
            or any(boundary_spaces.get(identity) in corridor_ids for identity in row.get("boundary_ids", []))
        )
    ]
    difference_items = differences.get("items", []) if isinstance(differences, Mapping) else []
    suspicious_kinds = {"declared_divider_with_little_ink", "unsupported_open_separator"}
    review["drawing_difference_items"] = [
        row for row in difference_items
        if isinstance(row, Mapping) and (row.get("type", row.get("kind")) in suspicious_kinds
            or (row.get("type") == "opening_offset_from_gap" and "one continuous space" in row.get("check", "")))
    ]
    findings = []
    if len(corridor_ids) > 1:
        findings.append({
            "kind": "multiple_corridor_spaces",
            "count": len(corridor_ids),
            "meaning": "review whether the drawing contains physical separators between these spaces",
        })
    if review["precision_items"]:
        findings.append({"kind": "corridor_precision_findings", "count": len(review["precision_items"])})
    if review["drawing_difference_items"]:
        findings.append({
            "kind": "unsupported_corridor_separator_candidates",
            "count": len(review["drawing_difference_items"]),
            "meaning": "these trial drawing differences can indicate an invented cross-wall or open separator",
        })
    review["findings"] = findings
    if corridor_ids:
        review["status"] = "warning" if findings else "reported"
    else:
        review["reason"] = "no trial source space is labelled corridor; automatic corridor-specific filtering is unavailable"
    return review


class PlanTrial:
    """Run the existing compiler/check/overlay stack in a child task service.

    ``tools`` points only at the writable trial workspace. It remains private;
    the reader receives this wrapper and can call only ``trial_plan_bim``.
    """

    def __init__(self, tools, *, image_name: str, receipt_directory: Path | None = None,
                 workspace: Path | None = None, profile_directory: Path | None = None):
        if not isinstance(image_name, str) or not image_name.strip():
            raise ValueError("plan trial requires one image filename")
        self.tools = tools
        self.image_name = image_name
        self.workspace = Path(workspace).resolve() if workspace is not None else None
        self.receipt_directory = Path(receipt_directory).resolve() if receipt_directory is not None else None
        self.profile_directory = (Path(profile_directory).resolve()
                                  if profile_directory is not None else None)
        self.receipts: list[dict[str, Any]] = []
        self._memory_plans: dict[str, dict[str, Any]] = {}
        self._memory_numeric: dict[str, dict[str, Any]] = {}
        self.reference_plan = None
        self.allowed_rework_targets = None
        self.inherited_topology_issues = []
        self._memory_images: dict[str, list[dict[str, Any]]] = {}
        self._load_receipts()

    def _relative_to_workspace(self, path: Path) -> str:
        if self.workspace is None:
            return str(path)
        return path.resolve().relative_to(self.workspace).as_posix()

    def _load_receipts(self) -> None:
        if self.receipt_directory is None or not self.receipt_directory.is_dir():
            return
        for path in sorted(self.receipt_directory.glob("trial_[0-9][0-9][0-9].json")):
            receipt = json.loads(path.read_bytes())
            if not isinstance(receipt, dict) or receipt.get("receipt_file") != self._relative_to_workspace(path):
                raise ValueError(f"invalid trial receipt identity: {path}")
            input_path = _inside(self.workspace or self.receipt_directory, receipt["input_plan_file"])
            if not input_path.is_file() or _file_sha256(input_path) != receipt.get("plan_sha256"):
                raise ValueError(f"trial input plan changed: {input_path}")
            decoded = json.loads(input_path.read_bytes())
            try:
                decoded_sha256 = canonical_plan_sha256(decoded)
            except (ValueError, TypeError, KeyError):
                # A failed receipt may deliberately preserve contradictory
                # aliases that could not be normalized. Its exact bytes still
                # remain hash checked and available for repair.
                decoded_sha256 = hashlib.sha256(_plan_bytes(decoded)).hexdigest()
            if decoded_sha256 != receipt["plan_sha256"]:
                raise ValueError(f"trial input plan is not canonical/hash-consistent: {input_path}")
            numeric_file = receipt.get("compiled_numeric_plan_file")
            numeric_sha = receipt.get("compiled_numeric_plan_sha256")
            if numeric_file is not None or numeric_sha is not None:
                if not isinstance(numeric_file, str) or not isinstance(numeric_sha, str):
                    raise ValueError("trial numeric plan receipt is incomplete")
                numeric_path = _inside(self.workspace or self.receipt_directory, numeric_file)
                if not numeric_path.is_file() or _file_sha256(numeric_path) != numeric_sha:
                    raise ValueError(f"trial numeric plan changed: {numeric_path}")
                # Besides the byte hash, require the saved product to remain JSON.
                json.loads(numeric_path.read_bytes())
            for profile in receipt.get("measurement_profiles", []):
                if not isinstance(profile, Mapping):
                    raise ValueError("trial measurement profile receipt is malformed")
                profile_path = _inside(
                    self.workspace or self.receipt_directory, profile.get("file", "")
                )
                if (not profile_path.is_file()
                        or _file_sha256(profile_path) != profile.get("sha256")):
                    raise ValueError(f"trial measurement profile changed: {profile_path}")
            if receipt.get("status") == "passed":
                candidate = receipt.get("candidate")
                if not isinstance(candidate, str):
                    raise ValueError("successful trial receipt has no candidate")
                source = _inside(self.workspace or self.receipt_directory, f"{candidate}/source_model.json")
                if not source.is_file() or _file_sha256(source) != receipt.get("candidate_source_sha256"):
                    raise ValueError(f"successful trial candidate changed: {candidate!r}")
            for image in receipt.get("returned_images", []):
                image_path = _inside(self.workspace or self.receipt_directory, image["file"])
                if not image_path.is_file() or _file_sha256(image_path) != image.get("sha256"):
                    raise ValueError(f"trial feedback image changed: {image_path}")
            self.receipts.append(receipt)

    def _existing(self, plan_hash: str) -> dict[str, Any] | None:
        return next((row for row in reversed(self.receipts) if row.get("plan_sha256") == plan_hash), None)

    def _numeric_plan(self, plan: Mapping[str, Any], number: int) -> tuple[
        dict[str, Any], list[str], list[dict[str, Any]], list[dict[str, Any]],
        list[dict[str, Any]], Path | None, str,
    ]:
        """Resolve only explicit aliases, quantities and selected profile candidates."""

        normalized, aliases = normalize_plan_fields(dict(plan))
        numeric, length_bindings = resolve_plan_lengths(normalized)
        used_profiles: dict[str, tuple[bytes, str]] = {}

        image_sha256 = "numeric-plan-has-no-profile-reference"
        if self.workspace is not None:
            image_path = self.workspace / "images" / self.image_name
            if not image_path.is_file():
                raise ValueError("trial original image is missing")
            image_sha256 = _file_sha256(image_path)

        def load_profile(profile_id: str) -> dict[str, Any]:
            if self.profile_directory is None:
                raise ValueError(
                    f"{profile_id} was selected but this trial has no reader profile directory"
                )
            folder = self.profile_directory.resolve()
            path = (folder / f"{profile_id}.json").resolve()
            if path.parent != folder or not path.is_file():
                raise ValueError(
                    f"choose an existing profile_id returned by this reader: {profile_id}"
                )
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            used_profiles[profile_id] = (raw, digest)
            return {"record": json.loads(raw), "sha256": digest}

        numeric, measurement_bindings = resolve_plan_pixels(
            numeric,
            image=self.image_name,
            image_sha256=image_sha256,
            load_profile=load_profile,
        )
        numeric_bytes = _canonical_plan_bytes(numeric)
        numeric_sha256 = hashlib.sha256(numeric_bytes).hexdigest()
        numeric_path = None
        profile_records = []
        if self.receipt_directory is not None:
            self.receipt_directory.mkdir(parents=True, exist_ok=True)
            numeric_path = self.receipt_directory / f"trial_{number:03d}_numeric_plan.json"
            numeric_path.write_bytes(numeric_bytes)
            profile_folder = self.receipt_directory / f"trial_{number:03d}_profiles"
            for profile_id, (raw, digest) in sorted(used_profiles.items()):
                profile_folder.mkdir(parents=True, exist_ok=True)
                target = profile_folder / f"{profile_id}.json"
                target.write_bytes(raw)
                profile_records.append({
                    "profile_id": profile_id,
                    "file": self._relative_to_workspace(target),
                    "sha256": digest,
                })
        else:
            profile_records = [
                {"profile_id": profile_id, "file": None, "sha256": digest}
                for profile_id, (_, digest) in sorted(used_profiles.items())
            ]
        return (
            numeric,
            aliases,
            length_bindings,
            measurement_bindings,
            profile_records,
            numeric_path,
            numeric_sha256,
        )

    def _save_returned_images(self, raw: object, number: int, plan_hash: str) -> list[dict[str, Any]]:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("content"), list):
            return []
        origins = {}
        try:
            origins = self.tools.image_origins(raw)
        except (AttributeError, TypeError, ValueError):
            origins = {}
        records, memory = [], []
        for index, block in enumerate(raw["content"], 1):
            if not isinstance(block, Mapping) or block.get("type") != "image" or not isinstance(block.get("data"), str):
                continue
            try:
                data = base64.b64decode(block["data"], validate=True)
            except ValueError as error:
                raise ValueError("trial feedback image is not valid base64") from error
            digest = hashlib.sha256(data).hexdigest()
            mime = block.get("mimeType", "image/png")
            suffix = ".png" if mime == "image/png" else ".jpg"
            origin = dict(origins.get(digest, {}))
            origin.setdefault("sent_sha256", digest)
            origin.update({
                "source_image_name": self.image_name,
                "transport": "trial compiler/check feedback derived from the one admitted original and plan",
                "origin_status": "verified trial input lineage",
            })
            if self.workspace is not None:
                original = self.workspace / "images" / self.image_name
                if original.is_file():
                    origin["original_path"] = str(original)
                    origin["original_sha256"] = _file_sha256(original)
            record = {"sha256": digest, "mime_type": mime, "origin": origin}
            memory.append(dict(block))
            if self.receipt_directory is not None:
                folder = self.receipt_directory / f"trial_{number:03d}_images"
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / f"{index:02d}_{digest[:12]}{suffix}"
                if path.is_file() and path.read_bytes() != data:
                    raise ValueError(f"trial feedback image collision: {path}")
                if not path.is_file():
                    path.write_bytes(data)
                record["file"] = self._relative_to_workspace(path)
            records.append(record)
        self._memory_images[plan_hash] = memory
        return records

    def _image_content(self, receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
        result = self._memory_images.get(str(receipt.get("plan_sha256")), [])
        if result:
            return [dict(row) for row in result]
        if self.workspace is None:
            return []
        blocks = []
        for image in receipt.get("returned_images", []):
            path = _inside(self.workspace, image["file"])
            blocks.append({
                "type": "image",
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                "mimeType": image["mime_type"],
            })
        return blocks

    async def run(self, plan: dict[str, Any], *, base_plan_sha256=None, changes=None) -> dict[str, Any]:
        if not isinstance(plan, Mapping):
            raise ValueError("trial plan must be an object")
        normalization_error = None
        try:
            normalized, _ = normalize_plan_fields(dict(plan))
        except (ValueError, TypeError, KeyError) as error:
            # Keep the exact rejected object recoverable even when aliases are
            # internally contradictory. A valid alias spelling still hashes as
            # its canonical field name through ``canonical_plan_sha256``.
            normalized = dict(plan)
            normalization_error = error
        plan_bytes = _plan_bytes(normalized)
        plan_hash = hashlib.sha256(plan_bytes).hexdigest()
        existing = self._existing(plan_hash)
        if existing is not None:
            return existing
        prior = self.receipts[-1] if self.receipts else None
        previous_plan = self.load_plan(prior) if prior is not None else self.reference_plan
        change_report = []
        if previous_plan is not None:
            expected_base = prior["plan_sha256"] if prior is not None else canonical_plan_sha256(previous_plan)
            if base_plan_sha256 != expected_base:
                raise ValueError(f"rework needs base_plan_sha256={expected_base}; copy the prior trial hash and list only pointed changes")
            manifest_path = self.workspace / "inputs.json" if self.workspace else None
            image_size = (json.loads(manifest_path.read_bytes()).get("images", {}).get(self.image_name, {}).get("size")
                          if manifest_path and manifest_path.is_file() else None)
            change_report = review_changes(previous_plan, normalized, changes or [], image_size=image_size,
                                          allowed_targets=self.allowed_rework_targets)
        elif base_plan_sha256 is not None or changes:
            raise ValueError("the first trial has no earlier draft to revise")
        number = len(self.receipts) + 1
        self._memory_plans[plan_hash] = normalized
        input_plan_file = None
        if self.receipt_directory is not None:
            self.receipt_directory.mkdir(parents=True, exist_ok=True)
            input_plan_file = self.receipt_directory / f"trial_{number:03d}_plan.json"
            input_plan_file.write_bytes(plan_bytes)
        try:
            if normalization_error is not None:
                raise normalization_error
            (
                numeric_plan,
                field_aliases,
                length_bindings,
                measurement_bindings,
                measurement_profiles,
                numeric_plan_path,
                numeric_plan_sha256,
            ) = self._numeric_plan(plan, number)
        except (ValueError, TypeError, KeyError) as error:
            receipt = {
                "status": "failed",
                "plan_sha256": plan_hash,
                "original_plan_sha256": plan_hash,
                "image": self.image_name,
                "source_geometry_ready": False,
                "candidate": None,
                "draft": None,
                "compiled_plan_sha256": None,
                "input_plan_file": (self._relative_to_workspace(input_plan_file)
                                    if input_plan_file is not None else None),
                "compiled_numeric_plan_file": None,
                "compiled_numeric_plan_sha256": None,
                "field_aliases": [],
                "length_bindings": [],
                "measurement_bindings": [],
                "measurement_profiles": [],
                "drawing_differences": {
                    "status": "unavailable",
                    "reason": "numeric plan resolution failed before compilation",
                },
                "building_precision": {
                    "status": "unavailable",
                    "reason": "numeric plan resolution failed before compilation",
                },
                "overlay": None,
                "corridor_review": {
                    "status": "not_assessed",
                    "reason": "numeric plan resolution failed before compilation",
                    "hint": CORRIDOR_REVIEW_HINT,
                },
                "returned_images": [],
                "reason": f"numeric_plan_resolution: {error}",
                "repair_hint": plan_error_hint(normalized, str(error)),
                "changes": change_report,
                "base_plan_sha256": expected_base if previous_plan is not None else None,
            }
            if self.receipt_directory is not None:
                path = self.receipt_directory / f"trial_{number:03d}.json"
                receipt["receipt_file"] = self._relative_to_workspace(path)
                path.write_text(
                    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n",
                )
            self.receipts.append(receipt)
            return receipt
        self._memory_numeric[plan_hash] = numeric_plan
        raw = await self.tools.call_tool(
            "build_plan_bim",
            {"image": self.image_name, "plan_json": _canonical_plan_bytes(numeric_plan).decode("utf-8")},
        )
        try:
            result = _payload(raw)
        except ValueError as error:
            result = {"source_geometry_ready": False, "error": str(error)}
        ready = result.get("source_geometry_ready") is True
        plan_input = result.get("plan_input") if isinstance(result.get("plan_input"), Mapping) else {}
        differences = _verified_report(self.workspace, result.get("drawing_differences", {
            "status": "unavailable", "reason": "build result omitted drawing_differences"
        }))
        precision_path = None
        if self.workspace is not None and isinstance(result.get("candidate"), str):
            candidate_precision = _inside(self.workspace, f"{result['candidate']}/precision_report.json")
            if candidate_precision.is_file():
                precision_path = candidate_precision
        precision = (json.loads(precision_path.read_bytes()) if precision_path is not None
                     else result.get("building_precision", {
                         "status": "unavailable", "reason": "build result omitted building_precision"
                     }))
        receipt: dict[str, Any] = {
            "status": "passed" if ready else "failed",
            "plan_sha256": plan_hash,
            "original_plan_sha256": plan_hash,
            "image": self.image_name,
            "source_geometry_ready": ready,
            "candidate": result.get("candidate"),
            "draft": plan_input.get("plan_file"),
            "compiled_plan_sha256": plan_input.get("plan_sha256"),
            "input_plan_file": (self._relative_to_workspace(input_plan_file)
                                if input_plan_file is not None else None),
            "compiled_numeric_plan_file": (
                self._relative_to_workspace(numeric_plan_path)
                if numeric_plan_path is not None else None
            ),
            "compiled_numeric_plan_sha256": numeric_plan_sha256,
            "field_aliases": field_aliases,
            "length_bindings": length_bindings,
            "measurement_bindings": measurement_bindings,
            "measurement_profiles": measurement_profiles,
            "drawing_differences": differences,
            "building_precision": precision,
            "overlay": result.get("source_plan_views") or plan_input.get("draft_view"),
            "corridor_review": _corridor_review(self.workspace, result, precision, differences),
            "changes": change_report,
            "base_plan_sha256": expected_base if previous_plan is not None else None,
        }
        receipt["returned_images"] = self._save_returned_images(raw, number, plan_hash)
        if ready and receipt["compiled_plan_sha256"] != numeric_plan_sha256:
            ready = False
            receipt.update(
                status="failed",
                source_geometry_ready=False,
                reason=("trial compiler did not compile the exact saved numeric plan: "
                        f"expected {numeric_plan_sha256}, got {receipt['compiled_plan_sha256']}"),
            )
        if ready and self.workspace is not None and isinstance(result.get("candidate"), str):
            source = _inside(self.workspace, f"{result['candidate']}/source_model.json")
            if not source.is_file():
                ready = False
                receipt.update(status="failed", source_geometry_ready=False,
                               reason="trial claimed success but source_model.json is missing")
            else:
                receipt["candidate_source_sha256"] = _file_sha256(source)
        if not ready:
            receipt.setdefault("reason", str(result.get("error") or result.get("status") or
                                             "trial did not produce source geometry"))
            if "repair_hint" in result:
                receipt["repair_hint"] = result["repair_hint"]
        flagged_dividers = {row.get("divider") for row in topology_issues([receipt])}
        receipt["topology_dividers"] = {row["id"]: row["points"] for row in numeric_plan.get("partitions", [])
                                       if isinstance(row, Mapping) and row.get("id") and row.get("id") in flagged_dividers}
        receipt["topology_issues"] = [*self.inherited_topology_issues, *topology_issues([*self.receipts, receipt])]
        if self.receipt_directory is not None:
            path = self.receipt_directory / f"trial_{number:03d}.json"
            receipt["receipt_file"] = self._relative_to_workspace(path)
            path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.receipts.append(receipt)
        return receipt

    async def call(self, plan: dict[str, Any], **review) -> dict[str, Any]:
        receipt = await self.run(plan, **review)
        content = self._image_content(receipt)
        if receipt.get("status") == "passed":
            message = json.dumps(receipt, ensure_ascii=False)
        else:
            message = (
                f"trial_plan_bim failed: {receipt.get('reason', 'unknown')}. "
                f"Minimum correct example or repair hint: "
                f"{json.dumps(receipt.get('repair_hint', {}), ensure_ascii=False)}"
            )
        content.append({"type": "text", "text": message})
        return {
            "content": content,
            "isError": receipt.get("status") != "passed",
            "structuredContent": receipt,
        }

    def load_plan(self, receipt):
        if receipt.get("input_plan_file") and self.workspace is not None:
            path = _inside(self.workspace, receipt["input_plan_file"])
            if not path.is_file() or _file_sha256(path) != receipt["plan_sha256"]:
                raise ValueError("trial input plan hash mismatch")
            return json.loads(path.read_bytes())
        return self._memory_plans[receipt["plan_sha256"]]

    def numeric_plan(self, receipt):
        if receipt.get("compiled_numeric_plan_file") and self.workspace is not None:
            path = _inside(self.workspace, receipt["compiled_numeric_plan_file"])
            if not path.is_file() or _file_sha256(path) != receipt["compiled_numeric_plan_sha256"]:
                raise ValueError("trial numeric plan hash mismatch")
            return json.loads(path.read_bytes())
        return self._memory_numeric[receipt["plan_sha256"]]

    def verified_plan(self, plan_sha256):
        receipt = self._existing(plan_sha256)
        if receipt is None or receipt.get("status") != "passed":
            raise ValueError("submit_plan_reading requires the plan_sha256 of a successful isolated trial")
        if self.workspace is not None:
            saved = _inside(self.workspace, receipt["receipt_file"])
            if json.loads(saved.read_bytes()) != receipt:
                raise ValueError("trial receipt changed since validation")
            source = _inside(self.workspace, f"{receipt['candidate']}/source_model.json")
            if not source.is_file() or _file_sha256(source) != receipt["candidate_source_sha256"]:
                raise ValueError("successful trial source hash mismatch")
            manifest = json.loads((self.workspace / "inputs.json").read_bytes())
            if _file_sha256(self.workspace / "images" / self.image_name) != manifest["images"][self.image_name]["sha256"]:
                raise ValueError("trial original image changed")
        plan = self.load_plan(receipt)
        if canonical_plan_sha256(plan) != plan_sha256:
            raise ValueError("submitted plan hash mismatch")
        self.numeric_plan(receipt)
        return plan, {"validation_passed": True, **receipt}

    def require_success(self, plan: Mapping[str, Any]) -> dict[str, Any]:
        plan_hash = canonical_plan_sha256(plan)
        receipt = self._existing(plan_hash)
        if receipt is not None and receipt.get("status") == "passed":
            return receipt
        if receipt is not None:
            raise ValueError(
                f"plan {plan_hash} has no successful isolated trial; latest failure: {receipt.get('reason', 'unknown')}"
            )
        raise ValueError(f"plan {plan_hash} has not been run through trial_plan_bim")

    def delivery_receipt(self, plan: Mapping[str, Any]) -> dict[str, Any]:
        """Return the same-plan trial outcome for artifact registration.

        Failed trials remain readable/reworkable artifacts, but the explicit
        ``validation_passed`` flag lets build_from_artifact reject them without
        discarding the reader's plan or concrete compiler reason.
        """

        plan_hash = canonical_plan_sha256(plan)
        receipt = self._existing(plan_hash)
        if receipt is None:
            raise ValueError(f"plan {plan_hash} has not been run through trial_plan_bim")
        return {"validation_passed": receipt.get("status") == "passed", **receipt}

    def durable_snapshot(self) -> dict[str, Any]:
        """Hash stable trial receipts and products; omit clocks and live process state."""

        rows = []
        for receipt in self.receipts:
            row = {
                "plan_sha256": receipt.get("plan_sha256"),
                "status": receipt.get("status"),
                "candidate": receipt.get("candidate"),
                "candidate_source_sha256": receipt.get("candidate_source_sha256"),
                "compiled_plan_sha256": receipt.get("compiled_plan_sha256"),
                "compiled_numeric_plan_sha256": receipt.get("compiled_numeric_plan_sha256"),
                "measurement_profile_sha256": [
                    profile.get("sha256") for profile in receipt.get("measurement_profiles", [])
                ],
                "returned_image_sha256": [image.get("sha256") for image in receipt.get("returned_images", [])],
            }
            if self.workspace is not None and isinstance(receipt.get("receipt_file"), str):
                path = _inside(self.workspace, receipt["receipt_file"])
                row["receipt_sha256"] = _file_sha256(path)
            rows.append(row)
        canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {
            "image": self.image_name,
            "receipts": rows,
            "snapshot_sha256": hashlib.sha256(canonical).hexdigest(),
        }

    def artifacts(self) -> list[Path]:
        """Return the small durable set needed to inspect/recover trial decisions."""

        if self.workspace is None:
            return []
        paths = []
        for fixed in (self.workspace / "inputs.json", self.workspace / "images" / self.image_name):
            if fixed.is_file():
                paths.append(fixed)
        for receipt in self.receipts:
            for key in ("receipt_file", "input_plan_file", "compiled_numeric_plan_file"):
                if isinstance(receipt.get(key), str):
                    path = _inside(self.workspace, receipt[key])
                    if path.is_file():
                        paths.append(path)
            candidate = receipt.get("candidate")
            if isinstance(candidate, str):
                for name in ("source_model.json", "precision_report.json"):
                    path = _inside(self.workspace, f"{candidate}/{name}")
                    if path.is_file():
                        paths.append(path)
            for image in receipt.get("returned_images", []):
                if isinstance(image.get("file"), str):
                    path = _inside(self.workspace, image["file"])
                    if path.is_file():
                        paths.append(path)
            for profile in receipt.get("measurement_profiles", []):
                if isinstance(profile, Mapping) and isinstance(profile.get("file"), str):
                    path = _inside(self.workspace, profile["file"])
                    if path.is_file():
                        paths.append(path)
        return sorted(set(paths))

    def image_origins(self, raw_result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        """Recover persisted lineage for trial images returned to the reader model."""

        if not isinstance(raw_result, Mapping):
            raise TypeError("raw_result must be an MCP envelope")
        structured = raw_result.get("structuredContent")
        if not isinstance(structured, Mapping):
            return {}
        result = {}
        for image in structured.get("returned_images", []):
            if isinstance(image, Mapping) and isinstance(image.get("sha256"), str):
                result[image["sha256"]] = dict(image.get("origin", {}))
        return result


class PlanTrialSession:
    """Prepare one-image writable trial state and hide it behind :class:`PlanTrial`."""

    def __init__(self, reader_run: Path, image_name: str, root: Path = ROOT):
        self.reader_run = Path(reader_run).resolve()
        self.image_name = image_name
        self.root = Path(root).resolve()
        self.workspace = self.reader_run / "trial_workspace"
        self._client_context = None
        self._client = None
        self.trial: PlanTrial | None = None

    def _prepare(self) -> None:
        manifest_path = self.reader_run / "inputs.json"
        if not manifest_path.is_file():
            raise ValueError("reader run has no inputs.json")
        parent = json.loads(manifest_path.read_bytes())
        images = parent.get("images", {})
        if self.image_name not in images or len(images) != 1:
            raise ValueError("plan trial requires the reader's one admitted original image")
        source = self.reader_run / "images" / self.image_name
        expected = images[self.image_name].get("sha256")
        if not source.is_file() or _file_sha256(source) != expected:
            raise ValueError("reader original image is missing or changed")
        (self.workspace / "images").mkdir(parents=True, exist_ok=True)
        target = self.workspace / "images" / self.image_name
        if target.is_file() and _file_sha256(target) != expected:
            raise ValueError("trial original image changed on resume")
        if not target.is_file():
            shutil.copyfile(source, target)
        trial_manifest = {
            "images": {self.image_name: images[self.image_name]},
            "image_kind": parent.get("image_kind", "drawings"),
            "input_mode": "role_plan_trial",
            "scope": "one plan-reader image; no parent building draft",
            "floor_plan_images": [self.image_name],
            "floor_scope_source": "plan_reader_single_image",
            "max_candidates": 24,
        }
        for key in ("started_epoch", "deadline_epoch", "time_budget_seconds"):
            if key in parent:
                trial_manifest[key] = parent[key]
        target_manifest = self.workspace / "inputs.json"
        if target_manifest.is_file() and json.loads(target_manifest.read_bytes()) != trial_manifest:
            raise ValueError("trial inputs or timing changed on resume")
        if not target_manifest.is_file():
            target_manifest.write_text(
                json.dumps(trial_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
            )

    async def __aenter__(self) -> PlanTrial:
        from src.agent.runtime_tools import FrozenBimTools, coordinator_role, frozen_bim_client
        from src.harness_contracts.budget import BudgetAmounts

        self._prepare()
        self._client_context = frozen_bim_client(
            self.workspace, readonly=False, repository_root=self.root
        )
        self._client = await self._client_context.__aenter__()
        try:
            tools = FrozenBimTools(
                self._client,
                coordinator_role(BudgetAmounts(calls=64)),
                run_directory=self.workspace,
            )
            self.trial = PlanTrial(
                tools,
                image_name=self.image_name,
                receipt_directory=self.workspace / "trial_receipts",
                workspace=self.workspace,
                profile_directory=self.reader_run / "pixel_profiles",
            )
            return self.trial
        except Exception:
            await self._client_context.__aexit__(*sys.exc_info())
            raise

    async def __aexit__(self, exc_type, exc, traceback):
        if self._client_context is not None:
            return await self._client_context.__aexit__(exc_type, exc, traceback)
        return False
