# Q1 A–C 逐项清单

从 `replay_report.json.gz` 自动摘出全部 applied_changes、eliminated、rejected；序号对应原数组，未去重。
`floor_regularization_rejected` 是同层明细的汇总封套，不能把它再算作独立缺陷。完整嵌套原因与回滚前状态见原 JSON 的同一位置。
拒绝组没有交付后的几何与精度指标；attempted_changes_not_delivered 是尝试后回滚，不能记作已消除。

## sm21_role

状态 `regularized`；原 JSON `regularization_replay[0].items`。
已应用 2；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
已应用 2；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
已应用 0；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
已应用 0；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

无。

### eliminated

无。

### rejected

无。

## sm25_role

状态 `regularized`；原 JSON `regularization_replay[4].items`。
已应用 33；删除/合并记录 6；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 4 条；消除偏差的唯一外皮线对 4 对。外皮对齐不重复计入删除/合并记录。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 2，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 2。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 3，消除窄条空间 1，删除种子 0，合并重复开口 0，删除退化接头 1。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 4。

### applied_changes

1. `applied_changes[0]` · `merge_duplicate_wall_into_fixed_footprint` · p_corridor_wall / footprint[7]

   from_m=14.118918919; to_m=13.989189189; movement_m=0.12972973; length_m=4.99567474 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

2. `applied_changes[1]` · `retain_openings_on_merged_wall` · F1

   from_m=6.010810811; to_m=6.010810811; movement_m=0.0 openings already on the retained line survived the strip elimination and their before/after hosts remain explicitly mapped

3. `applied_changes[2]` · `merge_duplicate_wall_into_fixed_footprint` · p_bot_e / footprint[3]

   from_m=5.881081081; to_m=6.010810811; movement_m=0.12972973; length_m=10.012975779 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

4. `applied_changes[3]` · `move_wall_line` · F1

   from_m=14.118918919; to_m=13.989189189; movement_m=0.12972973 align touching collinear wall ends to an existing line

5. `applied_changes[4]` · `move_wall_line` · F1

   from_m=5.881081081; to_m=6.010810811; movement_m=0.12972973 align touching collinear wall ends to an existing line

6. `applied_changes[5]` · `retain_openings_on_merged_wall` · F2

   from_m=5.004370629; to_m=5.004370629; movement_m=0.0 openings already on the retained line survived the strip elimination and their before/after hosts remain explicitly mapped

7. `applied_changes[6]` · `merge_duplicate_wall_into_fixed_footprint` · mwW / footprint[5]

   from_m=5.113636364; to_m=5.004370629; movement_m=0.109265734; length_m=13.993471164 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

8. `applied_changes[7]` · `merge_duplicate_wall_into_fixed_footprint` · corrS / footprint[6]

   from_m=14.124047878; to_m=13.993471164; movement_m=0.130576714; length_m=5.004370629 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

9. `applied_changes[8]` · `retain_openings_on_merged_wall` · F2

   from_m=6.006528836; to_m=6.006528836; movement_m=0.0 openings already on the retained line survived the strip elimination and their before/after hosts remain explicitly mapped

10. `applied_changes[9]` · `merge_duplicate_wall_into_fixed_footprint` · bandN / footprint[2]

   from_m=5.854189336; to_m=6.006528836; movement_m=0.152339499; length_m=9.986888112 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

11. `applied_changes[10]` · `move_wall_line` · F2

   from_m=5.113636364; to_m=5.004370629; movement_m=0.109265734 align touching collinear wall ends to an existing line

12. `applied_changes[11]` · `remove_collapsed_wall_step` · F2

   from_m=5.004370629; to_m=5.004370629; movement_m=0.130576714 the sub-0.30 m connector collapsed to a point while its adjoining wall was aligned

13. `applied_changes[12]` · `move_wall_line` · F2

   from_m=14.124047878; to_m=13.993471164; movement_m=0.130576714 align touching collinear wall ends to an existing line

14. `applied_changes[13]` · `move_wall_line` · F2

   from_m=5.854189336; to_m=6.006528836; movement_m=0.152339499 align touching collinear wall ends to an existing line

15. `applied_changes[14]` · `move_wall_line` · F2

   from_m=13.993471164; to_m=13.989189189; movement_m=0.004281975 move a connected collinear wall-chain segment with its cross-storey footprint edge

16. `applied_changes[15]` · `move_footprint_edge` · F2/footprint[6] / F1/footprint[7]

   from_m=13.993471164; to_m=13.989189189; movement_m=0.004281975 align one overlapping cross-storey footprint edge to the policy-selected existing edge

17. `applied_changes[16]` · `move_wall_line` · F2

   from_m=6.006528836; to_m=6.010810811; movement_m=0.004281975 move a connected collinear wall-chain segment with its cross-storey footprint edge

18. `applied_changes[17]` · `move_footprint_edge` · F2/footprint[2] / F1/footprint[3]

   from_m=6.006528836; to_m=6.010810811; movement_m=0.004281975 align one overlapping cross-storey footprint edge to the policy-selected existing edge

19. `applied_changes[18]` · `move_footprint_edge` · F2/footprint[5] / F1/footprint[6]

   from_m=5.004370629; to_m=4.99567474; movement_m=0.008695889 align one overlapping cross-storey footprint edge to the policy-selected existing edge

20. `applied_changes[19]` · `move_footprint_edge` · F2/footprint[1] / F1/footprint[2]

   from_m=15.013111888; to_m=14.987024221; movement_m=0.026087667 align one overlapping cross-storey footprint edge to the policy-selected existing edge

21. `applied_changes[20]` · `move_wall_line` · F2

   from_m=7.986942329; to_m=8.0; movement_m=0.013057671 cross-storey alignment to an existing higher-priority wall line

22. `applied_changes[21]` · `move_wall_line` · F2

   from_m=13.971708379; to_m=13.989189189; movement_m=0.017480811 cross-storey alignment to an existing higher-priority wall line

23. `applied_changes[22]` · `move_wall_line` · F1

   from_m=5.881081081; to_m=5.854189336; movement_m=0.026891745 cross-storey alignment to an existing higher-priority wall line

24. `applied_changes[23]` · `move_wall_line` · F2

   from_m=12.034820457; to_m=12.0; movement_m=0.034820457 cross-storey alignment to an existing higher-priority wall line

25. `applied_changes[24]` · `move_wall_line` · F1

   from_m=3.935135135; to_m=3.895538629; movement_m=0.039596506 cross-storey alignment to an existing higher-priority wall line

26. `applied_changes[25]` · `move_wall_line` · F2

   from_m=9.967355822; to_m=10.010810811; movement_m=0.043454989 cross-storey alignment to an existing higher-priority wall line

27. `applied_changes[26]` · `move_wall_line` · F1

   from_m=16.0; to_m=15.952121872; movement_m=0.047878128 cross-storey alignment to an existing higher-priority wall line

28. `applied_changes[27]` · `move_wall_line` · F2

   from_m=9.003496503; to_m=8.9316609; movement_m=0.071835604 cross-storey alignment to an existing higher-priority wall line

29. `applied_changes[28]` · `move_wall_line` · F2

   from_m=13.090034965; to_m=12.997404844; movement_m=0.092630121 cross-storey alignment to an existing higher-priority wall line

30. `applied_changes[29]` · `move_wall_line` · F2

   from_m=11.145104895; to_m=11.051038062; movement_m=0.094066833 cross-storey alignment to an existing higher-priority wall line

31. `applied_changes[30]` · `move_wall_line` · F2

   from_m=21.04458042; to_m=20.934256055; movement_m=0.110324364 cross-storey alignment to an existing higher-priority wall line

32. `applied_changes[31]` · `move_wall_line` · F1

   from_m=16.064864865; to_m=15.952121872; movement_m=0.112742993 cross-storey alignment to an existing higher-priority wall line

33. `applied_changes[32]` · `move_wall_line` · F2

   from_m=5.113636364; to_m=4.887543253; movement_m=0.226093111 cross-storey alignment to an existing higher-priority wall line

### eliminated

1. `eliminated[0]` · `merge_duplicate_wall_into_fixed_footprint` · p_corridor_wall / footprint[7]

   from_m=14.118918919; to_m=13.989189189; movement_m=0.12972973; length_m=4.99567474 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

2. `eliminated[1]` · `merge_duplicate_wall_into_fixed_footprint` · p_bot_e / footprint[3]

   from_m=5.881081081; to_m=6.010810811; movement_m=0.12972973; length_m=10.012975779 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

3. `eliminated[2]` · `merge_duplicate_wall_into_fixed_footprint` · mwW / footprint[5]

   from_m=5.113636364; to_m=5.004370629; movement_m=0.109265734; length_m=13.993471164 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

4. `eliminated[3]` · `merge_duplicate_wall_into_fixed_footprint` · corrS / footprint[6]

   from_m=14.124047878; to_m=13.993471164; movement_m=0.130576714; length_m=5.004370629 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

5. `eliminated[4]` · `merge_duplicate_wall_into_fixed_footprint` · bandN / footprint[2]

   from_m=5.854189336; to_m=6.006528836; movement_m=0.152339499; length_m=9.986888112 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

6. `eliminated[5]` · `remove_collapsed_wall_step` · F2

   from_m=5.004370629; to_m=5.004370629; movement_m=0.130576714 the sub-0.30 m connector collapsed to a point while its adjoining wall was aligned

### rejected

无。

## sm25_single

状态 `regularized`；原 JSON `regularization_replay[5].items`。
已应用 24；删除/合并记录 2；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 3 条；消除偏差的唯一外皮线对 3 对。外皮对齐不重复计入删除/合并记录。

楼层 `1F` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 1，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 1。

楼层 `2F` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 1，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 1。

### applied_changes

1. `applied_changes[0]` · `merge_duplicate_wall_into_fixed_footprint` · PcorrS / footprint[6]

   from_m=14.118918919; to_m=13.989189189; movement_m=0.12972973; length_m=5.0 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

2. `applied_changes[1]` · `move_wall_line` · 1F

   from_m=5.881081081; to_m=5.751351351; movement_m=0.12972973 align touching collinear wall ends to an existing line

3. `applied_changes[2]` · `move_wall_line` · 1F

   from_m=14.118918919; to_m=13.989189189; movement_m=0.12972973 align touching collinear wall ends to an existing line

4. `applied_changes[3]` · `merge_duplicate_wall_into_fixed_footprint` · QcorrS / footprint[6]

   from_m=14.13304253; to_m=14.002181025; movement_m=0.130861505; length_m=4.97382199 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

5. `applied_changes[4]` · `move_wall_line` · 2F

   from_m=14.13304253; to_m=14.002181025; movement_m=0.130861505 align touching collinear wall ends to an existing line

6. `applied_changes[5]` · `move_wall_line` · 2F

   from_m=14.002181025; to_m=13.989189189; movement_m=0.012991836 move a connected collinear wall-chain segment with its cross-storey footprint edge

7. `applied_changes[6]` · `move_footprint_edge` · 2F/footprint[6] / 1F/footprint[6]

   from_m=14.002181025; to_m=13.989189189; movement_m=0.012991836 align one overlapping cross-storey footprint edge to the policy-selected existing edge

8. `applied_changes[7]` · `move_footprint_edge` · 2F/footprint[1] / 1F/footprint[1]

   from_m=14.986910995; to_m=15.0; movement_m=0.013089005 align one overlapping cross-storey footprint edge to the policy-selected existing edge

9. `applied_changes[8]` · `move_footprint_edge` · 2F/footprint[5] / 1F/footprint[5]

   from_m=4.97382199; to_m=5.0; movement_m=0.02617801 align one overlapping cross-storey footprint edge to the policy-selected existing edge

10. `applied_changes[9]` · `move_wall_line` · 1F

   from_m=10.010810811; to_m=10.010905125; movement_m=9.4315e-05 cross-storey alignment to an existing higher-priority wall line

11. `applied_changes[10]` · `move_wall_line` · 1F

   from_m=12.0; to_m=11.99563795; movement_m=0.00436205 cross-storey alignment to an existing higher-priority wall line

12. `applied_changes[11]` · `move_wall_line` · 1F

   from_m=8.0; to_m=8.00436205; movement_m=0.00436205 cross-storey alignment to an existing higher-priority wall line

13. `applied_changes[12]` · `move_wall_line` · 2F

   from_m=12.979930192; to_m=12.987012987; movement_m=0.007082795 cross-storey alignment to an existing higher-priority wall line

14. `applied_changes[13]` · `move_wall_line` · 2F

   from_m=5.888767721; to_m=5.881081081; movement_m=0.00768664 cross-storey alignment to an existing higher-priority wall line

15. `applied_changes[14]` · `move_wall_line` · 1F

   from_m=14.010810811; to_m=14.002181025; movement_m=0.008629786 cross-storey alignment to an existing higher-priority wall line

16. `applied_changes[15]` · `move_wall_line` · 1F

   from_m=3.956756757; to_m=3.947655398; movement_m=0.009101359 cross-storey alignment to an existing higher-priority wall line

17. `applied_changes[16]` · `move_wall_line` · 2F

   from_m=20.920593368; to_m=20.930735931; movement_m=0.010142562 cross-storey alignment to an existing higher-priority wall line

18. `applied_changes[17]` · `move_wall_line` · 2F

   from_m=8.922338569; to_m=8.939393939; movement_m=0.01705537 cross-storey alignment to an existing higher-priority wall line

19. `applied_changes[18]` · `move_wall_line` · 2F

   from_m=11.038394415; to_m=11.060606061; movement_m=0.022211645 cross-storey alignment to an existing higher-priority wall line

20. `applied_changes[19]` · `move_wall_line` · 2F

   from_m=4.97382199; to_m=5.0; movement_m=0.02617801 cross-storey alignment to an existing higher-priority wall line

21. `applied_changes[20]` · `move_wall_line` · 1F

   from_m=16.021621622; to_m=16.052344602; movement_m=0.03072298 cross-storey alignment to an existing higher-priority wall line

22. `applied_changes[21]` · `move_wall_line` · 1F

   from_m=16.021621622; to_m=16.052344602; movement_m=0.03072298 cross-storey alignment to an existing higher-priority wall line

23. `applied_changes[22]` · `move_wall_line` · 2F

   from_m=9.904013962; to_m=9.935064935; movement_m=0.031050973 cross-storey alignment to an existing higher-priority wall line

24. `applied_changes[23]` · `move_wall_line` · 2F

   from_m=5.888767721; to_m=5.751351351; movement_m=0.137416369 cross-storey alignment to an existing higher-priority wall line

### eliminated

1. `eliminated[0]` · `merge_duplicate_wall_into_fixed_footprint` · PcorrS / footprint[6]

   from_m=14.118918919; to_m=13.989189189; movement_m=0.12972973; length_m=5.0 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

2. `eliminated[1]` · `merge_duplicate_wall_into_fixed_footprint` · QcorrS / footprint[6]

   from_m=14.13304253; to_m=14.002181025; movement_m=0.130861505; length_m=4.97382199 outer footprint stayed fixed; only the duplicate sub-0.30 m overlap was removed and its contents were audited

### rejected

无。

## 2026-10-01_opus_dev_sm21

状态 `regularized`；原 JSON `regularization_replay[6].items`。
已应用 0；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
已应用 0；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
已应用 5；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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

状态 `regularized`；原 JSON `regularization_replay[9].items`。
已应用 30；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 8 条；消除偏差的唯一外皮线对 8 对。外皮对齐不重复计入删除/合并记录。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

1. `applied_changes[0]` · `move_wall_line` · F2

   from_m=5.999563509; to_m=5.999134012; movement_m=0.000429498 move a connected collinear wall-chain segment with its cross-storey footprint edge

2. `applied_changes[1]` · `move_footprint_edge` · F2/footprint[2] / F1/footprint[2]

   from_m=5.999563509; to_m=5.999134012; movement_m=0.000429498 align one overlapping cross-storey footprint edge to the policy-selected existing edge

3. `applied_changes[2]` · `move_footprint_edge` · F2/footprint[4] / F1/footprint[4]

   from_m=-0.002182453; to_m=-0.008659883; movement_m=0.00647743 align one overlapping cross-storey footprint edge to the policy-selected existing edge

4. `applied_changes[3]` · `move_footprint_edge` · F2/footprint[0] / F1/footprint[0]

   from_m=19.989087735; to_m=19.995670058; movement_m=0.006582324 align one overlapping cross-storey footprint edge to the policy-selected existing edge

5. `applied_changes[4]` · `move_footprint_edge` · F2/footprint[5] / F1/footprint[5]

   from_m=4.994334525; to_m=5.003456619; movement_m=0.009122095 align one overlapping cross-storey footprint edge to the policy-selected existing edge

6. `applied_changes[5]` · `move_footprint_edge` · F2/footprint[1] / F1/footprint[1]

   from_m=14.996077748; to_m=15.006049084; movement_m=0.009971336 align one overlapping cross-storey footprint edge to the policy-selected existing edge

7. `applied_changes[6]` · `move_wall_line` · F2

   from_m=14.096464426; to_m=14.106949556; movement_m=0.01048513 move a connected collinear wall-chain segment with its cross-storey footprint edge

8. `applied_changes[7]` · `move_footprint_edge` · F2/footprint[6] / F1/footprint[6]

   from_m=14.096464426; to_m=14.106949556; movement_m=0.01048513 align one overlapping cross-storey footprint edge to the policy-selected existing edge

9. `applied_changes[8]` · `move_footprint_edge` · F2/footprint[3] / F1/footprint[3]

   from_m=24.997820971; to_m=25.008641549; movement_m=0.010820578 align one overlapping cross-storey footprint edge to the policy-selected existing edge

10. `applied_changes[9]` · `move_footprint_edge` · F2/footprint[7] / F1/footprint[7]

   from_m=0.004358058; to_m=-0.008641549; movement_m=0.012999607 align one overlapping cross-storey footprint edge to the policy-selected existing edge

11. `applied_changes[10]` · `move_wall_line` · F1

   from_m=9.993505088; to_m=9.993452641; movement_m=5.2447e-05 cross-storey alignment to an existing higher-priority wall line

12. `applied_changes[11]` · `move_wall_line` · F2

   from_m=11.030244923; to_m=11.030936744; movement_m=0.000691821 cross-storey alignment to an existing higher-priority wall line

13. `applied_changes[12]` · `move_wall_line` · F1

   from_m=9.000172831; to_m=9.00374793; movement_m=0.003575099 cross-storey alignment to an existing higher-priority wall line

14. `applied_changes[13]` · `move_wall_line` · F1

   from_m=9.000172831; to_m=9.00374793; movement_m=0.003575099 align touching collinear wall ends to an existing line

15. `applied_changes[14]` · `move_wall_line` · F2

   from_m=3.991706678; to_m=3.996536047; movement_m=0.004829368 cross-storey alignment to an existing higher-priority wall line

16. `applied_changes[15]` · `move_wall_line` · F2

   from_m=3.991706678; to_m=3.996536047; movement_m=0.004829368 align touching collinear wall ends to an existing line

17. `applied_changes[16]` · `move_wall_line` · F2

   from_m=3.991706678; to_m=3.996536047; movement_m=0.004829368 align touching collinear wall ends to an existing line

18. `applied_changes[17]` · `move_wall_line` · F2

   from_m=3.991706678; to_m=3.996536047; movement_m=0.004829368 align touching collinear wall ends to an existing line

19. `applied_changes[18]` · `move_wall_line` · F2

   from_m=3.991706678; to_m=3.996536047; movement_m=0.004829368 align touching collinear wall ends to an existing line

20. `applied_changes[19]` · `move_wall_line` · F2

   from_m=12.001309472; to_m=12.006927906; movement_m=0.005618435 cross-storey alignment to an existing higher-priority wall line

21. `applied_changes[20]` · `move_wall_line` · F2

   from_m=8.00742034; to_m=8.001731977; movement_m=0.005688364 cross-storey alignment to an existing higher-priority wall line

22. `applied_changes[21]` · `move_wall_line` · F2

   from_m=4.994334525; to_m=5.003456619; movement_m=0.009122095 cross-storey alignment to an existing higher-priority wall line

23. `applied_changes[22]` · `move_wall_line` · F2

   from_m=5.803142732; to_m=5.793461788; movement_m=0.009680944 cross-storey alignment to an existing higher-priority wall line

24. `applied_changes[23]` · `move_wall_line` · F2

   from_m=14.009166303; to_m=13.998701018; movement_m=0.010465285 cross-storey alignment to an existing higher-priority wall line

25. `applied_changes[24]` · `move_wall_line` · F2

   from_m=9.962520701; to_m=9.929139302; movement_m=0.033381399 cross-storey alignment to an existing higher-priority wall line

26. `applied_changes[25]` · `move_wall_line` · F1

   from_m=20.990321466; to_m=20.944826985; movement_m=0.045494481 cross-storey alignment to an existing higher-priority wall line

27. `applied_changes[26]` · `move_wall_line` · F2

   from_m=16.038847665; to_m=15.990474129; movement_m=0.048373536 cross-storey alignment to an existing higher-priority wall line

28. `applied_changes[27]` · `move_wall_line` · F2

   from_m=16.038847665; to_m=15.990474129; movement_m=0.048373536 align touching collinear wall ends to an existing line

29. `applied_changes[28]` · `move_wall_line` · F2

   from_m=16.038847665; to_m=15.990474129; movement_m=0.048373536 align touching collinear wall ends to an existing line

30. `applied_changes[29]` · `move_wall_line` · F1

   from_m=13.169720014; to_m=12.991371045; movement_m=0.178348969 cross-storey alignment to an existing higher-priority wall line

### eliminated

无。

### rejected

无。

## 2026-09-26_sm25_height_repeat_claude_run54

状态 `regularized`；原 JSON `regularization_replay[10].items`。
已应用 24；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 8 条；消除偏差的唯一外皮线对 8 对。外皮对齐不重复计入删除/合并记录。

楼层 `F1` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

楼层 `F2` 的 A 阶段独立结果：严格编译与源模型保存检查 `True`；墙线合并 0，消除窄条空间 0，删除种子 0，合并重复开口 0，删除退化接头 0。

整楼交付状态 `delivered`；A 阶段独立结果仅作证据、未交付 `False`；实际计入整楼消除 0。

### applied_changes

1. `applied_changes[0]` · `move_footprint_edge` · F2/footprint[0] / F1/footprint[0]

   from_m=19.989088925; to_m=19.99566959; movement_m=0.006580664 align one overlapping cross-storey footprint edge to the policy-selected existing edge

2. `applied_changes[1]` · `move_footprint_edge` · F2/footprint[1] / F1/footprint[1]

   from_m=14.995640802; to_m=14.987035436; movement_m=0.008605366 align one overlapping cross-storey footprint edge to the policy-selected existing edge

3. `applied_changes[2]` · `move_footprint_edge` · F2/footprint[7] / F1/footprint[7]

   from_m=0.0; to_m=-0.008643042; movement_m=0.008643042 align one overlapping cross-storey footprint edge to the policy-selected existing edge

4. `applied_changes[3]` · `move_footprint_edge` · F2/footprint[3] / F1/footprint[3]

   from_m=25.0; to_m=24.991356958; movement_m=0.008643042 align one overlapping cross-storey footprint edge to the policy-selected existing edge

5. `applied_changes[4]` · `move_wall_line` · F2

   from_m=13.987997818; to_m=13.998051315; movement_m=0.010053498 move a connected collinear wall-chain segment with its cross-storey footprint edge

6. `applied_changes[5]` · `move_footprint_edge` · F2/footprint[6] / F1/footprint[6]

   from_m=13.987997818; to_m=13.998051315; movement_m=0.010053498 align one overlapping cross-storey footprint edge to the policy-selected existing edge

7. `applied_changes[6]` · `move_footprint_edge` · F2/footprint[4] / F1/footprint[4]

   from_m=0.0; to_m=-0.010826026; movement_m=0.010826026 align one overlapping cross-storey footprint edge to the policy-selected existing edge

8. `applied_changes[7]` · `move_footprint_edge` · F2/footprint[5] / F1/footprint[5]

   from_m=5.100261552; to_m=4.982713915; movement_m=0.117547637 align one overlapping cross-storey footprint edge to the policy-selected existing edge

9. `applied_changes[8]` · `move_wall_line` · F2

   from_m=5.979268958; to_m=5.856879939; movement_m=0.122389019 move a connected collinear wall-chain segment with its cross-storey footprint edge

10. `applied_changes[9]` · `move_footprint_edge` · F2/footprint[2] / F1/footprint[2]

   from_m=5.979268958; to_m=5.856879939; movement_m=0.122389019 align one overlapping cross-storey footprint edge to the policy-selected existing edge

11. `applied_changes[10]` · `move_wall_line` · F1

   from_m=9.974070873; to_m=9.960767219; movement_m=0.013303654 cross-storey alignment to an existing higher-priority wall line

12. `applied_changes[11]` · `move_wall_line` · F1

   from_m=16.033344159; to_m=16.01745772; movement_m=0.01588644 cross-storey alignment to an existing higher-priority wall line

13. `applied_changes[12]` · `move_wall_line` · F2

   from_m=9.972722313; to_m=9.992421782; movement_m=0.019699469 cross-storey alignment to an existing higher-priority wall line

14. `applied_changes[13]` · `move_wall_line` · F2

   from_m=8.9581517; to_m=8.980121003; movement_m=0.021969303 cross-storey alignment to an existing higher-priority wall line

15. `applied_changes[14]` · `move_wall_line` · F2

   from_m=11.958537916; to_m=11.984410523; movement_m=0.025872607 cross-storey alignment to an existing higher-priority wall line

16. `applied_changes[15]` · `move_wall_line` · F1

   from_m=15.990040056; to_m=16.01745772; movement_m=0.027417663 cross-storey alignment to an existing higher-priority wall line

17. `applied_changes[16]` · `move_wall_line` · F2

   from_m=13.987997818; to_m=13.954747212; movement_m=0.033250605 cross-storey alignment to an existing higher-priority wall line

18. `applied_changes[17]` · `move_wall_line` · F2

   from_m=12.990409765; to_m=12.955920484; movement_m=0.034489281 cross-storey alignment to an existing higher-priority wall line

19. `applied_changes[18]` · `move_wall_line` · F2

   from_m=11.028770706; to_m=10.989628349; movement_m=0.039142357 cross-storey alignment to an existing higher-priority wall line

20. `applied_changes[19]` · `move_wall_line` · F1

   from_m=3.951499405; to_m=3.906164757; movement_m=0.045334647 cross-storey alignment to an existing higher-priority wall line

21. `applied_changes[20]` · `move_wall_line` · F2

   from_m=20.924149956; to_m=20.972342264; movement_m=0.048192308 cross-storey alignment to an existing higher-priority wall line

22. `applied_changes[21]` · `move_wall_line` · F2

   from_m=5.034873583; to_m=4.982713915; movement_m=0.052159668 cross-storey alignment to an existing higher-priority wall line

23. `applied_changes[22]` · `move_wall_line` · F2

   from_m=7.921440262; to_m=8.022085093; movement_m=0.100644831 cross-storey alignment to an existing higher-priority wall line

24. `applied_changes[23]` · `move_wall_line` · F2

   from_m=5.979268958; to_m=5.856879939; movement_m=0.122389019 cross-storey alignment to an existing higher-priority wall line

### eliminated

无。

### rejected

无。

## 2026-09-26_sm24_whole_building_claude_run55

状态 `legacy_geometric_pass_source_save_incompatible`；原 JSON `regularization_replay[11].items`。
已应用 0；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
已应用 0；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
已应用 7；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
已应用 7；删除/合并记录 0；拒绝记录 0；尝试后回滚 0。

其中跨层外轮廓边对齐 0 条；消除偏差的唯一外皮线对 0 对。外皮对齐不重复计入删除/合并记录。

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
