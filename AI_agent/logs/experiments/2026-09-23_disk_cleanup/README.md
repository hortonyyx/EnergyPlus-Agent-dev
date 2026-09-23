# 2026-09-23 Docker 磁盘清理证据

- `cleanup.json`：删除的扩展 ZIP 清单、npm/pip 缓存大小、文件系统清理前后读数。`host_reclaimed_bytes: null` 表示尚未验证 Windows D 盘回收量。
- `temporary_archive_plan.json`：39 个历史临时目录及处理前大小/最后修改时间。
- `archive_result.json`：归档路径、SHA-256、完整 tar 对比通过时间及实际移除目录清单。
- `server_cleanup.json`：宿主确认只有当前容器运行后，移除的 7 个旧 server 及保留版本。
- `pytest_cleanup.json`：经历史记录核实的 3 个完整测试 worker 临时树清理。
- `host_followup.json`：用户返回的容器身份确认、第二阶段实际变化和累计读数。

首阶段净减少约 24.19GB，用户返回宿主核验结果后又清理约 18.86GB；最终相对首次读数累计净减少约 **42.84GB**（两阶段之间存在并发工具写入，分项变化不直接相加作为最终读数）。5.39GB 压缩归档保留在当前容器 `/var/tmp/energyplus-cleanup-2026-09-23/`，不随 Git 保存。若后续删除当前容器，需先将归档复制出去。

详见[执行记录与恢复方法](../../worklog/2026-09-23_disk_cleanup.md)和[Windows 后续操作](../../../workflow/disk_cleanup.md)。没有删除项目源码、正式实验资产、容器、镜像或卷。
