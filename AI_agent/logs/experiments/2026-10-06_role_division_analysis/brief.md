# 派工：分工体系 v1 · D1-A（10-05 两处变差的定位、按角色小题的参照）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1a`，分支 `dev/sol-d1a-20261006`，基于含本派工单的主线提交。另一个 Astra 会话同时在 `…\d1` 开发分工 v1（D1）；本包结论是它的设计输入，写好一部分就更新报告。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“分工体系 v1 · D1-A”一节交付。** 先读：[工种与角色分工](../../../design/role_division.md)、[10-05 分界回归记录](../2026-10-05_node_regression_c3/README.md)（含评分脚本 `evaluate.py`、速度与开销脚本 `metrics.py`），以及 [10-04 回归记录](../2026-10-04_node_regression_c2/README.md)。

**文件范围：** 只写 `AI_agent/logs/experiments/2026-10-06_role_division_analysis/`。不改代码、指引、配置与历史数据。

**要点：**
- 运行记录在证据分支：10-05 是 `evidence/node-regression-c3-2026-10-05`，10-04 的分支名与压缩包哈希见各回归目录的 `evidence/` 清单。用 `git show`／`git archive` 解到本工作树的临时目录（如 `AI_agent/archive/local_backup/d1a/`），先核压缩包哈希；用完删除；不检出或切换分支。
- 行为记录脚本、评分脚本可直接复用；只记可观察的依据（请求、工具参数与返回、可见文字与保存结果），不推测隐藏思考。
- 参照只用于小题答案与评价，不进入任何运行输入。参照来源（GT 文件或经评审的好结果、哈希）写进报告。
- 0 次模型请求，不用 DeepSeek；不读、不打印 `.env`。
- 跑脚本前在工作树根目录执行 `. .\scripts\activate_windows.ps1`（本工作树自己的 `.venv` 已建好）。
- **Windows 沙箱下所有 `.git` 都是只读的：不要尝试提交、建分支或改 Git 配置。** 改动留在工作树，报告里写建议的提交分组，由 Opus 复核后提交。

**开工先把报告初稿写到 `AI_agent/logs/experiments/2026-10-06_role_division_analysis/README.md`**，按 A→B→C→D 的顺序推进，每完成一项就更新报告。最终回复按验收 A–E 逐条给结论与证据位置。
