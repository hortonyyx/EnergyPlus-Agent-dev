# F-20 修法设计稿：`validate_case` 接通 v3 accepted proof

- 日期：2026-08-10
- 出稿席：GPT 侧 sol
- 性质：设计稿；只读出稿，**不含生产码、测试码或脚本施工**
- 基点：`2d991e0`
- 结论：**选项①，且必须是“V2 账本严格受信、V1/无账本仅保留合法 legacy”形态。**

## 0. 一页结论

`validate_case` 应把 `_run/run_manifest.json` 分成三种状态，而不是只做“有／无”二分：

1. **没有账本**：只允许 schema v1/v2 沿用今天的 stage-root 离线审计；v3 因无法取得凭证而硬失败。
2. **V1 账本**：它是项目明定的 grandfathered legacy，只允许 schema v1/v2 沿用今天的行为；不得自动升级，也不得承载 v3。
3. **V2 账本**：accepted attempt 是权威来源。必须调用现有 `load_verified_accepted_correction(...)`，把它返回的 accepted geometry、`VerifiedWindowHostProof` 及已验真的 window evidence 作为一个整体交给下游；任何加载、哈希、缺件、合同或重验失败都硬阻断，**绝不回退 stage-root 便利副本**。

凭证必须在同一次改动里送到三个既有消费口：

- `check_correction(..., window_host_proof=..., window_evidence=...)`
- `build_geometry(..., window_host_proof=...)`
- `check_kernel(..., window_host_proof=...)`

结构性取证失败新增独立检查 `correction.accepted_artifact_trust`，放在 `1_correction` 的报告中；它不再伪装成 `2_modelling.build / kernel build failed`。这条检查始终属于 `CheckLayer.INVARIANT`。

## 1. 契约考古结论（先找用途，再设计改动）

本稿不删除或推翻现有 stage-root 入口、V1 grandfather 标记、便利镜像或两处历史注释。相关提交原文给出的用途如下：

- `0d267bf`：`validate_case` 是不侵入生产流水线的离线审计面；老的、手工形成的 run 也能被审。
- `06d01a0`：stage-root correction 重建用于核对磁盘 2/3 产物，保证 approval digest 绝不绑定陈旧／垃圾的 `building_geometry.json` 或 `geometry_specs.md`。它没有禁止读取 accepted attempt。
- `963d952`：`validation_manifest.json` 的独立文件名是为了不覆盖／冒充审计账本；它管输出名，不管输入来源。
- `b14af01`：V1/V2 是明确分开的 wire；V1 是 grandfathered、只读，升级只能显式迁移，不能静默发生。
- `bac689b`：stage-root 两份 correction 文件是“gate acceptance 后才晋升”的 convenience copies；同次写入的 accepted `output.json` 才有 V2 hash 身份。该提交还把 per-floor footprint 留在版本化 schema 接缝内。
- `2885a84`：v3 构建无条件要求 `VerifiedWindowHostProof`，包括零窗输出；legacy 又明确禁止接收 B5 proof。
- `e645d63`：accepted geometry bytes 与 B5 proof 是一个受信边界；六件套要全验，并明确删除 v3→B2 的兼容后门。
- `15ea05d`：项目刚把两处“未知新严格档默认宽松”的 fail-open 翻成 fail-closed；本稿沿用同一纪律。

因此，①不是把离线审计面改造成“所有历史 run 必须有账本”，也不是删除 stage-root 契约；它只是规定：**一旦 V2 正式账本存在，就不能绕开它另信一份便利副本。** 无账本和 V1 的 legacy 出口继续保留。

## 2. §4 七问逐条回答

### 2.1 问题 1：选项定夺

**选项①，条件分支形态；不另造第三条生产路径。**

理由：

- 它复用现成且已有生产调用的受信加载器，不新增写入面，也不新增任何 proof 文件副本。
- V2 accepted attempt 的六件套逐字节受 manifest hash 约束；篡改权威文件必被抓。
- 它把 accepted geometry 与 proof 作为同一身份整体交付，符合 `e645d63` 已立的边界。
- 对无账本和 V1 legacy 留显式出口，保住两个仍在用的 no-manifest golden anchor。
- 分支只看版本化 manifest/schema/artifact contract，不读取或推断 footprint、楼层满铺、层高、窗所在 cardinal facade 等当前简化事实。

**不选选项②。它会在以下时候咬人：**

- 今天：stage-root 便利副本中一个不影响几何的标签字段被改，现有检查可能完全看不见；调查的 `windows[0].room` 对照已实测如此。
- 下一次 correction writer 或 proof wire 加字段／加 sidecar 时：attempt 与 stage root 两套手写清单必须同步，漏一处便形成两份事实。
- 未来加入 per-floor footprint、退台、挑空、双层高或中庭 void 时：artifact contract 很可能继续扩展；镜像方案会随复杂度扩大漂移面，而 manifest loader 只需按版本化合同扩展一次。
- 维护者误以为“复制成功等于受信”时：便利副本没有 accepted hash 身份，安全强度不会因文件齐全而自动出现。

**选项①自身会咬人的条件：**若把分支误写成“任何 run 都必须有 V2 账本”，两个 no-manifest golden 会被误杀；若在 V2 加载失败后回退 stage root，则会重新制造 fail-open。本稿用三态分支和相反方向的锁分别钉住这两点。

### 2.2 问题 2：条件分支的确切语义

新增检查固定为：

- `check_id`：`correction.accepted_artifact_trust`
- `CheckLayer`：所有分支均为 `INVARIANT`
- 所在报告：`res.reports["1_correction"]`

状态与控制流如下：

| 盘上状态 | `CheckStatus` | 后续行为 |
|---|---|---|
| 无 manifest，stage-root geometry 是 v1/v2 | `NOT_APPLICABLE` | 保留今天的 stage-root 行为；proof/evidence 均为 `None`；可继续 2/3 重建 |
| manifest 是合法 V1，stage-root geometry 是 v1/v2 | `NOT_APPLICABLE` | 同上；消息明确写 grandfathered V1，绝不自动迁移 |
| 无 manifest 或 V1 manifest，但 geometry 是 v3 | `FAIL` | 凭证来源不存在；不进 2/3 重建，不出 digest |
| manifest 文件存在但 JSON／版本／schema 无法解析 | `FAIL` | 这是磁盘审计材料无效，不是检查器自身崩溃；不回退 stage root |
| V2 缺 accepted `1_correction` 指针 | `FAIL` | 不回退 stage root；不进 2/3 |
| V2 accepted `output.json` 或任一已声明 artifact 哈希不符 | `FAIL` | 不回退；不进 2/3；digest 为 `None` |
| V2/B5 合同要求的六件套任一缺件 | `FAIL` | 同上。包括 `output/checks/audit/feature_states/window_resolver_inputs/window_hosts`；合法 legacy contract 不凭空要求 B5 专属件 |
| accepted geometry 是 v3，但 `artifact_contract` 不是 `correction_b5_v1` 或 `correction_b5_orientation_v1` | `FAIL` | 明确拒绝 v3→B2/base/migrated 兼容后门 |
| accepted geometry 是 v1/v2，且其 legacy contract 与 hash chain 合法 | `PASS` | 以 accepted geometry 为权威继续，proof/evidence 为 `None`；legacy build 语义不变 |
| accepted geometry 是 v3，B5 六件套及 raw reading/view-manifest 重验全过 | `PASS` | 以 accepted geometry + proof + evidence 整体继续 |
| 已知磁盘／载荷异常以外的意外代码异常 | `ERROR` | 仍为 INVARIANT/BLOCK；不回退；保留异常类型供诊断 |

特别限定：

- “`artifact_contract` 不是 B5”只在 **accepted output 确为 v3** 时是失败；合法 v1/v2 本来就不应伪装成 B5。
- `ValueError`／Pydantic validation error／合同要求的文件不存在等由磁盘载荷触发的可预期拒绝，记 `FAIL`；权限拒绝、设备级 I/O 故障或检查代码本身的未知异常记 `ERROR`。两者在 INVARIANT 层都 BLOCK。
- V2 分支一旦开始，任何失败都不能进入 no-manifest/V1 分支。不得写 `except: use snapped`、不得把 proof 置空后继续。
- V2 分支使用 loader 返回的 accepted output，不把 stage-root convenience copy重新升格为第二权威。现有 required-artifact guard 暂不删除；是否以后取消 V2 下对 convenience copy“必须存在”的要求，不属于 F-20。

### 2.3 问题 3：Q4 独立出口要不要做

**要做。名称为 `correction.accepted_artifact_trust`，放在 `1_correction`，不采用示例名 `2_modelling.window_host_proof_unavailable`。**

理由：哈希、六件套、accepted 指针和 artifact contract 都是 correction accepted-artifact 的信任问题；失败时内核根本没有获得合法输入，称作“kernel build failed”会错误归因。“unavailable”也覆盖不了“材料存在但被篡改／合同伪装”的事实。

控制边界：

- 受信检查 `FAIL/ERROR` 后，设置本轮 geometry consistency 为 false，跳过 2/3 rebuild，保证 digest 为空。
- 只有受信检查为 `PASS` 或合法 legacy 的 `NOT_APPLICABLE` 时才进入现有 kernel `try`。
- 进入 kernel 后发生的真实建模／序列化异常仍走现有 `2_modelling.build + ERROR + INVARIANT`；不改它的职责。
- 新检查必须同时有 `PASS` 行；否则“永远失败的 trust gate”会让所有负锁永久假绿。

把新行放在 `1_correction` 还有一个兼容性理由：legacy 的 `NOT_APPLICABLE` 不会进入 geometry checkpoint digest 所哈希的 `2_modelling` report，因此不会仅因 F-20 让旧 approval digest 全部失效。

### 2.4 问题 4：legacy／无账本 run

选择 **① 整道几何确认门照旧能过**。

更精确地说：

- 对 schema v1/v2 的无账本或 V1 run，新 trust 子检查显示 `NOT_APPLICABLE`，但 `1_correction`、`2_modelling` 和 geometry checkpoint 整体照常运行；这不是把整道门降级为 N/A。
- legacy 的 `build_geometry(..., proof=None)` 与 `check_kernel(..., proof=None)` 保持原样；`kernel.window_parent_binding` 仍按现有合同显示 legacy N/A。
- 新行不放进 kernel report，旧 geometry digest 的输入形状不变；两个 no-manifest golden 不应因 F-20 新增 blocker 或 digest 漂移。
- 无账本／V1 中若实际塞的是 v3，则不属于“老产物继续可审”，而是“新合同绕过信任根”，必须 `FAIL`。

### 2.5 问题 5：`--intake-from`／`DOWNSTREAM_ONLY`

**不受影响。** 现有 early return 在 required-artifact guard、manifest 解析和 0–4 逻辑之前。F-20 的 resolver 必须留在这个 return 之后；不得为了“统一初始化”把 manifest/proof 加载提到函数顶部。

该路径继续只产生 `5_intakeoutput` report，geometry digest 仍为 `None`。锁中会用一份故意损坏的上游账本证明：完整校验会阻断，而 downstream-only 仍完全不触碰它。

### 2.6 问题 6：锁怎么配

采用**程序化最小夹具**，不把 1.3 MB 真实 run 纳入本次修法。基础砖是 `tests/test_c2_b5_artifact_trust.py::_accepted(tmp_path)`；它已通过 `StageRunner.record(...)` 形成真实 V2 accepted attempt、六件套、view manifest 和 raw reading。测试再用现有 canonical serializer 在临时目录补齐 2/3 产物。

完整锁清单见 §4。最少必须同时观察：

- 新 trust 行 `PASS`；
- `correction.window_host_resolution` `PASS`；
- `kernel.window_parent_binding` `PASS`；
- `2_modelling` report 通过；
- geometry digest 非空，且真实 `approve_geometry(...)` 能返回检查点；
- 任一 trust 失败后 digest 为空，且没有 stage-root fallback。

### 2.7 问题 7：施工顺序

可以分步开发，**不能把三个 proof 消费口拆成可发布的独立落地点**。安全顺序及危险中间态见 §5；合并时建议一个原子提交，或至少保证任何中间提交都不进入共享绿色基线。

## 3. 改动清单（伪代码，不是可粘贴实现）

### 3.1 `src/agent/execution/validation_run.py`

新增一个仅供离线校验使用的私有 resolver（名称可由施工席微调），职责只包括“选择受信 correction source + 形成 trust 事实”，不做任何几何推导：

```text
resolve correction source:
    查看 manifest 文件状态并用版本 dispatcher 解析

    若不存在:
        读取现有 stage-root geometry
        legacy -> (geometry, no proof, no evidence, NOT_APPLICABLE)
        v3     -> (no trusted source, FAIL)

    若为 V1:
        读取现有 stage-root geometry
        legacy -> (geometry, no proof, no evidence, NOT_APPLICABLE)
        v3     -> (no trusted source, FAIL)

    若为 V2:
        调现有 accepted loader；任何拒绝都返回 FAIL，不 fallback
        从 verified raw output 构造 geometry
        legacy -> proof/evidence 都必须为空，返回 PASS
        v3     -> proof 与 raw host evidence 必须齐全；返回 PASS

    非载荷型意外异常 -> ERROR
```

在 `validate_case(...)` 的现有 1_correction/2/3 段调整数据流：

```text
source = resolver(...)

若有可检查 geometry:
    correction report = check_correction(
        geometry,
        proof=source.proof,
        evidence=source.window_evidence,
        其余现有参数不变,
    )
否则:
    建一个 1_correction report 保存 trust failure

把 correction.accepted_artifact_trust 的 PASS/N_A/FAIL/ERROR 加入该 report
写报告动作延后到新行加入之后

若 trust BLOCK:
    geometry_consistent = false
    不调用 build_geometry / check_kernel / serializer
否则:
    build_geometry(..., window_host_proof=source.proof)
    check_kernel(..., window_host_proof=source.proof)
    其余 2/3 磁盘一致性与 digest 逻辑保持现状
```

实现边界：

- v3 evidence 从 loader 已验真的 `raw_window_hosts_bytes` 解析得到；不从 stage-root 新造 claims，不自行重算一套替代 proof。
- 无 geometry 可供普通 correction checks 运行时，新建的 trust-only report 也必须显式带入当前 `capability_profile` 与 `run_profile`；不得依赖默认档。
- 不修改 `load_verified_accepted_correction`、`VerifiedWindowHostProof`、`build_geometry` 的合同。
- 不把 accepted-loader 的异常文本当稳定 API；新 check_id/status/reason code 才是稳定诊断面。
- 不移动 `DOWNSTREAM_ONLY` early return。
- 不删除 snapped required-artifact guard、两条历史注释或 validation summary 独立文件名。

### 3.2 `tests/test_c2_b5_artifact_trust.py`

- 复用并小幅扩展 `_accepted(...)`，允许有窗／零窗两种 B5 accepted fixture。
- 增加 F-20 正向、fail-closed、legacy 和诊断映射锁；所有写盘只发生在 pytest `tmp_path`。
- 用 `building_geometry_json`、`serialize_geometry`、`geometry_specs_markdown` 生成 2/3；不手写方盒坐标期望，不复制真实 run。

### 3.3 `tests/test_check_parity.py`

在 `_EXCLUDED_VALIDATE_CHECKS` 明列：

```text
(1_correction, correction.accepted_artifact_trust)
    原因：这是 validate_case 离线审计面专有的“盘上 accepted chain 重验”；
          inline pipeline 使用的是刚签发的内存 verified bundle，不存在同一盘上重放检查。
```

该豁免符合 `fea6981` 建表时“离线专属检查必须逐条具名解释”的合同；不得用前缀或整 stage 批量豁免。

### 3.4 明确不改

- 不改 `src/agent/execution/stage_runner.py`，不新增三份 stage-root 镜像。
- 不改 `src/agent/output_coordinates.py` 的信任根算法。
- 不改 `src/agent/geometry/build.py` 的 v3 强制 proof／legacy 禁 proof 门。
- 不改 `scripts/tool_scripts/run_stage.py`。
- 不读、不 import `case_tests/test_baseline/gt/`。

## 4. 锁清单

所有 F-20 新负锁先在同一个干净夹具上断言 trust `PASS` 且 geometry digest 非空，再做单一变异；这样“门恒红”会先在正向对照处大声失败。底层已有的六件套 19 个 anti-tamper 锁继续保留，但它们不替代本节的 `validate_case` 集成锁。

### L1 正向锁：v3 accepted proof 贯通三个消费口

- **锁什么**：有窗和零窗两种 v3 都得到 trust `PASS`；校正宿主检查、内核父墙绑定均 `PASS`；2_modelling 通过；digest 非空；真实 geometry approval 能签发。
- **夹具怎么来**：`_accepted(tmp_path, include_window=True/False)` + canonical 2/3 writers；为 approval 冻结 `orthogonal_polygon` policy。断言只看身份／状态，不看方形尺寸、固定层高或对象计数。
- **自证前提怎么写**：在调用修后入口前，分别断言同一 geometry 直接无 proof 构建会抛 `v3 build requires...`、无 proof/evidence 的 correction check 会产生 `correction.window_host_resolution` blocker、无 proof 的 kernel check 会产生 `kernel.window_parent_binding` blocker。任一前提消失立即 fail，不把夹具静默当成 legacy／空锁。
- **不加修法它红不红**：**红**。已在 `/tmp` 用该砖实测，现状 correction host FAIL、`2_modelling.build` ERROR、digest 为 `None`。

L1 的末段再放一条 scope 守恒断言：把上游账本改成完整校验必拒的状态后，用一份合法 IntakeOutput 跑 downstream-only，仍只得到 S5 报告。该断言与前面的 F-20 正向段同测，因此整把锁在修前仍为红；现有 `test_downstream_only_scope_skips_geometry` 继续作为独立旧哨兵，但不冒充“修前会红”的 F-20 证据。

### L2 fail-closed 锁：accepted output 哈希不符

- **锁什么**：V2 accepted `output.json` 被改、manifest hash 不改时，新 trust 行为 `FAIL/INVARIANT`，digest 为空，错误不落入 generic kernel bucket，且绝不使用仍然干净的 stage-root copy。
- **夹具怎么来**：先跑 L1 同形干净对照；随后只改 attempt 中一个非几何标签字段，stage-root 原样保留。
- **自证前提怎么写**：变异前显式断言 trust `PASS`、digest 非空；变异后先断言 stage-root bytes 未变，避免测试误把两边一起弄坏。
- **不加修法它红不红**：**红**。修前没有专用 check_id，干净对照本身也因缺 proof 无 digest。

### L3 fail-closed 锁：六件套缺件

- **锁什么**：删掉一个 proof 承重件（首选 `window_hosts.json`）后映射为 `correction.accepted_artifact_trust = FAIL/INVARIANT`，不 fallback、不出 digest。
- **夹具怎么来**：L1 同形夹具；干净对照后只删 attempt 中该文件。底层现有 `test_tamper_14_each_missing_six_artifact_is_rejected` 继续参数化覆盖全部六件，本集成锁只验证“loader 拒绝如何进入 validate report”。
- **自证前提怎么写**：先断言六个文件和六个 manifest key 精确齐全、干净 validate 为正；再只删一个。如果 fixture 将来没生成该文件，测试在变异前就大声失败。
- **不加修法它红不红**：**红**。专用映射不存在，且修前正向对照过不了。

### L4 fail-closed 锁：v3 被降格成非 B5 contract

- **锁什么**：v3 output 即使仍可解析，也不能挂在 B2/base/migrated contract 下继续；trust `FAIL`，digest 为空。
- **夹具怎么来**：复用现有 `test_d2_accepted_loader_rejects_v3_record_downgraded_to_b2_without_proof` 的变异法，在干净集成对照后改 record contract、移除对应 B5 keys/files，并把变异后的 manifest 重新保存到临时 run。
- **自证前提怎么写**：变异前断言 output schema 为 3、record contract 为 B5、clean trust 为 `PASS`；变异后断言 wire 仍是一个可加载的 V2 manifest，避免只测到“JSON 写坏了”。
- **不加修法它红不红**：**红**。修前没有专用 trust 行，clean control 也红。

### L5 权威来源锁：V2 不回信 stage-root convenience copy

- **锁什么**：accepted attempt 保持干净、只篡改 stage-root 非权威副本时，V2 审计仍以 accepted output + proof 为一体；反方向篡改 accepted attempt 则由 L2 必拒。两把锁共同钉住“谁是权威”。
- **夹具怎么来**：L1 夹具；只改 stage-root `room` 标签，attempt/manifest 不动。
- **自证前提怎么写**：先断言两份 bytes 原本相同；变异后断言只剩 stage-root hash 改变、accepted hash 仍等于 manifest。若两边同时变，立刻 fail。
- **不加修法它红不红**：**红**。修前 v3 无 proof，无法形成 digest；修后该锁同时防止实现误从 stage root 取 geometry、再与 accepted proof 混搭。

### L6 legacy 配对锁：无账本与 V1 继续可审

- **锁什么**：同一个配对测试先证明 V2/v3 正向路径能过，再证明 schema v1/v2 在“无 manifest”和“合法 V1 manifest”两种参数下，trust 行均为 `NOT_APPLICABLE/INVARIANT`，2_modelling 仍通过，digest 与修前冻结值相同且非空；validate 不写入／升级账本。
- **夹具怎么来**：第一半复用 L1；第二半用程序化 legacy geometry + canonical 2/3，分别不放 manifest、放一个真实 `RunManifestV1`。旧 digest 用施工前冻结的 fixture 值（或等价 frozen report）对比，不在修后临时“算一个期望值”。另保留两个 golden anchor 的 targeted replay，确认没有新增 F-20 blocker。
- **自证前提怎么写**：V2/v3 半先执行 L1 的三项无-proof 红态断言；legacy 半先断言 schema 不是 3，V1 参数下断言 dispatcher 返回的确是 V1且受信 accepted loader 明确拒绝“v1 runs are legacy-only”，无账本参数下断言调用前后 manifest 都不存在。
- **不加修法它红不红**：**整把配对锁红**，而且红在 V2/v3 正向半的真实 F-20 缺陷上；legacy 半的通过语义修前本来就绿。不得把后者伪报成“修前 legacy 失败”，也不得只靠“新增 check_id 尚不存在”制造形式红。

### L7 legacy 反向锁：V1／无账本不得夹带 v3

- **锁什么**：同一份 v3 stage-root geometry 把 V2 manifest 去掉或替换成 V1 后，trust `FAIL/INVARIANT`，不进 kernel，digest 为空。
- **夹具怎么来**：L1 夹具，仅替换 manifest 状态；stage-root v3 和 canonical 2/3 保持。
- **自证前提怎么写**：先断言 direct no-proof build 确实会抛错，并断言 dispatcher 状态确为 None/V1；防止 fixture 悄悄还留着 V2。
- **不加修法它红不红**：**红**。修前只得到 generic kernel error，没有指定 check_id/status；正向 V2 对照也过不了。

### L8 诊断分层锁：未知代码异常是 ERROR，不是数据 FAIL

- **锁什么**：让 accepted resolver 抛一个非数据型哨兵异常时，`correction.accepted_artifact_trust = ERROR/INVARIANT`，无 fallback、无 digest；普通 hash/缺件仍是 `FAIL`。
- **夹具怎么来**：L1 夹具；仅 monkeypatch 新私有 resolver 内调用的 loader 为抛哨兵异常，不改磁盘。
- **自证前提怎么写**：先用未 patch 的同夹具断言 `PASS`，再确认哨兵异常确实被触发一次；零调用或多调用都 fail。
- **不加修法它红不红**：**红**。修前不会触发该受信调用，也没有新 check_id。

## 5. 分步施工与危险中间态

推荐开发／落地顺序：

1. **先加 fixture assertion 和 F-20 锁，确认定向红。** 只可留在施工分支，不能单独并入绿色主线。
2. **加入三态 resolver、稳定 check_id/status/reason、parity 具名豁免。** 此步若尚未线程化三个消费口，v3 仍会红；它是 fail-closed 的不完整态，不是假绿，但不应发布。
3. **一个原子改动同时线程化 correction check、geometry build、kernel check，并在 trust BLOCK 时完全跳过 kernel。** 这是承重施工步，不拆。
4. **先跑 L1 正向与 L2–L8 定向锁，再跑 `tests/test_check_parity.py` 和两个 legacy targeted baseline；不需要为 F-20 跑全仓。** 全仓是否跑由后续 gate/施工流程另定，本稿不授权。
5. **对抗审确认后再合并。** 不改 stage runner、不补镜像、不顺手迁移 V1。

危险中间态：

| 单独落地的部分 | 中间态 | 危险度／处置 |
|---|---|---|
| 只有 loader 调用，但 `except` 后回 stage root | 篡改／缺件反而触发旧便利副本继续 | **禁止**，典型 fail-open |
| 只把 proof 给 `build_geometry` | build 能走，`kernel.window_parent_binding` 仍因无 proof 失败 | fail-closed 但未修完；不得发布 |
| 把 proof 给 build + kernel，却没给 correction 的 proof/evidence | 2_modelling 可能通过并产生 digest，但 `correction.window_host_resolution` 仍 FAIL；`approve_geometry` 目前只看 digest 是否存在，可能签发一个上游仍阻断的检查点 | **最危险，三个消费口必须原子落地** |
| 只给 correction，不给 build/kernel | correction 绿，2_modelling 仍红 | fail-closed 但未修完；不得发布 |
| 把 legacy N/A 行塞进 kernel report | 老 geometry digest 输入变化，既有 approval 全部变 stale | **禁止**；新行放 1_correction |
| 新增 check_id 却不更新显式 parity 豁免 | parity 测试红 | 安全但 CI 不可合并；必须同批具名解释 |
| 改成镜像三件套 | 进入选项②，产生第二物理事实与无 hash 权威面 | **不属于本设计，禁止夹带** |

## 6. 建筑复杂度可扩展性复核

本设计不新增任何 footprint／楼层／层高／facade 推断：

- resolver 只分辨 manifest version、accepted artifact contract 和 schema version；geometry 内容作为版本化对象整体传递。
- 窗宿主仍由 B5 proof 中的 segment/room identity 与现有 deterministic kernel 重验；`validate_case` 不自行用矩形边、共底面或 cardinal span 重建宿主。
- accepted loader 未来若扩展到 per-floor footprint、退台、void／atrium sidecar，只需在版本化 artifact contract 的单一信任根扩展；本分支无需改成“每层满铺”的特判。
- 锁只断言 proof 身份、检查状态和 digest，不冻结“一个方形、一层、3 米层高、固定窗数”等数值。最小方形 fixture 只是便宜的接线载体，不成为生产算法前提。
- 零窗也参数化正向通过，防止施工写出 `if windows: load proof` 这种会绕过“zero-window 也必须有 proof”的后门。

因此该修法不烤死非方形、退台、挑空或中庭路径；相反，拒绝手写镜像清单减少了复杂 schema 扩展时的轴 B 漂移面。

## 7. 需用户拍板的点（白话）

**背景**：项目现在同时保留两类历史文件夹。老文件夹没有后来新增的正式记账系统，但仍需要继续被检查；新文件夹有一份正式记录，里面写明哪次结果被接受，并给每份材料附了防伪指纹。

**问题**：新版本重算窗和墙的关系时，检查员必须拿到一套可信凭证。凭证只在正式记录指向的那份材料里完整存在；旁边的方便副本既不完整，也没有同等防伪身份。需要决定新文件夹到底信正式记录，还是继续扩充方便副本。

**每个选项的后果**：信正式记录，可以抓住任何被改动或缺失的材料；正式记录一旦损坏就会大声停下，但老文件夹仍按老办法检查。扩充方便副本，表面改动较小，却会多出三份手工复制品；实测有人只改一个标签时检查员可能完全看不见，未来建筑支持退台、挑空或中庭后还会继续增加同步负担。

**推荐与理由**：建议同意“新文件夹信正式记录、老文件夹保留旧入口”，并同时把“凭证材料有问题”和“几何内核坏了”分成两种清楚的报错。理由是它防篡改更强、不会误杀仍在用的老样本，也不给未来复杂建筑再造第二套材料事实。**本稿需要用户拍板的唯一点，就是是否接受这条原则。**

## 8. 我没能确定的部分

1. **修后完整 `validate_case` 尚未真实跑绿。** 本轮禁止改生产码；我只在 `/tmp` 坐实了同一 `_accepted()` fixture 的修前红态，并手工把现有 loader 输出送入三个现有消费口，得到 correction/kernel 均通过。最终集成绿必须由施工席用 L1 证明。
2. **真实 1.3 MB run 未作为修后夹具跑通。** 本稿选择程序化最小 fixture，未声称 `run_2026-08-09_f18_e2e_verify` 在修后端到端已绿；调查报告也明确没有证实这一点。
3. **受信加载器没有稳定的 typed error code 枚举。** 可以稳定承诺的是新 check_id、layer、status 与少量本地 reason category；不能把当前 `ValueError` 逐字消息写成长期 API。若要细分“哪一个哈希／哪一个文件”的机器码，需要另开小设计，不能靠匹配英文异常文本补。
4. **没有枚举所有 V2 legacy run 的 accepted output 是否与今天 `validate_case` 所读的 stage-root convenience copy 语义一致。** 本设计明确规定 V2 下 accepted attempt 为权威；若施工 targeted replay 发现这会改变某个历史 V2 legacy run 的几何结果，应停下上报其差异和影响，而不是悄悄回退 convenience copy。
5. **未复核“生产调用点究竟算 6 个还是 7 个独立入口”。** 它不影响本稿：F-20 只复用既有 loader，不改其他调用者；因此没有用该数字承担任何设计结论。

## 9. 合法退出口复核

- 这不是伪岔口：两条路的权威来源、防篡改与副本数量实质不同。
- 未发现调查报告承重实测被反证；轻门指出的 loader 出生日期更正和复制假阳性均已吸收，未把它们写成设计依据。
- 未发现请求书内部硬约束冲突。
- 本稿所需信息均来自请求书列出的产物、相关现行源码及引入这些契约的提交说明；没有读取 gt。

结论：**可以出稿，不触发 §7 停止上报。**
