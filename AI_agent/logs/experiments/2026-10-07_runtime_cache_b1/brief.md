# 派工：底座优化 B1（分工模式的上下文缓存）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\b1`，分支 `dev/astra-b1-20261007`，基于含本派工单的主线提交（当前 Agent `t1-20261006-d1g.1`）。**与 D1h（一步工具，另一工作树）并行**，文件归属见下。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“底座优化 B1”一节交付。** 先读 [sm24 分工整案调试](../2026-10-06_role_division_sm24_debug/README.md) 与 [10-07 调试](../2026-10-07_role_division_debug/README.md)，再读 `src/agent_runtime/context.py`（`ContextPolicy`、`_project_by_tokens`、压缩与图片决定）、`src/agent_runtime/anthropic.py`（`convert_messages` 的 `cache_control` 位置）、`src/agent_runtime/loop.py`（每次请求怎样投影上下文、记账里的缓存读取量）、`src/agent/runtime_roles/entry.py`（调度员的上下文策略）与 `session.py` 的 `run_reader`（读图员的上下文策略）。之前的缓存工作见 `AI_agent/project/unified_agent_acceptance.md` 的 C1、A2-R、C3-R 各节（上下文只追加、请求前缀已查明干净、流式与会话标识无效）。

**为什么做：** 用户 10-06 定底座优化提到换模型之前、以缓存命中为首；新底座要在速度、消耗、缓存命中上全面超过 Claude Code。run3 调度员缓存读取仅约 17%，Opus 的初步核对：上下文在 5 万与 13 万 token 之间来回跳，第 20–37 分钟压缩 8 次，每次压缩改写前缀；另有读图期间约 13.6 分钟的等待使缓存过期。这是初步解释，A 项要用数据核实或推翻。

**文件范围：** `src/agent_runtime/context.py`（新增的策略项默认保持现有行为）、新建 `src/agent/runtime_roles/context_policy.py`（按角色给策略）、`session.py` 的 `run_reader` 与 `entry.py` 中构造 `ContextPolicy(...)` 的那一处（改为调用新模块，其余归 D1h，不动）、`tests/` 中上下文相关检查、本实验目录。**不改 Agent 版本登记文件**（由 D1h 登记，合并后 Opus 统一重新登记）。单模型请求逐字节不变，不改单模型的指引、工具与上下文默认值。

**要点：**
- 开工先在本目录写报告初稿 `README.md`（诊断方法、逐次前缀对比的算法、策略选择与理由），随进度更新。
- run3、run4 的运行目录 Opus 已拷到本工作树 `AI_agent/archive/local_backup/b1/runs/`（事件记录 `events.jsonl` 含调度员与读图员全部请求，`task_id` 区分）。逐次核对写成可重复运行的脚本放本目录，结果存成 JSON。
- 前缀对比用实际请求投影（按现有估算口径算 token，图片按模型档案估算）；能从已存请求正文直接比对的，优先用实际正文。
- 读图员也在范围内（平面读图员在 10 万 token 压缩、立面读图员上下文较小），按数据决定是否改。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。
- **本包 0 次模型请求**。Paratera 0，DeepSeek 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`（本工作树自己的 `.venv` 已建好），确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/b1/pytest`（先建好父目录）。**交付前把 `AI_agent/archive/local_backup/b1/` 下你建的临时目录删掉**（`runs/` 是 Opus 拷入的，留着即可）。不为变绿放宽保护性断言。
- 新检查要克制：只加检查行为是否正确的几项，不锁报错原文。
- **Windows 上写文本一律 LF**。
- **沙箱下所有 `.git` 都是只读的：不要尝试提交、建分支或改 Git 配置。** 改动留在工作树，报告给出建议的提交分组。

不设硬时限；开工即写报告初稿、逐步更新。最终回复按验收 A–F 逐条给结果，附逐次前缀对比的改前改后数字、所选策略与理由、检查结果与建议的提交分组。
