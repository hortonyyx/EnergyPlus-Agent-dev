# 施工单 · F-11：下游死循环 + foundations 阶段跑终态校验

> **「施工单」**（解法已由调查定案，orchestrator 已独立复核全部承重断言）。
> 调查全档：[`execution/2026-08-06_f11_downstream_loop_investigation_glm.md`](../execution/2026-08-06_f11_downstream_loop_investigation_glm.md)（你自己写的）。

- **日期**：2026-08-06 · **席位**：GLM-5.2，主工作树 · **基点**：`6.15_ValidationArchM0toM4` @ `8dd4167`

## 0. 开工自检（不对就停）

```bash
git log --oneline -1     # 期望 8dd4167
git status --short       # 期望：5 个未跟踪项（4 个 case_tests 目录 + 你的 F-11 调查日志）
pwd                      # 期望 /workspaces/EnergyPlus-Agent-dev
```
⛔ 绝不 `git add -A`。

## 1. ⛔⛔ 安全边界（先读）

**下游链路目前会无限循环并持续调用 DeepSeek（按量计费真金白银）。**
- ⛔ 任何触发下游图的命令**必须带 `timeout`**（≤300s）
- ⛔ **不许**用管道接 `| tail`（会缓冲掉全部进度日志）
- ✅ 你上一单自制的「不进 LangGraph、直调节点」探针**继续用**，能不烧钱就不烧

## 2. 承重事实（orchestrator 已独立复核）

| # | 事实 |
|---|---|
| 1 | `src/agent/nodes/cross_ref.py:33` `cross_ref_foundations_node` = `validate_references() + _output_coordinate_errors(state)` |
| 2 | `src/agent/nodes/cross_ref.py:40` `cross_ref_complete_node` = **逐字相同的一行** |
| 3 | `validate_node` 也调 `_output_coordinate_errors`（`src/agent/nodes/validate.py`）|
| 4 | ⭐ `cross_ref_foundations_node` 的 **docstring 自己写着** *"Most checks are moot at this stage (**no constructions, surfaces, HVAC yet**)"* —— **作者知道这阶段没有面，后加的 E4 校验没顾上** |
| 5 | drift 检查 = `src/validator/output_coordinates.py:794 _vertex_drift_issues`，逐条拿 `snapshot.records` 去 `config.surfaces` 里找，找不到即 `:802` "missing from ConfigState" |
| 6 | 触发条件 = **契约来源类型**：`accepted_correction` 强制带 snapshot（今晚 5_intakeoutput 首次产出）⇒ 触发；`legacy standalone` 无 snapshot（probe B）⇒ 不触发 |

## 3. 施工内容（两件，**必须成对**）

### A · 让 foundations 阶段不再跑「依赖终态产物」的校验
**要求的行为**（机制你自己定）：
- `cross_ref_foundations_node` **不得**因「snapshot 里的面/窗在 ConfigState 里不存在」而报错 —— 那一刻它们本就不该存在；
- **⛔ 契约保证一条不许丢**：`cross_ref_complete_node` 与 `validate_node` **必须仍执行全量** output-coordinate 校验（含 vertex-drift）；
- 你可以选「foundations 完全不跑」或「foundations 只跑阶段适用的子集」——**自己判断哪个更对，并在日志里说明理由**。

### B · ⭐ 可观测性 + 循环熔断（与 A 成对，⛔ 不许只做 A）
1. **拒绝必须留痕**：`runner.py:145 auto_approval` 判定 `approved: False` 时**必须打日志并输出错误内容**。
   现状是**全程零输出** —— orchestrator 因此瞎跑了 1 小时 40 分、约 400 圈。
2. **循环必须能终止**：即使将来出现别的持久错误，`validate → intake → … → validate` **不得无限转**。
   机制你定（如：连续 N 轮 `validation_errors` 相同即终止 / 不再重置 `retry_count` / 显式熔断计数），
   **但必须是确定性的终止保证，⛔ 不许靠"错误早晚会消失"**。

## 4. 验收（缺一不可）

| # | 条件 |
|---|---|
| **1 ⭐真实产物** | 用今晚的 intake 跑下游，**必须不再死循环**，且 `surface`/`fenestration`/`hvac`/`people`/`lights` **五个 subagent 都执行到**（日志里看得见节点名）。⚠️ **带 `timeout`**。⛔ **不要求它跑到 EP 成功** —— 后面还有没探过的段，跑出别的错是正常的，**如实记录即可** |
| **2 ⭐契约不丢** | 构造一份**真有 drift** 的输入（snapshot 与 ConfigState 真不一致），断言 `cross_ref_complete` / `validate` **仍然报出该 drift**。⛔ 这是防「把门删没了」的锁，断言落在**具体 issue code / check 行**上 |
| **3 熔断** | 构造一个持久错误场景，断言循环**在有限轮内终止**。⛔ 不许断言「不是 None」「跑完了」 |
| **4 拒绝留痕** | 断言 `auto_approval` 拒绝时错误内容进了日志 |
| **5 neuter** | 上述锁**两向 neuter**，且**先 `git diff` 确认改动真的落下去了**再跑 |
| **6 全仓** | `pytest -n auto`（**不加 `-m`**），基线 **2225 绿 / 10 xfail / 0 红**，净增锁零回归。新锁⛔不许依赖 gitignored 文件（F-8）|

## 5. 边界

⛔ 不改 5_intakeoutput 产契约的行为（`accepted_correction` 带 snapshot 是**正确的更强行为**，是它把这条潜伏缺陷照出来的）·
⛔ 不放宽 `_vertex_drift_issues` 本身 · ⛔ 不碰 `case_tests/` 未跟踪目录 · ⛔ 不 push · ✅ 一次性脚本放 `/tmp`

## 6. 交付

代码 + 锁 + 执行日志 `execution/2026-08-06_f11_fix_glm.md`（含验收 1–6 的**实际命令与实际输出**、neuter 的 `git diff` 证据、A 选了哪个机制及理由）。
**自己 commit**（`08.06_f11_foundations_stage_scope_and_loop_breaker`，body 含 ①改动 ②为何此刻 ③影响），**不要 push**。可一并 `git add` 本单与你的调查日志。

## 7. 停下上报（**记功不记过**）

本轮至今 **7 次「停下上报」，7 次都是派工方的题错了**。事实不符 / 验收做不到 / 修法方向有问题 ⇒ **立刻停下上报**。
⛔ 硬凑出一把假锁是本项目最贵的错误。
