# Reading Summary — run_2026-06-20_sonnet_reading

Model: claude-sonnet-4-6  
Date: 2026-06-20  
Images processed: 6

---

## Per-image confidence

| Image | Confidence | Key uncertainties |
|---|---|---|
| 1f_view.json | Medium | Interior wall x-positions for south zone (S9-S11) estimated from bottom dim chain with some ambiguity; east wall window y range approximate; 240 interior dim labels partially uncertain in position |
| 2f_view.json | Medium | Interior vertical walls in south workstation bay (S8-S11) x-positions uncertain — bottom dim chain interpretation of 360+560 segments unclear for divider vs wall edge; center bay count (3 vs 4 dividers) uncertain |
| South_view.json | Medium-High | F1 window y-ranges: left inner chain (S7) and right inner chain (S8/S9) give different values — two chains appear genuine (small window vs large windows); F1 window x-positions (S8/S9) unambiguous from bottom chain; door entrance x-extent approximate |
| North_view.json | High | Clean symmetric layout; F2 windows from top chain unambiguous; F1 windows from bottom chain unambiguous; inner chain F1 partial (only 1000+1600 visible, 400 inferred) |
| East_view.json | High | Only 1 window per floor, centered; dim chains clean; F1 inner chain gives unusual 200mm head clearance (transcribed faithfully) |
| West_view.json | High (F2) / Medium (F1) | F2 window clear; F1 element classified as door (double-door leaves visible) — not traced, logged; inner F1 chain shows only outer 3000mm label with no sub-segments for the door opening |

---

## Repeatedly null fields

| Field | All images | Reason |
|---|---|---|
| `strokes[*].thickness_m` | All plan strokes (1f, 2f) | Schema rule: EP wall has no thickness concept; always null |
| `scale_origin.world_y_m` | All elevation images | Elevation does not carry world y; null as per schema |
| `scale_origin.world_z_m` | Both plan images | Plan does not carry z; null as per schema |
| `scale_origin.world_x_m` | East_view, West_view | East/West elevations — world x is not the local axis origin |
| `ocr_texts` | All images | No room name text or annotation labels visible in any image (no text labels inside rooms or on leaders); dimension numbers transcribed in `dimensions[]` |
| `facade_axis_note` | Plan images | Null per schema for plans |

---

## Schema feedback

1. **Two inner dim chains on South elevation**: the South view has two separate inner height chains — one on the left side (F1: sill=1500, h=900, head=600) and one on the right side (F1: sill=1000, h=1600, head=400). Both are transcribed in `dimensions[]`. The correction stage will need to match each chain to the appropriate window(s) by x-position proximity.

2. **Scale annotation**: drawing scale (1:100 or similar) is likely present but not visible in these image crops — not transcribed. No `scale` category entries added.

3. **Door in West F1**: the west facade F1 element (double-door) is classified as a door in elevation. Per pen library it is not traced as a `window` stroke. It is the main building entrance. The correction stage will need to handle this as a zero-window west F1 with a door opening noted.

4. **South facade entrance door**: similarly the south facade has a double-door at far left (within the 3440mm zone). Not traced as window stroke. Three real windows in F1 south: S7 (narrow, 1200mm wide), S8 (large, 2400mm wide), S9 (large, 2400mm wide).

5. **240 dimension labels in plans**: small "240" annotations are visible inside rooms in the plan views. These appear to be sill/reveal depth markers or wall return depths rather than room dimensions. They were transcribed as approximate D-entries with low positional confidence. The correction stage should treat these as informational only.

6. **Interior wall positions in plans**: plan strokes for interior walls derive x-positions by cumulative sum from dimension chains. These are high-confidence for perimeter-anchored walls and medium-confidence for interior dividers where dimension chains run along the outside of the building rather than through room interiors.
