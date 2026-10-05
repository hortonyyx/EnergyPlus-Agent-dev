# 派工：吸收包第五批 A5-T（按标注落位、命名缺口、按用量精简工具、指引共用段）

派工人：Opus 5.5。工作树 `.worktrees/astra-a5t`，分支 `dev/astra-a5t-20261005`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a5r` 做 A5-R；**文件归属**：`scripts/tool_scripts/run_bim_agent.py` 里的 `run_experiment` 函数与 `scripts/tool_scripts/evaluate_bim_agent.py` 归 A5-R，本包不改；其余 `scripts/tool_scripts/`、`src/agent/geometry/`、`src/agent/runtime_tools.py`、`src/agent_runtime/agent_versions.json` 归本包。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第五批 A5-T”一节交付。** 这是分界前最后一批工具侧吸收项，之后两边旗舰做第二次完整审查。先读[首次完整审查汇总](../../reviews/2026-10-03_first_full_review/summary.md)第四节与 [Opus 报告](../../reviews/2026-10-03_first_full_review/opus.md)的 L2、`AI_agent/logs/worklog/2026-10-01_opus_reconstruction_dev_pass.md`（按标注落位与命名缺口）、`AI_agent/design/bim_naming.md`。行为记录：10-04 两次 27B 与节点回归的运行（证据分支 `evidence/node-regression-a1-2026-10-04` 与主线压缩包，哈希清单在各实验目录 `evidence/`），以及 `AI_agent/logs/experiments/2026-10-01_behaviour_records/records/`。解包放本工作树的临时目录，用完删掉。

要点：
- 检查只报告不自动改；误报比漏报更伤，给出命中与误报条数。
- 移出默认目录不是删除：历史重放需要的工具保留注册，只在重放时暴露；按用量下结论要写明统计范围，没用过不等于没用，唯一入口的工具不动。
- 改写给模型的文字坚持“替换不追加”，四项合计必须下降。
- 0 次模型请求。在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-05_absorb_a5t/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 110 分钟内交付；到点没做完的，已完成部分小步提交并在报告里写清剩余（优先保证 C、D 完整）。最终回复按验收 A–E 给结果、命中与误报条数、移出的工具清单、改前改后的数字、新版本号、检查与提交列表。
