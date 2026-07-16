# B4b Phase A 施工派发（terra 执行档，2026-07-15）

**任务**：按 [AI_agent/proposals/c2_b4b_detail_spec.md](../../proposals/c2_b4b_detail_spec.md) **v2 定稿**施工 **Phase A（合同、identity 与 score inputs）**。该稿是唯一施工合同（累计式自包含）；本单**只放行 Phase A**（稿 §13 Phase A 行），Phase B/C/D 后续单独派工。

**前置已满足**：B4a Phase A 已 CLOSED（`25d3946`）；**B4B-REC-A 逐字对账门已由主控跑过并 PASS**——记录见 [verdict/2026-07-15_b4b_rec_a.md](../verdict/2026-07-15_b4b_rec_a.md)（37 机器比对+3 行为探针；两项登记偏差:PA-C7① list-vs-tuple 永久留痕、PA-R2④ wall_thickness_m 默认已由同日 B4a Phase B 在树内修除——**本批一律按合同编码,视其为必填 nullable 无默认**）。

## Phase A 范围（稿 §13 Phase A + §12 对应件）

- strict score schema/config/canonical hash（新增 `src/agent/judge/score_schema.py` + `src/agent/judge/score_config.py` + `src/configs/judge_score.yaml`,§6 strict wire、§5 稳定常量/错误码/gate id）；
- typed loader capability dispatch skeleton（§7.1:v3 只走 `load_gt_document()`/`load_gt_file()`,v3 绝不调用 raw `load_gt()`）；
- GT identity、product/accepted identity、helper identity（`load_score_gt_identity()` 等,§6/§7.1）；
- score view bindings 与 resolved direction validation（新增 `src/agent/judge/score_inputs.py`,§6.3 受信 view_bindings——§17 裁决 1 已批准）；
- user/dataset completeness builder、effective manifest 纯函数（§6/§13,base/effective hash 区分）；
- GT-to-Va adapter facade hash preimage proof（§7.2:独立重算 `facade_segments_sha256`,不 import Va 私有 hash helper,与 A0 frozen preimage 字节相等）；
- **按 §6.3.8 把 frame-transform 全字段 preimage 登记进 A0**（`skills/intake_pipeline/1_correction/A0_contract.md`,sorted-key compact UTF-8 SHA-256 口径,VA-C3 同款;登记完成是独立重算开工门）；
- sidecar v8 NA/REJECTED skeleton（**SCORER_SCHEMA 切 "8"**,盘面现值 "7";不接几何 scorer）；
- 新增 `scripts/tool_scripts/build_judge_score_inputs.py`（候选 user/dataset declaration builder/validator）——若稿把它划在后续 Phase,以稿为准并在简报注明。

**测试**（稿 §13 Phase A 测试清单全数落地）：strict extra/missing/type/NaN/Infinity 拒绝;config hash/关系/A0 fixture;schema 7 sidecar 必重算;base/effective manifest hash 区分;user/dataset 两条真实生成路径与 body hash;每 view 单 source、base 冲突、幂等重复;standard/true/unknown direction;mirrored/local-x 不能来自产品;GT-to-Va facade hash 与 A0 frozen preimage 字节相等;sign 正负/mirror 两态/local-x 两态 fixture 的 frame-transform hash 与 A0 固定向量字节相等,缺/多任一 preimage 键均失败;v3 绝不调用 raw `load_gt()`。

**出口 gate**（稿 §13）：`B4B-A1-wire-strict` / `B4B-A2-identity-total` / `B4B-A3-completeness-owner` / `B4B-A4-va-preimages` / `B4B-A5-production-import-zero`。

## ⚠️ 并行车道边界

同树有**另一批已完工未 commit 的 B4a Phase B 改动**（`scripts/tool_scripts/inspect_dxf.py`、`src/agent/judge/gt_extraction.py`、`src/agent/judge/gt_schema.py`、`tests/test_gt_extraction.py`、`tests/test_gt_schema.py`）——**一律不碰、不 revert、不重构**;`git status` 见到它们属正常。本批对 B4a 的依赖面只允许是**已 commit 的 Phase A 公共 API**（`526c38e` 基座,REC-A 已对账）+ gt_schema 在树内状态的只读 import。

本批同样不碰：`gt.py`/`gt_manifest.py`/`judge_gt.yaml`（B4a 件）、`gt_from_dxf.py`/render 系（B4a Phase C/D）、correction/Vg/Va 生产代码（Va module 只有 source scan 发现 no-op 回归才改,且属后续 Phase——§12.2）、production output schema、`view_manifest.py` base emitter、任何 gt/golden/verified overlay 资产。

## 硬边界

- 基座 = HEAD `526c38e` + 树内 B4a Phase B 未 commit 件（如上）。
- 零资产扰动：合成输入只进 pytest 临时目录。
- gt 铁律：生产路径（executor/correction/reading）零 judge import（`B4B-A5`）;`tests/test_gt_discipline.py` 既有门保持绿。
- legacy scorer 行为锁定：`reading_score.py`/`correction_score.py`/`elevation_score.py`/`score_policy.py` 只加 typed dispatch adapter,**不在旧函数内塞 v3 分支**（§12.2）;若 Phase A 尚不需要动它们,不动。
- 备份：主控已全量备份 `backup/src_history/2026-07-15_b4a_phaseB_b4b_phaseA/`。
- 本批不创建 commit;不改管理文档。

## 测试纪律

- 定向组：新增 score 测试族 + 既有 `test_gt_schema.py`/`test_gt_discipline.py`/`test_judge_harness.py`/`test_reading_score.py`/`test_elevation_score.py` 回归,逐组记 passed 数;全量 pytest 归主控轻门。
- 稿 §13 Phase A 测试清单全数落地;确有未竟逐条列明,不得静默;稿章节→测试映射表写进简报。
- 独立合并条件：五出口 gate 全绿;真实 v3 promotion 仍等 §15 联合门禁（本批不做 promotion）。

## 交付

1. 工作树内完成代码+测试（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-15_b4b_phaseA_construction_brief.md`（改动映射/验收与测试/预期行为变化/未决·偏离/review-ask——无则注明 none;**附本批改动文件清单**,供主控按车道切分 diff）。
3. 回复只给 terse report（各组 passed/改动文件/关键结论/偏差/review-ask 摘要）,不贴 diff。

审向：**Opus 执行审（升一档）→ 主控轻门（独立全量+抽查+裁决）**。
