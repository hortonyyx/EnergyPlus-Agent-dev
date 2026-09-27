"""Frozen pre-change Toolkit.profile from f0c6e877; experiment control only."""
from scripts.tool_scripts.run_bim_agent import PILImage, _empty_profile_diagnostics


def profile(self, name, box, axis, rgb, tolerance):
    import numpy as np
    with PILImage.open(self.image_path(name)) as raw:
        x0,y0,x1,y1 = box
        if not (0 <= x0 < x1 <= raw.width and 0 <= y0 < y1 <= raw.height):
            raise ValueError("box outside original image bounds")
        pixels = np.asarray(raw.convert("RGB").crop(box)).astype(float)
    if len(rgb) != 3 or not all(0 <= c <= 255 for c in rgb) or not 0 <= tolerance <= 442:
        raise ValueError("RGB in 0..255 and distance tolerance in 0..442 required")
    mask = np.linalg.norm(pixels - np.asarray(rgb), axis=2) <= tolerance
    if axis not in {"x", "y"}:
        raise ValueError("axis must be x or y")
    counts = mask.sum(axis=0 if axis == "x" else 1)
    offset = x0 if axis == "x" else y0
    # Return runs of positive support plus maxima, without naming objects.
    runs = []; start = None
    for i, count in enumerate([*counts, 0]):
        if count > 0 and start is None: start = i
        if count == 0 and start is not None:
            peak = start + int(counts[start:i].argmax())
            runs.append({"pixels": [start+offset, i-1+offset], "peak": peak+offset,
                         "max_count": int(counts[peak])})
            start = None
    result = {"axis": axis, "runs": runs, "matching_pixels": int(mask.sum())}
    diagnostic = _empty_profile_diagnostics(
        pixels, rgb, counts, 1, mask.shape[0] if axis == "x" else mask.shape[1])
    if diagnostic is not None:
        result["empty_filter_diagnostics"] = diagnostic
    self.log("pixel_profile", {"name": name, "box": box, "rgb": rgb,
                               "tolerance": tolerance, "result": result})
    return result
