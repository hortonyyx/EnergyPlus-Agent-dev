# 10-06 Opus：分工体系 v1 开工（进行中）

用户开工时说：“开工，现在已经完成了容器迁移，目前应该是运行在Windows环境了”。Opus 任项目经理，按[上一份交接](2026-10-05_windows_native_migration.md)与 10-05 定的路线推进第 ② 项“分工体系 v1”。

**用户本轮的话：**
- 中途：“还是先梳理一下再正式开工吧”。Opus 随即停下，整理了状态、第一版做法、强模型候选与价格、建议顺序和待定事项。
- 对梳理的答复：“可以，你综合把控”；以及对“强模型”的说明（五档原话见[决策](../../project/decisions.md) 10-06）：本项目以 4 档及以下为主力、接受 3 档，“如果3档单模驱动能做好，可以认为3档是相对目标的强模型，不代表是普遍意义上的强模型”。

## 开工核对

- Windows 原生：Python 3.12.10 从仓库 `.venv` 启动，`src.agent` 导入正常；PowerShell 7.6.5、codex-cli 0.156.1、Claude CLI 可用。C 盘余约 52.6 GiB，D 盘约 215.4 GiB。
- 主线 `c7ac1881` 干净、与远端一致，只有一个工作树。本会话 Codex 的 MCP 接口没连上，派工走命令行，不受影响。

## 强模型调研（0 次推理请求）

- Paratera 目录刷新一次，只列型号：86 项。新增与下线清单、2 档候选的官方参考价见[模型与费用](../../workflow/models.md) 10-06。
- 结论按用户口径收敛：第一阶段用 3 档，即 GLM 订阅 `glm-5.3-flash`；2 档候选本阶段不用，原拟的约 4 元强模型小测取消。

## Windows 派工方式实测（`codex sandbox -P :workspace`，0 次模型请求）

| 检查 | 结果 |
|---|---|
| 在 `%LOCALAPPDATA%` 下的目录启动沙箱进程 | 失败：`CreateProcessWithLogonW failed: 267`，原文档建议的工作树位置用不了 |
| 在桌面下的新目录、仓库目录启动 | 正常 |
| 工作树里 `git commit`（只给工作树写权限 ／ 另加主仓库 `.git` 写权限） | 两种都失败：写不进 `.git/worktrees/<名>/index.lock` |
| 独立本地克隆里 `git commit` | 失败：克隆自己的 `.git/index.lock` 也写不进 |
| 用虚拟环境完整路径运行 Python | 正常（3.12.10） |
| 沙箱里联网（默认，以及显式开网络） | 都能连上，返回 200 |
| `git status` 等只读命令 | 正常 |
| `Start-Process` 拉起的进程在工具调用结束后 | 继续运行 |

据此：工作树放 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\<任务名>`；工作空间写模式下所有 `.git` 都只读，Astra 不提交，改动留在工作树，Opus 复核后按报告给出的分组提交；用 `Start-Process` 启动派工，避开后台任务 2 小时上限。试验目录已删除。

## 派工

验收标准写在[验收记录](../../project/unified_agent_acceptance.md)的“分工体系 v1 · D1”“D1-A”两节；派工单：[D1](../experiments/2026-10-06_role_division_d1/brief.md)、[D1-A](../experiments/2026-10-06_role_division_analysis/brief.md)。

已派出（10-06 13:18 新加坡时间，主线 `e07764e6`）：
- D1：工作树 `EnergyPlus-Agent-worktrees/d1`，分支 `dev/astra-d1-20261006`，`gpt-6-astra`／max，线程 `01a10fa6-59e7-7de0-a19c-5666701880f7`。
- D1-A：工作树 `EnergyPlus-Agent-worktrees/d1a`，分支 `dev/sol-d1a-20261006`，`gpt-5.6-sol`／high，线程 `01a10fa6-59e7-7621-b5d8-de946c545dbe`。
- 两个工作树各建约 38 秒，各自 `.venv` 约 12 秒，导入均指向本工作树。启动脚本、提示、事件与错误输出在各工作树已忽略的 `AI_agent/archive/local_backup/<任务名>-dispatch/`。启动正常；错误输出里只有用户 Codex 配置的若干无关告警（未识别的设置、插件图标、名为 codex 的 MCP 连不上）。

**工作树位置调整（用户问“这个必须要这么做吗，要在桌面多一个管理文件夹吗”）：** 不必放桌面，限制只在 AppData。实测用户目录 `C:\Users\Horton\` 与 D 盘下的新目录都能启动沙箱并写入。以后工作树放 `C:\Users\Horton\EnergyPlus-Agent-worktrees\<任务名>`：与仓库同盘，三块盘都是固态。每个工作树约 3.6 GB，含 0.45 GB 虚拟环境。不放仓库目录里，以免标准答案多一份副本、旧底座防偷看的路径规则管不到。首批两个正在跑，中途移动会打断会话，所以做完收回后再删桌面那个文件夹。D 盘探测目录 `D:\EnergyPlus-Agent-worktrees-probe`（内有 4 字节的 probe.txt）在驱动器根下，删除被本机工具的安全规则拦下，留给用户手动删除。
