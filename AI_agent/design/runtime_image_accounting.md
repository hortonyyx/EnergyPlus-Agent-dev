# 运行时图片 token 与费用记账

## 目的与口径

模型请求包含图片时，运行时同时保存三类数，不能互相替代：

1. **服务商实报 token**：原样保存响应中的 usage，是可追溯的上游事实。
2. **图片 token 估算**：按实际发送图片的解码尺寸和模型档案计算，用于发送前预算，也用于响应缺少可靠图片分项时补足预算消耗。
3. **人民币估算**：按仓库记录的单价估算，必须标注为 estimate，不能称为账单金额。单价或分项未知时，完整金额为 `null`，同时保留可计算的已知小计。

若没有服务商 usage，预算账本继续保留请求时的保守预留，不用估算值伪造一次实报结算。

## 图片公式

设原图宽高为 `w, h`，模型档案的 patch 大小为 `p`、merge 大小为 `m`，网格因子 `f = p * m`。先把宽高规整到 `f` 的整数倍，再依据档案的最小、最大像素数等比例缩放并再次规整。图片 token 为：

```text
floor(resized_width / f) * floor(resized_height / f) + 2
```

- Qwen3.8-27B / Qwen3.8-Flash：`p=16, m=2, f=32`，像素范围 65,536 到 16,777,216。
- GLM-5.3-Flash：`p=14, m=2, f=28`，像素范围 12,544 到 6,272,000。

实现读取持久化 `AdapterRequest.images[].sent` 所指向的实际发送字节，重新解码尺寸，因而恢复运行后仍可重建相同估算。它不使用原始图片尺寸，也不按 base64 字符数计费。

## 避免重复记账

`image_tokens` 分项出现本身不足以证明顶层输入已包含图片。只有响应同时提供非负整数 `text_tokens`、`image_tokens` 和 `prompt_tokens`，且满足：

```text
prompt_tokens == text_tokens + image_tokens
```

才把顶层 usage 认定为已包含图片，预算消耗直接采用服务商实报总数。其他情形保留实报总数不变，并把发送时的图片估算单独加到预算消耗：

```text
effective_budget_tokens = provider_reported_total + image_tokens_estimate
```

该规则故意要求完整等式证据。若以后服务商增加明确的“顶层已含图片”结构化声明，可以新增等价的可信判断；不能根据供应商名称或仅有一个分项推断。

## 费用估算

Paratera 当前观察单价按每百万 token 计：

| 模型 | 未缓存文本输入 | 图片输入 | 缓存输入 | 输出 |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | ¥3.0 | ¥3.0 | ¥0.6 | ¥12.0 |
| Qwen3.8-Flash | ¥1.0 | ¥1.0 | ¥0.1 | ¥3.0 |
| GLM-5.3-Flash | ¥0.8 | 未知 | 未知 | ¥2.8 |

Qwen 的图片单价由 10-03 导出账单观察到与文本输入同价。GLM 导出账单没有 `image_input` 行，图片和缓存单价均不能从现有证据确认。因此 GLM 图片请求的 `estimated_cost_cny` 为 `null`，`known_cost_components_cny` 只累计已知的文本和输出部分。

## API 与恢复

- `get_cny_price_schedule(model, route_id=..., provider=...)` 返回已知单价表；无匹配供应商或型号时返回 `None`。
- `account_request_usage(raw_usage, image_tokens_estimate=..., pricing=...)` 生成单请求回执，分别给出实报、图片估算、预算消耗、完整人民币估算和已知小计。
- `request_accounting_from_store(store, request_event_id, usage=None)` 从事件库和已发送图片字节恢复单请求记账；未显式传 usage 时查找对应响应。
- `summarize_request_accounting(records)` 生成根任务合计，并按模型和 task 单独聚合，子任务可以独立核查。
- `BudgetSettlement.effective_tokens` 是预算账本实际扣减口径；`actual.tokens` 仍保持服务商原始 usage。

## 10-03 离线校准

校准脚本只读取已有事件、压缩证据和账单 CSV，不发模型请求：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r2/calibrate_image_accounting.py
```

已有 63 个 Qwen 图片请求中，62 个有完整响应分项。这 62 个请求的公式估算与响应 `image_tokens` 均逐请求完全相等，总计 72,406，最大绝对误差 0；对应全部 10 个型号/北京时间小时账单桶也完全相等，覆盖账单 72,406 / 72,406（100%）。其中北京时间 00:00 的两个桶来自四次既有 elevation probe 历史请求：27B 和 Flash 都是 East 2,380 加 West 2,513，各合计 4,893；recorded request 图片 SHA、实际文件尺寸、`response.created` 和 usage 均由离线脚本交叉核验，本轮没有新增请求。另有一个估算 877 token 的请求没有模型响应，账单桶不包含它，分类为未知而非误差。

GLM 的校准量是相对 31-token 文本对照的输入增量，并非接口实报的图片分项。224×224 和 896×896 两个点与该增量完全相等；1600×1200 点估算 2,453，输入增量 1,314，保守高估 1,139，整请求点误差 84.68%。旧迁移运行的 10 个 GLM 图片请求合计估算 52,238，但原始 usage 没有文本/图片完整分项，只能归为未知。现有账单也不能说明 GLM 图片是否另计费。

机器可读结论在 `AI_agent/logs/experiments/2026-10-03_runtime_r2/image_accounting_calibration.json`。其中只引用已有大证据的路径和 SHA-256，不复制原文件。

## 覆盖边界

- Qwen 的账单校准覆盖已保存完整分项的 62 次请求和全部 10 个型号/小时桶；另一个没有响应的 877-token 请求仍然未知，不能用账单匹配代替缺失的单请求 usage。
- GLM 公式只有三个点，且大图点明显保守；它适合预算上界，不是账单复刻公式。
- GLM 图片与缓存单价未知，因此只报告已知人民币小计。
- 汇总只有在每次请求均有 usage 时才给出完整实报/预算合计；缺失请求不会被静默当作零。
