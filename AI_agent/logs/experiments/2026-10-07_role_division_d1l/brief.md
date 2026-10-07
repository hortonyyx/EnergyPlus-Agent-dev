# 派工：提速包 D1l（平面读图员按标杆做法先出稿，调度员开头一次派齐、按精度三档收手）

派工人：Opus 5.5（项目经理）。工作树 `D:\EnergyPlus-Agent-worktrees\d1l`，分支 `dev/astra-d1l-<日期>`，基于**质量包 Q1、Q2 合入后**的主线提交（本包改的角色文件与两包重叠，不并行）。**迭代范围：domain（methods、guidance、tools），只影响分工模式**；单模型交给模型的内容逐字节不变，runtime 不改。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“提速包 D1l”一节交付（A–G，10-08 凌晨定稿）。** 先读 [名词规范](../../../project/terminology.md)、[评价口径](../../../design/evaluation.md)“精度三档”、[工种与角色分工](../../../design/role_division.md)、[Sonnet 5.5 标杆](../2026-10-07_sonnet55_benchmark/README.md)（尤其“行为观察”里它的五步做法）、[合入效果测试](../2026-10-07_merged_sm25/README.md)的行为观察，再读 `src/agent/runtime_roles/guidance.py`、`readers.py`、`trial.py`、`session.py`、`assembly.py`、`assembly_review.py` 与 Q1 新加的墨线对齐、尺寸链规整、Q2 新加的平立面比对。

**为什么做：** 用户 10-07：“几个小时完全无法接受”，提速目标 sm24 ≤ 10、sm21 ≤ 15、sm25 ≤ 30 分钟（分工模式，质量不降）。同一 domain 上 Sonnet 5.5 做 sm25 只用 12.2 分钟、无实质错误，平面一次写全、没用一次像素剖面；GLM 平面读图员试建前要做 21–22 次剖面、第 24 分钟才首次试建，是整案的关键路径。另有调度员没一次派齐读图任务白等约 10 分钟、两处派工参数被拒。

**证据（只读，需要时拷到本工作树 `AI_agent/archive/local_backup/d1l/`）：** 主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\` 下 `merged\sm25_role_n1`（10-07 夜 GLM sm25 分工，含 `events.jsonl`、`dev_observe.json`）、`bench\A2_sonnet55_haiku_workers`（Sonnet 5.5 的完整工具序列 `agent_stream.jsonl`、`tools.jsonl`）、`cmp3\sm24_role`、`cmp3\sm21_role`、`speed\sm24_role_low`。逐角色时间线用 `python scripts/dev/observe_run.py <运行目录>`。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新。报告列出改前改后的平面读图员方法步骤原文对照与各角色字数。
- **0 次模型请求**；Paratera 0，DeepSeek 0。效果由 Opus 合入后在 GLM 上实测。
- 环境：工作树根目录 `uv sync --frozen --offline --python 3.12`，再 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树。pytest 显式 `-n 2 -p no:cacheprovider`，`--basetemp` 放 `AI_agent/archive/local_backup/d1l/pytest`，交付前用 Python 的 `shutil.rmtree` 删掉（沙箱建的目录项目经理账户无权删除，上一批残留了约 5 GB）。不跑全量。
- 文件归属：本包独占上面列的角色文件；不改 `src/agent/geometry/`、`scripts/tool_scripts/`（单模型与共用工具），不改 `src/agent_runtime/` 与登记表（合并后 Opus 用 `python -m src.agent_runtime.agent_registry register` 统一登记）。
- 新检查要克制，只验行为，不锁指引原文和报错原文；被替换的旧方法对应的旧检查直接改写或删除，不并存。写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。

最终回复按验收 A–G 逐条给结果，附分块规则与提醒次数的取值依据、指引字数前后对照、检查结果与建议的提交分组。
