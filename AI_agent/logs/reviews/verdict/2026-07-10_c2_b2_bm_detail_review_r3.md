# C2 B2 + B-M 细稿 r3 对抗复审

Date: 2026-07-10  
HEAD: `7422f42`  
Objects: `AI_agent/proposals/c2_b2_detail_spec.md`、`AI_agent/proposals/c2_bm_view_manifest_spec.md`（v3，同路径覆写）  
Governing design: `AI_agent/proposals/c2_full_unlock_design.md` v2.2；baseline: `AI_agent/proposals/c2_orthogonal_polygon_design.md` D1–D10  
B2 verdict: **REWORK**  
B-M verdict: **REWORK**

## 一、总裁决

r3 对 r2 的修法方向没有形态偏离，但仍不能施工：

- B2：r2 7 条为 **2 CLOSED / 5 PARTIAL / 0 NOT-CLOSED**；r1 遗留 5 条 PARTIAL 中 **2 CLOSED / 3 PARTIAL**。新增 **5 findings（4 BLOCKER / 1 HIGH）**。
- B-M：r2 6 条为 **5 CLOSED / 1 PARTIAL / 0 NOT-CLOSED**；r1 遗留 5 条 PARTIAL 中 **3 CLOSED / 2 PARTIAL**。新增 **2 findings（1 BLOCKER / 1 HIGH）**。

最先必须处理的是文档身份：两份 v3 都把大量规范删成“v2 不变”，但 v2 正是同路径覆写的前一内容，HEAD 中没有 `*_v2.md`、commit blob 或其他不可变规范快照；两份当前 proposal 甚至仍是 Git 未跟踪文件。r2 verdict 只记录问题与裁决，未保存完整 v2 schema、事务、路由表和测试合同。当前 v3 因此不是可独立执行的细稿，而是指向已消失文本的增量补丁。此问题对两稿均为 BLOCKER。

除该文档问题外，B2 还有三个硬缺口：V3 typed instance 仍可绕过重验、默认 rectangular target 被错误映射到必遭 capability 拒绝的 schema v2、readiness sidecar 没有 accepted-attempt bundle identity。B-M 的 r2 修法主体基本闭合，剩余实质缺口是所声称的 canonical run id 没有任何 wire 字段或生成规则。

本审只读核对 HEAD，并在仓库 Pydantic `2.13.3` 上重跑无落盘反例。除本 verdict 外未改任何文件。

## 二、r2 B2 findings 关闭矩阵

| r2 finding | 状态 | r3 复核 |
|---|---|---|
| R2-B2-01 typed/raw coercion 全入口 | **PARTIAL** | dict、宽松基类、judge/core/check/load/render 点名均已采；但“已经是 `CorrectedGeometryV3` 就原样返回”把 `isinstance` 再次当成已验证证明，`model_copy` 无效更新可绕过入口和末尾重验。见 R3-B2-02。 |
| R2-B2-02 子类序列化 / FinalizeResult | **CLOSED** | 非 Pydantic dataclass、直接 dump `result.geom` 运行时实例、通用 `_to_json` 显式拒绝 FinalizeResult、attempt 往返逐键测试均已冻结（细稿 `AI_agent/proposals/c2_b2_detail_spec.md:80-85`）。 |
| R2-B2-03 cardinal/segment/identity | **PARTIAL** | cardinal、段轴对齐/垂直/family/interval 与事务身份快照均已落；但 `depth` 从原定 FiniteFloat 写成普通 `float = Field(ge=0)`，仍接受正无穷。见 R3-B2-05。 |
| R2-B2-04 ring 宽进严出 | **PARTIAL** | draw 宽编码、core 唯一 canonical owner、final 开环 CCW 的阶段裁决正确；但当前只定义一棵 V3 wire，并未给出 final-phase validator/API，且通用 ensure 对 V3 原样返回，所谓 post-core revalidation 不会自然切换到“严出”规则。见 R3-B2-02。 |
| R2-B2-05 CorrectionTarget | **PARTIAL** | 单一对象贯穿链已采，但 `rectangular → schema v2` 与现 capability/base D1 正面冲突，默认 legacy run 会自拒；target 甚至不允许 schema v1。见 R3-B2-03。 |
| R2-B2-06 feature-state 载体/owner | **PARTIAL** | support/state API、三态、Vg 新 attempt、不回写旧 accepted 均已采；但 sidecar 没有 writer 载体和 manifest-bound hash，既写不进声明的 FinalizeResult，也可在不改变 accepted output hash 时被替换。见 R3-B2-04。 |
| R2-B2-07 stable debt id / strict resolution | **CLOSED** | debt schema bump、source-bound deterministic id、attempt input hash、strict resolution kind、本 attempt 引用检查与伪造/重复/跨 run 负例均已落（细稿 `:87-92`）。 |

## 三、r1 B2 遗留 PARTIAL 复核

| r1 finding | r2 状态 | r3 状态 | 说明 |
|---|---|---|---|
| B2-01 strict wire + legacy adapter | PARTIAL | **PARTIAL** | 子类族与 raw/base 分发方向正确；V3 实例 no-op fast path 仍留 typed-object 逃逸。 |
| B2-02 footprint 产权/事务 writer | PARTIAL | **CLOSED** | 就修法语义看，v3 禁 cells 兜底、七步单事务及三阶段 ring ownership 已消除原缺口；完整规范仍须按 R3-B2-01 恢复到当前稿。 |
| B2-03 constrained types/identity | PARTIAL | **PARTIAL** | cardinal 与 identity 已闭；非有限 `depth` 仍漏。 |
| B2-05 v3 生产发射 | PARTIAL | **PARTIAL** | 发射批次、真实重抽与单 target 已有；rectangular/v2 错配使发射矩阵仍不可执行。 |
| B2-06 typed debt resolution | PARTIAL | **CLOSED** | stable debt id、strict audit kind 和 attempt 输入绑定均已补齐。 |

r1 已 CLOSED 的 B2-04/B2-07/B2-08 未见其原问题被语义性重开；但 R3-B2-01 必须把其当前仅以“v2 不变”引用的规范正文恢复，R3-B2-03 也必须避免用新 target 选择破坏 legacy run 行为。

## 四、B2 r3 新 findings — **REWORK**

### R3-B2-01 — BLOCKER — 当前 v3 是引用已消失 v2 的增量补丁，不是自包含施工细稿

当前稿把关键合同压成：feature 表“v2 不变”（`AI_agent/proposals/c2_b2_detail_spec.md:22-28`）、footprint 产权与七步事务“v2 不变”（`:43-49`）、Window resolver/类型/claims“v2 不变”（`:57-60`）、四处 capability 与整个 `floor_footprint` 路由“v2 不变”（`:62,78`）、accepted-attempt writer/report 规则“v2 不变”（`:80-85`）、测试计划“v2 九条保留”（`:106-114`）。

但 v2 与 v3 使用同一路径，v2 内容已被覆盖；HEAD 没有可链接的 v2 proposal，`git ls-files` 也确认两份细稿当前均无历史 blob。r2 verdict 不包含完整子类字段、十路 consumer、七步 writer、ManifestEntry 条件模型等规范，不能成为基线 include。执行者无法仅凭当前稿回答“完整 v3 class 到底有哪些字段/validator”“七步事务精确顺序”“旧九项测试原文是什么”。

**建议修法**：首选把 v2 全文与 r3 增量合并成一份累计式 v3，删除所有会影响施工的“v2 不变”。若必须增量写法，先把逐字节 v2 固化到版本化路径并登记 SHA-256，再让 v3 用精确章节链接；review verdict 不能充当 normative include。重送前以新执行者只读当前 v3 能列出完整 wire、writer、consumer 与验收表为自包含测试。

### R3-B2-02 — BLOCKER — `ensure_corrected_geometry` 对 V3 实例 no-op，`model_copy` 逃逸与 final 严出校验均未封死

伪代码明确规定：基类 schema 3 若“已是 `CorrectedGeometryV3` 则原样返回”，只有宽松基类才 strict round-trip（`AI_agent/proposals/c2_b2_detail_spec.md:30-37`）；finalize 入口和末尾都调用这个边界（`:38`）。Pydantic 的类身份不是 validation 证明：`v3.model_copy(update={"floors": bad_value})` 不运行 validator，返回值仍是 `CorrectedGeometryV3`。本轮探针用同构 strict model 将 `int` 字段更新成字符串，实例类型不变；只有 `model_dump → model_validate` 才拒绝。

因此入口 ensure 会把坏 V3 原样交给 mutation，末尾再调同一 ensure 仍原样返回。ring 合同也受同一问题影响：draw 允许 CW/closed、final 要求 open/CCW（`:43-49`），但当前没有一个命名的 final validator；普通 `CorrectedGeometryV3`/ensure 无法同时表达这两把尺。

**建议修法**：任何 trust boundary 都对 schema 3 做 strict round-trip，不为“已经是 V3”设置 no-op；如担心对象 identity，由返回的新对象作为唯一后续输入。另拆两个明确 API：`parse_correction_draw` 使用 encoding-tolerant ring validator，`validate_final_corrected_geometry` 使用 canonical ring validator并返回 fresh V3。finalize 固定为 `parse/ensure input → snapshot → mutate → validate_final`，judge/check/build 对 accepted artifact 只走 final validator。负例增加“V3.model_copy 注入坏嵌套类型/extra/CW final ring”。

### R3-B2-03 — BLOCKER — `rectangular → schema v2` 在现规则下必拒，并擅自删除了合法 schema v1 producer target

`CorrectionTarget.schema_version` 只允许 `"2" | "3"`，并把 `rectangular` 映射为 legacy v2（`AI_agent/proposals/c2_b2_detail_spec.md:64-76`）。这不是“保持 legacy 目标”：基底明确 `schema v1 = rectangular`、`schema v2 = polygon-capable`，rectangular 仍是默认 profile（`AI_agent/proposals/c2_orthogonal_polygon_design.md:9-13`）。现实 capability 表也声明 v1 仅 rectangular、v2 同时声明 rectangular+orthogonal polygon，而 rectangular profile 只允许 rectangular（`src/agent/geometry/capability.py:21-30`）；subset gate 位于 `:51-75`。所以任何 schema v2 artifact 在 rectangular profile 下都必被拒。

还有第二重混搭：legacy `CorrectedGeometry.model_json_schema()` 的 `schema_version` 默认仍是 `"1"`（`src/agent/correction/schema.py:70-78`）。用它作为“v2 target schema”时，prompt/inner validator允许 LLM 省略版本并得到 v1，直到 target equality 才失败；单一 target 对象并未让 schema 本身成为 v2 wire。

**建议修法**：生产 target 矩阵按现上位语义冻结为 `rectangular → schema v1 + legacy model`、`orthogonal_polygon → schema v3 + strict V3 model`。schema v2 继续作为可读 legacy artifact，不必成为 B2 后的新 producer target；若确需生产 v2，须另有 `Literal["2"]` 的 version-specific wire model并使用 polygon profile。`CorrectionTarget.schema_version` 至少覆盖真实的 v1/v3，测试必须包含默认 rectangular run 全链仍发 v1且 bytes/行为不变。

### R3-B2-04 — BLOCKER — `feature_states.json` 未进入 FinalizeResult/StageRecord 的身份，readiness 可被无痕翻转

本稿冻结的 `FinalizeResult` 只有 `geom` 与 `audit_payload`（`AI_agent/proposals/c2_b2_detail_spec.md:80-84`），随后却说“finalize 在 attempt 归档物中写 `feature_states.json`”（`:94-103`）。纯 finalize 不知道 attempt dir，也尚未知道 output serialization hash；attempt writer则拿不到 FinalizeResult 中不存在的 feature payload。两处 owner 互相悬空。

即使机械写出 sidecar，当前 accepted identity 仍只有 `StageRecord.output_hash`（`src/agent/execution/manifest.py:99-111`）；`StageRunner.record` 只归档 output/checks并据 output 文本算 hash（`src/agent/execution/stage_runner.py:124-180`）。sidecar 内写 output hash只是“sidecar 指向 output”，不能证明“accepted manifest 指向这份 sidecar”。攻击者可把 `declared_unpopulated` 改成 `populated`、保留原 output hash/helper 文案，manifest 完全不变，`artifact_feature_state` 就会放行尚未施工的 consumer。

**建议修法**：将 `feature_states_payload` 纳入 FinalizeResult，或明确由 attempt writer依据 `CorrectionTarget+final geom`唯一生成；唯一 attempt writer在算出 output hash后写入 schema-versioned sidecar，并以临时 attempt dir整体 rename。扩 `StageRecord` 为 typed `artifact_hashes`（至少 output/checks/audit/feature_states）或记录一个 canonical bundle hash；下游从 manifest-accepted attempt 读取并逐 hash 验证。sidecar/helper/version/output/state 任一篡改都必须断链。finalize 本身继续零 I/O。

### R3-B2-05 — HIGH — `depth: float = Field(ge=0)` 仍允许正无穷，违反 constrained finite geometry

细稿把真实非负约束写成 `depth: float = Field(ge=0)`（`AI_agent/proposals/c2_b2_detail_spec.md:51-55`），但 Pydantic `2.13.3` 实测 `float("inf")` 可通过 `ge=0`；NaN/负数才被拒。无限 depth 随后会污染排序、visibility 与 hash/JSON 语义。r2 前的类型原本要求 `FiniteFloat`，这里是收紧时的回退。

**建议修法**：使用 `Annotated[FiniteFloat, Field(ge=0)]`（或等价 finite validator）；所有 angle/interval/depth/uncertainty 继续统一用 finite 类型。加 `+inf/-inf/nan` 三负例，不能只测负数。

## 五、r2 B-M findings 关闭矩阵

| r2 finding | 状态 | r3 复核 |
|---|---|---|
| R2-BM-01 source-aware Va | **CLOSED** | plan 不交 Vg、elevation 才交该 view visible、跨通道在各自 coverage 后比较及凹形四例均已明确（细稿 `AI_agent/proposals/c2_bm_view_manifest_spec.md:38-43`）。 |
| R2-BM-02 isolation run binding | **PARTIAL** | formal/preview 分立、preview 恒拒 merge、provenance hashes、A→B/替换负例均已采；但被绑定的 canonical run id 无 wire 字段、生成规则或现实来源，同输入的两个 run 仍无法按稿实现区分。见 R3-BM-02。 |
| R2-BM-03 direction provenance/sidecar | **CLOSED** | `direction_source` 与 `semantics_source` 分轴、上位枚举统一、manifest 不回写及 hash-bound ResolvedViewDirection 接缝已落（细稿 `:25-34`）。 |
| R2-BM-04 RunManifest/grandfather/API | **CLOSED** | V1/V2 wire 分立、共同 serializer、grandfather 只读、新 attempt 先 migrate、provision/verify 分立均已明确（细稿 `:45-55`）。 |
| R2-BM-05 reader 可见性旁路 | **CLOSED** | C2 可见 drawing 恒 required+output、不可记账文件不拷/不可读、derived copy parent 等价绑定及三负例均已写死（细稿 `:11-18`）。 |
| R2-BM-06 entry identity | **CLOSED** | 唯一 `input_id`、canonical sort、所有 foreign key 与 collision/dangling 负例已冻结，`view_id` 术语明确废除（细稿 `:20-23`）。 |

## 六、r1 B-M 遗留 PARTIAL 复核

| r1 finding | r2 状态 | r3 状态 | 说明 |
|---|---|---|---|
| BM-01 trusted completeness | PARTIAL | **CLOSED** | 默认空、trusted assertion/typed coverage 与 source-aware plan/elevation 公式已闭。 |
| BM-02 isolation bypass | PARTIAL | **PARTIAL** | merge/check/accept 与 preview 旁路均闭；run A/B 的稳定 identity 仍未定义。 |
| BM-03 direction axes | PARTIAL | **CLOSED** | raw source、semantics source、manifest building direction 与 resolved sidecar 已分开。 |
| BM-05 emitter/RunManifest | PARTIAL | **CLOSED** | emitter/verify 分立、两 wire serializer与只读 grandfather 已闭。 |
| BM-08 strict schema/version chain | PARTIAL | **PARTIAL** | `input_id` 与 direction 字段缺口已闭；但完整顶层/entry/completeness schema 被“v2 基础”悬空引用删除，须按 R3-BM-01 恢复后才能关闭。 |

## 七、B-M r3 新 findings — **REWORK**

### R3-BM-01 — BLOCKER — 当前 B-M v3 同样依赖已消失的 v2 正文

当前 76 行文件没有完整 top-level manifest、ManifestEntry required/excluded union、opening_evidence/completeness assertion、coverage model、strict loader 归一化规则或原八项测试；它们分别被写成“v2 不变/基础上修/保留”（`AI_agent/proposals/c2_bm_view_manifest_spec.md:9-13,20,36-39,45-50,63-74`）。v2 已在同路径被覆盖，也没有版本化快照；r2 verdict 只摘录问题相关片段，不能恢复完整 wire。

这会产生直接实现二选一：例如 `direction_source` 新字段应加进哪个 discriminated entry model、coverage 条件约束的准确枚举/必填关系、`content_sha256` canonical payload 到底包含哪些字段，当前稿均无法独立回答。所谓“RunManifestV1 = 现类原封”可从代码取，View Manifest v2 则没有代码或旧文件可取。

**建议修法**：把 v2 全文累计合并回 v3，当前修订覆盖冲突段；或先保存不可变、带 hash 的完整 v2 并精确 include。最终 B-M v3 必须独立给出 top-level、两个 entry 分支、所有 submodel、conditional validators、canonical hash、generator 全映射、gate、isolation、测试与验收，不得要求执行者从 verdict 拼规范。

### R3-BM-02 — HIGH — “canonical run id”只出现在 prose，RunManifestV2 没有该身份

isolation provenance 被要求绑定 canonical run id，merge 再逐项比较（`AI_agent/proposals/c2_bm_view_manifest_spec.md:57-61`）；但同稿定义的 `RunManifestV2` 只在现模型上增加 `manifest_version` 与 `run_inputs.view_manifest_sha256`（`:52-55`），没有 `run_id`。现实 RunManifest 也只有 `case/manifest_version/stages`（`src/agent/execution/manifest.py:114-135`），execution 路径中不存在通用 immutable run UUID。

若把目录名/绝对路径临时当 id，移动/复制 run 会改义；若只比较 case id、view manifest、metadata 和 image hashes，同一 case 的 run A/B 完全可能全相等，正是稿内承诺要拒绝的 A→B merge。`:60` 的“目标 run 的 manifest hash”还需消歧：若指整个 `run_manifest.json`，build 后任何合法 StageRecord 更新都会让 in-flight workspace无故失效；若指 `view_manifest_sha256`，应直写该名。

**建议修法**：在 `RunManifestV2` 增必填、immutable `run_id`（UUID/128-bit random 或冻结的等价类型），新 run provisioning 唯一生成，v1→v2 migration 生成并登记；正式 builder、staging MANIFEST/provenance、merge target、StageRecord input hashes均绑定它。merge 比较 `run_id + case_id + view_manifest_sha256 + metadata/image hashes`，不要模糊比较会随 stage accept 变化的整份 run-manifest hash。补“同 case/同图/同 manifest、仅 run_id 不同”的 A→B 负例。

## 八、开放问题与重新送审门

r1 四个开放问题的裁决不变：debt check 在两路径 pre-core、不进纯 finalize；Window 使用新 `floor_id`；manifest coverage 所有 profile 恒 BLOCK；未知 staged image fail closed 且 reader 可见 drawing 必记账。本轮无需要用户重新拍板的产品选择。

### B2 重送门

1. 恢复累计式完整 v3 规范，或提供不可变、有 hash 的完整 v2 normative include。
2. 删除 V3 instance no-op：trust boundary 始终 fresh strict validation；拆 draw parser 与 final-artifact validator。
3. CorrectionTarget 改为默认 rectangular→v1、orthogonal→v3；v2 仅作 legacy read，除非另建真正 Literal-v2 wire。
4. feature_states 纳入唯一 attempt bundle writer与 manifest hash identity，finalize 保持零 I/O。
5. depth 恢复 finite+nonnegative，补非有限负例。

### B-M 重送门

1. 恢复完整 View Manifest schema/generator/gate/test 正文，不再悬空引用已覆盖 v2。
2. 给 RunManifestV2 增真实 immutable run_id并冻结生成、migration、provenance与 merge 比较规则。

## Review ask

none — r2 13 条的修法方向均已明确；当前阻塞项都是规范闭合/代码现实问题，不需要新的产品裁决。修订后再送 r4。
