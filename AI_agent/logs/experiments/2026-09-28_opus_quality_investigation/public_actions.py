"""Extract only public actions from an agent stream: assistant text, tool_use inputs, tool_result text.

Thinking / redacted_thinking blocks are skipped without being read or printed.
Usage: python public_actions.py <run_dir> [--grep WORD] [--max N] [--full-input]
"""
import argparse
import gzip
import json
import os


def iter_public(stream_path):
    with gzip.open(stream_path, "rt") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            kind = event.get("type")
            if kind not in ("assistant", "user"):
                continue
            message = event.get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            for block in content or []:
                btype = block.get("type")
                if btype in ("thinking", "redacted_thinking"):
                    continue
                if kind == "assistant" and btype == "text":
                    yield "TEXT", block.get("text", "")
                elif kind == "assistant" and btype == "tool_use":
                    name = (block.get("name") or "").replace("mcp__bim__", "")
                    yield "CALL", f"{name} {json.dumps(block.get('input'), ensure_ascii=False)}"
                elif kind == "user" and btype == "tool_result":
                    parts = block.get("content")
                    if isinstance(parts, list):
                        text = " ".join(p.get("text", "") for p in parts if p.get("type") == "text")
                        images = sum(1 for p in parts if p.get("type") == "image")
                        if images:
                            text = f"[{images} image] " + text
                    else:
                        text = str(parts)
                    yield "RESULT", text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--stream", default="agent_stream.jsonl.gz")
    parser.add_argument("--grep", default=None)
    parser.add_argument("--max", type=int, default=600)
    args = parser.parse_args()
    path = os.path.join(args.run_dir, args.stream)
    for index, (kind, text) in enumerate(iter_public(path)):
        if args.grep and args.grep.lower() not in text.lower():
            continue
        text = " ".join(text.split())
        print(f"[{index}] {kind}: {text[: args.max]}")


if __name__ == "__main__":
    main()
