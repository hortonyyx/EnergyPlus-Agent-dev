---
name: haiku-downgrade-model-is-lever
description: Haiku4.5降级测试坐实模型能力是reading主导杠杆·脚手架托不起弱VLM·CV提日程·Sonnet5定为baseline
metadata: 
  node_type: memory
  type: project
  originSessionId: 1d115693-1854-4020-aa2f-deef499bb008
---

**2026-07-05 Haiku 4.5 降级测试（单变量 A/B，登记在册）**：同一套完全恢复的脚手架（skill/reading 内容哈希与 Sonnet 5 基线逐字节相同）、同 case（sm21 满家具双层）、同判卷尺、同冷启隔离协议，**唯一变量=reading 模型**。Haiku 4.5 vs Sonnet 5 基线（`run_2026-07-02_sonnet_flow_e2e`）。

**结果（reading vs gt 坐标对账）**：Haiku **平面墙 0/9·平面窗 0/7·过度分割+9·立面窗 0/15(17 extra)·四立面全 ambiguous**，仅外框 footprint 8/8 + 楼层线对；Sonnet 5 = 9/9·7/7·15/15·0.0m。除 trivially-dimensioned 外框/楼层线外**全线归零**。

**裁决（用户 2026-07-05 定）**：① **模型能力是主导杠杆·脚手架有它托不起弱 VLM 的能力地板**（约束能提示"读准/别过度分割/窗中锚定"，但弱模型满家具图上感知本身错，脚手架给不出它看不到的）。② **非方差**（0/15、0/9 整体坍塌，不同于 Sonnet 4.6 窗 4-11 方差带；n=1 已定性）。③ **CV 提上日程**（Phase C 经典 CV 工具箱当 VLM 看图小工具——sm21_pre 好 reading forensics 证 Sonnet 5 是自发写 CV 才拿 0.0m，弱 VLM 无此拐杖即崩；见 [[reading-cv-toolkit-methodology]]）。④ **Sonnet 5 那次 run 定为 reading 参考 baseline**。

run 停在 J0 characterization stop 未推下游（DeepSeek 额度未花）。实验日志 `logs/experiments/2026-07-05_haiku_downgrade_test/`。关联 [[reading-quality-investigation-2026-06-24]]（脚手架恢复=墙/结构可恢复但窗位残留指向模型，本次把"模型主导"推到极端弱模型坐实）+ [[standardize-test-flow-and-judge-arch]]。
