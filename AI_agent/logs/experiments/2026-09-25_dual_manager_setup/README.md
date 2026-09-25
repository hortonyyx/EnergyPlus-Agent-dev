# Astra / Opus 5.5 并行开发启动

用户要求两位最高档开发负责人协作：Astra 与 Opus 5.5 各自按需选派子代理，模型家族不绑定建模路线，用户统一与 Astra 沟通；Astra 负责总体范围、共享接口、合并、项目文档与统一收工。Claude 额度恢复，工作模型可按任务选择 Claude 或 GLM，原费用权限及产品 Sonnet 级上限保留。

本工作包中 Opus 使用本机 Claude Code `2.1.280`，通过现有订阅启动，初始化回执为 `claude-opus-5-5`、`xhigh`。这是带文件/代码工具的开发会话，不是只有文本输入的审阅调用，也不是产品工作模型实验。

- [任务原文](opus_task.md)、[启动器](run_opus.py)、`opus_started.json` 保留任务范围、命令、基准提交和进程信息；结束后保存 `opus_receipt.json` 和回答。
- 独立分支 `dev/opus-voimatalo-20260925` 从 `f7e8d5ef` 启动，工作树位于主仓持久化挂载内的 `.worktrees/opus-voimatalo-20260925`，该目录已忽略。
- 当前任务是 Voimatalo 内部组织和缺失补全的待用户验收开发候选；只写自己的新实验目录。Astra 同时推进 sm25 的观察/源分区一致性和工作模型验证；此分配不固定为长期路线归属。
- 订阅环境沿用已登录身份，移除 API/第三方路由环境变量；禁用额外 MCP、项目设置和 hooks，显式允许读写、Shell 与内置子代理。使用现有 Python，并将模块路径指向本工作树，不运行依赖同步，避免改动共享 editable 安装。

运行状态与集成结果由 [统一交接](../../worklog/2026-09-25_dual_manager_development.md) 更新；原始资产和旧实验未覆写。
