# 测试工程修复批 —— M-1 / M-2 / m-1 / n-2 / n-3 执行日志

**席位**：Claude 侧执行档（Sonnet 5 子代理，「测试工程修复」摊）
**派工单**：交叉复审裁决书 `AI_agent/logs/reviews/verdict/2026-08-17_substrate_fix_and_gridA_review_glm.md`
（M-1/M-2 = §2.0；m-1 = §2.5；n-2 = §2.3；n-3 = §3.3）
**改动文件**：`tests/test_substrate_fix_tools.py`（M-1 重写 neuter 机制 + M-2 改指夹具 + n-2 补断言）·
`tests/test_substrate_fix_cleanroom.py`（m-1，两处新增断言）·
`scripts/tool_scripts/cv_probe.py`（n-2，报错文案 +3/-1）·
`tests/fixtures/substrate_fix_II/`（新建，M-2 夹具，4 个源文件 + README）·
本执行日志的上一篇 `2026-08-16_substrate_fix_I_execution_log.md`（n-3，仅改一行数字 + 追加更正批注）。
**未改动**：`src/agent/execution/isolation.py` · `src/agent/reading/**` · `skills/**`（按纪律不碰，另一席位在
`/workspaces/ep_707_prereq` 独立 worktree 改这些）；`AI_agent/CLAUDE.md` 的改动不是本次产出（主控确认是其自
己加的 reading 口径 banner）。
**未 commit**：全部改动停在工作树，等待主控统一提交。

**⚠️ 中途一次网络硬中断**：执行到「已建好 `xrv_m1_original_repro` worktree、确认其带原始 `_neutered` 机制」
这一步时会话被中断，恢复后主控要求先核实断线状态。核实结果：`git diff --stat` 精确等于本文档下方列出的改
动面，无半截改动、无遗留 neuter（新写法结构上不产生「改坏了没恢复」的残留，见 M-1 小节）；`xrv_m1_original_
repro` worktree 尚未跑出复现结果，恢复后按顺序补完（见 M-1 小节「独立复现原始竞态」）。

---

## 0. 五条的修法与理由

### M-1 —— neuter 覆写仓库真实文件，与并行跑测竞态（MAJOR）

**机制核实**：`tests/test_substrate_fix_tools.py` 原有 `_neutered(real_path, backup_path)` 是一个
`@contextlib.contextmanager`：把 `real_path`（仓库里被 F-52/F-54/F-58/F-53 修过的 4 个真实源文件之一）整
个覆写成 `backup_path`（修法前备份）的字节内容，`yield` 出去跑测试，`finally` 里再写回改前内容。四处调用点
分别对应 `scripts/tool_scripts/cv_probe.py`、`src/agent/execution/isolation_templates/run_cv_probe.py`、
`src/agent/reading/cv_toolbox/tools.py`、`skills/intake_pipeline/0_reading/cv_toolbox.md`。

这四个文件都会被 `build_isolation_workspace`（`src/agent/execution/isolation.py`）在**每次 staging 构建时**
从仓库读入并拷贝/生成到 staging 树里（`cv_probe.py` 经文本替换写到 `tools/cv_probe.py`；`run_cv_probe.py` 经
`importlib.resources` 读入写到 `tools/run_cv_probe.py`；`tools.py` 经 `shutil.copy2` 拷到
`src/agent/reading/cv_toolbox/tools.py`）。本仓默认并行跑测（`pyproject.toml` `addopts = ["-n", "auto",
"--dist", "load"]`），`--dist load` 下同一文件里的不同测试函数可能被分派到不同 worker；`tests/
test_substrate_fix_cleanroom.py` 的 `staging` fixture 还是**函数级**（每个测试都建一次全新 staging），这就
让「某个 worker 正在 neuter 窗口内、真实文件处于改坏状态」与「另一个 worker 恰好在这个时刻建 staging（会拷
贝到被改坏的内容）」两件事出现真实的时间重叠机会——是竞态，不是假设。

**修法**：新增 `_neuter_into_fresh_staging(tmp_path, real_path, backup_path, staged_rel_path, *, rewrite=None)`，
把「改字源→建 staging→跑→还原」倒过来做成「先用当前（已修好）源码正常建一个 `tmp_path` 专属的全新 staging→
只覆写 staging 内那一份副本→跑」。两种顺序落在 staging 里的最终字节是**完全相同的**（`build_isolation_
workspace` 对 `cv_probe.py` 做的那处路径替换，新写法用 `rewrite=` 参数原样复现，保证不是「凑巧也崩但语义
不对」），所以不是弱化 neuter、只是搬了执行位置——被覆写的对象从「所有 worker 共享的仓库文件」变成「这次调
用自己在 `tmp_path` 下建的、没有第二个进程会看到的副本」，因此不再需要 `finally` 里的还原：没有仓库文件被
碰过，也就没有"改坏了没恢复"这类残留可谈。F-53（文档类）额外做了一层简化：由于该批四个测试里只有 F-53 的
正/负向测试是直接读仓库文件文本（从不进 staging 执行），neuter 干脆不再建任何 staging 副本，直接把 fixture
的文本喂给同一套抽取/扫描辅助函数——连"覆写副本"这一步都省了，是四个里最彻底的一个。

改动位置：`tests/test_substrate_fix_tools.py`——模块 docstring 的 neuter 段落、`_fresh_staging`/新增
`_neuter_into_fresh_staging` 两个辅助函数、新增的 `F5x_STAGED_REL`/`F52_PATH_REWRITE` 常量、4 处调用点
（`test_f52/f54/f58/f53_neuter_...`）。删除 `_neutered`、`import contextlib`。

**独立复现原始竞态**（不满足于照抄裁决书数字，自己重新撞了一次）：

1. `git worktree add` 一棵 detached-HEAD worktree（`16b247b`，即本批修法之前的提交），确认其
   `test_substrate_fix_tools.py` 就是原始 `_neutered` 写法。
2. 该 worktree 是 `git worktree add` 出来的纯净检出，`backup/` 下没有 M-2 要修的那份备份（`.gitignore` 排
   除），单独跑 `-k neuter` 直接 `FileNotFoundError`——这本身就是对 M-2 的又一次独立佐证。为了**单独**看
   M-1 的竞态（不被 M-2 的问题挡住），把主树本机上已有的 4 份备份手工拷进这棵 worktree 的 `backup/`（不动
   任何 git 状态，纯粹让原始代码能跑到断言那一步）。
3. `nproc` = 16。先用任务里指定的判据命令 `pytest ... -n4 -q` 复现：单文件连跑 3 轮、两文件一起连跑 6 轮，
   **全部 0 红**——在这台 16 核机器上，`-n4` 撞不出裁决书报告的竞态。
4. 换成**纯默认调用**（不加 `-n4`，让 `addopts` 的 `-n auto` 在 16 核上拉满 16 个 worker）：两文件一起连跑
   6 轮，**6 轮全红**（6 或 7 failed / 46 total），其中 4 轮精确复现裁决书 §2.0 原文数字「7 failed / 39
   passed」。
5. 结论：M-1 描述的竞态是真实存在的，而且在本机默认并发形态下**几乎必现**；但任务派工单里写的验收命令
   `-n4` 在**这台**机器上恰好是偏弱的判据（并发度不够，撞不到）——这不是裁决书或派工单的事实性错误（`-n4`
   确实是裁决书自己撞出竞态用的命令，只是不同机器的核数/调度时机不同，同一命令在不同机器上复现率不同），而
   是我在验证方法论上补的一层：不能只信一个具体并发度的「跑绿」，要覆盖到本机实际会用到的最强并发形态。

用完 `git worktree remove --force`（已清理，`git worktree list` 确认不再残留，主树 `git status` 未受影响）。

**修法验证**（同样覆盖 `-n4` 和纯默认两种并发形态，而不只是派工单字面指定的那一种）：

- `-n4`：`tests/test_substrate_fix_tools.py tests/test_substrate_fix_cleanroom.py` 连跑 **8 轮**（前 2 轮
  跑在 2 分钟超时前完成、后 6 轮完整跑完），**全部 46 passed，零红**。任务判据要求的 6 轮已覆盖，详见 §1。
- 纯默认调用（16 worker）：同样两文件连跑 **6 轮，全部 46 passed，零红**——覆盖了本机实际最强并发形态，
  不只是应付 `-n4` 这一个特定并发度。

### M-2 —— pre-fix 备份夹具被 gitignore，新克隆恒红（MAJOR）

**机制核实**：`F52_BACKUP`/`F54_BACKUP`/`F58_BACKUP`/`F53_BACKUP` 原先指向
`backup/{scripts,src,Skill}_history/2026-08-16_substrate_fix_II/*`，命中 `.gitignore` 第 19 行
`**/backup/**/20*_*/`（`git check-ignore -v` 四个路径全部命中）。`git ls-files backup/` 确认这批文件从未
入库。

**选择的修法方向**：任务允许「入库 `-f`」或「代码生成」二选一。我选**relocate 入库**——把 4 份文件原样搬到
`tests/fixtures/substrate_fix_II/`（新目录，不在任何 gitignore 规则命中范围内，`git check-ignore` 确认未命
中，无需 `-f`）。理由：
1. **本仓已有强先例**：`tests/fixtures/sm24_review/`、`tests/fixtures/f9_window_host_crash/`、
   `tests/fixtures/f15_producer_schema_scope/` 都是同一类问题（测试依赖的输入原本在 gitignore 覆盖的路径
   下）用同一种手法解决的——`tests/fixtures/sm24_review/README.md` 原文就写着"移到这里让依赖显式且可跟
   踪"，逐字符合我们这次的场景。
2. **避开已知的 gitignore 陷阱**：memory 记录过`「被 ignore 的已跟踪文件 git add 静默失败」`——如果强行
   `-f` 进 `backup/` 树内（该目录规则是**按目录名形状**匹配的 `20*_*/`，不是仅路径），以后这几份文件哪怕
   再也不改，也会让人怀疑"这次真的入库了吗"，每次都要额外用 `git show HEAD:<path>` 验证。搬到
   `tests/fixtures/` 后这个顾虑从结构上不存在。
3. **代码生成的替代方案本可行但更脆**：4 个文件里 F-52 那处的 diff 只有 `_bbox` 函数体，F-54/F-58 各自也
   是几十行的局部改动——理论上可以在测试里用字符串替换从当前源码"倒推"出 pre-fix 版本，但那样等于把"这段
   历史代码长什么样"这份知识第二次编码进测试逻辑里，且下次这几个文件再被改动时容易静默失配（测试里的字符
   串替换找不到锚点会怎样，需要另外设计失败模式）。保留一份原样的历史文件更直接、更不容易撒谎。

`backup/{...}/2026-08-16_substrate_fix_II/` 下的原始文件**没有删除**——继续作为本机本地的「改前备份」，只
是测试不再依赖它们。

**修法验证**：
1. 干净 worktree（`git worktree add`，检出 `16b247b`，即本批修法前的提交）单独跑 `-k neuter`，**先确认复现
   `FileNotFoundError`**（4 个 neuter 测试全部报错，指向 `backup/.../2026-08-16_substrate_fix_II/...` 不存
   在）——证明「不修就恒红」这个前提本身成立，不是臆测。
2. 把本次改动的 5 个文件（两个测试文件、`cv_probe.py`、`tests/fixtures/substrate_fix_II/` 整个目录）拷进同
   一棵干净 worktree（模拟"这些改动被提交后，全新 clone 会长什么样"），确认该 worktree 的 `backup/` 下**完
   全没有**这批文件（`find backup -iname "*substrate_fix_II*"` 空），排除"其实是另一份本地文件顶上了"的
   可能。
3. 该 worktree 内跑 `tests/test_substrate_fix_tools.py tests/test_substrate_fix_cleanroom.py`：纯默认调用
   1 轮 46 passed；`-n4` 额外连跑 3 轮，46 passed × 3，零红。
4. `git worktree remove --force` 清理，`git worktree list` 确认已移除，主树 `git status` 未受影响。

### m-1 —— guard allow + wrapper 拒的组合在 access_log 上无留痕（MINOR）

**机制核实**：guard.py 的 PreToolUse 钩子在**工具真正执行之前**就已经把 `decision`/`reason`/
`tool_input_excerpt` 写进 `access_log.jsonl` 并返回；`run_cv_probe.py` wrapper 是否真的成功执行，是钩子
返回之后才发生的独立子进程，guard 结构上不可能知道。所以「guard 判 allow，wrapper 转头就拒」这种组合，
access_log 里唯一留下的就是一条 `decision=allow` 的记录，和"真的跑成功了"的记录长得一模一样——只看
`decision` 字段的人会把「没跑成」误读成「跑成了」。这正是 `test_substrate_fix_cleanroom.py` 里 F-56/F-57
两把哨兵锁本来就在验证的确切场景（guard 对撤销的工具名 / 跨工具的参数名视而不见，靠 wrapper 自己的
`ALLOWED_TOOLS`/argparse 兜底拒绝）。

**修法选择**：裁决书原话是「建议后续在**日志语义或文档**里写明」、「不要求 guard 校验 tool 值」——明确不是
要 guard 本身多做校验或多记字段（guard 在写日志那一刻，wrapper 还没跑，物理上拿不到这个信息，加字段也只能
加一个"未知"占位，没有实质信息量）。给定纪律要求"只动 tests/\*\* + 必要的夹具 + 执行日志"、`guard.py`（`src/
agent/execution/isolation_templates/guard.py`）虽不在字面禁改清单的 3 项里，但仍在 `src/` 下、仍属于另一
席位正在改的隔离/审计基础设施区域——出于避免任何潜在冲突的考虑，我选择**完全不碰 `src/` 任何文件**，把
「显式记一条」落在 `tests/test_substrate_fix_cleanroom.py` 里：给 `test_f56_...`/`test_f57_...` 两个已经在
构造这个确切场景的测试各加一段 docstring 说明 + 一条断言——读最后一条 access_log 条目、断言其
`decision == "allow"`，并把"decision=allow 不等于执行成功"这句话直接写进断言失败信息里。这样"allow ≠ 执行
成功"从一句可能被忽略的注释，变成一条会被每次跑测检查到的、失败时会说明原因的机器可验证事实，比纯文档描述
更有约束力，且不改变任何运行时行为（与"不修" F-56/F-57 的判决完全不冲突）。

**修法验证**：`-k "f56 or f57"` 单独跑通过；随后 `test_substrate_fix_cleanroom.py` 全量 23 passed。

### n-2 —— `_bbox` len≠4 报错文案未提 JSON 数组写法（NIT）

**机制核实**：`scripts/tool_scripts/cv_probe.py::_bbox` 有三处会抛 `ArgumentTypeError`——JSON 解析失败、
JSON 顶层不是数组、`float()` 转换失败——这三处的文案都已经在 F-52 修法里写上了「or a JSON array
[x0,y0,x1,y1]」；唯独第四处（`len(parts) != 4`，元素个数不对）还是修法前的旧文案，只字未提 JSON 数组这个
合法写法。一个用 JSON 数组写了 3 个元素的读者，看到的提示只会说"必须是 x0,y0,x1,y1"，容易被误导以为要改用
逗号写法，而不是"数组要凑够 4 个数"。

**修法**：把 `len(parts) != 4` 分支的错误文案改成与旁边三处一致的
`"--bbox must be x0,y0,x1,y1 or a JSON array [x0,y0,x1,y1]"`（+3/-1，纯文案改动，无逻辑变化）。同时把
`tests/test_substrate_fix_tools.py::test_f52_negative_malformed_bbox_still_gets_argparse_error` 里 3 元素
JSON 数组那个 case（`--bbox [100,80,700]`，正好命中 `len!=4` 分支）加一条 `assert "JSON array" in
proc_len.stderr`，把这处文案变成有回归锁的修法，不是只改一次就可能被后人无意间改回去的裸文本。

**范围判断（主动说明）**：`scripts/tool_scripts/cv_probe.py` 不在纪律列出的 3 项禁改路径（`isolation.py` /
`src/agent/reading/**` / `skills/**`）里，也不在 `src/` 下（它在 `scripts/tool_scripts/`），派工单第 4 条本
身就是明确要求"补上"这处文案——我判断这属于任务显式指派、且与另一席位改动区域（隔离/审计基础设施）没有交
集的一处例外，所以按要求做了，没有停下上报。这是我对"你只动 tests/\*\* + 必要的夹具 + 执行日志"这句话的一
个具体解读（当成"本批工作量的主体形状"，不当成排除显式指派任务的硬清单），在此明确标出，供复核。

**修法验证**：该测试单独跑通过；`tests/test_substrate_fix_tools.py` 全量 23 passed（含此断言）。

### n-3 —— 摊 I 执行日志「76 个正锁」对不上账（NIT）

**核实**：裁决书 §3.3 指出「76」与任何当前可观测数字都对不上。独立重新跑
`pytest tests/test_substrate_sweep_tools.py -q`（该行原文语境明确指"该文件"= sweep_tools.py，见上下文
"3 把 xfail(strict=True)…" 那句），实测 **47 passed**，与裁决书 §3.1「摊 A 交付 43 正锁 + 4 xfail = 47；
摊 II 修掉后 4 把 xfail 全部翻正 ⇒ 47 passed / 0 xfail」完全吻合，判定 76 是笔误、47 是正确值。

**修法**：只改 `AI_agent/logs/reviews/execution/2026-08-16_substrate_fix_I_execution_log.md` 该行文字，把
「76」改成「**47**」（并补一句 43+4 的构成说明），下面加一条 `> [2026-08-17 n-3 更正]` 引用块，写明原数字、
更正依据（复审 finding 编号 + 我独立重跑的命令与结果），不删除也不掩盖原文的存在，只做透明更正。未改动该
文件的任何其他文字，未改动任何代码。

---

## 1. `-n4` 连跑验证（任务判据，M-1）

`pytest tests/test_substrate_fix_tools.py tests/test_substrate_fix_cleanroom.py -n4 -q` 连续调用，逐轮结
果（前 2 轮因单条 bash 调用 2 分钟超时被截断，但两轮本身都已完整跑完并输出结果；之后改用更长超时连续跑满
6 轮）：

| 轮次 | 结果 |
|---|---|
| 1 | 46 passed in 52.42s |
| 2 | 46 passed in 53.92s |
| 3 | 46 passed in 50.83s |
| 4 | 46 passed in 50.16s |
| 5 | 46 passed in 50.69s |
| 6 | 46 passed in 51.61s |
| 7 | 46 passed in 51.24s |
| 8 | 46 passed in 50.98s |

**8 轮全绿，零红**（超出任务要求的 6 轮）。另见 §0/M-1 独立复现小节：因发现 `-n4` 在本机（16 核）上对原始
（未修）代码几乎撞不出竞态，额外用纯默认调用（`-n auto` → 16 worker）对修法后的代码又连跑 6 轮，同样零红
（46 passed 每轮，47–57s）——覆盖了本机实际最强并发形态，不只是字面满足 `-n4` 这一个判据。

## 2. 干净 worktree 验证（任务判据，M-2）

1. `git worktree add /tmp/.../xrv_m2_worktree HEAD`（`16b247b`，本批修法前）。
2. **先跑通"不修就应该红"**：`pytest tests/test_substrate_fix_tools.py -k neuter -n0 -q` → 4 failed，全部
   `FileNotFoundError: .../backup/Skill_history/2026-08-16_substrate_fix_II/cv_toolbox.md`（及另 3 个同类
   路径）——证明前提成立。
3. 把本次改动的 `tests/test_substrate_fix_tools.py`、`tests/test_substrate_fix_cleanroom.py`、
   `scripts/tool_scripts/cv_probe.py`、`tests/fixtures/substrate_fix_II/`（4 源文件 + README）拷进该
   worktree。
4. `find backup -iname "*substrate_fix_II*"` 确认该 worktree 的 `backup/` 下**没有**这批文件（不是"顶替"
   出来的假绿）。
5. `pytest tests/test_substrate_fix_tools.py tests/test_substrate_fix_cleanroom.py`（纯默认调用）→
   **46 passed**；`-n4` 额外连跑 3 轮 → 46 passed × 3。
6. `git worktree remove --force` 清理；`git worktree list` 确认已移除；主树 `git status` 未受影响。

## 3. 全仓 `-n auto` 数字（任务判据）

```
1 failed, 2819 passed, 14 xfailed, 212 warnings in 700.78s (0:11:40)
FAILED tests/test_mep_idd_field_alignment.py::test_b2_prescan_reproduction
```

与任务给定基线**逐字段精确匹配**：2819 passed / 14 xfailed / 1 failed，唯一红 = `test_b2_prescan_
reproduction`（F-36 旧债，与本轮无关）。未见任何额外红。

---

## 2. 证伪结果（对派工方「27/27」记录的主动核验）

本轮**没有找到派工方的事实性错误**——M-1/M-2/m-1/n-2/n-3 五条描述的机制、位置、影响面逐一核实后全部准确：

- M-1 描述的竞态机制（覆写仓库真实文件 + 本仓默认并行 + 函数级 `staging` fixture 扩大窗口）经独立在隔离
  worktree 里从零复现，确认真实存在。
- M-2 描述的 gitignore 命中 + 新克隆恒红，经独立在干净 worktree 复现 `FileNotFoundError`，确认真实存在。
- m-1/n-2/n-3 三条的具体位置（access_log 语义空隙、`_bbox` 报错分支、执行日志数字）逐一打开源码/日志核实，
  描述准确。

**但发现一处值得记录、不改变任何结论的方法论补充**：任务判据里写的 `-n4` 是裁决书自己撞出竞态用的命令，我
在本机（16 核）上用它复现原始（未修）代码的竞态时**撞不出来**（单文件 3 轮、两文件 6 轮全部 0 红），换成
不加 `-n4` 的纯默认调用（本机 `-n auto` 拉到 16 worker）才 6 轮全红、且精确复现裁决书原文数字。这不是
裁决书或派工单写错了什么（`-n4` 确实是他们那台机器上真实撞出过红的命令，只是并发度/调度时机因机器而
异，同一条命令在不同硬件上复现率不同）——是我在验证环节主动加做的一层：只用派工单字面指定的并发度验证还
不够充分，需要额外覆盖本机实际会用到的最强并发形态，否则"绿"可能只是运气好没撞上。已把这层额外验证的结
果一并计入 §1。

---

## 4. 改动文件清单（对账用）

| 文件 | 改动类型 | 对应条目 |
|---|---|---|
| `tests/test_substrate_fix_tools.py` | 重写 neuter 机制、改指夹具常量、n-2 断言 | M-1 / M-2 / n-2 |
| `tests/test_substrate_fix_cleanroom.py` | 两处新增 access_log 断言 | m-1 |
| `scripts/tool_scripts/cv_probe.py` | 报错文案 +3/-1 | n-2 |
| `tests/fixtures/substrate_fix_II/`（新建） | 4 个 pre-fix 源文件 + README | M-2 |
| `AI_agent/logs/reviews/execution/2026-08-16_substrate_fix_I_execution_log.md` | 一行数字更正 + 追加更正批注 | n-3 |
| `AI_agent/logs/reviews/execution/2026-08-17_test_engineering_fix_execution_log.md`（本文件，新建） | 本批执行日志 | — |

`backup/{scripts,src,Skill}_history/2026-08-16_substrate_fix_II/` 下的原始文件保留未删（继续作为本机本地
备份，测试不再依赖）。`src/agent/execution/isolation.py`、`src/agent/reading/**`、`skills/**` 全程未碰。
