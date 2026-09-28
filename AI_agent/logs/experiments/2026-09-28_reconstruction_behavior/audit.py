"""Object-level reading of saved public actions and results; no model calls.

Object identities below are development-side correspondences checked against
the original drawings. They are not inferred from matching ID strings across runs.
This is a bounded audit of five existing runs, not a new production evaluator.
"""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OBJECTS = {
    57: ["F1:W-N1", "F1:W-S1", "F2:W-E"],
    58: ["F1:W_N1", "F1:W_S1", "F2:W_E"],
    79: ["F1:W1", "F1:W4", "F2:W_east"],
    80: ["F1:W_N1", "F1:W_S1", "F2:W_east_corridor2"],
    81: ["F1:W_N1", "F1:W_S1", "F2:W2F_East"],
}
LABELS = ["F1 north regular window", "F1 south small window", "F2 east corridor window"]


def calls(path):
    """Retain public requests/results only; never read model reasoning fields."""
    found = {}
    with gzip.open(path, "rt") as stream:
        for line in stream:
            parts = json.loads(line).get("message", {}).get("content", [])
            for part in parts if isinstance(parts, list) else []:
                if part.get("type") == "tool_use" and part["id"] not in found:
                    found[part["id"]] = dict(ordinal=len(found) + 1,
                        tool=part["name"].removeprefix("mcp__bim__"),
                        input=part.get("input", {}), result_received=False)
                elif part.get("type") == "tool_result" and part.get("tool_use_id") in found:
                    row = found[part["tool_use_id"]]
                    row.update(result_received=True, is_error=bool(part.get("is_error")))
                    content = part.get("content", [])
                    row["image_count"] = sum(p.get("type") == "image" for p in content) if isinstance(content, list) else 0
                    texts = [p["text"] for p in content if p.get("type") == "text"] if isinstance(content, list) else [content]
                    for value in texts:
                        try:
                            result = json.loads(value)
                        except (TypeError, ValueError):
                            continue
                        if isinstance(result, dict):
                            row["returned_candidate"] = result.get("candidate")
                            row["returned_error"] = result.get("error")
    return list(found.values())


def extent(opening):
    points = opening["vertices"]
    return {axis: [min(p[i] for p in points), max(p[i] for p in points)]
            for i, axis in enumerate(("x", "y", "z"))}


def analyze(number, ids):
    run, = BASE.glob(f"*run{number}")
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path.relative_to(BASE))] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    summary = read(run / "summary.json")
    final = summary["delivery"]["candidate"]
    selected_source = read(run / final / "source_model.json")
    source_versions = [(p.parent.name, read(p)) for p in sorted(run.glob("candidate_*/source_model.json"))]
    manifest = read(run / "inputs.json")
    stream = run / "agent_stream.jsonl.gz"
    hashes[str(stream.relative_to(BASE))] = hashlib.sha256(stream.read_bytes()).hexdigest()
    actions = calls(stream)
    claims = [read(p) for p in sorted((run / "claims").glob("claim_*.json"))]
    drafts = [(p.parent.name, read(p)) for p in sorted(run.glob("plan_drafts/*/plan.json"))]
    rows = []
    for label, identity in zip(LABELS, ids):
        selected, = [o for o in selected_source["openings"] if o["id"] == identity]
        history = []
        for name, source in source_versions:
            matching = [o for o in source["openings"] if o["id"] == identity]
            if matching:
                opening, = matching
                history.append(dict(candidate=name, extent=extent(opening),
                                    host=opening["host_boundary_id"], spaces=opening["space_ids"]))
        linked = [c for c in claims if {"kind": "window", "id": identity} in c["claim"]["objects"]]
        interventions = []
        for action in actions:
            if action["tool"] not in {"revise_bim", "confirm_claims"}:
                continue
            operations = json.loads(action["input"]["operations_json"])
            selected_ops = [op for op in operations if op.get("id") == identity]
            if selected_ops:
                interventions.append({**{k: v for k, v in action.items() if k != "input"},
                    "candidate": action["input"].get("candidate"), "operations": selected_ops})
        floor, local_id = identity.split(":", 1)
        declarations = [dict(draft=name, floor_id=floor,
            anchors={axis: plan[axis + "_anchors"] for axis in ("x", "y")}, opening=opening)
            for name, plan in drafts if plan["floor_id"] == floor
            for opening in plan["openings"] if opening["id"] == local_id]
        rows.append(dict(label=label, object_id=identity, final_extent=extent(selected),
            plan_declarations=declarations,
            source_history=history, claims=[{k: c[k] for k in
                ("id", "claim", "resolved_values", "sources", "verification")} for c in linked],
            interventions=interventions))
    return dict(run=run.name, selected_candidate=final, response_completed=summary["agent_response_completed"],
        image_sha256={name: row["sha256"] for name, row in manifest["images"].items()},
        objects=rows, original_views=[a for a in actions if a["tool"] == "view_image"],
        source_elevation_views=[a for a in actions if a["tool"] == "view_elevation_candidate"],
        reference_reads=[a for a in actions if a["tool"] == "get_bim_reference"],
        end_actions=actions[-2:], evidence_sha256=hashes)


def main():
    result = dict(model_calls=0, runs=[analyze(n, ids) for n, ids in OBJECTS.items()],
        interpretation="Descriptive object histories. No causal effect estimate or automatic drawing-truth verdict. Claims/confirmations are model observations, not independent evaluation.",
        limitations=["Three development-selected window identities in five completed sm21 runs; not an unbiased success sample.",
                     "Run conditions differ. Preserve per-run results, do not pool success rates.",
                     "Originals and independent audits establish correctness separately; correct execution of a wrong observation is still a wrong result."])
    target = HERE / "object_traces.json"
    with target.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"runs": len(result["runs"]), "object_traces": sum(len(r["objects"]) for r in result["runs"]), "model_calls": 0}))


if __name__ == "__main__":
    main()
