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
from src.agent_runtime.context import ContextPolicy, StateEntry
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.providers import LIVE_PROVIDERS, provider_parameters
from src.agent_runtime.store import json_bytes
from src.agent_runtime.versions import make_versions
from src.harness_contracts import ToolExecutionPayload
from src.harness_contracts.roles import ToolGrant

from .accounting import role_accounting
from .artifacts import ArtifactRegistry, valid_task_id


def envelope(value, *, error=False):
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
            "structuredContent": value, "isError": error}


def role_parameters(config):
    if config["provider"] == "scripted":
        return {"max_tokens": config["output_tokens"], "reasoning_effort": config["reasoning_effort"]}
    return provider_parameters(config["provider"], output_tokens=config["output_tokens"],
        reasoning_effort=config["reasoning_effort"])


def schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


TASK_SCHEMA = schema({
    "task_id": {"type": "string"}, "role_id": {"enum": ["plan_reader", "elevation_reader"]},
    "image": {"type": "string"}, "target": {"type": "string", "minLength": 1},
    "instructions": {"type": "string", "minLength": 1},
    "previous_task_id": {"type": "string"},
    "issues": {"type": "array", "items": {"type": "string"}},
    "budget": schema({"model_calls": {"type": "integer", "minimum": 1},
                      "tool_calls": {"type": "integer", "minimum": 0},
                      "tokens": {"type": "integer", "minimum": 1},
                      "seconds": {"type": "number", "exclusiveMinimum": 0}}),
}, ("task_id", "role_id", "image", "target", "instructions"))

EXTRA_TOOLS = [
    {"name": "delegate_readers", "description": "Dispatch independent single-image plan/elevation readers concurrently. Use a new task_id plus previous_task_id and issues for rework. Completed task IDs return their saved artifacts without another request. Specify floor origin/directions/scale or facade orientation/viewing direction in instructions.",
     "inputSchema": schema({"tasks": {"type": "array", "items": TASK_SCHEMA, "minItems": 1, "maxItems": 32}}, ("tasks",))},
    {"name": "read_role_artifact", "description": "Read the complete immutable reader delivery after checking its hash; includes its original evidence and unresolved items.",
     "inputSchema": schema({"task_id": {"type": "string"}, "sha256": {"type": "string"}}, ("task_id",))},
    {"name": "build_from_artifact", "description": "Build a floor directly from a validated plan_reader artifact. No retranscription or overrides. Repeated identical references return the existing build; rework needs a new reader task.",
     "inputSchema": schema({"task_id": {"type": "string"}, "sha256": {"type": "string"}}, ("task_id", "sha256"))},
    {"name": "match_elevation", "description": "Match a validated elevation_reader artifact to a saved whole-building candidate. Returns matched openings, source-only/elevation-only openings and conflicts. Does not modify heights.",
     "inputSchema": schema({"task_id": {"type": "string"}, "candidate": {"type": "string"}}, ("task_id", "candidate"))},
    {"name": "apply_elevation_heights", "description": "Confirm a saved match and apply safe matched heights with their image evidence. The source hash must still match. Unmatched or conflicting openings remain unresolved. Repeated match IDs cannot modify twice.",
     "inputSchema": schema({"match_id": {"type": "string"}, "confirm": {"const": True}}, ("match_id", "confirm"))},
    {"name": "role_state", "description": "Read all reader task/target/status/artifact references and per-role/root usage. These references also survive context compaction.", "inputSchema": schema({})},
]


class RoleSession:
    def __init__(self, *, store, frozen, routes, adapter_factory, limits, root,
                 max_concurrent_readers=4, started_epoch=None, reader_fault_hook=None):
        if type(max_concurrent_readers) is not int or max_concurrent_readers < 1:
            raise ValueError("max_concurrent_readers must be a positive integer")
        self.store, self.frozen, self.routes = store, frozen, routes
        self.adapter_factory, self.limits, self.root = adapter_factory, limits, Path(root)
        self.run_directory = frozen.run_directory
        self.registry = ArtifactRegistry(store)
        self.started_epoch = time.time() if started_epoch is None else started_epoch
        self.max_concurrent_readers = max_concurrent_readers
        self.slots = asyncio.Semaphore(max_concurrent_readers)
        self.reader_fault_hook = reader_fault_hook
        self.manifest = json.loads((self.run_directory / "inputs.json").read_bytes())
        self.schemas = {tool["name"]: tool["inputSchema"] for tool in EXTRA_TOOLS}

    async def list_tools(self):
        # Keep the ordinary toolkit unchanged. Role tools exist only in this wrapper.
        ordinary = await self.frozen.list_tools()
        return [*ordinary, *EXTRA_TOOLS]

    def repeatability(self, name):
        if name in self.schemas:
            return "non_idempotent_write" if name in {"build_from_artifact", "apply_elevation_heights"} else "read_only"
        return self.frozen.repeatability(name)

    def snapshot_state(self):
        value = self.frozen.snapshot_state()
        return {"bim": value, "reader_artifacts": {key: row.get("artifact") for key, row in self.registry.records.items()
                                                 if row.get("artifact")}}

    def artifacts(self):
        return self.frozen.artifacts()

    def image_origins(self, raw):
        return self.frozen.image_origins(raw)

    async def call_tool(self, name, arguments):
        if name not in self.schemas:
            return await self.frozen.call_tool(name, arguments)
        try:
            jsonschema.validate(arguments, self.schemas[name])
            if name == "delegate_readers":
                return envelope(await self.delegate_many(arguments["tasks"]))
            if name == "read_role_artifact":
                return envelope({"record": self.registry.records[arguments["task_id"]],
                                 "artifact": self.registry.read(**arguments)})
            if name == "build_from_artifact":
                return await self.build_from_artifact(**arguments)
            if name == "match_elevation":
                return envelope(self.match(**arguments))
            if name == "apply_elevation_heights":
                return await self.apply_heights(arguments["match_id"])
            return envelope(self.state())
        except (ValueError, KeyError, jsonschema.ValidationError) as error:
            return envelope({"status": "rejected", "reason": str(error)}, error=True)

    def state(self):
        return {"readers": self.registry.state(), "max_concurrent_readers": self.max_concurrent_readers,
                "usage": role_accounting(self.store, self.registry)}

    def _task(self, arguments):
        jsonschema.validate(arguments, TASK_SCHEMA)
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
            if previous["image"] != image or previous["role_id"] != arguments["role_id"] or previous["target"] != arguments["target"]:
                raise ValueError("rework must keep the same role, original image and target")
            if not arguments.get("issues"):
                raise ValueError("rework needs specific issues")
            task["previous_artifact"] = previous.get("artifact")
        return task

    async def delegate_many(self, tasks):
        identities = [task["task_id"] for task in tasks]
        if len(identities) != len(set(identities)):
            raise ValueError("reader task IDs must be unique within a batch")
        # Validate every dispatch before starting any model request.
        admitted = [self._task(task) for task in tasks]
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
        return {"status": "completed", "results": await asyncio.gather(*(one(task) for task in admitted))}

    async def run_reader(self, task):
        from .readers import ReaderTools, validate_plan_artifact
        from .guidance import get_role_guide, ELEVATION_EXAMPLE
        from .elevation import validate_elevation_artifact
        from .trial import PlanTrialSession

        child = self.registry.admit(task)
        saved = self.registry.records.get(task["task_id"])
        if saved and saved["status"] == "completed":
            self.registry.read(task["task_id"])
            return {**saved, "reused_saved_result": True}
        if saved and saved["status"] not in {"running", "interrupted"}:
            return {**saved, "reused_saved_result": True}
        deadline = self.started_epoch + self.limits.seconds
        timing_path = child.task_directory / "reader_timing.json"
        if timing_path.is_file():
            timing = json.loads(timing_path.read_bytes())
        else:
            start = time.time()
            seconds = min(task.get("budget", {}).get("seconds", self.limits.seconds), deadline - start)
            if seconds <= 0:
                return self.registry.save(task, status="failed", reason="root time budget exhausted")
            timing = {"started_epoch": start, "deadline_epoch": start + seconds, "time_budget_seconds": seconds}
            child.write_json("reader_timing.json", timing)
        allowance = {"model_calls": min(task.get("budget", {}).get("model_calls", self.limits.model_calls), self.limits.model_calls),
                     "tool_calls": min(task.get("budget", {}).get("tool_calls", self.limits.tool_calls), self.limits.tool_calls),
                     "tokens": task.get("budget", {}).get("tokens", self.limits.tokens),
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
            tools = ReaderTools(scoped, role_id=task["role_id"], image_name=task["image"], trial=trial)
            catalog = await tools.list_tools()
            role = base_role.model_copy(update={"role_id": task["role_id"],
                "read_only": task["role_id"] != "plan_reader", "tool_whitelist": tuple(
                ToolGrant(tool_name=tool["name"], access="read" if tools.repeatability(tool["name"]) == "read_only" else "write")
                for tool in catalog)})
            parameters = role_parameters(config)
            route = {"route_id": config["provider"], "model": config["model"]}
            specs = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                      "parameters": t["inputSchema"]}} for t in catalog]
            versions = make_versions(child, root=self.root, prompt=guide, tools=specs, parameters=parameters,
                                     route=route, code_paths=("src/agent/runtime_roles", "src/agent/runtime_tools.py"))
            previous = self.registry.read(task["previous_task_id"]) if task.get("previous_artifact") else None
            content = [{"type": "text", "text": json.dumps({"task": task, "previous_artifact": previous,
                       "coordinates": "all boxes refer to original image pixels; geometric values in metres"}, ensure_ascii=False)},
                       {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw_image).decode()}}]
            def validate(text):
                value = json.loads(text)
                if task["role_id"] == "plan_reader":
                    result = validate_plan_artifact(value, image_name=task["image"])
                    trial.delivery_receipt(result["plan"])
                    boxes = [row["bbox"] for row in result["evidence"]]
                else:
                    try:
                        result = validate_elevation_artifact(value, image_name=task["image"])
                    except ValueError as error:
                        raise ValueError(f"{error}. Minimum correct example: "
                            + json.dumps(ELEVATION_EXAMPLE, ensure_ascii=False, separators=(",", ":"))) from error
                    boxes = [row["bbox"] for row in result["elevations"] + result["openings"]]
                for index, box in enumerate(boxes):
                    if box[2] > size[0] or box[3] > size[1]:
                        raise ValueError(f"evidence bbox[{index}] exceeds original image {size}; "
                                         "minimum correct example: [0,0,10,10]")
                return result
            adapter = self.adapter_factory(task["task_id"], config, child)
            if hasattr(adapter, "close"):
                stack.push_async_callback(adapter.close)
            engine = Runtime(store=child, adapter=adapter, tools=tools, role=role,
                model=config["model"], parameters=parameters, versions=versions, limits=limits,
                strict_model_profile=config["provider"] in LIVE_PROVIDERS,
                root_tool_calls=self.limits.tool_calls, start_epoch=timing["started_epoch"],
                answer_validator=validate, max_answer_repairs=1,
                low_output_limit_reason=config.get("low_output_limit_reason"),
                context_policy=ContextPolicy(compact_at_tokens=100_000),
                request_timeout_seconds=self.limits.seconds / (self.max_concurrent_readers + 1),
                fault_hook=self.reader_fault_hook)
            original_ref = child.put_bytes(raw_image, "image/png")
            runtime = await engine.run([{"role": "system", "content": guide}, {"role": "user", "content": content}],
                image_originals={original_ref.sha256: original_ref}, resume=bool(child.events))
            artifact = validate(runtime["answer"]) if runtime["status"] == "completed" else None
            status = "completed" if artifact is not None else "failed"
            return self.registry.save(task, status=status, artifact=artifact, runtime=runtime,
                                      validation=trial.delivery_receipt(artifact["plan"]) if artifact and trial else None,
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

    async def build_from_artifact(self, task_id, sha256):
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
        return await self._once("plan:" + task_id, "build_plan_bim",
            {"image": record["image"], "plan_json": json.dumps(plan, ensure_ascii=False)},
            reference={"task_id": task_id, "sha256": sha256})

    def _source(self, candidate):
        if not isinstance(candidate, str) or Path(candidate).name != candidate or not candidate.startswith("candidate_"):
            raise ValueError("candidate must be a saved candidate identifier")
        path = (self.run_directory / candidate / "source_model.json").resolve()
        if not path.is_relative_to(self.run_directory.resolve()):
            raise ValueError("candidate escapes the BIM run")
        if not path.is_file():
            raise ValueError(f"saved candidate does not exist: {candidate}")
        return json.loads(path.read_bytes())

    def match(self, task_id, candidate):
        from .elevation import match_elevation
        artifact = self.registry.read(task_id, role_id="elevation_reader")
        source = self._source(candidate)
        result = match_elevation(source, artifact, candidate=candidate)
        result["source_file_sha256"] = hashlib.sha256(
            (self.run_directory / candidate / "source_model.json").read_bytes()).hexdigest()
        match_id = hashlib.sha256(json_bytes({"task_id": task_id, "candidate": candidate, "result": result})).hexdigest()
        value = {"match_id": match_id, "task_id": task_id, "candidate": candidate, "result": result}
        self.store.write_json("role_matches/" + match_id + ".json", value)
        return value

    async def apply_heights(self, match_id):
        from .elevation import height_application
        if not isinstance(match_id, str) or len(match_id) != 64 or any(c not in "0123456789abcdef" for c in match_id):
            raise ValueError("match_id must be the hash returned by match_elevation")
        path = self.store.directory / "role_matches" / (match_id + ".json")
        if not path.is_file():
            raise ValueError("match_id has no saved match; call match_elevation first")
        value = json.loads(path.read_bytes())
        expected = hashlib.sha256(json_bytes({key: value[key] for key in ("task_id", "candidate", "result")})).hexdigest()
        if match_id != expected:
            raise ValueError("match result hash mismatch")
        # A completed application remains reusable after its own source mutation.
        operation = self.store.directory / "role_operations" / (hashlib.sha256(("height:" + match_id).encode()).hexdigest() + ".json")
        if operation.is_file():
            saved = json.loads(operation.read_bytes())
            if "result" in saved:
                return saved["result"]
            raise ValueError("height application outcome unknown; no repeated mutation")
        artifact = self.registry.read(value["task_id"], role_id="elevation_reader")
        source = self._source(value["candidate"])
        if hashlib.sha256((self.run_directory / value["candidate"] / "source_model.json").read_bytes()).hexdigest() != value["result"]["source_file_sha256"]:
            raise ValueError("matched source file changed; compute a new elevation match before applying")
        application = height_application(artifact, value["result"], value["candidate"],
                                         provenance={"source_model_sha256": source.get("source_model_sha256"), "source_bim": source})
        return await self._once("height:" + match_id, "claim_transaction",
            {"candidate": value["candidate"], "entries_json": application["entries_json"]},
            reference={"match_id": match_id, "task_id": value["task_id"],
                       "artifact_sha256": self.registry.records[value["task_id"]]["artifact"]["sha256"]})

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
            elif call.tool_name in {"build_from_artifact", "apply_elevation_heights"}:
                identity = ("plan:" + call.full_arguments["task_id"] if call.tool_name == "build_from_artifact"
                            else "height:" + call.full_arguments["match_id"])
                path = self.store.directory / "role_operations" / (hashlib.sha256(identity.encode()).hexdigest() + ".json")
                if not path.is_file() or "result" not in json.loads(path.read_bytes()):
                    continue
                raw = json.loads(path.read_bytes())["result"]
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
