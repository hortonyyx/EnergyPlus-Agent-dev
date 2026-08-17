# 交叉复审裁决 —— 基座修法批（摊 I + 摊 II）+ grid_A

**审阅席**：GLM 家族（glm-5.3，交叉复审席，非作者方）
**被审对象**：提交 `c68c293` 中 Claude 侧产出（修法 + 新锁 + 被改既有锁 + grid_A + 两份执行日志）
**请求书**：`AI_agent/logs/reviews/request/2026-08-17_substrate_fix_and_gridA_crossreview_glm.md`
**状态**：✅ 审阅完成（2026-08-17）

---

## 0. 总裁决

**CHANGES REQUIRED（1 BLOCKER / 2 MAJOR / 2 MINOR / 4 NIT）**

| 级别 | # | finding | 一句话 |
|---|---|---|---|
| BLOCKER | B-1 | §2.1 | F-55「藏起来」这条腿实测够得着：cwd/`__file__`/`os.getcwd`/glob 四形态 guard 全放行，读、清空审计日志真跑成功（3323B→0），且命名规则可从读图器可读的 guard.py 源码直接提取。F-55 在 BLOCKER-2 闭合前不得记为「已闭合」；E1 结论需再降一档（日志无任何机制能自证未被裁剪）。 |
| MAJOR | M-1 | §2.0 | 摊 II 4 把自 neuter 测试覆写仓库真实文件，与本仓默认并行在子集形态下竞态（`-n4` 六轮三轮红；两文件默认形态 7 failed）；全仓形态本轮未撞（2819/1红 F-36，与提交说明一致）。子集恰是日常跑测最常用形态，且 neuter 窗口可能掩盖真红。 |
| MAJOR | M-2 | §2.0 | 同 4 把测试的 pre-fix 备份输入被 gitignore 未入库 ⇒ 新克隆恒红（worktree 实测 FileNotFoundError）。「绿只绿在这台机器上」第四次同型。 |
| MINOR | m-1 | §2.5 | 「guard allow + wrapper 拒」在 access_log 上无留痕，decision 字段单独不可作准——应显式记录「allow ≠ 执行成功」。 |
| MINOR | m-2 | §3.2 | grid_A §5「⛔ 不要修」与 README §三「本轮全部未修」和同提交修 5 条的终态矛盾，权威表无勘误行。 |
| NIT | n-1 | §2.2 | staging 外 guard.py 副本执行时日志落到意外的 `isolation_archive.audit/`（fail-closed，不进正式审计链）。 |
| NIT | n-2 | §2.3 | `_bbox` len≠4 报错文案未提 JSON 数组合法写法。 |
| NIT | n-3 | §3.3 | 摊 I 日志「76 个正锁」数字无法对账。 |
| NIT | n-4 | §2.4 | E2E 快照视野天然不含 `.audit` 兄弟目录（merge 锁除外）。 |

**通过的部分**（都经真跑验证，非代码审查）：
- **2.2 双推导漂移**：排除（7 场景实测一致 + 两把行为锁）。请求书最担心的「静默丢失」有门会红。
- **2.3 F-52 单点修法**：三层（wrapper 三形态 + batch 混用 + guard 层）实测全绿；拒改 `JSON_OR_PATH_KEYS` 的理由实测成立。
- **2.4 十六处测试改动**：机械核对全部是读取路径替换，断言零增删，48 节点全绿，无放宽。
- **2.5 F-56/F-57 不修**：判决维持（注释时间线 07-31/08-01/08-15 早于本轮 + 独立论据）；两把哨兵锁 neuter A/B 双向真绑。
- **新锁接线**：cleanroom N1（4红）/N2（1红）/N3（13红）、哨兵 A/B，全部真绑、零假锁、还原零残留。
- **grid_A 普查质量**：主表抽验数值精确、前提核验与缺口清单诚实。
- 全仓默认并行独立复跑 = 1 failed（F-36 旧债）/ 2819 passed / 14 xfailed，与提交说明一致。

**结构判语**：修法批的**内容**大体扎实（五处攻击点四处守住），塌的两处都在**测试自身工程**上——一把锁的价值取决于它红的时侯可信，flaky 锁与机器绑定的锁都会在下次有人看到红时浪费整整一轮排查。BLOCKER-1 则是老账（BLOCKER-2 锚点族未修）在 F-55 头上的投影，处置方向（与 BLOCKER-1/F-59 合并）请求书已写对，本裁决补的是：**在它闭合前，F-55 的净收益只有「拦字面路径」这一档，任何「审计日志已安全」的表述都超出实测**。


## 1. 五处重点攻击

### 2.1 F-55 修法「藏起来」这条腿是否够得着

**结论：够得着。BLOCKER（修法前提「读图器不知道路径」被实测证伪）。**

实测环境：真 `build_isolation_workspace`（sm21_anchor）+ 真 guard 子进程（hook payload）。
复现：`/tmp/xrv_21/probe_21.py` + `probe_21b.py`（探针随本档留存路径，重跑需先 build staging）。

**A. guard 判定（修法后现状）**：

| 形态 | 命令要点 | guard 判定 |
|---|---|---|
| 逐字相对路径 | `cat ../staging.audit/access_log.jsonl` | **DENY**（`..`） |
| cwd 锚点族 | `python -c 'c=Path.cwd(); p=c.parent/(c.name+".audit")/"access_log.jsonl"; ...'` | **ALLOW** |
| `__file__` 锚点族 | `python -c 's=Path(__file__).resolve().parent; while … (s.parent/(s.name+".audit"))…'` | **ALLOW** |
| `os.getcwd()` | 同上换 `os.getcwd()` | **ALLOW** |
| glob 免拼名 | `Path.cwd().parent.glob("*/access_log.jsonl")` | **ALLOW** |

**B. 真跑**：cwd 锚点那条在 staging 内实际执行，`AUDIT: True` —— 读到审计日志。
**C. 清空**：guard ALLOW 后真跑 `p.read_text(); p.write_text("")`，**3323 字节 → 0**，被审计方销毁了自己的审计痕迹（精确到行的选择性改写同理放行）。
**D. 规则本身零秘密**：`cat guard.py` ALLOW；`python -c` 用正则从 staging 里的 guard.py 源码提取 `_audit_dir` 真跑成功，输出 `RULE: root.parent / f"{root.name}.audit"`。命名推导规则对被审计方完全可见，guard.py 注释自己也写着 "This is a FIXED NAME-DERIVATION RULE, not a secret"。

**净收益的准确表述**：F-55 修法防住的唯一形态是「逐字写出路径」（相对带 `..` 被 `..` 规则拦；绝对路径被 outside-staging 规则拦）。任何推导形态（BLOCKER-2 锚点族，未修）全部放行，读+销毁均可达。提交说明写的口径限制「真正起作用的是『不在它知道的那棵树里』」**过于乐观**：审计日志就在 `cwd.parent` 下、名字 = `cwd.name + ".audit"`、规则文本躺在读图器可读的 guard.py 里 —— 读图器不需要「知道那棵树」，它的 cwd 的父目录就是那棵树。

**但要害不在「漏报新缝」**（BLOCKER-2 已登记在案、CLAUDE.md 已有「F-55 强度上限取决于 BLOCKER-2 关没关」）。要害在两处：
1. **执行日志与隔离注释的论证把「藏」讲成了有效腿**——「so a location outside that tree is off the reader's map for any ordinary command it runs」这句在现状代码上为假（普通命令 `python -c` + cwd 锚点即达）。若后续有人据这句把 F-55 记为「已闭合」，即成假绿叙事。
2. **E1 结论降档还可以再降一档**：现在写的是「我们手上这份日志显示它没碰」；实测证明日志既可清空也可选择性改写，且 guard 自己会在清空后继续 append（时间上后写的条目无法自证此前的日志未被裁剪）。严格措辞应是「我们手上这份日志**未被可检测地改动过**」都做不到——没有任何机制能检测。这是审计信任根的结构性缺口，不是表述问题。

**分级：BLOCKER**（承重前提错：F-55 的有效性主张建立在「路径不可达」上，实测四种普通形态可达且可销毁；与 BLOCKER-2 合并处置是正确方向，但 F-55 不能在 BLOCKER-2 闭合前被记为已闭合）。


### 2.2 guard.py 与 isolation.py 双推导漂移

**结论：产品链上不漂移（实测通过），镜像一致性另有两把行为锁钉住；发现一个意外留痕位置（NIT）。**

两侧公式：
- guard.py `_audit_dir(root)` = `root.parent / f"{root.name}.audit"`，root = `Path(__file__).resolve().parent`（guard.py 在 staging 内执行）
- isolation.py `_audit_dir(staging_root)` = `Path(staging_root).resolve().parent / f"{...resolve().name}.audit"`

**实测**（`/tmp/xrv_22/probe_22.py`，真 build + 真 hook 子进程）：

| 场景 | 结果 |
|---|---|
| 直接 build | 两边推导一致 |
| **symlink build**（build 传链接路径） | 一致（isolation 侧 `_audit_dir` 内部 resolve 穿透链接；实测 `via_link` → 两边都算 `real2.audit`） |
| **相对路径 build** | 一致（`Path(...).resolve()` 归一；实测 `rel_staging` → 两边同为绝对 `.audit`） |
| 名字含**空格** | 一致，hook 真跑后 isolation 侧能读到日志 |
| 名字含**点号**（`staging.dot.name`） | 一致，同上 |
| 名字本身以 **`.audit` 结尾** | 一致（推导出 `x.audit.audit`，两边同名） |
| 中文名字 | 一致 |

结构上为什么一致：① 两边公式是字面量镜像；② 两边都 `resolve()`（isolation 侧在 `_audit_dir` 内、guard 侧在 `_staging_root()` 内）；③ hook 命令路径在 `_write_settings` 时用 **build 时已 resolve 的绝对路径**固化，`__file__` 与 build 参数同源。merge 侧 `merge_isolated_output` 开头又 resolve 一遍。

**漂移的行为锁（不是代码审查）**：`test_real_guard_hook_keeps_appending_to_the_relocated_log_across_many_calls`（真 hook 连续写、`_access_log()` 读得到）+ `test_merge_still_archives_the_relocated_log_and_binds_its_hash`（真 merge、归档件存在且内容=写前日志、provenance hash 非空）。若任一侧公式单边改动，merge 锁必红（归档件读不到）——**「hook 写一处、审计读另一处且无门会红」的担忧被这两把锁排除**。

**发现的边缘（NIT）**：执行 staging 外的 guard.py 副本（如 merge 后 `attempts/NNN/isolation_archive/guard.py`，或手工拷贝件）时，其 `_staging_root()`= 副本所在目录 → `_append_log` 写到**该目录的兄弟** `isolation_archive.audit/`（实测产生此目录）。副本本身对一切命令 fail-closed deny（`out/` 缺失），deny 日志仍落到意外位置。**不触及正式审计链**（staging 的 `.audit` 原件不受影响），但「在归档目录里跑副本做验证」的人会把验证留痕写到意料之外的位置。可留档不修。

**分级：无 finding（通过）+ 1 NIT**（归档副本意外留痕位置）。


### 2.3 F-52 `_bbox()` 单点修法覆盖面 + 拒改 JSON_OR_PATH_KEYS 的理由

**结论：覆盖面成立（三层实测全绿）；拒改理由实测成立；1 NIT（len≠4 报错文案未提 JSON 数组写法）。**

**覆盖面实测**（`/tmp/xrv_23/probe_23.py`，真 staging + 真 wrapper/guard 子进程）：

| 形态 | bbox 写法 | wrapper rc | guard 判定 |
|---|---|---|---|
| B direct CLI | comma `0,0,50,50` | 0 | ALLOW |
| B direct CLI | JSON 数组 `[0,0,50,50]`（含空格） | 0 | ALLOW |
| A `--request` | 原生数组 `[0,0,40,40]`（wrapper dumps 成紧凑串再喂 `_bbox`） | 0 | ALLOW |
| A `--request` | comma 字符串 | 0 | — |
| C `--batch` 混用 | 条目1 原生数组 + 条目2 comma | 0，两条都出 crop 产物 | ALLOW |
| C `--batch` 坏值 | 3 元素数组 | 2，干净报错拒整批 | — |

`_bbox()` 是 argparse `type=` callable，挂在 `--bbox` 上、位于三种形态收敛之后（wrapper `_request_to_argv` 把 request 折成 argv 再交给同一 parser）——「单点」的声称属实。cv_probe 全参数表里 list/dict 型输入只有 `bbox`/`anchors_json`/`candidates_json` 三个，后两个已在 `JSON_OR_PATH_KEYS`（其 cv_probe 侧 `_json_arg` 天然接受 `[`/`{` 开头字符串），无同病漏修参数。

**拒改 JSON_OR_PATH_KEYS 的理由：实测成立。** 反证（`/tmp/xrv_23` 探针末段，不动仓库文件）：若把 `bbox` 加进该集合，comma 字符串 `"0,0,50,50"` 会走 `_resolve` 路径分支 → 拼成 `<staging>/0,0,50,50` 绝对路径 → `_bbox` 内 `float('/tmp/.../staging/0')` 必然 `ArgumentTypeError`。即当前唯一有文档背书的 comma 写法会死。施工席的拒绝是**实测过的负收益**，不是偷懒。

**NIT**：`_bbox` 的 `len(parts) != 4` 分支报错文案仍是旧的 `--bbox must be x0,y0,x1,y1`，未提 `or a JSON array [x0,y0,x1,y1]`（新文案只在 float 转换失败分支出现）。用 JSON 数组写法传 3 元素的用户看到的提示漏了一半合法写法。一行文案事，不影响判定。

**分级：通过 + 1 NIT**。


### 2.4 test_isolation.py 16 个既有测试逐个核实

**结论：声称属实——16 处改动全部是同一模式的「读取路径」行替换，断言行零增删，全绿；无一处放宽。**

机械核对（`git diff e0367e1 c68c293 -- tests/test_isolation.py` 逐行）：

- **被删行恰 16 行**，全部形如 `log/entry = json.loads((staging / "access_log.jsonl").read_text(...).splitlines()[-1])`；**被增行除 helper/注释外恰 16 行**，与被删行逐一对应、仅 `(staging / "access_log.jsonl")` → `_access_log(staging)`。
- **`^\+.*assert` 与 `^-.*assert` 均零命中** —— 没有任何断言被新增/删除/改写。
- 16 处分布的 16 个测试函数（逐一列出核对）：`test_build_kickoff_probe_forms_match_live_guard` · `test_guard_allows_legal_run_cv_probe_and_logs` · `test_guard_with_transcript_path_still_denies_illegal_tool_input` · `test_guard_rejects_forbidden_bash_shapes` · `test_guard_allows_reading_summary_with_prose_forbidden_tokens` · `test_guard_r1_allows_reading_summary_content_with_slash_and_grade_line` · `test_guard_r1_excludes_content_role_params_from_path_scan` · `test_guard_r3_free_text_params_of_non_write_tools_are_allowed` · `test_guard_allows_direct_probe_form_and_logs` · `test_probe_help_is_allowlisted_and_documents_all_three_forms` · `test_guard_probe_shape_receipts_include_a_minimal_correct_repair` · `test_guard_denies_illegal_direct_probe_shapes` · `test_guard_allows_bounded_probe_batch_and_logs_every_request_path` · `test_access_log_records_the_payload_on_allow_too` · `test_access_log_hashes_every_scanned_script` · `test_scanned_non_code_files_are_not_logged_as_executed_code`。与「16 个」的声称一致，无第 17 处。
- 唯一非测试改动 = `_E2E_EXEMPT_NAMES` 上方加注释说明该豁免已 vestigial（日志搬出 staging 后 `rglob` 看不见它）——**豁免本身未删**，非放宽。

**行为验证**：16 个函数（参数化展开 48 节点）全绿；`tests/test_isolation.py` 全量 **248 passed**（独立复跑，107.8s）。这些测试读不到日志会直接 `FileNotFoundError` 炸——绿即证明它们真在读新位置的日志，不是空转。

**边缘观察（NIT，非放宽）**：E2E 快照（`_staging_snapshot`）以 staging 为根做 `rglob`，日志搬走后 `.audit` 兄弟目录天然落在一切快照锁视野之外（merge 锁除外）。即「guard 实际往 .audit 写了什么文件」目前只有 merge 一把锁看得到。

**分级：通过 + 1 NIT**。


### 2.5 F-56/F-57 不修的理由 + 两把哨兵锁

**结论：不是纯循环论证（注释时间线 + 独立论据支撑「不修」），但存在一个未论证的审计盲区（MINOR）；两把哨兵锁 neuter 双向实测均真绑。**

**循环论证判别**：
- 施工席引用的三处「已声明的设计」注释，git blame 核实分别来自 `ec709822`（**07-31**，`_direct_to_request` docstring「deliberately NOT duplicated」）· `07631640`（**08-01**，guard「not an authorization list」）· `dc4ca571`（**08-15**，wrapper「PROBE_TOOL_NAMES exists only to phrase error messages」）——**三个不同批次、全部早于本轮**。注释在本轮之前就已存在，不是作者本轮顺手写注释自证现状。
- 且论证并非只靠注释：②改分工的代价（guard 须运行时 import 另一 staged 文件、改变两文件分工 = 架构决定不该在判缺陷单里顺手定）独立成立；③最刺眼症状（裸栈）确已被 F-54 修掉（实测 wrapper 报 `run_cv_probe.py: error: unsupported cv_probe tool` rc=2）；④剩余代价定位为审计粒度。
- ⚠️ 但「注释证明的是**有意性**，不是**正确性**」——正确性实际由「wrapper 兜底 fail-closed」承担，而这一环靠两把哨兵锁钉住（见下），这个依赖关系哨兵锁 docstring 写明了。综合判：**不修的判决维持**。

**两把哨兵锁 neuter 实测**（/tmp/xrv_neuter worktree，改完即还原，零残留）：

| neuter | 操作 | 结果 |
|---|---|---|
| A（F-56 承重半） | 把已撤的 `prescan-plan` 偷偷加回 wrapper `ALLOWED_TOOLS`（模拟撤除被静默回滚） | **F-56 锁红**（wrapper rc=0 且真产出了 candidates.json），F-57 锁不受牵连 |
| B（F-57 承重半） | 给 `storey_line_profiler` 子解析器增设 `--axis`（模拟 argparse 层键属主校验放松） | **F-57 锁红**（"unrecognized" 不再出现），F-56 锁不受牵连 |

**真钉住的东西**：两把锁各钉「不修」论证的承重前提——wrapper 兜底若被拿掉/放松（撤除回滚、未知参数被吞），锁红。锁同时钉「guard 保持松」的现状半（`decision.returncode == 0` 断言）：若未来有人正确地修 F-56/F-57（让 guard 收紧），锁也会红——这是**故意的**（红 = 强制重开该判断、不许顺手改），docstring 明说。零假锁。

**MINOR（论证缺口，非推翻）**：「guard 记 allow + wrapper 拒」的条目在 access_log 上 `decision="allow"`，而 **wrapper 拒绝不产生任何留痕** ⇒ 审计者只读 decision 字段会把「没跑成」读成「跑成了」，必须下钻 `tool_input_excerpt` 里的命令原文才能分辨。在「access_log = 审计信任根」（F-44 的立论）的定位下，这是已知盲区；执行日志把它归为「不精确」，措辞偏轻。建议后续在日志语义或文档里写明「allow ≠ 执行成功」——这不要求 guard 校验 tool 值，与「不修」判决不冲突。

**分级：通过（判决维持）+ 1 MINOR（审计盲区应显式记录）**。


## 2. 新锁 neuter 实测 + 新锁自身两处工程缺陷

### 2.0 ⛔ 先说两处 MAJOR（新锁自身的缺陷，先于 neuter 结论）

**MAJOR-1：摊 II 的 4 把自 neuter 测试覆写仓库真实文件，与全仓默认并行（`-n auto`）竞态 ⇒ 权威门形态下 flaky 红。**

- 机制：`tests/test_substrate_fix_tools.py::_neutered()` 把 `F52_REAL`/`F54_REAL`/`F58_REAL`/`F53_REAL`（= `scripts/tool_scripts/cv_probe.py`、`src/.../run_cv_probe.py`、`src/.../tools.py`、`skills/.../cv_toolbox.md` 四份**仓库真实文件**）用 pre-fix 备份覆写、跑完还原。xdist 下其他 worker 的测试（阳性锁 build staging / 直接读文档）在 neuter 窗口内读到 pre-fix 内容 ⇒ 阳性锁红；反之窗口错开则 neuter 锁自己红。
- 实测（主树）：
  - `tests/test_substrate_fix_tools.py` 单文件：`-n0` 串行 **23 passed** 稳定；`-n 4` 六轮 = 1/2/1/0/2/2 failed **约半数轮次红**；两新锁文件合计按默认形态（`addopts` 自带 `-n auto`）跑一次 = **7 failed / 39 passed**。失败名单轮轮不同（f52/f53/f54/f58 的 neuter 锁与 f53 阳性锁都出现过）——竞态特征。
  - **全仓默认 `-n auto`（我独立跑，8:57）= 1 failed / 2819 passed / 14 xfailed**，唯一红 = `test_b2_prescan_reproduction`（F-36 旧债）——**本轮未撞竞态**。即：全仓形态下两文件测试被 ~2800 个测试稀释，竞态概率降低但非零；**高概率复现形态是「受影响子集/单文件」——恰是本仓日常跑测最常用的形态**（`affected_tests.py` 产物、席位回归、轻门）。
- 后果：提交说明的全仓数字本轮可复现（如实记录），但「单文件/子集并行跑测会随机红」是引入即带的：任何席位按三档节奏跑受影响子集，都可能吃到一个假红、或更糟——在 neuter 窗口内**漏看一个真红**（阳性锁在 pre-fix 窗口内跑过 = 阳性断言失败会被误读为「修法坏了」或反向掩盖）。本仓 07-26 提速批已把「并行与串行节点集合逐字节相等」立为门规，本轮引入的测试自己破坏了它在子集形态下的成立。
- 复现：`python -m pytest tests/test_substrate_fix_tools.py -q`（什么都不加，默认 `-n auto`），连跑 3 次观察红数波动。
- 修法方向（供下轮，本轮不修）：neuter 改为**只动测试自建的 staging 副本**（staging 本来就是拷贝），或 4 把 neuter 加 `@pytest.mark.xdist_group` + `--dist loadfile`/独占串行标记；任何一条都先以「默认并行形态 3 连绿」验收。

**MAJOR-2：4 把自 neuter 测试的输入（pre-fix 备份）未入版本控制 ⇒ 新克隆恒红，「绿只绿在这台机器上」第四次同型。**（全仓形态下我未独立撞到它——因为主树盘上有这份备份；它是结构性的：克隆即红。）

- `F52_BACKUP`/`F54_BACKUP`/`F58_BACKUP`/`F53_BACKUP` 指向 `backup/{scripts_history,src_history,Skill_history}/2026-08-16_substrate_fix_II/*`；`git check-ignore` 四个路径**全部命中**（backup/ 的 ignore 规则盖住了这批新备份，且未 `-f` 入库——`git ls-files backup/` 只有 MCP_history 等旧批）。
- 实测：干净 worktree（`git worktree add /tmp/xrv_neuter c68c293`）单跑 `test_f52_neuter_reverting_bbox_parser_reproduces_the_original_crash` ⇒ `FileNotFoundError: /tmp/xrv_neuter/backup/scripts_history/2026-08-16_substrate_fix_II/cv_probe.py` 恒红。
- 这正是 07-26 治理教训的原文场景（「关键输入不在 git 里 ⇒ 新克隆上 skip 或红 = 第三次同型」）——本轮第四次。修法：备份文件 `-f` 入库（量级 ~几十 KB 源码），或自 neuter 测试改为在测试内**内存还原**缺陷形态（从当前源码字符串替换出 pre-fix 形态），彻底摆脱盘上备份。

### 2.6 摊 I（test_substrate_fix_cleanroom.py，23 测）neuter 矩阵

| # | neuter | 结果 |
|---|---|---|
| N1 | guard.py `_audit_dir` 还原为写回 staging 内 | **4 红**（含 `test_real_guard_hook_keeps_appending…` append 行为锁 + `test_merge_still_archives…` merge 行为锁）|
| N2 | isolation.py `_audit_dir` 还原为读 staging 内 | **1 红**（merge 锁）|
| N3 | `_lock_down_readonly_surface` no-op | **13 红**（mode-bits 系 + setpriv 降权系全灭）|

结论：F-55 两条机制（日志搬家 × 两侧推导、chmod）各自有真绑行为锁，**接线成立**；全部 neuter `git checkout` 干净还原、零残留。哨兵锁（F-56/F-57）neuter A/B 见 §2.5，均真绑。

### 2.7 摊 II（test_substrate_fix_tools.py，23 测）

4 把自 neuter 测试设计上是好想法（锁「缺陷形态可复现」），但被 MAJOR-1/MAJOR-2 两个工程缺陷拖累。正锁部分：F-52/F-54/F-58/F-53 的阳性/阴性断言经我 2.3 的独立三形态实测交叉印证成立（wrapper 层 rc 与文案、argparse 原生错误不受 try/except 影响、overlay 形状校验两分支、文档示例真 shell 跑通）。


## 3. 其余 finding（五处之外：grid_A / README / 执行日志）

### 3.1 grid_A 普查表质量：**通过**（抽验 + 对账）

- **主表抽验**：S-1「px_m_calibrator 原生数组 anchors → `px_per_m`=40.0」我独立真跑复现（`/tmp/xrv_23`，sidecar `results[0].px_per_m = 40.0` 精确）。S-1 的 18/18 声称与我在 2.3 的三形态实测交叉印证一致。
- **前提核验节**（§0 六条 ⚠️ 逐条列核verification 方法）与「没做完的格子」诚实清单（§8：S-2 未穷举、4 项缺口具名列出）——方法论质量好，与 README §五「没普查完的面」一致。
- **锁数对账**：摊 A 交付 43 正锁 + 4 xfail = 47；摊 II 修掉 F-52/F-53/F-54 后 4 把 xfail 全部翻转成 4 把正锁 ⇒ 当前 HEAD 实测 **47 passed / 0 xfail** ✓。「三把 xfail 实为四把」（派工方错误率 27/27 第③条）在 `test_substrate_sweep_tools.py:707-709` 的注释里有如实记录。

### 3.2 MINOR：同提交内「普查表状态」与「修法终态」错位，无勘误行

- `grid_A.md` §5 对 F-52/F-53/F-54 仍写「**⛔ 不要修**」「均未修，仅登记」；`README.md` §三表头写「统一编号 F-52…F-58，**⛔ 本轮全部未修**」——而**同一提交**修掉了 5 条。README 自称「两摊的合并权威表 + 统一编号」，读者从权威表出发会得到与提交说明相反的状态。README §二「主控轻门 = 43 passed / 4 xfailed」同样是普查时点数字（当前为 47 passed）。
- 修法：README/grid_A 各加一行勘误（「本表为普查时点快照；F-52/F-53/F-54/F-55/F-58 已于同提交修复，见提交说明/执行日志」）。纯文档，非阻断。

### 3.3 NIT：摊 I 执行日志一处无法对账的数字

摊 I 日志 §0 断线说明里写「摊 II 自己把 xfail 摘掉、变成 **76 个正锁**全绿」——与任何当前可观测数字对不上（sweep_tools 47 / fix_tools 23 / 两文件合计 70 / 两摊合计 89 均非 76）。疑为当时中途状态的转述或笔误。外围论据错，记录后不阻断。

### 3.4 执行日志其余声称核对（通过）

- 摊 I「改动文件清单」（isolation.py / guard.py / test_isolation.py 16+1 / policy 1 处 / cleanroom 新建 23）与 git diff 逐项对上；policy 文件那处改动 = `access_log()` helper（F-55 适配），与 test_isolation.py 的 helper 同一公式。
- 摊 I 对 F-55 root 限制的披露（`setpriv` 验证、`chattr` overlayfs 不可用、候选 F-59）诚实且与 isolation.py 注释一致；「断线说明」如实。
- 摊 II 对 F-54/F-58「两条修法各自独立必要」的交叉论证成立（F-54 收敛在 wrapper 入口层、F-58 收敛在 toolbox 函数层，层不同互不兜底——f58 的 AttributeError 不经过 wrapper 的 main()）。
- 备份纪律（`backup/{src,scripts,Skill}_history/2026-08-16_substrate_fix_II/`）本体存在，但见 §2.0 MAJOR-2——备份未入库拖累了依赖它的测试。


## 4. 请求书待证伪判断对账（派工方错误率 27/27）

| # | 请求书判断 | 核验结果 |
|---|---|---|
| 1 | 2.1「权限位那条腿在本容器无效（root 绕过 DAC）」 | **成立**。我独立复现：staging 内 `guard.py` mode=`0o555`（写位已清），root 下 `open(p,"a")` append **成功**（探针后已还原）。 |
| 2 | 2.1「`Path.cwd().parent` 就是 staging 的父目录，`<name>.audit` 正好是那里的兄弟」 | **成立，且比请求书写的更糟**：cwd 锚点族 4 形态全 ALLOW，且规则文本可从读图器可读的 guard.py 里直接提取（见 §2.1 D）。 |
| 3 | 2.2「hook 写一处、审计读另一处，静默丢失且无门会红」 | **产品链上被排除**：双推导实测一致（symlink/相对/空格/点号/中文），且 merge 行为锁使任一侧单边改动必红（见 §2.2）。 |
| 4 | 2.3「施工席拒绝改 JSON_OR_PATH_KEYS」 | 拒绝理由**实测成立**（comma 写法会被 `_resolve` 拼成 staging 路径再喂 `_bbox` 必炸），非偷懒。 |
| 5 | 2.4「16 个测试函数」 | **数目准确**（本仓罕见地没踩「共 N 处」坑）：恰 16 函数、16 处替换、assert 零改动。 |
| 6 | 2.5「注释是作者写的，不构成外部理由」 | **部分成立**：三处注释 blame 为 07-31/08-01/08-15 三个早于本轮的批次（非本轮自证），但注释证明有意性不证明正确性——判决最终靠独立论据 + 哨兵锁撑住（见 §2.5）。 |
| 7 | §0 自认的三条新增错误（漏文档示例格 / 写错 e0367e1 改动面 / 三把 xfail 实为四把） | 第③条我核实属实（47=43+4 全翻转，`test_substrate_sweep_tools.py:707` 注释如实记录）；①②未独立复核（①与 grid_A S-1b 的「主控中途补的一格」自洽；②为对历史的记述，不影响本轮裁决）。 |

**本轮请求书零证伪命中（第 1/2/4/5 条全部核过成立，第 3/6 条被精化）**——按本仓惯例如实记录：派工方这次的判断没有踩坑，我证伪未遂。

