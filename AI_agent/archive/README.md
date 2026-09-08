# 历史与恢复索引

归档保存原文和恢复依据，旧文中的批准、测试、批次与待办不自动成为现行要求。当前规则从 [Agent.md](../Agent.md) 开始。

| 归档 | 保存内容 |
|---|---|
| [接手前核心管理稿](2026-09-08_pre_takeover/) | 前次保留的 8 份原入口、计划、决策与长指南 |
| [整套管理重建快照](2026-09-08_management_rebuild/README.md) | 本轮重建前 74 份文件原文、哈希与逐文档处置 |
| [Codex 记忆](2026-09-08_codex_memory/README.md) | 5 份原记忆/索引/探测文件及同步位置 |
| [Claude 记忆](2026-09-08_claude_memory/README.md) | 两处项目目录 187 份 Markdown 原样归档，本地改为索引 |
| [工作树存档清单](2026-09-08_takeover_inventory.json) | 原 67 棵树的路径、HEAD、状态及保留方式 |

Git 归档标签 `archive/2026-09-08/branches/*` 与 `archive/2026-09-08/worktrees/*` 保存旧分支和 detached HEAD。完整 bundle、脏文件差异和私有配置在既有本地 `backup/2026-09-08_takeover/` 中，不推送凭据。
恢复命令和实际还原验证见 [接手记录](../logs/worklog/2026-09-08_takeover.md)，本轮额外检查点见 [管理重建记录](../logs/worklog/2026-09-08_management_rebuild.md)。

历史快照保持原文，其内部相对链接按原仓库位置写成，未全部重写；需要原上下文时使用对应基线 checkout。现行兼容页同时提供新说明和原稿的直接路径。
