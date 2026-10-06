# 派工：分工体系 v1 · D1i（一步建楼写出覆盖表认可的高度依据）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1i`，分支 `dev/astra-d1i-20261007`，基于含本派工单的主线提交（当前 Agent `t1-20261007-c4.2`）。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“D1i”一节交付。** 先读同一文件 C4 验收结论的 E 项与 [C4 报告](../2026-10-07_cleanup_c4/README.md) 的 E 节（含 `E_replay.py`、`E_evidence.json`、`E_notes.md`：覆盖表只认 `D2`、`W_B1`），再读 `src/agent/runtime_roles/assembly.py`、`height_writes.py`、`elevation.py`（`height_application`）、`scripts/tool_scripts/bim_agent_role_heights.py`，以及覆盖表的实现 `src/agent/execution/bim_height_coverage.py`（只读）和交付时怎样调用它。

**为什么做：** 交付要求之一是“立面上读到的外墙门窗高度，作为有定位依据的记录在交付稿上确认或应用”。一步建楼已把高度几何写对（三次运行外墙高度 14/14），但它写的依据大多不被覆盖表认作“已定位”，交付时就报缺口；run6 调度员一步建楼后又试写 28 条依据事务，很可能就是在补这个缺口。C4 已把事务工具撤出调度员目录，缺口要从一步建楼的写入一侧消除。

**文件范围：** `src/agent/runtime_roles/`、`scripts/tool_scripts/bim_agent_role_heights.py`、`tests/` 中角色相关检查、Agent 版本登记（本包负责）、本实验目录。**不改**共用的覆盖检查、依据事务实现、单模型指引与工具（可以调用）；单模型请求逐字节不变。若确实只能改共用代码，先停下在报告里写明原因与最小改法。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新。
- run3、run6 的运行目录在主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\role_debug\` 下（只读，可以读，不要写）；需要时拷到本工作树 `AI_agent/archive/local_backup/d1i/` 再用。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。**本包 0 次模型请求**；Paratera 0，DeepSeek 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/d1i/pytest`。本机同时在跑整案调试，不跑全量。已知 `test_role_end_to_end.py::test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 机器忙时偶发失败，遇到时单独重跑并如实写。改了登记文件后用 `python -m src.agent_runtime.agent_registry register --root . --version <新版本> [--add-file KIND:PATH]` 登记。
- 新检查要克制，不锁报错原文；写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。

最终回复按验收 A–D 逐条给结果，附 13 个门窗的逐项表、改前改后覆盖数、检查结果与建议的提交分组。
