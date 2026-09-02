# 模块 7 接线 · 验收 1 真模型端到端（2026-09-02 · GLM 施工席）

**派工单**：[`reviews/request/2026-09-02a_wiring_module7_dispatch_v2.md`](../../reviews/request/2026-09-02a_wiring_module7_dispatch_v2.md) §三 验收 1。

## 输入（真实产物，冻结字节）

- `0_reading/sm25_2f_v2.json` ← 逐字节拷贝自
  [`2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json`](../../experiments/2026-08-23_as_drawn_reading_prototype/out/)
  （通过 `AsDrawnPlanV2` 校验的 22 份新格式产物之一，派工单 §〇 表第 5 行点名的那批）

## 跑的命令

```python
run_correction_evidence_chain(
    base / '0_reading', 'sm25_2f_v2.json',
    out_dir=base / '1_correction',
    profile='exploratory', round_budget=3,
)   # 不传 fixed_responses ⇒ 模型拍真跑
```

## 读数（2026-09-02 03:27，模型=deepseek-v4-pro，llm.yaml section `correction_decision`）

- **elapsed 185.8 s · success=True · exit_reason=success · 2 轮**
- round 0：模型 `select_candidate` 全部 **22** 个待裁决项（thickness_resolution），无 failed_checks
- round 1：新 packet（provisional 已动）→ 模型空决策 + `verdict=accept`（绑新 packet_hash `e2532584…`）
- 残余：open items 0 · 债 3 条（as-drawn 平面 absent 的 support 通道，exploratory 政策表判不挡 success）· degraded walls 0

## 产物

| 文件 | 内容 |
|---|---|
| `1_correction/decision_loop_outcome.json` | `DecisionLoopOutcomeV1` 全量落盘（success/exit_reason 如实） |
| `1_correction/correction_decision_raw.txt` | 模型最后一轮原始响应（`_call_json_llm` 存 last attempt：round 1 的 accept；round 0 的 22 项决策见 outcome.rounds[0].selected_item_ids + decision_hash） |
| `1_correction/correction_decision_thinking.txt` | 模型推理过程 |
| `_run/evidence_chain_route.json` | 路径记录：`route=evidence_chain` · `response_source=model:correction_decision`（⛔ 不是 fixed_responses——模型真跑的证据就在这一行） |

## ⛔ 这条 run 没证明什么

- 只跑了 sm25 的 **2F 一张平面**，不是整个 case（与派工方探针同口径）。
- `success=True` 是决策环的成功（四联条件），**不等于**几何正确——判分归 judge（本单不跑）。
- completion 仍为 `degraded`（3 条 support 通道债随行），模块 6 政策表如实放行。
