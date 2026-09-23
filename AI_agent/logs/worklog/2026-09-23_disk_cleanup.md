# 09-23 Docker 开发环境磁盘清理

## 范围与核实结果

用户报告 D 盘剩余约 39.6GB，Docker `docker_data.vhdx` 约 174.37GB，要求先清理项目开发环境。本轮暂停产品开发，仅清理磁盘。

- 开工为 `main`，提交 `eba31f56`，工作树干净，只有主工作树。
- 当前开发容器 ID 前缀 `d5136ba15fc0`。没有 Docker CLI/socket、Windows PowerShell/WSL 命令入口，无法独立复核宿主容器清单与 VHDX 实际文件大小。
- 从实际挂载确认：项目源码位于 Windows C 盘；`/vscode` 是 Docker 卷，容器内部 `/tmp` 和工具文件也使用 Docker 数据文件系统。
- 容器内文件系统初始使用量 84,070,440,960 字节。`/tmp` 约 29.44GB；`/vscode` 约 23GB，主要为扩展安装包及历史 server 程序。
- 用户提供的 `vibrant_murdock` 53.7GB、旧 `ep_agent_dev`、构建缓存等数据作为待核线索；没有删除容器、镜像、卷或运行全局 prune。

## 已清理缓存

扫描并确认 ZIP 格式后，删除两处 `extensionsCache` 中超过一天未修改的 222 个扩展安装包，文件字节数合计 17,640,787,035；相应文件系统空闲量增加 17,641,472,000 字节。已展开插件、用户数据和近期缓存保留。

另清除 npm 下载缓存 561,029,120 字节和 pip 下载缓存 49,238,016 字节（两者按已分配空间统计）。uv 缓存被在用工具占用，普通 prune 等待锁后主动终止，没有用 force。环境没有 pip 模块，未安装新依赖，改为直接清除已识别的 pip 缓存目录。

共享卷有约 6GB 历史 VS Code server。当前容器使用 `7debcd0e2acdea1c52de81bf9ee1620444407dda`；由于无法核查其他容器是否使用其他版本，本轮保留 server 程序。

## 历史临时目录归档

选择超过 100MiB、全部内容超过 30 天未修改且没有当前进程 cwd/exe/fd 引用的 39 个目录，原已分配空间合计 11,933,442,048 字节。排除近期实验和仍供日常验证的 `/tmp/ep-bim-browser-qa`。

归档路径：`/var/tmp/energyplus-cleanup-2026-09-23/historical-tmp.tar.gz`。该本地归档不入 Git，父目录权限 0700；保留历史源码、Git 对象和独有测试/审阅文件。最终归档 5,386,432,687 字节，`tar --compare` 与全部原件完整对比通过，重新检查原件修改时间和进程引用后，已移除全部 39 个原目录。逐目录结果与归档 SHA-256 保存在 `archive_result.json`。

需要恢复时，先查看归档清单，再将所需目录解压到一个新的空目录，避免覆盖后来同名的临时文件：

```bash
tar -tzf /var/tmp/energyplus-cleanup-2026-09-23/historical-tmp.tar.gz
mkdir /tmp/energyplus-history-restored
tar -xzf /var/tmp/energyplus-cleanup-2026-09-23/historical-tmp.tar.gz -C /tmp/energyplus-history-restored
```

归档仍在当前容器内部；后续如删除该容器，需先将归档复制到容器之外。

## 验证与待完成项

移除原件后首次读数净减少 24.45GB；执行 `sync -f /vscode` 将待写数据落盘后，最终已用量为 59,877,617,664 字节，较清理前减少 24,192,823,296 字节，约 **24.19GB / 22.53GiB**。缓存文件与目录大小是分项统计，最终净变化采用落盘后的文件系统读数；并发工具的小量写入及文件系统开销可影响读数。Windows D 盘实际回收量仍未知。

缓存清理后 NumPy、Shapely、Pillow、pytest 均可导入，当前编辑器/助手继续工作。项目源码、原图、正式实验产物及生产依赖没有清理，本轮不运行模型或全量测试。

`fstrim -v /vscode` 返回 `Operation not permitted`，没有成功向宿主执行块回收。Windows D 盘最终空闲量和 VHDX 收缩量尚未验证。已经请求用户在 Windows PowerShell 提供容器大小/挂载的只读输出，以继续核实大容器。

宿主核验及压缩步骤见[磁盘清理操作说明](../../workflow/disk_cleanup.md)；最后退出 Docker/关闭 WSL 会中断当前会话，需在 Windows 完成。VHDX 与 Docker 统计的差值不能直接承诺为可回收字节数。

逐项执行清单见[清理证据目录](../experiments/2026-09-23_disk_cleanup/)。产品研发下一入口仍是 [09-22 BIM 输出与 Agent 主线讨论](2026-09-22_reconstruction_agent_reframing_close.md)。

## 用户返回 Windows 结果后的续清理

用户提供 `docker ps -a --size` 和 `docker inspect`：当前 `d5136ba15fc0` 就是 `vibrant_murdock`，也是唯一运行中的容器，另一只 `ep_agent_dev` 已停止。前者不能作为“无用旧容器”删除；`echo` 启动命令不代表其实际用途。挂载结果再次确认源码在 C 盘、`vscode` 为独立卷。用户贴出的 53.7GB 是其执行命令时的 Docker 统计，不覆盖本轮实时文件系统读数。

核对全部当前进程的程序路径、工作目录和打开文件后，清除 7 个超过一周未修改的旧版 VS Code server，保留当前 `7debcd0e2acdea1c52de81bf9ee1620444407dda` 及 09-17 的 `645f29cc3176500b4b5762ba887cf2a7f0ffdf2c`。确认目录为 VS Code 程序分发包，删除对应旧链接；文件系统净减少 4,988,264,448 字节，卷现约 1.4GiB。

继续发现 `/var/tmp/ea2_astra_pytest` 和 `/var/tmp/ea2_review_glm_pytest` 的历史完整测试副本。与 [09-06 执行记录](../reviews/execution/2026-09-06d_Ea2_evidence/resumption.md)、[复核记录](../reviews/verdict/2026-09-06g_Ea2_crossreview_claude.md) 和现有测试函数核实：`authorized_baseline`、`final_full`、`claude_full` 三目录仅包含各 6 个 pytest-xdist worker 的临时测试树，全部内容超过两周未修改且无当前进程引用。清除这三个可重建目录，净减少 13,873,688,576 字节。保留同级审阅报告、脚本、其他临时结果及仓库内正式测试原文；未将整个 `/var/tmp` 当缓存删除。

本次追加净减少约 **18.86GB**，最终文件系统使用量 **41,227,739,136 字节**；相对第一轮清理前净减少 **42,842,701,824 字节，约 42.84GB / 39.9GiB**。当前程序、备用程序、本地历史归档和审阅报告均存在，Python 依赖可导入，源码未改，无需重跑全量。

清单新增 `server_cleanup.json`、`pytest_cleanup.json`、`host_followup.json`。已经询问 VHDX 完整路径，宿主压缩和 Windows D 盘实际回收量仍待完成；没有删除任何容器、镜像、卷。
