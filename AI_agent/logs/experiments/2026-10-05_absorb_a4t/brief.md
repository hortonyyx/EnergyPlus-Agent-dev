# 派工：吸收包第四批 A4-T（全楼检查：上下层对齐与细条、平面差异检查）

派工人：Opus 5.5。工作树 `.worktrees/astra-a4t`，分支 `dev/astra-a4t-20261005`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a4r` 做 A4-R（底座），文件范围不重叠：本包只改 `scripts/tool_scripts/`、`src/agent/geometry/` 中的检查与诊断、`src/agent_runtime/agent_versions.json` 与对应测试。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第四批 A4-T”一节交付。** 先读 `AI_agent/design/model.md` 里 10-02 的规整原则与容差分层、[开发计划](../../../project/unified_agent_harness_plan.md)第七之二节“迁移后的改进待办”，以及 [10-04 节点回归记录](../2026-10-04_node_regression_a1/README.md)的 sm25 一节。sm25 新线路的原始运行在证据分支 `evidence/node-regression-a1-2026-10-04`（哈希清单在主线 `2026-10-04_node_regression_a1/evidence/`）；10-01 Opus 亲做三例与历史草稿冻结参照的位置见各自实验目录（09-30 修复包、10-01 开发三例）。解包放本工作树的临时目录，用完删掉。

要点：
- 检查只报告、给出对齐到哪条已有线的建议，不自动改几何；误报比漏报更伤，给出误报条数。
- 不新增工具；改写给模型的文字坚持“替换不追加”，四项合计不得增加；返回里新增的内容走 A3-T 的摘要方式。
- 0 次模型请求。在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。同机还有别的检查在跑，别开太多并发。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-05_absorb_a4t/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 110 分钟内交付；到点没做完的，先保证 A 完整提交，B 已完成部分小步提交并在报告里写清剩余。最终回复按验收 A–D 给结果、命中与误报条数、改前改后的数字、新版本号、检查与提交列表。
