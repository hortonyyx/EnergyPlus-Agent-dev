# 每次会话怎样加载上下文

唯一正文是 [AI_agent/Agent.md](../Agent.md)，不要在根目录重新建立 AGENTS.md / CLAUDE.md，也不要把规则复制到工具 memory。本文只说明加载办法，初始阅读范围由 Agent.md 定义。

## 跨会话怎样接续

接续依靠仓库里的文档和已保存产物。新会话或换模型后，从以下固定路径取得上下文：

1. **入口与长期约定**：读取 Agent.md，按其要求读取产品目标、当前任务和工作方式；开发派工前再读取模型与费用约定。
2. **最新进度与交接**：`project/roadmap.md` 的“当前交接”指向最新一份收工/交接记录，助手须打开阅读。这里知道做到哪里、哪些检查有效、剩余问题和下一步；旧日志按需查证。
3. **按任务展开**：实现依据查 `design/`，输入、输出和复现证据查 `logs/experiments/`，需要追溯经过时查 `logs/worklog/`；同时核对 Git 状态、近期提交和工作树，避免只凭文档判断实际代码。

Agent.md 保持稳定入口，当前任务维护最新指向，收工记录保存每轮经过。结束会话时同步目标/设计/约定变化，更新当前任务和交接链接，再正常提交推送。助手本地 memory 仅作路径索引，用户要求与项目事实必须写回仓库。

自动载入 Agent.md 不等于自动载入其中所有链接；助手仍须按要求实际打开这些文件。下节的本地入口配置未随 Git 保存，换机器或客户端时需先接好入口，不能假定新环境已经配置。

## 当前 Codex 环境

现有、已忽略的 `.codex/config.toml` 已增加以下入口设置，保留原来的沙箱和 MCP 配置：

```toml
project_doc_fallback_filenames = ["AI_agent/Agent.md"]
```

可复制配置片段见 [codex_entry.toml](codex_entry.toml)。它不是独立的项目规则。
Codex 按项目目录层级寻找指令文件；当前安装版本实际支持该相对路径。2026-09-08 移除根 AGENTS.md 后，用 `codex debug prompt-input` 检查了加载结果，确认 Agent.md 正文进入新会话上下文；该检查不调用生成模型。
该配置是本地文件，克隆到新环境不会随 Git 自动出现：把以上一项合入当地已有 `.codex/config.toml`，不要覆盖其他设置。项目配置只有在相应信任/配置加载条件下生效，新环境需重新检查。

在仓库根启动时可用下面的显式覆盖方式，无需新建根入口文件：

```bash
codex -c 'project_doc_fallback_filenames=["AI_agent/Agent.md"]'
```

官方说明：[自定义指令发现](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[配置项](https://learn.chatgpt.com/docs/config-file/config-reference)。嵌套相对路径的可用性以上述本地验证为依据，不假定所有版本和客户端都相同。

## Claude 与其他助手

所有客户端统一指定 `AI_agent/Agent.md`。旧 `AI_agent/CLAUDE.md` 已移除，不再保留工具专属的兼容入口。
不能假定从仓库根启动的任意客户端会自动发现嵌套文件。尚未验证该客户端的加载方式时，在它的项目初始上下文中指定 `AI_agent/Agent.md`，并让助手首轮读取。当前没有修改 Claude 的全局配置或权限。

切模型时不复制会话摘要当作另一套规则：先把新增项目事实、决定和待办写回管理文档，另一个助手从相同入口接续。本地项目 memory 只保留这些路径的索引。
