# 执行日志 · F-9 路线② S2：权威 projector + shadow position evidence

- **席位**：Claude 侧 Sonnet 5（执行档）
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD = `21b4739`（S0/S1 已落库）
- **派工单**：[`2026-08-12_f9_route2_s2_shadow_projector_dispatch_claude.md`](../request/2026-08-12_f9_route2_s2_shadow_projector_dispatch_claude.md)
- **设计稿**：[`f9_route2_evidence_citation_design.md`](../../../proposals/f9_route2_evidence_citation_design.md) §10 S2 / §12.2 / §1.3 / §6 / §7.1-7.3
- **文件所有权**：`src/agent/correction/window_position.py`（扩）+ `src/validator/checks/correction.py`（扩）+
  `scripts/tool_scripts/run_stage.py`（一行接线）+ 新建测试文件 `tests/test_f9_route2_s2_authoritative_projector.py`。
  另有一处**超出名义所有权的最小改动**：`src/agent/pipeline.py`（单行 kwarg，见 §1.4，理由见 §5）。
  **未触碰** `envelope_transform.py` / `finalize.py` / `window_host.py` / `window_sources.py` / `deterministic.py` /
  `stage_runner.py`（这些文件在本次执行期间被并行席位实时修改，`git status` 已核实零重叠）。

---

## §0. 防假验证自检（开工前，逐字兑现）

**做法**：在 `src/validator/checks/correction.py::check_correction` 函数体末尾（我计划插入 S2 调用的确切位置）插入
`raise RuntimeError("STEP0_PROBE_F9_S2_SHADOW_INTEGRATION_POINT")`，用真实 `_draw_correction`（stub 掉 LLM 边界
`run_correction`）与真实 `run_pipeline_artifacts`（同样 stub `run_correction`）各跑一次，输入取
`case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e`（真实、完整跑通到 EnergyPlus 的 v3 run）经
`tmp_path` 隔离裁剪的最小文件集。

**结果**：两条真实入口都精确抛出了该探针字符串（`STEPWISE: probe fired as expected.` /
`INTEGRATED: probe fired as expected.`），**且 integrated 路径不需要 mock 4_mep** ——
`check_correction` 在真实 `run_pipeline_artifacts` 里于 4_mep/kernel geometry 之前执行，探针在到达 4_mep 前就命中。
探针随后立即撤回，未混入正式实现。**⇒ 我计划的接线点（`check_correction` 函数体内，在其余检查之后）在两条真实入口上都可达，
不是假验证路径。**

---

## §1. 改了什么

### 1.1 `src/agent/correction/window_position.py`（新增 ~750 行，无删除）

在 S0 既有内容后追加一个独立的 "§10 S2" 段落，**不修改任何 S0 已有代码**：

- **常量**（v2.1 §5.3/§7.3，冻结值，不走 `configs/correction.yaml`——理由见 §5）：
  `WINDOW_EVIDENCE_PAIRING_TOL_M = 0.300`、`PROJECTION_SCOPE_EPSILON_M = 1e-9`、
  `Z_DATUM_MODE_WORLD_Z = "world_z"`（唯一、显式命名的 z-datum 模式，见 §5 对硬约束#6 的回应）。
- **`AuthoritativeViewProjectionFrameV2`**：权威 frame 的类型安全包装，只能经
  `.from_current_ring_binding(binding)` 从既有 `materialize_current_ring_va_elevation_bindings`
  （生产已在用，`window_host.py::_source_world_interval` 消费的同一份）构造。
- **`AdvisoryViewProjectionFrameV1`**：结构上不同的类型，只为 neuter 测试存在，生产代码从不构造它。
- **`project_window_source_along(source, *, window_facade, frame=None, scope_floor_id=None)`**：
  §6.3 唯一投影入口；plan 源直接取世界坐标；elevation 源要求 `isinstance(frame, AuthoritativeViewProjectionFrameV2)`，
  否则 `TypeError`（advisory / `None` / 任意对象一律拒绝）。
- **`resolve_elevation_source_floor_scope(source, floors)` + `_FloorScopeResolution`**：
  §7.3 z-datum 归属，三态（`not_declared` / `resolved` / `unresolved`），显式单一 `world_z` 模式，
  full-containment + `PROJECTION_SCOPE_EPSILON_M` 松弛，重叠/零匹配一律 `unresolved`（不取最近/第一个）。
- **`WindowPositionEvidenceShadowDecisionV1`** / **`WindowPositionEvidenceShadowReportV1`**：
  逐窗 / 逐 run 的 shadow 判定与报告，各自 `model_validator` 自证哈希与内部不变式
  （**刻意不复用 S0 的 `WindowPositionDecisionV1`/`WindowPositionEvidenceArtifactV1`**——
  那两个类型绑定的是尚未接线的 raw-v2 wire 身份根，理由写在模块内新增的 "§10 S2" 段落说明里）。
- **`_build_authoritative_frames`**（私有、刻意可 monkeypatch 的接缝）、
  **`_window_existence_sources`**、**`_build_window_position_evidence_shadow_decision`**（全函数纯计算、
  对任何良构输入 total，不抛异常表达数据质量问题）、**`compute_window_position_evidence_shadow`**（公开入口）。

### 1.2 `src/validator/checks/correction.py`（+112 行）

- `check_correction(...)` 新增可选参数 `verified_window_inputs=None`（向后兼容——所有既有调用方不传时行为不变，
  已用 317 个既有测试实测确认，见 §4）。
- 新增 `_window_position_evidence_shadow(rep, geom, verified_window_inputs)`：三态分派
  （`NOT_APPLICABLE` / 计算成功 PASS-or-FAIL / 计算过程异常或 `binding_unavailable` 时 FAIL），
  **恒定注册在 `CheckLayer.CROSS_CHECK`**，且用 `try/except Exception` 兜底——shadow 自身的任何异常
  （含 advisory frame 类型错误）只会变成 FAIL 行，绝不上抛到 `check_correction` 之外。

### 1.3 `scripts/tool_scripts/run_stage.py`（+8 行，我的所有权）

`_draw_correction` 里既有的 `check_correction(...)` 调用新增一个 kwarg：
`verified_window_inputs=verified_window_inputs`（复用该函数**已经**在上方为 `finalize_correction_draw`
构建好的同一个 `verified_window_inputs` 局部变量，零新增计算）。

### 1.4 `src/agent/pipeline.py`（+7 行，超出名义所有权，理由见 §5）

`run_pipeline_artifacts` 里既有的 `check_correction(...)` 调用同样新增一个 kwarg
`verified_window_inputs=verified_window_inputs`（同样复用该函数已有的同名局部变量）。
**这是本次交付里唯一一处不在派工单列出的四项所有权范围内的改动**，且是单行 kwarg 追加、
未新增 import、未改动周边任何一行。执行期间该文件被并行席位（摊 C）同时修改
（新增 `annotation_basis.json` 侧车写入逻辑）；`git diff` 已核实两处改动互不重叠、无冲突。

### 1.5 新建测试文件

`tests/test_f9_route2_s2_authoritative_projector.py`（45 个测试，见 §3/§4）。

---

## §2. 每把锁绑的是什么

真实数据来源（零手搓几何）：
- `tests/fixtures/f9_window_host_crash/`：真实 F-9 镜像 bug run 的字节级裁剪（`W-F1-N-1`/`W-F1-N-3`/
  `W-F2-N-1`/`W-F2-N-2` 四扇窗引错了镜像搭档，`resolve_window_hosts` 会因既有粗粒度 overlap 检查而拒绝
  ——本测试套件直接调用 `apply_deterministic_core` + `materialize_all_facade_segments`，**不经过**
  `finalize_correction_draw`，让这四扇窗的 shadow 判定可被观测而不是被提前拦截）。
- `case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e/`：真实、完整跑通到 EnergyPlus 0 Severe
  的 v3 生产 run，15 扇窗全部引用正确，用作"干净基线"（真正走通 `finalize_correction_draw`）。

| 锁（组） | 绑什么 | 关键断言 |
|---|---|---|
| F-9 oracle（4 个测试） | 真实 F-9 fixture，15 扇窗 | 11 accept / 4 reject，`W-F1-N-1` 手算数字与设计稿 §12.3 逐位吻合（plan=[1.24,3.64]，cited S5→[11.24,13.64]，d=10.00）；另设 `W-F1-N-1` S5→S7 换引用后**同一扇窗**从 reject 翻 accept（d=0.12），对齐设计稿"F-9 mirror negative"锁的原始措辞 |
| z-scope 消歧（3 个测试） | 真实 `East_view/S3` vs `S4`（同 along `[3.52,4.72]`、z 分属 floor-2/floor-1） | 两扇真实窗各自正确解到自己楼层；手工把 `W-F1-E-1` 换引 `S3`（z 属 floor-2）在**有**z-scope 检查时 reject（`position_evidence_pair_mismatch`），**neuter 掉** `resolve_elevation_source_floor_scope` 后同一构造变 accept（假阳性复现，证明该检查真的承重） |
| 阈值边界（1 个测试 + 2 个配置测试） | 手搓 identity frame | d=0.29 → accept，d=0.31 → reject（唯一变量是 endpoint 残差）；`WINDOW_EVIDENCE_PAIRING_TOL_M` 冻结值断言 = 0.300；配置交叉校验函数对小于 0.300 的 `envelope_reconcile_tol_m` 拒绝；`compute_window_position_evidence_shadow` 真的调用了该校验（монkeypatch 常量后触发 `ValueError`） |
| Advisory 隔离（4 个类型测试 + 2 个 wiring 测试） | `project_window_source_along` 的 isinstance 门 | advisory / `None` / 任意 object 全部 `TypeError`；plan 分支不受 frame 参数影响；F-9 数据自证 advisory 与权威 frame 确有 0.12 差（14.88 vs 15.0） |
| None 纪律（5 个测试） | `WindowPositionEvidenceShadowReportV1` 三态 | 零窗 = 真实 PASS（`window_count=0`，非空 hash）；缺 `verified_window_inputs` = `NOT_APPLICABLE`（≠ PASS ≠ FAIL）；`WindowDirectionBindingError` = `binding_unavailable`（≠ `evaluated`）；pydantic 层面也拒绝 `binding_unavailable` 但 `binding_error_code=None` 的构造 |
| 恒不阻断（2 个测试） | `disposition()` | 用**真实 4/15 reject 的 F-9 数据**在 `run_profile="regression"`（最严档）下断言 `disposition(...) == FLAG`，且该 check-id 不在 `rep.blocking()` 里；另断言该行永远注册在 `CheckLayer.CROSS_CHECK` |
| 真实入口 × 2（4 个测试） | `_draw_correction` + `run_pipeline_artifacts` | 干净 run 通过两条真实入口都产出 `correction.window_position_evidence_shadow` 明确 `PASS`（evidence 含 `window_count=15`/`rejected_window_ids=[]`） |
| 身份/哈希自证（5 个测试） | pydantic `model_validator` | 篡改 `distances`/`all_accepted`/交叉身份字段后 `model_validate` 拒绝；accept 分支要求 `derived_span == plan_world_interval`；reject 分支禁止携带 `derived_span` |
| 权威性拆分（4 个测试） | zero/multi plan、zero elevation、同 view 重复 corroborator | 各自映射到对应 `reject_code`（`position_evidence_authority_invalid` / `position_evidence_insufficient`） |
| legacy span diff（2 个测试） | `legacy_span_delta_m` | reject 时恒 `None`（非"算出来是 0"）；accept 时恒是真实 float |

---

## §3. 两个 must-red neuter 的实测结果

### neuter ①「摘掉 projector」

**做法**：monkeypatch `wp._build_authoritative_frames`，对其真实返回值逐个 `model_copy(update={"along_origin": 0.0})`
（模拟"当前环投影从未真正跑过"，而不是简单把局部坐标当世界坐标直通——那样在这份数据上恰好不构成有效判别，见下方"遮蔽自查"）。

- **单元级**（`test_neuter_remove_projector_flips_clean_run_pass_to_fail`）：干净 run（15/15）
  先自证 `all_accepted is True`，neuter 后 `all_accepted` 变 `False`，**至少一扇窗** decision 从
  accepted 翻 rejected。
- **真实入口级**（`test_real_stepwise_entry_neuter_projector_flips_to_fail_blocking_unaffected` /
  `test_real_integrated_entry_neuter_projector_flips_to_fail`）：同一份真实数据走**两遍**真实
  `_draw_correction`（分别落两个独立 `tmp_path`，只有 neuter 这一个变量不同），shadow 行从
  `PASS` 翻 `FAIL`；`rep.blocking()` 两遍都是空列表；**且逐条比对除 shadow 行外的全部其余 check
  （coverage/nondegenerate/zstack/window_host_resolution/zone_count/window_on_wall/facade_frame_cross_check/
  audit_completeness/evidence_debt_coverage，共 >5 条）状态与消息逐字节相同**——
  证明 `window_host.py::resolve_window_hosts` 自己独立调用的
  `materialize_current_ring_va_elevation_bindings`（未被我的 monkeypatch 触碰，因为它不经过
  `wp._build_authoritative_frames` 这个接缝）确实没有被这次 neuter 波及，不是巧合性沉默。
- **有没有连带**：无。仅 `correction.window_position_evidence_shadow` 一行受影响。

### neuter ②「改用 advisory frame」

**做法**：monkeypatch `wp._build_authoritative_frames`，把返回值替换成同 `input_id`/`sign` 的
`AdvisoryViewProjectionFrameV1` 实例。

- **单元级**（`test_project_window_source_along_rejects_advisory_frame` 等 3 个类型测试）：
  直接调用 `project_window_source_along(elev_source, frame=<advisory>)` → `TypeError`。
- **接线级**（`test_neuter_advisory_frame_substitution_becomes_fail_row_via_check_correction` /
  对应的真实入口版本）：干净 run 先自证 `PASS`；neuter 后 `check_correction` 的 shadow 行变
  `FAIL`，`evidence.exception_type == "TypeError"`；该行仍不进入 `rep.blocking()`。
- **有没有连带**：无（同上，其余检查逐字节不变）。
- **关键发现（写在这里避免误导）**：在真实 F-9 数据上，advisory 与权威 frame 的数值差只有约
  0.12 m（`along_origin` 14.88 vs 15.0），**对绝大多数窗不足以把 accept 翻成 reject**——
  真正把这条 neuter 变成"锁转红"的是**类型门**（`TypeError`），不是数值分歧本身。
  这与设计稿 §12.2 原文"advisory 类型传入 enforcement 必须 type/error FAIL"的措辞一致，
  但意味着"改用 advisory frame 会导致数值判错"这句直觉描述**不准确**——准确说法是
  "改用 advisory frame 结构上不可能通过类型门，因而必然报错"。已在测试
  `test_advisory_frame_numbers_genuinely_differ_from_authoritative_on_f9_data` 里把这个 0.12 差异
  单独立成一条自证前提的测试，不与"锁转红"的机制混为一谈。

---

## §4. shadow 开关的不变性实测（"不得因启用观测而改变接受结果"）

**判据**：把 shadow 打开和关掉，所有现有 run 的接受/拒绝结果必须逐字节一致。

- **直接判据**：`_window_position_evidence_shadow` 恒定注册在 `CheckLayer.CROSS_CHECK`；
  `src/validator/checks/schema.py::disposition()` 对 `CROSS_CHECK` 层的 `FAIL` 状态在**任何**
  `run_profile` 下都映射 `Disposition.FLAG`（唯一能变成 `BLOCK` 的分支是 `CheckStatus.ERROR`，
  而 `_window_position_evidence_shadow` 的实现里没有任何路径产出 `CheckStatus.ERROR`——
  已用 `test_shadow_fail_never_blocks_under_regression_profile`
  在真实 4/15 reject 的 F-9 数据、`run_profile="regression"`（全项目最严档）下机械验证）。
- **关掉等价于什么**：`verified_window_inputs=None`（不传该参数，即 S2 之前的调用方式）
  →`NOT_APPLICABLE`——用 317 个既有测试（`test_c2_b0.py`/`test_c2_b1_cell_polygon.py`/
  `test_c2_b2_v3.py`/`test_c2_b5_artifact_trust.py`/`test_checks_reading_correction.py`/
  `test_f9_route2_s0_raw_contract.py`/`test_f9_route2_s1_convention_truth.py`/
  `test_f9_window_host_crash.py`/`test_e2e_break_r2_locks.py`）实测：**317 passed**，
  零回归——所有既有调用方（未显式传 `verified_window_inputs`）的既有断言全部不受影响。
- **打开后**：两次真实入口的 neuter 前后对照（见 §3）已经是最强的"打开/关闭"不变性实测——
  与其只做"传参 vs 不传参"两态比较，我用"同一份真实数据、真实入口跑两遍、只让 shadow 的
  内部判定翻转"的方式，同时证明了"这条 CROSS_CHECK 行无论内容如何都不影响
  `rep.blocking()`"和"其余检查逐字节不受 shadow 状态影响"两件事。

---

## §5. 关键设计取舍（含硬约束的落实方式）

1. **z 轴 datum 显式规则（dispatch 硬约束 #6）**：新增 `Z_DATUM_MODE_WORLD_Z` 具名常量 +
   `resolve_elevation_source_floor_scope` 独立函数，而不是在投影公式里内联 `local_z == world_z`。
   真实 `East_view/S3`（z 属 floor-2）与 `S4`（z 属 floor-1）投影到**逐位相同**的世界坐标
   `[3.52, 4.72]`——这正是 dispatch 点名的"沿墙区间逐位相同、只有高度不同"的真实案例，
   已用 §2 表格里的 z-scope 消歧测试组覆盖，并用 neuter 证明该检查确实承重
   （非隐式巧合，见 `test_zscope_neuter_disabling_scope_check_causes_false_accept`）。
2. **`window_evidence_pairing_tol_m` / `projection_scope_epsilon_m` 未落进 `configs/correction.yaml`**：
   两值都被设计稿要求"冻结"，我改用模块级硬编码常量而非 YAML 可调字段——这与"冻结"的字面含义
   更贴合，也**避免了触碰 `src/agent/correction/config.py`**（不在我的文件所有权范围内，
   且它是多处生产代码共享的配置基础设施，改动风险与并行席位冲突的可能性都更高）。
   跨字段校验（`0 < window_evidence_pairing_tol_m <= envelope_reconcile_tol_m`）改为运行时函数
   `_validate_window_evidence_pairing_tolerance`，每次 `compute_window_position_evidence_shadow`
   调用时都会执行（已用 monkeypatch 证明它真的被调用，见 §2 表格）。
3. **`pipeline.py` 的单行改动**：设计稿与 dispatch 都明确要求"真实 `_draw_correction` 与
   integrated pipeline 都出现该 fact"，而 `check_correction` 的两个真实调用点（`run_stage.py`
   与 `pipeline.py`）都已经各自独立构建好了同名 `verified_window_inputs` 局部变量，只是没有把它
   传给 `check_correction`。除了在这两处各加一个 kwarg 之外，我没有找到任何**不接触
   `pipeline.py`**就能满足两条真实入口验收条件的路径（`finalize.py`/`window_host.py` 是更"正统"
   的接线点，但那两个文件在整个执行期间被并行席位实时修改，接触它们的碰撞风险明显更高，
   且 `finalize_correction_draw` 对 F-9 真实镜像 bug fixture 会直接抛异常、根本不适合作为
   shadow 观测点）。这是本次交付里唯一超出名义所有权四项列表的改动，改动本身单行、无副作用、
   已用 `git diff` 核实与并行席位的改动零重叠。
4. **不做完整 §5.3 全量互斥候选搜索（mutual-nearest across the whole catalog）**：
   S2 的验收文本（§10）只要求"记录 plan authority、current-ring elevation projection、pair
   distance、legacy model span 差异"，未提"跨全 catalog 搜索是否有更好的候选"——那是设计稿把
   "detector"（S3 的阻断门）与"shadow"（S2）刻意分层表述里，S3 才要做的事（"代码即使找到更好的、
   但模型没有引用的 source，也只可据此判'引错了'"这句本身就属于 §5.3 的 detector 语境，
   S2 阶段模型引用的仍是**今天**的 wire，不是新 raw-v2 引用协议）。**这是一处主动的范围收窄，
   已在下方"未验证的项"里如实列出**，不是遗漏。

---

## §6. 未验证的项与不确定的判断（如实列出）

1. **跨 catalog 唯一最佳匹配（mutual-nearest）未实现**——见 §5 第 4 点。今天的 shadow 判定只验证
   "模型已引用的那一对是否在容差内、z-scope 是否匹配"，不验证"是否存在另一个模型没引用、但代码
   算出来更贴近的候选"。如果 S3 的验收口径要求这条也在 S2 就落地，需要返工。
2. **同一 view 多 corroborator 的场景零真实数据验证**——`test_duplicate_same_view_elevation_corroborators_rejected`
   是手搓夹具，15 扇真实窗全部只有 1 个 plan + 1 个 elevation 引用，没有任何真实产物覆盖"同一扇窗
   引用两条来自不同 view 的 elevation corroborator"（设计稿允许的合法多 view 加强场景）路径。
3. **z-interval 缺失（`not_declared`）时的宽松处理未被真实数据触发**——15 扇窗的 elevation 引用
   全部带 z 区间，"当 elevation 引用没有 z 数据时跳过 scope 检查、只按 along 距离判定"这条分支
   只有手搓单元测试覆盖，没有真实产物路径。这是一处刻意选择的宽松（详见模块内该函数的
   docstring），但没有真实数据能证明它在生产语料上是否常见或是否安全。
4. **`validate_case`（`src/agent/execution/validation_run.py` 第三个 `check_correction` 调用点）
   未接线**——它没有传 `verified_window_inputs`，因此对经它重跑检查的历史 run，shadow 行永远是
   `NOT_APPLICABLE`。设计稿 §12.1 的两条必须真实入口（stepwise + integrated）都不包含它，
   dispatch 也未点名，但如果它算"第三条真实入口"，本次未覆盖。
5. **`binding_unavailable`（`WindowDirectionBindingError`）路径只有 monkeypatch 覆盖**——没有找到
   一份真实产物会真的触发 `materialize_current_ring_va_elevation_bindings` 报
   `direction_binding_ring_invalid`/`_incompatible`（这个既有函数本身的"各楼层 footprint/extent
   必须相同"限制，我未改动也未验证它在多楼层退台等场景下的真实触发条件）。
6. **`legacy_model_span` 在窗口 span 结构性畸形（如长度≠2 或 lo>=hi）时的降级路径未经真实或构造
   数据验证**——按现有生产流程，`geom` 到达 `check_correction` 时应已通过 `resolve_window_hosts`
   的 span 合法性检查（见 `window_position.py` 该分支的 docstring 推理），但我没有构造一个
   真实能到达这条防御性分支的夹具，只是让代码"理论上不会崩"。
7. **未对 EnergyPlus / 下游产物做任何验证**——本次改动是 gate① 的一条 CROSS_CHECK，不影响
   `output.json`/IDF/EnergyPlus 输出，也没有跑真实 EnergyPlus 仿真去确认这一点（用 disposition
   与逐字节报告对比已经是我认为最直接的证明方式，但没有额外做端到端仿真复核）。
8. **并行席位改动的交互面**：`envelope_transform.py`/`finalize.py`/`deterministic.py`/
   `stage_runner.py` 在本次执行期间被并行席位实时修改，我只在这些文件里做了只读引用（未编辑），
   且全部相关测试（含我新建的 45 个）在这些改动**已经落在工作树里**之后运行全部通过——
   但我没有在他们改动之前的基线上重新跑一遍做纯净对照，理论上不能排除他们的改动恰好隐藏了
   我这边的某个问题（可能性较低，因为我的代码路径与他们改动的文件在调用图上不相交，
   已用 `git diff` 确认零重叠行）。
