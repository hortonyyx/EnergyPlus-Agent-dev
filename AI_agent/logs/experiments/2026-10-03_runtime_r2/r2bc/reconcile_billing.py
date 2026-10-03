"""Offline R2b counterexample: nine original responses versus three invoice rows."""

import csv
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import tarfile

from src.agent_runtime.accounting import account_request_usage, get_cny_price_schedule

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
ARCHIVE = ROOT / "AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_evidence.compact.tar.xz"
BILL = ROOT / "AI_agent/logs/experiments/2026-10-03_migration_comparison/paratera_bill_2026-10-03.csv"
HOUR = "2026-10-03 14:00"


def reconcile():
    rows = []
    with tarfile.open(ARCHIVE) as archive:
        manifest = json.load(archive.extractfile("manifest.json"))
        for path, record in manifest["files"].items():
            if not path.endswith("events.jsonl") or record["kind"] != "stored":
                continue
            events = [json.loads(line) for line in archive.extractfile(record["object"]).read().splitlines()]
            requests = {e["event_id"]: e for e in events if e["payload"]["event_type"] == "adapter_request"}
            for response in events:
                payload = response["payload"]
                if payload["event_type"] != "model_response":
                    continue
                request = requests[payload["request_event_id"]]
                identity = request["payload"]["versions"]["remote_model"]
                local = datetime.fromisoformat(request["occurred_at"]["value"].replace("Z", "+00:00")) + timedelta(hours=8)
                if local.strftime("%Y-%m-%d %H:00") != HOUR or identity["remote_alias"] != "Qwen3.8-27B":
                    continue
                raw = payload["usage"]["raw_usage"]
                details = raw["prompt_tokens_details"]
                image = details["image_tokens"]
                accounting = account_request_usage(raw, image_tokens_estimate=image,
                    pricing=get_cny_price_schedule(identity["remote_alias"], provider="paratera"))
                rows.append({"source": path, "events_object": record["object"],
                    "request_event_id": request["event_id"], "response_event_id": response["event_id"],
                    "raw_usage": raw, "text_detail_tokens": details["text_tokens"],
                    "invoice_text_input": raw["prompt_tokens"] - details.get("cached_tokens", 0),
                    "invoice_image_input": image, "invoice_text_output": raw["completion_tokens"],
                    "accounting": accounting.receipt_dict()})
    rows.sort(key=lambda row: (row["source"], row["request_event_id"]))
    assert len(rows) == 9
    rates = {"text_input": Decimal(3), "image_input": Decimal(3), "text_output": Decimal(12)}
    with BILL.open() as source:
        invoice = [r for r in csv.DictReader(source) if r["bill_start_beijing"] == HOUR and r["model"] == "Qwen3.8-27B"]
    lines = []
    for line in invoice:
        item = line["item"]
        count = sum(row["invoice_" + item] for row in rows)
        amount = Decimal(count) * rates[item] / Decimal(1_000_000)
        rounded = amount.quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
        assert count == int(line["tokens"])
        assert rounded == Decimal(line["fee_yuan"])
        lines.append({"item": item, "recomputed_tokens": count, "invoice_tokens": int(line["tokens"]),
            "token_error": 0, "cny_per_million": str(rates[item]), "unrounded_cny": str(amount),
            "rounded_cny": str(rounded), "invoice_cny": line["fee_yuan"], "cny_error": "0"})
    assert len(lines) == 3
    return {"status": "passed", "model_requests": 0, "bill_hour_beijing": HOUR,
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ARCHIVE, BILL)},
        "requests": rows, "invoice_lines": lines,
        "provider_reported_tokens": sum(row["raw_usage"]["total_tokens"] for row in rows),
        "budget_charge_tokens": sum(row["accounting"]["budget_charge_tokens"] for row in rows),
        "unrounded_cny": str(sum((Decimal(r["unrounded_cny"]) for r in lines), Decimal(0))),
        "invoice_total_cny": str(sum((Decimal(r["rounded_cny"]) for r in lines), Decimal(0))),
        "rounding": "Sum tokens per hourly invoice line, then round each line to five decimal places; do not round each request first."}


if __name__ == "__main__":
    result = reconcile()
    (HERE / "billing_reconciliation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"requests", "sources"}}, ensure_ascii=False))
