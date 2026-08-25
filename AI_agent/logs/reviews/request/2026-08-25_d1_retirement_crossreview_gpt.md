# 跨家族复核请求 · 双份代码退役（债 D-1）

- **日期**：2026-08-25　**对方**：⭐ **GPT 家族**（用户 08-25：「审走 GPT」）
- **档位**：工程档 ⇒ **审恒升一档**；⛔ **谁写谁不批**（派工单 orchestrator 出、施工 GLM 家族做）
- **被审 commit**：**`98e72d6`**，在 worktree **`/workspaces/ep_d1_retire`** 的 detached HEAD 上，
  ⛔ **尚未合回主线** —— 审过才合。
- **原始需求**：[`2026-08-25_d1_duplicate_code_retirement_dispatch.md`](2026-08-25_d1_duplicate_code_retirement_dispatch.md)
- **施工报告**：[`../execution/2026-08-25_d1_retirement_construction_report.md`](../execution/2026-08-25_d1_retirement_construction_report.md)

⛔ 只看**原始需求 + `git diff` + 实际输出**；自述与 diff 冲突以 diff 为准。

## 一、⭐ 请重点攻的五条

1. ⭐⭐⭐ **identity 壳的语义等价性真的成立吗？**（**orchestrator 认为这是本单最脆的一点**）
   每个退役件现在是 ~25 行的壳：`globals().update(vars(_impl))` 把 src 件的**整个命名空间**搬进来。
   请攻**它在什么情况下不等价**，至少覆盖：
   - **模块级可变状态**：src 件里若有模块级 `list`/`dict`/缓存，壳与 src 现在**共享同一对象**
     —— 这是等价还是新耦合？某个夹具改了它，会不会串到 `python -m src.…` 的跑法上？
   - **`__file__` / `__name__` 依赖**：壳里的函数其 `__globals__` 指向 **src 件的模块字典**，
     所以 `__file__` 是 src 的路径。有没有消费者依赖「`__file__` 指向 tools/」？
   - **后绑定**：`vars()` 是**快照**。src 件在 import 后动态新增/替换属性时，壳看不到。有没有这种用法？
   - 席位声称「grep 证实无消费者依赖 `__module__`/pickle」—— **请独立复核这句**。
2. ⭐⭐ **判据本身有没有洞？**（`verify_no_logic_duplicate.py`）
   它用**函数体规范化 AST 哈希**求 tools↔src 交集。请攻：
   **改一个局部变量名 / 调整语句顺序 / 拆一个辅助函数**，哈希就不同 ⇒ **同一段逻辑仍可能两处而判据全绿**。
   ⇒ 这道判据是「防止**未来**漂移」的门，还是只是「证明**这一次**退役干净」的一次性检查？**请说清楚。**
3. ⭐ **v1 血统豁免边界**（席位主动请求被挑战）：`as_drawn.py` / `as_drawn_elev.py` 各有 1 个
   `_chain_zero_px` 与 v2 同体，被**显式豁免并点名**（非静默 allowlist），理由是「v1 是历史快照/演进前身，
   无现行链路以其为源」。**这条边界站得住吗？** 若站不住，是该一并退役还是该记为新债？
4. **第五个夹具的连带修复是否正确**：`glm_rework.py` 做**源码文本手术**
   （读文本 → 断言含 `WIDTH_COEFF` 规则行 → 替换系数 → `exec`）。壳化后它改读 src 件。
   ⭐ 请验证：**那个守卫（断言规则行存在）在 src 件上仍然是有效的守卫**，
   而不是碰巧也能匹配上、实际已经守不住原来那件事。
5. **「证据仍可复跑」这条验收有没有被真正满足**：席位跑了 4 个点名夹具 + run_all 内的第 5 个，
   并对 **171 个产物**做规范化对比（167 逐字节 + 4 等价 + 0 不等价）。
   ⭐ **orchestrator 没有独立验证这 171 个对比** —— **请你抽验若干**。

## 二、验收判据

1. ⭐ **判据的红/绿两态请自己复跑**：
   `python AI_agent/logs/experiments/2026-08-25_d1_retirement/verify_no_logic_duplicate.py --baseline fa8e597`
   （应报**恰好 6 对 DUPLICATE**）与不带参数（应 **PASS**）。
   ⚠️ 提醒：`--baseline HEAD` 在这棵 worktree 上会指向**退役后**的树（orchestrator 已在此踩过一次）。
2. **全量绿**：在 **worktree 里**跑 `python -m pytest -n auto` ⇒ 0 failed / 0 errors；基线 `3017 passed, 13 xfailed`。
   ⭐ 请自己跑，⛔ 不要只信席位粘的汇总行。
3. **范围**：diff 应只含实验目录的 7 个 tools 件 + 退役 README + 判据脚本。
   ⛔ 碰了 `src/` / `scripts/` / `tests/` / venv ⇒ REJECT。

## 三、⚠️ 必答

**跨家族「停下上报」累计 26 次全是派工方（orchestrator）题错；本单席位又上报了 4 条**（见施工报告 ⑦），
其中最要紧的一条是「派工单说按路径加载只有两处模块名」**不完整** —— 实际还有平铺 import 与 subprocess 两条通道，
**若按我给的候选 A 只改 `_load` 会漏掉它们**。**这 4 条你认同吗？还有第 5 条吗？**

⭐ 另请评估席位自己总结的那条教训是否成立并值得固化：

> 「**四个『点名必跑』全绿不够** —— `run_all` 内部拉起的第五个夹具以『结果少一段』的形式**静默失败**，
> 是**对全部产物做规范化对比**才撞出来的。」

## 四、产出

先给 **APPROVE / REJECT / APPROVE-WITH-FINDINGS** 一句话结论，再逐条列证据（指到文件行或命令输出）。
⛔ 只审：不改文件、不提交、不 push。⭐ 用完的临时目录/worktree 请自己清理。
