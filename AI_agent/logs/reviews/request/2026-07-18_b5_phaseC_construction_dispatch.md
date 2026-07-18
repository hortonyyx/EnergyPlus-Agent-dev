# B5 Phase C 施工派工单（⬆全升一档：sol 施工 → Fable 对抗审 → 主控轻门）
2026-07-18 · Opus 主控 · C2 收官关键路径 · B5 施工第 3 批（共 4 Phase）

## 0. 分工 & 流程（用户 07-18 拍：Phase C 全升一档，同 Phase B）
- 施工：**sol**（最高档 GPT，xhigh；B5 spec 作者）；在 Phase A/B 已 CLOSED 的地基上完成整个 Phase C。
- 施工审：**Fable**（最高档 Claude，对抗审；跨厂商，谁写谁不批）。
- 主控轻门：Opus 独立全量 pytest + 亲核 diff/探针。主控全程零技术裁决，交审阶梯。

## 1. 本批范围 = B5 **Phase C** only（§14 Phase C，gates B5-C1..C5）
**绑定施工合同**：`AI_agent/proposals/c2_b5_detail_spec.md`（v3 定稿，1612 行；权威、累计式自包含，按字面施工）。

**上游已 CLOSED（build on top，勿重做）**：
- **Phase A**（`window_sources.py` + `window_host.py` 地基）：source 路由/strict resolver input/ring-free direction facts（8 字段零泄漏）/current-ring binding helper/三容差进 correction.yaml+CoreTolerances+A0/view_manifest floor_ref 连续 1-based/parse·schema draw 拒 producer ref。
- **Phase B**（纯 resolver 主链）：room-boundary interval/source-aware 两支+clamp/conflict/transient·final Vg 每轮按当前 ring 重派生时序/B2b dry resolver 替换/§3.2 步骤 9 真实预序列化 identity（`PreparedCandidateIdentity`，**禁占位 64-hex** 已落）/Va evidence+negative decisions/final commit·audit·provenance。**trusted-negative 双向已在盘**（8 条件、reference-positive 排除）。

Phase C 施工项（§14 Phase C 原文 + 对应正文节）：
- **`SegmentLine2D` 与 `window_verts_on_line`**（§6.5）：低层顶点函数，替换现 `_window_verts`；旧 cardinal 函数**只重命名** `_legacy_cardinal_window_verts` 供 legacy attach，原模块原位置保留（§3.3）。
- **proof-aware build / attach**（§8）：`build_geometry(..., window_host_proof)` + `attach_windows_v3()` 真实 parent Surface 候选与几何 realization。
- **correction / kernel validators**（§10.1/§10.2）：`check_window_host_resolution` + kernel `window_parent_binding` 两层硬门。
- **versioned built / spec serializer**（§8.3/§10.4）：`geometry_contract` legacy vs `c2_b5_v1`；building JSON/fenestration spec 携带 source/segment/proof digest；legacy byte-parity 必须由 version-gated serializer **测试证明后**才承诺。
- **B4b official contract dispatch / independent host score**（§10.5）：judge 先验六件套 B5 artifact identity → 再独立重算评分关系（不信 proof 自证）；禁 official temporary binding。

**不越界**：writer 独立重算全量（§9.1）/accepted·integrated loader（§9.3）/E4 rebind（§9.4）/legacy 封口 + v1v2 byte gates 全量（§3.3 + §13.6 全量 + §13.7 封口）归 **Phase D**。Phase C 落 line 几何 + proof-aware build + 四同步 + versioned serializer（byte-parity 语义证明可先落）。

## 2. ⚠️ 高危面（施工审必往死里打，先做对）
按稳定优先级与 spec 逐条：
- **`window_verts_on_line` 禁 facade/x/y 分支**（§6.5）：函数体只做 `point_at(t)` + z + `_orient(normal)`；**禁 `_facade_axis()` 决定顶点**（§1）。writer/loader/build 均从 line+t+z+normal **fresh 重算**四点，**不把 record 四点喂回 helper 自证**。C2 `FacadeSegment` schema 仍拒斜线（LINE-5）；diagonal `SegmentLine2D` helper 正例只证明接口可扩、**不扩大 C2 capability**（§12.4）。
- **负向轴不许 sort 破坏方向**（§6.5 + LINE-2/3/7）：p1→p2 沿负 x/负 y 时 world `lo` 点可能是第二点；**禁 `sorted(points)`**；record 按世界升序写回但 t 仍按 p1→p2 = `resolver_output_tampered`，writer 与 loader 均拒（LINE-7）。
- **parent 候选恰一，零/多是 blocking invariant 非 note+skip**（§8.2#7）：用分量残差 `<= plane epsilon` 验 normal，**不用旧 `dot>0.9` 宽门**（#5）；fragmented wall 若无单一 Surface 完整含窗 span=跨 built seam **必拒，不自动切双窗**（§8.2 末 + PARENT-4）。
- **不按中心点猜**（§7.2 + GEO-2/3）：禁 `min(distance(window_center))`、room polygon `contains(center)`、parent `min(center_distance)`、先截到 cell bbox 再宣称唯一、id 破平局。测试用两段/两 room 对称包围 center 强制拒绝。
- **serializer legacy byte-parity 必须版本门测试证明**（§8.3 末）：**不得仅因 dataclass 加 defaults 就宣称 legacy byte equality**；version-gated serializer 测试证明前，测试名/文案只能写 semantic/geometry equality（§13.7）。
- **四同步不得软接线**（§6.6 末 + §10）：validator fresh 重算硬门 / kernel 三集合一一相等 + built verts 与 fresh recompute 逐值相等 / specs 从 built fresh 生成**不读 LLM 抄写 digest** / judge 先验六件套 identity 再独立重算**不信 proof 自证** + 禁 temporary binding + host score 独立从 product cell boundary+segment+room 重算。**禁「先接受 output、以后补 sidecar/spec」**。
- **production correction 模块禁 import judge**（§10.5#7 + B5-C5）；judge 侧可 import production helper 做 parity，但反向零 import。
- **broad-except 禁令**（§1）：§6.6 的窄捕获 `FacadeApplicabilityInvariantError`/`WindowDirectionBindingError` 后**必转 typed reject**，这是唯一允许的窄捕获；resolver/writer/loader/build 无 fail-open。
- **shipped-untested = 未交付**（§13 首行 + §14 末）：**任何安全拒绝分支缺测试锁视为未交付**，不得用现有总绿数代替。fixture 期望 record/hash/verts 必须手写字面量或冻结文件，**禁调用被测 resolver/`window_verts_on_line`/hash helper 生成 expected 再自比**；禁 `x!=x` 恒真伪检查。

## 3. 测试（§14 gate B5-C1..C5 + §13 对应表，逐 gate 落点）
- `B5-C1-parent-unique` → §13.4 **PARENT-1..5**（同 family 两墙选唯一 / 零 parent BLOCK / 两 parent multiple BLOCK / 半 span 不切双窗 / normal 反向 BLOCK）。
- `B5-C2-line-parameterized` → §13.3 **LINE-1/4/6/8**（p1→p2 t 与 endpoints 手写 / diagonal 四点手写+normal / zero·逆 t·越界 t 三拒 / wire normal 非法三拒）。
- `B5-C3-negative-axis-locks` → §13.3 **LINE-2/3/5/7**（负 x / 负 y / diagonal FacadeSegment 进 C2 拒 / 负轴世界升序写回 writer·loader 均拒）。
- `B5-C4-validator-audit-specs-judge-sync` → §13.4 **SYNC-1/2 + JUDGE-1/2/3** + §13.2 **GEO-1..12**（segment/room/clamp conflict 全轴，含弃 cell bbox GEO-2、cross-segment GEO-3、endpoint clamp/overrun GEO-6/7、cross-room GEO-9P/9E、min-edge/full-parent GEO-12）。
- `B5-C5-production-import-judge-zero` → production correction source scan 零 judge import 断言。
- **serializer/build 相关 anti-tamper**（§13.6 中触及 build/serializer/specs 的项，如 spec parent/verts 篡改 SYNC-2、built verts 篡改）先落本批；§13.6 writer 独立重算全量（#16/#17 对偶探针）与 §13.7 v1/v2 byte 封口归 Phase D。
- v1/v2 legacy 语义不变（§13.7 相关行的 semantic equality）；version-gated serializer 落地后按 §8.3 承诺 byte equality。

## 4. 交付纪律 & 回报
- 只跑 targeted（codex ~30s / idle-timeout 杀长进程，**全量 = 主控轻门唯一权威**）。
- 产出后回报：改了哪些文件（§12.1/12.2 对照）+ 五 gate（C1..C5）测试落点 + 触及的 §13 表格清单 + targeted 结果 + **诚实标注做完/未完/存疑**。
- **做不完如实报未完成全链，别伪实现占位**（B4b Phase B 藏假绿教训 vs Phase D 诚实部分交付获正评的对比）。安全拒绝分支若未锁齐，明确列出，不得声称交付。
