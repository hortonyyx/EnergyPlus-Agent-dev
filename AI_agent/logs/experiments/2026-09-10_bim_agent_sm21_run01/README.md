# sm21 BIM Agent 首次接线尝试：工具未加载

本目录是 09-10 独立订阅模型原图实验的第一次启动，**没有生成候选，也没有实际读图**。

- 输入：sm21 六张原始 PNG，复制字节及 SHA-256 见 `inputs.json`；无 GT、历史 reading 或开发助手填入的几何。
- 请求 Sonnet，CLI 实际主模型 `claude-sonnet-5`。约 16.05 秒，估算 $0.024394（含 CLI 辅助 Haiku，非账单）。
- CLI 初始化中 `mcp_servers` 为 pending，工具列表为空。模型因此称未收到图片并要求提供输入；没有工具调用。`summary.json` 中旧字段 `agent_completed=true` 只表示文字回复完成，不能证明任务完成；真实候选列表为空。
- 根因：当前 CLI 的 MCP 异步加载与关闭全部内置工具相遇，首请求拿不到工具。后续入口已使用 `alwaysLoad:true` 与 `ENABLE_TOOL_SEARCH=false`；离线 stdio 确认服务原本能返回图片/工具，run02 的 CLI 初始化已实际显示 connected 与七项工具。
- 修正依据：[Claude Code 官方 MCP 文档](https://code.claude.com/docs/en/mcp) 关于 `alwaysLoad` 等待连接及工具延迟加载的说明。本次不是读图质量测试失败。

原始请求、流式轨迹及回执保留；后续新建 [run02](../2026-09-10_bim_agent_sm21_run02/)，不覆盖本次失败。
