# 派工：分工体系 v1 · D1h（建层到写高度一步完成）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1h`，分支 `dev/astra-d1h-20261007`，基于含本派工单的主线提交（当前 Agent `t1-20261006-d1g.1`）。**与 B1（底座缓存，另一工作树）并行**，文件归属见下。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“分工体系 v1 · D1h”一节交付。** 先读同一文件 D1g 的验收结论，再读 [sm24 分工整案调试](../2026-10-06_role_division_sm24_debug/README.md)（run3 的逐步过程）与 [10-07 调试](../2026-10-07_role_division_debug/README.md)（run4），然后读 `src/agent/runtime_roles/` 的 `session.py`（派工、建层、对位、写高度、续接）、`levels.py`、`elevation.py`（`match_elevation`、`height_application`）、`height_writes.py`、`lineage.py`、`assembly_review.py`、`guidance.py`、`config.py`、`entry.py`，以及 `scripts/tool_scripts/run_bim_agent.py` 里 `assemble_plan_bim` 的输入约定（`get_bim_reference('plan_assembly')`）。

**为什么做：** 读图员已能各自交付，调度员却还要逐步调用读产物、带标高建层、总装、每面对位、写高度；run3 调度员 41 次请求、371 万 token，大半花在这些机械步骤和弯路上（镜像、旧稿对位、拿错编号、改层高后重写、并行分叉）。D1g 堵了弯路，本包把机械步骤合成一个确定性工具，调度员只处理对不上的部分。

**文件范围：** `src/agent/runtime_roles/`（`session.py` 与 `entry.py` 中构造 `ContextPolicy(...)` 的那一处参数归 B1，本包不动）、`scripts/tool_scripts/bim_agent_role_heights.py`、Agent 版本登记（本包负责登记）、`tests/` 中角色相关检查、本实验目录。不改 `src/agent_runtime/context.py`（归 B1）、单模型的指引与工具目录、`scripts/tool_scripts/run_bim_agent.py` 与 `src/agent/geometry/` 的共用内核（可以调用）。不改历史实验数据与原始输入。

**要点：**
- 开工先在本目录写报告初稿 `README.md`（设计说明：一步工具的输入输出、选交付的规则、标高规则与容差、需要决定事项的格式、可重复与续接怎样做、与总装审查怎样衔接），随进度更新。
- 报告给出“需要决定的事项”在 run3、run4 真实交付上的实际样子（离线重放所得），让人看得出调度员下一步该做什么。
- 指引改动是**替换**：给出调度员指引改前改后字符数（改前 2,007），说明删了哪些、加了哪些。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。
- **本包 0 次模型请求**：不跑真实整案，合并后由 Opus 复跑 sm24、sm25。Paratera 0，DeepSeek 0。
- run3 原始运行在证据分支 `evidence/role-division-sm24-debug-2026-10-06`（需要时用 `git show <分支>:<文件>` 取出，解到 `AI_agent/archive/local_backup/d1h/` 下，用完删除）；run3、run4 的运行目录 Opus 已拷到本工作树 `AI_agent/archive/local_backup/d1h/runs/`。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`（本工作树自己的 `.venv` 已建好；脚本已默认 `OPENBLAS_NUM_THREADS=1`），确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/d1h/pytest`（先建好父目录）。改了登记文件后用 `python -m src.agent_runtime.agent_registry register --root . --version <新版本>` 登记再跑真实工具检查。**交付前把 `AI_agent/archive/local_backup/d1h/` 下你建的临时目录删掉**（沙箱身份建的目录，本机账户事后删不掉；`runs/` 是 Opus 拷入的，留着即可）。沙箱里结束进程的检查会因权限失败，注明即可。不为变绿放宽保护性断言。
- 新检查要克制：只加检查行为是否正确的几项，不锁报错原文；被替换的分步设计的旧检查直接删除。
- **Windows 上写文本一律 LF**：`write_text(..., newline="\n")` 或现有写入辅助。
- **沙箱下所有 `.git` 都是只读的：不要尝试提交、建分支或改 Git 配置。** 改动留在工作树，报告给出建议的提交分组。

不设硬时限；开工即写报告初稿、逐步更新。最终回复按验收 A–I 逐条给结果，附离线重放结果、存稿数与调度员调用数对比、指引字符数、检查结果与建议的提交分组。
