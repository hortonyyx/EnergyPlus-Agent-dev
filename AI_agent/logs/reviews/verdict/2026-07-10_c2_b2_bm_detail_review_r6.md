# C2 B2 + B-M 细稿 r6 短文字复核

Date: 2026-07-10  
HEAD: `7422f42`  
Objects: `AI_agent/proposals/c2_b2_detail_spec.md`、`AI_agent/proposals/c2_bm_view_manifest_spec.md`（v6）  
B2 verdict: **APPROVE**  
B-M verdict: **APPROVE**

## 一、复核范围与结论

本轮仅复核 r5 的 R5-X-01、R5-BM-01 两处补丁及 B2/B-M 交叉同步，不重审已关闭正文。

结论：**两条均 CLOSED；未发现补丁引入新的 wire、writer、migration 或 source-identity 不一致。** 两稿可进入既定施工顺序，**无需 r7**。

## 二、补丁关闭矩阵

| r5 finding | 状态 | r6 核对 |
|---|---|---|
| R5-X-01 StageRecord native/migrated 判别 + migration commit | **CLOSED** | `ArtifactContract` 已成为 StageRecordV2 必填 discriminant；四行矩阵只按 contract 决定 artifact keys，writer/migrator owner明确，无默认降级。B2 writer 同步固定 `correction_b2_v1 + stage_version="2"`，B-M loader 对 stage/provenance做交叉校验，漏 bump、native 冒充 base、伪造 migrated 均拒。migration 已改为内存构建/backfill→同目录 temp+fsync→view manifest先落→RunManifestV2最后落为唯一 commit point，并冻结 V1 orphan 忽略、hash复用/覆盖与幂等恢复。证据：`AI_agent/proposals/c2_bm_view_manifest_spec.md:170-207`、`AI_agent/proposals/c2_b2_detail_spec.md:260-278,304-318`。 |
| R5-BM-01 coverage source 双义 | **CLOSED** | coverage 已删除裸 `source_ref`，只保留 `completeness_assertion_id`；source 统一经外层 assertion解引用，extra-forbid拒绝任何 coverage 自带来源字段。`UserSourceRef` 内层 assertion_id 已删除，身份唯一归 `CompletenessAssertion.assertion_id`；validator与负例同步。证据：`AI_agent/proposals/c2_bm_view_manifest_spec.md:100-106,118-146`。 |

## 三、交叉一致性核对

- B-M 是 RunManifestV2/StageRecordV2 唯一规范 owner；B-M 先落、B2 后消费的依赖未回退。
- B-M 矩阵中的 `correction_b2_v1 → output/checks/audit/feature_states` 与 B2 writer 完全一致。
- B2 将 `artifact_contract` 与 `stage_version="2"` 一并纳入 CorrectionTarget→writer 贯穿断言；现 StageRunner 默认 `"1"` 不再构成静默降级口。
- migrated legacy 只登记真实存在 artifact，与 native B2 correction 四键硬门互不混淆。
- RunManifestV2 最后落盘是唯一语义 commit；孤儿 view manifest 在 V1 下无效且恢复路径幂等，不再虚构“两次 rename 原子”。
- completeness source 现在只有 assertion 一条权威链，coverage 不再持有第二份可漂移来源。

## 四、最终放行

### B-M — **APPROVE**

按既定依赖先施工：共同 RunManifestV2/StageRecordV2 wire、claims.py、trusted manifest及 isolation/gate 接线。

### B2 — **APPROVE**

B-M 共同 wire 合入并复核后，按 B2 §9 顺序施工；correction writer 必执行 `artifact_contract="correction_b2_v1"` 与 `stage_version="2"` 双设置及交叉负例。

**可进入既定施工顺序、无需 r7。**

## Review ask

none
