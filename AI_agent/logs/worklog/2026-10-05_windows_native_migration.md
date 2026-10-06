# Windows 原生开发环境迁移（10-05—10-06；原生验证完成，清理已授权、待回读）

用户交由 Windows 上的 Codex 主导，按 [迁移派工单](../../workflow/windows_migration_brief.md) 顺序推进。范围仅环境与平台兼容；不调用 DeepSeek、不跑整案，GLM 订阅只允许一次最小连通请求。撤容器须所有检查通过且用户明确确认；10-06 用户已确认删除范围，现等待 Docker Desktop 清理完成和空间回读。

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

## 2. 平台兼容

- 新增 `src/utils/file_lock.py`，以 portalocker 的真实操作系统锁替代 `fcntl`；存储、调用额度及仍被当前检查调用的两个证据脚本接入。portalocker 3.2.0 原已间接锁定，本次只声明直接依赖，没有升级其他依赖。
- Windows 不提供 POSIX 的目录 fsync；存储继续执行文件 fsync 与原子替换，断电时目录项持久性由文件系统负责，不能声称等同 Linux 的目录 fsync。
- 30 项存储、并发额度、证据打包检查通过（5.83 秒），包含跨进程争锁和最多 7 次票据的并发验证。没有改成空锁，也没有取消安全断言。权限恢复检查比较当前文件系统实际支持的源权限。
- 审阅包清单统一使用正斜杠，修正 Windows 下目录集合误报；47 项相关非变异检查通过（17.10 秒）。
- 第一轮全量检查在 MCP 工具调用持续等待时停止，保留原始日志，不计作完成；定位与后续修复结果见下文。

## 入口与沙箱的独立核对

- Windows 个人 Codex 设置已改为 `gpt-6-astra / xhigh`，原配置先备份到被忽略的本地备份目录。没有输出或提交凭据。
- CLI 0.156.1 从仓库根使用嵌套备用文件名不能加载 Agent.md；从 `AI_agent` 启动、使用 `Agent.md` 备用名则完整载入。直接 CLI 与 PowerShell 包装命令均已实测。项目本地配置增加该备用名，文档改为从 `AI_agent` 启动并 `--add-dir` 整个工作树。桌面根目录启动仍需要首条消息明确要求读取。
- Claude 新路径记忆索引已创建，正文只含读取 Agent.md 的一行索引。使用本机 HTTP 模拟接口检查首轮请求，索引和显式 `@AI_agent/Agent.md` 引用的 39 条实质长行全部载入；真实模型调用为 0。原容器 memory 保留。
- Codex `sandbox -P :workspace` 实际写入通过，仓库外单独探测目录的写入被拒绝。首次写 ACL 设置约 47 秒，首次 45 秒探测超时后，设置已完成，再探测通过。没有改用完全访问来完成验证。
- `session_setup.md`、`codex_entry.toml`、`development.md` 已替换为本机验证过的入口和 PowerShell 派工方式。未启动实际开发模型派工。
- 已请用户开启开发者模式以允许真实符号链接测试，并提醒仓库的 Defender 排除项；用户随后确认前者，并授权我尝试添加后者，实际结果见下文。
- Docker 仅作只读清点：两个已停止容器均引用本项目开发镜像；数据盘位于 `D:/Docker_wsl/DockerDesktopWSL/disk/docker_data.vhdx`，逻辑文件大小 162,866,921,472 字节（约 151.7 GiB）。这不是已释放空间，没有删除/压缩。

## 后续状态

10-05 入夜时第二轮全量测试进行中，尚未发出任何工作模型请求；之后的检查、GLM 一次请求与最终交付进展见下节。撤容器始终须检查通过和用户确认。

## 10-06 凌晨：全量结果与兼容修复

- 第二轮全量已完成：`214 failed, 5266 passed, 17 skipped, 13 xfailed, 48 errors`，1979.64 秒。原始 XML、日志在被忽略的本地备份目录；这是迁移中间结果，不是通过结论。
- 第一批修复统一 UTF-8/LF 产物字节，使 manifest 中的哈希与落盘内容相同；评分双文件继续保留文件 fsync、校验、原子替换及失败回滚，Windows 不执行不支持的目录 fsync。GT 临时文件在权限设置异常时也能关闭句柄。DXF 生成器固定 LF，历史源 DXF 不变。
- 两张图分别在 Windows 和临时启动的旧 Linux 容器里生成；旧容器均恢复停止。旧 PNG 文件哈希仍与原测试常量完全一致，两端模式、尺寸、全部像素完全相同。差异仅为 zlib 1.2.11 与 zlib-ng 的 PNG 编码。将原 Linux PNG 保存为测试夹具，保留其字节哈希，同时严格比较所有像素；评分 sidecar 除已核对的 PNG 编码哈希外仍满足原完整内容哈希。没有更换几何/评分答案。
- 修复后的失败项复测：245 通过、23 失败（130.60 秒）；再修复剩余问题后这 23 项全部通过（19.62 秒）。75 步历史回放另行诊断，最终全量仍待进行。
- 用户已开启开发者模式；原生非管理员 Python 实际创建、读取符号链接通过，相关越界测试已在上述复测中执行。
- 用户授权我添加仓库 Defender 排除项。提权执行失败，系统返回 `0x800106ba`；回读确认 Windows Defender 原本未运行、实时防护关闭，排除项未添加。我没有更改服务/防护启停设置。后续启用防护时仍应补排除项。
- 三份案例配置的 `runtime_configuration check` 返回 ready：两份 GLM 案例、一份 Qwen 27B 案例。只检查配置，未 launch；历史配置不改，新配置位于 `workflow/configs/windows_migration/`，凭据相对仓库根，run_root 为本机用户目录。
- **GLM 唯一最小请求已完成，不再重复：** 新底座 `HttpAnthropicAdapter` 经审核的 GLM 订阅 Anthropic 路线，`glm-5.3-flash`、low、max_tokens 128；返回 OK/end_turn，input 17、output 3、cache_read 0，成功请求 1 次、重试 0 次。证据 `glm-connectivity-attempt.json` 与 `glm-connectivity-result.json` 只存非敏感元数据；一次性标记阻止误重试。DeepSeek、Paratera 和整案模型运行均为 0。
- 75 步历史离线回放复核通过：实际工具、原始调用参数、状态/证据/既定错误断言全部执行，响应为预先保存的脚本，没有真实模型请求；未改回放断言。原失败随文件字节与路径修复消失。
- 最终 MCP 烟测已完成：实际启动 `run_bim_agent.py serve` 四次，coordinator/coordinator_mesh/readonly/readonly_mesh 分别列出 43/50/14/19 个工具，全部匹配 `t1-20261006-win.3` 登记哈希。登记的 58 个 Agent 文件也验证通过。
- 代码固定于 `3b3ba233` 后启动第三轮全量，使用原生 `.venv/Scripts/python.exe -m pytest -n 2 tests`，正在等待最终结果。到此已完成 8 个迁移提交并正常 push。
- PowerShell 5.1 会剥掉传给原生 CLI 的内部双引号；文档命令已改用 TOML 单引号。Windows PowerShell 5.1、PowerShell 7.6.5 分别执行 `codex debug prompt-input` 成功，解析后都包含完整 Agent.md（并逐条核对 31 条超过 80 字符的长行）；0 模型请求。
- 第三轮在 89% 时出现一次工作进程异常退出：`test_long_run_recovers_write_interrupted_before_intent`。不是断言失败；日志显示额外启用的 `faulthandler_timeout=120` 打印到半途时发生 Windows access violation，系统事件指向 Python 3.12.10 的 `python312.dll`、RVA `0x27e990`，邻近导出 `_Py_DumpTracebackThreads`（RVA `0x27e514`）。该用例在第二轮曾通过。随后保持项目代码和断言不变、移除额外诊断计时器，用默认设置复验；第三轮本身不计作全量通过。
- 第三轮最终为 `1 failed, 5534 passed, 17 skipped, 13 xfailed`，2323.07 秒；唯一失败是上述工作进程崩溃。同一用例按默认设置、仍用两个 worker 单独复验通过（225.83 秒）。两次 5 秒诊断小样没有稳定复现崩溃，因此只将异步堆栈诊断列为首要解释，不宣称已证明某个上游缺陷。没有修改项目限额、检查断言或故障恢复逻辑。
- 最后复核时进一步收紧几何事实比较：闭环可循环换起点，但保留腔体分组顺序，并拒绝分组交错；新增两条反例，相关 18 项检查通过（19.05 秒）。测试改动已提交并推送 `cdd2e2e6`（本轮第 9 个提交），生产 Agent 仍为 win.3。
- **第四轮全量通过：** 固定于 `cdd2e2e6050cbd563767d9657b5865e3d80db752`，使用 `python -m pytest -n 2 tests`，仅加详细输出和 JUnit 记录，不再添加堆栈诊断计时器。`5537 passed, 17 skipped, 13 xfailed, 203 warnings`，0 failed、0 errors，2033.25 秒（33 分 53 秒），进程退出码 0。上一轮崩溃用例及全部长任务恢复检查在本轮都通过；运行保护和测试断言未因该崩溃而削弱。
- 用于核实临时目录递归清理是否保留链接目标的探测命令，被工具自动审批策略以 `blocked by policy` 拒绝，未执行、未绕过；没有通过其他工具重试删除。pytest 本身的正常临时目录保留/回收机制继续由测试工具管理。

## 改动文件与边界

- 环境：`pyproject.toml`、`uv.lock` 声明原已锁定的 portalocker；`scripts/activate_windows.ps1` 接好本机解释器、UTF-8 与当前检出。
- 文件与路径：`src/utils/file_lock.py`、`src/agent_runtime/{store,call_quota,versions}.py` 及 `src/agent/execution/`、`src/agent/judge/` 的相关模块处理真实锁、原子写入、换行、相对路径、临时目录与 Windows 子进程环境；`isolation_templates/guard.py` 从实际仓库注入禁止路径并识别 Windows 路径。
- 运行入口：`scripts/glm_code.py`、`scripts/tool_scripts/run_bim_agent.py`、`gt_from_dxf.py`、`run_stage.py` 和 BIM 工具辅助模块；`src/agent/runtime_*.py` 保持跨平台路径、输出及命令格式。Windows MCP 在读取标准输入前载入 SciPy，避免第一次数值调用初始化 DLL 时等待输入锁。
- 配置与登记：新增 `workflow/configs/windows_migration/` 的两份配置文件；Agent 版本登记追加 win.1—win.3，不覆盖旧登记。10-05 原配置、历史实验数据和原始输入未改。
- 验证：`tests/native_shell.py` 明确找到 Git for Windows 的 Bash；相关检查适配换行、锁、权限、路径及 PNG 编码差异；`tests/facts_equivalence.py` 仅规范闭环起点并验证派生标识，反例保护所有事实字段。两张原 Linux PNG 入测试夹具，旧哈希与每个像素继续核对。
- 当前检查仍会执行四个历史证据脚本，因此只修改它们的平台兼容逻辑：`2026-10-02_harness_stage0/{build_samples,extract_sources}.py`、`2026-10-02_harness_stage3/evidence_pack.py`、`2026-10-04_absorb_a3r/sequence_probe.py`；原始实验数据保持不变。
- 管理文档：`workflow/{session_setup,development}.md`、`workflow/codex_entry.toml`、`project/roadmap.md` 和本记录。最终核验摘要将附完整文件清单，原始含本机配置的诊断材料仍留在忽略目录。

## 最终核验与剩余事项

- 完整结果、76 个改动文件的清单、代码提交、烟测、跳过原因及原始日志哈希见 [核验摘要](../experiments/2026-10-06_windows_native_migration/verification.json)。原始日志留在本地忽略目录；没有提交凭据、个人配置或会话备份。
- 17 个跳过分别为：8 个 EnergyPlus 25.1 可执行文件/天气/探测夹具不可用，1 个 Windows 没有 SIGALRM，6 个依赖 Linux `setpriv`，2 个必须显式选择的真实提供方测试。EnergyPlus 是派工单允许以后再装的可选下游，真实提供方测试按本次费用约束未启用；Windows 的真实链接、路径越界、只读访问和沙箱写入已另行实测。
- 13 个预期失败保持原有状态：9 个确定性命名金标待更新、2 个 F-56 工具值检查、1 个 F-52B staging 写入边界、1 个暂缓的 free-end non_zoning 路径。本次没有新增跳过或预期失败来掩盖平台兼容问题，也不宣称这 13 项已经修复。
- 最终测试数为 5567：相对 Linux 记录新增 11 项检查（真实文件锁 2 项、事实比较反例 9 项），Windows 多 15 项环境性跳过，因此通过数为 5537；不是漏收集了原有测试。
- 三份案例配置、一次 GLM 订阅最小请求、四类真实 MCP 工具目录、Codex/Claude 新会话入口、PowerShell 5.1/7 与写沙箱均已核对。未运行建筑整案，未调用 DeepSeek 或 Paratera，不把环境通过当作建模质量已经恢复。
- 两份备份 SHA256 再次与原清单一致；gzip 完整流校验和 tar 目录均可读取。Codex 备份有 9599 个条目、445 个 rollout JSONL；临时资料备份有 53 个条目。SQLite 打包一致性的原有提示仍保留，不覆盖本机现有历史。
- 原生验收收尾时只剩用户确认 Docker 保留范围、手动清理和 D 盘释放量回读。当时 D 盘为 64.30 GiB 可用，未删除容器、镜像、卷或 VHDX。10-06 用户随后已确认范围，最新清理基线见下文；实际释放量仍待回读，不能提前把整个迁移标为完成。
- 本轮测试使用系统临时目录；最后一轮主目录为 `%TEMP%/pytest-of-Horton/pytest-91`，原始核验日志已另存。临时数据按 pytest 自身的保留机制回收，未绕过自动审批策略做递归删除。01:52 回读 C 盘约 24.86 GiB 可用，包含本轮尚保留的测试副本；D 盘释放量独立核对。

## 撤容器清单（检查通过且用户确认之后才执行）

只读清点为：停止容器 `ep_agent_dev`（`d183441550d5`）、`vibrant_murdock`（`d5136ba15fc0`）；开发镜像 `6d9cf088f586`（`vsc-energyplus-agent-dev-…:latest`）、EnergyPlus 镜像 `b8c8d7bfc335`（`nrel/energyplus:25.1.0`）；卷 `vscode`。仓库与已挂载的个人配置实际在 Windows；容器专有会话及临时资料的两份备份已校验，保留在本机忽略目录。

最终检查通过后，先由用户确认 Docker 中是否还有其他要保留的东西，以及上述内容能否删除。确认没有保留内容时，带用户在 Docker Desktop 操作：

1. Containers 中删除上述两个停止容器。
2. Images 的本地列表中删除上述开发镜像和 EnergyPlus 镜像。
3. 打开 Docker Desktop 的 Troubleshoot（问号/排障菜单），选择 **Clean up data**（旧版可能叫 Clean / Purge data），核对提示后清理 Docker 本地数据。这会清理全部 Docker 本地容器、镜像等数据；若还有别的项目要保留，不执行这一步，也不选择恢复出厂设置。
4. 操作完成后回读 D 盘可用字节和 Docker 虚拟磁盘实际状态，记录前后差额。开工可用 64.30 GiB；151.7 GiB 的 VHDX 逻辑大小不作为释放量承诺。

入口与行为依据 [Docker Desktop 官方排障文档](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/)。目前**尚未取得容器删除、数据清理或压缩的完成结果**。

## 10-06：清理授权与操作前基线

- 用户明确选择：保留 Docker Desktop 和仓库构建配置；两个旧容器、镜像和卷都可清理。无需为将来部署留下旧开发实例；部署时按当时的代码重新构建、验收，本次未验证生产部署。
- `.devcontainer/`、`docker/`、`pyproject.toml`、`uv.lock` 均已纳入 Git；本轮回读确认 `85a26408` 与远端 main 一致。软件、仓库、个人配置及本机会话备份保留。
- 10:52（Asia/Singapore）只读回查仍只有已批准的两个停止容器、两个镜像和 `vscode` 卷。清理前 D 盘可用 **69,112,606,720 字节（64.366 GiB）**；数据 VHDX 逻辑大小 **162,866,921,472 字节**。最终释放量应与这次紧邻清理的基线比较，不将逻辑文件大小当作已释放空间。
- 已给用户 Docker Desktop 的 Containers → Images → Troubleshoot / Clean up data 操作步骤；等待操作完成后回读 Docker 清单、D 盘可用空间和 VHDX 状态，再将迁移标为完成并提交收尾记录。
