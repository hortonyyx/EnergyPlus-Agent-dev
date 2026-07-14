# B4b 细稿 r1 交叉审判词（Fable 最高档，2026-07-14）

**对象**：`AI_agent/proposals/c2_b4b_detail_spec.md` v1（sol 次高档出稿，1709 行）。
**审向**：GPT 侧稿 → Claude 侧最高档审（谁写谁不批）。
**方法**：全文逐节精读 + 五项机械事实核查（记录见文末）。

## 总裁决：APPROVE-WITH-CHANGES

**severity 计数**：BLOCKER 0 · MAJOR 0 · MINOR 2 · NIT 1。架构与批次边界全部成立；两处 MINOR 均为"实现者会被迫猜"的合同缺口，v2 补文字即可放行。

## 逐条 findings

### B4B-F1 —— MINOR：§6.3.8 引用的"Va A0 frame preimage"尚不存在

§6.3.8 规定 `frame_transform_sha256` 须"按 Va A0 preimage 独立重算"，且全稿禁止 import Va 私有 hash helper——但 A0 §4.1 只冻结了 `facade_segments_sha256` 的 preimage；frame hash 的 preimage（Va 内部 `_frame_hash` 的 `view_projection_binding_v1` 字段字典）**没有登记进 A0**。照稿施工者要么被迫 import 私有 helper（违稿）、要么猜 preimage（违细稿纪律）。
**要求**：v2 明确二选一并写死——推荐：B4b 实施批（Phase A）把 frame preimage 按 VA-C3 同款（全字段逐一点名+canonical JSON 口径）登记进 A0；备选：Va 模块导出 public frame-hash helper（须列为 §12.2 对 Va 的显式改动项）。

### B4B-F2 —— MINOR：§7.3 reference 正证据区间的构造公式缺失

reference ledger 的 `OpeningClaimsV1.positive_evidence` 需要给出 plan `world_interval` 与 elevation `local_interval` 的具体值——稿只说"source refs 可支持哪些 claim"，没写区间怎么来。两个实现会在 denominator 上分叉。
**要求**：v2 写死构造公式：plan 证据 `world_interval` = GT opening `world_along_interval`（target 原样）；elevation 证据 `local_interval` = 用该 view 受信 frame 对 target 区间做**逆映射**（mirror/sign 由 frame 处理，映射后取升序端点），随后由 Va 标准通道完成 local→world→∩target→∩visible。并注明该构造的性质：reference 证据=「假定图上完整可见该窗」的最大证据，实际可计分范围由 Va 与 visible intervals 相交后收窄。

### B4B-F3 —— NIT：§8.1 GT 侧 interior partition 不需要容差

GT v3 的 zone tiling 由 B4a validator 精确校验（零重叠零缝隙），共享边端点逐位相等——GT 侧共享边归组应为**精确匹配（零容差）**；"tolerance-aware canonical line grouping"措辞只应属产品侧（§8.2）。v2 改措辞，避免实现者往 GT 侧引入无谓容差。

## §17 五项裁决请求（主控裁决）

| # | 请求 | 裁决 |
|---|---|---|
| 1 | 新增 judge-only `score_inputs/view_bindings.json` 受信 GT view/mirror/frame 映射 | **批准**。现役 manifest 无 GT source-view 映射/镜像/方向解算是盘面事实；判卷可信度要求 judge 用自己的受审输入而非产品自报——正是 E1'/Va 设计的 judge 独立性要求。资产进 GT bundle 走独立资产 review 批。 |
| 2 | partial denominator 规则（existence/sill/head=有可见片段记 1；host/along/width=精确 L(A)/L(T)；host 仅 judge-only 关系评分不写回；appearance 本批 NA） | **批准**。scalar claim 可见即可读全值、interval claim 按可见长度配比,语义正确;host 不抢 B5 writer 所有权的切法干净;appearance 无 GT 独立真值,NA 诚实。 |
| 3 | 盘面迁移=`SCORER_SCHEMA "7"→"8"` | **确认**（主控亲核 `run_stage.py:75` 现值 `"7"`；历史记录中的"schema 2 重算"只作旧机制描述，管理记忆将同步纠正）。 |
| 4 | 现役 manifest v1 下每 view 最多一个 completeness source + judge-only overlay 生成 effective manifest（不改 base emitter/RunManifest） | **批准**。`OpeningEvidence` 单 assertion 槽位是现役 wire 事实；效果清单=内存纯函数投影+hash 入 sidecar，不动 production 权威，正确。 |
| 5 | B4b 只交付 PNG 灰纹 NA + sidecar provenance 接缝；HTML assumed/observed 猜色归 B5b | **批准**。与设计 v2.2 批次表分工一致。 |

## 事实核查记录（主控亲核，全过）

1. `scripts/tool_scripts/run_stage.py:75` `SCORER_SCHEMA = "7"`——§1.2/§17.3 属实（我方 memory 的"schema 2"为过时记录，本稿纠正正确）。
2. `tests/test_judge_batch_b.py:414` `complete_total == 14` 断言真实存在——§9.1 legacy 回归锚点属实。
3. sidecar 命名 `score_vs_gt.json`/`grade.png` 落 attempt 目录——§10.1 属实。
4. `facade_applicability.py:348` 附近为正常 flip 计算,无 tautological no-op——§1.2 对 VA-C7 第六项的处置（source-scan 回归封口、不制造清理 diff）成立。
5. Va 公开类型（`FacadeVisibilityLedgerV1`/`ElevationViewBindingV1`/`OpeningClaimsV1`/`OpeningApplicabilityLedgerV1`）与 §6.0/§6.7 引用逐名吻合。

## 正向确认（登记留痕）

- 四 Phase 各带出口 gate + **B4a 落地后逐字对账门 REC-A~D**（§14）——对并行在建依赖的处理完全符合派单要求（冻结合同引用+对账门,零预读）。
- Va=唯一 applicability 引擎贯穿（reference/product/absence 三 ledger 全走同一公开函数;§8.6.1 负证据只消费 Va 输出）。
- 不变量 #5（product declaration 删除不得改 denominator）+ §7.4 双调用测试=VA-C7 精神的正确吸收。
- sidecar v8 身份全覆盖（GT/capability/base+effective manifest/bindings/helpers/tolerances/output/accepted record）+ 全等才 cache hit + 原子 pair 写序——信任根洞（B-M CR-01/Vg CR1/B-O CR4-5 四现家族）的系统性预防。
- NA/REJECTED 两轴分离、denominator 守恒断言、render totality 审计——机读 NA 形状完整（闭 B-04 残余）。
- legacy v2 全量回归锁定（含 sm20 无 GT 行为）+ 零 golden/GT 资产改动。
