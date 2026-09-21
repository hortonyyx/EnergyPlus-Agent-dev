## East Facade Opening Observation — Summary

**Saved comparison record:** `facade_comparisons/comparison_001.json` (compare_facade_spans call above), images `1f_view.png` (plan) and `East_view.png` (elevation), hashes as recorded.

### Plan (1f_view.png), east wall, y-axis
Axis anchors: pixel 151 = 0 m, pixel 878 = 20 m (measured, profile_002 C01/C08 — long green extension lines of the full 0–20000 mm dimension chain, cross-checked against the inner dimension chain 540+1500+2380+1200+740+4800+1540+1600+5700 = 20000 mm, which closes exactly).

| id | pixels (y) | metres | kind | evidence |
|---|---|---|---|---|
| P_W1_1500 | 170–225 (profile_008 C01/C02, measured) | 0.52–2.04 m | window | cyan double-line band, matches label "1500" |
| P_W2_1200 | 311–355 (profile_006 C01/C02, measured) | 4.40–5.61 m | window | cyan band, matches label "1200" |
| P_W3_740 | 355–382 (profile_004 C01/C02, measured) | 5.61–6.35 m | window | cyan band directly adjoining P_W2 (thin pier between), matches label "740" |
| P_D1_1600 | 614–669 (profile_007 C01/C03, measured) | 12.74–14.25 m | door | cyan jambs + quarter-circle swing arc, wall jogs outward here; matches label "1600" |

Directly re-inspected: the long "4800" and "1540" segments (pixel ≈382–556 and ≈556–613) are solid gray wall with **no cyan marks** — confirmed no opening there in plan.

### Elevation (East_view.png), x-axis
Axis anchors: pixel 373 = 0 m, pixel 2261 = 20 m (measured, profile_009 C01/C02, the "20000" overall dimension line).

| id | pixels (x) | metres | kind | evidence |
|---|---|---|---|---|
| E_D1_1600 | 911–1062 (profile_011 C01/C06, measured) | 5.70–7.30 m | door | double-leaf with round handles + transom; width ≈1.60 m |
| E_W_big_4800 | 1208 (visual estimate) –1661 (profile_011 C07, measured) | 8.85–13.64 m | window | large single rectangle, width ≈4.80 m |
| E_W_med1_1200 | 1730 (visual estimate) –1844 (profile_013 C02, measured) | 14.38–15.58 m | window | width ≈1.21 m |
| E_W_med2_1500 | 2070 (visual estimate) –2210 (profile_013 C03, measured) | 17.98–19.46 m | window | width ≈1.48 m |

Left edges of the two medium windows and of the big window were only visually located in a magnified clean crop (no clean color-profile candidate returned there); these three numbers are explicit visual estimates, not profile measurements.

### Correspondence result (compare_facade_spans, both directions checked)
- Forward pairing (plan order = elevation left→right): mean residual 6.42 m — rejected.
- **Reverse pairing** (plan order = elevation right→left): mean residual 0.71 m, clearly preferred (gap 5.7 m ≫ 0.05 m tolerance). Pair-by-pair:
  - P_W1_1500 ↔ E_W_med2_1500: residuals **+0.018 / −0.012 m** — strong match.
  - P_W2_1200 ↔ E_W_med1_1200: residuals **+0.016 / +0.013 m** — strong match.
  - P_D1_1600 ↔ E_D1_1600: residuals **−0.036 / +0.051 m** — strong match (door confirmed both views).
  - P_W3_740 ↔ E_W_big_4800: residuals **+0.74 / +4.80 m** — large, i.e. **not a real correspondence**; this pairing only occurred because both opening counts are 4 and the tool pairs by centre order.

### Conclusion / uncertainty
- Door (1600 mm) and two windows (1500 mm, 1200 mm) correspond convincingly between plan and elevation (sub-5 cm residuals) — treat as high confidence.
- Plan's small 740 mm window (pixel 355–382, immediately beside the 1200 mm window) and elevation's large 4800 mm window have no counterpart in the other view: plan shows solid wall where the 4800 mm elevation window sits, and elevation shows no ~740 mm-wide opening. This is a genuine, unresolved conflict per the tool's guidance (large residual, count coincidentally equal but identity mismatched) — reported as-is, not corrected or invented away.
- Door sill/head heights (1000 mm sill, 1100 mm head clearance within a 4500 mm chain) are read directly from the elevation's vertical dimension chain but the ground-line datum is inferred, not independently confirmed; the 1000 mm base gap for an exterior door is unusual and is flagged as an explicit inference, not a verified height.
- Not examined: north/south/west facades, second-floor or roof openings, and interior side of doors/windows — out of scope for this task.
