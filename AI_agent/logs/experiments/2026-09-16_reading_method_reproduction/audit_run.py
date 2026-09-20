"""Audit completed reader turns; does not supply feedback or load evaluation GT."""
from pathlib import Path
import base64
from collections import Counter
import hashlib
import io
import json

from PIL import Image

ROOT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def audit():
    manifest = json.loads((ROOT / "input_manifest.json").read_text())
    stage = Path(manifest["workspace"])
    inputs = []
    for row in manifest["files"]:
        local = stage / row["path"]
        frozen = ROOT / "frozen_input" / row["path"]
        inputs.append({"path": row["path"],
                       "live_unchanged": digest(local.read_bytes()) == row["sha256"],
                       "archive_matches": digest(frozen.read_bytes()) == row["sha256"]})
    rounds = []
    for directory in sorted((ROOT / "invocations").iterdir()):
        if not (directory / "receipt.json").is_file():
            continue
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        calls = {c["id"]: c for e in events if e.get("type") == "assistant"
                 for c in e.get("message", {}).get("content", []) if c.get("type") == "tool_use"}
        images = []
        errors = []
        for e in events:
            if e.get("type") != "user":
                continue
            for c in e.get("message", {}).get("content", []):
                call = calls.get(c.get("tool_use_id"), {})
                if c.get("is_error"):
                    errors.append({"call": call, "error": c.get("content")})
                if not isinstance(c.get("content"), list):
                    continue
                for part in c["content"]:
                    if part.get("type") != "image":
                        continue
                    data = base64.b64decode(part["source"]["data"])
                    image = Image.open(io.BytesIO(data)).convert("RGB")
                    name = call.get("input", {}).get("file_path", "")
                    original = Path(name)
                    same_pixels = None
                    if original.is_file():
                        expected = Image.open(original).convert("RGB")
                        same_pixels = expected.size == image.size and expected.tobytes() == image.tobytes()
                    images.append({"path": name, "size": list(image.size),
                                   "sha256": digest(data), "matches_local_pixels": same_pixels})
        receipt = json.loads((directory / "receipt.json").read_text())
        evidence = directory / "0_reading" / "cv_evidence"
        sidecars = [json.loads(p.read_text()) for p in evidence.rglob("*.json")]
        tools = Counter(item.get("tool") for item in sidecars)
        views = []
        for path in sorted((directory / "0_reading").glob("*_view.json")):
            data = json.loads(path.read_text())
            views.append({"name": path.name, "sha256": digest(path.read_bytes()),
                          "pens": dict(Counter(s.get("pen") for s in data.get("strokes", []))),
                          "dimensions": len(data.get("dimensions", [])),
                          "scale_origin": data.get("scale_origin")})
        rounds.append({"label": directory.name, "session_id": receipt["result"].get("session_id"),
            "models": receipt["actual_models"], "elapsed_seconds": receipt["elapsed_seconds"],
            "cli_cost_estimate_usd": receipt["result"].get("total_cost_usd"),
            "usage": receipt["result"].get("usage"), "tool_calls": len(calls),
            "tool_names": dict(Counter(c["name"] for c in calls.values())),
            "tool_errors": errors, "image_transport": images,
            "cv_tools_in_snapshot": dict(tools), "views": views})
        # Exact operation inputs, without the giant image blocks or token telemetry.
        (directory / "tool_calls.json").write_text(json.dumps(list(calls.values()), indent=2, ensure_ascii=False) + "\n")
    result = {"input_verification": inputs, "rounds": rounds,
              "same_session": len({r["session_id"] for r in rounds}) <= 1,
              "limitations": ["Pixel identity checks CLI tool-return images, not provider-internal vision preprocessing.",
                              "Bash boundary compliance must also be reviewed in tool_calls.json; no OS sandbox is claimed.",
                              "CV counts are cumulative workspace snapshots, not independent new calls per resumed turn."]}
    (ROOT / "execution_audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"completed_rounds": len(rounds), "inputs_unchanged": all(x["live_unchanged"] and x["archive_matches"] for x in inputs),
                      "same_session": result["same_session"], "images_checked": sum(len(r["image_transport"]) for r in rounds)}))


if __name__ == "__main__":
    audit()
