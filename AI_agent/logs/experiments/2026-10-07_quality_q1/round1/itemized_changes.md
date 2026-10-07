# Q1 A–C 逐项清单

从 `replay_report.json.gz` 自动摘出全部 applied_changes、eliminated、rejected；序号对应原数组，未去重。
`floor_regularization_rejected` 是同层明细的汇总封套，不能把它再算作独立缺陷。完整嵌套原因与回滚前状态见原 JSON 的同一位置。
拒绝组没有交付后的几何与精度指标；attempted_changes_not_delivered 是尝试后回滚，不能记作已消除。

## sm21_role

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[0].items`。
已应用 0；已消除 0；拒绝记录 4；尝试后回滚 2。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `cross_storey_alignment_rejected` · PLAN.F2/wall-corridor-south / PLAN.F1/wall-corridor-S

   distance_m=0.11049756; overlap_m=15.0 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 7 对原有 >=30cm 分离；逐对前后值见本条 JSON。

2. `rejected[1]` · `cross_storey_alignment_rejected` · PLAN.F2/wall-corridor-north / PLAN.F1/wall-corridor-N

   distance_m=0.132090042; overlap_m=15.0 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 3 对原有 >=30cm 分离；逐对前后值见本条 JSON。

3. `rejected[2]` · `storey_wall_offset_under_0_30m` · PLAN.F1/wall-corridor-N / PLAN.F2/wall-corridor-north

   distance_m=0.132090042; overlap_m=15.0 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

4. `rejected[3]` · `storey_wall_offset_under_0_30m` · PLAN.F1/wall-corridor-S / PLAN.F2/wall-corridor-south

   distance_m=0.11049756; overlap_m=15.0 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

## sm21_single

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[1].items`。
已应用 0；已消除 0；拒绝记录 4；尝试后回滚 2。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `cross_storey_alignment_rejected` · F2/corridor_N / F1/corridor_N

   distance_m=0.017547497; overlap_m=15.0 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 3 对原有 >=30cm 分离；逐对前后值见本条 JSON。

2. `rejected[1]` · `cross_storey_alignment_rejected` · F2/corridor_S / F1/corridor_S

   distance_m=0.079618495; overlap_m=15.0 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 1 对原有 >=30cm 分离；逐对前后值见本条 JSON。

3. `rejected[2]` · `storey_wall_offset_under_0_30m` · F1/corridor_S / F2/corridor_S

   distance_m=0.079618495; overlap_m=15.0 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

4. `rejected[3]` · `storey_wall_offset_under_0_30m` · F1/corridor_N / F2/corridor_N

   distance_m=0.017547497; overlap_m=15.0 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

## sm24_role

状态 `regularized`；原 JSON `regularization_replay[2].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## sm24_single

状态 `regularized`；原 JSON `regularization_replay[3].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## sm25_role

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[4].items`。
已应用 0；已消除 0；拒绝记录 16；尝试后回滚 0。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `ambiguous_partition_near_fixed_footprint` · p_corridor_wall / footprint[7]

   distance_m=0.12972973; length_m=4.99567474 Cannot safely remove p_corridor_wall near fixed footprint[7] (0.130 m apart over 4.996 m). Redraw the intended single boundary or keep a real space at least 0.60 m wide.

2. `rejected[1]` · `protected_strip_at_fixed_footprint` · p_bot_e / footprint[3]

   distance_m=0.12972973; length_m=10.012975779 Cannot merge p_bot_e into fixed footprint[3]: they are 0.130 m apart over 10.013 m, and the strip contains named seeds [] or openings ['W_bigN']. Remove the duplicate inner line, or confirm a real space at least 0.60 m wide; the outer footprint will not be moved.

3. `rejected[2]` · `parallel_wall_lines_under_0_30m` · p_corridor_wall / footprint[7]

   distance_m=0.12972973; overlap_m=4.99567474 Draw one wall line, or confirm two walls and move them at least 0.30 m apart.

4. `rejected[3]` · `parallel_wall_lines_under_0_30m` · p_bot_e / footprint[3]

   distance_m=0.12972973; overlap_m=10.012975779 Draw one wall line, or confirm two walls and move them at least 0.30 m apart.

5. `rejected[4]` · `space_width_under_0_60m` · s_B1

   minimum_width_m=0.12972973 Move the responsible existing boundary so every part of the space is at least 0.60 m wide; do not silently delete a named space.

6. `rejected[5]` · `space_width_under_0_60m` · s_O7

   minimum_width_m=0.12972973 Move the responsible existing boundary so every part of the space is at least 0.60 m wide; do not silently delete a named space.

7. `rejected[6]` · `protected_strip_at_fixed_footprint` · mwW / footprint[5]

   distance_m=0.109265734; length_m=13.993471164 Cannot merge mwW into fixed footprint[5]: they are 0.109 m apart over 13.993 m, and the strip contains named seeds [] or openings ['W_MW1', 'W_MW2']. Remove the duplicate inner line, or confirm a real space at least 0.60 m wide; the outer footprint will not be moved.

8. `rejected[7]` · `ambiguous_partition_near_fixed_footprint` · corrS / footprint[6]

   distance_m=0.130576714; length_m=5.004370629 Cannot safely remove corrS near fixed footprint[6] (0.131 m apart over 5.004 m). Redraw the intended single boundary or keep a real space at least 0.60 m wide.

9. `rejected[8]` · `protected_strip_at_fixed_footprint` · bandN / footprint[2]

   distance_m=0.152339499; length_m=9.986888112 Cannot merge bandN into fixed footprint[2]: they are 0.152 m apart over 9.987 m, and the strip contains named seeds [] or openings ['W_BN1']. Remove the duplicate inner line, or confirm a real space at least 0.60 m wide; the outer footprint will not be moved.

10. `rejected[9]` · `parallel_wall_lines_under_0_30m` · corrS / footprint[6]

   distance_m=0.130576714; overlap_m=5.004370629 Draw one wall line, or confirm two walls and move them at least 0.30 m apart.

11. `rejected[10]` · `parallel_wall_lines_under_0_30m` · mwW / footprint[5]

   distance_m=0.109265734; overlap_m=13.993471164 Draw one wall line, or confirm two walls and move them at least 0.30 m apart.

12. `rejected[11]` · `parallel_wall_lines_under_0_30m` · bandN / footprint[2]

   distance_m=0.152339499; overlap_m=9.986888112 Draw one wall line, or confirm two walls and move them at least 0.30 m apart.

13. `rejected[12]` · `space_width_under_0_60m` · stack5

   minimum_width_m=0.152339499 Move the responsible existing boundary so every part of the space is at least 0.60 m wide; do not silently delete a named space.

14. `rejected[13]` · `space_width_under_0_60m` · 

   minimum_width_m=0.109265734 Move the responsible existing boundary so every part of the space is at least 0.60 m wide; do not silently delete a named space.

15. `rejected[14]` · `floor_regularization_rejected` · F1

   尺寸见对应明细。  同层拒绝汇总；完整清单在本条 .report，状态 rejected。

16. `rejected[15]` · `floor_regularization_rejected` · F2

   尺寸见对应明细。  同层拒绝汇总；完整清单在本条 .report，状态 rejected。

## sm25_single

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[5].items`。
已应用 0；已消除 0；拒绝记录 8；尝试后回滚 0。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `ambiguous_partition_near_fixed_footprint` · PcorrS / footprint[6]

   distance_m=0.12972973; length_m=5.0 Cannot safely remove PcorrS near fixed footprint[6] (0.130 m apart over 5.000 m). Redraw the intended single boundary or keep a real space at least 0.60 m wide.

2. `rejected[1]` · `parallel_wall_lines_under_0_30m` · PcorrS / footprint[6]

   distance_m=0.12972973; overlap_m=5.0 Draw one wall line, or confirm two walls and move them at least 0.30 m apart.

3. `rejected[2]` · `space_width_under_0_60m` · roomA

   minimum_width_m=0.12972973 Move the responsible existing boundary so every part of the space is at least 0.60 m wide; do not silently delete a named space.

4. `rejected[3]` · `ambiguous_partition_near_fixed_footprint` · QcorrS / footprint[6]

   distance_m=0.130861505; length_m=4.97382199 Cannot safely remove QcorrS near fixed footprint[6] (0.131 m apart over 4.974 m). Redraw the intended single boundary or keep a real space at least 0.60 m wide.

5. `rejected[4]` · `parallel_wall_lines_under_0_30m` · QcorrS / footprint[6]

   distance_m=0.130861505; overlap_m=4.97382199 Draw one wall line, or confirm two walls and move them at least 0.30 m apart.

6. `rejected[5]` · `space_width_under_0_60m` · conference

   minimum_width_m=0.130861505 Move the responsible existing boundary so every part of the space is at least 0.60 m wide; do not silently delete a named space.

7. `rejected[6]` · `floor_regularization_rejected` · 1F

   尺寸见对应明细。  同层拒绝汇总；完整清单在本条 .report，状态 rejected。

8. `rejected[7]` · `floor_regularization_rejected` · 2F

   尺寸见对应明细。  同层拒绝汇总；完整清单在本条 .report，状态 rejected。

## 2026-10-01_opus_dev_sm21

状态 `regularized`；原 JSON `regularization_replay[6].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## 2026-10-01_opus_dev_sm24

状态 `regularized`；原 JSON `regularization_replay[7].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## 2026-10-01_opus_dev_sm25

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[8].items`。
已应用 0；已消除 0；拒绝记录 10；尝试后回滚 5。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `cross_storey_alignment_rejected` · F2/P_MTe / F1/P_LMe

   distance_m=8.726e-06; overlap_m=8.12 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 5 对原有 >=30cm 分离；逐对前后值见本条 JSON。

2. `rejected[1]` · `cross_storey_alignment_rejected` · F2/P_col / F1/P_col

   distance_m=8.726e-06; overlap_m=10.06 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 6 对原有 >=30cm 分离；逐对前后值见本条 JSON。

3. `rejected[2]` · `cross_storey_alignment_rejected` · F2/P_bo20.94 / F1/P_MRe

   distance_m=8.726e-06; overlap_m=3.94 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 1 对原有 >=30cm 分离；逐对前后值见本条 JSON。

4. `rejected[3]` · `cross_storey_alignment_rejected` · F2/P_BC / F1/P_corTop

   distance_m=8.726e-06; overlap_m=3.94 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 2 对原有 >=30cm 分离；逐对前后值见本条 JSON。

5. `rejected[4]` · `cross_storey_alignment_rejected` · F2/P_top / F1/P_off16

   distance_m=0.06; overlap_m=3.94 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 12 对原有 >=30cm 分离；逐对前后值见本条 JSON。

6. `rejected[5]` · `storey_wall_offset_under_0_30m` · F1/P_corTop / F2/P_BC

   distance_m=8.726e-06; overlap_m=3.94 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

7. `rejected[6]` · `storey_wall_offset_under_0_30m` · F1/P_col / F2/P_col

   distance_m=8.726e-06; overlap_m=10.06 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

8. `rejected[7]` · `storey_wall_offset_under_0_30m` · F1/P_LMe / F2/P_MTe

   distance_m=8.726e-06; overlap_m=8.12 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

9. `rejected[8]` · `storey_wall_offset_under_0_30m` · F1/P_MRe / F2/P_bo20.94

   distance_m=8.726e-06; overlap_m=3.94 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

10. `rejected[9]` · `storey_wall_offset_under_0_30m` · F1/P_off16 / F2/P_top

   distance_m=0.06; overlap_m=3.94 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

## 2026-09-26_sm25_height_cold_claude_run53

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[9].items`。
已应用 0；已消除 0；拒绝记录 52；尝试后回滚 31。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `cross_storey_alignment_rejected` · F2/wing_p10 / F1/wing_p10

   distance_m=5.2447e-05; overlap_m=3.965141004 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 8 对原有 >=30cm 分离；逐对前后值见本条 JSON。

2. `rejected[1]` · `cross_storey_alignment_rejected` · F2/wing_bot / F1/wing_bot

   distance_m=0.000429498; overlap_m=3.965141004 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 9 对原有 >=30cm 分离；逐对前后值见本条 JSON。

3. `rejected[2]` · `cross_storey_alignment_rejected` · F2/wing_left / F1/wing_left

   distance_m=0.000691821; overlap_m=10.039284155 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 9 对原有 >=30cm 分离；逐对前后值见本条 JSON。

4. `rejected[3]` · `cross_storey_alignment_rejected` · F2/conf_east / F1/mid_east_b

   distance_m=0.003575099; overlap_m=4.190362355 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 5 对原有 >=30cm 分离；逐对前后值见本条 JSON。

5. `rejected[4]` · `cross_storey_alignment_rejected` · F2/conf_east / F1/mid_east_a

   distance_m=0.003575099; overlap_m=4.102959338 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 5 对原有 >=30cm 分离；逐对前后值见本条 JSON。

6. `rejected[5]` · `cross_storey_alignment_rejected` · F2/r_y4a / F1/conf_top_a

   distance_m=0.004829368; overlap_m=4.087452471 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 16 对原有 >=30cm 分离；逐对前后值见本条 JSON。

7. `rejected[6]` · `cross_storey_alignment_rejected` · F2/r_y4d / F1/conf_top_b

   distance_m=0.004829368; overlap_m=4.031203696 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 21 对原有 >=30cm 分离；逐对前后值见本条 JSON。

8. `rejected[7]` · `cross_storey_alignment_rejected` · F2/r_y4c / F1/conf_top_b

   distance_m=0.004829368; overlap_m=3.743903276 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 20 对原有 >=30cm 分离；逐对前后值见本条 JSON。

9. `rejected[8]` · `cross_storey_alignment_rejected` · F2/r_y4e / F1/conf_top_b

   distance_m=0.004829368; overlap_m=0.045494481 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 21 对原有 >=30cm 分离；逐对前后值见本条 JSON。

10. `rejected[9]` · `cross_storey_alignment_rejected` · F2/wing_p12 / F1/wing_p12

   distance_m=0.005618435; overlap_m=3.965141004 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 8 对原有 >=30cm 分离；逐对前后值见本条 JSON。

11. `rejected[10]` · `cross_storey_alignment_rejected` · F2/wing_p8 / F1/wing_p8

   distance_m=0.005688364; overlap_m=3.965141004 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 8 对原有 >=30cm 分离；逐对前后值见本条 JSON。

12. `rejected[11]` · `cross_storey_alignment_rejected` · F2/n_x5 / F1/o_wall_x5

   distance_m=0.009122095; overlap_m=3.95024007 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 2 对原有 >=30cm 分离；逐对前后值见本条 JSON。

13. `rejected[12]` · `cross_storey_alignment_rejected` · F2/conf_bot / F1/mid_bot

   distance_m=0.009680944; overlap_m=3.996716212 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 5 对原有 >=30cm 分离；逐对前后值见本条 JSON。

14. `rejected[13]` · `cross_storey_alignment_rejected` · F2/wing_p14 / F1/wing_p14

   distance_m=0.010465285; overlap_m=3.965141004 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 8 对原有 >=30cm 分离；逐对前后值见本条 JSON。

15. `rejected[14]` · `cross_storey_alignment_rejected` · F2/conf_top / F1/mid_top

   distance_m=0.01048513; overlap_m=3.996716212 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 6 对原有 >=30cm 分离；逐对前后值见本条 JSON。

16. `rejected[15]` · `cross_storey_alignment_rejected` · F2/n_x997 / F1/o_wall_x994

   distance_m=0.033381399; overlap_m=3.95024007 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 4 对原有 >=30cm 分离；逐对前后值见本条 JSON。

17. `rejected[16]` · `cross_storey_alignment_rejected` · F2/r_x2094 / F1/conf_east

   distance_m=0.045494481; overlap_m=3.993889131 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 1 对原有 >=30cm 分离；逐对前后值见本条 JSON。

18. `rejected[17]` · `cross_storey_alignment_rejected` · F2/n_y16a / F1/o_wall_y16a

   distance_m=0.048373536; overlap_m=4.989976466 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 8 对原有 >=30cm 分离；逐对前后值见本条 JSON。

19. `rejected[18]` · `cross_storey_alignment_rejected` · F2/n_y16c / F1/wing_p16

   distance_m=0.048373536; overlap_m=3.965141004 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 18 对原有 >=30cm 分离；逐对前后值见本条 JSON。

20. `rejected[19]` · `cross_storey_alignment_rejected` · F2/r_x13 / F1/conf_mid

   distance_m=0.178348969; overlap_m=3.993889131 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 15 对原有 >=30cm 分离；逐对前后值见本条 JSON。

21. `rejected[20]` · `storey_wall_offset_under_0_30m` · F1/o_wall_x5 / F2/n_x5

   distance_m=0.009122095; overlap_m=3.95024007 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

22. `rejected[21]` · `storey_wall_offset_under_0_30m` · F1/o_wall_x994 / F2/n_x997

   distance_m=0.033381399; overlap_m=3.95024007 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

23. `rejected[22]` · `storey_wall_offset_under_0_30m` · F1/o_wall_y16a / F2/n_y16a

   distance_m=0.048373536; overlap_m=4.989976466 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

24. `rejected[23]` · `storey_wall_offset_under_0_30m` · F1/o_wall_y16a / F2/n_y16b

   distance_m=0.048373536; overlap_m=0.009122095 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

25. `rejected[24]` · `storey_wall_offset_under_0_30m` · F1/o_wall_y16b / F2/n_y16b

   distance_m=0.048373536; overlap_m=4.925682682 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

26. `rejected[25]` · `storey_wall_offset_under_0_30m` · F1/wing_left / F2/wing_left

   distance_m=0.000691821; overlap_m=10.039284155 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

27. `rejected[26]` · `storey_wall_offset_under_0_30m` · F1/wing_bot / F2/wing_bot

   distance_m=0.000429498; overlap_m=3.965141004 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

28. `rejected[27]` · `storey_wall_offset_under_0_30m` · F1/wing_p16 / F2/n_y16c

   distance_m=0.048373536; overlap_m=3.965141004 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

29. `rejected[28]` · `storey_wall_offset_under_0_30m` · F1/wing_p14 / F2/wing_p14

   distance_m=0.010465285; overlap_m=3.965141004 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

30. `rejected[29]` · `storey_wall_offset_under_0_30m` · F1/wing_p12 / F2/wing_p12

   distance_m=0.005618435; overlap_m=3.965141004 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

31. `rejected[30]` · `storey_wall_offset_under_0_30m` · F1/wing_p10 / F2/wing_p10

   distance_m=5.2447e-05; overlap_m=3.965141004 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

32. `rejected[31]` · `storey_wall_offset_under_0_30m` · F1/wing_p8 / F2/wing_p8

   distance_m=0.005688364; overlap_m=3.965141004 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

33. `rejected[32]` · `storey_wall_offset_under_0_30m` · F1/mid_top / F2/conf_top

   distance_m=0.01048513; overlap_m=3.996716212 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

34. `rejected[33]` · `storey_wall_offset_under_0_30m` · F1/mid_east_a / F2/conf_east

   distance_m=0.003575099; overlap_m=4.102959338 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

35. `rejected[34]` · `storey_wall_offset_under_0_30m` · F1/mid_east_b / F2/conf_east

   distance_m=0.003575099; overlap_m=4.190362355 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

36. `rejected[35]` · `storey_wall_offset_under_0_30m` · F1/mid_bot / F2/conf_bot

   distance_m=0.009680944; overlap_m=3.996716212 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

37. `rejected[36]` · `storey_wall_offset_under_0_30m` · F1/conf_top_a / F2/r_y4a

   distance_m=0.004829368; overlap_m=4.087452471 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

38. `rejected[37]` · `storey_wall_offset_under_0_30m` · F1/conf_top_a / F2/r_y4b

   distance_m=0.004829368; overlap_m=3.900461954 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

39. `rejected[38]` · `storey_wall_offset_under_0_30m` · F1/conf_top_a / F2/r_y4c

   distance_m=0.004829368; overlap_m=0.178348969 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

40. `rejected[39]` · `storey_wall_offset_under_0_30m` · F1/conf_top_b / F2/r_y4c

   distance_m=0.004829368; overlap_m=3.743903276 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

41. `rejected[40]` · `storey_wall_offset_under_0_30m` · F1/conf_top_b / F2/r_y4d

   distance_m=0.004829368; overlap_m=4.031203696 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

42. `rejected[41]` · `storey_wall_offset_under_0_30m` · F1/conf_top_b / F2/r_y4e

   distance_m=0.004829368; overlap_m=0.045494481 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

43. `rejected[42]` · `storey_wall_offset_under_0_30m` · F1/conf_mid / F2/r_x13

   distance_m=0.178348969; overlap_m=3.993889131 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

44. `rejected[43]` · `storey_wall_offset_under_0_30m` · F1/conf_east / F2/r_x2094

   distance_m=0.045494481; overlap_m=3.993889131 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

45. `rejected[44]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[0] / F2/footprint[0]

   distance_m=0.006582324; overlap_m=14.99171969 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

46. `rejected[45]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[1] / F2/footprint[1]

   distance_m=0.009971336; overlap_m=13.989524225 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

47. `rejected[46]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[2] / F2/footprint[2]

   distance_m=0.000429498; overlap_m=9.991771887 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

48. `rejected[47]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[3] / F2/footprint[3]

   distance_m=0.010820578; overlap_m=6.001316465 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

49. `rejected[48]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[4] / F2/footprint[4]

   distance_m=0.00647743; overlap_m=19.994364352 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

50. `rejected[49]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[5] / F2/footprint[5]

   distance_m=0.009122095; overlap_m=14.098646879 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

51. `rejected[50]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[6] / F2/footprint[6]

   distance_m=0.01048513; overlap_m=4.989976466 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

52. `rejected[51]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[7] / F2/footprint[7]

   distance_m=0.012999607; overlap_m=5.882138178 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

## 2026-09-26_sm25_height_repeat_claude_run54

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[10].items`。
已应用 0；已消除 0；拒绝记录 40；尝试后回滚 16。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `cross_storey_alignment_rejected` · F2/P_conf / F1/P_mid_top

   distance_m=0.010053498; overlap_m=3.857890148 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 5 对原有 >=30cm 分离；逐对前后值见本条 JSON。

2. `rejected[1]` · `cross_storey_alignment_rejected` · F2/P_bc / F1/P_off2_right

   distance_m=0.013303654; overlap_m=3.955744766 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 2 对原有 >=30cm 分离；逐对前后值见本条 JSON。

3. `rejected[2]` · `cross_storey_alignment_rejected` · F2/P_top_bottom / F1/P_nw_bottom

   distance_m=0.01588644; overlap_m=9.974070873 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 12 对原有 >=30cm 分离；逐对前后值见本条 JSON。

4. `rejected[3]` · `cross_storey_alignment_rejected` · F2/P_c3 / F1/P_o5

   distance_m=0.019699469; overlap_m=3.95826473 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 7 对原有 >=30cm 分离；逐对前后值见本条 JSON。

5. `rejected[4]` · `cross_storey_alignment_rejected` · F2/P_conf / F1/P_mid_top

   distance_m=0.021969303; overlap_m=8.00872886 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 9 对原有 >=30cm 分离；逐对前后值见本条 JSON。

6. `rejected[5]` · `cross_storey_alignment_rejected` · F2/P_c2 / F1/P_o4

   distance_m=0.025872607; overlap_m=3.95826473 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 7 对原有 >=30cm 分离；逐对前后值见本条 JSON。

7. `rejected[6]` · `cross_storey_alignment_rejected` · F2/P_top_bottom / F1/P_o2

   distance_m=0.027417663; overlap_m=3.997407087 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 12 对原有 >=30cm 分离；逐对前后值见本条 JSON。

8. `rejected[7]` · `cross_storey_alignment_rejected` · F2/P_c1 / F1/P_o3

   distance_m=0.033250605; overlap_m=3.95826473 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 7 对原有 >=30cm 分离；逐对前后值见本条 JSON。

9. `rejected[8]` · `cross_storey_alignment_rejected` · F2/P_s2 / F1/P_mtg_div

   distance_m=0.034489281; overlap_m=3.906164757 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 1 对原有 >=30cm 分离；逐对前后值见本条 JSON。

10. `rejected[9]` · `cross_storey_alignment_rejected` · F2/P_col_left / F1/P_col_left

   distance_m=0.039142357; overlap_m=10.038188762 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 36 对原有 >=30cm 分离；逐对前后值见本条 JSON。

11. `rejected[10]` · `cross_storey_alignment_rejected` · F2/P_row_top / F1/P_mtg_top

   distance_m=0.045334647; overlap_m=15.872080713 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 17 对原有 >=30cm 分离；逐对前后值见本条 JSON。

12. `rejected[11]` · `cross_storey_alignment_rejected` · F2/P_s4 / F1/P_mtg_top

   distance_m=0.048192308; overlap_m=3.906164757 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 1 对原有 >=30cm 分离；逐对前后值见本条 JSON。

13. `rejected[12]` · `cross_storey_alignment_rejected` · F2/P_ab / F1/P_off_div

   distance_m=0.052159668; overlap_m=3.955744766 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 2 对原有 >=30cm 分离；逐对前后值见本条 JSON。

14. `rejected[13]` · `cross_storey_alignment_rejected` · F2/P_c4 / F1/P_o6

   distance_m=0.100644831; overlap_m=3.95826473 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 7 对原有 >=30cm 分离；逐对前后值见本条 JSON。

15. `rejected[14]` · `cross_storey_alignment_rejected` · F2/P_col_bottom / F1/P_o_bottom

   distance_m=0.122389019; overlap_m=3.95826473 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 8 对原有 >=30cm 分离；逐对前后值见本条 JSON。

16. `rejected[15]` · `cross_storey_alignment_rejected` · F2/P_conf / F1/P_mid_top

   distance_m=0.122389019; overlap_m=3.857890148 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 5 对原有 >=30cm 分离；逐对前后值见本条 JSON。

17. `rejected[16]` · `storey_wall_offset_under_0_30m` · F1/P_off_div / F2/P_ab

   distance_m=0.052159668; overlap_m=3.955744766 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

18. `rejected[17]` · `storey_wall_offset_under_0_30m` · F1/P_nw_bottom / F2/P_top_bottom

   distance_m=0.01588644; overlap_m=9.974070873 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

19. `rejected[18]` · `storey_wall_offset_under_0_30m` · F1/P_off2_right / F2/P_bc

   distance_m=0.013303654; overlap_m=3.955744766 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

20. `rejected[19]` · `storey_wall_offset_under_0_30m` · F1/P_col_left / F2/P_col_left

   distance_m=0.039142357; overlap_m=10.038188762 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

21. `rejected[20]` · `storey_wall_offset_under_0_30m` · F1/P_o2 / F2/P_top_bottom

   distance_m=0.027417663; overlap_m=3.997407087 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

22. `rejected[21]` · `storey_wall_offset_under_0_30m` · F1/P_o3 / F2/P_c1

   distance_m=0.033250605; overlap_m=3.95826473 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

23. `rejected[22]` · `storey_wall_offset_under_0_30m` · F1/P_o4 / F2/P_c2

   distance_m=0.025872607; overlap_m=3.95826473 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

24. `rejected[23]` · `storey_wall_offset_under_0_30m` · F1/P_o5 / F2/P_c3

   distance_m=0.019699469; overlap_m=3.95826473 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

25. `rejected[24]` · `storey_wall_offset_under_0_30m` · F1/P_o6 / F2/P_c4

   distance_m=0.100644831; overlap_m=3.95826473 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

26. `rejected[25]` · `storey_wall_offset_under_0_30m` · F1/P_o_bottom / F2/P_col_bottom

   distance_m=0.122389019; overlap_m=3.95826473 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

27. `rejected[26]` · `storey_wall_offset_under_0_30m` · F1/P_mid_top / F2/P_conf

   distance_m=0.010053498; overlap_m=3.857890148 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

28. `rejected[27]` · `storey_wall_offset_under_0_30m` · F1/P_mid_top / F2/P_conf

   distance_m=0.021969303; overlap_m=8.00872886 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

29. `rejected[28]` · `storey_wall_offset_under_0_30m` · F1/P_mid_top / F2/P_conf

   distance_m=0.122389019; overlap_m=3.857890148 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

30. `rejected[29]` · `storey_wall_offset_under_0_30m` · F1/P_mtg_top / F2/P_row_top

   distance_m=0.045334647; overlap_m=15.872080713 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

31. `rejected[30]` · `storey_wall_offset_under_0_30m` · F1/P_mtg_top / F2/P_s4

   distance_m=0.048192308; overlap_m=3.906164757 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

32. `rejected[31]` · `storey_wall_offset_under_0_30m` · F1/P_mtg_div / F2/P_s2

   distance_m=0.034489281; overlap_m=3.906164757 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

33. `rejected[32]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[0] / F2/footprint[0]

   distance_m=0.006580664; overlap_m=14.987035436 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

34. `rejected[33]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[1] / F2/footprint[1]

   distance_m=0.008605366; overlap_m=14.009819967 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

35. `rejected[34]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[2] / F2/footprint[2]

   distance_m=0.122389019; overlap_m=9.995716156 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

36. `rejected[35]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[3] / F2/footprint[3]

   distance_m=0.008643042; overlap_m=5.856879939 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

37. `rejected[36]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[4] / F2/footprint[4]

   distance_m=0.010826026; overlap_m=19.891095406 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

38. `rejected[37]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[5] / F2/footprint[5]

   distance_m=0.117547637; overlap_m=13.987997818 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

39. `rejected[38]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[6] / F2/footprint[6]

   distance_m=0.010053498; overlap_m=4.982713915 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

40. `rejected[39]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[7] / F2/footprint[7]

   distance_m=0.008643042; overlap_m=5.99103761 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

## 2026-09-26_sm24_whole_building_claude_run55

状态 `regularized`；原 JSON `regularization_replay[11].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## 2026-09-26_sm24_whole_building_repeat_claude_run56

状态 `regularized`；原 JSON `regularization_replay[12].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## 2026-09-26_sm21_whole_building_claude_run57

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[13].items`。
已应用 0；已消除 0；拒绝记录 14；尝试后回滚 14。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `cross_storey_alignment_rejected` · F2/CS-d / F1/CS-c

   distance_m=0.000946659; overlap_m=3.751082564 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 3 对原有 >=30cm 分离；逐对前后值见本条 JSON。

2. `rejected[1]` · `cross_storey_alignment_rejected` · F2/CS-a / F1/CS-a

   distance_m=0.000946659; overlap_m=3.75 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 5 对原有 >=30cm 分离；逐对前后值见本条 JSON。

3. `rejected[2]` · `cross_storey_alignment_rejected` · F2/CN-a / F1/CN-a

   distance_m=0.003110868; overlap_m=4.998201956 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 4 对原有 >=30cm 分离；逐对前后值见本条 JSON。

4. `rejected[3]` · `cross_storey_alignment_rejected` · F2/CN-a / F1/CN-b

   distance_m=0.003110868; overlap_m=2.501798044 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 4 对原有 >=30cm 分离；逐对前后值见本条 JSON。

5. `rejected[4]` · `storey_wall_offset_under_0_30m` · F1/CN-a / F2/CN-a

   distance_m=0.003110868; overlap_m=4.998201956 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

6. `rejected[5]` · `storey_wall_offset_under_0_30m` · F1/CN-b / F2/CN-a

   distance_m=0.003110868; overlap_m=2.501798044 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

7. `rejected[6]` · `storey_wall_offset_under_0_30m` · F1/CN-b / F2/CN-b

   distance_m=0.003110868; overlap_m=2.497482739 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

8. `rejected[7]` · `storey_wall_offset_under_0_30m` · F1/CN-c / F2/CN-b

   distance_m=0.003110868; overlap_m=5.002517261 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

9. `rejected[8]` · `storey_wall_offset_under_0_30m` · F1/CS-a / F2/CS-a

   distance_m=0.000946659; overlap_m=3.75 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

10. `rejected[9]` · `storey_wall_offset_under_0_30m` · F1/CS-a / F2/CS-b

   distance_m=0.000946659; overlap_m=1.248201956 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

11. `rejected[10]` · `storey_wall_offset_under_0_30m` · F1/CS-b / F2/CS-b

   distance_m=0.000946659; overlap_m=2.501798044 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

12. `rejected[11]` · `storey_wall_offset_under_0_30m` · F1/CS-b / F2/CS-c

   distance_m=0.000946659; overlap_m=2.497482739 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

13. `rejected[12]` · `storey_wall_offset_under_0_30m` · F1/CS-c / F2/CS-c

   distance_m=0.000946659; overlap_m=1.251434698 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

14. `rejected[13]` · `storey_wall_offset_under_0_30m` · F1/CS-c / F2/CS-d

   distance_m=0.000946659; overlap_m=3.751082564 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

## 2026-09-27_sm21_whole_building_repeat_claude_run58

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[14].items`。
已应用 0；已消除 0；拒绝记录 14；尝试后回滚 14。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `cross_storey_alignment_rejected` · F2/PS4 / F1/PS3

   distance_m=0.001334849; overlap_m=3.758122744 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 3 对原有 >=30cm 分离；逐对前后值见本条 JSON。

2. `rejected[1]` · `cross_storey_alignment_rejected` · F2/PS1 / F1/PS1

   distance_m=0.001334849; overlap_m=3.747292419 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 5 对原有 >=30cm 分离；逐对前后值见本条 JSON。

3. `rejected[2]` · `cross_storey_alignment_rejected` · F2/PN2 / F1/PN3

   distance_m=0.009475962; overlap_m=4.989200864 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 6 对原有 >=30cm 分离；逐对前后值见本条 JSON。

4. `rejected[3]` · `cross_storey_alignment_rejected` · F2/PN2 / F1/PN2

   distance_m=0.009475962; overlap_m=2.516214299 Cross-storey alignment was rolled back because the affected current plan did not strictly recompile with unchanged rooms, openings, connections and existing wall separations of at least 0.30 m. 会改变 6 对原有 >=30cm 分离；逐对前后值见本条 JSON。

5. `rejected[4]` · `storey_wall_offset_under_0_30m` · F1/PN1 / F2/PN1

   distance_m=0.009475962; overlap_m=5.0 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

6. `rejected[5]` · `storey_wall_offset_under_0_30m` · F1/PN2 / F2/PN1

   distance_m=0.009475962; overlap_m=2.494584838 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

7. `rejected[6]` · `storey_wall_offset_under_0_30m` · F1/PN2 / F2/PN2

   distance_m=0.009475962; overlap_m=2.516214299 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

8. `rejected[7]` · `storey_wall_offset_under_0_30m` · F1/PN3 / F2/PN2

   distance_m=0.009475962; overlap_m=4.989200864 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

9. `rejected[8]` · `storey_wall_offset_under_0_30m` · F1/PS1 / F2/PS1

   distance_m=0.001334849; overlap_m=3.747292419 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

10. `rejected[9]` · `storey_wall_offset_under_0_30m` · F1/PS1 / F2/PS2

   distance_m=0.001334849; overlap_m=1.252707581 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

11. `rejected[10]` · `storey_wall_offset_under_0_30m` · F1/PS2 / F2/PS2

   distance_m=0.001334849; overlap_m=2.494584838 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

12. `rejected[11]` · `storey_wall_offset_under_0_30m` · F1/PS2 / F2/PS3

   distance_m=0.001334849; overlap_m=2.516214299 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

13. `rejected[12]` · `storey_wall_offset_under_0_30m` · F1/PS3 / F2/PS3

   distance_m=0.001334849; overlap_m=1.23107812 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

14. `rejected[13]` · `storey_wall_offset_under_0_30m` · F1/PS3 / F2/PS4

   distance_m=0.001334849; overlap_m=3.758122744 Align one affected plan draft to the higher-priority existing wall line, then recompile it.
