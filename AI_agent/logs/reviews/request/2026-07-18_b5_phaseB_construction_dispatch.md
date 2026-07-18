# B5 Phase B 施工派工单（⬆全升一档：sol 施工 → Fable 对抗审 → 主控轻门）
2026-07-18 · Opus 主控 · C2 收官关键路径 · B5 施工第 2 批（共 4 Phase）· 本轮收工前完成

## 0. 分工 & 流程（用户 07-18 拍：Phase B 全升一档）
- **原 terra 施工两趟只交诚实部分增量、没啃下 B2b/finalize/身份接线** → 用户拍**整批升一档**。
- 施工：**sol**（最高档 GPT，xhigh；B5 spec 作者，续其 spec 线程带全设计上下文）；接住 terra 已建的 `resolve_window_hosts` core 骨架、完成整个 Phase B。
- 施工审：**Fable**（最高档 Claude，对抗审；未写 spec 实现，跨厂商）。
- 主控轻门：Opus 独立全量 pytest + 亲核。谁写谁不批（sol 写 → Fable 审）。

## 1. 本批范围 = B5 **Phase B** only（§14 Phase B，gates B5-B1..B7）
**绑定施工合同**：`AI_agent/proposals/c2_b5_detail_spec.md`（v3 定稿）。**上游 = Phase A 已 CLOSED**（`window_sources.py`/`window_host.py` 的 wire + ring-free direction facts + current-ring binding helper + 三容差 + draw 拒例已在盘）。

Phase B 施工项（§14 Phase B 原文）：
- room-boundary interval（§6.4）；
- **source-aware 两支 + clamp/conflict**（§6.2/6.3/6.4 + §7）：plan 来源在**全部**外边界段（含 hidden）挂、hidden 不阻挂；elevation 来源**只在 visible** 段挂、完整 span 落**唯一** room interval 才补 room；**段 id≠room**；
- **transient/final Vg + 每轮 binding 按当前 ring 重派生时序**（§3.2 步骤 5-9 + §4.5 helper 在 dry-pre/dry-post/final 三处各按当轮 ring 调）；
- **B2b dry resolver 替换**（§3.2 步骤 5 一次性 dry_geom + B2b post-transform 重解析）；
- **output/feature 预序列化真实 identity + Va evidence/negative decisions**（§3.2 步骤 9 用与 writer 同一 serializer 预序列化取真实 hash 封 `PreparedCandidateIdentity`；§6.6 Va negative；**禁占位 64-hex**，即原 B5-R1-04 时序洞的落地）；
- final commit/audit/provenance（§5.1/§5.3）。

**不越界**：真实 parent Surface build / `window_verts_on_line` / validator·specs·judge 四同步（§8/§10）归 Phase C；writer 独立重算 / loader / E4 rebind / legacy 封口（§9.1 writer/§9.3/§9.4/§3.3）归 Phase D。Phase B 落 resolver 主链 + 时序 + Va evidence identity 地基。

## 2. ⚠️ 高危面（施工审必往死里打，先做对）
- **trusted-negative 不许过火**（B4b Phase C 刚栽这里一个 MAJOR）：negative 证据只在**另一通道对该 span coverage 完整 且 manifest 承诺该图种完整表达 openings** 时才构成 conflict；遮挡/hidden/裁切/无 completeness 只记 `uncorroborated`，**不删窗、不判 conflict**；negative_inputs 必须**排除 reference 携 GT-positive 的源**。§7.3 逐条落，配负轴测试（缺 completeness→不 conflict / reference-positive 源→不算 negative / 遮挡→uncorroborated）。
- **不按中心点猜**（§7.2）：跨段/零或多候选/room 不符 → typed conflict，绝不落窗中心破局。
- **信任根身份**：Va evidence ledger 的 output/feature hash 必须等于步骤 9 真实预序列化 hash（**禁占位**），Phase D writer 复算会逐字节比对——本批先把真实 hash 封进去。

## 3. 测试（§14 gate B5-B1..B7 + §13 对应行 + 接 Phase A 延后项）
逐 gate：`B5-B1-plan-hidden-host` / `B2-elevation-visible-room` / `B3-no-center-guess` / `B4-b2b-host-parity` / `B5-negative-proof` / `B6-resolver-totality` / `B7-va-artifact-identity`。
- **接住 Phase A 显式登记延后到 Phase B 的项**：`BIND-5/6`（dry-pre/dry-post mapper integration 的 ring_invalid/incompatible）、`WindowEvidenceDecisionV1`/`WindowEvidenceLedgerV1` 的 decision/aggregate/content hash 拒例、§13.2 segment/room/clamp conflict、§13.5 trusted negative。
- 所有安全拒绝分支独立锁、负轴齐（缺一条=未交付）；禁自指假绿；禁 fail-open/broad-except；v1/v2 legacy 行为不变。

## 4. 全量归主控 / 交付回报
只跑 targeted（codex ~30s 杀长进程，全量=主控轻门唯一权威）。产出后回：改了哪些文件（§12 对照）+ 七 gate 测试落点 + 接住的 Phase-A 延后项清单 + targeted 结果 + **诚实标注做完/未完/存疑**（做不完如实报未完成全链，别伪实现占位——B4b Phase B 教训）。
