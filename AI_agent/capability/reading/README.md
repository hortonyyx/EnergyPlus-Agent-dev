# capability/reading/ —— reading 能力提升（子文件夹，2026-08-19 立）

> **为什么单独成夹**（用户 08-19：「建一个子文件夹吧，把 reading 相关的能力提升都整理进去」）：
> reading 是本项目唯一无法用确定性代码替代的一环，相关材料此前散在
> `capability/` 根、`proposals/`、`logs/experiments/` 三处，找一次要翻三个地方。

| 文档 | 放什么 |
|---|---|
| [`good_reading_implementations.md`](good_reading_implementations.md) | ⭐ **总账**：所有真跑出过好 reading 的**实现形式**（模型/树/隔离/指令/返工/工具调用/成本）+ 两条路线的机制与失效模式 + 降本杠杆。**每出一份好 reading 就追加一行，⛔ 不删旧条目** |
| [`prescan_snapshot/`](prescan_snapshot/RESTORE.md) | **撤出但未放弃的代码**：prescan 实现 + 测试 + 恢复步骤（与 `0cfa289` 逐字节相同）。⛔ 撤出 ≠ 废弃；去留归本专项，且**应与 §9.1 的根治修法合并决策** |
| [`improvement_methodology.md`](improvement_methodology.md) | 方法论 + 诊断史 + Phase A/B/C 路线 + 决策记录；**§9 = 专项收件箱**（根治 / Haiku 回归 / 图像分辨率 / sm24 准入门 / 双路线 / prescan） |

## 不在本夹、但相关的

| 文档 | 为什么不搬 |
|---|---|
| [`../recognition_modeling_capability.md`](../recognition_modeling_capability.md) | 识图**与建模**两腿并行，搬进来会把建模那半misfile |
| [`../floorplan_redraw_strategy.md`](../floorplan_redraw_strategy.md) | 两步法/重绘策略，是 reading 的下游支线 |
| [`../../proposals/hard_isolation_direction.md`](../../proposals/hard_isolation_direction.md) | 隔离面自成专项；与本夹的交叉点只有 `run_cv_probe.py` 的 wrapper 形态 |
| [`../../proposals/dimension_basis_and_wall_thickness_direction.md`](../../proposals/dimension_basis_and_wall_thickness_direction.md) | `scale_origin` / 墙厚基准归那边 |

## 纪律

- 本夹放**活文档**（还在演进的方法与决策）；**跑测实况归 `logs/experiments/`，run 产物归 `case_tests/`**。
- 收录一份好 reading 时，**必须写清它的实现形式**——只写分数不写形式的条目不算数。
  本项目正是因为「知道 07-07 是 9/9、不知道它怎么做到的」而空转了六周。
