# R2 交付：截断补救、输出上限、图片记账、Agent 版本登记

派工基点 `543beae3`，分支 `dev/astra-r2-20261003`。全部改动与提交仅在 Astra R2 工作树；不合入、不推送。验收由 Opus 完成，本目录不改写项目验收结论。

## 实现与验收入口

| 项 | 实现及自评 | 证据 |
| --- | --- | --- |
| A 截断补救 | 原始回复全额结算，整条截断回复不执行任何工具调用；记独立事件，用短提示继续。默认每任务连续补救最多 2 次、根运行累计最多 3 次，子角色和摘要请求均计入；超出仍为 `incomplete_response`。实现通过定向反例。 | `tests/test_runtime_r2_truncation.py`；[真实小测](truncation_probe_result.json)、[逐请求核验](truncation_evidence_audit.json) |
| B 输出上限 | GLM 建议 32,000，Qwen 两档建议 16,384；低于建议值先拒绝，只有非空理由可显式放行。理由写入配置与回执，R1 历史配置字节不变。 | `model_profiles.json`、`output_limits.py`；`tests/test_runtime_r2_output_limits.py` |
| C 图片记账 | 实报、图片估算、人民币估算分列，缺失用量保留预留。图片计入根账与子账；有完整等式证明实报已包含图片时不重复相加。实现与可匹配部分通过；原验收前提存在下述反证，剩余账单和 GLM 单价未核实。 | [校准说明](image_accounting_calibration.md)、[摘要](image_accounting_calibration.json)、[脚本复算](image_accounting_recomputed.json)；`tests/test_runtime_image_accounting.py` |
| D Agent 版本 | 登记 45 个工具、指引与任务说明依赖，核验四种 MCP 目录。运行记录当前版本；未经登记的修改被拒，登记后可用，历史 `5bb10538` 保留。 | [交付细节与命令](agent_version_registry_delivery.md)；`tests/test_runtime_agent_registry.py`、`tests/test_runtime_frozen_tools.py` |
| E 范围与回归 | 冻结工具、指引、几何、原执行模块、项目管理文件、派工单与历史配置不改。最终回归结果以 [最终汇总](validation_final.json) 为准；初次失败及修正理由保留。 | `validation/`、[范围核验](scope_audit.json)、[改动与提交清单](change_manifest.json) |

运行设计：[截断与上限](../../../design/runtime_r2_recovery.md)、[图片记账](../../../design/runtime_image_accounting.md)。

## 真实截断小测与用量

GLM-5.3-Flash / Paratera，纯文本、无工具，故意把输出上限设为 128，并写明低上限理由。
首轮要求连续列出 1–1000；截断后按系统约定仅回复 `OK`。这是有意构造的协议小测，不代表复杂建模任务会自行恢复质量。

| 请求 | 输入 | 输出（含思考） | 其中思考 | 结束原因 |
| --- | ---: | ---: | ---: | --- |
| 1 | 85 | 128 | 8 | length |
| 2 | 124 | 32 | 29 | stop，回答 OK |
| 合计 | 209 | 160 | 37 | 369 token，约 4.01 秒 |

共 2/5 次授权请求，无失败、超时或重试；按文本单价估计 ¥0.0006152，**不是账单**。
第二次请求没有截断回复的 assistant 消息或思考，只有新增短提示。请求计数与结算见独立账本
`paratera_requests.jsonl`；没有新增图片校准、整案、DeepSeek 或 GLM 订阅调用。

新归档 `live_truncation_probe.tar.xz` 与 manifest 保存本次小测；同仓库字节改为路径＋SHA-256 引用。
第 1 次迁移失败的原始回复仅引用原路径与哈希，不复制原运行。离线反例完整结算其 63,420 token，
并验证 45,034 字思考、18 字可见输出、16,377 思考 token 的截断事件。
小测发生在 R2 集成中段；之后补齐的根累计限制、登记文件闭包和摘要恢复由最终离线检查验证，没有重复真实小测。

## 图片口径和误差

公式沿用模型处理器的网格缩放：尺寸规整并按最小/最大像素范围等比例缩放后，
`tokens=(缩放宽/f)×(缩放高/f)+2`。Qwen `f=32`，像素范围 65,536–16,777,216；
GLM `f=28`，范围 12,544–6,272,000。读取实际发送字节的尺寸，恢复运行可按相同证据重算。

58 次 Qwen 回复、8 个型号/小时账单桶匹配 62,620 图片 token，占账单 72,406 的 86.48%；
逐请求公式、实报图片分项和已匹配账单三者误差均为 0。余下 9,786（北京时间 00:00 两桶各 4,893）缺对应事件；
另有一次 877-token 图片请求没有回复，均保留未知。

这些 58 次回复全部满足 `prompt_tokens=text_tokens+image_tokens`，反证“顶层实报总是漏图片”的旧推断。
实现保留原始 usage，仅当这条非负整数等式成立时不重复补记；分项不完整时另加图片估算作保守预算。
这是对证据前提的纠正，没有放宽预算或修改历史记录，需 Opus 在维护全局说明时复核。

GLM 224×224、896×896 与相对 31-token 文本对照的输入增量吻合；1600×1200 估算 2,453、增量 1,314，
高估 1,139（整请求误差 84.68%）。这不是接口实报的图片分项。旧迁移 10 次图片请求估计 52,238，
包含关系和另计费状态未核实；GLM 图片/缓存单价未知，因此完整人民币估算留空，单列已知小计。

## 验证与复现

从本工作树根运行，必须设置 `PYTHONPATH`，避免共享安装指到另一棵树：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r2/verify_delivery.py
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r2/run_validation.py
PYTHONPATH="$PWD" python -m src.agent_runtime.agent_registry verify --root .
```

前两条均为离线检查，不读取凭据或调用模型。`truncation_probe.py` 是已执行的一次性付费探针，
**不作为复验命令重复执行**。

初次短联合 302 项通过。长故障矩阵与真实工具回放暴露旧离线假模型的额度不适配：
未知模型按解码像素估算图片，新增结算后在第 71 次左右耗尽原 8,000 万额度。
两处离线 75 步回放额度改为 1.2 亿；生产上限、调用次数和 900 秒限制未改，独立调用预算耗尽反例保留。
重跑记录带 `-final` 后缀；首次结果没有覆盖。D 后补当前登记测试 9 项通过，摘要补救在 A 定向 15 项中通过。
最终汇总按测试 ID 去重，重复定向检查不累加计数。

## 交接与未决

- 技术未核实：9,786 个图片账单 token 缺请求事件；GLM 图片包含关系、另计费及图片/缓存单价；大图缩放服务行为。
- 需 Opus 复核：C 的旧账单解释与新分项证据冲突；本包不自行修改 `AI_agent/project/` 或 `models.md`。
- 用户拍板：本包没有新增产品取舍或外部调用申请；后续整案和工具改进包合入按原安排办理。
- 本包不实施 T1 合入，不改 Claude Code 运行器，不评价 Opus 正在进行的迁移第 2 次。

开发由 Astra 主持。两个 `gpt-5.6-sol` / high 子代理分别负责版本登记和图片记账，均已交回；
协作接口未提供子代理 token 用量，记为未获取。开发主线程订阅用量同样未获取。
工作模型的付费调用仅上述 Paratera 2 次，子代理无额外外部模型调用。
