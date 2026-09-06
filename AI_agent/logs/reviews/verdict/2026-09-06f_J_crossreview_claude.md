# 跨家族复核裁决 · J：判分接线 + 补立面（复核方：Claude）

**裁决：APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 2**

被审对象：`/tmp/j_grade_glm` `363844b3..01a94fab`（5 commits）；本复核在 `/tmp/j_review_claude`（detached，`01a94fab`）完成。
简报只看原始需求（`2026-09-06e_J_grade_wiring_dispatch.md`）+ diff + 我自己跑出的测试输出；交件长篇自述仅作线索，未作证据。

---

## 开工自检

```
$ git rev-parse --short HEAD
01a94fab
$ python -c "import src.agent.judge.as_drawn.elevation_grade as m; print(m.__file__)"
/tmp/j_review_claude/src/agent/judge/as_drawn/elevation_grade.py
```
两条均落在本工作目录，符合承重不变量。

## 全量复算（独立跑，非转引）

```
$ python -m pytest -q -n 6 -p no:cacheprovider
3954 passed, 2 skipped, 13 xfailed, 211 warnings in 525.76s (0:08:45)
$ python -m pytest -q --collect-only -p no:cacheprovider
3969 tests collected in 3.76s
```
`3954+2+13=3969`，与独立 `--collect-only` 逐位吻合，差额 0，与交件读数完全一致。
跑测前后 `git status --short` 为空、`git rev-parse --short HEAD` 未变（`01a94fab`）。

---

## §2.1 三条复核（对「跨两层立面必须判出分」锁：`tests/test_elevation_grade.py:47 test_a_two_storey_facade_grades_whole`，实现侧 `src/agent/judge/as_drawn/elevation_grade.py:136 elevation_targets`）

**① 改动前红**：在 `elevation_targets`（`elevation_grade.py:153` `for opening in gt.get("openings")` 循环体、`:157` `if ref is None: continue` 之后）注入 F-89 原形状的一行过滤 `if opening.get("floor_id") != floor_ids[0]: continue`（只留第一层），原样跑 `tests/test_elevation_grade.py`：

```
FAILED test_a_two_storey_facade_grades_whole[East_view-13]
FAILED test_a_two_storey_facade_grades_whole[South_view-7]
FAILED test_a_two_storey_facade_grades_whole[North_view-8]
FAILED test_a_two_storey_facade_grades_whole[West_view-6]
FAILED test_north_storeys_both_carry_openings
FAILED test_east_grades_thirteen_for_thirteen
FAILED test_the_axis_hypothesis_is_reported_not_smuggled
FAILED test_an_invented_opening_bills_as_extra
8 failed, 13 passed in 4.81s
```
四张立面的 F-89 参数化锁**全部**变红（不是碰巧只中一个）。

**② 改动后绿**：还原文件（`cp` 回未改版本，`git diff --stat` 确认 0 改动），重跑：`21 passed in 4.34s`。

**③ ⭐⭐⭐ 换同形输入仍走不通**：自己造一份**合成 gt**（不复用 sm25 任何数据）——3 层楼、一张立面声明 `floor_ids: ["F2","F3"]`（**跨的是 F2+F3，不是 sm25 四张立面统一都在跑的 F1+F2**），F2 挂 5 个洞口、F3 挂 2 个洞口（5:2 非对称分布，sm25 里没有这种切法）。脚本见下（跑后已删除，不留痕迹于工作树）：

```
BASELINE OK: synthetic F2+F3 facade grades whole, 7/7 targets, no floor dropped
```
（`elevation_targets` 返回 `floor_ids==["F2","F3"]`、`openings==7`、`ledger.openings_by_floor=={"F2":5,"F3":2}`；`grade()` 全量匹配 7/7，未丢任一层。）
再对这份**新构造的输入**重新注入同一条 F-89 过滤突变：
```
AssertionError: 5   ← len(targets["openings"])，从 7 掉到 5（只剩 F2）
```
证明挡住的是**这一类缺陷**（任何按 `floor_id` 过滤的路径），不是恰好把 sm25 四个 fixture 背下来。

**配套：变异实测把 `__file__` 与 pytest 放同一条命令跑**（纪律 §四要求）：
```
$ python -c "import src.agent.judge.as_drawn.elevation_grade as m; print(m.__file__)"
/tmp/j_review_claude/src/agent/judge/as_drawn/elevation_grade.py
```
每次注入/还原后都单独确认过落在本目录，排除了「变异没生效」与「锁没牙」的读数混淆。

**第二把锁**（flow 路由「分支不劫持」，`scripts/tool_scripts/run_stage.py:2050 _grade_as_drawn_reading_branch`）也独立做了①②：把入口条件 `if not any(d.contract_id in AS_DRAWN_CONTRACTS ...): return None` 替换成恒 `False`（即让分支对任何输入都吞），跑 `tests/test_j_grade_wiring.py`：`legacy` 输入本该走 `None`（交回旧路径），突变后返回了一个非 `None` 的 grade 字典 → `test_flow_typed_entry_routes_as_drawn_output_to_the_branch` 红；还原后 `11 passed`。

---

## §2.2 判据量的是本体还是影子——J-2 自造第三个分辨率值

execution.md 只演示过 `0.6`（超带拒判）和 `0.35`（带内改动）两个值。我用**这两个数之外**的第三个值 `0.123`（`quantization_band_m(0.001, 0.123)=0.062`，落在带内、不触发拒判）独立验证：

```
baseline product_resolution_m: 0.01     mutated product_resolution_m: 0.123
baseline quantization_band_m: 0.0055    mutated quantization_band_m: 0.062
baseline along errs: [0.0, 0.0, 0.01, 0.01, 0.005, 0.005, 0.005, 0.01, 0.01, 0.0, 0.01, 0.0, 0.01]
mutated  along errs: [0.0055, 0.0265, 0.014, 0.0325, 0.0115, 0.03, 0.009, 0.013, 0.0055, 0.0265, 0.014, 0.0325, 0.0115]
PASS: an independently-chosen third resolution value moves the real grade output
```
真实产物（East_view 13 个洞口）的**逐条对齐误差数值随声明改变**，不是常量不相等这个影子读数。

进一步做了**消费路径的破坏性突变**：把 `read_product_resolution`（`src/agent/judge/as_drawn/resolutions.py:130`）改成永远走默认分支（忽略 `resolution_m` 字段），跑 J-2 相关全部锁：
```
FAILED test_elevation_grade.py::test_a_coarser_product_declaration_moves_the_grade
FAILED test_elevation_grade.py::test_a_finer_product_declaration_is_consumed_mechanically
FAILED test_j2_resolutions.py::test_product_declaration_is_read_and_flagged_as_declared
3 failed, 29 passed
```
还原后 `32 passed`。⇒ 判据验的确实是「声明值改了、判分结果的数值真的跟着变」，不是「两个常量恒不相等」这个影子。

---

## §2.4 「零流量」这件事读准了吗

execution.md §七逐字写的是：「新判分分支**零流量**（接线是保险丝，不是已通车的路…）」——**没有**把零流量说成「已验证」，措辞诚实，前后一致（§二接线点清单也只说锁住了路由逻辑，没有声称有生产调用）。

**47 条测试里，真的走了 `run_stage.py` 那个生产接线点（`_grade_as_drawn_reading_branch`，`run_stage.py:2050`，即 `_grade_typed_attempt_artifacts` 在 `:2130` 调用的那一行）的，精确数字 = 2**：
- `tests/test_j_grade_wiring.py:151 test_flow_typed_entry_routes_as_drawn_output_to_the_branch`
- `tests/test_j_grade_wiring.py:183 test_branch_result_shape_matches_the_typed_contract`

且这 2 条也**不是**经 `flow` CLI 的完整入口跑的——是手搭 `attempt_dir`/`document`/`output` 直调 `rs._grade_as_drawn_reading_branch()`，`_grade_typed_attempt_artifacts`（真正被 `flow` 调用的外层函数，`run_stage.py:2096`）本身在这 47 条里**从未被以 as-drawn 输出调用过**（`grep -rn "_grade_typed_attempt_artifacts" tests/` 命中的都是别的历史测试文件，喂的都是旧格式）。

其余 45 条的构成：
- `tests/test_j_grade_wiring.py` 另外 9 条：直调 `flow_wiring.py` 的模块函数（`split_output_by_contract`/`resolve_*_view_id`/`grade_as_drawn_attempt`），用真 gt + 真产物，但**不经过** `run_stage.py`。
- `tests/test_elevation_grade.py`（21）+ `tests/test_j2_resolutions.py`（11）= 32 条：纯判分器/分辨率数学单测，直接把构造好的 dict 喂进 `grade()`/`read_*_resolution()`，不涉及任何路由。
- `tests/test_render_elevation_grade.py`（4）：直调渲染器模块，同样绕开路由。

⇒ 分层给数：**2/47** 摸到生产接线点本体，**11/47**（含上面 2 条）摸到 `flow_wiring.py` 的真实路由/落盘逻辑，**36/47** 是构造夹具喂进纯函数的单测。这与「零流量」的自陈一致——不是隐瞒，是**这次没人问过精确拆分，现在给出**。

---

## §2.5 接线是否真按产物契约选路

- `src/agent/reading/vector_contract.py` 在本次 5 个提交里**逐行 diff 为空**（`git diff 363844b3..01a94fab -- src/agent/reading/vector_contract.py` 无输出）⇒ 只读复用属实。
- `flow_wiring.py:54 from src.agent.reading import vector_contract`、`:95 split_output_by_contract` 直接调用其 `classify_vector_json`，未见任何自建的「这是什么格式」判断（`grep -n "endswith\|startswith\|\.suffix"` 命中的三处都在注释里说明"⛔ 不按文件名"，代码体里没有一处按文件名/扩展名分类)。
- `resolve_plan_view_id`/`resolve_elevation_view_id`（`flow_wiring.py:120,134`）用 stem/正则解析的是**视图身份**（这是哪张图对应 gt 哪个 view），不是「这是什么契约」——两件事分开，未违反派工单禁止的「第二分类器」（那条禁令针对的是契约判断，不是身份解析）。
- `grade_as_drawn_plan`（`flow_wiring.py:172`）里 `signed_source_dxf`（`:162`）按请求哈希绑定源 DXF，不按文件名 glob，独立读码确认。
- 禁区路径复核：`src/agent/correction/**`、`src/agent/pipeline.py`、`src/agent/reading/vector_contract.py`、`case_tests/test_baseline/gt/**`、`src/agent/judge/as_measured.py` 五处 `git diff --stat` **全部零命中**，独立复算与主控 §一一致。

---

## 不阻断的两条

1. **47 条测试里精确摸到生产接线点的只有 2 条**（见 §2.4）——不是缺陷，是量出来的数字，登记以便下次「E-a 接生产格式」落地后回来补一条经 `_grade_typed_attempt_artifacts` 真正入口的端到端锁（今天不能补，因为生产格式还没走到这条路，喂不出真实输入）。
2. **E3 结构线「axis-immune by construction」的假设目前只在 sm25 真实四张立面上验证过**（`elevation_grade.py:376` 附近注释自陈其推理：端线目标是答案自己 extent 的两端，镜像把该集合映到自身，所以不需要跟着 opening 的镜像假设一起翻转）。四张真实立面里 East/South 是 identity、North/West 是整字段级镜像，且全部 100% 通过，但没有构造一个「结构线本身的绘制惯例也跟着镜像错位」的合成实例去压这条假设的反例（即结构线的物理位置记录是否可能在某种产品实现里也需要跟着翻轴）。今天不阻断，登记为下次任何「产品坐标系镜像/惯例」相关改动前的必查项。

---

## 最薄弱一处（⛔ 未写「无」）

与交件 §七判断一致，且我认为这仍是当前最薄弱的一点：**新判分路径在真实 `flow` 全链路里今天完全没有被生产调用过**——`0_reading/` 的真实产物还是旧格式，`E-a`（A-6 认领生产格式）线尚未落地，这条新路径的全部信心来自「构造真实 gt + 真实 prototype 产物直接喂函数」，而不是「跑一次真实 `flow <case> <run> --to 0_reading`」。§2.4 的数字量化了这句话——47 条里只有 2 条碰到生产接线点本体，且都是手搭调用、不经过 `flow` CLI。这是接线单固有的时序问题（下游生产者还没交货），不是本单能力范围内的缺陷，但下一次任何人想引用「J 单判分器已经在保护立面判分」时，必须先确认 E-a 落地、这条路径真的有生产流量。

---

## 结论

三条复核（含第三条换同形输入）、J-2 自造第三值、零流量数字核实、接线只读复用核实——均未发现阻断级问题。**APPROVE-WITH-FINDINGS，阻断 0 / 不阻断 2**（见上）。
