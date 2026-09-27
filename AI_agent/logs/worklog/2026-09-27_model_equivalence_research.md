# 09-27 GPT、GLM、DeepSeek 同档候选调研

用户在建模回归收工后要求调查可调用的 GPT 代理型号，并选出 Sonnet / Haiku 档候选，加入 GLM、DeepSeek，服务于模型泛化测试及减少 Claude 额度中断。此次只核本地工具/源码、历史证据和官方文档，没有启动子代理、模型探测、建模回归或付费调用，没有修改生产路由。此前开发及回归的完整结果仍见[本轮收工](2026-09-27_reconstruction_use_guidance_close.md)：质量尚未恢复，四次尝试全部结束。

## 结论与建议

**优先选择 GPT-6 Sol 与 GPT-6 Luna，分别作为 Sonnet 档主控、Haiku 档局部执行的候选。** 此处“同档”是按官方任务定位、模态及成本提出的角色近似，不是建筑读图、空间推理或整案质量已经等效。不能靠降低推理档位把旗舰变成低档模型，也不能靠名称或价格证明满足产品能力上限。Astra 继续用于开发，不加入常规产品候选。

| 家族 | Sonnet 工作档候选 | Haiku 工作档候选 | 本项目的关键限制 |
| --- | --- | --- | --- |
| GPT | `gpt-6-sol`，主控、规划、工具组织 | `gpt-6-luna`，有界读图、提取、局部核查 | 两者均支持图像；当前会话可选，但 BIM 实验入口尚未接入 |
| GLM | `glm-5.3`，暂限文本主控候选 | `glm-5.3-flash`，视觉及局部执行候选 | 5.3 历史视觉探针不可靠；整案图像对照应单列 Flash，不能默认 5.3 能直接替换 Sonnet |
| DeepSeek | `deepseek-v4-pro`，文本推理/主控候选 | `deepseek-flash`，当前对应 V4.1-Flash，视觉及局部执行候选 | Pro 官方不支持图像；整案视觉候选是 Flash，Pro＋Flash 分工属于另一实验条件 |

GPT 官方分别把 [Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) 定位于复杂编码/代理任务、[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) 定位于高吞吐的有界任务，两者接受文字和图像。GLM 的[模型目录](https://autoclaw.z.ai/models/)区分 5.3 的复杂工程/长程任务与 5.3 Flash 的原生多模态。DeepSeek 的[当前模型表](https://api-docs.deepseek.com/quick_start/pricing/)明确 Pro 无视觉、Flash 有视觉；这些是候选依据，均非本项目横向质量实测。

建议先接通 GPT，保留已有 GLM Flash 作为另一个家族的对照；DeepSeek 作为付费备用候选。不要预先将三个家族都固定为双代理架构。先比较同一角色，再判断拆分是否提高整体质量与成本表现；轻量档优先承担边界明确的局部任务。

## 当前能选什么、已经接通什么

本会话 `collaboration.spawn_agent` 的型号参数实际公开以下五项。这是接口可选择性，不代表已发起新推理或核实剩余额度：

| 当前代理型号 | 推理档位 | 本轮选择 |
| --- | --- | --- |
| `gpt-6-astra` | low / medium / high / xhigh / max / ultra | 开发负责人，排除常规产品选型 |
| `gpt-6-sol` | low / medium / high / xhigh / max / ultra | Sonnet 档首选候选 |
| `gpt-6-luna` | low / medium / high / xhigh / max | Haiku 档首选候选 |
| `gpt-5.6-sol` | low / medium / high / xhigh / max / ultra | 旧代备用，暂不扩实验矩阵 |
| `gpt-5.6-terra` | low / medium / high / xhigh / max / ultra | 旧代备用，暂不扩实验矩阵 |

本地只读核验 `codex-cli 0.153.4`。本地模型目录缓存还列出 `gpt-5.6-luna`、`gpt-5.5`，但这两项不在当前代理工具的可选名单，不能混称当前可调用子代理。缓存、公开 API 型号、当前代理接口、账户实际可用性是不同层面的证据；本轮没有探测账户额度。

项目 [`run_bim_agent.py`](../../../scripts/tool_scripts/run_bim_agent.py) 的订阅入口仅接受 `claude` / `glm`。GLM 将 `sonnet` 与 `haiku` 两角色都路由到 `glm-5.3-flash`，当前不是实际高低档组合。GPT 子代理可选不等于已接入隔离的 BIM 冷启动实验；DeepSeek 虽有[通用启动脚本](../../../scripts/deepseek_code.sh)，也未接此 BIM 入口。

GLM [09-05 历史探针](../experiments/2026-09-05_model_roster_probe/README.md)中，5.3 Flash 六项合成图任务全部正确；5.3 仅一项完全正确，既有拒看也有识别错误。这不足以宣称 5.3 完全不支持视觉，但足以阻止把“请求接受图像”当作“读图可靠”。当时 5v-Turbo 返回订阅不可用；本轮不将其列为已有可用通道。Flash 已有 BIM 实跑，质量与限制见[模型记录](../../workflow/models.md)，没有证明与 Sonnet 等效。

DeepSeek 官方当前把旧 `deepseek-v4-flash` 等别名转到 V4.1-Flash；项目脚本仍保留旧名称。后续必须记录实际返回型号、日期和请求参数，不能把旧名称当作冻结版本。新 Flash 的[视觉接口](https://api-docs.deepseek.com/guides/vision/)支持图片及工具交互；本项目尚未实测。Pro 当前后端为 V4-Pro-0813。

## 价格与额度

以下为 2026-09-27 查阅的官方美元 API 单价，每百万 token 的非缓存输入 / 输出。仅帮助判断工作档与潜在成本，不是现有订阅账单，也不表示按量 API 已获授权。缓存、服务档位、长上下文等费用条件另计。

| 型号 | 输入 / 输出（美元 / 百万 token） | 官方来源 |
| --- | --- | --- |
| Claude Sonnet 5（对照） | 2 / 10 | [Claude 模型表](https://platform.claude.com/docs/en/models/overview) |
| Claude Haiku 4.5（对照） | 1 / 5 | [Claude 模型表](https://platform.claude.com/docs/en/models/overview) |
| GPT-6 Sol | 2 / 10 | [Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) |
| GPT-6 Luna | 0.10 / 0.50 | [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| GLM-5.3 | 1.40 / 4.40 | [Z.ai 定价](https://docs.z.ai/guides/overview/pricing) |
| GLM-5.3-Flash | 0.15 / 0.50 | [Z.ai 定价](https://docs.z.ai/guides/overview/pricing) |
| DeepSeek-V4-Pro | 谷 0.66 / 1.98；峰 1.32 / 3.96 | [DeepSeek 定价](https://api-docs.deepseek.com/quick_start/pricing/) |
| DeepSeek-V4.1-Flash | 谷 0.15 / 0.60；峰 0.30 / 1.20 | [DeepSeek 定价](https://api-docs.deepseek.com/quick_start/pricing/) |

GPT 上表是标准服务、常规上下文价格；官方对超过 272K 输入 token 的请求有加价条件。不同家族 token 切分、思考消耗、图片计量、重试和返工不同，不能只看单价预测整案总费用。

[Codex 官方额度说明](https://learn.chatgpt.com/docs/pricing)仍按五小时窗口估算使用量，并可能有周限额；额度受型号、上下文和工具使用影响。换 GPT 是增加独立供应商通道，不是消除额度限制；同一 OpenAI 账户不同型号也不能默认拥有独立额度。GLM 也受所购套餐和账户权限约束，见[订阅连接说明](https://zcode.z.ai/cn/docs/configuration)。DeepSeek 当前为付费余额通道，按本项目既有约定，每个调用任务/批次仍须用户明确同意；此次调研不构成调用许可。

## 后续如何做有解释力的泛化测试

下一开发节点可先完成 GPT 适配与离线检查，再准备具体回归范围，交用户决定是否运行。本轮不实施适配，也不补跑已中断的 Claude 批次。

1. 优先让 Sol 使用现有原图、任务、BIM 工具和交付要求。保持生成侧无 GT、旧答案和开发会话上下文；不能直接继承当前主助手完整历史冒充冷启动。同一冻结实现下作跨家族对照，并保留此前好版本作能力参考。
2. 接入时核清图像和工具回执运输、工具权限、隔离目录、终态及用量。可考察 [Codex 非交互入口](https://learn.chatgpt.com/docs/non-interactive-mode)的结构化事件和 MCP；跨 CLI 会引入运行支撑差异，报告应称“模型＋运行支撑”对照，不能把全部差异归因于模型本体。若改用 API，需另核通道授权与接口兼容。
3. 主控同角色对照与低档局部读图分开。Sol 可从 medium 起步，Luna 可先固定 medium 的局部任务；这只是待测配置。不要让一组单模型、另一组高低档组合却声称只换了型号。
4. 各厂商推理参数不等价。DeepSeek 官方[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)将 `medium` 映射为 `high`，不能用相同字符串宣称算力预算一致。记录实际模型/思考配置、时间、用量、调用次数和所有中断。
5. 沿用房间、隔墙、门窗、连接、高度及可查看交付评价，单列拓扑严重错误、可接受尺寸差异、用途/证据质量和失败率。至少独立重复后再讨论稳定性；不以价格、通用榜单、一次局部探针或最佳一次替代整案证据。
6. 批次出现额度拒绝就保存终态，检查之后再决定下一步，不在同一脚本里无条件续跑，不自动换家族补成绩。新节点回归仍由用户拍板，DeepSeek 保持专项调用许可。

本轮验证仅需文档 diff、引用路径及源码/工具名单核对；没有生产行为变化，无需运行模型或重跑单测。研发仍处于已收工状态，下一次可在质量原因调查之外，安排 GPT 接入作为减少单供应商依赖的独立开发项。
