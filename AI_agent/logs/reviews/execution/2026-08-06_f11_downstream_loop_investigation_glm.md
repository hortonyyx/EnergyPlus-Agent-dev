# 执行日志 · F-11：下游 LangGraph 死循环 + foundations 阶段校验尚未存在的面

> **席位**：GLM-5.2（调查席）· **日期**：2026-08-06 · **基点**：`6.15_ValidationArchM0toM4` @ `9b6a7ff`
> **对应调查单**：`AI_agent/logs/reviews/request/2026-08-06_f11_downstream_loop_investigation_glm.md`
> **产出性质**：⛔ 只调查、零生产码改动、零 commit / push、零 `git add -A`、未碰 `case_tests/` 任何文件。一次性脚本仅在 `/tmp`。

---

## 0. 开工自检（已执行，全过）

```bash
git log --oneline -1   # → 9b6a7ff 08.06_wall3_orchestrator_lightgate_passed   ✅
pwd                    # → /workspaces/EnergyPlus-Agent-dev                     ✅
git status --short     # → 4 个 case_tests 未跟踪目录（含 run_2026-08-06_wall3_a_retest）✅
                       #   另有 M AI_agent/plan.md（工作树既有，非本席改动）+ 本调查单本身
```

---

## 1. 安全边界遵守记录（先说清我**没**碰什么）

调查单 §1 的红线 = 这条链路会无限循环 + 持续按量计费调用 DeepSeek。**本席全程未触发任何下游 LLM subagent，零 DeepSeek 费用。**

- ⛔ **未跑** §2 的复现命令 `run_full_pipeline.py ... --intake-from ...`（它会触发 zone/material/schedule 三个 LLM subagent，且 §2 已证明会无限循环）。
- ⛔ **未跑** §3 的 `cross_ref_foundations_node` spy 探针（它 monkeypatch 在 cross_ref 处 `SystemExit`，但仍会让 intake→zone→material→schedule 真跑一遍，即 3 次 DeepSeek 调用 + 约 16 秒）。
- ✅ **改用零 LLM 确定性探针**（`/tmp/f11_no_llm_probe.py`）：直接加载 intake bundle、手工构造 foundations 阶段 state、直接调 `cross_ref_foundations_node`，**完全不进入 LangGraph、不调任何 subagent**。20 秒内出结果，独立可重跑，证据等价。
- 所有命令均带 `timeout`，无 `| tail`。

**判断**：§2/§3 的会调 LLM 的命令，其结论（115 条 + 不终止）已能用确定性探针完整复现，没必要为"再跑一遍"付费。这是对 §1 安全边界的**加严**而非放宽。

---

## 2. TL;DR（核心结论，三句）

1. **115 条错误不是"cross_ref 在校验 ConfigState 自己的 surfaces"，而是 E4 output-coordinate 契约门的 vertex-drift 检查**：它把**终态 snapshot**（外部坐标快照，含全部 115 个面）逐条和 `ConfigState.surfaces` 比对；foundations 阶段 surfaces 还没建（=空）⇒ snapshot 里每条都"missing from ConfigState"。`validate_references()` 在 foundations 阶段 surfaces/fenestrations/constructions 全空，报 **0 条**（探针实证）。
2. **循环结构上不可能终止**（§6.2 详证）：三个出口全被封死——重试被 `MAX_RETRIES=0` 封死；人工批准被 `auto_approval` 有错必拒封死；错误消失（surfaces 建出来）被 `_cross_ref_router`「有错即短路到 validate、跳过 construction→surface」封死。surface/fenestration/hvac/people/lights 五个 subagent **一次都不会被触达**。
3. **是"校验时机错位"为主因、"路由短路"为放大器**——不是路由顺序错、也不是输入不该带 snapshot。今晚是 **5_intakeoutput 首次**产出 `accepted_correction` intake（world_legacy 强制带 snapshot），此前所有 sm21 intake 都是 legacy standalone（禁止 snapshot、vertex-drift 自动跳过）⇒ 这条路径潜伏至今才被撞出。与 F-10「潜伏一个月无人发现」同形。

---

## 3. §6 五问逐条回答

### 问题 1 ⭐ cross_ref_foundations 为什么要在 foundations 阶段校验 surfaces？路由顺序错 / 校验放错层 / 输入不该带 snapshot？

**先纠正提法**：它校验的**不是** ConfigState 自己的 surfaces。`cross_ref_foundations_node` 的代码（`src/agent/nodes/cross_ref.py:26-34`）是：

```python
return AgentStateUpdate(
    validation_errors=state.config_state.validate_references() + _output_coordinate_errors(state)
)
```

两部分：
- `validate_references()`（`src/mcp/state.py:250-`）：遍历 `self.surfaces / self.fenestrations / self.constructions` 检查内部引用。foundations 阶段这三个 list 全空 ⇒ for 循环全空转 ⇒ **0 条**（探针 STEP 1 的 115 条**全部**来自第二部分，验证 `validate_references()` 这部分 0 贡献）。
- `_output_coordinate_errors(state)`（`cross_ref.py:4-23`）：跑 E4 契约门 `validate_output_coordinate_contract`，其中第 6 步 `_vertex_drift_issues`（`src/validator/output_coordinates.py:794-818`）遍历 **snapshot.records**，逐条查 `config.surfaces`/`config.fenestrations` 里有没有同名对象，没有就报 `VERTEX_FRAME_DRIFT: '<面名>' in the snapshot is missing from ConfigState`。

snapshot 是**终态几何快照**（`build_output_coordinate_snapshot`，`output_coordinates.py:697-718`，遍历 `bg.surfaces`+`bg.windows` 全部对象），在 5_intakeoutput 装配完成后才算出来；而 foundations 阶段几何内核还没跑，`config.surfaces` 必然为空。**终态快照 vs 非终态状态，逐条比对必然全 missing。**

**设计意图（历史考据）**：
- `_output_coordinate_errors` 进 cross_ref 的提交 = `ccb396e 7.14_BO_NorthAxisWiringClosure`（`git log -S "_output_coordinate_errors" -- src/agent/nodes/cross_ref.py`）。
- 其 docstring（`cross_ref.py:5-9`）写明意图：*"Run the E4 contract gate at graph repair boundaries. The final Workflow gate remains authoritative for the converted IDF, but **an in-memory drift must not survive a parallel merge/checkpoint/retry only to be discovered at export time** (E4 §5.2 call point 3, BO-CR8)."*
- 即：意图是**防止"完整几何"在 merge/checkpoint/retry 中被悄悄改坏**。这个意图本身合理，但它有一个**未言明的前置条件——被比对的几何必须已经完整**。

**三选一的判据**：

| 候选 | 判定 | 依据 |
|---|---|---|
| 路由顺序错了 | ❌ 不是主因（但有一个真放大器，见下） | `intake→phase1→cross_ref_foundations→construction/validate` 的拓扑本身合理；foundations 后做一次 cross-ref 是对的。 |
| **校验放错了层 / 时机** | ✅ **主因** | vertex-drift 是**终态语义**检查（依赖完整几何），却被 `_output_coordinate_errors` **无差别地**挂在**所有** graph repair 边界（`cross_ref_foundations` / `cross_ref_complete` / `validate_node` 三处都调它，见 `cross_ref.py:33,40` 与 `validate.py:9-27,39`）。它只在几何完整后（cross_ref_complete 之后）才有意义。 |
| 输入不该带 snapshot | ❌ 不是 | snapshot 是 `world_legacy + accepted_correction` 契约的**法定组成**：`output_coordinates.py:190-192` 强制 `geometry_snapshot_sha256` 非 None；删它等于破坏 E4 信任根（snapshot 是 vertex-drift 终门的"pre-E4 基线"证据）。 |

**放大器（路由层的真问题）**：`_cross_ref_router`（`graph.py:50-52`）= `"validate" if state.validation_errors else "construction"`。foundations 阶段一旦有任何错（哪怕是 vertex-drift 这种"时机误报"），就**短路到 validate、跳过 construction→surface→fenestration 整条链**——于是 surfaces 永远建不出来，错误永远不消失。即使把 vertex-drift 从 foundations 移除，"foundations 有错即跳过 construction"这个语义本身也值得审视：它让 foundations 阶段的任何错误都无法通过"继续把几何建完"来自愈。

**净判据**：**主因 = vertex-drift 检查的时机错位（终态语义挂在了非终态阶段）；放大器 = 有错即短路 construction 的路由。**

---

### 问题 2 ⭐ 那个循环在什么条件下能终止？逐条走通 §2 的 1–6，说明存不存在任何一条退出路径。

**结论先行：结构上不可能终止。三条潜在出口全部被封死。**

逐条（行号均为本基点 `9b6a7ff`）：

1. **`_route_after_foundations` / `_cross_ref_router`**（`graph.py:50-52`）：`return "validate" if state.validation_errors else "construction"`。foundations 阶段 `validation_errors` = 115 条（非空）⇒ 走 **validate**，跳过 construction。
2. **`MAX_RETRIES = 0`**（`_share.py:7`，自 `299149c 4.20-zero` 起未变，`git log -S "MAX_RETRIES: Final"`）。`state.max_retries` 默认 = `MAX_RETRIES = 0`（`state.py:243`）。
3. **validate 重试分支**（`validate.py:41`）：`if errors and state.retry_count < state.max_retries:` = `errors and 0 < 0` = `errors and False` = **False** ⇒ **永不重试**，直接进 `interrupt()`。
4. **validate rejected 分支**（`validate.py:67-77`）：`goto="intake"`，`update={..., "validation_errors": decision.get("errors", []), "retry_count": 0}`。
5. **`auto_approval`**（`runner.py:145-160`）：有错时返回 `{"approved": False, "feedback": "please address errors: ..."}`——**无 `"errors"` 键**（探针 STEP 2 实证：`has 'errors' key? False`）。
6. **intake 短路条件**（`intake.py:52`）：`if state.intake_output is not None and not state.validation_errors:`

**链式推导（零 LLM 探针逐环实证，`/tmp/f11_no_llm_probe.py`）**：

- ⑤⇒④：auto_approval 无 `errors` 键 ⇒ `decision.get("errors", [])` = `[]` ⇒ **`validation_errors` 被设为空列表**（探针 STEP 2：`carried=[]`）。
- ⑥：`intake_output` 非空（`--intake-from` 流程下 intake 短路分支**不重跑 pipeline**、`intake_output` 保持；validate 的 update 字典里**不含** `intake_output`，故 LangGraph 不覆盖它）且 `validation_errors=[]` ⇒ `not []` = True ⇒ **短路触发**（探针 STEP 3：`short-circuit TAKEN = True`），重新 seed `config_state`（building + site + apply contract），**surfaces 仍空**。
- 回到 zone/material/schedule（phase-1 并行，**只填 zones/materials/schedules，不填 surfaces**）⇒ cross_ref_foundations ⇒ ① `validation_errors` 又 115 条。
- 探针 STEP 4：第二轮 cross_ref_foundations 返回 **115 条，且与第一轮逐字节相同**（`errs == errs2 == True`）。

**三条潜在出口为何全封死**：

| 出口 | 封死它的东西 |
|---|---|
| 重试自愈（③） | `MAX_RETRIES=0` ⇒ `retry_count < max_retries` 恒 False |
| 人工批准（interrupt→approved） | `auto_approval`（⑤）在有错时**永远** `approved=False`（这是设计：`runner.py:155-160`，有错就不该放行去 simulate） |
| 错误消失（surfaces 建出来让 115 条变 0） | `_cross_ref_router`（①）有错即跳过 construction⇒surface⇒fenestration，**这五个 subagent 一次都跑不到**（与 §2 现象「surface/fenestration/hvac/people/lights 一次都没跑过」逐字吻合） |

> **明确写：结构上不可能终止。** 不存在任何一条能让它在当前代码 + 当前输入下退出的路径。唯一"出口"是进程被杀 / 超时 / 断电。

---

### 问题 3 ⭐ 2–3 个修法选项，每个写清后果与代价（⛔ 不动手）

#### 选项 A（治标 / 单独无效）：让 `auto_approval` 有错时回传 `"errors"` 键
让 ④ 的 `decision.get("errors", [])` 拿到真实错误 ⇒ intake 短路条件因 `validation_errors` 非空而**不短路** ⇒ 进 intake 的 pipeline 分支（`intake.py:71` `if state.reading_vector_dir:`）。
- **后果**：`--intake-from` 流程**没有** `reading_vector_dir`（`run_full_pipeline.py:297-306` 只在 `--reading-from` 时设它）⇒ 跳过两个 `if` 直落 `intake.py:111` `raise RuntimeError("intake_node: no input...")` ⇒ **把无限循环换成一次崩溃**。不是修好，是换了个失败形态。
- **代价**：0 价值，且制造新崩溃。**排除。**

#### 选项 B（治本 / 校验层，推荐）：把 vertex-drift 检查从 foundations 阶段移除，只保留在几何完整后的边界
`_output_coordinate_errors` 拆成两部分：**frame 检查**（Building North Axis / GGR A3-A5 / Zone frame，`output_coordinates.py:613-649`，foundations 阶段已完整、有意义）留在 cross_ref_foundations；**vertex-drift 检查**（`_vertex_drift_issues`，依赖终态 snapshot+完整几何）只在 `cross_ref_complete` / `validate` / export 跑。
- **后果**：foundations 阶段不再误报 ⇒ 路由进 construction ⇒ surfaces/fenestrations 建出来 ⇒ 后续 vertex-drift 有完整几何可比对 ⇒ 115 条要么变 0（几何没被改坏，正常）、要么是真 drift（该报）。**正解。**
- **代价**：是设计层改动（需派工 + 对抗审，因 E4 信任根涉及签字/可复现）。要确认"frame 检查"与"vertex-drift 检查"在 foundations 阶段没有别的依赖耦合（目前看 `_output_coordinate_errors` 是两者串接，拆分干净）。**与设计意图最对齐**：vertex-drift 本就只在"几何已完整"时才有意义。
- **风险**：要复核 cross_ref_complete 与 validate 是否真能兜住所有真 drift（即不能因为移出 foundations 而漏掉某条本该早报的）。

#### 选项 C（路由止血）：`_cross_ref_router` 有错时不再短路到 validate，降级为 advisory + 继续走 construction
foundations 阶段的错误只记录不阻断；硬校验留给 cross_ref_complete / validate。
- **后果**：surfaces 能建出来；foundations 的 vertex-drift 误报不阻断后续。
- **代价**：改的是路由语义不是校验语义，与 B 同向但更粗（B 是精准移除"不该在这阶段跑的检查"，C 是"不管什么错都先放过"）。需确认 foundations 阶段是否还有别的真该阻断的检查——目前 `validate_references()` 在 foundations 阶段报 0 条，所以现状下没有；但语义上"foundations 错误不阻断"比 B 更宽，未来加新检查时容易漏。
- **风险**：比 B 更容易放水（把真该早停的 foundations 错误也一起放过了）。

#### 选项 D（什么都不改）：后果
循环永远不终止，每轮调用 zone/material/schedule 三个 LLM subagent（DeepSeek 按量计费），永远到不了 surface/fenestration/hvac/people/lights/simulate。§1 已实犯 1h40m / ~400 圈。**不可接受**（既是钱，也永远产不出 IDF）。

> **我的推荐（不动手，供派工方拍板）**：**选项 B**（最干净、对齐设计意图、不放宽语义）。C 是次选（更粗但同样止血）。A 排除。无论选哪个，**都必须同时修 §6.5 的可观测性**（见下），否则下次同类问题还是只能靠账单发现。

---

### 问题 4 它是不是与 F-5 / F-7 / F-10 / 墙 3 同族？是哪一种形状？

**是同族。最贴近 F-10（潜伏缺陷）+ F-5（接口错位），叠加"测试绿而真链路崩"。**

| 形状 | 本案对照 | 证据 |
|---|---|---|
| **接口错位**（F-5/F-10 形） | vertex-drift 检查是**终态语义**，被挂在**非终态阶段**（foundations）——两个接口（snapshot 的"终态"语义 vs foundations 的"非终态"时机）对不上 | `cross_ref.py:33` 无差别调用 `_output_coordinate_errors`；`output_coordinates.py:794` 假设几何完整 |
| **被前面的墙遮蔽**（F-10 形："串行修墙让后段缺陷无限期潜伏"） | 5_intakeoutput 至今"零证据"（见 CLAUDE.md §2），**今晚才首次**产出带 snapshot 的 `accepted_correction` intake；此前所有 sm21 intake 都是 legacy standalone（无 snapshot），这条 vertex-drift-in-foundations 路径从未被触发 | 下表：06-16/07-02 无 snapshot 侧车；今晚首次有 |
| **测试绿而真链路崩**（F-5 形："夹具照抄实现、合规产物必崩") | E4 gate 是 7.14（`ccb396e`）落地的；其测试用的是"几何已完整"的 fixture（cross_ref_complete / export 场景），**没有任何测试用"--intake-from 带 snapshot + foundations 阶段空 surfaces"组合**驱动 cross_ref_foundations | 全仓测试在 foundations 阶段空 ConfigState 下从不报 115 条 |

**snapshot 有无的实证（坐实"今晚首次"）**：
```
run_2026-06-16_opus_e2e/5_intakeoutput:        NO snapshot sidecar / NO contract
run_2026-07-02_sonnet_flow_e2e/5_intakeoutput: NO snapshot sidecar / NO contract
run_2026-08-06_wall3_a_retest/5_intakeoutput:  HAS snapshot sidecar / HAS contract  ← 今晚首次
```
且今晚 `intake_output.json` 仍是**纯 11 字段**（contract/snapshot 在**并列侧车**，符合 E4 §3.4 flat 设计），所以"输入多了 snapshot"这件事是 5_intakeoutput 装配端的新行为，不是 intake 本体变了。

> **形状判定**：与 [[seed-bypass-exposes-hidden-downstream-blocker]] / [[probe-past-the-blocker-to-find-hidden-walls]] 记录的方法论**完全同构**——"链路卡在 X（F-9/F-10）"≠"X 之后都没问题"，5_intakeoutput 一旦能产出产物，立刻撞出这条潜伏的循环。F-11 是 F-10 之后的"下一堵被遮蔽的墙"。

---

### 问题 5 ⚠️ 附带：链路跑飞时零错误输出（auto_approval 不打日志）——算不算独立缺陷？

**算，但性质是"加重危害的可观测性缺陷"，不是根因。**

- **事实**：`auto_approval`（`runner.py:145-160`）在有错时只构造 `feedback` 字符串、**不 log**；`validate_node` 调 `interrupt()`、拿到 decision 后也**不 log**。`run_session`（`runner.py:59-76`）的 `on_event` 默认 None（`run_full_pipeline.py:343` 传了一个只 log `[node=] keys=` 的回调，但那不打印 validation_errors 内容）。所以循环跑飞时，stdout 只有 intake/zone/material/schedule 的正常 INFO 在每 ~16 秒重复，**看不到"被拒 / 115 条错 / errors 被清空"任何痕迹**——这正是 §1 orchestrator 瞎了 100 分钟的直接原因。
- **是否独立缺陷**：**是，独立的可观测性缺陷**。它与根因（vertex-drift 时机错位 + intake 短路 + MAX_RETRIES=0 三者叠加）正交：即使根因修了，`(a) auto_approval 拒绝时不打日志` + `(b) 图执行没有"已跑 N 轮仍无进展"的护栏（循环计数器/熔断）`这两条不补，未来任何同类死循环仍会静默烧钱直到账单惊到人。
- **建议（不动手）**：(a) `auto_approval` 拒绝时 `logger.warning` 出 errors 条数+前几条；(b) `run_session` 加一个"同一 thread 连续 N 次 interrupt 且 state 无关键字段（如 surfaces_count）增长即 raise/熔断"的护栏。这两条与选项 B/C 正交，应**成对做**。

---

## 4. §4 orchestrator 猜测的验证（方向成立，归因需精化）

§4 猜：「6 月那份 coordinate_mode 不同（今天日志写 world_legacy，5_intakeoutput 另写了 contract/snapshot 两个侧车），所以没踩这条。完全没验证。」

**验证结果：方向成立，但"coordinate_mode"归因应精化为"contract source 类型"。**

直接证据：
- **今晚 contract**（`run_2026-08-06_wall3_a_retest/5_intakeoutput/output_coordinate_contract.json`）：`mode=world_legacy`、`source.binding_kind=accepted_correction`、`geometry_snapshot_sha256=01cf9f87...`（非 None）。snapshot = **115 records**（100 BuildingSurface:Detailed + 15 FenestrationSurface:Detailed）。
- **probe_b**（08-05 跑通的 6 月 legacy intake）：其 export audit `output_coordinate_audit.json` 的 **`snapshot_sha256: None`**（跑时无 snapshot）、`offenders: 0`、跑到 EP（有完整 `eplusout.*`）。其 `config_counts` = `BuildingSurface:Detailed 100 / FenestrationSurface:Detailed 15 / Zone 14`——**与今晚 snapshot 同一栋楼**，唯一差别就是 snapshot 有无。
- **代码路径**（`output_coordinates.py:651-665`）：vertex-drift 只在 `context.raw_snapshot_bytes is not None` 时比对；standalone contract 禁止带 snapshot（`:195-197`），accepted_correction 强制带（`:190-192`）。

**精化后的归因**：分歧点不是"coordinate_mode（world_legacy vs 其它）"，而是 **contract source 类型**——`accepted_correction` 强制带 snapshot ⇒ foundations 阶段 vertex-drift 必报 115 条 ⇒ 死循环；`legacy standalone` 禁止带 snapshot ⇒ vertex-drift 跳过 ⇒ 不死循环。probe_b 走的是后者。

> §4 自己注明"完全没验证、可推翻"。本席的验证是**支持 + 精化**，不是推翻，故**未触发 §9 停下上报**。

---

## 5. 证据附录（每条可独立重跑）

### 5.1 零 LLM 确定性探针（核心证据）
脚本：`/tmp/f11_no_llm_probe.py`（本席所写，一次性）。重跑：
```bash
cd /workspaces/EnergyPlus-Agent-dev && timeout 90 python3 /tmp/f11_no_llm_probe.py
```
输出要点（本席实测）：
- `[load] contract.mode=world_legacy source.binding_kind=accepted_correction snapshot_sha=set raw_snapshot_bytes=set`
- STEP 1：`errors returned: 115` · `by code: {'VERTEX_FRAME_DRIFT': 115}`
- STEP 2：`auto_approval returned keys: ['approved','feedback']` · `has 'errors' key? False` · `carried=[] (len=0)`
- STEP 3：`short-circuit TAKEN = True`
- STEP 4：`errors on iteration 2: 115 (identical to iteration 1: True)`

### 5.2 关键代码行号（基点 `9b6a7ff`）
| 断言 | 位置 |
|---|---|
| foundations 路由 | `src/agent/graph.py:50-52` `_cross_ref_router` |
| MAX_RETRIES=0 | `src/agent/_share.py:7`（+ `state.py:243` 默认值） |
| validate 重试分支（恒 False） | `src/agent/nodes/validate.py:41` |
| validate rejected→intake + 清空 errors | `src/agent/nodes/validate.py:67-77`（`:71` `decision.get("errors", [])`） |
| auto_approval 有错必拒、无 errors 键 | `src/agent/runner.py:155-160` |
| intake 短路条件 | `src/agent/nodes/intake.py:52` |
| cross_ref_foundations 调 contract 门 | `src/agent/nodes/cross_ref.py:26-34`（docstring `:5-9` 述意图） |
| vertex-drift「missing from ConfigState」 | `src/validator/output_coordinates.py:794-804`（`_vertex_drift_issues`） |
| vertex-drift 仅在 snapshot 非空时跑 | `src/validator/output_coordinates.py:651-665` |
| accepted_correction 强制 snapshot / standalone 禁止 | `src/agent/output_coordinates.py:190-197` |

### 5.3 历史考据命令（可重跑）
```bash
git log --oneline -S "_output_coordinate_errors" -- src/agent/nodes/cross_ref.py   # → ccb396e 7.14
git log -p -S "MAX_RETRIES: Final" -- src/agent/_share.py | head -20              # → 299149c 4.20, 值=0
git show ccb396e --format='%B' -s | head -3                                       # 设计意图
```

### 5.4 snapshot 有无对照（坐实"今晚首次"+§4）
```bash
ls case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/5_intakeoutput/        # 无 contract/snapshot
ls case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/5_intakeoutput/ # 无 contract/snapshot
ls case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/5_intakeoutput/  # 有 contract+snapshot
python3 -c "import json;d=json.load(open('case_tests/e2e_tests/sm21_anchor/probe_b_2026-08-05_legacy_intake/output_coordinate_audit.json'));print('snapshot_sha256=',d['snapshot_sha256'])"  # → None
```

---

## 6. 边界遵守自检（收尾）

- ⛔ 零 `src/` `scripts/` `skills/` `tests/` 改动 · ⛔ 零 commit/push · ⛔ 零 `git add -A` · ⛔ 未碰 `case_tests/` 任何文件（只读）。
- ✅ 一次性脚本仅 `/tmp/f11_no_llm_probe.py`。
- ✅ 全程零 DeepSeek 调用（未跑 §2 复现命令、未跑 §3 spy 探针；改用确定性探针等价复现）。
- ✅ 未触发 §9 停下上报——本单 7 条代码事实逐条独立复核全部属实，§6 框架可完整回答；唯一精化是 §4 自述"未验证"的归因措辞（验证后支持+精化，非推翻）。

---

## 7. 收尾观察：基点漂移（不影响结论，仅备查）

本席开工自检时 HEAD = `9b6a7ff`（调查单 §0 期望基点）。调查进行中，orchestrator 做了 commit `8dd4167 08.06_f11_downstream_infinite_loop_registered`，HEAD 漂移到 `8dd4167`。

- `git show 8dd4167 --stat`：仅改 `AI_agent/plan.md`（+4/-1，注册 F-11 待办）+ 调查单本身（首次 `git add`，+108）。
- **零 `src/`/`scripts/`/`skills/`/`tests/` 改动** ⇒ 本席调查所依据的全部代码在 `9b6a7ff`↔`8dd4167` 间逐字节相同，§5 的行号、探针结果、代码逻辑**全部仍成立**。
- 本席日志标注"基点 `9b6a7ff`"准确：所有证据在 HEAD=`9b6a7ff` 时取得；`8dd4167` 未动代码。未来重跑 `/tmp/f11_no_llm_probe.py` 在 `8dd4167` 上结果不变。
- 此观察仅为完整性记录；非本席造成、亦非本席处理（orchestrator 的 git 操作）。
