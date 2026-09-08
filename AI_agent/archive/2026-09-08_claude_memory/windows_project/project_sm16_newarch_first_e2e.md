---
name: sm_16_newarch 半人工端到端首跑 + EP 全链路通验证
description: 2026-05-07 半人工架构 14 节点全通 + L4 EP 真跑实证（手工修一行 Construction 后）；T-vertex 不卡 EP；真 fatal = fenestration SimpleGlazing layer 兼容性 bug
type: project
originSessionId: 7dd08f4a-2004-433d-a281-03e9103623c8
---
`smalloffice_16_newarch` 是 sm_16 的拷贝，专为验证 2026-05-06 半人工架构改造做的首次端到端测试。

**Why:** 验证半人工 intake (Opus) + 自动下游 (DeepSeek V4 pro × 9 subagent) 14 节点 LangGraph 通不通；A 段 4 项闭环后第一次真正端到端跑通；2026-05-07 晚追加真跑 EP 验证完整链路。

**How to apply:**
- 引用本 case 时记得它**不是**真实建筑案例，是架构测试用拷贝；真正的能力评测请用 sm_13/14/15/16/17 + GT 集
- **架构通透性 anchor**：半人工 intake → 自动下游 → IDF → EnergyPlus 全链路 100% 通，零架构层 bug
- 已证 PASS：14 节点机制 / DeepSeek tool-calling 多轮 ReAct（thinking-off）/ L1 Pydantic / L2 cross_ref errors=[] / L4 EP 真跑（手工 glazingfix 后 `Completed Successfully` / 0 severe / 9 warnings / 14.8 秒，全年 RunPeriod）
- T-vertex 实证**不卡 EP**：warm-up 阶段 0 几何 severe → plan.md B0' 关闭，validator 永久保持 warning
- 真 fatal 已定位：fenestration SimpleGlazing layer 兼容性 bug（详见 memory `project_fenestration_glazing_layer_bug`），不调 prompt 等 idfpy
- artifacts：原始 IDF [`temp_20260507_154141.idf`](../../../test_data/SmallOffice/smalloffice_16_newarch/output/temp_20260507_154141.idf)；glazingfix IDF [`temp_20260507_154141_glazingfix.idf`](../../../test_data/SmallOffice/smalloffice_16_newarch/output/temp_20260507_154141_glazingfix.idf)；EP 跑成功结果 `output/ep_run_glazingfix/`
- baseline 全档：[`runs/2026-05-07_sm_16_newarch_v4pro_no_sim_v1/`](../../../test_data/test_baseline/runs/2026-05-07_sm_16_newarch_v4pro_no_sim_v1/)（含 2026-05-07 晚的 Addendum）
- 总耗时 ~28 min（construction ~20min + surface ~4min 占大头），完整 trace 在 `test_data/SmallOffice/smalloffice_16_newarch/output/pipeline_run.log`
- L3 OpenStudio 视察待用户做
