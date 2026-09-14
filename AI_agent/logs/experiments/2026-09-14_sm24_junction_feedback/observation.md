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