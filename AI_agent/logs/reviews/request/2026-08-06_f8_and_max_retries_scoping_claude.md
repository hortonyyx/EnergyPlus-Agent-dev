# 调查单 · 两条治理债排期：F-8（「全仓绿」不可移植）+ `MAX_RETRIES=0`

> **⚠️ 这是「调查单」不是「施工单」。⛔ 只调查、不改生产代码/测试、不 commit、不 push。**

- **日期**：2026-08-06
- **派工方**：orchestrator（Opus 5）
- **席位**：Claude 侧 Sonnet 子代理（GLM 撞 5h 额度窗，本轮改由 Claude 侧推）
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD 应为 `dfbd62a`，**主工作树**

---

## 0. 开工自检（不对就停）

```bash
git log --oneline -1     # 期望 dfbd62a
git status --short       # 4 个 case_tests 未跟踪目录属已知、⛔ 不要动
pwd                      # 期望 /workspaces/EnergyPlus-Agent-dev
```

---

## 任务一（主）· F-8：「全仓绿」是这台机器工作目录的属性，不是这个提交的属性

### 已知事实（orchestrator 08-05 实测坐实，不必重复证明）

主树 `case_tests/` 比干净检出**多 619 个被 `.gitignore` 挡住的文件**
（`.gitignore:275 eplusout.*` · `:249 *.txt` 等：EP 输出 / correction·mep 的原始 LLM 回复 / viewer HTML），
**其中一部分是测试的活输入** ⇒ **干净 worktree / 新克隆 / CI 跑全仓必红 5 条**：

- `test_inspect_dxf::test_manifest_inspector_cli_exit_and_json_contract`
- `test_checks_reading_correction::test_partition_on_window_jamb_real_restore_reading_r2_flags_four`
- `test_gt_from_dxf::test_build_only_cli_round_trips_l_candidate_and_nonzero_north`
- `test_reading_score::test_sm21_phase1_reading_score_regression_floor`
- `test_validation_run_baseline::test_sm21_anchor_ep_clean`

同一份代码：主树 = 全绿；干净 worktree = 这 5 条红。
`test_validation_run_baseline.py:161` 的注释显示原作者**部分知情**（为个别用例合成了 `.end`），但覆盖不全。

**⇒ 与 F-5/F-7 同族：测试的绿证明不了它声称证明的东西。**

### 请你回答的（交付物）

1. **精确清单**：这 5 条测试各自**依赖哪些具体文件**、这些文件**为什么被 ignore**（引 `.gitignore` 行号）、
   **谁生产它们**（哪条命令/哪个 run 产的）。⛔ 不要给「大概是 EP 输出」这种话，给路径。
2. **分类**：把每个缺失依赖归入下列之一，并说明判据——
   ① 应当入仓的**小体积夹具**（几十 KB 级、稳定、可当契约样本）；
   ② 应当由测试**自己合成**的（像 `:161` 已经做的那样）；
   ③ 应当**标记为需要真实产物**因而在干净环境**跳过**（`skipif`）而不是红；
   ④ 其它（说清楚）。
3. **体积核算**：若走 ① 入仓，总共多少字节、多少文件。这条决定可行性。
4. **⭐ 一条防复发的机械检查**：怎样让「新增测试依赖了被 ignore 的文件」这件事**在提交时/CI 里自动被抓住**，
   而不是靠人记得。给 2 个选项 + 各自代价。⛔ 不要动手实现。
5. **排期建议**：哪几条能一次性收掉、哪几条要单独立项。

### 边界

- ⛔ **不改任何测试、不改 `.gitignore`、不 `git add` 任何被 ignore 的文件**。本单只出清单与方案。
- ✅ 允许**建临时干净 worktree 只读复现**（⚠️ 建 worktree 必须显式指定基点 `dfbd62a`，
  **⛔ 不许用默认基点**——默认会从 `origin/main` 切出，历史上已犯过）。用完自己清理。
- ✅ 一次性脚本放 `/tmp`。

---

## 任务二（次）· `MAX_RETRIES` 为什么被关成 0

`src/agent/_share.py:7` 定义 `MAX_RETRIES: Final[int] = 0`，
经 `src/agent/state.py:13,243` 成为 `max_retries` 默认值；`src/agent/runner.py:38` 的注释提到它。

### 请你回答的

1. **它到底关掉了什么重试**（哪条链路、哪一层）？给调用链与行号。
2. **`git log -S`/`-L` 查它何时、在哪个提交被改成 0，当时的提交信息说了什么理由**。
3. **现在把它设回非 0 会发生什么**（引代码说，⛔ 不要跑）——特别是与 F-4（correction 内层盲重试已改成回灌）、
   F-11（下游熔断 `InterruptLoopBreakerError`）的关系：**这三处重试语义是否互相冲突**。
4. **结论只要一句**：这是**有意关闭**（则把理由记进文档即可结案）还是**误伤**（则立项）。

---

## 交付

- 日志落 `AI_agent/logs/reviews/execution/2026-08-06_f8_and_max_retries_scoping_claude.md`（先落骨架再补）。
- ⛔ **不 commit、不 push。**做完在最终回复里给 **TL;DR**：F-8 的四类清单摘要 + 任务二那一句结论。

## 证据纪律（硬要求）

> **⛔ 不接受「我看了 / 我读了」作为结论依据** —— 每条结论给出**可独立重跑的命令 / 路径+行号 / 数字**。

## 停下上报（**记功不记过**）

本轮至今 **8 次「停下上报」，8 次都是派工方（我）的题错了**。
本单陈述的事实与你看到的不符 / 你认为提法本身有问题 / 真相与本单框架不兼容 ⇒ **立刻停下上报，不要硬凑**。
