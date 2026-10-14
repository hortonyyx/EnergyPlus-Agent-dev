# OpenCode Go 独立订阅 provider 接线

用户提供Go订阅凭据，指定Go与Paratera承担后续work model消耗，并明确要求完成接线。本轮从主库`0c30d691`（runtime16/domain78）在独立工作树实施，未接续主线程的harness优化任务，未修改原案例/run/GT、默认6 Sol配置、Paratera凭据或桌面安装。

**开发完成，READY_FOR_MAIN_REVIEW。** 实现和正式登记已提交到`codex/opencode-go`，主线文档提交`4f86191f`已合入此分支以保留最新用户取舍；主库本身未由本侧合并。工作树保留供主线程按既定流程审阅、合入及小范围验收。机器可读完成标记见 [handoff.json](handoff.json)。

## 已接入行为

- 新增独立`opencode-go` provider，固定订阅端点`https://opencode.ai/inference/go/v1`，不标成Paratera，不自动换平台或按量端点。
- 显式读取仓库外Go凭据文件，无环境/插值回退；公开路由记录仅保存provider、端点、协议和subscription计费类别。
- 按精确model ID选择Chat Completions、Messages或Responses。注册六个本地可配置型号：GLM-5.3-Flash、Kimi K3、MiniMax M3、Qwen3.8 Max、Claude Haiku 5.5、GPT-6 Luna。40个目录条目中其余型号仍拒绝，GPT-6 Sol不在Go目录。
- 请求带自身User-Agent与稳定会话UUID，同任务恢复时复用，不同并发reader区分。单模型与role_division均接线，角色连接按provider+model区分，保留并发及共享预算。
- Go Responses实际传送输出cap，保存/重送原生响应项，复用现有工具与图片审计；Go Messages使用标准头和system字段，不带GLM专用beta。Chat不带Paratera思考开关或多采样参数。
- Go按subscription类别结算实报tokens，不套Paratera人民币单价，供应商prompt/input tokens含图像时不重复叠加估算图片tokens。费用未知不能记为免费。

细节：[Go接入说明](../../workflow/opencode_go.md) · [用户配置示例](../../../product/config.opencode-go.example.json)。默认产品示例仍是6 Sol，Go示例为Kimi K3服务默认思考；没有偷偷把默认或历史Astra配置改成其他型号。

## 离线验证

| 范围 | 结果 | 耗时 | 模型调用 |
|---|---|---:|---:|
| Go专用性质、两份产品配置与原Responses工具/恢复节点 | 17通过 | 3.26秒 | 0 |
| 原订阅与角色配置相邻检查 | 48项通过（来自57项批次，Go相关失误已单独修复复验） | 批次约10秒 | 0 |
| 原Messages/Responses、估算、图像记账与并发 | 96通过；1项版本封印检查在临时登记后通过 | 9.46秒＋1.48秒 | 0 |
| Go/原Messages重验，含中途system上下文 | 27通过 | 5.05秒 | 0 |
| 最终Go前置保护/endpoint profile与原Responses恢复 | 16通过 | 2.64秒 | 0 |
| Go最终保护与既有Sol/Luna分工配置 | 14通过 | 4.07秒 | 0 |
| 正式登记后版本封印与真实stdio MCP目录 | 2通过 | 8.28秒 | 0 |

表内范围有重叠，不能直接相加。首次pytest临时根缺失导致45项setup错误，建好独立D盘目录后复验；初版Go Messages图片proxy定位和PreparedRequest字段接线失误已修复。原版本封印拒绝新源码是预期保护，没有关闭校验或把未知型号降为非严格模式。

证据根：`D:/Sim-BIM-Agent/cache/opencode-go-wiring-20261015/`，包括`tests-corrected.xml`、`go-repair.xml`、`adjacent.xml`、`native-context.xml`、`staged-node.xml`、`final-targeted.xml`、`precommit.xml`、`final-profile.xml`。临时登记只用于本轮源快照验证，不是正式版本发布。最终检查还保留非Go角色共享一个连接对象、Go角色按型号分流、external_coordinator_mcp前置拒绝及Go endpoint-scoped profile；原生Responses沿用实报input usage锚点，不把密文当普通文本计数。

## 真实服务与runtime工具图片闭环

每个成功样本先让模型调用只读`inspect_fixture`，返回一张8×8红色合成PNG和仅工具可得的随机nonce，再由模型回答颜色与nonce。使用本次生产连接解析、适配器、请求编码、Runtime、EventStore、工具审计和订阅结算；无BIM建模或供应商切换，最多2模型请求、1工具、120秒、50000tokens、0自动重试，输出4096并显式记录最小测试例外。

| 型号 | 模型／工具调用 | 结果 | 实报tokens | 耗时 |
|---|---:|---|---:|---:|
| GLM-5.3-Flash | 2／1 | 工具→图片→正确颜色/nonce通过 | 593 | 16.641秒 |
| MiniMax M3 | 1／0 | 有效文本响应，但跳过工具、缺nonce；闭环未通过 | 445 | 1.688秒 |
| GPT-6 Luna | 2／1 | 原生Responses工具/图片闭环通过 | 336 | 4.344秒 |
| Kimi K3 | 2／1 | 工具/图片闭环通过 | 782 | 5.656秒 |
| Claude Haiku 5.5 | 2／1 | 原生Messages工具/图片闭环通过 | 1171 | 4.953秒 |

本轮接线实测合计**9次模型请求、4次工具、3327实报tokens**，用量完整，0BIM整案、0Paratera/DeepSeek模型调用。四次闭环第二请求均实际包含工具图片，原图与送达图SHA相等。MiniMax的runtime终态completed只代表它给了最终文本，不能把它计入要求的工具/图片闭环成功。

真实probe保留于 [原始摘要与journal目录](D:/Sim-BIM-Agent/cache/opencode-go-wiring-20261015/live/)。先后使用临时登记快照：前三个样本在首个接线快照，之后为Messages的原生system和前置保护补充了检查，Kimi/Haiku在后一个快照验证；不把不同快照写成同版建筑复跑。旧快照与原始日志未覆盖改写。

前一轮环境准备另有3次模型请求、751tokens（Go目录＋GLM工具续接＋Kimi小图），位于`D:/Sim-BIM-Agent/local-connections/opencode-go/verification.json`；不与本轮调用重复计算。

## 版本与交付边界

实现提交`d589f0d7`，正式登记为 **runtime-v17-20261015 / domain-v79-20261015**，登记与源文件核验通过；正式版本封印/真实stdio MCP目录2项通过8.28秒，无模型调用。Go接线为单独变更，不改写主线程的v78首版评价或收工结论。整合时保留主线随后新增的文档提交。

此接线支持服务调用，不宣称六个型号都已通过建筑识读、整楼交付、满容量上下文或并发真实服务验收。Qwen3.8 Max仅有协议/profile接线和离线校验，本轮未调用；MiniMax仅通过接口响应，工具行为仍需后续任务核验。本轮不更新桌面安装或进行新BIM整案；开发库的`sim_bim.py`和运行配置入口可用，桌面包仍为之前发布的v16/v78。

图片预算公式仍是明确标注的本地proxy，Go部署上限来自provider元数据；没有把Paratera的历史校准当作Go已校准。客户端未执行付费回退；账号控制台是否启用服务端余额回退未读取，不从客户端配置推断该账号设置。

官方依据：[Go端点与客户端要求](https://opencode.ai/v2/docs/console/go/)、[OpenCode模型元数据](https://models.dev/api.json)、[标准Responses工具协议](https://developers.openai.com/api/docs/guides/function-calling)、[无状态推理输出保存](https://developers.openai.com/api/docs/guides/reasoning)。
