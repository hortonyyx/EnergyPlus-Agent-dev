"""Bounded setup check: synthetic image -> tool call -> tool result receipt.

At most two short requests per explicit candidate; no retries, fallback, BIM
generation, DeepSeek invocation, or quality claim beyond this protocol check.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from dotenv import dotenv_values
from openai import OpenAI, APIStatusError, APIConnectionError, APITimeoutError
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MODELS = ["Qwen3.8-27B", "Qwen3.5-35B-A3B", "Qwen3.8-Flash", "GLM-5.3-Flash"]


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    values = dotenv_values(ROOT / ".env")
    key = values["PARATERA_API_KEY"]
    client = OpenAI(api_key=key, base_url=values["PARATERA_BASE_URL"],
                    max_retries=0, timeout=60)
    catalog = {r["id"] for r in json.loads((HERE / "catalog.json").read_text())["data"]}
    assert set(MODELS) <= catalog
    folder = HERE / "protocol_probe"
    folder.mkdir(exist_ok=False)
    # Deliberately synthetic input, unrelated to any building benchmark or GT.
    picture = Image.new("RGB", (480, 200), "white")
    draw = ImageDraw.Draw(picture)
    font = ImageFont.load_default(size=68)
    draw.rectangle([15, 15, 225, 185], outline="black", width=4)
    draw.rectangle([255, 15, 465, 185], outline="black", width=4)
    draw.text((65, 58), "37", font=font, fill="black")
    draw.text((305, 58), "84", font=font, fill="black")
    picture.save(folder / "input.png")
    raw = (folder / "input.png").read_bytes()
    messages = [{"role": "user", "content": [
        {"type": "text", "text": "Read the integer in each box. Call add_numbers with left and right matching the image, without answering directly. After the tool responds, output only its receipt field."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw).decode()}}
    ]}]
    function = {"type": "function", "function": {"name": "add_numbers",
        "description": "Add the two observed integers and return a receipt.",
        "parameters": {"type": "object", "properties": {"left": {"type": "integer"}, "right": {"type": "integer"}},
                       "required": ["left", "right"], "additionalProperties": False}}}
    dump(folder / "scope.json", dict(models=MODELS, maximum_requests=8, max_output_tokens_per_request=1024,
        timeout_seconds_per_request=60, retries=0, automatic_fallback=False, input_sha256=hashlib.sha256(raw).hexdigest(),
        user_authorization="User supplied this platform/key and requested working-model setup and candidate screening.",
        limits="Synthetic protocol capability only, not a building regression, model ranking or confirmed billing rate."))
    reports = []
    for model in MODELS:
        output = folder / model
        output.mkdir()
        report = dict(requested_model=model, requests=0, status="started", started_at_utc=datetime.now(timezone.utc).isoformat())
        extra = {"reasoning_effort": "low"} if model.startswith("GLM") else {"enable_thinking": False}
        try:
            body = dict(model=model, messages=messages, tools=[function], tool_choice="auto",
                        max_tokens=1024, temperature=0.7, extra_body=extra)
            dump(output / "request_1.json", {**body, "messages": [{"role":"user", "content":[messages[0]["content"][0],
                {"type":"image_url", "image_url":{"url":"../input.png; transmitted as exact base64 bytes"}}]}]})
            started = time.monotonic()
            report["requests"] += 1
            first = client.chat.completions.create(**body)
            report["first_elapsed_seconds"] = round(time.monotonic() - started, 3)
            serialized = first.model_dump(mode="json")
            assert key not in json.dumps(serialized)
            dump(output / "response_1.json", serialized)
            report.update(returned_model=first.model, usage_1=serialized.get("usage"), finish_reason_1=first.choices[0].finish_reason)
            answer = first.choices[0].message
            calls = answer.tool_calls or []
            report["tool_called"] = len(calls) == 1 and calls[0].function.name == "add_numbers"
            if report["tool_called"]:
                arguments = json.loads(calls[0].function.arguments)
                report["visual_arguments_correct"] = arguments == {"left": 37, "right": 84}
                report["observed_arguments"] = arguments
                token = "receipt_" + hashlib.sha256(model.encode()).hexdigest()[:12]
                result = {"sum": arguments.get("left", 0) + arguments.get("right", 0), "receipt": token}
                next_messages = [*messages, answer.model_dump(exclude_none=True),
                    {"role":"tool", "tool_call_id":calls[0].id, "content":json.dumps(result)}]
                body_2 = {**body, "messages":next_messages, "tool_choice":"none"}
                dump(output / "request_2.json", {**body_2, "messages":[
                    {"role":"user", "content":"Same exact input image and instruction as request_1.json"}, *next_messages[1:]]})
                report["requests"] += 1
                started = time.monotonic()
                second = client.chat.completions.create(**body_2)
                report["second_elapsed_seconds"] = round(time.monotonic() - started, 3)
                dump(output / "response_2.json", second.model_dump(mode="json"))
                report.update(returned_model_2=second.model, usage_2=second.usage.model_dump() if second.usage else None,
                    finish_reason_2=second.choices[0].finish_reason,
                    tool_result_followed=(second.choices[0].message.content or "").strip() == token)
            report["status"] = "pass" if all(report.get(k) for k in ("tool_called", "visual_arguments_correct", "tool_result_followed")) else "protocol_check_incomplete_or_failed"
        except APIStatusError as error:
            report.update(status="http_error", http_status=error.status_code,
                error=str(error).replace(key, "[REDACTED]"))
        except (APIConnectionError, APITimeoutError) as error:
            report.update(status="transport_error", error_type=type(error).__name__)
        except (ValueError, TypeError) as error:
            report.update(status="invalid_model_output", error_type=type(error).__name__)
        reports.append(report)
        dump(output / "receipt.json", report)
        dump(folder / "report.json", dict(reports=reports, requests=sum(r["requests"] for r in reports),
            limits="Interface/vision/tool-result smoke only. Billing rates, whole-building quality and actual upstream weight identity remain unverified."))
        print(json.dumps(report, ensure_ascii=False), flush=True)
        if report.get("http_status") in {401, 402, 403, 429} or report["status"] == "transport_error":
            break
    client.close()


if __name__ == "__main__":
    main()
