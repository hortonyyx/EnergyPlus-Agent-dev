---
name: skills-lib-clean-spec-policy
description: skills/intake_pipeline/（原 energyplus_mcp_twostep，2026-06-10 改名）是英文的、纯当前版本 spec —— 不放时间戳/版本变更日志/决策与 AI_agent 文档交叉引用
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2ad6b8e4-c212-47ec-aeba-ff73a103bfc5
---

`skills/intake_pipeline/`（0–5 阶段 intake skill 库，**2026-06-10 从 `energyplus_mcp_twostep/` 改名**；`energyplus_mcp/` 单步法旧库已退役、归档到 Skill_history）是「规范的、迭代的、当前最新版本」spec。用户拍板的风格约束（2026-05-25）：

- **全英文**（OCR 反例里故意保留的中文如 `"办公室"` 除外——那是"不要翻译"的示范）
- **不放时间戳 / 版本变更日志 / 版本号**（标题别写 `v1.3`，别留 `> v1.x (date) ...` changelog 块，别写 inline `(v1.3)` / `v1.3 起`）
- **不放决策相关内容**：别引用 AI_agent 决策文档（`floorplan_redraw_strategy.md §10`、`plan.md B1.5` 等），别写"某 case 首跑暴露规则漏洞所以加了 X"这类 rationale-history
- **保留**：操作规则本身 + 其内联物理/逻辑依据（如"EP 墙是连续边界面所以补门"）、worked example、文档内部 §N 交叉引用
- **操作启动 prompt 不放 skill 库**（2026-05-28 用户拍板）：phase1 / phase2 的「粘进新会话的启动 prompt」（原 `phase1/prompt_template.md` / `phase2/prompt_template.md`）归操作指南整段内联，skill 库只留知识 spec（`phase1/guide.md` + `reading_guide.md` + `pen_library.md` + `phase2/rules.md`）。**Why**：用户"不要弄到两个地方"——启动 prompt 是操作脚手架，归操作指南，避免与跑流程漂移。**2026-05-29 更新落点**：临时文件 `new_case_guide_twostep.md` 已删（guide 完全并轨），phase1/phase2 启动 prompt 现在 [AI_agent/guides/new_case_guide.md](AI_agent/guides/new_case_guide.md) **附录 A / B**；`run_phase2_deepseek.py` 注释 / skill README 引用已重指主指南附录。

**Why**：skills 库要做干净的 HEAD spec；版本/日期/决策史归 git history + `AI_agent/`（floorplan_redraw_strategy.md §10 / plan.md / CLAUDE.md）。我之前给 phase1_vector_schema 加 v1.3 changelog 头被纠正。

**How to apply**：动这个目录时只反映"当前规则是什么"，把"为什么这么改 / 哪天改的 / 哪个 case 触发"写进 AI_agent 文档或 commit message，不要写进 skill 文件。同目录的 `README.md` 已据此去掉「当前版本号」「演进流程 changelog」「未来计划」等节。备份仍按 [[CLAUDE.md]] §6#5 进 `Skill_history/`。`energyplus_mcp/`（单步法旧库，中文）已于 2026-06-10 退役归档（legacy 单步 intake 路径同时停用）。skill 库现 0–5 阶段布局（0_reading/1_correction/2_modelling/3_split_pairing/4_mep/5_intakeoutput，code 阶段 2/3/5 是 `spec.md` code-of-spec、非 prompt）。相关见 [[pipeline-0-5-refactor-status]]、[[twostep-poc-v2-status]]。
