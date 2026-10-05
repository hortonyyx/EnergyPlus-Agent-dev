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

## 2. 平台兼容（推进中）

- 新增 `src/utils/file_lock.py`，以 portalocker 的真实操作系统锁替代 `fcntl`；存储、调用额度及仍被当前检查调用的两个证据脚本接入。portalocker 3.2.0 原已间接锁定，本次只声明直接依赖，没有升级其他依赖。
- Windows 不提供 POSIX 的目录 fsync；存储继续执行文件 fsync 与原子替换，断电时目录项持久性由文件系统负责，不能声称等同 Linux 的目录 fsync。
- 30 项存储、并发额度、证据打包检查通过（5.83 秒），包含跨进程争锁和最多 7 次票据的并发验证。没有改成空锁，也没有取消安全断言。权限恢复检查比较当前文件系统实际支持的源权限。
- 审阅包清单统一使用正斜杠，修正 Windows 下目录集合误报；47 项相关非变异检查通过（17.10 秒）。
- 第一轮全量检查在 MCP 工具调用持续等待时停止，保留原始日志，不计作完成。正在单独定位，再重新全量验证。

## 入口与沙箱的独立核对

- Windows 个人 Codex 设置已改为 `gpt-6-astra / xhigh`，原配置先备份到被忽略的本地备份目录。没有输出或提交凭据。
- CLI 0.156.1 从仓库根使用嵌套备用文件名不能加载 Agent.md；从 `AI_agent` 启动、使用 `Agent.md` 备用名则完整载入。直接 CLI 与 PowerShell 包装命令均已实测。项目本地配置增加该备用名，文档改为从 `AI_agent` 启动并 `--add-dir` 整个工作树。桌面根目录启动仍需要首条消息明确要求读取。
- Claude 新路径记忆索引已创建，正文只含读取 Agent.md 的一行索引。使用本机 HTTP 模拟接口检查首轮请求，索引和显式 `@AI_agent/Agent.md` 引用的 39 条实质长行全部载入；真实模型调用为 0。原容器 memory 保留。
- Codex `sandbox -P :workspace` 实际写入通过，仓库外单独探测目录的写入被拒绝。首次写 ACL 设置约 47 秒，首次 45 秒探测超时后，设置已完成，再探测通过。没有改用完全访问来完成验证。
- `session_setup.md`、`codex_entry.toml`、`development.md` 已替换为本机验证过的入口和 PowerShell 派工方式。未启动实际开发模型派工。
- 已请用户开启开发者模式以允许真实符号链接测试，并按派工单添加仓库的 Defender 排除项；尚未收到完成确认。
- Docker 仅作只读清点：两个已停止容器均引用本项目开发镜像；数据盘位于 `D:/Docker_wsl/DockerDesktopWSL/disk/docker_data.vhdx`，逻辑文件大小 162,866,921,472 字节（约 151.7 GiB）。这不是已释放空间，没有删除/压缩。

## 后续状态

第二轮全量测试进行中；配置检查、GLM 唯一请求、最终 MCP 目录核对及最终交付仍待完成。Codex/Claude 入口与 Windows 写沙箱已独立核对，撤容器仍待全部检查通过和用户确认。尚未发出任何工作模型请求。

## 10-06 凌晨：全量结果与兼容修复

- 第二轮全量已完成：`214 failed, 5266 passed, 17 skipped, 13 xfailed, 48 errors`，1979.64 秒。原始 XML、日志在被忽略的本地备份目录；这是迁移中间结果，不是通过结论。
- 第一批修复统一 UTF-8/LF 产物字节，使 manifest 中的哈希与落盘内容相同；评分双文件继续保留文件 fsync、校验、原子替换及失败回滚，Windows 不执行不支持的目录 fsync。GT 临时文件在权限设置异常时也能关闭句柄。DXF 生成器固定 LF，历史源 DXF 不变。
- 两张图分别在 Windows 和临时启动的旧 Linux 容器里生成；旧容器均恢复停止。旧 PNG 文件哈希仍与原测试常量完全一致，两端模式、尺寸、全部像素完全相同。差异仅为 zlib 1.2.11 与 zlib-ng 的 PNG 编码。将原 Linux PNG 保存为测试夹具，保留其字节哈希，同时严格比较所有像素；评分 sidecar 除已核对的 PNG 编码哈希外仍满足原完整内容哈希。没有更换几何/评分答案。
- 修复后的失败项复测：245 通过、23 失败（130.60 秒）；再修复剩余问题后这 23 项全部通过（19.62 秒）。75 步历史回放另行诊断，最终全量仍待进行。
- 用户已开启开发者模式；原生非管理员 Python 实际创建、读取符号链接通过，相关越界测试已在上述复测中执行。
- 用户授权我添加仓库 Defender 排除项。提权执行失败，系统返回 `0x800106ba`；回读确认 Windows Defender 原本未运行、实时防护关闭，排除项未添加。我没有更改服务/防护启停设置。后续启用防护时仍应补排除项。
- 三份案例配置的 `runtime_configuration check` 返回 ready：两份 GLM 案例、一份 Qwen 27B 案例。只检查配置，未 launch；历史配置不改，新配置位于 `workflow/configs/windows_migration/`，凭据相对仓库根，run_root 为本机用户目录。
- **GLM 唯一最小请求已完成，不再重复：** 新底座 `HttpAnthropicAdapter` 经审核的 GLM 订阅 Anthropic 路线，`glm-5.3-flash`、low、max_tokens 128；返回 OK/end_turn，input 17、output 3、cache_read 0，成功请求 1 次、重试 0 次。证据 `glm-connectivity-attempt.json` 与 `glm-connectivity-result.json` 只存非敏感元数据；一次性标记阻止误重试。DeepSeek、Paratera 和整案模型运行均为 0。
