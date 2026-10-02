"""Small target-tier probe (10-02): read window heights from one elevation image.

The sm24 GLM baseline put the 4800 mm windows on the east/west elevations at the
common 2.8 m head instead of 3.4 m. This asks the same local question in isolation:
3 configured Paratera candidates x 2 elevations = 6 requests, no tools, no retries,
no fallback. Raw requests (image replaced by path and sha256) and responses are kept.
"""
import base64
import hashlib
import json
from pathlib import Path
import time

from dotenv import dotenv_values
from openai import OpenAI

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
IMAGES = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data"
FACADES = ("East_view.png", "West_view.png")
# Parameters copied from the candidate profiles in src/configs/llm_paratera.yaml.
MODELS = {
    "Qwen3.8-27B": dict(temperature=0.7, max_tokens=16384, extra_body={"enable_thinking": True}),
    "Qwen3.8-Flash": dict(temperature=0.7, max_tokens=16384, extra_body={"enable_thinking": True}),
    "GLM-5.3-Flash": dict(temperature=0.7, max_tokens=16384, extra_body={"reasoning_effort": "low"}),
}
PROMPT = (
    "This image is an elevation drawing of one facade of a building. Dimension annotations are in "
    "millimetres.\n"
    "List every window on this facade from left to right. For each window give its width in "
    "millimetres if it can be read, its sill height and head height in metres above the ground line "
    "as drawn, and which dimension annotations you used.\n"
    'Reply with JSON only, in this form: {"windows": [{"index": 1, "width_mm": 1500, '
    '"sill_m": 1.0, "head_m": 2.8, "basis": "..."}]}')


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    values = dotenv_values(ROOT / ".env")
    client = OpenAI(api_key=values["PARATERA_API_KEY"], base_url=values["PARATERA_BASE_URL"],
                    max_retries=0, timeout=300)
    out = HERE / "responses"
    out.mkdir(exist_ok=False)
    totals = {}
    for model, params in MODELS.items():
        for facade in FACADES:
            raw = (IMAGES / facade).read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            content = [{"type": "text", "text": PROMPT},
                       {"type": "image_url", "image_url": {
                           "url": "data:image/png;base64," + base64.b64encode(raw).decode()}}]
            request = dict(model=model, messages=[{"role": "user", "content": content}], **params)
            recorded = json.loads(json.dumps(request))
            recorded["messages"][0]["content"][1]["image_url"]["url"] = (
                f"<{(IMAGES / facade).relative_to(ROOT)} sha256={sha}>")
            row = dict(model=model, facade=facade, request=recorded, image_sha256=sha)
            started = time.monotonic()
            try:
                response = client.chat.completions.create(**request)
                row["response"] = response.model_dump(mode="json")
            except Exception as error:  # record and continue; never retry
                row["error"] = dict(type=type(error).__name__,
                                    status=getattr(error, "status_code", None))
            row["elapsed_seconds"] = round(time.monotonic() - started, 2)
            dump(out / f"{model}_{facade.split('_')[0]}.json", row)
            usage = (row.get("response") or {}).get("usage") or {}
            totals[f"{model}/{facade}"] = dict(elapsed_seconds=row["elapsed_seconds"],
                                               error=row.get("error"), usage=usage)
            print(model, facade, row["elapsed_seconds"], usage.get("total_tokens"), row.get("error"))
    dump(HERE / "usage.json", dict(requests=len(totals), retries=0, fallback=False, runs=totals))


if __name__ == "__main__":
    main()
