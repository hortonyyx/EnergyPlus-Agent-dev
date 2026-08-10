# F-9 治本设计稿 v2 · 路线②：模型只指认证据，代码换算、验真与落位

> **状态**：设计稿 v2，2026-08-10，待对抗审；通过前不得施工。
> **拍板边界**：沿用用户 2026-08-09 在 `decision_log.md §5.15` 选择的路线②。
> **版本说明**：v1 于 2026-08-09 被交叉审判为 **REWORK**（3 BLOCKER / 5 MAJOR / 1 MINOR）。
> v2 不继承 v1 正文；关键改动是：补上独立证据身份门，拆开 raw / authenticated / hydrated / full
> 合同，禁止提权 advisory frame，改用 current-ring projector，先 shadow 再启用 detector，最后原子
> cutover；同时补齐历史 v3 producer artifact 的版本边界与 per-floor / z-band 扩展接缝。

---

## 0. 结论先行

新路径的权威关系固定为：

1. 模型只为每扇窗声明真实可见的 observation reference，例如 `1f_view/S11`、`North_view/S7`；
   对 `Window.span` 不再输出世界坐标。
2. 代码把被引 **plan window stroke** 作为该窗唯一的 world-along authority。plan 已在世界坐标系，
   代码按 facade 选择 x/y 区间，得到候选 `span`。
3. 代码把被引 **elevation window stroke** 经唯一的 current-ring affine projector 映射到世界 along；
   它只用于独立身份对账、可见性与审计，不能反过来自证自己的派生值。
4. cited plan / elevation 必须在冻结的端点残差带内形成唯一、无歧义的互相最佳配对；否则拒绝。
   代码即使找到更好的、但模型没有引用的 source，也只可据此判“引错了”，不得偷偷替换引用。
5. 对账通过后，代码把 plan authority 的区间写入 full `WindowV3.span`，再进入 snap、envelope、host
   resolution。最终 room、facade segment、clamp 与 source audit 仍全由代码产生。

因此，新正确性门比较的是两个独立上游观测：

```text
cited plan world interval  <----compare---->  cited elevation local interval
        |                                      |
        |                                      +-- current-ring frame + 唯一 affine projector
        +-- 最终 span authority
```

它不是“从 elevation stroke 派生 span，再拿 span 与同一 stroke 比”的恒真式。

本批只改 `Window.span` 的 world-along authority。`z`、cell geometry 等其他 correction 字段仍按现行
合同处理；本稿不把这个窄范围偷换成“整个 correction draw 已经零模型几何”。

---

## 1. 问题、现状与 v1 为什么不能施工

### 1.1 已坐实的事故

真实 F-9 产物中，`W-F1-N-1.span=[1.24,3.64]` 是正确 plan 位置；模型却在
`existence.source_ids` 引了镜像搭档 `North_view/S5`。North 的基础符号为 `-1`，S5 经现行
current-ring 映射后是 `[11.24,13.64]`，所以 `window_host.py::resolve_window_hosts` 报
`source_geometry_mismatch`。

根因不是 `_BASE_SIGN` 错，而是模型用“立面 local 裸数值约等于 plan world 裸数值”挑 source，
没有应用镜像符号。South / East 的符号为正，同一错误策略恰好得到正确答案，长期遮住了缺陷。

### 1.2 当前承重合同

| 事实 | 当前入口 |
|---|---|
| `WindowV3.span` 继承自 `Window`，full schema 中必填 | `correction/schema.py::Window` |
| v3 `existence.source_ids` 必须非空且非 assumed | `window_sources.py::_claim_links` |
| live model reference 是 `<expected_output_id>/<observation_id>` | `window_sources.py::_translate_observation_reference` |
| 内部 authenticated locator 才是 `src:<64hex>` | `window_sources.py::source_locator` |
| host resolver 当前只从 `existence` links 选 plan/elevation | `window_host.py::resolve_window_hosts` |
| 强制 elevation 映射来自 actual correction ring | `materialize_current_ring_va_elevation_bindings` + `ViewProjectionFrame` |
| prompt hint 的 `_advisory_elevation_world_frame` 使用 elevation overall `W` | `window_sources.py`；只允许 advisory |
| finalize 在 envelope/core 后才 materialize `facade_segments` 并正式 resolve host | `finalize.py::finalize_correction_draw` |
| envelope transaction 会在变换前、后各 dry-resolve 一次 | `envelope_transform.py::_dry_resolve_current_ring` |

现行 producer identity 绑定的是已经通过 full `CorrectedGeometryV3` 验证的 draw；而 full model 又要求
`span`。如果只是给 `span` 打 `CORRECTION_DRAW_DERIVED` marker，外部 reading / manifest / ring 尚未
进入 schema validator，无法填值，且会形成“先要 full producer 才能认证 source、先认证 source 才能
生成 full producer”的环。

### 1.3 advisory 绝不能提权

真实 fixture 中 elevation overall 宽为 `15.0`，correction current ring 为 `[0.12,14.88]`。
对 North/S5：

```text
advisory overall-W frame : [11.36, 13.76]
authoritative current ring: [11.24, 13.64]
差                         : 0.12 m
```

提交 `99d9521` 引入 advisory 时已经明确禁止它进入强制路径；差异来自外皮尺寸基准与 current ring
基准，不是浮点噪声。v2 只允许 advisory frame 帮助 prompt 展示，任何 enforcement API 都必须在类型上
拒绝它。

### 1.4 v1 的失效点

v1 不能施工，因为它同时：

- 让被引 stroke 生成 `span` 后再由同一 stroke 验证，消掉了独立性；
- 把 authority 误写成 `along.source_ids`，但现行 mandatory / routing contract 由 `existence` 驱动；
- 误把 external hydration 当成 F-16 同 draw validator 可完成的 derivation；
- 试图提升 advisory 函数；
- 漏掉 `facade.py::_CONVENTION`，且没有冻结 string/bool mirror 归一；
- 给模型发明了不存在的 `src:<input>:<obs>:<sha>` wire；
- 把单 view binding 与“各层 footprint/extent 相同”绑死；
- 锁没有穿过 raw draw → source auth → hydration → core → finalize 的真实入口。

---

## 2. 不变量、范围与明确不做的事

### 2.1 必须保持

1. **LLM / 代码分工**：模型只决定“哪条 observation 支持这扇窗”；world-along 轴选择、符号、origin、
   区间映射、配对判定、span 写入、host 装配全归代码。
2. **独立性**：至少一条 plan world anchor 与一条 elevation local observation 独立对账；单条 source
   不得自证。
3. **拒绝而不代选**：模型引错 evidence 是 `model_draw_error`，归档本次 attempt 后盲重抽；不硬崩，
   也不把代码找到的“更好 source”写回。
4. **证据不足不是模型错**：上游根本没有独立 pair 时，停止为 typed input-evidence block；不得浪费
   correction 重抽预算。
5. **单一几何实现**：只有一个 public source projection dispatcher，只有一个 elevation affine interval
   projector；plan/elevation 可有合法的 discriminated adapter，不可各自复制符号公式。
6. **advisory/authority 隔离**：二者可以共享纯公式与 facade convention，但 frame 类型、datum 来源和
   接受入口不同；enforcement 不接受 advisory frame。
7. **GT 隔离**：production/shared convention 不 import judge、case 或 GT；绝不从 GT 生成 production
   binding。
8. **全局世界坐标**：最终 `span` 仍是全楼唯一 world frame，不引入每层本地世界原点。
9. **复杂体量接缝**：binding 不含“所有楼层一个 fingerprint/extent”断言；floor/z-band、segment、depth、
   visibility 是独立 scope。
10. **无隐式 fallback**：缺 plan、缺 elevation、方向 unknown、datum 未声明、scope 不唯一时均 fail closed；
    不猜最近窗，不借用未引用 source，不取第一层，不拿 overall `W` 当权威。

### 2.2 本批不做

- 不改用户拍板的 North/West 方向约定。
- 不解决 reading 外皮与 correction centerline 的 0.12 m 基准债；本批只把它显式放入独立配对门的
  命名容差和审计。
- 不实现完整退台遮挡、挑空或中庭 kernel；但新接口现在就为 `along × z` scope 留槽，不允许以后
  推翻本批架构。
- 不把 elevation-only window 偷偷放行。仅有一个 elevation source 时没有独立身份观测，当前合同应
  报 evidence insufficient。未来若增加独立拓扑/语义 anchor，必须升 position-evidence contract 版本。
- 不改变 v1/v2 full wire，也不静默重释历史 v3 producer artifact。

---

## 3. 目标流水线与阶段类型

```text
LLM JSON
  │
  ▼
CorrectionDrawV3CitationV2                 raw：无 span/floor/segment/audit
  │ parse_raw_correction_draw
  ▼
ParsedCorrectionDrawV3CitationV2           仍无 span；保存 canonical raw bytes/hash
  │ authenticate_window_sources
  ▼
AuthenticatedCorrectionDrawV3              refs 已翻译为 locator；绑定 manifest/reading/direction
  │ build current-ring frame + reconcile cited plan/elevation
  ▼
WindowPositionEvidenceV1                   独立 identity decision；不改 geometry
  │ hydrate_correction_draw
  ▼
HydratedCorrectionV3                       full WindowV3.span 由 plan authority 写入
  │ deterministic core + envelope pre/post evidence gates
  ▼
Full CorrectedGeometryV3                    final ring + Vg segments + host refs + audit
  │ writer independent replay
  ▼
accepted attempt bundle                     output + raw sources + hydration + hosts
```

四种对象不得都叫 `CorrectedGeometryV3`。函数签名必须用不同类型，禁止用“某些字段暂时 None”的约定
冒充阶段边界。

---

## 4. Wire、版本与兼容合同

### 4.1 两个版本轴必须分开

`schema_version="3"` 表示 full geometry capability，不足以说明 producer draw 是否允许模型写 `span`。
仓库已经存在历史 v3 producer bytes；所以新增独立版本轴：

| 对象 | 版本 | `span` | 解释规则 |
|---|---|---:|---|
| legacy full/draw | schema v1/v2 | model-authored required | 原样保留 |
| 历史 v3 producer artifact | `window_resolver_inputs_v1` | model-authored required | 只由 v1 artifact loader 重放 |
| 新 v3 raw draw | `draw_contract_version="correction_draw_v3_window_citation_v2"` | 字段不存在 | 只由 raw-v2 parser 接受 |
| 新 v3 hydrated/full | schema v3 + hydration artifact v1 | code-authored required | 只由 hydrator构造 |

禁止按“有没有 `span`”猜版本。`WindowResolverInputsArtifactV1` 与新 V2 必须按显式
`artifact_version` dispatch；未知版本 fail closed。

### 4.2 新 model-facing raw window

示意 wire：

```json
{
  "schema_version": "3",
  "draw_contract_version": "correction_draw_v3_window_citation_v2",
  "windows": [
    {
      "id": "W-F1-N-1",
      "floor_id": "floor-1",
      "facade": "North",
      "z": [1.0, 2.6],
      "room": "F1-office-north-west",
      "provenance": {
        "existence": {
          "provenance": "observed",
          "source_ids": ["1f_view/S11", "North_view/S7"]
        },
        "host": {
          "provenance": "derived",
          "source_ids": ["1f_view/S11"]
        },
        "along": {
          "provenance": "derived",
          "source_ids": ["1f_view/S11"]
        }
      }
    }
  ]
}
```

Raw `WindowCitationV2` 明确没有 `span`、derived `floor`、`facade_segment_id`；raw top level 也没有
`facade_segments`、`north_axis` 或 `window_host_resolution` audit。它应是独立 strict Pydantic model，
不是从 full model dump schema 后临时删字段。

`draw_contract_version` 只属于 raw envelope 和 resolver identity；hydrator 构造 full
`CorrectedGeometryV3` 时不得把它复制成额外 geometry 字段。

如果 live model 偷写 `span`，raw-key preflight 在 Pydantic generic error 前发出稳定码
`producer_window_span_populated`，分类 `model_draw_error`。历史 artifact loader 不经过这扇 live 门。

Live draw 只接受 `<expected_output_id>/<observation_id>`。内部 `src:<64hex>` 只允许 authenticated
artifact / legacy fixture loader，live raw 若写 `src:` 必须拒绝；不得继续把内部兼容入口暴露给模型。

### 4.3 `CorrectionTarget` 的职责拆分

`CorrectionTarget` 对 v3 必须分别持有：

- `draw_model = CorrectionDrawV3CitationV2`；
- `full_model = CorrectedGeometryV3`；
- `draw_contract_version`；
- `full_schema_version`；
- legacy artifact loader registry。

`pipeline._build_correction_messages` 直接展示 `draw_model.model_json_schema()`；
`parse_raw_correction_draw` 只返回 raw type；`validate_final_corrected_geometry` 只接受 full type。
`CORRECTION_DRAW_DERIVED` 继续服务 F-16 的 same-draw `floor_id → floor` 兼容路径，但不得拿来声称
external `span` hydration 已完成。

### 4.4 raw projection context：显式切断阶段环

新增 `materialize_raw_projection_context(raw, authenticated_inputs) -> RawProjectionContextV1`。它只读取
raw 中与窗无关、足以形成当前 facade ring 的 footprint / floor / wall 几何，以及已认证 direction
facts；它的输入类型不含 full `WindowV3`，实现不得调用要求 `span` 的 full parser、window snap、host
resolver 或 finalize。context 记录每个 floor/z-band 的 ring hash、view datum 与适用 scope，并绑定
`raw_draw_sha256` 和 resolver hash。

因此 source authentication 可以先绑定原始 bytes，current-ring projector 随后可在 hydration 前运行；
`span` 只有对账 PASS 后才被写入 full geometry。若 raw 中连 window-independent ring 都无法形成，走
typed upstream/capability failure，而不是临时给窗塞 placeholder span 来骗过 schema。

---

## 5. Source authority 与独立证据身份门

### 5.1 当前 profile 的 citation 规则

每扇新 v3 raw window：

| claim | 规则 | 作用 |
|---|---|---|
| `existence` | 非 assumed；恰有一个 plan source，并至少有一个 elevation source | 现行 mandatory identity 总量；不可删除 |
| `along` | 非 assumed；恰有一个 plan source，且必须与 `existence` 中唯一 plan 相同 | 明确唯一 span authority |
| `host` | 非 assumed；恰有同一个 plan source | 保留独立 wall-plane evidence |
| 其他 claim | 按现行 channel permission；不得改变 position authority | sill/head/appearance 等继续各司其职 |

`existence` 中每一个 elevation source 都是 corroborator，必须全部通过对账；多条 corroborator 只允许
来自不同 elevation view，同一 view 最多一条 position corroborator。这样多 view 可以增强证据，又不会
让代码在同一 view 内任挑一条通过而忽略冲突条目。一个 plan authority 或 elevation position source在
同一 draw 中不得被两个 window 复用。

这明确改变了现行 host resolver 的职责：它不再自行从一袋 `existence` sources 选 branch；
`build_window_position_evidence` 先从 existence + along + host 产生唯一、带 hash 的 authority decision，
host resolver 只消费该 decision。`existence` 没有被旁路，`along` 也不再是未接线的装饰字段。

### 5.2 认证与候选域

认证阶段沿用并收紧现行唯一翻译点：

1. 从 accepted reading bytes 和 trusted manifest 重建 source catalog；
2. 把 model-facing ref 翻译为 `src:<64hex>`；
3. 校验 locator、reading output hash、claim permission、manifest observability、floor order；
4. 严格归一 elevation direction / mirror；
5. 按 `(floor scope, facade family)` 建 plan/elevation 候选域；
6. 产出绑定 raw draw hash 的 `VerifiedWindowResolverInputsV2`。

任何 raw reading / manifest / hash 不一致是 `input_integrity_error`；任何模型虚构、错 scope、重复、越权
reference 是 `model_draw_error`。两者不得从异常字符串推断。

### 5.3 “引对了”如何判断

对每个 window，令：

- `P` = cited plan authority 经 plan adapter 得到的 sorted world interval；
- `E_i` = cited elevation corroborator 经 authoritative current-ring frame 得到的 sorted world interval；
- `d(P,E) = max(abs(P.lo-E.lo), abs(P.hi-E.hi))`。

冻结一个独立配置项：

```text
window_evidence_pairing_tol_m = 0.300
```

它是外皮 / centerline 基准的测量容差，初值与已登记的
`facade_frame_cross_check_tol_m` / `envelope_reconcile_tol_m` 同量级，但必须有自己的字段、文档和阈值锁；
不得借用 `window_host_span_epsilon_m`（后者只是 1e-9 数值门）。配置校验要求
`0 < window_evidence_pairing_tol_m <= envelope_reconcile_tol_m`。

通过条件不是“有一点 overlap”，而是同时满足：

1. 每个 cited `E_i` 的 `d(P,E_i) <= window_evidence_pairing_tol_m`；
2. 对每个 `E_i`，在它所属 elevation view 的同 floor/facade elevation 候选与 plan 候选之间，cited
   `(P,E_i)` 是唯一 mutual-nearest pair：`E_i` 是该 view 内离 `P` 最近的 elevation，`P` 也是离
   `E_i` 最近的 plan；不同 elevation view 不互相竞争，因而同一 `P` 可被多 view 独立佐证；
3. 最优与次优距离之差大于纯数值 ambiguity epsilon；
4. 全 draw 的 position source 分配无重复；
5. plan 的 plane interval、floor_ref 与 model 的 floor/facade/host claim 一致；
6. elevation direction、floor/z scope 与 window 一致。

全 catalog 只用于验证 cited pair 是否在上述 view-scoped 候选域中唯一最佳。若代码发现 `P` 与同一
view 的另一个未引 `E*` 更匹配，结果是 `position_evidence_pair_mismatch`；绝不能把 `E_i` 改成
`E*`。

若 catalog 自身存在几何同分、重复投影或缺一 channel，使代码无法独立判 identity，结果是
`position_evidence_insufficient`，不是反复抽模型。

这道门能证明“被引 plan 与 elevation 是同一物理开口”，不能凭空证明模型自造的 `window.id` 文本
等于某个外部命名。若模型把 plan + elevation + room 等全部成对一致地置换到另一行，现有输入没有第三个
独立 identity key 可判它错；几何层看到的是一次行名重命名。为使边界可审，新 decision 必须另存
`canonical_window_key = hash(plan_authority_locator)`，host/evidence audit 以它标识物理开口，model
`window.id` 只作 alias。若下游要求跨 run 稳定的人类 window id，必须另增 trusted identity anchor，不能
宣称本门已经解决。

### 5.4 span 的唯一选择规则

对账通过后：

```text
derived_span = sorted(plan_authority.world_{x|y}_interval)
```

North/South 取 x，East/West 取 y。elevation projection 不参与数值仲裁，不做平均，不覆盖 plan，
也不把 advisory overall `W` 的数值写入 full geometry。随后只允许既有 deterministic window snap、
envelope transaction 和 unique-host endpoint clamp 对该值作带 audit 的确定性变换。

这使 0.12 m 的处理明确：它影响“两个独立 source 是否仍是同一扇窗”的 accept/reject，不影响最终
span authority。F-9 的 `W-F1-N-1` 最终仍从 plan 得 `[1.24,3.64]`。

---

## 6. 唯一 facade convention 与 projector

### 6.1 gt-free convention 单源

新增不含 case/judge/GT import 的 shared module（建议
`src/agent/correction/facade_convention.py`），唯一持有：

| family | world axis | base sign | outward normal | legacy base plane side |
|---|---|---:|---|---|
| South | x | +1 | (0,-1) | y_min |
| North | x | -1 | (0,+1) | y_max |
| East | y | +1 | (+1,0) | x_max |
| West | y | -1 | (-1,0) | x_min |

唯一 sign 规则：

```text
effective_flip = mirrored XOR (local_x_positive == image_right_to_left)
sign = -base_sign if effective_flip else base_sign
```

`facade.py`、`window_sources.py`、`facade_applicability.py` 和 judge score binding validator 都只消费该
gt-free convention；删除各自 `_BASE_SIGN` / `_CONVENTION` / inline XOR。production 不得反向 import
judge。judge 继续保有独立、手写的 expected truth table 和 judge-owned binding bytes，不能用 production
输出生成 oracle。

### 6.2 mirror 的版本化归一

新 live v3 adapter：

- bool `true/false` 直接接受；
- legacy string `"true"/"false"` 可由明确命名的 compatibility adapter 归一并记录 adapter version；
- `"unknown"`、`None`、其他字符串一律 typed fail closed；
- canonical reading-v2 没有 `local_x_positive` 时按其合同固定为 image-left-to-right；显式 legacy
  right-to-left 只经 legacy adapter 接入。

不得继续让 `facade.py::_is_mirrored("true") == True`、而
`window_sources._resolve_facade_flip_fields("true") == False`。

### 6.3 frame 类型与唯一 projection API

区分两种 frame：

- `AuthoritativeViewProjectionFrameV2`：datum 来自已认证 direction fact + 当前 geometry projection
  context；仅它能进入 evidence gate / hydrator / host / Va。
- `AdvisoryViewProjectionFrameV1`：datum 来自 reading overall width；仅 prompt formatter 接受。

二者可调用同一个纯函数：

```text
project_affine_interval(frame, local_interval)
  a = frame.along_origin + frame.sign * local.lo
  b = frame.along_origin + frame.sign * local.hi
  return [min(a,b), max(a,b)]
```

公开入口只有 `project_window_source_along(source, context)`：

- plan adapter 返回已经在 world frame 的 interval，并附带 plane evidence；
- elevation adapter 唯一调用 `project_affine_interval`；
- 返回统一 `ProjectedAlongEvidenceV1`，保留 channel、locator、frame hash、scope hash；
- 穷尽分派未知 channel，不能 fallback。

这是“一处公开入口、一份 elevation 公式”，不是假装 plan/elevation 没有类型差异。

---

## 7. Frame / binding 如何通过铁律 #6

### 7.1 view datum 与 applicability scope 分离

替代当前单 fingerprint 的 `ElevationViewBindingV1`，新 binding 至少拆成：

```text
ElevationViewProjectionBindingV2
  input_id
  resolved_building_direction
  world_axis / sign / mirrored / local_x_positive
  datum_mode
  along_origin
  datum_geometry_sha256
  scopes[]

ElevationProjectionScopeV1
  scope_id
  floor_id
  z_band_id + world_z_interval
  source_footprint_fingerprint
  candidate_facade_segment_ids[]
  visible_regions_along_z[]
  scope_sha256
```

`datum_geometry_sha256` 哈希 view datum 所依赖的全部 per-floor projection facts；它不是“任选第一层
fingerprint”。每个 scope 自带 floor/z-band fingerprint、segments、depth/visibility 适用域。

### 7.2 当前 datum mode

当前 cardinal full-elevation adapter 明确声明
`datum_mode="view_global_projected_envelope"`：同一张 elevation 的 local x=0 对应整栋投影域的一个
稳定全局 edge；代码从所有适用 floor/z-band 的投影联合求全局 lo/hi，再按 sign 选 origin。当前各层
footprint 相同时它与现行结果一致，但 binding 本身不比较“所有 fingerprint/extent 必须相同”。

若未来输入的 local x 是每层各自归零，不能复用此 adapter；manifest / orientation sidecar 必须显式给
`datum_mode="floor_z_band_reset"`，origin 随 scope 存储并升 binding 版本。没有声明时 typed
`projection_datum_unresolved`，绝不猜。

### 7.3 复杂体量逐项

- **退台**：各层 scope 可有不同 fingerprint、extent、candidate segments；view-global origin 不随层漂。
  可见性由 `along × z` regions 限定，不再是一条全楼共享 1D interval。
- **L / U 形**：同 family 可有多个不同 depth segment。affine coordinate 仍可投影，但 host identity
  必须结合 plan plane、segment id、depth 与 visibility，不能只看 along。
- **挑空 / 双层高**：一个 floor 不再等于一个连续 z applicability；用 z-band scopes 表达 void 与跨层窗。
- **中庭 / 竖井**：内外 segment 可同 family、同 along；必须由 manifest view coverage 与 segment scope
  区分。普通 exterior elevation 没有该 coverage 时，证据对该 inner segment 不适用。

当前 full schema 仍有“v3 per-floor footprints identical”的能力限制时，本批至少把它转为明确、typed
的 capability rejection；新 binding/hydrator 不得再新增或依赖该相等式。未来 schema 放开时，position
contract 无需推翻。

---

## 8. Hydration、identity、envelope 与 host 事务

### 8.1 无环 hash 链

建议对象与 hash 关系：

```text
raw_draw_canonical_bytes
  └─ raw_draw_sha256
       └─ WindowResolverInputsArtifactV2.content_sha256
            └─ per-window WindowPositionDecisionV1.decision_sha256
                 └─ hydrated_geometry_sha256
                      └─ WindowPositionEvidenceArtifactV1.content_sha256
                           └─ final output / WindowHostsArtifactV2
```

`WindowPositionDecisionV1` 的 preimage 包含 raw hash、resolver hash、plan/elevation locators、两个投影
interval、frame/scope hashes、distance、tolerance name/value、decision 与 derived span；不包含自身 hash
或 final output hash。Hydrator把 decision hash 写入 code-owned audit 后再算 `hydrated_geometry_sha256`，
所以没有循环。

`WindowResolverInputsArtifactV2` 内嵌：raw draw canonical bytes、raw manifest bytes、raw reading bytes、
direction/datum sidecar bytes。重放必须从这些 bytes 重新翻译 refs 和构建 facts，不能信 persisted
Python object。`RawProjectionContextV1` 的 content hash 也进入 resolver/decision preimage；重放必须从
raw 的 window-independent geometry 重建它，不能把旧 context 当权威缓存。

### 8.2 Hydrator 的原子后置条件

`hydrate_correction_draw(authenticated, position_evidence)` 一次完成：

1. 核对 raw/resolver/position hashes；
2. 为每窗写 derived `floor`；
3. 为每窗写 plan-authority `span`；
4. 保持 `facade_segment_id=None`、`facade_segments=[]`、`north_axis=None`；
5. 写 code-owned position decision audit；
6. 构造并重新验证 full `CorrectedGeometryV3`；
7. 产出 `HydratedCorrectionV3` marker + `WindowPositionEvidenceArtifactV1`。

少一扇窗的 decision、decision 两边为空、span 未写、raw hash 不同均为 invariant；不得返回半 hydration
对象。`finalize_correction_draw` 对新 draw 只接受这个 marker，不再接受“full geom + 独立 verified inputs”
这对可错配参数。

### 8.3 与 deterministic core / envelope 的顺序

新顺序固定为：

1. raw parse；
2. source authentication；
3. 构造 raw projection context，并运行 current-ring position evidence gate；
4. hydrate full geometry；
5. structural/window snap；
6. envelope pre-transform：以当前 ring 重算 position decision，必须 PASS；
7. candidate envelope transform；
8. envelope post-transform：以 candidate ring 重算 decision，并检查 window/host identity parity；
9. 只有全部 pass 才 commit candidate；若 deterministic transform 自己制造 mismatch，拒绝 candidate、保留
   before geometry，并记 deterministic envelope rejection，不能记到模型账上；
10. final ring materialize Vg segments；
11. final position decision + host resolution；
12. full validation、feature states、evidence ledger、serialization。

raw 引错在第 3 步就以 `model_draw_error` 退出。第 6/8/11 步使用同一个 projector/reconciler，不复制
公式；phase 和 ring hash 进入 trace。`_advisory_elevation_world_frame` 不参与任何一步。

### 8.4 Host resolver 的新输入

`resolve_window_hosts` 新增必填 `position_evidence`，不再从未分角色的 `existence` links 自选 authority。
它使用：

- decision.derived_span 作为 resolver raw span；
- plan authority 的 plane interval 过滤 segment；
- elevation corroborators + scope 做 visibility / applicability；
- plan/elevation 全部 locators 写入 source audit；
- 代码解析出的 room / segment 作为 final identity。

旧的“model span vs every existence source overlap”不再承担 correctness；新 artifact path中应删除这份
重复投影。历史 `window_resolver_inputs_v1` replay 仍走冻结的 legacy resolver 行为。新 host artifact 升
`window_hosts_v2`，显式绑定 `position_evidence_sha256`，不能把 V1 wire 就地加字段。

### 8.5 Attempt bundle 与 writer 重放

新 accepted v3 attempt 至少包含：

- `output.json`：final full geometry；
- `checks.json`；
- `audit.json`；
- `feature_states.json`；
- `window_resolver_inputs.json`：artifact v2，内嵌 raw draw / manifest / readings；
- `window_position_evidence.json`：hydration + phase trace；
- `window_hosts.json`：artifact v2。

`StageRunner` 在创建最终 attempt 目录前，从 persisted bytes 独立执行：raw parse → auth → position gate →
hydrate → core/envelope → host/evidence，并逐对象比 hash。任一 `None == None` 不算验证：每个必要 artifact
须存在、hash 匹配 `^[0-9a-f]{64}$`、window count 与 id totality 相等。

---

## 9. 错误词表与出口

| 条件 | 稳定码示例 | 归因 | 出口 |
|---|---|---|---|
| live raw 偷写 `span` | `producer_window_span_populated` | model format | 只给字段级 inner-retry guidance；不得回显任何几何值；仍失败则该 draw 不进入 semantic gate |
| ref 格式/视图/obs 不存在 | 现行 observation-reference codes | model draw | `correction.window_position_evidence` FAIL；归档本 attempt；外层盲重抽 |
| authority 缺失、额外 plan、跨 claim 不一致、source 复用 | `position_evidence_authority_invalid` | model draw | `correction.window_position_evidence` FAIL；归档本 attempt；外层盲重抽 |
| cited pair 非唯一最佳、明显错配 | `position_evidence_pair_mismatch` | model draw | `correction.window_position_evidence` FAIL；归档本 attempt；外层盲重抽 |
| catalog 根本缺 plan/elevation，或候选固有同分 | `position_evidence_insufficient` | upstream evidence | typed `input_evidence_blocked`；不重抽 correction |
| mirror/datum/scope 未解析 | `projection_datum_unresolved` | upstream evidence | 同上；需要补 reading/manifest/sidecar |
| raw manifest/reading/hash 被换 | `source_identity_invalid` | input integrity | hard fail；不归档成模型错 |
| hydration/hash/decision 被改 | `position_hydration_identity_drift` | invariant | no geometry commit；hard fail |
| envelope candidate 才制造 mismatch | `position_evidence_post_transform_mismatch` | deterministic transform | reject candidate；保留 before；不得重抽模型 |

为避免把 upstream insufficiency 当 stochastic block 烧完预算，执行层需要显式
`INPUT_EVIDENCE_BLOCKED` terminal status（或等价 typed terminal outcome）。不得通过 message substring、
普通 invariant FAIL 或“预算耗尽后自然停”模拟这个状态。

模型引错 source 的外层重抽继续是盲的：attempt 的 `checks.json` 可记录 window id / stable code / source
locator audit，但这些具体错处不得回灌同一 run 的模型 prompt。

成功路径必须在 `checks.json` 写出具体 PASS 行：

- `correction.window_position_evidence`；
- `correction.window_position_hydration_identity`；
- `correction.window_position_envelope_parity`（有 envelope transaction 时）；
- `correction.window_host_resolution`。

不能只在失败时临时造 report；零窗也要写 PASS，证据中明确 `window_count=0` 与非空 artifact hash。

---

## 10. 施工顺序与每步验收性

本稿没有沿用请求书中的旧步骤编号：把“阶段合同壳”与“可运行的证据门”拆开，并按真实依赖重编号。
原因是证据语义可以在 S0 冻结，但 detector 在 convention 与 authoritative projector 尚未接好前没有可验
实现；它应先以 S2 shadow 证明正向可通过，再在 S3 承重。producer cutover 因跨越 schema、identity、
writer，集中为最后的 S4 原子批次。

安全关键路径为：

```text
S0 合同/版本壳
  → S1 gt-free convention 单源
  → S2 current-ring projector + shadow evidence
  → S3 active detector / typed routing（仍保留旧 span）
  → S4 raw→authenticated→hydrated→full 原子 cutover
```

### S0｜阶段合同、错误词表与 artifact 版本壳

内容：新增 raw type、`CorrectionTarget.draw_model/full_model`、raw projection context、resolver artifact v2、
position decision / artifact strict models、显式 loader registry、typed error categories；均先不接 live
production。

**可独立验收：是。** 直接 schema/serialize/reload/hash 测试；历史 v1/v2 与历史 v3 artifact V1 byte
parity 必须保持。未知 artifact version 必须 fail closed。

### S1｜完整合并 facade convention

内容：合并 `facade.py::_CONVENTION`、`window_sources.py::_BASE_SIGN`、
`facade_applicability.py::_BASE_SIGN`、judge `_BASE_SIGN` 与 inline XOR；加 versioned mirror adapter。

**可独立验收：是。** 行为保持；4 facade × mirror × local-direction 外部字面量 truth table、string
边界、live-consumer structure lock 全过后可单独落地。它在推理上不是先设计 S0 的前提，但在施工上必须
先于 S2，避免 shadow 又造一份临时公式。

### S2｜权威 projector 与 shadow position evidence

内容：实现 authoritative frame V2、统一 projection dispatcher、pairing decision；在现有 model-authored
span 路径旁 shadow 运行。输出同时记录 plan authority、current-ring elevation projection、pair distance、
legacy model span 差异；不得覆盖 span、不得 block。

**可独立验收：是。** 真实 `_draw_correction` 与 integrated pipeline 都出现
`correction.window_position_evidence_shadow` 明确 PASS/FAIL fact；shadow FAIL 固定为 cross-check/FLAG，
不得因启用观测而改变接受结果。摘掉 projector 或改用 advisory frame，shadow 锁转红。不可用 `None`
表示“跑过但没结果”。

### S3｜启用独立 detector 与路由

内容：冻结 citation 规则；prompt 要求 existence 的 plan+elevation 与 along/host 的唯一 plan；把 S2
decision 变成 blocking gate；接通 model error archive/blind resample、input evidence terminal、integrity
hard fail。此时模型仍写 span，现行 span/source gate继续存在。

**可独立验收：是，但 prompt + gate + 正向锁 + routing 必须作为一个原子提交。** 只开 gate 不改 prompt
会让所有真实 draw 恒红；只改 prompt 不启 gate 没有安全收益。正确 citation 必须在真实入口 PASS，镜像
搭档必须在新 check-id 处 FAIL。

### S4｜新 producer contract 与 hydration cutover

内容：live v3 prompt 移除 span 与相关心算指令；`run_correction` 返回 raw type；source auth 绑定 raw bytes；
hydrator 写 span；finalize/envelope/host/check/writer/accepted loader 全部改收新 marker/artifact；host artifact
升 V2；历史 artifact 走显式 legacy loader；删除新 live path 上 model-authored span 与重复 projector。

**不能拆成可独立落地的小步。** 以下必须同一原子批次：

- raw schema + raw-key rejection；
- prompt schema/text；
- resolver inputs V2 identity；
- position gate + hydrator；
- `correction_draw_issues` 的 raw/full 分层；
- deterministic/envelope pre/post replay；
- final host 与 audit；
- StageRunner independent replay；
- attempt writer/loader artifact map；
- v1/v2、historical-v3、新-v3 三路兼容锁。

任一半成品都会产生“raw 无 span 却进旧 core”“full span 未绑定 raw”“writer 按旧 producer bytes 重放”
之一，禁止合并。S4 验收后，新 live v3 只有一条 span implementation；legacy V1 loader 是只读历史边界，
不是新 run 的第二实现。

---

## 11. 预计施工落点

这是文件责任图，不是要求机械按文件分 commit：

| 责任 | 主要落点 |
|---|---|
| raw/full schema 与 target | `correction/schema.py`, `correction/parse.py`, `correction/vocab.py` |
| prompt / live raw writer | `pipeline.py` |
| source auth、artifact V2、mirror facts | `correction/window_sources.py` |
| gt-free convention | 新 `correction/facade_convention.py`，并改 `facade.py` / `facade_applicability.py` / judge consumer |
| projector、pairing、hydration artifact | 建议新 `correction/window_position.py`，避免继续膨胀 `window_sources.py` |
| core / envelope phase replay | `correction/deterministic.py`, `correction/envelope_transform.py` |
| host / final evidence | `correction/window_host.py`, `correction/finalize.py` |
| real entry error routing | `scripts/tool_scripts/run_stage.py`, `execution/step_orchestrator.py` |
| independent writer/replay | `execution/stage_runner.py` 与 accepted artifact loaders |
| 配置 | `configs/correction.yaml`, `correction/config.py` |

production/shared module 不得 import `src.agent.judge`、`case_tests`、`tests` 或任何 GT path。judge 可以单向
import gt-free convention，但 frame datum、GT bindings 与 expected truth table 仍由 judge 独立拥有。

---

## 12. 锁规格：入口、正向、反事实与遮蔽

### 12.1 总纪律

每道门必须同时有：

1. 真实入口路径锁；
2. 明确 PASS check-id 的正向锁；
3. 失败夹具先自证前提；
4. neuter / mutation 后必红；
5. 逐 window 属性 oracle；
6. 对“是否被第二道防线先拦”作显式断言；
7. hash/集合相等前断言双方非空与 totality。

真实入口至少覆盖：

- stepwise：`run_one_stage → run_stage._draw_correction`，只 stub LLM 返回值；
- integrated：`run_pipeline_artifacts → finalize_correction_draw → StageRunner.record`；
- 不以直接调用 private projector 代替这两把 wiring lock。

### 12.2 必做锁矩阵

| 锁 | 夹具前提自证 | 正向/负向断言 | neuter 与遮蔽要求 |
|---|---|---|---|
| Raw contract | 新 raw fixture 确认 JSON 无 `span`；另一个只多 `span` | 无 span parse PASS；多 span 报 `producer_window_span_populated` | 改回 full schema 直 parse 后锁红；不能由 generic ValidationError 冒充稳定码 |
| Reference translation | raw refs 确认是 `view/obs` 且 catalog 中存在 | 翻译后 locator 非空且 hash 重算相等；live `src:` FAIL | 旁路唯一 translator 后锁红；legacy loader 单独测试 |
| Raw projection context | raw 无 span；footprint/floor/wall 非空且 ring 手算可成；context hash 非空 | hydration 前 current-ring context PASS，且绑定 raw/resolver hash | 给 context builder 传 full model、补 placeholder span 或改用 finalize/advisory 时，structure/path 锁红 |
| Convention truth | 手写 4 facade × 2 mirror × 2 local-direction expected；lo/hi 非零 | 每格 axis/sign/origin 精确；`"true"/"false"/"unknown"` 边界 | 任一 live consumer 恢复本地 table/XOR，AST structure lock 或真实路径锁红 |
| Advisory 隔离 | F-9 数字先断言 overall-W 与 current-ring 结果确实差 0.12 | authoritative artifact 只能带 current-ring frame kind；advisory 类型传入 enforcement 必须 type/error FAIL | 把 advisory frame 注入 hydrator，锁红；两边都 `None` 禁止 |
| Pair positive | plan/elevation refs 都独立存在；手算 endpoint distance ≤ 0.300 且逐 view 唯一 mutual-nearest；另有两 view 同证一 plan | `correction.window_position_evidence` PASS；decision 逐 view 列出 authority/corroborator/hash | 删除 view scope、mutual-nearest 或 endpoint gate，各自有专用多 view/阈值/歧义夹具转红 |
| F-9 mirror negative | `W-F1-N-1` plan `[1.24,3.64]`；S7 current-ring 投影 `[1.12,3.52]`；S5 `[11.24,13.64]`，先断言前者在带内、后者超带 | 只把 cited elevation S7 换成合法 S5，报 `position_evidence_pair_mismatch`，check-id 精确为 `correction.window_position_evidence` | 测试 double 伪造 detector PASS 后，后续不得由另一份重复 projector 先挡；整条路径应能继续，证明真正承重门就是 detector |
| Hydration positive | raw 无 span、decision 非空、id totality 相等 | full span 精确 `[1.24,3.64]`；`floor` derived；segment 仍空；`correction.window_position_hydration_identity` PASS | 不写 span、改从 elevation/advisory 写、交换两窗 decision，分别转红 |
| Final attributes | 非对称 North + West；South + East 控制；至少两房间 | 逐 window id 断言 `span`, `room`, `facade_segment_id`, host resolution source locators, decision hash；不准只比集合 | 交换两窗 room/segment 时必须红，即使 span 集合不变 |
| Envelope pre/post | 非零 lo/hi 且真有正交 envelope intents；先断言路径调用 pre/post phase | 两 phase 的 `correction.window_position_envelope_parity` 都 PASS，final span/room/segment 手算一致 | 绕过任一 phase 或改用 stale/advisory frame，锁红；确认目标门早于其他 envelope hard gate |
| Wrong-source routing | attempt 1 错 S5、attempt 2 正 S7；两者均为 raw no-span | 真实 stochastic loop 产生两个 attempt；001 的具体 check-id/code；002 PASS；两次 feedback 都是 None | 去掉 category catch 后应恢复抛出/计数错误，锁红 |
| Evidence-insufficient routing | catalog 确认某 floor/facade 缺独立 channel，非模型漏引 | 单次 typed `INPUT_EVIDENCE_BLOCKED`，不启动第二 correction draw，不记 invariant | 若退化为 blind resample，draw count 锁红 |
| Artifact replay | 三个 artifact 都存在、hash 非 None/非空、ids total | writer 从 bytes 重建 raw→hydrate→core→host，逐字节/逐 hash 相等 | 分别 tamper raw ref、decision span、hydrated hash、final audit；每个命中独立稳定 invariant code |
| Legacy scope | 固定 v1、v2、historical v3 artifact V1 bytes | schema/parse/serialize/replay byte parity；新 run 总是 artifact V2 | 以“有无 span”猜版本或让 legacy 走新 hydrator，锁红 |
| Complex-shape seam | L/U 同 family 多 segment；synthetic per-floor extent 不同；z-band 有 void | frame 可投影但 segment identity 仍需 plan plane/scope；binding 序列保留各 fingerprint/extent | 引入 `len(fingerprints)==1`、取 `per_floor[0]`、一维全楼 visibility，structure/contract lock 红 |

当前 correction/full wire 没有 `host_zone_id` 字段；逐属性锁以真实存在的 `room`、
`facade_segment_id` 和 `WindowHostResolutionV2.room_id` 为准，不得为了对齐文案发明一个未接线字段。

### 12.3 F-9 真夹具的具体 oracle

在 `/tmp` 复制 `tests/fixtures/f9_window_host_crash/` 生成测试输入，不改原 fixture：机械去掉新 raw
禁止字段，并把正确/错误 citation 作为两个明确 variant。至少固定：

```text
window               plan authority       correct elevation    mirror twin
W-F1-N-1             1f_view/S11           North_view/S7        North_view/S5
plan world span      [1.24, 3.64]
S7 current-ring      [1.12, 3.52]          endpoint d = 0.12
S5 current-ring      [11.24, 13.64]        endpoint d = 10.00
```

S7/S5 的 expected 必须是冻结 raw 数值手算，不得调用 production projector 生成 expected。其余三扇真实
North 冲突也应逐窗覆盖，防只修第一扇。

### 12.4 防“第二条防线遮蔽”的测试组织

- detector unit/mutation lock 在 hydrator 前直接断言 decision；
- true-entry negative lock 断言实际首个 blocking check-id 是
  `correction.window_position_evidence`，并用 call counter 证明 host 尚未运行；
- cutover 后 host 不再复制 position pairing，所以“伪造 detector PASS”的专用 mutation 可继续到接受，
  反证 detector 确实承重；
- host、envelope、writer 各用已经 PASS 的真实 position decision，避免上游先红；
- 每个 mutation 只改一个 seam，不能用“大面积 monkeypatch 全部下游”制造假分辨力。

---

## 13. Cutover、回滚与完成定义

### 13.1 Cutover

- 新 run 在配置/manifest 中明确选择 draw contract V2；不得自动探测。
- S3 先收集 shadow / active detector 的 pass、mismatch、insufficient 数量；S4 前确认不是
  “真实产物全红”。
- S4 上线后 live prompt 不再出现 `span` required schema，也不再出现“模型自己 mirror / derive world
  span”的指令。
- 旧 v1/v2 与 historical v3 artifact V1 只读 replay；不把旧 producer bytes改写为 V2。

### 13.2 回滚

新 live path 不保留 runtime“失败就回退让模型写 span”开关；那会恢复两份 authority。回滚单位是完整
S4 commit / release，不能在单次 run 中 fallback。已经生成的 V2 artifact 由显式 V2 loader 保留可审性。

### 13.3 完成定义

只有同时满足以下条件才可称路线②落地：

- model-facing v3 schema 中没有 `span`；
- raw、authenticated、hydrated、full 四类对象和 hash 链均存在；
- 正确 plan/elevation pair 在真实入口 PASS；镜像搭档在同一入口走 typed model error + archive + blind
  resample；
- final span 逐窗来自 cited plan authority，不来自 advisory 或 model 数字；
- authoritative elevation formula 只有一份，所有 live consumer 接线；
- pre/post envelope 与 writer replay 都验证同一 position artifact；
- v1/v2、historical v3 artifact V1 均未被重释；
- complex-shape binding 没有 shared-footprint/first-floor 假设；
- production/shared code 继续 GT-blind；
- 所有门有具体 PASS row、负向锁、前提自证和 neuter 证据。

---

## 14. 对抗审该重点打哪里

### 14.1 我最没把握的判断

1. **一致成对置换的可判性边界**：现有材料没有独立于两条 citation 的 stable window identity；因此
   本稿只能把 plan locator hash 定为物理 key，不能判模型 row alias 的一致置换。请审者确认下游是否把
   model-authored `window.id` 当跨 run 业务身份；若是，本稿还缺 trusted identity source。
2. **0.300 m pairing band 是否过宽**：它有既有 envelope/centerline 基准依据，且 unique mutual-nearest
   会再收紧，但本轮没有对全 corpus 测误配率。请重点构造相邻窗间距小于 0.30 m、重复等宽窗和多 view
   的反例。
3. **view-global projected-envelope datum 是否覆盖未来退台图纸习惯**：它适合一张 elevation 共用一个
   image x 原点；若实际 reading 会按楼层重置 local x，必须走显式 floor/z-band mode，不能默认。
4. **新 citation 总量是否太严**：要求一个 plan authority + 至少一个 elevation corroborator 会把
   plan-only/elevation-only 资料正确挡成 evidence insufficient，但真实数据中这种情况占比未核。
5. **路线②的窄范围解释**：本稿只移除 `span`，没有顺手移除 `z` 等其他 model-authored geometry。
   v1、REWORK 裁决和事故本体都只讨论 world-along；仍请审者确认用户的“模型只指认证据”没有意图在
   本批扩大到全部 window 数值。
6. **typed `INPUT_EVIDENCE_BLOCKED` 的执行层接法**：语义必要，但当前 runner 只有 capability-based
   resample / deterministic defect；请重点审最小改动是否会误改其他 stage 的 retry policy。
7. **historical v3 compatibility 面**：当前代码和 fixture 已证明 v3 producer bytes 存在；但本轮没有
   盘点所有已落盘 artifact 版本与 loader call site，S0 必须补全 inventory 后才能施工。

### 14.2 结论来源：推理 vs 实测

标记说明：`[既有实测]` 是必读材料已记录、并由 orchestrator/上一轮审阅复核的运行结果；
`[本轮静态核对]` 是本轮只读源码/fixture/git 检查；`[设计推理]` 尚未由新代码或探针验证。

- `[既有实测]` F-9 四窗镜像错配、North sign=-1、残差 0.12 m、现行
  `source_geometry_mismatch` 能抓住事故。
- `[既有实测]` advisory `[11.36,13.76]` 与 current-ring `[11.24,13.64]` 不同；提交 `99d9521`
  明令 advisory 不进 enforcement。
- `[既有实测]` 基线为 2361 passed / 10 xfailed / 0 failed；本轮没有复跑。
- `[本轮静态核对]` HEAD 为 `cb1ce62`；工作树并非字面全空，唯一额外项是未跟踪的本次请求书。
- `[本轮静态核对]` current full v3 schema 要求 `span`；`existence` 驱动 source selection；producer hash
  绑定 full draw；envelope 有 pre/post dry resolver；StageRunner 会从 producer bytes 重放。
- `[本轮静态核对]` facade convention/sign 至少分散在 `facade.py`、`window_sources.py`、
  `facade_applicability.py`、judge `score_inputs.py`，且 string mirror 归一不一致。
- `[本轮静态核对]` 仓库已有 historical v3 producer artifact V1，故不能只写 v1/v2 compatibility。
- `[设计推理]` 选择 cited plan interval 为最终 authority、elevation 为 corroborator。
- `[设计推理]` endpoint L∞ distance + unique mutual-nearest 是足以避免 B1 恒真、又不代选 source 的门。
- `[设计推理]` raw/resolver/decision/hydrated/final 的 hash 链无环，并能由 writer 独立重放。
- `[设计推理]` view datum 与 floor/z-band scopes 分离后可在不推翻 projector 的前提下长到退台/L 形/
  挑空。

**本轮没有运行任何 Python/pytest/几何探针，也没有运行全仓测试。** 因而不存在可标为“本轮运行
实测”的新算法结论；上面的 runtime 数字全部来自必读材料中的既有实测。

### 14.3 未能验证清单

- 未统计真实/历史 v3 draw 中满足“唯一 plan + 至少一 elevation existence、same plan along/host”的比例。
- 未对全 corpus 测 `0.300 m + unique mutual-nearest` 的误拒/误放率。
- 未验证多 elevation corroborator、重复窗、同投影不同 depth、跨楼层同 x 的 pairing 行为。
- 未验证下游是否要求 model-authored `window.id` 跨 run 稳定；若要求，plan-locator physical key 不足以
  完成业务 identity 迁移。
- 未验证 reading 的 elevation local-x datum 在所有来源中都确为 view-global，而非某些图按 floor 重置。
- 未验证当前所有 accepted/replay/orientation-enrichment loader 对 artifact V2 所需的完整改动清单。
- 未验证新 terminal status 与 CLI/status/report UI 的最小兼容方案。
- 未实测 per-floor 不同 footprint、退台 `along × z` visibility、挑空/中庭 scope；本稿只冻结接口接缝。
- 未验证把 host V1 升为 V2 后所有 judge/parity consumer 的迁移成本。
- 未验证本批是否应同时移除 model-authored `z`；现有材料不足，未擅自扩 scope。
- 未读取、import 或以任何方式接触 `case_tests/test_baseline/gt/`。
