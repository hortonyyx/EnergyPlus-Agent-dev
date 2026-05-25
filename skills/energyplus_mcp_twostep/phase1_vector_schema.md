# Vector Schema — phase1 output format ("redraw the source image with semantic pens")

Phase 1 turns each architectural drawing into a vector JSON. The model acts like
an artist re-tracing the original image with a set of **semantically labeled pens**,
without doing any spatial-topology reasoning. All topology is left to phase 2.

---

## 0. Mental model

Think of phase 1 as "re-tracing the source image with a set of semantically labeled pens":
- the **wall pen** traces every stroke that drew a wall
- the **window pen** traces every stroke that drew a window
- … plus dimension chains and text annotations

**What phase 1 does**: identify which component type each stroke is, and trace its
geometry by type.
**What phase 1 does NOT do**: merge strokes into "one exterior wall" / outline "this is a
room" / say "this window belongs to that wall" / judge "this wall faces outside or inside".

All of that topology reasoning is left to phase 2.

### 0.1 Error budget (important)

Phase 1 and phase 2 are mutually exclusive in the kind of error each can introduce:

| Stage | Can see | Errors it can introduce |
|---|---|---|
| phase 1 | the source image (multimodal) | **perception errors**: misread dimension, missed stroke, offset coordinate, wrong elevation x-axis direction |
| phase 2 | phase 1 JSON + skill rule docs + testdata_prompt metadata (**does not see the image**) | **pure reasoning errors**: wrong grouping, inside/outside misjudged, parent-child mapping wrong, IntakeOutput field wrong |

**Implications**:
- Every error about "a value / position / stroke type in the image" must be caught in
  phase 1. Once phase 1 writes it wrong, phase 2 has no chance to backtrack.
- When diffing IntakeOutput, any inconsistency tied to the source image roots 100% in
  phase 1; only topology / naming / field-format errors are phase 2's.
- So when writing the JSON, phase 1 **prefers null over guessing** — null means "I couldn't
  see it", whereas a guessed value makes phase 2 treat a wrong number as truth.

### 0.2 Effect of simulation physics

In EnergyPlus a zone is enclosed by **surfaces (2D faces)**; a wall has no thickness concept. So:
- a "thick black wall" in plan is just a **centerline** (2D polyline) in simulation; the wall
  body width does not participate in the calculation
- phase 1 need not estimate wall thickness — fill `thickness_m` with `null`
- an elevation `wall_fill` rectangle is only a z-range signal source (which layer's z is where),
  it does not mean "the wall is this thick"
- **a door is simply ignored in energy simulation**: a "wall with a door" is, in its simulation
  reality, **one continuous wall**. So when phase 1 sees a door opening it heals the wall to be
  continuous (door-healing, see §2.1); the door symbol only triggers the heal and does not enter
  `strokes`

---

## 1. Global constraints

- **Units**: meters, two decimals
- **Each image carries its own local 2D coordinate system**:
  - `image_kind="plan"`: x = world x (east), y = world y (north)
  - `image_kind="elevation"`: x = horizontal direction along that facade (`facade_axis_note`
    states which world axis it maps to, with sign), y = world z (up positive, ground z=0)
  - `image_kind="section"`: defined per image, explained in `facade_axis_note`
- **scale_origin** records where this image's local (0,0) sits in the world system
- **Tracing rule**: write what is drawn; fill `null` when not found; never backfill defaults from
  background knowledge
- **OCR text verbatim**, do not translate

---

## 2. JSON Schema

```jsonc
{
  // ===== metadata =====
  "image_label": "Floor 1 plan view",       // use the official label from testdata_prompt.json
  "image_kind": "plan | elevation | section | other",
  "facade_axis_note": null,                 // required for elevation, otherwise null
                                            // e.g. "South facade: local x = world x, increasing eastward"
                                            //      "North facade: local x = -world x, i.e. x_local increasing = world westward"
  "scale_origin": {
    "world_x_m": 0.00,                      // world x of this image's local (0,0)
    "world_y_m": 0.00,                      // world y of this image's local (0,0)
    "world_z_m": null,                      // plan: always null (z comes from elevation dim chains); elevation: base elevation of this facade (ground usually 0.00)
    "note": "this image's local origin = SW inner corner of the whole-building footprint"
  },

  // ===== strokes =====
  // each stroke = one continuously drawn stroke + its semantic type (pen).
  // door handling: a door opening in a wall does **not** break the wall — heal the two
  //   segments split by the door into one continuous wall stroke, and record
  //   "healed door opening at <position>" in that stroke's note (in EP a wall is a continuous
  //   boundary face and a door is ignored, so the continuous wall is faithful to the simulation).
  //   A window opening is NOT healed — keep it as a window pen. Guardrails (only heal openings
  //   with a door symbol, do not heal a doorless open span) see §2.1.
  "strokes": [
    {
      "id": "S1",
      "pen": "wall",                        // enum: wall | window | stair | other
                                            // door is not a legal pen: a door only triggers healing, it is not drawn (see §2.1 / §3.1)
                                            // other = visible strokes that cannot be classified (e.g. north arrow, title block)
      "geometry": {
        "kind": "line",                     // line | rect | polyline
        "p1": [0.00, 0.00],
        "p2": [15.00, 0.00],
        "thickness_m": null                 // plan walls always null (EP zones are enclosed by surfaces, walls have no thickness)
      },
      "note": ""                            // free text, e.g. "south horizontal perimeter wall"
    },
    // rect-fill example (elevation wall body, elevation window)
    {
      "id": "S99",
      "pen": "window",
      "geometry": {
        "kind": "rect",
        "x_range_m": [1.40, 3.80],          // this image's local coordinates
        "y_range_m": [1.00, 2.80]
      },
      "note": "south facade F2 window 1"
    },
    // polyline example (non-straight wall)
    {
      "id": "S100",
      "pen": "wall",
      "geometry": {
        "kind": "polyline",
        "points": [[0,0],[5,0],[5,3],[8,3]],
        "thickness_m": null,
        "closed": false
      },
      "note": ""
    },
    // door-healing example: a door split this wall in the source; healed into one continuous wall + trace note
    {
      "id": "S101",
      "pen": "wall",
      "geometry": {
        "kind": "line",
        "p1": [5.00, 0.00],
        "p2": [10.00, 0.00],
        "thickness_m": null
      },
      "note": "healed door opening at x≈7.5 (door swing seen in plan); EP wall is continuous"
    }
  ],

  // ===== dimension chains (structured composite primitives) =====
  // visually a "tick + number + tick" chunk is one unit, classified on its own; phase 2 uses it to derive coordinates
  "dimensions": [
    {
      "id": "D1",
      "text": "15.00",                      // transcribe the dimension number verbatim
      "from": [0.00, 0.00],
      "to":   [15.00, 0.00],
      "axis": "x",                          // x | y | z (z only on elevation)
      "note": "bottom total-length chain"
    }
  ],

  // ===== text annotations =====
  "ocr_texts": [
    {"id": "T1", "text": "Office 101", "anchor": [3.00, 1.50], "note": ""}
  ],

  // ===== self check =====
  "self_check": {
    "all_dimensions_transcribed": true,     // are all dimension-chain numbers transcribed
    "all_visible_strokes_captured": true,   // did all visible strokes go into the strokes array
    "no_topology_inferred": true,           // did you resist grouping rooms / judging inside-outside / pairing parent-child
    "pens_used": ["wall"],                  // pen values actually used in this image (deduped)
    "unknowns_noted": [
      "wall thickness not dimensioned -> strokes[*].thickness_m = null"
    ],
    "uncaptured_visual_elements": [
      // **required**: anything "seen but not drawn into strokes" must be acknowledged here:
      //   (1) strokes the pen dictionary can't cover (cornice / index arrow ...)
      //   (2) clutter actively excluded by selective extraction (furniture / paving / texture / room text boxes ...)
      //   (3) healed door openings ("healed door at <position>")
      // "acknowledged skip" vs "silent loss" makes a world of difference at review time.
      // Even when the keep-set + dictionary really are enough, leave an explicit note rather than an empty default.
      // e.g. "F1 plan excluded 8 furniture symbols + 2 paving fills"
    ]
  }
}
```

---

## 2.1 Door-healing guardrails

In EP a wall is a continuous boundary face, a window is a sub-face on a wall, and a door is
ignored outright in energy simulation. So a "wall with a door" is, in its simulation reality,
**one continuous wall**. Phase 1 can see the door arc / leaf at a glance; phase 2 only has
coordinates and cannot reliably tell apart "door / real opening / two independent walls" — so by
the error-budget principle, healing the door belongs to phase 1. Effect: phase 2 always receives
a clean, closed wall network (one uniform, image-free, validated regime).

**Healing ≠ assigning rooms**: phase 1 only guarantees the wall network is geometrically
continuous and closed; which walls enclose which room / inside vs outside / naming is still
phase 2's job (§0 red line).

Guardrails (to stop phase 1 inventing walls):

1. **Only heal openings carrying a door symbol (door leaf / swing arc)** — the door symbol is the trigger
2. **Do not heal a doorless large opening / open span** — that is a real topology signal
   (possibly the same zone / a genuinely open boundary); welding it shut destroys information
   phase 2 needs. A gap alone, with no door symbol, does not count
3. **Do not heal windows** — keep them as a window pen (a window is a sub-face, not a boundary break)
4. **Always leave a trace when healing**: write `healed door opening at <position>` in that wall
   stroke's note, and record it in `self_check.uncaptured_visual_elements`, so SVG review can
   verify "the heal is correct, no real opening was covered up"

---

## 3. pen enums (split by image_kind)

**Important**: plan and elevation use different legal pen sets. Phase 1 must pick the dictionary
matching the image's `image_kind`; do not cross-use.

### 3.1 image_kind = "plan" legal pens

| pen | typical visual | when to use |
|---|---|---|
| `wall` | thick black line / black filled rectangular bar | any stroke recognized as a wall |
| `window` | opening in wall + short blue bar (only if a window is actually drawn in plan) | window |
| `stair` | parallel diagonal lines / stair-tread symbol | stairs |
| `other` | none of the above but actually drawn | north arrow, grid label, furniture, title block |

**Plan does not emit a `door` pen, but doors must be "recognized to drive wall-healing" (see §2.1)**:
when you see a door leaf / arc, do not draw a door stroke — instead heal the walls on its two sides
into **one continuous wall stroke** and write `healed door opening at <position>` in the note. The
door is only a trigger and does not enter strokes itself; the heal also goes into
`uncaptured_visual_elements` as a trace.

### 3.2 image_kind = "elevation" legal pens

| pen | typical visual | when to use |
|---|---|---|
| `wall_fill` | light-gray filled rectangle (one per floor) | **one wall_fill stroke per floor** (see §3.3) |
| `window` | blue filled rectangle | elevation window |
| `outline` | overall outline heavy line of the elevation | only if the outline does not coincide with the wall_fill edges / a separate outer frame is drawn |
| `other` | none of the above but actually drawn | floor-divider lines, structural lines (columns/beams), decorative lines (mouldings/cornices), elevation index arrows, shadows |

**Elevation does not emit a `door` pen** — same as plan; a main entrance door may be noted but does
not enter strokes.

**Handling `other`**: tag any stroke outside the enum as `other` + a note describing "this is a
floor-divider line" or "this is a cornice". Do not invent a new pen value per decoration type — keep
the dictionary minimal.

### 3.3 elevation wall_fill convention (key)

Record elevation wall-body gray fill as "**one wall_fill stroke per floor**". For example:

- a south elevation of a 3-story office → 3 wall_fill strokes, each covering the F1 / F2 / F3 gray
  fill rectangle (split by y range)
- even if the gray looks like one continuous block (no visible seam), as long as the dimension chain
  marks each floor's z range, still write 3 strokes — phase 1 splits by the dimension chain
- if a floor's gray fill is **completely broken** by a door/window opening (white unfilled area
  around the frame), record each broken rectangle segment as its own stroke; but when elevation
  windows overlay the gray fill (no break), it stays one fill per floor

Once phase 2 has per-floor wall_fill it maps directly to each floor's wall surface z_floor / z_top,
cheaper than "one fill for the whole wall then split".

### 3.4 visual recognition vs spatial topology (emphasized again)

Judging wall vs window vs wall_fill vs other is **visual recognition** (the strokes look different) —
phase 1's domain.
Judging wall ext vs int / which wall a window belongs to / which walls enclose which room / which
floor a wall_fill maps to ←—— these are **spatial topology** judgments, all left to phase 2.

---

## 4. Elevation notes

`facade_axis_note` must state which world axis the local x maps to + the increasing direction (with sign):

| facade | facade_axis_note example |
|---|---|
| South | `"South facade: local x = world x (increasing eastward); local y = world z"` |
| North | `"North facade: local x = -world x (local x increasing = world westward); local y = world z"` |
| East | `"East facade: local x = world y (increasing northward); local y = world z"` |
| West | `"West facade: local x = -world y (local x increasing = world southward); local y = world z"` |

Elevation window strokes use `geometry.kind="rect"` + `x_range_m` / `y_range_m` (this image's local
coordinates); phase 2 uses `facade_axis_note` to translate back to the world system.

---

## 5. Counter-examples

- ❌ `"pen": "wall", "is_exterior": true` —— is_exterior is phase 2's call, do not add the field
- ❌ stuffing a room polygon into strokes —— a room is not a drawn stroke
- ❌ `"pen": "wall", "parent_window_ids": [...]` —— parent-child is phase 2's inference
- ❌ splitting one continuous wall into 10 small strokes —— one stroke per continuous stroke
- ❌ splitting a wall with a door into two wall strokes on either side —— heal it into one continuous wall + note (§2.1)
- ❌ welding a doorless open span into a continuous wall —— that is a real topology signal; only heal openings with a door symbol
- ❌ leaving `uncaptured_visual_elements` empty when furniture was excluded / a door was healed —— it is required; actively excluded items + heals must be acknowledged
- ❌ `"text": "办公室"` for an image that says "Office 101" —— OCR does not translate
- ❌ `"thickness_m": 0.20` —— plan walls always null (simulation does not need wall thickness, see §0.2)
- ❌ `"pen": "wall_fill"` drawn on a plan —— wall_fill is only in the elevation dictionary
- ❌ `"pen": "wall"` drawn on an elevation —— elevation walls use wall_fill; the wall value is plan-only
- ❌ one wall_fill for an entire elevation wall —— should be "one wall_fill per floor" (see §3.3)
- ❌ inventing a pen value for door / furniture / decorative line such as `"furniture"` / `"cornice"` —— do not expand the dictionary, use `other` + a note

---

## 6. Self-check list

- [ ] picked the right pen dictionary by image_kind (plan uses §3.1, elevation uses §3.2)
- [ ] every visible wall/window/wall_fill stroke is in the strokes array with the right pen field
- [ ] elevation wall bodies split as "one wall_fill per floor"
- [ ] no rooms[] / is_exterior / parent relations or other topology fields
- [ ] no standalone door / furniture / decoration pen values (all go to other or are not recorded)
- [ ] door openings healed into continuous walls (only openings with a door symbol; doorless open spans kept), wall stroke note says `healed door opening at ...`
- [ ] every dimension-chain number is in the dimensions array
- [ ] text labels transcribed verbatim
- [ ] not-found fields filled with null
- [ ] elevation facade_axis_note includes axis + sign
- [ ] elevation outline: not drawn separately if it coincides with wall_fill edges (§3.2); confirmed for this image
- [ ] plan scale_origin.world_z_m is null (not 0.00)
- [ ] self_check.pens_used lists the pen set used in this image
- [ ] self_check.uncaptured_visual_elements is **non-empty** (required): records everything "seen but not drawn" — out-of-dictionary strokes + actively excluded clutter + healed doors

---

## 7. Contract with downstream

Phase 2 receives a set of these JSONs (one per image) + testdata_prompt.json + skill rule docs, and
rebuilds topology:
- recognize closed regions enclosed by multiple wall strokes as rooms / zones
- judge each wall's is_exterior (whether it sits on the perimeter)
- map each window stroke to its parent wall
- translate elevation strokes back to world coordinates, cross-check plan ↔ elevation consistency
- output the IntakeOutput Pydantic

Phase 1's output is not IntakeOutput, and **should not align directly with IntakeOutput fields**.
Phase 1's product is just "the image, re-traced".
