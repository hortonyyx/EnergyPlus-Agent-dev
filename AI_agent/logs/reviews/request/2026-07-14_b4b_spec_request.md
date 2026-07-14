# B4b 批施工细稿出稿请求（派 sol 次高档，2026-07-14）

**任务**：为 C2 的 **B4b 批（段级 scorer + per-claim denominator/NA + sidecar 身份扩 + render_grade v3）**出代码级施工细稿，落盘 `AI_agent/proposals/c2_b4b_detail_spec.md`（v1）。**本轮只出稿：不改任何代码、测试、golden、gt 资产或其他文档。**

## 1. 权威输入（优先序）

1. [AI_agent/proposals/c2_full_unlock_design.md](../../proposals/c2_full_unlock_design.md) v2.2：**B4b 行**＝段级 plan/elevation scorer + `NOT_APPLICABLE(unobserved)` 机读结构/独立 denominator/灰纹画法 + sidecar 身份扩（gt hash/schema、capability、manifest hash、helper version，bump SCORER_SCHEMA）+ per-claim denominator/NA 机读形状（闭 B-04 残余）+ 不支持组合在评分入口显式 NA/拒绝；依赖 B4a+Va；**XL，4 子件顺做**。另 §E2'（opening×claim 判卷/证据通道×属性矩阵/知识表 assumed 语义）、§T'（sm26 验收器=内壁窗 x/宽计分·z 记 NA·HTML 猜测色）。
2. [AI_agent/proposals/c2_b4a_detail_spec.md](../../proposals/c2_b4a_detail_spec.md) **v2 定稿**：§15.1 B4b 稳定输入清单（含 visible_intervals=Vg 派生量声明）、§15.2 真实 GT 提升联合门（B4b 是其第 3 条）、§6.2 loader 契约（`load_gt()` 遇 v3 fail=B4b 迁 typed API 的机械门）。**注意：B4a 代码尚未施工（Phase A 同期在建）——B4b 稿必须把 B4a wire 当冻结合同引用，开工前置门设「B4a 对应 Phase 施工落地后逐字对账」条款，禁预读未建之物（B2b r1 教训）。**
3. [AI_agent/proposals/c2_va_detail_spec.md](../../proposals/c2_va_detail_spec.md) v2 + **已收录实码** `src/agent/correction/facade_applicability.py`（1070 绿在册）：Va ledger 输出形状=B4b 唯一 applicability 输入；`FacadeVisibilityLedgerV1` 输入类型与 A0 §4.1 冻结的 `facade_segments_sha256` preimage（B4b 的 GT→Va 适配器要按它生产 hash）；**VA-C7 挂账六项本批吸收**（第八词拒例/重复 opening_id/悬空 source 显式拒例/产品删声明双调用对照/凹形多段 fixture/facade_applicability.py:348 no-op assert 清理——判词 [2026-07-14_va_construction_review_r1.md](../verdict/2026-07-14_va_construction_review_r1.md) r2 节）。
4. **现役判卷面实码（出稿前亲自读盘）**：`src/agent/judge/{reading_score,correction_score,elevation_score,score_policy,verdict}.py`、`scripts/tool_scripts/{render_grade,_grade_transform,score_reading_vs_gt}.py`、`scripts/tool_scripts/run_stage.py` 的 score sidecar/`scorer_schema` 现状与缓存键。
5. **completeness user/dataset 生成通路**（Va 细稿 §1.2 显式移交 B4b 的接缝）+ `src/agent/execution/view_manifest.py` 实码（CompletenessAssertion/三声明家族）。

## 2. 上位定案（不得偏离）

- **gt 铁律**：scorer/judge 侧可读 gt；生产路径零 import——B4b 全部落 judge 侧。
- **判卷容差=judge 侧独立尺**（correction.yaml 不复制）；新容差走配置+A0 登记，禁裸字面量。
- **NA ≠ 0 分 ≠ 折半**：`partially_applicable` 按 Va 精确区间分区制定 per-claim scorer policy（Va 稿 §8 移交条款）；denominator 独立、per-claim 机读形状；unobserved 灰纹画法。
- **不支持组合评分入口显式 NA/拒绝**（闭 B-04 残余），禁静默跳过。
- sidecar 身份扩必须 bump `SCORER_SCHEMA` 并保持老件自动重算兼容（现状=schema 2 老件重算机制）。
- 零 golden 改动；v2 gt case（sm20/sm21）判卷行为回归锁定。
- **XL 批**：给 4 子件顺做的 Phase 切分，每 Phase 独立可验收、可单独派工。

## 3. 细稿纪律（硬要求）

- 累计式自包含施工合同（新执行者只读本稿即可施工；禁「沿用 vN 未变」）；精确类型（pydantic strict/Literal）；签名、wire、gate id、错误码、测试族全写。
- 施工前置门只断言**已收录依赖**的机械条件；对 B4a 未建件设显式「落地对账门」而非预读。
- 明确批次边界：只放行 B4b；不放行 B5/B5b/B6 顺带施工。

## 交付

1. 细稿落盘 `AI_agent/proposals/c2_b4b_detail_spec.md`。
2. 回复只给 terse report（稿结构概要/关键定案与裁决建议/review-ask 自报不确定与需主控裁的判断题），不贴稿全文。

审向：**Fable 最高档交叉审（GPT 侧稿→Claude 侧审，谁写谁不批）**。
