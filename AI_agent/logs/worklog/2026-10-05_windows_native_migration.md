# Windows 原生开发环境迁移（10-05，执行中）

用户交由 Windows 上的 Codex 主导，按 [迁移派工单](../../workflow/windows_migration_brief.md) 顺序推进。范围仅环境与平台兼容；不调用 DeepSeek、不跑整案，GLM 订阅只允许一次最小连通请求。撤容器须所有检查通过且用户明确确认，当前尚未授权删除。

## 开工与备份

- 已完整读取 Agent.md、goal.md、roadmap.md、development.md、最新交接及派工单。
- 起点 `6d277f84ae223778e623fdb8fb3711c885446d48`，main 干净，仅一个工作树；`git pull --ff-only` 无更新，HEAD 与 origin/main 一致。
- `AI_agent/archive/local_backup/container_2026-10-05/` 两份压缩包 SHA256 与 SHA256SUMS 全部相符，目录被 Git 忽略。原备份说明保留：SQLite 打包时可能不一致，需要恢复时以会话 JSONL 为准；没有覆盖 Windows 现有 Codex 数据。
- D 盘开工可用约 64.30 GiB；尚未进行 Docker 删除、清理或磁盘压缩。

## 1. 原生环境

- 已有 Python 3.12.10、uv 0.11.22、Node 24.15.0、Codex CLI 0.156.1、Claude Code 2.1.280。
- 仓库原 `.venv` 是 Linux 环境，已在核实路径位于本仓库后移到上述本地备份目录的 `venv-linux/`，未删除。
- 在仓库根执行 `uv sync --frozen --python <本机 Python312/python.exe>`，原锁文件安装 176 个包，Windows 环境位于已忽略的 `.venv/`。
- `.venv/Scripts/python.exe -c "import src.agent"` 通过，解释器实际来自本仓库 `.venv`。

## 后续状态

路径、文件锁与进程兼容正在检查；全量测试、配置检查、GLM 唯一请求、MCP 工具目录、Codex/Claude 入口、Windows 沙箱写入、文档交付和撤容器均待完成。尚未发出任何工作模型请求。
