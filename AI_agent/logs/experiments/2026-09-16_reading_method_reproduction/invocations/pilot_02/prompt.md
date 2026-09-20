External pilot review: REWORK REQUIRED. Continue this same session, revise only
the 1F pilot, and stop again for review. Do not start the other images.

This feedback uses your saved artifacts, your CV results and the supplied source
image, not a reference geometry or expected wall/window counts.

1. Calibration is not established. Your actual 001_px_m_calibrator sidecar reports
   residuals +139.2 px / -69.6 px (RMSE 110.05 px). The x span 57..730 and y span
   51..1049 came from the global extent of green annotation ink, not verified tick
   endpoints on one dimension line. Splitting these into two independent axis
   scales does not fix the wrong anchors. Crop/zoom the actual dimension chains;
   bind each transcribed value to its own two extension/tick endpoints. Re-run
   the calibrator with several independently measured spans and inspect residuals.
   Establish an explicit image-local origin and one auditable pixel-to-metre
   conversion. Preserve failed evidence and record why it was superseded.

2. The pilot's 31-wall regular grid is unsupported. Your own wall profiler has
   measured candidate positions, while the JSON repeats a uniform set of vertical
   partitions and complete cross-building horizontals. Review the actual original
   crops for each proposed continuous wall. Classify wall, furniture, annotation,
   door swing, window frame, or uncertain; record accepted/rejected decisions and
   reasons with overlay_logger. Use the measured grayscale wall candidates; your
   helper's black-pixel mask is dominated by this image's background. Do not invent
   a regular grid to replace unresolved evidence. Preserve actual open spans and
   wall turns; heal only a gap whose door symbol belongs to that wall.

3. The pilot is substantially incomplete: no window strokes, only seven
   dimensions, no crop_zoom evidence, and no candidate disposition ledger. These
   were part of the assigned pilot. Use the provided crop_zoom tool to make small
   labels and door/window components legible, read its saved crop image, transcribe
   visible dimension chains verbatim, and measure/trace the visible windows. Mark
   uncertainty per object rather than omitting an entire category. The legacy
   loader accepts the JSON, but syntax acceptance does not establish faithful or
   complete reading. The old gate also flags incomplete/non-closing chains.

4. Before returning, load the file with the provided historical reading loader
   (`from src.agent.reading import load_reading_view`) as well as checking JSON
   syntax. Recheck against source crops and record the remaining concrete
   uncertainties. Keep the historical schema (including scale_origin, provenance,
   confidence, dimension_refs, flat dimension anchors, and uncaptured notes).
   A prose warning does not replace correcting unsupported strokes.

Complete and self-check the full pilot before stopping. You have a fresh 1800s
turn budget; correctness and usable evidence take priority over speed.
