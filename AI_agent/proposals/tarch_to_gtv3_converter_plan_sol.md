> ⚠️ **本文件 = 双独立出案之一（sol 稿），不是施工基线。**
> 施工基线 = [tarch_to_gtv3_converter_plan.md](tarch_to_gtv3_converter_plan.md)（主控综合裁决稿）。
> 裁定：**主干算法未采用本稿的 WallRibbon 双线配对路线**（理由见基线 §0/§3，本稿自认最脆环节 + 信息论不可识别）；
> 但本稿的 **7 条证据纪律与边界情形条款已并入基线 §2** 并具约束力，
> 双线配对内核作为 backlog 备选保留（基线 §3）。

# 天正真实建筑图 → GT v3 单线区划转换器方案（sol 独立稿）

> 日期：2026-07-21 · 状态：可施工设计稿；本稿不包含生产代码 · 目标样本：`sm24_anchor` 的 `sm24_source.dxf` · 目标接缝：规范化 DXF + extraction manifest v1 → **不改动的** GT v3 提取器

## 0. 决策摘要

采用一个 **judge-only、确定性、证据驱动、要求唯一解** 的天正适配器：先把双线墙恢复为带逐墙厚度和来源证据的 `WallRibbon` 图，再把外墙的真实外皮输出为 footprint、把内部墙的中性线输出为共享区划线，并用门窗证据把边界上的洞口虚拟闭合；随后生成规范化 DXF、标准 extraction manifest、逐实体 source map 和可视化审计件，交给现有 `gt_from_dxf.py`。

主链固定为：

```text
天正图形导出 DXF + 转换请求/区划意图
  → tarch_to_gtv3（只在 judge/tool 侧）
      → normalized.dxf
      → extraction_manifest.json
      → conversion_report.json + source_map.json + renders/
  → 现有 inspect_extraction_inputs / extract_plan_geometry / extract_gt_v3
  → candidate gt.json
  → render_gt + overlay + 人审
  → 独立晋升流程（转换器不得自动晋升或覆盖答案）
```

这个接缝对当前 L/U 形、无洞正交建筑不改 GT v3 本体，回归面最小。**回字形 courtyard 是明确例外**：当前 `c2_simple_orthogonal_no_holes`、提取器和 validator 都拒绝 interior ring；sm27 前必须先落一个通用的带洞 profile 扩展。转换器内部从 v1 起就保留多环和逐层 footprint，绝不把“无洞、单层、各层同 footprint”写进算法。

转换器不用 LLM，不按“最近的一对线”猜墙，不从自己切出的面反向生成种子后再自证正确。证据不足、解不唯一、区划意图缺失、目标 profile 表达不了时一律阻断。

---

## 1. 已核事实、术语与范围

### 1.1 事实底座

本设计以 `SURVEY.md` 和当前代码为准：

- sm24 源 DXF 的 SHA256 为 `92885d52340af72e24cd6396e893924f581b72983f5f1643076972d2aade245d`，`$INSUNITS=0`，显式按 mm 解释，即 `metres_per_unit=0.001`。
- 平面墙在 `WALL` 层，共 132 条 `LINE`；按现有 1 mm 轴对齐容差归一后为 67 竖、65 横。
- 墙为双线，门窗处墙面线中断。原墙线直接 polygonize 得到 23 个墙带小面，房间面没有闭合；仅取外皮得到 18 个 dangle、0 个面。
- 平面 `WINDOW` 层有 11 个 `$TCHSYS$WIN2D` 窗块、10 个 `$DorLib2D$*` 门块。
- 现有 `_entity_points` 的边界选择器不接受 `INSERT`；`_polygonize` 对 dangle/cut/invalid 零容忍。
- 当前 plan 提取要求：footprint 唯一、每个 polygonized face 恰好一个 `zone_seed`、所有 zone 并集与 footprint 相等。
- 当前 manifest 虽声明 `outer_skin|centerline`，实现只接受 `boundary_reference="outer_skin"`。
- 当前 schema/profile 禁止 polygon interior ring，且强制不同楼层 canonical footprint 完全相同。
- sm24 没有房间名；用户已定 sm24 的 role 不评分，sm25 起在 CAD 标房间名。sm24 的 L 形走廊是一个热区，总计 8 区。

### 1.2 本稿的最小只读复核

对指定样本另做了一次不落仓的只读探针，结果如下：

- 源 SHA、单位、132 条墙线均与 SURVEY 一致。
- 55 条墙线的“非主轴差”不是数学上的精确 0，最大仅 `1.31e-10 mm`；用 `judge_gt.yaml` 的 `dxf_axis_alignment_tolerance_m=0.001` 后恰为 67 竖、65 横。这与 SURVEY **无实质冲突**，实现不得用浮点精确相等判正交。
- 132 条墙线的颜色、线型、线宽属性完全相同，不能靠样式配对墙面。
- 11 个窗块完整 bbox 的法向尺寸全为 240 mm，沿墙尺寸为 1200/1500/4800 mm。
- 10 个门块的完整 bbox 包含门扇开启图形；法向尺寸为 585/780/877.5 mm，并非 240 mm。其沿墙投影/块尺度对应 900/1200/1600 mm 洞宽。

因此，SURVEY §5.1 对**窗块**的结论成立；派单问题 2 把它泛化成“门窗完整 bbox 都等于洞口”并不成立。门洞必须以“双侧墙面同步缺口”为几何真值，门块只作位置、类型和沿墙宽度的交叉证据。

### 1.3 术语

| 术语 | 本稿定义 |
|---|---|
| 墙面线（face track） | 天正导出的墙某一侧表面线，可能被洞口和接头切成多个片段 |
| 墙带（wall ribbon） | 一道墙的两侧面、局部厚度、中心支撑线、端头/接头和来源证据的组合；厚度逐墙、逐段保存 |
| 外皮（outer skin） | 与该层建筑外部无界空间相邻的外墙表面；它定义 GT footprint |
| 区划中性线 | 内部墙带两侧面的等距中线；相邻 zone 共享这一条零厚边界 |
| 虚拟闭合 | 只为拓扑和 GT 区划在门窗洞上补连续边，不修改或抹去原始门窗证据 |
| 区划意图锚点 | 在求解前已存在的“每个预期热区一个点”；来自 CAD 房间标签或经人确认的 sidecar，不由最终 faces 自动反推 |
| 规范化 DXF | 原 DXF 的审计副本，保留原实体并新增只含 GT 可消费图元的专用层 |

### 1.4 范围边界

范围内：正交墙；逐墙不同厚度；L/T/十字/自由端；L/U/回字形的内部 IR；块式或炸开式门窗；多 plan view/多 floor 的逐层处理；有/无房名两种流程。

本轮目标 profile 范围外：斜墙、曲墙、跨层对齐推断、多部件 multipolygon。遇到这些不是降级近似，而是稳定诊断并停止。

本工具是受控 GT 来源的**天正方言适配器**，不是产品 CAD 输入模态。它可使用 `WALL`、`WINDOW` 和天正块名前缀；不得把这些规则放进 `0_reading`、correction、执行器或 gate①。未来产品 CAD 模态仍应按原方案 §10 走“多方言适配器 → 产品 canonical IR”；本工具的 judge normalization IR 不冒充那个产品 IR。

---

## 2. 架构与接缝选择

### 2.1 文件/模块落点（施工建议）

后续施工建议新增：

- `src/agent/judge/tarch_converter_schema.py`：严格 request/report/source-map/IR model；无默认容差。
- `src/agent/judge/tarch_converter.py`：只读解析、墙图求解、规范化和验证；不写 GT。
- `scripts/tool_scripts/tarch_to_gtv3.py`：薄 CLI、路径策略、原子写新目录。
- `scripts/tool_scripts/render_tarch_conversion.py`：source/墙带/区划/洞口/诊断 overlay。
- `tests/test_tarch_converter.py`：合成、性质、负例。
- `tests/test_tarch_converter_sm24.py`：真样本只读端到端，所有输出进 `tmp_path`。
- `tests/test_gt_discipline.py`：机械保证 runtime/gate① 不 import 新工具，新 DXF 不进入 `case_data`。

`gt_extraction.py`、`gt_manifest.py`、`gt_schema.py` 在当前 L/U 落地阶段保持不变。sm27 的 profile 扩展单列为 §8 的前置批次，不能夹带进天正适配器实现。

### 2.2 为什么输出“增广副本 DXF”而不是直接生成 gt.json

1. 现有 v3 已经承担单位、view、snap、polygonize、zone tiling、opening/elevation、hash 和 canonical round-trip；复用它避免复制第二套 GT 规则。
2. 原门窗/立面实体及 handle 可原样保留；新增的 footprint/zone/opening evidence 放在独立层，selector 不会误吃原双线墙。
3. 人可在 CAD 或 overlay 中同时看到原双线和转换后的单线，答案可核验。
4. 转换错误被分成“证据恢复错误”和“v3 契约错误”，定位比把所有逻辑塞进提取器清楚。
5. 天正方言不会污染通用 v3 提取器。

### 2.3 被否决方案

| 方案 | 否决理由 |
|---|---|
| 让用户另画区划线 | 已被用户否决；复杂建筑不可扩展且会把人工错误变成标准答案 |
| 退回 v2 矩形分带/坐标聚类 | 会切碎 L 形走廊，烤死矩形 bbox/网格，正是本项目要消灭的错误 |
| 把相邻或最近的平行线直接平均 | 房间两侧的墙面也可能是“相邻平行线”；无厚度证据时问题本质上不可识别，最近策略会静默猜错 |
| 全图统一 120/200/240 mm | 当前样本通过不代表泛化；外/内墙及同层墙厚都可能不同 |
| 对双线做通用 `buffer()`/负 buffer | 会引入圆角/mitre 参数、吞小凹口、掩盖断线，且无法给每条输出边完整来源 |
| 只用 `PUB_HATCH` 找墙 | sm24 只给外墙 hatch，内墙缺失 |
| 填满所有小缺口后 polygonize | 会把漏画、接头错误也当门窗修掉，违反 fail-closed |
| 让 v3 直接理解天正块/双线 | 把来源方言、墙恢复和 GT 通用契约耦合，扩大回归面；回字形 profile 问题也不会因此消失 |
| 用 LLM 判断哪两条线是一道墙 | 非确定、不可复现、无法证明唯一解，不适合作为答案生成器 |

---

## 3. 输入、内部 IR 与输出契约

### 3.1 `TarchConversionRequestV1`

请求是 source-hash 绑定的严格 JSON，不允许未知字段。至少包含：

```jsonc
{
  "request_version": 1,
  "case": "sm24_anchor",
  "source_dxf_label": "sm24_source.dxf",
  "source_dxf_sha256": "92885d52340af72e24cd6396e893924f581b72983f5f1643076972d2aade245d",
  "normalized_source_id": "sm24-anchor-normalized",
  "target_geometry_profile": "c2_simple_orthogonal_no_holes",
  "native_units": "unitless",
  "metres_per_unit": 0.001,
  "floors": [
    {"id": "F1", "name": "Floor 1", "z_floor_m": 0.0, "ceiling_height_m": 4.5}
  ],
  "plan_views": [
    {
      "id": "plan-F1",
      "floor_id": "F1",
      "clip_box_dxf": {"xmin": 12276.94, "ymin": 18802.14,
                       "xmax": 41994.33, "ymax": 51678.57},
      "world_from_source_m": {"m00": 1.0, "m01": 0.0, "m02": -23.0576,
                              "m10": 0.0, "m11": 1.0, "m12": -26.5652},
      "wall_selector": {"entity_types": ["LINE", "LWPOLYLINE", "POLYLINE"],
                        "layers": ["WALL"]},
      "opening_selector": {"entity_types": ["INSERT", "LINE", "LWPOLYLINE", "POLYLINE"],
                           "layers": ["WINDOW"]},
      "room_label_selector": {"entity_types": ["TEXT", "MTEXT", "ATTRIB"],
                              "layers": ["0"]},
      "dialect_rules": {"window_block_names": ["$TCHSYS$WIN2D"],
                        "door_block_prefixes": ["$DorLib2D$"]},
      "zone_intent": {"mode": "cad_labels_or_reviewed_anchors", "anchors": []},
      "void_intent": []
    }
  ],
  "elevation_views": [],
  "north_axis": null,
  "raster_overlays": [],
  "label_role_map": {"办公室": "office", "会议室": "meeting", "走廊": "corridor"},
  "critical_dimensions": [],
  "overrides": [],
  "request_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

上例 clip 和 affine 是 sm24 的实测值：plan `edge` 框与 outer-skin SW `(23057.6, 26565.2) mm` 对齐，使 world footprint 为 `[0,10]×[0,20] m`。其它 case 必须从各自 `edge` 框和已审核原点生成，不能沿用 sm24 数字。

`request_sha256` 的 canonical 规则与 manifest 一致：计算时先将本字段置 64 个零，JSON key 排序、紧凑 separators、UTF-8、末尾一个换行；最终请求必须回填非零 digest。示例的空 anchors/零 hash 表示 sm24 首遍 REVIEW 请求，不是可 PASS 的最终文件。

关键约束：

- `plan_views` 是列表，算法逐层逐 view 运行；不允许 `floor_count == 1` 分支。
- `world_from_source_m` 沿用 manifest 的 signed-permutation + translation 语义；单位只乘一次。
- layer/block 名是每请求的天正方言绑定，不放全局隐藏默认。内置的已知块名前缀也必须记录 classifier 版本和命中规则。
- `elevation_views`、north、overlay 使用现有 manifest wire 的同构字段，转换器只透传和重绑必要 handle，不重新推断立面。
- `critical_dimensions` 是可选但强烈建议的独立真值约束，记录 DIMENSION handle、轴、期望跨度；有声明就必须吻合。
- override 只能是以下窄操作：绑定两条 source face track、把一组炸开图元绑定成一个 opening、声明某自由端墙为 `non_zoning`、确认一个候选 joint、提供 reviewed zone/void anchor。禁止 override 直接提交整套最终多边形。
- 所有 override 都带 source handles、几何摘要、理由、reviewer 和 request/source hash；源文件一变即失效。

### 3.2 区划意图契约

每层在墙图求解前必须有一组固定意图锚点：

```text
ZoneIntentAnchorV1
  zone_id / name / role
  point_world_m
  source = cad_label | reviewed_anchor
  source_entity_handle (cad_label 时必填)
  role_scored: bool
```

- sm25 起：从 footprint 内的 CAD `TEXT/MTEXT/ATTRIB` 得到点和原文；精确 `label_role_map` 决定 role，未知词不猜。
- sm24：首遍可输出编号 faces/候选点，但状态必须是 `NEEDS_REVIEW`；人确认 8 个锚点并明确 L 形走廊只给一个锚点后写回 hash-bound request，第二遍才可 PASS。sm24 使用 `role="unclassified"` 且 `role_scored=false`，不能按位置猜办公室/走廊。
- “自动给每个最终 face 放一个 centroid”只允许生成预览，不能成为可出 GT 的意图来源，否则错误切分会自我通过。

CAD 标签未显式给 zone ID 时，ID 固定为 `<floor_id>:zone:<uppercase-source-handle>`；同名办公室靠不同 handle 区分。标签点取 DXF 对齐/插入点，经 world affine 一次变换；点落边上时转 REVIEW，不用文字 bbox 猜另一个点。reviewed anchor 则必须由 request 明写 ID/name/role/point。

`role_scored` 只属于转换审计 wire，当前 `GtZoneV3` 没有这个字段。sm24 晋升前还必须机械确认该 case 的 judge/scorer 配置确实不判 role，并把那份配置的 hash 写入 report；不能向 GT JSON 偷加未知字段。

### 3.3 内部 IR

内部 IR 从第一版就支持以下结构：

```text
NormalizedBuildingIRV1
  floors[]
    floor_id, plan_view_id
    wall_ribbons[]
      id, axis, side_a_tracks[], side_b_tracks[]
      centre_segments[], thickness_m_by_segment[]
      caps[], joints[], openings[]
      evidence[], source_refs[]
    footprint
      exterior_ring
      interior_rings[]
    zoning_edges[]
      kind = wall_midline | exterior_closure_connector
      source/proof refs
    zones[]
      polygon (exterior + interior rings)
      intent_anchor
    non_zoning_walls[]
```

这里没有 `W_m/D_m`、行列、band、全局 wall thickness、共同 footprint 或固定楼层数。当前 v3 adapter 若表达不了某字段，应在 adapter 边界报 profile 错误，不能在 IR 中丢掉它。

### 3.4 输出 bundle

成功只写一个**全新、拒绝覆盖**的目录：

```text
<out>/
  source.original.dxf
  conversion_request.json
  normalized.dxf
  extraction_manifest.json
  conversion_report.json
  source_map.json
  bundle.json
  renders/
    plan-F1_source_vs_ribbons.png
    plan-F1_normalized_topology.png
    plan-F1_zone_intent.png
```

- `source.original.dxf`：输入 raw bytes 的逐字节副本，仅留 judge-only staging，hash 必须等于 request。
- `conversion_request.json`：回填非零 canonical hash 的精确请求副本，含所有 review/override。
- `normalized.dxf`：原 DXF 审计副本 + 生成层；不删除原墙/门窗/立面。
- `extraction_manifest.json`：合法 `GtExtractionManifestV1`，source hash 指向 `normalized.dxf`。
- `source_map.json`：每个生成 handle 到所有原 handle/子段、推导操作和 proof 的一对多映射。
- `conversion_report.json`：状态、统计、诊断、所有容差/config/实现 hash、IR semantic hash、v3 round-trip 结果。
- `bundle.json`：除自身外全部文件的 hash；按 canonical JSON 排序。

失败时只允许写诊断报告和标红预览，CLI 返回非零；不得留下名称看似可消费的 `normalized.dxf` 或 extraction manifest。

### 3.5 规范化 DXF 层

生成层名固定并由 exact handles 选择：

| 层 | 图元 | 用途 |
|---|---|---|
| `GT3_NORM_FOOTPRINT` | 每层一个闭合无 bulge `LWPOLYLINE` | v3 `footprint_boundary`；当前 profile 只容许外环 |
| `GT3_NORM_ZONE` | 独立 `LINE` 或无 bulge polyline edges | 内部区划中性线和必要的外墙 closure connector |
| `GT3_NORM_OPENING` | 每个可输出的外部 opening 一个闭合矩形 polyline | 避开 boundary selector 对 INSERT 的限制，并避免门扇 bbox 污染 |
| `GT3_AUDIT_*` | 非 selector 图元 | 墙带 ID、厚度、锚点、被虚拟补齐的洞口和诊断 |

有实体时，manifest selector 使用 `only_listed`、排序后的 exact handles、`min_count == max_count == 实际数`。单 zone 层可能没有内部区划实体，此时 `zone_boundaries` 必须改用 `all_matching`、空 handles、`min_count=max_count=0`；不能构造 schema 不允许的空 `only_listed`。`plan_openings` 直接列生成 outline locator，并显式按 host wall 方向写 `span_world_axis`。这样后续有人往消费层加线也不会静默进答案。

预期 CLI 接法为：

```text
python scripts/tool_scripts/tarch_to_gtv3.py \
  --dxf <source.dxf> --request <conversion_request.json> \
  --config src/configs/judge_gt.yaml --vg-config src/configs/correction.yaml \
  --out-dir <new-staging-dir>

python scripts/tool_scripts/gt_from_dxf.py \
  --dxf <new-staging-dir>/normalized.dxf \
  --manifest <new-staging-dir>/extraction_manifest.json \
  --config src/configs/judge_gt.yaml --vg-config src/configs/correction.yaml \
  --out <new-candidate-path>
```

`--out-dir` 必须不存在，并拒绝 `case_data`、默认 GT 根和受保护 gt-source 根；原图、规范化 DXF 和 candidate 均先留在 judge-only staging。

---

## 4. 转换算法

### 4.1 S0：输入和 view 预检

1. 读取 raw bytes，先核 source SHA，再交给 ezdxf；单位和显式 scale 不符即停止。
2. 用 request 的 clip/view binding 切 plan。`edge` 闭框和框内图名可用于生成 request 建议，但最终 clip 必须 hash-bound；多框/跨框/框重叠不猜。
3. plan clip 内 proxy/custom object 非零即要求重新“图形导出”。
4. 只接受 request selector 命中的墙/洞口/房名；家具、标注和立面不参与墙恢复，但 inventory 进入报告。
5. 坐标先乘 `metres_per_unit`，再进 affine；后续只用 world metre。

### 4.2 S1：原始图元归一化

1. `LINE/LWPOLYLINE/POLYLINE` 拆成带 handle/subentity ancestry 的 primitive；bulge/arc/非平面阻断。
2. 使用 `dxf_axis_alignment_tolerance_m` 投到水平/竖直；两轴残差都超限为非正交，两个跨度都小于等于该值为短边错误。
3. endpoint join 复用 `dxf_node_join_tolerance_m`：连通分量直径也必须不超过该值，禁止链式漂移；代表点取字典序最小点。
4. 同支撑坐标上的共线片段只做 interval union，不丢 ancestry；重叠/重复来源进入 exact-cover 约束，不能先静默删线。
5. 每条 source `WALL` primitive 最终必须恰好被解释为 wall side、cap、jamb、joint return 或显式 ignored-with-review；未计入即阻断。

### 4.3 S2：门窗证据与洞口区间

处理顺序是“证据组件 → 两侧同步缺口 → host 墙候选”，不是先把所有缺口补上。

#### 块仍存在

- 展开 INSERT 的完整变换，只用于 bbox/组件审计，不把 INSERT 放入边界 selector。
- 窗：块 bbox 的短边可作为该位置的局部厚度证据，但仍须与两条墙面上的相同沿墙 gap 一致。
- 门：块完整 bbox 含开启扇，**不得**拿法向 bbox 当墙厚或补洞矩形；沿墙轴由块 rotation 与候选墙共同确定，最终 opening span 取两侧墙面的公共缺口，块沿墙投影必须在 node tolerance 内同意。
- 一个组件匹配 0 个 host 或多个 host 都阻断；不得用 handle 排序消歧。

#### 块已炸成线

1. 在 configured opening layers 上按几何连通和原 ancestry 形成组件；不把全层散线按“距离近”随意聚成一扇。
2. 组件 bbox/弧线/门扇线只用于给候选位置和类型；两侧墙面上端点一致的公共 gap 才定义洞宽。
3. 若门窗线也落到 `WALL` 层，则短 jamb/return、成对 gap 和组件拓扑可提出候选；仍无唯一 kind/host 时输出候选 overlay，要求窄 override。
4. “有同步 gap 但无门窗证据”与“有门窗证据但无同步 gap”都不自动修；前者可能是漏画，后者可能是家具/详图/错误层。

对每个确认 opening 记录：kind、wall-ribbon ID、side-A/side-B gap、沿墙 span、局部厚度证据、源 handles。随后只在**工作拓扑**上补齐两侧 face track 和区划中性线；原 DXF 洞口仍保留并在 audit 图中用虚线显示补段。

现有 GT v3 的 `GtOpeningV3` 只挂 footprint 的 exterior boundary segment。因此：

- 所有内外门窗都参与墙拓扑闭合；
- 只有 host 为 footprint exterior 的 opening 进入 `plan_openings` 和 `GT3_NORM_OPENING`；
- 内门不伪装成 exterior GT opening，只在 `source_map/report` 留证。若未来要判内门，需另开 schema/profile，不在本转换器偷塞。

### 4.4 S3：逐墙厚度证据与双线配对

#### 厚度证据，不设全局厚度

候选厚度只能来自源图中的离散证据：

1. 窗 bbox 短边；
2. 连接两侧面的墙端 cap 或 opening jamb；
3. `PUB_DIM` 中 request 显式绑定的墙厚尺寸；
4. `PUB_HATCH` 的两侧边界（只作外墙局部证据）；
5. 已有证据厚度在另一段上的精确复现；
6. source-hash 绑定的人审 face-pair override。

不得出现 `DEFAULT_WALL_THICKNESS=0.24`、`MAX_WALL_PAIR_DISTANCE`、`MIN_ROOM_WIDTH` 或“取最小间距”。同一层可以同时有 120/200/240 mm，也可有其它从图中证明的厚度；每个 `WallRibbonSegment` 保存自己的厚度和 proof。

#### 候选 wall ribbon

两条平行 face track 只有同时满足下列条件才成为候选：

- normal separation 与某条厚度证据一致；
- 扣除已认证 opening 和 joint interval 后，沿墙覆盖互相对应；
- gap 端点、cap/jamb 或 joint 端型能成对解释；
- 两面之间没有另一条会使墙实体自交的 face track；
- 生成的局部墙实体为正面积、无自交正交带。

然后做确定性的全局 exact-cover/回溯求解：

- 每条相关 WALL primitive 恰好承担一个角色；
- 每个 opening gap 恰好属于一道墙；
- 每个 cap/joint 的所有半边恰好闭合；
- wall-ribbon interiors 只能在已分类 joint 处相交；
- 解必须满足预先给定的 zone/void anchors，但 anchors 不参与生成新墙线。

要求 **恰好一个 canonical 解**。0 解报缺失证据，2 个及以上报歧义并列出最小冲突集；禁止给候选打“最近/最像”分后选第一名。纯双线矩形在没有厚度、标签、cap 等语义时确实可能无法区分“厚墙”与“窄房间”，这是信息论上的不可识别，正确行为就是阻断而不是发明先验。

### 4.5 S4：接头求解

接头只从已配对 wall ribbons 的支撑轴和原 face 端型推导。因墙面在厚墙接头处本来会停在另一墙的近/远面，中心轴延伸量可能大于 1 mm；这不是容差补线，而是由两道已证明墙带的交点精确派生。

| 接头 | 判定 | wall-ribbon 结果 | 输出区划线 |
|---|---|---|---|
| L 角 | 两轴各仅在交点一侧有墙，face returns 唯一配合 | 两中线在唯一交点 miter；厚度可不同 | 两边在交点相接；外轮廓由外侧 face 求，不由统一 offset 求 |
| 丁字 | 主墙轴穿过交点，支墙只在一侧；支墙两面终止于主墙两面 | 支墙中线精确止于主墙中线 | 主墙为内部墙时节点相接；主墙是外墙时再生成到真实 outer skin 的 closure connector |
| 十字 | 两轴在交点两侧都有成对支持 | 两中线同时 node，墙实体在 joint 处 union | 两条区划线在一点相交，形成四个拓扑象限；若 anchors 不支持四分则阻断 |
| 自由端 | 两侧面由唯一 cap 连接且无其它 wall joint | 中线止于 cap 中点，墙实体闭合 | 不盲目延伸。若两侧空间绕 cap 连通且属同一 intent，可经证明标为 non-zoning；否则要求人确认/修图 |
| 厚度变化 | 同一支撑方向的相邻 ribbon 段有不同已证厚度 | 保留逐段厚度和必要的中线小 jog/过渡 joint | 只要形成合法正交分区即可；不得强拉成一个全局轴 |

任何 T/L/十字有两种同样合法的 continuation，或自由端会导致 v3 dangle 而又无 `non_zoning` 证据，均 fail。尤其不能把 interior wall 穿过走廊拐角延长到另一边；只有 raw wall ribbon continuation 存在时才续线。

### 4.6 S5：outer skin、凹角与洞

1. 用已闭合 opening 的 wall ribbons 构造墙实体 arrangement。
2. 从 arrangement 外侧做无界 flood-fill；与无界外部相邻的墙面链构成该层 exterior outer-skin ring。**不用所有墙的 bbox。**
3. 依 source face 次序连接凹/凸角，要求一个合法正交简单外环；L/U 的凹角天然保留。
4. 被外墙包围、与无界空间不连通的空白 component 不能简单当“房间”或“courtyard”：
   - 有 zone anchor → 房间/zone 候选；
   - 有 `VoidIntentAnchor` → footprint interior ring；
   - 两者都无或都有 → 阻断。
5. 多个不相交 exterior ring 是 multipolygon，当前范围阻断并保留 IR 诊断，不取最大环。

footprint 始终取真实 exterior outer skin。内部墙始终取每道墙自己的中性线。两者看似混合，实为 v3 所需语义：footprint 保留建筑外包尺寸，内部相邻 zone 又必须共享一条零厚边界。

### 4.7 S6：区划线、种子和 L 形走廊

1. 对每道**确认为 zoning** 的内部 wall ribbon 发射中性线。
2. 内墙接 exterior wall 时，从 wall-ribbon 中线 joint 沿支墙轴补到已求出的真实 outer skin；该 closure connector 有两道墙的 provenance，不能是无来源的任意延长。
3. non-zoning 自由端墙保留在审计 IR，不发到 `GT3_NORM_ZONE`。
4. 用 exterior outer skin + zoning edges 跑与 v3 等价的 noding/`polygonize_full`。dangle/cut/invalid 任一非零立即阻断。
5. 每个 face 必须恰含一个**预先存在**的 zone anchor，anchor 距边大于 node join tolerance；0/2+ 都阻断。
6. zone union 必须等于实际 footprint，差面积不超过 topology area tolerance。

L 形走廊的保证来自两道相互独立的约束：

- 转换器不发射没有 wall-ribbon 证据的“拐角补线”；
- sm24 的 reviewed intent 只给走廊一个锚点。若某条误延长把走廊切成两个 face，其中一个必然无锚，转换器不能为它自动造 seed，因此会阻断。

### 4.8 S7：生成当前 v3 可消费物

当前无洞 profile 下：

- `GT3_NORM_FOOTPRINT` 每层写一个闭合 exterior `LWPOLYLINE`；有 interior ring 时先报 profile 阻断，不丢洞。
- `GT3_NORM_ZONE` 写内部中性线/closure connector；按 canonical 几何排序后分配 handle。
- 外部 opening 写由两侧共同 gap 构成的正交矩形 outline，而不是复制门块完整 bbox。
- manifest 的 `footprint_boundary`/`zone_boundaries`/`plan_openings` 指向生成 handles。
- `boundary_reference="outer_skin"`，`default_wall_thickness_m=null`。逐墙厚度留在 report/map；不能压成一个默认值。
- zone seeds、name、role 来自 §3.2 意图；转换器不得覆盖。

然后在尚未交给正式 CLI 前，转换器自己调用：

1. `GtExtractionManifestV1` strict validate + hash；
2. `inspect_extraction_inputs`，必须 `PASS`；
3. `extract_plan_geometry`，重验 footprint、zones、source refs；
4. 若请求带完整 elevation binding，再调用 `extract_gt_v3` 和 `validate_gt_v3`；
5. DXF 实体顺序打乱后重新转换，semantic IR、manifest payload 和 GT canonical bytes 必须一致。

任一步失败都把原 v3 code 包进 `TGC_V3_PREFLIGHT_FAILED` context，转换器自身仍返回非零。

---

## 5. 容差纪律与确定性

转换器只接收 `load_gt_tooling_config()` 解析出的冻结 profile；不在代码、request 或 CLI 增加数值 override。

| 现有字段（profile v1 值） | 转换器中的唯一用途 |
|---|---|
| `dxf_axis_alignment_tolerance_m = 0.001` | 判断/投影近水平、近竖直 primitive；不用于决定哪两面是一道墙 |
| `dxf_node_join_tolerance_m = 0.001` | endpoint、gap、jamb、厚度/尺寸证据的坐标一致、label/seed 边距和同一 joint 的坐标相等；component 直径仍受限 |
| `dxf_topology_area_tolerance_m2 = 0.000001` | sliver、polygon/tiling/overlay 面积残差门限 |
| `opening_boundary_max_distance_m = 0.400` | opening evidence 到候选 wall ribbon 的 host 候选门；不能用来拉伸墙 |
| `opening_assignment_tie_epsilon_m = 1e-9` | 两个 opening host 候选的距离并列判定；并列即失败 |
| `elevation_match_max_distance_m = 0.400` | 只由下游现有 elevation 配对使用 |
| `elevation_match_tie_epsilon_m = 1e-9` | 只由下游现有 elevation 配对使用 |
| Vg depth/endpoint epsilon 均为 `1e-9 m` | 只由下游 boundary visibility 使用，仍归 `correction.yaml` 所有 |

墙厚是源数据，不是 tolerance。墙配对是离散唯一解，不需要“最大墙厚”或 cost epsilon。后续若真实数据证明必须增加新容差，应走 `judge_gt.yaml` 的 versioned profile 评审；不得在实现里藏一个常数。

确定性要求：

- 所有 source handle、primitive、候选、解、生成实体和诊断按公开 canonical key 排序。
- 不读 clock/random/network/cwd 隐式文件。
- 保存 DXF 前清理/固定可变时间和 GUID header；生成 handle 顺序固定。
- 相同 source bytes + request bytes + config bytes + converter implementation bytes 必须得到相同 semantic hash、manifest 和 GT canonical bytes。
- 如果 ezdxf reserialization 仍有非语义字节波动，测试必须先暴露并阻断；不能只比较几何而让 manifest source hash漂移。

---

## 6. 来源链和人工可核验性

### 6.1 逐边 ancestry

每个生成图元在 `source_map.json` 中至少记录：

```text
generated_handle
view_id / floor_id / semantic_role
canonical_geometry_world_m
operation = outer_skin | midline | opening_bridge | joint_connector | opening_outline
source_entity_refs[]
wall_ribbon_ids[] / opening_id / joint_id
proof_ids[]
```

一个中线通常对应两侧多个 raw LINE；一个 closure connector 对应内部墙和外墙 joint；不能把 ancestry 缩成一个随便的 handle。

规范化 DXF 的 named object dictionary 中写一个 XRECORD `ENERGYPLUS_AGENT_GT_NORMALIZATION_V1`，内容为：raw source SHA、request SHA、source-map SHA、converter implementation SHA、judge/vg config SHA。于是 GT 的 source hash → normalized DXF → XRECORD → raw source/map 构成可验证链，而无需改当前 GT schema。

保存顺序固定为：先生成稳定 handles → canonical source map → 算 map hash → 写 XRECORD → 保存最终 DXF → 算 normalized SHA → 生成 extraction manifest。禁止先写 manifest 后再改 DXF。

### 6.2 必备渲染

每层至少产三张图：

1. raw 双线灰色；wall ribbon 两侧彩色；厚度和配对 ID 标注；未消费 source 线红色。
2. outer skin 黑色；内部中性线蓝色；虚拟洞口补段紫色虚线；joint 类型和自由端标注。
3. polygonized zones 半透明填色；CAD label/reviewed anchor 十字；L/U 凹角与 void 单独着色。

随后必须走现有 `render_gt.py` 和 `render_gt_overlay.py`。转换器 PASS 只说明机器契约通过；GT 仍是 `candidate`。只有人看过 source-vs-normalized、direct GT render 和原 PNG overlay，才能按现有四种 verification method 晋升。转换器和 `gt_from_dxf.py` 均不得提供 `--promote`、`--overwrite`。

---

## 7. 失败诊断设计

### 7.1 wire

`ConversionDiagnosticV1` 固定字段：

```text
code, severity = BLOCK | REVIEW | INFO, stage
view_id, floor_id
source_entity_handles[], generated_candidate_ids[]
source_points_dxf[], points_world_m[]
context{}                  # 结构化数字/候选/下游 code
action_code                # 稳定、可由 UI 映射成人话
overlay_asset              # 指向具体标红图
```

`BLOCK` 和 `REVIEW` 都不准生成可消费 bundle；`REVIEW` 仅表示可通过 hash-bound 窄 override 继续。异常消息不能只有 Python traceback。

### 7.2 诊断码和闭环

| code | 触发 | 人拿到后能做什么 |
|---|---|---|
| `TGC_INPUT_SOURCE_HASH_MISMATCH` | request 与 DXF bytes 不同 | 选对源文件或重建 request；旧 override 自动失效 |
| `TGC_INPUT_UNIT_UNBOUND` | unitless 且未显式给 scale | 在 request 绑定经尺寸链确认的 `metres_per_unit` |
| `TGC_INPUT_PROXY_IN_PLAN` | plan 内仍有天正专有对象 | 重新执行天正“图形导出” |
| `TGC_VIEW_AMBIGUOUS` | clip 缺失、重叠、跨框 | 在 overlay 选择正确 `edge` 框/修 request |
| `TGC_ENTITY_UNSUPPORTED` | arc/bulge/非平面/未知 truth entity | 查看 handle，修图/导出；本轮不近似斜曲线 |
| `TGC_WALL_NONORTHOGONAL` | 超 axis tolerance | 查看两端坐标；若确是斜墙则超出本轮范围 |
| `TGC_WALL_THICKNESS_UNEVIDENCED` | 某墙无窗/cap/dim/hatch/override 厚度证据 | 绑定现有尺寸或在候选图中确认该 face pair |
| `TGC_WALL_PAIR_MISSING` | 某 face 无合法配面 | 查看红线及相邻洞口；修断线或补窄 override |
| `TGC_WALL_PAIR_AMBIGUOUS` | exact-cover 有多个解 | overlay 并列显示候选墙带；人只确认冲突 pair，不重画全图 |
| `TGC_WALL_ENTITY_UNACCOUNTED` | WALL primitive 未分配角色 | 检查它是墙、详图还是误层；修 selector/源图 |
| `TGC_OPENING_GAP_UNEXPLAINED` | 两侧同步 gap 无门窗证据 | 检查漏块、炸块、漏画；不得自动补 |
| `TGC_OPENING_EVIDENCE_UNBOUND` | 门窗组件找不到同步 gap | 检查家具/立面被误选、墙线未断或图层错误 |
| `TGC_OPENING_GEOMETRY_DISAGREEMENT` | 块沿墙跨度与双侧 gap 不同 | 显示块/gap 两组端点，修源图或确认炸块 group |
| `TGC_OPENING_HOST_AMBIGUOUS` | 一个组件可挂多道墙 | 查看候选 wall IDs；用 opening-group override 绑定唯一 host |
| `TGC_OPENING_KIND_AMBIGUOUS` | 炸开后门/窗类型不可判 | 绑定源组件为 door/window；不靠形状评分猜 |
| `TGC_JOINT_AMBIGUOUS` | T/L/十字 continuation 不唯一 | 查看 joint 四向半边图，确认 joint 或修断线 |
| `TGC_FREE_END_INTENT_REQUIRED` | 自由端会产生 dangle/分区歧义 | 标为 non-zoning、补正确连接，或确认它确实应闭区 |
| `TGC_FOOTPRINT_MULTIPLE` | 多个 exterior component | 检查漏闭合；若确为多栋则等待 multipolygon profile |
| `TGC_PROFILE_HOLE_UNSUPPORTED` | IR 有 courtyard/interior ring，目标是 no-holes | 不填洞；先完成 §8 新 profile，再重跑 |
| `TGC_PROFILE_FLOOR_FOOTPRINT_UNSUPPORTED` | 各层 footprint 不同但当前 profile 要求相同 | 不复制首层 footprint；切换新 profile |
| `TGC_TOPOLOGY_RESIDUAL` | dangle/cut/invalid/sliver | context 给残线端点、source handles 和 topology overlay |
| `TGC_ZONE_INTENT_MISSING_FACE` | 某 face 无预先锚点 | 查误切线/漏房名；不能自动新增 seed |
| `TGC_ZONE_INTENT_MULTIPLE` | 一 face 有多个锚点 | 修重复标签/anchor 或漏墙 |
| `TGC_ZONE_SEED_NEAR_BOUNDARY` | 点距边不大于 node tolerance | 移房名/审核锚点到面内，不挪边界迁就点 |
| `TGC_ZONE_INTENT_SPLIT` | 一个具名 intent 被错误线切开，含 L 走廊场景 | 查看造成 split 的 wall/joint；禁止给碎片再造 seed |
| `TGC_LABEL_ROLE_UNKNOWN` | sm25+ 房名不在 exact map | 扩充经审核的 label-role map 或修 CAD 文字 |
| `TGC_PROVENANCE_INCOMPLETE` | 生成边无 source/proof 或 map hash 不闭合 | 这是实现缺陷；不能人审绕过 |
| `TGC_V3_PREFLIGHT_FAILED` | 现有 v3 inspect/extract/validate 拒绝 | context 保留原 v3 code；按具体边/seed/manifest 修 |
| `TGC_NONDETERMINISTIC_OUTPUT` | 重排/重复运行产物不同 | 阻断发布，修排序、header 或 handle 分配 |

诊断报告最后附 `unconsumed_source_handles`、`opening_coverage`、`wall_proof_coverage`、`zone_intent_coverage` 四个清单；只给总数不足以定位。

---

## 8. L/U/回字形与 GT profile 演进

### 8.1 当前 profile 能做什么

- L、U 形只要是一个无洞的正交简单 exterior ring，当前 `c2_simple_orthogonal_no_holes` 能表达；现有合成测试也已覆盖凹多边形和 Vg 多 depth。
- sm24 外包是 10×20 矩形，L 形的是走廊 zone；当前 profile 可表达非凸 zone polygon。
- 当前 profile **不能**表达 courtyard、zone 的 interior ring、不同楼层 footprint 或 inner-loop boundary segment。

### 8.2 sm27 前必须落的新 profile

建议新增 profile 名 `c2_orthogonal_per_floor_holes_v1`，保持 schema_version 3 但以 profile 分支旧/新行为；旧 profile 的 canonical bytes 和错误码不得变化。施工范围至少包括：

1. `GtExtractionManifestV2`/`PlanViewBindingV2`：分别绑定 exterior boundary、hole boundaries 和 `VoidSeedV1`，不能靠“无 zone seed 的面就是洞”猜。
2. `geometry_profile` literal 增加新值；`GtPolygonV3.interior_rings` 真正启用。canonical 规则固定为 exterior CCW、hole CW；各 ring 从字典序最小顶点开始且删除共线点；holes 按 canonical 顶点 tuple 排序。
3. `_canonical_polygon` 和 footprint polygonize 保留 holes；每个 hole 必须由一个 void seed 唯一证明。
4. `boundary_loop_id` 从仅 `"exterior"` 扩为稳定 loop ID（如 `exterior`、`hole:0001`）；inner-loop outward normal 指向 courtyard。
5. stable boundary ID 的新 profile contract 纳入 loop ID，避免外/内环同几何碰撞。
6. Vg/立面 surface binding 支持 inner-loop façade；看不见的 courtyard 边也不能丢。
7. validator 用完整含洞 Polygon 检查 zone within/union/overlap；允许必要的 zone interior rings。
8. 去除新 profile 下“各层 footprint 完全相同”的约束；仍逐层校验 z stack 和各自 tiling。
9. `render_gt.py`、overlay、scorer/judge adapter 显示和比较洞，不以 bbox 填回 courtyard。
10. 加旧 profile golden regression、新 profile donut/多层异 footprint/inner opening 的 round-trip 测试。

这不是天正特例，而是 GT 几何能力缺口。把 courtyard 在转换器里用一条“切缝”变成无洞环、填成实心、取 bbox，都会改变答案，必须禁止。

---

## 9. 测试与验收

### 9.1 合成单元与负例矩阵

每个夹具从独立的 canonical building oracle 生成双线天正式 DXF，再要求 converter 反演后与 oracle 拓扑相等；不能拿 converter 自己的输出作 golden。

| 维度 | 必测值 |
|---|---|
| 墙厚 | 同图 120/200/240；沿墙厚度变化；非标准但有尺寸证据 |
| footprint | 矩形、L、U、凹阶梯；donut 在 IR 成功而旧 adapter 明确阻断 |
| zone | 矩形、非凸 L/T、单 zone、多个 zone、一个带洞 zone（新 profile） |
| joint | L、T、十字、外墙 T、不同厚度相交、自由端 zoning/non-zoning |
| opening | window INSERT、door INSERT+门扇 bbox、炸开成线、嵌套块、双侧 gap 不一致、证据缺失 |
| 意图 | 一面一标签、重复/缺失/边上标签、reviewed anchors、L 走廊一个 anchor |
| 楼层 | 1/2/3 层；相同和不同 footprint；不同 plan view 方位/镜像 |
| 单位/顺序 | mm 与 m 同构；平移、90°旋转、镜像；实体重排；共线段 split/merge |

必须有以下 fail-closed mutation tests：删一侧墙片、移动一个门块、增加一条无证据 spur、交换两个 face pair、破坏一个 cap、复制房名、把 seed 移到边上、给 donut 使用旧 profile。每个 mutation 应命中稳定 code 和具体 handle/坐标，而非产生另一份 PASS 几何。

性质/变形测试：

- 正交 polyomino grammar 随机生成 L/U/多凹角/洞和逐墙厚度，双线化后 round-trip；不只生成矩形网格。
- source 全局平移、合法 signed-permutation、单位换算、entity/handle 创建顺序变化后，world semantic IR 相同。
- 门窗块炸开前后，opening host/span 和最终区划拓扑相同。
- 同一共线墙被切成 N 段或合成一段，结果相同、ancestry 可不同。
- 人为构造两个 equally valid wall pairing，必须 `TGC_WALL_PAIR_AMBIGUOUS`，不能选择一个。

### 9.2 sm24 真图端到端 gate

sm24 是真实回归锚，不是泛化证明。最低通过条件：

1. 输入 SHA、单位、plan frame 与 SURVEY 一致；132 条 WALL primitive 全部有解释，未消费清单为空。
2. 11 窗 + 10 门证据全部唯一绑定到 wall ribbon；门的法向 full bbox 不被当厚度。
3. 规范化 footprint 为真实 outer skin 的 10.000 m × 20.000 m，面积 200 m²；不得输出 9.76×19.76 的 centerline bbox。
4. `polygonize_full` 对 footprint+zones 得 8 个 zone face，dangle/cut/invalid 均为 0；zone union 与 footprint 对称差在现有 area tolerance 内。
5. L 形走廊为一个非凸 polygon、一个 reviewed seed；没有拐角 spur 或两个 corridor zone ID。
6. `inspect_extraction_inputs == PASS`，`extract_plan_geometry` 成功，source refs 每条边非空。
7. 完整 elevation manifest 就绪后，`extract_gt_v3`、`validate_gt_v3`、canonical reload 全过；只有 exterior openings 进入 GT opening wire，内门仍在转换报告中对账。
8. source-vs-ribbon、normalized topology、direct GT render、原 PNG overlay 四类图由人审；总体 10×20、墙/洞/区划逐处吻合。
9. sm24 role 全为明确的 unscored policy；不得输出位置推断的“办公室/会议室”并假装来自 CAD。

### 9.3 泛化证据，不以 sm24 代替

采用三层证据：

1. **语法覆盖**：上述独立 oracle + property tests 覆盖厚度、接头、洞口编码、非凸、洞、多层的笛卡尔组合。
2. **变形不变量**：平移/镜像/旋转/单位/分段/炸块不改变语义；这能发现靠绝对坐标、线长、创建顺序的隐式假设。
3. **按序 held-out 真图**：在看 sm25 前冻结 converter/config/version，用 sm25 L 验证；修订后再冻结，用 sm26 U 验证；完成 §8 profile 并冻结后才用 sm27 donut 验证。每次修订都回跑前面所有 golden，且记录“因哪个新方言证据改了哪条规则”。

sm25/sm26 的通过不能只看 v3 PASS，还要比较 CAD 房名“一 face 一 label”、关键尺寸和人工 overlay。sm27 在旧 profile 下得到明确阻断本身是正确测试，但不算路线完成；新 profile 端到端通过才算。

---

## 10. 分阶段施工与退出门

### P0：contract 与诊断骨架

- 落严格 request/report/source-map model、canonical hash、CLI 新目录/不覆盖策略。
- 接现有 tooling config，禁止新容差。
- 落 source inventory、view/unit/proxy/orthogonal preflight 和诊断 renderer。

退出门：同输入重复运行 report byte-identical；所有输入负例有稳定 code；discipline tests 通过。

### P1：opening + wall-ribbon 唯一解内核

- 落块/炸块组件、同步 gap、逐墙厚度 evidence、候选 exact-cover。
- 落 L/T/十字/自由端/厚度变化 joint。
- 落 source primitive 100% accounting 和最小冲突集。

退出门：§9.1 无洞合成矩阵和所有 ambiguity mutation 通过；没有 nearest/global thickness 常量。

### P2：当前 profile adapter + sm24

- 落 outer-skin flood-fill、中性区划线、closure connector、reviewed anchor 双遍流程。
- 写增广 DXF、source map/XRECORD、manifest v1。
- 复用现有 v3 全链并完成 sm24 四类人审。

退出门：§9.2 全部通过；只产 staging candidate，不晋升。

### P3：sm25/sm26 与房名

- 落 TEXT/MTEXT/ATTRIB label binding 和 exact label-role map。
- 依 held-out 纪律跑 L/U；只吸收真正出现的天正导出差异。

退出门：两真图每 face 恰一 CAD label，非凸 footprint/zone、开口、overlay、GT round-trip 全过。

### PH：带洞/逐层 footprint profile（sm27 前置）

- 按 §8 独立设计/实现/对抗审；旧 profile byte regression 必须不变。

退出门：合成 donut、inner façade/opening、多层异 footprint、render/overlay/judge 全链通过。

### P4：sm27 held-out

- converter 内部 IR 不改形状模型，只启用新 adapter/profile。
- 回字 courtyard 由 void intent 证明，不能由无 seed 猜。

退出门：sm27 end-to-end + 人审；旧 profile 对同图仍稳定报 `TGC_PROFILE_HOLE_UNSUPPORTED`。

---

## 11. 八个设计问题逐项结论

1. **双线 → 单线**：以有来源的逐墙厚度建立 wall ribbons，全局 exact-cover 要求唯一。外墙输出真实 outer skin；内部墙输出各自中性线。`boundary_reference="outer_skin"` 描述 target footprint，内部共享中性线不等于把 manifest 改成 centerline；`default_wall_thickness_m=null`。
2. **洞口补齐**：先把块/炸开组件与墙双侧同步 gap 唯一绑定，再只在工作拓扑上补齐。窗 bbox 短边可证厚度；门完整 bbox 含门扇，不能直接补墙。规范化 opening 一律写生成的闭合 polyline，v3 不需吃 INSERT。
3. **接头**：L/T/十字由 paired ribbon 支撑轴和 face 端型求唯一 continuation；自由端先闭 wall solid，再由 zone intent 证明是否 non-zoning。只用现有 axis/node/topology/opening 容差，不设墙厚或延长容差。
4. **凹角/非凸/洞**：外皮从无界外部与墙实体的相邻边求，故 L/U 不会退成 bbox。回字 courtyard 必须有 void intent，并需要新 `c2_orthogonal_per_floor_holes_v1`；当前 profile 只能明确阻断。
5. **区划意图**：sm25+ 来自 CAD 房名点；sm24 来自首遍预览后经人确认、source-hash 绑定的 8 个 anchors。最终 faces 不得自动反生正式 seeds。走廊只有一个 anchor，误切后出现无 seed face，必失败。
6. **失败定位**：结构化 code 携带 view/floor、raw handles、source/world 坐标、候选/冲突集、action 和标红 overlay；BLOCK/REVIEW 均不产可消费 bundle，形成“定位 → 修图或窄 override → source hash 重跑”的闭环。
7. **验收**：sm24 真图全链 + 独立 oracle 合成/property/mutation/metamorphic + sm25/26/27 逐次冻结 held-out。sm24 PASS 只证明锚点，不证明泛化。
8. **房间 role**：sm24 走显式 `unclassified + role_scored=false`，不推断；sm25 起一 face 一 CAD label，原文作 name、request 的 exact map 作 role，未知/重复/缺失均阻断。有标签和无标签流程都可运行，但无标签必须经过 reviewed anchors。

---

## 12. 主要风险与未决项

1. **最脆环节是 wall-ribbon 配对与 joint 唯一性**。门窗/接头把 face track 切碎，而纯几何有时不可识别。风险控制不是加启发式，而是厚度 proof、source 100% accounting、固定 anchors、唯一解和窄 override。
2. **门块 full bbox 不能代表门洞矩形**。sm24 已实测；施工测试必须把这条做成回归，防止沿用窗逻辑。
3. **sm27 受 GT profile 阻塞**。这不是 converter 能“修”的输入差异；若 profile 延误，正确状态是明确失败而非伪造无洞 footprint。
4. **sm25 房名的实际导出类型/图层尚未有真样本**。实现应先支持 TEXT/MTEXT/ATTRIB 的显式 selector；若天正导出仍丢房名，回退 reviewed anchor，而非按布局猜 role。
5. **DXF 重写的 byte determinism** 需要专门验证。若 ezdxf 不能稳定保存增广副本，可改为生成最小 deterministic DXF 并把原 plan/elevation evidence规范化复制进去；接缝和 source-map 契约不变。
6. **人工核验仍是必要安全门**。自动 topology 一致只能排除结构错误的一部分，不能证明用户的热区意图；candidate 不得因全绿而自动晋升。

本稿与事实底座唯一需要特别澄清的出入是：SURVEY 本身只证明窗块完整 bbox 等于洞口，派单问题把它泛化到了门；只读复核表明门块完整 bbox 含开启扇。除此之外，复核数字与 SURVEY 一致。
