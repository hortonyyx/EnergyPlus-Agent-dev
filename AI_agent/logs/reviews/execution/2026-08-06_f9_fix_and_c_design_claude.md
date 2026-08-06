# F-9 施工 + C 设计出稿（Claude Sonnet 5 施工席）

- **日期**：2026-08-06
- **派工方**：orchestrator（Opus 5），派工单
  [`request/2026-08-06_f9_fix_and_c_design_dispatch_claude.md`](../request/2026-08-06_f9_fix_and_c_design_dispatch_claude.md)
- **工作区**：独立 worktree `.claude/worktrees/f9-fix`，分支 `f9-fix-2026-08-06`，基点 `dfbd62a`
  （`git log --oneline -1` 已核实）。主树未动。
- **性质**：第一段施工（两个接线缺口 + 锁 + neuter）+ 第二段纯设计出稿（⛔ 未施工）。

---

## 第一段：施工

### 1.1 两个接线缺口怎么补的

**缺口 2.1 —— `envelope_transform.py:536` 缺 try/except（与 :577-591 不对称）**

原代码（:536-539）对 pre-transform 的 `_dry_resolve_current_ring` 裸调用，没有任何捕获；
post-transform 那次（:577-591）已经包了 `except WindowHostResolutionError`，按
`fallback_action` 分流：`invariant_no_geometry_commit` 一律 `raise`（逃逸口，绝不可静默吞掉），
其余折叠成结构化的 `EnvelopeTransformRejected`。

补丁给 pre-transform 那次加上**完全对称**的处理（同一段判据、同一个 gate_id
`correction.window_host_resolution`，只有提示文字从 "post-transform" 改成
"pre-transform"）。改动位置：`src/agent/correction/envelope_transform.py:536-558`。

**缺口 2.2 —— `WindowHostResolutionError` 没有分类，接不进 F-7 机制**

给 `WindowHostResolutionError` 加了一个 `.category` **只读 property**（不是构造参数），
镜像 `WindowResolverInputError.category` 的对外形状，但推导方式不同：

```python
@property
def category(self) -> WindowSourceErrorCategory:
    if any(row.fallback_action == "invariant_no_geometry_commit" for row in self.conflicts):
        return "input_integrity_error"
    return "model_draw_error"
```

**为什么是这样推导、不是每个抛出点手写一个 category=**：`window_host.py` 里有 9 个
`raise WindowHostResolutionError(...)` 抛出点，其中 4 个（`:664`/`:903`/`:922`/`:985`，加上
`map_direction_binding_error`/`map_va_applicability_error` 映射出来的几乎全部分支）**已经**
把它们构造的每条 conflict 的 `fallback_action` 显式设成 `"invariant_no_geometry_commit"`——
这本来就是 `envelope_transform.py:582-586` 用来判断"能不能折叠成软拒绝"的**同一个字段**。
`.category` 只是把这个已经在抛出点写死的信号读出来聚合，不是另开一套分类标准：
**只要有一条 conflict 标了 `invariant_no_geometry_commit`，说明至少有一个抛出点判定"这个状态
绝不能被静默放过"**，整个异常就是 `input_integrity_error`（重抽没用，必须硬崩）；
只有当**所有** conflict 都是较软的 `needs_input_no_geometry_commit`（本次 4 条真实冲突全是
`source_geometry_mismatch` + 默认 `fallback_action`，即这一档）才是 `model_draw_error`。
这是「分类落在抛出点」的字面兑现——没有匹配 `str(exc)`、没有默认兜底（属性本身没有
default 分支，只有这两个值，`raise ValueError` 若 `conflicts` 为空在构造函数里已经守住）。

改动位置：`src/agent/correction/window_host.py`
（import 增加 `WindowSourceErrorCategory`；`WindowHostResolutionError` 类新增 `category` 属性）。

**接线**：`scripts/tool_scripts/run_stage.py` 的 `_draw_correction` 里，`finalize_correction_draw`
调用外新增 `except WindowHostResolutionError as exc:`，与已有的
`except WindowResolverInputError as exc:` 完全同构——`category != "model_draw_error"` 就
`raise`（硬崩，不吞），否则归档成 `CheckReport` 的一条 `correction.window_host_resolution` FAIL
并返回（`_window_host_error_report`，消息里带真实的 `window_id:reason_code` 列表，不是泛词）。

### 1.2 锁落在哪几条断言

新文件 `tests/test_f9_window_host_crash.py` + 新夹具 `tests/fixtures/f9_window_host_crash/`
（真实崩溃 run `run_2026-08-05_f7_verify_sonnet` 的精简拷贝，只留 `_draw_correction`
真正会读的文件：6 个 `0_reading/*_view.json` + `attempts/001/output.json` +
`_run/{run_manifest,view_manifest}.json` + `1_correction/{correction_geometry,evidence_debt}.json`，
280K，逐字节未改；**不依赖 `f7-manual` 那棵临时 worktree**——那棵树不会随分支存在，
锁必须能在任何 checkout 上复现）。

八条锁，三组：

**Lock 1（端到端真实入口）**：直接调用 `scripts/tool_scripts/run_stage.py::_draw_correction`
——这正是 StageRunner/step_orchestrator 实际调用的 1_correction draw 函数——只 monkeypatch
LLM 边界（`pipeline.run_correction` 返回归档的崩溃草稿），其余全部真代码路径。
- `test_real_crash_run_no_longer_hard_crashes`：断言不抛异常 + `rep.blocking()` 里含
  `check_id == "correction.window_host_resolution"` + 断言报告文字里出现全部 4 个真实
  window_id（`W-F1-N-1/W-F1-N-3/W-F2-N-1/W-F2-N-2`）——不是"不是 None"，是具体 check-id +
  具体证据内容。
- `test_real_crash_run_neuter_run_stage_wiring_removed_restores_crash`：把 `.category`
  monkeypatch 成恒返回 `"input_integrity_error"`（等价于"没有分类接线"的效果），断言
  `pytest.raises(WindowHostResolutionError)`。

**Lock 2（`.category` 判据本身）**：
`test_category_all_model_draw_conflicts_is_model_draw_error` /
`test_category_any_invariant_conflict_is_input_integrity_error` /
`test_category_all_invariant_conflicts_is_input_integrity_error`——三个格子实测
`fallback_action` 的三种组合真的分得对；
`test_real_crash_conflicts_classify_as_model_draw_error`——直接跑真实崩溃产物到
`finalize_correction_draw`，断言 `excinfo.value.category == "model_draw_error"` +
4 条 conflict 的 window_id 集合 + `reason_code` 集合都对得上。

**Lock 3（`apply_v3_envelope_transaction` 自身契约对称）**：
`test_pre_transform_conflict_folds_to_rejected_not_raised`——直接调用
`apply_v3_envelope_transaction`（不经 run_stage.py），断言 `result.committed is False` +
`result.failed_gate_id == "correction.window_host_resolution"` +
`result.geom.conflicts` 里能读出真实的 4 个 window_id（结构化证据落进了 `.evidence.conflicts`，
不是被吞掉）。
`test_pre_transform_invariant_conflict_still_raises`——用 monkeypatch 让
`_dry_resolve_current_ring` 在 `dry_pre_transform` 阶段抛一个
`fallback_action="invariant_no_geometry_commit"` 的冲突，断言 `apply_v3_envelope_transaction`
仍然 `raise`（逃逸口没被误封）。

### 1.3 neuter 红了几条、红在哪

三次独立 neuter，每次**改动病灶本体本身**（不是只在函数内部包一层），逐字节复原到当前状态后
用 `diff` 核对（`diff` 输出为空，确认复原精确）：

| neuter 对象 | 怎么改回缺陷形态 | 红了几条 | 红在哪 |
|---|---|---|---|
| **run_stage.py 的 `except WindowHostResolutionError`（2.2 的接线）** | 直接删掉该 except 分支（源码级还原，不是 monkeypatch） | **1 条**（8 条里唯一一条端到端锁） | `test_real_crash_run_no_longer_hard_crashes` —— 真实崩溃产物在 `window_host.py:903`（`apply_window_host_resolutions` 的 `recomputed != claims` 复核，因为这次 envelope 转换成功折叠、走到了 apply 阶段的复核）重新硬崩，未被任何东西捕获 |
| **envelope_transform.py:536 的对称捕获（2.1）** | 源码级还原成裸调用（去掉 try/except，恢复原始三行） | **1 条**（且是精确定向的那一条） | `test_pre_transform_conflict_folds_to_rejected_not_raised` 红——`apply_v3_envelope_transaction` 直接调用时又变回硬 raise，不再返回 `committed=False`。**其余 7 条仍然全绿**，包括端到端锁——见下方「诚实发现」 |
| **`WindowHostResolutionError.category`（2.2 的判据本身）** | 整段删除该 property | **6 条** | 端到端锁 2 条（`AttributeError` 而非预期行为/预期异常）+ Lock 2 的 4 条分类测试（`AttributeError: no attribute 'category'`） |

（`test_pre_transform_invariant_conflict_still_raises` 全程未参与 neuter——它验证的是
"逃逸口没被误封"这条不变量，两个修复分支都不应该、也确实没有影响它，三次 neuter 里它
始终绿，这是预期行为不是遗漏。）

**诚实发现（未在派工单预判范围内，但不构成"题错了"，是设计权衡的副产品）**：单独 neuter
2.1（envelope 对称捕获）时，端到端锁 `test_real_crash_run_no_longer_hard_crashes`
**仍然是绿的**——因为 2.2（run_stage.py 的 wiring）本身已经足够兜住"随便从哪层逃逸出来的
`WindowHostResolutionError`"，不管它是从 `envelope_transform.py:536` 直接逃出来，还是从
`finalize.py:142`/`window_host.py:903` 逃出来，run_stage.py 那层 except 都能接住。
**这意味着 2.1 和 2.2 不是"缺一不可、必须同时打才不崩"的强耦合关系**——2.2 单独就能
让端到端不崩；2.1 的独立价值在于 `apply_v3_envelope_transaction` **自己的契约**
（"pre-transform 和 post-transform 对称处理"，派工单里明确点名的那个不对称本身就是缺陷，
不依赖调用方最终有没有兜底）——这条契约只有 Lock 3 能验到，端到端锁验不到。两个都按派工单
要求打了，但它们各自锁的是不同层次的正确性，我如实记录这个耦合关系比预想的松，而不是含糊带过。

### 1.4「归档重抽 vs 硬崩」判成哪一类、论证

**判成 `model_draw_error`**（归档失败 attempt + 盲重抽），论证：

真实的 4 条冲突全部是 `reason_code="source_geometry_mismatch"` +
`fallback_action="needs_input_no_geometry_commit"`（`window_host.py:722`，走的是 `_conflict`
辅助函数的**默认** `fallback_action`，没有任何抛出点把这次的冲突显式标成
`invariant_no_geometry_commit`）。按 1.1 节的推导规则，`.category` 算出来就是
`"model_draw_error"`——这不是我另立的判断，是把"这次错误的抛出点自己都没把它标成
不可恢复"这个既有信号读出来的必然结果。

调查单提出的反对意见（"这类错误是系统性策略失误，不是随机噪声，盲重抽期望修复率不确定"）
我认同，但它论证的是**"归档重抽机制对这个案例治标不治本"**，不是**"这个案例该被归类成
input_integrity_error"**——`input_integrity_error` 在现有代码里的含义是"上游产物本身坏了/
被篡改，任何重抽都没有意义"（比如 `resolver_output_tampered`、`va_identity_invalid`），
这次不是——上游 `0_reading` 的四条北窗笔画本身是干净的（`W-F1-N-1` 的平面声明 `[1.24,3.64]`、
北立面 `North_view/S5` 的局部值 `[1.24,3.64]`，两边数据都对，错的是**correction 抽签**
选笔画时没套用镜像），换一次抽签**理论上**是有机会避开的（哪怕本单没有真实多轮抽样数据
证明"实际会不会避开"）。**为了让 case 跑过去而把它归成 input_integrity_error 是给错误分类
——我没有这么做**：`.category` 的推导完全独立于"我希望它落哪一类"，是先定推导规则、
再看真实数据落在哪一格,不是反过来。

`归档重抽`本身**不代表"问题被修好了"**——只代表"没有硬崩、被记录在案、消耗一次重抽预算"；
是否要在此基础上追加更强的干预（见第二段设计），交给这份设计稿处理，不在本判断范围内。

---

## 第二段：设计出稿（⛔ 未施工，本节及以下均为设计文字，未改任何生产代码）

### 2.1 §3 第 1 问：`along_origin` 在建目录时刻拿不拿得到 —— **结论：拿不到，结构性的，不是"忘了传参"能补的**

**证据链（行号 + 调用顺序）**：

1. 目录构建函数 `build_observation_reference_catalog_from_run`
   （`src/agent/correction/window_sources.py:493-495`）签名是：

   ```python
   def build_observation_reference_catalog_from_run(
       *, run_dir: Path, reading_dir: Path, required_for_v3: bool = False,
   ) -> str | None:
   ```

   —— **只接受 `run_dir`/`reading_dir`，没有任何几何/`geom` 参数**。它内部只读
   `view_manifest.json`（:524-529）+ 0_reading 各 `expected_output_id.json` 原始字节
   （:536-546），喂给 `derive_observation_reference_catalog`（:456-476，同样不接收几何）。

2. 调用时机：`scripts/tool_scripts/run_stage.py:329-333` 在
   `run_correction(...)`（:334，**这次 LLM 画图调用本身**，产出 `CorrectedGeometryV3` 的平面
   footprint）**之前**调用这个目录构建函数。也就是说：目录被造出来的那一刻，correction
   这次要画的平面 footprint **根本还不存在**——不是"存在但没传进来"，是这次调用链上
   压根没有一个 `geom` 变量可以传。

3. `along_origin` 的**唯一**两条计算路径都需要 footprint/ring：
   - `derive_facade_frame`（`src/agent/correction/facade.py:72-112`）需要
     `footprint_x: list[float]` / `footprint_y: list[float]`（:75-76 形参），
     `along_origin = lo if sign > 0 else hi`（:103）直接来自这两个 list 的 `min`/`max`（:85-86）。
   - `derive_view_projection_frame`（`facade.py:166-211`）需要 `vertices`（:168 形参），
     `lo, hi = (min(xs), max(xs)) if axis == "x" else (min(ys), max(ys))`（:198）同样直接来自
     传入的顶点坐标；下游真正在用的入口是
     `materialize_current_ring_va_elevation_bindings`（`window_sources.py:999-1002`），
     文档字符串写得很直白：**"Fresh, non-cached 13-field Va bindings for exactly `geom`'s
     ring."**——形参就是 `geom: CorrectedGeometryV3`（:999），"exactly `geom`'s ring"
     就是这次 correction 正在画的那个 ring，不是别的什么固定值。

4. 这个 `along_origin` 目前**唯一**被消费的地方是 `window_host.py:658-675` 的
   `_source_world_interval`（`resolve_window_hosts` 内部，:669 处
   `along_origin=binding.along_origin`），而 `resolve_window_hosts` 只在**画完之后**
   （`finalize.py:120` 的 `apply_deterministic_core` 内部 / `finalize.py:142` 的 final phase）
   才被调用——这正是 F-9 今天能被**发现**（但不能被**预防**）的原因：检查它的代码本来就是
   post-draw 的，从来没打算 pre-draw 用。

**结论**：这与 F-7 当初"签名里根本没有 manifest"是**同一个形状**——不是随便加一个参数就能
传进去，是"世界区间"这个量的**定义本身**依赖这次抽签要画的那份几何，而目录构建这一步
在时间线上排在那次抽签**之前**。想在目录里塞世界区间，必须先解决"用什么样的几何去算"这个
更上游的问题——这正是下面两条路线分道扬镳的地方。

### 2.2 两条路线的后果与代价（含张力正面讨论）

**路线 ①「代码算好世界区间、喂给模型，模型仍然自己挑」**

按 §2.1 的证据，**这条路线在今天的单次单遍抽签架构里无法照字面实现**——"代码先算好"这句话
本身要求 `along_origin` 已知，而 `along_origin` 依赖这次要画的 footprint。要让①成立，
只有两个子选项，且都比派工单原始描述（"模型不必心算镜像"）的实现成本高得多：

- ①a **两遍抽签**：第一遍只画 footprint（不引用窗户 source_ids），代码用这份草稿算出
  `along_origin` → 重新生成一份带世界区间的目录 → 第二遍抽签基于这份目录挑窗户来源。
  这是把今天"一次 LLM 调用画完平面+立面引用"的单遍架构改成两遍，涉及
  `_build_correction_messages`（`pipeline.py:329` 起）新增一条 LLM 往返、`run_stage.py`
  的 `_draw_correction` 流程重排、以及"第一遍产出算不算一次正式 attempt"这类计次/审计
  问题——成本远高于"补一段 prompt 文本"，接近一次架构改动。
- ①b **代理值**：不用这次抽签的 footprint，改用 `0_reading` 的**原始平面读数**（尺寸链
  推出的 footprint 边界）近似算一个 `along_origin`，绕开"必须等这次抽签画完"的时序问题。
  代价：这个近似值和**下游权威检查**（`resolve_window_hosts` 用的是这次抽签**校正后**的
  ring，Vg envelope reconcile 之后可能已经和原始读数有出入——这正是 07-08 就登记、至今
  未收口的"尺寸基准=轴线还是墙面"债务，本单 08-06 调查单里那个恒定 0.12m 残差就是同一类
  基准偏移的具体案例）**不是同一个数**——目录里给模型看的"世界区间提示"和最终真正拿来判
  重叠的"世界区间"可能对不上，模型可能被一个不完全准的提示误导，制造新的、更隐蔽的
  "提示说对但检查说错"的困惑案例。

  `source_ids`「模型自证用了哪条证据」的语义在①下**完整保留**——不管是①a 还是①b，
  模型仍然要在目录里挑一个具体的 `<view>/<observation_id>` 填进 `source_ids`，只是
  挑选时多了一份世界区间参考，B5 的审计意图不受影响。

**路线 ②「配对整个交给代码，模型不再挑」**

结构上**没有时序问题**——世界区间计算本来就只能发生在画完之后（§2.1 结论4），
`resolve_window_hosts` 已经在这个时间点跑；路线②只是把"哪条候选立面笔画配这扇窗"这个
**判断**，从"模型在目录构建时刻的心算"挪到"代码在 `resolve_window_hosts` 这个既有的
post-draw 时间点做几何匹配"——不需要引入新的时序，是把已经存在的检查函数从
"事后挑错"升级成"事后直接选对"，改动范围收敛在 `window_host.py`/`window_sources.py`
内部，prompt 目录层可以做得比①更小（模型只需要声明"这扇窗在哪个视图里有证据"这一层，
不需要声明"是哪一条具体笔画"）。

**`source_ids` 语义被架空的张力（必须正面讨论，不能回避）**：B5 立 `source_ids` 这个字段的
本意是"模型自证用了哪条观测"——如果配对完全交给代码，模型不再需要（也不再能够）指认
"具体是哪一条笔画"，`source_ids` 在细粒度（哪一条 stroke id）上的自证意义确实被削弱。
但**不是完全架空**：可以保留"模型声明这扇窗的证据落在哪个视图"这一层的引用（例如只要求
`North_view` 而不要求 `North_view/S5`）——这一层仍然是模型自己的判断，仍然能拦住
"模型凭空捏造一扇窗、在任何视图里都找不到证据"这类更严重的错误（这正是本次没有出问题的
`W-F1-N-2`——它至少证明"哪个视图有证据"这一层模型是能判对的，出错的只是"哪一条"这个更细的
几何判断）。细粒度的"哪一条"这个判断——恰恰是这次证明"人类/模型心算镜像不可靠"的那个判断
——移交给代码，符合不变量 #1；但这确实是**审计粒度的下降**，B5 当初设计
`source_ids` 精确到单条笔画是否有其他消费者依赖这个精确粒度（比如某个下游审计报告直接
展示"这扇窗引用了哪条具体笔画"），我没有在本单范围内逐一核查所有消费者，这一点需要
在采纳②之前专项核实，不能想当然认为"降到视图级别"零副作用。

### 2.3 不管走哪条，2.2 的「归档重抽 vs 硬崩」分类还成不成立、要不要改

**分类机制本身（`.category` 的推导规则）不需要改**——它是一个通用的、基于
`fallback_action` 的故障分类器，不针对"立面裸数值配对"这一个根因，任何未来新出现的
`WindowHostResolutionError`（不管是不是同一个根因）都会按这条规则分类。

**会变的是"落在哪一类的实例数量"，不是分类规则本身**：路线①或②任一落地后，
"源自立面裸数值配对错误"这一形状的 `source_geometry_mismatch` 冲突会**结构性地不再产生**
（①靠给模型正确提示大幅降低出错概率但不保证归零；②靠代码接管配对判断，只要几何计算本身
无 bug 就能做到归零，因为不再有"模型心算镜像"这一步可错）。也就是说，`model_draw_error`
这一类的 `WindowHostResolutionError` 发生率会下降，但机制本身（一旦真的发生，判成
`model_draw_error` 归档重抽）不需要重新设计。

### 2.4 什么都不改会怎样

第一段的 2.1+2.2 修好之后，**不再硬崩**，但没有解决"这类布局下裸数值配对会系统性配反"
这个抽签行为本身——**任何窗口位置关于立面对称轴不对称、且局部数值容易与另一扇窗重合/接近
的布局**（本 case 是北立面回文尺寸链），correction 阶段会**持续**产出这 4 类冲突、被归档成
`model_draw_error` 走盲重抽。根据 08-06 调查单 §5 的分析，这类系统性错误的盲重抽期望修复率
**不确定**——`step_orchestrator.py:245` 的 `draw_fn(None)  # blind: never inject
judge/feedback in the loop` 是一条**明确写在代码注释里的既有设计决定**：重抽循环刻意不
注入任何反馈，所以模型再抽一次大概率还是用同一套"裸数值配对"策略、大概率还是配反同一批
窗——除非这次数值巧合没那么精确（本例精确到小数点后两位完全相同，不保证每次都这么整齐）。
**⇒ 结构性风险仍在**：对称/近对称立面布局的 case，即使不再硬崩，也可能反复烧光重抽预算
最终落入 `QUARANTINED`（`step_orchestrator.py` 里 `existing >= cap_draws` 分支），
只是从"硬崩"变成了"更慢地失败"。这正是第一段止血（2.1+2.2）之外还需要走完这份设计稿
（路线①或②）的理由。

**旁证一条（未在派工单要求范围内，顺带记录不做为结论依据）**：我考虑过"重抽循环改成非盲
（把冲突的镜像搭档提示喂回下一次抽签）"作为第三条更便宜的路线，但
`step_orchestrator.py:245` 那条注释显示"重抽永远盲"是一条**既有的、刻意的**设计边界
（大概率是为了不让 gate①/judge 反馈污染重抽，防止模型学会"迎合检查器"而不是真正学会
几何推理——具体动机本单未考证，只确认了这条边界的存在），采纳这条"非盲重抽"路线需要
显式打破这条既有边界，代价不比①②低，且需要用户单独拍板是否值得为这一类错误破例，
本单不推荐把它当作低成本捷径。

### 2.5 推荐

**推荐路线②，但要求在采纳前专项核实 `source_ids` 细粒度的其他消费者**。理由：①在今天的
单遍抽签架构下无法按字面实现，唯一可行的两个子路线（两遍抽签 / 代理值）分别付出"架构改动"
或"提示和权威检查可能对不上"的代价；②结构上没有时序问题，直接把"已经证明人类/模型心算
不可靠"的那个判断（镜像配对）交回代码，命中不变量 #1 最彻底，且改动范围收敛在
`window_host.py`/`window_sources.py` 内部。唯一的风险是 `source_ids` 审计粒度下降，
这是一个需要用户/B5 原始设计者拍板的权衡，不是纯技术问题——本单只负责把张力摆清楚，
不代为拍板。

---

## 全仓回归数字

**基点**：`f9-fix-2026-08-06` 分支，HEAD 上叠了本单 3 处生产代码改动 + 1 个新测试文件 +
1 个新夹具目录（未 commit 前先测；commit SHA 见文末）。

**⚠️ 环境陷阱（已核实，与本单改动无关）**：本机共享 venv 的 editable 安装
`_editable_impl_energyplus_agent.pth` 把 `import src...` 的兜底路径钉死在**主工作树**
（`/workspaces/EnergyPlus-Agent-dev`），而不是这棵 worktree。凡是以 `python3
scripts/tool_scripts/xxx.py`（相对路径脚本文件）形式起子进程的测试，子进程自己的
`sys.path[0]` 是脚本所在目录（不含 `src`），落回该 `.pth` 时会解析到**主树**的 `src/`。
已用 `python3 -c "print(sys.path)"` 精确复现该路径解析（子进程内 `gt_schema.__file__` ==
主树路径、`REPO_ROOT` == 主树根），并证实：`git stash` 到干净 `dfbd62a`（零改动）后，
同样的 5 条测试里有 2 条（`test_inspect_dxf.py::test_manifest_inspector_cli_exit_and_json_contract`
/ `test_gt_from_dxf.py::test_build_only_cli_round_trips_l_candidate_and_nonzero_north`）
**依然红**，加 `PYTHONPATH=<本 worktree>` 后立刻转绿——**与本单改动无关，是纯环境假红**。

**不设 PYTHONPATH（默认调用方式）**：`pytest -n auto` → **5 failed, 2229 passed, 8 skipped,
10 xfailed**（350.97s）：3 条真实已知 F-8（缺 `.gitignore` 挡住的活输入）+ 2 条上述假红。

**设 `PYTHONPATH=<本 worktree 绝对路径>`（消除假红后的真实数字，且已核实
`tests/test_f9_window_host_crash.py`/相关子集在该设置下同样全绿）**：
`pytest -n auto` → **3 failed, 2231 passed, 8 skipped, 10 xfailed**（324.64s）。

3 条真红逐条核实为已知 F-8（在 `git stash` 后的干净 `dfbd62a` 上**同样**这 3 条红，
证实与本单改动无关，如实登记、未修、未 `git add -f` 任何东西）：
- `tests/test_checks_reading_correction.py::test_partition_on_window_jamb_real_restore_reading_r2_flags_four`
  —— `FileNotFoundError`，缺 `AI_agent/logs/experiments/2026-06-30_reading_scaffold_restore_validation/readings/sonnet_r2/1f_view.json`（`AI_agent/logs/experiments/` 未入库）。
- `tests/test_reading_score.py::test_sm21_phase1_reading_score_regression_floor`
  —— `assert scores` 得到 `{}`，缺 `case_tests/e2e_tests/smalloffice_21_pre/phase1` 活输入。
- `tests/test_validation_run_baseline.py::test_sm21_anchor_ep_clean`
  —— `read_ep_end` 返回 `None`，缺 EP 产物（`.gitignore` 挡住的 EP/EP_run）。

派工单声明的基线是"2234 绿/10 xfail/0 红"，同一份留言另附了「⚠️可能有 3 条已知 F-8 红」
的但书——本单实测数字（`PYTHONPATH` 修正后 **2231 绿 + 3 条已知 F-8 红 = 2234**）与
"但书"完全吻合，只是"0 红"那句话本身和它自己的但书矛盾，未构成停下上报的门槛（唯一
不接受的上报理由是要求推翻 `_BASE_SIGN`，这不是那种情况；本单如实登记数字而非硬凑成
"0 红"）。

`tests/test_f9_window_host_crash.py`（本单新增的 8 条锁）：全绿，
`tests/test_c2_b2b_envelope_transform.py`/`test_c2_b5_*`/`test_f5_window_source_fields.py`/
`test_f7_observation_reference_translation.py`/`test_e2e_break_r2_locks.py`/
`test_run_stage_flow.py`/`test_audit_remediation_accepted_inputs.py`（受影响面全集）
先行小范围跑过一次：326 passed，零回归。

---

## 边界自查

- ⛔ 未改 `_BASE_SIGN` / `A1_coordinate_normalization.md` §2.2——本单全程未打开这两处。
- ⛔ 未放宽 `_claim_links`、未放宽任何容差、未碰 0.12m 那条既有债。
- ⛔ 未重跑 correction 抽签——`tests/fixtures/f9_window_host_crash/` 是已归档产物的精简拷贝，
  零 LLM 调用；本单全程零 LLM 成本。
- ⛔ 未碰 `case_tests/` 未跟踪目录、未在 `f7-manual` worktree 写任何东西（只读取用于制作夹具，
  制作后新增文件全部落在本 worktree 的 `tests/fixtures/`，`f7-manual` 树零改动）。
- ⛔ 未 push；逐个文件 `git add`（见下方 commit）。
- 一次性 repro 脚本/patch 备份全部留在 `/tmp/claude-0/.../scratchpad/`，未落回仓库。

## Commit

（见最终回复的 commit SHA）
