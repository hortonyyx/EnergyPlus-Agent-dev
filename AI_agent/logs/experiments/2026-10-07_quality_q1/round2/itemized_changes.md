# Q1 A–C 逐项清单

从 `replay_report.json.gz` 自动摘出全部 applied_changes、eliminated、rejected；序号对应原数组，未去重。
`floor_regularization_rejected` 是同层明细的汇总封套，不能把它再算作独立缺陷。完整嵌套原因与回滚前状态见原 JSON 的同一位置。
拒绝组没有交付后的几何与精度指标；attempted_changes_not_delivered 是尝试后回滚，不能记作已消除。

## sm21_role

状态 `regularized`；原 JSON `regularization_replay[0].items`。
已应用 2；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `PLAN.F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

楼层 `PLAN.F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

1. `applied_changes[0]` · `move_wall_line` · PLAN.F2

   from_m=3.005405405; to_m=3.115902965; movement_m=0.11049756 cross-storey alignment to an existing higher-priority wall line

2. `applied_changes[1]` · `move_wall_line` · PLAN.F2

   from_m=5.005405405; to_m=4.873315364; movement_m=0.132090042 cross-storey alignment to an existing higher-priority wall line

### eliminated

无。

### rejected

无。

## sm21_single

状态 `regularized`；原 JSON `regularization_replay[1].items`。
已应用 2；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

1. `applied_changes[0]` · `move_wall_line` · F2

   from_m=5.020242915; to_m=5.002695418; movement_m=0.017547497 cross-storey alignment to an existing higher-priority wall line

2. `applied_changes[1]` · `move_wall_line` · F2

   from_m=3.076923077; to_m=2.997304582; movement_m=0.079618495 cross-storey alignment to an existing higher-priority wall line

### eliminated

无。

### rejected

无。

## sm24_role

状态 `regularized`；原 JSON `regularization_replay[2].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## sm24_single

状态 `regularized`；原 JSON `regularization_replay[3].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## sm25_role

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[4].items`。
已应用 0；已消除 0；拒绝记录 6；尝试后回滚 31。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 2，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `rejected_no_deliverable`；A 阶段独立结果仅作证据、未交付 `True`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 3，消除窄条空间 1，删除种子 0，合并重复开口 0，删除退化接头 1。

整楼交付状态 `rejected_no_deliverable`；A 阶段独立结果仅作证据、未交付 `True`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `storey_wall_offset_under_0_30m` · F1/p_corridor_wall / F2/corrS

   distance_m=0.004281975; overlap_m=3.92729027 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

2. `rejected[1]` · `storey_wall_offset_under_0_30m` · F1/p_bot_e / F2/bandN

   distance_m=0.004281975; overlap_m=3.935986159 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

3. `rejected[2]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[2] / F2/footprint[1]

   distance_m=0.026087667; overlap_m=13.989189189 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

4. `rejected[3]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[3] / F2/footprint[2]

   distance_m=0.004281975; overlap_m=9.986888112 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

5. `rejected[4]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[6] / F2/footprint[5]

   distance_m=0.008695889; overlap_m=13.989189189 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

6. `rejected[5]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[7] / F2/footprint[6]

   distance_m=0.004281975; overlap_m=4.99567474 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

## sm25_single

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[5].items`。
已应用 0；已消除 0；拒绝记录 5；尝试后回滚 23。

楼层 `1F` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 1，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `rejected_no_deliverable`；A 阶段独立结果仅作证据、未交付 `True`；实际计入整楼消除 0。

楼层 `2F` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 1，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `rejected_no_deliverable`；A 阶段独立结果仅作证据、未交付 `True`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `storey_wall_offset_under_0_30m` · 1F/PcorrS / 2F/QcorrS

   distance_m=0.012991836; overlap_m=3.922338569 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

2. `rejected[1]` · `storey_wall_offset_under_0_30m` · 1F/Pm1N / 2F/QhallS

   distance_m=0.009101359; overlap_m=9.986910995 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

3. `rejected[2]` · `fixed_footprint_storey_offset_under_0_30m` · 1F/footprint[1] / 2F/footprint[1]

   distance_m=0.013089005; overlap_m=14.248648649 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

4. `rejected[3]` · `fixed_footprint_storey_offset_under_0_30m` · 1F/footprint[5] / 2F/footprint[5]

   distance_m=0.02617801; overlap_m=13.989189189 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

5. `rejected[4]` · `fixed_footprint_storey_offset_under_0_30m` · 1F/footprint[6] / 2F/footprint[6]

   distance_m=0.012991836; overlap_m=4.97382199 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

## 2026-10-01_opus_dev_sm21

状态 `regularized`；原 JSON `regularization_replay[6].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## 2026-10-01_opus_dev_sm24

状态 `regularized`；原 JSON `regularization_replay[7].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## 2026-10-01_opus_dev_sm25

状态 `regularized`；原 JSON `regularization_replay[8].items`。
已应用 5；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

1. `applied_changes[0]` · `move_wall_line` · F2

   from_m=8.940008726; to_m=8.94; movement_m=8.726e-06 cross-storey alignment to an existing higher-priority wall line

2. `applied_changes[1]` · `move_wall_line` · F2

   from_m=11.059991274; to_m=11.06; movement_m=8.726e-06 cross-storey alignment to an existing higher-priority wall line

3. `applied_changes[2]` · `move_wall_line` · F2

   from_m=20.940008726; to_m=20.94; movement_m=8.726e-06 cross-storey alignment to an existing higher-priority wall line

4. `applied_changes[3]` · `move_wall_line` · F2

   from_m=9.940008726; to_m=9.94; movement_m=8.726e-06 cross-storey alignment to an existing higher-priority wall line

5. `applied_changes[4]` · `move_wall_line` · F1

   from_m=16.0; to_m=16.06; movement_m=0.06 cross-storey alignment to an existing higher-priority wall line

### eliminated

无。

### rejected

无。

## 2026-09-26_sm25_height_cold_claude_run53

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[9].items`。
已应用 0；已消除 0；拒绝记录 10；尝试后回滚 24。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `rejected_no_deliverable`；A 阶段独立结果仅作证据、未交付 `True`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `rejected_no_deliverable`；A 阶段独立结果仅作证据、未交付 `True`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `storey_wall_offset_under_0_30m` · F1/wing_bot / F2/wing_bot

   distance_m=0.000429498; overlap_m=3.965141004 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

2. `rejected[1]` · `storey_wall_offset_under_0_30m` · F1/mid_top / F2/conf_top

   distance_m=0.01048513; overlap_m=4.00029131 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

3. `rejected[2]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[0] / F2/footprint[0]

   distance_m=0.006582324; overlap_m=14.99171969 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

4. `rejected[3]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[1] / F2/footprint[1]

   distance_m=0.009971336; overlap_m=13.989524225 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

5. `rejected[4]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[2] / F2/footprint[2]

   distance_m=0.000429498; overlap_m=9.991771887 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

6. `rejected[5]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[3] / F2/footprint[3]

   distance_m=0.010820578; overlap_m=6.001316465 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

7. `rejected[6]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[4] / F2/footprint[4]

   distance_m=0.00647743; overlap_m=19.994364352 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

8. `rejected[7]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[5] / F2/footprint[5]

   distance_m=0.009122095; overlap_m=14.098646879 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

9. `rejected[8]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[6] / F2/footprint[6]

   distance_m=0.01048513; overlap_m=4.989976466 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

10. `rejected[9]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[7] / F2/footprint[7]

   distance_m=0.012999607; overlap_m=5.882138178 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

## 2026-09-26_sm25_height_repeat_claude_run54

状态 `rejected_no_deliverable_after_metrics`；原 JSON `regularization_replay[10].items`。
已应用 0；已消除 0；拒绝记录 10；尝试后回滚 18。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `rejected_no_deliverable`；A 阶段独立结果仅作证据、未交付 `True`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `rejected_no_deliverable`；A 阶段独立结果仅作证据、未交付 `True`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

1. `rejected[0]` · `storey_wall_offset_under_0_30m` · F1/P_o_bottom / F2/P_col_bottom

   distance_m=0.122389019; overlap_m=3.997407087 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

2. `rejected[1]` · `storey_wall_offset_under_0_30m` · F1/P_mid_top / F2/P_conf

   distance_m=0.010053498; overlap_m=3.879859451 Align one affected plan draft to the higher-priority existing wall line, then recompile it.

3. `rejected[2]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[0] / F2/footprint[0]

   distance_m=0.006580664; overlap_m=14.987035436 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

4. `rejected[3]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[1] / F2/footprint[1]

   distance_m=0.008605366; overlap_m=14.009819967 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

5. `rejected[4]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[2] / F2/footprint[2]

   distance_m=0.122389019; overlap_m=9.995716156 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

6. `rejected[5]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[3] / F2/footprint[3]

   distance_m=0.008643042; overlap_m=5.856879939 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

7. `rejected[6]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[4] / F2/footprint[4]

   distance_m=0.010826026; overlap_m=19.891095406 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

8. `rejected[7]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[5] / F2/footprint[5]

   distance_m=0.117547637; overlap_m=13.987997818 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

9. `rejected[8]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[6] / F2/footprint[6]

   distance_m=0.010053498; overlap_m=4.982713915 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

10. `rejected[9]` · `fixed_footprint_storey_offset_under_0_30m` · F1/footprint[7] / F2/footprint[7]

   distance_m=0.008643042; overlap_m=5.99103761 Outer footprints are fixed. Confirm the setback, or correct the affected plan evidence before compilation.

## 2026-09-26_sm24_whole_building_claude_run55

状态 `legacy_geometric_pass_source_save_incompatible`；原 JSON `regularization_replay[11].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `False`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `legacy_geometric_pass_source_save_incompatible`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## 2026-09-26_sm24_whole_building_repeat_claude_run56

状态 `legacy_geometric_pass_source_save_incompatible`；原 JSON `regularization_replay[12].items`。
已应用 0；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `False`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `legacy_geometric_pass_source_save_incompatible`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## 2026-09-26_sm21_whole_building_claude_run57

状态 `regularized`；原 JSON `regularization_replay[13].items`。
已应用 7；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

1. `applied_changes[0]` · `move_wall_line` · F2

   from_m=3.000676315; to_m=2.999729657; movement_m=0.000946659 cross-storey alignment to an existing higher-priority wall line

2. `applied_changes[1]` · `move_wall_line` · F2

   from_m=3.000676315; to_m=2.999729657; movement_m=0.000946659 align touching collinear wall ends to an existing line

3. `applied_changes[2]` · `move_wall_line` · F2

   from_m=3.000676315; to_m=2.999729657; movement_m=0.000946659 align touching collinear wall ends to an existing line

4. `applied_changes[3]` · `move_wall_line` · F2

   from_m=3.000676315; to_m=2.999729657; movement_m=0.000946659 align touching collinear wall ends to an existing line

5. `applied_changes[4]` · `move_wall_line` · F1

   from_m=5.000270343; to_m=4.997159475; movement_m=0.003110868 cross-storey alignment to an existing higher-priority wall line

6. `applied_changes[5]` · `move_wall_line` · F1

   from_m=5.000270343; to_m=4.997159475; movement_m=0.003110868 align touching collinear wall ends to an existing line

7. `applied_changes[6]` · `move_wall_line` · F1

   from_m=5.000270343; to_m=4.997159475; movement_m=0.003110868 align touching collinear wall ends to an existing line

### eliminated

无。

### rejected

无。

## 2026-09-27_sm21_whole_building_repeat_claude_run58

状态 `regularized`；原 JSON `regularization_replay[14].items`。
已应用 7；已消除 0；拒绝记录 0；尝试后回滚 0。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

1. `applied_changes[0]` · `move_wall_line` · F2

   from_m=2.995929444; to_m=2.994594595; movement_m=0.001334849 cross-storey alignment to an existing higher-priority wall line

2. `applied_changes[1]` · `move_wall_line` · F2

   from_m=2.995929444; to_m=2.994594595; movement_m=0.001334849 align touching collinear wall ends to an existing line

3. `applied_changes[2]` · `move_wall_line` · F2

   from_m=2.995929444; to_m=2.994594595; movement_m=0.001334849 align touching collinear wall ends to an existing line

4. `applied_changes[3]` · `move_wall_line` · F2

   from_m=2.995929444; to_m=2.994594595; movement_m=0.001334849 align touching collinear wall ends to an existing line

5. `applied_changes[4]` · `move_wall_line` · F1

   from_m=4.994594595; to_m=5.004070556; movement_m=0.009475962 cross-storey alignment to an existing higher-priority wall line

6. `applied_changes[5]` · `move_wall_line` · F1

   from_m=4.994594595; to_m=5.004070556; movement_m=0.009475962 align touching collinear wall ends to an existing line

7. `applied_changes[6]` · `move_wall_line` · F1

   from_m=4.994594595; to_m=5.004070556; movement_m=0.009475962 align touching collinear wall ends to an existing line

### eliminated

无。

### rejected

无。
