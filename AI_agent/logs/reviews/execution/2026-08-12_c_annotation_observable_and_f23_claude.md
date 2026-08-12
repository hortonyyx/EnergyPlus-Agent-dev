# 执行记录 · 摊 C+D — 标注法观测量露出 + F-23 脆弱断言（Claude 侧）

- **日期**：2026-08-12 · **席位**：Claude 侧 Sonnet 5 · **任务书**：
  `AI_agent/logs/reviews/request/2026-08-12_c_annotation_observable_and_f23_dispatch_claude.md`
- **文件所有权**：本轮只改了 `tests/`（未碰 `src/`；`src/agent/correction/envelope_transform.py`
  的摊 C 生产码全程只读，未发现真实缺陷，故未上报停工）。

## 第 0 步 · 防假验证自检（已做）

- 摊 C：在 `src/agent/correction/envelope_transform.py::observe_envelope_annotation_basis` 顶部临时插入
  `raise RuntimeError('STEP0_C_MUST_RAISE_SENTINEL')`，跑 `pytest tests/test_c2_b2b_envelope_transform.py`
  → **17 个既有测试级联失败在该异常上**，证明我打算写锁的验收命令确实穿过这段生产码。立即用 Edit 精确撤销该行，
  重跑 28/28 绿，`git diff` 确认无残留。
- 摊 D：以 `run_stage._grade_typed_attempt_artifacts` + `score_reading_vs_gt.py` CLI 为真实入口写新测试后，
  实测确认它们真的产出 `score_vs_gt.json`/`grade.png`（`kind == "c2_scored"`，非早退 `not_applicable`），
  证明验收路径真的穿过判卷生产码，不是冻结产物+跳段的假验证。

（详细过程见下文「摊 C / D」两节）

---

## 摊 C · 改了什么

**只改 `tests/test_c2_b2b_envelope_transform.py`**（未新建文件，追加在文件尾部）：
- import 增加 `EnvelopeAnnotationObservation`、`observe_envelope_annotation_basis`、`resolve_envelope_move_intents`。
- 新增私有 fixture `_annotation_envelope(dx, dy)`：对 `_geom()` 既有 `[0,10]x[0,8]` bbox 按给定位移构造
  `AuthoritativeEnvelope`（`dx`/`dy` 为 `None` 时该轴不落入 `axes` dict，对应「无权威证据」）。复用既有 `_geom()`
  （其 L 形环 bbox 恰为 `[0,10]x[0,8]`，`observe_envelope_annotation_basis` 只读 bbox 不读环内部形状，故无需另建夹具）。
- 新增 6 个测试函数（4 正向锁 + 1 不变性锁×2 参数化）。

## 摊 C · 每把锁绑的是什么

| 锁 | 状态 | 构造 | 绑定断言 | 自证前提 |
|---|---|---|---|---|
| `test_annotation_basis_names_axis_line_annotation_when_displacement_is_negligible` | 按轴线标注 | `dx=dy=0.0`（真实构造位移=0，不是跳过） | `apply_v3_envelope_transaction` 真实入口 → `result.annotation_basis` 4 条全 `axis_line_annotation`，`displacement_m==0.0` | `resolve_envelope_move_intents` 在同一夹具上返回 `()`——旧观测通道对此状态确实沉默 |
| `test_annotation_basis_names_outer_skin_annotation_at_half_wall_thickness_scale` | 按外包标注 | `dx=dy=0.12`（半墙厚量级） | 同上入口 → 4 条全 `outer_skin_annotation`；`result.committed=True`；`result.geom.footprint_x==[-0.12,10.12]` | `resolve_envelope_move_intents` **确实**产生 4 条 intent（旧通道唯一有信号的一档），但 `EnvelopeMoveIntent.__dict__` 不含 `basis`/`basis_label` 字段——旧信号是无名的裸数字 |
| `test_annotation_basis_names_exceeds_tolerance_beyond_reconcile_tol` | 超出容差 | `dx=dy=0.5`（>0.30） | 同上入口 → 4 条全 `exceeds_tolerance` | `resolve_envelope_move_intents` 返回 `()` |
| `test_annotation_basis_names_no_authoritative_evidence_when_axis_unresolved` | 无权威证据 | `dx=dy=None`（轴不落入 `AuthoritativeEnvelope.axes`） | 同上入口 → 4 条全 `no_authoritative_evidence`，`displacement_m is None` 但 `old_value_m` 仍报告 | `resolve_envelope_move_intents` 返回 `()`；另加 `envelope.axis("x") is None` 夹具自检 |
| `test_annotation_basis_observation_never_perturbs_existing_transaction_outputs[...]`（参数化 2 例：committed 路径 / no-intents 路径） | 不变性 | 对同一 `(geom, envelope)` 跑两次 `apply_v3_envelope_transaction`：一次走真实 `observe_envelope_annotation_basis`，一次经 `monkeypatch` 换成返回明显不同值的桩 | `committed`/`geom`/`transaction_id`/`intent_ids`/`failed_gate_id` 五个既有字段两次调用逐一相等；另断言 `"annotation_basis" not in swapped.geom.model_dump()`（观测不泄漏进产物本体） | 换桩前先断言 `baseline.annotation_basis` 非空且 basis 符合预期（否则换桩是空操作） |

全部 6 把锁均直接调 `apply_v3_envelope_transaction`（真实入口，`envelope_transform.py:748` 无条件调用观测函数），
而不只在 `observe_envelope_annotation_basis` 裸函数层断言。前 4 把还额外直接调裸函数做机制级核对。

## 摊 C · neuter 结果

在 `/tmp` 隔离副本（`cp -r src/ tests/test_c2_b2b_envelope_transform.py pyproject.toml`，与真实工作树完全隔离；
真实仓库全程只读，`git diff` 全程 0 处 `NEUTER` 残留）中做了 3 组变异，每组测完立即在副本内还原、删除副本：

| 变异 | 手法 | 结果 |
|---|---|---|
| **A 机制** | `observe_envelope_annotation_basis` 函数体首行改 `return ()` | 新增 6 把锁**全部转红**，既有 28 把**零连带** |
| **B 接线** | 只改调用点 `envelope_transform.py:748`，把 `annotation_basis = observe_envelope_annotation_basis(...)` 硬编码成 `annotation_basis = ()`，函数体本身不动 | 同上：6 红 / 28 绿零连带（证明锁测的是接线，不只是机制——若接线被断、机制完好，锁照样报警） |
| **C 污染副作用**（意外发现） | 在函数体内加一行 `geom.footprint_x = [v+999 for v in geom.footprint_x]`（模拟"纯观测"违约、真的写了输入） | **只有 no-intents 参数化例**（`dx=dy=0.0`）转红；**committed 参数化例**（`dx=dy=0.12`）不变仍绿 |

**C 的连带调查**：committed 路径会在 `_apply_components` 结尾无条件按环重算 `footprint_x/y`
（`bbox = footprint_bbox(candidate); candidate.footprint_x, candidate.footprint_y = ...`），
把对 `footprint_x` 的污染"自愈"掉了；no-intents 早退路径直接原样返回 `before`，没有这层自愈，因此完整暴露污染。
**这是本轮 neuter 意外抓到的一个真实覆盖盲区**：不变性锁最初只用 committed 夹具，对这一类污染是瞎的。
已在 C 之前就把不变性锁参数化补上 no-intents 例并重新验证（上表已是补完后的最终版），
**未改任何生产码**——原因是真实生产实现里根本没有这行污染（我读过 `observe_envelope_annotation_basis`
全文，它只读不写），C 组变异纯属我主动注入的假设性回归，用来检验锁的覆盖面，不代表发现了真实缺陷。

## 摊 D · git log -S / blame 契约核实结论

- `git log -S'"git", "diff", "--name-only", "--", "case_tests"' --oneline --all` **只命中一个提交** `6b08ac6`
  （2026-07-17，`7.17_B4bPhaseD_CLOSED_RECD_B4bSeriesComplete`）——该断言自 introduced 起从未被修改过。
- 该提交的 message 通篇讲"B4b Phase D 施工 CLOSED"，**确认派工单原文的判断**：commit message 没有解释为什么用
  `git diff`。
- 但**真实承载物找到了，在 `AI_agent/logs/reviews/execution/2026-07-17_b4b_phaseD_construction_brief.md`**
  （terra 执行简报）与 `AI_agent/logs/reviews/request/2026-07-17_b4b_phaseD_construction_dispatch.md`（派工单）：
  - 派工单原文（禁区条款）：「**明确不改**（§12.3）：production output schema、...、任何
    `case_tests/.../gt`/golden/verified overlay、B5/B5b/B6 文件。**无 GT/golden diff**（gate D6，测试锁）。」
  - 执行简报的六出口表格把这条记成「D6 protected clean | ... | PASS（**工作树 diff 无 case_tests**）」。
  - **⇒ 真实契约 = 这是一次性的「本次 Phase D 施工没有动 case_tests」构造期纪律检查**，写检查的人当时是对的
    （那一刻「我的未提交 diff」= 「这次施工的改动」，两者恰好重合），**但把它原样焊进了永久回归测试**，
    脱离了"这一次施工"这个语境后，「工作树当前 diff」再也不等于「这次判卷运行造成的改动」。
- **未发现该断言另有正当用途**（如"防止测试执行期间意外写入 case_tests"这类运行时不变量的证据）——
  找到的两份文档口径高度一致，均指向"构造期一次性纪律"，没有第三处文档给出不同解释。
  ⇒ **按派工单建议方向修，未停下上报**。
- 但**没有原样照抄建议的实现**（"取指纹→跑 judge 路径→再取→断言相同"是对的方向，但派工单没有指定
  用什么取指纹）——自行选型：**放弃 git，改用纯文件系统 path+size+mtime_ns 指纹**（性能测得 `find`~1.1s、
  纯 Python pathlib~35s、`os.scandir`~4-5s，git 完全不必要且天然带回原问题）。

## 摊 D · 改了什么

**只改 `tests/test_c2_b4b_phase_d.py`**：
1. 新增 `import os`。
2. 新增两个私有 helper：`_scandir_files`（递归 `os.scandir` 生成器）+ `_case_tests_metadata_fingerprint(root)`
   （path+size+mtime_ns 指纹，sha256 摘要，默认 `root=Path("case_tests")` 但可覆盖，供隔离仓库测试复用同一实现）。
3. 原 `test_d5_va_source_has_no_tautological_noop_assertion_and_d6_new_judge_modules_stay_judge_only`
   函数**只删了最后 5 行**（`git diff --name-only` 那段），换成一段注释指向替代它的新测试；
   函数其余部分（no-op 断言扫描 + judge-only import 边界扫描）**一字未动**。
4. 新增 3 个测试函数（1 条真实替代锁 + 2 条自证前提）。

## 摊 D · 每把锁绑的是什么

| 测试 | 目的 | 真实入口 | 断言 |
|---|---|---|---|
| `test_d6_judge_scoring_path_leaves_case_tests_byte_for_byte_unchanged` | **真实替代锁**：判卷路径真的不写 `case_tests/` | ① `run_stage._grade_typed_attempt_artifacts`（`1_correction` 阶段，走 `_correction_v3_runstage_fixture`→`_stepwise_e4_run` 真实管线拼出的 accepted attempt，拿到真实 `"c2_scored"` 而非早退 `not_applicable`）；② `score_reading_vs_gt.py` 作为真实子进程被 spawn（`0_reading` 阶段） | `_case_tests_metadata_fingerprint()` 环绕两个真实调用前后取值，`assert after == before`；另有「两个入口真的各自产出了制品」的自证（`kind=="c2_scored"`、PNG magic bytes、CLI 输出文件存在） |
| `test_d6_old_git_diff_check_false_positives_on_unrelated_dirty_tree` | 自证方向 1：工作树脏 ⇒ 旧写法误判 | `/tmp` 隔离 git 仓库（`tmp_path`，绝非真实工作树） | 先 `git commit` 一个 baseline `case_tests/README.md`，再做一次与判卷代码无关的编辑（模拟"orchestrator 改一个 README"），断言旧技术（`git diff --name-only -- case_tests` 逐字复刻）此刻 `stdout.strip() != ""`（旧断言会失败）；同一夹具下新方法（指纹环绕一个不写文件的只读操作）`after == before`（新方法保持绿） |
| `test_d6_old_git_diff_check_false_negatives_once_committed_but_fingerprint_catches_it` | 自证方向 2：judge 真改了素材 ⇒ 新写法红，旧写法一提交就瞎 | `/tmp` 隔离 git 仓库 | 先 baseline 提交，再做一次判卷路径可能造成的写入（换成明显不同长度的内容，规避 mtime 分辨力问题），断言新指纹 `after != before`（新方法真的抓到）；随后 `git add`+`commit` 这处"damage"，断言旧技术此刻 `stdout.strip() == ""`（旧断言会假装没事——委派书原文"只要 git add 或 commit 一下就变绿"的确切复现） |

## 摊 D · neuter 结果

- **`_case_tests_metadata_fingerprint` 本体的敏感性**：在一个我完全控制的 `/tmp` 目录（非真实 `case_tests/`）里
  做内容变化(不同长度)/新增文件/删除文件三种变异，逐一验证指纹在变异前后确实不同、且对无变异保持确定性相同。
- **主锁 `assert after == before` 的接线是否真实**：用 `monkeypatch` 把
  `tests.test_c2_b4b_phase_d._case_tests_metadata_fingerprint` 换成一个"前后返回不同常量"的桩（不碰真实
  `case_tests/`），跑真实的 `test_d6_judge_scoring_path_leaves_case_tests_byte_for_byte_unchanged` 函数体，
  确认它在 `assert after == before` 那一行精确失败——证明这句比较不是恒真、真的在读指纹返回值。
- **两条自证测试本身即为自证结构**（分别在测试体内部同时断言旧法失败与新法成立），无需额外 neuter。
- **⛔ 未做**：没有向真实 `case_tests/` 注入任何写入（哪怕是临时后删除）——按纪律「在真实工作树弄脏 case_tests/
  会把另一席位的全仓跑打红」，判定这类验证只能通过 monkeypatch 或隔离目录做，不接受"写了再马上删"的折中方案
  （担心中途中断导致真的留下脏数据）。

## 全仓测试汇总行

命令：`python3 -m pytest`（默认 `-n auto --dist load`，来自 `pyproject.toml`）·
日志/退出码独立文件名 `fullsuite_20260812_084029.{log,rc}`（未复用任何历史文件名）。

```
========== 2539 passed, 10 xfailed, 211 warnings in 469.05s (0:07:49) ==========
```

`.rc` 文件内容 `EXIT_CODE=0`。日志内 `grep -c "^FAILED\|^ERROR"` = 0；无 `short test summary` 段
（该段只在有失败/错误时才出现，本次没有）。

**与任务书基线（2515 passed / 10 xfailed / 0 failed）对账**：`2539 − 2515 = +24`。
独立核实我自己两个文件贡献的净增量：`git show HEAD:...` 取施工前内容分别 `--collect-only`，
两文件 HEAD 版共 45 个测试 ID → 我改后共 54 个 → **我本人净增 9 个测试 ID**（摊 C 4 把独立正向锁 +
1 把参数化不变性锁×2 例 = 6；摊 D 1 把新替代锁 + 2 把自证前提锁 = 3；原 D6 断言删 5 行但函数本体保留，
不增减测试 ID 计数）。**+24 与 +9 的差额 +15 不是我引入的**——`git status` 显示并行席位（摊 B）本轮期间
持续提交，新增了 `tests/test_f22_blocker1_core_stamp.py`、`tests/test_f9_route2_s2_authoritative_projector.py`
两个新文件并扩写了 `tests/test_f15_producer_schema_scope.py`/`tests/test_judge_batch_b.py`，这些改动全程
未被我触碰，但与我共享同一棵工作树、同一次全仓跑测。**0 failed 是本轮验收的关键事实：不管 +24 里谁贡献了
多少，没有任何测试红。**

独立复核（隔离出我自己的两个文件，在当前共享树状态下单独跑）：
`pytest tests/test_c2_b2b_envelope_transform.py tests/test_c2_b4b_phase_d.py -q` → **54 passed**，
与全仓子集完全一致。

## 未验证的项 / 不确定的判断（如实列出）

1. **`_case_tests_metadata_fingerprint` 的实测耗时在本环境下有较大波动**（4.3s–14.5s/趟，与并行席位当时的系统负载
   强相关，`uptime` 峰值看到过 load average 21+）。已改用 `os.scandir`（比 `pathlib.rglob`+`stat` 快约 8×），
   但仍比 shell 版 GNU `find -printf`（约 1.1s/趟）慢 4–5×——认定是 Python 逐条 stat 调用在这台 9p/drvfs
   挂载点上的固有开销，非算法问题；没有再往下用 `find` 子进程只因它是非可移植 GNU 扩展。
   **这会让 `test_d6_judge_scoring_path_leaves_case_tests_byte_for_byte_unchanged` 单条耗时波动在约
   10–40 秒**，是本项目已有测试里偏慢的一条（但仍在个位数分钟量级的全仓预算内，且只影响这一条）。
2. **未新增测试覆盖 `record_baseline.py::_annotation_basis_summary` / `_render_annotation_basis_summary`**
   （摊 C §C.3 第 3 点"报告露出位置"的消费端）——理由：① C.4 逐字列出的锁要求只针对
   `EnvelopeAnnotationObservation`/`observe_envelope_annotation_basis`，未提及报告渲染层；
   ② `record_baseline.py` 当前正被并行席位实时修改（`git status` 显示其未提交改动持续变化），
   此刻加锁风险是测在对方半成品上。已读过 `_annotation_basis_summary` 源码，实现看起来稳妥
   （best-effort 读取、缺失/损坏都不报错、不影响报告生成），但**这只是源码审阅、不是执行验证**。
3. **未独立验证摊 C 生产码在真实 v3 case（如 sm24）产物上的行为**——本轮 6 把锁全部基于本文件既有
   `_geom()`/`_envelope()` 风格的合成 fixture（与文件里其余 28 个既有测试同风格，并非我降低标准），
   不是拿一份真实识图/校正产物跑出来的。
4. **摊 D 的 F-23 契约调查止步于 `git log -S` + 两份文档**（构造期简报与派工单）——未再扩大搜索范围去找
   是否还有第三份文档（如某次 judge② 裁决书）提过这条检查；但两份已找到的文档口径完全一致，
   且 `git log -S` 证实该行代码自诞生起从未被除我之外的任何提交 touch 过，认为已经充分。
5. **全仓测试是在并行席位持续提交的共享工作树上跑的**（`git status` 显示 `src/agent/correction/schema.py`、
   `src/agent/judge/correction_score.py` 等我未触碰的文件在本轮期间被对方持续修改）——本轮汇总行反映的是
   *那个时刻* 共享树的整体状态，不是"仅我的改动"单独的隔离结果。已用 `/tmp` 隔离副本验证过我自己两个文件的
   变更在没有对方并发改动时同样成立（见上文 neuter 部分），但全仓号数字本身不能排除对方同期改动的影响。
