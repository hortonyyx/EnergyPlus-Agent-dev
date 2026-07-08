# 文档沉淀复核（2026-07-08，Opus 沉淀 → Codex 独立复核）

**对象**：把 2026-07-06/07/08 Fable5 主控期的高价值工作从 logs 沉淀到活文档，保持 logs 为纯过程痕迹。
沉淀落点 = decision_log A 时间线（07-03→07-08 六条里程碑）/ plan 当前焦点（Fable5 体检 backlog 追踪 + Phase B/C 定位）/ contracts §5.6-5.8（架构接缝审计）/ capability B1 补（判卷+gt 同步升级线）/ CLAUDE §2（已在 commit `df6f249`）。

**Codex 复核**（`mcp__codex__codex`，danger-full-access，xhigh）= **APPROVE-WITH-CHANGES，4 findings，全采纳**：

- **F1+F2+F3（同根）报告 B3「再拓扑纳入 pipeline」的架构裁决未充分沉淀** —— 只在 decision_log 一笔带过，活 proposal `geometry_first_zonification.md` 仍旧口径（休眠·idfpy+B5 启动）。报告 B3 是长期架构裁决（stage 1.5 位置 / `zonification_output.json` sidecar / `method` run_config 参数 / 绑 C2 启动 / 切配内核已在本项目侧故比原设想更易落地）。
  → **修**：`geometry_first_zonification.md` §9 加「Fable5 B3 更新」块（纳入方案 + 分阶段 P0-P4 + 启动时机绑 C2 + 更易落地）+ §0 状态段指针 + plan 分出去模块表状态更新。
- **F4 plan.md 两处旧 backlog 与 07-08 已完成事实冲突** —— 「污染硬隔离硬化…后续改/现状=prompt 约束」+「污染硬隔离机制化(backlog，仍 prompt 级)」，与 07-08 已落地自相矛盾。
  → **修**：两处改「✅ 2026-07-08 已落地」并指向 decision_log 07-08 条；顺带修 ezdxf 依赖缺口过时表述（07-06 M2 已补 pyproject）。

**CONFIRMED（无问题）**：Top10 主线沉淀完整（#1/#6/#7/#9 进 07-06 里程碑·#2/#3/#4/#8/#10 开放项进 plan）；归位合理（历史→decision_log·backlog→plan·接缝→contracts·升级矩阵→capability）；其余 07-06/07/08 request/verdict/execution logs 仍是过程痕迹、无活文档误放；C2 B1 `Cell.polygon`/schema v2、判卷 W1-W6、CV 工具箱阳性满分等事实与执行日志/实验 README 一致。

**结论**：APPROVE-WITH-CHANGES → 4 findings 全采纳并修正 → 沉淀完成。
