# Va 批代码级施工细稿出稿请求（派 sol 次高档，2026-07-12）

**任务**：为 C2 的 **Va 批（opening×claim applicability 薄适配）**出一份代码级施工细稿，落盘 `AI_agent/proposals/c2_va_detail_spec.md`（v1）。**本轮只出稿：不改任何代码、测试、golden 或其他文档。**

## 1. 权威输入（优先序）

1. [AI_agent/proposals/c2_full_unlock_design.md](../../proposals/c2_full_unlock_design.md) v2.2：§E1'（Vg/Va 纯函数、frame 拆两层）、§E2'（证据通道×属性矩阵、opening×claim 判卷、unobserved-NA）、C-04（Vg/Va 定名分工）、§DAG 与批次表 Va 行（`Va(Vg 输出, B-M manifest, opening claims)`，依赖 B-M+Vg，S 档）、B4b 行（Va 的唯一下游消费者：段级 scorer + per-claim denominator/NA 机读形状）。
2. [AI_agent/proposals/c2_vg_detail_spec.md](../../proposals/c2_vg_detail_spec.md) v3 + **已收录实码**：`src/agent/correction/facade_visibility.py`（Vg 纯核，含 `FacadeSegment` 可见段派生）、`facade.py`（frame 拆两层）、`finalize.py`（materialize 接线）、`feature_state.py`（中央 release map）。以实码为准。
3. [AI_agent/proposals/c2_bm_view_manifest_spec.md](../../proposals/c2_bm_view_manifest_spec.md) v6 + 已收录实码：`src/agent/execution/claims.py`、`view_manifest.py`（受信视图清单、CompletenessAssertion、三声明家族）。
4. [AI_agent/proposals/c2_b2_detail_spec.md](../../proposals/c2_b2_detail_spec.md) v6（schema v3 类型、FacadeSegment 约束、feature-state 合同）。

## 2. Va 的设计定位（上位定案，不得偏离）

- `Va(Vg 输出, B-M manifest, opening claims) → opening×claim applicability`：**gt-blind 纯函数**；judge 与执行器各拿**自己的输入**调**同一函数**——不破 gt 铁律（gt 只 gate②/人可读），解 B4↔B5 循环。
- Va 是**薄适配**：不重算几何、不重派生可见段（那是 Vg 的），只把「段可见性 × 视图清单 × 每窗每属性的证据声明」对成判卷可用的 applicability 判定（含 `NOT_APPLICABLE(unobserved)` 语义的输入基础）。
- 消费者 = B4b 段级 scorer（per-claim denominator / NA 机读形状）。Va 细稿必须给出 B4b 可直接消费的输出类型与稳定形状。
- 建筑复杂度可扩展性铁律：不得烤死"四标准立面/矩形"假设——C2 词汇表封闭 {逐层平面, 四标准立面, 补充平面, 总平}，但接口形状要给 C2.1（局部/内院立面开放集）留缝。

## 3. 细稿纪律（硬要求）

- **累计式自包含施工合同**：新执行者只读本稿即可施工；禁止"沿用 vN 未变"式引用；签名、wire 形状、gate id、审计形状、测试族全部写全。
- 精确类型（pydantic strict / Literal），无隐式默认容差；新容差如需，走 correction.yaml + A0 登记，禁裸字面量。
- 给出施工前置门（只断言已收录依赖的机械条件，不预读本批自建之物——B2b r1 教训）与施工后自检的拆分。
- 明确批次边界：本稿只放行 Va 施工；不放行 B4a/B4b/B5 顺带施工。
- 设计 v2.2 的 C-03/C-04 条款已并入其正文，出稿前先对齐。

## 4. 交付

1. `AI_agent/proposals/c2_va_detail_spec.md`（v1，中文，版本史只记已发生事实）。
2. 回复 INLINE 只给 terse report：稿件结构一览 / 关键设计取舍 / **review-ask 段**（自报哪些处没把握、做了判断取舍、建议主控复核重点；无则注明 none）。**不要贴稿件全文。**

审向：Fable 最高档交叉审（谁写谁不批）。
