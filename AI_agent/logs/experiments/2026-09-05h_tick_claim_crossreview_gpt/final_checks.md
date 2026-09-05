# 最终核验与逐字引文补充

以下命令均在当前 worktree 执行。第二段提交前范围核验；不重跑已经通过的探针。

```sh
git diff --exit-code 75f7732a -- src tests AI_agent/logs/reviews/execution/2026-09-05f_tick_claim_design_rework2.md AI_agent/logs/reviews/verdict/2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md AI_agent/guides/reading_correction_split_guide.md AI_agent/logs/reviews/request/2026-09-05f_tick_claim_design_rework2.md AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt
```

```text
[exit 0]
```

```sh
git status --short
git diff --name-only 75f7732a
git diff --check
```

```text
?? AI_agent/logs/reviews/request/2026-09-05h_tick_claim_design_rework2_crossreview.md
?? AI_agent/logs/reviews/verdict/2026-09-05h_tick_claim_design_rework2_crossreview_gpt.md
AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/README.md
AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/capture.py
AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/evidence.md
AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/legacy_capture.md
AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/legacy_numbers.md
AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/numbers.md
AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/probe.py
[exit 0]
```

```sh
grep -nE 'WholeBuildingOpeningReviewInputV1:|第二步整体把关拿到的输入之一|structural_only_tick_claims: tuple|不变量：bundle|OpeningEdgeTickClaimV1，必须原样|逐节点前缀和.*CALIBRATION_CHAIN_NODE|D2-a 不存在对应行|这条洞口边在这一步之后|∃ k|node_ref 合法|calibration.x 是这张立面唯一被冻结|operand.role == "segment_len"|^DerivedOperandV1:|^    role: Literal|^    ref:  ArtifactPointerV1|^    derivation: Literal|^segment_span_diff:|^segment_span_sum:|^前置：每个 operand|__slots__|validate_evidence_bundle\(self|return _derive_tick' AI_agent/logs/reviews/execution/2026-09-05f_tick_claim_design_rework2.md
```

```text
112:    ∃ k : Decimal(calibration.x.cum_mm[k]) == Decimal(claimed_mm)
195:WholeBuildingOpeningReviewInputV1:
196:    # 第二步整体把关拿到的输入之一，⛔ 不是可选项
197:    structural_only_tick_claims: tuple[OpeningEdgeTickClaimV1, ...]
198:    #  不变量：bundle 里每一条 provenance.confidence == "structural_only" 的
199:    #  OpeningEdgeTickClaimV1，必须原样出现在这个元组里——构造函数机械遍历
235:| **逐节点前缀和**（`cum[i] == cum[i-1] + values[i-1]` 对所有 `i`，精确整数域比较）| **新增、独立的**前置检查 `_require_chain_prefix_consistent`（本稿只给规格，不写实现，⛔ 改动 `evidence_adapters.py` 属另一张施工单）| 同一错误族：`EvidenceContractError("CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM")`，整条链的任何 `node_ref`/`chain_derived` 认领全部拒绝构造——**在构造函数的守卫里堵死，不是先构造出来再指望某个下游校验器发现** |
268:DerivedOperandV1:
269:    role: Literal["axis", "half_wall_thickness", "cum_lo", "cum_hi", "segment_len"]
270:    ref:  ArtifactPointerV1
271:    derivation: Literal["declared_as_half", "half_of_declared_full"] | None
290:        operand.role == "segment_len" ⇒ 同 cum_lo/cum_hi 的锚点检查
346:        __slots__ = ("_artifact",)
357:            validate_evidence_bundle(self._artifact.bundle, self._artifact.frozen_sources)  # 门在前
358:            return _derive_tick_claims_from_frozen_bytes(self._artifact)  # 纯函数，永远从冻结字节算
421:    ⛔ ②b/③ 场景下，D2-a 不存在对应行 ⇒ 本类型**根本不为这条边构造实例**——
423:    这条洞口边在这一步之后仍然是**纯平面实体**，等待第二步 §14.4 的
583:DerivedOperandV1:
584:    role: Literal["axis", "half_wall_thickness", "cum_lo", "cum_hi", "segment_len"]
585:    ref:  ArtifactPointerV1
586:    derivation: Literal["declared_as_half", "half_of_declared_full"] | None  # 仅 half_wall_thickness（F-4②）
666:∃ k : Decimal(calibration.x.cum_mm[k]) == Decimal(claimed_mm)
667:    ⇒ node_ref 合法（不要求 dimension_refs 指向的链与 calibration.x 是同一条命名链——
668:       calibration.x 是这张立面唯一被冻结的权威 x 记录，dimension_refs 只作辅助）
678:segment_span_diff:     结果 = cum_hi_units − cum_lo_units（同链，允许负值，F-4④）
679:segment_span_sum:      结果 = Σ segment_len_units（operands 索引连续，F-4④）
680:前置：每个 operand 的证据档位 == chain_backed 或 role == 声明常量（F-4③，
[exit 0]
```

```sh
grep -nE 'downstream obligation, or' src/agent/correction/evidence_contract.py
grep -nE 'if debt.obligation is None|continue' src/agent/correction/opening_synthesis.py | rg '700:|701:|742:|743:'
```

```text
529:    #: downstream obligation, or ``None`` = no downstream obligation at all
700:        if debt.obligation is None:
701:            continue
742:        if debt.obligation is None:
743:            continue
[exit 0]
```

```sh
grep -nE '权威次序|本图一致性|刻度认领.*第一步|第一步.*逐图独立' AI_agent/guides/reading_correction_split_guide.md
```

```text
1006:| **刻度认领**（这条边指尺寸链哪个节点）| **第一步** | 模型出决定 · **代码出坐标** | ⭐ **零阈值**：认领是判断题，⛔ 不是毫米比较；认不上 ⇒ 落到 §14.2b 的**低一档证据**，⛔ 不是失败 |
1096:- **刻度认领（第一步）= 本批做**：只用**这张图纸自己画出来的数**，外部可证伪、**零建筑先验**
1136:- **两步 = 阶段**（2026-09-04 用户定）：**第一步 尺寸证据裁定**（逐图独立）→ **第二步 空间推理**（跨图）。
1141:第一步 · 尺寸证据裁定（逐图独立，⛔ 跨图的事一件不做）
1145:  ③代码：落值（一档取链上的数 · 二档取像素）→ 重跑本图一致性检查 → 有新的不一致回②（有限轮）
1160:### 15.4 第一步 · 尺寸证据裁定（逐图独立）
1182:**权威次序**：一档 > 二档；跨图冲突时 §14.3 的分工 ——
[exit 0]
```

```sh
grep -nE '唯一途径是提供|冻结字节.*信任根|不在 B2 范围' AI_agent/logs/reviews/execution/2026-09-04w_B2_rework3_execution.md
```

```text
329:  对冻结字节的解析。**要移动装配出来的那个数，唯一途径是提供一份能过门的不同
330:  冻结字节** = 自造一份自洽 reading 产物 = reading 信任根（裁决 §三#3 已裁定
331:  不在 B2 范围）。载体内已无 `_levels` 字段，「换元素」没有对象。
387:   为 reading 信任根、不在 B2 范围（本单 §〇② 重申别再动）。
[exit 0]
```
