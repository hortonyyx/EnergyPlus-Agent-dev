# 派工单：把 reading 工具箱从探索档转正进 `src/`

> **日期** 2026-08-25 · **出单** orchestrator（Claude Opus 5）· **待用户拍板派谁**
> **分支** `08.23_AsDrawnReading` · **提交** `c28f302`（拆管子那次）
> **治理依据** [CLAUDE.md §0.4#3](../../../CLAUDE.md)：`src/` 须**派工 + 换人审**，orchestrator 只能直接改探索档。

---

## 一、为什么是现在

用户 2026-08-25：「我们**先把新架构的管线搭好，合并进主线**再开始迭代 harness」
「**补成工具那步并回主线（非 main 那个主线）再做，因为那个本身就是 harness 迭代了**」。

⇒ **本单只做「转正」，⛔ 不含任何新能力。** 补新工具（单色图适配、平行线带枚举器、图例读取…）
属于 harness 迭代，**并回主线之后另开单**。

---

## 二、⛔ 范围（严格）

### 要搬的

| 从（探索档） | 到 | 是什么 |
|---|---|---|
| `tools/as_drawn_v2.py` 的 **9 个工序函数 + `Ruler` + 薄 `build()`** | `src/agent/reading/as_drawn/` | 量具与编排（编排是**默认那一条路**） |
| `tools/ink_palette.py` | `src/agent/reading/as_drawn/pens.py` | 墨族发现（⛔ 不给任何族起名） |
| `tools/reading_toolbox.py` | `scripts/tool_scripts/reading_toolbox.py` | CLI：`pens` / `ruler` / `faces` / `pairs` / `gaps` / `build` |
| `tools/checks_as_drawn_v2.py` 的 **11 道门** | `src/validator/checks/as_drawn.py` | 出口（不读 gt） |
| `tools/denominator.py` + `tools/reading_grade.py` | `src/agent/judge/as_drawn/` | 判分（读 gt ⇒ **只能 judge 侧**，见 §四） |
| `tools/render_reading_grade.py` | `scripts/tool_scripts/render_reading_grade.py` | grade 图 |

### ⛔ 不要搬的

- `glm_*.py` / `crossreview_mutate_v2.py` / `f88_probe.py` / `glm_cheats.py` —— **作弊夹具与探针**，
  它们要留在实验档当回归矩阵（⛔ 但**必须继续能跑**，见验收 §五#4）。
- `as_drawn.py` / `checks_as_drawn.py` / `reconstruct_check*.py` 等 **v1 时代文件** —— 已被 v2 取代。
- `cfg_*.json` —— per-case 配置，归 case 目录不归 `src/`。

---

## 三、⛔ 施工时必须保持不变的（这是本单的全部风险面）

1. ⭐⭐ **三个 view 的产物逐字节相同。** 这是唯一硬验收，见 §五。
2. **十一道门的状态逐项不变**：sm25 1F/2F 全绿；sm24 三道非绿
   （`pair_hypothesis_reconciles`=degraded · `pair_spacing_explicable_by_callouts`=red ·
   `forward_ledger_structural_ink_claimed`=degraded）——**这三道红/降级是对的**，
   ⛔ 不许在搬运中"顺手修绿"。
3. **判分数字不变**：画对 99.2 / 97.8 / 97.9 · 错切 0 / 1 / 1 · 多画 0.722 / 0.524 / 5.786 ·
   门窗 31/31 · 30/30 · 20/21。
4. ⛔ **不许趁搬运做任何"改进"**：不调阈值、不加分支、不删注释里的实测记录
   （那些数字是判据的来源，删了下一轮就没人知道它为什么这么写）。

---

## 四、⭐ 一条硬约束：判分器碰 gt，接线必须走 judge 侧

`denominator.py` 读 **gt 的 DXF**，`reading_grade.py` 读**分母**。
按 [CLAUDE.md §1.5#4 gt 铁律](../../../CLAUDE.md)：
**评测答案只 gate② judge / 人 可读，gate①/执行器绝不 import。**

⇒ 落位必须是 `src/agent/judge/` 下，且**执行路径（`run_pipeline` / gate① / 11 道门）不得 import 它**。
⭐ **请施工方显式验证这一条**，方式：从 `src/agent/pipeline.py` 出发做一次 import 闭包扫描，
证明闭包里没有 `judge.as_drawn` 与 `judge.gt`。

---

## 五、验收（⛔ 每条都要贴实测输出，不接受"已核对"）

1. ⭐ **产物逐字节**：对三个 view 各跑一次新路径，`cmp -s` 对比
   `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/<view>_v2.json`。
   **三个全过才算数。**
2. **门状态**：贴出三个 view 的 11 道门逐条状态，与 §三#2 逐项对照。
3. **判分数字**：贴出三行 grade 输出，与 §三#3 逐项对照。
4. ⭐ **回归矩阵仍能跑**：实验档的 `tools/run_all.py` 在搬完之后**仍然跑得通**
   （它引用了被搬走的模块 ⇒ 需要改 import 而**不是**改逻辑）。
   ⛔ 这条是防「搬完把作弊夹具矩阵搞死了」——那批夹具是五轮跨家族审的全部产出。
5. **gt 隔离**：§四那次 import 闭包扫描的输出。
6. **全仓测试**：`-n auto` 全量绿（当前基线 2835 绿 + 14 strict xfail，⚠️ 实际数以施工时为准）。
7. ⛔ **不加新锁**（§0.4#4：锁跟契约走不跟脚手架走）。唯一例外：
   §四那条 gt 隔离**建议加一把锁**，因为它是契约级的。

---

## 六、建议的施工席位与审阅

| | 建议 | 理由 |
|---|---|---|
| **施工** | **GLM**（执行档主力） | 纯搬运 + 接线，风险面窄且验收是机械的 |
| **审阅** | **跨家族**（sol / DeepSeek 皆可） | 「谁写谁不批」；本单碰 `src/` ⇒ 施工审恒升一档 |
| **⛔ 不可** | orchestrator 自己施工 | 治理 §0.4#3 |

⚠️ 审阅方请**只看**：本单 + `git diff` + 上面 7 条验收的实测输出。⛔ 不看施工方长篇自述。

---

## 七、已知会绊人的两处

1. **`as_drawn_v2.py` 顶部从 `plan_ink` 导入**（`INK_MIN` / `load_rgb` / `vertical_runs_mask` /
   `witness_ticks` / `fit_chain` / `dump` / `Axis`）。`plan_ink.py` 是 v1 时代的大文件（33 KB），
   ⛔ **本单不重构它**——按原样搬进 `src/agent/reading/as_drawn/_plan_ink.py`，
   下划线前缀标明「内部、待整理」。
2. **`reading_toolbox.py` 用 `sys.path.insert` 导入同目录模块**。进 `src/` 后改成正常包导入，
   ⛔ 但 CLI 的六个子命令名与输出格式**一个字都不许变**（下一轮我要拿它跑 sm20）。
