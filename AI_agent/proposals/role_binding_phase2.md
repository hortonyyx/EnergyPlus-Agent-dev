# Role 绑定 phase-2 —— 确定性空间指派 + provenance 门（DEFERRED · 远期）

> **状态：DEFERRED（用户定"更精准修法"缓做）。** phase-1 已落地（`6.21_RoleObservationsPhase1`：reading 产
> `room_labels` 观测 → 喂 correction 当**输入**，绑定仍由 correction 隐式做）。**本文 = phase-2 的活设计**，
> 记录"把 role→cell 空间指派从 correction LLM 移出、做成确定性可审"的目标态与设计。
>
> **溯源**：本设计原稿在 `logs/reviews/request/2026-06-21_role_to_reading_plan_request.md`（v2/v3 章）+
> `logs/reviews/verdict/2026-06-21_role_to_reading_plan_review.md`（Codex 三审）。2026-07-05 从 logs 抽出归位
> proposals/（logs 那份留作 phase-1 落地的冻结审轨）。**一旦动工，按本文 → Codex 审 → 执行。**

## 1. 目标（phase-1 之上要补的）

phase-1 只让 reading 的 role 观测成为 correction 的**输入**，**空间绑定（哪个观测归哪个 cell）仍藏在
correction LLM 里**、不可机械证明。phase-2 = 把绑定**显式化 + 确定性化 + 可审**，最终把 LLM 彻底移出空间绑定。

守住的边界（承 phase-1）：correction 永 image-blind 纯文本；role 词表单一来源；`unknown` = "无背书观测" **≠ office**。

## 2. 设计（源自 v2，经三审收敛）

1. **reading `RoomRoleObservation`（phase-1 已有雏形，phase-2 补全审计位）**：
   `{id(view 内唯一), view_id/image_label, image_kind(plan), floor_ref?, anchor[x,y]+coordinate_frame,
   anchor_confidence, bbox?, role(canonical), label_text(逐字), basis(label|furniture|ocr), confidence}`。
   reading 只把**可见且无歧义**标签归一到 canonical role；家具推断 basis=furniture + 低置信。**不出**
   cell/polygon/topology/membership。

2. **显式 source-linkage（关键收敛：不入主 correction JSON）**：`role_source_label_id` 走 **post-correction
   sidecar `role_assignments.json`**，**不塞进主 correction 输出**（二审定：塞进去会加剧 DeepSeek malformed/retry）。
   非 unknown role 必须引用某 reading 观测；`Cell.role` 必须等于该观测 canonical role；**不许发明**；无 source →
   `role="unknown"`。`Cell.role_source_label_id` 字段可选 / 仅审计。

3. **gate① role-provenance INVARIANT**（correction check，live 路 `pipeline.py` + replay 路
   `validation_run.py` 都接）：INVARIANT fail 当 (a) 非 unknown 无 source_label_id / (b) source 指向不存在观测 /
   (c) role ≠ 引用观测 canonical role；CROSS_CHECK flag 当 role=unknown。**空间 anchor-in-cell 是否强制取决于 #6。**

4. **legacy grandfather**：旧 reading 无 room_labels（特征键检测：非空列表）→ role provenance `NOT_APPLICABLE`
   跳过该 invariant，保 sm21 golden + 现有 fixtures 绿；一次性迁移给 sm21 golden + 关键 fixture 补 room_labels 再开严格。

5. **4_mep unknown 策略**：unknown → office 物理默认 + **显式 cross-check flag + text note**（不静默当 office 语义）。

6. **大件使能件 = plan-local→world 一等可审变换产物**（deferred 中的 deferred）：有了确定性 plan→world 变换，
   才能做**确定性 anchor-in-cell**（观测 anchor 落哪个 cell 由代码判），把 LLM 彻底移出空间绑定。**没它之前，
   空间正确性只能交 J1 flag「spatial binding not mechanically provable」**。与 reading Phase B（`derive_facade_frame`
   接线 / local→world）同源，宜并轨推进（见 [[reading-improvement-methodology]] / plan.md Phase B）。

## 3. 落地时的验收锚
- 全量 pytest 绿；带/不带 room_labels 都 round-trip（legacy-safe）。
- sm21 baseline 重录（phase-2 动了产物：role_assignments sidecar + 命名可能受 role 影响）。
- gate① role-provenance INVARIANT 三条 fail 条件各有测试；legacy NOT_APPLICABLE 保绿。

## 4. 依赖 / 关联
- 依赖 **plan-local→world 变换**（#6）→ 与 Phase B / `derive_facade_frame` 接线共命运（E/W sign 须先对 gt 校验，
  见 [[derive-facade-frame-unwired-ew-sign-trap]]）。
- 命名确定性化已落地（`6.23_DeterministicNaming`），role 归一器已在；phase-2 的 sidecar 绑定可回填命名的 role 位。
