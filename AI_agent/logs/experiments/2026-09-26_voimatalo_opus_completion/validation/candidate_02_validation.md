# Voimatalo 09-26 candidate_02 validation

Overall required checks: **pass**

Source sha256 `6e2b46888cac11fdcb6748a2806602b393b9f46901d9bbdaf44ba03fb4194703`

| Check | Status |
|---|---|
| Exact source proposal replay | pass |
| Plan rebuild + assembly replay (byte-identical) | pass |
| No positive-volume source-space overlap | pass |
| Only change to the shell = tower rectangle on F1-F7 | pass |
| All 80 spaces / 300 windows / 88 doors of 09-25 unchanged; additions exactly the tower items | pass |
| All 287 candidate_04 windows unchanged; additions explained | pass |
| Declared openings all built; windows single exterior host | pass |
| Partitions meet facades in window piers | pass |
| Continuous volumes without intermediate slabs | pass |
| Declared open contacts open on both sides, no displayed slab | pass |
| Roof-part contacts open; slabs kept | pass |
| Reachable via doors/open contacts; two vertical routes per upper storey | pass |
| Tower contacts, landing doors, measured bounds | pass |
| Room/corridor widths plausible (shaft exempt) | pass |
| Enclosure bookkeeping (unknown reasons, party walls) | pass |
| Packaged links resolve | pass |
| Offline original/BIM/overlay viewer and images | pass |
| Offline viewer aimed at the tower (overlay/BIM screenshots) | pass |

## Key numbers

- 09-25 → 09-26: spaces 80 → 81, windows 300 → 306, doors 88 → 95; prev openings missing 0, moved 0, re-hosted 0.
- Tower contact areas: {'ANNEX_hall': 11.39, 'CORE_S_continuous': 106.05}; landing doors on ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7'].
- Measured bounds: {'east_face_x': 2.5, 'east_face_min_from_north_stub_x': 2.38, 'east_face_max_from_annex_facade_x': 2.9, 'north_stub_max_x_incl_annex_edge': 4.31, 'annex_facade_min_x': 2.32, 'hole_median_y_range_z7_25': [-26.08, -21.98], 'tower_y_range': [-25.9, -21.7], 'south_face_offset_from_hole_m': 0.18, 'north_face_offset_from_hole_m': 0.28}.
- Unknown-enclosure boundaries: 15 (09-25) → 15.

## Limits

- The tower use (lifts) and its windowless exterior are inference; the checks prove consistency, not the real use.
- Reachability follows the declared door/open-contact scheme; it does not verify the real interior.
- Technical checks are not the user acceptance of this completion.
