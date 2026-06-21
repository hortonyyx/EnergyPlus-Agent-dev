# reading_summary.md — GPT-5.4 (codex CLI -i) reading of sm21_anchor

Per-image reading produced independently from the pixels (one codex `exec -i` call per image, gpt-5.4, medium reasoning). Schema follows skills/intake_pipeline/0_reading. Elevation rect geometry stored as x_range_m/y_range_m.

| view | kind | walls | windows | wall_fill | confidence |
|---|---|---|---|---|---|
| 1f_view | plan | 10 | 7 | 0 | high |
| 2f_view | plan | 10 | 8 | 0 | high |
| South_view | elevation | 0 | 7 | 2 | high |
| North_view | elevation | 0 | 5 | 2 | high |
| East_view | elevation | 0 | 2 | 2 | high |
| West_view | elevation | 0 | 1 | 2 | high |

## Notes
- Plans: interior walls traced at true wall gridlines (not at every exterior dimension tick). thickness_m=null throughout.
- Elevations: one wall_fill per floor; doors healed into wall and logged in uncaptured_visual_elements (not traced as windows).
- Repeatedly null: scale_origin world axes on elevations (image-local), thickness_m on plans (by rule).
