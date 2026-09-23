# 2026-09-23 Docker 磁盘清理证据

- `cleanup.json`：删除的扩展 ZIP 清单、npm/pip 缓存大小、文件系统清理前后读数。`host_reclaimed_bytes: null` 表示尚未验证 Windows D 盘回收量。
- `temporary_archive_plan.json`：39 个历史临时目录及处理前大小/最后修改时间。
- `archive_result.json`：归档路径、SHA-256、完整 tar 对比通过时间及实际移除目录清单。

清理净减少约 24.19GB（落盘后的文件系统读数）；5.39GB 压缩归档保留在当前容器 `/var/tmp/energyplus-cleanup-2026-09-23/`，不随 Git 保存。若后续删除当前容器，需先将归档复制出去。

详见[执行记录与恢复方法](../../worklog/2026-09-23_disk_cleanup.md)和[Windows 后续操作](../../../workflow/disk_cleanup.md)。没有删除项目源码、正式实验资产、容器、镜像或卷。
