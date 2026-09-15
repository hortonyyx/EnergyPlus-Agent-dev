# Voimatalo developer candidate validation

Overall self-consistency: **pass**

## Replay and declared-plan checks

| Check | Status |
|---|---|
| Source digest and exact export replay | pass |
| Old candidate exact replay compatibility | pass |
| No same-height source-space overlap | pass |
| F1–F8 union covers declared case_plan outline | pass |
| Two continuous cores and per-storey declared doors | pass |
| Usable spaces reach exterior in declared door graph | pass |
| Opening count and mapping retention | pass |

## One-way mesh diagnostic

- `candidate_03`: distance mean 2.364 m, q50 2.426 m, q90 2.897 m; axis difference mean 10.14°, q90 20.07°.
- `candidate_02`: distance mean 0.070 m, q50 0.034 m, q90 0.183 m; axis difference mean 4.54°, q90 9.15°.

## Interpretation limits

- Storey coverage only proves consistency with `case_plan.json`; it is not a truth or fidelity test.
- The mesh metric samples the fixed 2,090 original near-vertical faces at z=8–22 m and measures mesh → candidate exterior only. Extra or missing candidate perimeter is not penalised.
- Missing/cropped end faces and internal partitions cannot be verified by this metric. Relief and slanted facade triangles can bias distance and axis difference.
- Door reachability follows declared, partly inferred doors. It does not establish the real circulation layout.
- The U-shaped service/lobby spaces, their core subtraction and the north-service wall position are case-plan hypotheses, not measurements.
- No exterior classification uses the presence of any adjacent host; perimeters come from same-height source-space unions.
