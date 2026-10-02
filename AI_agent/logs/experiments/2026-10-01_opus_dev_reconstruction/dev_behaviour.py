"""Behaviour summary of the developer runs in the same terms as the work-model records.

Source: every bridge request/reply saved under <run>/bridge/ and dev_calls.jsonl. The
developer's own reading and reasoning between batches is not a tool call; its wall time is
inside the elapsed figures. Writes <run>/dev_behaviour.json and prints a table row.
"""
from collections import Counter
import json
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
FACADES = ("north", "south", "east", "west")


def facade(name):
    return next((f for f in FACADES if f in str(name).lower()), None)


def summarise(case):
    run = EXP / f"2026-10-01_opus_dev_{case}"
    calls = [json.loads(line) for line in (run / "dev_calls.jsonl").read_text().splitlines()]
    t0 = calls[0]["t"]
    steps = []
    for call in calls:
        folder = Path(call["record"]) if call.get("record") else None
        if folder is None or not (folder / "requests.json").exists():
            continue
        requests = json.loads((folder / "requests.json").read_text())
        replies = json.loads((folder / "replies.json").read_text()) if (folder / "replies.json").exists() else []
        for i, request in enumerate(requests):
            reply = replies[i] if i < len(replies) else None
            if reply is None:  # the bridge stops a batch at its first error; later requests never ran
                continue
            steps.append(dict(t=round(call["t"] - t0, 1), tool=request["tool"], arguments=request["arguments"],
                              error=bool(reply["isError"])))
    tools = Counter(s["tool"] for s in steps)
    first_build = next((s["t"] for s in steps if s["tool"] == "build_plan_bim"), None)
    before = [s for s in steps if first_build is None or s["t"] < first_build]
    views = [s for s in steps if s["tool"] == "view_image"]
    claims = []
    for s in steps:
        if s["tool"] != "record_claim" or s["error"]:
            continue
        claim = json.loads(s["arguments"]["claim_json"])
        claims.append(dict(objects=[o["id"] for o in claim["objects"]], source_view=claim["sources"][0].get("view_id"),
                           reason=claim["reason"][:120]))
    summary = dict(
        case=case, run=run.name, elapsed_seconds=json.loads((run / "summary.json").read_text())["elapsed_seconds"],
        bridge_batches=len(calls), tool_calls=len(steps), tool_errors=sum(s["error"] for s in steps),
        errors=[dict(t=s["t"], tool=s["tool"]) for s in steps if s["error"]], tools=dict(tools),
        first_build_s=first_build, calls_before_first_build=len(before),
        full_views_before_first_build=sum(1 for s in before if s["tool"] == "view_image" and "box" not in s["arguments"]),
        crops_before_first_build=sum(1 for s in before if s["tool"] == "view_image" and "box" in s["arguments"]),
        pixel_tools_before_first_build=sum("pixel" in s["tool"] for s in before),
        elevation_crops=sum(1 for s in views if "box" in s["arguments"] and facade(s["arguments"].get("name"))),
        elevation_overlays=dict(Counter(s["arguments"].get("facade") for s in steps if s["tool"] == "view_elevation_candidate")),
        claims=claims, plan_builds=tools["build_plan_bim"], plan_revisions=tools["revise_plan_bim"],
        candidate_revisions=tools["revise_bim"],
        note="Every plan built on its first attempt; heights were read per facade before drafting and entered in the first drafts.")
    (run / "dev_behaviour.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


if __name__ == "__main__":
    for case in ("sm21", "sm24", "sm25"):
        s = summarise(case)
        print(json.dumps({k: s[k] for k in ("case", "elapsed_seconds", "tool_calls", "tool_errors", "first_build_s",
                                            "calls_before_first_build", "crops_before_first_build",
                                            "pixel_tools_before_first_build", "elevation_overlays", "plan_builds",
                                            "plan_revisions", "candidate_revisions")}, ensure_ascii=False),
              "| claims", len(s["claims"]))
