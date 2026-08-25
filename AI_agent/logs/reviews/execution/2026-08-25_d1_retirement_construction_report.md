# 施工交件报告 · 双份代码退役（债 D-1）

- **派工单**：[`../request/2026-08-25_d1_duplicate_code_retirement_dispatch.md`](../request/2026-08-25_d1_duplicate_code_retirement_dispatch.md)
- **席位**：**GLM 家族**执行档（用户 08-25：「施工你和 GLM 都可以派」）
- **交件 commit**：**`98e72d6`**（在 worktree `/workspaces/ep_d1_retire` 的 detached HEAD 上，**未合回主线、未 push**）
- **复核**：⭐ **GPT 家族**（用户 08-25：「审走 GPT」）
- ⛔ 席位自述按 §5#8 **一律以 `git diff` 为准**；orchestrator 的机械核对单列文末。

## ② 选了哪条：**B 的精确化 —— identity 转发壳**

每件 ~25 行：自举仓库根 → import src 权威件 → **`globals().update(vars(_impl))` 全命名空间搬入（含私有名，比 `import *` 强）** → `__main__` CLI 逐字保留、只把 `main` 换成委托 src 件。

- ⛔ **不选 A（删原件）**：同链历史脚本（`assemble_reading` / `as_drawn_elev` / `read_plan` / `glm_rework` 的**平铺 import**）会全断。
- ⛔ 不选 C/D：同意派工单的否定理由（C 把风险换成噪声、D 没解决命题）。
- ⭐ **对「过程痕迹要不要能原样跑」的取舍：要。** 理由 ——
  **这批夹具是五轮跨家族审的证据，而可复跑性就是证据的证明力**；
  壳以近乎零成本保全了**三类消费通道**（平铺 import / `spec_from_file_location` / subprocess CLI）。
- B 的已知代价（re-export 语义不等价）逐项消解：私有名全量搬 · `__main__` 逐字保留 ·
  grep 证实无消费者依赖 `__module__` / pickle。

## ③ 机械判据 + 输出

判据 = [`verify_no_logic_duplicate.py`](../experiments/2026-08-25_d1_retirement/verify_no_logic_duplicate.py)：
(a) tools↔src 全量 `.py` 的**函数体规范化 AST 哈希零交集**（相交 = 同一段逻辑两处）·
(b) 壳命名空间每名与 src 件 **`is` 同一对象** · (c) 壳**零顶层 def/class**。
⭐ **`--baseline <commit>` 模式自证分辨力。**

| | 结果 |
|---|---|
| **退役前** `fa8e597` | `8 shared (6 duplicate / 2 exempt)` —— 6 对逐个点名，期望「恰好 6 对」**YES** |
| **退役后**（工作区）| `2 shared (0 duplicate / 2 exempt)` · (c)=0 · (b)=0 ⇒ **VERDICT: PASS** |

## ④ 四个夹具改前/改后各跑一遍

| 夹具 | 改前 | 改后 | 一致性 |
|---|---|---|---|
| `glm_cheats` | 27s exit=0 | 33s exit=0 | honest 100.0/99.2；四种作弊被门点红逐项一致 |
| `glm_probes` | 10.5s exit=0 | exit=0 | `bridge_window` C1=98.2 C5=31/31 一致 |
| `glm_sweeps` | 43s exit=0 | exit=0 | `punch 20%: C1=18.2`（悬崖）· `pos_tol` 平台 100.0 一致 |
| `run_all` | ~5min exit=0 | ~7min exit=0 | **stdout 逐行一致**；11 道门分辨力机器检查全 `ok` |

⭐ **产物对比（171 个 out 文件）**：**167 逐字节相同 + 4 规范化等价 + 0 不等价**。
那 4 个的差异全部来自 `reconstruct_check_v2.py`（**不在 6 件内、未改**）的跨进程键序漂移（`PYTHONHASHSEED`），改前两次跑之间同样漂。

## ⑤⑥ 全量与提交

```
========== 3017 passed, 13 xfailed, 211 warnings in 456.02s (0:07:36) ==========
```
= 基线 `3017 passed, 13 xfailed`，0 failed / 0 errors。
commit `98e72d6`，**+448/−3240**，九文件逐个点名 add，`git show HEAD:<path>` 逐件验证入提交；
⭐ out/ 覆写副产物已 `git checkout` 恢复（**防 worktree 绝对路径烤进 `"source"` 字段污染回并**）。

## ⑦ ⚠️ 与派工单说法不符 —— **四条**（第 27 次上报，仍是派工方题错）

1. ⭐⭐ **「按路径加载只有两处模块名」不完整。** 夹具消费 tools 原件还有**两条派工单未列的通道**：
   **平铺 import**（`glm_cheats.py:48-56` `from as_drawn_v2 import _family_masks`，靠 `sys.path.insert(0, T)`）
   与 **subprocess 按文件路径**（跑 `T/"checks_as_drawn_v2.py"`、`T/"denominator.py"`）。
   ⇒ **派工单候选 A「只改 `_load`」会漏掉这两条**，壳方案三通道全覆盖。
2. **「行数各差 1、docstring 逐字相同」不准**：实际 `plan_ink.py` 与 `reading_grade.py` 与 src 件**逐字节相同**；
   其余 4 对差异全在 **import 区 / `__file__` 推导深度**，函数体逐字相同。
3. **`run_all.py` 已经不吃任何 6 原件**（转正时就改成走 `python -m src.…`，派工单未提）。
4. **判据比派工单多抓到 2 对**：`as_drawn.py` / `as_drawn_elev.py`（v1 血统，无 src 件）各有 1 个 `_chain_zero_px` 与 v2 同体。
   处置 = **显式豁免并点名**（⛔ 非静默 allowlist），豁免边界机械可判（= RETIRED 键集）。
   ⭐ **席位主动请 GPT 审挑战这条边界。**

## ⑧ 走了本单没给的路（席位主动单列）

1. **v1 血统豁免边界**（见 ⑦.4）—— 判据初版直接 FAIL，**逼它显式划界而非放水**。
2. ⭐⭐⭐ **连带修复 `glm_rework.py` —— 第五个夹具，不在派工单点名的四个里。**
   它做**源码文本手术**（读 `tools/reading_grade.py` 的**文本**、断言含 `WIDTH_COEFF` 规则行、替换系数后 `exec`），
   壳化后守卫红。修法 = 与转正先例同款：改读 `src/agent/judge/as_drawn/reading_grade.py`。
   > ⭐ **席位自己总结的教训**：「**四个「点名必跑」全绿不够** —— `run_all` 内部拉起的第五个夹具
   > 以『RESULTS_v2 少一段』的形式**静默失败**，是**对全部产物做规范化对比**才撞出来的。」
3. **补壳 CLI 冒烟**：三个壳的 `__main__` 委托不被四夹具覆盖 ⇒ 各冒烟一次；
   `reading_grade` 壳 CLI 与 `python -m src.…` 直跑产物**逐字节相同**（连旧 kw 接口的报错都逐字一致）。
4. **out/ 覆写副产物不提交**（理由见 ⑥）。

---

## ⭐ orchestrator 的机械核对（⛔ 不是「审」）

| 核了什么 | 结果 |
|---|---|
| `git show --stat 98e72d6` | ✅ **9 文件 / +385 −3177**：7 个 tools 件瘦身（含连带修的 `glm_rework.py`）+ 退役 README + 判据脚本。⛔ 未碰 `src/` `scripts/` `tests/` `AI_agent/` 管理文档 |
| worktree `git status` | ✅ clean |
| ⭐ **判据的红/绿两态**（我自己跑的）| ✅ `--baseline fa8e597` ⇒ **6 对 DUPLICATE 逐个点名 + 期望 YES**；工作区 ⇒ **0 duplicate / (b)=0 / (c)=0 / PASS**。⚠️ 我第一次用 `--baseline HEAD` 得到 0 对 —— **是我参数用错**（worktree 的 HEAD 已是退役后），⛔ 不是判据失效 |
| 全量 | 席位自跑 `3017 passed, 13 xfailed`，与合并后基线一致 |
| ⛔ **未独立验证** | ④ 那 171 个产物的逐字节对比 · ⑧.2 连带修复的正确性 ⇒ **交 GPT 独立复核** |
