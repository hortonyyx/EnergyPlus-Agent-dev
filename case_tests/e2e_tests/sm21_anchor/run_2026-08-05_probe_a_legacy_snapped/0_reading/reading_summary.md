# sm21_anchor — 0_reading summary

Re-traced each of the six source images with semantically labeled pens. No topology / no
world placement inferred (left to 1_correction). Coordinates are the reading stage's local 2D
system; verbatim dimension numbers (mm) are in each `dimensions[]`.

Building at a glance (perception only, not asserting topology): a 2-storey rectangular block,
plan footprint 15000 x 8000 mm, two storeys 3000 + 3600 = 6600 mm tall, flat top. A central
horizontal corridor runs the full length on both floors. 1F = 3 rooms top + 3 rooms bottom;
2F = 2 (large/conference) rooms top + 4 (small/office) rooms bottom.

## Per-image confidence table

| image | kind | strokes (wall / window / wall_fill / outline) | doors healed or noted | dims | overall confidence |
|---|---|---|---|---|---|
| 1f_view | plan | 17 (10 / 7 / – / –) | 8 healed (6 interior swing + W entrance + SW exterior) | 36 | med–high on structure; med on exact x/y |
| 2f_view | plan | 18 (10 / 8 / – / –) | 6 healed (2 top + 4 bottom interior swings) | 32 | med–high on structure; med on exact x/y |
| South_view | elevation | 10 (– / 7 / 2 / 1) | 1 door noted (lower-left, not traced) | 35 | high on z-bands; med on lower-window x |
| North_view | elevation | 8 (– / 5 / 2 / 1) | none | 24 | high on z-bands; med on lower-window x |
| East_view | elevation | 5 (– / 2 / 2 / 1) | none | 17 | high (symmetric, simple) |
| West_view | elevation | 4 (– / 1 / 2 / 1) | 1 door noted (centered lower, not traced) | 15 | high (symmetric, simple) |

Pen sets used: plans `wall` + `window`; elevations `outline` + `wall_fill` + `window`. No
`door`/`other` pens anywhere. `thickness_m` = null on every plan wall.

## Window / door tallies (what each image shows)

- **1F plan**: north wall 3 window groups, south wall 3 windows, east wall 1 window = 7 windows.
  8 doors total, all healed/noted: 3 corridor->top-room swings, 3 corridor->bottom-room swings,
  1 west entrance (into corridor), 1 SW exterior door on the bottom-left room.
- **2F plan**: north wall 2 windows, south wall 4 windows, west wall 1, east wall 1 = 8 windows.
  6 interior swing doors (2 top + 4 bottom), all healed. No exterior door on 2F.
- **South elevation**: 4 upper windows (two 1200-wide pairs, 720 gap each), 3 lower windows
  (1 small ~600 tall + 2 large ~1600 tall). 1 lower-left door (note only).
- **North elevation**: 2 upper windows (~3600 wide), 3 lower windows (~2400 wide). No door.
- **East elevation** (8000 wide): 1 upper + 1 lower window, both centered 1200 wide. No door.
- **West elevation** (8000 wide): 1 upper window centered 1200 wide; 1 centered lower entrance
  door (note only). No lower-floor window.

## Z-bands read from elevation level chains (high confidence)

- Storey line at z = 3000 on all four elevations; parapet/roof top z = 6600.
- Upper-floor windows: sill 4000, head 5800 (1000 + 1800 + 800 chain) — consistent on N/S/E/W.
- Lower-floor windows differ per facade (transcribed verbatim from each image's own chain):
  - North: 1000–2600 (1000/1600/400)
  - South large: 1000–2600 (1000/1600); South small: 1500–2100 (1500/600)
  - East: 1000–2800 (1000/1800/200)
  - West: door only (no lower window)

## Repeatedly-null / low-confidence fields (honest flags)

- **`dimensions[*].from` / `to`** left **null** in almost every entry. The interior sub-chains are
  window/pier/partition spacing runs, not a single additive run I could pin endpoint-to-endpoint
  onto the geometry. Only the overall chains (15000 / 8000 / 6600) and a few clean symmetric ones
  carry explicit from/to. This is deliberate "prefer null over guessing", not an omission — every
  number is still transcribed verbatim in `text`.
- **`thickness_m`** = null on all plan walls (per guide §0.2). Plans label walls "240" mm; that is
  recorded only as `ocr_texts`, never as geometry.
- **Plan stroke x/y and elevation window x-ranges** are centerline / best-fit estimates. I am
  confident about *which* walls/windows exist and their ordering; I am *not* confident the metre
  coordinates are exact. The correction stage should resolve precise positions from the verbatim
  dimension chains, not from my coordinates. Flagged in each file's `unknowns_noted`.
- Exact y of the two corridor walls on both plans is approximate (room band ~3000, corridor
  interior 1200 east / 1500 west on 1F, 1200 on 2F — the 1F west corridor band reads 1500 while
  east reads 1200; I transcribed both verbatim and did not reconcile them, since reconciliation is
  topology/measurement work for downstream).

## Ambiguities I had to judge

- **1F west side**: a door on the west perimeter wall (entrance, swing into corridor) plus a
  separate door at the SW corner of the bottom-left room. Both carry swing arcs, so both were
  healed into their host wall with notes. The small 540/900 + 250/1500/250 dims around there are a
  little cramped; I transcribed them verbatim but did not try to place the doors to the millimetre.
- **South lower-left tall element vs West centered tall element**: both are floor-height leaves with
  panel/cross-bar + a handle dot -> classified as **doors**, so not traced in elevation (note only).
  This matches the plans (west entrance door + a south-side exterior door region on 1F).
- **East lower window height = 1800 (head-to-storey gap 200)** vs North/South lower windows
  1600 (gap 400). I did not "correct" East to match the others — each elevation's own chain governs.
- **2F top rooms**: the north chain 1889/1891 around the centre suggests the central partition sits
  near x ~ 7.5 m; I placed S7 there with an explicit "approximate" note rather than asserting exact.

## Schema feedback

- The P1b `facade` block (image-local, no world axis/sign) was clean to fill from the trusted
  filename. `facade_axis_note` is kept `null` on elevations per the new convention (world axis is
  1_correction's job), which is consistent with the no-world-placement rule. Worth noting the
  legacy `guide.md` §4 still describes `facade_axis_note` with world-axis text — that example
  predates the P1b facade block and was intentionally NOT followed here.
- `dimensions[].from/to` being frequently null is the honest outcome for spacing sub-chains on a
  pure perceptual pass; if downstream wants pinned endpoints it would need either a scale/grid
  anchor in the image or an explicit instruction to interpolate, which would cross into measurement
  inference the reading stage is told to avoid.
</content>
