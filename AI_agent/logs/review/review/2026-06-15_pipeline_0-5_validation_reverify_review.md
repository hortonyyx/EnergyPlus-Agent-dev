# Re-verify Review · 0–5 校验架构设计与施工方案

Date: 2026-06-15  
Reviewer: Codex  
Request: `AI_agent/logs/review/request/2026-06-15_pipeline_0-5_validation_reverify_request.md`

## Overall Verdict

**NOT YET CLOSEABLE。**

修订已经解决了原方案的核心方向问题：

- 确定性后置失败改为 fail-closed，不再靠上游换样本掩盖代码 bug；
- M0 执行/审计地基被提升为所有 gate 接线的前置；
- facade 世界落位移到 correction，reading schema 增加 dimension chain/provenance；
- 矩形 coverage、本体 MEP 语义、统一 IDF-fragment parser 都进入本轮范围。

这些实质修复是正确的。当前不能关闭的原因不是方案方向，而是
`pipeline_stage_contracts.md` 仍把 v7 修订放在 §0.4 作“覆盖解释”，同时在权威的
§1/§3 中保留相反规范。施工者会同时读到 manual 与自动重读、`uncaptured` 可空与必须非空、
不得复用与复用旧 validator、trimesh 先行与 pyvista 必选、S4 唯一 owner 与 S5 再查。

本项目明确要求“全部确定完再施工”，因此活文档不能依赖“上文覆盖下文”的优先级推理。
把下述 must-fix 同步后，两份原 review 可关闭，无需第三轮架构重审。

## Must-Fix Findings

### High 1 - §0.4 没有真正替换 §1/§3 的旧规范

**证据**

- `pipeline_stage_contracts.md:97` 仍写“坏 draw 直接盲重抽”，但 `:100-110` 要求先分类，
  0 当前 manual，确定性 code failure 必须 fail-closed。
- `:143` 仍要求 `uncaptured 非空`，并宣称 stroke↔dimension 能逮“整条一致抄错”；
  与 `:122`、`:125` 直接相反。
- `:144` 仍要求 0_reading 自动盲重读 3 次；与 `:107` 的
  `human_redraw_required` 相反。
- `:139`、`:143-144` 仍把 reading 产物描述成“带符号 facade_axis”；没有写出
  image-local schema。
- `:164`、`:221` 仍指定 pyvista；`:167`、`:221` 仍把用户确认写成必经门；
  与 `:128-129` 的 caller policy + trimesh-first 相反。
- `:184-185` 仍把 zone↔load 接缝归 5；`:126` 与 build v2 明确全部 MEP 引用图归 4。
- `:176`、`:269` 没有列 IDF parser 和对象语义，甚至把 no-mass 仍放在合理区间 flag。
- `:272` 仍写“复用 `_make_correction_validator`”与 hard sample 直接归集；
  与 `:108`、`:110` 相反。
- §3.1 仍是覆盖式 flat 产物布局，没有 `run_manifest` / immutable attempts /
  approval；`:245` 还把 `kernel_gate_report` 标为 advisory。

**影响**

这不是历史 changelog 残留，而是被 §0.4 明确称为“逐段契约”和“施工序”的活规范。
实现 M0/M1/M2 时存在多套合法解读，会直接造成接口和测试漂移。

**必须修复**

逐段改齐，而不是再加一层 banner：

1. 重写 §1 的 0/1/2+3/4/5 校验条目，使其只保留 v7 口径。
2. 重写 §3 产物矩阵、on-disk 布局和 backlog，纳入 attempts/manifest/approval/checks。
3. 删除 `复用 _make_correction_validator`、`uncaptured 非空`、
   “逮整条一致抄错”、0 自动重读、pyvista 必选、5 owner MEP 图等旧指令。
4. dated v3-v6 changelog 可以保留原话；活区块不可以。

### Medium 1 - M0 的失效 DAG 与批准 checkpoint 范围尚不完整

**证据**

- build v2 `:30` 只列 `0→1-5`、`1→2-5`、`4→5`，未定义 2/3 的失效边。
- `:31`、`:86` 只把 approval 绑定 `building_geometry` hash；用户确认发生在 2/3 后，
  实际交付还包含 `geometry_specs.md`、kernel checks 和 accepted attempt。

**影响**

代码升级、手工重跑或 resume 时，stage 3 可能被重新序列化而 approval 仍显示有效；
也无法明确重跑 2 或 3 时哪些 accepted artifacts 必须失效。

**必须修复**

- 写全 DAG：`0→1-5`、`1→2-5`、`2→3-5`、`3→4-5`、`4→5`。
- approval 绑定 accepted geometry checkpoint/manifest digest，至少覆盖
  `building_geometry`、`geometry_specs`、kernel check report、stage/check version。
- resume 必须复用已批准 attempt，不得静默重新生成 2/3 产物。

### Medium 2 - facade image-local schema 仍混合两个坐标语义

build v2 `:62` 写 `local_x_direction(左右|东西)`，把 image-relative left/right 与
world-relative east/west 放在同一个字段候选中。后者正是本次要从 reading 移出的世界落位
语义。

M1 开工前应锁定 canonical schema，例如：

- `view_facade`: South/North/East/West（来自可信图名/元数据）；
- `local_x_positive`: `image_left_to_right`；
- `mirrored`: true/false/unknown；
- `orientation_evidence`: 结构化来源；
- world axis/sign/base 只由 correction 派生。

若确需保存 east/west OCR 提示，应另作 `world_direction_hint` + provenance，不能与
image-local 主字段混用。

### Medium 3 - 施工 M6 的测试承诺只落实了一部分

build v2 已列 bad-2f、自洽错尺寸、facade sign、coverage hole，方向正确；但 reverify
request 声称纳入的以下验收尚未在实际计划中形成测试卡：

- no-mass / SimpleGlazing / missing day type 的负例 fixture；
- malformed/partial/insufficient-evidence verdict；
- per-stage/global budget 与 route cycle；
- rejected attempts 不覆盖、accepted manifest/hash；
- invalidation/resume 与 approval 后不重跑 1/2/3；
- `--reading-from`、legacy facade、`--intake-from` bypass；
- sm20 golden 的稳定 check ids、对象计数和关键 metrics/hash。

无需把测试实现细节写很长，但 M0/M2c/M3/M4 各自应列明确 acceptance tests，避免只靠
文首“每条配单测”兜底。

## Per-Finding Re-verification

### Design Review

| Finding | Result | Re-verify |
|---|---|---|
| H1 确定性失败/0 重抽 | **PARTIAL** | 新失败分类正确；§1 仍写通用盲重抽和 0 自动重读。 |
| H2 facade world placement 越界 | **PARTIAL** | §0.4/build 已移到 correction；§1 仍保留旧 facade_axis 带符号表述，canonical local schema 未锁。 |
| H3 2f 归因与证据独立性 | **PARTIAL** | delta/audit + bad fixture 已进方案；§1 仍宣称 stroke↔dimension 能逮“自洽地全错”。 |
| H4 矩形 coverage | **PASS** | §1 2/3、§3.2 与 build M2b 均明确本轮 block，B5 只泛化。 |
| M1 uncaptured 非空 | **PARTIAL** | §0.4/build 已修；§1 仍要求非空。 |
| M2 4/5 owner 与引用图 | **PARTIAL** | 新引用图正确；§1 5 的校验/归属表仍把 zone↔load 归 5。 |
| M3 MEP 对象语义 | **PARTIAL** | §0.4/build M2c 已补；§1 4_mep 与 §3.2#4 未同步。 |
| M4 用户确认门策略 | **PARTIAL** | caller policy/hash 已进入新方案；§1/§3 仍写 pyvista 必经确认。 |
| L1 judge 密度 | **PASS** | §0.3 已统一 0/1/4 eligible、2/3 手动、5 无 judge。J4 disabled 属 rollout 选择。 |
| L2 unknown/归因不确定 | **PASS** | verdict v2 字段及不自动路由规则已落实。 |

### Build Plan Review

| Finding | Result | Re-verify |
|---|---|---|
| H1 execution/checkpoint | **PASS** | M0、registry、manifest、attempts、resume、approval 均已进入前置。DAG/checkpoint 完整性作为本轮新 must-fix。 |
| H2 通用 retry harness | **PASS** | 已拆 `draw_json_once` / `retry_stage_draw` / execution route，并隔离 feedback 两入口。 |
| H3 reading schema | **PASS** | chain/role/order/value/verbatim/pixel anchor 与 internal-consistency 定位已进入 M1/M2a；facade enum 另见新 M2。 |
| H4 coverage deferred | **PASS** | 矩形 coverage 已进入 M2b block。 |
| M1 IDF-fragment parser | **PASS** | 单一 parser 与 stage adapter 边界明确。 |
| M2 S4/S5 重复 | **PASS** | build M2c 已明确 S4 owner、S5 shared backstop。 |
| M3 CheckReport 太薄 | **PASS** | status/version/profile/hash/evidence 与 policy-fact separation 已纳入。 |
| M4 uncaptured 非空 | **PASS** | build S0 已改为字段存在且 list。 |
| M5 viewer 选型 | **PASS** | trimesh-first + spike + explicit skip 已纳入。 |
| M6 测试策略 | **PARTIAL** | 核心 geometry fixtures 已列；状态机、judge、MEP、兼容与 golden acceptance tests 尚未实际列入。 |
| L1 并行表述 | **PASS** | 已改为 validator 可并行、接线按依赖串联。 |
| L2 `--intake-from` | **PASS** | `validation_scope=downstream_only` 已明确。 |

## Three Critical Points

1. **确定性 fail-closed**：设计机制已正确补上；须删除 §1 中通用“坏则盲重抽”的旧口径后
   才算规范闭环。
2. **M0 执行地基**：模块和里程碑成立，是正确开工点；开工前补全 DAG 和 checkpoint digest。
3. **facade + reading schema**：职责切分已正确；还需把 image-local 字段定义成唯一坐标语义，
   并同步清掉 §1 的旧 world-sign facade_axis。

## Closeability

- **Architecture design review：暂不可关闭。**
  Must-fix = 同步重写活跃 §1/§3，消除与 §0.4 的直接矛盾。
- **Build plan review：方向已通过，但与本轮一起暂不关闭。**
  Must-fix = 完整 DAG/checkpoint digest + 明确 acceptance-test matrix。

完成上述三项后，可以直接将两份原 review 标记 **CLOSED** 并开始 M0；不需要重新讨论
“确定性优先、M0 先行、judge 后置”的架构方向。

## Verification

- 对照 reverify request 的 22 条处置逐项检查 contracts v7 与 build plan v2。
- `git diff --check`：修订文档无 whitespace error。
- 本轮为设计/施工文档复核，未运行代码测试。

