# Brief：请 sol 撰写"天正转换器返工"的 GLM 结构化核验清单

**日期**：2026-07-23 · **主控**：Opus 4.8
**撰写方**：sol（GPT 侧，本裁决书作者，最了解攻击面）
**执行方**：GLM（GLM 侧）—— 谁写谁不批：施工 = terra（GPT 侧），审的**判定**由 GLM 出（跨家族），sol 只提供清单不下最终裁决。

---

## 0. 为什么是这个分工

GLM 的能力画像（回溯测实证，[`logs/experiments/2026-07-21_glm_capability_exam/`](../../logs/experiments/2026-07-21_glm_capability_exam/README.md)）：
**验证性审阅**（给定细清单、验锁真绑）= Fable 级；**探索性审阅**（无线索找未知洞）= 不及格。
本次返工的**攻击面已经被你（sol）在裁决书里完整测绘**（9 条出口 + 场景 A/B + 9 门 neuter + hash + PASS 全门），
所以把任务改造成 GLM 的强项 = **照单验证**。你写的清单越细、越把"验什么/什么算不成立"写死，GLM 表现越接近你自己。
这正是上轮 GLM 对合并稿审阅（[`verdict/2026-07-21_tarch_converter_merged_glm_r1.md`](../verdict/2026-07-21_tarch_converter_merged_glm_r1.md) §7b）成功的打法。

## 1. 输入材料

- **你自己的裁决书**（权威）：[`verdict/2026-07-22_tarch_converter_p0p2_sol.md`](../verdict/2026-07-22_tarch_converter_p0p2_sol.md)（9 出口 + 每条失败场景 + 核验方式）。
- **terra 施工单**：[`request/2026-07-23_tarch_converter_rework_terra_dispatch.md`](2026-07-23_tarch_converter_rework_terra_dispatch.md)（含主控对"同墙一致性门"的设计推演）。
- terra 返工产物（施工完成后给你），代码在 `src/agent/judge/tarch_normalize.py` + `tarch_converter_schema.py` + `tests/test_tarch_converter_p{0,1,2}_*.py`。

## 2. 清单要求（output = 一份 GLM 照单执行的核验清单）

把 9 条出口 + 你活体探针里用过的攻击，转成**逐条结构化命题**。每条**必须写死**：

1. **验什么**（一句话断言）。
2. **怎么验**（具体操作：跑哪个命令 / 构造什么几何 / 改哪个值 / 看哪个输出字段）。
3. **什么算成立 / 什么算不成立**（红线判据，数字/布尔，不留"看起来合理"的空间）。
4. **要求 GLM 用独立几何自建**（不复用 terra 的测试夹具期望），凡涉及场景 A/B、九门变异、hash 篡改这类。

**必须覆盖的核验点（下限，你可加）**：
- **G8 真独立**：改 `basis`/`thickness` 但**保持 `offset_native` 不变** ⇒ G8 必须变红（证明不再消费 `offset_native`）；把边法向/offset 用的存量字段挖空 ⇒ G8 仍能从 `p1/p2+basis+thickness` 重算。
- **同墙一致性门**：GLM 独立构造场景 A（错轴线 x=4060 / 左 t=360 / 右 t=120），断言这道门**变红**；再构造一个合法同墙（两侧 t 一致）断言**绿**。丁字/十字接头下的部分重叠配对也要验。
- **场景 B（面积补偿）**：独立构造（小房间 A 被吞成墙材、数量恰好对）；断言近阈值承重门**要求人核、不静默 PASS**。
- **九门变异**：逐门（G1–G10）neuter，断言恰对应必红夹具失败、其余不变（上轮 7 门假锁 = 本次重点复验）。
- **hash gate**：source SHA 改 64 个 `0` ⇒ BLOCK、不 PASS、不写几何。
- **PASS 全门**：任一门 `passed=false` ⇒ 报告非 PASS、bundle 不晋升。
- **G10 未签字**：`verification_status=="candidate"` ⇒ G10 不得 passed、不得晋升。
- **厚度绑证据**：`wall_lines=[]` ⇒ 发 `tarch_wall_thickness_unevidenced`/`tarch_provenance_incomplete`，不静默出厚度；source_map proof_ids 非空。
- **S7 事件坐标**：变厚度墙（前 220mm 厚 300、其余 100 / 中段 100→300→100）⇒ 精确定位变化点，不受合法墙厚上限驱动、不漏检。
- **契约版本**：P0 后加字段 ⇒ request 版本已提升 + 跨版本 hash 兼容测试在位。
- **未接线码**：17 个原未接线诊断码要么真发得出、要么已从 registry 移除（AST 枚举 `_diag` 首参 vs registry 做集合差）。
- **去写死**：native-unit 常量 / LINE 端点反转 / `floors[0]` 单层 ⇒ 已去除或已前置 BLOCK。
- **gt 隔离**：`test_gt_discipline.py` 11/11；converter 无渗透进 gate①/执行器/reading/correction。
- **sm24 端到端**：8 区 / 对称差 0 / 重叠 0 / v3 PASS 仍成立，且现在是"真门通过"。

## 3. 交付

清单落 `logs/reviews/request/2026-07-23_tarch_converter_rework_review_checklist.md`（GLM 执行时把结论回填或另落 verdict）。
GLM 的最终裁决落 `logs/reviews/verdict/2026-07-23_tarch_converter_rework_glm_r1.md`。
写清单时**不要下裁决**（你是清单作者不是本次判官）；把"什么算不成立"写死，让 GLM 逐条给实测依据。
