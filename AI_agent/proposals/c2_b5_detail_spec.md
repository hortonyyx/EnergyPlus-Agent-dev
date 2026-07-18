# C2 B5 施工细稿 v3：source-aware 窗挂载 / 宿主解析 resolver

- 日期：2026-07-18
- 出稿：sol
- 状态：r2 APPROVE-WITH-CHANGES 后累计式定稿候选，待 Fable 窄增量复核
- 施工边界：B5 只落“窗 → facade segment → room boundary → built parent wall”；不改墙、楼板、屋顶造面，不接管 B5b coverage/REPORT/HTML
- 权威基线：`c2_full_unlock_design.md` v2.2 §E1'、§E2'、§122 B5 行、§128；B2 v6；B4b v2；现码基线 `6d5fd1b`

> 本稿是累计式、自包含施工合同。执行者只读本文件即可定位数据流、wire、函数签名、拒绝条件、配置、测试和验收，不得用“沿用上一版未变部分”补正文。

---

## 0. 执行结论

B5 在 correction **确定性核**内新增唯一的 production host resolver。LLM 只声明窗几何和可追溯的 reading source locator；代码负责 source 分类、segment 候选、room-boundary interval、clamp、parent wall、顶点、hash、validator/audit/specs/judge 接线。任何零解、多解、跨缝、room 不符、source/identity/hash 不一致均 fail closed；不得以窗中心、最近墙、输入顺序或 id 字典序破局。

本稿冻结以下结论：

1. v3 窗不再按 cell bbox clamp。`window_clamp_to_parent` 和现有 `_find_parent_wall` 只留给 v1/v2 legacy；v3 沿 facade segment 的真实区间 clamp，并在完整 room-boundary interval 上验宿主。
2. resolver 有且只有两条实体挂载分支：
   - 有任何经核验 plan existence source → **plan 分支**；候选是该层/该 family 的全部外边界段，hidden 不过滤；
   - 无 plan、至少一个经核验 elevation existence source → **elevation 分支**；候选必须在对应视图方向上有正宽 visible overlap。
   - plan+elevation 同时存在仍走 plan 分支；elevation 是属性/矛盾佐证，不能把 plan 窗从 hidden 段赶走。
3. `facade_segment_id` 与 `room` 是两个独立引用。segment 可跨多个 room；resolver 必须同时写/验二者，永不以 segment id 代替 room。
4. 跨 segment 边界、segment 零/多候选、room interval 零/多候选、已声明 room 不符、source 身份不完整均为结构化 conflict/A3/interactive；本次 attempt 不可 accepted。
5. “另一通道无窗”只有在 Va 证明另一通道对目标 span 的 trusted negative coverage 完整，且 manifest 对 `existence` 明确承诺 openings 完整表达时才是 conflict。遮挡、hidden、裁切、无 completeness 或 coverage 不满只记 `uncorroborated`，不删窗、不降级挂载。
6. resolver写出的segment id、room、clamped span、p1→p2参数、plan clamp endpoints、四个3D clamp顶点、host/evidence digests及aggregate均由代码重算；Va ledger只绑定正式serializer产生的output/feature hashes。finalize、attempt writer、accepted loader、geometry build边界逐层复验；缺sidecar、hash断链或复算不同一律拒绝，禁止except后继续。
7. `window_verts_on_line`（替换现`_window_verts`）的公开低层接口只认识任意2D有向线段`p1→p2`、参数区间`t0<t1`和z区间，不认识North/South/East/West或x/y常量面。C2 adapter仍只接schema允许的轴向`FacadeSegment`；斜线helper正例为C4留接缝，斜`FacadeSegment`进入C2必须拒绝。
8. v1/v2（包括 lax extra 中伪造的 `facade_segment_id`）显式走现有 legacy window snap/clamp/parent/serializer 路径，不读取 B5 source/proof，不改变 built geometry/specs/audit 语义。
9. B5 新增两个 accepted-attempt sidecar：`window_resolver_inputs.json` 与 `window_hosts.json`，并新增 B5 artifact contracts；不能把 resolver digest 塞进现有 feature-state 四轴，也不能用 feature-state 非空列表冒充 host proof。
10. 现役 E4 orientation enrichment 必须消费并重新绑定 B5 host proof：north-axis enrichment 改变 output hash 后，旧 `window_hosts.json` 不能原样沿用。

## 0.1 In / Out

### In

- v3 window source catalog、source locator 与 provenance 核验；
- v3 pre-host/final-host finalize 时序；
- source-aware 两分支 resolver；
- segment endpoint clamp、room-boundary 完整 span、built parent wall；
- p1→p2参数化`window_verts_on_line`；
- resolver strict wire、conflict/negative-evidence wire、hash chain；
- validator、audit、specs、judge、E4 accepted-artifact 接缝；
- 新容差进 `correction.yaml`、`CoreTolerances`、A0；
- 全分支正/负/防篡改/legacy 测试。

### Out

- 墙/楼板/屋顶造面与 split-pairing 算法；
- prior 补 sill/head、knowledge table；
- B5b observed-zero/unknown-fenestration coverage 归档、REPORT assumed 桶、HTML 三色；
- C4 schema 对斜 segment 的正式放行；
- 图像匹配、OCR、LLM host 判断；
- GT/golden 资产改动。

---

## 1. 现码对账与必须替换的错误路径

以下是 `6d5fd1b` 的真实迁移起点，施工简报必须逐项给出落地位置，不得只按旧细稿行号猜：

| # | 现码事实 | B5 动作 |
|---|---|---|
| 1 | `deterministic.py` 的 window pass 在 Vg materialize 前运行；span 按 `w.room` 的 `Cell.x/y` bbox clamp | v1/v2 原样封装为 legacy；v3 拆出 pre-host snap + final segment clamp，禁止 cell bbox |
| 2 | `finalize_correction_draw` 先跑 monolithic core，后 materialize Vg，随后即 final validate | v3 改为 §3 固定时序；B5 commit 后才是 accepted final |
| 3 | B2b `resolve_unique_window_host` 用 room cell edge + footprint edge，且 elevation-only room 为空时直接拒绝 | 替换为 B5 dry resolver；用临时 Vg，既支持 plan hidden，也支持 elevation 补 room |
| 4 | `WindowV3` 已有 `floor_id`、`facade_segment_id`、field provenance；`FacadeSegment` 已有完整 p1/p2/normal/span/visible/fingerprint | 不 bump correction schema；复用槽位，host proof 进独立 sidecar |
| 5 | v3 draw contract 禁 producer 写 `facade_segments`，但未统一禁止 producer 自报 segment ref/host audit | B5 draw 明确要求全部 ref 为 null、reserved resolver audit 缺席；唯一 writer 是代码 |
| 6 | `_window_verts` 按 facade 分 N/S 与 E/W；`_find_parent_wall` 写死 0.05m seam/inset 和 cardinal axis | 旧函数重命名`_legacy_cardinal_window_verts`；v3只调公开线段接口`window_verts_on_line`与命名容差 |
| 7 | built `Window` 只有 name/parent/verts；kernel gate 未把 source window、segment、host digest 一一对账 | v3 internal window/proof 扩展 + `kernel.window_parent_binding` |
| 8 | `check_windows_on_wall` 只验 room bbox；B4b judge 有 temporary segment binding，但明确不写回 | v3 validator 消费 proof；judge 独立重算关系并要求正式 B5 artifact contract |
| 9 | accepted correction contract 只有 B2/Vg 与 E4 orientation 四件套 | B5 增六件套，E4 enrichment 重绑 host proof |
| 10 | Va 与 `gt_manifest` 各有同名 `ElevationViewBindingV1` | B5 只 import `src.agent.correction.facade_applicability.ElevationViewBindingV1`（13 字段 Va 型），绝不 import 15 字段 GT-manifest 型 |

静态禁止项：

- v3 resolver/attach path 不得调用 `cell_facade_span()`、`Cell.x/y` 作 host/clamp 权威；
- 不得调用 judge 的 `bind_correction_window_segment()` 或 `resolve_correction_window_host()`；production 不反向 import judge；
- 不得使用`_facade_axis()`决定`window_verts_on_line`顶点；
- 不得复制 Va 的 completeness/negative 判据；
- 不得使用 `getattr(window, "facade_segment_id", ...)` 判断 v1/v2 capability；
- 不得出现 `except Exception: pass/return original` 类 fail-open。

---

## 2. 术语、所有权与不变量

### 2.1 术语

- **source observation**：受信 manifest 所列 reading output 中真实存在的一条 window observation，身份是 `(input_id, observation_id, output_sha256)`。
- **source locator**：`src:` + 上述三元组 canonical JSON 的 SHA-256；LLM 只能引用 orchestration 已列给它的 locator，不能自造 channel。
- **plan branch**：至少一个已核验 `existence` source 来自 plan。
- **elevation branch**：没有 plan existence source，至少一个已核验 `existence` source 来自 elevation。
- **segment interval**：`FacadeSegment.world_along_interval`，半开 `[lo,hi)`；实体 span 的闭端点表达不改变 segment 表的半开可见性语义。
- **room-boundary interval**：某 room polygon 的外边界与某 facade segment 同平面、同 outward normal 的一个最大连续 interval；不同 room、不同平面或中间有 gap 的 interval 不合并。
- **clamped span**：只把 raw/snapped span 超出已唯一选中 segment 端点、且超量不大于专用 clamp tolerance 的部分裁回 segment；不把跨 room seam 裁成“看似合法”。
- **host resolution**：floor + room + segment + room-boundary interval + clamped span + p1→p2 t interval 的完整关系。
- **parent wall**：built geometry 中属于已解析 room/zone、`stype=Wall`、`obc=Outdoors`、与 segment 共面同法向并完整包含窗 span 的唯一 Surface。
- **uncorroborated**：另一通道没有独立正证据，但没有获得完整 trusted negative；不是 conflict。

### 2.2 所有权

- `facade_segments`：Vg 唯一 writer；
- `WindowV3.facade_segment_id`、elevation-only `room`、v3 along clamp：B5 resolver 唯一 writer；
- host 顶点与 record hash：B5 deterministic helper 唯一 writer；
- applicability/negative interval：Va 唯一引擎；
- ring-free elevation direction facts：B-M/受信direction resolution提供，`window_sources.py`验证；ring-dependent 13字段Va binding：`window_sources.py` current-ring helper唯一production writer；
- parent Surface name 与 fenestration vertices：geometry realization 消费 B5 proof 后确定性产生；
- judge host score：B4b judge-only 独立重算，不写回；
- LLM：只输出未挂载 v3 draw 和 source locator provenance，不做 candidate/room/clamp/hash。

### 2.3 强制不变量

1. 每个 final v3 window 恰有一个 floor、一个 room、一个 facade segment、一个 resolution record；集合按 window id 精确相等。
2. `window.floor_id == segment.floor_id == room 所属 floor.id`，且 legacy display `window.floor == floor.name`。
3. `window.facade == segment.facade_family`；C2 normal 与 family 逐值相等，不用角度近似。
4. clamped span 完整落在 segment interval 和唯一 room-boundary interval 内；不得只验 center。
5. plan branch 的 segment candidate 集含 hidden；elevation branch 的 candidate 必有正宽 visible overlap。
6. visible 只影响 elevation entity/claim；不得反向阻断 plan entity。
7. segment id 永不充当 room id；即使两字符串偶然相等也分别解析、分别记 wire。
8. 跨 segment/room seam 不 clamp、不猜；物理 endpoint clamp 只处理已唯一 segment 的微小端点越界。
9. source locator 必须命中真实 reading observation，channel 由 manifest/reading 决定，不信 `FieldProvenance.method` 自报。
10. assumed provenance 不得立窗实体；每个 v3 window 的 existence 必须有 observed/derived 且非空 source locator。
11. hidden-window candidate/`uncaptured[]` 不是实体 source，不能进入 Window；它只可供 B5b/conflict audit。
12. resolver record/hash 不参与自身候选选择；hash 只在结果已独立算完后封装。
13. parent wall 必须唯一；零/多候选为 invariant failure，不能返回 notes 后继续。
14. v1/v2 不读取 v3-only extra；v3 不降级 legacy。
15. `WindowResolverInputsV1`不得含fingerprint/origin/axis/sign/frame hash；13字段Va binding不得持久化或跨ring缓存。
16. Va evidence不得改变已序列化candidate geom/audit；若evidence需要改output，视为时序INVARIANT而非重新hash重试。

---

## 3. 总数据流与 finalize 固定时序

### 3.1 端到端数据流

```text
trusted ViewManifest + reading output bytes + ring-free elevation direction facts
                         |
                         v
             build WindowSourceOfferV1
             (prompt-only locator/allowed-claim catalog)
                         |
                         v
LLM v3 draw (segment refs null; provenance only references listed locators)
                         |
                         v
             build + verify WindowResolverInputsV1
             (draw hash + links + direction facts)
                         |
                         v
structural snap + z clamp --[if B2b intent]--> transient Vg on one-use geom copy
                         |                         |
                         |                         v
                         |              derive Va bindings from THIS ring
                         |                         |
                         |                         v
                         |                 dry resolver -> B2b transform
                         +-------------------------+
                         |
                         v
                  final Vg materialize
                         |
                         v
derive Va bindings from FINAL ring -> final resolver -> commit room/ref/span/audit
                         |
                         v
final validate -> canonical output bytes + feature-state bytes/hash
                         |
                         v
Va with real candidate identities -> sidecar-only evidence / negative decision
                         |
                         v
writer byte-parity + independent host/binding/Va recompute
                         |
                         v
accepted output + audit + feature_states + resolver_inputs + window_hosts
                         |
             +-----------+-----------+
             v                       v
      geometry build             judge normalization
  recompute parent + verts    verify identity, independently score relation
             |
             v
      specs / IDF / kernel gate
```

### 3.2 为什么 v3 必须拆时序

现有 B2b 在 Vg 前要求 `window.room` 已存在；E1'.2 又允许 elevation-only window 在可见 segment 上补 room。若直接保留现序，会把合法 elevation-only 窗误拒；若先持久化 Vg 再做 B2b，segment id/fingerprint 会因 footprint transform 变 stale。故 v3 固定为：

1. `parse/ensure`：strict v3 draw；保存 floor/window/source identity snapshot；producer 预填 segment ref/resolver audit 在这里即拒；
2. `verify_window_resolver_inputs`：对真实 manifest/reading bytes/hash/source locator 与**不含任何 ring 派生字段**的 elevation direction facts 建 verified marker；
3. `apply_structural_core_pre_host`：ring/cell/z-stack/axis canonicalization；window 只 snap span/z，z 只 clamp 到 `floor[z_floor,z_top]`；**不按 room/cell clamp，不写 segment ref**；
4. 若无 B2b accepted intent，跳到第 7 步；
5. 对pre-transform canonical ring运行**临时、内存态**Vg；以`dry_geom = geom.model_copy(deep=True, update={"facade_segments": list(transient_segments)})`构造一次性视图，严格验证Vg后，由production helper按**dry_geom当前ring**派生Va 13字段bindings，再用同一B5算法dry-resolve。该helper调用只窄捕获`WindowDirectionBindingError`，立即经`map_direction_binding_error(..., phase="dry_pre_transform")`生成typed blocking conflicts并reject attempt；不得裸传播、吞掉、回滚后继续。用后丢弃`dry_geom`；不得回写原`geom.facade_segments`、window ref、audit或sidecar；
6. B2b在fresh candidate上消费ephemeral host关系，完成transform；变形后丢弃所有临时segment id/binding。B2b post-simulation gate对候选ring重跑临时Vg、重新构造一次性geom、重新按**候选当轮ring**派生binding，再dry-resolve；helper异常只窄捕获并经`map_direction_binding_error(..., phase="dry_post_transform")`转typed invariant reject，不能被B2b普通几何回滚掩盖后继续。floor/room/facade/完整span必须仍唯一；绝不复用pre-transform id、fingerprint、origin或frame hash；
7. 对最终 post-core ring 调 Vg，**首次持久化** `geom.facade_segments`；
8. 由production helper按**final ring**重新派生Va bindings；`WindowDirectionBindingError`只窄捕获并经`map_direction_binding_error(..., phase="final")`转typed invariant reject。随后调B5 final resolver计算几何host records，全部成功后在fresh geom一次commit room/segment/span/provenance/typed audit；运行`validate_final_corrected_geometry`+B5 geometry totality。host resolution record不含Va负证据，故此后Va不会再改output/audit；
9. 用与writer**同一个versioned serializer**将candidate geom预序列化为 `candidate_output_bytes`并算真实output SHA；提前fresh derive feature-state claims，构造 `FeatureStatesArtifactV1(output_sha256=...)`，用writer同一serializer得到真实feature-state bytes/SHA。两份bytes与hash封入`PreparedCandidateIdentity`；禁止占位64-hex；
10. 从final segments构造Va visibility ledger：`source_output_sha256`必须等于步骤9真实candidate output hash，`feature_states_sha256`必须等于步骤9真实feature-state artifact hash，helper tuple按现Va合同精确；用步骤8的final-ring bindings调用Va。Va结果只进入sidecar-only `WindowEvidenceLedgerV1`并通过evidence totality check；trusted-negative conflict则整次B5 commit作废并返回rejected attempt；
11. 形成`FinalizeResult`：geom、audit、feature claims、geometry host claims、evidence ledger、verified inputs、prepared identity；
12. writer再次用同一serializer从runtime geom取bytes，必须与prepared bytes**逐字节相等**，并独立重算feature artifact、Vg、final-ring bindings、host claims与Va evidence；全部相等才绑定output hash并原子写attempt bundle。

临时 Vg 与 final Vg 调同一 public Vg、同一 `VisibilityTolerances`。临时 Vg 是变形安全证明，不是第二份真值；只有第7步segments可进入output/feature-state。方向事实可跨ring冻结；`source_footprint_fingerprint/along_origin/world_axis/sign/frame_transform_sha256`只能由每轮current-ring helper瞬时派生，禁止跨dry/final缓存。

### 3.3 legacy 固定时序

`apply_deterministic_core`入口只做**分派决策与模式标记**：v1/v2标为legacy、v3标为B5；绝不能在入口提前执行window pass。v1/v2的`_apply_legacy_window_pass`执行位置保持现码顺序不动：先完成全部结构axis snap、cell/ring canonicalization与z-stack，再在`deterministic.py`原窗口block所在位置调用。其函数体只允许对现 `deterministic.py` window block逐行等价搬移：

- `window_snap_grid_m`；
- `window_clamp_to_parent` 开关；
- parent cell `x/y` clamp；
- current min-edge/full-wall-face guard；
- 当前deterministic window correction audit的字段、文案与append顺序。

geometry侧另行分派，不能混进上述correction helper：现 `geometry/modelling.py` 的parent寻找逻辑、cardinal顶点逻辑（施工时仅重命名为`_legacy_cardinal_window_verts`）、built naming以及`geometry/specs.py` legacy serializer均**原模块原位置保留**，`build_geometry`按schema选择legacy/B5 attach。不得把这些函数搬入`deterministic.py`，不得改变其调用顺序、notes或命名排序。

legacy 分支不构造resolver inputs/host proof，不看facade segment feature，不因lax extra改行为。回归fixture必须包含“结构snap确实移动cell clamp边界”的窗，证明window pass仍消费已snap cell；未知未来schema fail closed。

---

## 4. Strict resolver input wire 与 source 路由

所有 B5 wire 使用 Pydantic v2、`extra="forbid"`、strict scalar、finite float、frozen model。JSON canonicalization 固定：Pydantic JSON 标量、UTF-8、`sort_keys=True`、`separators=(",", ":")`、`ensure_ascii=False`、禁止 NaN/Infinity，SHA-256 小写 hex。

### 4.1 常量

```python
WINDOW_RESOLVER_INPUT_SCHEMA_VERSION = "1"
WINDOW_HOST_SCHEMA_VERSION = "1"
WINDOW_HOST_HELPER_VERSION = "window_host_resolver_v1"
WINDOW_HOST_ARTIFACT_VERSION = "window_hosts_v1"
SOURCE_LOCATOR_PREFIX = "src:"
```

claim vocabulary 直接 import `src.agent.correction.claims.WINDOW_CLAIMS` 和 `CLAIMS_VOCAB_VERSION`，不得复制第八词。

### 4.2 source observation 与 locator

```python
class SourceIntervalV1(StrictWire):
    lo: FiniteFloat
    hi: FiniteFloat                 # lo < hi

class PlanSourceWindowV1(StrictWire):
    channel: Literal["plan"]
    source_locator: SourceLocator   # ^src:[0-9a-f]{64}$
    source_input_id: StableId
    source_output_sha256: Hex64
    observation_id: StableId
    floor_ref: PositiveInt
    world_x_interval: SourceIntervalV1
    world_y_interval: SourceIntervalV1
    positive_claims: tuple[ClaimName, ...]

class ElevationSourceWindowV1(StrictWire):
    channel: Literal["elevation"]
    source_locator: SourceLocator
    source_input_id: StableId
    source_output_sha256: Hex64
    observation_id: StableId
    local_along_interval: SourceIntervalV1
    local_z_interval: SourceIntervalV1 | None
    positive_claims: tuple[ClaimName, ...]

SourceWindowV1 = Annotated[
    PlanSourceWindowV1 | ElevationSourceWindowV1,
    Field(discriminator="channel"),
]

class WindowClaimSourceLinkV1(StrictWire):
    window_id: StableId
    claim: ClaimName
    source_locator: SourceLocator

class ReadingArtifactIdentityV1(StrictWire):
    input_id: StableId
    expected_output_id: StableId
    output_sha256: Hex64

class ElevationDirectionFactV1(StrictWire):
    input_id: StableId
    resolved_building_direction: CardinalFamily
    resolution_source: Literal[
        "manifest_building_axis", "resolved_direction_sidecar"
    ]
    mirrored: StrictBool
    local_x_positive: Literal[
        "image_left_to_right", "image_right_to_left"
    ]
    orientation_output_hash: Hex64 | None
    adapter_version: StableId | None
    view_manifest_sha256: Hex64
```

locator preimage 精确是：

```json
{"input_id":"<manifest input_id>","observation_id":"<reading id>","output_sha256":"<raw reading bytes sha256>","schema":"window_source_locator_v1"}
```

首个不可由被测 helper 生成的冻结向量：完整 preimage 字面量

```json
{"input_id":"plan-1","observation_id":"W-01","output_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","schema":"window_source_locator_v1"}
```

其 UTF-8（无尾换行）SHA-256 必须硬编码为
`d4e4d28c48522a4852047b9c7f257b9370692c9c186a85c884c2774f2fa9d2e2`，locator 必须是
`src:d4e4d28c48522a4852047b9c7f257b9370692c9c186a85c884c2774f2fa9d2e2`。测试不得调用 production canonical/hash helper生成 expected。

source catalog builder 从 `ViewManifest.required_entries()` 与真实 reading bytes 生成，channel 取 manifest `view_type`；不读 correction window 自报 channel。plan/elevation observation 必须由正式 reading parser 验证为 window；虚线 hidden candidate 若按 E2'.9 留在 `uncaptured[]`，不得进入 catalog。

### 4.3 resolver input 顶层

```python
class WindowResolverInputsV1(StrictWire):
    schema_version: Literal["1"]
    claims_vocab_version: Literal["1"]
    producer_draw_sha256: Hex64
    view_manifest: ViewManifest
    reading_artifacts: tuple[ReadingArtifactIdentityV1, ...]
    elevation_direction_facts: tuple[ElevationDirectionFactV1, ...]
    source_windows: tuple[SourceWindowV1, ...]
    claim_links: tuple[WindowClaimSourceLinkV1, ...]
    content_sha256: Hex64

class WindowSourceOfferV1(StrictWire):
    schema_version: Literal["1"]
    view_manifest_sha256: Hex64
    source_windows: tuple[SourceWindowV1, ...]
    allowed_claims_by_locator: tuple[
        tuple[SourceLocator, tuple[ClaimName, ...]], ...
    ]
    content_sha256: Hex64
```

`ElevationDirectionFactV1`恰是可跨ring冻结的八项方向事实；严禁加入`source_footprint_fingerprint/world_axis/sign/along_origin/frame_transform_sha256`。它覆盖manifest全部elevation required views，方向来源、mirror、orientation hash按B-M/E4现合同核验；`content_sha256`是删除自身字段后的canonical hash。

真正调用Va时仍须认准13字段Va型，production helper的返回型必须这样import：

```python
from src.agent.correction.facade_applicability import (
    ElevationViewBindingV1 as VaElevationViewBindingV1,
)
```

严禁从 `src.agent.judge.gt_manifest` import 同名 15 字段型。

13字段型只存在于某一轮current-ring内存中，不进入`WindowResolverInputsV1` content hash，不跨dry/final复用，也不由LLM/调用方持久化自报。

### 4.4 source link 验证

prompt前先调用`build_window_source_offer(...)`；它不含producer hash/claim links，不是resolver信任marker。LLM draw返回后，`build_verified_window_resolver_inputs()`从同一raw artifacts重新建catalog，不信prompt offer回传值，并固定执行：

1. 逐 raw bytes 重算 reading artifact hash；manifest input/output 一一对应；
2. 重算每个 source locator；重复 locator报`duplicate_source_locator`，重复`(input,observation)`报`duplicate_source_observation`，dangling link报`source_identity_invalid`；
3. `claim_links` 必须逐项来自 `WindowV3.provenance[claim].source_ids`，不能由 caller 另传一份不同映射；
4. 每个 final-candidate v3 window 恰有一个非空 existence provenance；`assumed` existence 拒绝；
5. link claim必须在source的`positive_claims`中，否则`source_claim_undeclared`；也必须在manifest `potentially_observable_claims`中，否则`manifest_claim_not_observable`；plan链接sill/head/appearance或elevation链接host报`claim_permission_invalid`；三门各自判断、各自稳定code；
6. 同一 source locator 的 existence 不得链接多个 window；重复归属为 identity conflict；
7. B-M `floor_ref`语义登记为`manifest_floor_order_v1 = 1-based ascending floor.z`；B-M先验plan required floor_ref去重后必须无gap为`1..max_ref`，B5再要求`max_ref == len(geom.floors)`，缺号/跳号/超界均报`manifest_floor_ref_non_contiguous`。B5按z升序唯一rank映射floor_id；source rank与window.floor_id不符报`floor_ref_window_mismatch`。禁止按floor name/OCR模糊匹配；
8. elevation direction fact的resolved family必须与window facade一致；source local_z可唯一归层却与window.floor_id不符报`elevation_floor_mismatch`，无法唯一归层报同code并带candidate floors；
9. 每个elevation required entry恰有一个direction fact；`manifest_building_axis`要求manifest direction/building family一致且orientation字段均None，`resolved_direction_sidecar`要求受信orientation hash+adapter version均非空；manifest hash、来源或mirror事实不符报`direction_fact_invalid`；
10. plan+elevation source都有时，plan决定resolver分支；source列表排序不影响分支；
11. 产生只含raw immutable bytes的`VerifiedWindowResolverInputs` marker。finalize、writer不接受裸`WindowResolverInputsV1`。

marker 与唯一 builder 签名冻结为：

```python
@dataclass(frozen=True)
class VerifiedWindowResolverInputs:
    inputs: WindowResolverInputsV1
    raw_inputs_bytes: bytes
    producer_draw_canonical_bytes: bytes
    raw_view_manifest_bytes: bytes
    raw_reading_artifacts: tuple[tuple[str, bytes], ...]  # keyed by input_id

def build_window_source_offer(
    *,
    raw_view_manifest_bytes: bytes,
    raw_reading_artifacts: Mapping[str, bytes],
) -> WindowSourceOfferV1: ...

def build_verified_window_resolver_inputs(
    *,
    producer_draw: CorrectedGeometryV3,
    raw_view_manifest_bytes: bytes,
    raw_reading_artifacts: Mapping[str, bytes],
    elevation_direction_facts: tuple[ElevationDirectionFactV1, ...],
) -> VerifiedWindowResolverInputs: ...
```

`producer_draw_sha256` 明确定义为 producer draw 经 strict parse 后、尚未 core/host commit 的 canonical model JSON hash，不是 caller 任意序列化文本 hash。builder fresh parse manifest/readings、构造 source catalog、从 producer provenance派生 links，再生成 `raw_inputs_bytes`；dataclass不能由 public constructor直接构造，模块只导出 builder 与 verifier。writer可借 `producer_draw_canonical_bytes`复验 runtime 输入；accepted loader则以 manifest绑定的 resolver-input artifact、原 reading artifacts及 final output关系复验，不假装从 final output反推原 producer bytes。

source locator 由 orchestration 在 correction prompt 中列出；LLM 不需要、也不允许自己拼 `input_id/observation_id`。v3 draw 仍须把 `facade_segments=[]`、全部 `facade_segment_id=null`、resolver reserved audit 缺席；producer 预填任一项直接拒绝。

入口拒绝统一用窄类型`WindowResolverInputError(code, context)`；code vocabulary至少冻结：`producer_segment_ref_prefilled / producer_resolver_audit_prefilled / duplicate_source_locator / duplicate_source_observation / manifest_floor_ref_non_contiguous / floor_ref_window_mismatch / elevation_floor_mismatch / claim_permission_invalid / source_claim_undeclared / manifest_claim_not_observable / direction_fact_invalid / source_identity_invalid`。parse发现window ref与reserved audit分别报前两个code，不能合成无上下文`ValueError`。

§E2' claim权限在B5只允许下表，不按窗口整体验证后“一证全证”：

| source channel | 可立positive claim | 不可立positive claim | visibility对实体的效果 |
|---|---|---|---|
| plan | `existence, host, along, width` | `sill, head, appearance` | bypass；hidden不阻实体/host |
| elevation | `existence, along, width, sill, head, appearance` | `host` | 必须有visible正宽交；partial只影响逐claim applicability |
| 两者都无 | 无 | 全部 | 实体禁止产生 |

`appearance`虽可由elevation提供产品证据，当前B4b因reference value unavailable仍按其合同NA；B5不得借此改judge denominator。对plan来源窗，Vg visibility只影响elevation-channel的z/外观/宽度等逐claim能否计分，永不反向撤销plan existence或host。

### 4.5 production current-ring binding helper

唯一owner是`src/agent/correction/window_sources.py`；production禁import judge。签名冻结：

```python
CURRENT_RING_BINDING_HELPER_VERSION = "window_direction_frame_v1"

DirectionBindingErrorCode = Literal[
    "direction_binding_ring_invalid",
    "direction_binding_ring_incompatible",
]

class WindowDirectionBindingError(ValueError):
    code: DirectionBindingErrorCode
    context: dict[str, object]

    def __init__(self, code: DirectionBindingErrorCode, context: dict[str, object]):
        self.code = code
        self.context = dict(context)
        super().__init__(f"{code}: {self.context}")

def materialize_current_ring_va_elevation_bindings(
    *,
    geom: CorrectedGeometryV3,
    manifest: ViewManifest,
    direction_facts: tuple[ElevationDirectionFactV1, ...],
    visibility_tolerances: VisibilityTolerances,
) -> tuple[VaElevationViewBindingV1, ...]: ...
```

`WindowDirectionBindingError`是helper唯一业务异常，不能复用`FacadeApplicabilityInvariantError`，不能被转换成普通`ValueError`或broad-except吞掉。helper每次调用必须fresh执行：

1. `validate_materialized_facade_segments(geom, ...)`并从current `floor.footprint`重算fingerprint；segment所带fingerprint与current ring任一不符即抛`WindowDirectionBindingError("direction_binding_ring_invalid", {floor_id, segment_id, declared_fingerprint, recomputed_fingerprint})`；
2. C2要求同一elevation view覆盖的各层footprint fingerprint与对应family extent逐值相同；否则抛`WindowDirectionBindingError("direction_binding_ring_incompatible", {input_id, floor_ids, fingerprints, family_extents})`，不任选一层；
3. `world_axis = {North:x, South:x, East:y, West:y}[family]`；`flip = mirrored XOR (local_x_positive == image_right_to_left)`；base sign按Va冻结约定`North:-1, South:+1, East:+1, West:-1`，flip时取反；这些是方向事实的确定性adapter，不是二次方向识别；
4. 对current segments该family取`extent=(min(world_lo), max(world_hi))`，`along_origin = extent.lo if sign==+1 else extent.hi`；
5. 以Va `_frame_hash`同一九字段preimage（schema/input/direction/current fingerprint/axis/sign/current origin/mirror/local-positive）canonical hash，构造13字段Va binding；
6. helper不缓存，不接受caller传fingerprint/origin/frame hash override；final路径的Va公开derive会实际执行Va binding validation，dry路径只消费helper结果做local→world投影，不伪造accepted-correction ledger identity。

dry/pre-transform、B2b post-simulation、final三处均调用此同一helper，且每次参数geom就是当轮带Vg segments的一次性或final geom。测试允许import judge作parity oracle；production模块零judge import。同一ring上，production结果与由同方向事实+同ring构造的judge `materialize_va_elevation_bindings`之13字段model dump及frame hash必须逐字节一致。

三处调用均只窄捕获`WindowDirectionBindingError`并调用§5.2 `map_direction_binding_error`；两code统一落`reason_code=direction_binding_invalid`、保留原`upstream_error_code`、`fallback_action=invariant_no_geometry_commit`。它们是ring/Vg身份硬错，不转A3、不回legacy、不改为`uncorroborated`。

helper先按manifest required input集合做exact totality/去重，再按`input_id`排序输出；direction facts、source windows、claim links也分别按`input_id`、`(channel,input_id,observation_id)`、`(window_id,CLAIM_ORDER index,locator)` canonical排序后才hash，caller顺序不得影响任何digest。

---

## 5. Resolver 输出 wire、conflict 与负证据形状

### 5.1 host resolution record

```python
class Point2V1(StrictWire):
    x: FiniteFloat
    y: FiniteFloat

class Point3V1(StrictWire):
    x: FiniteFloat
    y: FiniteFloat
    z: FiniteFloat

class ParamIntervalV1(StrictWire):
    lo: FiniteFloat
    hi: FiniteFloat                 # 0 <= lo < hi <= 1

class NegativeEvidenceDecisionV1(StrictWire):
    source_input_id: StableId
    channel: Literal["plan", "elevation"]
    claim: Literal["existence"]
    positive_evidence_declared: StrictBool
    negative_evidence_capable: StrictBool
    completeness_assertion_id: StableId | None
    coverage_frame: Literal["plan_floor_region", "elevation_local_along"] | None
    coverage_region: Literal["full_floor", "full_facade"] | None
    negative_intervals: tuple[SourceIntervalV1, ...]
    covers_complete_target: StrictBool
    outcome: Literal[
        "positive", "trusted_negative_conflict", "uncorroborated"
    ]

class WindowHostResolutionV1(StrictWire):
    host_schema_version: Literal["1"]
    helper_version: Literal["window_host_resolver_v1"]
    window_id: StableId
    floor_id: StableId
    room_id: StableId
    branch: Literal["plan", "elevation"]
    facade_family: CardinalFamily
    facade_segment_id: StableId
    segment_p1: Point2V1
    segment_p2: Point2V1
    segment_outward_normal: tuple[Literal[-1,0,1], Literal[-1,0,1]]
    room_boundary_interval: SourceIntervalV1
    clamped_span: SourceIntervalV1
    segment_parameter_interval: ParamIntervalV1
    clamped_plan_endpoints_p1_to_p2: tuple[Point2V1, Point2V1]
    z_interval: SourceIntervalV1
    clamped_vertices: tuple[Point3V1, Point3V1, Point3V1, Point3V1]
    source_locators: tuple[SourceLocator, ...]
    visible_overlap_intervals: tuple[SourceIntervalV1, ...]
    resolution_sha256: Hex64

    @model_validator(mode="after")
    def _normal_and_visibility_shape(self):
        if self.segment_outward_normal not in {
            (0, 1), (0, -1), (1, 0), (-1, 0)
        }:
            raise ValueError("C2 host normal must be one cardinal unit vector")
        if self.branch == "plan" and self.visible_overlap_intervals:
            raise ValueError("plan branch visible_overlap_intervals must be empty")
        if self.branch == "elevation" and not self.visible_overlap_intervals:
            raise ValueError("elevation branch requires visible overlap")
        for left, right in zip(
            self.visible_overlap_intervals, self.visible_overlap_intervals[1:]
        ):
            if right.lo <= left.hi:
                raise ValueError("visible overlap intervals must be canonical union")
        return self
```

`resolution_sha256` preimage是删除自身字段后的完整**几何host** record canonical JSON。它不含Va negative/corroboration，避免“Va ledger要output hash、output audit又要Va digest”的自引用环。plan branch的`visible_overlap_intervals`固定空tuple（不适用）；elevation branch固定为target与selected segment visible union的canonical正宽交，非空、升序、不重叠。record排序键固定`(floor_id, facade_segment_id, clamped_span.lo, clamped_span.hi, window_id)`。

```python
class WindowHostClaimsV1(StrictWire):
    schema_version: Literal["1"]
    helper_version: Literal["window_host_resolver_v1"]
    resolver_inputs_sha256: Hex64
    view_manifest_sha256: Hex64
    facade_segments_sha256: Hex64
    resolutions: tuple[WindowHostResolutionV1, ...]
    aggregate_sha256: Hex64

class WindowEvidenceDecisionV1(StrictWire):
    window_id: StableId
    source_locators: tuple[SourceLocator, ...]
    negative_evidence: tuple[NegativeEvidenceDecisionV1, ...]
    corroboration_status: Literal["supported", "uncorroborated"]
    evidence_sha256: Hex64

class WindowEvidenceLedgerV1(StrictWire):
    schema_version: Literal["1"]
    helper_version: Literal["window_evidence_ledger_v1"]
    direction_helper_version: Literal["window_direction_frame_v1"]
    output_sha256: Hex64
    feature_states_sha256: Hex64
    resolver_inputs_sha256: Hex64
    view_manifest_sha256: Hex64
    facade_segments_sha256: Hex64
    direction_bindings_sha256: Hex64
    va_ledger_content_sha256: Hex64
    decisions: tuple[WindowEvidenceDecisionV1, ...]
    aggregate_sha256: Hex64
    content_sha256: Hex64

class WindowHostsArtifactV1(StrictWire):
    artifact_version: Literal["window_hosts_v1"]
    output_sha256: Hex64
    claims: WindowHostClaimsV1
    evidence: WindowEvidenceLedgerV1
    content_sha256: Hex64
```

`evidence_sha256`是删除自身后的完整decision canonical hash。host `aggregate_sha256`是ordered `resolution_sha256` JSON array的hash；evidence aggregate同理hash ordered `evidence_sha256`。两个集合的window id必须彼此及final geom三方精确相等。accepted artifact中任何decision含`trusted_negative_conflict`均strict reject（该结果只能转§5.2 rejected conflict）。空窗二者都用完整canonical JSON字面量`[]`（UTF-8、无尾换行），SHA-256固定为`4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。各`content_sha256`删除自身后重算。

### 5.2 conflict wire

```python
HostConflictReason = Literal[
    "source_identity_invalid",
    "source_channel_missing",
    "source_geometry_mismatch",
    "claim_evidence_invalid",
    "direction_binding_invalid",
    "va_identity_invalid",
    "cross_segment_boundary",
    "segment_endpoint_overrun",
    "invalid_window_span",
    "zero_segment_candidates",
    "multiple_segment_candidates",
    "elevation_segment_not_visible",
    "zero_room_interval_candidates",
    "multiple_room_interval_candidates",
    "cross_room_boundary",
    "room_mismatch",
    "floor_mismatch",
    "facade_mismatch",
    "trusted_negative_conflict",
    "parent_wall_zero_candidates",
    "parent_wall_multiple_candidates",
    "invalid_host_line",
    "resolver_output_tampered",
]

class WindowHostConflictV1(StrictWire):
    kind: Literal["window_host_conflict"]
    conflict_schema_version: Literal["1"]
    window_id: StableId
    floor_id: StableId | None
    branch: Literal["plan", "elevation", "unresolved"]
    reason_code: HostConflictReason
    raw_span: SourceIntervalV1 | None
    source_input_ids: tuple[StableId, ...]
    candidate_segment_ids: tuple[StableId, ...]
    candidate_room_ids: tuple[StableId, ...]
    crossed_segment_ids: tuple[StableId, ...]
    trusted_negative: tuple[NegativeEvidenceDecisionV1, ...]
    upstream_error_code: Literal[
        "va_claim_ledger_invalid",
        "va_projection_frame_invalid",
        "va_direction_unresolved",
        "va_identity_mismatch",
        "va_visibility_ledger_invalid",
        "direction_binding_ring_invalid",
        "direction_binding_ring_incompatible",
    ] | None
    failed_gate_id: Literal["correction.window_host_resolution"]
    fallback_action: Literal[
        "needs_input_no_geometry_commit", "invariant_no_geometry_commit"
    ]
    blocking: Literal[True]

    @model_validator(mode="after")
    def _upstream_code_shape(self):
        va_reasons = {
            "claim_evidence_invalid", "direction_binding_invalid",
            "va_identity_invalid",
        }
        if self.upstream_error_code is not None and self.reason_code not in va_reasons:
            raise ValueError("Va upstream code requires a Va-mapped reason")
        if self.reason_code == "va_identity_invalid" and self.fallback_action != "invariant_no_geometry_commit":
            raise ValueError("Va identity failure is invariant, not interactive")
        if self.upstream_error_code in {
            "direction_binding_ring_invalid",
            "direction_binding_ring_incompatible",
        } and (
            self.reason_code != "direction_binding_invalid"
            or self.fallback_action != "invariant_no_geometry_commit"
        ):
            raise ValueError("ring binding failure must be a direction invariant")
        return self
```

conflict按window id/reason/candidate ids canonical排序，进入rejected attempt的`audit.json`与`checks.json` evidence；不进入accepted output。`WindowHostResolutionError`必须携带typed rows。只有`fallback_action=needs_input_no_geometry_commit`可按completion mode转A3/interactive；`invariant_no_geometry_commit`始终硬错。non-interactive不得自动回legacy/nearest wall。

`src/agent/correction/window_host.py`新增唯一mapper：

```python
def map_direction_binding_error(
    exc: WindowDirectionBindingError,
    *,
    geom: CorrectedGeometryV3,
    verified_inputs: VerifiedWindowResolverInputs,
    phase: Literal["dry_pre_transform", "dry_post_transform", "final"],
) -> tuple[WindowHostConflictV1, ...]: ...
```

mapper按error context定位受影响input/floor并为相关window产生canonical rows；无法缩小范围时覆盖本批全部window，零窗时resolver跳过binding materialization。每row固定`reason_code=direction_binding_invalid`、`upstream_error_code=exc.code`、`fallback_action=invariant_no_geometry_commit`、`blocking=True`；`checks.json` companion evidence保留`phase`与完整strict context。mapper不得调用Va error mapper，也不得把两code改写成`direction_fact_invalid`（事实没错，错的是current ring/segments身份）。

### 5.3 accepted audit row

每个成功 window 无论坐标是否变化，都在 `geom.corrections` 写一条 strict `WindowHostResolutionAuditV1`，因为 segment/room attribution 是 topology identity 变更：

```python
class WindowHostResolutionAuditV1(StrictWire):
    kind: Literal["window_host_resolution"]
    rule_id: Literal["deterministic_core.window_host_resolver_v1"]
    stage: Literal["core"]
    claim_type: Literal["topology_identity"]
    window_id: StableId
    floor_id: StableId
    original_room_id: StableId | None
    resolved_room_id: StableId
    original_facade_segment_id: None
    resolved_facade_segment_id: StableId
    original_span: SourceIntervalV1
    resolved_span: SourceIntervalV1
    source_ids: tuple[SourceLocator, ...]
    branch: Literal["plan", "elevation"]
    resolution_sha256: Hex64
    tolerance_names: tuple[
        Literal["WINDOW_SEGMENT_ENDPOINT_CLAMP_TOL"],
        Literal["WINDOW_HOST_SPAN_EPSILON"],
        Literal["WINDOW_HOST_PLANE_EPSILON"],
    ]
    changes_topology: Literal[True]
```

draw parser 拒绝 producer 自报此 `kind`；final validator 要求它与 `window_hosts` records 一一对应并重算一致。其他 correction audit 保持既有宽容。

`original_span` 的冻结口径是 **resolver 入口的 post-snap / post-floor-z-clamp span**，不是 producer raw bytes 中尚未经过确定性 snap 的数值。例如 producer `-0.006` 经既有 snap 成为 `-0.01`，audit 的 `original_span.lo` 必须为 `-0.01`。producer raw 仍由 `VerifiedWindowResolverInputs.producer_draw_canonical_bytes` 认证；Phase D writer 校验本字段时必须从该 bytes fresh parse 并 replay 同一确定性 snap，再与 audit 比较，禁止拿 raw producer span 直接比较，也禁止把 final clamped span 冒充 original。

---

## 6. Source-aware resolver 主链（六步精确化）

### 6.1 公共纯函数

新模块 `src/agent/correction/window_host.py`：

```python
def resolve_window_hosts(
    geom: CorrectedGeometryV3,
    *,
    verified_inputs: VerifiedWindowResolverInputs,
    tolerances: CoreTolerances,
    commit: Literal[False],
) -> WindowHostClaimsV1: ...

def apply_window_host_resolutions(
    geom: CorrectedGeometryV3,
    *,
    claims: WindowHostClaimsV1,
    verified_inputs: VerifiedWindowResolverInputs,
    tolerances: CoreTolerances,
) -> CorrectedGeometryV3: ...

def recompute_window_host_claims(
    geom: CorrectedGeometryV3,
    *,
    verified_inputs: VerifiedWindowResolverInputs,
    tolerances: CoreTolerances,
) -> WindowHostClaimsV1: ...

def derive_window_evidence_ledger(
    geom: CorrectedGeometryV3,
    *,
    host_claims: WindowHostClaimsV1,
    verified_inputs: VerifiedWindowResolverInputs,
    candidate_identity: PreparedCandidateIdentity,
    tolerances: CoreTolerances,
) -> WindowEvidenceLedgerV1: ...

def map_va_applicability_error(
    exc: FacadeApplicabilityInvariantError,
    *,
    host_claims: WindowHostClaimsV1,
    verified_inputs: VerifiedWindowResolverInputs,
) -> tuple[WindowHostConflictV1, ...]: ...
```

`resolve_window_hosts`是无mutation的唯一candidate算法；它只从参数`geom.facade_segments`消费当轮Vg结果，并在入口调用§4.5 helper从verified direction facts按该geom current ring瞬时派生bindings。dry B2b传的是§3.2的一次性`dry_geom`，final传持久化segments后的final geom；不设`segments_override`，从签名上杜绝“原geom无segments却私传第二真值”。`apply...`先在fresh copy逐项比对claims，再写room/ref/span/provenance/audit；它不接受caller手组record。

writer/loader的`recompute...`从final output fresh copy，仅清空window `facade_segment_id`后调用同一核（final room与clamped span保留并必须重新唯一解析到同结果），再重建final-only host record；record故意不持久化不可由accepted final output复得的pre-snap临时span。writer另用runtime marker里的`producer_draw_canonical_bytes`验证audit `original_room/original_span/ref-null`；accepted loader信任manifest绑定的writer产物并重验final关系/hash，不伪称能从final bytes反推producer临时态。evidence由`derive_window_evidence_ledger`在真实candidate identity就绪后生成。

### 6.2 Step 1：floor / room / segment identity

对每个 window 按 window id 排序：

1. floor_id 恰指向一层，display floor 与 name 相等；z interval 有序、落在 floor z 范围；
2. source link 决定 branch：plan existence 非空则 plan，否则 elevation existence 非空；两者都空为 `source_channel_missing`；
3. 所有 source 的 floor/family 与 window 一致；不一致不删除 offending source 后继续，而是 conflict；
4. 每个existence source interval经正式frame映到world-along后，必须与producer/snapped W有大于span epsilon的正宽交；plan按`window.facade`的along轴从真实x/y interval取值，elevation只用§4.5按**本轮ring**派生的Va binding投影。零交为`source_geometry_mismatch`，不得只因locator真实就把别的窗挂过来；
5. plan 分支要求 producer `room` 非空并在同层唯一存在；elevation 分支允许 room 空，后续补；
6. final resolve 前 `facade_segments` 必须是 Vg 完整 materialization，fingerprint 与 floor ring 匹配；
7. final input window ref 必须仍为 null。若非 null 说明绕过 writer，拒绝。

### 6.3 Step 2：segment 候选与真实区间 clamp

先令 snapped window interval 为 `W=[w0,w1]`，要求 `w0<w1`。先取同 floor/family 全段；plan 分支再应用 evidence-driven plane filter：对每个 linked plan existence source，按 facade family 取与 world-along 垂直的真实 source interval（North/South 取 `world_y_interval`，East/West 取 `world_x_interval`），segment plane 必须落在该 interval 的 `window_host_plane_epsilon_m` 闭包内。此过滤器只用 source footprint 几何辨认不同物理 plane，不读 window center、cell bbox、最近距离或 id；同一 plane 的多个段必须全部保留，因此不能掩盖 seam/cross-segment。elevation 分支不使用该 plane filter。对过滤后的每段 `S=[s0,s1]` 按以下规则候选：

1. 若 W 与两个或以上保留 segment 各有大于 `window_host_span_epsilon_m` 的正宽交，先报 `cross_segment_boundary`；尤其共面相邻段不得被 plane filter 或后续 clamp 隐去跨段事实；
2. endpoint overrun：`max(0,s0-w0)` 与 `max(0,w1-s1)` 各自必须 `<= window_segment_endpoint_clamp_tol_m`；超过即 `segment_endpoint_overrun`，不得混报 zero candidate；
3. clamp 只作 `C=[max(w0,s0), min(w1,s1)]`，且 `length(C) >= min_edge_length_m`；宽/高、z 或 full-face 安全门不满足统一报 `invalid_window_span`；不吸向 interior endpoint，不 clamp room seam；
4. plan 分支不看 `visible_intervals`；
5. elevation 分支要求 `C` 与该 segment `visible_intervals` union 有大于 span epsilon 的正宽交。允许部分 visible，以支持 E2'.5 existence fragment；完全 hidden 不候选；
6. 候选恰一。零解按是否完全 hidden 分 `elevation_segment_not_visible`/`zero_segment_candidates`，多解为 `multiple_segment_candidates`。

不能用 cell bbox 先缩 W 再找段，也不能用 W center 所在段。

### 6.4 Step 3：room-boundary interval 与 parent wall 前置一致性

从每个 `Cell` 的实际 canonical polygon/bbox ring 枚举有向边，计算 cell 外向 normal。对选中 segment：

1. cell edge 与 segment 必须在 `window_host_plane_epsilon_m` 内共线；
2. cell edge outward normal 与 segment normal 在 C2 逐值相等；
3. edge 与 segment 正宽交形成 room interval；同 room、同 plane、首尾只差 span epsilon 的 degree-2 连续碎边可 canonical merge；不同 room 或中间有正 gap 永不合并；
4. **完整** C 必须被一个 room interval 包含（端点只容 span epsilon）；部分 overlap 不算；
5. plan：先在全部相邻room intervals检验C；若C对两个room各有正宽交且无一完整包含，报`cross_room_boundary`。否则只接受declared room的完整interval；其他room完整包含也不能替producer偷换，普通无完整interval报zero、多个报multiple；
6. elevation：在所有room interval中完整包含C的room必须恰一，然后写`window.room`。若C对两个相邻room interval各有正宽交但无一完整包含，同样报`cross_room_boundary`；普通零解报`zero_room_interval_candidates`；重叠坏拓扑多解报`multiple_room_interval_candidates`；
7. producer elevation window 若已给 room，必须等于唯一结果，否则 `room_mismatch`。

此步骤体现“一段可跨多 room、段 id≠room”。它同时冻结 built parent 的逻辑前置关系：resolved room、segment plane/outward normal、完整 C span 三者缺一不可。built Surface 要在造面完成后才能取 name，故 correction 核此处写可复算 proof，geometry realization 再按完全相同三条件选唯一 Surface；不得用“尚未造面”为由退回 facade family/center 猜墙。实际 parent 候选与零/多拒绝见 §8。

### 6.5 Step 4：p1→p2 参数与 clamped plan endpoints

选中 segment 后构造有向线段：

```python
@dataclass(frozen=True)
class SegmentLine2D:
    p1: tuple[float, float]
    p2: tuple[float, float]

    def point_at(self, t: float) -> tuple[float, float]: ...
    def parameter_of(self, point: tuple[float, float]) -> float: ...
```

C2 adapter 用 segment family 的 world-along scalar 把 `C.lo/C.hi` 映到线上的两个 point，再用 dot product 求各自 t；record 存 `t_lo<t_hi` 顺序和相应 `point_at(t_lo), point_at(t_hi)`，即 **p1→p2 顺序**。若 p1→p2 沿负 x/负 y，world `lo` 点可能是第二点；不得 `sorted(points)` 破坏方向。

zero-length line、非有限分量、非单位/非垂直 outward normal、逆序或越界 t 均报 `invalid_host_line`。low-level 顶点函数冻结：

```python
def window_verts_on_line(
    *,
    host_line: SegmentLine2D,
    parameter_interval: tuple[float, float],
    z_interval: tuple[float, float],
    outward_normal_xy: tuple[float, float],
) -> list[tuple[float, float, float]]: ...
```

实现只做：

```python
q0x, q0y = host_line.point_at(t0)
q1x, q1y = host_line.point_at(t1)
v = [(q0x,q0y,z0), (q1x,q1y,z0),
     (q1x,q1y,z1), (q0x,q0y,z1)]
nx, ny = outward_normal_xy
return _orient(v, np.array([nx, ny, 0.0], dtype=float))
```

`window_verts_on_line`是B5替换现`_window_verts`的公开低层接口；旧cardinal函数施工时只重命名`_legacy_cardinal_window_verts`并仅供legacy attach。新函数体禁止facade/x/y分支；`_orient`明确是现`modelling.py` 3D normal适配，normal先升为`(nx,ny,0)`。resolver将结果逐点写入`clamped_vertices`；writer、loader、build均从line+t+z+normal fresh重算四点，不把record四点喂回helper自证。C2 `FacadeSegment` schema仍拒斜线；diagonal `SegmentLine2D` helper正例只证明接口可扩，不扩大C2 capability。

### 6.6 Step 5：Va negative 与 validator / audit / specs / judge 四同步

resolver commit候选已算出segment/room且步骤9真实candidate identities就绪后，构造Va `OpeningClaimsV1`：

- target 是 clamped span；
- plan source 用真实 plan interval；
- elevation source用真实local interval与§4.5从**final current ring**刚派生的Va 13字段binding；
- visibility ledger从final candidate `facade_segments`独立构造，segment hash重算；`source_output_sha256`与`feature_states_sha256`只能取`PreparedCandidateIdentity`真实值；
- 恰七 claim，source claim 权限遵循 E2' 矩阵。

finalize与writer在本节取得final-ring binding时，helper调用均位于`try/except WindowDirectionBindingError`窄边界；异常只交`map_direction_binding_error(..., phase="final")`并typed invariant reject，绝不进入下面的`FacadeApplicabilityInvariantError`捕获器。

intersection只有两个互斥的业务权威触发点，不设通用pre-Va重复门：

- `existence`：唯一权威是Step 1#4。resolver用current-ring binding映射并检查正宽交；零交只报`source_geometry_mismatch`。Va adapter只能在同一transaction的resolver/recompute成功返回后调用，该成功返回本身建立`existence_overlap_verified` runtime invariant，不新增wire/hash字段；
- `host/along/width/sill/head/appearance`：B5不预判intersection，直接交Va的正式映射/`_intersect`语义；Va报`va_claim_ledger_invalid`后，mapper唯一转`claim_evidence_invalid`。partial正宽交合法，coverage/applicability仍由Va裁定，不自行要求full width。

若Va在该runtime invariant成立后仍报existence intersection类`va_claim_ledger_invalid`，这不是第二个业务诊断，而是Step1与Va映射漂移：固定转`va_identity_invalid + invariant_no_geometry_commit`。禁止转`source_geometry_mismatch`或`claim_evidence_invalid`。由此同一输入不会因执行顺序得到多个业务code。

随后调用Va public `derive_opening_claim_applicability()`。只允许窄捕获`FacadeApplicabilityInvariantError`，禁止捕`Exception`：

- `va_claim_ledger_invalid`且context claim为非existence → 对其`opening_id`生成`claim_evidence_invalid` conflict；context claim为existence → 生成`va_identity_invalid` invariant conflict，表示Step1/Va漂移；
- `va_projection_frame_invalid`或`va_direction_unresolved` → 对引用该input的window生成`direction_binding_invalid`；
- `va_identity_mismatch`或`va_visibility_ledger_invalid` → 对本批windows生成blocking `va_identity_invalid`；
- typed conflict的`upstream_error_code`保留原Va code/context，attempt rejected；未知code不降级，作为INVARIANT raise并阻止写attempt accepted。

这是“窄类型捕获后必转typed reject”，不违反§1 broad-except禁令。B5不复制`_negative`、coverage frame或visible intersection算法。existence负证据见§7；属性applicability只进`WindowEvidenceLedgerV1`供B4b/B5b，不能改变实体host、geom或audit。Va ledger bindings中的output/feature hash必须与最终artifact逐字节一致，占位或错位在finalize、writer、loader三处均拒。

同一 accepted resolution 随后必须一次同步到四个消费者，任何一个缺席都不能 promotion：validator fresh重算关系并硬门；audit写 strict typed row；built/specs携带source+segment+proof并重算顶点；judge先验正式B5 artifact identity、再独立重算评分关系而不信proof自证。四处的具体签名和拒绝语义见 §8、§10、§12.3；不得拆成“先接受output、以后补sidecar/spec”的软接线。

### 6.7 Step 6：legacy / final totality

- v3：所有geometry records成功后一次commit并冻结output bytes；Va evidence成功且negative无conflict后才可形成accepted候选；final window/evidence/record三集合不得丢项；
- v1/v2：严格 legacy path；没有 ref 是正常合同；
- v3 任一失败：无部分 commit，无“其余窗继续 accepted”；返回 typed conflict，attempt rejected；
- final validator 重算 floor/segment/room/span/t/hash totality；
- build 阶段再验真实 parent Surface，见 §8。

---

## 7. Conflict 纪律与 trusted negative 精确判据

### 7.1 几何 conflict 优先级

同一 window 多问题时按以下稳定优先级报主 reason，并把其他 facts 留 evidence：

1. source/floor/facade/direction identity；
2. claim evidence/permission；
3. cross-segment positive-width crossing；
4. segment zero/multiple/hidden；
5. cross-room或room interval zero/multiple；
6. room mismatch；
7. trusted negative conflict；
8. parent wall zero/multiple；
9. digest/artifact identity tamper。

稳定优先级只决定诊断，不作为候选 tiebreak。candidate ids 全量排序写出。

### 7.2 不按中心点猜

以下实现均禁止：

- `segment = min(segments, key=distance(window_center,...))`；
- room polygon `contains(window_center)`；
- parent Surface `min(center_distance)`；
- global assignment 最后按 id 破平局；
- 先把 W 截到某 cell bbox，再宣称唯一。

测试用两个段/两个 room 对称包围 center，确保实现必须拒绝；不能只做 source scan。

### 7.3 trusted negative conflict

对某 final window 的 existence，只有同时满足以下全部条件，另一通道的“无”才进入 `trusted_negative_conflict`：

1. 当前 window 在通道 A 有至少一个已核验 positive existence source；
2. 通道 B 与 A 不同，且是该 floor/family 的相关 required view；
3. manifest 的 B entry `negative_evidence_capable_claims` 包含 `existence`；这就是“图种承诺完整表达 openings”的机读位；
4. coverage/assertion 成对存在、引用闭合，plan 为 `plan_floor_region/full_floor`，elevation 为 `elevation_local_along/full_facade`；
5. Va 对 B source 的 `positive_evidence_declared=False`；
6. Va `negative_evidence_intervals` 的 canonical union 覆盖整个 clamped target，残差 `<= window_host_span_epsilon_m`；
7. elevation hidden/partial-visible residual 不可被 coverage 宣言越过：Va negative interval 已与 Vg visible 相交，故 hidden 部分自然不满足完整覆盖；
8. completeness 来源来自 trusted manifest，不接受 product/LLM 自报“我没看见”。

全部成立→conflict，B5 attempt不accepted。任一不成立→`uncorroborated`；`WindowEvidenceLedgerV1`保留decisions但几何正常挂载。不得把uncorroborated记miss、删窗或降到assumed entity。

若同一 source 同一区间同时有 positive declaration 与 trusted negative absence，属于 manifest/source input 自相矛盾，直接 input invariant reject，不转成 window conflict。

---

## 8. Built parent wall 与 geometry realization

### 8.1 proof-aware build API

```python
@dataclass(frozen=True)
class VerifiedWindowHostProof:
    raw_resolver_inputs_bytes: bytes
    raw_window_hosts_bytes: bytes
    raw_output_bytes: bytes
    # 仅由 accepted/integrated verifier 构造

def build_geometry(
    geom: CorrectedGeometry,
    *,
    capability_profile: str = "rectangular",
    window_host_proof: VerifiedWindowHostProof | None = None,
) -> BuildingGeometry: ...
```

- v1/v2：`window_host_proof` 必须为 None，旧行为；
- v3：proof 必填，即使零窗也要有空 totality artifact；裸 geom 不允许 build；
- build 入口重算 output hash、resolver input/hash、host record/hash，并从 raw output fresh parse，拒绝 caller-mutated geom。

### 8.2 parent Surface 候选

`attach_windows_v3()` 在全部 wall surfaces 完成后，对每条 resolution：

1. room id 经 `zv_by_cell` 唯一映到 zone；
2. candidate `Surface.zone==zone`、`stype=="Wall"`、`obc=="Outdoors"`；
3. 从 Surface 唯一 XY base line 构造线段；退化/多于两 XY 点拒绝；
4. 该 line 与 resolution segment 在 `window_host_plane_epsilon_m` 内共线；
5. `_newell(surface.verts)` 的 XY unit normal 与 segment outward normal 同向；C2 以分量残差 `<= plane epsilon` 验，不用旧 `dot>0.9` 宽门；
6. parent line 完整包含 resolution 两个 clamped plan endpoints（span epsilon）；
7. candidate 恰一。零/多不是 note+skip，而是 blocking invariant；
8. 用§6.5 `window_verts_on_line`生成vertices，确认每点在parent plane、z在parent、窗面积正且严格小于parent area；
9. built window 写 source window id、facade segment id、resolution hash；命名仍按 parent 内几何排序。

fragmented exterior wall 若没有任何单一 Surface 完整包含窗 span，说明窗跨 built surface seam，必须拒绝；不能把一个 window 自动切成两个。

### 8.3 internal dataclass 与 serializer gate

```python
@dataclass
class Window:
    name: str
    parent: str
    verts: list[tuple[float,float,float]]
    source_window_id: str | None = None
    facade_segment_id: str | None = None
    host_resolution_sha256: str | None = None

@dataclass
class BuildingGeometry:
    ...
    geometry_contract: Literal["legacy", "c2_b5_v1"] = "legacy"
```

`building_geometry_dict`、`serialize_geometry`、`geometry_specs_markdown` 显式接 `geometry_contract`：

- legacy projection 排除三个 None/default 字段，输出 key/order/text 与当前完全相同；
- `c2_b5_v1` 的 building JSON window 行加入 source/segment/resolution digest；fenestration spec 同行显示 `source_window`、`segment`、`host_proof`，parent/verts 仍是下游唯一几何指令；
- 不得仅因 dataclass 加 defaults 就宣称 legacy byte equality；必须由 version-gated serializer 测试证明后才承诺。

---

## 9. 信任根、attempt artifact 与 E4 接缝

### 9.1 writer 独立重算

`FinalizeResult` 累加字段：

```python
@dataclass(frozen=True)
class PreparedCandidateIdentity:
    output_bytes: bytes
    output_sha256: str
    feature_states_bytes: bytes
    feature_states_sha256: str

@dataclass(frozen=True)
class FinalizeResult:
    geom: CorrectedGeometry
    audit_payload: dict
    feature_state_claims: FeatureStateClaimsV1
    window_host_claims: WindowHostClaimsV1 | None
    window_evidence_ledger: WindowEvidenceLedgerV1 | None
    verified_window_resolver_inputs: VerifiedWindowResolverInputs | None
    prepared_candidate_identity: PreparedCandidateIdentity | None
```

v1/v2全部B5字段必须None；v3四个B5字段必须非空。`PreparedCandidateIdentity`只由finalize在§3.2步骤9用正式serializer构造，不是持久wire。StageRunner在写accepted候选前：

1. 对runtime geom再次versioned serialize；bytes必须与prepared `output_bytes`逐字节相同，SHA必须相同，不等即`candidate_output_identity_drift`；
2. 从 verified raw resolver inputs fresh parse/重算 content hash；
3. 从 output bytes fresh parse geom，独立 rerun Vg materialization validator；
4. fresh derive feature claims并构造`FeatureStatesArtifactV1`，用正式serializer取bytes；必须与prepared feature bytes/SHA逐字节相等；
5. writer在方法内部执行`from src.agent.correction import window_host as window_host_module`，调用`window_host_module.recompute_window_host_claims`，不得复用`finalize`模块绑定；与result host claims逐字段比较；
6. writer从`window_sources`模块fresh调用§4.5 helper，随后用步骤1/4真实hash重建Va visibility ledger并调用`window_host_module.derive_window_evidence_ledger`；与result evidence逐字段比较；
7. 任一record的segment/room/span/t/endpoints/3D vertices/digest，或任一evidence/output/feature/direction binding/VA digest不同即拒绝；
8. 构造output-bound `WindowHostsArtifactV1`；
9. 写output/checks/audit/feature_states/window_resolver_inputs/window_hosts到临时attempt dir，全部回读strict validate，再整体rename；
10. 只有checks不block才移动manifest accepted pointer和stage-root convenience copy。

严禁用fixture/调用方传入`resolution_sha256`、direction binding或Va ledger identity作为重算输入，也严禁`try/except`后只丢sidecar仍接受output。finalize与writer可以共享`window_host.py`内纯几何私有核，但writer不能经`finalize.resolve_window_hosts`符号调用；测试注入点按§13.6冻结。

### 9.2 artifact contract

`manifest.py` 新增：

```text
ArtifactKey += window_resolver_inputs | window_hosts
ArtifactContract += correction_b5_v1 | correction_b5_orientation_v1

correction_b5_v1 required/allowed =
  output, checks, audit, feature_states,
  window_resolver_inputs, window_hosts

correction_b5_orientation_v1 required/allowed =
  output, checks, audit, feature_states,
  window_resolver_inputs, window_hosts
```

v1/v2 新 attempt 继续 `correction_b2_v1`；历史 contracts 可读。新生产 v3 B5 base 只能 `correction_b5_v1`，orientation-enriched 只能 `correction_b5_orientation_v1`。host resolver 不改变 B2/Vg feature-state 四轴/`helper_versions`；artifact contract 与 window-host sidecar单独表达 B5 capability，避免破坏 Va 现有 accepted-correction visibility identity。

StageRecord `output_hash == artifact_hashes["output"]` 继续成立；六键任一缺失/多余/不匹配拒绝。

### 9.3 accepted loader

`load_verified_accepted_correction` 对 B5 contracts：

- 验六个 artifact hash；
- `window_hosts.output_sha256 == output hash`；
- resolver inputs manifest/content/reading hashes重算；
- final geom fresh parse + Vg重验 + current-ring direction bindings + host claims重算；
- feature-state仍按现合同fresh derive并重建artifact bytes/hash；
- 以真实output/feature hash重建Va visibility与evidence ledger；`window_hosts.evidence`逐字段一致；
- 返回扩展后的 immutable raw-byte bundle；不得从 stage-root convenience copy 取 proof。

integrated path `verify_integrated_gate1_correction` 接收并同样验证两份 raw sidecar；v3 缺 proof 不得构造 accepted marker。

### 9.4 E4 orientation enrichment

现 `finalize_orientation_enrichment` 只接受 `correction_b2_v1`，B5 施工须同步：

1. 新生产 v3 base 只接受 verified `correction_b5_v1`；历史 B2→E4 replay 保留旧分支但不冒充 B5-ready；
2. enrichment 只可改 north_axis 与 orientation audit；room/ref/span/host audit逐值保持；
3. 它必须携带verified resolver-input raw bytes；ring-free direction facts及其受信orientation-sidecar hash逐值保持，按orientation-enriched geom的current ring重派生ring-dependent bindings并rerun host claims；不得把base的13字段binding带过来；
4. 因north axis改了output hash，重新预序列化output/feature artifacts、重建Va evidence与`window_hosts.json`绑定新hash，不复制base artifact bytes；
5. writer 标 `correction_b5_orientation_v1`；
6. `AcceptedCorrectionRef`、`OutputCoordinateContract`、assembly loader允许新 orientation contract；relative contract 仍只由 schema v3 + populated north axis + orientation contract触发，不按 theta 数值猜；
7. output-coordinate逻辑不消费 host数值，但必须先验完整六件套，不能让 host sidecar篡改绕过 accepted chain。

---

## 10. validator / audit / specs / judge 四同步

### 10.1 correction validator

新增：

```python
def check_window_host_resolution(
    geom: CorrectedGeometry,
    *,
    proof: WindowHostClaimsV1 | VerifiedWindowHostProof | None,
    evidence: WindowEvidenceLedgerV1 | None,
) -> GeometryFinding: ...
```

- v1/v2：调用旧 `check_windows_on_wall`，check id/层级/evidence 语义不变；
- v3：`correction.window_host_resolution`为INVARIANT，重算floor/room/segment/interval/record totality；proof/evidence任一缺失直接fail，evidence的output/feature/Va identity与window-id totality同时检查；
- `check_windows_on_wall` 不再用于 v3，避免 bbox 假绿；
- v3 conflicts 非空且含 `window_host_conflict` 时 gate 必 block；不得只靠总 conflict count；
- `check_correction`新增kw-only proof/evidence参数，pipeline/flow parity同传。

### 10.2 built kernel validator

新增 `kernel.window_parent_binding` INVARIANT：

- source window ids、built windows、resolution records 三集合一一相等；
- parent surface 存在、Outdoors、zone/plane/normal/span全对；
- built vertices与`window_verts_on_line` fresh recompute逐值相等；
- built window segment/digest 与 proof相等；
- 任一额外/遗漏/重复/篡改 fail。

现 `build_geometry` 的“窗口数相等”总数门保留，不能代替集合/关系门。

### 10.3 audit / report

- `audit.json` 顶层保持 `corrections/conflicts/unsupported`，B5 accepted record在 corrections中；orientation可额外带现有 orientation节；
- rejected host conflicts 进入 attempt audit/check evidence，accepted root不提升；
- stage-root `corrections.json` 仍只由 accepted attempt promote；
- `record_baseline.py`/`report_assembly.py`从manifest-accepted audit与同attempt已验`window_hosts.evidence`读：branch/clamped来自geometry proof，corroboration来自evidence ledger，conflict reason来自rejected attempt；不得从root旧文件或audit猜corroboration；
- audit record的 resolution hash必须在 report前重验，坏 hash不能仅标“unreadable”继续出成功报告。

### 10.4 specs

- `building_geometry.json` v3 window携带 source/segment/proof；
- `geometry_specs.md` v3 fenestration行携带同身份并仍引用唯一 parent/verts；
- `fenestration_specs` 的窗数与 proof record数相等；
- specs consistency checker从 built geometry fresh生成期望，不读 LLM抄写的 digest；
- legacy serializer gate见 §8.3。

### 10.5 judge

B4b 不失去 judge-only 独立性：

1. official GT v3 + correction v3 scoring 要求 accepted record是 `correction_b5_v1` 或 `correction_b5_orientation_v1`，并先通过六件套 verifier；旧/pre-B5 v3为 machine NA `unsupported_product_contract`，不能 temporary binding后当正式 B5产物计分；
2. `normalize_correction_for_score`从 fresh verified output生成 observation，显式 segment ref必须存在且 span/floor/family一致；
3. B5 contract下 `bind_correction_window_segment` 禁 temporary unique span binding；该方法只可留给明确标识的 pre-B5 candidate/test path；
4. host score继续按 B4b §8.4.1独立从 product cell boundary + segment + room重算，不信 `window_hosts` relation/digest为分数真值；proof只作identity/tamper gate；
5. score cache identity已有 accepted StageRecord canonical hash，六件套 hash变化会触发重算；capability key再纳入 artifact contract，避免同 schema 3跨合同命中；
6. product Va ledger消费 B5 final segment ref/provenance；reference denominator仍只来自 reference ledger，B5 proof不能改 denominator；
7. production correction模块不得 import judge。

---

## 11. 新容差：`correction.yaml` + `CoreTolerances` + A0

B5 新增三项，均 required、无 dataclass默认、无 Python裸 fallback：

```yaml
correction:
  window_segment_endpoint_clamp_tol_m: 0.010
  window_host_span_epsilon_m: 1.0e-9
  window_host_plane_epsilon_m: 1.0e-9
```

| config key | A0 名 | 值 | 语义 | 明确不得用于 |
|---|---|---:|---|---|
| `window_segment_endpoint_clamp_tol_m` | `WINDOW_SEGMENT_ENDPOINT_CLAMP_TOL` | 0.010m provisional | 已唯一 segment 后，window snapped endpoint 超真实 segment endpoint 的最大可裁回量 | room seam、segment 选择、source matching、min edge |
| `window_host_span_epsilon_m` | `WINDOW_HOST_SPAN_EPSILON` | 1e-9m provisional | span包含、正宽交、半开端点、coverage残差的 IEEE-754 数值门 | 物理 clamp、缝隙闭合、可见性 epsilon替身 |
| `window_host_plane_epsilon_m` | `WINDOW_HOST_PLANE_EPSILON` | 1e-9m provisional | room edge/segment/built parent共线与顶点在面复算的数值门 | angle tolerance、wall thickness、segment candidate距离 |

`CoreTolerances.validate()` 新关系：

```python
0 < window_host_plane_epsilon_m <= window_host_span_epsilon_m
window_host_span_epsilon_m < window_segment_endpoint_clamp_tol_m
window_segment_endpoint_clamp_tol_m <= min_edge_length_m
```

三者不能复用 `min_edge_length_m`、`facade_visibility_endpoint_epsilon_m`、judge tolerance或旧 `_SPAN_TOL=0.10`；即使数值相同也保持独立 owner。`window_clamp_to_parent` 注释改为“legacy v1/v2 only”；v3 B5 clamp是强制合同，不能用 bool关闭。

A0 §4登记三行；§5 schema/profile registry登记`window_host_resolver_v1`、`window_direction_frame_v1`、两个sidecar schema、两个artifact contract，并登记`manifest_floor_order_v1 = floor_ref 1-based ascending floor.z`。B-M manifest合同/生成器同步声明该语义，`ViewManifest`校验plan required floor_ref去重后为无gap`1..max_ref`；B5要求`max_ref`等于actual floor数并按z顺序交叉验证。A0 §7 `window_anchor_validation`精确化为segment+room+parent+proof totality。

所有直接构造 `CoreTolerances` 的测试 helper 必须显式加三值；缺 key测试必须 fail，不允许 loader `.get(default)`。

---

## 12. 公开接口与文件级施工清单

### 12.1 新增

- `src/agent/correction/window_sources.py`
  - source catalog、locator、raw hash、ring-free direction facts验证、production current-ring Va binding helper；
- `src/agent/correction/window_host.py`
  - strict wire、segment/room candidate、clamp、t参数、Va negative adapter、digest；
- `tests/test_c2_b5_source_routing.py`
- `tests/test_c2_b5_host_resolution.py`
- `tests/test_c2_b5_parent_and_verts.py`
- `tests/test_c2_b5_artifact_trust.py`
- `tests/test_c2_b5_legacy.py`
- synthetic/temp-only fixtures；不改 GT/golden。

### 12.2 修改

- `src/agent/correction/schema.py`
  - 注册 strict audit row校验；WindowV3字段表不新增；
- `parse.py`
  - v3 draw拒 segment ref/resolver audit；final totality接缝；
- `config.py`、`src/configs/correction.yaml`
  - 三 required tolerance；
- `deterministic.py`
  - 显式 legacy/v3 window分支、pre-host core；
- `finalize.py`
  - §3时序、verified input、host claims；
- `envelope_transform.py`
  - B2b旧 resolver替换为B5 dry resolver；不持久化临时 segment；
- `facade_visibility.py`
  - 只复用public Vg；不得加window逻辑；
- `feature_state.py`
  - 四feature语义不变；只补B5 artifact compatibility测试，不塞第五feature；
- `orientation.py`
  - B5 base/host proof重绑；
- `execution/manifest.py`、`stage_runner.py`、`output_coordinates.py`
  - 六件套 contracts、writer/loader/integrated/E4；
- `pipeline.py`、`scripts/tool_scripts/run_stage.py`
  - source catalog prompt、双路径同一 finalize/proof传递；
- `execution/view_manifest.py`及B-M合同文档
  - 登记/校验`manifest_floor_order_v1`连续1-based语义；
- `geometry/modelling.py`、`build.py`、`specs.py`
  - line helper、proof-aware attach/build、versioned serializer；
- `correction/geometry_validator.py`、`validator/checks/correction.py`、`validator/checks/kernel.py`
  - v3 host/parent hard gates；
- `judge/opening_claim_score.py`、对应 scorer service
  - B5 contract dispatch、无official temporary binding、independent score；
- `record_baseline.py`、`report_assembly.py`
  - accepted host audit摘要；
- `skills/intake_pipeline/1_correction/A0_contract.md`
  - §11容差、direction helper与floor-order合同登记项。

### 12.3 唯一准签名

以下为施工后的唯一准签名；未列参数不得由各调用路径私加平行版本：

```python
def finalize_correction_draw(
    geom_or_payload,
    *,
    vector_dir: Path,
    verified_window_inputs: VerifiedWindowResolverInputs | None,
    tol: CoreTolerances | None = None,
    target: CorrectionTarget,
) -> FinalizeResult: ...

def apply_deterministic_core(
    geom: CorrectedGeometry,
    tol: CoreTolerances | None = None,
    *,
    authoritative_envelope: AuthoritativeEnvelope | None = None,
    capability_profile: str = "rectangular",
    verified_window_inputs: VerifiedWindowResolverInputs | None = None,
) -> CorrectedGeometry: ...

def apply_v3_envelope_transaction(
    geom: CorrectedGeometryV3,
    tol: CoreTolerances,
    authoritative_envelope: AuthoritativeEnvelope,
    *,
    verified_window_inputs: VerifiedWindowResolverInputs,
) -> EnvelopeTransactionResult: ...

def build_geometry(
    geom: CorrectedGeometry,
    *,
    capability_profile: str = "rectangular",
    window_host_proof: VerifiedWindowHostProof | None = None,
) -> BuildingGeometry: ...

def check_correction(
    geom: CorrectedGeometry,
    *,
    window_host_proof: WindowHostClaimsV1 | None = None,
    window_evidence: WindowEvidenceLedgerV1 | None = None,
    expected_zone_total: int | None = None,
    raw_geom: CorrectedGeometry | None = None,
    relied_on_testdata: bool = False,
    elevation_widths: dict[str, float] | None = None,
    reading_views: list[Any] | None = None,
    capability_profile: str = "rectangular",
    run_profile: RunProfile = "exploratory",
    evidence_debt: EvidenceDebt | dict | None = None,
) -> CheckReport: ...

def verify_integrated_gate1_correction(
    *,
    raw_output_bytes: bytes,
    correction_report: CheckReport,
    feature_states: FeatureStatesArtifactV1,
    raw_window_resolver_inputs_bytes: bytes | None,
    raw_window_hosts_bytes: bytes | None,
) -> VerifiedAcceptedCorrection: ...

def finalize_orientation_enrichment(
    base: VerifiedAcceptedCorrection,
    resolution: VerifiedOrientationResolution,
    *,
    capability_profile: str = "orthogonal_polygon",
) -> FinalizeResult: ...
```

`StageRunner.record(...)` 外部签名保持现状，靠 `output_obj: FinalizeResult` 携带 verified marker/claims；writer内部按 schema/contract决定四件套或六件套。`load_verified_accepted_correction(*, run_dir: Path, manifest) -> VerifiedAcceptedCorrection` 外部签名也保持现状，但返回型累计 `raw_window_resolver_inputs_bytes`、`raw_window_hosts_bytes` 两个可空字段：v1/v2为None，B5 v3必非空。`resolve_unique_window_host(...)` 从 production删除；不得保留为B2b第二套算法。

兼容纪律：v1/v2调用 `finalize_correction_draw` 时 `verified_window_inputs=None`；v3必须传 verified marker，即使零窗也不例外。pipeline与stepwise不得各包一个默认。`apply_deterministic_core` 的 v3分支只允许 marker；v1/v2若非None反而拒绝。所有新参数均kw-only，避免旧位置调用静默错位。

### 12.4 明确不改

- GT/golden/verified overlay；
- wall/floor/roof face construction；
- Va public wire/helper/version；
- B5b HTML/REPORT assumed呈现；
- v1/v2 schema类字段；
- C2 `FacadeSegment` axis-aligned validator。

---

## 13. 测试矩阵（所有安全拒绝分支必须有锁）

测试fixture的期望record/hash/verts必须是手写字面量或冻结文件；禁止调用被测resolver/`window_verts_on_line`/hash helper生成expected再自比。性质测试可重算数学关系，但至少一组固定向量必须独立硬编码。禁止`x != x`、`assert not (x != x)`等恒真/恒假伪检查。

### 13.1 source-aware 两支

| ID | fixture | 必须断言 |
|---|---|---|
| SRC-P1 | plan-only，目标段 `visible_intervals=[]` | 仍挂 hidden 段、room/ref都有，branch=plan |
| SRC-P2 | plan+elevation，plan段hidden | 仍按plan挂；elevation只记unobserved/属性NA |
| SRC-P3 | plan source rank与window floor不符 | `floor_ref_window_mismatch` BLOCK |
| SRC-P4 | plan source真实locator被篡改/悬空 | `source_identity_invalid` BLOCK |
| SRC-P5 | assumed existence | BLOCK，实体不得由prior立 |
| SRC-E1 | elevation-only，唯一visible段、room为空、span落唯一room interval | 自动补room+segment，branch=elevation |
| SRC-E2 | elevation span仅部分visible | 可挂实体；visible overlap为片段，width/applicability partial |
| SRC-E3 | elevation段完全hidden | `elevation_segment_not_visible` BLOCK |
| SRC-E4 | elevation view resolved family与window不符 | `facade_mismatch` BLOCK |
| SRC-E5 | 同一source locator被两个window existence引用 | identity BLOCK |
| SRC-I1 | v3窗没有任何plan/elevation existence source | `source_channel_missing` BLOCK，不按几何猜channel |
| SRC-I2 | locator真实但引用另一处、与目标span零正宽交的window observation | `source_geometry_mismatch` BLOCK，不能只验hash存在 |
| SRC-Z0 | v3零窗 | 空records/aggregate仍有proof，build可过；不擅自证明observed-zero（留B5b） |

入口/link拒例每行一个独立test，不得参数化成一次调用只断总失败：

| ID | fixture | 稳定断言 |
|---|---|---|
| SRC-C1 | plan source raw `positive_claims`与link都含`sill`（权限门须先于manifest observable门） | `claim_permission_invalid` |
| SRC-C2 | elevation source链接`host` | `claim_permission_invalid` |
| SRC-C3 | producer draw预填window `facade_segment_id` | parse入口`producer_segment_ref_prefilled` |
| SRC-C4 | producer draw预填`kind=window_host_resolution` audit | parse入口`producer_resolver_audit_prefilled` |
| SRC-C5 | 对strict未验`WindowResolverInputsV1`重复插入同一catalog row/locator后调用verifier | `duplicate_source_locator`，不得构造verified marker |
| SRC-C6 | 单个raw reading artifact含两个相同observation id；在locator catalog生成前检查 | `duplicate_source_observation`，证明raw parser层独立去重 |
| SRC-C7 | plan required floor_ref为`{1,3}`/缺2 | `manifest_floor_ref_non_contiguous` |
| SRC-C8 | elevation local_z唯一归floor B但window声明floor A | `elevation_floor_mismatch` |
| SRC-C9 | link claim不在source `positive_claims` | `source_claim_undeclared` |
| SRC-C10 | link claim不在manifest `potentially_observable_claims` | `manifest_claim_not_observable` |

current-ring binding生命周期锁：

| ID | fixture | 必须断言 |
|---|---|---|
| BIND-1 | 改direction fact的family/mirror/orientation hash任一字节 | `direction_fact_invalid`，不能靠重派生洗白 |
| BIND-2 | 同一verified direction facts；pre-B2b ring与移动0.24m后的post ring分别Vg+helper | test-only分别直接过Va `_validate_bindings(manifest, bindings)`；fingerprint/origin/frame hash随ring按预期不同，dry生产路径不伪造ledger identity |
| BIND-3 | 同一ring/同一方向事实；judge score-binding fixture的ring字段与frame hash为独立手写冻结值，不取production helper输出 | production helper与judge`materialize_va_elevation_bindings`的13字段model dump/frame hash逐字节parity；测试可import judge，production source scan零judge import |
| BIND-4 | 把pre-transform 13字段binding强塞给post ring Va | `va_projection_frame_invalid`；final resolver从API上不接受该binding |
| BIND-5 | dry helper收到transient segment fingerprint与其current floor ring重算值不符 | 独立抛`WindowDirectionBindingError.code=direction_binding_ring_invalid`；dry mapper转`direction_binding_invalid`且`fallback_action=invariant_no_geometry_commit`，不得被同次B2b回滚后继续掩盖 |
| BIND-6 | 多层fixture中每层segment fingerprint各自匹配其current ring，但同一view覆盖层的fingerprints及对应family extents彼此不一致 | Step 1通过、Step 2独立抛`WindowDirectionBindingError.code=direction_binding_ring_incompatible`，不任选一层；post与final捕获边界分别转typed invariant reject |

### 13.2 segment / room / clamp conflict

| ID | fixture | 必须断言 |
|---|---|---|
| GEO-1 | L形同family多段，window完整落深段 | 唯一深段，非bbox外侧段 |
| GEO-2 | cell bbox包含window但真实room boundary不含 | 拒绝，锁“弃cell bbox” |
| GEO-3 | window对相邻两段各正宽交 | `cross_segment_boundary`，不按center |
| GEO-4 | segment零候选 | zero BLOCK |
| GEO-5 | 重叠坏segment导致多候选 | multiple BLOCK，不按id破局 |
| GEO-6 | endpoint超段5mm | clamp到真实端点，audit delta/hash固定 |
| GEO-7 | endpoint超段11mm（默认10mm） | `segment_endpoint_overrun` BLOCK，不大幅裁回 |
| GEO-8 | 段跨两room，span完整落room B | elevation补B，segment id与room id分别断言 |
| GEO-9P | plan span跨declared room seam | `cross_room_boundary` BLOCK，不降成zero、不按center |
| GEO-9E | elevation span跨room seam | `cross_room_boundary` BLOCK，不按center |
| GEO-10 | 两room坏重叠都完整包含 | multiple room BLOCK |
| GEO-11 | plan declared room与唯一interval不同 | room_mismatch BLOCK |
| GEO-12 | window宽/高低于min edge或覆盖完整parent face | 物理安全拒绝有锁 |

### 13.3 p1→p2、负向轴与 C4 接缝

| ID | fixture | 手写期望 |
|---|---|---|
| LINE-1 | p1=(0,0), p2=(4,0), span[1,3] | t=(.25,.75)，endpoints=(1,0),(3,0) |
| LINE-2 | **负x** p1=(4,0), p2=(0,0), world span[1,3] | t=(.25,.75)，p1→p2 endpoints=(3,0),(1,0)，不得sort回世界升序 |
| LINE-3 | **负y** p1=(0,4), p2=(0,0) | 同理锁负向轴 |
| LINE-4 | low-level diagonal line (0,0)→(3,4), t=(.2,.6), z=(1,2) | 手写四点 (0.6,0.8,z)/(1.8,2.4,z) 并验normal |
| LINE-5 | diagonal `FacadeSegment` 进入C2 schema | 明确拒绝，证明“接口预埋”不等于“C2放行” |
| LINE-6 | zero-length line、逆t、越界t | 三个安全拒例全锁 |
| LINE-7 | 负x/负y record故意把endpoints按世界升序写回、但t仍按p1→p2 | writer与loader均拒 `resolver_output_tampered`，锁负轴错误实现不能假绿 |
| LINE-8 | wire normal取(0,0)或(1,1)；plan record带visible overlap；elevation record overlap为空 | 三项分别在strict wire层拒绝 |

### 13.4 parent wall / specs / validator / judge

| ID | fixture | 必须断言 |
|---|---|---|
| PARENT-1 | room中同family两outdoor墙不同plane | segment plane/normal选唯一正确parent |
| PARENT-2 | 零parent | build与kernel都BLOCK，不只note |
| PARENT-3 | 两parent完整覆盖 | multiple BLOCK |
| PARENT-4 | parent只覆盖半span | BLOCK，不切双窗 |
| PARENT-5 | parent normal反向 | BLOCK |
| SYNC-1 | output→built JSON→geometry specs | source/segment/digest/parent/verts全一致 |
| SYNC-2 | 篡改spec parent或verts | specs consistency BLOCK |
| JUDGE-1 | 正确B5 proof但room几何关系错（构造篡改后重签不可能） | accepted verifier先拒；judge不信proof给complete |
| JUDGE-2 | official B5 product显式ref缺失 | unsupported/rejected，不temporary binding |
| JUDGE-3 | pre-B5 candidate capability | 可机器NA/测试temporary，不混official |

### 13.5 trusted negative

| ID | fixture | 必须断言 |
|---|---|---|
| NEG-1 | plan positive；elevation full_facade + existence negative promise +全target visible且无positive | trusted_negative_conflict BLOCK |
| NEG-2 | 与NEG-1相同plan positive/elevation full coverage，但manifest无`negative_evidence_capable_claims` | uncorroborated，不conflict |
| NEG-3 | 有promise但coverage/assertion缺/悬空 | manifest/input invariant BLOCK |
| NEG-4 | elevation hidden导致negative interval为空 | uncorroborated，plan窗仍挂 |
| NEG-5 | negative只覆盖target一部分 | uncorroborated，不把partial当完整 |
| NEG-6 | 另一通道有positive source | supported，不negative conflict |
| NEG-7 | product自报“低清/没看见/完整” | 不改变Va decision |
| NEG-8 | 同source同interval positive+trusted negative | input invariant BLOCK |
| NEG-9 | elevation positive；plan full_floor + existence negative promise且无positive | trusted_negative_conflict BLOCK，证明“两通道”判据双向而非只写plan→elevation |
| VA-ERR1 | 属性claim source interval与final target零正宽交；B5不设前置属性门，交真实Va后走窄mapper | `claim_evidence_invalid` typed conflict，attempt rejected |
| VA-ERR2 | 窄型Va callable抛`FacadeApplicabilityInvariantError("va_claim_ledger_invalid", {opening_id, claim:"width"})` | mapper保留upstream code并转`claim_evidence_invalid`；不得裸raise丢evidence |
| VA-ERR3 | 窄型Va callable抛未知code | INVARIANT/BLOCK且无accepted artifact；不得吞或转uncorroborated |
| VA-ERR4 | 窄型Va callable抛`va_direction_unresolved` | mapper独立转`direction_binding_invalid`并保留upstream code |
| VA-ERR5 | 窄型Va callable抛`va_identity_mismatch` | mapper独立转`va_identity_invalid`，且严格断`fallback_action=invariant_no_geometry_commit` |
| VA-ERR6 | Step1已成功后，窄型Va callable对同opening抛`va_claim_ledger_invalid`且`claim="existence"` | 作为映射漂移转`va_identity_invalid + invariant_no_geometry_commit`，绝不产生第二个`source_geometry_mismatch`/`claim_evidence_invalid`业务code |
| VA-ID1 | 正常candidate | visibility ledger output/feature hashes与最终两artifact逐字节一致 |
| VA-ID2 | 两个identity字段任一填占位/旧attempt hash | finalize/writer/loader分别拒`va_identity_invalid` |

### 13.6 anti-tamper / fail-closed

逐项单独 mutate，不能一个大测试只改一项：

1. output `facade_segment_id`；
2. output room；
3. output clamped span；
4. segment p1/p2/normal/visible/fingerprint；
5. record plan endpoint；
6. record任一3D clamp vertex；
7. record t interval；
8. record `resolution_sha256`；
9. aggregate hash；
10. `window_hosts.output_sha256`；
11. resolver-input source locator/reading hash/manifest hash/direction fact；
12. StageRecord artifact hash；
13. output改了同时由攻击fixture自行重算普通SHA-256，但room/segment/span关系与source facts不符；独立几何/source复算仍拒，不能把“hash自洽”当“关系可信”；
14. 删除任一六件套文件；
15. E4 enrichment沿用base `window_hosts` bytes导致output hash stale；
16. 手工构造`FinalizeResult`，只改其`window_host_claims`一条span/digest，直接喂writer；writer从fresh output调用真`window_host_module.recompute_window_host_claims`并拒；不patch算法符号；
17. 对偶探针只patch`finalize.resolve_window_hosts`模块绑定使finalize产伪claims；writer内部module-qualified import不受该patch影响并拒，证明两边没有共享可劫持符号；
18. accepted loader遇解析异常；
19. parent resolver内部异常。

每项必须断言稳定gate/error；#18/#19明确不得得到accepted/build geometry。禁止全局patch`window_host.resolve_window_hosts`来声称writer独立，因为它会同时改真复算核。source scan锁定resolver/writer/loader无broad-except fail-open。

固定 digest 测试必须把完整 canonical JSON 字面量与预先冻结 SHA-256 写进 fixture；不能先调用 `_canonical_hash()` 生成 expected。另加一项改变单字节后 hash 必不同。

### 13.7 legacy 与验收三层锁

- v1 矩形 fixture：raw→finalize→build→building JSON→zone/surface/fenestration specs→audit，与改造前 frozen snapshot 语义逐项相等；
- v2 polygon fixture：raw→finalize→build→building JSON→zone/surface/fenestration specs→audit，与改造前v2 frozen snapshot语义逐项相等；
- v1与v2各有一个cell边界会被structural snap移动、window恰需按移动后边界clamp的fixture；断言window pass结果与改造前snapshot一致，锁定“入口只决策、原位后执行”；
- v1/v2 window extra中加入合法/非法 `facade_segment_id`、fake host digest，输出行为与无extra相等；
- `window_clamp_to_parent=False` legacy语义不变；
- v1/v2 missing room/no parent current失败/notes语义不偷修；
- integrated/stepwise同输入：final geom、proof、built/spec/audit语义相等；
- version-gated serializer落地后再断 v1/v2 output/build/spec/audit bytes；在此之前测试名和文案只能写 semantic/geometry equality；
- 全仓 protected GT/golden零diff。

### 13.8 B2b / E4 回归

- 有B2b intent + elevation-only room空：transient Vg dry resolver能补room，变形后final resolver仍唯一；
- B2b使visibility/room归属变化：post-simulation gate拒/回滚，不带pre id；
- B2b无intent：只跑final Vg，不多写临时audit；
- B2b入口仍无persistent facade segment/ref；
- B5 base→orientation enrichment：host关系逐值不变，window_hosts重绑新output hash；
- theta 0/90/270 existing E4 geometry/EP语义不变；
- legacy World contract不要求B5 sidecar。

---

## 14. 施工 Phase、gate 与建议顺序

### Phase A：wire / source trust / config

施工：

- 三 tolerance + A0；
- source locator/catalog、strict resolver input、ring-free direction facts、Va 13字段型import固定；
- production current-ring binding helper与B-M floor-order合同；
- resolution/conflict/audit/artifact wire与hash；
- draw contract拒 producer refs/resolver audit。

gate：

- `B5-A1-source-identity`
- `B5-A2-wire-strict`
- `B5-A3-config-a0`
- `B5-A4-va-type-import`
- `B5-A5-hash-vectors`
- `B5-A6-current-ring-binding-parity`
- `B5-A7-draw-link-rejections`

### Phase B：纯 resolver + B2b/finalize 时序

施工：

- room boundary interval；
- source-aware两支、clamp/conflict；
- transient/final Vg + 每轮binding重派生时序；
- B2b dry resolver替换；
- output/feature预序列化真实identity + Va evidence/negative decisions；
- final commit/audit/provenance。

gate：

- `B5-B1-plan-hidden-host`
- `B5-B2-elevation-visible-room`
- `B5-B3-no-center-guess`
- `B5-B4-b2b-host-parity`
- `B5-B5-negative-proof`
- `B5-B6-resolver-totality`
- `B5-B7-va-artifact-identity`

### Phase C：parent / line / validator / specs / judge

施工：

- SegmentLine2D与`window_verts_on_line`；
- proof-aware build/attach；
- correction/kernel validators；
- versioned built/spec serializer；
- B4b official contract dispatch/independent host score。

gate：

- `B5-C1-parent-unique`
- `B5-C2-line-parameterized`
- `B5-C3-negative-axis-locks`
- `B5-C4-validator-audit-specs-judge-sync`
- `B5-C5-production-import-judge-zero`

### Phase D：artifact trust / E4 / legacy 封口

施工：

- manifest/StageRunner六件套；
- accepted/integrated loader；
- E4 rebind；
- report摘要；
- anti-tamper全量；
- v1/v2 semantic/byte gates。

gate：

- `B5-D1-writer-recompute`
- `B5-D2-accepted-chain`
- `B5-D3-e4-rebind`
- `B5-D4-legacy-semantic`
- `B5-D5-versioned-byte`
- `B5-D6-protected-assets-clean`

四 Phase 顺序执行；每 Phase targeted tests + 相关全仓 tests全绿才合。任何安全拒绝测试缺失视为 shipped-untested，不得用现有总绿数代替。

---

## 15. 验收三层、失败处理与 promotion

### 15.1 三层验收

1. **legacy 行为层**：v1/v2 built geometry、specs、audit 的行为/语义等价；这是 B5 merge 的无条件门。
2. **byte 层**：只有 version-gated serializer 明确排除 legacy defaults/new keys，并有 frozen byte fixtures 后，才承诺 v1/v2 artifact byte equality；否则所有简报/判词只写 semantic/geometry equality。
3. **配置层**：三项新容差各自命名进入 `correction.yaml`、`CoreTolerances` loader/validation、A0；禁复用 min-edge/visibility/judge常数，禁裸值。

### 15.2 promotion 条件

- source-aware两支、mixed、hidden、partial visible全绿；
- 同一direction facts在pre/post ring各自重派生binding并过Va，且同ring与judge oracle逐字节parity；
- conflict/negative/legacy/tamper/parent每个拒绝分支有独立测试；
- claim权限、producer预填、catalog重复、floor-ref、elevation-z、dangling claim六类入口拒绝逐项有锁；
- resolver、writer、loader、build四边界全fail closed；
- Va ledger的output/feature identity与最终artifact逐字节一致，零占位hash；
- p1→p2负向轴+diagonal helper+C2 diagonal reject三面全绿；
- integrated/stepwise parity；
- B4b sidecar/cache identity未被B5绕过；
- E4 orientation新contract全链；
- protected assets零diff；
- Fable 对抗审最终 APPROVE。

### 15.3 失败与回滚

- source/geometry/negative conflict：attempt rejected，输出 typed conflict，no geometry commit；
- B2b candidate导致普通几何host conflict：按B2b原子回滚，随后在rolled-back geom重新final resolve；若仍有host conflict则B5 reject。`WindowDirectionBindingError`不属于可回滚候选冲突：dry-pre/dry-post任一ring code立即按§5.2 typed invariant reject，禁止回滚后继续掩盖；
- writer/loader/hash/parent failure：INVARIANT/ERROR，不能回legacy或删窗；
- Phase regression：回滚本Phase接线，不更新golden追行为；
- v3 artifact contract不完整：不可被output-coordinate、build或judge消费；
- v1/v2 legacy regression：B5不得promotion。

---

## 16. Fable 对抗审重点与开放问题

请重点攻击：

1. `WindowDirectionBindingError`两code是否只由current-ring helper窄抛，dry-pre/dry-post/final三处是否都转`direction_binding_invalid + invariant_no_geometry_commit`而无裸崩、吞错或回滚后继续；
2. existence零交是否只由Step 1#4给`source_geometry_mismatch`，属性零交是否只由Va→mapper给`claim_evidence_invalid`，Va在existence runtime invariant之后反报零交是否固定升级为`va_identity_invalid`；
3. `map_va_applicability_error`的direction与identity两支是否由VA-ERR4/5独立锁住，identity fallback是否严格为`invariant_no_geometry_commit`；
4. resolver input是否彻底排除ring-dependent五字段，dry/post/final是否每轮都从当轮ring重派生binding；
5. production helper与judge oracle同ring parity是否为独立冻结fixture、没有自指；
6. output/audit先冻结、Va evidence侧车化是否真正解除hash环，ledger是否只用真实output/feature artifact hash；
7. B2b transient geom copy是否既让resolver看到segments又不回写stale id/binding；
8. writer的module-qualified复算是否不受finalize符号patch影响；
9. legacy分派是否只在入口决策、window pass仍在structure/z-stack之后原位执行；
10. resolver inputs/output/record/evidence/artifact/E4 rebind是否仍有自报信任或fail-open。

**开放问题：无用户拍板项。** 三个新容差的初始数值均标provisional，后续若跨case probe要校准，必须作为独立config+A0变更，不得在B5执行中临场改常数。
