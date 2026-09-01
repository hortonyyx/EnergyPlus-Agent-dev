# 测量档 · F-156 v2 施工席的四支探针（⛔ 线索非证据以外的都是命令直出）

- **日期**：2026-09-01 · **产出方**：Claude 家族施工席（F-156 v2）· **树**：`f9bac1e`，`src/` 零改动
- **用途**：为 **F-156 v2 停报**提供机械可复现的读数；⛔ 这些脚本是**探索档探针**，
  不是产物、不进成绩、不许整段搬进 `src/`。
- **执行档**：[../../reviews/execution/2026-09-01b_f156v2_execution.md](../../reviews/execution/2026-09-01b_f156v2_execution.md)

| 脚本 | 回答的问题 |
|---|---|
| `probe_1_segment_owners_and_endcaps.py` | 两个走廊腔的每一段：`_boundary_owners` 有几个？无主段的**端头归属候选**有几个？ |
| `probe_2_intersection_ring_vs_answer.py` | 求交环（clear-span）逐腔：合并后几条支撑线、几条有面、几条只有端头；与所配答案 zone 的**边数**与**对称差** |
| `probe_3_projected_ring_symdiff.py` | 把事实环**按答案的基准投影后**再与答案 zone 比：对称差是多少 |
| `probe_4_where_the_residual_lives.py` | 投影后仍然对不上的那部分**长在哪里**（逐块面积 + 包围盒） |

跑法（任一）：`python AI_agent/logs/experiments/2026-09-01b_f156v2_measurements/<脚本>`
