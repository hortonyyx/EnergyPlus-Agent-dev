---
name: smalloffice_15_post baseline run
description: Geometry-phase build of test_data/SmallOffice/smalloffice_15_post — completed clean on 2026-04-27.
type: project
originSessionId: dabf94b5-507c-47f4-86a1-aa4a8568d6f3
---
Geometry-phase YAML+IDF for `test_data/SmallOffice/smalloffice_15_post` produced 2026-04-27.

- Building: 15.00 × 8.00 m, 2 floors × 3.60 m, 14 zones (3 N rooms + full-width corridor + 3 S rooms per floor).
- Fenestration: 12 windows total, only on South (Wall_1 of S1/S2/S3) and North (Wall_3 of N1/N2/N3) facades; East/West blank (elevation files provided but no blue rectangles).
- Outputs under `test_data/SmallOffice/smalloffice_15_post/output/`: `top_view_annotated.png`, `claude_ep.md`, `smalloffice_15_post.yaml`, `smalloffice_15_post.idf`.
- Workflow ran cleanly first try — single `update_surfaces_batch` (84 items) and single `create_fenestration_surfaces_batch` (12 items), no retries.

**Why:** Part of the SmallOffice baseline test series used to validate the energyplus_mcp skill end-to-end. Other cases in the series live as siblings under `test_data/SmallOffice/`.

**How to apply:** When re-running this case, expect the exact 14-zone / 12-window layout above. If any count differs, the dimension extraction or facade-blank detection regressed — investigate before assuming the skill changed.
