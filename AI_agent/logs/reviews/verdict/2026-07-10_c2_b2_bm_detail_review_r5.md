# C2 B2 + B-M 细稿 r5 对抗复审

Date: 2026-07-10  
HEAD: `7422f42`  
Objects: `AI_agent/proposals/c2_b2_detail_spec.md`、`AI_agent/proposals/c2_bm_view_manifest_spec.md`（v5，累计式全文）  
Governing design: `AI_agent/proposals/c2_full_unlock_design.md` v2.2；baseline: `AI_agent/proposals/c2_orthogonal_polygon_design.md` D1–D10  
B2 verdict: **APPROVE-WITH-CHANGES**  
B-M verdict: **APPROVE-WITH-CHANGES**

## 一、总裁决

r4 的四条修法均已实质采纳，且没有新的架构 BLOCKER：

- RunManifest/StageRecord 顶层与嵌套 wire 已分 V1/V2，唯一 owner 与 B-M→B2 顺序已定，artifact key 受控、output 双 hash、migration backfill 均进入正文。
- B2 feature state 已拆为 finalize claims 与 writer artifact 两型，writer重派生比对，不再信任可变裸 dict；R1–R10 route id 也消除了计数二义。
- B-M completeness source 已成为 discriminated union，OpeningEvidence 五条联动约束与三正五负测试均已落。

本轮仍有两个 **HIGH**，都属于局部 wire 补全，可按明确修法机械修改，不要求重画架构：

1. StageRecordV2 没有机器可判的“native B2 correction / pre-B2 native / migrated legacy”合同，导致“四键何时必填”仍依赖 prose；显式 migration 所称跨两个文件原子提交也未冻结 commit/recovery 顺序。
2. CompletenessAssertion 虽已 strict，但 `coverage.source_ref` 仍是裸字符串，无法和 discriminated `source_ref` 机械做“source 家族一致”；user source 还重复一份未约束相等的 assertion_id。

关闭统计：

- r4 共同/B2 三条：**2 CLOSED / 1 PARTIAL / 0 NOT-CLOSED**。
- r4 B-M 一条：**PARTIAL**。
- 新 findings：**2 HIGH**（共同 1、B-M 1）；无 BLOCKER。

因此两稿均给 **APPROVE-WITH-CHANGES**：完成本 verdict 的两条精确补丁后可进入既定施工顺序，无需再开产品裁决。若执行档未先补，则相应 invariant 仍不得视为已放行。

本审只读核对 HEAD；除本 verdict 外未改任何文件。

## 二、r4 findings 关闭矩阵

| r4 finding | 状态 | r5 复核 |
|---|---|---|
| R4-X-01 RunManifestV2/StageRecord 共同 wire | **PARTIAL** | V1/V2 顶层+嵌套分型、ArtifactKey、基础/四键/isolated 规则、output 双 hash、stages backfill、唯一 owner与 B-M→B2 顺序均已落；但 native/migrated 与“B2 后”尚无 machine-readable discriminator，migration 跨文件 commit 语义也只写“原子”。见 R5-X-01。 |
| R4-B2-01 strict feature-state wire | **CLOSED** | `FeatureStateClaimsV1` 为 immutable complete-key claims，writer按 target+final geom重派生比较，再构造 output-bound `FeatureStatesArtifactV1`；consumer 的 schema/hash/output 三重先验与篡改/未知/缺键负例齐全（`AI_agent/proposals/c2_b2_detail_spec.md:260-294`）。 |
| R4-B2-02 route id | **CLOSED** | 路由已冻结 R1–R10，两 renderer 分 R9/R10，测试按 route id 集合相等（细稿 `:230-258,304-317`）。 |
| R4-BM-01 CompletenessAssertion strict wire | **PARTIAL** | 三种 source ref、outer assertion与五条 OpeningEvidence 联动已落；coverage 侧残留裸 `source_ref` 与 user 双 assertion id，尚不能执行第五条联动。见 R5-BM-01。 |

## 三、历史遗留 PARTIAL 复核

| 历史 finding | r4 状态 | r5 状态 | 说明 |
|---|---|---|---|
| R3-B2-04 feature-state attempt identity | PARTIAL | **PARTIAL** | claims/artifact/hash本体已闭；accepted StageRecord 的 stage-contract 判别仍受 R5-X-01 影响。 |
| R2-B2-06 feature-state | PARTIAL | **PARTIAL** | support/populated、owner、strict sidecar均已闭；end-to-end 四键强制仍依赖未冻结的 stage discriminator。 |
| r1 BM-08 strict schema/version chain | PARTIAL | **PARTIAL** | manifest主 wire/version/identity已闭；negative-evidence 信任根还剩 R5-BM-01 两个引用二义。 |
| R2-BM-02 / r1 BM-02 isolation binding | CLOSED | **CLOSED** | run_id、正式/preview、merge identity、同门与八负例未回退。 |

其余 r1–r3 findings 均维持 CLOSED；本轮未发现 strict v3、legacy bytes、ring 两阶段、CorrectionTarget、debt resolution、direction/source-aware Va、reader visibility 或恒 BLOCK 被重开。

## 四、共同新 finding

### R5-X-01 — HIGH — StageRecordV2 的必填 artifact 合同仍靠“B2 后/legacy migrated”自然语言，migration 也缺跨文件 commit 点

B-M 唯一规范 owner 已定义 `StageRecordV1/V2`、`ArtifactKey` 与 `RunManifestV1/V2`（`AI_agent/proposals/c2_bm_view_manifest_spec.md:170-188`），这是正确修复。但随后的 validator 规则写成：全部新 attempt 两键、**B2 后** correction 四键、isolated reading 三键、legacy migrated只登记真实键（`:189-194`）。当前 V2 wire 只有：

- `record_schema_version: Literal["2"]`——所有 native/migrated V2 record 相同；
- 从 V1 继承的自由字符串 `stage_version`——稿内没有冻结 B2 correction 的具体新值、比较规则或迁移保留值；
- 无 `record_origin`/`artifact_contract` 字段。

因此 loader 无法仅凭 wire 判断一个 `stage="1_correction"` 的 V2 record 是：迁移来的 legacy、B-M 已落但 B2 未落时产生的 native record，还是 B2 后本应有四键的新 record。现实 `StageRunner.record` 的 `stage_version` 默认仍是 `"1"`（`src/agent/execution/stage_runner.py:124-134`）；若 B2 caller漏传 bump，新 correction 只带 output/checks 仍会被当作合法旧合同，readiness sidecar硬门被绕过。

migration 还有一个崩溃窗口：步骤② provision `view_manifest.json`、步骤③回填后才提交 RunManifestV2（B-M `:192`）。两个最终文件无法靠一次 `os.replace` 同时提交；若沿用普通 provision 先写最终清单，回填失败/进程崩溃会留下“V1 manifest + 新 view_manifest”，与“任一步失败整体原子、保持 V1 不动”不完全等价。

**建议修法**：

1. 冻结机器可判合同。推荐在 `StageRecordV2` 增 `artifact_contract: Literal["migrated_v1", "base_v2", "reading_isolated_v2", "correction_b2_v1"]`（名称可调整），并由唯一 writer/migrator设置；或冻结不可歧义的 `(stage, stage_version)` 常量矩阵，明确 B2 必 bump 的 exact value。validator只按该字段/矩阵决定 required keys，禁止调用方用默认值降级。
2. B2 §5/测试增加：B2 新 correction 缺 audit/feature_states 即拒；同 stage 的 migrated legacy 两键可读；伪造 migrated/native contract 与 attempt provenance 不符即拒。`stage_version` bump 必进入 CorrectionTarget→writer 贯穿测试。
3. 冻结 migration commit 协议：先在内存完成 manifest生成与全部 backfill，两个新文件写同目录 temp并 fsync；以明确 commit marker/journal 或可恢复顺序提交。若选择“view manifest 先落、RunManifestV2 最后作为 commit point”，必须声明 V1 loader忽略孤儿清单、重试如何校验/覆盖、崩溃恢复如何清理；不得笼统声称两个 rename 原子。

这是单一 wire 判别与 crash-recovery 补丁，不要求改变 B-M→B2 顺序，故定 HIGH 而非 BLOCKER。

## 五、B-M 新 finding

### R5-BM-01 — HIGH — coverage 仍用裸 `source_ref`，新 CompletenessSourceRef 无法真正完成“source 家族一致”校验

新 §3.6 正确定义了 `CaseMetadataSourceRef | UserSourceRef | DatasetSourceRef` discriminated union（`AI_agent/proposals/c2_bm_view_manifest_spec.md:118-138`），但 coverage wire 仍是：

```json
{"source_ref": "…", "completeness_assertion_id": "…"}
```

即 `source_ref` 仍为无格式字符串（细稿 `:100-106`）。OpeningEvidence validator 第五条却要求 `coverage.source_ref` 与 `CompletenessAssertion.source_ref` 的 source 家族一致（`:139-145`）。一个任意字符串没有 discriminant，施工者只能自行发明前缀、JSON pointer或ID解析规则；这正是 strict wire 要消灭的隐性二选一。

另有重复身份：`UserSourceRef.assertion_id`（`:125-128`）与外层 `CompletenessAssertion.assertion_id`（`:135-137`）可以不同，五条 validator 没有要求相等。coverage只引用外层 id，于是同一对象可同时声称两个 assertion identity。

**建议修法**：最小方案是删除 coverage 的 `source_ref`，只保留 `completeness_assertion_id`，source 统一经 assertion 解引用；若 coverage 必须自带来源，则改为 typed `CoverageSourceRef`/同一个 discriminated union并冻结精确 equality规则。删除 `UserSourceRef.assertion_id` 这一重复字段，或增加与 outer id 强制相等的 validator。负例增：裸/未知 source family、coverage/assertion source不一致、user inner/outer id不一致。

## 六、两稿结论档

### B2 — **APPROVE-WITH-CHANGES**

B2 自身的 r4 两条 finding 已 CLOSED；仅共同 StageRecord contract 判别仍影响 feature-state四键强制。按 R5-X-01 补 exact contract/stage-version 与 migration协议后可施工，不需再改 geometry/schema/finalize 架构。

### B-M — **APPROVE-WITH-CHANGES**

B-M 已成为共同 wire owner并正确补 run/migration骨架；须按 R5-X-01 完成 record contract与 crash recovery，并按 R5-BM-01 消除 completeness source双义。两项都是本稿内局部 strict schema修订。

## 七、重新送审/执行门

1. 共同 wire 增 machine-readable artifact contract（或 exact stage-version matrix）并冻结 B2 stage bump；补 native/migrated交叉负例。
2. migration 写明多文件 commit point、fsync、崩溃恢复与孤儿清单处置。
3. coverage source 改 typed或删冗余；user assertion id 只留一个权威值。

完成这三项后无需新的产品决策；若主控选择先修稿再施工，可作一次短 r6 文字复核，也可在执行档开工前检查清单逐项对照本门。

## Review ask

none — 无需用户拍板；剩余均为局部 wire 精确化。
