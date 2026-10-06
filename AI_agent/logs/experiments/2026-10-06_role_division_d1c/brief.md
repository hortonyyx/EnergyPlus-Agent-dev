# 派工：分工体系 v1 · D1c（平面读图员的起草与返工）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1c`，分支 `dev/astra-d1c-20261006`，基于含本派工单的主线提交（D1b 已合入，当前 Agent `t1-20261006-d1b.2`）。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“分工体系 v1 · D1c”一节交付。** 先读同一文件的“D1b 验收结论”，再读[平面读图员实测](../2026-10-06_plan_reader_probe/README.md)和 [probe_trials.json](../2026-10-06_plan_reader_probe/probe_trials.json)（17 次试建逐次分类），然后读 `src/agent/runtime_roles/` 的 `trial.py`、`plan_review.py`、`readers.py`、`submission.py`、`guidance.py`，以及 `src/agent/geometry/plan_revision.py` 与 `scripts/tool_scripts/run_bim_agent.py` 里的 `revise_plan`（单模型的按操作修改）。

**为什么做：** D1b 合入后单独实测平面读图员（sm24 一层，30 次请求），没有交付：17 次试建里 8 次被返工申报手续拒收，6 次格式错误（每次只报一处），3 次几何错误。第一份稿字段名全错，改对格式后整份都算“改动”，被要求逐项申报 33–45 项。D1 版本同一任务第 4 次试建即通过。D1-A 发现的问题（整层重建冲掉已对的项）仍要防，但应在有了一份出几何的稿之后才管，而且用“按操作修改”自然做到，不靠申报。

**文件范围：** `src/agent/runtime_roles/`（主要是 `trial.py`、`plan_review.py`、`readers.py`、`submission.py`、`guidance.py`、`session.py` 中返工相关部分）；`tests/` 中角色相关检查；本实验目录。可以调用但不要修改 `src/agent/geometry/plan_revision.py` 与 `scripts/tool_scripts/run_bim_agent.py`；单模型的指引、工具目录、请求与返回逐字节不变。不改历史实验数据与原始输入。

**要点：**
- 开工先在本目录写报告初稿 `README.md`（设计说明：起草期与操作期怎样区分、基准稿怎样记、操作如何复用 `apply_plan_revision`、跨任务 `rework_targets` 如何限制、格式问题如何一次列全、`wall_reference` 新写法），随进度更新。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。
- 指引改动是**替换**：给出平面读图员指引改前改后的字符数（改前 8,015），说明删了哪些句子、加了哪些。
- E 的离线复放用 [probe_trial_arguments.json](../2026-10-06_plan_reader_probe/probe_trial_arguments.json)，原图 `AI_agent/logs/experiments/2026-10-01_opus_dev_sm24/images/1f_view.png`；用真实冻结工具服务，不调用模型。
- **本包 0 次模型请求**：不跑真实小测，合并后由 Opus 复测。Paratera 0，DeepSeek 0，整案 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`（本工作树自己的 `.venv` 已建好；脚本已默认 `OPENBLAS_NUM_THREADS=1`，避免多个工具服务进程挤爆内存），确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/d1c/pytest`（先建好父目录）。**交付前把 `AI_agent/archive/local_backup/d1c/` 下的检查临时目录删掉**（沙箱身份建的目录，本机账户事后删不掉）。沙箱里结束进程的检查会因权限失败，注明即可。不为变绿放宽保护性断言。
- **Windows 上写文本一律 LF**：`write_text(..., newline="\n")` 或现有写入辅助，实验脚本同样。
- **沙箱下所有 `.git` 都是只读的：不要尝试提交、建分支或改 Git 配置。** 改动留在工作树，报告给出建议的提交分组。

不设硬时限。最终回复按验收 A–G 逐条给结果，附复放结果、指引字符数、检查结果与建议的提交分组。
