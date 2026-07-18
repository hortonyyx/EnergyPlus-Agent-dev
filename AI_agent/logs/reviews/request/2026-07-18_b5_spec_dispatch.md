# B5 细稿出稿委托单（sol 出稿 → Fable 对抗审）
2026-07-18 · Opus 主控 · C2 收官关键路径

> **流程（用户 07-18 定，交叉翻转）**：**sol 出稿**（GPT 侧，最高档）→ **Fable 对抗审**（Claude 侧，最高档）→ sol 按 findings 返修 → 迭代**至 Fable APPROVE 为止**。**主控不做技术裁决**：findings 采纳/闭合由 sol↔Fable 交叉收敛，Fable 点头 = 终止条件；主控只编排/传话/记账。谁写谁不批（sol 写→Fable 批，跨厂商）成立。

## 0. 任务
出 **B5 施工细稿**（窗挂载 / 宿主解析 resolver），施工-ready、**累计式自包含**（禁"vN 不变"引用旧正文，每版全文累计——`spec-must-be-cumulative` 教训 BLOCKER 史）。目标 = 让非方形（L 形）的窗**确定性地挂到墙段**、几何 clamp 到段真实区间，为 C2 收官 case **sm25-L** 端到端铺路（sm25-L 图已就绪）。

## 1. 上游状态（全 CLOSED，可直接依赖）
- **B2**：strict v3 schema 子类族——`Floor.id`(immutable 主键)+`Floor.footprint`(typed exterior ring)；`FacadeSegment` typed = `id/floor_id/facade_family/p1/p2/normal/world_along_interval/depth/visible_intervals/source_footprint_fingerprint`；`Window.facade_segment_id`+field-level evidence/provenance map（**段 ref 不取代 room**）；`floor_footprint` 单一 helper 贯穿 core/validator/naming/audit/render/judge；双路径同一 correction-finalize；矩形显式 legacy 分支。
- **B4b（A–D + REC-A–D 全收官）**：段级 plan/elevation scorer；per-claim applicability 判卷；sidecar v8 全身份；**Va = 唯一 applicability 引擎**（reference / product / absence 三 ledger）。
- **Vg**：分段 + 可见性 gt-blind 纯函数（`FacadeSegment.visible_intervals` 是其派生量，非独立真值）。
- **B-M**：受信视图清单 manifest（`view_kind` / `view_direction`+来源 / `direction_semantics` / `negative_evidence_capable_claims` + 可信 coverage region）。
- **几何造面（墙 / 楼板 / 屋顶）已由 B1/B2/B2b 落地**；B5 只做**窗 → 段挂载**，不碰造面。

## 2. B5 范围（设计稿 §122 + §E1'.2）
resolver 主链：
1. 验 `floor / room / segment` 一致；
2. clamp 窗到**段真实区间**（弃 cell bbox）；
3. parent wall 同时满足 `room` + 段平面/法向 + **完整 span**；
4. `_window_verts` 按宿主墙 **p1→p2 参数化**（接口按线段；C2 只实现轴向——**接口须为 C4 斜交预埋，不得烤死轴对齐**，不变量 #6）；
5. `validator / audit / specs / judge` 四处同步；
6. 无 `facade_segment_id` ref 的 v1/v2 走**严格 legacy path**（行为不变，验收三层①）。

**source-aware 宿主解析两支（§E1'.2，硬要求）**：
- **平面来源窗**：在**全部**外边界段（含 hidden）上按 room boundary + 完整 span **唯一**解析——**hidden 段不阻止挂段**（有平面证据的窗必拿到段归属 + 宿主墙）；可见性只决定立面属性（z 等）**能否计分**，不决定实体挂不挂。
- **立面来源窗**：只在该视图 **visible** 段候选中解析；完整 span 落入**唯一** room-boundary interval 才补 room（一段可跨多 room，**段 id 不替代 room**）；跨 room 缝 / 零或多候选 → A3 / interactive。
- **conflict 纪律**：跨段边界 / 零或多候选 / room 不符 → conflict，**绝不按窗中心点猜**；负证据须满足 §E1'.2 前提（另一通道对该位置 coverage 完整 **且** 图种承诺完整表达 openings）才算 conflict，否则只是"无独立佐证"。

## 3. 北极星 & 硬约束（非协商）
1. **分工铁律**：B5 = correction **确定性核**（代码做所有几何）；LLM 不参与挂载判定。
2. **信任根纪律**（C2 连续 8 批头号 MAJOR，B-M/Vg/B-O/Va/PhaseA 信任根洞第 1–5 现）：resolver 写出的 `facade_segment_id` + clamped verts + 任何 hash/digest **必须代码重算、不信自报**；篡改必须被 verify/门拒；**禁 fail-open**（except-Exception 吞、proxy 门放行 = 前科）。
3. **复杂度可扩展铁律（#6）**：`_window_verts` 接口按 per-segment 线段参数化，轴向只是当前实现；**禁把"轴对齐 / 共底面盒子"烤死到无法松动**。
4. **段 id ≠ room**；**不按中心点猜**。

## 4. 已知坑
**`ElevationViewBindingV1` 同名两型**（REC-C 揪出）：`gt_manifest` 版 15 字段 vs `facade_applicability`(Va) 版 13 字段。B5 若 import，**认准 Va 那个**，别串型。

## 5. 纪律（施工审会照打，先写进稿）
- **shipped-untested = 连续 8 批头号 MAJOR**：所有分支——尤其 source-aware 两支 / conflict 路径 / 负证据 / legacy path——**必须有测试锁**，负轴（拒例）不得缺。
- **禁恒真式自检**（Va `_relevant_negative` family 过滤 / PhaseC F1 `x!=x` 恒 False 前科）；冻结向量硬编码字面量、**禁自指**（fixture 用被测函数自产再自比 = 假绿）。
- **安全拒绝分支必须有测试锁**（B2 F1：拒绝条件被替换非扩展、707 绿不报警的教训）。
- **验收三层（§128）**：①v1/v2 built geometry/specs/audit 行为不变（语义等价为准）；②byte 等价只在 version-gated serializer(exclude defaults) 后承诺，否则文案一律"semantic/geometry equality"；③新容差（clamp 端点 / span epsilon 等）各自**命名进 `correction.yaml` + A0**，禁复用线性 min-edge、禁裸常数。
- **累计式自包含**。

## 6. 参考（权威源，自读，勿凭转述）
- 设计稿 `proposals/c2_full_unlock_design.md`：§E1'（尤 §E1'.2 两支）、§E2'（证据×属性矩阵）、§122 B5 行、§128 验收三层。
- 已定稿细稿范式：`proposals/c2_b4b_detail_spec.md`（段级 scorer / Va 接口）、`proposals/c2_b2_detail_spec.md`（v3 schema / finalize / legacy 分支）。
- 现码：`src/agent/correction/`（schema / deterministic / finalize）、`src/agent/geometry/`（定位 `_window_verts` 当前实现）、Va = `src/agent/correction/facade_applicability.py`。

## 7. 审阅需求（交 Fable 对抗审重点核）
①source-aware 两支判据严丝合缝否（尤其"hidden 段不阻挂载" vs "立面来源只在 visible 解析"的边界）；②信任根（clamp / 挂载写出物防篡改）；③conflict / 负证据前提可机读、不静默否；④`_window_verts` 线段接口是否真为 C4 预埋（非轴向烤死）；⑤v1/v2 legacy path 行为不变的锁；⑥所有分支测试锁齐、无恒真自检 / 自指假绿。
