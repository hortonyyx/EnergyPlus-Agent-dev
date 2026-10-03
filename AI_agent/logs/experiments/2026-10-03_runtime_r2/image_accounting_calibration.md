# R2-C 图片 token 校准记录

本记录只使用 10-03 已有账单、已保存请求事件和图片字节，未新增模型请求。可重复脚本为 `calibrate_image_accounting.py`，机器可读摘要为 `image_accounting_calibration.json`，运行时口径见 `AI_agent/design/runtime_image_accounting.md`。

## 结论

**R2b 更正（10-03）：** 原校准证明了图片分项与公式匹配，不能证明账单只收一次。Paratera 的 Qwen 两档按含图片的输入总数收文本输入费，还另外收图片行。当前预算为实报总数＋图片量；人民币为（输入总数−缓存）×文本价＋缓存×缓存价＋图片×图片价＋输出×输出价。以下原核对事实与过程保留，旧预算推断明确标为失效。

- 10-03 Paratera 账单共有 **72,406** 个图片输入 token。
- 仓库现有材料可逐请求核验全部 **72,406 / 72,406（100%）**。这部分涵盖 62 次有完整回复的 Qwen 图片请求和全部 10 个型号/北京时间小时桶；公式估算、响应的 `image_tokens` 分项、对应账单桶三者均完全相等，最大绝对误差为 0。
- 这 62 次响应都满足 `prompt_tokens = text_tokens + image_tokens`，反证“Qwen 顶层 usage 一律漏掉图片 token”的旧推断。R2 原文因此写“运行时不能再次补加”，**这一预算推断已失效**：包含图片的输入总数与额外图片行会同时出现在账单。
- 原先未匹配的 00:00 两桶来自 `2026-10-02_paratera_elevation_probe` 的四次既有 Qwen 历史探针。27B 和 Flash 都是 East 2,380 加 West 2,513，各合计 4,893；四个 `response.created` 换算后处于北京时间 00:23–00:27。脚本同时验证 recorded request 的图片 SHA 与实际文件一致。这是读取已有记录，本次新增请求为 0。
- 另有一次 Qwen 图片请求估算 877 token，但没有模型响应，而且未进入对应账单桶。它归为 `unknown_no_response`，不参与公式误差和账单覆盖结论。
- GLM 的校准量是相对 31-token 文本对照的输入增量，并非接口实报的图片分项。224×224、896×896 两个观察点与公式完全相等；1600×1200 估算 2,453、输入增量 1,314，高估 1,139。旧迁移运行的 10 次 GLM 图片请求合计估算 52,238，但 usage 没有完整文本/图片分项；现有账单也没有 GLM `image_input` 行。GLM 图片顶层包含关系与图片单价仍未知。

## R2 原运行时判定（预算部分已被 R2b 覆盖）

只有响应同时给出非负整数 `prompt_tokens`、`text_tokens`、`image_tokens`，并满足 `prompt_tokens == text_tokens + image_tokens`，才认定顶层 usage 已包含图片。R2 原规则在符合时不重复扣预算；不符合时另加图片估算。R2b 保留包含关系的判定，但对账单单列图片的 Qwen 两档始终额外扣图片量，优先采用接口实报分项，缺失时才用公式估算。

人民币金额仅为按当前观察单价计算的估算，不是账单。GLM 图片或缓存单价未知时完整估算为 `null`，另报可计算的已知小计。

## R2b 逐项反例与金额复算

北京时间 14:00 的 9 次 R1 立面请求：输入 70,026（文字 58,958、图片 11,068），输出 56,951。对应账单文本输入、图片输入、输出三行分别为 70,026、11,068、56,951，逐项误差为 0。实报总数 126,977，预算扣量 138,045。每百万单价为输入/图片 3 元、输出 12 元；按每个小时账单行舍入五位小数，0.21008＋0.68341＋0.03320＝**0.92669 元**，金额误差为 0；未舍入小计为 0.926694 元。

06:00 的 187,838 文本＋19,456 缓存＝207,294，比归档回复 207,095 多 199，属于归档外请求。全账实报口径 778,052 等于文本、缓存、输出之和；账单另加的 72,406 正是图片行。不能把 06:00 说成逐请求完全匹配。

新增 [离线反例脚本](r2bc/reconcile_billing.py)和[九条原始 usage／三行账单复算](r2bc/billing_reconciliation.json)，保留原归档与 CSV 的 SHA-256。R2b 新增模型请求为 0。原 `image_accounting_calibration.json` 保留为当时的公式校准证据，不改写历史产物。

## 复现

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r2/calibrate_image_accounting.py
```

可选地审计未入库的旧 GLM 迁移运行：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r2/calibrate_image_accounting.py \
  --run /workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-10-03_runtime_r1/runs/migration_sm24_glm_paratera
```

脚本输出 `external_requests_made: 0`。引用证据与 SHA-256 全部记录在 JSON 摘要中；本目录不复制已有归档或运行字节。
