# Paratera 工作模型接入与首轮筛选（2026-09-28）

用户提供 Paratera 地址、文档及凭据，要求先筛适合的工作模型；理想组合以 Qwen 27B 这种可本地部署级模型为主，部分 Flash 级模型辅助。以下是助手建议和实际接口证据，尚非用户选定型号或建筑质量基线。

## 推荐候选

| 平台 model ID | 建议用途 | 官方能力与部署尺度 | 本轮实测 |
|---|---|---|---|
| `Qwen3.8-27B` | 首选主力 | 原生视觉语言、27B 稠密、Apache 2.0 开放权重，符合本地主力方向 | 看图→正确工具参数→采用工具回执，通过 |
| `Qwen3.5-35B-A3B` | 本地主力对照 | 原生多模态、35B 总参数/3B 激活 MoE、Apache 2.0；3B 激活不表示只需加载 3B 权重 | 同上，通过 |
| `Qwen3.8-Flash` | 首选 API 辅助 | 官方托管版本以 Qwen3.8-Flash-Next 为基础；支持图像和工具，规模大于 27B 本地档 | 同上，通过 |
| `GLM-5.3-Flash` | 跨家族辅助对照 | 原生多模态、320B 总参数/18B 激活、MIT 开放权重；本轮按 API 辅助考虑 | 同上，通过 |

先以 **27B 主力 + Qwen Flash 辅助** 进入后续验证，另外两项保留作对照；这是依据部署目标和接口能力的选择，不是建筑任务排名。辅助可承担有界图证核查、歧义复核等任务，触发方式仍须用实际效果验证，不预设每案必调或固定角色数量。没有下载权重、安装本地推理服务器或核算具体硬件容量。

官方来源（09-28 核对）：[Paratera API 文档](https://ai.paratera.com/document/llm/quickStart/useApi)、[平台下线公告](https://ai.paratera.com/document/llm/support/lmsOffline)、[Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)、[Qwen3.5-35B-A3B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)、[Qwen3.8-Flash-Next 与托管 Flash 对应](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)、[GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)。Flash-Next 卡列出 125B/6B 激活，另有 51B ngram 和 4B MTP，不能将 Flash 名称理解为 27B 档显存需求。

## 已配置与接入范围

- 实际 API base：`https://llmapi.paratera.com/v1`；密钥只写根目录 gitignored `.env`，权限 0600，不入仓。
- [公开模板](../../../../.env.example) 提供 `PARATERA_API_KEY`、`PARATERA_BASE_URL` 占位；[候选配置](../../../../src/configs/llm_paratera.yaml) 提供 `default/local_main/local_alternative/flash_assist/flash_crosscheck/connection_check`。
- 现有 API 消费端可显式设置 `EP_AGENT_LLM_CONFIG=src/configs/llm_paratera.yaml`，通过 `load_llm_section` 选配置。`provider: openai` 表示兼容客户端协议，不表示调用 OpenAI 的模型。六个配置已通过实际加载和客户端构造，见 [离线记录](config_validation.json)。
- **当前 `run_bim_agent.py` 仍是 Claude/GLM 订阅循环，尚不读取这份 API 配置。** 后续需将聊天、图片和工具回执接入同一 MCP 工具集；单改 URL 无法替代该适配。没有切换既有默认配置、运行整栋回归或引入自动回退。
- 配置中的 Qwen 主任务暂定启用思考、最大输出 16384；本轮探针关闭思考、每请求最多 1024。启用思考、长上下文与长程多工具执行尚未实测，候选参数不算已验证生产参数。

## 本轮实际请求

本次用户要求配置并筛选指定平台，覆盖必要的小型接口探针。鉴权 `GET /v1/models` 一次成功、返回 94 项，见 [目录](catalog.json) 与 [回执](catalog_receipt.json)。名单内仍出现下线公告中的旧型号，不能凭列出即认定可用；本轮四项均另有真实生成成功证据。

[探针脚本](probe.py) 对四项串行各两次请求：给出只含数字 37、84 的合成图片，要求调用 `add_numbers`，随后要求返回工具提供的唯一回执。四项均读数正确、传参正确并采用第二轮工具结果；不是只测文本问候。使用 OpenAI SDK、60 秒请求超时、零自动重试/回退；无 DeepSeek、订阅模型或整栋模型调用，也未上传项目建筑/GT。首个离线准备因字体名不可用失败，改用 Pillow 自带字体；当时零推理请求，见 [准备记录](setup_attempts.json)。

[实测报告](protocol_probe/report.json) 共 **8 次请求、输入 2645 / 输出 188 / 合计 2833 tokens**；模型响应 ID 均与请求型号相同。原始请求记录用本地图像路径替代 base64，响应和每项回执均保存。API 返回名称不构成上游权重身份认证。每模型仅一组小任务，时长不能用于稳定性能排名。

[用量记录](usage_summary.json) 保留平台费用未知：模型目录不含价格，静态价格页列旧型号，上游自有 API 价格也不能替代 Paratera 账单；本轮未报虚构费用或免费结论。价格、剩余额度、并发和长期稳定性仍未核实。

## 后续验收

下一能力包是统一 BIM 入口的 API/MCP 适配：保留现有工具、图像反馈、用量与错误回执、运行边界，先离线验证消息转换和真实工具结果。节点闭合后按既有回归约定准备具体建筑验证范围。以同样可观察的“取得图证→对象解释→工具执行→保存修订→回查”对应源 BIM 的空间、门窗和连接质量，不把更换模型、调用更多辅助或协议探针成功当作还原质量提升。本次不自动补跑此前因 429 结束的 Sonnet 批次。
