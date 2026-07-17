# B4b Phase B 施工派发（terra 执行档，2026-07-17）

**任务**：按 [AI_agent/proposals/c2_b4b_detail_spec.md](../../proposals/c2_b4b_detail_spec.md) **v2 定稿**施工 **Phase B（Plan segments、opening matching 与 denominator）**（稿 §13 Phase B）。该稿是唯一施工合同（累计式自包含）；本单**只放行 Phase B**。Phase A（identity/score inputs/sidecar v8 skeleton）已 CLOSED 收录（07-15）。

## 前置门（全部已满足，可开工）
- **B4b Phase A 已合并**（score_schema.py/score_config.py/score_inputs.py/build_judge_score_inputs.py/judge_score.yaml + sidecar v8 skeleton + A0 frame preimage 登记）。
- **B4a Phase B/C 的 polygon/segment/opening typed 输出已落地**（`GroundTruthV3` 全 typed，Phase C CLOSED、Phase D CLOSED）。
- **B4B-REC-B 逐字对账门已 PASS**（[verdict/2026-07-17_b4b_rec_b.md](../verdict/2026-07-17_b4b_rec_b.md)：floor/zone polygon、segment id preimage+碰撞、opening ref/world-along/nullable-z、Vg tolerance+segment 排序、canonical bytes 五项全一致）。
- **Va（`src/agent/correction/facade_applicability.py`）= 唯一 applicability 引擎**已就位（`derive_opening_claim_applicability` + ledger 族，Va 批 CLOSED 07-14）。
- **B4b typed GT fixture**（`tests/b4b_contract_fixture.py`）已就位（Phase D 交付，只读 `GroundTruthV3` 构造）。
- 基座 = HEAD `d028744`（1168 绿 + 9 xfail，树干净）。

## Phase B 范围（稿 §13 Phase B 施工 + §7/§8/§6.6/§6.4，以稿为准）

**新增两个核心 judge 模块**（§12.1）：
- **`src/agent/judge/segment_score.py`**：exterior/interior actual polygon segment extraction + reading/correction segment observations + **确定性全局 assignment 与 tie rejection**（§8.1 GT segment 集 / §8.2 产品 segment 集 / §8.3 Segment assignment）。
- **`src/agent/judge/opening_claim_score.py`**：GT-to-Va adapter（§7.2）+ reference/product/absence 三 ledger Va 调用（§7.3–7.5）+ opening assignment（§8.4）+ host judge-only 关系解析（§8.4.1）+ **精确 partial denominator**（§8.5）+ claim 比较（§8.6）+ trusted negative conflict（§8.6.1）+ 多 source fusion（§8.7）。
- correction window temporary unique span binding（§8.3/§8.4 所指）；plan existence/host/along/width 四类 claim 计分；exact partial units 与 claim summaries（§6.6 per-claim score wire）；**extra 的 completeness gate**（§6.4 + §8）。
- 如需 reading/correction 观测入口，**扩** `score_inputs.py`（typed dispatch adapter，不在旧函数塞 v3 分支）；**不**在本批做 elevation projection / policy-verdict / grade PNG / run-stage schema 8（那是 Phase C/D）。

## 硬不变量与禁区（违即偏差）
- **Va 是唯一 applicability 引擎**（稿 §2.3 强制不变量）：applicability/reference-product-absence 三 ledger **一律调 Va 公开函数**，**禁止在 segment_score/opening_claim_score 里重实现或旁路 applicability 判定**。负证据只消费 Va 输出。
- **精确 partial 分母**（§8.5，gate B4B-B4）：host/along/width 分母 = 精确几何比例（L(A)/L(T) 等），existence/sill/head 可见即 binary；**禁止固定 0.5 或任何硬编码分母**。denominator 守恒（NA/0/miss 三者守恒 + declaration 删除双调用 reference denominator 不变）必须成立。
- **确定性全局 assignment + tie 拒绝**（§8.3/§8.4，gate B4B-B2）：assignment 对输入顺序/ID 重命名不变；exact tie **必拒**（不用 ID 消歧）；missing/ambiguous product segment id fail-closed。
- **禁 bbox / 固定四面**（§8.1，gate B4B-B1）：segment topology 从 actual polygon 提取，凹多边形/L/U/多同-family/短回折都要真处理。
- **extra 的 completeness gate**（gate B4B-B5）：无 completeness 的 unmatched opening = **NA**；只有完整负覆盖才判 extra。
- **只 7 个固定 claim**：第八 claim 拒绝（§6.6）。
- **judge-only**（稿 §2.2 + §12.3）：本批全落 `src/agent/judge/`；**生产路径（executor/correction/reading/pipeline）零 import 本批模块**；`facade_applicability.py`（Va production 侧）**只有 source scan 发现 no-op 回归才改**，否则一行不动。
- **明确不改**（§12.3）：production output schema、`view_manifest.py` base emitter、`RunManifestV2` artifact key union、任何 `case_tests/.../gt`/golden/verified overlay、B5/B5b/B6 文件、`render_grade.py`/`run_stage.py`（Phase D 领地）。
- **不越界 Phase A 稳定件**：score_schema/config canonical hash、sidecar v8 identity、A0 frame preimage 已 CLOSED，不 revert 不重构。
- 若必须跨界或改 Va 才能过验收 → **停止报 blocker**，不擅改。

## 测试纪律（稿 §13 Phase B 测试矩阵，全数落地、真断言）
逐条落地，**负轴不得 shipped-untested**（升一档审专抓此型）：
- 凹多边形 / L/U 形 / 多同-family segment / 短回折；concave multi-segment Va fixture；
- **禁止 bbox/fixed-four-side**（显式反例测试）；
- assignment 输入顺序 / ID 重命名不变（determinism 锁）；
- **exact tie 必拒绝**；missing/ambiguous product segment id fail；
- **partial 10% / 50% / 90% 按精确比例**（证明不是固定 0.5——三点各自断精确值）；
- **NA / 0 / miss 三者守恒**；
- declaration 删除双调用：reference denominator 不变（守恒证明）；
- 无 completeness 的 unmatched opening = NA，有完整负覆盖才 extra；
- duplicate opening id / dangling source / **第八 claim 拒绝**。
- 稿章节→测试映射表 + 五出口 gate（B4B-B1 segment-topology / B4B-B2 assignment-determinism / B4B-B3 va-only-applicability / B4B-B4 denominator-conservation / B4B-B5 extra-proof）逐一具名落测。
- 定向组逐组记 passed 数；全量 pytest 归主控轻门。

## 交付
1. 工作树内代码+测试（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-17_b4b_phaseB_construction_brief.md`（改动映射 / 稿章节→测试映射表 / 五 gate→测试 / 验收各组 passed 数 / 预期行为变化 / 未决·偏离 / review-ask〔无则注明 none〕 / 本批改动文件清单）。
3. terse report（各组 passed / 改动文件 / 关键结论 / 偏差 / review-ask 摘要），不贴 diff。

审向：**Opus 子代理执行审（升一档·最高对抗档·活体探针）→ 主控轻门（独立全量+抽查+裁决）**。重点探：Va 是否真被调用非重实现（信任根）、partial 分母是否精确非固定 0.5（恒真式假绿）、负轴测试矩阵是否全落真断言（shipped-untested）、denominator 守恒是否真成立。
