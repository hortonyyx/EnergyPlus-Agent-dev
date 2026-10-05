# 派工：分界清理包 C3-T（保存结果契约、返回瘦身、报错修正）

派工人：Opus 5.5（项目经理）。工作树 `/root/worktrees/astra-c3t`（本机盘，不在 `/workspaces` 的 9p 挂载上），分支 `dev/astra-c3t-20261005`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `/root/worktrees/astra-c3r` 做 C3-R。

**文件归属（写到函数一级）：**
- 本包：`scripts/tool_scripts/` 全部，**例外** `bim_agent_budget.py` 整个文件，以及 `bim_agent_guidance.py` 中 `FINISHING` 段“Tools report used and remaining minutes. After halfway, save missing floor drafts before refining. Below 15%, …”这两句（归 C3-R，其余指引归本包）；`src/agent/runtime_context.py` 里选当前稿的部分（`changed_bim` 一段及其读取的字段）；`src/agent/runtime_coordinator.py` 的 `source_bim`、观察是否已应用的判定（`:331`、`:347` 一带）及恢复时重建（`:166` 一带）；`src/agent/runtime_behaviour.py`；`src/agent/runtime_tools.py` 的 `_result_metadata` 与工具名表；`src/agent_runtime/agent_versions.json`（登记归本包）；对应测试。
- C3-R：`src/agent_runtime/` 其余、`src/harness_contracts/`、`runtime_entry.py`、`runtime_configuration.py`、`runtime_tools.py` 的 `snapshot_state` 与检查点、`bim_agent_budget.py`、上述两句指引、旧检查文件。两边都需要改的地方先在报告里写明，不越界改。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“清理包 C3-T”一节交付。** 先读[第二次完整审查汇总](../../reviews/2026-10-05_second_full_review/summary.md)，再读两份报告里与本包有关的部分：[Astra](../../reviews/2026-10-05_second_full_review/astra.md) 第二节 2、3（事务接线与失败判定的复现方法在报告末尾“证据与审查边界”），[Opus](../../reviews/2026-10-05_second_full_review/opus.md) 第 1.1、2.2、2.3、6.1 节与清单第 2、4 条。

要点：
- A 是本包最重要的一项。目标是“所有保存入口一份契约、各处都读它”，不是往两个白名单里各补一个名字。部分成功的事务不能回滚式重试。
- B 只挪不删：全文进文件、可读回，诊断结论不变，严重项不截断。改模型可见文字要替换不追加，四项合计不得上升。
- 重放所需原始运行从证据分支取（`evidence/node-regression-a1-2026-10-04`，哈希清单在各实验目录 `evidence/`；A4-T 的 `revise_bim` 重放在 `AI_agent/logs/experiments/2026-10-05_absorb_a4t/`），用 `git show`／`git archive` 解到本工作树的临时目录，用完删掉；不检出或切换分支。
- 0 次模型请求，不用 DeepSeek；凭据不打印、不入仓。跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。本工作树在本机盘，检查会比以往快得多。
- 合并时由 Opus 统一跑全量并重新登记共同版本；本包按 E 登记自己的版本即可。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-05_cleanup_c3t/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 110 分钟内交付；到点没做完的，已完成部分小步提交并在报告里写清剩余。最终回复按验收 A–E 给结果、改前改后的字符数、检查与提交列表。
