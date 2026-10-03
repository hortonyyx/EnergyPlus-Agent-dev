# R2-C 图片 token 校准记录

本记录只使用 10-03 已有账单、已保存请求事件和图片字节，未新增模型请求。可重复脚本为 `calibrate_image_accounting.py`，机器可读摘要为 `image_accounting_calibration.json`，运行时口径见 `AI_agent/design/runtime_image_accounting.md`。

## 结论

- 10-03 Paratera 账单共有 **72,406** 个图片输入 token。
- 仓库现有事件可逐请求核验其中 **62,620** 个，占 **86.48%**。这部分涵盖 58 次 Qwen 图片请求和 8 个型号/北京时间小时桶；公式估算、响应的 `image_tokens` 分项、对应账单桶三者均完全相等，最大绝对误差为 0。
- 这 58 次响应都满足 `prompt_tokens = text_tokens + image_tokens`。因此它们直接反证“Qwen 顶层 usage 一律漏掉图片 token”的旧推断：这些事件的顶层输入已经包含图片，运行时不能再次补加。
- 未覆盖的 **9,786** 个账单 token 分别来自 00:00 的 Qwen3.8-27B 和 Qwen3.8-Flash 桶，各 4,893。仓库没有相应请求事件，无法判断其顶层 usage 是否包含图片，不能用总账差额外推每次请求的行为。
- 另有一次 Qwen 图片请求估算 877 token，但没有模型响应，而且未进入对应账单桶。它归为 `unknown_no_response`，不参与公式误差和账单覆盖结论。
- GLM 的校准量是相对 31-token 文本对照的输入增量，并非接口实报的图片分项。224×224、896×896 两个观察点与公式完全相等；1600×1200 估算 2,453、输入增量 1,314，高估 1,139。旧迁移运行的 10 次 GLM 图片请求合计估算 52,238，但 usage 没有完整文本/图片分项；现有账单也没有 GLM `image_input` 行。GLM 图片顶层包含关系与图片单价仍未知。

## 运行时判定

只有响应同时给出非负整数 `prompt_tokens`、`text_tokens`、`image_tokens`，并满足 `prompt_tokens == text_tokens + image_tokens`，才认定顶层 usage 已包含图片。符合时图片估算单列展示但不重复扣预算；不符合或字段不完整时，服务商实报原样保存，图片估算另加到预算消耗。

人民币金额仅为按当前观察单价计算的估算，不是账单。GLM 图片或缓存单价未知时完整估算为 `null`，另报可计算的已知小计。

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
