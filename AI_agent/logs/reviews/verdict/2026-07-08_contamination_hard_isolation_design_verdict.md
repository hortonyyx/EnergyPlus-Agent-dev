# 污染硬隔离机制化设计审查结论

结论：**APPROVE-WITH-CHANGES**。

设计方向正确：L1 clean-room 物理裁剪是本方案的安全核心，L2/L3 提供进程级显式拒绝、Bash 逃逸面收口与可审计日志，明显强于现行 `new_case_guide.md` 里“只喂 case_data + skill，prompt 禁 attempts/judge/gt”的约束。当前不建议 REJECT，因为不存在必须推翻的架构性错误；但 H2/H3 前必须修正权限语义、默认拒绝策略、hook 覆盖验证和 merge 并发语义，否则“硬隔离”容易被误表述成比实际更强。

## 对 §5 五个问题的逐项判断

1. **L2 deny 规则语法：`Read(//abs/**)` 方向正确，但写法还不够完整。**
   - 已查 Claude Code 官方权限文档：Read/Edit 路径规则采用 gitignore 语义，`//path` 才是“从文件系统根开始”的绝对路径；`/path` 不是绝对路径，而是相对定义该 settings 的来源目录。用 `--settings <file>` 时，`/path` 会解析为 `<settings 文件所在目录>/path`。因此 `Read(//workspaces/**)`、`Read(//root/**)` 这类双斜杠写法与官方语义一致。
   - 更稳写法：用 `permissions.deny` 覆盖 repo、root、home、全局敏感区，同时用 `permissions.allow` 只放 staging，并设置明确的默认拒绝/受限模式；不要依赖“没有 allow 就不能读”的隐含行为。建议最小集：`Read(<staging 绝对路径双斜杠>/**)`、`Edit/Write(<staging>/out/**)`、`Bash` 由 hook 放行；`deny` 加 `Read(//workspaces/EnergyPlus-Agent-dev/**)`、`Read(//root/**)`、`Read(//home/**)`、`WebFetch`、`WebSearch`、`Task`、`Agent`、`mcp__*`，并在真实 `claude -p --settings` 冒烟中验证。
   - 注意：官方文档明确 Read/Edit deny 会作用于内置文件工具和 Claude Code 能识别的 Bash 文件读取命令，但**不作用于任意 Python/Node 子进程自己打开文件**。因此 L2 不能替代 L1 和 L3 的 Bash allowlist。

2. **L3 Bash 白名单不会掐死必要动作，但要修 cv_probe 打包方式并避免过窄命令匹配。**
   - `cv_probe.py` 的运行入口只需要 Python 调用、图像路径、out-dir、JSON 参数和读回产物；overlay 回读属于 Read，不必通过 Bash cat。白名单 “`python tools/cv_probe.py ...` + 少量 `ls/file`”对 reading 执行器是足够的。
   - 但是现有 `scripts/tool_scripts/cv_probe.py` 通过 `Path(__file__).resolve().parents[2]` 推导 repo root 并 `from src.agent.reading.cv_toolbox import ...`。如果设计按 §1 把入口“平铺为 `tools/cv_probe.py`”、包也平铺为 `tools/`，这个 import 形态会失效，或在 staging 里错误地把 `/tmp/ep_isolation` 当 root。H1/H2 需要明确采用哪一种：保留 `src/agent/reading/cv_toolbox` 目录结构并设置 `PYTHONPATH=<staging>`，或生成一个 isolation 专用 wrapper 改为从本地 `tools.cv_toolbox` import。
   - Bash 白名单建议用 `shlex.split` 解析命令，允许 `python`/`python3`/`sys.executable` 三种等价入口；逐参解析 path-like 参数并 `resolve(strict=False)` 后确认在 staging 内。不要只做字符串前缀匹配。

3. **MANIFEST 禁运 token 表基本够，但 `judge` 作为全路径 token 会误伤，需要按类别/相对路径断言。**
   - 必须拒入：`case_tests/test_baseline/gt/**`、`gt.json`、`<case>/run_*/**`、`0_reading/attempts/**`、`attempts/**`、`judge.json`、`verdict*`、`grade*`、`*_score*`、`report/` 中由 gt/judge 派生的产物，以及 skill 里的 `judge_rubric.md`。
   - `judge` 这个裸 token 过宽：它会误伤明确应剔除的 `judge_rubric.md`，但也可能误伤未来合法说明文本中的普通词。建议禁运断言分两层：路径/文件名精确规则为硬 block；内容或来源类别 token 只用于审计 warning。`prescan/candidates.json` 不含这些路径名，本身不应被误伤。
   - 还要补“来源路径不泄漏”检查：MANIFEST 若记录 `source_path`，不应把 repo 中 `run_*`、gt、attempts 的绝对路径写入 staging 内 manifest；白名单文件的 source_path 可以记录，但最好以 repo-relative 记录，避免执行器 prompt 或 Read manifest 时获得不必要 repo 结构。

4. **merge 走既有 manifest append 可复用，但有并发和 hash 绑定坑，必须在 H3 显式处理。**
   - 现有 `new_attempt_dir()` 是 “读最大 N -> mkdir N+1”，`mkdir(exist_ok=False)` 能防覆盖，但并发两个 merge 会有一个 `FileExistsError`，没有自动重试或锁。`StageRunner.record()` 会把 `output.json` hash 写入 `checks.json` 和 manifest pointer，hash 绑定是有的；问题在于并发 merge 的失败语义和 manifest 保存的最后写赢。
   - H3 必须要求 merge 单进程串行，或在 `new_attempt_dir` 碰撞时重算 index 重试，并对 `run_manifest.json` 写入加锁/原子替换。否则两个 isolated reader 同时回收时，attempt append-only 不会破坏，但可能丢 manifest pointer 更新。
   - provenance 建议作为 attempt 目录内独立文件落盘，例如 `isolation_provenance.json`，并把它的 hash 纳入 `input_hashes` 或 `StageRecord` 扩展字段；只在外部日志记 settings/guard/access_log 摘要不足以绑定 accepted output。

5. **更简做法：可以简化 L2/L3，但不能替代 L1。**
   - 同等机制强度的最简安全核心是：只保留 L1 物理裁剪 + wrapper 自己执行 cv_probe + Claude 仅用 Read/Write/Edit 读写 staging/out，完全不把 Bash 暴露给模型。这会比“允许 Bash 但靠 hook 解析”更简单、更强。
   - 如果需要模型按需调用 cv_probe，则当前 L3 是合理折中；但应把 Bash 缩到一个固定子命令包装器，例如 `python tools/run_cv_probe.py --request <json>`，由 wrapper 校验 JSON schema 和路径。这样比解析任意 `cv_probe.py` CLI 参数更容易测试。

## Findings

### MAJOR-1：L2 当前表述缺少默认拒绝/allowlist 模式，可能保留 cwd 或继承配置带来的隐式访问。

设计写了 `deny: Read(//workspaces/**), Read(//root/**)` 和 `allow: Read(<staging>/**)`，但没有规定 `permissions.defaultMode`、`additionalDirectories`、用户/项目 settings 合并影响，也没有要求 `--settings` 运行时不加载仓库 `.claude` 配置。Claude Code 文档说明启动目录默认可访问，additional directories 会扩展可读范围；deny 优先，但仅覆盖写出的路径集合。

整改：H2 必须生成完整 settings 并做真实 CLI 冒烟：cwd=staging，staging 不在 repo 内；allow 只含 staging/out；deny 覆盖 repo/root/home/web/agent/mcp；明确 defaultMode；验证 `Read(//workspaces/EnergyPlus-Agent-dev/...)` 被拒、`Read(<staging>/case_data/...)` 成功。

### MAJOR-2：Read/Edit deny 不拦截任意子进程文件读取，L3 必须从“字符串检查”升级为结构化命令 allowlist。

官方文档明确 Read/Edit deny 不适用于 Python/Node 脚本自己打开文件；而本设计允许 Bash，再让 `python tools/cv_probe.py` 运行。只靠字符串查 `..`、`~`、绝对路径 token，不足以覆盖参数文件间接读取、symlink、环境变量、工作目录变化和 shell 展开。

整改：Bash hook 用 `shlex` 解析，拒绝所有非 allowlisted 命令；对所有 path 参数做 `Path.resolve()` 并拒绝 staging 外、symlink 指向 staging 外、参数文件内容里出现禁运路径；设置干净 env，例如 `PYTHONPATH=<staging>`、清空可疑 env；必要时禁止 `cd`/`env`/重定向。

### MAJOR-3：cv_probe 的“平铺为 tools/”与当前 import 机制矛盾。

当前 `cv_probe.py` 依赖 `src.agent.reading.cv_toolbox`，并通过入口文件位置推导 repo root。直接把入口放到 `tools/cv_probe.py` 且把包平铺到 `tools/`，会破坏 import。设计虽意识到 PYTHONPATH 指向工作区，但白名单拷贝布局没有与代码导入形态对齐。

整改：H1 选择一种可测布局并固定：优先保留 `src/agent/reading/cv_toolbox` 相对结构，`tools/cv_probe.py` 只是薄 wrapper；或改 isolation 专用 wrapper 从 `tools.cv_toolbox` import。验收加入真实 `python tools/cv_probe.py prescan-plan ...`。

### MAJOR-4：merge append-only 的并发语义未定义。

现有 attempts 机制用 `next_attempt_index()` 找最大序号再 `mkdir`，能防覆盖但不保证并发成功；manifest pointer 保存也没有锁。设计 §4 问到“并发/hash 绑定坑”，目前答案必须是“有坑但可修”。

整改：H3 明确 isolated merge 由主控串行执行，或实现 attempt index 碰撞重试 + manifest 文件锁/原子写。验收加一个双 merge 碰撞测试，至少证明失败是 fail-closed 且不会覆盖既有 attempt。

### MAJOR-5：`--resume <session>` 可能破坏隔离边界，需要单独证明或降级为非目标。

设计希望支持 pilot->review->batch 分段 resume。Claude Code resume 会恢复会话上下文；如果上一段 prompt、工具结果或人工 review 把 judge/gt/old attempts 摘要带进了同一 session，物理文件隔离已无法消除上下文污染。当前设计只隔离文件系统可见性，没有定义 resume 前后上下文可携带内容。

整改：H3 要么禁止对同一个 reader session 注入 judge/gt/attempt 评语，只允许主控传“继续 batch/修改输出格式”这类无污染控制语；要么每段冷启新 session，把 pilot 产物作为 staging/out 中的自有文件传递，并在 manifest 中标出上下文来源。验收需覆盖“review 文本不含禁运 token”。

### MINOR-1：`judge` 裸 token 过宽，禁运断言应按路径类别精确化。

建议把 `judge_rubric.md` 作为精确 deny 文件，而不是所有含 `judge` 的路径一律拒入。否则未来合法文档名、说明字段或测试 fixture 可能被误杀。

### MINOR-2：settings 里的工具名需按 Claude Code 实际工具名确认。

设计写 `Grep`/`Glob` 同规则、`Task`/`Agent` 全禁。Claude Code 官方文档对 Agent 使用 `Agent(...)`，MCP 可用 `mcp__*`，Read 规则会 best-effort 作用于 Grep/Glob。H2 settings 生成单测之外，还需要 `claude -p` 真跑并检查这些 deny 没有被 warning 跳过。

### MINOR-3：access_log 的审计字段还不够绑定。

建议每条记录包含 normalized tool name、原始 input hash、normalized paths、decision、reason、guard version、settings sha，并在 merge 时保存 access_log 全量 hash。不建议只保存 denied 计数。

### MINOR-4：staging 生命周期需要定义。

如果 `/tmp/ep_isolation` 自动清理，后续审计只剩合并摘要，无法复核 MANIFEST 与 access_log。建议 H3 merge 后把 `MANIFEST.json`、settings、guard hash、access_log 或其压缩副本归档进 attempt 目录；staging 本体可清理。

## H1-H3 批次可执行性与验收

H1 可执行，但需要补两项验收：cv_probe 拷贝布局的真实 import/run 测试；MANIFEST 的 source path 不泄漏禁运路径测试。

H2 可执行，但必须从 unit test 扩展到真实 Claude Code settings/hook smoke。只测 `guard.py` 函数不够，因为本风险点正是 settings 规则语义、hook matcher、exit 2 行为、deny 优先级和工具名拼写。建议 H2 验收至少包含：合法 Read staging 成功、repo gt Read 被 settings 或 hook 拒绝、合法 cv_probe 成功、`python -c`/复合 shell/外部 path/symlink 均拒绝。

H3 可执行，但范围略大，建议拆成 H3a spawn/resume、H3b merge/provenance、H3c guide 改写。验收需要增加：merge 后 attempt 目录含 isolation provenance；manifest output hash 与 output.json 一致；resume 不携带污染 review 文本；guide 明确旧 prompt 级隔离废弃。

现有总体验收“全测试套绿 + sm21 真 spawn 冒烟”方向正确，但不充分。必须把“故意要求读 gt 被 deny 且留痕”改成两个断言：一是 tool call 被实际阻断；二是后续没有通过变形路径或 Bash 子进程成功读取。鉴于第二项很难完全证明，至少应加入 symlink、`python -c`、参数 JSON 外部路径三类负例。

## 参考依据

- 本设计文档 §1-L2/L3/L4 与 §4：`AI_agent/logs/reviews/request/2026-07-08_contamination_hard_isolation_design_request.md`。
- 现行 prompt 级隔离位置：`AI_agent/guides/new_case_guide.md` 附录 A，第 261-272 行。
- 既有 attempts 机制：`src/agent/execution/manifest.py` 的 `next_attempt_index()` / `new_attempt_dir()` 与 `src/agent/execution/stage_runner.py` 的 output hash / manifest accept。
- Claude Code 官方权限文档：Read/Edit 路径模式中 `//path` 表示文件系统绝对路径，`/path` 相对 settings 来源；Read/Edit deny 不拦任意 Python/Node 子进程读文件；hook exit 2 可阻断工具调用。见 https://code.claude.com/docs/en/permissions 与 https://code.claude.com/docs/en/hooks-guide 。
