# 派工：清理包 C4（分工模式的反馈去重、坐标契约、交付核对与调度员目录）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\c4`，分支 `dev/astra-c4-20261007`，基于含本派工单的主线提交（当前 Agent `t1-20261007-b1.1`）。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“清理包 C4”一节交付。** 先读 [第三次完整审查汇总](../../reviews/2026-10-07_third_full_review/summary.md) 与两份报告（[astra.md](../../reviews/2026-10-07_third_full_review/astra.md)、[opus.md](../../reviews/2026-10-07_third_full_review/opus.md)，必修项的文件与行号都在里面），再读 [10-07 分工调试](../2026-10-07_role_division_debug/README.md) 的 run4–run6，然后读 `src/agent/runtime_roles/` 的 `session.py`、`trial.py`、`readers.py`、`submission.py`、`assembly.py`、`assembly_review.py`、`guidance.py`。

**为什么做：** 两份独立审查一致认为分工的方向成立（一步建楼首次真实调用即成功、层高与外墙高度三次都对、调度员缓存 17% → 46%），但三例对照前要先去掉重复变厚的反馈、统一读图员的坐标说法并收住调度员的派工说明、堵上交付核对的漏层缺口、把调度员目录收成必要工具，否则对照会把这些与方案无关的问题一起测进去。

**文件范围：** `src/agent/runtime_roles/`、`tests/` 中角色相关检查、Agent 版本登记（本包负责）、本实验目录。**不改** `scripts/tool_scripts/`、`src/agent_runtime/`、`src/agent/geometry/`（可以调用）；单模型请求与返回逐字节不变（`test_role_single_parity.py` 必须仍过）。如果某项必修确实只能改共用代码才能做到，先停下在报告里写明原因与最小改法，不要自行扩范围。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，逐项设计说明，随进度更新。
- A 项要给离线复放的改前改后字符数：run3、run6 的平面试建（成功与失败各取几次）、一次派工结果、一次一步建楼返回。run3、run4、run5、run6 的运行目录在主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\role_debug\` 下（只读，可以读，不要写）；需要时拷到本工作树 `AI_agent/archive/local_backup/c4/` 再用。
- E 项的先决核对写进报告：交付检查到底要求什么依据、一步建楼写的依据是否满足、撤下依据事务后有没有路径缺口。
- 指引改动是**替换**：给出调度员、平面读图员、立面读图员指引与工具说明的改前改后字符数。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。
- **本包 0 次模型请求**：不跑真实整案，合并后由 Opus 复跑 sm24。Paratera 0，DeepSeek 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`（本工作树自己的 `.venv` 已建好），确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/c4/pytest`（先建好父目录）。本机同时在跑整案调试，不跑全量。已知 `test_role_end_to_end.py::test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 在机器忙时偶发失败（单独重跑能过），遇到时单独重跑并在报告里如实写。改了登记文件后用 `python -m src.agent_runtime.agent_registry register --root . --version <新版本> [--add-file KIND:PATH]` 登记再跑真实工具检查。
- 新检查要克制：只加检查行为是否正确的几项，不锁报错原文；设计被替换时旧检查直接删除。
- **Windows 上写文本一律 LF**。
- **沙箱下所有 `.git` 都是只读的：不要尝试提交、建分支或改 Git 配置。** 改动留在工作树，报告给出建议的提交分组。交付前尽量删掉 `AI_agent/archive/local_backup/c4/` 下你建的临时目录；删不掉就在报告里列出。

不设硬时限；开工即写报告初稿、逐步更新。最终回复按验收 A–H 逐条给结果，附复放的字符数、指引字符数、E 项先决核对结论、检查结果与建议的提交分组。
