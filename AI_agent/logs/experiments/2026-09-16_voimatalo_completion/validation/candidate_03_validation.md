# Voimatalo candidate_03 validation

Overall required checks: **fail**

| Check | Status |
|---|---|
| Exact source proposal replay | pass |
| Frozen plan/observation assembly replay | pass |
| No positive-volume source-space overlap | pass |
| Old 244 windows retained; additions listed | pass |
| Declared openings all mapped and built | pass |
| Non-roof spaces reach exterior in declared door graph | pass |
| Two unchanged continuous cores, no intermediate slabs | pass |
| Roof contacts open; F8-to-roof slab retained | pass |
| Packaged links resolve | fail |
| Offline original/BIM/overlay, rotation and images | pass |
| 09-15 fixed-face diagnostic replayed | pass |

## Opening comparison

- Baseline windows: 244; candidate windows: 287; added: 43.
- Missing old windows: none.
- Changed old windows: none.
- Door changes are reported separately: missing none, changed ['D_F3_CORE_N', 'D_F3_CORE_S', 'D_F3_services_n', 'D_F3_services_s', 'D_F4_CORE_N', 'D_F4_CORE_S', 'D_F4_services_n', 'D_F4_services_s', 'D_F5_CORE_N', 'D_F5_CORE_S', 'D_F5_services_n', 'D_F5_services_s', 'D_F6_CORE_N', 'D_F6_CORE_S', 'D_F6_services_n', 'D_F6_services_s', 'D_F7_CORE_N', 'D_F7_CORE_S', 'D_F7_services_n', 'D_F7_services_s', 'D_F8_CORE_N', 'D_F8_CORE_S', 'D_F8_services_n', 'D_F8_services_s'], added none.

## Limits

- Door reachability follows the declared, partly inferred scheme and does not verify the real interior.
- The fixed-face mesh diagnostic is one-way and does not penalise candidate-only perimeter or establish completeness.
- Browser transport and exact replay prove that the saved artifact was shown unchanged; visual fidelity still requires human review of the saved screenshots.
