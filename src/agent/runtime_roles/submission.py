"""Explicit reader submission tools and their small durable delivery receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
from PIL import Image

from .plan_review import box, opening_hosts, topology_issues, validate_topology, validate_wall_reference


def obj(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1}
NUMBER = {"type": "number"}
BOX = {"type": "array", "items": NUMBER, "minItems": 4, "maxItems": 4}
PAIR = {"type": "array", "items": NUMBER, "minItems": 2, "maxItems": 2}
STRINGS = {"type": "array", "items": TEXT}
EVIDENCE_TYPE = {"enum": ["annotation", "pixels", "annotation_and_pixels", "visual_estimate", "assumption", "declared"]}
WALL_LINE_SCHEMA = obj({"convention": {"enum": ["centerline", "inner_face", "outer_face", "explicit_face"]},
                        "dimension_basis": TEXT, "basis": TEXT, "bbox": BOX},
                       ("convention", "dimension_basis", "basis", "bbox"))
WALL_REFERENCE_EXAMPLE = {
    "perimeter": {"convention": "outer_face", "dimension_basis": "outer_face",
                  "basis": "overall dimensions end on the observed outer faces", "bbox": [0, 0, 10, 10]},
    "partitions": {"convention": "centerline", "dimension_basis": "centerline",
                   "basis": "internal dimension anchors converted to observed divider midplanes", "bbox": [0, 0, 10, 10]},
}
OPERATION_SCHEMA = {"oneOf": [
    obj({"op": {"const": op}, "reason": TEXT, "source_refs": {**STRINGS, "minItems": 1}, "bbox": BOX, **fields},
        ("op", "reason", "source_refs", "bbox", *fields))
    for op, fields in {
        "update": {"collection": {"enum": ["partitions", "openings", "space_seeds"]}, "id": TEXT,
                   "changes": {"type": "object", "minProperties": 1}},
        "add": {"collection": {"enum": ["partitions", "openings", "space_seeds"]}, "value": {"type": "object"}},
        "remove": {"collection": {"enum": ["partitions", "openings", "space_seeds"]}, "id": TEXT},
        "set": {"field": TEXT, "value": {}},
    }.items()
]}
PLAN_SCHEMA = obj({
    "plan_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "evidence": {"type": "array", "items": obj({"item": TEXT, "source": TEXT, "bbox": BOX, "basis": TEXT},
                                                   ("item", "source", "bbox"))},
    "unresolved": STRINGS,
    "north_arrow": obj({"bbox": BOX, "basis": TEXT,
        "world_north_toward": {"enum": ["image_top", "image_bottom"]},
        "world_east_toward": {"enum": ["image_left", "image_right"]}},
        ("bbox", "basis", "world_north_toward", "world_east_toward")),
    "wall_reference": obj({"perimeter": WALL_LINE_SCHEMA, "partitions": WALL_LINE_SCHEMA},
                          ("perimeter", "partitions")),
    "topology_decisions": {"type": "array", "items": obj({"issue_id": TEXT,
        "decision": {"enum": ["retain_opening", "continuous_space"]}, "basis": TEXT, "bbox": BOX},
        ("issue_id", "decision", "basis", "bbox"))},
}, ("plan_sha256", "evidence", "unresolved", "wall_reference", "topology_decisions"))

ELEVATION_SCHEMA = obj({
    "orientation": {"enum": ["North", "South", "East", "West"]},
    "view_direction": {"enum": ["North", "South", "East", "West"]},
    "x_calibration": obj({"pixel_start": NUMBER, "pixel_end": NUMBER, "world_start_m": NUMBER,
                          "world_end_m": NUMBER, "world_axis": {"enum": ["x", "y"]}},
                         ("pixel_start", "pixel_end", "world_start_m", "world_end_m")),
    "elevations": {"type": "array", "items": obj({"id": TEXT,
        "kind": {"enum": ["ground", "floor", "eave", "roof", "other"]}, "value_m": NUMBER,
        "floor_id": TEXT, "evidence_type": EVIDENCE_TYPE, "bbox": BOX},
        ("id", "kind", "value_m", "evidence_type", "bbox"))},
    "openings": {"type": "array", "items": obj({"id": TEXT, "floor_id": TEXT,
        "kind": {"enum": ["window", "door"]}, "x_px": PAIR, "width_m": NUMBER,
        "sill_m": NUMBER, "head_m": NUMBER, "evidence_type": EVIDENCE_TYPE, "bbox": BOX},
        ("id", "floor_id", "kind", "x_px", "width_m", "sill_m", "head_m", "evidence_type", "bbox"))},
    "counts": {"type": "array", "items": obj({"floor_id": TEXT,
        "window_count": {"type": "integer", "minimum": 0}, "door_count": {"type": "integer", "minimum": 0}},
        ("floor_id", "window_count", "door_count"))},
    "unresolved": STRINGS,
}, ("orientation", "view_direction", "x_calibration", "elevations", "openings", "counts", "unresolved"))

SUBMISSION_TOOLS = {
    "plan_reader": {"name": "submit_plan_reading",
        "description": "Submit the successful trial by plan_sha256 with located evidence and separate wall references. No topology warnings: topology_decisions=[]. Mirrored axes require north_arrow with the original arrow bbox, basis and both reported directions. Normal orientation needs no extra field.",
        "inputSchema": PLAN_SCHEMA},
    "elevation_reader": {"name": "submit_elevation_reading",
        "description": "Submit this one facade's structured readings. Values are metres and boxes are original pixels. The tool checks fields, counts, ordering and evidence; fix pointed errors and resubmit within the task budget.",
        "inputSchema": ELEVATION_SCHEMA},
}


def parse_target(role_id, target):
    if target is None:
        return None, set()
    if not isinstance(target, str) or not target.strip():
        raise ValueError("reader target must be a nonempty floor ID or facade[/floor IDs]")
    if role_id == "plan_reader":
        return target.strip(), set()
    parts = target.split("/", 1)
    facade = parts[0].strip().title()
    if facade not in {"North", "South", "East", "West"}:
        raise ValueError("elevation target must be North, South, East or West, optionally /F1 or /F1,F2")
    floors = {part.strip() for part in parts[1].split(",")} if len(parts) == 2 else set()
    if "" in floors:
        raise ValueError("elevation target floor IDs cannot be empty")
    return facade, floors


def _bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode()


class ReaderSubmission:
    def __init__(self, *, role_id, image_name, directory=None, trial=None, target=None):
        self.role_id, self.image_name, self.trial, self.target = role_id, image_name, trial, target
        self.target_identity, self.target_floors = parse_target(role_id, target)
        self.directory = Path(directory) if directory is not None else None
        self.path = self.directory / "reader_submission.json" if self.directory is not None else None
        self.value = None
        self.image_size = None
        if self.directory and (self.directory / "images" / image_name).is_file():
            with Image.open(self.directory / "images" / image_name) as image:
                self.image_size = image.size
        if self.path and self.path.is_file():
            self.value = json.loads(self.path.read_bytes())
            self.read()

    def read(self):
        if self.path and self.path.is_file():
            saved = json.loads(self.path.read_bytes())
            if self.value is not None and saved != self.value:
                raise ValueError("reader submission changed after acceptance")
            self.value = saved
        if self.value is None:
            return None
        value = self.value
        if value["role_id"] != self.role_id or value["image"] != self.image_name or value.get("target") != self.target:
            raise ValueError("reader submission scope changed")
        if hashlib.sha256(_bytes(value["artifact"])).hexdigest() != value["artifact_sha256"]:
            raise ValueError("reader submission artifact hash mismatch")
        if self.trial is not None:
            plan, receipt = self.trial.verified_plan(value["validation"]["plan_sha256"])
            if plan != value["artifact"]["plan"] or receipt["candidate_source_sha256"] != value["validation"]["candidate_source_sha256"]:
                raise ValueError("reader submission does not match its immutable successful trial")
        return value

    def submit(self, arguments):
        try:
            return self._submit(arguments)
        except (ValueError, KeyError, TypeError) as error:
            if "Minimum correct example" in str(error):
                raise ValueError(str(error)) from error
            from .guidance import ELEVATION_EXAMPLE
            example = ELEVATION_EXAMPLE if self.role_id == "elevation_reader" else {
                "plan_sha256": "copy the passed trial plan_sha256",
                "evidence": [{"item": "plan.x_anchors", "source": self.image_name,
                              "bbox": [0, 0, 10, 10], "basis": "printed dimension chain"}],
                "unresolved": [], "wall_reference": WALL_REFERENCE_EXAMPLE,
                "topology_decisions": []}
            suffix = (" Cover every declared object in evidence and every trial topology issue in topology_decisions."
                      if self.role_id == "plan_reader" else "")
            raise ValueError(f"{SUBMISSION_TOOLS[self.role_id]['name']}: {error}. Minimum correct example: "
                             + json.dumps(example, separators=(",", ":")) + suffix) from error

    def _submit(self, arguments):
        from .readers import validate_plan_artifact
        from .elevation import validate_elevation_artifact
        from .guidance import ELEVATION_EXAMPLE

        tool = SUBMISSION_TOOLS[self.role_id]
        try:
            jsonschema.validate(arguments, tool["inputSchema"])
        except jsonschema.ValidationError as error:
            path = ".".join(str(part) for part in error.absolute_path) or "arguments"
            example = ELEVATION_EXAMPLE if self.role_id == "elevation_reader" else {
                "plan_sha256": "copy the successful trial hash", "evidence": [], "unresolved": [],
                "wall_reference": WALL_REFERENCE_EXAMPLE,
                "topology_decisions": []}
            raise ValueError(f"{tool['name']}.{path}: {error.message}. Minimum correct example: "
                             + json.dumps(example, separators=(",", ":"))) from error
        if self.role_id == "plan_reader":
            from .coordinates import validate_north_arrow
            plan, validation = self.trial.verified_plan(arguments["plan_sha256"])
            if self.target_identity is not None and plan.get("floor_id") != self.target_identity:
                raise ValueError(f"plan.floor_id must match task.target {self.target_identity}")
            artifact = validate_plan_artifact({"plan": plan, "evidence": arguments["evidence"],
                                               "unresolved": plan["unresolved"]}, image_name=self.image_name)
            # The delivery never edits the plan, including assumptions/unresolved.
            artifact["plan"] = plan
            artifact["unresolved"] = list(dict.fromkeys([*plan["unresolved"], *arguments["unresolved"]]))
            issues = list({row["issue_id"]: row for row in [*self.trial.inherited_topology_issues,
                           *topology_issues(self.trial.receipts)]}.values())
            validation = {**validation, "validation_passed": True,
                "wall_reference": validate_wall_reference(arguments["wall_reference"], image_size=self.image_size),
                "opening_hosts": opening_hosts(self.trial.numeric_plan(validation)),
                "topology_issues": issues,
                "topology_decisions": validate_topology(issues, arguments["topology_decisions"],
                                                       self.trial.numeric_plan(validation), image_size=self.image_size)}
            north_arrow = validate_north_arrow(self.trial.numeric_plan(validation), arguments.get("north_arrow"),
                                               image_size=self.image_size)
            if north_arrow is not None:
                validation["north_arrow"] = north_arrow
            boxes = [row["bbox"] for row in artifact["evidence"]]
        else:
            try:
                artifact = validate_elevation_artifact(arguments, image_name=self.image_name)
            except ValueError as error:
                raise ValueError(f"{error}. Minimum correct example: " + json.dumps(ELEVATION_EXAMPLE, separators=(",", ":"))) from error
            validation = {"validation_passed": True}
            boxes = [row["bbox"] for row in artifact["elevations"] + artifact["openings"]]
            if self.target_identity is not None and artifact["orientation"] != self.target_identity:
                raise ValueError(f"orientation must match task.target {self.target_identity}")
            floors = {row["floor_id"] for key in ("openings", "elevations", "counts")
                      for row in artifact[key] if row.get("floor_id") is not None}
            if self.target_floors and (not floors <= self.target_floors or
                    {row["floor_id"] for row in artifact["counts"]} != self.target_floors):
                raise ValueError(f"floor_id/counts must cover exactly task.target floors {sorted(self.target_floors)}")
        for evidence_box in boxes:
            box(evidence_box, self.image_size)
        value = {"role_id": self.role_id, "image": self.image_name, "target": self.target, "artifact": artifact,
                 "artifact_sha256": hashlib.sha256(_bytes(artifact)).hexdigest(), "validation": validation}
        previous = self.read()
        if previous is not None and previous != value:
            raise ValueError("this task already has an accepted submission; rework uses a new task_id")
        if previous is None and self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_bytes(_bytes(value))
            temporary.replace(self.path)
        self.value = value
        return {"status": "accepted", "artifact_sha256": value["artifact_sha256"],
                "plan_sha256": validation.get("plan_sha256"), "unresolved": artifact["unresolved"],
                "next_action": "Submission saved. End your turn with a short acknowledgement; do not repeat the artifact."}

    def snapshot(self):
        value = self.read()
        return None if value is None else {"artifact_sha256": value["artifact_sha256"],
            "receipt_sha256": hashlib.sha256(_bytes(value)).hexdigest()}
