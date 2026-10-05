# 每次会话怎样加载上下文

唯一正文是 [AI_agent/Agent.md](../Agent.md)，不要在根目录重新建立 AGENTS.md / CLAUDE.md，也不要把规则复制到工具 memory。本文只说明加载办法，初始阅读范围由 Agent.md 定义。

## 跨会话怎样接续

接续依靠仓库里的文档和已保存产物。新会话或换模型后，从以下固定路径取得上下文：

1. **入口与长期约定**：读取 Agent.md，按其要求读取产品目标、当前任务和工作方式；开发派工前再读取模型与费用约定。
2. **最新进度与交接**：`project/roadmap.md` 的“当前交接”指向最新一份收工/交接记录，助手须打开阅读。这里知道做到哪里、哪些检查有效、剩余问题和下一步；旧日志按需查证。
3. **按任务展开**：实现依据查 `design/`，输入、输出和复现证据查 `logs/experiments/`，需要追溯经过时查 `logs/worklog/`；同时核对 Git 状态、近期提交和工作树，避免只凭文档判断实际代码。

Agent.md 保持稳定入口，当前任务维护最新指向，收工记录保存每轮经过。Codex 主助手统一同步目标/设计/约定变化、当前任务及交接链接，并负责主线提交推送与每轮收工；Claude 结束获派任务时先保存成果与证据并交回主助手，不独立更新全局交接或推送 main。Claude 开工除读取共同入口，还须核对主助手分配的工作目录、基准提交与文件范围，见[协作规则](development.md#统一统筹与开发协作09-25确认)。助手本地 memory 仅作路径索引，用户要求与项目事实必须写回仓库。

自动载入 Agent.md 不等于自动载入其中所有链接；助手仍须按要求实际打开这些文件。下节的本地入口配置未随 Git 保存，换机器或客户端时需先接好入口，不能假定新环境已经配置。

## 当前 Codex 环境

Windows 本机的 `.codex/config.toml` 被 Git 忽略，入口设置如下，保留原来的沙箱和 MCP 配置：

```toml
project_doc_fallback_filenames = ["AI_agent/Agent.md", "Agent.md"]
```

可复制配置片段见 [codex_entry.toml](codex_entry.toml)。它不是独立的项目规则。
2026-10-05 在 Windows 的 Codex CLI 0.156.1 重新实测：从仓库根启动，嵌套备用路径没有载入正文；从 `AI_agent` 目录启动，用备用名 `Agent.md` 则完整载入。PowerShell 包装命令与直接可执行文件均已用 `codex debug prompt-input` 验证，不调用生成模型。9 月容器中的成功结论不能替代本机验证。
该配置是本地文件，克隆到新环境不会随 Git 自动出现：把以上一项合入当地已有 `.codex/config.toml`，不要覆盖其他设置。项目配置只有在相应信任/配置加载条件下生效，新环境需重新检查。

Windows 从仓库根使用以下入口；工作目录设为 `AI_agent`，额外可写目录仍是整个仓库，无需新建根入口文件：

```powershell
$taskRoot = (Get-Location).Path
codex -c "project_doc_fallback_filenames=['Agent.md']" -C (Join-Path $taskRoot 'AI_agent') --add-dir $taskRoot
```

10-06 已分别在 Windows PowerShell 5.1 和 PowerShell 7.6.5 验证这条配置写法：`debug prompt-input` 返回成功，解码后的上下文包含完整 Agent.md。配置值内部使用 TOML 单引号，避免 PowerShell 5.1 剥掉内部双引号后把数组误传成字符串。两个检查均未调用模型。

本机 `~/.codex/config.toml` 的个人偏好为 `model = "gpt-6-astra"`、`model_reasoning_effort = "xhigh"`。桌面客户端从仓库根打开的会话仍应在首条消息明确要求：“先完整读 AI_agent/Agent.md，按开始会话读取指定文档。”本次桌面会话按此要求实际读完；未声称其根目录自动载入已经恢复。

Windows 环境在仓库根用 `. ./scripts/activate_windows.ps1` 激活，再用 `python`。该脚本只设置当前 PowerShell 的虚拟环境、UTF-8 和本仓库 PYTHONPATH，不读取凭据。创建环境用 `uv sync --frozen --python 3.12`；无需为每次普通代码修改重新同步依赖。EnergyPlus 求解器是另行安装的可选下游，本次未安装或运行整案。

官方说明：[自定义指令发现](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[配置项](https://learn.chatgpt.com/docs/config-file/config-reference)。嵌套相对路径的可用性以上述本地验证为依据，不假定所有版本和客户端都相同。

## Claude 与其他助手

所有客户端统一指定 `AI_agent/Agent.md`。旧 `AI_agent/CLAUDE.md` 已移除，不再保留工具专属的兼容入口。
Claude 的本地记忆按实际项目路径分目录。Windows 当前仓库对应 `~/.claude/projects/c--Users-Horton-Desktop-EnergyPlus-Agent-dev/memory/MEMORY.md`，只保留一行读取 `AI_agent/Agent.md` 的索引，不复制项目规则。10-05 已创建，旧容器项目记忆目录保留。

在仓库根启动 `claude '@AI_agent/Agent.md 请按开始会话读取指定文档，再处理本次任务。'`，文件引用会进入首轮上下文。10-05 用仅监听本机的模拟接口验证新会话：索引已载入，Agent.md 的 39 条实质长行全部进入请求；没有调用真实模型。未修改 Claude 全局权限。其他客户端仍需明确让助手首轮读文件，不能假定都支持相同的引用语法。

切模型时不复制会话摘要当作另一套规则：先把新增项目事实、决定和待办写回管理文档，另一个助手从相同入口接续。本地项目 memory 只保留这些路径的索引。
