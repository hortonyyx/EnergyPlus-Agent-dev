# 派工：分工体系 v1 · D1k（平面读图员少写字：依据框自动生成、墙线基准默认值、试建两种写法、按引用提交）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1k`，分支 `dev/astra-d1k-20261007`，基于含本派工单的主线提交（当前 Agent `t1-20261007-d1i.1`）。与 D1j 并行。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“D1k”一节交付。** 先读 [名词规范](../../../project/terminology.md) 第二节（10-07 用户定的代号：BIM Agent、work model、dev model、harness、runtime、domain），[工种与角色分工](../../../design/role_division.md)“提速的两类做法”，[第三次审查 Opus 报告](../../reviews/2026-10-07_third_full_review/opus.md) 的“换 4 档前”第 4、5 项与 L2、L3，[Astra 报告](../../reviews/2026-10-07_third_full_review/astra.md) 的“换 4 档前优先”一行；再读 `src/agent/runtime_roles/` 的 `readers.py`、`trial.py`、`submission.py`、`plan_format.py`、`guidance.py`（平面读图员一段），以及交付与评价侧读取平面依据的地方。

**为什么做：** 这是 Agent 迭代（接口按小模型能填对的标准设计；省时是顺带）。平面读图员是关键路径：sm24 run7 14 分钟、sm21 run1 一层 21 分钟，约三分之一花在写稿上——每次试建整份重写平面（7–8 千字符），提交时再手写全部依据（run7 42 条、9,185 字符，首次提交被拒后又整份重写）。依据框其实都能从试建对象的像素推出来。

**文件范围与并行约定：** 本包负责 `readers.py`、`trial.py`、`submission.py`、`plan_format.py`，`guidance.py` 里**平面读图员**一段，`tests/` 中对应的角色检查，Agent 版本登记（本包负责），本实验目录。D1j 同时在改 `elevation.py`、`assembly.py`、`height_writes.py`、`height_evidence.py`、`session.py` 与 `guidance.py` 的调度员、立面读图员两段：这些不要改；若确实要动，先停下在报告里写明。**不改** `scripts/tool_scripts/`、`src/agent_runtime/`、几何内核与单模型工具（可以调用）；单模型请求与返回逐字节不变（`test_role_single_parity.py` 必须仍过）。若评价或覆盖检查依赖手写依据而只能改共用代码，先停下在报告里写明原因与最小改法。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，逐项设计说明，随进度更新。
- 真实运行目录在主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\role_debug\`（run3、run5、run6、run7、sm21_run1、sm25_run1），只读；需要时拷到本工作树 `AI_agent/archive/local_backup/d1k/` 再用。
- 自动依据不能降低可追溯性：交付稿里每个平面对象仍要能追到原图位置，推断与假设仍与观测分开。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。**本包 0 次模型请求**；Paratera 0，DeepSeek 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/d1k/pytest`（先建好父目录）。本机在跑三例对照，不跑全量。已知 `test_role_end_to_end.py::test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 机器忙时偶发失败，遇到时单独重跑并如实写。登记用 `python -m src.agent_runtime.agent_registry register --root . --version <新版本> [--add-file KIND:PATH]`。
- 新检查要克制，不锁报错原文；写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。

不设硬时限；开工即写报告初稿、逐步更新。最终回复按验收 A–H 逐条给结果，附改前改后提交参数与参数结构字符数、手续性拒收的重放结果、指引字符数、检查结果与建议的提交分组。
