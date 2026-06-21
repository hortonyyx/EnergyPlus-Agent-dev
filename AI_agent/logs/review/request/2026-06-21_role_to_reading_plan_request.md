# Plan review request — role 权威从 1_correction 移到 0_reading（option a，topology-light）

> 审阅方向：Claude 出方案，Codex 审方案（adversarial）。请逐条 agree/disagree/risk/alternative，**不改代码**。背景数据流见同目录 `2026-06-21_role_and_naming_recon.md`（你写的侦察）。**本方案只做 role，命名另开一刀**（用户定 role 先做）。

## 1. 问题（已坐实）

room role 现由 `1_correction` 的 LLM（DeepSeek，**image-blind**，只拿 reading 矢量文本）凭布局先验产出 `Cell.role`（`correction/schema.py:30-37`，默认 "office"）→ 判错（sm21 F1 东南圆桌房=meeting 被判 office）。0_reading **看得见图**（OCR 标签 + 家具线索）却无 role 字段（`reading/schema.py`）。role 下游：`ZoneVolume.role`→`zone_specs` 文本→`4_mep` prompt 派负载（非结构化契约字段，下游改动风险低）。

## 2. 目标 / 守住的边界

1. **role 权威移到看得见图的 0_reading**；**correction 不许发明/更改 role**（代码强制，非仅 prompt）。
2. **守住 reading topology-light 哲学**：reading 不画房间边界、不做区划/分组（那是 correction 的活）。reading 只**观测**："这有个标签/家具线索 → 它是什么房间 + 在图上哪个位置"。
3. role 词表受控、跨阶段一致（命名阶段复用）。
4. 不动 IntakeOutput 契约 / run_pipeline 结构 / 下游 9 subagent。全量 pytest 绿。

## 3. 方案（option a：reading 观测 role，correction 空间指派 + 锁定）

### 3.1 reading 产出 role 观测（topology-light）
- `reading/schema.py` 新增 `RoomLabel`（或 `RoomRoleObservation`）：`{label_text: str(逐字 OCR/家具描述), role: str(受控词表), anchor: [x,y](image-local, 同 stroke/facade 口径), basis: "label"|"furniture"|"ocr", note?: str}`；`ReadingView` 加 `room_labels: list[RoomLabel] = []`。
- reading guide：指示观测可见房间标签/家具线索 → 出 role + anchor；**明确不画房间边界、不分组**。label_text **逐字保留**供 correction/judge 审。
- `validator/checks/reading.py`：轻校验（role ∈ 词表、anchor 在图幅内、label_text 非空）。

### 3.2 correction 消费 + 锁定（correction 不许改 role）
- correction prompt（`pipeline.py:289-306`）改：cells 仍由 correction 划（topology 不变），但**每个 cell 的 role 必须取自落在其内的 reading room_label**；**禁止**凭布局先验发明 role；无 label 命中的 cell → `role="unknown"` + flag，**不准猜**。
- **role 指派放哪**（核心待审，见 §6）：倾向 **correction 后的确定性代码步**——把 reading anchors 经 correction 的 image→world 同一变换映射后，point-in-cell 指派 role（把 DeepSeek 彻底移出 role）。难点=correction 的坐标变换是 LLM 不透明产出、anchors 未必能干净复用同一变换。退路=LLM-assisted 但受约束（prompt 强制取自 label）+ 下条确定性 guard 兜底。
- **确定性 guard（新 check，= "correction 不许改 role" 的强制）**：correction stage 加 check——每个 `Cell.role` 必须可溯源到某 reading room_label（按 anchor-in-cell 或显式 label_id 链）；role 无 reading 背书 → check fail/flag（judge② J1）。这把"不许改"从 prompt 升级为代码门。

### 3.3 role 词表
- 定受控 role 词表（office/meeting/corridor/restroom/stair/lobby/storage/...，含 unknown），单一来源（reading + 命名 + 4_mep 共用），放 config 或常量模块。

### 3.4 下游
- role 仍 `ZoneVolume.role`→`zone_specs`→`4_mep`，**只换来源、不换流向**，下游/MEP 不变。viewer 的 role 发现（`render_geometry_viewer.py:535-557` 按 cell.id==zone 名匹 correction_geometry）暂不受影响（role 仍在 correction_geometry.json 的 cell 上）。

## 4. 迁移 / 兼容
- 老 reading（无 room_labels）：`room_labels` 默认空 → correction 全 cell role="unknown" + flag（不崩）。给迁移说明：旧 anchor case 需补 room_labels 或接受 unknown。
- 现有 fixtures/测试中带 role 的（recon §测试清单：test_geometry_kernel/test_intakeoutput_assembly/test_gt_from_dxf 等）：role 值口径不变（仍 office/corridor），但**来源链**变；按需补 room_labels fixture。

## 5. 验收 / 测试
- 单测：① reading room_labels schema + 校验；② correction role 取自 reading label（命中→该 role）；③ 无 label 命中→unknown+flag；④ correction 自造 role（无背书）→ guard fail。
- 端到端：sm21_anchor 给 GPT54 reading 补 room_labels（圆桌房=meeting）→ 重跑 correction → F1 东南房 role=meeting（修正原 bug）；其余 role 不退化；EP 不破。
- 全量 pytest 绿。

## 6. 请 Codex 重点回答
1. **role 指派该确定性代码步 vs LLM-assisted+guard**？给定 correction 的 image→world 变换不透明，确定性 point-in-cell 可行吗？anchors 能否干净复用同一变换？若不行，LLM-assisted + 确定性 guard 是否够稳？
2. anchor 坐标系：reading image-local → correction world 的对账，有没有干净做法？多图（多层平面）时 anchor 归属哪张图、怎么对到对应 floor 的 cell？
3. **reading 出 role 是否越界**？"观测标签/家具→role+anchor" 还算 topology-light 忠实观测，还是已经踩进 correction 的区划？边界划在哪最稳（如：reading 只出 label_text+anchor、role 推断留 correction？还是 role 也归 reading）？
4. 受控词表放哪、unknown 语义、与 4_mep 现有 office 默认怎么衔接。
5. guard 放 correction check（gate①）还是 judge②（gate②）更合适？无 label 命中是 fail（阻塞）还是 flag（放行+判 judge）？
6. 有没有遗漏的 BLOCKER/MAJOR / 更简洁正确的做法。

---

## v2 — Revised after Codex REWORK（降级 source-linkage，空间确定性 deferred）

裁决：接受 REWORK。核心让步=**当前无 plan-local→world 一等变换**（变换藏在 correction LLM），确定性 anchor-in-cell **现在不可行** → 降级为「显式 source-linkage + 确定性 provenance guard」，空间正确性交 J1 / deferred。

**v2 设计**
1. **reading `RoomRoleObservation`**：`{id(稳定,view 内唯一), view_id/image_label, image_kind(plan), floor_ref(有则结构化), anchor[x,y]+coordinate_frame, anchor_confidence, bbox?(可选), role(canonical), label_text(逐字), basis(label|furniture|ocr), confidence}`。reading 可把**可见且无歧义**的标签归一到 canonical role；**家具推断** basis=furniture + 低置信。**不出** cell/polygon/topology/membership。
2. **correction `Cell.role_source_label_id: str|None`**：非 unknown role 必须引用某 reading 观测；`Cell.role` 必须等于该观测 canonical role；**不许发明**；无 source → `role="unknown"`。
3. **gate① 强制（correction check，live 路 `pipeline.py:425-442/469-482` + replay 路 `validation_run.py:128-137` 都要接）**：INVARIANT fail 当 (a) 非 unknown 无 source_label_id / (b) source 指向不存在观测 / (c) role≠引用观测 canonical role。CROSS_CHECK flag 当 role=unknown。**空间 anchor-in-cell 本期不强制**（无变换）→ 交 J1 flag「spatial binding not mechanically provable」或 defer。
4. **受控词表共享模块**（reading 校验 / correction guard / 命名(后) / MEP 同源 import）：canonical roles + 别名表（`meeting room→meeting`、`entrance lobby→lobby`）。`unknown` = 「无背书观测」**≠ office**。
5. **legacy grandfather（修 BLOCKER#2）**：旧 reading 无 room_labels → role provenance `NOT_APPLICABLE`（跳过该 invariant），保 sm21 golden + 现有 fixtures 绿；另给一次性迁移给 sm21 golden + 关键 fixture 补 room_labels 再开严格。新 draw 走全 guard。
6. **4_mep unknown 策略（修 MAJOR）**：unknown → office 物理默认 + **显式 cross-check flag + text note**（不静默当 office 语义）。

**deferred（backlog）**：plan-local→world 一等可审变换产物 → 启用确定性 anchor-in-cell、把 LLM 彻底移出空间绑定。大件，后做。

**v2 待二审**：(a) source-linkage guard + NOT_APPLICABLE legacy 模式能否保 sm21 baseline + 全量测试绿？(b) **给已偏脆的 DeepSeek correction 输出加 `role_source_label_id` 必填字段，会不会加剧不稳定**？若是，有无更稳做法（如 role 绑定走 correction 后单独一问/或 sidecar 而非塞进主 correction JSON）？(c) 还有无遗漏 BLOCKER。

> 二审结论 APPROVE-WITH-CHANGES：role 绑定**不入主 correction JSON**（会加剧 DeepSeek malformed/retry）→ 用 post-correction sidecar；`role_source_label_id` 可选/仅审计；legacy 靠 reading 是否有 room_labels 特征键检测（非空列表）。无遗留概念 BLOCKER。

---

## v3 — 用户收窄为 phase-1（dispatch-ready；精准绑定/gate/baseline 迁移 deferred 到远期规划）

用户决定收窄：**本期不做显式绑定步 / sidecar / gate① provenance / Cell 新字段 / baseline 重录**。只做「reading 产 role 观测 → 喂 correction 当**输入**」，绑定仍由 correction **隐式**完成（输入从盲先验升级为真·图像观测）。**关键稳健性**：只加 correction prompt 的**输入**，**不动 correction 输出 schema**（Cell 仍 `{id, role, x, y}`）→ 不增 malformed 风险；room_labels 可选默认空 → baseline/legacy 天然安全。

**改动文件**
1. `src/agent/reading/schema.py`：新增 `RoomRoleObservation`：`{id, anchor:[x,y](image-local), role(canonical), label_text(逐字), basis(label|furniture|ocr), confidence?}`；`ReadingView` 加 `room_labels: list[RoomRoleObservation] = []`（**可选默认空**）。topology-light：**不加** cell/polygon/membership/topology 字段。
2. `skills/intake_pipeline/0_reading/guide.md`：指示观测可见标签/家具 → role+anchor；label_text 逐字；家具推断 basis=furniture+低置信；明确不画房间边界/不分组。
3. `src/validator/checks/reading.py`：**仅当 room_labels 存在**时的 per-image 轻校验——role∈词表、anchor 数值且在图幅内、id 唯一、basis∈枚举。**不**做 topology/anchor-in-cell。
4. **新增共享 role 词表模块**（如 `src/agent/roles.py`）：`CANONICAL_ROLES` + `ALIASES`（meeting room→meeting、entrance lobby→lobby）+ `normalize()` helper。reading 校验 import（后续绑定/命名/MEP 复用同源）。
5. `src/agent/pipeline.py` correction prompt（~`289-306`/`326-330`）：把 reading `room_labels` 作为**显式输入**传入 + 指示「**优先采用 room_labels 的图像观测 role**；仅当无观测覆盖某房间才回退布局先验」。**Cell 输出 schema 不变**。
6. 单测：reading schema 带/不带 room_labels 均 round-trip（legacy-safe）；reading 校验（词表/anchor/唯一）；词表 normalize/别名；correction prompt 含 room_labels（轻断言）。

**deferred → 远期规划**：显式绑定 sidecar + `role_source_label_id` + gate① role-provenance INVARIANT + 4_mep unknown 策略 + sm21 baseline 重录 + **plan-local→world 一等变换产物**（确定性 anchor-in-cell 的使能件）。

**验收**：全量 pytest 绿；reading schema 带/不带 room_labels 都解析；correction prompt 含 room_labels（当存在）。**不动 sm21 baseline**。

**v3 待三审（快）**：(a) 可选 room_labels + 仅 prompt 输入，是否真 baseline/legacy/全测试安全（无校验/replay 路径因缺省或空列表触发）？(b) prompt-as-input（不改输出 schema）作为 phase-1 是否够、且不destabilize correction？(c) 这个收窄范围还有无遗留 blocker。
