# C2 B2 + B-M 细稿对抗审

Date: 2026-07-10  
HEAD: `7422f42`  
Objects: `AI_agent/proposals/c2_b2_detail_spec.md`、`AI_agent/proposals/c2_bm_view_manifest_spec.md`（v1）  
Governing design: `AI_agent/proposals/c2_full_unlock_design.md` v2.2；baseline: `AI_agent/proposals/c2_orthogonal_polygon_design.md` D1–D10  
B2 verdict: **REWORK**  
B-M verdict: **REWORK**

两稿都抓到了真实接缝，但都还没有达到可施工细稿的精度。

- B2：**8 findings（BLOCKER 2 / HIGH 6）**。`Floor.id + Floor.footprint` 的方向正确，四处 capability 硬编码和双路径 envelope 缺口也对账准确；但“单类 + after-validator”并不等价于 v3 `extra="forbid"` + v1/v2 adapter，v3 dict scorer 还保留了从 cells 反推 footprint 的逃逸口，直接重新打开 B3 自证循环。`Window.floor`、生产 v3 发射、pre-core evidence-debt、accepted-attempt audit 身份也都未闭合。
- B-M：**8 findings（BLOCKER 2 / HIGH 4 / MEDIUM 2）**。清单前置和产品不可改的方向正确；但 negative-evidence completeness 被 generator 的两行常量无证据升级，`merge_isolated_output()` 又可完全绕过拟议 gate。`true_azimuth` 与 building-axis direction 仍混在一个字段，supplementary/undeclared image、`validate_case` 只读合同和 run-manifest 演化也未闭合。

按上位 v2.2 裁：其 `v3 extra="forbid" + v1/v2 adapter`、C-03 的“可信 coverage/completeness”、C-04 的 `true_azimuth → θ → building-axis` 守卫均优先于两份细稿中的冲突写法。本 verdict 不放行 B2 或 B-M 施工，也不放行任何后续批借合成 fixture 绕过这两个开工门。

本审只读核对代码与样本，另以 `PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider` 实跑基线；除本 verdict 外未修改其他文件。

## 一、代码现实与 file:line 对账

| 细稿陈述 | 结论 | HEAD 证据 |
|---|---|---|
| B2 点名四处 `schema_version_of(geom) != "2"` | **可证** | `src/agent/correction/deterministic.py:751-754`、`src/agent/correction/geometry_validator.py:65-68`、`src/agent/pipeline.py:481-485`、`src/agent/geometry/modelling.py:392-395`。 |
| pipeline 传 tol+envelope，run_stage 不传 envelope | **可证** | integrated 路径在 `src/agent/pipeline.py:921-933`；flow 路径在 `scripts/tool_scripts/run_stage.py:181-183`。tol 缺省由 core 自载，见 `src/agent/correction/deterministic.py:724-738`；真正差异确为 envelope。 |
| `footprint_x/y` 为 50 个文本命中 / 10 文件 | **词法计数可证** | 审阅请求附录与 HEAD `rg` 一致；但其中含 schema 声明和 `facade.py` 文档/形参，不等于 50 个独立语义 writer。B2 表实际给 9 路由行（两 render 合并一行），不能把计数本身当“全消费语义已闭合”的证据。 |
| pipeline 有 evidence-debt BLOCK，flow 没有 | **证伪** | flow 的 `check_correction(..., evidence_debt=...)` 在 `scripts/tool_scripts/run_stage.py:191-195`；该函数内部明确调用 `_evidence_debt_coverage`，见 `src/validator/checks/correction.py:85-111`。真实差异是 pipeline 在 core 前先查一次（`src/agent/pipeline.py:897-919`），flow 只在 core 后查。 |
| flow 的 reading 发现为 `*_view.json` | **事实可证，引用范围偏两行** | 真正 glob 在 `scripts/tool_scripts/run_stage.py:111-112`，不是细稿链接起点 `:114`；聚合/校验在 `:113-134`。对标准 `South_view.png → South_view.json` 成立，对 supplementary 命名不成立，见 B-M-04。 |
| `dimensioned_view_names()` 读 `views:{}` 扩展 | **可证** | `src/agent/execution/case_metadata.py:51-75`；当前 sm20/sm21/sm24 metadata 均无 `views`。 |
| isolation 的 `MANIFEST.json` 是另一物种 | **可证** | `src/agent/execution/isolation.py:57-88`；其内容是 staging 文件复制审计。 |
| “570 绿 + 9 strict xfail” | **当前 HEAD 实跑可证** | 579 collected；最终 `570 passed, 9 xfailed, 116 warnings`。9 个 xfail 均由 strict marker 定义：`tests/test_validation_run_baseline.py:26-29` 与 `tests/test_orchestrate_baseline.py:32-35`。这只证明改造前基线，不证明两稿的“零 golden”改造后仍成立。 |

## 二、B2 findings — **REWORK**

### B2-01 — BLOCKER — 单一宽松模型的 after-validator 不等价于上位要求的 v3 strict wire schema + legacy adapter

B2 §2.6 选择在一套 `extra="allow"` 模型上递归扫 `model_extra`，声称对 v3 与 `extra="forbid"` 语义等价。这个等价性不成立：

1. 现模型所有层均 `extra="allow"`（`src/agent/correction/schema.py:32-40,43-52,62-78`）。把 `Floor.id/footprint`、`Window.provenance/facade_segment_id`、顶层 `north_axis/facade_segments` 变成“已知字段”后，Pydantic 会在 `mode="after"` validator 运行**之前**按新类型解析它们。一个 v1/v2 历史 extra 若恰好同名且形状不同，今天可原样保留，改造后会提前 ValidationError；after-validator 根本无机会“跳过 legacy”。
2. 同一问题反向存在：v1/v2 payload 可填入形状合法的 v3 新字段；因版本门跳过递归 extra 检查，这些半 v3 字段会成为正式 typed values，而 helper 又宣称 v1/v2 只走 legacy bbox。于是“保存但忽略”与“后续 consumer 误读”并存。
3. `model_copy(update=...)`/`model_construct` 类路径不会重新执行这套 wire gate。仓库已有大量 `model_copy(update=...)` 测试用法；仅把约束放在一次 after-validator 不是完整边界。
4. 实际入口不统一经过某个新 adapter：flow loader 在 `scripts/tool_scripts/run_stage.py:219-232`，offline validator 在 `src/agent/execution/validation_run.py:151-165`，judge dict 路径在 `src/agent/judge/correction_score.py:316-337`，都直接指向 `CorrectedGeometry`。

这与上位 `AI_agent/proposals/c2_full_unlock_design.md:84-91` 的“v3 几何子模型 `extra="forbid"`；v1/v2 经 adapter 保持 legacy 宽容”正面冲突，按上位裁掉 B2 的单类等价性主张。

**建议修法**：冻结独立的 v1/v2 wire model（保持旧字段与 `extra="allow"`）和全层 `extra="forbid"` 的 v3 wire model，以 schema_version 在 raw payload 边界分发；两者再适配到共享内部几何类型。所有 JSON/dict 入口只能走该分发器，未知版本在分发前 fail closed。若保留公共 `CorrectedGeometry` 名称，也应让它成为 adapter/factory，不得让一个宽松 BaseModel 同时冒充两份 wire contract。补同名 legacy-extra、嵌套 extra、`model_copy`/raw-dict、未知版本的负例。

### B2-02 — BLOCKER — v3 footprint 产权仍可从 cells 自证，且 ring 的 canonical/snap/envelope writer 没有闭合

B2 正文说 `Floor.footprint` 必须由 correction 独立声明、禁止 `union(cells)` 派生；但 §4 对 judge 明写“v3 floors[].footprint 缺失再走 cells 兜底”。现 scorer 的兜底正是从所有 cells 求 bbox（`src/agent/judge/correction_score.py:220-249`），再在 `:333-337` 喂给模型。若照细稿保留到 v3，任何绕过 model adapter 的 raw attempt 都能用被测 cells 自造 footprint，B3 的分母重新被产品本身决定。

ring writer 也未写到可施工：当前 core 只把全局 `footprint_x/y` 当 hard anchors 并覆写它们（`src/agent/correction/deterministic.py:778-808`），随后只 snap cell vertices/bboxes（`:849-872`）；envelope transaction 同样只移动 cells 和顶层 bbox（`:591-721`）。细稿一处写“跨层路由吃 bbox”，另一处又写“ring 顶点一并进轴收集/snap”，但没有点名谁覆写每个 `Floor.footprint`，也没有说明矩形 envelope reconcile 如何同步 ring。按当前顺序，极易得到 `Floor.footprint bbox != footprint_x/y` 的自相矛盾 v3 artifact。

**建议修法**：

- v3 的 model/dict helper 对缺失 `Floor.footprint` 一律 INVARIANT；只有明确的 v1/v2 adapter 可从 `footprint_x/y` 造 legacy rectangle，任何版本都不得从 cells 造权威 footprint。
- 冻结单一事务顺序：保存 producer 原 bbox → 校验并 canonicalize 每层 ring → 将每个 ring 顶点纳入 floor-namespaced axis reconcile → 回写并重验每层 ring → 矩形 ring 的 envelope transaction 同步移动 ring+attached cells，非矩形则整轴不动并记 unsupported → 从最终 rings 派生顶层全楼 bbox → post-core 重验 fingerprint/ref。
- 增负例：删 v3 footprint、只改 cells、只改顶层 bbox、矩形 envelope 成功、L 形 envelope unsupported；judge/render/validator 都必须得到同一 fail/geometry，不能有 dict adapter 特赦。

### B2-03 — HIGH — 所谓“精确类型冻结”仍留下长度、有限性、唯一性和可变性二选一

`FacadeSegment` 的 `p1/p2/normal/world_along_interval/visible_intervals` 都只是裸 `list[float]`（`AI_agent/proposals/c2_b2_detail_spec.md:64-77`）：长度 0/1/3、NaN/Inf、逆区间、重叠可见区间、非单位 normal 都能过类型层。segment id 全局/每层唯一性、segment 的 floor fingerprint 是否匹配引用层、interval 是否在 segment span 内也未冻结。`NorthAxisEvidence.uncertainty_deg` 没有非负/有限约束，hash 字段没有 digest 形状约束（`:91-104`）。

`Floor.id` 被称为 immutable，但现有 Pydantic 模型默认可变，core 又明确原地 mutate 整个 geom（`src/agent/correction/deterministic.py:724-734`）；只写“核不改”不是 immutability 机制。引用完整性若只在初次 model validation 做，core 后也没有自动重验。

**建议修法**：用 fixed-length constrained tuple/type（明确 p1/p2 是 world-XY 二元组）、finite float、`lo < hi`、sorted/disjoint/subset validators、cardinal unit normal、唯一 segment id、64-hex digest 类型；`Floor.id` 用 frozen field 或不可变 identity 子模型。明确 v3 至少一层、每层非空 cells、source_ids/knowledge_ref 的条件约束，并在 finalize 后执行完整 contract revalidation。Vg 可以决定值，不能替 B2 临场决定 wire type。

### B2-04 — HIGH — `Window.floor` 跨版本改义会让 judge/render 静默丢窗；裁决为新增 `floor_id`

当前 `Window.floor` 明确是字符串，现实消费者按 `Floor.name` 使用（`src/agent/correction/schema.py:43-52`）：

- correction scorer 的 floor map 以 `fl.name` 为键（`src/agent/judge/correction_score.py:62-122`），窗口再用 `win.floor` 查该 map（`:285-307`）；末尾完整性检查也拿 window floor 与 `{f.name}` 比（`:405-415`）。
- elevation scorer 直接 `floor_map.get(win.floor)`（`src/agent/judge/elevation_score.py:964-1000`）。
- corrected-geometry renderer 以 floor name 过滤窗口（`scripts/tool_scripts/render_corrected_geometry.py:114-120,181-182`）。

细稿只增加 `floor_key()` 并点名 deterministic per-floor 桶，不能覆盖这些消费者。若 v3 同字段突然装 id，scorer/elevation/render 会把合法窗当 unmatched 或不画；这不是小范围 helper 能兜住的兼容变化。

**建议修法 / 开放问题裁决**：v3 新增并要求 `Window.floor_id`，`floor` 保留为 deprecated legacy/display name，不能继续当主键。若过渡期两字段并存，validator 必须要求 `floor_id` 唯一引用且 `floor`（若给）与该 Floor.name 一致；内部 consumer 统一先 resolve id，再在需要展示/映射 gt 时取 name。v1/v2 adapter 从 legacy `floor` 解析，但不得伪造持久 v3 id。全量改 scorer、elevation、render、audit、validator，并加重名 Floor.name 负例。

### B2-05 — HIGH — “v3 随 B5 才生产发射”把 B2/B3/Vg 的真实 producer 倒挂到下游

上位 DAG 是 `B2 → B3/Vg → B4a/B4b → B5`（`AI_agent/proposals/c2_full_unlock_design.md:97-123`），且 v3 `Floor.footprint` 的 owner 是 correction。B2 却保留生产 prompt 的 v2 文案直到 B5；当前 prompt 确实硬写 schema 2（`src/agent/pipeline.py:317-328`）。结果是：

- B2 名义上冻结并贯穿 v3，却不提供一份生产 accepted v3 artifact；B3、Vg、B4a/B4b 全部只能在手写 fixture 上通过。
- B5 同时成为“首次真实 v3 producer + segment/window 接线 + prompt 切换”的大爆破点，而 B5 又依赖已经用纯合成输入验收的 B4b。
- prompt 会嵌入统一 `CorrectedGeometry.model_json_schema()`（`src/agent/pipeline.py:300-302`）。若采用 B2-01 的单类方案，文本说 v2、JSON schema 却展示所有 v3 optional slots，恰好制造细稿声称要避免的半成品 v3/v2 混合输出。

**建议修法**：按上位 DAG，B2 在生成独立 `Floor.footprint` 后就发射 v3；尚未施工的 segment/ref 以合同明确的空/None 状态存在，并由 capability/readiness gate 区分“schema 可表达”与“feature 已填充”。prompt 必须按目标版本提供版本专属 schema。若坚持到 B5 才发射，就必须把生产 footprint writer、B3/Vg 真实验收和 DAG 一并后移，属于修改上位定稿，不能由本细稿自行决定。

### B2-06 — HIGH — evidence-debt 开放问题建立在错误事实之上，且 flow 的 post-core 检查可被 core audit 洗掉

flow 不是“无 coverage check”：`check_correction` 已调用它。真正风险更隐蔽：pipeline 在 deterministic core 前检查（`src/agent/pipeline.py:897-919`），flow 先跑 core 再在总 check 内检查（`scripts/tool_scripts/run_stage.py:181-195`）。coverage 判定只要 corrections/conflicts 任一文本包含 offender id 就算 covered（`src/validator/checks/correction.py:534-578`）；而 core 会生成大量带 cell/window id 的 audit target（例如 `src/agent/correction/deterministic.py:760-770,783-796,925-930`）。因此一次普通 snap audit 可能替 LLM “认领”它从未处理的 reading evidence debt，pipeline 会挡、flow 会放。

**建议修法 / 开放问题裁决**：evidence-debt policy **不进**纯 `finalize_correction_draw`，但也**不得留到 B5**。B2 内抽一个两路径共用的 pre-finalize check，且 coverage 只能接受 correction/A3 明确声明的 debt resolution entry（typed debt id/source），不能用任意 deterministic audit 字符串命中。pipeline 可维持 fail-fast；flow 将同一事实并入当前 draw 的 gate① report，使 blocked draw 仍按 attempts 记账。补“core audit 同 id 不得洗债”的路径对等负例。

### B2-07 — HIGH — finalize 的 stage-root writer 没有绑定 accepted attempt，audit 仍可指向被拒绝 resample

细稿让 finalize 直接写 stage root 的 `correction_geometry_snapped.json + corrections.json`，但 flow 的 attempt 是 finalize 返回后才创建；`StageRunner.record()` 只归档 `output.json` 和 `checks.json`（`src/agent/execution/stage_runner.py:124-180`）。仓库自己已承认 stage-root snapped 可能被后来的 blocked draw 覆盖，所以 `_load_snapped()` 必须优先 accepted attempt（`scripts/tool_scripts/run_stage.py:199-228`）。`corrections.json` 却没有相同保护，baseline/report 仍直接读 stage root（`scripts/tool_scripts/record_baseline.py:372-395`、`scripts/tool_scripts/report_assembly.py:373-394`）。

因此“两个文件唯一 writer”不是 accepted-attempt identity；一次拒绝的 resample 可以让下游几何读 accepted output、最终 REPORT 却展示 rejected audit。仅比较两个 wrapper 的 stage-root snapped bytes 也抓不到这类漂移。

**建议修法**：finalize 返回 `{geom, audit_payload}`，attempt writer 在同一 NNN 下原子归档 output/checks/audit；只有 gate①接受后才 promote stage-root convenience copy。更小的兼容修法是彻底从 manifest-accepted `attempts/NNN/output.json` 派生 audit/report，不再信任 root sidecar。parity 测试必须覆盖“001 accepted → 002 blocked → downstream/report 仍全绑定 001”。

### B2-08 — HIGH — 新默认字段会改变所有 v1/v2 序列化 bytes/hash；“零 golden”缺 version-gated serializer

当前两条 writer 都使用普通 `model_dump_json(indent=2)`，没有排除新默认字段（`src/agent/pipeline.py:939-954`、`scripts/tool_scripts/run_stage.py:184-190`）；attempt writer 同样直接 dump model（`src/agent/execution/stage_runner.py:140-154,184-189`）。一旦在单类上加 `Floor.id=None/footprint=None`、`facade_segments=[]`、`north_axis=None`、Window 新字段，所有 v1/v2 输出都会多键，accepted output hash、approval/packet 身份随之变化。after-validator 跳过 v1/v2 并不会阻止默认序列化。

这正是上位 `AI_agent/proposals/c2_full_unlock_design.md:128` 只在 version-gated serializer 落地后才允许 byte-equivalence 承诺的原因。当前 570/9 全绿不能证明改造后零爆破。

**建议修法**：增加唯一的 version-aware serializer，并让 pipeline、flow、StageRunner、parity test 全部调用；v1/v2 显式排除 v3-only 字段但保留现有默认键，不能粗暴全局 `exclude_defaults=True`。未落该 serializer 前，把 B2 §2.6 的“逐字节不变”降为 semantic/geometry equality，并补 legacy serialized bytes/hash、accepted attempt hash、judge packet 与 render 的回归。

## 三、B-M findings — **REWORK**

### BM-01 — BLOCKER — generator 用“图种常量”凭空制造 completeness，C-03 的可信负证据前提没有落地

现有 case metadata 只提供路径、楼层、`dimensioned` 与方向键；helper 也只派生 dimensioned name（`src/agent/execution/case_metadata.py:41-75`）。sm21 实样同样没有“本图完整表达 openings”声明（`case_tests/e2e_tests/sm21_anchor/case_data/testdata_prompt.json:7-22`）。然而 B-M §3 规定 generator 自动把 dimensioned plan/elevation 升成 `declares_openings=true`、`coverage=full` 和一组 `negative_evidence_capable_claims`，`completeness_basis=drawing_convention`；只有 metadata 显式关掉才撤销。

`dimensioned` 只证明有尺寸，不证明所有 openings 都画全；“elevation 这种图通常画窗”也不是某一张图的可信 completeness evidence。默认 true 是 fail-open：没有受信声明时，本应只是“无独立佐证”的缺失，会被升级为 conflict/miss denominator。`coverage: "full"` 还是无坐标框架的标量，无法自身证明某 opening 位置在 plan region 或 Vg-visible elevation interval 内。

sm26 尤其危险：常量 elevation 行同时宣称 existence/along/width/sill/head/appearance 可作负证据；若 Va 没有先与 Vg visible interval 做强制交集，hidden 内壁窗在完整 elevation 中“没出现”就会被误判。细稿把 Va 留后批，却没有给 B-M schema/测试写下这个不可绕过的组合门。

**建议修法**：

- 静态常量表只能声明 `potentially_observable_claims`，不得声明 case-specific completeness。`negative_evidence_capable_claims` 默认空；只有 case metadata/user 的显式受信断言，或有版本、有引用的 dataset contract，才能开启。
- coverage 改成 typed domain（plan floor polygon/region；elevation local-along/z interval 或 `full_building_projection`），带 coordinate frame、source_ref、completeness assertion id。Va 必须机械取 `trusted coverage ∩ Vg visible intervals`，reader 自报字段永不参与。
- sm26 固定负例：plan 的正证据保留 existence/host/along/width；hidden elevation absence 不构成负证据；sill/head 值可 assumed 但 denominator 为 NA。再加“无显式 completeness 时 absence 仅 uncorroborated”和“reader 漏读显式完整 plan 才是 miss”。

### BM-02 — BLOCKER — isolation 可绕过 manifest generator 与 coverage gate，空 views 也会被直接接受

B-M 只在测试里断言 staging 中没有 `view_manifest.json`，却没接 `merge_isolated_output()`。现实路径是：builder 复制 inputs 后保存 staging MANIFEST（`src/agent/execution/isolation.py:91-120`）；merge 随后把任意 output bytes 写入 attempt，手造一个仅含 `reading.isolation_provenance_bound=PASS` 的 CheckReport，并在 `accept=True` 时直接写 accepted StageRecord（`:150-214`）。现有测试甚至明确用 `{"views":[]}` 并断言已接受（`tests/test_isolation.py:286-302`）。

这条入口既不解析 ReadingView schema，也不比较 manifest view ids，更不绑定拟议 `view_manifest_sha256`。所以正常 flow 即使加了 `reading.view_manifest_coverage`，isolated reader 仍可提交空清单并成为 accepted 0_reading；C-03 的 denominator 防洗在入口处已经失守。

**建议修法**：在 isolation build 前 ensure trusted manifest，并把其 hash 写入 staging provenance/最终 StageRecord input hashes；merge 对实际 aggregate payload 调与 flat-flow **同一个** coverage/schema checker，report.blocking 非空时绝不能因调用者 `accept=True` 强制接受。pilot/partial output 不得冒充完整 0_reading accepted stage：要么是未接受的 partial attempt，要么等所有 manifest entries 汇总后一次 gate。加 empty/missing/extra/tampered-image/changed-manifest 五组 isolation 负例。

### BM-03 — HIGH — `view_direction` 同时冒充 raw label 与 building-axis direction，`true_azimuth` 分支违反 C-04

细稿把 `view_direction` 定义为“建筑系立面族”，又无条件从 metadata 的 `<Dir> view` 键写入；`views:{}` 只覆盖 `direction_semantics/azimuth_deg`。于是一个 `South` 标题若声明 `direction_semantics=true_azimuth`，同一 entry 同时声称“建筑系 South”与“地理方位 South/azimuth”。`unknown` 也仍携带看似已解析的 building direction。

上位要求是：仅 `building_axis` 可直接得到 N/S/E/W；`true_azimuth` 必须带数值并经 θ 映射，unknown/不可唯一映射 conflict（`AI_agent/proposals/c2_full_unlock_design.md:77-80`）。B-M 当前字段会让 Va/Vg 调用者有两条合法读法，正是 C-04 要消灭的隐性二选一。

**建议修法**：拆成 `declared_direction_token`（原始 N/S/E/W/title token）+ `direction_semantics` + `azimuth_deg`，另设 `building_view_direction: ... | None`。B-M 只填 raw/trusted metadata；仅 semantics=building_axis 可当场填 building direction。true_azimuth 由 E4 adapter 绑定 accepted θ/orientation digest 后产生 resolved building direction；Vg 仍只收 polygon+resolved direction vector，Va 才收 manifest/opening claims，B-M 不侵入 Vg。

### BM-04 — HIGH — 所有 staged 图片没有全分类；supplementary 图会在“应读”与“额外产物 fail”之间互相打架

isolation 会复制 case_data 下**所有 PNG**（`src/agent/execution/isolation.py:252-260`），kickoff 只告诉 reader “drawings are at case_data”（`:308-322`）。现 reading skill 又要求每个 source image 有一行/一个 output，并明确列 `supp_plan.png → supp_plan_view.json`（`skills/intake_pipeline/0_reading/session_kickoff.md:44-58`）。sm20 metadata 确有一张显式 supplementary plan（`case_tests/e2e_tests/sm20_anchor/case_data/testdata_prompt.json:12-16`）。

B-M 的映射表只覆盖 `Floor plans[]`、四向 elevation 和 `views:{}`，没有为其他图片定义合法分支；按稿内仅剩的数据结构，它们只能被漏掉或误塞进不受信的 `undeclared_images`。新 gate 又规定任何清单外 stem 都 fail。这里有两个错误：

- `supp_plan` 实际已被 metadata 声明，不能叫 undeclared；schema 虽列 `detail/site_plan`，generator 没有到达它们的规则。
- source stem `supp_plan` 与 skill output stem `supp_plan_view` 不相同，细稿的“image stem 就是对账键”只对本来以 `_view` 结尾的标准文件碰巧成立。

更坏的是 audit-only unknown PNG 仍对 reader 可见并可影响产品，却不进入 judge denominator，形成旁路证据面。

**建议修法 / 开放问题裁决**：每个 staged image 必须在 trusted manifest 中被**全分类**为 `required_view` 或 `excluded_input`（带 deterministic reason/source relation）；未知、非 allowlist 图片生成期 BLOCK。`_source.png` 等确证为同源工作副本的文件可按版本化规则排除并绑定 parent hash，不能泛化为“文件名像工作副本就忽略”。metadata 已声明的 supp/site/detail 应建 typed entry，是否要求 reader output 由 entry 明写；对账使用显式 `expected_output_id`，不猜 stem。给 reader 一个只含 input inventory/id/type/raw direction 的只读 staging projection；negative-evidence/completeness 仍留受信原件，避免让“隐藏 manifest”妨碍合法命名却没有增加真实防篡改能力。

### BM-05 — HIGH — `validate_case`、run manifest 与 judge-only 接线互相冲突，且没有 legacy/零-golden 迁移

细稿要求 `validate_case` “生成/校验”清单，但该函数的合同是 non-invasive audit（`src/agent/execution/validation_run.py:1-14`），默认 `write_reports=False`；只有显式写报告时才写独立 `validation_manifest.json`（`:277-283`）。现测试还断言 validate_case 不创建/覆盖 run manifest（`tests/test_validation_run_baseline.py:54-65,99-105`）。若默认生成 `_run/view_manifest.json`，直接验证仓库内旧 anchors 就会改 golden 工作树，与“零 golden”矛盾。

`run_manifest.json` 也没有可放 run-level hash 的槽：`RunManifest` 为 `extra="forbid"`，字段只有 case/version/stages（`src/agent/execution/manifest.py:114-135`）。此外还有两个 writer：普通 `save()` 与 isolation 的 `_atomic_save_manifest()`（`src/agent/execution/isolation.py:514-524`）。细稿只写“登记 view_manifest_sha256”，没决定顶层字段、manifest version、旧文件迁移或 isolation writer。所谓 judge-only 幂等校验也没有现实 hook：`cmd_judge` 直接 load accepted record 和 verdict（`scripts/tool_scripts/run_stage.py:1383-1406`），不会经过 `_draw_reading`。

**建议修法**：

1. run provisioning/0_reading preflight 是唯一 emitter；`validate_case` 只在内存重建 expected manifest 并比较磁盘/hash，默认绝不写。缺失/漂移形成 report；显式 migration CLI 才可落盘。
2. 冻结 manifest evolution：建议 `RunManifest.manifest_version` bump，并加 typed run input hash，且 0_reading StageRecord.input_hashes 同时绑定该 hash；普通 flow、isolation、judge/replay 共用 `ensure_view_manifest()`。
3. 老 run 以旧 manifest version 明确 grandfather/NOT_APPLICABLE，或一次性迁移并登记；不能在 validate 时静默补文件。新 run 一律 required。把“零 golden”定义为不改现有 anchor artifacts，同时新测试证明 legacy 行为和新合同各自明确。

### BM-06 — HIGH — “exploratory=warn / regression=block”不是现有 disposition 的自动行为；裁决为所有 profile 恒 BLOCK

当前 disposition 只有特定 evidence check ids 才按 run profile 分档；普通 INVARIANT fail 在所有 profile 都 BLOCK，普通 CROSS_CHECK fail 在所有 profile 都 FLAG（`src/validator/checks/schema.py:106-145`）。新 id `reading.view_manifest_coverage` 既不在 evidence 集合（`:41-59`），细稿也没定 layer，所以“走现有机制即可得到 exploratory warn / regression fail-closed”在 HEAD 上不存在。

这个 check 不是模糊感知质量，而是 accepted input identity/completeness。已有“一个 view 都没有”的 `reading.present` 就是 INVARIANT（`scripts/tool_scripts/run_stage.py:106-121`）；少一个 manifest-required view 与少全部是同类事实，不能因 exploratory 把洗分入口打开。

**建议修法 / 开放问题裁决**：`reading.view_manifest_coverage` 定为 `CheckLayer.INVARIANT`，missing/extra/identity/hash mismatch 在所有 run profiles 均 BLOCK；partial C2 又已明确不支持，没有合法降级态。需要探索单图/pilot时，使用未 accepted 的 partial attempt/独立工具模式，不把不完整 0_reading 放进正式 DAG。

### BM-07 — MEDIUM — generator 若复用现 metadata loader，会把缺失/坏 JSON 静默变成空清单

`load_case_metadata()` 对找不到文件、JSON 解析失败、非 dict 都返回 `{}`（`src/agent/execution/case_metadata.py:9-28`）。这对旧 helper 是宽容行为，对 trusted-manifest generator 却是 fail-open；结合 audit-only `undeclared_images`，一份坏 metadata 可能退化成“没有受信 views，所有 PNG 仅审计”而非硬错。metadata 路径还常是 repo-relative（例如 sm21 的 `case_tests/.../case_data/*.png`），细稿没有冻结如何解析成 case-relative `source_image`，也没写防 path escape/symlink 规则。

**建议修法**：generator 使用独立 strict loader：metadata 必须存在、合法 object；声明路径必须解析到当前 case allowlisted input root、文件可读且非逃逸，随后统一 emit `case_data/<name>`。定义 repo-relative legacy path 的唯一归一化算法、重复 basename/stem 冲突、大小写、symlink 和非 PNG 行为。写盘用 temp+fsync/replace 或现有等价原子 helper，不能仅靠“重算 hash”处理并发半写。

### BM-08 — MEDIUM — schema v1 仍缺条件约束与语义版本，hash 只能证明 bytes，不能解释 claims

JSONC 样例没有冻结 submodel `extra="forbid"`、唯一 view_id、条件字段互斥/必填、azimuth finite `[0,360)`、source path 规范、claims 去重/排序/受控词汇等。正文说“CLAIMS_VOCAB_VERSION 同记”，但顶层 schema 样例只有 manifest schema version、case/views/undeclared/hash，没有 `claims_vocab_version` 或 generator/ruleset version。两行常量以后改义时，旧 manifest 的相同 schema_version 无法解释。

**建议修法**：用 strict typed models 冻结条件：plan 必有 floor_ref 且不得有 elevation-only resolved fields；true_azimuth 必有 finite normalized angle；unknown 不得伪装 resolved direction；claim 集合来自版本化词汇且 canonical sort。顶层加入 `claims_vocab_version`、`generator_version/completeness_ruleset_version`，hash 绑定规范化 payload和源 metadata hash。所有 consumer 先验 schema+版本+content hash，再读字段；未知版本 fail closed。

## 四、四个开放问题的明确裁决

| 开放问题 | 裁决 |
|---|---|
| B2 §9.1 evidence-debt BLOCK 是否进 finalize/是否维持差异 | **不进 finalize；但必须在 B2 内闭合，不得留 B5。** 两路径在 core 前调用同一 typed debt-resolution check。pipeline 可 fail-fast；flow 以 gate① blocked attempt 记账。core audit 不得充当 LLM debt resolution。 |
| B2 §9.2 `Window.floor` 是否跨版本改义 | **否。采用新 `Window.floor_id`。** v3 要求 floor_id；legacy `floor` 保留/deprecate，若并存须一致。所有 consumer 经 resolver，禁止同字段在 v1/v2 表示 name、v3 表示 id。 |
| B-M §7.1 manifest coverage 在 exploratory 的处置 | **所有 profile 恒 BLOCK。** 这是 input identity/completeness INVARIANT，不是感知证据质量；pilot 用非 accepted partial 工作流。 |
| B-M §7.2 `undeclared_images` audit-only 还是 raise | **未知图片 fail closed；已知派生物显式 allowlist/excluded。** 每个 staged image 全分类。metadata-declared supp/site/detail 不得落入 undeclared；工作副本须绑定 parent/reason，不能宽泛 audit-only。 |

## 五、重新送审门

### B2

1. 以 strict v3 wire model + legacy adapter 替换单类 after-validator 等价性主张，并给出版本专属 serializer/prompt schema。
2. 删除 v3 的 cells→footprint fallback，写死 Floor.footprint canonical/snap/envelope/全楼 bbox 的单事务 writer 与 post-core revalidation。
3. 冻结 FacadeSegment/NorthAxis/identity 的 constrained types；采用 `Window.floor_id` 并列出全部 consumer 改面。
4. 解决 v3 生产发射与上位 DAG 的倒挂；B2/B3/Vg 至少各有真实 producer-path 合成 E2E，不只直接构造 post-schema object。
5. 两路径 pre-core evidence-debt 对等；accepted attempt 同时绑定 geometry/audit。新增 blocked-resample 不污染 accepted report 的回归。
6. 保住现有 579 项的 570 pass + 9 strict xfail 状态，并让新增测试另行通过；不得修改 sm20/sm21 golden 来掩盖默认字段、hash 或 envelope 行为变化。经批准的 flow envelope 缺陷修复用独立非-golden fixture 明示。

### B-M

1. 将“可观察 claim”与“本 case 完整性声明”拆开；默认无负证据，coverage/completeness 必须有 typed trusted source，补 sm26 hidden-window 反例。
2. 普通 flow、isolation merge、validate_case、judge/replay 全部调用同一 manifest ensure/check；空 isolation output 不得 accepted。
3. 拆 raw direction 与 resolved building direction，true_azimuth 只经 accepted θ adapter 解析；维持 Vg/Va 责任边界。
4. 对全部 staged images 做 required/excluded 全分类，冻结 expected_output_id；reader 获得只读 input inventory projection。
5. 冻结 RunManifest 演化、0_reading attempt hash 绑定、legacy run 迁移和 validate_case 只读语义；补原子写/篡改/换图/judge-only 测试。
6. 现有 579 项的 570 pass + 9 strict xfail 必须保持；新增 manifest 测试不能在 validate 旧 anchors 时落盘或改 golden。

## 审阅需求（review-ask）

none — 四个开放问题已在本 verdict 裁定；按上述重新送审门修订两份细稿后再审。
