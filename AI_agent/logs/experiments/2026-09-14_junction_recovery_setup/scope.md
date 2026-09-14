Continue restoration from the saved seed proposal. This increment concerns
physical partitions and spatial continuity in the middle part of the plan, with
the doors/windows whose hosts are affected by an actual partition correction.
Do not redo unrelated parts of the building or optimize first-draft speed.

The complete earlier local observation below is FALLIBLE, NOT APPROVED. Its
claims, IDs, references, door descriptions and assumptions may be wrong. It is
supplied intact, not filtered to correct conclusions. Compare it with original
drawings and the actual seed, decide what is supported, and apply useful local
corrections yourself. Do not merely restate the observation or add notes while
retaining a substantiated physical discrepancy. Independently verify wall end
junctions, the full extent of the spaces on both sides, and which oriented wall
a door swing belongs to. Clean magnified crops retain context around junctions.
Measured grey ink includes furniture, walls, crossings and omissions; it is not
a wall catalogue. Missing color support does not decide whether an opening exists.

Use the existing deterministic geometry, pixel/dimension mapping and inspection
tools. Inspect seed and read the relevant geometry/edit reference. If a change
adds/removes a physical space or exceeds a local edit's supported scope, use a
complete revised build_bim proposal (or build_plan_bim if suitable), preserving
the unaffected geometry and IDs. Do not invent an abstract divider to keep a
space rectangular. Do not delete, clip, resize or silently reclassify openings
just to make the geometry compile: inspect affected openings in the plan and
elevations, then represent supported changes explicitly and keep uncertainty.
The supplied building declaration retains its original meaning; thermal zoning
is not the source-room count. Reliable exterior shape, vertical properties and
unrelated source spaces/openings should remain stable. Old notes are hypotheses;
do not copy them as fresh evidence or infer structural load-bearing from ink alone.

Register an observed image calibration and inspect the NEW actual source plan,
its original-image overlay, and the affected source opening/connection inventory.
Revise conflicts using the original evidence and save an honest final selection
with finish_bim. Record the remaining unexamined scope and unsupported claims.

Development boundary: the developer chose this local aspect, failed seed and
previous observation. No GT, evaluation report, correct source geometry or
developer-approved subset of observations is supplied. This is assisted local
recovery, not an independent cold start or proof of whole-building fidelity.

Complete earlier observation (unmodified):
## Findings

**Context crop** [360,260,630,660]@3×: Two dining-table rooms are separated by a horizontal double line around y≈367–371 that runs from the vertical wall near x≈457 rightward to the exterior wall at x≈603–611. Lower down, near y≈583–587, a single cyan door-leaf arc is attached to the vertical wall at x≈402, swinging into the corridor; the vertical wall at x≈457 turns into a second solid horizontal run toward the exterior wall at that same height.

**Junction A** — box [422,319,512,419]@6×, confirmed further in [430,300,620,420]@5×: The vertical wall at x≈457 (C02) runs continuously through y≈367/371. The horizontal double line (C04/C05) meets it in a clean, capped T‑junction — both wall faces (the two parallel grey strokes) terminate flush against the vertical wall’s faces, no gap, no furniture outline. This is a real corner, not a coincidental crossing: the horizontal member is a load-bearing-drawn partition separating the shelf/cabinet area above (with the "240" dimension) from the dining-table room below.

**Junction B** — box [362,533,497,652]@6×, plus [380,500,500,660]@4× and [360,560,470,660]@5×: The vertical wall at x≈402 is continuous (not terminating at y≈583 as first appearance suggested); a single cyan door leaf is hinged on this vertical wall near (402,583) and swings left into the corridor, capped by flat head/sill ticks at x≈360–397. Separately, the vertical wall at x≈457 turns and continues as a solid horizontal wall from x≈462 to the exterior wall (x≈603–611) with no door. Between x≈397 and x≈462 (the "gap" the profile flagged) there is no drawn wall of any orientation — it is open corridor floor bounded by the two independent vertical walls. So the earlier framing of "C06/C07 = one horizontal wall with a central door" is not supported: the door belongs to the vertical wall (x≈402), and the x≈462–611 run is an unrelated solid horizontal wall with no opening.

```json
{
  "junctions": [
    {
      "id": "A",
      "object": "physical_wall",
      "relation": "separates_spaces (T-junction)",
      "joins": ["C04/C05 horizontal (y=367/371, x=462-611)", "C02 vertical (x=457, peak y=415-587 run)"],
      "separate_runs": [],
      "evidence": "Crop [430,300,620,420]@5x shows both parallel grey strokes of the horizontal element terminate flush against both faces of the continuous x=457 vertical wall, forming a capped T-junction with no gap; the vertical wall continues above and below the junction row. This is a genuine end-cap connection, not a coincidental profile crossing.",
      "prior_claim_action": "revise (prior 'wall_fragment / unresolved whether it connects left of x=462' is corrected: it clearly connects to and terminates at the x=457 wall, forming a real T-junction and dividing the cabinet/shelf area above from the dining-table room below)"
    },
    {
      "id": "B",
      "object": "uncertain (composite: door in vertical wall x=402 + unrelated solid horizontal wall x=462-611; no wall at all spans x=397-462)",
      "relation": "not a single horizontal wall with a central door",
      "joins": ["door leaf hinge belongs to C01 vertical wall (x=402), not to a horizontal member", "C02 vertical wall (x=457) turns into the solid horizontal run x=462-611 with no opening"],
      "separate_runs": [
        ["C06/C07 support interval [360,397] (door-leaf head/sill cap on x=402 wall)"],
        ["C06/C07 support interval [462,611] (solid horizontal wall attached to x=457 wall)"]
      ],
      "evidence": "Crops [380,500,500,660]@4x and [360,560,470,660]@5x show the x=402 vertical wall running continuously through y=583-650 with a single cyan door leaf hinged on it, swinging left into the corridor (flat cyan caps at x~360-397 mark head/sill, not a wall face). Crop [440,550,630,620]@5x shows the x=462-611 span is an unbroken solid double-line wall joined to the x=457 vertical wall, with no arc or jamb break. Between x=397 and x=462 no wall ink of either orientation is present; this is open corridor floor, not a doorway cut into a horizontal wall.",
      "prior_claim_action": "revise (prior 'W-bottom-with-door: unbridged interval x=397-462 is a doorway opening in a bottom horizontal wall' is corrected: there is no single horizontal wall there; the door belongs to the x=402 vertical wall, the x=462-611 stretch is an unrelated solid wall, and the x=397-462 zone is simply open corridor space between two independent verticals — black-pixel/profile adjacency should not have been read as one continuous horizontal wall with a central door)"
    }
  ],
  "unresolved": [
    "Exact hinge coordinate and swing direction of the door leaf on the x=402 wall relative to the corridor floor were read visually from the arc icon only; no jamb-width/frame ink was separately isolated to confirm leaf thickness.",
    "Whether the x=457→horizontal (x=462-611) wall at y=583/587 is the same physical wall thickness/material as the x=402 wall, or a distinct partition type, was not checked beyond line width comparison."
  ]
}
```
Earlier measured profile (unmodified; original-pixel references only):
{
  "name": "1f_view.png",
  "image_sha256": "47cf5eeeb574d0107c15898c389e4397123a34ddcefcd8c8bc61a8fd57f34350",
  "axis": "x",
  "box_original_pixels": [
    360,
    260,
    630,
    610
  ],
  "rgb": [
    169,
    169,
    169
  ],
  "tolerance": 100.0,
  "min_fraction": 0.3,
  "minimum_count": 105,
  "support_length": 350,
  "matching_pixels": 4632,
  "candidates": [
    {
      "id": "C01",
      "pixels": [
        402,
        402
      ],
      "peak": 402,
      "max_count": 235,
      "max_fraction": 0.671429,
      "support_intervals_at_peak": [
        [
          296,
          296
        ],
        [
          301,
          359
        ],
        [
          392,
          418
        ],
        [
          451,
          598
        ]
      ]
    },
    {
      "id": "C02",
      "pixels": [
        457,
        457
      ],
      "peak": 457,
      "max_count": 224,
      "max_fraction": 0.64,
      "support_intervals_at_peak": [
        [
          296,
          296
        ],
        [
          301,
          323
        ],
        [
          356,
          382
        ],
        [
          415,
          587
        ]
      ]
    },
    {
      "id": "C03",
      "pixels": [
        603,
        611
      ],
      "peak": 603,
      "max_count": 129,
      "max_fraction": 0.368571,
      "support_intervals_at_peak": [
        [
          260,
          310
        ],
        [
          356,
          381
        ],
        [
          558,
          609
        ]
      ]
    }
  ],
  "profile_image": "pixel_profiles/profile_001.png",
  "profile_record": "pixel_profiles/profile_001.json",
  "profile_image_sha256": "3f860afbe1a510829d848289b7d529fb1f184b674bd5da2c40e740a4106bb8fc",
  "panel_layout": {
    "original_crop_combined_pixels": [
      0,
      0,
      270,
      350
    ],
    "mask_panel_combined_pixels": [
      273,
      0,
      543,
      350
    ],
    "separator_width": 3
  },
  "panel_note": "Left is the untouched original crop. Right is an exact color-distance mask: magenta outlines candidate bands; blue marks only actual support at the peak coordinate. Marks are coordinate references, not entities. Right-panel local coordinates correspond to the same original crop after removing its combined-image offset.",
  "evidence_note": "Support intervals are measured only at each candidate peak. They do not prove a whole band is continuous or identify a wall. Filtered or empty results do not prove an object is absent.",
  "remaining_seconds": 226,
  "returned_size": [
    543,
    350
  ],
  "original_pixels_per_returned_pixel": [
    1.0,
    1.0
  ],
  "display_note": "For a returned-image point (rx, ry), first multiply by original_pixels_per_returned_pixel to obtain full combined-image coordinates (fx, fy). On the left, original image coordinates are (box_left + fx, box_top + fy). On the right, subtract mask_panel_combined_pixels[0] from fx before adding box_left. Prefer candidates and support intervals, which already use original-image coordinates."
}

Earlier measured profile (unmodified; original-pixel references only):
{
  "name": "1f_view.png",
  "image_sha256": "47cf5eeeb574d0107c15898c389e4397123a34ddcefcd8c8bc61a8fd57f34350",
  "axis": "y",
  "box_original_pixels": [
    360,
    260,
    630,
    610
  ],
  "rgb": [
    169,
    169,
    169
  ],
  "tolerance": 100.0,
  "min_fraction": 0.3,
  "minimum_count": 81,
  "support_length": 270,
  "matching_pixels": 4632,
  "candidates": [
    {
      "id": "C01",
      "pixels": [
        296,
        296
      ],
      "peak": 296,
      "max_count": 208,
      "max_fraction": 0.77037,
      "support_intervals_at_peak": [
        [
          360,
          407
        ],
        [
          452,
          611
        ]
      ]
    },
    {
      "id": "C02",
      "pixels": [
        305,
        307
      ],
      "peak": 305,
      "max_count": 99,
      "max_fraction": 0.366667,
      "support_intervals_at_peak": [
        [
          402,
          402
        ],
        [
          457,
          457
        ],
        [
          508,
          595
        ],
        [
          603,
          611
        ]
      ]
    },
    {
      "id": "C03",
      "pixels": [
        327,
        327
      ],
      "peak": 327,
      "max_count": 87,
      "max_fraction": 0.322222,
      "support_intervals_at_peak": [
        [
          402,
          402
        ],
        [
          509,
          594
        ]
      ]
    },
    {
      "id": "C04",
      "pixels": [
        367,
        367
      ],
      "peak": 367,
      "max_count": 151,
      "max_fraction": 0.559259,
      "support_intervals_at_peak": [
        [
          457,
          457
        ],
        [
          462,
          611
        ]
      ]
    },
    {
      "id": "C05",
      "pixels": [
        371,
        371
      ],
      "peak": 371,
      "max_count": 151,
      "max_fraction": 0.559259,
      "support_intervals_at_peak": [
        [
          457,
          457
        ],
        [
          462,
          611
        ]
      ]
    },
    {
      "id": "C06",
      "pixels": [
        583,
        583
      ],
      "peak": 583,
      "max_count": 190,
      "max_fraction": 0.703704,
      "support_intervals_at_peak": [
        [
          360,
          397
        ],
        [
          402,
          402
        ],
        [
          457,
          457
        ],
        [
          462,
          611
        ]
      ]
    },
    {
      "id": "C07",
      "pixels": [
        587,
        587
      ],
      "peak": 587,
      "max_count": 194,
      "max_fraction": 0.718519,
      "support_intervals_at_peak": [
        [
          360,
          397
        ],
        [
          402,
          402
        ],
        [
          457,
          611
        ]
      ]
    }
  ],
  "profile_image": "pixel_profiles/profile_002.png",
  "profile_record": "pixel_profiles/profile_002.json",
  "profile_image_sha256": "f016865e28c86fa718c90b420c8901ad57bb77f9de79f61aa8b1c664574b1fa9",
  "panel_layout": {
    "original_crop_combined_pixels": [
      0,
      0,
      270,
      350
    ],
    "mask_panel_combined_pixels": [
      273,
      0,
      543,
      350
    ],
    "separator_width": 3
  },
  "panel_note": "Left is the untouched original crop. Right is an exact color-distance mask: magenta outlines candidate bands; blue marks only actual support at the peak coordinate. Marks are coordinate references, not entities. Right-panel local coordinates correspond to the same original crop after removing its combined-image offset.",
  "evidence_note": "Support intervals are measured only at each candidate peak. They do not prove a whole band is continuous or identify a wall. Filtered or empty results do not prove an object is absent.",
  "remaining_seconds": 226,
  "returned_size": [
    543,
    350
  ],
  "original_pixels_per_returned_pixel": [
    1.0,
    1.0
  ],
  "display_note": "For a returned-image point (rx, ry), first multiply by original_pixels_per_returned_pixel to obtain full combined-image coordinates (fx, fy). On the left, original image coordinates are (box_left + fx, box_top + fy). On the right, subtract mask_panel_combined_pixels[0] from fx before adding box_left. Prefer candidates and support intervals, which already use original-image coordinates."
}
