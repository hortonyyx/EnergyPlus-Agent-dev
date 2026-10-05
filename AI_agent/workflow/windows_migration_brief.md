# 派工：开发环境从 Dev Container 迁到 Windows 原生，然后撤容器（10-05 备）

由 Opus（项目经理）10-05 收工时备好，交给在 Windows 上直接运行的 Claude 或 GPT（Codex）开发助手主导执行。用户决定撤掉容器（Docker 数据占 D 盘一百多 G；Windows 上可直接用 Claude、ChatGPT 桌面客户端，更方便远程）；部署时再考虑容器。背景见 [10-05 工作记录](../logs/worklog/2026-10-05_opus_second_review_c3_regression.md)。

## 开工前

1. 完整阅读 [Agent.md](../Agent.md)，按其“开始会话”读当前任务、工作方式与最新交接；遵守其中权限约定，尤其：**DeepSeek 任何调用都要用户先明确同意**；Paratera 只在已批额度内（余约 14 元，本任务不需要）；整案运行属于节点回归，要用户批准，本任务不跑整案。
2. `git status`、`git pull`，确认在 `main` 且与远端一致。

## 现状（哪些在 Windows 上，哪些只在容器里）

- **已在 Windows 上：** 仓库本身（容器只是挂载，且全部已推送 GitHub）；`~/.claude`（Claude Code 的会话记录、本地记忆、凭据）；`~/.claude.json`；`~/.codex/auth.json`；`~/.gemini`。
- **只在容器里、已备份：** Codex 的会话记录、自身记忆与状态库（容器 `/root/.codex`，约 1.7 GB），以及 Opus 10-05 会话的临时文件，已打包到仓库内被忽略的 `AI_agent/archive/local_backup/container_2026-10-05/`（附 `SHA256SUMS`）。一般不需要还原；要续接旧 Astra 会话时再解开到 Windows 的 `~/.codex`。
- **只在容器里、需重装：** Python 3.12 环境（容器内 `/opt/venv`，由仓库根 `pyproject.toml`、`uv.lock` 用 uv 装）；Linux 版 EnergyPlus 25.1.0（主线暂不跑 EnergyPlus，需要时装 Windows 版）；Node（Claude Code、Codex CLI 自带的除外）。
- **只适用于容器的写法：** 运行配置与文档里的 `/workspaces/EnergyPlus-Agent-dev`、`/root/...`、`/opt/venv`、`/tmp/...` 路径；`src/agent/execution/isolation_templates/guard.py:235` 硬编码了容器内仓库路径；派 Astra 的命令（[工作方式](development.md)“从 Claude Code 派 Astra”）是为“容器里建不了 codex 沙箱”写的 bash 命令。

## 要做的事（按顺序，小步提交）

1. **装环境：** 在 Windows 上装 Python 3.12 与 uv，在仓库根按 `uv.lock` 建虚拟环境（放仓库外或已忽略的位置），确认 `python -c "import src.agent"` 可用。
2. **找出并改掉容器专属写法：** 只改当前在用的代码、配置与工作文档；历史实验记录里的路径是当时的事实，不改。改路径优先改成相对仓库根或配置项，不换成另一个写死的 Windows 路径。
3. **跑全部检查：** `python -m pytest -n 2 tests`（Linux 本机盘上约 25 分钟：5,541 过、0 失败、2 跳过、13 预期失败，见[验收记录](../project/unified_agent_acceptance.md)“C3 合并后核对”）。Windows 上新出现的失败逐个判断：平台差异（路径分隔符、进程启动方式、bash 命令如 `timeout`／`split`、文件权限与符号链接、换行符）就做最小修正；**不为变绿放宽保护性断言**；改不了的写清原因。
4. **烟测（不跑整案）：** `python -m src.agent.runtime_configuration check <配置>` 对 [10-05 回归配置](../logs/experiments/2026-10-05_node_regression_c3/configs/) 改好路径后通过；GLM 订阅发一次最小请求，确认新底座线路通（订阅调用已获授权）；`run_bim_agent.py serve` 能列出工具目录。
5. **入口与个人设置：**
   - Codex：仓库 `.codex/config.toml` 已有 `project_doc_fallback_filenames = ["AI_agent/Agent.md"]`；Windows 的 `~/.codex/config.toml` 设 `model = "gpt-6-astra"`、`model_reasoning_effort = "xhigh"`（容器里的个人设置只有这两项有用）。按 [会话设置](session_setup.md) 用 `codex debug prompt-input` 核对新会话确实载入 Agent.md；桌面应用若不载入，记下并提示用户开头让它先读 Agent.md。
   - Claude：项目本地记忆按项目路径分目录，换路径后在新项目的 memory 目录建 `MEMORY.md`，内容照旧只写一行索引：先读 `AI_agent/Agent.md`（旧索引在 `~/.claude/projects/-workspaces-EnergyPlus-Agent-dev/memory/MEMORY.md`）。
6. **派工方式：** 在 Windows 上确认 Codex 的沙箱能否正常写仓库；据此改写[工作方式](development.md)“从 Claude Code 派 Astra”一节的命令与说明（替换，不追加）；Astra 的工作树放在 Windows 本地磁盘上，不放网络盘或同步盘。
7. **性能提醒（告诉用户）：** 把仓库目录和虚拟环境加入 Windows 安全中心的排除列表，否则大量小文件读写会被逐个扫描、明显变慢；整案运行目录也放本地磁盘（运行配置的 `run_root`）。
8. **最后才撤容器（带用户做）：** 以上都通过后，先问用户 Docker 里还有没有别的要留的东西；然后在 Docker Desktop 里删掉本项目的容器与镜像，再用 Docker Desktop 的清理数据（或卸载 Docker Desktop），D 盘上的虚拟磁盘文件才会缩小、空间才会释放。
9. **记录：** 在 `AI_agent/logs/worklog/` 写一份迁移记录（做了什么、改了哪些文件、检查结果、未解决项）；更新[会话设置](session_setup.md)、[工作方式](development.md)里与环境有关的段落；把 [当前任务](../project/roadmap.md) 顶部的“下一步 ①”标为完成并把“当前交接”指向这份记录；commit 并 push。

## 完成标准

Windows 上全部检查跑完且失败项都有结论；配置检查与 GLM 最小请求通过；Codex 与 Claude 新会话都能载入 Agent.md；派 Astra 的方式有可用写法；文档已更新并推送；用户确认已撤容器并释放空间。之后回到 [当前任务](../project/roadmap.md) 的下一步 ②（分工体系 v1）。
