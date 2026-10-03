"""R2 authorized text-only truncation probe; at most five durable send tickets.

This is a protocol probe, not a building case. Credentials stay in the main-tree
.env, which is read for the two Paratera values only and never serialized.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from src.agent.runtime_entry import paratera_credentials
from src.agent_runtime.adapter import HttpChatAdapter
from src.agent_runtime.call_quota import QuotaAdapter
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import InputMaterialRequirement, ReturnRequirement, RoleDefinition


ROOT = Path(__file__).resolve().parents[4]
DELIVERY = Path(__file__).resolve().parent


class NoTools:
    async def list_tools(self):
        return []

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []


async def probe():
    directory = DELIVERY / "live_truncation_probe"
    if directory.exists():
        raise ValueError("this probe is single-use; inspect its receipt before any follow-up")
    limits = RunLimits(model_calls=3, tool_calls=0, seconds=180, tokens=100_000,
        max_consecutive_truncations=2, max_total_truncations=2)
    role = RoleDefinition(role_id="protocol_probe", responsibilities=("Test output truncation recovery only",),
        tool_whitelist=(), input_materials=(InputMaterialRequirement(name="text", media_type="text/plain"),),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="text"),),
        budget=limits.ledger_limit(), read_only=True)
    model = "GLM-5.3-Flash"
    parameters = {"max_tokens": 128, "temperature": 0.0, "reasoning_effort": "low"}
    system = (
        "This is a text-only output-limit protocol test. On the first request, write every integer "
        "from 1 to 1000, separated by spaces, without a preamble or abbreviations. "
        "If a later runtime message says the previous response exceeded the output limit, "
        "immediately answer only OK. Do not repeat the number list in that case."
    )
    base_url, key = paratera_credentials(Path("/workspaces/EnergyPlus-Agent-dev/.env"))
    adapter = HttpChatAdapter(base_url=base_url, api_key=key)
    guarded = QuotaAdapter(adapter, DELIVERY / "paratera_requests.jsonl", limit=5,
        category="r2_truncation_probe_only")
    try:
        with EventStore(directory, run_id="r2-truncation-probe", task_id="protocol_probe",
                budget_limit=limits.ledger_limit()) as store:
            versions = make_versions(store, root=ROOT, prompt=system, tools=[], parameters=parameters,
                route={"route_id": "paratera", "model": model, "base_url": base_url})
            engine = Runtime(store=store, adapter=guarded, tools=NoTools(), role=role,
                model=model, parameters=parameters, versions=versions, limits=limits,
                strict_model_profile=True,
                low_output_limit_reason="R2 authorized text-only probe deliberately uses 128 tokens to trigger finish_reason=length.")
            receipt = await engine.run([{"role": "system", "content": system},
                {"role": "user", "content": "Start the number list now."}])
            success = receipt["status"] == "completed" and receipt["truncations"] >= 1 and receipt["answer"].strip() == "OK"
            result = {"protocol_probe_passed": success, "model": model,
                "scope": "text-only output truncation and continuation; no building case or tools",
                **{k: receipt[k] for k in ("status", "answer", "model_calls", "reported_tokens", "image_tokens_estimate",
                    "estimated_cost_cny", "usage_accounting", "elapsed_seconds", "truncations", "agent_version")}}
            (DELIVERY / "truncation_probe_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps(result, ensure_ascii=False))
    finally:
        await adapter.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-authorized-probe", action="store_true", required=True)
    parser.parse_args()
    asyncio.run(probe())
