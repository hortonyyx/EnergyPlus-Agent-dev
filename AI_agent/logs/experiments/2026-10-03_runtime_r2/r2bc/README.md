# R2b / R2c 交付

派工：[brief_r2bc.md](../brief_r2bc.md)，续接基点 `d3a09a90`。工作树 `.worktrees/astra-r2`，分支 `dev/astra-r2-20261003`；只在本分支提交，不合入、不推送。冻结 Agent 仍为 `5bb10538`。本报告给出自检结果，项目验收由 Opus 维护。

## R2b：账单口径修正

Paratera Qwen3.8-27B / Qwen3.8-Flash 的输入总数已经含图片，但账单另列图片收费。现在人民币按（完整输入−缓存）×文本价＋缓存×缓存价＋图片×图片价＋输出×输出价计算；预算按实报总数＋图片量扣除。优先用服务实报图片分项，缺失时才用公式估算，并标为 `formula_estimate`。请求前也额外预留图片行；模型上下文长度不重复计算图片。根账、子账、恢复后的账本均采用相同口径，原 `usage` 不改写；旧结算缺少新字段时保留其历史语义。

反例使用现有 R1 立面归档的 9 次真实回复，本项新增模型请求 **0**。[逐请求原始 usage 和逐行复算](billing_reconciliation.json)由 [reconcile_billing.py](reconcile_billing.py)生成，源归档与账单 SHA-256 一并记录。

| 北京时间 14:00 账单行 | 回复复算 token | 账单 token | 误差 | 按行舍入金额 |
| --- | ---: | ---: | ---: | ---: |
| 文本输入（含图片） | 70,026 | 70,026 | 0 | ¥0.21008 |
| 图片输入 | 11,068 | 11,068 | 0 | ¥0.03320 |
| 输出 | 56,951 | 56,951 | 0 | ¥0.68341 |

输入文字分项为 58,958；输入总数为 70,026。实报总数 126,977，预算应扣 **138,045**。先按小时汇总每个账单行，再舍入五位小数，金额合计 **¥0.92669**，误差 0；未舍入小计为 ¥0.926694。06:00 的文本＋缓存是 207,294，归档输入 207,095，差 199 属于归档外请求，不声称完全匹配。全账 778,052 的实报口径之外，另有 72,406 图片 token 收费。

[原校准说明](../image_accounting_calibration.md)、[设计说明](../../../../design/runtime_image_accounting.md)与 [R2 README](../README.md)均已更正，保留原公式核对过程和历史产物。GLM 在 Paratera 是否另收图片仍未知，未套用 Qwen 规则。

## R2c：GLM 订阅线路

新增 `--provider glm-subscription --model glm-5.3-flash`，与 Paratera 并存。单跑入口、外部协调入口及配置校验共用路线规则。凭据只由主工作树 `/workspaces/EnergyPlus-Agent-dev/.env` 读取 `GLM_API_KEY` / `GLM_BASE_URL`；不回退环境变量，不接受其他凭据文件。端点固定为 `https://open.bigmodel.cn/api/coding/paas/v4`，密钥只放 HTTP 请求头，不进事件或版本记录。

默认输出上限 **32,000**。实际请求发送 `model`、`messages`、`max_tokens`、`stream=false`；有工具时发送 `tools`、`tool_choice=auto`；图片以已留存字节的 `image_url` 发送。默认不发送 `temperature`、`n`、`thinking`、`enable_thinking`、`reasoning_effort`。显式 temperature 可传；未经本端点确认的思考覆盖参数会被拒绝，使用服务默认值。

[官方模型说明](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash.md)列有温度和思考选项，但不能据此宣称它们在这条订阅端点的实际效果。检索记录见 [provider_documentation.json](provider_documentation.json)。本次只将实测发送与回报作为证据；没有把请求参数当作服务生效证明。旧 Claude Code 的 `effort=medium` 如何映射到服务参数未被捕获，精确的隐藏客户端条件仍未知。新配置不猜测这一映射。

订阅回执标明 `billing_mode=subscription`，人民币完整估算及已知小计均为 `null`；不生成按量价格。token、调用数、时间上限照常执行，离线反例验证了 token 和时间不足时发送前停止。图片没有完整包含关系分项时继续保守加图片估算，不能把预算扣量解释为订阅费用。

### 真实小测（4 / 6 次）

独立硬限账本：[subscription_requests.jsonl](subscription_requests.jsonl)。4 次均成功返回，无失败、超时、重试、备用线路或整案请求。合计 **1,499 实报 token**，两组运行时间约 **19.01 秒**；订阅按量人民币估算为空。新增 Paratera / DeepSeek 请求为 0。

| 请求 | 检查 | 输入 | 输出（其中思考） | 结束原因 |
| --- | --- | ---: | ---: | --- |
| 1 | 256×256 图片＋`report_color`，正确返回 green | 325 | 30（18） | tool_calls |
| 2 | 工具返回送回模型，回答 OK | 385 | 3（0） | stop |
| 3 | 512-token 小上限 | 78 | 512（509） | length |
| 4 | 短提示补救，回答 OK | 117 | 49（46） | stop |

首轮图片请求返回 `reasoning_content` 85 字符；截断与补救两轮分别回报 1,058、225 字符。第二轮工具往返接受了历史消息中服务回传的思考字段；这仅证明本次往返成功，不比较思考质量。截断轮的整个 assistant 输出没有进入补救请求，补救请求无思考字段、无残缺工具调用。图片组实报 743，保守图片附加估算 166，预算扣 909；文本组扣 756，合计扣 1,665。

[小测摘要](subscription_probe_result.json)、[图片与工具结果](visual_tool_result.json)、[截断结果](truncation_result.json)、[逐字节离线核验](delivery_verification.json)。原始请求/响应/事件/图片保存在 [压缩归档](subscription_probe.tar.xz)与 [manifest](subscription_probe_manifest.json)中；已有 `uv.lock` 用路径＋哈希引用，不重复入仓。`subscription_probe.py` 是本轮已执行的一次性小测，**不作为复验命令再次执行**。

### 迁移配置与启动

[sm24 订阅单跑配置](configs/migration_sm24_glm_subscription.json)：冻结工具、3000 秒、24 个候选、无委派，预计 **45 次请求**，硬停 60 次模型 / 120 次工具 / 4,000,000 token。与 10-02 基线核验任务正文逐字相同：SHA-256 `a05ae6d543fdd14076a46859c8b4e2fa781f560a0ddfcce6d1948597632fa795`；五张原图及绘图指引也核对一致。任务预算参数、输出上限与实际发送参数全部显式留存。本轮只检查配置，整案留给 Opus 启动。

从本工作树根执行：

```bash
PYTHONPATH="$PWD" python -m src.agent.runtime_r1_preparation launch \
  AI_agent/logs/experiments/2026-10-03_runtime_r2/r2bc/configs/migration_sm24_glm_subscription.json \
  --case sm24_glm_subscription
```

### 回归与复验

短回归 **319 / 319 通过**（170.96 秒），覆盖 stage 0–3、R1、R2 及新增 13 项反例；长任务故障矩阵 **10 / 10 通过**（1,485.74 秒）；冻结工具 75 步回放 **3 / 3 通过**（585.92 秒）。去重合计 **332 / 332 通过**，无失败、错误或跳过。最终结果见 [validation.json](validation.json)；各组保留原始日志、JUnit、源文件哈希，三组运行期间源码均未变化。本次回归新增模型请求为 0。

离线复验，无模型调用：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r2/r2bc/verify_delivery.py
PYTHONPATH="$PWD" python -m src.agent.runtime_r1_preparation check \
  AI_agent/logs/experiments/2026-10-03_runtime_r2/r2bc/configs/migration_sm24_glm_subscription.json
```

范围审计、凭据排除检查和提交记录在 [scope_audit.json](scope_audit.json)。冻结工具、指引、几何、原执行模块、项目管理文档、派工单、R1 历史配置及历史证据均未改。本轮没有委派子代理。

提交：`6e9c6c10` 修正账单图片行、预留与结算并补真实反例；`4acbaa5b` 接入 GLM 订阅、配置与 4 次小测证据。最终文档和回归归档以单独收尾提交交付。
