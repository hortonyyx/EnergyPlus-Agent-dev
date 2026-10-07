# 派工：runtime 小包 RT1（按模型服务承受能力错开派发、被拒请求的用量、每次运行的时间分布）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\rt1`，分支 `dev/astra-rt1-20261007`，基于含本派工单的主线提交。**迭代范围：只改 runtime**（`src/agent_runtime/` 及 runtime 相关检查、本实验目录）；domain（`src/agent/`、`scripts/tool_scripts/`）不改。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“runtime 小包 RT1”一节交付。** 先读 [名词规范](../../../project/terminology.md) 第二节（runtime／domain 的分界），再读 `src/agent_runtime/` 的 `loop.py`、`adapter.py`、`anthropic.py`、`providers.py`、`failures.py`、`budget.py`、`accounting.py`、`model_profiles.json`，以及分工模式怎样在同一进程里并发跑多个读图员（`src/agent/runtime_roles/session.py`、`entry.py`，只读）。

**为什么做：** 分工模式开头会同时派出全部读图员；GLM 订阅白天只接住约 5 路，多出的被拒后各自退避重试，今天 sm21 分工的一个平面读图员因此晚开工约 1 分钟，而它在关键路径上。用户决定先在 runtime 里按服务承受能力错开派发，以后再考虑换允许更多并发的服务。

**证据：** 今天的运行目录在主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\cmp3\`（`sm21_role` 开头约 120–190 秒的 `plan_f1` 五次 429；`sm24_role`、`sm24_single`、`sm21_single` 作对照），昨晚的在 `...\role_debug\`；只读，需要时拷到本工作树 `AI_agent/archive/local_backup/rt1/`。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新。
- 不调用真实模型服务；用模拟服务验证排队、降档与恢复。**本包 0 次模型请求**；Paratera 0，DeepSeek 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`，确认 `src.agent_runtime.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/rt1/pytest`。本机在跑三例对照，不跑全量。已知 `test_role_end_to_end.py::test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 机器忙时偶发失败，遇到时单独重跑并如实写。
- 新检查要克制，不锁报错原文；写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。

最终回复按验收 A–E 逐条给结果，附模拟场景的前后对比、sm21 分工新回执的时间分布示例、检查结果与建议的提交分组。
