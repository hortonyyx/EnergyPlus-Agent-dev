#!/usr/bin/env python3
"""CLI wrapper for deterministic reading CV probes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent.reading.cv_toolbox import (  # noqa: E402
    allocate_sidecar_path,
    crop_zoom,
    overlay_logger,
    prescan_elevation,
    prescan_plan,
    px_m_calibrator,
    storey_line_profiler,
    wall_line_profiler,
    window_cc_detector,
    write_sidecar,
)


def _bbox(value: str) -> list[float]:
    parts = [float(part) for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("--bbox must be x0,y0,x1,y1")
    return parts


def _json_arg(value: str):
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--recipe", default="clean_vector_v1")
    parser.add_argument("--bbox", type=_bbox)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--sidecar-name", default="auto")


def _overlay_candidates(payload: dict, default_status: str = "undecided") -> list[dict]:
    candidates = []
    for result in payload.get("results", []):
        candidates.append(
            {
                "candidate_id": result["candidate_id"],
                "geometry": result.get("geometry") or result.get("anchor_px", {}).get("value", {}),
                "status": default_status,
                "reason": "cv_probe automatic overlay",
            }
        )
    return candidates


def _reject_nested_prescan_out_dir(out_dir: Path) -> str:
    """F-1: the prescan tool itself appends ``cv_evidence/<stem>/prescan/`` to
    ``--out-dir``. If the caller already concatenated either of those layers
    (``--out-dir`` ends in ``cv_evidence`` or ``prescan``), the result is a nested
    ``.../cv_evidence/.../cv_evidence/...`` that the isolation copy-guard does
    NOT recognize, so it silently never reaches staging. Fail-closed here with
    the correct example rather than writing files in the wrong place. Returns an
    error message when nested, else an empty string."""
    last = Path(out_dir).name
    if last in ("cv_evidence", "prescan"):
        return (
            f"--out-dir must be the reading root; the tool appends "
            f"cv_evidence/<stem>/prescan/ itself, so a path ending in {last!r} "
            f"would nest and never reach staging. Example: --out-dir <RUN>/0_reading"
        )
    return ""


def _write(args: argparse.Namespace, payload: dict, crop_chain: list[dict] | None, overlay_candidates: list[dict]) -> Path:
    sidecar_path = allocate_sidecar_path(args.out_dir, args.image, payload["tool"], args.sidecar_name)
    overlay_path = sidecar_path.with_name(f"{sidecar_path.stem}_overlay.png")
    if overlay_candidates:
        overlay_payload = overlay_logger(
            args.image,
            overlay_candidates,
            output_path=overlay_path,
            recipe_id=args.recipe,
            source_name=args.image.name,
        )
        payload.setdefault("diagnostics", {})["overlay_decisions"] = overlay_payload["diagnostics"]["decisions"]
    else:
        overlay_path = None
    return write_sidecar(sidecar_path, args.image, payload, crop_chain=crop_chain, overlay_path=overlay_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="tool", required=True)

    p = subparsers.add_parser("crop_zoom")
    _common(p)

    p = subparsers.add_parser("wall_line_profiler")
    _common(p)
    p.add_argument("--axis", required=True, choices=["row", "col"])

    p = subparsers.add_parser("storey_line_profiler")
    _common(p)

    p = subparsers.add_parser("px_m_calibrator")
    _common(p)
    p.add_argument("--anchors-json", required=True, type=_json_arg)
    p.add_argument("--residual-warn-px", type=float)
    p.add_argument("--residual-warn-m", type=float)

    p = subparsers.add_parser("window_cc_detector")
    _common(p)
    p.add_argument("--min-area", type=int)
    p.add_argument("--min-width", type=float)
    p.add_argument("--min-height", type=float)
    p.add_argument("--max-width", type=float)
    p.add_argument("--max-height", type=float)
    p.add_argument("--min-aspect", type=float)
    p.add_argument("--max-aspect", type=float)
    p.add_argument("--merge-gap", type=float)
    p.add_argument("--merge-overlap-ratio", type=float)
    p.add_argument("--merge-iou", type=float)

    p = subparsers.add_parser("overlay_logger")
    _common(p)
    p.add_argument("--candidates-json", required=True, type=_json_arg)

    p = subparsers.add_parser("prescan-plan")
    _common(p)
    p.add_argument("--capability-profile", default="orthogonal_polygon")
    p.add_argument("--no-cc", action="store_true")
    p.add_argument("--min-strength", type=float)
    p.add_argument("--min-line-len-px", type=float)
    p.add_argument("--label", default="prescan")

    p = subparsers.add_parser("prescan-elevation")
    _common(p)
    p.add_argument("--capability-profile", default="rectangular")
    p.add_argument("--no-cc", action="store_true")
    p.add_argument("--min-strength", type=float)
    p.add_argument("--min-line-len-px", type=float)
    p.add_argument("--label", default="prescan")

    args = parser.parse_args(argv)
    if args.tool == "crop_zoom":
        if args.bbox is None:
            parser.error("crop_zoom requires --bbox")
        sidecar_path = allocate_sidecar_path(args.out_dir, args.image, "crop_zoom", args.sidecar_name)
        crop_path = sidecar_path.with_name(f"{sidecar_path.stem}_crop.png")
        payload, _crop, crop_chain = crop_zoom(
            args.image,
            args.bbox,
            scale=args.scale,
            output_path=crop_path,
            recipe_id=args.recipe,
            source_name=args.image.name,
        )
        overlay_path = sidecar_path.with_name(f"{sidecar_path.stem}_overlay.png")
        overlay_payload = overlay_logger(
            args.image,
            [{"candidate_id": payload["results"][0]["candidate_id"], "geometry": {"kind": "bbox", "bbox_px": args.bbox}, "status": "accepted", "reason": "crop region"}],
            output_path=overlay_path,
            recipe_id=args.recipe,
            source_name=args.image.name,
        )
        payload.setdefault("diagnostics", {})["overlay_decisions"] = overlay_payload["diagnostics"]["decisions"]
        write_sidecar(sidecar_path, args.image, payload, crop_chain=crop_chain, overlay_path=overlay_path)
    elif args.tool == "wall_line_profiler":
        payload, crop_chain = wall_line_profiler(
            args.image,
            axis=args.axis,
            recipe_id=args.recipe,
            bbox_px=args.bbox,
            scale=args.scale,
            source_name=args.image.name,
        )
        _write(args, payload, crop_chain, _overlay_candidates(payload))
    elif args.tool == "storey_line_profiler":
        payload, crop_chain = storey_line_profiler(
            args.image,
            recipe_id=args.recipe,
            bbox_px=args.bbox,
            scale=args.scale,
            source_name=args.image.name,
        )
        _write(args, payload, crop_chain, _overlay_candidates(payload))
    elif args.tool == "px_m_calibrator":
        payload = px_m_calibrator(
            args.anchors_json,
            recipe_id=args.recipe,
            residual_warn_px=args.residual_warn_px,
            residual_warn_m=args.residual_warn_m,
            source_name=args.image.name,
        )
        candidates = []
        for anchor in args.anchors_json:
            if anchor["axis"] == "xy":
                continue
            if anchor["axis"] == "x":
                geometry = {"kind": "line", "axis": "col", "x_px": anchor["px_a"]}
            else:
                geometry = {"kind": "line", "axis": "row", "y_px": anchor["px_a"]}
            candidates.append({"candidate_id": f"{payload['results'][0]['candidate_id']}:{len(candidates)+1}", "geometry": geometry, "status": "accepted", "reason": "calibration anchor"})
        _write(args, payload, [], candidates)
    elif args.tool == "window_cc_detector":
        payload, crop_chain = window_cc_detector(
            args.image,
            recipe_id=args.recipe,
            min_area_px=args.min_area,
            bbox_px=args.bbox,
            scale=args.scale,
            min_width_px=args.min_width,
            min_height_px=args.min_height,
            max_width_px=args.max_width,
            max_height_px=args.max_height,
            min_aspect=args.min_aspect,
            max_aspect=args.max_aspect,
            merge_gap_px=args.merge_gap,
            merge_overlap_ratio=args.merge_overlap_ratio,
            merge_iou=args.merge_iou,
            source_name=args.image.name,
        )
        _write(args, payload, crop_chain, _overlay_candidates(payload))
    elif args.tool == "overlay_logger":
        sidecar_path = allocate_sidecar_path(args.out_dir, args.image, "overlay_logger", args.sidecar_name)
        overlay_path = sidecar_path.with_name(f"{sidecar_path.stem}_overlay.png")
        payload = overlay_logger(
            args.image,
            args.candidates_json,
            output_path=overlay_path,
            recipe_id=args.recipe,
            source_name=args.image.name,
        )
        write_sidecar(sidecar_path, args.image, payload, crop_chain=[], overlay_path=overlay_path)
    elif args.tool in ("prescan-plan", "prescan-elevation"):
        # F-1: reject a nested --out-dir (caller already appended a layer the tool
        # adds itself) before writing anything, then echo the final landing path.
        reason = _reject_nested_prescan_out_dir(args.out_dir)
        if reason:
            print(reason, file=sys.stderr)
            return 2
        prescan_fn = prescan_plan if args.tool == "prescan-plan" else prescan_elevation
        candidates_path, _overlay_path = prescan_fn(
            args.image,
            out_dir=args.out_dir,
            recipe_id=args.recipe,
            capability_profile=args.capability_profile,
            include_cc=not args.no_cc,
            min_strength=args.min_strength,
            min_line_len_px=args.min_line_len_px,
            label=args.label,
        )
        print(str(Path(candidates_path).resolve()))
    else:
        parser.error(f"unknown tool: {args.tool}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
