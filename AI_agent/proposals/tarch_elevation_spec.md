# 天正命名立面处理细稿

> 日期：2026-07-24  
> 性质：bounded feature spec；累计式、自包含；只设计，不含实现  
> 适用主线：天正真实建筑 DXF → 天正转换器 → GT v3 manifest / candidate GT → render / overlay  
> 状态标记：`[S]` = 本稿建议直接采纳；`[M]` = 留主控裁决，不得由施工者自行猜定

## 0. 裁决摘要

### 0.1 本批要交付的能力

[S] 本批只处理**有视图框、框内有唯一且受 request 绑定的命名立面**。立面名称给出 `facade_family`；不做按几何猜 North/South/East/West 的 C2.1 matcher，也不做无立面时的 assumed-z。

[S] 一次成功转换必须形成完整链：

```text
request 中的命名立面 intent
  → 框 / 标题 / 楼层 datum / 轴映射预检
  → E_WINDOW 窗框 + 门块结构轮廓分组
  → 增广 DXF 中的规范化闭合立面 opening 轮廓
  → 立面 opening 与平面 exterior opening 的唯一链接
  → ElevationViewBindingV1 + ElevationOpeningEvidenceV1
  → 完整 extract_gt_v3（不是 plan-only preflight）
  → 11 个外窗 + 3 个 exterior door 获得 observed z
  → gt_elev.png + 四张 overlay_*_view.png
```

[S] sm24 的完整 v3 立面 scope 还会覆盖 3 个平面 exterior door。现有 GT v3 完备性规则要求相关 view 中的所有 opening 都有 elevation evidence，不能只发窗而让门静默 `z=null`。因此本批包含一个**仅用于闭合现有 v3 契约的窄门分支**：把 5 个 `E_WINDOW/INSERT` 确定性合成 3 个 exterior-door 证据组。7 个 interior door 继续 INFO 排除，不进入 GT。

[S] 任何以下情况都阻断候选 GT：

- 立面标题与 request 的 exact named binding 不一致；
- z 没有句柄绑定的楼层 datum；
- datum、轴比例、offset 或有向 along 端点锚不自洽；
- 窗框不能唯一分组为合法矩形；
- 门块定义漂移、结构轮廓不唯一或合并后不是合法矩形；
- 立面 opening 与平面 exterior opening 无候选、全局多解或有落单；
- v3 完整提取、完整校验、canonical reload 任一步失败；
- 要求交付 overlay 时，raster hash / affine / view binding 不完整。

### 0.2 明确不做

[S] 本批不做：

- C2.1 未命名立面 matcher；
- 用窗列、外包宽度或文件顺序猜 facade；
- 缺立面时按知识表补 sill/head；
- 把相邻窗、同层多数窗高或“常见窗台 1m”复制给无证据窗；
- 任意旋转建筑、true-north/site-plan 归向；
- section、detail、局部立面、内院立面；
- 修改 v2 legacy 的数据语义或默认 scorer；
- 由 execution / reading / correction / gate① import 转换器。

### 0.3 本稿最重要的纪律

[S] `z_interval` 只有一条 observed 来源：

```text
源 DXF opening 几何
  × request 声明且由 floor-datum 句柄复核的 source→world-z affine
```

没有 datum 就没有 z；不能退回图框底、窗台标注、最小 y、相邻窗、楼层默认或 assumed knowledge。

---

## 1. 已核实的事实底座

### 1.1 现有转换器缺口

[S] 当前生产代码的事实：

- `TarchConversionRequestV1.elevation_views` 和 `ElevationViewIntentV1` 已声明；
- `tarch_normalize._build_manifest` 只构造一个 plan view，并写 `"views": [pv]`；
- `request.elevation_views` 在转换生产路径从未被读取；
- `_run_g9_v3_preflight` 只跑 `inspect_extraction_inputs` 与 `extract_plan_geometry`，没有跑 `extract_gt_v3`；
- manifest 的 `raster_overlays` 固定为空。

这是 D8“声明字段不参与计算”在立面路径上的实例。修复必须有一条活锁：改变、删掉或篡改 `request.elevation_views` 后，manifest / GT 必须随之变化或明确 BLOCK，不能仍全绿。

### 1.2 sm24 源图事实

[S] `logs/experiments/2026-07-24_sm24_gt_review/source.dxf` 已核实：

- `edge` 层有 5 个闭合框：`1f平面图`、`北立面`、`南立面`、`西立面`、`东立面`；
- 每框内恰一个标题；
- 四立面轮廓地面 source y 均约为 `5231.311185586`，屋顶约为 `9731.311185586`；
- `E_WINDOW` 有 44 个 LINE + 5 个 INSERT；
- 44 条 LINE 恰为 11 个四线窗框；
- 5 个 INSERT 的受校验结构轮廓按相接关系组成 3 个 facade door：
  北 2 块合 1 门、南 1 块为 1 门、东 2 块合 1 门；
- 这 5 个 INSERT 均引用块 `$EWDLib$00000614`；块定义中 `LWPOLYLINE`
  handle `112` 是唯一的闭合四边外轮廓，local bbox 为
  `[0,900]×[0,2400]`；handle `11C` 是 CIRCLE，另有内部门扇/装饰线；
- `11C` 这次恰好落在 `112` 内，故 raw virtual bbox 未被撑大；这只是样本侥幸，
  不能把整个 INSERT 的 virtual bbox 当结构门框或 z 证据；
- 平面 GT opening 候选为 11 个 exterior window + 3 个 exterior door；另有 7 个 interior door 已由转换器 INFO 排除；
- 立面窗几何经真实 datum 映射后为：
  - 普通窗 `z=[1.0, 2.8]`；
  - 大窗 `z=[1.0, 3.4]`；
  - 门图元为 `z=[0.2, 2.6]`。

最后一项只是样本观测，不是可烤入算法的常量。

[S] 四面 opening 布局的镜像核验结果：

- North、West、East 的 typed opening 集均不关于 facade 中点对称；
- South 的两扇 window interval 恰为 `[0.54,2.04]` 与 `[7.96,9.46]`，
  window 子集严格镜像对称；
- South 的 door 略偏心，故 typed 全集不严格对称。

因此 opening assignment 不能承担 along 方向证明：只看 South 窗时，写反 sign
仍可得到同一 interval 集并静默换窗。方向必须由与 opening 布局无关的有向 datum
端点锚先行证明。

### 1.3 sm21 交付形态

[S] `case_tests/test_baseline/gt/sm21_anchor` 是 legacy v2，但它钉住了用户期望的交付外形：

- `gt.json` 的每扇窗有沿墙起点、宽度、sill、head；
- `renders/gt_elev.png`；
- `renders/overlay_{East,North,South,West}_view.png`；
- 平面 overlay 另存，不与四张立面 overlay 混名。

本批不复制 sm21 v2 schema，只用 v3 的：

```text
opening.world_along_interval
opening.z_interval
opening.source_refs(role="opening_elevation")
boundary_segment.projection_surface_keys
source.views[kind="elevation"]
```

达到等价的可读交付。

### 1.4 对现有 v3 立面消费链的实测

[S] 已对 sm24 做过两条真实内存 / 临时目录验证：

1. 直接把原始四线组作为 `grouped_line_bbox` 交给现有 v3：
   - 11 组中 6 组报 `dxf_opening_grouped_line_invalid`；
   - 原因是源 LINE 端点存在约 `1e-11` native 的浮点毛刺，而 v3 的 grouped-line polygonize 不先走转换器量化。
2. 转换器先生成单个闭合 `LWPOLYLINE` 轮廓，再以 `closed_outline_bbox` 交给 v3：
   - 11 个 window + 3 个 exterior door 全部匹配；
   - `extract_gt_v3`、`validate_gt_v3`、canonical reload 全通过；
   - 14/14 opening 均得到真实 `z_interval`。

[S] 因此本批不把原始 E_WINDOW LINE 直接塞进 manifest。源 LINE 仍是证据；manifest 绑定的是增广 DXF 中的规范化闭合轮廓，source-map 反指原 LINE / INSERT。

[S] 另有一个已确证的 v3 缺口：`_assign_elevation` 当前不检查
`evidence.kind == opening.kind`。`kind` 字段声明了却不参与候选计算，属于另一处 D8。施工范围必须包含这一行语义级修复及必红测试。

---

## 2. 输入契约

### 2.1 request 版本

[S] 新请求使用 `request_version=3`。原因是：

- `ElevationViewIntentV1` 从“有字段但无足够证据”升级为可实际计算；
- raster overlay 不能继续只存 ID；
- 新字段必须进入 request canonical hash；
- 不能让旧 v1/v2 请求在未补 datum 的情况下突然产生 z。

旧 v1/v2 仍按原语义解析：可以无 elevation，不能由默认值制造 elevation。

### 2.2 命名立面 intent

[S] `ElevationViewIntentV1` 至少扩成以下语义；字段名可在施工时按现有命名风格微调，但信息量不得减少：

```text
id                         StableId
binding_source             Literal["named_title"]
frame_title                HumanLabel
frame_entity               EntityLocatorV1
title_entity               EntityLocatorV1
floor_ids                  sorted unique floor IDs
facade_family              North | South | East | West
clip_box_dxf               exact frame bbox
world_along_from_source_m  request-side native-DXF → world-m Affine1D
world_z_from_source_m      request-side native-DXF → world-m Affine1D
floor_datums               non-empty list[ElevationFloorDatumIntentV1]
window_selector            TarchEntitySelectorV1
door_selector              TarchEntitySelectorV1 | None
view_kind                  Literal["full"] in this batch
segment_scope_mode         Literal["all_family_segments"] in this batch
```

[S] 当前批只接受 `binding_source="named_title"`。字段使用 discriminator，未来 C2.1 可增加 `matched_sidecar` variant；不得把“所有 elevation 永远必须命名”写进下游 GT manifest schema。

### 2.3 标题到 facade 的确定绑定

[S] `TarchDialectRulesV1` 增加 request-hash-bound 的 exact title map，例如：

```text
"北立面" → "North"
"南立面" → "South"
"东立面" → "East"
"西立面" → "West"
```

只允许 Unicode NFC 与首尾空白规范化；不做包含匹配、编辑距离、方位词抽取或“北立面图≈北立面”的隐式别名。要支持别名，必须在 request map 中逐项列出。

[S] 预检必须同时验证：

- `frame_entity` 是 `edge` selector 命中的唯一闭合正交框；
- 它的 bbox 在 `tau_node` 内等于 `clip_box_dxf`；
- `title_entity` 位于框内且框内没有第二个标题；
- 标题 exact 等于 `frame_title`；
- title map 的结果 exact 等于 `facade_family`；
- 同一 request 内同一 full facade/floor 不能有两个竞争 view。

因此 facade 来自明确图名绑定，不来自窗口位置或框排序。

### 2.4 request-side affine 的单位口径

[S] 现有 plan intent 的实际口径是“DXF native coordinate → world metre”，而 v3 manifest 的口径是“source metre → world metre”。立面必须显式沿用同一换算，禁止再出现双重缩放：

```text
request_scale  = ±metres_per_unit
manifest_scale = request_scale / metres_per_unit = ±1
offset         = world metre；request 与 manifest 相同
```

[S] request validator 必须要求两个 elevation scale 的绝对值都 exact 等于 `metres_per_unit`，source axes 不同；converter emit 后置条件与构造测试必须要求 manifest scale exact 为 `±1`。任意二次缩放、shear 或 `scale=0` BLOCK。本批不借机扩大为“所有外部手写 manifest 的 affine 全仓收紧”。

### 2.5 z datum

[S] 新增 `ElevationFloorDatumIntentV1`，最小语义为：

```text
floor_id       已声明 floor
entity         精确 handle/subentity locator
datum_kind     Literal["floor_line"]
world_along_lo_source_endpoint
               Literal["start","end"]；该有向端必须映射到 plan 投影 lo
```

converter 从实体本身读取 source coordinate，不允许 request 再抄一个可漂移的 source y 数。

[S] datum 判据：

1. locator 在该 view clip 内唯一命中 LINE 或无 bulge polyline 子段；
2. datum 段沿 `world_along_from_source_m.source_axis` 延伸；
3. datum 在 z source axis 上为常量；
4. 非零长；
5. full view 中，映射后的 datum along interval 必须覆盖该 facade 的完整 plan projection interval；
6. 在对 interval 排序前，`world_along_lo_source_endpoint` 指定的 DXF 有向端点
   必须映射到 plan facade projection 的 `lo`，另一端必须映射到 `hi`；
7. 由该 datum 与 `floor.z_floor_m` 重算：

   ```text
   z_offset = floor.z_floor_m - source_datum_native × request_z_scale
   ```

8. 重算 offset 必须 exact 等于 request 中的 z affine offset；多个 datum 必须推出同一 offset；
9. 每个 opening 的 z 区间必须完整落入 `floor_ids` 中恰一个 floor 的
   `[z_floor_m, z_floor_m + ceiling_height_m]`。

[S] 单层 sm24 的 datum 证据为各立面地面轮廓线，而不是“框内最低 y”：

| facade | source datum handle | 映射到 world-along `lo` 的 source 端 | datum 绑定到 |
|---|---:|---|---|
| North | `125` | `start` | `F1.z_floor_m = 0` |
| South | `102` | `start` | `F1.z_floor_m = 0` |
| West | `144` | `end` | `F1.z_floor_m = 0` |
| East | `12F` | `end` | `F1.z_floor_m = 0` |

这些 handle 是 sm24 fixture 证据，不是通用常量。

[S] sm24 的地面线本身没有机器可读的“±0.000”文字。converter 能证明 locator
确实是一条 full-span 水平轮廓、它与 plan/floor/opening 全链自洽，却不能从无标签几何
中证明“这条线在人类语义上就是 1F datum”。因此 exact datum handle 是本 feature 的
受信非机器输入边界，并必须出现在 review overlay / report 中供人复核。若将来要求把
这层人信任也机器化，输入图必须新增可定位的 elevation marker / floor-level 标注；
不得在本批用最低线启发式冒充证明。

[S] 禁止的 z 基准：

- view clip 的 ymin/ymax；
- 框内最低 structural entity；
- 最低窗边；
- `PUB_DIM` 中看起来像 1000/4500 的数字；
- “天正通常从 0 画”；
- 相邻 view 或相邻窗复制；
- request 未绑定的人工 offset。

### 2.6 along 映射

[S] canonical world-along 延用 v3 既有口径：

- North / South：world x；
- East / West：world y；
- interval 总是升序；
- source 图是否镜像由 affine scale 的正负表达，不按 facade 名硬编码镜像。

[S] full-view datum 线同时提供 along span 复核。映射后的升序 interval 必须等于
plan facade 的投影 interval，但 span 相等只证明尺度，不证明方向；“靠逐窗失败
暴露 sign”不得作为 gate。

[S] 方向 gate 必须使用 §2.5 的有向 datum 端点：

```text
source datum 指定端点
  --未排序的 world_along_from_source_m-->
plan facade projection.lo

source datum 另一端
  --未排序的 world_along_from_source_m-->
plan facade projection.hi
```

该锚来自 DXF LINE 的 `start/end`（polyline 子段则来自有向顶点顺序）和 plan
facade 投影端点，不引用任何 window/door。即使开窗完全中心对称，sign 写反且同步
改 offset 以维持相同升序 span，两个端点也会对调并在 E1 BLOCK。不得自动交换
`start/end`、自动改 sign，亦不得尝试“哪个方向 assignment cost 更小就选哪个”。

sm24 的已核实 intent 结果是 South/East 正向、North/West 反向；这只是该 request 的显式事实，不是转换器全局规则。

### 2.7 opening selector

[S] sm24 命名立面 intent 使用两个明确 selector：

- `window_selector = {entity_types:["LINE"], layers:["E_WINDOW"]}`；
- `door_selector = {entity_types:["INSERT"], layers:["E_WINDOW"]}`，并由 request dialect
  逐个列出的 exact elevation-door block name 分类，不做 prefix 猜测。

窗和门不能因同层名而混成一类。未知 INSERT、LINE 以外实体、selector 命中但分类不了的构件均 BLOCK。

[S] `TarchDialectRulesV1` 还必须为每个准入的 elevation-door block 给出
request-hash-bound 的 `ElevationDoorBlockRuleV1`：

```text
block_name_exact
block_definition_sha256
entity_roles:
  - BlockEntityLocatorV1(block_name, entity_handle)
    role = structural_outline | nonstructural_detail
```

角色清单必须穷尽该 block definition 的全部直接实体，handle 不得重复或漏列。
`structural_outline` 本批只准一个闭合、无 bulge、四边四角的正交
LWPOLYLINE；LINE 拼框、嵌套 INSERT、ARC/CIRCLE/ELLIPSE、TEXT/MTEXT/ATTRIB、
HATCH、SPLINE 均不得担任结构轮廓。`nonstructural_detail` 可包含门扇、开启弧、
五金圆、注记和装饰，但永远不参与 along/z 极值。

[S] sm24 的 exact 规则把 `$EWDLib$00000614` 的 `112` 标为
`structural_outline`，`113`–`11F`（含 CIRCLE `11C`）全部显式标为
`nonstructural_detail`。块定义新增、删除、换 handle、几何变化或出现未分类实体，
即使顶层 source hash 已随 fixture 更新，仍以 block-definition drift BLOCK；只有
request 显式更新 fingerprint 与穷尽角色清单后才可重新验收。这是与 datum handle
相同的人信任输入边界，不由“最大 bbox 看起来像门”替代。

[S] `block_definition_sha256` 的 canonical preimage 固定为：

```text
block exact name
block base point
按 entity handle 排序的全部直接实体：
  handle + DXF type + layer + 几何/文字/块引用/显示相关 canonical tags
```

排除 owner pointer、文件写入时间等非语义容器噪声，但不能排除 entity handle、
CIRCLE radius、TEXT content/placement、polyline bulge 或任何会改变 virtual
geometry 的 tag。canonical number/string 规则复用 request hash 规则。这样新增一个
撑 bbox 的注记一定改变 fingerprint，同时同一 block 的迭代顺序不影响 hash。

### 2.8 raster overlay intent

[S] 当前 `request.raster_overlays: list[StableId]` 不足以构造
`RasterOverlayBindingV1`。request v3 将其升级为 typed binding：

```text
id
source_label          basename，例如 North_view.png
source_sha256
view_id               必须命中 plan/elevation intent id
pixel_to_source_m     pixel → source-m Affine2D
calibration_controls  至少 3 个不共线的 hash-bound 控制点
```

[S] `pixel_to_source_m` 必须来自外部、hash-bound 的 raster calibration / rasterization 事实，不在转换器里通过图像边缘启发式猜。转换器只校验：

- basename 与显式 raster root；
- hash；
- affine 非奇异；
- 每个 control 的 pixel 点经 affine 后等于其 exact DXF
  `entity + endpoint/vertex` source 点，残差不超过既有 raster calibration tolerance；
- elevation controls 必须包含 floor datum 的有向 lo、hi 两端和一个 z 不同的
  frame/structural 点，三点不共线；
- control 的 lo/hi 角色必须与 §2.5 的有向端点锚一致；
- 反投影的 facade envelope / opening 四角均在图内；
- 一个 view 最多一个 raster binding。

只检查“非奇异 + 四角在图内”不足以证明 raster 没镜像：对称立面可能仍全在图内。
不得用图像边缘、窗位或 OCR 自动交换 raster 方向；有向 controls 不成立则 overlay
交付门 BLOCK。

为得到目标文件名，sm24 elevation view id 固定为
`North_view`、`South_view`、`East_view`、`West_view`；writer 自然产
`overlay_<view-id>.png`。

---

## 3. 立面处理流水线

### 3.1 时序

[S] 在现有 plan S0–S8 全部通过后、最终 augmented DXF hash / manifest hash 计算前，运行 elevation 子流水线：

```text
E0 named-view preflight
E1 datum + affine verification
E2 raw window/door grouping
E3 raw group → normalized closed outline
E4 facade/floor/along pairing with plan exterior openings
E5 append elevation outlines + source-map
E6 build complete manifest
E7 full extract_gt_v3 + postcondition
E8 render + overlay review bundle
```

[S] 所有 `GTV3_*` 实体写完并关闭 DXF 后，才计算 augmented DXF sha256；之后才计算 manifest hash。不能先 hash 再追加 elevation outline。

### 3.2 E0：框、标题与成员归属

[S] 仅以实体几何中心位于 clip 严格内部作为 selector 成员初筛；实体触碰框边或跨框为 BLOCK，沿用 v3 的“不在边界上猜归属”纪律。

[S] 不按模型空间距离聚类 view。frame handle + exact clip + exact title 是唯一 view membership 入口。

### 3.3 E1：datum、轴与 facade span

[S] 先验证 datum，再读取 opening。datum 失败时不得继续算“看起来合理”的相对窗高。

[S] full view 的 source along 总 span映射到 plan facade 后必须一致；差异只允许使用已登记的 `dxf_node_join_tolerance_m`，不得新造“立面宽度容差”。

[S] E1 必须分别校验“无向 span”和“有向端点”：

1. source datum 两端映射后的升序 span 等于 plan facade projection span；
2. request 指定的 `world_along_lo_source_endpoint` 在**排序前**映射到 plan `lo`；
3. 另一端在排序前映射到 plan `hi`；
4. 多 floor datum 各自独立满足 1–3，且推出相同 along affine；
5. 任何端点互换只报 `tarch_elevation_along_direction_mismatch`，不进入 E2。

opening interval、assignment cost 和 raster 像素都不能反向决定或修正 E1。

### 3.4 E2：四线窗框分组

[S] window selector 命中的 LINE 按以下步骤处理：

1. source 端点先走转换器既有量化 `q = tau_node / 10`；
2. 每条线必须为量化后非零、正交线；
3. 以量化后共享端点建无向图；
4. 每个 connected component 独立 polygonize；
5. 合法 component 必须：
   - 恰 4 条边；
   - 恰 4 个角；
   - 零 dangle / cut / invalid；
   - 恰一个正面积矩形 face；
   - 两个 source axes 上均有正宽；
6. component 之间不得共享边、共享角或相交。

[S] 不使用“每四条排序一组”、最近邻、bbox 重叠或窗宽先验。一个 component 有内部分格线、缺边、多余线、斜线或连到另一扇窗时 BLOCK；未来若要支持 mullion，另加显式 outer-outline selector / override，不在本批猜。

[S] sm24 的 44 LINE 必须得到 11 个 component，按 facade 为：

```text
North 1 / South 2 / West 5 / East 3
```

这个计数是 anchor 验收值，不是生产代码的全局固定数。

### 3.5 E2b：外门最小闭包

[S] door selector 命中的 INSERT 只接受 dialect exact 命中的
`ElevationDoorBlockRuleV1`。**禁止使用整个 INSERT 的 raw virtual bbox 产
along/z**。每个 INSERT 的证据抽取固定为：

1. 重算 block definition canonical fingerprint，必须 exact 等于 request；
2. 对 block 内全部直接实体做穷尽角色对账；未分类、重复分类、locator 漂移均 BLOCK；
3. 只读取 `structural_outline`，在 block-local 坐标验证：
   - 恰 1 个闭合、无 bulge、正面积 face；
   - 恰 4 条非零正交边、4 个角、零 dangle/cut/hole/self-intersection；
   - 两个 local axis 上均有正宽；
4. 应用该 INSERT 的完整变换；变换后仍须是 view source along/z 两轴对齐的四边
   矩形，任意 rotation/shear/退化使其不再对齐即 BLOCK；
5. 仅从这个受校验的 transformed structural rectangle 取
   `source_along_interval/source_z_interval`；
6. `nonstructural_detail` 只进入 excluded-entity audit，不进入 extrema、union 或
   normalized outline。

[S] 整块 virtual geometry/bbox 仍可计算，但只作诊断审计：

```text
raw_virtual_bbox
structural_bbox
excluded_entity_handles/types
```

两 bbox 不等不是取较大者的理由；已由 exact 角色表准入的 CIRCLE/TEXT 即使伸到
结构框外，也应被确定性排除且结构 z 不变。若块定义变了但 request 没显式重签角色
表，则在几何抽取前 BLOCK。

[S] 多个 INSERT 只在 transformed structural rectangle 上分组。一个候选门组必须：

- 每个 module 的 source z interval 在 `tau_node` 内相同；
- 沿 along 正宽、量化后只允许相接；正面积重叠、缺口或 T 形拼接均 BLOCK；
- polygon union 恰一个无洞 face；
- dissolve 共线内缝后，union 外边界恰 4 边 4 角、沿 along/z 轴对齐；
- union 的四个 extrema 均来自已选 structural outline 顶点；
- 合并后能唯一链接到一个同 facade、同 floor 的平面 exterior door。

因此单模块门和双模块门最终接受同一矩形合法性，不存在“窗验形、门只看 bbox”的
旁路。

[S] 分组不是单靠“相接就合并”：候选组与 plan exterior door 做同一全局唯一分配，组法多解即 BLOCK。sm24 北/东双块合门、南单块成门。

[S] 7 个 interior door 不进入 exterior candidate set，也不要求 elevation evidence。反向规则更严格：任何被 selector 选中的 elevation door group 若对不上 exterior door，不得声称“可能是内门”后丢弃，必须 BLOCK 或通过 request selector 明确排除。

### 3.6 E3：规范化 closed outline

[S] 每个通过分组的 window / exterior door 在增广 DXF 写一条闭合、无 bulge、正交 LWPOLYLINE：

```text
layer = GTV3_ELEV_OPENING
window geometry = 量化后四线矩形的 exact boundary
door geometry   = 量化后 structural-outline union 的 exact outer boundary
```

[S] 这是证据规范化，不是 z 修补：

- 四边必须分别由已验证 structural evidence 的真实极值给出；
- 不扩大、不裁切、不套默认尺寸；
- canonical geometry 仍处于 source DXF coordinate；
- window source-map 保存所有原 LINE；
- door source-map 保存原 INSERT、block-definition fingerprint、结构 outline handle
  和被排除 detail inventory；raw virtual bbox 不进入 provenance 计算链。

[S] window 与 door 共用同一个 `NormalizedElevationOpening` 后置条件。保存并重开
augmented DXF 后，每个 emitted outline 必须再次满足闭合、4 边、4 角、无 bulge、
正交、正面积，且其 along/z interval 在 `tau_node` 内 exact 等于内存中的结构证据。
两类任一失败均 BLOCK，不能只重验 generated handle 存在。

[S] manifest 对这些生成实体使用：

```text
geometry_mode = "closed_outline_bbox"
entities = [generated EntityLocatorV1]
```

本批不修 v3 grouped-line snap；避免 converter 和 extractor 各维护一套不同 snap。必须保留一个真实 sm24 必红/转绿夹具，证明生成轮廓是必要消费接缝而非无用复制。

### 3.7 分支强度对账

[S] E2/E3 之后不得再区分“窗严、门松”的成功标准：

| invariant | window source branch | door source branch | shared postcondition |
|---|---|---|---|
| 结构来源 | 4 条 exact raw LINE | exact block role map 中的 outline | 不取注记/装饰 bbox |
| 形状 | 4 边 4 角唯一矩形 | 每 module 与 union 均 4 边 4 角唯一矩形 | emitted outline 重开复验 |
| along/z | 结构边真实极值 | 结构 outline/union 真实极值 | 同一 affine、floor containment |
| pairing | facade+floor+kind+along | facade+floor+kind+along | 同一全局唯一分配 |
| provenance | 4 LINE handles | INSERT + block outline + excluded inventory | 同一 opening_id，缺项 BLOCK |

[S] 同理，几何方向与 raster 方向都必须有有向证据：前者用 datum start/end，
后者用 calibration lo/hi controls。任何分支若只有“总 span 一致”“不越界”或
“最终看起来能匹配”而没有方向锚，一律不能宣称通过强校验。

---

## 4. 立面 opening ↔ 平面 exterior opening 链接

### 4.1 平面候选的 facade 与 along

[S] 不能用 plan block 的 source axis 名直接当 facade。对每个已由 S3/S4 判为 exterior 的 `ResolvedOpening`：

1. 用 plan affine 把 opening rectangle 转为 world；
2. 找到它所在的 footprint outer-skin face；
3. 由该 face 的 world outward normal 得到 facade family；
4. North/South 取 world-x interval，East/West 取 world-y interval；
5. 记录 kind、floor、opening_id、world interval。

face 必须唯一；无 face或多个 face均 BLOCK。该结果之后还要与 v3 最终 `boundary_segment_id/facade_family` 复核。

### 4.2 立面证据 tuple

[S] 每个 normalized elevation group 在链接前形成：

```text
(evidence_id, view_id, facade_family, floor_id, kind,
 world_along_interval, world_z_interval,
 raw_source_handles, structural_source_handles)
```

floor_id 由 z interval 完整落入恰一 floor 得到，不从 view 列表第一项取。
window 的两组 handle 相同；door 的 raw source 是 INSERT，structural source 是
exact block-definition outline，不能把 raw virtual bbox 填进结构证据位。

### 4.3 候选判据

[S] evidence `e` 与 plan opening `p` 只有同时满足以下条件才是候选：

- `e.facade_family == p.facade_family`；
- `e.floor_id == p.floor_id`；
- `e.kind == p.kind`；
- p 的 host segment 在该 view scope 内；
- p 与 Vg visible interval、view coverage 有正宽交；
- endpoint cost

  ```text
  max(|e.lo-p.lo|, |e.hi-p.hi|)
  ```

  不超过现有 `elevation_match_max_distance_m`。

不能按中心点、宽度近似、窗序号或 source handle 字典序单独决定。

### 4.4 唯一全局分配

[S] 每个 view / floor / kind 分区内做一对一全局最小总代价 assignment，规则与 v3 §10.7 同构：

- 每个 evidence 恰好一个 plan opening；
- 每个该 view 中 relevant 的 plan opening 恰好一个 evidence；
- 无完整 assignment → BLOCK；
- 最优与次优总成本差 `<= elevation_match_tie_epsilon_m` → BLOCK；
- 不以 lexical ID 打破语义平局。

一个 evidence 有多个初始候选不自动等于歧义；只有全局求解后仍多最优才是歧义。这样既 fail-closed，又与现有 v3 消费模型一致。

### 4.5 完备性集合

[S] 对 sm24 四个 full elevation，relevant 集合应为全部 14 个 exterior openings：

```text
11 window + 3 exterior door
```

核心验收另单列：

```text
all exterior windows have z_interval != null
window count with z == 11
```

[S] 如果未来某 named view 不是 full，只有 manifest scope + Vg coverage 判为 relevant 的 opening 才要求 evidence；不能把“sm24 恰四张全立面”烤成 GT schema 的固定四面假设。

### 4.6 最小冲突集

[S] BLOCK 诊断至少带：

- view id、facade、floor、kind；
- 相关 evidence_id / opening_id；
- 两侧 intervals；
- 每条候选 cost；
- tolerance / tie epsilon；
- raw source handles；
- `no_candidate | unmatched_plan | unmatched_evidence | ambiguous_assignment | kind_mismatch` 原因。

多解时只报构成第一、第二最优差异的最小 alternating component，不倾倒全图所有 opening。

---

## 5. Manifest emit

### 5.1 `ElevationViewBindingV1`

[S] 每个通过的 named elevation intent 生成一个 binding：

| manifest 字段 | 来源 |
|---|---|
| `kind` | `"elevation"` |
| `id` | intent.id，如 `North_view` |
| `floor_ids` | intent，排序唯一 |
| `projection_surface_key` | 稳定唯一值，建议 `ps_<view-id>` |
| `facade_family` | exact named-title binding |
| `view_kind` | 本批 `"full"` |
| `world_along_coverage` | full 时 `null` |
| `direction_semantics` | 本批 `"building_axis"` |
| `azimuth_deg` | building-axis 时 `null` |
| `clip_box_dxf` | 已核框的 exact bbox |
| `world_along_from_source_m` | request scale 除以 mpu 后的 source-m affine |
| `world_z_from_source_m` | datum 复核后的 source-m affine |
| `segment_scope_mode` | 本批 `"all_family_segments"` |
| `boundary_entities` | full 时空 |
| `opening_entities` | 本 view 的 normalized evidence groups |

[S] `projection_surface_key` 不等于 facade 名；它代表一个 source projection view。未来同 family 多 partial view 时仍可各有 key。

### 5.2 `ElevationOpeningEvidenceV1`

[S] 每个 normalized outline 生成：

```text
evidence_id   全 manifest 唯一、由 view id + raw minimum handle 稳定派生
kind          window | door
geometry_mode "closed_outline_bbox"
entities      仅该生成 LWPOLYLINE locator
```

当前 wire 不携带 plan `opening_id`。converter 内部 pairing ledger 必须保留
`evidence_id → opening_id`，供完整提取后独立复核；不得仅因 v3 又会匹配一次就省掉 converter 链接。

### 5.3 views 列表

[S] `_build_manifest` 从：

```text
"views": [pv]
```

改为：

```text
"views": sorted(plan_bindings + elevation_bindings)
```

排序规则固定为 plan 在前，再按 elevation view id lexical；hash 与输出不得依赖 request 列表顺序或 DXF entity iteration 顺序。

### 5.4 source-map

[S] 每个 `GTV3_ELEV_OPENING` handle 必须有 source-map entry：

- `view_id` = elevation view；
- `floor_id` = 链接所得 floor；
- `semantic_role` = opening；
- operation 增加 `elevation_opening_outline`；
- `opening_id` = 已链接 plan opening id；
- source refs：
  - window：4 个原 `E_WINDOW/LINE` handle；
  - door：1 或 2 个原 `E_WINDOW/INSERT` handle，加每个实例实际使用的
    block-definition structural outline handle；
- door provenance 另存 block definition fingerprint、实例变换以及
  nonstructural excluded inventory；
- canonical geometry 记录 world along + z rectangle。

plan opening 的 source-map 与 elevation opening 的 source-map 是两条来源记录，共享同一个 opening_id，不互相覆盖。

### 5.5 raster overlays

[S] typed raster intents 经 hash、三点 calibration、有向 lo/hi control、图内范围
校验后 emit 为 `RasterOverlayBindingV1`。sm24 acceptance profile 必须有四个
elevation raster binding；否则几何 GT 可以作为内部 candidate 构建，但“与 sm21
对齐的交付”门不得通过。control evidence 留在 conversion report/source-map；
不得因为现有 manifest wire 不承载 control 就跳过 converter 侧验证。

### 5.6 hash 顺序

[S] 固定顺序：

1. 复制原 DXF；
2. 写 plan `GTV3_*`；
3. 写 `GTV3_ELEV_OPENING`；
4. 保存并重新打开一次 augmented DXF；
5. 按 emitted handles 对 window/door 共用的闭合矩形后置条件与结构 interval 重验；
6. 计算 augmented DXF sha256；
7. 构造 complete manifest；
8. 计算 manifest sha256；
9. full extraction。

任何先算 hash 后补实体的实现都属失败。

---

## 6. 下游 GT v3 消费范围

### 6.1 保留的现有能力

[S] 继续复用现有：

- elevation view → boundary segment projection key 绑定；
- `_elevation_geometry` 的 along/z affine；
- floor containment；
- per-view global assignment；
- multi-view z exact disagreement check；
- GT validator 的 relevant-view 完备性；
- canonical round-trip。

### 6.2 必须修的 v3 缺口

[S] `_assign_elevation` 的候选谓词增加：

```text
evidence.kind == opening.kind
```

并加负锁：把一个真实 window evidence 的 kind 篡改为 door 时，即使 along interval 完全相同，也必须 `elevation_opening_no_candidate` 或稳定的 kind-mismatch 错误，不能生成 GT。

这是本批唯一要求修改的 v3 匹配语义。

### 6.3 不在 v3 修的真实图毛刺

[S] `grouped_line_bbox` 对 sm24 原 LINE 毛刺失败，处理责任放在 converter 的既有量化 / normalized-outline 层；本批不向 v3 再塞一个隐式 snap，也不放松 grouped-line 的零残线契约。

### 6.4 G9 必须升级为完整提取

[S] 当前 G9 的 plan-only 行为删除。新的 G9 成功条件是一次真实：

```text
inspect_extraction_inputs
extract_gt_v3
  └─ 内含 validate_gt_v3
  └─ canonical serialize/reload
converter pairing-ledger ↔ GT source_refs postcheck
```

其中任一 `ExtractionError` 原码进入 `tarch_v3_precondition.context.v3_code`，不吞、不改写成 PASS。

[S] 必红 mutation：让 `extract_plan_geometry` 正常、只在 elevation assignment 或最终 GT validator 抛错，G9 必须红。它专门防止“G9 预检绿但完整 extraction 红”的旧洞口教训复发。

### 6.5 converter ↔ v3 配对一致性

[S] 完整 GT 产出后，按每个 `opening_elevation` source ref 的 generated handle 反查 evidence，再与 converter pairing ledger 比较：

- view id 相同；
- opening id 相同；
- kind 相同；
- z interval 等于 converter 计算值；
- 每个 relevant pair 恰一组 refs。

不一致 BLOCK。这样 current wire 即使没有显式 `opening_id` 字段，也不会让 converter 预链接变成无人消费的伪检查。

### 6.6 sm24 e2e 后置条件

[S] sm24 anchor 测试至少断言：

- source views = 1 plan + 4 elevation；
- 四个 facade 的 projection key 均出现在正确 boundary segment；
- `len(openings) == 14`；
- 11 个 kind=window 的 `z_interval` 全非空；
- window z 只出现真实的 `[1.0,2.8]` 与 `[1.0,3.4]`；
- 3 个 exterior door 有 source-observed z，不由 floor default 生成；
- door z 只来自受校验的 block structural outline；sm24 CIRCLE `11C` 明确在
  excluded inventory，且不改变 z；
- 每个 opening 有 plan ref；每个 relevant opening 有对应 elevation ref；
- 7 个 interior door 不在 GT；
- canonical reload bytes 与首次输出逐字节一致。

数值断言属于真实 anchor fixture；生产算法不得按这些数字分支。

---

## 7. Render 与 overlay

### 7.1 `gt_elev.png`

[S] 现有 `gt_to_render_model` 已从 v3 `source.views[kind=elevation]` 和
`projection_surface_keys` 生成动态 elevation surface；`render_gt.py` 已固定输出
`gt_elev.png`。

本批不改 render 几何算法，只要求 e2e 证明：

- 不再出现 `NO ELEVATION SOURCE BINDING`；
- 有 4 个 sm24 surface panel；
- 11 个 window box 均按真实 along × z 绘制；
- exterior door 若在 surface 中则按 source-observed z 绘制；
- candidate 未签字前保留 `CANDIDATE — NOT BASELINE`。

### 7.2 四张 v3 overlay

[S] `render_gt_overlay.py` 已能按 manifest affine 反投影 v3 elevation。输入必须是：

- full GT v3；
- 与 GT generator hash 一致的 complete manifest；
- raster root；
- 四个 hash-bound `RasterOverlayBindingV1`。

输出必须恰含：

```text
overlay_East_view.png
overlay_North_view.png
overlay_South_view.png
overlay_West_view.png
```

若同时请求 plan overlay，可另产 `overlay_<plan-view-id>.png`；不影响四张立面验收。

[S] 最终 sm24 bundle 要与 sm21 的目录形态对齐：

```text
gt/gt.json
gt/renders/gt_plan.png
gt/renders/gt_elev.png
gt/renders/overlay_East_view.png
gt/renders/overlay_North_view.png
gt/renders/overlay_South_view.png
gt/renders/overlay_West_view.png
```

现有 v3 overlay writer 要求目标目录不存在，而 `render_gt.py` 会先创建
`renders/`；因此不能串行让两个 CLI 分别“占有”同一目录。bundle 编排必须先在同一 sibling 临时目录生成全部 render/overlay 文件，核对 canonical inventory 后一次原子 rename 为新的 `renders/`。不得先落 `renders/`，再把 overlay 非原子搬入。

### 7.3 overlay fail-closed

[S] 以下均阻断 overlay 交付门：

- raster 缺失、hash 漂移、symlink/路径逃逸；
- view id 不存在或重复 raster binding；
- pixel affine 奇异、三点不共线条件失败或 control residual 超限；
- 有向 lo/hi raster control 对调；
- world opening 四角反投影越界；
- GT manifest hash 不一致；
- sanitize 后输出名碰撞；
- out-dir 已存在。

不得退回 legacy v2 的自动密度框校准来“尽量画一张”。

[S] 上述 atomic bundle packaging 只复用
`build_gt_overlay_images_v3` 的现有投影结果；不要求放松
`write_gt_overlay_images_v3` 的“目标目录已存在即拒绝”安全语义。

### 7.4 人工验收

[S] 用户最终看的是同一 candidate hash 下的：

- `gt_plan.png`；
- `gt_elev.png`；
- 四张 elevation overlay；
- conversion report 中的 view / opening / pairing 摘要。

用户确认前保持 candidate；确认后才走既有签字 / promotion 纪律，不能由 converter 自签 `human_verified`。

[M] G10 acknowledgement 是继续只绑定一个 review-index 文件，还是把
`gt_elev + 四 overlay + plan overlay` 的逐文件 hash 直接扩进 ack wire，由主控在施工 dispatch 前裁定。无论采用哪种 wire，必须绑定**整个 review bundle 的 canonical inventory hash**，不能继续只绑 `overlay_plan.svg` 后宣称立面已审。

---

## 8. 诊断与 gate

### 8.1 新诊断码

[S] 至少补以下稳定码；名字可按 registry 现有风格机械调整，但一义一因：

| code | severity | 条件 |
|---|---|---|
| `tarch_elevation_title_mismatch` | BLOCK | exact title / facade map 不一致 |
| `tarch_elevation_datum_missing` | BLOCK | datum locator 无命中 |
| `tarch_elevation_datum_invalid` | BLOCK | 非合法 floor line / 不覆盖 full span |
| `tarch_elevation_z_transform_mismatch` | BLOCK | datum 推导 offset 与 request 不同 |
| `tarch_elevation_along_direction_mismatch` | BLOCK | datum 有向端点未映射到 plan lo/hi |
| `tarch_elevation_opening_component_invalid` | BLOCK | 窗线组不是唯一矩形 |
| `tarch_elevation_door_block_drift` | BLOCK | 门块 fingerprint / 穷尽角色表漂移 |
| `tarch_elevation_door_structure_invalid` | BLOCK | 门结构 outline 或其 union 非唯一合法矩形 |
| `tarch_elevation_normalized_outline_drift` | BLOCK | 重开后 emitted 轮廓与结构 interval 不同 |
| `tarch_elevation_opening_no_candidate` | BLOCK | evidence 或 relevant plan opening 落单 |
| `tarch_elevation_opening_assignment_ambiguous` | BLOCK | 全局多最优 |
| `tarch_elevation_opening_kind_mismatch` | BLOCK | 窗/门跨 kind 候选 |
| `tarch_elevation_pairing_drift` | BLOCK | converter ledger 与 v3 GT refs 不同 |
| `tarch_interior_opening_elevation_not_applicable` | INFO | interior plan opening 无 elevation 义务 |
| `tarch_raster_overlay_unbound` | BLOCK（交付门） | acceptance profile 缺 raster binding |
| `tarch_raster_calibration_invalid` | BLOCK（交付门） | 三点/有向 control 与 affine 不一致 |

所有 BLOCK 必须有 handle 或 source point，满足现有 localizable 纪律。

### 8.2 既有 gate 的扩展

[S] 不另造 G11；扩展既有门的证据：

- G1：四个 named frame、exact title、datum、scale、有向 along 端点锚；
- G3：plan opening + elevation raw group 的分组/分类，以及门块 fingerprint /
  exhaustive roles / structural union；
- G4：exterior 14、interior 7 的适用性对账；
- G9：完整 v3 extraction + pairing postcheck；
- G10：含立面的 review-bundle 签字。

conversion report 的 gate evidence 至少写：

```text
elevation_view_count
window_raw_entity_count
window_group_count
exterior_window_pair_count
exterior_door_pair_count
door_structural_outline_count
door_nonstructural_excluded_count
interior_opening_excluded_count
openings_with_z_count
raster_calibration_control_count
render/overlay inventory hashes
```

### 8.3 失败产物

[S] 几何 BLOCK 时仍应在 staging 留一张本地化 elevation diagnostic SVG/PNG：

- 画 view frame；
- 高亮坏 component 或冲突 opening；
- 标 evidence/opening ID 与 cost；
- 不生成貌似权威的 gt_elev。

失败图是诊断，不是 G10 审核通过物。

---

## 9. 必红夹具与验收矩阵

### 9.1 request / D8

[S]

- 删除一个 `elevation_views` 条目：对应 source view / projection key / overlay 必须消失或 acceptance profile BLOCK；
- 篡改一个 facade title：G1 红；
- 篡改 request elevation affine 但重算 request hash：datum gate 红；
- 旧 v2 request：仍只产 plan，不暗产 elevation。

### 9.2 frame / title

[S]

- frame handle 不存在；
- bbox 相同但 handle 指向第二框；
- 框内 0/2 个标题；
- `北立面图` 未显式列入 alias map却 request 写 `北立面`；
- 两个 full North view 覆盖同 floor；
- entity 跨 frame 边。

全部必须 BLOCK。

### 9.3 z

[S]

- datum 换成屋顶线；
- datum source axis 与 z axis 不符；
- z scale 从 `0.001` 改成 `1.0`；
- offset 平移 0.2m；
- 两个 datum 推出不同 offset；
- 窗框跨楼层；
- 窗 z 高于 ceiling。

不得因最终数值“仍像窗高”而放行。

### 9.4 along 方向

[S]

- South 保持两扇严格对称 window，只把 along sign 写反，并同步改 offset 使升序
  span 仍为 `[0,10]`：有向 datum 端点 gate 红；
- 同一 mutation 即使 window assignment 总成本仍为 0，也不得进入 E2/E4；
- 对调 request 的 lo endpoint 而不改 source LINE：G1 红；
- North/West 的负 sign 与表中端点锚原样：绿；
- raster affine 做水平镜像且所有 opening 仍在图内：有向 calibration control 红。

此组专门证明方向安全不依赖非对称 opening。不能用“sm24 typed 全集不对称”替代
South window-only 必红夹具。

### 9.5 window grouping

[S]

- 原始 sm24 的 `1e-11` 端点毛刺：converter 分组通过，直接 v3 grouped-line 夹具保持红；
- 删除一条边；
- 增加一条对角线；
- 一条线桥接两扇窗；
- component 有五条 mullion；
- 零宽/零高；
- 斜线超 axis tolerance。

只有第一项经 converter 量化后转绿，其余红。

### 9.6 door structure / grouping

[S]

- 原始 sm24：`112` 唯一作为 structural outline，CIRCLE `11C` 在 excluded
  inventory，5 INSERT → 3 合法矩形且 z 为 source-observed `[0.2,2.6]`；
- 在块中加入一个伸出 `112` 上方的 CIRCLE，重算顶层 source hash 但不更新
  block fingerprint / exhaustive role map：`tarch_elevation_door_block_drift` 红；
- 在块中加入一条伸出 `112` 上方的 TEXT/MTEXT，做同样 mutation：同码红；
- 显式重签 fingerprint 并把上述 CIRCLE/TEXT exact handle 标为
  `nonstructural_detail`：结构 interval 与 normalized outline 必须逐字节不变；
- 把 CIRCLE/TEXT 错标为 `structural_outline`：实体类型 gate 红；
- 删除 `112` 一边、给它加 bulge、复制第二个 structural outline：结构 gate 红；
- 两个 module z 不同、正面积重叠、留缝、拼成 T 形：union gate 红；
- raw virtual bbox 被非结构实体撑大但实现仍拿它产 z：anchor 断言红，不能静默得到
  更高 head。

这一组同时覆盖“安全 BLOCK”和“经显式角色表正确排除”两条路径；没有任何夹具允许
raw whole-block bbox 成为 z 来源。

### 9.7 pairing

[S]

- 删一个 elevation window → unmatched plan 红；
- 加一个合法矩形但无 plan window → unmatched evidence 红；
- 平移超过 0.4m → no candidate 红；
- 制造两个等代价 plan opening → ambiguous 红；
- 镜像 sign 写反 → 在 E1 有向端点 gate 红，不等到 assignment 自动翻面；
- 把 window evidence kind 改 door → v3 kind gate 红；
- 只发 11 window、不发 3 relevant exterior door → 完整 GT validator 红；
- 保留 7 interior door 且不发 elevation evidence → 绿；
- 额外选中一个无法链接的 elevation door → 红，不能 INFO 排除。

### 9.8 manifest / source-map

[S]

- duplicate view id、projection key、evidence id；
- elevation 引未知 floor；
- generated outline handle 丢失；
- source-map 少一个 raw handle；
- door source-map 少 structural outline handle、fingerprint 或 excluded inventory；
- emitted door outline 重开后 interval 与 structural union 不同；
- 保存 DXF 后再追加实体但不更新 hash；
- request/entity iteration 顺序打乱。

前七项红；最后一项 canonical manifest / GT bytes 必须不变。

### 9.9 G9

[S]

- plan extraction 绿、elevation assignment 抛错：G9 红；
- assignment 绿、最终 `gt_opening_elevation_evidence_mismatch`：G9 红；
- GT canonical reload 被篡改：G9 红；
- pairing ledger 与 GT refs 换一对：G9 红。

### 9.10 render / overlay

[S]

- `gt_elev` primitive surface 数为 4；
- window box 数为 11；
- 四张 overlay 文件名 exact；
- raster hash 改 1 byte；
- affine 使一个 opening 角越界；
- affine 水平镜像但开窗仍全部在图内；
- 三个 controls 共线或 lo/hi control 对调；
- GT 的 manifest hash 改 1 byte；
- 缺 West raster binding。

前三项绿；后六项交付门红。

### 9.11 隔离与资产纪律

[S]

- import guard 继续证明 execution / reading / correction / gate① 不 import tarch converter；
- converter 只能写 staging；
- candidate writer 不覆盖已有文件；
- 本批测试不得写 `case_tests/test_baseline/gt`、`gt_sources` 或 e2e `case_data`；
- 用户签字前不自动 promotion。

---

## 10. 施工触点

[S] 预计触点，仅作为边界，不是逐行施工指令：

| 文件 | 设计内改动 |
|---|---|
| `src/agent/judge/tarch_converter_schema.py` | request v3、named view/datum 有向端点、door block exact role map、raster controls、诊断码、source-map operation |
| `src/agent/judge/tarch_normalize.py` | E0–E8、door structural-outline extraction/union、generated elevation outlines、complete manifest、full G9 |
| `src/agent/judge/gt_extraction.py` | elevation assignment 加 kind equality |
| `tests/test_tarch_converter_*` | schema、分组、datum 有向锚、door block drift/shape、pairing、gate mutation、sm24 e2e |
| `tests/test_gt_from_dxf.py` | kind-mismatch 必红 |
| `tests/test_gt_overlay.py` / render tests | 四 view overlay 与真实 affine |

[S] 原则上不改：

- GT v3 wire 的 `ElevationViewBindingV1` / `ElevationOpeningEvidenceV1` 字段；
- `GroundTruthV3` opening wire；
- v2 legacy adapter；
- scorer / Va / Vg 的既有语义；
- `render_gt.py` 与 `render_gt_overlay.py` 的核心投影算法。

若施工发现必须改以上“不改”项，先停工回主控，不得借实现便利扩大范围。

---

## 11. 完成定义

[S] 功能施工不能只以 unit tests 绿或 manifest 看起来正确收工。必须同时满足：

1. request v3 的四个 named elevation 真被消费；
2. sm24 原 44 window LINE → 11 个规范化 window outlines；
3. 5 door INSERT 只经 block `112` 结构轮廓 → 3 个 exterior-door outlines；
4. 11 window 与 plan exterior window 一一链接，无 orphan / ambiguity；
5. 四个 datum 的有向端点均绑定 plan lo/hi；South 对称窗 sign mutation 必红；
6. sm24 CIRCLE `11C` 被 exact 排除，门 z 与 raw virtual bbox 无数据依赖；
7. complete manifest 含 1 plan + 4 elevation bindings；
8. G9 真跑 `extract_gt_v3`；
9. 14 opening 全有 source-observed z，其中 11 window 是核心验收；
10. GT 中每个 relevant opening 的 elevation refs 与 converter ledger 一致；
11. `gt_elev.png` 有四个真实 surface，不是 NO-BINDING 占位；
12. 四张 `overlay_{East,North,South,West}_view.png` 经三点有向 calibration，在同一个
    `gt/renders/` 原子 bundle 中产生且不过界；
13. 用户看同 hash review bundle 并签字后，才可锁定 / promotion；
14. 全量测试无 v2、execution、reading、correction 回归。

---

## 12. 为 C2.1 保留的接缝

[S] 本稿特意保留：

- elevation view 数量开放，不在 GT schema 固定四张；
- `binding_source` 是 discriminator，后续可加 matcher sidecar；
- `projection_surface_key` 不等于 facade 名；
- `view_kind/coverage/scope` 继续留在 manifest；
- pairing 输入是候选 facade 集与 canonical along interval，不依赖 DXF 框的左右顺序；
- full-view 有向 anchor 是 intent variant 的证据字段；未来 partial/matched view 可换
  locator 类型，但不得退回由 opening 分布猜方向；
- `z_interval` 仍只有 observed source evidence；assumed-z 继续走未来知识/provenance 通道，不混进 GT observed truth；
- normalized outline 与 source-map 分离，未来可支持 mullion/partial view 而不改 GT opening wire。

[S] C2.1 未来若给出未命名 view，只替换“view → facade 的可信来源”；E1 datum、E2 opening grouping、E3 normalization、E4 pairing、v3 consumption 不应重写。

---

## 13. 待主控裁决

[M] 仅剩一个不影响几何算法的 wire 选择：G10 是升级现有 ack 为“逐文件 hash 列表”，还是新增一个 canonical review-index 文件并让 ack 只绑定 index hash。推荐后者，便于未来动态 view 数量；但施工者必须等主控拍板。

[S] 其余核心设计——datum 句柄及有向端点来源、11 窗分组、门块 exact role map 与
3 外门结构轮廓闭包、全局唯一链接、normalized closed-outline、v3 kind 修复、完整
G9、三点有向 raster binding、四张 overlay——不留施工自由裁量。
