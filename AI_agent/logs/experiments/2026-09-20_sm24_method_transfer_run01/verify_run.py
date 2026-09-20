"""Post-generation, read-only audit of a standalone BIM-agent run.

Run only after summary.json exists. GT is loaded only with --gt and is never
passed to the generator. The report checks reproducibility and transport; a
passing report alone does not establish drawing fidelity or user acceptance.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tempfile

from PIL import Image, ImageChops

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from src.agent.execution.source_proposal import export_source_proposal


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same_pixels(returned: bytes, saved: Path, *, box=None, thumbnail=False) -> bool:
    with Image.open(io.BytesIO(returned)) as actual, Image.open(saved) as original:
        expected = original.convert("RGB")
        if box is not None:
            expected = expected.crop(tuple(box))
        if thumbnail:
            expected.thumbnail((1600, 1600))
        observed = actual.convert("RGB")
        return observed.size == expected.size and ImageChops.difference(observed, expected).getbbox() is None


def input_checks(run: Path, manifest: dict, original_dir: Path | None) -> list[dict]:
    rows = []
    for name, info in manifest.get("images", {}).items():
        frozen = run / "images" / name
        expected = info["sha256"]
        row = {"path": str(frozen.relative_to(run)), "expected_sha256": expected,
               "frozen_matches": frozen.is_file() and sha(frozen) == expected}
        if row["frozen_matches"]:
            with Image.open(frozen) as image:
                row["size_matches"] = list(image.size) == info["size"]
        else:
            row["size_matches"] = False
        if original_dir is not None:
            original = original_dir / name
            row["original_matches"] = original.is_file() and sha(original) == expected
        rows.append(row)
    building = manifest.get("building_input")
    if building:
        frozen = run / building["frozen_path"]
        row = {"path": building["frozen_path"], "expected_sha256": building["raw_sha256"],
               "frozen_matches": frozen.is_file() and sha(frozen) == building["raw_sha256"]}
        if original_dir is not None:
            original = Path(building["source_path"])
            row["original_matches"] = original.is_file() and sha(original) == building["raw_sha256"]
        rows.append(row)
    return rows


def replay(run: Path, candidate: str, manifest: dict) -> dict:
    folder = run / candidate
    proposal_path = folder / "proposal.json"
    source_path = folder / "source_model.json"
    display_path = folder / "display_geometry.json"
    report = load(folder / "report.json")
    source = load(source_path)
    proposal = load(proposal_path)
    result = {"candidate": candidate,
              "proposal_hash_matches_report": sha(proposal_path) == report.get("proposal_sha256"),
              "source_hash_matches_report": source.get("source_model_sha256") == report.get("source_model_sha256"),
              "input_manifest_matches_provenance":
                  source.get("generation", {}).get("provenance", {}).get("input_manifest_sha256") == sha(run / "inputs.json"),
              "saved_validation": source.get("validation", {}).get("status"),
              "saved_counts": {key: len(source.get(key, [])) for key in
                               ("spaces", "boundaries", "openings", "connections", "unbuilt_openings", "unsupported")}}
    with tempfile.TemporaryDirectory(prefix="bim_run_replay_") as temporary:
        destination = Path(temporary) / "candidate"
        reproduced = export_source_proposal(
            proposal, destination, provenance=source["generation"]["provenance"])
        result["replay_source_ready"] = reproduced.get("source_geometry_ready")
        result["source_bytes_identical"] = (destination / "source_model.json").read_bytes() == source_path.read_bytes()
        result["display_bytes_identical"] = (destination / "display_geometry.json").read_bytes() == display_path.read_bytes()
        result["report_counts_match_source"] = report.get("counts") == result["saved_counts"]
    return result


def _events(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def _expected_images(run: Path, name: str, arguments: dict, payload: dict) -> list[tuple[Path, list | None, bool]]:
    def path(value):
        return run / value
    if name == "view_pixel_profile" and payload.get("profile_image"):
        return [(path(payload["profile_image"]), None, True)]
    if name == "view_pixel_region_overview" and payload.get("overview_image"):
        return [(path(payload["overview_image"]), None, False)]
    if name == "view_pixel_region" and payload.get("region_image"):
        return [(path(payload["region_image"]), None, False)]
    if name in {"preview_space_trace", "view_space_trace"} and payload.get("trace_image"):
        return [(path(payload["trace_image"]), None, False)]
    if name == "view_candidate":
        floor = arguments.get("floor_id")
        candidate = arguments.get("candidate")
        if isinstance(floor, str) and isinstance(candidate, str):
            stem = "plan_" + floor.replace("/", "_").replace("\\", "_")
            if "/" in floor or "\\" in floor:
                stem += "_" + hashlib.sha256(floor.encode()).hexdigest()[:12]
            return [(run / candidate / (stem + ".png"), None, False)]
    if name == "overlay_candidate" and payload.get("overlay_image"):
        return [(path(payload["overlay_image"]), payload.get("box_original_pixels"), True)]
    if name in {"build_plan_bim", "build_bim", "build_parametric_bim", "revise_bim"}:
        specs = []
        draft = payload.get("plan_input", {}).get("draft_view", {})
        if draft.get("image_file") and not payload.get("source_geometry_ready"):
            specs.append((path(draft["image_file"]), None, False))
        specs.extend((path(item["overlay_image"]), None, True)
                     for item in payload.get("source_image_projections", []) if item.get("overlay_image"))
        specs.extend((path(item["plan_image"]), None, False)
                     for item in payload.get("source_plan_views", []) if item.get("plan_image"))
        return specs
    if name == "view_elevation_candidate":
        for key in ("elevation_image", "image_file"):
            if payload.get(key):
                return [(path(payload[key]), None, False)]
    return []


def image_transport(run: Path) -> dict:
    stream = run / "agent_stream.jsonl"
    if not stream.exists():
        stream = run / "agent_stream.jsonl.gz"
    if not stream.exists():
        return {"stream_present": False, "comparisons": [], "unpaired_image_returns": 0}
    calls = {}
    comparisons = []
    unpaired = 0
    for event in _events(stream):
        if event.get("type") == "assistant":
            for part in event.get("message", {}).get("content", []):
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    calls[part["id"]] = part
        if event.get("type") != "user":
            continue
        for result in event.get("message", {}).get("content", []):
            if not isinstance(result, dict) or result.get("type") != "tool_result":
                continue
            parts = result.get("content", [])
            if not isinstance(parts, list):
                continue
            images = [part for part in parts if isinstance(part, dict) and part.get("type") == "image"]
            if not images:
                continue
            call = calls.get(result.get("tool_use_id"), {})
            name = call.get("name", "").rsplit("__", 1)[-1]
            payload = {}
            for part in reversed(parts):
                if isinstance(part, dict) and part.get("type") == "text":
                    try:
                        value = json.loads(part["text"])
                    except (ValueError, KeyError, TypeError):
                        continue
                    if isinstance(value, dict):
                        payload = value
                        break
            specs = _expected_images(run, name, call.get("input", {}), payload)
            for index, part in enumerate(images):
                if index >= len(specs):
                    unpaired += 1
                    continue
                saved, box, thumbnail = specs[index]
                raw = base64.b64decode(part["source"]["data"])
                comparisons.append({"tool": name, "saved": str(saved.relative_to(run)),
                                    "saved_exists": saved.is_file(),
                                    "pixels_match": saved.is_file() and same_pixels(raw, saved, box=box, thumbnail=thumbnail)})
    return {"stream_present": True, "tool_calls": len(calls),
            "comparisons": comparisons, "unpaired_image_returns": unpaired,
            "note": "Unpaired returns include ordinary view_image crops without a saved rendered counterpart; this is not a transport failure."}


def model_usage(run: Path, summary: dict) -> dict:
    rows = []
    for path in sorted(run.glob("*_receipt.json")):
        receipt = load(path)
        result = receipt.get("result", {})
        rows.append({"receipt": path.name, "requested_model": receipt.get("requested_model"),
                     "actual_model": receipt.get("actual_model"), "channel": receipt.get("channel"),
                     "elapsed_seconds": receipt.get("elapsed_seconds"), "returncode": receipt.get("returncode"),
                     "timed_out": receipt.get("timed_out", False), "is_error": result.get("is_error"),
                     "usage": result.get("usage"), "modelUsage": result.get("modelUsage"),
                     "cli_estimated_cost_usd": result.get("total_cost_usd")})
    partial = sum(row["cli_estimated_cost_usd"] for row in rows
                  if isinstance(row["cli_estimated_cost_usd"], (int, float)))
    token_fields = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
    token_totals = {field: sum((row["usage"] or {}).get(field, 0) for row in rows)
                    for field in token_fields}
    return {"receipts": rows, "receipt_count_matches_summary": len(rows) == summary.get("subscription_invocations"),
            "requested_models": dict(Counter(row["requested_model"] for row in rows)),
            "actual_models": dict(Counter(row["actual_model"] for row in rows)),
            "token_totals": token_totals, "cli_estimated_cost_sum_usd": partial,
            "reported_partial_cost_matches_summary": abs(partial - summary.get("reported_partial_cost_usd", partial)) < 1e-8,
            "cost_note": "CLI estimate, not a subscription bill; modelUsage can include Claude CLI auxiliary models."}


def gt_openings(source: dict, translation: tuple[float, float, float] = (0, 0, 0)) -> dict:
    """One-to-one typed-v3 exterior opening comparison in existing world coordinates."""
    from src.agent.geometry.opening_review import facade_inventory
    from src.agent.judge.gt import load_gt_document
    from src.agent.judge.gt_schema import GroundTruthV3

    dx, dy, dz = translation
    gt = load_gt_document("sm24_anchor")
    if not isinstance(gt, GroundTruthV3) or gt.verification.status != "human_verified":
        raise ValueError("verified typed-v3 sm24 GT required")
    classifications = facade_inventory(source)["opening_classifications"]
    source_rows = []
    for item in source["openings"]:
        if not item.get("exterior") or item["kind"] not in {"window", "door"}:
            continue
        xy = sorted({(float(v[0]), float(v[1])) for v in item["vertices"]})
        z = sorted({float(v[2]) for v in item["vertices"]})
        classification = classifications.get(item["id"], {})
        facade = classification.get("facade")
        if len(xy) != 2 or len(z) != 2 or facade is None:
            source_rows.append({"id": item["id"], "kind": item["kind"], "facade": facade,
                                "space_ids": item["space_ids"], "host_boundary_id": item["host_boundary_id"],
                                "unmatchable_reason": classification.get("reason", "nonrectangular_or_unknown")})
            continue
        along_shift = dx if facade in {"North", "South"} else dy
        along = sorted((point[0] if facade in {"North", "South"} else point[1]) + along_shift for point in xy)
        plane = (xy[0][1] + dy) if facade in {"North", "South"} else (xy[0][0] + dx)
        source_rows.append({"id": item["id"], "kind": item["kind"], "facade": facade,
                            "along": along, "plane": plane,
                            "translated_line_xy": [[x + dx, y + dy] for x, y in xy],
                            "z": [height + dz for height in z], "space_ids": item["space_ids"],
                            "host_boundary_id": item["host_boundary_id"]})
    segments = {segment.id: segment for floor in gt.floors for segment in floor.boundary_segments}
    targets = [{"id": item.id, "kind": item.kind,
                "facade": segments[item.boundary_segment_id].facade_family,
                "plane": segments[item.boundary_segment_id].p1[1]
                    if segments[item.boundary_segment_id].facade_family in {"North", "South"}
                    else segments[item.boundary_segment_id].p1[0],
                "along": [item.world_along_interval.lo, item.world_along_interval.hi],
                "z": None if item.z_interval is None else [item.z_interval.lo, item.z_interval.hi],
                "host_zone_id": item.host_zone_id} for item in gt.openings]
    options = []
    for ti, target in enumerate(targets):
        for si, candidate in enumerate(source_rows):
            if (target["kind"], target["facade"]) != (candidate["kind"], candidate["facade"]) or "along" not in candidate:
                continue
            overlap = min(target["along"][1], candidate["along"][1]) - max(target["along"][0], candidate["along"][0])
            if overlap > 0:
                options.append((-overlap, ti, si))
    used_t, used_s, matches = set(), set(), []
    for _, ti, si in sorted(options):
        if ti in used_t or si in used_s:
            continue
        used_t.add(ti); used_s.add(si)
        target, candidate = targets[ti], source_rows[si]
        delta = [candidate["along"][i] - target["along"][i] for i in (0, 1)]
        matches.append({"gt_id": target["id"], "source_id": candidate["id"],
                        "kind": candidate["kind"], "facade": candidate["facade"],
                        "gt_host_zone_id": target["host_zone_id"], "source_space_ids": candidate["space_ids"],
                        "source_host_boundary_id": candidate["host_boundary_id"],
                        "source_translated_line_xy": candidate["translated_line_xy"],
                        "gt_plane_m": target["plane"], "source_plane_m": candidate["plane"],
                        "plane_delta_m": round(candidate["plane"] - target["plane"], 6),
                        "gt_along_m": target["along"], "source_along_m": candidate["along"],
                        "endpoint_delta_m": [round(x, 6) for x in delta],
                        "center_abs_error_m": round(abs(sum(delta) / 2), 6),
                        "width_error_m": round(delta[1] - delta[0], 6),
                        "gt_z_m": target["z"], "source_z_m": candidate["z"],
                        "z_endpoint_delta_m": None if target["z"] is None else
                            [round(candidate["z"][i] - target["z"][i], 6) for i in (0, 1)]})
    return {"mode": "post_generation_gt_only", "gt_schema": gt.schema_version,
            "gt_content_sha256": gt.content_sha256,
            "explicit_translation_m": list(translation),
            "basis": "kind, source-host-derived facade and positive world-coordinate overlap; caller-declared translation only; no registration fit",
            "scope": {"source_exterior": dict(Counter(row["kind"] for row in source_rows)),
                      "gt_exterior": dict(Counter(row["kind"] for row in targets))},
            "matches": sorted(matches, key=lambda row: (row["kind"], row["facade"], row["gt_along_m"])),
            "missing_gt_openings": [targets[i] for i in range(len(targets)) if i not in used_t],
            "extra_source_openings": [source_rows[i] for i in range(len(source_rows)) if i not in used_s],
            "limit": "GT has no per-opening interior-door targets; source room host correctness requires separate partition matching."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--candidate", help="Saved candidate; default is delivered candidate")
    parser.add_argument("--original-dir", type=Path, help="Optional original case_data directory for byte comparison")
    parser.add_argument("--gt", action="store_true", help="Post-generation typed-v3 external opening comparison")
    parser.add_argument("--translation-m", nargs=3, type=float, metavar=("X", "Y", "Z"), default=(0, 0, 0),
                        help="Explicit source-to-GT translation in metres for --gt; no rotation, scale or fitting")
    parser.add_argument("--translation-basis", default="", help="Original-drawing basis for a nonzero translation")
    args = parser.parse_args()
    if not all(math.isfinite(value) for value in args.translation_m):
        parser.error("--translation-m values must be finite")
    if not args.gt and any(args.translation_m):
        parser.error("--translation-m requires --gt")
    if any(args.translation_m) and not args.translation_basis.strip():
        parser.error("nonzero --translation-m requires --translation-basis")
    run = args.run.resolve()
    if not (run / "summary.json").is_file() or not (run / "agent_receipt.json").is_file():
        parser.error("run is still active or incomplete: summary.json and agent_receipt.json are required")
    summary = load(run / "summary.json")
    manifest = load(run / "inputs.json")
    candidate = args.candidate or (summary.get("delivery") or {}).get("candidate")
    if not candidate or candidate in {".", ".."} or "/" in candidate or "\\" in candidate:
        parser.error("choose a saved candidate with --candidate; no valid delivery candidate found")
    result = {"run": str(run), "candidate": candidate,
              "input_checks": input_checks(run, manifest, args.original_dir),
              "replay": replay(run, candidate, manifest),
              "image_transport": image_transport(run),
              "model_usage": model_usage(run, summary),
              "limits": ["Replay and pixel transport prove saved artifacts are consistent, not faithful to source drawings.",
                         "Visual BIM review, partition quality and user acceptance are separate."]}
    result["pass"] = (
        all(row["frozen_matches"] and row["size_matches"] if "size_matches" in row else row["frozen_matches"]
            for row in result["input_checks"])
        and all(row.get("original_matches", True) for row in result["input_checks"])
        and all(result["replay"][key] for key in
                ("proposal_hash_matches_report", "source_hash_matches_report", "input_manifest_matches_provenance",
                 "replay_source_ready", "source_bytes_identical", "display_bytes_identical", "report_counts_match_source"))
        and result["image_transport"]["stream_present"]
        and bool(result["image_transport"]["comparisons"])
        and all(row["pixels_match"] for row in result["image_transport"]["comparisons"])
        and result["model_usage"]["receipt_count_matches_summary"]
        and result["model_usage"]["reported_partial_cost_matches_summary"])
    (run / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.gt:
        source_path = run / candidate / "source_model.json"
        original_source_file_sha256 = sha(source_path)
        source = load(source_path)
        original = gt_openings(source)
        shifted = gt_openings(source, tuple(args.translation_m)) if any(args.translation_m) else None
        comparison = {"source_model_sha256": source["source_model_sha256"],
                      "original_source_file_sha256": original_source_file_sha256,
                      "original_source_unchanged": sha(source_path) == original_source_file_sha256,
                      "explicit_translation_m": args.translation_m,
                      "translation_basis": args.translation_basis,
                      "original_frame": original, "translated_frame": shifted,
                      "alignment_policy": "caller declared from original drawings; no GT-derived alignment"}
        (run / "opening_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "candidate": candidate,
                      "image_returns_compared": len(result["image_transport"]["comparisons"]),
                      "gt_matches_original": len(original["matches"]) if args.gt else "not_run",
                      "gt_matches_translated": len(shifted["matches"]) if args.gt and shifted else "not_run"}, ensure_ascii=False))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
