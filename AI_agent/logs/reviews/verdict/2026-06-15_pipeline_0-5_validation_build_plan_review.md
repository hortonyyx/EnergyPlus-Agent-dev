# 审阅结果 · 0–5 校验架构施工方案

> 审阅执行：Codex，2026-06-15  
> 审阅对象：`architecture/pipeline_validation_build_plan.md`  
> 请求：`request/2026-06-15_pipeline_0-5_validation_build_plan_request.md`

## Verdict

**CHANGES REQUESTED。**

模块方向基本合理，且“先 M2 确定性、后 M3 judge”是正确施工原则。但当前计划把最难的
跨阶段问题放进了一个尚不存在的 harness：没有 stage runner、checkpoint 失效、resume、
attempt 留档和人工批准绑定，就无法安全实现根因路由、0_reading 重抽或 2/3 后暂停。

建议在现 M1 前增加“执行地基”，并先补 reading schema 与 IDF-fragment parser，再按段
合并 validators。下面给出可直接替换的依赖序。

## Findings

### High 1 - 缺少 stage execution/checkpoint 层，M3 根因路由与 M4 用户暂停无法落地

**对应：B2 / B5 / B7。**

**证据**

- 当前 `run_pipeline` 是 1→5 单体函数；0_reading 是外部目录，不是 callable runner。
- `pipeline_validation_build_plan.md` 直接在 M2 把 checks 接入 `pipeline.py`，M3 再加
  “根因阶段重跑”，M4 在 2/3 后暂停等用户。
- 计划没有定义 stage input/output manifest、下游失效规则、resume 入口或 approval
  与产物版本的绑定。

**影响**

- judge 路由到 0 时无函数可重读；
- 重跑 1 会使 2→5 全部失效，但计划没有原子清理/新 attempt 目录；
- 用户确认 2/3 后若重新执行命令，1_correction 会再次采样，确认的几何不再是随后使用的
  几何；
- 现有 raw/check 文件会被覆盖，无法复盘被拒 draw，也无法作为训练数据工厂。

**建议**

在 F1 前新增 **E0 execution foundation**：

1. `StageRunner`/stage registry：声明 stage id、input artifact hashes、runner capability
   （manual/stochastic/deterministic）、outputs。
2. append-only attempt 布局，例如
   `<stage>/attempts/001/{output,checks,judge}.json`，另有 `run_manifest.json` 指向 accepted
   attempt；不得覆盖失败 draw。
3. 明确 invalidation DAG：重跑 0 失效 1-5；重跑 1 失效 2-5；重跑 4 只失效 5。
4. `resume_from_checkpoint`：M4 批准后从已批准 geometry hash 继续 4/5，不再重抽 1。
5. `geometry_approval.json` 记录 artifact hash、policy、actor、timestamp。
6. 当前 0 runner 标 `manual`，自动路由只返回 `human_redraw_required`；未来 VLM 接入再
   改为 stochastic。

没有这层，不建议先把 gate 直接散接进 `pipeline.py`。

### High 2 - `_make_correction_validator` 不能作为通用 judge harness 复用

**对应：B3 / B5。**

**证据**

- `_make_correction_validator` 返回 `Callable[[dict], None]`，只负责拒绝一个 correction
  draw。
- 真正重试循环内嵌在 `_call_json_llm`，只知道同一 prompt 重发，不知道 stage 路由、
  downstream invalidation、judge verdict 或全局预算。
- 当前 `intake_node` 的 validate→intake repair 会把 `validation_errors` 作为 `feedback`
  注入；judge 盲重抽又要求绝不注入 feedback。两条路径不能共用一个模糊参数。

**影响**

硬把 judge 塞进现 callback 会形成两套或半套重试语义；更危险的是误伤现有合法的下游 repair
feedback，或让 judge 评语进入 prompt。

**建议**

- 抽取两层，不要“复用 validator”：
  - `draw_json_once(...)`：一次模型调用；
  - `retry_stage_draw(runner, validators, budget, artifact_sink)`：只负责同阶段 blind draw；
  - 跨阶段 route/invalidation 由 E0 orchestrator 负责。
- validator 返回结构化 `CheckReport`，不要靠抛异常传语义；transport/parse/schema/
  invariant 分开记。
- 明确两个入口：`repair_feedback`（现下游 repair，可注入）与
  `judge_retry_context=None`（必须盲抽）。测试断言两者不串线。
- verdict schema 必须有 `retry_stage|null`、`retriable`、`root_confidence`；
  当前逐 criterion status/evidence 不足以实现根因路由。

### High 3 - S0 尺寸链与 stroke↔dimension 算法在现 schema 上不可稳健实现

**对应：B3。**

**证据**

- reading `dimensions[]` 没有 `chain_id`、overall/segment 类型、order、pixel anchor。
- 同一轴上可有 top/bottom、left/right、多层和重复链；当前 2f 就有多组 x/y chain。
- 当前刷新后的 2f 甚至把 top/bottom 或 left/right duplicate 写成相同语义坐标；
  reading summary 也注明 elevation dimension endpoint 仍有 placeholder 约定。
- stroke 和 dimension 米制坐标由同一次识图生成，不能作为独立真值。

**影响**

“按轴向+位置邻近配准”会在多链图上高误报，也抓不到数字、端点、stroke 一起抄错的情况。
这不是调容差能解决的问题。

**建议**

把 P1 扩成 reading schema migration，而不只加 facade 字段：

- dimension 增加 `chain_id`、`role=overall|segment|baseline`、`order`、`value_m`、
  `text_verbatim`；
- 增加 image-space bbox/anchor 或 independent OCR provenance；
- 明确 plan/elevation endpoint 坐标约定；
- S0 先做 chain closure 和内部一致性；“验证原图数字”留给 VLM/独立 OCR。

在 schema 落地前，stroke↔dimension 只能作为低置信 flag，不应作为 2f 主验收项。

### High 4 - 2/3 coverage completeness 不应继续随 B5 deferred

**对应：B3 / B6。**

计划已知 current gate 看不到“两侧都 Outdoors”的内部边界洞，却把 coverage 放到 B5，
同时 2/3 无自动 judge。矩形 case 已可从 cell polygon shared boundary 推导 expected
interfaces，本轮应先实现 rectangle profile 的 block check；B5 再泛化非矩形/void。

这也是 sm20 positive golden 之外必须新增的 negative regression：人为把一对内部墙都改为
Outdoors，要求 kernel check 必失败。

### Medium 1 - S4 可行，但计划缺少统一 IDF-fragment parser

**对应：B1 / B3。**

`MepOutput` 的六个 specs 是 IDF fragment 字符串。现有 `schedules.py` 明确只接 eppy
`IDF`，不能直接“复用”在字符串上。

本次只读 spike 已验证：把 sm20 的 material/construction/schedule/people/lights/hvac
片段合并后可由 `IDF(StringIO(text))` 解析，共 138 个对象，
`validate_schedule_completeness` 返回 0 issue。因此方案**可行**，但需要显式模块：

`src/validator/idf_fragments.py`

- 一次解析完整 MEP fragment bundle；
- 返回对象索引与 parse diagnostics；
- schedule/material/construction/zone-reference checks 都消费同一索引；
- 禁止每个 check 自己用 regex 猜 IDF 字段。

解析失败本身应是 4_mep block，并触发同阶段 blind redraw。

### Medium 2 - S4/S5 重复解析同一引用图，assembly 没有新增可见信息

**对应：B1 / B5。**

计划让 S4 检 construction/material/schedule/per-zone 覆盖，S5 又检查
construction→material→schedule 与 zone↔loads。4 validator 已持有 required zones 和
used constructions，能在 MEP 产出点完成这些检查。

建议：

- S4 拥有全部 MEP reference graph checks；
- S5 只做 `assemble_intake_output`、Pydantic、accepted S4 report/hash backstop；
- 若 S5 再跑同一检查，标为 backstop，复用同一函数，不另写 assembly parser。

`interzone.py` / `schedules.py` 保留原位是对的；它们是低层领域 validator，
`checks/kernel.py` / `checks/mep.py` 只作 stage adapter。

### Medium 3 - Check schema 太薄，无法支撑 retry、兼容与训练审计

**对应：B1 / B4。**

当前 `CheckResult{id,stage,layer,severity,passed,evidence}` 缺少：

- `status=pass|fail|skipped|not_applicable|error`；
- `check_version` / capability profile；
- artifact/input hash 与 attempt id；
- machine-readable evidence（对象 id、坐标、差值）；
- policy 与事实分离。

建议 validator 只报告事实/outcome，block/flag policy 由 stage+capability profile 映射。
同一 coverage check 才能在 rectangle profile block、unsupported profile skipped/flag，
并避免以后改 policy 就改 validator。

### Medium 4 - `uncaptured 非空` 会让 clean image 永久失败

**对应：B3 / B5。**

S0 的 block 条件应改为“字段存在且类型正确”。clean sm20 旧产物合法为 `[]`。若需要保证
忽略/door-heal 被记录，必须先有结构化 event/provenance，不能靠强制写“没有家具”等句子。

同时补 block：唯一 stroke/dimension id、finite numbers、非退化 geometry、合法
pen×kind、dimension text/value 可解析。

### Medium 5 - 3D viewer 选型应先 spike，现依赖更适合从 trimesh 起步

**对应：B3。**

`pyproject.toml` 已有 `trimesh`，没有 pyvista/VTK。直接引入 pyvista 会显著放大容器依赖，
静态 screenshot 还受 offscreen backend 影响。

建议把 M2 viewer 拆成两步：

1. 用现有 trimesh 生成 mesh + GLB/JSON 和确定性静态投影视图；
2. 做一个短 spike 比较 pyvista export_html 与轻量 three.js viewer，再决定产品依赖。

viewer 失败不能阻塞几何确定性 checks；静态 render smoke test 要允许 headless backend
不可用时给明确 skip reason，而不是假 PASS。

### Medium 6 - 测试策略缺少真实坏样本、状态机与兼容路径

**对应：B4 / B5。**

“每条 check 一正一反 + 2f fixture”是起点，不足以覆盖接线。至少增加：

- 保存真实 bad 2f corridor-split reading，与 corrected anchor 分开；
- self-consistent wrong dimension fixture，证明 deterministic 只 flag internal consistency，
  J0 mock 才负责原图真值；
- rectangle internal-boundary coverage hole；
- wrong facade sign/base 与对称窗案例；
- no-mass / SimpleGlazing 多层 / missing schedule day type；
- judge malformed/partial/unknown verdict、root attribution uncertain、judge unavailable；
- per-stage 与 global budget、route cycle、downstream invalidation；
- rejected attempts 不覆盖、accepted manifest/hash 正确；
- geometry approval 后 resume 不重跑 1；
- `--reading-from`、legacy missing facade field、`--intake-from` bypass 语义；
- sm20_anchor golden 不只“0 issue”，还断言稳定 check ids、对象计数和关键 hashes/metrics。

judge 测试全部 mock/fake runner，不把模型措辞放进断言，只断言结构化 policy 行为。

### Low 1 - M2 “全段可并行”表述过强

实际隐藏依赖：

- S1 facade translation 依赖 reading schema migration；
- S4 依赖 IDF-fragment parser；
- S5 应复用 S4 reference graph；
- pipeline wiring 依赖 E0 stage execution；
- user gate 依赖 checkpoint/resume。

纯 validator 实现可并行，接线不可并行。建议按下面替代里程碑切 PR。

### Low 2 - `--intake-from` 与用户确认门的语义需显式

`--intake-from` 当前有意跳过 0–5。不要偷偷让它跑 stage checks 或等待 3D 批准。
应记录 `validation_scope=downstream_only`，继续执行现有 cross_ref/InterZone/schedule/EP
门；若用户要对 finished IntakeOutput 做新 assembly audit，提供显式独立命令。

## 建议替代依赖序

### M0 - 执行与审计地基

- E0 stage runner / run manifest / immutable attempts / invalidation / resume
- F1 CheckReport v2（status/version/hash/attempt，policy 分离）
- CLI policy：judge on/off、confirmation required/optional/disabled、global budgets

### M1 - 输入 schema 与 parser 地基

- P1a reading dimension/provenance schema
- P1b facade 只保留 image-local orientation；world base 在 correction 生成
- P2 IDF-fragment parser + object/reference index
- legacy adapters 与 migration flags

### M2a - 0/1 确定性校验与二维视觉件

- S0 linter/internal consistency
- S1 coverage/closure/cross-image/window placement
- bad 2f + sm20 golden
- 半人工 0 失败先返回 human action，不自动 redraw

### M2b - 2/3 几何门

- zone closure/normals/spec references
- kernel report hard gate
- rectangle coverage completeness block
- mesh/export spike；viewer 不阻塞 validator merge

### M2c - 4/5 与 EP baseline

- S4 parse/reference/object semantics/schedule checks
- S5 mechanical assembly + shared backstop
- `read_ep_end` assertions + warning policy

### M3 - judge

- one-stage blind retry executor
- J0/J1；J4 保持 disabled stub，避免“空 judge”进入正式流
- root attribution only when evidence/confidence sufficient
- append-only verdict/hard-sample quarantine

### M4 - 产品策略与 baseline

- hash-bound geometry approval + resume
- optional 3D viewer integration
- sm20/sm21 positive baselines + negative corpus
- cost/cache/latency report

## B1-B7 明确答复

| 项 | 结论 |
|---|---|
| **B1 模块切分** | `checks/` + `judge/` 方向可用；保留 `interzone.py`/`schedules.py` 原位。补 `idf_fragments.py` 和 E0 execution 层；避免 `checks/correction.py` 与 `correction/geometry_validator.py` 双 owner。 |
| **B2 依赖序** | 确定性优先正确，但 M0 缺失。M2 只能“纯实现并行”，接线需按 schema/parser/execution 依赖串联。 |
| **B3 算法** | stroke↔dimension 现 schema 不足，需先扩 chain/provenance；矩形 coverage 现在可做；facade legacy 可短期 adapter；现 retry callback 不可直接复用；pyvista 应先 spike。 |
| **B4 测试** | 每 check 单测必要但不够；需真实坏 fixture、状态机/route/budget/attempt tests、sm20 golden、parser/object semantic tests。 |
| **B5 接线** | 最大风险是 0 不可重跑、单体 pipeline 无 invalidation/resume、人工批准后重新采样、feedback 路径串线、`--intake-from` 语义。 |
| **B6 范围** | provenance 富化可分步，但 dimension chain/provenance 最小字段不能 deferred；矩形 coverage 与关键材料对象语义应提前；J4 空 stub 建议 disabled 而非接线。 |
| **B7 切片** | 建议按 M0/M1/M2a/M2b/M2c/M3/M4 小 PR；每个 PR 都可无网络测试并独立回归。 |

## Verification

- 阅读并对照 `pipeline_stage_contracts.md`、施工方案、`pipeline.py`、
  `intakeoutput.py`、`schedules.py`、`interzone.py`、geometry kernel、CLI/short-circuit。
- 只读 parser spike：sm20 六类 MEP fragment 可由 eppy 解析为 138 个对象；
  schedule completeness 0 issue，证明 S4 前移可行，但需要统一 parser adapter。
- 当前工作树未修改主开发文件；本 review 仅新增审阅文档。

