---
name: reading-evolution-and-phase-a
description: reading 病根=prose↔gate落差+算术在VLM；三档演进路线；Phase A证据门+A8下游闭合已落地；item④阶段1-5迁移缺口首批已修；Phase B仍待启
metadata: 
  node_type: memory
  type: project
  originSessionId: b6c2154b-324a-4b66-b4af-0a1916dd876d
---

2026-06-30 reading 实测 + 演进方案 + Phase A 落地（`6.30_ReadingEvidenceGateHardening`，详 decision_log §A / plan.md N1g）。**⚠️ 2026-07-03：reading 提升唯一管理文档 = `AI_agent/capability/reading_improvement_methodology.md`**（原 `proposals/reading_evolution_dual_channel_cv.md` 已折入并删；文档职责划分=proposal 纯设想/未动工、动工后进 capability 不两处并存）。演进/诊断/Phase A-C/CV 工具箱方法论/决策全在那一处，见 [[reading-cv-toolkit-methodology]]。

**实测**：冷启 Sonnet×2 用恢复后脚手架（[[reading-scaffold-restore-policy]] 的 `6.27` 全恢复版）重读 sm21 + `score_reading_vs_gt`：**r1 复现 sm21_pre 地板（墙9/9·过度分割0·2f竖墙0.0m）/ r2 墙9/9·过度分割+4·窗12/15**。结论=**墙/结构稳达回归地板；过度分割+窗位仍 run 方差/模型主导、非 prose 可治**（同脚手架同图 r1 干净 r2+4）。

**病根（三方收敛：Claude 实测 + 外部模型可恢复性规则 + Codex 架构回归审）**：
1. **prose↔gate 执行落差**——reading docs 要双通道证据，但 schema/validator 把缺失/弱证据当 clean 放行 → correction 救场、"pipeline 绿"掩"reading 弱"。
2. **算术在 VLM**——reading 纯尺寸链累加算坐标、像素 anchor 空着，违反 0-5"LLM 感知/代码算几何"；扒 attempt 坐实 r2 伪墙落窗 jamb 处 `prov=seen`（再证伪"dimension_derived=坏机制"）。

**关键判断（写进方案）**：
- 对 VLM"按像素算"**最不可靠**（像素定位是弱项）；对立轴=**感知 vs 计算**非像素 vs 尺寸链；像素忠实正解=经典 CV（DXF 数据工厂起手），非逼 VLM。
- **可恢复性规则**（外部模型，采纳为档位判据）：correction 能否从此模型错恢复？能→弱模型/VLM 够；不能→才上更可靠抽取器。尺寸是唯一不可恢复，但——
- **闭合反转**（Claude）：`dimension_chain_closure` 早写好、chain_id optional 被跳过；强制 chain_id+完整性即把 silent misread 变**可检测** → **闭合门优先、OCR 暂不起**。
- **用户定：先不上 CV**（自训泛化差、reading 要吃各风格图），维护脚手架为主。

**三档路线**：A 证据门硬化（本轮✅）/ B 双通道+算术下沉（尺寸驱动重建·Shapely polygonize·接线 derive_facade_frame）/ C OCR+CV（DXF→逐层掩膜数据工厂起手）。

**Phase A 已落地**（两批 Codex 执行 + Claude 全面审，365 绿）：`RunPolicy.run_profile`（exploratory|dev|golden|regression）+ `EVIDENCE_CHECK_IDS` 机器可读 allowlist + 四信号（syntax-valid/evidence-clean/j0-semantic-clean/pipeline-recovered）+ 链完整性闭合 + dimension_derived refs 门 + dimensioned manifest 门（`case_metadata.py` 不 import gt）+ provenance 升级 + raw-presence sidecar + `partition_on_window_jamb` advisory + E/W sign 翻正。**flag/block 裁定**=syntax 永 block / evidence exploratory=flag·golden=block / **legacy_migrated 祖父化**（2 个 legacy golden 不被打 block）。**A8 defer**（触 correction 契约）。reading/correction schema 契约未动。

**E/W sign（接 [[derive-facade-frame-unwired-ew-sign-trap]]）**：已裁定 East+1/West−1（A1 doc + old phase1 + gt-validated 活口径为准）；facade.py 原 East−1/West+1 **已 test-first 翻正**（锚 sm21 gt East-F2/West-F2 窗世界 x）。**facade.py 仍未接线**（仅测试引用），翻常量安全；真接线进核仍归 Phase B。

**A8 已落地（2026-07-01 `A8_CorrectionEvidenceRouting`，Claude 出方案→Codex 审→两轮讨论定案 6 条→用户 ratify→Codex 执行→Claude 大节点全面审，365→374 绿·零 golden 变更）**：Phase A 让证据债"可见"、A8 让它"有后果"——给 correction 软环节装**仪表+前后确定性卡门**。新 `src/agent/execution/evidence_preflight.py`（`EvidenceDebt` pydantic，对 0_reading CheckReport 的 evidence 子集做**确定性投影**〔非新真相源，可从 CheckReport 重算〕、**按当前 run_profile 重判 disposition**、`schema_version+producer` 最小扩展位不搭 severity、`scope` 数据驱动 element_local/view_global）；`run_correction`/`run_pipeline` 加 `run_profile`（默认 exploratory 向后兼容）→ 总产 `1_correction/evidence_debt.json`、仅 golden/regression fail-closed；correction prompt 注入债块（债元素别编坐标、落 `conflicts` **不碰 `unsupported`**）；A8.3b 新 `check_evidence_debt_coverage`（correction 后确定性覆盖门，element-local 强核全 offender_ids/view-global lexical advisory、disposition by run_profile、只判覆盖不判坐标）。**零改 CorrectedGeometry/reading 契约、不新增 needs_reread**（golden/regression reread 走既有 AWAITING_REREAD）。**本质定性（用户 ratify）**：Phase A+A8 都**不修 reading、不修伪墙**=仪表层（探测+接线让弱有后果、藏不住）；伪墙多标 `seen` 无证据债、A8 抓不到；修弱那刀在 Phase B。backlog：standalone run_correction 空 testdata 漏 dimensioned-view-only debt；element-local 覆盖只查 offender id 出现未证几何映射（留 Phase B 双通道解）。

**item ④ reading 1-5 迁移缺口修法首批已落地（2026-07-01 `7.01_Stage1to5MigrationGapFixes`，用户本轮定先不做 Phase B、改做 item ④）**：综合 Codex 独立全 0-5 迁移审计（`logs/review/2026-06-27_full_0to5_migration_audit_codex`，80 条 ✅64/❌4/⚠️7/🗑5）逐条对**当前树**核实 11 条开放 finding。**裁定**：stage-0 四条冲突（S0-04/05/15/26）**全已 stale**（`6.27_ReadingImageLocalUncaptured` 修掉，别再重提）；**S1-10 非矩形 cell + S1-12 derive_facade_frame 接线 = Phase B 领**；S4-12（TBD 门）用户不选记 backlog。实修 4 条（Claude 方案→Codex 审 APPROVE-WITH-CHANGES 全采纳→执行→Claude 全面审 pytest+diff，374→381 绿·零 golden）：**S4-07** `mep._load_refs` 补验 People Activity Level Schedule（eppy raw+fields[9] 兜底）填 EP-fatal 缺口 / **S23-16** InterZone kernel gate run_profile 口径一致（run_pipeline 产 `2_modelling/kernel_checks.json`、golden/regression fail-closed、exploratory 经 `E:gate:…:kernel.pairing_gate` 可见续行；run_state 由编排账本派生不 overload）/ **S1-09** A3 走廊连续单区 prose（不碰内核）/ **S1-18** A0:291 四个 residual soft check 补显式 NOT_APPLICABLE 占位。

**迁移完全裁决（2026-07-01 续 `7.01_Stage1to5MigrationComplete`，用户定"补真空+宣告完全"）**：派**第二路独立 Codex** 冷启对抗式重审 stage 1-5（DeepSeek MCP 本会话不可用→同模型独立，独立性弱于 reading 三路但抓到真发现）。第二路把第一路 ~15 条 ✅ 降 ⚠️，**Claude 逐条代码核验裁定=路径差非迁移缺失**：约束**迁到了 `validate_case`**（M0-M4 非侵入 capstone、contracts §280；`check_correction`/`check_mep` 只在 validate_case+stepwise 调、`intake_node→run_pipeline` 生产路径不 inline；validate_case 由 record_baseline+step_orchestrator 调 → dev/baseline 全走它跑 full gate①）。**锚：相对 sm21_pre，迁移在 validate_case 口径下基本完全。** 真·无处强制三条本轮补进 `check_mep`（validate_case 路径、**不 inline run_pipeline**）：`mep.placeholder_ban`(INVARIANT)/`mep.name_charset`(flag)/`mep.site_matches_testdata`(anchor→NA)。381→388 绿零 golden。**重要架构事实（backlog）**：**run_pipeline 生产路径不跑 full check_correction/check_mep**——A8/S23-16 已把 evidence_debt/kernel inline 进 run_pipeline，correction/mep 门没跟上=生产路径自校半拉子；补齐=独立前瞻 initiative、宜并 Phase B correction 重构（**不是 sm21_pre 迁移缺口**，validate_case 口径下 dev/baseline 已强制）。**Codex 最后全面审=GO 收口**（应用户"有效约束别被 refactor 弄丢"关切，独立复核 reconciliation：逐 ⚠️ 项每条 NOT LOST/FIXED、127ba06 重扫"new lost-capability findings: none"）→ **相对 sm21_pre，stage 1-5 脚手架约束能力迁移完全（validate_case 口径），遗留迁移完整性工程问题关闭**；下一步进入新能力（reading 质量 / Phase B）。

**残留 / 下轮候选=Phase B（用户 2026-07-01 定，仍待启）**：双通道 schema（reading 不吐最终坐标）+ 算术下沉确定性求解器（尺寸驱动重建·Shapely polygonize）+ 接线 `derive_facade_frame`〔接核前必对 gt 校验 E/W sign，见 [[derive-facade-frame-unwired-ew-sign-trap]]；含点名生产调用点+测试〕= 正面解过度分割那一刀。另 Phase C 远期。
