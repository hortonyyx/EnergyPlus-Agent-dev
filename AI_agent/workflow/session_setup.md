# 会话与环境

开发仓库：`D:\Sim-BIM-Agent\repo`。桌面发布目录固定为 `Sim BIM Agent`，版本以自身 `release-manifest.json` 为准；开发助手不在发布目录中编辑。更新/回滚使用 [发布工具](../../scripts/release/update_product.ps1)，不再创建桌面版本目录。

每次读取 [Agent.md](../Agent.md)、[roadmap](../project/roadmap.md)及唯一最新交接，再按任务查设计/约束。历史按问题搜索，不自动加载全部旧节点。

```powershell
Set-Location D:/Sim-BIM-Agent/repo
. ./scripts/activate_windows.ps1
code --reuse-window --remote= D:/Sim-BIM-Agent/repo
```

新建开发环境使用`uv sync --frozen --python 3.12`，已有缓存可加`--offline`；普通改动不反复重建。确保实际Python和PYTHONPATH均来自当前检出。不得复制旧路径的editable环境或让发布程序导入开发源码。

Codex/其他客户端项目位置使用D盘repo。首条任务可明确引用`AI_agent/Agent.md`；不依赖某客户端自动发现嵌套文件。个人工具设置可从旧目录迁移，但凭据不入Git。主助手当前任务在旧工作路径继续时，所有命令需显式指定D盘repo。

短期工作树位于`D:/Sim-BIM-Agent/worktrees`。运行、检查缓存和历史分别外置到`runs`、`cache`、`archive`；运行输入只取获准案例，不共享整个D盘。

版本和实验身份按 [开发方式](development.md) 登记。换模型或收工更新仓库交接，助手记忆只留入口索引。
