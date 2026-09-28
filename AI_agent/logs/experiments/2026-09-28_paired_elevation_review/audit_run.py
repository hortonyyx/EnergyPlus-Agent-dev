"""Post-run public behavior, actual image transport and independent geometry audit."""
import argparse
import base64
from collections import Counter
import gzip
import hashlib
import importlib
import io
import json

from PIL import Image
from scripts.tool_scripts.run_bim_agent import Toolkit, coordinate_grid_view
from src.agent.geometry.source_elevation_view import render_source_elevation
from .batch import HERE, ROOT, RUN, PRIOR, load, save, sha


def completed():
    summary, receipt = load(RUN / "summary.json"), load(RUN / "agent_receipt.json")
    assert summary["agent_response_completed"] and receipt.get("returncode") == 0
    assert not receipt.get("timed_out") and not receipt.get("routing_error")
    assert not receipt.get("result", {}).get("is_error")
    assert receipt["actual_model"].startswith("claude-sonnet-")
    assert summary["subscription_invocations"] == len(list(RUN.glob("*_receipt.json"))) == 1
    frozen = load(HERE / "frozen.json")
    assert frozen == load(RUN / "experiment_condition.json")
    assert load(RUN / "batch_approval.json") == load(HERE / "approval.json")
    assert load(RUN / "agent_request.json") == frozen["request"]
    assert sha(RUN / "seed/proposal.json") == frozen["seed_proposal_sha256"]
    for name, value in frozen["execution_sha256"].items():
        assert sha(ROOT / name) == sha(RUN / "runtime_snapshot" / name) == value
    for name, info in frozen["images"].items():
        assert sha(RUN / "images" / name) == info["sha256"]
    return summary, receipt


def verify_original(meta, raw):
    saved = Toolkit(RUN).read_image_view(meta["view_id"])
    assert saved["sha256"] == meta["view_record_sha256"]
    assert hashlib.sha256(raw).hexdigest() == saved["record"]["returned_png_sha256"] == meta["returned_png_sha256"]
    assert sha(RUN / "images" / meta["name"]) == meta["image_sha256"]
    region = meta["box_original_pixels"]
    with Image.open(RUN / "images" / meta["name"]) as original:
        expected = original.convert("RGB").crop(region)
    if meta["display_scale_requested"] == 1:
        expected.thumbnail((1600, 1600))
    else:
        expected = expected.resize(tuple(meta["returned_size"]), Image.Resampling.NEAREST)
    if meta["coordinate_grid"]["shown"]:
        expected, _ = coordinate_grid_view(expected, region)
    actual = Image.open(io.BytesIO(raw)).convert("RGB")
    assert expected.size == actual.size and expected.tobytes() == actual.tobytes()
    return dict(view_id=meta["view_id"], image=meta["name"], box=region,
        actual_transport_sha256=hashlib.sha256(raw).hexdigest(), pixels_match_original=True)


def behavior():
    completed()
    archive = RUN / "agent_stream.jsonl.gz"
    raw = gzip.decompress(archive.read_bytes()) if archive.exists() else (RUN / "agent_stream.jsonl").read_bytes()
    calls, texts, originals, elevations, seen = {}, [], [], [], set()
    for line in raw.splitlines():
        event = json.loads(line)
        blocks = event.get("message", {}).get("content", [])
        for block in blocks if isinstance(blocks, list) else []:
            kind = block.get("type")
            if kind == "text" and event.get("type") == "assistant":
                texts.append(dict(after_tool_count=len(calls), text=block["text"]))
            if kind == "tool_use":
                calls[block["id"]] = dict(ordinal=len(calls)+1,
                    tool=block["name"].removeprefix("mcp__bim__"), input=block.get("input", {}),
                    previously_returned_views=sorted(seen))
            if kind != "tool_result":
                continue
            call = calls[block["tool_use_id"]]
            call["is_error"] = bool(block.get("is_error"))
            parts = block.get("content", [])
            parts = [dict(type="text", text=parts)] if isinstance(parts, str) else parts
            pictures = [base64.b64decode(p["source"]["data"]) for p in parts if p.get("type") == "image"]
            call["returned_image_count"] = len(pictures)
            if call["is_error"]:
                call["error_text"] = [p["text"] for p in parts if p.get("type") == "text"]
                continue
            values = []
            for part in parts:
                if part.get("type") != "text":
                    continue
                try:
                    value = json.loads(part["text"])
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict):
                    values.append(value)
            if call["tool"] == "view_elevation_candidate":
                meta = next(v for v in values if v.get("mode") == "source_elevation_view")
                source = load(RUN / meta["candidate"] / "source_model.json")
                pic, reproduced = render_source_elevation(source, meta["facade"])
                assert all(meta[key] == value for key, value in reproduced.items())
                data = io.BytesIO(); pic.save(data, "PNG")
                assert pictures[-1] == data.getvalue() == (RUN / meta["elevation_image"]).read_bytes()
                assert load(RUN / meta["review_file"]) == meta
                assert len(pictures) == (2 if "original_view" in meta else 1)
                if "original_view" in meta:
                    original = verify_original(meta["original_view"], pictures[0])
                    originals.append(dict(tool=call["tool"], ordinal=call["ordinal"], **original))
                    seen.add(original["view_id"])
                elevations.append(dict(ordinal=call["ordinal"], candidate=meta["candidate"],
                    facade=meta["facade"], source_model_sha256=meta["source_model_sha256"],
                    original_image=meta.get("original_view", {}).get("name"),
                    exact_source_image_and_metadata=True, review_file=meta["review_file"]))
            elif call["tool"] in {"view_image", "record_claim", "view_claim_evidence", "replace_claim_sources"}:
                metas = [v for v in values if "view_id" in v and "returned_png_sha256" in v]
                metas = metas or [m for v in values for m in v.get("evidence_previews", [])]
                assert len(metas) == len(pictures), (call["tool"], len(metas), len(pictures))
                for meta, picture in zip(metas, pictures):
                    original = verify_original(meta, picture)
                    originals.append(dict(tool=call["tool"], ordinal=call["ordinal"], **original))
                    seen.add(original["view_id"])
            if call["tool"] == "replace_claim_sources":
                assert set(call["input"]["view_ids"]) <= set(call["previously_returned_views"])
    claim_refs = []
    for path in sorted((RUN / "claims").glob("claim_*.json")):
        claim = load(path)
        for ref in claim["sources"]:
            if "view_id" in ref:
                assert ref["view_id"] in seen
                assert sha(RUN / "image_views" / (ref["view_id"] + ".json")) == ref["view_sha256"]
                claim_refs.append(dict(claim=path.stem, view_id=ref["view_id"]))
    assert not any(c["tool"] == "review_detail" for c in calls.values())
    save(RUN / "behavior_audit.json", dict(completed=True, model_calls_for_audit=0,
        public_actions=list(calls.values()), public_assistant_text=texts,
        counts=dict(tool_calls=len(calls), errors=sum(c.get("is_error", False) for c in calls.values()),
            original_returns=len(originals), elevation_returns=len(elevations), paired_returns=sum(bool(e["original_image"]) for e in elevations)),
        original_transport=originals, elevation_transport=elevations, claim_view_references=claim_refs,
        interpretation="Public requests/results and assistant text only; image exposure and claim linkage do not certify semantic truth or causal benefit."))
    print(json.dumps(dict(tool_calls=len(calls), original_returns=len(originals), elevation_returns=len(elevations))))


def evaluate():
    summary, receipt = completed()
    candidate = load(RUN / "delivery.json")["candidate"]
    shared = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
    source, _, _ = shared.replay_final(RUN, candidate)
    save(RUN / "producer_replay.json", dict(candidate=candidate, source_model_sha256=source["source_model_sha256"],
        source_display_replay_exact=True, input_and_execution_hashes_verified=True))
    # Existing independent checks and tolerances; only the run target is changed.
    from scripts.tool_scripts.evaluate_bim_agent import evaluate as evaluate_bim
    from src.agent.judge.gt import load_gt_document
    output = RUN / "evaluation/gt"
    if not (output / "summary.json").exists():
        evaluate_bim(RUN, "sm21_anchor", modelling_task="reconstruction", out=output,
            reference_scope="Six originals plus unverified saved proposal; no old claims or evaluation. GT only after model completion.")
    partition = load(output / f"{candidate}_partition.json")
    legacy = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings")
    openings = legacy.diagnostic(source, load_gt_document("sm21_anchor"), partition)
    save(output / "final_opening_diagnostic.json", openings)
    original = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original")
    original.audit(RUN)
    identity = importlib.import_module("AI_agent.logs.experiments.2026-09-28_sm21_threshold_feedback_setup.postrun.room_identity")
    save(RUN / "room_identity_audit.json", identity.review(RUN))
    archive = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_continuation_setup.audit_run")
    transports = archive.archive_streams(RUN)
    previous = load(RUN / "seed/source_model.json")
    changes = []
    for path in sorted(RUN.glob("candidate_*/source_model.json")):
        current = load(path)
        groups = {}
        for group in ["floors", "spaces", "boundaries", "openings", "connections"]:
            identity_key = "opening_id" if group == "connections" else "id"
            a, b = ({r[identity_key]: r for r in s[group]} for s in (previous, current))
            groups[group] = dict(added=sorted(set(b)-set(a)), removed=sorted(set(a)-set(b)),
                changed=[dict(id=k, fields={f: dict(before=a[k].get(f), after=b[k].get(f))
                    for f in set(a[k]) | set(b[k]) if a[k].get(f) != b[k].get(f)})
                    for k in sorted(set(a)&set(b)) if a[k] != b[k]])
        changes.append(dict(candidate=path.parent.name, groups=groups))
        previous = current
    save(RUN / "source_changes.json", dict(sequence=changes, starting_candidate="seed"))
    strict = partition["comparison"]
    identity_codes = {"source_space_split", "source_spaces_merged", "missing_source_space", "extra_source_space", "floor_assignment_changed", "candidate_spaces_overlap"}
    report = dict(candidate=candidate, source_model_sha256=source["source_model_sha256"],
        input_mode="saved_proposal_paired_elevation_recovery", input_and_producer_hashes_verified=True,
        source_display_replay_exact=True, invocations=1, actual_models=[receipt["actual_model"]],
        elapsed_seconds=summary["elapsed_seconds"], estimated_usd_not_bill=summary["estimated_cost_usd"],
        counts={k: len(source[k]) for k in ["floors", "spaces", "boundaries", "openings", "connections"]},
        kinds=dict(Counter(r["kind"] for r in source["openings"])),
        strict_partition_status=strict["status"], matched_spaces=strict["matched_count"],
        space_identity_findings=[r for r in strict["findings"] if r["code"] in identity_codes],
        topology_findings=partition["topology_findings"], original_openings=load(RUN / "evaluation/original_openings.json"),
        matched_exterior=len(openings["matched"]),
        exterior_parameters_match=sum(all(r.get(k) is True for k in ["along_within_judge_tolerance", "width_within_judge_tolerance", "z_within_judge_tolerance"]) for r in openings["matched"]),
        exterior_height_differences=[r for r in openings["matched"] if any(d > 1e-6 for d in r["z_endpoint_delta_m"])],
        height_mismatches=[r for r in openings["matched"] if not r["z_within_judge_tolerance"]],
        unmatched_reference=openings["unmatched_reference"], unmatched_built_exterior=openings["unmatched_built_exterior"],
        transported_images=sum(t["image_count"] for t in transports),
        source_assumptions=source["assumptions"], unresolved=source["generation"]["unresolved"],
        original_reference_sha256=sha(original.HERE / "original_reference.json"),
        limits=load(HERE / "frozen.json")["limits"])
    save(RUN / "postrun_audit.json", report)
    print(json.dumps({k:report[k] for k in ["candidate", "counts", "strict_partition_status", "exterior_parameters_match", "height_mismatches"]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["behavior", "evaluate"])
    behavior() if parser.parse_args().action == "behavior" else evaluate()
