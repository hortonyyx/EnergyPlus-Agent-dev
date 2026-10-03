# 派工：清理包 C1（底座呈现与稳健性）

派工人：Opus 5.5。工作树 `.worktrees/astra-c1`，分支 `dev/astra-c1-20261003`，基于主线。只在本分支小步提交，不合入、不推送。同时有另一个 Astra 会话在 `.worktrees/astra-c2` 做 C2（Agent 与量具），两包文件范围不重叠，见验收标准。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“清理包 C1”一节交付。** 背景与证据先读：`AI_agent/logs/reviews/2026-10-03_first_full_review/summary.md`，以及同目录 `opus.md` 第五节、`astra.md` 第 5 节（两份审查已完成，现在可以读）。

要点：
- 这包的目的，是让新底座上模型每轮看到的东西与 Claude Code 对齐，并且不再因一次服务抖动就整轮作废。之后要真跑同条件对照，所以 A（上下文只追加、按阈值压缩）是核心。不要为了省 token 去删模型需要的信息。
- 离线重放用迁移对照的真实运行：P3 的压缩包在证据分支 `evidence/migration-2026-10-03`（`git show evidence/migration-2026-10-03:attempt_03_run.tar.xz`），订阅三次也在那里；主线有哈希清单。解包放本工作树的临时目录，用完删掉。
- 不改几何内核、工具实现、指引（那些归 C2 或以后）。
- 最多 4 次 GLM 订阅小请求（见验收 G），Paratera 与 DeepSeek 为 0。
- 在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内，用完删掉。

约 110 分钟内交付。交付报告放 `AI_agent/logs/experiments/2026-10-03_cleanup_c1/README.md`，最终回复按验收 A–G 逐项给结果、改前改后的数字、重跑的检查、提交列表和未完成项。
