Second external rework, same pilot and same session. Do not batch yet.

The previous correction is still invalid. Your source image is 790 x 1111 pixels,
but the revised origin is y=1595, outside that image. The left crop was made with
`bbox=[35,50,80,880]`, scale 2, producing a 90 x 1660 crop. Coordinates measured
in that enlarged crop must be transformed back to ORIGINAL pixels:
source_x = bbox_x0 + crop_x / scale; source_y = bbox_y0 + crop_y / scale.
Your y calibration mixed crop coordinates with source coordinates. A recomputation
from the same mistaken endpoints is not an independent zero-residual validation.

Use Python to read the recorded crop transform and perform this conversion, and
assert all reported source pixel anchors fit the original image. Detect tick
positions on the relevant dimension-line row/column from actual pixel support,
rather than estimating them from displayed image size. The x and y scales should
be compatible for this original drawing; inspect both actual tick endpoints and
their extension lines whenever they disagree materially. Re-run px_m_calibrator
with corrected SOURCE endpoints and save the new sidecar.

The wall/window interpretation also remains unsupported. Two dimension crops
alone do not verify interior wall geometry. Open focused crops of the actual
wall candidates and endpoints before accepting them. Keep measured source-pixel
line positions AND actual start/end support, not just projection peaks extended
across the building. Furniture and dimension lines remain rejection candidates.
Use overlay_logger to retain accepted/rejected/undecided classifications and
reasons. Do not label guessed endpoints as pixel measurements or cite an unseen
overlay as confirmation. Trace all visibly supported windows and the full visible
dimension chains; incomplete whole categories cannot be marked completed.

Correct the geometric output, not just its report. Run historical schema loading
and your own coordinate/support checks, then stop for review with honest remaining
items. You have another 1800s allowance. No expected geometry, reference answers,
or target counts are supplied by this feedback.
