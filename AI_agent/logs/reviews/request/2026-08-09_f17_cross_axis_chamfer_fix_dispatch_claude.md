# 派工单 · F-17：envelope 跨轴组件把直角切成 45° 斜边

- **日期**：2026-08-09
- **席位**：Claude 侧 Sonnet（单席，用户 08-09 拍板）
- **性质**：内核 bug 修复 + 分类修法 + 锁。**不碰任何 prompt、不碰下游节点。**
- **基点**：`e4c22f8`（分支 `6.15_ValidationArchM0toM4`）。全仓基线 **2323 passed / 10 xfailed / 0 failed**。
- **调查全档（必读）**：[`logs/experiments/2026-08-09_f17_envelope_cross_axis_chamfer/README.md`](../../experiments/2026-08-09_f17_envelope_cross_axis_chamfer/README.md)

---

## 0. ⛔ 第一步：防假验证自检（动手前先做，别跳）

本项目吃过大亏：**验收路径根本不经过被改的代码**（冻结产物 + 跳段入口 = 假验证温床）。
所以**先回答这三问，写进你的执行记录**：

1. 我要改的代码是 `_apply_components`。**我的验收路径真的会执行到它吗？**
   （提示：它只在 `schema_version == "3"` **且** envelope 产生 ≥1 个 intent 时才被调用；
   `--intake-from` / `--reading-from` 之类跳段入口会绕开整个 1_correction。）
2. 我的锁如果**把修法整个还原**，会不会转红？（不会 ⇒ 那不是锁。）
3. 我断言的是**手算出来的具体坐标**，还是「没抛异常 / 数量变了」？（后者不算数。）

---

## 1. 背景（一句话）

F-16 修好之后，模型的 draw 第一次通过 parse 层全部门，链路**第一次真正走到 v3 envelope
transaction**，当场炸在确定性核：

```
ValueError: cell RM1F_01: polygon edge 3 is not orthogonal
  cell_geometry.py:172 ← validate_cell_polygon ← envelope_transform.py:424 _apply_components
```

**这是内核 bug，不是模型错。** 模型输出的 14 个 cell **全部 `polygon: None`**（用矩形 `x`/`y` 边界），
`RM1F_01` 是标准轴对齐矩形 ⇒ **重抽多少次都没用。**

---

## 2. 根因（已实测坐实，⛔ 不是推断）

**`_apply_components`（`src/agent/correction/envelope_transform.py:392-427`）顺序【就地】改写同一份几何，
但每个组件的 `intervals` 都是在【变换前】的坐标系里算好的。**

当第二个组件与第一个**正交**时：

1. 第一个（x）组件把公共角点 `(0.12, 0.12)` 挪到 `(0.0, 0.12)`；
2. 第二个（y）组件的区间是 x ∈ [0.12, 14.88]，而该点的 x 已是 **0.0 < 0.12 − tol**
   ⇒ `_on_component` 判「不在组件上」⇒ **漏移**；
3. 同时 `_materialize_axis_splits` 在那条已被拉长的边上插入区间端点 `0.12`
   （**现在才严格落在边内部**）⇒ 新点 `(0.12, 0.12)` 被正确移到 `(0.12, 0.0)`；
4. ⇒ **一个直角裂成两点，连线成 45° 斜边**（dx = dy = 0.12）。

### 关键实测（可复跑，`tools/` 下三个脚本）

| 事实 | 证据 |
|---|---|
| **单个组件永远不产生斜边**；同轴两个组件也不 | 组合矩阵 15 格全跑 |
| **跨轴 ⇔ 斜边**，数量 = 4 × (x 组件数 × y 组件数) | 同上，零例外 |
| 中招判据 = **cell 碰不碰 footprint 的角** | F1：碰角的 4 个全中，不碰角的 3 个全正常 |
| **干净原始几何上四个组件的插点数都是 0** | ⇒ **插点本身就是顺序污染的产物** |

> ⛔ **立项时登记的推断已被推翻**（「插中间点后只部分移动 ⇒ 共线三点中间被移出斜边」）。
> 别照那个方向修。

### ⭐ legacy 路径本来是对的（这条决定了修法形状）

`tests/test_deterministic_core.py::test_authoritative_envelope_accepts_bounds_and_moves_only_perimeter_edges`
用的**正是**真实数字 `[0.12,14.88]×[0.12,7.88]`，**同时声明 x 与 y 两轴**，
断言 `cells["A"].x == [0.0, 5.0]` 且 `.y == [0.0, 8.0]` —— **跨轴角点两个方向都移对了**。

| | 表示 | 「改哪个坐标」怎么定 | 跨轴独立性 |
|---|---|---|---|
| legacy（`_apply_legacy_envelope_reconcile`） | cell 的 **bbox** | **索引** `values[edge_idx] = new_value` | ✅ 表示本身送的 |
| v3（`_apply_components`） | cell 的**顶点环** | **坐标匹配谓词** `_on_component(...)` | ❌ 谓词在第一次移动后失效 |

**⇒ 修法 = 在 v3 里把这个「跨轴独立性」重新拿回来。**

---

## 3. 修法（三阶段；**已由 orchestrator 用探针在两格上验证通过**）

把「边移边判」拆成三相：

- **相 1 · materialize**：对每个组件依次插点，**此阶段不移动任何点**
  ⇒ 所有坐标仍是原始坐标。
- **相 2 · 定位 + 移动**：每个顶点对**全部**组件求 `_on_component`（坐标仍是原始的），
  命中哪个就改哪个分量 —— **一个角点可同时被 x 与 y 组件命中，两个分量一起改**。
- **相 3 · 规范化**：沿用现有 `_canonical_open_ccw` / rect 回落 / 校验。

**参考实现在 [`tools/f17_fixprobe.py`](../../experiments/2026-08-09_f17_envelope_cross_axis_chamfer/tools/f17_fixprobe.py)
的 `apply_components_fixed()`** —— ⛔ **它是参考不是成品**：请按仓库风格实现进
`_apply_components`，并自行复核审计字典与边界条件。

### 探针实测结果

| 格 | 场景 | 现行实现 | 三阶段修法 |
|---|---|---|---|
| **A** | 真实 sm21 产物（矩形 footprint，四条边全要动） | ⛔ ValueError | ✅ 全正交；footprint = `(0,0),(15,0),(15,8),(0,8)`；14 个 cell 全轴对齐 |
| **B** | **L 形 footprint + 跨轴组件**（materialize 真的要用） | ⛔ ValueError | ✅ 全正交，L 形拐角保持 |

几何结果也是对的：14.76 × 7.76 → **15.0 × 8.0**。

### ⭐ 副作用（正向，但要留意）

修好之后**矩形 cell 不再被误升级成 polygon**（探针实测 `promoted_rect_cells_to_polygon = []`；
现行实现下它们全被切角后升级了）。**已查：全仓没有任何测试断言在 `moved` 审计字段上**，
所以这不该造成回归 —— 但如果你撞到相关的红，**先停下上报**，别改断言迁就。

---

## 4. ⛔ 三条硬约束（违反其一即整批打回）

1. **⛔ 不许删 / 绕过 `_materialize_axis_splits`。**
   探针里它在格 A 零插点，**只因为那个 case 是矩形**；**格 B（L 形）它是必需的**
   —— T-junction 与图闭包（`_floor_axis_edges`）就是为它设的。
   修法只该改「**定位用哪套坐标**」，不该动「插不插点」。
   ⇒ 这正是本项目「删『看起来多余』的规范化之前，先找出它在为哪份契约服务」那条纪律的形状。
2. **⛔ 不许给正交校验加豁免 / 放宽容差。** 斜边是真的斜边，不是编码差异。
   （对照：F-13 那次「循环旋转」是编码差异，本条不是。）
3. **⛔ 不许动 `_BASE_SIGN` / 方向约定 / 任何 prompt。** 与本条无关。

---

## 5. 第二条出口：分类修法（**必须一起做**）

`_apply_components:422-424` 那个校验循环在 `run_envelope_hard_gates` **之前**，且**不在任何 try 里**：

| 情形 | 现状 | 后果 |
|---|---|---|
| cell 碰角 ⇒ **cell** 出斜边 | 裸 `ValueError` | **炸穿整个 flow**，`attempts/` 零归档（同 F-15 第二堵墙） |
| cell 都不碰角 ⇒ 只有 **footprint** 出斜边 | 走 `correction.envelope_ring_valid=False` | 结构化拒绝、**归档重抽** —— 但重抽永远没用，**烧钱到 quarantine，且把内核 bug 记在模型账上** |

**要做的**：让这个校验失败**走结构化拒绝**（`EnvelopeTransformRejected` + 合适的 `check_id`），
不要裸 `ValueError` 炸穿 flow。

**⛔ 但分类修法【不能单独交付】** —— 只做分类不修根因，等于把内核 bug 永久记在模型账上、
让它无限重抽烧钱。**两条一起交。**

---

## 6. 必须交付的锁（形态写死，⛔ 数量不限但形态不许缺）

1. **跨轴组件锁（核心）**：夹具 footprint 的 **lo 侧必须 ≠ 0**。
   ⛔ **这一条是本批的命门** —— 全仓 2323 绿之所以漏掉这个 bug，就是因为走 v3 变换的夹具
   footprint 环**全部以 `[0,0]` 起** ⇒ lo 侧不产生 intent ⇒ **结构上凑不出正交组件对**。
   夹具用 `[0.12, …]` 这类偏移起点。
2. **断言等于手算值**：如 footprint == `[(0,0),(15,0),(15,8),(0,8)]`、
   某个角 cell == `[(0,0),(5,0),(5,3),(0,3)]`。
   ⛔ 不许只断言「没抛异常」「cell 数没变」「结果非 None」。
3. **L 形 + 跨轴锁**（格 B）：证明 materialize 仍在起作用、拐角没被抹平。
4. **分类锁**：证明该失败**走归档重抽路径**而不是裸 `ValueError` 炸穿。
   ⛔ 注意本项目有前科：这类锁若用 monkeypatch 强行造 category，就只锁住了机制、没锁住接线。
5. **neuter 自验**（做完写进执行记录）：把定位改回「边移边判」（即复原缺陷本体），
   **上面这些锁必须转红**；恢复后必须全绿。
   ⛔ **neuter 要覆盖「接线」不只「机制」** —— 问自己：
   **「把调用点改回缺陷形态，锁红不红？」**

---

## 7. 验收条件

- [ ] `tools/f17_repro.py` **不再抛 ValueError**（用真实产物跑，官方入口）。
- [ ] `tools/f17_matrix.py` 的 15 格组合**全部 0 斜边**。
- [ ] 全仓 **≥ 2323 passed / 10 xfailed / 0 failed**，零回归。
      **⛔ 跑测用 `-n 8`，不要 `-n auto`**（16 worker 实测会在 ~98% 处静默 OOM 中断，
      外观与「还在跑」难分）；**以汇总行 + 退出码为准，⛔ 不看进度条**。
- [ ] neuter 自验做过且如实记录（红了哪几条、零连带、恢复后全绿）。
- [ ] 执行记录落 `AI_agent/logs/reviews/execution/2026-08-09_f17_cross_axis_fix_claude.md`。

**⛔ 不要求你跑真链路**（要烧 LLM 钱）。真链路验收由 orchestrator 另行决定。

---

## 8. 文件白名单

**允许改**：
- `src/agent/correction/envelope_transform.py`（主要是 `_apply_components`，必要时相邻私有函数）
- `tests/test_c2_b2b_envelope_transform.py` 或**新建**一个 `tests/test_f17_cross_axis_envelope.py`
- `AI_agent/logs/reviews/execution/2026-08-09_f17_cross_axis_fix_claude.md`（你的执行记录）

**⛔ 不许改**：任何 prompt · `src/agent/nodes/**` · `_BASE_SIGN` · `cell_geometry.py` 的正交判据 ·
`AI_agent/CLAUDE.md` / `plan.md`（收工由 orchestrator 统一写）。

---

## 9. ⭐ 合法退出口（请务必用）

**派工方（orchestrator）的历史错误率是 12/12** —— 每一次施工席「停下上报」，
最后查明都是**我的题出错了**，不是施工能力问题。所以：

**如果你发现下列任何一种情况，⛔ 请立刻停下来上报，不要硬凑：**

- 验收条件互相冲突，或某条根本不可达；
- 我给的根因/修法与你实测到的不符（**以你的实测为准**）；
- 某把锁「硬补必得假锁」（例如要锁的行为在当前代码里根本不存在差异）；
- 我在上面写的某个「共 N 处 / 一律 / 全部」与你逐处核对的结果对不上
  （**这类批量措辞我犯过两次，都是只看名字形状没看那一行的值**）；
- 修法在 L 形 / 多层 / 其它形态上退化，而我没给出处理方式。

**如实上报比照做有价值得多。** 上报时请附：你实测到了什么、为什么与派工单冲突。
