"""Drawing-role tasks share one ledger and return immutable, verified artifacts."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import time
from contextlib import AsyncExitStack
from pathlib import Path

import jsonschema
from PIL import Image

from src.agent.runtime_context import update_building_context
from src.agent.runtime_tools import local_observer_role
from src.agent_runtime.context import StateEntry
from .context_policy import role_context_policy
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.providers import LIVE_PROVIDERS, provider_parameters
from src.agent_runtime.store import json_bytes
from src.agent_runtime.versions import make_versions
from src.harness_contracts import ToolExecutionPayload
from src.harness_contracts.roles import ToolGrant

from .accounting import role_accounting
from .artifacts import ArtifactRegistry, valid_task_id
from .coordinates import task_coordinates


def envelope(value, *, error=False):
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
            "structuredContent": value, "isError": error}


def role_parameters(config):
    if config["provider"] == "scripted":
        return {"max_tokens": config["output_tokens"], **{k: config[k] for k in
            ("reasoning_effort", "temperature", "enable_thinking") if config.get(k) is not None}}
    return provider_parameters(config["provider"], output_tokens=config["output_tokens"],
        reasoning_effort=config.get("reasoning_effort"), temperature=config.get("temperature"),
        thinking=True if config.get("enable_thinking") is None else config["enable_thinking"])


def schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


TASK_SCHEMA = schema({
    "task_id": {"type": "string"}, "role_id": {"enum": ["plan_reader", "elevation_reader"]},
    "image": {"type": "string"}, "target": {"type": "string", "minLength": 1},
    "instructions": {"type": "string", "minLength": 1},
    "origin": {"type": "string", "minLength": 1},
    "previous_task_id": {"type": "string"},
    "issues": {"type": "array", "items": {"type": "string"}},
    "rework_targets": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    "budget": schema({"model_calls": {"type": "integer", "minimum": 1},
                      "tool_calls": {"type": "integer", "minimum": 0},
                      "tokens": {"type": "integer", "minimum": 1},
                      "seconds": {"type": "number", "exclusiveMinimum": 0}}),
}, ("task_id", "role_id", "image", "target", "instructions"))

# Readers get these per-task allowances, capped by what remains of the run; tokens
# stay under the run's own total. The coordinator no longer chooses them: in the
# 10-06 sm24 debug run it guessed 100-120k tokens, while a plan reader alone used
# ~0.9M and an elevation reader up to ~0.25M, so readers stopped after two or three
# requests. Measured use: plan reader 19-30 requests, elevation reader up to 8.
ROLE_TASK_BUDGET = {
    "plan_reader": {"model_calls": 40, "tool_calls": 120, "seconds": 3600},
    "elevation_reader": {"model_calls": 16, "tool_calls": 50, "seconds": 1800},
}
COORDINATOR_TASK_SCHEMA = schema({key: value for key, value in TASK_SCHEMA["properties"].items() if key != "budget"},
                                 tuple(TASK_SCHEMA["required"]))
LEVEL_REFERENCE_SCHEMA = schema({"task_id": {"type": "string"}, "elevation_id": {"type": "string"}},
                                ("task_id", "elevation_id"))
HEIGHT_SCHEMA = schema({"match_id": {"oneOf": [{"type": "string"},
    {"type": "array", "items": {"type": "string"}, "minItems": 1}]}}, ("match_id",))

EXTRA_TOOLS = [
    {"name": "delegate_readers", "description": "Dispatch single-image readers concurrently, plans first. Give floor/facade target and a common building origin; runtime fixes x East, y North by the north arrow, z Up. Instructions cannot change directions. Rework uses a new task_id, previous_task_id and issues. Completed IDs reuse deliveries; allowances come from the role.",
     "inputSchema": schema({"tasks": {"type": "array", "items": COORDINATOR_TASK_SCHEMA, "minItems": 1, "maxItems": 32}}, ("tasks",))},
    {"name": "read_role_artifact", "description": "Read the complete immutable reader delivery after checking its hash; includes its original evidence and unresolved items.",
     "inputSchema": schema({"task_id": {"type": "string"}, "sha256": {"type": "string"}}, ("task_id",))},
    {"name": "build_from_artifact", "description": "Build a validated reader plan without retranscription. First read elevation levels: optional z_floor and ceiling_height in metres each require their *_evidence (delivered elevation task_id + elevation_id). z_floor equals its cited Z; ceiling_height equals cited top Z minus floor Z. Overrides change a compilation copy, keep evidence, and leave the reader artifact intact. Identical inputs reuse the build.",
     "inputSchema": schema({"task_id": {"type": "string"}, "sha256": {"type": "string"},
         "z_floor": {"type": "number"}, "z_floor_evidence": LEVEL_REFERENCE_SCHEMA,
         "ceiling_height": {"type": "number", "exclusiveMinimum": 0},
         "ceiling_height_evidence": LEVEL_REFERENCE_SCHEMA}, ("task_id", "sha256"))},
    {"name": "match_elevation", "description": "Match a validated elevation_reader artifact to a saved whole-building candidate. Returns matched openings, source-only/elevation-only openings and conflicts. Does not modify heights.",
     "inputSchema": schema({"task_id": {"type": "string"}, "candidate": {"type": "string"}}, ("task_id", "candidate"))},
    {"name": "apply_elevation_heights", "description": "Give match_id as one ID or a list: all safe facade heights save at most one candidate. Calls serialize on the latest usable draft; changed opening XY/hosts require a new match. Equal values only record evidence, with no new candidate. Unmatched/conflicting openings stay unresolved.",
     "inputSchema": HEIGHT_SCHEMA},
    {"name": "role_state", "description": "Read all reader task/target/status/artifact references and per-role/root usage. These references also survive context compaction.", "inputSchema": schema({})},
    {"name": "review_role_assembly", "description": "Acknowledge each reported assembly change against the accepted reader trials with its specific reason before continuing writes or delivery. Source and reader hashes must still match.",
     "inputSchema": schema({"review_id": {"type": "string"}, "decisions": {"type": "array", "items": schema({
         "change_id": {"type": "string"}, "reason": {"type": "string", "minLength": 1}}, ("change_id", "reason"))}}, ("review_id", "decisions"))},
]

# The lower-level methods remain available to offline scripts, but no longer
# occupy the coordinator's tool catalog or its model-side permission grants.
INTERNAL_TOOLS = [t for t in EXTRA_TOOLS if t["name"] in {
    "build_from_artifact", "match_elevation", "apply_elevation_heights"}]
EXTRA_TOOLS = [t for t in EXTRA_TOOLS if t not in INTERNAL_TOOLS]
EXTRA_TOOLS.insert(2, {"name": "assemble_from_readers",
    "description": "Build floors, resolve cited elevation levels, assemble, match facades and write all safe heights in one resumable call. Omit task_ids to use each floor/facade's latest accepted delivery. Returns candidate, level citations, matches and located decisions; missing/conflicting levels retain explicit plan assumptions. Repeat after reader rework or a local candidate correction. level_overrides use absolute cited floor Z and ceiling_height=top Z-floor Z. Assembly changes require review_role_assembly before further writes.",
    "inputSchema": schema({"task_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "uniqueItems": True},
        "level_overrides": {"type": "array", "items": schema({
            "floor_id": {"type": "string"}, "z_floor": {"type": "number"},
            "z_floor_evidence": LEVEL_REFERENCE_SCHEMA,
            "ceiling_height": {"type": "number", "exclusiveMinimum": 0},
            "ceiling_height_evidence": LEVEL_REFERENCE_SCHEMA}, ("floor_id",))}})})


class RoleSession:
    def __init__(self, *, store, frozen, routes, adapter_factory, limits, root,
                 max_concurrent_readers=8, started_epoch=None, reader_fault_hook=None):
        if type(max_concurrent_readers) is not int or max_concurrent_readers < 1:
            raise ValueError("max_concurrent_readers must be a positive integer")
        self.store, self.frozen, self.routes = store, frozen, routes
        self.adapter_factory, self.limits, self.root = adapter_factory, limits, Path(root)
        self.run_directory = frozen.run_directory
        self.registry = ArtifactRegistry(store)
        self.started_epoch = time.time() if started_epoch is None else started_epoch
        self.max_concurrent_readers = max_concurrent_readers
        self.slots = asyncio.Semaphore(max_concurrent_readers)
        self.write_lock = asyncio.Lock()
        self.reader_fault_hook = reader_fault_hook
        self.manifest = json.loads((self.run_directory / "inputs.json").read_bytes())
        self.schemas = {tool["name"]: tool["inputSchema"] for tool in [*EXTRA_TOOLS, *INTERNAL_TOOLS]}
        from .assembly_review import AssemblyReview
        self.assembly = AssemblyReview(self)

    async def list_tools(self):
        # Keep the ordinary toolkit unchanged. Role tools exist only in this wrapper.
        ordinary = await self.frozen.list_tools()
        return [*ordinary, *EXTRA_TOOLS]

    def repeatability(self, name):
        if name in self.schemas:
            if name == "review_role_assembly":
                return "idempotent_write"
            return "non_idempotent_write" if name in {"build_from_artifact", "apply_elevation_heights", "assemble_from_readers"} else "read_only"
        return self.frozen.repeatability(name)

    def snapshot_state(self):
        value = self.frozen.snapshot_state()
        return {"bim": value, "reader_artifacts": {key: row.get("artifact") for key, row in self.registry.records.items()
                                                 if row.get("artifact")}, "assembly_review": self.assembly.current(),
                "reader_floor_sources": self.assembly._load("role_floor_sources.json", {})}

    def artifacts(self):
        return self.frozen.artifacts()

    def image_origins(self, raw):
        return self.frozen.image_origins(raw)

    async def call_tool(self, name, arguments):
        if name not in self.schemas and self.frozen.repeatability(name) != "read_only":
            async with self.write_lock:
                return await self._call_tool(name, arguments)
        return await self._call_tool(name, arguments)

    async def _call_tool(self, name, arguments):
        try:
            if name not in self.schemas:
                if self.frozen.repeatability(name) != "read_only":
                    self.assembly.guard()
                if name == "finish_bim":
                    candidate = arguments.get("candidate")
                    if candidate:
                        self.assembly.check(candidate, require_all=True)
                        self.assembly.guard()
                result = await self.frozen.call_tool(name, arguments)
                from scripts.tool_scripts.bim_agent_saved_result import result_metadata
                meta = {**result_metadata(result), **(result.get("structuredContent") or {})}
                candidate = meta.get("candidate")
                if candidate and meta.get("source_geometry_ready"):
                    report = self.assembly.check(candidate, require_all=name == "assemble_plan_bim")
                    if report is not None:
                        result = self._with_assembly_review(result, report)
                return result
            if name == "apply_elevation_heights" and isinstance(arguments, dict):
                # The former confirm flag carried nothing beyond match_id; GLM's
                # Anthropic-compatible route sent it as the string "true" (10-06 sm24
                # debug run2), so tolerate and drop it rather than block heights.
                arguments = {key: value for key, value in arguments.items() if key != "confirm"}
            jsonschema.validate(arguments, self.schemas[name])
            if name == "delegate_readers":
                return envelope(await self.delegate_many(arguments["tasks"]))
            if name == "read_role_artifact":
                return envelope({"record": self.registry.records[arguments["task_id"]],
                                 "artifact": self.registry.read(**arguments)})
            if name == "assemble_from_readers":
                from .assembly import assemble_from_readers
                async with self.write_lock:
                    return await assemble_from_readers(self, **arguments)
            if name == "build_from_artifact":
                self.assembly.guard()
                return await self.build_from_artifact(**arguments)
            if name == "match_elevation":
                return envelope(self.match(**arguments))
            if name == "apply_elevation_heights":
                self.assembly.guard()
                return await self.apply_heights(arguments["match_id"])
            if name == "review_role_assembly":
                return envelope(self.assembly.acknowledge(**arguments))
            return envelope(self.state())
        except (ValueError, KeyError, jsonschema.ValidationError) as error:
            return envelope({"status": "rejected", "reason": str(error)}, error=True)

    def state(self):
        return {"readers": self.registry.state(), "max_concurrent_readers": self.max_concurrent_readers,
                "usage": role_accounting(self.store, self.registry), "assembly_review": self.assembly.current()}

    @staticmethod
    def _with_assembly_review(result, report):
        from scripts.tool_scripts.bim_agent_saved_result import result_metadata
        value = {**result_metadata(result), **(result.get("structuredContent") or {}), "assembly_review": report}
        return {**result, "structuredContent": value, "content": [
            {"type": "text", "text": json.dumps(value, ensure_ascii=False)},
            *[block for block in result.get("content", []) if block.get("type") != "text"]]}

    def _task(self, arguments):
        from .submission import canonical_target, parse_target
        jsonschema.validate(arguments, TASK_SCHEMA)
        arguments = {**arguments, "target": canonical_target(arguments["role_id"], arguments["target"])}
        valid_task_id(arguments["task_id"])
        image = arguments["image"]
        if Path(image).name != image or image not in self.manifest["images"]:
            raise ValueError("reader image must be one admitted original filename")
        path = self.run_directory / "images" / image
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != self.manifest["images"][image]["sha256"]:
            raise ValueError("reader original image changed since admission")
        task = {**arguments, "input_sha256": digest}
        if arguments.get("previous_task_id"):
            previous = self.registry.records[arguments["previous_task_id"]]
            if previous["image"] != image or previous["role_id"] != arguments["role_id"] or canonical_target(previous["role_id"], previous["target"]) != arguments["target"]:
                raise ValueError("rework must keep the same role, original image and target")
            if not arguments.get("issues"):
                raise ValueError("rework needs specific issues")
            if arguments["role_id"] == "plan_reader" and previous.get("artifact") and not arguments.get("rework_targets"):
                raise ValueError("plan rework needs explicit rework_targets such as plan.openings:D1; all other objects stay fixed")
            task["previous_artifact"] = previous.get("artifact")
        parse_target(arguments["role_id"], arguments["target"])
        task["coordinate_contract"] = task_coordinates(arguments)
        return task

    def _with_plan_floors(self, tasks):
        """A facade target without floors names the plan floors (10-07 run4: a bare
        "South" reader invented floor "GF", which no plan floor matched)."""
        from .submission import canonical_target
        floors = {canonical_target("plan_reader", task["target"]) for task in tasks
                  if isinstance(task, dict) and task.get("role_id") == "plan_reader" and isinstance(task.get("target"), str)}
        floors |= {row["target"] for row in self.registry.records.values()
                   if row.get("role_id") == "plan_reader" and row.get("target")}
        if not floors:
            return tasks
        result = []
        for task in tasks:
            if isinstance(task, dict) and task.get("role_id") == "elevation_reader" and isinstance(task.get("target"), str):
                target = canonical_target("elevation_reader", task["target"])
                if "/" not in target:
                    task = {**task, "target": target + "/" + ",".join(sorted(floors))}
            result.append(task)
        return result

    async def delegate_many(self, tasks):
        identities = [task["task_id"] for task in tasks]
        if len(identities) != len(set(identities)):
            raise ValueError("reader task IDs must be unique within a batch")
        # Validate every dispatch before starting any model request.
        admitted = [self._task(task) for task in self._with_plan_floors(tasks)]
        for task in admitted:
            self.registry.admit(task)

        async def one(task):
            async with self.slots:
                try:
                    return await self.run_reader(task)
                except (ValueError, KeyError) as error:
                    if self.registry.records.get(task["task_id"], {}).get("status") == "completed":
                        raise
                    return self.registry.save(task, status="failed", reason=str(error))
        ordered = sorted(admitted, key=lambda task: task["role_id"] != "plan_reader")
        results = await asyncio.gather(*(one(task) for task in ordered))
        by_id = {row["task_id"]: row for row in results}
        return {"status": "completed", "results": [by_id[identity] for identity in identities]}

    async def run_reader(self, task):
        from .readers import ReaderTools
        from .guidance import get_role_guide
        from .trial import PlanTrialSession

        child = self.registry.admit(task)
        saved = self.registry.records.get(task["task_id"])
        if saved and saved["status"] == "completed":
            self.registry.read(task["task_id"])
            return {**saved, "reused_saved_result": True}
        if saved and saved["status"] not in {"running", "interrupted"}:
            return {**saved, "reused_saved_result": True}
        deadline = self.started_epoch + self.limits.seconds
        budget = {**ROLE_TASK_BUDGET[task["role_id"]], **task.get("budget", {})}
        timing_path = child.task_directory / "reader_timing.json"
        if timing_path.is_file():
            timing = json.loads(timing_path.read_bytes())
        else:
            start = time.time()
            seconds = min(budget["seconds"], deadline - start)
            if seconds <= 0:
                return self.registry.save(task, status="failed", reason="root time budget exhausted")
            timing = {"started_epoch": start, "deadline_epoch": start + seconds, "time_budget_seconds": seconds}
            child.write_json("reader_timing.json", timing)
        allowance = {"model_calls": min(budget["model_calls"], self.limits.model_calls),
                     "tool_calls": min(budget["tool_calls"], self.limits.tool_calls),
                     "tokens": budget.get("tokens", self.limits.tokens),
                     "seconds": timing["time_budget_seconds"], "max_model_retries": self.limits.max_model_retries,
                     "retry_backoff_seconds": self.limits.retry_backoff_seconds,
                     "max_consecutive_truncations": self.limits.max_consecutive_truncations,
                     "max_total_truncations": self.limits.max_total_truncations}
        if self.limits.tokens is not None and (allowance["tokens"] is None or allowance["tokens"] > self.limits.tokens):
            allowance["tokens"] = self.limits.tokens
        limits = RunLimits(**allowance)
        self.registry.save(task, status="running")
        config = self.routes[task["role_id"]]
        config = config.model_dump(mode="json") if hasattr(config, "model_dump") else config
        guide = get_role_guide(task["role_id"])
        raw_image = (self.run_directory / "images" / task["image"]).read_bytes()
        with Image.open(io.BytesIO(raw_image)) as image:
            size = image.size
        base_role = local_observer_role(limits.ledger_limit())
        async with AsyncExitStack() as stack:
            scoped = await stack.enter_async_context(self.frozen.task_session(
                directory=child.task_directory / "bim", root=self.root, role=base_role,
                timing=timing, images={task["image"]: (raw_image, size)}))
            trial = None
            if task["role_id"] == "plan_reader":
                trial = await stack.enter_async_context(PlanTrialSession(
                    scoped.run_directory, task["image"], root=self.root))
            previous = self.registry.read(task["previous_task_id"]) if task.get("previous_artifact") else None
            if trial is not None and previous is not None:
                validation = self.registry.records[task["previous_task_id"]].get("validation") or {}
                if validation.get("source_geometry_ready") is True and validation.get("validation_passed") is True:
                    from .trial import PlanTrial, canonical_plan_sha256
                    workspace = self.registry.child(task["previous_task_id"]).task_directory / "bim/trial_workspace"
                    prior = PlanTrial(None, image_name=task["image"], workspace=workspace,
                                      receipt_directory=workspace / "trial_receipts")
                    if canonical_plan_sha256(previous["plan"]) != validation["plan_sha256"]:
                        raise ValueError("rework artifact differs from its successful trial")
                    trial.inherit_reference(prior, validation["plan_sha256"], task["rework_targets"])
                # The accepted review also covers warnings from trials made
                # after the selected successful geometry receipt.
                trial.inherited_topology_issues = validation.get("topology_issues", [])
            tools = ReaderTools(scoped, role_id=task["role_id"], image_name=task["image"], trial=trial, target=task["target"])
            catalog = await tools.list_tools()
            role = base_role.model_copy(update={"role_id": task["role_id"],
                "read_only": False, "tool_whitelist": tuple(
                ToolGrant(tool_name=tool["name"], access="read" if tools.repeatability(tool["name"]) == "read_only" else "write")
                for tool in catalog)})
            parameters = role_parameters(config)
            route = {"route_id": config["provider"], "model": config["model"]}
            specs = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                      "parameters": t["inputSchema"]}} for t in catalog]
            versions = make_versions(child, root=self.root, prompt=guide, tools=specs, parameters=parameters,
                                     route=route, code_paths=("src/agent/runtime_roles", "src/agent/runtime_tools.py"))
            content = [{"type": "text", "text": json.dumps({"task": task, "previous_artifact": previous,
                       "coordinates": "all boxes refer to original image pixels; geometric values in metres"}, ensure_ascii=False)},
                       {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw_image).decode()}}]
            def validate(text):
                submitted = tools.submission.read()
                if submitted is None:
                    name = "submit_plan_reading" if trial is not None else "submit_elevation_reading"
                    raise ValueError(f"No accepted submission. Call {name}; free text is not the reading artifact.")
                return submitted["artifact"]
            adapter = self.adapter_factory(task["task_id"], config, child)
            if hasattr(adapter, "close"):
                stack.push_async_callback(adapter.close)
            engine = Runtime(store=child, adapter=adapter, tools=tools, role=role,
                model=config["model"], parameters=parameters, versions=versions, limits=limits,
                strict_model_profile=config["provider"] in LIVE_PROVIDERS,
                root_tool_calls=self.limits.tool_calls, start_epoch=timing["started_epoch"],
                answer_validator=validate, max_answer_repairs=1,
                low_output_limit_reason=config.get("low_output_limit_reason"),
                context_policy=role_context_policy(task["role_id"]),
                request_timeout_seconds=self.limits.seconds / (self.max_concurrent_readers + 1),
                fault_hook=self.reader_fault_hook)
            original_ref = child.put_bytes(raw_image, "image/png")
            runtime = await engine.run([{"role": "system", "content": guide}, {"role": "user", "content": content}],
                image_originals={original_ref.sha256: original_ref}, resume=bool(child.events))
            submitted = tools.submission.read()
            artifact = submitted["artifact"] if submitted is not None else None
            status = "completed" if artifact is not None else "failed"
            return self.registry.save(task, status=status, artifact=artifact, runtime=runtime,
                                      validation=submitted["validation"] if submitted is not None else None,
                                      reason=runtime["status"] if artifact is None else None)

    async def _once(self, operation_id, name, arguments, *, reference):
        digest = hashlib.sha256(operation_id.encode()).hexdigest()
        path = self.store.directory / "role_operations" / (digest + ".json")
        if path.is_file():
            saved = json.loads(path.read_bytes())
            if (saved["tool"], saved["arguments"], saved["reference"]) != (name, arguments, reference):
                raise ValueError("operation identity already refers to different arguments")
            if "result" not in saved:
                raise ValueError("operation outcome unknown; cannot repeat a possible model write")
            return saved["result"]
        saved = {"operation_id": operation_id, "tool": name, "arguments": arguments, "reference": reference}
        self.store.write_json("role_operations/" + path.name, saved)
        result = await self.frozen.call_tool(name, arguments)
        # Preserve the actual expanded tool arguments as an audited blob without retransmitting a full plan.
        result = dict(result)
        metadata = dict(result.get("structuredContent") or {})
        from scripts.tool_scripts.bim_agent_saved_result import result_metadata
        metadata = {**result_metadata(result), **metadata,
                    "role_application": {"reference": reference, "expanded_parameters": self.store.put_json(saved).model_dump(mode="json")}}
        result["structuredContent"] = metadata
        result["content"] = [block for block in result.get("content", []) if block.get("type") != "text"]
        result["content"].insert(0, {"type": "text", "text": json.dumps(metadata, ensure_ascii=False)})
        self.store.write_json("role_operations/" + path.name, {**saved, "result": result})
        return result

    @staticmethod
    def _build_identity(task_id, levels):
        suffix = ":" + hashlib.sha256(json_bytes(levels)).hexdigest() if levels else ""
        return "plan:" + task_id + suffix

    async def build_from_artifact(self, task_id, sha256, **levels):
        async with self.write_lock:
            self.assembly.guard()
            return await self._build_from_artifact(task_id, sha256, **levels)

    async def _build_from_artifact(self, task_id, sha256, resolved_levels=None, **levels):
        value = self.registry.read(task_id, sha256=sha256, role_id="plan_reader")
        record = self.registry.records[task_id]
        if not record.get("validation", {}).get("validation_passed"):
            raise ValueError("plan delivery has no successful trial receipt")
        plan = value["plan"]
        receipt = record["validation"]
        if receipt.get("compiled_numeric_plan_file"):
            from .trial import canonical_plan_sha256
            if canonical_plan_sha256(plan) != receipt["plan_sha256"]:
                raise ValueError("trial receipt does not refer to this original plan")
            workspace = self.registry.child(task_id).task_directory / "bim/trial_workspace"
            path = (workspace / receipt["compiled_numeric_plan_file"]).resolve()
            if not path.is_relative_to(workspace.resolve()) or not path.is_file():
                raise ValueError("compiled reader plan is outside its trial or missing")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != receipt["compiled_numeric_plan_sha256"]:
                raise ValueError("compiled reader plan hash mismatch")
            plan = json.loads(raw)
        from .levels import apply_levels, apply_resolved_levels
        if resolved_levels is None:
            plan, citations = apply_levels(self.registry, plan, **levels)
        else:
            if levels:
                raise ValueError("choose resolved levels or explicit legacy overrides")
            plan, citations = apply_resolved_levels(plan, resolved_levels), resolved_levels
            levels = {"resolved_levels": resolved_levels}
        reference = {"task_id": task_id, "sha256": sha256}
        if citations:
            reference["levels"] = citations
        result = await self._once(self._build_identity(task_id, levels), "build_plan_bim",
            {"image": record["image"], "plan_json": json.dumps(plan, ensure_ascii=False)},
            reference=reference)
        meta = result.get("structuredContent") or {}
        if meta.get("source_geometry_ready") and meta.get("candidate"):
            self.assembly.bind(task_id)
            result = self._with_assembly_review(result, self.assembly.check(meta["candidate"]))
        return result

    def _source(self, candidate):
        if not isinstance(candidate, str) or Path(candidate).name != candidate or not candidate.startswith("candidate_"):
            raise ValueError("candidate must be a saved candidate identifier")
        path = (self.run_directory / candidate / "source_model.json").resolve()
        if not path.is_relative_to(self.run_directory.resolve()):
            raise ValueError("candidate escapes the BIM run")
        if not path.is_file():
            raise ValueError(f"saved candidate does not exist: {candidate}")
        return json.loads(path.read_bytes())

    def match(self, task_id, candidate, *, height_bounds=False):
        from .elevation import match_elevation
        from .lineage import guard_replaced_plans
        artifact = self.registry.read(task_id, role_id="elevation_reader")
        source = self._source(candidate)
        guard_replaced_plans(self, candidate)
        result = match_elevation(source, artifact, candidate=candidate)
        if height_bounds:
            # Horizontal matching alone does not prove a proposed Z fits the host.
            hosts = {row["id"]: row for row in source["boundaries"]}
            openings = {row["id"]: row for row in source["openings"]}
            safe = []
            for row in result["matches"]:
                host = hosts[openings[row["source_opening_id"]]["host_boundary_id"]]
                low, high = min(p[2] for p in host["vertices"]), max(p[2] for p in host["vertices"])
                if row["sill_m"] < low - 1e-8 or row["head_m"] > high + 1e-8:
                    result["conflicts"].append({**row, "status": "conflict", "type": "height_outside_host",
                                              "host_z_m": [low, high]})
                else:
                    safe.append(row)
            result["matches"], result["can_apply"] = safe, bool(safe)
        result.pop("match_id")  # Only the outer durable identifier is public.
        result["source_file_sha256"] = hashlib.sha256(
            (self.run_directory / candidate / "source_model.json").read_bytes()).hexdigest()
        match_id = hashlib.sha256(json_bytes({"task_id": task_id, "candidate": candidate, "result": result})).hexdigest()
        value = {"match_id": match_id, "task_id": task_id, "candidate": candidate, "result": result}
        self.store.write_json("role_matches/" + match_id + ".json", value)
        return value

    async def apply_heights(self, match_id):
        from .height_writes import apply_heights
        async with self.write_lock:
            self.assembly.guard()
            return await apply_heights(self, match_id)

    async def recover_pending(self):
        """Complete only our recoverable durable operations after a process death.

        Ordinary unknown BIM writes retain the runtime's conservative refusal.
        Reader dispatch is reconstructed from child checkpoints and immutable
        deliveries. A write can be acknowledged only from its saved receipt.
        """
        from src.agent_runtime.adapter import convert_tool_result
        completed = {event.payload.invocation_event_id for event in self.store.events
                     if event.payload.event_type == "tool_execution"}
        recovered = []
        for event in list(self.store.events):
            call = event.payload
            if call.event_type != "tool_invocation" or event.event_id in completed:
                continue
            if call.tool_name == "delegate_readers":
                raw = await self.call_tool(call.tool_name, call.full_arguments)
            elif call.tool_name == "assemble_from_readers":
                raw = await self.call_tool(call.tool_name, call.full_arguments)
                if raw.get("isError"):
                    # Unacknowledged inner writes keep their original refusal.
                    continue
            elif call.tool_name in {"build_from_artifact", "apply_elevation_heights"}:
                if call.tool_name == "build_from_artifact":
                    levels = {k: v for k, v in call.full_arguments.items() if k not in {"task_id", "sha256"}}
                    identity = self._build_identity(call.full_arguments["task_id"], levels)
                    path = self.store.directory / "role_operations" / (hashlib.sha256(identity.encode()).hexdigest() + ".json")
                    if not path.is_file() or "result" not in json.loads(path.read_bytes()):
                        continue
                    saved_result = json.loads(path.read_bytes())["result"]
                else:
                    from .height_writes import match_ids, load_match, saved_application
                    ids = sorted({load_match(self, identity)["match_id"] for identity in match_ids(call.full_arguments["match_id"])})
                    saved = saved_application(self, ids)
                    if saved is None:
                        continue
                    saved_result = saved["result"]
                # A process may die after the frozen build receipt was saved but
                # before its reader binding/comparison. Complete that read-only
                # bookkeeping from the receipt; _once will never rebuild it.
                raw = (await self._build_from_artifact(**call.full_arguments)
                       if call.tool_name == "build_from_artifact"
                       else saved_result)
            else:
                continue
            _, _, shown, _ = convert_tool_result(call.call_id, raw, self.store)
            self.store.append(ToolExecutionPayload(call_id=call.call_id, tool_name=call.tool_name,
                full_arguments=call.full_arguments, repeatability=call.repeatability,
                operation_key=call.operation_key, invocation_event_id=event.event_id,
                outcome="failed" if raw.get("isError") else "succeeded",
                applied_write_id=call.operation_key if call.repeatability != "read_only" and not raw.get("isError") else None,
                raw_result=self.store.capture(raw, force_blob=True), shown_result=self.store.capture(shown, force_blob=True),
                presentation_status="prepared"),
                source_refs=(self.store.source("tool-state-after", self.snapshot_state()),
                             self.store.source("role-operation-recovery", {"original_invocation": event.event_id,
                                 "method": "resume child checkpoints" if call.tool_name == "delegate_readers" else "read durable operation receipt"})))
            recovered.append(event.event_id)
        return recovered


def update_role_context(engine, event, raw):
    update_building_context(engine, event, raw)
    value = engine.tools.registry.state()
    previous = next((row for row in engine.context.state if row.key == "reader-artifacts"), None)
    engine.context.set_state(StateEntry(key="reader-artifacts", category="artifact_version", value=value,
        epistemic_status="computed", revision=1 if previous is None else previous.revision + 1,
        source_refs=(engine.store.source("reader-artifact-registry", value),)))
