# 派工：分工体系 v1 · D1j（立面对位不怕比例漂移、朝向由 runtime 推出、调度员收尾去弯路）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1j`，分支 `dev/astra-d1j-20261007`，基于含本派工单的主线提交（当前 Agent `t1-20261007-d1i.1`）。与 D1k 并行。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“D1j”一节交付。** 先读 [名词规范](../../../project/terminology.md) 第二节（10-07 用户定的代号：BIM Agent、work model、dev model、harness、runtime、domain），[工种与角色分工](../../../design/role_division.md)“提速的两类做法”，[10-07 调试](../2026-10-07_role_division_debug/README.md) 的 run5–run7，[第三次审查 Opus 报告](../../reviews/2026-10-07_third_full_review/opus.md) 的“换 4 档前”第 6 项与 L1；再读 `src/agent/runtime_roles/` 的 `elevation.py`（`match_elevation`、`_ordered_assignment`、立面交付格式）、`assembly.py`、`height_writes.py`、`height_evidence.py`、`session.py`（调度员目录与工具）、`guidance.py`（调度员与立面读图员两段）。

**为什么做：** 这是 Agent 迭代（做对、做稳、接口好填；省时是顺带）。sm24 run7 读图结束后调度员收尾 12 分钟，其中约 7 分钟花在东立面比例漂移造成的冲突自查与返工，约 3 分钟花在用 `revise_bim` 补房间用途（连错 4 次）；sm21 run1 没有这些弯路，收尾只要 5 分钟。立面提交的方向手续是立面首交被拒的主要原因，也是换 4 档模型时最先会暴露的问题之一。

**文件范围与并行约定：** 本包负责 `elevation.py`、`assembly.py`、`height_writes.py`、`height_evidence.py`、`session.py`，`guidance.py` 里**调度员与立面读图员**两段，`tests/` 中对应的角色检查，本实验目录。D1k 同时在改 `readers.py`、`trial.py`、`submission.py`、`plan_format.py` 与 `guidance.py` 的**平面读图员**一段：这些不要改；若确实要动（例如房间种子格式），先停下在报告里写明。**不改** Agent 版本登记（D1k 负责，合并后 Opus 统一登记）、`scripts/tool_scripts/`、`src/agent_runtime/`、几何内核与单模型工具（可以调用）；单模型请求与返回逐字节不变（`test_role_single_parity.py` 必须仍过）。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，逐项设计说明，随进度更新。
- 真实运行目录在主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\role_debug\`（run1–run7、sm21_run1、sm25_run1）与 `...\reader_model_probe\`（27B 摸底），只读；需要时拷到本工作树 `AI_agent/archive/local_backup/d1j/` 再用。参照在 `AI_agent/logs/experiments/2026-10-06_role_division_analysis/references/`。
- A 项的容差、最少门窗数与“比例合理范围”由你依据数据定，写明理由；宁可列冲突也不要硬对。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。**本包 0 次模型请求**；Paratera 0，DeepSeek 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/d1j/pytest`（先建好父目录）。本机在跑三例对照，不跑全量。已知 `test_role_end_to_end.py::test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 机器忙时偶发失败，遇到时单独重跑并如实写。
- 新检查要克制，不锁报错原文；写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。

不设硬时限；开工即写报告初稿、逐步更新。最终回复按验收 A–G 逐条给结果，附改前改后对上数与逐个核对表、参数结构与指引字符数、run7 七次修改意图的新工具重放结果、检查结果与建议的提交分组。
