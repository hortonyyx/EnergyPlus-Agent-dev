# 审阅请求：AI_agent 管理文档重构（2026-06-20）

> 变体：Codex MCP 直审（自主读文件 + 跑 pytest）。findings 内联回主 Agent，request/review 落盘留轨。

## 背景 / 动机（用户定方向）

AI_agent 管理文档此前职责不清、结构混乱、历史决策反复叠到两个主文档。本轮按用户 5 条方向重构：
1. **CLAUDE.md** = 根文件，只放项目结构 + 当前状态 + 约定 + 索引（不叠历史、不堆待办）。
2. **plan.md** = 活计划，近细远粗，分出去的独立模块用单独文档。
3. **历史决策统一归档** = 新建单文件 `decision_log.md`（不再叠到两个主文档）。
4. **memory↔管理文档同步硬纪律**（换主控模型不丢信息）写进 CLAUDE.md §5#1。
5. 口径通扫对齐当前；已 close 的 handoff 清理；`downstream_agent_changes.md` 保留为活文档；
   capability 类（全流程能力）回 capability/、未落地方案进新 `proposals/`、历史架构+已实现工程计划进新 `archive/`。

## 改动清单

**新结构**（用户拍板 3 项命名）：`decision_log.md` 单文件 / `proposals/` / `archive/`。

- **新建** `AI_agent/decision_log.md`：A 里程碑时间线（倒序，含 06-20 三条原只在 memory/commit 的新决策）+ B §5.1–5.13 决策详档（从旧 CLAUDE 切片，保真）+ C 两份 changelog 合并。
- **重写** `AI_agent/CLAUDE.md`（424→~120 行）：§1 总览+架构+关键路径+**§1.5 关键不变量** / §2 当前开发状态 / §3 责任 / §4 洞察 / §5 约定（**#1=memory↔docs 同步硬纪律**）/ §6 索引。
- **重写** `AI_agent/plan.md`（523→~90 行）：当前焦点 + 近期(细 N1–N4) + 中期(粗 C2/C3/C4) + 远期 + 分出模块指针 + 搁置 + 已完成一行汇总。
- **移动**（git mv 保历史）：architecture/{architecture, pipeline_validation_build_plan, rules_md_split_map, twostep_architecture_diagram}.md + logs/2026-06-09_refactor_handoff.md → `archive/`；architecture/pipeline_0-5_capability_upgrade_suggestions.md → `capability/`；architecture/{geometry_first_zonification, editable_geometry_confirmation, cad_to_gt_extraction_plan}.md → `proposals/`。**architecture/ 现只剩 pipeline_stage_contracts.md**（唯一当前架构文档）。
- **链接修复**：活文档（pipeline_stage_contracts / new_case_guide / capability/* / reference/* / proposals/*）指向被移动文件的链接已改向；活文档死链已清（仅剩 floorplan_redraw POC-史 里对已退役 energyplus_mcp 的历史叙述引用，有意保留）。
- **test_baseline 同步**：index.md（sm21 gt 路径→bundle、标注 South 2F 窗 x 未结、CAD→gt 方向、下一份 judge-in-the-loop run）+ README.md（补 gt 铁律/CAD→gt/render_gt 指针）。

## 请重点查

1. **信息无损**：decision_log 是否完整承接了旧 CLAUDE §5.1–5.13 + 7 条顶 banner + 两份 changelog？有无决策被整理时丢掉？
2. **职责互斥**：CLAUDE/plan/decision_log 三者边界是否清晰、无重复叠加？CLAUDE 是否仍含不该有的历史/待办？
3. **死链**：活文档（archive/ 与 decision_log 这两个历史档案豁免）有无指向不存在路径的链接？
4. **口径准确**：CLAUDE §1.3 关键路径表 / §1.5 不变量 / §2 当前状态（测试 274、分支、最新 commit、下一步）是否与代码实态一致？
5. **gt 铁律 / 分工铁律**等关键不变量表述有无错。

## 相关文件

`AI_agent/{CLAUDE.md, plan.md, decision_log.md}`、`AI_agent/{architecture,capability,proposals,archive}/`、`case_tests/test_baseline/{README.md,index.md,gt/README.md}`。代码实态对照 `src/agent/`、`tests/`（pytest 应 274 绿）。

## 验收

CHANGES REQUESTED / CLOSEABLE；分级 findings（High/Medium/Low）+ 证据 + 建议修复。
