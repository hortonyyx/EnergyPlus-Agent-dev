# B4b Phase D 施工派发（terra 执行档，2026-07-17）

**任务**：按 [AI_agent/proposals/c2_b4b_detail_spec.md](../../proposals/c2_b4b_detail_spec.md) **v2 定稿**施工 **Phase D（Run-stage、cache、renderer、CLI 与回归封口）**（稿 §13 Phase D + §10 / §11 / §12.2 / §6.7）。该稿是唯一施工合同（累计式自包含）；本单**只放行 Phase D**——这是 **B4b 全系列的最后一块封口批**。Phase A/B/C 全 CLOSED。

## 前置门（全部已满足，可开工）
- **B4b Phase A/B/C 已合并**：score schema/config/inputs + sidecar v8 骨架 + segment_score + opening_claim_score（plan + elevation + fusion + policy + trusted-negative）+ score_policy v3 criteria/verdict 全落。
- **B4a A–D 全 CLOSED**：typed render model（`gt_to_render_model`）+ render_gt/overlay v3 + render_grade legacy 边界 + writer no-promote 门全就位。
- **B4B-REC-D 逐字对账门已 PASS**（主控 Opus 先行，[verdict/2026-07-17_b4b_rec_d.md](../verdict/2026-07-17_b4b_rec_d.md)）：四项一致——① typed render model（探针产 PIL 图）；② grade overlay v3 接口（build/write_gt_overlay_images_v3 签名）；③ promotion gate（render_gt v3 CLI + writer no-auto-promote `write_gt_v3_candidate`/`_protected_candidate_path`/`gt_candidate_protected_path` + **render_grade 现为 legacy 边界=你要接的 seam**）；④ §15.2 联合门 item ③ = 本 Phase D 交付。
- **基座 = HEAD `239dc00`（1216 绿 + 9 xfail，树干净）**。

## Phase D 范围（稿 §13 Phase D 施工，以稿为准）

1. **`SCORER_SCHEMA "7" -> "8"`**（`scripts/tool_scripts/run_stage.py`）：Phase A/B 期过渡双值裁决（标签 legacy "7"/骨架 "8"）在本批**收敛**到 "8"；schema 0–7 sidecar 全部必重算。
2. **full identity cache validator + accepted StageRecord digest**（run_stage.py）：**逐个**改变 GT hash/schema、capability、config、base/effective manifest、overlay、bindings、Va/Vg/helper version、output、accepted 状态**都必须重算**；**完全相同 identity 才 cache hit**。
3. **sidecar/PNG atomic pair**（run_stage.py + render_grade.py）：sidecar 数据文件与 grade PNG **原子成对写入**；interrupted write/fault injection **不暴露半 pair**。
4. **typed polygon renderer 与 gray hatch**（`render_grade.py` + `_grade_transform.py`，§11.2/§11.3/§12.2）：**新增 v3 typed polygon path**（从 `gt_to_render_model` 取真实 polygon/segment/dynamic surface；projection/mirror/local-x 只来自 score bindings），**legacy transform 一行不动**；gray hatch = NA/unobserved 灰色斜线（full/partial clip、z-null rail 全 hatch 标 `PLAN-ONLY · z NA`、host 只对 unobserved residual hatch、appearance 整 claim rail hatch 各带 reason）；render totality（每 sidecar target/claim 在 audit map 恰一位置或显式 `not_rendered_reason`，多/少/未知 segment/clip 不守恒 → `scoring.render_totality` reject）。
5. **CLI service dispatch**（`scripts/tool_scripts/score_reading_vs_gt.py`，§10.5）：CLI 与 run-stage **共用同一 service 函数**，禁复制 scoring policy；覆盖 v2/v3/NA/REJECTED 四路。
6. **projection→scorer 生产接线**（Phase C 返工登记的 Phase D 领地）：把 `project_typed_elevation_observation` 接进真实 input 规范化/CLI 边界（§6.8 normalizer），使 typed elevation 产品观测经受信 frame 投影后进 scorer——Phase C 只在测试层演示了 projection→scorer，**生产 normalizer/CLI 接线本批补上**。
7. **legacy v2 regression 封口**（§9.1）：legacy renderer pixel hash/采样点保持；sm21 当前 floor map/counters/elevation assertions 不变；sm20 无 GT 行为不变。
8. **VA-C7 六项最终债务扫描**（Va tests，§12.2）：吸收 VA-C7 六项（第八词/重复 opening_id/悬空 source 拒例/删声明双调用对照/凹形多段 fixture 等，见 Va 批判词 VA-C7 束）；**Va module 只有 source scan 发现 no-op 回归才改**，否则一行不动。
9. **import boundary/static scan**（§13 Phase D）：production import judge 为零的静态扫描；source scan 无 tautological no-op assert。

## 硬不变量与禁区（违即偏差）
- **legacy v2 锁定**（§9.1，gate D4）：legacy wall/window/boundary/elevation counter/criteria/verdict/renderer 语义、legacy `_grade_transform`、legacy policy **一行不动**；v3 全走**新增 typed path 旁路**。sm21 pixel hash/采样点、sm20 no-GT 行为是硬回归锁。
- **cache identity 全量**（§10.2，gate D1）：任一 identity 组件（GT hash/schema/capability/config/base·effective manifest/overlay/bindings/Va·Vg·helper/output/accepted 状态）变化必重算；**完全相同才 hit**。禁"部分 identity"或宽松比对。
- **原子 pair**（§10.4，gate D2）：identity 未构造成功 → 直接 machine REJECTED，**不写可缓存 sidecar/PNG**；identity 已验证后的下游 REJECTED 才写错误信息板；**禁半 pair**（fault injection 测试锁）。
- **gray hatch 守恒**（§11.4，gate D3）：render totality——每 target/claim 恰一渲染位置或显式 not_rendered_reason，不守恒 raise `scoring.render_totality`。
- **judge-only**（§2.2/§12.3，gate D6）：本批全落 `src/agent/judge/` + `scripts/tool_scripts/`（judge 侧脚本）；**生产路径（executor/correction/reading/pipeline）零 import 本批 judge 模块**；`facade_applicability.py`（Va production 侧）**只有 source scan 发现 no-op 回归才改**。
- **明确不改**（§12.3）：production output schema、`view_manifest.py` base emitter、`RunManifestV2` production artifact key union、任何 `case_tests/.../gt`/golden/verified overlay、B5/B5b/B6 文件。**无 GT/golden diff**（gate D6，测试锁）。
- **不越界 Phase A/B/C 稳定件**：score schema/config canonical hash、sidecar v8 identity、A0 frame preimage、segment/opening assignment、elevation projection/fusion/policy 已 CLOSED，不 revert 不重构；只在其上接 run-stage/cache/render/CLI。
- 若必须跨界或改 Va（非 no-op scan）/改 production schema 才能过验收 → **停止报 blocker**，不擅改。

## 测试纪律（稿 §13 Phase D 测试矩阵，全数落地、真断言）
逐条落地，**负轴/回归不得 shipped-untested**（升一档审专抓此型）：
- schema 0–7 sidecar 全重算；**逐个** identity 组件变化都重算（GT hash/schema/capability/config/base·effective manifest/overlay/bindings/Va·Vg·helper/output/accepted 状态各一条负测）；**完全相同 identity 才 cache hit**；
- **interrupted write/fault injection 不暴露半 pair**（原子性真注入故障）；
- gray hatch full/partial clip、z-null label、NA 信息板（各自真断言渲染位置/reason）；
- **legacy renderer pixel hash/采样点保持**（v2 回归硬锁）；
- sm21 当前 floor map/counters/elevation assertions；sm20 无 GT 行为；
- CLI v2/v3/NA/REJECTED 四路；
- **source scan 无 tautological no-op assert**（自查恒真式）；
- **production import judge 为零**（静态扫描真断言）；
- **无 GT/golden diff**。
- 稿章节→测试映射表 + 六出口 gate（D1-cache-identity / D2-atomic-artifacts / D3-gray-hatch / D4-legacy-v2-regression / D5-va-c7-closed / D6-protected-assets-clean）逐一具名落测。
- 定向组逐组记 passed 数；**全量 pytest 归主控轻门**（codex exec ~30s 杀长前台进程，别跑全量；`run_stage`/render 相关 targeted 套自验即可）。

## 交付
1. 工作树内代码+测试（**不 commit**）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-17_b4b_phaseD_construction_brief.md`（改动映射 / 稿章节→测试映射表 / 六 gate→测试 / 各组 passed 数 / 预期行为变化 / 未决·偏离 / review-ask〔无则注明 none〕 / 本批改动文件清单）。**如实披露未竟项**（"未做说成留给审查"=披露偏差，会记档；SCORER_SCHEMA "7"→"8" 收敛是否真全链一致要明说）。
3. terse report（各组 passed / 改动文件 / 关键结论 / 偏差 / review-ask 摘要），不贴 diff。

审向：**Opus 子代理执行审（升一档·独立上下文·活体探针）→ 主控轻门（独立全量 + 抽查 + 裁决）**。重点探：① cache identity 是否真全量（改任一组件是否真重算，`schema 7→8` 是否漏某条 identity 使旧 sidecar 假 hit）；② 原子 pair 是否真原子（fault injection 是否真不暴露半 pair）；③ gray hatch render totality 是否真守恒（多/少/未知 segment 是否真 reject）；④ legacy v2 是否真一字未动（pixel hash 锁是否真咬合）；⑤ CLI/run-stage 是否真共用 service（policy 是否被复制）；⑥ projection 生产接线是否真接通（非又只在测试层）；⑦ production import judge 零 + source scan 无恒真式；⑧ 是否误碰 golden/GT/production schema。
