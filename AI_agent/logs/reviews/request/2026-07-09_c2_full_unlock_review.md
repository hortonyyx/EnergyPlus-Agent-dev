# 审阅请求：C2 收官设计（c2_full_unlock_design.md）双路审

- **对象**：`AI_agent/proposals/c2_full_unlock_design.md`（2026-07-09 Fable5 出稿）
- **基底**：`AI_agent/proposals/c2_orthogonal_polygon_design.md`（D1–D10，2026-07-06 Codex 定案）——增补稿与定案冲突处必须显式指出
- **背景**：`AI_agent/architecture/pipeline_stage_contracts.md` §5.6–5.8、`AI_agent/capability/pipeline_0-5_capability_upgrade_suggestions.md` §C2
- **两路分工**（今日 Claude 双子会话替代 Codex 首审，Codex 明日复核）：
  - **A 路（设计对抗审）**：E1 可见性模型的几何正确性与边界情形（部分遮挡/同深共线/台阶相邻/虚线画被遮挡构件）、E1.4 对 D10#2 的修订是否成立（确定性窗归翼 vs A3 仲裁）、E2 政策的诚实性漏洞、E3 与既有 envelope 权威规则的冲突。
  - **B 路（落地可行性审）**：设计假设 vs 代码现实逐条对账——schema（correction/schema.py、reading/schema.py Facade Literal）、内核（modelling/split_pairing/capability.py）、envelope.py、判卷（score_*、render_grade、judge_grade_model.md §8）、gt（gt_from_dxf、gt schema）；批次序 B2→B6 的依赖是否真实成立；工作量分档（哪批可机械执行、哪批要再出细稿）。
- **产出**：各写 verdict 至 `AI_agent/logs/reviews/verdict/2026-07-09_c2_full_unlock_review_{A|B}.md`，结论档 = APPROVE / APPROVE-WITH-CHANGES / REWORK + 编号 findings（严重度 + 建议修法）。
