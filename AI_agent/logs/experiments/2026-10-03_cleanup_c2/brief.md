# 派工：清理包 C2（Agent 与量具）

派工人：Opus 5.5。工作树 `.worktrees/astra-c2`，分支 `dev/astra-c2-20261003`，基于主线。只在本分支小步提交，不合入、不推送。同时有另一个 Astra 会话在 `.worktrees/astra-c1` 做 C1（底座呈现与稳健性），两包文件范围不重叠，见验收标准；确需碰对方文件时只做最小改动并在报告里写明。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“清理包 C2”一节交付。** 背景与证据先读：`AI_agent/logs/reviews/2026-10-03_first_full_review/summary.md`，以及同目录 `opus.md` 第一、二、三节、`astra.md` 第 1–3 节（两份审查已完成，现在可以读）。

要点：
- 改写给模型的指引时，坚持“替换不追加”：每处改动写明针对哪条证据，四项合计不得净增。
- 工具目录过滤只按运行实际开启的能力（委派、续查），推理与参数化工具保留，见汇总第二节第 3 条。
- 改完用登记命令登记新 Agent 版本（命名沿用 R3 的规则），用 R3 的核对脚本三例重跑确认两底座仍逐字节一致。
- 行为记录合一时，T1 两次运行的记录在主线 `AI_agent/logs/experiments/2026-10-01_behaviour_records/records/`；新底座六次运行的压缩包在证据分支 `evidence/migration-2026-10-03` 和主线 `AI_agent/logs/experiments/2026-10-03_migration_comparison/evidence/`。解包放本工作树的临时目录，用完删掉。
- 0 次模型请求，DeepSeek 0。不改几何内核。
- 在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内，用完删掉。

约 110 分钟内交付。交付报告放 `AI_agent/logs/experiments/2026-10-03_cleanup_c2/README.md`，最终回复按验收 A–H 逐项给结果、改前改后的数字、新版本号、重跑的检查、提交列表和未完成项。
