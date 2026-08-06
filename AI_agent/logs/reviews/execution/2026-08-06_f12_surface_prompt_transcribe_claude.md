# 执行日志 · F-12：下游 surface 节点改为「逐字照抄内核顶点」

- **日期**：2026-08-06
- **席位**：Claude 侧 Sonnet 子代理（施工档）
- **施工单**：[`request/2026-08-06_f12_surface_prompt_transcribe_dispatch_claude.md`](../request/2026-08-06_f12_surface_prompt_transcribe_dispatch_claude.md)
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD `dfbd62a`（开工自检通过：4 个已知 case_tests 未跟踪目录 + 本单本身，符合预期）

---

## 0. 开工自检

```
git log --oneline -1     # dfbd62a — 符合预期
git status --short       # 4 个已知 case_tests 未跟踪目录 + 本单，符合预期
pwd                      # /workspaces/EnergyPlus-Agent-dev — 符合预期
```
施工单陈述的行号/内容与实际代码逐一核对**全部对得上**（`surface.py` :18-38 重算节 / :40-53 worked example / :63 workflow 句 / :73 CCW 句；`fenestration.py` :42-43 WWR 句；`surface_specs`/`fenestration_specs` 确实已给完整绝对世界坐标顶点串，`_fmt_verts` 逐字确认）。**本轮无需停下上报。**

---

## 1. 改了什么 / 为什么这么改

### 1.1 `src/agent/nodes/surface.py`（主项）

删除整节「## CRITICAL: per-floor z values come from zone_specs」（原 :18-38，命令 LLM 用 `zone_specs.z_floor`/`ceiling_height` 自己重算墙顶点 Z）+ 自相矛盾的 worked example（原 :40-53，注释里自己先写错 `# ← but actually start with bottom; see below` 再更正，是噪声源）。

换成「## CRITICAL: transcribe vertices verbatim from surface_specs — do NOT recompute them」：
- 明确 `surface_specs` 已给出每一面的完整绝对世界坐标顶点串、已是 CCW-from-outside 顺序，是权威几何；
- 逐字转录，**含顺序** —— 不许重算/重排/四舍五入/补齐/去重；
- `zone_specs` 只用于 zone 名称/邻接/构造语义，明确**不作为顶点来源**。

同步改了三处会跟新指令打架的旧句：
- Workflow 步骤 3（原「using zone_specs' per-zone z_floor + ceiling_height for vertex z」）→ 改成「transcribing surface_specs' own vertex list for that surface exactly (same coordinates, same order)」；
- Rules 里「Order counter-clockwise when viewed from OUTSIDE the zone.」（暗示要模型自己判断朝向）→ 改成「surface_specs' vertex order is already CCW-from-outside — transcribe it as given; do NOT re-derive or re-sort the vertex order yourself.」；
- 装配处（`surface_agent` 函数体，`state.intake_output.zone_specs`/`surface_specs` 拼接的代码注释）由「bundle 是为了读 z_floor」改为如实说明现状（zone_specs 只给名称/邻接，顶点来源是 surface_specs），并记了一句 2026-08-06 (F-12) 备注解释为何改。

§Rules 其余约束（名字 verbatim、boundary condition、surface_type、>=3 顶点等）**原样保留未动**。

### 1.2 `src/agent/nodes/fenestration.py`（顺带项）

- worked example 由「手算一个居中窗（给出具体算术）」改为强调 `fenestration_specs` 已给完整顶点、逐字转录、不许用窗墙比（WWR）推导；
- 删除 Rules 里「Typical window-to-wall ratio: 0.3-0.4 on facade walls; derive vertex coordinates from the parent wall's corners and the WWR.」这条命令 LLM 用 WWR 推导坐标的指令，替换为「fenestration_specs' own vertices already satisfy [coplanar] — transcribe them as given; do NOT re-derive or re-sort the vertex order yourself.」。

### 1.3 备份 + 变更登记

- 改前分别 `cp` 到 `backup/src_history/2026-08-06_f12_surface_prompt_transcribe/{surface,fenestration}.py.orig`。
- 在 [`AI_agent/logs/downstream_agent_changes.md`](../../logs/downstream_agent_changes.md) 记了一条完整变更说明（背景/改动/影响范围/协作者建议）。

---

## 2. 锁

新文件 [`tests/test_f12_surface_prompt_transcribe.py`](../../../tests/test_f12_surface_prompt_transcribe.py)，5 条断言，全部落在**可指认的具体正则/字串**上（不是「长度变了/不是 None/含某泛词」）：

1. `test_surface_prompt_instructs_verbatim_transcription_from_surface_specs`：`SURFACE_SYSTEM_PROMPT` 必须含「transcribe...verbatim...surface_specs」+「do not use zone_specs...z_floor...ceiling_height...compute」两条正面指令。
2. `test_surface_prompt_does_not_command_z_floor_arithmetic`：**钉死旧缺陷原文的三个具体正则**（`bottom\s+z\s*=\s*z_floor` / `top\s+z\s*=\s*z_floor\s*\+\s*ceiling_height` / `using\s+zone_specs...z_floor...ceiling_height...for\s+vertex\s+z`）必须**不在**。
3. `test_surface_prompt_ccw_instruction_says_already_ccw_not_rederive`：必须含「already CCW-from-outside」，且旧的裸「Order counter-clockwise when viewed from OUTSIDE the zone.」整行必须不在。
4. `test_fenestration_prompt_instructs_verbatim_transcription`：`FENESTRATION_SYSTEM_PROMPT` 必须含「transcribe...verbatim」。
5. `test_fenestration_prompt_does_not_command_wwr_derivation`：钉死旧缺陷原文「derive vertex coordinates from the parent wall...corners...WWR」必须不在；另加一条防「WWR 直接接 derive」链式表述的负锁。

设计要点：负锁的正则专门验证过**不会误伤新提示词里合法的「do NOT derive ... WWR」这类否定句**（第 5 条锁最初一版用 `(?<!not )derive...WWR` 撞上了 "re-derive" 假阳性，改成钉住旧缺陷的具体短语结构后消除）。

---

## 3. neuter 自验（本项目硬纪律）

**做法**：把两个提示词**文件本体**整个替换回 `backup/.../surface.py.orig` / `fenestration.py.orig`（即把病灶恢复成缺陷形态本身，不是在函数内部包一层），再跑锁；确认后原样恢复回修复版（`diff` 逐字节核对与替换前完全一致）。

**结果**：**5 条全部由绿转红**，红的位置精确对应各自锁定的旧缺陷模式：

```
FAILED test_surface_prompt_does_not_command_z_floor_arithmetic
  AssertionError: surface prompt must not command bottom-z = z_floor arithmetic
FAILED test_surface_prompt_instructs_verbatim_transcription_from_surface_specs
  AssertionError: prompt must instruct verbatim transcription from surface_specs
FAILED test_fenestration_prompt_instructs_verbatim_transcription
  AssertionError: fenestration prompt must instruct verbatim vertex transcription
FAILED test_fenestration_prompt_does_not_command_wwr_derivation
  AssertionError: fenestration prompt must not command deriving vertex coords from WWR + parent wall corners
FAILED test_surface_prompt_ccw_instruction_says_already_ccw_not_rederive
  AssertionError: prompt must state surface_specs' vertex order is already CCW-from-outside
============================== 5 failed in 9.40s ===============================
```

恢复后 `diff` 确认字节级一致，5 条锁全部转回绿（`5 passed in 9.02s`）。**判别问法「把调用点/病灶本体改回缺陷形态，锁红不红」= 是** —— 这不是函数内部 neuter，是把两个提示词常量整个换回旧文件，接线与机制一起覆盖。

---

## 4. 真链路验收（主验收）

### 4.1 命令与快照确认

```bash
python scripts/run_full_pipeline.py sm21_anchor \
  --base-dir case_tests/e2e_tests \
  --intake-from run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json \
  --output-subdir run_2026-08-06_wall3_a_retest/EP_f12_verify
```
（施工单原始命令里的 `--intake-from` 路径写法有出入 —— 它是相对 `<case>/` 解析的，而 `<case>` 本身必须是 `sm21_anchor`〔`testdata_prompt.json` 在 `sm21_anchor/case_data/` 下,不在 run 目录下〕，故 `--intake-from` 要写成 `run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json`、`case`参数是 `sm21_anchor`。已按 `run_full_pipeline.py` 的 argparse 实际语义调整，非停下上报级问题，顺手修正。）

**开跑前确认冻结快照真的喂进去了**（否则 drift 门会因为拿不到快照而整段跳过，见 `output_coordinates.py:669-670`）：`load_intake_bundle` 走的是 `resolve_run_dir_for_intake` → 找到 `run_2026-08-06_wall3_a_retest/_run/run_manifest.json` → `5_intakeoutput` 的 accepted attempt `artifact_contract == "assembly_e4_v1"` → 从 `5_intakeoutput/attempts/001/` 读 `output_coordinate_contract.json` + `output_coordinate_snapshot.json` 并**逐哈希校验**（`hash_file(path) != record.artifact_hashes.get(key)` 任一不符即 raise）。日志确认走的是这条路径，快照真实喂入。

日志：[`experiments/2026-08-06_f12_transcribe_verify/run_full_pipeline_stdout.log`](../../logs/experiments/2026-08-06_f12_transcribe_verify/run_full_pipeline_stdout.log)（513 行，DeepSeek v4-pro 下游 9 subagent 真跑，退出码 0）。

### 4.2 逐条验收结果

**⭐ 关键澄清（本轮最重要的发现，直接改写了§5验收条件的可满足性）**：本项目对「顶点没漂移」实际有**两层完全独立的比对**，施工单 §5 的验收条件把它们当一件事写，但真实链路里是两件事：

| 层 | 检查函数 | 比对对象 | 触发位置 |
|---|---|---|---|
| **A. ConfigState 层** | `_vertex_drift_issues`（`output_coordinates.py:816`） | LLM `create_surface`/`create_fenestration` 工具调用时提交的原始顶点（未经任何后处理） | `cross_ref_complete_node` / `validate_node`（**就是历史上触发 `InterruptLoopBreakerError` 的那道门**） |
| **B. 实时 IDF 层** | `_live_idf_vertex_drift_issues`（`output_coordinates.py:781`） | **`ConverterManager.convert_all()` 之后**、真正写进 IDF 文件的顶点 | `run_simulation`/`export_idf_only` 内部的 "Pre-EnergyPlus gate" |

1. **`VERTEX_FRAME_DRIFT` 归零？**
   - **A 层（施工单 §1 描述的 44 条、InterruptLoopBreakerError 那道门）：✅ 归零，且是本单要修的确切目标。**
     证据：全链路 `intake → material → zone → schedule → cross_ref_foundations → construction → surface → fenestration → hvac → lights → people → cross_ref_complete → validate → simulate` **单程走完，零重试、零 `validate interrupt AUTO-REJECTED` 日志行**（`grep -c "AUTO-REJECTED"` = 0）。`validate_node` 的路由逻辑是「`errors` 非空且 `retry_count < max_retries` 才回 intake 重试；否则落 `interrupt()` 交 `auto_approval`，`auto_approval` 见 `errors` 非空必打印 WARNING 并拒绝」——**日志零 WARNING 行 + 单程直达 simulate，逻辑上唯一可能是 `errors == []`**，即 A 层的 `_output_coordinate_errors(state)`（含 `include_vertex_drift=True`）对全部 115 个对象（100 面 + 15 窗）返回空列表。**这正是施工单 §1 报的「validate 连拦 4 轮触发 InterruptLoopBreakerError」问题，本次单程通过、问题解决。**
   - **B 层（Pre-EnergyPlus gate，本单未曾预期会独立测到的一层）：❌ 未归零，104 条**（`grep -c VERTEX_FRAME_DRIFT` 对 `_live_idf_vertex_drift_issues` 复算结果 = 104；日志原句：`[simulate] Pre-EnergyPlus gate failed: 104 issue(s) (0 interzone, 0 schedule, 104 output-coordinate). Simulation not started.`）。**根因见 §5「撞到的新墙」，不是提示词能修的**（详下）。

2. **窗仍然零漂移？**
   - **A 层：✅ 是**（0/115 里窗占 15、A 层整体 0，故窗也是 0）。
   - **B 层：❌ 否**（15/15 窗在 B 层显示漂移，但**根因与墙相同、与本单改动无关**——见 §5，纯环形起点旋转，非坐标错，且这条路径**在 F-12 之前从未被真实数据测过**，故不构成"改坏了此前是 0 的东西"，是第一次测到）。

3. **不再触发 `InterruptLoopBreakerError`，链路走过 validate？✅ 是**（日志 `[node=validate]` 之后直接 `[node=simulate]`，零 interrupt/retry 循环）。

4. **跑到 EnergyPlus 且 `0 Severe`？❌ 否**。`run_simulation` 在 B 层 Pre-EnergyPlus gate 处被拦（104 issue），"Simulation not started"，EnergyPlus 从未被调用（`EP_f12_verify/` 下只有 `.idf`/`.yaml`，无 `eplusout.*`）。**按施工单 §5 第 4 条的既有条款处理：这是"更后面撞到的新的墙"，不算我的锅，如实登记（见 §5），不修（越界）。**

5. **全仓零回归：见 §6。**

6. **日志落 `AI_agent/logs/experiments/2026-08-06_f12_transcribe_verify/`**：✅（`run_full_pipeline_stdout.log` + `q1_kernel_vs_idf_reconciliation.py` + 其输出 + `pytest_full_tail.txt`）。

### 4.3 ⭐ Q1 闭合：内核 vs 最终 IDF 分层对账

用与 orchestrator §1 同法（`/tmp` 自写脚本，已拷贝进日志目录，未读 orchestrator 临时脚本），对 B 层（真正落盘 IDF）做逐面分层对账：

```
同名可比 115 面（100 BuildingSurface + 15 FenestrationSurface）
  逐顶点完全一致 : 11   （全部是 Floor 类型：Z08_Floor1/2, Z09_Floor1/2, Z10_Floor, Z11_Floor, Z12_Floor1/2, Z13_Floor1/2, Z14_Floor）
  不一致        : 104
    ├ 循环旋转（同一多边形、绕向不变、法向不变、EP 等价）: 104
    ├ 绕向反了（法向翻转）                              :   0
    └ 坐标真的不同                                      :   0
missing from IDF: 0
```

**今天的形态与施工单 §1 引用的 07-02 历史回溯（100 面同名可比、89 循环旋转 / 0 绕向反 / 0 坐标错）同构**——**今天的定性彻底证实了历史回溯的结论：偏差 100% 是起笔点旋转，0% 坐标错，0% 手性反**。样例（`Z01_W3_Win1`）：
```
snapshot: [(1.0,7.65,2.6), (3.4,7.65,2.6), (3.4,7.65,1.0), (1.0,7.65,1.0)]
actual:   [(3.4,7.65,2.6), (3.4,7.65,1.0), (1.0,7.65,1.0), (1.0,7.65,2.6)]
```
—— 同一四边形，绕向（CCW 方向）完全一致，只是从第 2 个点开始写。

脚本 + 完整输出：[`q1_kernel_vs_idf_reconciliation.py`](../../logs/experiments/2026-08-06_f12_transcribe_verify/q1_kernel_vs_idf_reconciliation.py) / [`q1_kernel_vs_idf_reconciliation_output.txt`](../../logs/experiments/2026-08-06_f12_transcribe_verify/q1_kernel_vs_idf_reconciliation_output.txt)。

---

## 5. ⭐⭐⭐ 撞到的新墙（如实登记，未修，候选编号 F-13）

**现象**：B 层（Pre-EnergyPlus gate，即 `run_simulation`/`export_idf_only` 内部对**真正写入 IDF 的顶点**做的比对）104/115 个对象与内核冻结快照不一致，**但每一条都是纯粹的起笔点循环旋转**（同一多边形、同一绕向、同一顶点集合，仅起始点不同），**0 条真坐标错、0 条绕向反转**。

**定性（不是提示词问题，不属本单范围）**：根因是 `src/validator/data_model.py:1103-1177` 的 `GeometrySchema.validate_points_sorting`（经 `_sort_vertices_clockwise` → `np.roll(points, -top_left_index, axis=0)`）——这是 `SurfaceConverter.validate()` / `FenestrationConverter.validate()`（`src/converters/{surface,fenestration}_converter.py`）在把面/窗写入 IDF **之前**、对**每一个**面/窗**无条件**重新计算的一套「按法向量求出'左上角'顶点、以它为起点、按计算出的绕向重排」逻辑——**不读取、不保留提交时的原始顶点顺序**，对所有 surface_type（含 Floor/Roof/Ceiling/Wall）和所有 FenestrationSurface 一视同仁。

**证据链**：
1. 代码本身：`_sort_vertices_clockwise` 对每个面/窗调用 `sorted(..., key=cmp_to_key(compare_points))` 重新按叉积排序 + `np.roll` 重新选起点，**入参 `surface.vertices` 用完即被整体替换**（`surface.vertices = self._sort_vertices_clockwise(...)`），无论输入顺序是什么。
2. `git blame` 确认该函数自 `299149c`（2026-04-21，项目极早期提交）起未变，**比 E4/output-coordinate 契约（07-14 才写活的 IDF 终门 `_live_idf_vertex_drift_issues`）早了近 3 个月**，是一段"一直存在、但从未被这道门测过"的代码。
3. `run_full_pipeline_stdout.log` 的工具调用摘要文本显示 LLM 自己汇报的 `Z01_W3_Win1` 顶点顺序 `(1.00,7.65,2.60)→(3.40,7.65,2.6...`——**与快照起点一致**；但最终落盘 IDF 里该窗顶点从 `(3.4,7.65,2.6)` 起——**证明 LLM 提交的顺序和最终 IDF 顺序不同，差异发生在 LLM 提交之后的转换层，不是 LLM 没抄对**。
4. B 层 104 条与 A 层 0 条的对比本身即是证据：A 层比对的是「LLM 提交给工具的原始顶点」（0 漂移，本单改动生效），B 层比对的是「转换器重排后的顶点」（104 条纯旋转），两层唯一的差异步骤就是 `GeometrySchema.validate_points_sorting`。

**为什么"窗此前零漂移"这条历史断言在 B 层不成立、但不算本单引入的回归**：该断言的原始依据是 A 层历史观测（`_vertex_drift_issues` 在旧提示词下窗为 0 条），而 **B 层这道 Pre-EnergyPlus gate 直到今天、这次真实下游跑测才第一次有冻结快照可比**（施工单 §1 已指出"全仓只有今天这个 run 带快照"）。`FenestrationConverter.validate()` 同样调用 `GeometrySchema.model_validate({"fenestrationsurfaces": ...})`，会触发同一段无条件重排逻辑——**窗和墙在 B 层受到的待遇完全相同**，与 `fenestration.py` 提示词改没改无关（A 层窗漂移在改动前后都是 0，改动没有让任何东西变坏）。

**为什么不修**：`src/validator/data_model.py` 不在施工单授权范围内（不是 `surface.py`/`fenestration.py` 提示词，是 MCP 工具/转换器共享的确定性代码层，影响面覆盖全部案例的全部面/窗，且是否要"保留提交顺序"是一个需要用户/orchestrator 裁定的架构问题——例如是否该在这里插入"顶点已给定绝对世界坐标时跳过重排"的分支——这类改动的正确性判断超出本单"提示词侧修法"的授权边界，属于"越界顺手修"）。

**候选编号**：F-13（全仓 grep 确认 `F-13` 此前未被占用）。

**建议的后续动作（仅建议，非本单要做的事）**：orchestrator 裁定是否要给 `GeometrySchema.validate_points_sorting` 加一个"信任已给定的绝对坐标顶点顺序、不重排"的旁路（可能需要一个 flag 或按 surface 来源区分），使 B 层的比对不再对结构性正确的输入产生假阳性。在此之前，**B 层 Pre-EnergyPlus gate 会持续拦下几乎所有真实几何**（只要面不是恰好本来就以"左上角"为起点提交），EnergyPlus 阶段不可达。

---

## 6. 全仓回归

**基线**（CLAUDE.md 记录）：2234 绿 / 10 xfail / 0 红。

**本轮独立全量**（`pytest -n auto`，含新增 5 条 F-12 锁）：

```
========== 2239 passed, 10 xfailed, 209 warnings in 328.83s (0:05:28) ==========
```

**2234 + 5（新增本单锁）= 2239，零回归。** 完整尾部输出：[`experiments/2026-08-06_f12_transcribe_verify/pytest_full_tail.txt`](../../logs/experiments/2026-08-06_f12_transcribe_verify/pytest_full_tail.txt)。

---

## 7. 停下上报判断

本单陈述的事实与实际代码/行号/verbatim 声明**全部核对一致**，验收条件本身也不互相冲突（§5 的 4 项条件各自独立可测）——**唯一的落差是"提示词修法能否让 VERTEX_FRAME_DRIFT 整体归零"这件事本身分成了两层，其中一层（A 层，本单目标）确实归零，另一层（B 层，一段独立于提示词的确定性代码）不可能靠提示词归零**。施工单 §5 第 4 条本身已经预先给出了"撞到新墙就登记不修"的处置条款，所以这不是一次"派工方的题错了"式的停下上报——**是施工单已经预料并放行的分支，如实按该条款执行**。

---

## 8. Commit

见仓库 git log（本单只 `add` 本单相关文件：`src/agent/nodes/{surface,fenestration}.py` / `tests/test_f12_surface_prompt_transcribe.py` / `AI_agent/logs/downstream_agent_changes.md` / `AI_agent/logs/reviews/request/2026-08-06_f12_surface_prompt_transcribe_dispatch_claude.md` / `AI_agent/logs/reviews/execution/2026-08-06_f12_surface_prompt_transcribe_claude.md`；**不 `git add -A`**，`AI_agent/plan.md` 与其它并行席位〔F-8/F-9〕产出的文件本轮检出已是 dirty/untracked 但非本单所改，一律不碰）。
