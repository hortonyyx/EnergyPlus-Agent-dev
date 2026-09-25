# Voimatalo 09-25 candidate_01 validation

Overall required checks: **pass**

| Check | Status |
|---|---|
| Exact source proposal replay | pass |
| Frozen plan/observation assembly replay | pass |
| No positive-volume source-space overlap | pass |
| Exterior shell/levels/roof identical to candidate_04 | pass |
| All 287 candidate_04 windows kept unchanged; additions explained | pass |
| Declared openings all built; windows single exterior host | pass |
| Inferred partitions meet facades in window piers | pass |
| Continuous stair/core volumes without intermediate slabs | pass |
| Declared stair/core open contacts open on both sides, no displayed slab | pass |
| Roof-part contacts open; F8/core-to-roof slab kept | pass |
| Reachable via doors/open contacts; two vertical routes per upper storey | pass |
| Room/corridor widths plausible | pass |
| Enclosure bookkeeping (unknown reasons, party walls) | pass |
| Packaged links resolve | pass |
| Offline original/BIM/overlay viewer and images | pass |

## Key numbers

- Windows: candidate_04 287 → candidate_01 300; old missing 0, old geometry changed 0, re-hosted 278; added measured 8, added inferred 5.
- Unknown-enclosure boundaries: 24 → 15; party-wall boundaries 34 (none with openings).
- Upper-storey corridor vertical routes: {'F2': ['CORE_N_continuous', 'CORE_S_continuous', 'STAIR_S_stair_hall'], 'F3': ['CORE_N_continuous', 'CORE_S_continuous', 'STAIR_S_stair_hall'], 'F4': ['CORE_N_continuous', 'CORE_S_continuous', 'STAIR_S_stair_hall'], 'F5': ['CORE_N_continuous', 'CORE_S_continuous', 'STAIR_S_stair_hall'], 'F6': ['CORE_N_continuous', 'CORE_S_continuous', 'STAIR_S_stair_hall'], 'F7': ['CORE_N_continuous', 'CORE_S_continuous', 'STAIR_S_stair_hall'], 'F8': ['CORE_N_continuous', 'CORE_S_continuous', 'STAIR_S_stair_hall']}.
- Partition ends on facades checked: 77.

## Limits

- Door/open-contact reachability follows the declared, inferred scheme; it does not verify the real interior.
- Shell identity is against candidate_04 (itself an approximate regularisation); no new mesh-fidelity score is claimed.
- Browser transport proves the saved artefacts display unchanged; visual plausibility needs human review of the saved screenshots and plans.
