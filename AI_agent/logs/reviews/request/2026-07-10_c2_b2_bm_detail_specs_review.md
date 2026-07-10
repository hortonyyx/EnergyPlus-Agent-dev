# 审阅请求：C2 B2 + B-M 细稿对抗审（sol · max）

- **对象**：
  1. `AI_agent/proposals/c2_b2_detail_spec.md`（B2 细稿 v1：schema v3 冻结 + per-floor footprint + floor_footprint helper + 双路径 finalize）
  2. `AI_agent/proposals/c2_bm_view_manifest_spec.md`（B-M 细稿 v1：受信视图清单 schema + generator）
- **上位**：`AI_agent/proposals/c2_full_unlock_design.md` **v2.2 定稿**（三轮审 21/21 闭合；细稿与定稿冲突处必须显式指出并按定稿裁）；基底 `AI_agent/proposals/c2_orthogonal_polygon_design.md`（D1–D10）。
- **细稿开工门核对**（v2.2 版本史注）：B2 = 闭 B-01（v3 精确类型不留二选一）/B-02（run_stage 不传 envelope，双路径同一 finalize）；B-M = **C-03**（负证据前提机读：类型化 negative_evidence_capable_claims + coverage/completeness 来源 + reader 不得改 denominator）与 **C-04**（direction_semantics 守卫条件、Vg/Va 分工不被 B-M 侵入）落地充分性。
- **审什么（对抗性）**：
  - **A. 设计对抗**：v3 类型定案是否仍留隐性二选一；单类+版本门验证器 vs extra="forbid" 的语义等价性漏洞（嵌套 extras、adapter 逃逸）；footprint 产权"correction 声明、禁 union(cells) 派生"是否真解 B3 自证循环；Floor.id/Window.floor 语义分叉（B2 §9#2）；生产发射口径（v3 随 B5 发射）是否制造 B3/Vg 的隐性依赖倒挂；B-M "staging 不拷贝"是否漏掉 reader 合法需要清单信息的场景；负证据常量表两行（plan/elevation claims）是否会在 sm26 内壁窗用例上判错。
  - **B. 落地对账**：细稿引用的 file:line 现实性（以 `7422f42` 为准）；helper 十路贯穿表是否漏消费点（grep 附录见下）；finalize 提取是否破坏 flow 外置 gate①/attempts 语义（run_stage.py:157-190）；flow 侧 envelope 生效的既有测试爆破面；B-M 接线点（run_stage/validate_case/run_manifest/gate① 新 check）与现编排的冲突；零 golden 承诺可信度（570 绿 + 9 strict xfail）。
  - **C. 开放问题裁定**：B2 §9 两条、B-M §7 两条，给出明确裁决。
- **产出**：verdict 写 `AI_agent/logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review.md`，结论档 = APPROVE / APPROVE-WITH-CHANGES / REWORK（两稿分别给档）+ 编号 findings（严重度 BLOCKER/HIGH/MEDIUM/LOW + 建议修法 + 证据 file:line）。**只写该 verdict 文件，不改任何其他文件。**
- **附录：footprint_x/footprint_y 全部消费点（2026-07-10 grep，50 处/10 文件）**：
  - src/agent/correction/deterministic.py:599,600,683,686,778,779,798,799,800
  - src/agent/correction/geometry_validator.py:85
  - src/agent/correction/facade.py:14-17,72,73,82,83
  - src/agent/correction/schema.py:75,76
  - src/agent/correction/envelope.py:270,271
  - src/agent/geometry/modelling.py:150-154,458
  - src/agent/judge/correction_score.py:237,238,246,248,272,273
  - src/validator/checks/correction.py:188,189,192,193,277,278,339,340
  - scripts/tool_scripts/render_elevation_windows.py:44,45
  - scripts/tool_scripts/render_corrected_geometry.py:70,71,115,116,186,187
