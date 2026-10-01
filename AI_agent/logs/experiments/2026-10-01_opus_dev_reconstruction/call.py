"""Developer call helper: send tool requests through bim_agent_bridge and print a digest.

The bridge saves every request, full reply and returned image under <run>/bridge/<id>/.
This helper only shortens what is printed to the developer; nothing is filtered from
the saved record. Usage:
  python call.py RUN '[{"tool":"inputs","arguments":{}}]' [--full]
"""
import asyncio
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.bim_agent_bridge import invoke  # noqa: E402


def main():
    run = Path(sys.argv[1])
    run = run if run.is_absolute() else HERE.parent / run
    requests = json.loads(Path(sys.argv[2]).read_text() if sys.argv[2].endswith(".json") else sys.argv[2])
    full = "--full" in sys.argv
    started = time.time()
    try:
        result = asyncio.run(invoke(run, requests))
    except Exception as error:  # surfaced, never retried
        print(f"BRIDGE ERROR: {type(error).__name__}: {error}")
        raise SystemExit(1)
    with (run / "dev_calls.jsonl").open("a") as log:
        log.write(json.dumps(dict(t=round(started, 1), seconds=round(time.time() - started, 1),
                                  record=result.get("record"), tools=[r["tool"] for r in requests],
                                  completed=result.get("completed"))) + "\n")
    print("record:", result.get("record"), "completed:", result.get("completed"))
    for index, reply in enumerate(result.get("replies", []), 1):
        body = reply.get("structuredContent")
        if body is None:
            body = [c.get("text") for c in reply["content"] if c.get("type") == "text"]
        text = json.dumps(body, ensure_ascii=False)
        limit = None if full else 2500
        print(f"--- {index} {reply['tool']} error={reply['isError']}")
        print(text if limit is None or len(text) <= limit else text[:limit] + f" …(+{len(text) - limit})")
        for c in reply["content"]:
            if c.get("type") == "image":
                print("IMAGE", c["path"])


if __name__ == "__main__":
    main()
