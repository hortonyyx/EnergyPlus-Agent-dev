# F-156 v3 · sm25 facts 三件套重做脚本

- **日期**：2026-09-01 · **产出方**：Claude 家族施工席（F-156 v3）
- **执行档**：[../../reviews/execution/2026-09-01c_f156v3_execution.md](../../reviews/execution/2026-09-01c_f156v3_execution.md)

`rebuild_sm25_facts_staging.py` —— 重新生成
`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/` 三件套。

**为什么必须重做**：`boundary_edges` / `boundary_ring_losses` 是**派生值且住在
`as_measured`/`as_signed` 内部**，被 `content_sha256` 覆盖 ⇒ 改推导必然改哈希。

**与 ②-1b 那支的唯一差别**：那支调 `boundary_audit.assert_consistent()`（不完全干净就不写）。
F-156 之后 sm25 的对账**按设计不完全干净**：两个走廊腔欠着 F-157 的
`outer_skin↔wall_axis` 基准切换。本脚本把闸写成**规则**——
`mismatches` 非空拒写；任何 structural 失败，只要它点名的那个腔在同一次跑里
**没有被投影环判据点名**，就拒写。⛔ 不是 cavity id 名单。

⚠️ **②-1b 那支现在会以 `BoundaryBasisMismatchError` 退出**（它不在本单写面，未改）。
