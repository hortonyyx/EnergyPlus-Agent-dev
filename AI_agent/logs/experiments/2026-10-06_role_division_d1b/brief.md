# 派工：分工体系 v1 · D1b（读图员交付、批量写高度、D1-A 五项）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1b`，分支 `dev/astra-d1b-20261006`，基于含本派工单的主线提交（D1、D1-A 均已合入）。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“分工体系 v1 · D1b”一节交付。** 先读同一文件的“D1 验收结论”“D1-A 验收结论”，再读 [D1 报告](../2026-10-06_role_division_d1/README.md) 的 G 节与未决项，以及 [D1-A 报告](../2026-10-06_role_division_analysis/README.md) 的 A、C、D 节（D 节是评分器与参照）。

**文件范围：** `src/agent/runtime_roles/`；C4 涉及的共用平面差异检查（在 `src/agent/geometry/` 或 `scripts/tool_scripts/` 里，以实际位置为准）；批量写高度需要的工具入口；D1-A 评分器的产物转换（新文件，放本实验目录或 `src/agent/runtime_roles/`，评分器本身不改）；对照配置；`tests/`。单模型的 `claim_transaction` 语义不变；单模型除 C4 那句提示外，请求与返回逐字节不变。不改历史实验数据与原始输入。

**要点：**
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。开工先在报告里写设计说明：提交工具的参数与检查、平面“引用已通过试建”的认定方式、批量写高度怎样只存一份稿、五项各落在哪里。
- 离线贯通按对照配置的候选上限 24 跑，不要临时调大；给出 sm21、sm24、sm25 各例的存稿数。sm21 也补一条离线贯通。
- **Windows 上写文本一律 LF**：`write_text(..., newline="\n")`，或用现有写入辅助；实验脚本同样。D1-A 曾因 CRLF 导致记录的哈希在检出后对不上。
- F 的真实小测在最终代码上跑（D1 的小测跑在最终代码之前），只用 GLM 订阅：凭据在主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\.env`，显式传路径，只读，不打印、不复制、不入仓；合计不超过 40 次请求。Paratera 0 次，DeepSeek 0 次，整案 0 次。
- 跑检查：先在工作树根目录执行 `. .\scripts\activate_windows.ps1`（本工作树自己的 `.venv` 已建好），确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/d1b/pytest`（先建好父目录）。沙箱里结束进程的检查会因权限失败，注明即可，由 Opus 本机复跑。不为变绿放宽保护性断言。
- 原始运行目录超过 10 MB 的留在原处，不必自己打包，Opus 按证据约定归档。
- **Windows 沙箱下所有 `.git` 都是只读的：不要尝试提交、建分支或改 Git 配置。** 改动留在工作树，报告给出建议的提交分组。

**开工先把报告初稿写到 `AI_agent/logs/experiments/2026-10-06_role_division_d1b/README.md`**，随进度更新。不设硬时限。最终回复按验收 A–H 逐条给结果，附小测数据、存稿数、检查结果与建议的提交分组。
