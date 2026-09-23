# Docker 开发环境磁盘清理

## 先区分实际文件和 Windows 虚拟磁盘

本机 2026-09-23 核实：项目目录从 Windows C 盘挂载到容器；`/tmp`、容器内部工具和 `/vscode` 卷位于 Docker 数据盘。用户报告该数据盘的 `docker_data.vhdx` 位于 D 盘。容器内删除文件后，文件系统空闲量与 Windows D 盘实际回收量需分别验证，不能将两者混报。

清理优先处理可重新下载的安装包、缓存。临时审阅目录可能包含未提交修改和唯一诊断证据，不能因处于 `/tmp` 或容器已停止就整批删除。需要收拢时先压缩归档，再用 `tar --compare` 对原件作完整校验，校验通过且未被进程使用后移除原目录。归档保存位置、恢复方法和本次处理清单写入工作记录。

`/vscode/vscode-server/extensionsCache` 保存扩展安装 ZIP，与已展开使用的 `extensions` 目录不同；清缓存应检查文件类型、修改时间并保留近期文件。共享卷内的旧 server 版本需核实所有使用者，不能只凭当前容器的进程列表判断其他容器未使用。运行中的 uv 工具占用缓存时，不用 `--force` 绕过占用检查。

## Windows 侧继续核验

在 PowerShell 执行只读检查，先核对容器身份和挂载：

```powershell
docker ps -a --size
docker system df
docker inspect vibrant_murdock --format '{{json .Mounts}}'
docker inspect d5136ba15fc0 --format '{{.Name}} {{.State.Status}}'
Get-PSDrive D | Select-Object Name, Used, Free
```

`d5136ba15fc0` 是 09-23 清理时当前开发容器的 ID 前缀，后续环境变化后应重新核实。容器启动命令显示 `echo` 不能证明它没有开发用途；VS Code 可以通过 exec 在容器中运行其他进程。删除前还需检查容器写入层中的源码、配置和独有产物，并将需要保留的内容备份到容器之外。不要直接运行删除全部停止容器/卷的 prune 命令。

## 将空闲空间归还 D 盘

先在 Docker Desktop 的 **Settings → Resources → Advanced** 核实实际磁盘位置；官方路径说明见 [Docker WSL 文档](https://docs.docker.com/desktop/features/wsl/)。本轮容器没有 Docker socket、Windows 命令入口或 FITRIM 权限，无法在容器内完成宿主磁盘回收。

完成清理、保存工作并准备结束容器会话后，在 Windows 操作：

1. 退出 Docker Desktop，关闭依赖 WSL 的工作；`wsl --shutdown` 会结束所有 WSL 发行版以及当前开发会话。
2. 在管理员 PowerShell 运行 `wsl --shutdown`，然后进入 `diskpart`。
3. 在 DiskPart 中执行以下命令，将占位路径换成前面核实的实际文件：

```text
select vdisk file="D:\实际目录\docker_data.vhdx"
detail vdisk
compact vdisk
exit
```

不要在磁盘仍被 Docker 使用时强制操作。Microsoft 要求压缩对象为动态虚拟磁盘，且处于卸载或只读挂载状态，见 [compact vdisk 官方说明](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/compact-vdisk)。压缩实际回收量受空闲块状态影响；不能把 VHDX 大小与 `docker system df` 的差值直接承诺为可回收量，也不要为压缩而写满零文件。

重启 Docker Desktop 后复核开发容器可用性、VHDX 文件大小和 `Get-PSDrive D` 的剩余空间，记录 Windows 侧实际变化。
