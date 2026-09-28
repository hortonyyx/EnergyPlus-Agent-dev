"""Frozen prechange view_profile from 2ef03895, for this experiment only."""
import io
import json
from scripts.tool_scripts.run_bim_agent import (
    PILImage, ImageDraw, Image, digest, dump, _profile_axis, _inclusive_runs,
    _empty_profile_diagnostics,
)

def view_profile(self, name, box, axis, rgb, tolerance, min_fraction):
    """Return a checkable profile table and image without assigning semantics."""
    import numpy as np
    if (not isinstance(min_fraction, (int, float)) or isinstance(min_fraction, bool)
            or not 0 < min_fraction <= 1):
        raise ValueError("min_fraction must be a number greater than 0 and at most 1")
    with PILImage.open(self.image_path(name)) as raw:
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= raw.width and 0 <= y0 < y1 <= raw.height):
            raise ValueError("box outside original image bounds")
        crop = raw.convert("RGB").crop(box)
        original_size = raw.size
        pixels = np.asarray(crop).astype(float)
    if len(rgb) != 3 or not all(0 <= c <= 255 for c in rgb) or not 0 <= tolerance <= 442:
        raise ValueError("RGB in 0..255 and distance tolerance in 0..442 required")
    if axis not in {"x", "y"}:
        raise ValueError("axis must be x or y")
    mask = np.linalg.norm(pixels - np.asarray(rgb), axis=2) <= tolerance
    counts, minimum_count, support_length, runs = _profile_axis(mask, box, axis, min_fraction)
    projection_offset = x0 if axis == "x" else y0
    support_offset = y0 if axis == "x" else x0
    candidates = [{"id": f"C{i + 1:02d}", **row} for i, row in enumerate(runs)]
    other_axis = "y" if axis == "x" else "x"
    _, other_minimum, other_length, other_runs = _profile_axis(mask, box, other_axis, min_fraction)
    edge_support = {}
    for edge, support, offset in (("left", mask[:, 0], y0), ("right", mask[:, -1], y0),
                                  ("top", mask[0, :], x0), ("bottom", mask[-1, :], x0)):
        edge_support[edge] = [[lo + offset, hi + offset] for lo, hi in _inclusive_runs(support)]

    # Keep the original crop untouched on the left.  The right panel is a
    # separate exact mask view with candidate bands and peaks labelled.
    panel_pixels = np.full((crop.height, crop.width, 3), 255, dtype=np.uint8)
    panel_pixels[mask] = (150, 150, 150)
    panel = PILImage.fromarray(panel_pixels, "RGB")
    draw = ImageDraw.Draw(panel)
    for candidate in candidates:
        lo = candidate["pixels"][0] - projection_offset
        hi = candidate["pixels"][1] - projection_offset
        peak = candidate["peak"] - projection_offset
        if axis == "x":
            draw.rectangle((lo, 0, hi, crop.height - 1), outline=(220, 0, 120), width=1)
            for support_lo, support_hi in candidate["support_intervals_at_peak"]:
                draw.line((peak, support_lo - support_offset,
                           peak, support_hi - support_offset), fill=(0, 110, 220), width=1)
            label_xy = (lo + 1, 1)
        else:
            draw.rectangle((0, lo, crop.width - 1, hi), outline=(220, 0, 120), width=1)
            for support_lo, support_hi in candidate["support_intervals_at_peak"]:
                draw.line((support_lo - support_offset, peak,
                           support_hi - support_offset, peak), fill=(0, 110, 220), width=1)
            label_xy = (1, lo + 1)
        draw.text(label_xy, candidate["id"], fill="black")
    combined = PILImage.new("RGB", (crop.width * 2 + 3, crop.height), "white")
    combined.paste(crop, (0, 0))
    combined.paste(panel, (crop.width + 3, 0))
    ImageDraw.Draw(combined).rectangle((crop.width, 0, crop.width + 2, crop.height - 1), fill="black")

    folder = self.run / "pixel_profiles"
    folder.mkdir(exist_ok=True)
    stem = f"profile_{len(list(folder.glob('profile_*.json'))) + 1:03d}"
    image_path = folder / f"{stem}.png"
    record_path = folder / f"{stem}.json"
    combined.save(image_path)
    result = {
        "name": name,
        "profile_id": stem,
        "image_sha256": self.manifest["images"][name]["sha256"],
        "axis": axis,
        "box_original_pixels": box,
        "rgb": rgb,
        "tolerance": tolerance,
        "min_fraction": float(min_fraction),
        "minimum_count": minimum_count,
        "support_length": support_length,
        "matching_pixels": int(mask.sum()),
        "candidates": candidates,
        "cross_axis_profile": {
            "axis": other_axis, "min_fraction": float(min_fraction),
            "minimum_count": other_minimum, "support_length": other_length,
            "runs": other_runs,
            "note": "Same exact mask and fraction, measured along the other axis. "
                    "Compare long traces with local junction peaks; neither is a wall label. "
                    "For bindable C IDs on this axis, request a profile using this axis.",
        },
        "crop_context": {
            "edge_support_intervals": edge_support,
            "suggested_view_box": [max(0, x0 - 32), max(0, y0 - 32),
                                   min(original_size[0], x1 + 32), min(original_size[1], y1 + 32)],
            "note": "Edge intervals are matching pixels on the crop border (right/bottom are exclusive "
                    "box limits, so samples are at right-1/bottom-1). A crop edge is not an object endpoint. "
                    "The suggested box is only an initial 32px context expansion; inspect further as needed "
                    "to establish both endpoints and adjoining space boundaries. No continuation is inferred.",
        },
        "profile_image": str(image_path.relative_to(self.run)),
        "profile_record": str(record_path.relative_to(self.run)),
        "profile_image_sha256": digest(image_path),
        "panel_layout": {
            "original_crop_combined_pixels": [0, 0, crop.width, crop.height],
            "mask_panel_combined_pixels": [crop.width + 3, 0, combined.width, crop.height],
            "separator_width": 3,
        },
        "panel_note": "Left is the untouched original crop. Right is an exact color-distance mask: magenta outlines candidate bands; blue marks only actual support at the peak coordinate. Marks are coordinate references, not entities. Right-panel local coordinates correspond to the same original crop after removing its combined-image offset.",
        "evidence_note": "Support intervals are measured only at each candidate peak. They do not prove a whole band is continuous or identify a wall. Filtered or empty results do not prove an object is absent.",
        "remaining_seconds": self.remaining_seconds(),
    }
    diagnostic = _empty_profile_diagnostics(pixels, rgb, counts, minimum_count, support_length)
    if diagnostic is not None:
        result["empty_filter_diagnostics"] = diagnostic
    returned = combined.copy()
    returned.thumbnail((1600, 1600))
    data = io.BytesIO()
    returned.save(data, "PNG")
    result["returned_size"] = list(returned.size)
    result["original_pixels_per_returned_pixel"] = [
        combined.width / returned.width, combined.height / returned.height]
    result["display_note"] = "For a returned-image point (rx, ry), first multiply by original_pixels_per_returned_pixel to obtain full combined-image coordinates (fx, fy). On the left, original image coordinates are (box_left + fx, box_top + fy). On the right, subtract mask_panel_combined_pixels[0] from fx before adding box_left. Prefer candidates and support intervals, which already use original-image coordinates."
    dump(record_path, result)
    self.log("view_pixel_profile", {"name": name, "box": box, "rgb": rgb,
                                    "tolerance": tolerance, "min_fraction": min_fraction,
                                    "result": result})
    return [Image(data=data.getvalue(), format="png"), json.dumps(result)]
