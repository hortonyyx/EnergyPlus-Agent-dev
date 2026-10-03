"""Five-ticket Paratera calibration for GLM-5.3-Flash.

The model ID and accepted ``reasoning_effort`` parameter were first checked in
the repository's 2026-10-02 Paratera probe response.  This run uses the existing
durable QuotaAdapter, no SDK retries, and no fallback.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

from dotenv import dotenv_values
from PIL import Image, ImageDraw

from src.agent_runtime.adapter import HttpChatAdapter
from src.agent_runtime.call_quota import QuotaAdapter
from src.agent_runtime.store import json_bytes


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
PRIVATE_ENV = Path("/workspaces/EnergyPlus-Agent-dev/.env")
MODEL = "GLM-5.3-Flash"
PARAMETERS = {"max_tokens": 8, "temperature": 0.0, "reasoning_effort": "medium"}
LIMIT = 5


def image_data(width: int, height: int) -> tuple[str, str]:
    picture = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(picture)
    draw.rectangle((2, 2, width - 3, height - 3), outline="black", width=2)
    draw.line((0, 0, width - 1, height - 1), fill="red", width=2)
    stream = io.BytesIO()
    picture.save(stream, format="PNG", optimize=True)
    raw = stream.getvalue()
    return "data:image/png;base64," + base64.b64encode(raw).decode(), hashlib.sha256(raw).hexdigest()


def cases() -> list[dict]:
    common = "Reply only OK. Token calibration uses a short English sentence and 中文字符 12345."
    long = ("Calibration record: level=2; object=space; source=view; status=observed; "
            "coordinates=[12.5, 18.75]; note=retain evidence and report uncertainty.\n") * 96
    result = [
        {"name": "text_control", "messages": [{"role": "user", "content": common}]},
        {"name": "text_long", "messages": [{"role": "user", "content": long}]},
    ]
    for width, height in ((224, 224), (896, 896), (1600, 1200)):
        url, sha256 = image_data(width, height)
        result.append({
            "name": f"image_{width}x{height}",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": common},
                {"type": "image_url", "image_url": {"url": url}},
            ]}],
            "image": {"width": width, "height": height, "sha256": sha256},
        })
    return result


def sanitized_body(body: dict, image: dict | None) -> dict:
    value = json.loads(json.dumps(body))
    if image:
        value["messages"][0]["content"][1]["image_url"]["url"] = (
            f"<synthetic image sha256={image['sha256']}>"
        )
    return value


async def main() -> None:
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError("run calibration from the assigned worktree root")
    HERE.mkdir(parents=True, exist_ok=True)
    journal = HERE / "quota.jsonl"
    if journal.exists():
        attempts = [json.loads(line) for line in journal.read_text().splitlines()]
        if any(row.get("event") == "attempt" for row in attempts):
            raise RuntimeError("calibration already has reserved tickets; do not rerun")
    values = dotenv_values(PRIVATE_ENV, interpolate=False)
    base_url, api_key = values.get("PARATERA_BASE_URL"), values.get("PARATERA_API_KEY")
    if not base_url or not api_key:
        raise RuntimeError("the two permitted Paratera fields are unavailable")
    adapter = HttpChatAdapter(base_url=base_url, api_key=api_key)
    quota = QuotaAdapter(adapter, journal, limit=LIMIT, category="r1-glm-estimation-calibration")
    rows = []
    try:
        for case in cases():
            body = {"model": MODEL, "messages": case["messages"], "stream": False, "n": 1,
                    **PARAMETERS}
            prepared = SimpleNamespace(body=body, wire_bytes=json_bytes(body))
            row = {"case": case["name"], "request": sanitized_body(body, case.get("image")),
                   "image": case.get("image")}
            try:
                response = await quota.send(prepared, timeout=180.0)
                row["response"] = response
            except Exception as error:
                row["error"] = {"type": type(error).__name__,
                                "status": getattr(error, "status_code", None)}
            rows.append(row)
            (HERE / "responses.json").write_text(
                json.dumps({"schema_version": 1, "model": MODEL,
                            "parameters": PARAMETERS, "rows": rows}, ensure_ascii=False, indent=2) + "\n"
            )
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
