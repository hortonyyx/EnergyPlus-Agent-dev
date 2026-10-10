# Sim BIM Agent：ChatGPT 订阅原生 runtime 接入

本轮接入已实现并离线验收，最终 **runtime v6 / domain v61**，生产源码提交 `322bd014`。用户明确已有订阅、不再购买按量 API；随后决定本轮暂不登录，之后换另一个账号。已取消授权等待，安全状态检查为 `signed_in=false, account_count=0`。**真实订阅可用性与账号模型目录尚未验证，新增产品模型请求为 0。**

## 实现范围

- runtime：独立 SIWC 动态客户端注册、PKCE/state/nonce/JWT 校验、Windows DPAPI 本机凭据、令牌轮换、账号目录；公开 `/v1/responses` 流请求；命名空间函数工具、文本/图片输入、opaque output 原样保存和断点重放。对外名称按用户最终决定为 **Sim BIM Agent**。
- runtime：wire 与来源留证，原生协议工具展示校验；input/output/cache 用量归一化，图片不重复计入 provider total；中途观测用量单独留证，最终未知仍保留 hold。32k 为本地预留，不能作为服务端输出硬上限。
- domain：单模型与分工入口的 provider、认证目录、模型目录及配置接线；建筑规则、kernel、tools、methods、roles、guidance 的建模行为未改，登记模式指纹不变。外部 MCP 调度入口显式拒绝此线路。
- 产品运行直接由自有 runtime 发 HTTP、执行本地工具、保存上下文和检查点；不启动 Codex CLI/app-server、不读取其账号凭据、不使用 `OPENAI_API_KEY`，不做付费或跨 provider 自动回退。这里验证的是产品运行链路；不表示当前 Codex 开发对话已迁移进本 runtime。

使用入口：[订阅登录与运行说明](../../../workflow/chatgpt_subscription_runtime.md)。官方依据：[SIWC](https://developers.openai.com/siwc/token-sharing-open-source)、[模型与推理](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)、[preview 限制](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)。账号实际可用性、额度和模型仍须登录后验证。

## 验证结果

所有离线 pytest 都使用仓库 `.venv`，Windows 并行测试设置 `PYTHONUTF8=1`。以下批次存在重叠，不相加当作独立用例总数。

| 验证 | 结果 | 耗时 | 用量与边界 |
|---|---|---:|---|
| 最终登记代码，18 个 runtime/入口/合同相关测试文件 | **286 passed，0 failed** | 48.67 s | 无外部模型请求；[XML](release-tests.xml) |
| 最后协议修复，认证、Responses 与原生循环 | 73 passed | 6.11 s | 已含中途 usage、流失败/外层取消、恢复、不执行 partial tools；[XML](protocol-recheck.xml) |
| 较早定向集成批次 | 259 passed | 22.94 s | 后续边界修复由最终批次覆盖；[XML](targeted-tests.xml) |
| 独立 Python 进程启动自有 runtime | completed / passed | 0.188 s | 2 个 SSE 夹具响应、1 次真实本地只读工具，100 token为夹具值；[回执](offline_smoke/smoke_result.json)、[事件](offline_smoke/events.jsonl)、[版本](offline_smoke/versions.json) |
| 版本核验 | v6 / v61 一致 | — | 旧 runtime/domain 记录与别名语义保持不变 |
| 真实 ChatGPT 订阅连接 | **按用户决定未执行** | — | 登录已取消，无应用账号；真实 OpenAI 请求0、付费 API 请求0 |
| 新 sm25 整案、BIM质量与5/10/30 cm分档 | **未运行，不适用** | — | 无新平面/叠图/BIM链接；旧失败保持冻结 |

命令：`python -m pytest -q -n 2` 指定 `test_agent_runtime`、`test_runtime_subscription`、`test_runtime_anthropic`、`test_runtime_openai_subscription`、`test_runtime_openai_profiles`、`test_runtime_responses`、`test_runtime_responses_integration`、`test_runtime_budget_recovery`、`test_runtime_image_accounting`、`test_runtime_context`、`test_runtime_control_recovery`、`test_runtime_recovery_edges`、`test_role_configuration`、`test_runtime_r2_truncation`、`test_runtime_r2b_billing`、`test_runtime_estimation`、`test_runtime_agent_registry`、`test_runtime_coordinator_root_limits`，均位于 `tests/`。完整集合与每项耗时保存在 release XML，不是全项目节点回归。

独立启动使用 `scripts/dev/smoke_chatgpt_runtime.py --out AI_agent/logs/experiments/2026-10-11_chatgpt_subscription_runtime/offline_smoke --model gpt-6.1-sol`，未加 `--live`。不需要已登录凭据；该实验并不证明真实服务接受请求或模型具备 BIM 质量。

## 独立审阅与修复过程

认证、Responses 分两个临时工作树实现，另一开发代理只读审查接线、账户/费用边界、流失败与恢复。发现并修复：

1. 外部 coordinator 配置原会错误接受新 provider，但内部仍走 Chat Completions；本轮提前拒绝该组合。
2. `current_tool_chain` 被接受但原生 opaque output 实际始终全回放；本轮显式只允许 `all`。
3. 两款已登记模型不支持 none/minimal 推理档位；发送前拒绝。
4. 流失败/外层取消会丢掉已经观察到的用量。初修曾将较早计数用于失败结算，主线程复核认为中途计数不能证明最终量，改为独立来源证据，终态未知继续保留 hold。两种失败都不执行部分工具调用。
5. OpenAI 图片 detail 参与持久化重估；省略按 auto，Responses 转换默认显式 high；原生 input usage 包含图片，缓存是其子集，均不重复加总。

早期失败没有覆盖或删除：

- 系统 Python 未装 pytest；改用 `.venv`。并行 worker 默认 GBK 造成两项读取失败；显式 UTF-8 后原四文件89项全过。
- 初次 Responses 集成47过1败，是测试直接索引允许省略的 `type` 字段；改为 `.get`。
- 接线30过1败，是旧命令参数顺序改变；恢复原顺序，31项全过。
- [早期协议批次](final-protocol-tests.xml)70过2败：流取消修复尚未合入时已运行新测试，且断言错误要求所有失败统一为 `token_usage_unavailable`。合入后明确保留时间/服务错误状态，同时验证最终 usage 未知、不执行工具及观测留证，最终73项和286项均通过。

OpenAI 原生线路没有自动缩小输出预留策略；服务实际输出仍可能超过预留。Sol 图片估计是标明未校准的保守代理，Astra 使用官方 patch 公式；两者文本估计也不是 provider tokenizer 的已校准上界。真实超支按回执结算，达到整轮保护线后停止后续工作。

## 收工与下一步

当前接入代码可以独立启动，登录待用户换号授权。之后先运行 `python -m src.agent_runtime.openai_subscription login`，再用 `models` 获取实际可用目录；经用户决定启动有界 `--live` 协议验证。无需购买付费 API，也不把账号订阅资格写成保证。

前一轮 runtime v5 的定向消息、暂停恢复、预算补账、工具恢复和开销迭代继续保留，见[前轮报告](../2026-10-10_runtime_control_iteration/README.md)。domain 下一步仍先讨论声明保存/局改、规整门槛及读图负担；没有新增 sm25 冷启动或修改旧失败账本。Git 与工作树收尾见[当前交接](../../worklog/2026-10-11_chatgpt_subscription_runtime_close.md)。
