"""Replay the real sm24 run3/run6 trial envelopes without geometry or model calls."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any


REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.agent.runtime_roles.trial import PlanTrial  # noqa: E402
from src.agent_runtime.adapter import convert_tool_result  # noqa: E402
from src.agent_runtime.image_capture import reconstruct_capture  # noqa: E402
from src.agent_runtime.json_tree import read_json_tree  # noqa: E402
from src.agent_runtime.loop import RunLimits  # noqa: E402
from src.agent_runtime.store import EventStore, json_bytes  # noqa: E402
from src.harness_contracts import (  # noqa: E402
    BlobCapture,
    ImageReferencedCapture,
    JsonReferencedCapture,
)


DEFAULT_SOURCE = Path(
    r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\role_debug"
)
DEFAULT_CASES = REPO / "AI_agent/archive/local_backup/c4/trial_replay_cases"
DEFAULT_OUTPUT = Path(__file__).with_name("trial_replay.json")


class InjectedTrial(PlanTrial):
    def __init__(self, receipt: dict[str, Any], images: list[dict[str, Any]]):
        super().__init__(object(), image_name=str(receipt.get("image") or "plan.png"))
        self.injected_receipt = receipt
        self.injected_images = images

    async def run(self, plan=None, *, operations=None):
        return self.injected_receipt

    def _image_content(self, receipt):
        return list(self.injected_images)


def _read_blob(run: Path, ref) -> bytes:
    data = (run / ref.uri).read_bytes()
    if hashlib.sha256(data).hexdigest() != ref.sha256:
        raise ValueError(f"blob hash mismatch: {ref.uri}")
    return data


def _resolve_capture(run: Path, value: dict[str, Any]) -> Any:
    read = lambda ref: _read_blob(run, ref)
    if value["kind"] == "inline":
        return value["value"]
    if value["kind"] == "blob":
        return json.loads(read(BlobCapture.model_validate(value).blob))
    if value["kind"] == "json_references":
        capture = JsonReferencedCapture.model_validate(value)
        decoded = read_json_tree(capture.blob, read)
        if hashlib.sha256(json_bytes(decoded)).hexdigest() != capture.wire_sha256:
            raise ValueError("reconstructed JSON capture hash mismatch")
        return decoded
    if value["kind"] == "image_references":
        compatible = dict(value)
        compatible["images"] = tuple(compatible["images"])
        capture = ImageReferencedCapture.model_validate(compatible)
        return json.loads(reconstruct_capture(capture, read))
    raise ValueError(f"unsupported capture kind: {value['kind']}")


def _extract(source: Path, cases: Path) -> list[Path]:
    cases.mkdir(parents=True, exist_ok=True)
    written = []
    for run_name in ("sm24_run3", "sm24_run6"):
        run = source / run_name
        for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            payload = event["payload"]
            if payload.get("event_type") != "tool_execution" or payload.get("tool_name") != "trial_plan_bim":
                continue
            raw = _resolve_capture(run, payload["raw_result"])
            receipt = raw.get("structuredContent")
            if not isinstance(receipt, dict) or receipt.get("status") not in {"passed", "failed"}:
                continue
            path = cases / f"{run_name}_{event['event_id']}.json"
            path.write_text(
                json.dumps({
                    "run": run_name,
                    "event_id": event["event_id"],
                    "call_id": payload["call_id"],
                    "raw": raw,
                }, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8", newline="\n",
            )
            written.append(path)
    return written


def _image_hashes(raw: dict[str, Any]) -> list[str]:
    return [
        hashlib.sha256(base64.b64decode(block["data"], validate=True)).hexdigest()
        for block in raw.get("content", []) if block.get("type") == "image"
    ]


def _tool_text(raw: dict[str, Any]) -> str:
    return "\n".join(
        block["text"] for block in raw.get("content", []) if block.get("type") == "text"
    )


def _compact_characters(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _convert(directory: Path, name: str, raw: dict[str, Any]) -> str:
    limits = RunLimits(model_calls=1, tool_calls=1, seconds=10, tokens=1_000_000)
    with EventStore(
        directory / name, run_id=name, task_id="plan-reader", budget_limit=limits.ledger_limit()
    ) as store:
        message, _, _, _ = convert_tool_result(raw.get("call_id", "trial-call"), raw, store)
    return message["content"]


def replay(cases: Path, scratch: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(cases.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        raw = record["raw"]
        receipt = raw["structuredContent"]
        images = [block for block in raw["content"] if block.get("type") == "image"]
        before_raw_text = _tool_text(raw)
        before_text = _convert(scratch, f"before-{record['event_id']}", raw)
        after_raw = asyncio.run(InjectedTrial(receipt, images).call({}))
        after_raw_text = _tool_text(after_raw)
        after_text = _convert(scratch, f"after-{record['event_id']}", after_raw)
        after_visible = after_raw["structuredContent"]
        full_images = receipt.get("returned_images", [])
        visible_images = after_visible.get("returned_images", [])
        preserved = {
            key: after_visible.get(key) == receipt.get(key)
            for key in (
                "reason", "repair_hint", "source_findings", "unhosted_openings",
                "loose_partition_ends", "drawing_differences", "building_precision",
                "topology_issues", "topology_dividers", "changes",
            ) if key in receipt
        }
        rows.append({
            "run": record["run"],
            "event_id": record["event_id"],
            "status": receipt["status"],
            "historical_tool_text_characters": len(before_raw_text),
            "historical_structured_content_characters": _compact_characters(receipt),
            "historical_adapter_visible_characters": len(before_text),
            "after_tool_text_characters": len(after_raw_text),
            "after_structured_content_characters": _compact_characters(after_visible),
            "after_adapter_visible_characters": len(after_text),
            "reduction_characters": len(before_text) - len(after_text),
            "reduction_percent": round((1 - len(after_text) / len(before_text)) * 100, 1),
            "historical_tool_text_reason_occurrences": (
                before_raw_text.count(str(receipt["reason"])) if receipt.get("reason") else 0
            ),
            "historical_adapter_reason_occurrences": (
                before_text.count(str(receipt["reason"])) if receipt.get("reason") else 0
            ),
            "after_tool_text_reason_occurrences": (
                after_raw_text.count(str(receipt["reason"])) if receipt.get("reason") else 0
            ),
            "after_adapter_reason_occurrences": (
                after_text.count(str(receipt["reason"])) if receipt.get("reason") else 0
            ),
            "image_hashes_before": _image_hashes(raw),
            "image_hashes_after": _image_hashes(after_raw),
            "image_hashes_unchanged": _image_hashes(raw) == _image_hashes(after_raw),
            "full_origin_records_present": all(isinstance(row.get("origin"), dict) for row in full_images),
            "visible_images_are_file_and_hash_only": all(
                set(row) <= {"file", "sha256"} and isinstance(row.get("sha256"), str)
                for row in visible_images
            ),
            "preserved_actionable_fields": preserved,
            "audit_refs": after_visible.get("audit_refs", {}),
        })
    return {
        "schema_version": 1,
        "source_runs": ["sm24_run3", "sm24_run6"],
        "model_requests": 0,
        "geometry_reruns": 0,
        "cases": rows,
        "summary": {
            "case_count": len(rows),
            "passed": sum(row["status"] == "passed" for row in rows),
            "failed": sum(row["status"] == "failed" for row in rows),
            "all_image_hashes_unchanged": all(row["image_hashes_unchanged"] for row in rows),
            "all_full_origins_retained": all(row["full_origin_records_present"] for row in rows),
            "all_visible_images_compact": all(row["visible_images_are_file_and_hash_only"] for row in rows),
            "all_actionable_fields_preserved": all(
                all(row["preserved_actionable_fields"].values()) for row in rows
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    written = _extract(args.source, args.cases)
    scratch = args.cases.parent / "trial_replay_events"
    if scratch.exists():
        shutil.rmtree(scratch)
    try:
        result = replay(args.cases, scratch)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
    result["temporary_case_files"] = [str(path.relative_to(REPO)) for path in written]
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
