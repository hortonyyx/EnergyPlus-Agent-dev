# B-O 批施工执行简报（真北接线，2026-07-12/13）

- 施工合同：[c2_e4_output_contract_spec.md](../../proposals/c2_e4_output_contract_spec.md) v2 定稿
- 派发单：[2026-07-12_bo_construction_dispatch.md](../request/2026-07-12_bo_construction_dispatch.md)
- r1 交叉审查基座：HEAD `3123611`；本返工接手的当前基座：HEAD `b5ff6d6`（前一版的 `4e3cb49` 记录错误，已按 BO-CR12 更正）。前置门确认：`_CORRECTION_STAGE_VERSION_BY_RELEASE`/`correction_stage_version()` 已在位、Vg release tuple=`("floor_footprint_v1","facade_visibility_v1")→"3"`、`NorthAxisEvidence`/`CorrectedGeometryV3.north_axis` 已在位、B2 draw 合同 `north_axis is None` 已在位。
- 未 commit；工作树内交付。执行档：Sonnet 5（中途限额中断一次，重启续工）。

---

## 一、改动映射（稿章节 × 代码落点）

### 新建模块（3）

| 稿章节 | 文件 | 内容 |
|---|---|---|
| §3.1/§3.2/§3.4/§3.5/§5.2/§6.2/§7.4/§8.1 | `src/agent/output_coordinates.py` | `OutputCoordinateContract` strict/frozen 类型 + `AcceptedCorrectionRef`/`LegacyStandaloneIntakeRef`（mode→常量组合 model_validator 全锁）、`VerifiedAcceptedCorrection`（只存 immutable bytes）、`load_verified_accepted_correction`（manifest 路径逐项对账）、`verify_integrated_gate1_correction`（gate① 无 blocking 边界）、`derive_output_coordinate_contract`（纯函数、每次重算 hash+fresh parse；v1/v2→world_legacy、v3+e4 contract→relative；B2 冒充 E4/缺 feature-state/digest 漂移全硬失败不回落）、`legacy_contract_for_unversioned_intake`（唯一 absence→legacy 工厂）、`OutputCoordinateSnapshotV1`/`build_output_coordinate_snapshot`（2dp 同源快照）、`apply_output_coordinate_contract`（deep-copy+GGR 三字段+Building θ+all_zero 归零）、`zero_zone_frames_with_audit`/`validate_zone_frames_all_zero`（全量 offender 按名排序）、`ZoneFrameNormalizationEntryV1`/`AssemblyCoordinateAuditV1`/`ExportCoordinateAuditV1`、`AssemblyE4Write`（S5 writer 载荷标记类型）、`assemble_intake_artifacts`、`coordinate_semantic_projection`（parity 投影 = dump exclude source）、`load_intake_bundle`（§3.4 四级优先级）、`OutputCoordinateValidationContext` |
| §3.2bis | `src/agent/correction/orientation.py` | `OrientationConflictV1`/`OrientationEvidenceSetV1`（content-addressed、空集有 canonical hash）/`OrientationRunConfigV1`/`OrientationResolutionInputV1`/`OrientationEnrichmentV1`/`NorthAxisAssumptionAuditV1`（六字段+policy_ref/knowledge_ref:null/N/A reason 全冻结）、`VerifiedOrientationResolution` + `verify_orientation_resolution`（三份 raw bytes hash 对账+completion_mode 绑 RunConfig）、`finalize_orientation_enrichment`（==1 采用/==0+interactive→`OrientationNeedsInputError`/==0+prior_fill→机械 assumed-0/conflict、多候选、base 已 populated、非 Vg base 全 BLOCK；fresh rebuild 且除 north_axis 外逐字段不变断言）、`OrientationEnrichmentResult`（writer 分辨标记） |
| §7/§8.1 | `src/validator/output_coordinates.py` | `CoordinateObjectRule`/`CoordinateExclusionRule`/`OutputCoordinateIssue`（8 个固定 issue code）、`ep25.1-v1` registry（frame controllers/detailed zone-bound/building-origin/rectangular A5/daylight A4/host-local/host-derived/site-world exempt/true-north param/PVWatts predicate/georeference exclusion）、IDD 层真扫描（`parse_idd_object_blocks`+短语/字段标记，非硬编码清单）、`idd_layer_completeness_diff`（候选−registry 必空）、`final_idf_layer_offenders`（live eppy IDF 层 4：unclassified/unsupported BLOCK，非空间对象不误伤）、`validate_output_coordinate_contract`（contract strict round-trip/source 重 hash/Building θ/GGR A3A4A5/全 Zone 四零/快照逐顶点对账/registry 门） |

### 修改文件（17 src+scripts，4 tests 适配）

| 稿章节 | 文件 | 改动 |
|---|---|---|
| §3.2bis E4-R3 | `src/agent/correction/feature_state.py` | `HELPER_NORTH_AXIS_ORIENTATION_V1`；release map 增第四行 exact tuple→`"4"`（字面量只在集中 map）；`correction_stage_version()` 增 E4 tuple 状态交叉门（phase==e4_orientation+双 populated，否则 INVARIANT）；`derive_feature_state_claims` 增 e4_orientation 分支（final geom 重派生，geom.north_axis None 则 INVARIANT）；`artifact_feature_state` 允许 contract 集合加入 `correction_e4_orientation_v1` |
| §3.4 | `src/agent/execution/manifest.py` | `ArtifactKey` 增两 sidecar 键；`ArtifactContract` 增 `correction_e4_orientation_v1`/`assembly_e4_v1`；两 contract 的 REQUIRED/ALLOWED key 集登记（旧 contract 键集零改动） |
| §3.2bis writer/§3.4 | `src/agent/execution/stage_runner.py` | `record()` 识别 `OrientationEnrichmentResult`（先于 FinalizeResult 判定）→ 四产物+`correction_e4_orientation_v1`+release map 派生 stage_version（caller 传值忽略、无 `"4"` 字面量）；识别 `AssemblyE4Write` → 单 attempt 目录五产物（output/checks/audit/两 sidecar）+`assembly_e4_v1`+root convenience 两 sidecar；Vg CR1 facade 重算防篡改门对 enrichment write 同样生效 |
| §4.1 | `src/validator/checks/mep.py` | 新增 `mep.building_north_axis_placeholder` INVARIANT（数值型且 ==0.0 才 pass，-0.0 接受；全 schema/profile 生效） |
| §4.2 | `src/agent/intakeoutput.py` | `assemble_intake_output(..., output_coordinates=None)`：有合同时先断言 MEP 占位 0（绕过 S4 也挡）→ 无条件 fresh `BuildingSchema.model_validate` 写 θ（θ=0 同样执行；不 mutate 传入 mep）→ final strict round-trip+终值断言；`output_coordinates=None` 走 pre-E4 原样路径（byte 不变） |
| §3.3 | `src/agent/state.py` | `AgentState`/`AgentStateUpdate` 增 `output_coordinate_contract`/`output_coordinate_context`（不进 IntakeOutput 11 字段、不进 merge_config_state） |
| §5.1 | `src/validator/data_model.py` | `GlobalGeometryRulesSchema` 增 A4/A5 字段（默认=IDD 默认 Relative，pre-E4 byte 不变）+ IDD choice validator |
| §5.1 | `src/converters/setting_converter.py` | `_global_geometry_rules_apply` 显式写 A3/A4/A5 |
| §5.2/§8.2 | `src/agent/nodes/intake.py` | `_seed_config(state, intake, contract)` 应用 GGR+θ（种子时 Zone 空）；短路路径应用 `state.output_coordinate_contract`；pipeline 路径改调 `run_pipeline_artifacts` 并把 contract/context 写回 AgentState |
| §5.2 | `src/agent/nodes/simulate.py` | WorkflowTool 显式传 `output_coordinates`/`validation_context` |
| §6.2 | `src/agent/nodes/zone.py` | Relative 版 system prompt（按 contract.zone_origin_policy 显式选择，不读 θ/GGR）；尾部无条件 `zero_zone_frames_with_audit` 归零+审计 |
| §6.2 item5 | `src/agent/tools/zone_tools.py` | `make_zone_tools(config, contract=None)`；all_zero policy 下 create/update 非零 frame 直接拒绝（结构化 ToolResponse）；contract=None=显式 legacy 直通 |
| §6.2 item1 | `src/agent/geometry/specs.py` | `serialize_geometry(bg, frame_label="world"|"building_axis")`：v3/E4 文案 building-axis、默认 world 分支 byte 不变；顶点数值两支零变化 |
| §3.5/§8.2/§11 | `src/agent/pipeline.py` | `run_pipeline_artifacts`（返回 `(intake, bundle|None)`；`run_pipeline` 收窄为兼容 wrapper）；gate① 干净后:v3 走 §3.2bis enrichment（本批唯一 producer=空证据集+prior_fill→assumed-0）、v1/v2 直接 verify；S5 经 `assemble_intake_artifacts` 出 bundle+θ override；s5 落两 sidecar;s1 落 orientation_audit.json+enriched snapped 覆写;3_split_pairing 按 schema 选 frame_label |
| §5.2/§4.3/§7.4 | `src/mcp/tools/workflow.py` | 构造函数收 contract/context；`_coordinate_gate`：pre-YAML 一道+post-convert（live IDF）一道并入既有 gate 失败面；contract=None=显式 legacy_unbound（Relative ConfigState 无合同硬失败、Building 非零占位硬失败）；contract 有而 context 无→拒绝；`_write_coordinate_audit` 绑实际 YAML/IDF raw hash 写 `output_coordinate_audit.json` |
| §3.4 item7/§8.2 | `scripts/run_full_pipeline.py` | `--intake-from` 改 `load_intake_bundle`（模块级 import 可 patch），contract/context 进 AgentState |
| §8.2 | `scripts/tool_scripts/run_stage.py` | `_flow_ep` 改 `load_intake_bundle(intake_path, run_dir=run_dir)`，contract/context 进 AgentState |
| 测试适配 | `tests/test_run_full_pipeline_shared.py`、`tests/test_ep_end_gate.py`、`tests/test_intake_pipeline.py` | monkeypatch 目标从 `load_intake_from`/`run_pipeline` 换到 `load_intake_bundle`/`run_pipeline_artifacts`；MagicMock state 补 `building.north_axis=0.0`+`coordinate_system="World"` 两个具体值（裸 MagicMock float()=1.0 会误触 legacy 门） |
| §10.2 | `tests/test_checks_mep_assembly.py` | 追加 12 个 S4/S5 owner 测试（只增不改，原 28 个全保留） |

## 二、备份

`backup/src_history/2026-07-12_bo_north_axis_wiring/`（按仓库相对路径,共 23 个文件:19 src/scripts + 4 tests）。已脚本核验:每份备份与 `git show HEAD:<path>` byte 一致,且 `git diff --name-only` 的每个被改文件都有备份。三个新建模块与六个新测试文件无"既有"可备份。

## 三、验收与测试（定向分组，逐组 passed 数）

### 新增测试族（6 文件，96 全绿）

| 组 | passed |
|---|---|
| `tests/test_output_coordinate_contract.py`（§10.1+§3.2bis 四表） | **30** |
| `tests/test_output_coordinate_application.py`（§10.3） | **17** |
| `tests/test_output_coordinate_identity.py`（§10.4+§10.6 投影子集） | **16** |
| `tests/test_output_coordinate_registry.py`（§10.5） | **19** |
| `tests/test_output_coordinate_dispatch_guard.py`（§5.3 哨兵+workflow 门） | **6** |
| `tests/test_e4_relative_north_axis_e2e.py`（§9/§10.7，**真跑 EP 25.1.0×4 变体**） | **8** |

### 被改模块对应既有组（全绿）

| 组 | passed |
|---|---|
| `test_checks_mep_assembly.py`（28 旧+12 新） | 40 |
| `test_intakeoutput_assembly.py` | 5 |
| `test_run_manifest_v2.py` | 26 |
| `test_step_orchestrator.py` | 34 |
| `test_run_pipeline_self_checks.py` | 11 |
| `test_pipeline_kernel_wiring.py` / `test_pipeline_evidence_debt_import.py` | 3 / 1 |
| `test_intake_pipeline.py` | 3 |
| `test_correction_stability.py` | 24 |
| `test_runner_shared.py` / `test_run_full_pipeline_shared.py` | 1 / 2 |
| `test_zone_agent.py` | 1 |
| `test_ep_end_gate.py` | 8 |
| `test_interzone.py` | 12 |
| `test_c2_b2_v3.py` | 25 |
| `test_execution_foundation.py` | 21 |
| 邻接回归批（a8_evidence_routing/c2_b0/c2_b1_cell_polygon/check_parity/deterministic_naming/validation_run_baseline） | 41 passed, **8 xfailed** |
| test_orchestrate_baseline 批（与 c2_b2_v3/execution_foundation 合跑） | 77 passed, **1 xfailed** |

xfail 台账合计 9,数量与 reason 未动。零 golden/gt/anchor 改动（git status 可核）。全量 pytest 归主控终审独立跑。

### EP 端到端（§9 五断言，容器内真跑）

四变体 = 探针提交版 IDF（world_000 保留迁移前非零 Zone origin `Y=4.85`;三个 rel 变体全零 frame）;`energyplus -x -w Shenzhen.epw`,每变体 completed+0 severe:

1. rel_000 vs world_000:114/114 同名面 Azimuth 相等（≤1e-6°）✅
2. rel_090 = rel_000 + 90 mod 360:114/114（circular diff ≤1e-3°）✅
3. rel_270 = rel_000 + 270 mod 360:114/114 ✅
4. 14 区 ×3 组=42 对 Floor Area/Volume 相等（≤1e-6）✅
5. `Any non-zero ... are ignored` 精确子串:world=1（含配套 Potential mismatch）,rel_000/090/270=0（**rel_000 也为 0,证明分支非 θ!=0 猜测**）✅

EIO 列号全部由 `! <...>` 表头动态定位;容差为 E4 专用三常量,未复用几何 min-edge/snap。

## 四、预期行为变化

1. **integrated v3 run（run_pipeline/--reading-from）**:gate① 干净后自动走 orientation enrichment;无总平/指北针 case 由 prior_fill 机械得 assumed-0,最终 IDF `GlobalGeometryRules=Relative/Relative/Relative`+`Building.North Axis=θ`+全 Zone 四零;`5_intakeoutput/` 新增两 sidecar,`1_correction/` 新增 orientation_audit.json。
2. **v1/v2 与纯历史 11 字段文件**:全链路 World legacy,GGR A3=World、A4/A5 显式写 Relative（=IDD 既有默认,IDF 语义不变但字段显式化——IDF 文本增两列),Building 恒 0,Zone frame 原样。
3. **S4 新硬门**:4_mep LLM 输出 `building.north_axis != 0.0` 直接 BLOCK（此前静默放行）。
4. **WorkflowTool**:standalone/无合同调用方若 ConfigState 是 Relative 或 Building 非零→export/simulate 拒绝(此前放行,EP 侧只 warning);graph 路径带合同则 pre-YAML+post-convert 双门+审计落盘。
5. **stepwise v3 flow 暂时 fail-closed**:`_flow_ep` 经 `load_intake_bundle`,v3 run 无 assembly_e4_v1 accepted attempt 时硬失败(见未决 #1);v1/v2 stepwise flow 不受影响(实测 legacy 路径绿)。
6. **zone 工具**:Relative 合同下 create/update 非零 frame 被拒;无合同/legacy 完全原行为。

## 五、首轮未决·偏离事项（历史记录；已由 §八返工 r1 逐项复核/取代）

1. **stepwise flow 的 enrichment/S5 编排未接**(稿 §8.3 步骤 2-3/§10.6 全量 parity):StageRunner writer、manifest contract、loader、invalidate 机制全部落地并测试(test_output_coordinate_identity 用真 StageRunner 走通 correction_b2_v1→correction_e4_orientation_v1(release "4")→assembly_e4_v1 全链);但 `run_stage.py` 的 flow 状态机尚未插入"enrichment 子步 + S5 改走 AssemblyE4Write + accept 后 invalidate 2–5"。后果=v3 stepwise flow 在 EP 入口 fail-closed(方向正确但功能未通),integrated↔stepwise byte-parity 测试只覆盖到 manifest-vs-integrated 合同投影相等+S5 五 hash 链,未覆盖两路径 IntakeOutput byte 相等。
2. **§5.2 调用点 3/4 未接**:`cross_ref_foundations_node` 幂等复验与 `validate_node` 合同检查未加;现闭环=seed 应用→zone 尾部归零→WorkflowTool pre-YAML+post-convert 双门(fail-closed 边界在)。
3. **§7.4 部分**:`AssemblyCoordinateAuditV1` 已在 stepwise S5 attempt 的 audit.json 落盘;integrated 路径 S5 目录只落两 sidecar 未落该 audit;`ExportCoordinateAuditV1` strict 类型已建但 workflow 写盘用等价 dict(未含 zone_normalizations/offenders——zone_agent 的归零审计现仅日志,未经 AgentState 传到 export);`output_coordinate_ep_audit.json`(simulate 后)未实现;`validate_case`/replay 重算 audit hash 未接。
4. **§9.3 泛化 fixture 部分**:高层 z 不变+Zone z_origin=0 已在 ConfigState/IDF 层验证(application 组);负坐标 L 形 v3 EP fixture 与手工 eppy shading/daylighting registry EP fixture 未建(registry BLOCK 行为已在 live-eppy 层 4 单测覆盖:Wall:Detailed/Shading:Zone:Detailed/Shading:Building:Detailed/Daylighting:ReferencePoint/Window/Shading:Overhang/Shading:Site:Detailed 七类)。
5. **§4.3 防回写门为门式而非点式**:BuildingTool.update/MCP update_building 未逐点拒绝 north_axis 改写;依赖 pre-export gate 复验(合同值 vs 终值不等即 BLOCK)。graph 内本无 building update 工具,standalone 由 legacy_unbound 门挡非零。
6. **§10.8 A0/配置登记未做**:phase_contract=e4_orientation、helper、release "4"、两 wire 类型、method/policy_ref 及三个 e4 容差的 A0/管理文档登记——派发单明令本批不改管理文档,归主控收口;容差常量现落在 e2e 测试模块顶部。
7. **`run_config.yaml` completion_mode 未接线**:§3.2bis 的 completion_mode 身份用独立 content-addressed `OrientationRunConfigV1` 记录(hash 进 input_hashes);未扩展现有 `run_config.yaml` loader(判卷/评审域)。integrated 路径本批固定 prior_fill(见 review-ask #2)。
8. **REPORT assumed 桶机械收录未接**(§3.2bis 尾):audit 侧 policy_ref/knowledge_ref:null/N/A reason 已冻结并测试;report_assembly 的 REPORT.md 收录归 REPORT 管线,本批未动。

## 六、首轮 review-ask（历史记录；裁定与返工后的新 ask 见 §八）

1. **integrated 路径 gate①-blocking+exploratory 的合同缺位**:correction gate① 有 blocking 但 exploratory profile 警告放行时,无 accepted 身份可绑,S5 走 pre-E4 原样装配(无 sidecar、无 override)。我判定这是"无 accepted correction 就无合同"的正确语义,但稿未显式写这个 profile 交叉场景——请审。
2. **integrated 路径 completion_mode 硬定 prior_fill**:run_pipeline 无 interactive 入口(全自动管线),我把 integrated 的 OrientationRunConfigV1 固定为 prior_fill。若上位想让 integrated 也可配 interactive(NEEDS_INPUT 中断),需加配置面。
3. **`load_intake_bundle` 对"旧 v1/v2 stepwise run(S5=base_v2)"的裁定**:稿 §3.4 规则 3 只对 v3 硬失败、规则 4 只覆盖"无任何 correction 身份";v1/v2 correction 身份+无 sidecar 落在两规则之间。我按 §5.3 分派表"v1/v2 accepted legacy→world_legacy"处理成 legacy standalone 形状合同(绑 IntakeOutput 自身 hash、无 snapshot——历史 run 无可信 pre-E4 基线,与稿 §8.1"historical standalone 不声称能证明 vertex drift"一致),保住全部历史 run 可跑。备选=也硬失败,但那会连 v1 anchor 都锁死。请审。
4. **guard 测试给 pipeline.py 开的 v3-producer 白名单**:pipeline 以 `schema_version == "3"` 决定"是否跑 enrichment 这个 producer 步骤"(enrichment 定义上 v3-only),合同 mode 仍全部出自 derive。稿字面是"全仓禁止重复写 schema_version == '3' 来决定坐标模式"——我判定 producer 选路不属"决定坐标模式",已在 guard 测试注释挑明。请审这个口径。
5. **legacy_unbound 拒绝非零 Building.North Axis 是行为收紧**:World 下 EP 本来只 warning+忽略;现 standalone 出口直接 BLOCK。按稿 §5.2 施工,但对 MCP 交互用户是可感知的破坏性变化。
6. **`verify_integrated_gate1_correction` 的 contract 推断**:integrated 路径依据 feature_states.claims(typed populated+phase e4)推断 artifact_contract。claims 由 finalize/enrichment 派生且 hash 绑 output,我认为不构成伪造面(伪造 claims 需同时伪造与 bytes 一致的 hash 且过 gate①),但这是 manifest 路径没有的推断步——请审。
7. **A4/A5 显式化使 legacy IDF 文本多两列**(值=IDD 默认,EP 语义零变化)。golden 未含 IDF byte 断言(验证过测试全绿),但若有外部 IDF byte diff 工具流会看到差异。
8. **registry 的 IDD ghost 台账**:`Building`/`Site:Location`/`DaylightingDevice:Tubular`/`DaylightingDevice:LightWell` 四行不在 IDD 短语启发式候选内(schema/producer 层登记),ghost 集合已用精确断言锁死,新漂移会红。启发式短语/字段标记清单是我按 25.1 IDD 实扫定的,IDD 升级时需重审。

## 七、稿章节→测试映射表

| 稿章节 | 测试落点 |
|---|---|
| §1.2 不变量 1（geometry invariant） | e2e 断言 1/4;identity `test_stepwise_enrichment_and_assembly_identity`(快照 hash);contract `test_enrichment_changes_only_north_axis_and_audit` |
| §1.2 不变量 2（single owner） | mep_assembly `test_s5_unconditional_override_all_thetas`/`test_s5_nonzero_mep_fails_even_when_equal_to_theta`;dispatch_guard workflow 门组 |
| §1.2 不变量 3（zero zone frame） | application 归零/幂等/offender 组;e2e `test_relative_variants_have_all_zero_zone_frames` |
| §1.2 不变量 4（explicit dispatch） | contract `test_theta_zero_and_ninety_take_the_same_mode_branch`;dispatch_guard 两条 grep 哨兵;e2e 断言 5(rel_000=0 hits) |
| §3.1 strict 类型/mode 矩阵/frozen | contract §10.1 组（extra/digest/NaN/360/负角/四混搭/manifest 身份形状/nested frozen） |
| §3.2 verifier+derive+factory | contract derive 矩阵组（v1 extra 不读/B2 冒充 BLOCK/digest 漂移/legacy factory）;identity `test_tampered_correction_output_breaks_the_chain` |
| §3.2bis 四表+audit 六字段 | contract `test_zero_evidence_prior_fill_generates_exact_assumed_zero`/interactive NEEDS_INPUT/conflict/multiple/hash 漂移/completion_mode 错配/`test_assumption_audit_*` |
| §3.2bis E4-R3 release map | identity release-map 六测（三 exact tuple/错序/漏 helper/phase 错配/north 未 populated/未知）+`test_no_stage_version_four_literal_outside_release_map`+`test_stepwise_enrichment_and_assembly_identity`(caller 传 "9" 仍记 "4") |
| §3.3 AgentState | application `test_contract_survives_pickle_and_agent_state_deep_copy` |
| §3.4 sidecar/加载优先级 | identity loader 五测（accepted attempt 读取/blocked 002 不影响/篡改断链/v3 无 sidecar 拒/纯历史→legacy/半对 sidecar 拒） |
| §3.5 assembly/parity 投影 | identity `test_integrated_and_manifest_refs_project_identically`;run 内 assemble_intake_artifacts 全链 |
| §4.1 S4 占位门 | mep_assembly `test_mep_north_axis_placeholder_zero_passes`/`negative_zero`/`nonzero_blocks[90/270/0.0001]` |
| §4.2 S5 override | mep_assembly S5 六测（0/90/270/无 conflict/相等也拒/model_copy 注入拒/round-trip 断言/legacy byte 不变） |
| §4.3 防回写 | dispatch_guard workflow 门组(门式,见未决 #5) |
| §5.1 GGR A4/A5 | application GGR 四测（默认/round-trip/坏 choice/IDF 三字段 Relative 与 legacy World-Relative-Relative 双锁） |
| §5.2 应用函数/调用点 | application apply 三测+seed 两表;zone_tools policy 两测;workflow 门四测 |
| §5.3 分派表+哨兵 | dispatch_guard 全组;contract mode 矩阵组 |
| §6 Zone 迁移 | application 归零/审计/幂等/late-write 拒/offender 全列/高层 z 保持/对抗 LLM 值 |
| §7.2/§7.3 registry 四层 | registry 全组（IDD 差集空/ghost 锁死/supported 集合精确/七类 unsupported BLOCK/site-world exempt/非空间对象不误伤/exclusion 有实理由） |
| §7.4 audit | identity S5 五 hash 逐名对账;AssemblyCoordinateAuditV1 placeholder==0 validator(经 identity 构造) |
| §8.1 validate 函数 | application `test_final_validator_lists_every_offender_sorted`;dispatch_guard workflow 门(经 `_coordinate_gate`→`validate_output_coordinate_contract`) |
| §8.2 六入口 | intake/simulate/CLI 接线经 test_intake_pipeline(3)/test_run_full_pipeline_shared(2)/test_ep_end_gate(8)/test_runner_shared(1);stepwise flow 入口见未决 #1 |
| §9/§10.7 EP 五断言 | e2e 8 测:五断言各一 test id+三条前置 sanity(fixture 非零 origin/rel 全零/名集相等 114+14) |
| §10.8 回归纪律 | 被改模块既有组全绿表;9 xfail 不变;零 golden(git status);E4 专用三容差常量 |

—— 施工完（工作树交付,未 commit）。

---

## 八、返工 r1（terra 接手，2026-07-14）

接手前先按审判词锚点核对工作树；前任已在树内完成 CR1–CR7 的大部分接线，本轮不信自报而以定向组和攻击负例复核，并补 CR8/CR9、§7.4 export/simulate/replay 证据闭环与缺测。

| finding / 测试族 | 结论 | r1 交付与锁定测试 |
|---|---|---|
| CR1 stepwise v3 | CLOSED | `run_stage` 在 S5 前 enrich accepted correction，使用同一 assembly API/`AssemblyE4Write`；`run_manifest_v2+step_orchestrator` 60 passed，identity 16 passed。 |
| CR2 六入口 sidecar/无合同 fallback | CLOSED | blocking gate hard-fail、flat sidecar、nested run-dir resolve 与 accepted-identity-only loader；intake/CLI/EP-end 13 passed。 |
| CR3 trusted evidence + real RunConfig | CLOSED | content-addressed evidence artifact、missing≠empty、`run_config.yaml` completion mode 和 hash-bound resolution；contract 31 passed。 |
| CR4 claims/hash chain | CLOSED | verifier/derive 均 fresh `derive_feature_state_claims()`、S5 five-artifact/input/ref checks；新增伪 populated-north claims 攻击负例，contract 31 + identity 16 passed。 |
| CR5 live IDF final gate | CLOSED | final gate 读取 Building/GGR A3-A5/all Zone frame/live vertices；新增 tampered-live-IDF 攻击负例，application 20 passed。 |
| CR6 registry four-layer | CLOSED | IDD/schema/converter/prod-route/live-IDF audits、ghost 双空、无 `or True`；registry 24 passed。 |
| CR7 audit chain | CLOSED | integrated/stepwise S5 strict audit；Zone normalization 随 AgentState 到 export，strict atomic export audit，simulate EP raw-hash audit，`validate_case` replay rehashes export/EP audits；identity/application/EP-end/validation baseline 定向组通过。 |
| CR8 early revalidation | CLOSED | cross-ref foundations/complete 与 validate-repair loop 均复验 contract；新增 missing-context graph-boundary negative，dispatch guard 7 passed。 |
| CR9 point write guard + frozen audit | CLOSED | BuildingTool direct North-Axis rewrite gate；strict frozen audit wire/tuple nested values；新增 direct-rewrite negative，application 20 passed。 |
| CR10 phase Literal | CLOSED | `CorrectionTarget` 和 claims phase 均收窄至 `b2|e4_orientation`；contract/identity groups pass。 |
| CR11 legacy comment | CLOSED | 注释改为 explicit A4/A5 的 EP semantic stability（非 IDF byte stability）；application 20 passed。 |
| CR12 provenance base | CLOSED | 本段及简报基座更正为 r1 `3123611` / current `b5ff6d6`。 |
| §10.1–§10.8 / §7.4 replay | CLOSED within B–O scope | strict/mode/evidence、GGR/Zone/live-IDF、identity/sidecar/retry, registry, entry parity, EP e2e 与 replay 覆盖均纳入上述专用组；未跑全量（主控权威 gate）。 |

### 定向测试（本返工复跑）

| group | result |
|---|---:|
| output-coordinate contract/application/identity/registry/dispatch | 31 / 20 / 16 / 24 / 7 passed |
| E4 EnergyPlus 25.1.0 e2e | 8 passed |
| MEP assembly | 40 passed |
| intake + full-pipeline shared + EP end gate | 13 passed |
| manifest + step orchestrator | 60 passed |
| pipeline self-check/kernel/evidence | 15 passed |
| runner/zone/intake assembly | 7 passed |
| correction stability + C2 B2 V3 + execution foundation | 70 passed, 1 existing serializer warning |
| validation baseline | 10 passed, 8 existing xfailed |

### 本轮文件与备份

本轮新增修改：`src/agent/state.py`、`src/agent/nodes/{zone,cross_ref,validate}.py`、`src/mcp/tools/{building,workflow}.py`、`src/agent/execution/validation_run.py`、`src/validator/output_coordinates.py` 及三组 E4 tests；未 commit、未改 golden。此前未备份的既有文件已按 HEAD 原字节备入 `backup/src_history/2026-07-12_bo_north_axis_wiring/`（不覆盖既有备份）。

### 新 review-ask（诚实）

1. `output_coordinate_ep_audit.json` 绑定本次 IDF/EIO/ERR 与 World-warning 断言；跨变体 azimuth/area/volume 的五条比较仍由专用 `test_e4_relative_north_axis_e2e.py` 完成，因为单次生产 simulate 无第二变体可比较。请确认该职责划分继续可接受。
2. `validate_case` 只在 E4 audit 已存在时重算/阻断，避免把历史 legacy run 的无 sidecar/audit 误判；新 E4 入口均会写 audit。请确认历史 replay 的这一兼容边界。
