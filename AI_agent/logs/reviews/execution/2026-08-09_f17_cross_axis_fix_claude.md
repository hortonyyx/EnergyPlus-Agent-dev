# F-17 · 跨轴组件切角修复施工日志（2026-08-09，Claude 侧执行档）

> 派工单：`AI_agent/logs/reviews/request/2026-08-09_f17_cross_axis_chamfer_fix_dispatch_claude.md`
> 调查全档：`AI_agent/logs/experiments/2026-08-09_f17_envelope_cross_axis_chamfer/README.md`
> ⛔ 未 `git add` / `commit` / push（orchestrator 统一落库）。

## 0. 防假验证自检（动手前）

1. **我的验收路径真的会执行到 `_apply_components` 吗？**
   会。`apply_v3_envelope_transaction`（`envelope_transform.py`）在 `intents` 非空时**无条件**调用
   `moved = _apply_components(candidate, components, tol)`——中间没有任何分支能跳过它。
   我的三把锁全部经 `apply_v3_envelope_transaction`（官方入口）驱动，不直接摆弄 `_apply_components`
   或用 monkeypatch 伪造调用——这样锁住的是「接线」（真实调用链），不是孤立函数本身。
   另外用官方复现脚本 `tools/f17_repro.py`（走 `parse_correction_draw` → `build_verified_window_inputs_from_run`
   → `finalize_correction_draw` 三步官方链路，真实 sm21 产物）交叉验证：修复前抛
   `ValueError: cell RM1F_01: polygon edge 3 is not orthogonal`，修复后 `[run] 没崩 —— 未复现`。
2. **锁如果把修法整个还原，会不会转红？**
   会，两轮独立 neuter 都精确转红（见 §3 全表）。
3. **断言的是手算出来的具体坐标，还是「没抛异常/数量变了」？**
   是手算值。三把锁全部断言 footprint 与每个 cell 的精确 `(x, y)`/顶点坐标（如
   `footprint == [(0,0),(15,0),(15,8),(0,8)]`），且这些手算值我逐点独立推导后，
   再用 `f17_fixprobe.py`/`f17_matrix.py` 的探针输出交叉核对完全吻合，才写进测试。
   零处断言停留在「没抛异常」或「数量变了」。

## 1. 改了什么

**唯一改动文件**：`src/agent/correction/envelope_transform.py`（`_apply_components` 函数体，
`_conflict_shape` 追加一个 check_id）。

### 1.1 根因修法：三阶段替换「边移边判」

把原来「遍历 `components.values()`，每次一个组件、就地改写环」的单循环，拆成三相（与派工单 §3
一致，参考实现是 `tools/f17_fixprobe.py::apply_components_fixed`，本次按仓库风格重写，**不是照抄**）：

- **相 1 materialize**：对每个组件依次调用 `_materialize_axis_splits`，只插点、不移动——保留原
  函数逐组件调用的顺序无关性（`_materialize_axis_splits` 只在「两端点都落在该组件坐标上」的边上
  插点，不同轴组件的插点候选边天然不相交，串行调用与调用顺序无关）。
- **相 2 relocate**：对相 1 输出的每个顶点，**用该点『冻结的』原始坐标**依次测试全部组件的
  `_on_component`，命中哪个分量就写哪个分量——**关键点**：测试永远针对同一份未被本轮任何组件
  改写过的坐标（局部变量 `original` 与被写入的 `resolved` 分离），所以一个角点被 x 分量命中后，
  y 分量的判定仍然拿它原始的 x 坐标去量，不会被 x 分量已经写下的新值污染。这是本次修复的核心：
  **我在第一版草稿里写错过一次**——把测试对象和写入对象合并成同一个可变列表，导致「点 2」这一相
  内部又重新引入了同型的顺序耦合 bug（x 分量先写，y 分量测试时已经读到 x 分量写完的新坐标）。
  对照 `f17_fixprobe.py` 逐行核对后发现并改正，记在这里以防同型错误再犯。
- **相 3 normalize**：原样保留（`_canonical_open_ccw` + rect 回落 + 末尾 `validate_cell_polygon`
  校验），未改动语义。

`_materialize_axis_splits` **未被删除/绕过**——照原样在相 1 里对每个组件调用一次；派工单点名的
「格 B（L 形）」用例已实测走通（§2 Group B），拐角未被抹平。

### 1.2 分类修法：cell 环校验失败改走结构化拒绝

`_apply_components` 末尾的 `if cell_has_polygon(cell): validate_cell_polygon(cell, ...)` 循环
原来是裸调用，`ValueError` 会一路无捕获地炸出 `apply_v3_envelope_transaction`、`apply_deterministic_core`、
`finalize_correction_draw`（后者对这条调用链没有任何 try/except，已用 grep 确认）。现在包一层
`try/except ValueError`，转译成 `EnvelopeTransformRejected("correction.envelope_cell_ring_valid", ...)`
——这个异常类型已经被 `apply_v3_envelope_transaction` 自己的 `except EnvelopeTransformRejected`
捕获（原有代码,未改动),转换成 `EnvelopeTransactionResult(committed=False, ...)` 正常返回,
`conflicts` 追加一条结构化记录、`fallback_action="rollback_keep_original_geometry"`——与
`correction.envelope_ring_valid`（footprint 环校验失败,已有的姊妹路径)完全同型。

新增的 check_id `correction.envelope_cell_ring_valid` 追加进 `_conflict_shape()` 的
`("unsupported_geometry", "topology_identity")` 桶（与 `correction.envelope_ring_valid`
同一桶——两者都是「环本身不合法」这一类失败,不是数值冲突)。

### 1.3 为什么两条必须一起交（如实记录我的判断）

三阶段修法本身已经让「跨轴切角」这个具体诱因消失,但 `validate_cell_polygon` 这一步仍然可能因为
**其它**原因失败（如某个 cell 被移动后宽度跌破 `min_edge_length_m`——与跨轴无关,单轴移动也能造出这
种情形)。这条校验失败不该再有第二次「裸 ValueError 炸穿 flow」的机会,所以分类修法必须覆盖它,
不能只指望根因修法把这条路径「关掉」。Group C 的锁专门验证一个**与跨轴机制完全无关**的最小复现
（§2）。

## 2. 三把锁

新文件 `tests/test_f17_cross_axis_envelope.py`（3 组,均经 `apply_v3_envelope_transaction` 官方入口驱动）：

| 组 | 锁什么 | 夹具 | 断言形态 |
|---|---|---|---|
| A（核心） | 跨轴组件对：x/y 两轴同时解出,四条边全动,四个角 cell 各占一个 footprint 角 | **逐字节照抄真实 sm21 产物 F1**（`footprint_x=[0.12,14.88]`、7 个 cell,与 `run_2026-08-08_f16_e2e_verify/1_correction/correction_geometry.json` 的 F1 完全一致）——lo 侧 = 0.12 ≠ 0 | footprint 与 7 个 cell 的精确坐标；外加 `moved["floor_vertex_refs"].count("f1:0")==2`、`moved["cell_vertex_refs"].count("f1:RM1F_04:0")==2` —— 直接证明同一个角点被 x 分量与 y 分量**各命中一次** |
| B（L 形） | L 形 footprint + 跨轴组件（x-lo + y-lo），证明 `_materialize_axis_splits` 仍在起作用、缺口未被抹平 | 逐字节照抄 `f17_fixprobe.py::fresh_b()` 的 L 形夹具 | footprint 6 顶点精确坐标（含 3 个未动的缺口角）+ 两个 cell 精确坐标 |
| C（分类） | 一个**与跨轴无关**的真实（非 monkeypatch）`validate_cell_polygon` 失败，走结构化拒绝而非裸异常 | 单独一个显式 `polygon` 字段的 cell，宽度 0.13m，x-lo 单轴内移 0.12→0.18（收缩，非扩张）后跌到 0.07m < `min_edge_length_m`(0.1m) | `not result.committed`、`failed_gate_id=="correction.envelope_cell_ring_valid"`、`conflict_type/claim_type/fallback_action` 精确值、`reason_unresolved` 含 `"below min_edge_length_m"`、`evidence` 精确字典；**调用点本身不包在 `pytest.raises` 里**——回归到裸异常会让这次调用本身报 ERROR，同样判红 |

Group A 的手算值我逐点独立推导（见执行过程,未落盘草稿,以下摘录关键一步）：
角 cell `RM1F_04`（x=[0.12,5.0], y=[0.12,3.0]）左下角 `(0.12,0.12)` 同时匹配 x-lo（0.12→0.0）与
y-lo（0.12→0.0）两个分量 ⇒ 应变为 `(0.0,0.0)`；结果 `RM1F_04 == ([0.0,5.0],[0.0,3.0])`,与
`f17_fixprobe.py` 探针输出、以及派工单 §6 给的示例值 `[(0,0),(5,0),(5,3),(0,3)]` 逐字节一致。

## 3. neuter 自验（两轮独立，覆盖「接线」不只「机制」）

按派工单要求，**把定位改回边移边判**（复原缺陷本体）单独验一轮，**把分类修法也单独复原**再验
一轮——两条修法分别独立证明「拿掉即红」，且互不连带（拿掉一条时另一条覆盖的锁不受影响）。

两轮都通过临时编辑 `src/agent/correction/envelope_transform.py`（工作树内直接改，改前用
`cp` 备份进 `/tmp/.../scratchpad/envelope_transform.FIXED.py`；每轮验完立即用备份逐字节恢复，
`diff` 确认 identical 后才继续）——**不是在 `/tmp` 之外的隔离拷贝里改**，因为本次改动只有一个
文件、且每次都有 git 可对账的 diff 兜底，全程 `git diff --stat` 可查。

### Pass 1 —— 只复原三阶段算法（保留分类修法的 try/except）

把 `_apply_components` 的相 1/相 2 整段换回原始「`for component in components.values(): ... 就地改写`」
单循环逐字复原，**分类修法的 try/except 原样保留**。

```
tests/test_f17_cross_axis_envelope.py -v
2 failed, 1 passed in 9.11s
FAILED test_cross_axis_components_move_every_footprint_corner_without_chamfering
  reason_unresolved: 'cell RM1F_01: polygon edge 3 is not orthogonal'
FAILED test_l_shape_footprint_with_cross_axis_components_preserves_notch
  reason_unresolved: 'cell bottom: polygon edge 0 is not orthogonal'
PASSED test_cell_ring_failure_is_a_structured_rejection_not_a_bare_exception
```

**Group A / B 精确转红,且 `reason_unresolved` 与 F-17 报告的原始崩溃文案、以及
`f17_fixprobe.py` 对 L 形格「现行实现」的输出逐字一致**（`cell RM1F_01: polygon edge 3 is not
orthogonal` 正是本条缺陷立项时的原始报错）。**Group C 不受影响**（保持绿）——符合预期，因为
Group C 的夹具只有单一 x 轴分量，不存在「边移边判」与「三阶段」的行为差异（差异只在≥2 个跨轴分量
时才会出现），这恰好证明 Group C 独立验证的是分类修法，不是算法修法。

### Pass 2 —— 只复原分类修法（保留三阶段算法）

把末尾校验循环换回裸 `if cell_has_polygon(cell): validate_cell_polygon(cell, min_edge_length_m=tol.min_edge_length_m)`
（无 try/except），三阶段算法原样保留。

```
tests/test_f17_cross_axis_envelope.py -v
1 failed, 2 passed in 9.43s
FAILED test_cell_ring_failure_is_a_structured_rejection_not_a_bare_exception
  ValueError: cell sliver: polygon edge 0 length 0.070000 m is below min_edge_length_m 0.100000 m
  (raised at src/agent/correction/cell_geometry.py:174, propagates uncaught out of
   apply_v3_envelope_transaction — exactly the "blows through the flow" shape)
PASSED test_cross_axis_components_move_every_footprint_corner_without_chamfering
PASSED test_l_shape_footprint_with_cross_axis_components_preserves_notch
```

**Group C 精确转红**（本次是裸异常从调用点本身逃出，pytest 报 ERROR 形态，同样判红）；
**Group A / B 不受影响**（保持绿）——三阶段算法此时仍在生效，两组夹具都不会产生非正交环，
所以分类修法有没有包一层对它们的结果没有影响。

### 恢复后

```
cp .../scratchpad/envelope_transform.FIXED.py src/agent/correction/envelope_transform.py
diff ... && echo "IDENTICAL - restore confirmed"   # IDENTICAL - restore confirmed
python -m pytest tests/test_f17_cross_axis_envelope.py tests/test_c2_b2b_envelope_transform.py -v
31 passed in 9.23s
```

**两轮 neuter 精确命中各自负责的锁、零连带、恢复后全绿**——满足派工单「问自己：把调用点改回缺陷
形态，锁红不红」的判别问法（这里「调用点」= `_apply_components` 函数体本身，因为它只有唯一一个
无条件调用点 `apply_v3_envelope_transaction:611`，不存在「函数内部对但调用点没接线」的额外分层，
两轮 neuter 都经由该唯一调用点、走官方入口验证，覆盖的正是接线本身）。

## 4. 全仓测试（`-n 8`，非 `-n auto`）

**⛔ 中间有一次假验证事故，如实记录**：第一次跑用了
`python -m pytest -n 8 2>&1 | tee logfile | head -20`——`head -20` 读完 20 行关闭 stdin 后，
`tee` 在给自己的 stdout 写第 21 行时收到 SIGPIPE 提前终止，连带上游 pytest 也被打断；
日志文件永久停在 33% 处（20 行），后台任务通知里的「退出码 0」其实是 `head` 的退出码，不是
pytest 的——**这正是派工单反复强调的「看退出码」陷阱的一个新变种（管道里退出码来自错误的那个
命令）**。发现日志不完整、且 `ps aux | grep pytest` 确认进程已死之后，立刻改用
`python -m pytest -n 8 > logfile 2>&1; echo $? > exitcode_file` 重新跑一遍（输出直接重定向到
文件，不经过任何下游管道，退出码单独存进只属于 pytest 自己的文件），避免同类截断。

**修正后重新完整跑通,与 orchestrator 独立观测到的数字逐字节一致**（两次独立测量互相印证）：

```
========== 2326 passed, 10 xfailed, 209 warnings in 411.08s (0:06:51) ==========
退出码 = 0
```

对账：基线 2323 passed / 10 xfailed / 0 failed + 本次新增 `test_f17_cross_axis_envelope.py`
3 条 = **2326 passed**，xfailed 数量不变（10）,**0 failed**——净增 3、零回归、零红。
209 条 warning 均为既有的 pytest fixture 路径提示（`record_baseline.py` 的
`run_config.yaml missing` 系列),与本次改动无关（已抽查确认与我改的文件无关联)。

## 5. 复跑脚本结果（官方验收条件 §7）

- `tools/f17_repro.py`：**不再抛 ValueError**（`[run] 没崩 —— 未复现`，退出码 0）。
- `tools/f17_matrix.py`：15 格组合矩阵（section A，直接调用生产 `_apply_components`）**全部 0 斜边 / OK**；
  section B（脚本自带的反事实探针，独立于生产代码）斜边总数 0，`validate_cell_polygon 全部通过`。
- `tools/f17_stepwise.py`：仍会在 step 3 报错——**这是预期行为，不是回归**。该脚本刻意人工地
  对同一个 `geom` 对象连续多次调用 `_apply_components`（每次只喂一个组件的 dict，组件间用
  **独立的调用**串行提交），这与生产路径「一次调用、components 字典里装全部组件」的形状不同
  ——我的三阶段修法解决的是「同一次调用内部」的顺序耦合，不能、也不该改变「跨越多次独立调用、
  每次调用之间提交」这种人为构造的探测方式的行为（那本身仍然是「edge move while judging」，
  只是把 judging 的粒度从组件内提到了调用之间）。验收条件 §7 也只点名了 `f17_repro.py` 与
  `f17_matrix.py` 两个脚本，未把 `f17_stepwise.py` 列为验收项。

## 6. 文件白名单核对

- 改：`src/agent/correction/envelope_transform.py`（仅 `_apply_components` + `_conflict_shape`
  一行新增）。
- 新增：`tests/test_f17_cross_axis_envelope.py`。
- 新增：本执行记录。
- ⛔ 未碰任何 prompt、`src/agent/nodes/**`、`_BASE_SIGN`、`cell_geometry.py` 正交判据、
  `AI_agent/CLAUDE.md`、`plan.md`。

## 7. 我认为派工单准确的地方（无需上报的确认，供 orchestrator 复核）

- 三阶段修法方向与探针数字完全对得上——格 A/格 B 手算值与 `f17_fixprobe.py`/`f17_matrix.py`
  逐字节一致，未发现推翻。
- 「⛔ 不许删/绕过 `_materialize_axis_splits`」——已确认原样保留，Group B 走通。
- 「两条必须一起交」——已确认，且分类修法覆盖了一个**跨轴机制之外**的真实场景（Group C），
  证明这条防线不是摆设。
- 未触发本文件的「合法退出口」——本次施工未发现验收条件冲突、根因/修法与实测不符、或某把锁
  硬补必得假锁的情形，未停下上报。

## 8. 一处如实登记：materialize 插点计数在两组锁夹具里都是 0

Group A、Group B 两组夹具（以及既有测试文件 `test_c2_b2b_envelope_transform.py` 里所有既有夹具，
含它自己命名为「T-junction」的用例）经逐点手算 + 用 `f17_repro.py` 的观测钩子交叉验证，**materialize
阶段插入的新点数量均为 0**——`component.intervals` 的合并边界恰好总是与某个 owner（footprint 或
某个 cell）自身环的原生端点重合，从未出现「合并区间的边界严格落在某个 owner 边内部」这种真正
需要插点的场景。构造一个真正触发插点的夹具，需要一个 owner 的边跨越一个由**其它** owner 贡献、
自身没有覆盖到的合并区间内部断点（真正的 T 型断点桥接场景），这类几何比派工单给的两格更复杂，
我未额外构造。**这意味着**：如果有人未来把 `_apply_components` 里对 `_materialize_axis_splits`
的调用整段删除（而不是改坏别的逻辑），Group A/B 目前**不会**因此转红（因为对这两组夹具而言，
删不删这一步的可观测输出完全相同）——这是本次交付的一个已知覆盖缺口，不是被隐藏的假设。
我认为这不构成「硬补必得假锁」（因为 Group A/B 本身仍是真锁，只是不覆盖这一种特定的删除方式），
但如实登记供 orchestrator 判断是否需要补一个更复杂的 T 型断点夹具。
