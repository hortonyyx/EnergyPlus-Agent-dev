## Summary of East‑facade opening observation

**Saved comparison record:** `facade_comparisons/comparison_001.json` (produced by `compare_facade_spans`, plan `1f_view.png` y‑axis vs elevation `East_view.png` x‑axis).

### Method / axis anchors
- **Plan (1f_view.png), y‑axis:** anchored with `profile_002` (green outer dimension chain on the east wall) candidates C01 (pixel 151 → 0 m) and C06 (pixel 878 → 20 m). This chain's five segments (4060/1940/5940/3120/4940 mm) sum exactly to 20 000 mm, matching the drawing's overall "20000" label, so the anchor is a bound dimension‑chain measurement, not a guess.
- **Elevation (East_view.png), x‑axis:** anchored with `profile_004` candidates C03 (pixel 373 → 0 m, left wall corner) and C10 (pixel 2261 → 20 m, right wall corner); the intervening ticks (911,1062,1207,1661,1730,1844,2069,2210) reproduce the printed chain 5700/1600/1540/4800/740/1200/2380/1500/540 mm almost exactly, confirming the pixel↔mm scale (≈10.59 mm/px).

### Plan openings (independent list, original pixels, y‑axis)
| id | pixel y‑interval | metres | evidence |
|---|---|---|---|
| P_Win1 | 172–225 | 0.58–2.04 m | `region_001` cyan mullion band on east wall; matches 540(wall)+1500(window) |
| P_Win2 | 313–355 | 4.46–5.61 m | overview_002 R20/R21; matches 1200 mm window |
| P_Win3_big | 383–556 | 6.38–11.14 m | region_002 + R22/R23; visually one continuous glazing band (the 383‑514/516‑556 split was only a dimension‑tick overlap, confirmed in a magnified crop, not a real mullion); matches 4800 mm opening |
| P_Door | 612–670 | 12.68–14.28 m | overview_002 R37/R39 jamb ticks + swing arc seen in crop; single‑leaf door, matches 1600 mm |

No other teal/cyan marks were found on this wall column between y=151 and y=878; the mark near y≈700–730 (arc) sits on an **interior** partition, not the exterior wall, and was excluded.

### Elevation openings (independent list, original pixels, x‑axis)
| id | pixel x‑interval | metres | evidence |
|---|---|---|---|
| E_Door | 911–1062 (profile_004 C04/C05, actual measurements) | 5.70–7.30 m | Double‑leaf glazed door with visible round handles (crop [890,390,1090,650]); overall width 1600 mm |
| E_Win_big | 1207–1662 | 8.83–13.65 m | plain rectangular window, overview_003 R02/R03; width ≈4800 mm |
| E_Win2 | 1730–1845 | 14.38–15.59 m | plain rectangular window, R04/R14; width ≈1200 mm |
| E_Win3 | 2068–2211 | 17.96–19.47 m | plain rectangular window, R05/R07/R11; width ≈1500 mm |

### Correspondence result
`compare_facade_spans` tested both directions:
- **elevation_forward:** mean residual 5.71 m, max 8.04 m → rejected.
- **elevation_reverse:** mean residual **0.028 m**, max **0.050 m** (within the 0.05 m tolerance) → accepted pairing:
 - P_Win1 ↔ E_Win3 (small window, farthest from door)
 - P_Win2 ↔ E_Win2 (small window)
 - P_Win3_big ↔ E_Win_big (large 4.8 m window)
 - P_Door ↔ E_Door

So plan north‑to‑south (y=0→20 m) corresponds to elevation right‑to‑left (x=2261→373 px), i.e. the elevation is mirrored relative to the plan's y order — consistent with viewing the same wall from the exterior (east) side.

### Distinguishing evidence types
- **Actual tool measurements (profile/region):** all plan axis anchors, elevation axis anchors, E_Door pixels (profile_004), all region bboxes (region_001/002, overview_002/003).
- **Explicit visual estimate:** none used for opening pixel positions (all bound to region/profile evidence); the "big window is one band, not two" call is an explicit visual judgment on a magnified crop, kept distinct in the evidence field.
- **Assumption:** none required beyond standard axis correspondence (both totals = 20 000 mm, independently confirmed from each drawing's own dimension chains).

### Uncertainty / open items
1. **Door leaf count mismatch:** plan shows a single‑leaf swing (no second leaf drawn), elevation shows a double‑leaf glazed door of the same total 1600 mm width. Positions/widths match to <5 cm, but representation style differs — flagged as uncertain identity detail, not a count conflict.
2. **Height/vertical chain:** only checked for the large window (E_Win_big): dimension chain "1100/2400/1000" (mm) with roofline pixel ≈220 and ground‑line pixel ≈650 (scale ≈10.47 mm/px) gives an approximate sill height ≈0.94–1.0 m and head height ≈3.3–3.4 m above ground — bound to a directly inspected chain, but with ~5–8 cm pixel‑rounding uncertainty. Heights for E_Win2, E_Win3, and E_Door were **not examined** (unexamined item; separate vertical chains near those openings were seen but not measured) — flagged as unresolved rather than inferred.
3. No additional uncertain ink marks (furniture, labels) were found overlapping the east wall column in either view beyond what is listed.
