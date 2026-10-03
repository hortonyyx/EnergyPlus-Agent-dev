#!/usr/bin/env python3
"""Reconcile the R2 image formula with existing events and the 10-03 bill.

This script is offline.  It reads checked-in evidence and optionally audits an
unpacked run directory supplied with --run; it never contacts a model endpoint.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import timedelta
import csv
import hashlib
import json
from pathlib import Path
import tarfile

from PIL import Image

from src.agent_runtime.estimation import get_model_profile, qwen_image_tokens


ROOT = Path(__file__).resolve().parents[4]
BILL = ROOT / "AI_agent/logs/experiments/2026-10-03_migration_comparison/paratera_bill_2026-10-03.csv"
STAGE3 = ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage3/evidence_all.compact.tar.xz"
FACADE = ROOT / "AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_evidence.compact.tar.xz"
CALIBRATION_RUNS = ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage3/calibration/runs"
STAGE1_PROBE = ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage1/paratera_probe_01"
GLM_SUMMARY = ROOT / "AI_agent/logs/experiments/2026-10-03_runtime_r1/glm_calibration/summary.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_tokens(model: str, width: int, height: int) -> int:
    profile = get_model_profile(model, strict=True)
    value, _, _ = qwen_image_tokens(width, height, profile)
    return value


def classify_usage(raw: dict | None, estimate: int) -> tuple[str, int | None, int | None]:
    if raw is None:
        return "unknown_no_response", None, None
    details = raw.get("prompt_tokens_details") or raw.get("input_tokens_details") or {}
    prompt = raw.get("prompt_tokens", raw.get("input_tokens"))
    text = details.get("text_tokens")
    image = details.get("image_tokens")
    if type(image) is not int or type(text) is not int or type(prompt) is not int:
        return "unknown_no_complete_breakdown", image if type(image) is int else None, None
    if prompt == text + image:
        return "top_level_includes_image", image, estimate - image
    if prompt == text:
        return "top_level_excludes_image", image, estimate - image
    return "unknown_inconsistent_breakdown", image, estimate - image


def collect_events(data: bytes, dimensions: dict[str, tuple[int, int]], source: str) -> list[dict]:
    events = [json.loads(line) for line in data.splitlines()]
    responses = {
        event["payload"]["request_event_id"]: event["payload"]
        for event in events
        if event.get("payload", {}).get("event_type") == "model_response"
    }
    rows = []
    for event in events:
        payload = event.get("payload", {})
        if payload.get("event_type") != "adapter_request" or not payload.get("images"):
            continue
        model = payload["versions"]["remote_model"]["remote_alias"]
        if model not in {"Qwen3.8-27B", "Qwen3.8-Flash", "GLM-5.3-Flash"}:
            continue
        per_image = []
        for transmission in payload["images"]:
            identity = transmission["sent"]["sha256"]
            width, height = dimensions[identity]
            per_image.append(image_tokens(model, width, height))
        estimate = sum(per_image)
        response = responses.get(event["event_id"])
        usage = None if response is None else response.get("usage", {}).get("raw_usage")
        classification, reported, error = classify_usage(usage, estimate)
        occurred = event["occurred_at"]["value"]
        from datetime import datetime
        beijing = datetime.fromisoformat(occurred.replace("Z", "+00:00")) + timedelta(hours=8)
        rows.append({
            "source": source,
            "request_event_id": event["event_id"],
            "bill_hour_beijing": beijing.strftime("%Y-%m-%d %H:00"),
            "model": model,
            "images": len(per_image),
            "estimated_image_tokens": estimate,
            "reported_image_tokens": reported,
            "estimate_minus_reported": error,
            "usage_classification": classification,
        })
    return rows


def compact_archive_rows(path: Path) -> list[dict]:
    rows = []
    with tarfile.open(path) as archive:
        manifest = json.load(archive.extractfile("manifest.json"))
        dimensions = {
            identity: tuple(record["pixel_size"])
            for identity, record in manifest["images"].items()
        }
        for logical_path, record in manifest["files"].items():
            if not logical_path.endswith("events.jsonl") or record["kind"] != "stored":
                continue
            rows.extend(collect_events(
                archive.extractfile(record["object"]).read(),
                dimensions,
                f"{path.relative_to(ROOT)}::{logical_path}",
            ))
    return rows


def plain_run_rows(directory: Path) -> list[dict]:
    event_path = directory / "events.jsonl"
    if not event_path.exists():
        return []
    dimensions = {}
    events = [json.loads(line) for line in event_path.read_bytes().splitlines()]
    for event in events:
        for transmission in event.get("payload", {}).get("images", []):
            identity = transmission["sent"]["sha256"]
            path = directory / transmission["sent"]["uri"]
            with Image.open(path) as image:
                dimensions[identity] = image.size
    try:
        source = str(event_path.relative_to(ROOT))
    except ValueError:
        source = str(event_path)
    return collect_events(event_path.read_bytes(), dimensions, source)


def billed_images() -> tuple[dict[tuple[str, str], int], int]:
    buckets = defaultdict(int)
    total = 0
    with BILL.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["item"] != "image_input":
                continue
            value = int(row["tokens"])
            buckets[(row["bill_start_beijing"], row["model"])] += value
            total += value
    return dict(buckets), total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, help="optional unpacked run to audit")
    args = parser.parse_args()

    rows = compact_archive_rows(STAGE3) + compact_archive_rows(FACADE)
    for directory in sorted(CALIBRATION_RUNS.iterdir()):
        rows.extend(plain_run_rows(directory))
    rows.extend(plain_run_rows(STAGE1_PROBE))
    bill, bill_total = billed_images()

    classifications = defaultdict(lambda: {"requests": 0, "estimated": 0, "reported": 0})
    event_buckets = defaultdict(int)
    maximum_error = 0
    for row in rows:
        bucket = classifications[row["usage_classification"]]
        bucket["requests"] += 1
        bucket["estimated"] += row["estimated_image_tokens"]
        if row["reported_image_tokens"] is not None:
            bucket["reported"] += row["reported_image_tokens"]
        if row["estimate_minus_reported"] is not None:
            maximum_error = max(maximum_error, abs(row["estimate_minus_reported"]))
        if row["usage_classification"] == "top_level_includes_image":
            event_buckets[(row["bill_hour_beijing"], row["model"])] += row["estimated_image_tokens"]

    matched = []
    unmatched_bill = []
    for key, billed in sorted(bill.items()):
        estimated = event_buckets.get(key)
        record = {
            "bill_start_beijing": key[0],
            "model": key[1],
            "billed_image_tokens": billed,
            "attested_event_image_tokens": estimated,
            "difference": None if estimated is None else estimated - billed,
        }
        (matched if estimated is not None else unmatched_bill).append(record)
    covered_bill = sum(row["billed_image_tokens"] for row in matched)
    covered_estimate = sum(row["attested_event_image_tokens"] for row in matched)

    glm = json.loads(GLM_SUMMARY.read_bytes())
    glm_rows = [row for row in glm["rows"] if row["case"].startswith("image_")]
    result = {
        "schema_version": 1,
        "offline_only": True,
        "external_requests_made": 0,
        "bill": {
            "source": str(BILL.relative_to(ROOT)),
            "sha256": sha256(BILL),
            "image_tokens": bill_total,
        },
        "qwen_event_calibration": {
            "request_rows": len(rows),
            "classifications": classifications,
            "formula_max_absolute_token_error_when_reported": maximum_error,
            "matched_bill_buckets": matched,
            "unmatched_bill_buckets": unmatched_bill,
            "bill_tokens_covered": covered_bill,
            "formula_tokens_for_covered_buckets": covered_estimate,
            "covered_difference": covered_estimate - covered_bill,
            "bill_coverage_percent": round(covered_bill / bill_total * 100, 2),
            "interpretation": (
                "A top-level usage value is treated as image-inclusive only when "
                "prompt_tokens == text_tokens + image_tokens. The bill's image rows "
                "are separate pricing evidence; they do not prove that every API "
                "top-level total omitted images."
            ),
        },
        "glm_formula_calibration": {
            "rows": glm_rows,
            "exact_cases": sum(
                row["estimated_image"] == row["actual_input"] - row["estimated_text"]
                for row in glm_rows
            ),
            "large_image_overestimate_tokens": (
                glm_rows[-1]["estimated_image"]
                - (glm_rows[-1]["actual_input"] - glm_rows[-1]["estimated_text"])
            ),
            "billing_status": "unknown; the exported bill has no GLM image_input row",
        },
        "sources": {
            "stage3_archive": {"path": str(STAGE3.relative_to(ROOT)), "sha256": sha256(STAGE3)},
            "facade_archive": {"path": str(FACADE.relative_to(ROOT)), "sha256": sha256(FACADE)},
            "glm_summary": {"path": str(GLM_SUMMARY.relative_to(ROOT)), "sha256": sha256(GLM_SUMMARY)},
        },
    }
    if args.run is not None:
        run_rows = plain_run_rows(args.run.resolve())
        result["optional_run_audit"] = {
            "path": str(args.run.resolve()),
            "events_sha256": sha256(args.run.resolve() / "events.jsonl"),
            "image_requests": len(run_rows),
            "estimated_image_tokens": sum(row["estimated_image_tokens"] for row in run_rows),
            "classifications": {
                name: sum(row["usage_classification"] == name for row in run_rows)
                for name in sorted({row["usage_classification"] for row in run_rows})
            },
            "rows": run_rows,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
