# B-O 批施工执行交叉审判词（sol，2026-07-13）

**结论：REWORK —— 7 MAJOR + 2 MINOR + 3 NIT。**

审查基准为当前 `HEAD 3123611` 与其上未提交 working tree；唯一施工合同为 `AI_agent/proposals/c2_e4_output_contract_spec.md` v2。dispatch 与 execution brief 仅用于边界及自报缺口定位，不覆盖合同原文。

## 总体裁定

- **六入口对等：FAIL。** 合同 §0.2、§8.2、§10.6、DoD 都要求 integrated、stepwise、`--reading-from`、`--intake-from`、export-only、simulate 可用且对等。v3 stepwise 在 EP 入口 fail-closed 只证明没有静默降级；它没有交付 stepwise 功能，不能算合同等价实现。
- **禁止按 θ 猜模式：PASS。** 独立 `rg` 覆盖 `src/` 与 `scripts/`；未发现 `if theta`、`if north_axis`、`theta != 0` 等决定 World/Relative 的分支。现有 `north_axis != 0.0` 仅用于 S4/S5/legacy-unbound/终值硬门，不是模式分派。
- **release `"4"` 与 writer 派生：PASS。** `src/agent/correction/feature_state.py:118-169` 集中登记 exact helper/state 组合；`src/agent/execution/stage_runner.py:267-305` 在 writer 边界重派生 claims 并只经 `correction_stage_version(expected)` 写 release。除集中 map 外未发现生产代码赋值字面量 `"4"`。
- **S4 placeholder-0 + S5 无条件 override：PASS（仅合同感知路径）。** `src/validator/checks/mep.py:250-278` 对所有 profile 精确要求 numeric 0；`src/agent/intakeoutput.py:68-99` fresh rebuild 且无条件写 contract θ，不 mutation MEP。stepwise 仍调用无 contract 的旧装配 API，故批次总体不通过。
- **Zone zeroing/migration：PARTIAL。** seed、zone postprocess、late Zone tool 拒绝和 ConfigState gate 已落；live IDF 的四字段/Building/GGR/顶点终门没有落，见 BO-CR5。
- **building-bound registry：FAIL。** 只有 IDD heuristic 与 live object-type 两层；合同规定的 schema/converter 与 producer 路由层缺失，且 registry ghost 差集被明文豁免，见 BO-CR6。
- **legacy World：实现核心语义 PASS，完整 byte-stability 证据不足。** `serialize_geometry(..., frame_label="world")` 保留旧文案，11-field `IntakeOutput` 仍是 11 字段，`assemble_intake_output(..., output_coordinates=None)` 保留原对象；World Zone frame 保留。A4/A5 显式列会按合同要求改变 IDF 文本但不改变 EP 语义。缺少 v1/v2 完整 pipeline bytes/golden 回放测试，列入缺测。
- **dispatch 硬边界：PASS。** 未见顶点旋转、facade relabel、IntakeOutput 扩字段或 commit；21 个 tracked 改动文件的备份均存在且与 `git show HEAD:<path>` byte 相等。

## Findings

- **BO-CR1（MAJOR，stepwise v3 未施工，fail-closed 不等于入口对等）** —— `scripts/tool_scripts/run_stage.py:386-419` 的 `_draw_assembly()` 仍直接 `assemble_intake_output(..., mep=mep)`，没有加载 accepted correction、orientation enrichment、snapshot、`AssemblyE4Write` 或 `assembly_e4_v1`；`scripts/tool_scripts/run_stage.py:1295-1344` 到 EP 时才让 `load_intake_bundle()` 拒绝 v3。`StageRunner` 能写手工构造的 E4 attempt 只是底层能力测试，不是 flow 编排。合同明确把 stepwise 与 integrated parity 作为完成条件，故该自报 gap 是合同违反，必须返工而非带条件放行。

- **BO-CR2（MAJOR，其余入口仍存在无合同/丢 sidecar 路径）** —— `src/agent/pipeline.py:1023-1030,1208-1236` 在 exploratory gate① blocking 时继续生成无 contract、无 sidecar、无 θ override 的新 IntakeOutput，违反“新 E4 run 缺合同硬失败”；`scripts/run_full_pipeline.py:302-315` 的 flat `--intake-only` 只复制 `intake_output.json`，没有把两 sidecar 与之并列；`scripts/run_full_pipeline.py:237-249` 对任意 `--intake-from <run>/5_intakeoutput/...` 固定把 case root 当 `run_dir`，嵌套 stepwise run 无法取得其 manifest identity。六入口中至少 stepwise、flat intake-only、嵌套 `--intake-from` 和 exploratory edge 不满足同一 bundle 契约。

- **BO-CR3（MAJOR，prior_fill 输入不是受信 artifact，completion mode 也未消费真实 RunConfig）** —— `src/agent/pipeline.py:1061-1079` 无条件在内存新造空 `OrientationEvidenceSetV1()` 和 `OrientationRunConfigV1(completion_mode="prior_fill")`；没有读取/写入合同冻结的 content-addressed evidence-set 文件，也没有从运行配置取得 completion mode。缺 artifact 被实现成“空证据”，正是合同 §3.2bis 禁止的降级；interactive 入口因此在实际 integrated/stepwise orchestration 中不可达。`finalize_orientation_enrichment()` 的 assumed-0 值本身正确，但生产输入链不合约。

- **BO-CR4（MAJOR，accepted-correction/sidecar identity 验证不完整，可用伪 claims 升级 Relative）** —— `src/agent/output_coordinates.py:298-319` 仅凭 caller 提供的 `typed_north_axis == "populated"` 与 phase 字符串推断 `correction_e4_orientation_v1`，未用 `derive_feature_state_claims()` 核 exact helper tuple/四 states；`src/agent/output_coordinates.py:356-378` 派生时也只复验 typed north populated。独立负探针以 helper tuple 空、其余三 state `not_declared`、仅 typed north populated 的伪 claims 调 integrated verifier，仍成功得到 `correction_e4_orientation_v1 / relative_north_axis`。此外 `load_intake_bundle()` 在 `src/agent/output_coordinates.py:684-710` 只核 S5 的 output/contract/snapshot 三 hash，没有核 checks/audit、S5 input hashes、root mirror 或 contract source 与 accepted correction 的全字段相等；`src/agent/output_coordinates.py:712-740` 又把“有 v1/v2 correction 身份但无 sidecar”伪装成 `LegacyStandaloneIntakeRef`，越过唯一的“无任何 correction metadata”逃生口。

- **BO-CR5（MAJOR，所谓 post-convert/final IDF gate 不检查实际坐标字段）** —— `src/validator/output_coordinates.py:381-434` 只检查 ConfigState；传入 `idf` 后，`src/validator/output_coordinates.py:435-437` 仅调用 object-type registry。它不读取 live IDF 的 `Building.North_Axis`、GGR A3/A4/A5、每个 Zone 四字段，也不按 IDF 对 snapshot 顶点/宿主。独立负探针构造 ConfigState 合约正确、但 live IDF 为 Building=90、GGR=Relative/World/World、Zone=(10,-3,3.6,45) 的 legacy case，validator 返回空 issues。Converter 或 raw-IDF 注入可绕过最终门。

- **BO-CR6（MAJOR，闭世界 registry 没有合同规定的全层审计）** —— `src/validator/output_coordinates.py:193-271` 只实现 IDD 扫描，并明确允许 ghost 非空；`src/validator/output_coordinates.py:274-322` 只按 live IDF object type 判 supported/unsupported。不存在合同 §7.3 要求的 ConfigState/schema/converter 枚举差集，也不存在 producer/AST route 差集；field pattern 与 variant predicate 只是字符串台账，runtime 没有逐字段/宿主/predicate 执行。`tests/test_output_coordinate_registry.py:43-50` 锁定四个 ghost 而不是要求双空，`tests/test_output_coordinate_registry.py:142-149` 末断言含 `or True`。未来 converter/producer 坐标字段仍可漏登。

- **BO-CR7（MAJOR，§7.4 audit 证据链未完成）** —— integrated S5 在 `src/agent/pipeline.py:1275-1286` 只写 output 与两 sidecar，没有 `AssemblyCoordinateAuditV1`；`src/agent/nodes/zone.py:81-92` 生成的 normalization entries 仅日志后丢弃；`src/mcp/tools/workflow.py:131-172` 以裸 dict 写 export audit，缺 strict wire 要求的 `zone_normalizations` 与 `offenders`，且 registry candidate hash 只是静态注册名；`src/mcp/tools/workflow.py:396-450` simulate 后没有 `output_coordinate_ep_audit.json`。`validate_case`/replay 的 raw-hash 重算也未接。合同把这些作为可验证证据与 DoD，不是可选日志。

- **BO-CR8（MINOR，§5.2 调用点 3/4 与 repair-loop 复验缺失）** —— `src/agent/nodes/cross_ref.py:4-15` 和 `src/agent/nodes/validate.py:9-55` 仍只跑 reference validation；没有幂等 apply/validate output-coordinate contract。末端 Workflow gate 能捕获部分 ConfigState 漂移，但 parallel merge、checkpoint、retry 期间不能按合同在规定边界尽早发现或重建失效 identity。

- **BO-CR9（MINOR，防回写与 frozen audit wire 只做了一半）** —— `src/mcp/tools/building.py:15-40` 仍无 contract/policy，继承的 `src/mcp/tools/base.py:178-212` 可直接更新 North Axis；只能等末端门发现。另 `src/validator/output_coordinates.py:64-76` 的 frozen dataclass 内藏可 mutation `detail: dict`，`src/agent/output_coordinates.py:552-564` 又把 `offenders` 放宽为 `tuple[object, ...]`，违反 §7.4 的 strict+frozen nested collection 要求。

- **BO-CR10（NIT，contract phase 类型未按冻结 Literal 收窄）** —— `src/agent/correction/parse.py:12-17` 的 `CorrectionTarget.phase_contract` 与 `src/agent/correction/feature_state.py:16-24` 的 claims phase 仍为任意 `str`，不是合同冻结的 `"b2" | "e4_orientation"` strict surface。中央 release map 对 E4 有交叉门，当前不会直接误发 release，但 wire/schema 仍偏松。

- **BO-CR11（NIT，legacy byte 注释不准确）** —— `src/validator/data_model.py:693-698` 声称 A4/A5 默认可让 pre-E4 caller 发出 byte-identical IDF；`src/converters/setting_converter.py:180-194` 已无条件显式写两字段，所以 IDF 文本必然多列。合同要求此显式化，行为本身正确；应把注释改成“EP 语义不变”而非 bytes 不变。

- **BO-CR12（NIT，执行简报基座记录错误）** —— `AI_agent/logs/reviews/execution/2026-07-12_bo_construction_brief.md:5` 记基座 `4e3cb49`，本审委托与实际 `git rev-parse --short HEAD` 均为 `3123611`。不影响代码判定，但削弱 provenance。

## 8 项 review-ask 裁决

1. **REJECT。** exploratory gate① blocking 后继续无 accepted identity/无 contract 不是正确语义；合同要求新 run 缺合同硬失败，不能回到 pre-E4 装配。
2. **REJECT / MUST CHANGE。** 自动 integrated 可以由真实 RunConfig 明确选择/default 到 prior_fill，但不能在 pipeline 内硬编码并自造 hash-bound config；否则 interactive/配置漂移合同不可验证。
3. **REJECT。** 有 v1/v2 accepted correction metadata 就必须走 accepted-correction derive；`LegacyStandaloneIntakeRef` 只允许完全无 correction/run metadata 的历史 11-field 文件。若需 grandfather 旧 stepwise run，须回合同或生成显式 accepted legacy sidecar，不能冒充 standalone。
4. **ACCEPT（窄口径）。** `schema_version == "3"` 用来选择 v3-only enrichment producer，不等同从数值猜 coordinate mode；最终 mode 仍须只由 derive 产生。该接受不豁免 BO-CR2 的无合同 fallback。
5. **ACCEPT。** legacy-unbound World + nonzero Building axis 在 EP 中会被忽略；直接 BLOCK 是合同 §5.2 明令的可感知收紧，不是回归缺陷。
6. **REJECT。** claims 推断只有在 writer/verifier fresh 重派生 exact claims 并核完整 feature-state hash chain 时才成立；当前实现可被伪 helper/state claims 升级为 E4，独立探针已复现。
7. **ACCEPT。** legacy IDF 文本多 A4/A5 两列是合同明确要求的显式化；验收口径应是 EP 语义/11-field/spec bytes 稳定，不是最终 IDF 文本逐字节稳定。
8. **REJECT。** 固定 ghost 台账不能替代“IDD/registry 双空”，更不能替代缺失的 schema/converter/producer route 审计；IDD 升级风险只是次要问题，当前 25.1 合同已经未满足。

## 真正缺失的测试族

- **§10.1 类型/分派：** 缺字段、未知 schema、feature-state 各错误 state/helper/phase、run_id/attempt 漂移；“evidence artifact 文件缺失不等于空集”的真实 I/O 负例；最终 REPORT assumed 桶的 policy/knowledge N/A 收录。
- **§10.3 GGR/Zone/config：** parallel merge 后不退回 World；`cross_ref_foundations_node`/`validate_node`/repair loop；normalization entries 随 AgentState/checkpoint 到 export；post-convert live IDF 的 Building/GGR/Zone/顶点篡改负例。
- **§10.4 identity/sidecar：** integrated 真落 assembly audit；accepted 001→blocked 002 且 root mirror 被污染；snapshot/S5 output/checks/audit/manifest/input-hash 各自 tamper 矩阵；真实 writer 的 geometry-coordinate digest 前后不变；有 v1/v2 correction 身份但无 sidecar 的明确契约测试。
- **§10.5 registry：** schema/converter 与 producer route 两组差集双空；registry ghost 真双空；unknown spatial candidate 的 unclassified BLOCK；host-local window/door 的缺宿主、跨宿主 frame 校验（当前只是任何 host-local 对象一律 unsupported）。
- **§10.6 路径 parity：** 同一 correction/MEP/specs 的 integrated vs 实际 `run_stage flow` IntakeOutput bytes、snapshot bytes、GGR 与 Zone snapshot 全对账；真实 `--reading-from`、嵌套 `--intake-from`、flat intake-only、export-only、simulate 入口；correction retry digest 变化后的 2–5 invalidate/rebuild。
- **§10.7 EP E2E：** 两层迁移 fixture 的真实 EP run；负 x/y 的 L-shape v3 EP fixture；simulate 后 EP audit 的 EIO/ERR/raw-hash 验证。114 面/14 区四变体五断言已覆盖且通过。
- **§10.8 回归：** v1/v2 完整 pipeline 的 IntakeOutput/specs/audit byte fixture与旧 golden/anchor 对账；A0/config 对 phase/helper/wire/method/policy/三容差的 registration 测试。
- **§7.4 replay（跨族）：** export audit strict round-trip、zone normalization/offenders 内容、IDF/audit 替换、registry candidate 漂移，以及 `validate_case`/replay 现场重算。

## 自跑与独立证据

- `test_output_coordinate_contract/application/identity/registry/dispatch_guard + test_checks_mep_assembly`：**128 passed in 8.09s**。
- `test_e4_relative_north_axis_e2e + intake/CLI/EP-end/manifest/step-orchestrator`：**81 passed in 7.93s**；EP 四变体五断言在本轮复跑通过。
- live-IDF 负探针：明显错误的 Building/GGR/Zone 字段得到 **0 issues**，复现 BO-CR5。
- integrated claims 负探针：伪 helper/state claims 仍派生 `correction_e4_orientation_v1 / relative_north_axis`，复现 BO-CR4。
- `git diff --check`：通过；tracked 改动备份：**21/21 存在且与 HEAD bytes 相同**；IntakeOutput fields：**11**。

本轮未跑全量 suite；按 dispatch，全量 pytest 仍由主控终审独立执行。即使全量为绿，BO-CR1 至 BO-CR7 仍是合同结构性缺口，不能由现有测试通过抵消。

---

## 主控裁决（Fable，2026-07-13）

**REWORK 成立，八条 review-ask 裁定全部采纳。** 亲核记录：

- **BO-CR4 亲核坐实**：`output_coordinates.py` verify 段仅凭 caller 提供的 `claims.typed_north_axis=="populated" ∧ phase_contract=="e4_orientation"` 即发 `correction_e4_orientation_v1`，无 `derive_feature_state_claims()` fresh 重派生、无 helper tuple/四 state 精确核——**与 B-M CR-01（content hash 不重算 payload）、Vg CR1（writer 不重算 wire）同族信任根洞，本项目第三次出现**。返工必须 fresh 重派生+全链 hash 核，并加攻击负例锁死（前两批的既定修法模式）。
- **BO-CR5 亲核坐实**：终门第 3-5 项（Building 轴/GGR 三字段/Zone 四字段）全部读内存 ConfigState，live IDF 仅过 registry 对象类型扫描；ConfigState 正确+IDF 被改 → 0 issues。合同的"最终 IDF 门"语义未交付。
- **BO-CR1**：执行器自报事实+合同 §0.2 六入口对等为 In 边界，fail-closed ≠ 交付，无争议。
- 主控独立全量 pytest = **1011 passed + 9 xfailed**（903→1011）；绿不抵消 CR1-CR7 结构缺口，与 sol 结论一致。
- 处置：返工单发原施工代理（同上下文续跑），CR1-CR7+CR8/CR9+CR10-CR12 全修，§10.1-§10.8 缺失测试族按判词清单补齐；返工后 sol 复核 r2 + 主控再全量。
