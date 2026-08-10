# 派工单 · F-21 候选**调查**：几何批准是否会在上游仍阻断时照样签发

- **日期**：2026-08-10 · **席位**：GPT 侧 **`gpt-5.6-terra`**（中档执行）· effort **high**
- **性质**：⛔ **只调查 + 定性，不施工、不改任何生产码**
- **基点**：分支 `6.15_ValidationArchM0toM4`，**HEAD = `78194f8`**
- **成本**：零 LLM 生产调用、零付费 API、零全仓测试（⛔ 不要跑全仓，8 分 45 秒且与本单无关）
- ⚠️ **有另一个施工席正在同一仓库改 `src/agent/execution/validation_run.py` 与 `tests/`（F-20）**
  ⇒ **⛔ 你只读，不要改任何文件、不要 `git add/commit/stash/checkout`**；
  若发现工作树有未提交改动，**那是它的，别动、也别报成缺陷**。

---

## 1. 观察到的事实（orchestrator 2026-08-10 亲手读码，⛔ 但严重性未定）

[`src/agent/execution/step_orchestrator.py:486-488`](../../../src/agent/execution/step_orchestrator.py#L486)：

```python
res = validate_case(run_dir, case_dir=case_dir, policy=effective)
if res.geometry_digest is None:
    return None
appr = GeometryApproval(digest=res.geometry_digest, ...)
appr.save(run_dir)
```

**它只看 `res.geometry_digest is None`，不看 `res.blocked`。**

而 `geometry_digest` 只由 `2_modelling` 那一段决定
（`validation_run.py` 里几何一致性 + kernel 通过才算出 digest）。
⇒ **推论（待你证实或证伪）**：若 `1_correction`（或 `0_reading`）有 blocking 结果、
而 `2_modelling` 恰好算得出 digest，则**几何批准仍会被签发并落盘**。

⛔ **这只是读码得出的推论。本单的任务就是把它变成事实或推翻它。**

---

## 2. 必答问题

### Q1（B3 纪律，最高优先）｜这是有意设计还是漏检？

用 `git log -S` / `git blame` 找出**引入 `if res.geometry_digest is None: return None` 这个判据的那次提交**，
**读它的 commit message 原文并引用**。要回答：

- 当初为什么用 digest 存在性、而不是 `res.blocked` 或 `res.all_passed()` 当闸门？
- **这东西没了 / 改成看 `res.blocked`，谁会因为「以为它还是老样子」而算错？**
- ⛔ **禁止**只凭当前源码或注释就断言「这是疏忽」。项目 08-09 刚在这上面栽过一次
  （把一个有明确理由的标记读成「当初没人敢用」，而理由逐字写在引入它的提交说明里）。
  **查不到就如实写「查不到」**，不要用源码注释冒充提交说明。

### Q2｜可达性：这个状态真的能出现吗？

**必须用真实产物或程序化构造**证明「`geometry_digest` 非空 **且** `res.blocked` 为真」这个组合可达。
- 盘上 `case_tests/e2e_tests/` 有大量真实 run，**逐个跑 `validate_case`（只读，`write_reports=False`）**
  统计这个组合出现几次、都是哪些 run、blocking 的是哪些 check_id。
- 若真实语料里一个都没有，**再判断是「结构上不可能」还是「只是碰巧没有」** ——
  这两者结论完全不同。

### Q3｜实际后果：flow 是否在别处拦住了？

追 `approve_geometry` / `geometry_is_approved` 的**全部调用点**
（含 `scripts/tool_scripts/run_stage.py` 的人工 `approve-geometry` 子命令与 `--geometry auto`）：
- 签发了一份「上游仍阻断」的批准之后，**下一步会发生什么**？flow 会继续往下走吗？
- 还是说另有一道门靠 `res.blocked` 把它拦住，使这个缺口**实际无害**？
- **人工批准路径与自动路径的后果是否一致？**

### Q4｜测试覆盖

有没有任何测试锁住「上游阻断时不得签发几何批准」？给出你数的确切命令。
（⚠️ 提醒：本项目 08-10 刚吃过一次「一道门只有负向断言 ⇒ 恒红不可观测」的亏
⇒ 数覆盖时要**同时**看正向锁和负向锁。）

### Q5｜定性与建议

给出你的定性：**真缺陷 / 无害的设计选择 / 需要更多信息**。
若判为真缺陷，给出**严重性**与**修法方向**（⛔ 只给方向，不要写实现）。
⚠️ 注意：把闸门改成 `res.blocked` 是**收紧**，可能让现有能批的 run 批不了
⇒ **必须实测 blast radius**（哪些真实 run 会从「能批」变成「不能批」）。

---

## 3. ⛔ 边界

1. ⛔ **不改任何文件**。探针只在 `/tmp`（`mktemp -d`），跑完自清。
2. ⛔ 不许 `git add` / `commit` / `stash` / `checkout` / 切分支。
3. ⛔ 不许读 `case_tests/test_baseline/gt/`（gt 只对 gate② judge 与人开放）。
4. ⛔ 不要跑全仓测试。
5. ⛔ **不要碰 F-20 施工席正在改的 `validation_run.py` / `tests/`** —— 你读它可以，改它不行；
   **且你读到的可能是它改到一半的状态** ⇒ 若发现该文件与 HEAD 不一致，
   **以 `git show HEAD:<path>` 为准做判断**，并在报告里注明。

---

## 4. 交付物

报告落 `AI_agent/logs/experiments/2026-08-10_f21_approve_geometry_blocked/README.md`：

1. **Q1–Q5 逐条结论 + 证据**（文件行号 / 命令与其输出片段 / 提交号与 message 原文）。
2. **可复跑只读脚本**随报告入库。
3. **⛔ 明确列出你没能证实的部分** —— 宁可留白，不要用推理填。
4. 你的定性与建议（若判为真缺陷，含实测的 blast radius）。

---

## 5. 合法退出口

以下任一情况请**停下如实上报**：

- §1 那条读码推论你实测下来是**错的**（那本身就是最有价值的结果，直接结案）；
- Q1 找不到引入提交、或提交 message 没写理由 ⇒ **如实说「查不到」**；
- 本单某两条要求互相冲突；
- 工作树状态让你无法可靠判断（F-20 施工席在同仓库跑）。

**⛔ 派工方（orchestrator）自陈错误率 = 14/14** —— 迄今每一次执行席「停下上报」，
事后都证明是派工单的题错了。**顶住不照做、如实上报是期望行为，不是失败。**
