# 10-11 Sim BIM Agent 订阅接入收工

用户要求将模型独立运行能力加入本轮 runtime，并明确已有 ChatGPT 订阅、不额外购买按量 API。应用最终命名 **Sim BIM Agent**。本轮实现完成，**runtime v6 / domain v61**；用户决定暂不登录，之后换另一个账号，真实服务接入仍待该步骤。

生产源码提交 `322bd014`。完整实现、测试失败与复验、原始证据见[本轮报告](../experiments/2026-10-11_chatgpt_subscription_runtime/README.md)，使用见[独立订阅接入](../../workflow/chatgpt_subscription_runtime.md)。

- runtime 已具备独立 SIWC 登录、本机凭据保护与轮换、账号模型目录、原生 Responses 请求、函数工具/图片、多轮 opaque state、检查点恢复和账本。支持单模型与分工；没有 Codex CLI/app-server 依赖、API-key 线路或付费回退。
- domain 只改入口与配置接线，工具和指引指纹未变。旧 sm25 失败run、未知用量、模型输出保持冻结；没有追加图纸建模验证。
- 最终18文件286项离线检查通过，48.67秒；独立Python启动完成2轮SSE夹具和1次真实本地只读工具，0.188秒，100 token只是夹具数。真实OpenAI/GLM/Paratera/DeepSeek产品模型请求均0；Codex开发会话用量未取得，不记零成本。
- 曾为用户打开一次浏览器授权页；用户说明之后换号，已取消等待。随后本程序状态确认未登录、账号数0。没有导入当前Codex账号。默认存储目录保留原工程命名以避免以后凭据迁移，授权页显示 Sim BIM Agent。
- 版本登记只追加v6/v61，旧版本和别名语义不变。已确认的应用名称同步到产品目标、会话入口、决策与接入说明。

前轮 v5/v60 的工作也属于这轮用户连续讨论后的 runtime 迭代：定向 message/pause/resume、安全恢复与补账、增量校验和预算缓存；其 GLM 订阅协议小测2请求/654 token/8.625秒已独立记录，不能加到本次新增OpenAI调用数。见[前轮交接](2026-10-10_runtime_control_iteration_close.md)。

下一步先由用户选择另一个账号授权，再读真实模型目录并决定协议小测；domain 下一轮方案仍留待讨论。不能把离线独立启动等同于真实订阅已连通、BIM质量通过或整案30分钟达标。

本轮 `openai-subscription-20261011`、`openai-responses-20261011` 两棵 D 盘工作树已在确认路径、干净状态和提交全部合入后由 `git worktree remove` 收回；两棵旧 evidence/role-kernel 工作树及旧受限目录按原交接保留，没有处理。认证代理一次空状态 CLI 检查在 `%TEMP%/EnergyPlus-Agent-cli-empty-test/credentials.lock` 留下0字节文件，不含凭据；自动审批拒绝清理，已保留，不换途径重试。

版本记录与本轮源码、测试、证据、交接均正常 commit/push；最终远端哈希核验由主线程收工确认，不强推。C/D盘剩余空间在收工对话报告。
