# 2026-10-12：固定目录升级、回滚与清理边界

用户要求补齐升级/回滚、桌面固定为 `Sim BIM Agent`、旧版备份放 D 盘；随后明确只做轻量保存，更早历史已有 Git，不建设复杂的本地版本管理系统。

## 已完成

- [一个 PowerShell 工具](../../scripts/release/update_product.ps1) 提供 `plan`、`update`、`rollback`、`status`。支持 Windows 自带 PowerShell；用法已写入 [开发流程](../workflow/development.md) 和 [产品说明](../../product/README.md)。
- 桌面固定入口：`C:/Users/Horton/Desktop/Sim BIM Agent/Start.cmd`。当前 500 个 payload 文件来自提交 `d2b1c059578b6bec586772dd9dc8fbe5ed576325`，runtime-v7-20261011 / domain-v65-20261011。真实执行 v64 → v65 → v64 → v65，最终 doctor=ready，原 ChatGPT 账号本地 signed_in=true。
- 本次修改属于发布工具与文档；模型可见 domain、runtime 及锁文件没有变化，不递增其版本。桌面原路径 `.venv` 始终保留；授权、案例和输出未移动。
- `D:/Sim-BIM-Agent/archive/product-backup/previous.zip` 为上一版 v64：496 个 payload 文件和发布清单，**4,090,574 bytes（3.90 MiB）**。ZIP 内逐文件 SHA-256 已回读通过。另有约 138 KiB 的 `state.json` 和空更新锁；无环境、案例、输出或凭据。
- 成功的更新临时目录已清理。当前完整发布包 `D:/Sim-BIM-Agent/releases/desktop-update-20261012` 约 17.4 MiB，不含环境；更早版本按 Git 提交恢复、重新构建。

工具先核对来源清单、安装文件、路径边界和冲突，再保全上一版；只更新变化文件、移除清单拥有的废弃文件，保留其他个人文件。拒绝运行中的产品和并发维护。每个文件替换采用同卷原子替换；待恢复状态写入后才修改安装。验收失败自动回滚；进程中断后拒绝新升级，使用同一 `rollback` 恢复。依赖有变化时按锁文件同步，若依赖恢复也失败则保留 pending，不虚报恢复成功。用户需结束当前运行，维护期间不启动新实例。

## 验证

| 范围 | 结果 | 耗时 | 真实模型请求 |
|---|---|---|---|
| 升级/回滚专项：固定路径、单备份、个人文件、路径越界、校验失败、中断恢复、并发/运行保护 | 最终 20 通过，0 失败、0 跳过 | 18.70 s | 0 |
| 相邻发布入口与身份检查 | 35 通过，复用首次组合批有效结果 | 原组合批 14.99 s，未独立计时 | 0 |
| 实际桌面 v64 → v65，产品自身隔离验收 | 通过 | 29.000 s | 0 |
| 实际桌面 v65 → v64 回滚，同样隔离验收 | 通过 | 26.875 s | 0 |
| 实际桌面 v64 → v65 再升级，同样隔离验收 | 通过 | 26.875 s | 0 |
| 最终 Start.cmd doctor + auth status、ZIP 内 496 文件校验 | ready、signed_in=true、全部哈希一致 | 未单计 | 0 |

专项检查使用小型合成安装与验证/依赖替身测试文件保护、故障和恢复；桌面三次切换使用真实产品验证器、各自安装目录的 Python、隔离 cwd/PYTHONPATH 和禁止外联的 guard，包含合成源 BIM、MCP 工具与 runtime 中断恢复。未运行真实图纸、照片/mesh、EnergyPlus 或付费服务；账号检查仅读取本地状态，不刷新令牌或获取目录。

最初组合批为 48 通过、4 失败，失败均在新升级工具的 Windows PowerShell 兼容处理：哈希命令自动加载、压缩程序集与 .NET 空字符串绑定。修正后专项 17 通过；增加保护/中断场景并减少重复文件操作后，最终 20 通过。相邻 35 项不受这些修正影响，没有重复跑全量。

小型证据入口：

- `D:/Sim-BIM-Agent/cache/pytest/product-update-20261012/32a6d1c11471/results.xml`：最终专项。
- `D:/Sim-BIM-Agent/cache/pytest/product-update-20261012/f5de40745804/results.xml`：首次组合批及相邻 35 项。
- `D:/Sim-BIM-Agent/cache/product-update-roundtrip-20261012.json`：三次真实切换摘要。
- `D:/Sim-BIM-Agent/cache/product-update-final-20261012.json`：最终桌面入口与登录状态。
- `D:/Sim-BIM-Agent/archive/product-backup/state.json`：最近一次更新身份、备份哈希和验证结果。后续更新会正常替换此记录。

## 清理尚未完成

已核验多余桌面 `Sim BIM Agent v65`、4 个旧 D 盘 releases 目录及 `archive/desktop-before-domain65-20261011`：全部 payload 哈希一致，没有未知程序文件，各来源提交均已在 origin/main。这 6 个重复副本共 1,489,807,920 bytes（约 1.39 GiB，包含可再生环境），原计划核验后移除。

**自动审批拒绝了这一批旧目录的递归删除，仅返回 `blocked by policy`，未给具体原因；命令未执行。** 没有换工具或拆分重试该删除。原位升级与回滚不受影响，但桌面额外目录以及这些 D 盘重复副本仍存在，不能称“已只剩一个目录”或“所有本地副本已精简”。

核验与拒绝记录：`D:/Sim-BIM-Agent/cache/product-update-cleanup-20261012.json`。可供用户审阅的单次脚本为 `D:/Sim-BIM-Agent/cache/finish-product-cleanup-20261012.ps1`：默认仅重新核验、列出范围，明确传 `-Apply` 才删除；不会处理固定安装、当前发布包、previous.zip、案例或运行数据。该脚本未代用户执行删除。

Git 历史与旧版本登记未改写，没有新建工作树。最后磁盘读数约 C 51.68 GiB、D 170.06 GiB；重复副本尚未释放。下一步模型与照片/细度讨论保持原边界，没有借此启动模型实测。
