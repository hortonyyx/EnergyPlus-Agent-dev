# 接头观察到源BIM修订：收工前最后一程

本批唯一一次恢复已正常完成，源变化、原图保真与实际查看均已核验，随后汇总全会话收工。没有追加整案或换例批次。

**结果：新增东侧源隔墙并拆窗，整案仍不采用。** [run19](../2026-09-14_bim_agent_sm24_run19/README.md)用时786.94秒，最终8空间/10窗/8门，自洽与离线查看通过；但新墙被移动0.298m迁就旧门，连续走廊仍错，独立分区severe。五原图/原声明/完整旧观察运输、源逐对象变化及独立重导出通过。模型登记标定的32.57%尺度冲突未处理，两次build后的自动回叠不能证明保真。CLI估算$2.0961823（非账单）。

[实际可查看结果](../2026-09-14_bim_agent_sm24_run19/index.html) · [事后原图复核](../2026-09-14_bim_agent_sm24_run19/post_run_review.md) · [全会话收工](../../worklog/2026-09-14_reconstruction_feedback_session_close.md)

## 输入与用途

- 新run：`2026-09-14_bim_agent_sm24_run19`，从失败整案run18/candidate_01的proposal恢复；不是从采用基点run12继续，也不是自主冷启动。
- 五张原始PNG与原始 `testdata_prompt.json`；完整未改写的 `2026-09-14_sm24_junction_feedback/observation.md`；前一Sonnet观察的两份原始x/y像素扫描JSON。没有原plan声明、GT、评价报告、正确源房间数或开发修正几何。
- 开发指定中段实体分隔/空间连续与受影响开口为本次工作范围，明示旧观察未批准、可能有错；完整原文及测量不筛选正确部分，由工作模型核原图决定是否和如何修改。
- Sonnet medium、900秒单次上限，Claude现有订阅，无付费API/DeepSeek回退。时限是本次局部研究预算，不是首稿速度指标。没有更改生产代码或降低几何拒绝条件。

`scope.md`和`frozen_inputs.json`保存实际提示、来源与散列。每份生成候选应与原seed逐对象比较；完整重建并不等于无历史输入的新生成。旧观察正确部分不可由开发偷偷挑出再计为自主应用。

## 执行与复核

`run_recovery.py --dry-run`已在调用前生成可查输入记录，没有启动模型。正式调用使用同一入口，结束后保存运行时代码快照和一致性检查。

新房间/门窗拆分超出现有 `revise_bim` 局部操作能力，需要完整 `build_bim` 或合适的像素墙网新声明。此次只给原proposal；接口复核另建议后续可保留生成时原始可编辑plan，降低重写/转录负担。该建议没有中途加入本次输入，见 `interface_review.md`。

```bash
python AI_agent/logs/experiments/2026-09-14_junction_recovery_setup/run_recovery.py
```

新run目录必须不存在。普通离线核验不重新调用模型：

```bash
python AI_agent/logs/experiments/2026-09-14_junction_recovery_setup/verify_inputs.py AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run19
python AI_agent/logs/experiments/2026-09-14_quality_feedback_setup/verify_execution.py AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run19
python AI_agent/logs/experiments/2026-09-14_junction_recovery_setup/verify_source_changes.py AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run19
```

源变化脚本以最终选择为准，若仅seed或源失败照实记录；不将编译成功、数量或旧观察一致当作保真结论。原图复核和生成结束后的独立分区评价另存，GT不反馈给生成模型。离线查看复用已有Chromium环境，不安装新依赖。
