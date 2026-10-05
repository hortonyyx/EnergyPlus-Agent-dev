# 派工：分界清理包 C3-R（底座开销、思考回传、按实际额度收尾、检查全量）

派工人：Opus 5.5（项目经理）。工作树 `/root/worktrees/astra-c3r`（本机盘，不在 `/workspaces` 的 9p 挂载上），分支 `dev/astra-c3r-20261005`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `/root/worktrees/astra-c3t` 做 C3-T。

**文件归属（写到函数一级）：**
- 本包：`src/agent_runtime/`（`agent_versions.json` 除外）、`src/harness_contracts/`、`src/agent/runtime_entry.py`、`src/agent/runtime_configuration.py`、`src/agent/runtime_tools.py` 的 `snapshot_state` 与检查点相关部分、`scripts/tool_scripts/bim_agent_budget.py` 整个文件、`bim_agent_guidance.py` 中 `FINISHING` 段“Tools report used and remaining minutes. After halfway, save missing floor drafts before refining. Below 15%, …”这两句、整案配置文件、`tests/` 中的旧检查文件（C3-T 改动模块的检查除外）。
- C3-T：`scripts/tool_scripts/` 其余、`runtime_context.py` 选当前稿的部分、`runtime_coordinator.py`、`runtime_behaviour.py`、`runtime_tools.py` 的 `_result_metadata` 与工具名表、登记表。本包不改登记表；需要对方配合的地方先在报告里写明，不越界改。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“清理包 C3-R”一节交付。** 先读[第二次完整审查汇总](../../reviews/2026-10-05_second_full_review/summary.md)，再读两份报告里与本包有关的部分：[Opus](../../reviews/2026-10-05_second_full_review/opus.md) 第 3.3、5.1、6.3 节与清单第 1、3、5 条；[Astra](../../reviews/2026-10-05_second_full_review/astra.md) 第三节测试部分与第四节 2、3。

要点：
- A 先计时再改，确认主因后再动；未知写恢复依赖写前后的快照，必须保留。运行根目录配置默认不变，只是允许显式指到本机盘；仍不能写进别的工作树。阶段 2 长任务与恢复、run99 重放必须照跑通过。
- B 做成按线路的配置，不改 GLM Anthropic 线路的行为；对连贯性的影响要等节点回归验证，所以 27B 配置改用新设置、旧设置可一键改回。Qwen 官方对多轮思考的建议如能查到，写进报告（只读文档，不调用模型）。
- C 替换原句，不新增一套催办规则；不自动放大任何额度；外部开发模型自身的用量看不到，不要把子请求账本当成全系统账单。
- D 不为变绿放宽保护性断言；重签哈希写明原因；退役的检查连同它锁的旧报告一起处理，并在报告里列清单。不改 `scripts/tool_scripts/` 里的文件来迁就 `test_scripts_bootstrap_lock`。
- 历史运行从证据分支取（`evidence/node-regression-a1-2026-10-04` 等，哈希清单在各实验目录 `evidence/`），用 `git show`／`git archive` 解到本工作树的临时目录，用完删掉；不检出或切换分支。
- 0 次模型请求，不用 DeepSeek；凭据不打印、不入仓。跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-05_cleanup_c3r/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 110 分钟内交付；到点没做完的，已完成部分小步提交并在报告里写清剩余（D 的全量可以放最后）。最终回复按验收 A–E 给结果、计时与字符数的改前改后、全量检查结果、检查与提交列表。
