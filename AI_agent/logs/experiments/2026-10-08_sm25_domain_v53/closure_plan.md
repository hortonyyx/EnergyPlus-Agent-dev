# sm25 domain-v53 完整运行收尾计划

状态：**仅准备，尚未执行复制、打包、提交、推送或清理。** 本文编写时运行仍在进行；活跃输出目录最后写入时间仍在变化。

本计划只处理本次工作树 `D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008`。不检查、不重试、也不删除此前被策略拦截的 G1、旧 scratch、v1、q1、q2 等路径。

## 已核对的项目约定

- `AI_agent/workflow/development.md` 要求整案从固定提交的独立工作树启动；退出后先把完整运行目录拷回主树 `AI_agent/archive/local_backup/`，再评估、打包，最后收回工作树。
- `AI_agent/archive/.gitignore:1` 的 `/local_backup/` 会忽略本次主树保留目录。
- 完整运行压缩后约 10 MB 以上时，归档放独立 evidence 分支，主线保留摘要、逐文件哈希清单及 evidence 分支/提交指针。
- 单文件超过 GitHub 100 MB 限制时，使用 Git for Windows 自带的 `split.exe` 按 90 MiB 分段；恢复时按文件名顺序拼接，先核整包 SHA-256 再解压。
- 最近的 G1 证据分支 `evidence/g1-takeover-2026-10-08` 是无主线内容的独立历史，保存 `*.tar.gz[.part-*]`、逐文件 manifest 和 summary；主线 `evidence_backup.json` 保存分支、提交、整包及各段哈希，并回读远端提交。

本次建议采用同一格式，分支名：

```text
evidence/sm25-v53-2026-10-09
```

该分支在本计划编写时本地和 `origin` 均不存在。

## 固定路径和身份

| 项目 | 值 |
|---|---|
| 冻结工作树 | `D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008` |
| 冻结提交 | `b55d47e7c82bb306c7ea838f00985648eef94304` |
| 活跃运行源 | `D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008\AI_agent\archive\local_backup\sm25_v53\sm25_role_v53` |
| 主树保留目标 | `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\sm25_v53\sm25_role_v53` |
| 实验记录 | `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\logs\experiments\2026-10-08_sm25_domain_v53` |
| launch receipt | 实验记录下 `launch_receipt.json` |
| 建议证据分支 | `evidence/sm25-v53-2026-10-09` |

只允许以上单一源目录进入本次运行归档。当前主树目标不存在，避免了与旧副本混合；若执行时目标已经存在，停止并人工比较，不能覆盖或 `/MIR`。

## 执行顺序与硬门槛

### 1. 等待运行确定退出

同时满足以下条件才开始复制：

1. `launch_receipt.json.status == "process_exited"`，并保存 `exit_code`、`ended_utc` 和 `inputs_unchanged`；
2. `input_manifest_after.json` 已生成，且 `inputs_unchanged == true`；
3. receipt 中的 `source_commit`、`worktree`、`output` 与上表逐字相同；
4. receipt 中的 `launcher_pid` 已不存在；
5. 活跃输出不再写入。以退出 receipt 为主，不用“若干分钟无事件”代替退出；
6. 读取最终 `events.jsonl`、根 receipt/delivery 状态，记录完成、失败、unknown、部分交付等真实结论。退出码非零或没有 delivery 不妨碍保存证据，但必须如实写进 summary。

若 launch receipt 没有完成态，即使进程似乎消失也先停下，不打包半写文件。

### 2. 拷回主树 ignored `local_backup`

再次断言源存在、目标不存在、源解析后的绝对路径属于本次冻结工作树。使用不带删除语义的复制，例如：

```powershell
$taskSource = 'D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008\AI_agent\archive\local_backup\sm25_v53\sm25_role_v53'
$taskDestination = 'C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\sm25_v53\sm25_role_v53'
robocopy $taskSource $taskDestination /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ
```

接受 robocopy 退出码 0-7；8 及以上视为失败。禁止 `/MIR`、`/PURGE`、先删目标或在源仍活跃时增量补拷。

### 3. 逐文件校验源和主树副本

在实验目录生成：

- `run_source_manifest.json`
- `run_copy_manifest.json`
- `run_copy_summary.json`

两个 manifest 都按相对 POSIX 路径排序，每个普通文件记录 `path`、`bytes`、`sha256`。扫描时拒绝 reparse point、符号链接、超出根目录的路径；不把目录时间戳作为内容身份。

通过条件：

```text
source file_count == copy file_count
source total_bytes == copy total_bytes
每个相对路径、字节数、SHA-256 完全相同
第二次源清单 == 第一次源清单
```

最后一项用于证明复制/哈希期间源没有继续变化。任何差异都停止，不进入归档分支。

### 4. 生成并回读验证归档

从主仓库根目录打包主树副本，使归档内保留项目相对路径：

```text
AI_agent/archive/local_backup/sm25_v53/sm25_role_v53/...
```

归档基名使用 `sm25_v53_run.tar.gz`。生成：

- `sm25_v53_run_manifest.json`：内容与已通过的 copy manifest 一致；
- `sm25_v53_run_summary.json`：`mode`、运行结论、冻结提交、版本、文件数、源字节、归档字节、整包 SHA-256、`all_archived_file_hashes_verified`；
- `sm25_v53_run.tar.gz`，若超过 100 MB 则只向 evidence 分支加入 `sm25_v53_run.tar.gz.part-000` 起的 90 MiB 分段。

回读不能只做 `tar -tf`。用 Python `tarfile` 流式读取包内每个普通文件，拒绝绝对路径、`..`、符号链接、硬链接和设备节点，并将每个 member 的字节数/SHA-256 与 manifest 逐项比较。只有完整包 SHA、文件数、总字节数和所有文件哈希均匹配时，summary 才能写：

```json
"all_archived_file_hashes_verified": true
```

分段后还需按文件名词法顺序拼接到一个临时文件，确认拼接后的整包 SHA-256 与分段前相同。记录整包和每段的 `bytes`/`sha256`。

### 5. 保存到独立 evidence 分支

使用单独的空 evidence 工作树，避免切换或污染主工作树：

```powershell
$taskEvidenceTree = 'D:\EnergyPlus-Agent-worktrees\evidence-sm25-v53-20261009'
git worktree add --orphan -b evidence/sm25-v53-2026-10-09 $taskEvidenceTree
```

该分支只加入以下文件：

```text
sm25_v53_run_manifest.json
sm25_v53_run_summary.json
sm25_v53_run.tar.gz                 # 仅当不需要分段
sm25_v53_run.tar.gz.part-*          # 需要分段时替代整包
```

提交信息建议为 `Preserve sm25 domain-v53 full-run evidence`。提交后推送：

```powershell
git push -u origin evidence/sm25-v53-2026-10-09
```

回读 `git ls-remote --heads origin refs/heads/evidence/sm25-v53-2026-10-09`，要求远端 SHA 与本地 evidence commit 完全相同；再 fetch 该 ref 并核对 tree 文件集合。不要只因 push 返回 0 就标记 `remote_verified=true`。

### 6. 主线留下可恢复索引

在本实验目录写 `run_evidence_backup.json`，字段至少包括：

- evidence 分支、最终 commit、`remote_verified`；
- 冻结提交、domain/runtime 版本、运行 case 和真实退出状态；
- 主树 ignored 副本路径；
- manifest 与 summary 的文件哈希；
- 整包文件数、源字节、归档字节、整包 SHA-256；
- 每一段的名称、字节数、SHA-256；
- 恢复方法：按段名拼接、核整包 SHA、解到独立恢复目录、再按 manifest 核每个文件。

该索引及最终运行/行为/质量结论在主线提交并推送后，再进入工作树清理。主线不要提交 ignored 完整运行副本。

### 7. 删除本次临时工作树

以下全部成立后才删除：

- 主树副本与源两轮清单完全相同；
- tar 回读逐文件验证通过；
- evidence commit 已推送并从远端 ref 回读相同；
- 主线恢复索引已提交并推送；
- `git worktree list --porcelain` 中该路径仍对应 detached `b55d47e7...`；
- 没有本次运行进程仍引用该路径。

解析并逐字核对目标为 `D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008` 后，只执行一次 Git 自身的收回：

```powershell
git worktree remove --force 'D:/EnergyPlus-Agent-worktrees/run-sm25-v53-20261008'
```

之所以需要 `--force`，是该工作树包含已忽略的完整运行产物；前述复制、归档和远端验证是使用它的先决条件。执行后分别检查：

1. `git worktree list --porcelain` 已无该登记；
2. `Test-Path -LiteralPath 'D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008'` 为 false。

两项必须分开记录。若 Git 收回被 policy 阻止、只清掉登记但磁盘目录仍在，或返回其他错误，立即停止；不要改用 `Remove-Item`、`cmd /c`、Python `shutil.rmtree` 或重试旧 G1/scratch 路径。把精确回执写入本实验目录，交给用户以管理员权限处理残留。

独立 evidence 工作树在提交、推送、远端回读完成且自身 clean 后，可用不带 `--force` 的 `git worktree remove` 收回；若失败同样只记录，不换删除手段。

## 本轮明确不做

- 运行仍活跃时不生成最终 manifest、压缩包或副本；
- 不修改冻结工作树、活跃运行产物、生产代码或管理总文档；
- 不把 `unknown_write_investigation` 的局部结论写成整案通过；
- 不执行任何旧工作树、旧 scratch 或 G1 残留的删除/重试；
- 本计划本身不授权或执行 push 与删除，实际操作仍需满足上述可核验门槛。
