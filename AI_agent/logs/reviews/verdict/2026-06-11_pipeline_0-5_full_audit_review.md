# Review — 0–5 管线完整体检（找硬伤）

- **执行**：2026-06-11，Fable 5（交叉模型审阅）
- **对应 request**：[2026-06-10_pipeline_0-5_full_audit_request.md](../request/2026-06-10_pipeline_0-5_full_audit_request.md)
- **范围**：sm21（对照基线）+ sm20（3 层首验）端到端实跑 + 0–5 全链代码审查 + 合成最小复现取证
- **环境**：容器 EP 25.1.0，DeepSeek 走全局 `src/configs/llm.yaml`（两案例均无 per-case llm.yaml），测试套件 69 绿

## Verdict

**两案例端到端一把跑通，验收标准 1 全部达成**：sm21 与 sm20 各自 InterZone 门 `pair_issues=0`、schedule 门 0 issue、EP `Completed Successfully` 0 severe。sm20（3 层）是 0–5 重构后**新架构首验，一次通过**；旧矢量 schema 与当前管线完全兼容；下游誊写保真度 100%（全部面与内核逐顶点一致，仅环起点旋转，零法向翻转）。

**但代码审查 + 合成复现确认了 3 High / 3 Medium / 3 Low 硬伤**。三个 High 全部是"契约只写在 prose、代码零守卫"或"失败信号被吞"类——本次两个干净案例没踩中，但每一个都有确定性的静默出错路径（复现脚本全部当场咬中，门全部放行）。这与项目自己立的哲学（schedules.py："prose compliance is not guaranteed, so the invariant is enforced in code"）直接冲突，建议修完再建 test_baseline。

---

## 1. 端到端实证结果

| 项 | sm21（基线） | sm20（3 层重点） |
|---|---|---|
| 1_correction | 1 次成功（attempt 1/3），25 857 completion tokens | 1 次成功（attempt 1/3），9 277 tokens |
| 几何 | 14 区 / 100 面 / **15 窗** 15/15 挂载 | 19 区 / 135 面 / **16 窗** 16/16 挂载 |
| 内核门（advisory） | 0 issue，0 notes | 0 issue，0 notes |
| 下游 InterZone 门 | `pair_issues=0`（31 对互逆） | `pair_issues=0`（45 对互逆） |
| schedule 门 | 0 issue | 0 issue |
| EP | Completed Successfully，**0 severe**，6 warnings | Completed Successfully，**0 severe**，25 warnings |
| warnings | 全无害（无 Timestep/无 design days/无热质量※/坐标系提示/地温默认） | 全无害（同类 + 19 条活动量 schedule 区间提示※） |

※ 两条标星是 4_mep capability 信号，已记到[配套文档](../../architecture/pipeline_0-5_capability_upgrade_suggestions.md)，见 §4。

产物：`<case>/output_fable_audit/`（`pipeline_out/{1_correction,2_modelling,3_split_pairing,4_mep,5_intakeoutput}/` + `temp_*.idf` + `eplusout.*`）。

**sm20 三个专项确认**：

- **3 层 z-stack 合成正确**（request §5.3#3）：F1 0–3.6 / F2 3.6–7.2 / F3 7.2–12.0 连续无缝；F2 窗 z[4.4,6.2]、F3 窗 z[8.2,10.8] 均落在各自层内；cell id 全局唯一（`F1_01…F3_04`）。
- **旧 0_reading schema 兼容**（request §3 行 0_reading）：sm20 矢量与 sm21 的 top-level keys / stroke keys / pen 词汇逐项一致，被 1_correction 正确消化，16 个 window stroke → 16 个窗实体。该 audit 点关闭。
- **切配覆盖完整性独立验证**（request §5.3#1 x/y 向）：手算交叠片数 = F1→F2 10 片 + F2→F3 9 片 = 19 个 interzone floor，与产物完全一致（Floor 26 = 7 Ground + 19 Surface；Ceiling 19；Roof 4 = F3 四 cell；**Floor-Outdoors = 0**；45 对 = 19 横向 + 26 墙对）。本案例**无覆盖洞**。

**誊写保真度**：装配 IDF 的全部 135/100 个面与 `building_geometry.json` 逐顶点比对——0 丢失、0 OBC/配对不一致、顶点全部为同环旋转（0 反射=0 法向翻转）；31 窗 parent 全对。fork (a)"下游忠实誊写"在两案例上成立。

---

## 2. 硬伤清单

> 复现脚本核心输入内嵌在各条目（运行方式：构造 `CorrectedGeometry` → `apply_deterministic_core` → `build_geometry` → `building_to_idf` → `validate_interzone_surface_pairs`）。

### High

#### H1 跨层重复 cell id 无确定性守卫 → 静默几何粉碎（复现 ✓，门放行）

**根因**：A0_contract.md §自检表把 `id_uniqueness` 列为 LLM 自检项，但代码侧零强制。三处 dict 以 cell id 为 key、重复时 last-wins：

- [split_pairing.py:46](../../../src/agent/geometry/split_pairing.py) `zv_by_id = {zv.cell_id: zv ...}` —— 配对查错楼层的体块；
- [build.py:45](../../../src/agent/geometry/build.py) `zv_by_cell` —— 窗挂错楼层的 zone;
- [deterministic.py:180](../../../src/agent/correction/deterministic.py) `cell_by_id` —— 窗被钳进错误楼层的 z 区间。

另外 [modelling.py `build_zone_volumes`](../../../src/agent/geometry/modelling.py) 用 `_safe(c.id)` 直接作 zone 名不查重（`"Room 1"` 与 `"Room_1"` 还会撞名），[to_idf.py:23](../../../src/agent/geometry/to_idf.py) `dict.fromkeys(bg.zones)` 把撞名静默去重成一个 ZONE。

**复现**：两层各有一个 `id="Corridor"` 的 cell（2+2 布局）→ 4 个体块只产出 3 个 zone、23 面（应 24）；F1 Corridor 的天花消失、F2 Corridor 的地板变 `Outdoors`、两层 Corridor 面合并进同一 zone——**InterZone 门 0 issue，notes 空**，EP 可正常跑 → 错建筑静默通过。配套复现：F1 的窗 `room="Room"`（两层同名）被钳成 z=[3.0,3.0] 零高窗（用了 F2 的层 z 区间）。

**修法**：`build_zone_volumes` 入口对 `cell_id` 与 `_safe` 后 zone 名做全局唯一性硬校验，冲突即 raise（kernel 硬错路径已有：`materialize_kernel_geometry` → `run_pipeline` raise）；`apply_deterministic_core` 的 `cell_by_id` 构建时同步检测。约 10 行,一处管全链。

#### H2 z-stack 连续性无守卫 → 楼层间缝隙静默建成"楼中天台"（复现 ✓，门放行）

**根因**：确定性核只吸附 x/y 轴（[deterministic.py](../../../src/agent/correction/deterministic.py) 注释明示 "structural x/y"），`z_floor`/`ceiling_height` 从不吸附也不校验；切配的跨层配对条件是 `|lower.zt − upper.zf| ≤ _Z_TOL (0.02)`（[split_pairing.py:96-99,118-121](../../../src/agent/geometry/split_pairing.py)），一旦超差,整个接缝退化为下层全 Roof + 上层 Floor(Outdoors)。A0 的 `z_stack_consistent` 同样 prose-only。

**复现**：F1（0–3.0）+ F2（z_floor=3.3，缝 0.3 m）→ Roof×2、Floor-Outdoors×1、interzone 对 0；**notes 空、门 0 issue**、EP 正常跑——建筑中部凭空多出一个室外层,错物理静默通过。

**定性**：这就是 request §5.3#1 担心的"覆盖洞盲区"**最容易踩的实现路径**——x/y 向有栅格吸附兜着（sm20 实证 0 洞），z 向完全裸奔，而 1_correction 输出 z 抖动（如 3.05 vs 3.0）是已知 LLM 行为模式。**不必等 shapely 全量覆盖检查**,先把 z 向这一刀挡住。

**修法**（确定性、低成本）：① 核里把相邻层 `|upper.z_floor − lower.zt| ≤ 容差`（建议复用 `gap_close_threshold_m`）的 z_floor 直接吸到 lower.zt 并记 correction；② 超出容差但 footprint 有交叠的,产出 unsupported / kernel 硬 note 升级为 gate issue。两层防线约 20 行。

#### H3 EP 退出码被忽略 → EP fatal/段错被报告为 "Simulation run successfully"

**根因**：[runner.py:147-154](../../../src/runner/runner.py) `run_idf` 对非零退出码返回 `False`,但全仓库唯一调用点 [workflow.py:257](../../../src/mcp/tools/workflow.py) 不接收返回值,无条件返回 `success=True, "Simulation run successfully."`；[simulate.py](../../../src/agent/nodes/simulate.py) 原样转发。全 `src/` 无任何代码读 `eplusout.end`/`.err`。

**后果**：EP 段错（exit 139）/fatal 时,pipeline 日志结尾仍是 `final: [simulate] Simulation run successfully`。2026-06-10 之前"EP 段错被长期误判为环境问题"与此直接相关——失败信号在工具层就被吞了,验收只能靠人手翻 `eplusout.end`。两道门建得很硬,最后一公里却是开环。

**修法**：接住 `run_idf` 返回值;失败时返回 `success=False` 并附 `eplusout.err` 尾部/退出码;成功时顺手解析 `eplusout.end` 的 `N Warning; M Severe` 进 `ToolResponse.data`,让"EP Completed Successfully 0 severe"验收可自动断言（也直接服务 test_baseline 建设）。

### Medium

#### M1 内核窗丢失只记 note，无完整性核对（复现 ✓）

`attach_windows`（[modelling.py:292-314](../../../src/agent/geometry/modelling.py)）对 `room=None`（schema 合法！[schema.py:37](../../../src/agent/correction/schema.py)）、room 查不到、找不到宿主墙三种情况一律 skip + note,管线继续。1_correction 级的 0 窗自检（`fd3d4bf`）只防"全丢",防不了 kernel 级逐个丢——若 15 窗挂上 14 个,产物照样下行,EP 干净通过。本次实跑 31/31 全挂上未咬,但机制是开的。
**修法**：`build_geometry` 末尾核对 `len(geom.windows)` vs `len(bg.windows)`,有差额时把逐窗丢失原因从 note 升级为 kernel 硬 issue（与 H1 同一 raise 路径）；并把 `Window.room` 改为必填（或 kernel 按 floor+span 兜底定位）。

#### M2 窗钳制可制造非法窗（满墙/零高），门对 fenestration 全盲（复现 ✓）

确定性核 `window_clamp_to_parent`（[deterministic.py:184-189](../../../src/agent/correction/deterministic.py)）把出界窗钳到 cell/层边界——z 超层高的窗被钳成 `[zf, zt]` 满墙窗（复现：span[0,10]×z[0,3] 与父墙完全重合,EP 必 severe: subsurface ≥ base surface）；H1 复现里钳出 z=[3.0,3.0] 零面积窗。InterZone 门只查 `BuildingSurface:Detailed`,对 `FenestrationSurface` 零检查,这类非法窗一路放行到 EP。
**修法**：钳制后校验窗最小尺寸 + 严格落在墙内（按 A0 已有的窗 10mm 分级留边）,不满足记 `unsupported` 显式丢弃,而不是产出非法几何;中期给门加 fenestration 检查（在父墙平面内/面积<父墙/同墙窗互不重叠）。

#### M3 schedule 门通过时零日志（可观测性）

[workflow.py `_check_schedules`](../../../src/mcp/tools/workflow.py) 仅在有 issue 时输出;InterZone 门则无条件输出 audit 行。本次两案例日志中 schedule 门"通过"与"没跑"不可区分（审计时只能靠读代码确认它在调用链上）。
**修法**：加一行 `INFO`（n 个 Schedule:Compact checked, 0 issue）,与 interzone audit 行对称。

### Low

#### L1 `_section()` 兜底吞所有异常
[pipeline.py:123-128](../../../src/agent/pipeline.py)：`intake_mep` 段写坏（YAML 语法/字段错）会静默 fallback 到 `intake_correction`,配置错误被掩盖。改为只捕"段不存在"类异常。

#### L2 `_call_json_llm` 传输层异常不消耗重试
[pipeline.py:177](../../../src/agent/pipeline.py) `client.chat.completions.create` 在 try 块外——DeepSeek 5xx/超时（SDK 自身 2 次重试耗尽后）直接中止全部 attempts,而 `attempts=3` 本意是兜稳定性。把 create 调用移进 try,传输异常同样记一次 attempt。

#### L3 facade 词汇无约束
`Window.facade` 是自由 str（schema 无 enum）；`_facade_axis`（[modelling.py:210](../../../src/agent/geometry/modelling.py)）对未知值（错拼/`"Northeast"`）静默按 N/S 处理,deterministic 核同样。改 `Literal["North","South","East","West"]`（大小写归一）或 kernel 校验 + unsupported。

---

## 3. 已知风险点核对（request §5.3）

1. **InterZone 覆盖洞盲区**：x/y 向在 sm20 3 层上**没有暴露**（§1 手算独立验证 0 洞——栅格吸附 + 确定性切配在矩形 regime 下结构性地保证了覆盖）；但 **z 向路径确认真咬**（H2,复现门放行）。结论：盲区真实存在,最危险子类可用 ~20 行确定性 z 守卫先挡住,shapely 全量覆盖检查仍按原计划随 B5。
2. **窗挂错宿主墙 / `_find_parent_wall` skip**：实跑 31/31 全部正确挂载、0 skip;跨层切配只切楼板不切墙,不会制造"外墙碎片让窗跨段"。但 skip 机制本身静默（M1）,且钳制可制造非法窗（M2）。
3. **3 层 z-stack 合成**：sm20 实证正确且一发即中（§1）。1_correction 稳定性数据点：两案例共 4 次 LLM 调用（2 correction + 2 mep）全部 attempt 1/3 一次成功,重试机制本次未触发。

---

## 4. 顺手 capability 发现（已记入[配套文档](../../architecture/pipeline_0-5_capability_upgrade_suggestions.md)，不在本 audit 修）

- **4_mep 材料真实性跨 draw 波动**：sm21 本次全配 no-mass 材料 → EP "building has no thermal mass" warning；sm20 同 prompt 无此问题。
- **OFFICE_ACTIVITY 活动量 schedule 数值**超 70–1000 W/person 典型区间（sm20,19 条 warning）。
- **SimulationControl 默认做 design day 仿真但 4_mep 不产 design days**;地温默认 18 °C——authoring 默认值可补齐。
- 1_correction"3 层 z-stack 待验"一条已可标验证通过。

## 5. 验收对照

| request §5 标准 | 结果 |
|---|---|
| 1. sm21+sm20 端到端（两门 0 issue + EP 0 severe） | ✅ 双案例达成（§1） |
| 2. 硬伤清单分级 + 证据 + 修法 | ✅ 3 High / 3 Medium / 3 Low（§2，关键项含合成复现） |
| 3. 三个已知风险点确认 | ✅ 逐项核对（§3）；覆盖洞的 z 向子类确认真咬并给出低成本修法 |

**建议处置顺序**：H1+H2+M1（同在 kernel 入口,一个 PR 可打包,~50 行 + 测试）→ H3（workflow/runner,独立 PR）→ M2/M3/L1-L3 随手。修完再落 test_baseline,baseline 的"EP 0 severe"断言依赖 H3。

---

## 6. 处置记录（2026-06-11 当日，Fable 5 执行，用户指示"全部修"）

全部 findings 已修复并验证,分三块落地（备份齐全,见 [downstream_agent_changes.md 2026-06-11 条](../../downstream_agent_changes.md)）:

| 块 | findings | 落点 |
|---|---|---|
| PR1 内核守卫 | H1 + H2 + M1 + M2 + L3 + **H4(新)** | schema.py / deterministic.py / modelling.py / build.py + tests/test_kernel_guards.py(16 测) |
| PR2 EP 闭环 | H3 + M3 | runner.py(`read_ep_end`) / workflow.py + tests/test_ep_end_gate.py(7 测) |
| PR3 correction 稳健性 | L1 + L2 + draw 级复合校验 | pipeline.py(`_make_correction_validator`) + test_correction_stability.py(16 测) |

**H4（修复过程中新发现的硬伤,已修）**：`_find_parent_wall` 原实现只按"常数轴 + 跨度覆盖"选墙、不校验朝向——全进深房间（南北两侧都有外墙）的南窗会静默挂到**北墙**（取决于面列表顺序）,窗被搬到对面立面,InterZone 门与 EP 全程无感。sm20/sm21 未踩中纯属偶然（所有带窗房间恰好单侧采光）。修复:按窗 facade 推外法向,用 Newell 法向点积 ≥ 0.9 过滤候选墙;新增双侧采光定向测试。

**防线分层**（同一不变量三道防线,层层兜底）:
1. **draw 级（重试）**:`run_correction` 的 validate 回调现做 schema(含 facade enum)/0 窗/重复 cell id/z-stack 断裂复合校验,坏 draw 触发重抽(attempts=3)而非死管线;
2. **确定性核（修复+显式丢弃）**:小 z 缝(≤0.3m)自动吸附记 correction;非法窗(退化/满墙)显式丢弃记 unsupported;
3. **内核（raise backstop）**:重复 id/撞 zone 名/断 z-stack(>0.02m)/丢窗 一律 raise,绝不静默产出坏几何。

**验证**:
- 全套 pytest **99 绿**（69 原有 + 30 新增）;
- §2 全部复现脚本反向验证 PASS（R1 core+kernel 双 raise / R2 0.3m 吸附+0.5m raise / R3 raise / R5 显式丢弃 / facade 非法 schema 拒绝）;
- **sm20 e2e 复跑回归**（output_fable_audit_postfix）:结果与修复前完全一致（19 区/135 面/16 窗、两门 0 issue、EP Completed Successfully 0 severe 25 warnings、correction 一发即中）,且 M3 audit 行（`6 Schedule:Compact checked, 0 issue(s)`）与 H3 新消息（`Simulation completed: 0 severe, 25 warnings`）均已生效。

**本 review 全部 findings closeable。**遗留(低优先,记录不阻塞): InterZone 门的 fenestration 检查(M2 的"中期"部分,核侧已兜)与 x/y 向 shapely 全量覆盖检查仍按原计划随 B5。
