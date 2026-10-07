# 派工：提速包 D1l（平面读图员先出稿后细查，调度员按精度三档收手）

派工人：Opus 5.5（项目经理）。工作树 `D:\EnergyPlus-Agent-worktrees\d1l`（10-07 起工作树放 D 盘），分支 `dev/astra-d1l-20261007`，基于含本派工单的主线提交。**迭代范围：domain（methods、guidance、tools），只影响分工模式**；单模型交给模型的内容逐字节不变，runtime 不改。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“提速包 D1l”一节交付（A–E）。** 先读 [名词规范](../../../project/terminology.md)、[评价口径](../../../design/evaluation.md)“精度三档”、[工种与角色分工](../../../design/role_division.md)，再读 `src/agent/runtime_roles/guidance.py`、`readers.py`、`trial.py`、`session.py`、`assembly.py` 与 `src/agent/geometry/plan_drawing_differences.py`。

**为什么做：** 用户 10-07：“几个小时完全无法接受，这也会拖慢开发进展”。三例对照里分工模式的关键路径是平面读图员，约九成时间花在第一次试建之前，用像素剖面把每条墙线量到像素级；sm25 分工的二层平面读图员到第 51 分钟才交付。数据见验收一节“依据”。

**证据（只读，需要时拷到本工作树 `AI_agent/archive/local_backup/d1l/`）：** 主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\cmp3\` 下 `sm24_role`、`sm21_role` 的 `events.jsonl`（读图员每步工具与请求时刻）；`sm25_role` 正在另一个工作树运行，完成后 Opus 会拷到同一目录，届时可补看，不必等。

**与同时进行的版本管理 V1 的文件分界：** V1 只改 `src/agent_runtime/` 下的登记与回执，并在 domain 新建一个指纹模块，不改 `src/agent/runtime_roles/` 的现有文件。本包不改 `src/agent_runtime/`，也不改 Agent 版本登记，合入后由 Opus 统一登记。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新。报告列出改前改后的平面读图员方法步骤原文对照与各角色字数。
- **0 次模型请求**；Paratera 0，DeepSeek 0。效果由 Opus 合入后在 GLM 上实测。
- 环境：工作树根目录先 `uv sync --frozen --python 3.12`，再 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树。pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/d1l/pytest`。不跑全量。已知 `test_role_end_to_end.py::test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 机器忙时偶发失败，遇到时单独重跑并如实写。
- 新检查要克制，不锁指引原文和报错原文；被替换的旧方法对应的旧检查直接改写或删除，不并存。写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。

最终回复按验收 A–E 逐条给结果，附提醒次数的取值依据、指引字数前后对照、检查结果与建议的提交分组。
