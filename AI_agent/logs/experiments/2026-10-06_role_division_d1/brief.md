# 派工：分工体系 v1 · D1（角色运行框架、两类读图员、立面对位）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1`，分支 `dev/astra-d1-20261006`，基于含本派工单的主线提交。另一个会话（GPT-5.6 Sol）同时在 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1a` 做 D1-A 分析，只写它自己的实验目录，与本包没有共享文件；它的结论会在途中放进它的报告，可参考，不必等。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“分工体系 v1 · D1”一节交付。** 先读：[工种与角色分工](../../../design/role_division.md)、[决策](../../../project/decisions.md) 10-05 与 10-06 两行、[10-05 分界回归记录](../2026-10-05_node_regression_c3/README.md)。现有机制：阶段 3／R1 的局部观察委派（`src/agent/runtime_delegation.py`，`runtime_coordinator.py` 的 `delegate`／`delegate_many`）、单模型入口 `src/agent/runtime_entry.py`、整案配置 `src/agent/runtime_configuration.py`、平面格式 `src/agent/geometry/plan_input.py` 与 `build_plan_bim`、角色与模型路由 `src/agent/model_routes.py`。

**文件范围：** 可改 `src/agent_runtime/`、`src/harness_contracts/`、`src/agent/` 下运行与角色相关模块（可新建角色目录模块）、`scripts/tool_scripts/`（试建、立面对位、指引）、新配置文件与 `tests/`。单模型模式的行为与请求不变。不改历史实验数据与原始输入。

**要点：**
- 内部怎么分工、要不要派子代理由你定（子代理优先 5.6 系列，在报告写明型号与原因）。先在报告里写一页设计说明：角色定义的结构、两种产物格式、产物登记与引用、立面对位的输入输出、配置格式；再实现。之后改了设计，同步更新说明。
- 指引替换不追加：读图员指引从单模型指引搬对应段落；调度员指引只留调度、建层组装、对位、检查返工、交付。给出字符数。
- 产物格式按小模型能填对的标准设计：扁平、必填少；出错信息指向具体项，并附最小正确示例。
- 真实小测只用 GLM 订阅。凭据在主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\.env`，显式传这个路径，只读，不打印、不复制、不入仓；合计不超过 40 次请求。Paratera 0 次，DeepSeek 0 次，整案 0 次。
- 好结果与历史运行：Opus 10-01 开发三例在 `AI_agent/logs/experiments/2026-10-01_opus_dev_sm21/`、`…_sm24/`、`…_sm25/`；10-05 回归的完整运行在证据分支 `evidence/node-regression-c3-2026-10-05`，需要时用 `git show`／`git archive` 解到本工作树的临时目录，用完删除，不检出或切换分支。
- 跑检查：先在工作树根目录执行 `. .\scripts\activate_windows.ps1`（本工作树自己的 `.venv` 已建好），确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放本工作树的 `AI_agent/archive/local_backup/d1/pytest`。不为变绿放宽保护性断言。
- **Windows 沙箱下所有 `.git` 都是只读的：不要尝试提交、建分支或改 Git 配置。** 改动留在工作树；报告里给出建议的提交分组（每组文件清单与提交说明），由 Opus 复核后提交。

**开工先把报告初稿写到 `AI_agent/logs/experiments/2026-10-06_role_division_d1/README.md`**，过程中随进度更新（设计说明、已完成与未完成、检查结果）。工作量较大，不设硬时限；每做完一部分就更新报告，便于中途接续。最终回复按验收 A–I 逐条给结果，附字符数、小测数据、检查结果与建议的提交分组。
