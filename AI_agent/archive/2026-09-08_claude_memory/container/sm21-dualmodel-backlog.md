---
name: sm21-dualmodel-backlog
description: 2026-06-21 双模型轮后用户定的下轮 backlog（修复/流程/质量/命名）
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2ee0e63e-a274-4690-a06a-829360d44eb7
---

2026-06-21 sm21 双模型轮后，用户定的待办（"先记录、下轮再修"）。**Why**: 这些是 GPT-5.4 跑测暴露的真问题 + 架构归属错位。**How to apply**: 下轮按此修。

**现在已查清（本轮做了）**：
1. 面数 112 vs 100 根因 = 跨层走廊错位 + 核无跨层对齐（详见 [[sm21-dualmodel-round-2026-06-21]]）。
2. viewer 确认是切配后产物（`materialize_kernel_geometry` 已 build 全部分面），现写在 `2_modelling/geometry_viewer.html`。

**下轮修**：
1. ✅ **核加跨层内墙对齐（2026-06-21 完成 `6.21_CrossFloorWallAlign`）**：根因修正=轴线图本就全楼共享，真因是同层/跨层共用 jitter=0.05、走廊跨层差恰 0.10 卡容差缝。修=`deterministic.py` 新增 `_reconcile_cross_floor`（per-floor identity→footprint 硬锚→mutual-nearest 跨层匹配+歧义 flag→provenance-aware sliver，`cross_floor_align_tol=0.11`）。sm21 112→100 面、走廊对齐 y[3.15,4.85]。Codex 双审+四重验证。详 [[codex-execution-protocol]]。
2. ✅ **viewer 单独放人工文件夹（2026-06-21 `6.21_ViewerToManualReview`）**：`2_modelling/` → `<run>/manual_review/geometry_viewer.html`（run_stage 输出改路 + 补 role 着色、record_baseline 文档 + .gitignore 同步；pytest 288）。后续接编辑回写。
3. **房间类型(role)移回 reading — ✅ phase-1（2026-06-21 `6.21_RoleObservationsPhase1`，测试 288）**：reading 加可选 `room_labels`(RoomRoleObservation,topology-light) + 共享词表 `src/agent/roles.py` + correction prompt 把 room_labels 当输入优先采用；绑定仍 correction 隐式做(输入升级)。Codex 三轮双审 + 大节点全面审。**phase-2 远期(用户定"更精准修法缓做")**=确定性绑定 sidecar + `Cell.role_source_label_id` + gate① provenance INVARIANT + 4_mep unknown 策略 + sm21 baseline 重录 + **plan→world 一等可审变换产物**(确定性 anchor-in-cell 使能件)。设计全在 `logs/review/.../2026-06-21_role_to_reading_plan_*` + plan.md N1b。**另：N2(South 2F 窗 x)经诊断已关闭=不复现、06-16 Opus 旧轮产物**。
4. **命名确定性化**：现在 zone cell id(`F1_office_01`) 由 DeepSeek 出 → 各 run 口径乱(`R_1F_Cor` vs `F1_corridor`)；surface/window 名由内核派生。改成**代码确定性生成**，约定 **楼层-类型-方位-序号**（序号含方位，如 SW/NE），用户倾向 GPT 这版表述。
5. **查 Sonnet 识图为何变差**：Sonnet 之前出过最忠实重绘，本轮 0/2（内墙↔尺寸刻度混淆、门当窗）。
6. **查平面识别为何下降**：现在立面很准、平面降了；以前相反(平面准/立面弱)。
7. **主控汇报优化**：一堆零散 json 该分门别类收好；用户只看报告、不直接看 json；要给**最终报告格式+内容的优化建议**。

关联 [[sm21-dualmodel-round-2026-06-21]] [[editable-geometry-confirmation-vision]]（viewer 编辑回写）[[recognition-modeling-capability]]。
