# 带贴图单体建筑：获取工作流

2026-09-18 调研。入口见 [体量输入调研](../textured_mass_route.md)，来源清单见 [sources.md](sources.md)，选样梯度见 [case_ladder.md](case_ladder.md)。

**09-20 复核入口：** [来源/选样复核](../../logs/experiments/2026-09-20_hongkong_material_audit/source_review.md)与[香港转换核查](../../logs/experiments/2026-09-20_hongkong_material_audit/conversion_audit.md)确认：15 栋旧导出只取首网格并丢节点矩阵，全批竖轴错误，两例共丢 62 面；现已按完整 scene 重转并生成四视图，14/15 可由现有观察器读取，余例因源 `alphaMode=BLEND` 遭拒。下方路线判断是 09-18 的研究方案，按此实证修订，不能把旧预览和旧“像素/米”当源质量证据。

本页回答两件事：现有那套「从城市瓦片裁单体」的脚本实际能力有多大、换场景要改多少；以及可选的几条获取路线各自的裁决。

## 定位：开发期摸路，用户自备素材

2026-09-18 用户确认：**当前主要是在开发阶段摸出一条可行的路，产品投入使用后，素材由用户自己去找所需的建筑贴图模型。**

这个定位改变了取舍重点：

- 不需要解决「全球任意建筑都能取到」这个问题。开发只需要**少数几个能稳定拿到、类型有梯度的样本**。
- 但需要给用户一份**可操作的获取指引**——用户会带着各种来源、各种格式的模型进来，Agent 侧的读取能力要能兼容，不能只认一种格式。
- 所以本页的路线裁决按「开发期够不够用」和「将来能不能兼容用户带来的东西」两条线看，不按「能否覆盖全球」打分。

## 现有脚本的真实能力

[prepare_single_building.py](../../../case_tests/textured_mass/prepare_single_building.py)（335 行）做的事：

1. 校验源 GLB 哈希，要求恰好一个已贴图 Trimesh
2. 用瓦片的 `origin_original` 逆变换还原原始本地坐标，`shapely.contains_xy` 按**三角面重心是否落在 footprint.buffer(0.35 m) 内**选面
3. `submesh(repair=False)` 裁剪——**不补洞不修复，产生非闭合结果是必然后果，不是 bug**
4. 按 footprint 中心重定平面原点、按裁剪后最低点设新 y=0
5. `mask_texture_to_selected_faces()` 把图集中未被选中面引用的像素涂灰、`MaxFilter(5)` 留 2 px 边距，JPEG q95 重压缩
6. 导出 GLB 并清除 extras，渲染三张固定机位预览 + footprint 叠图 + 三维查看页
7. 回读校验属性白名单 `{POSITION, NORMAL, TEXCOORD_0}`、面数与贴图 roundtrip

**全程沿用源瓦片既有 UV，没有 UV 重建，没有单位换算，没有朝向对齐**（不做 yaw 校正，方位继承源瓦片）。

真正的「去 SUM 语义标签」发生在上游 [prepare_samples.py](../../logs/experiments/2026-09-10_textured_mass_survey/prepare_samples.py)（第 92–97 行显式白名单重建），本脚本只负责裁剪与图集清理，从不打开带标签 PLY。

### 哪些是人工的

脚本**不含任何建筑识别、自动配准或类型推断逻辑**。以下全部是人工填进 `selection.json` 或写死的常量：

- 建筑 footprint 多边形
- 跨源坐标配准（OSM → EPSG:3879 → 赫尔辛基本地网格的投影与原点平移，**投影计算本身不在代码里，是文档里的成品数字**）
- 用途与层数信息
- 0.35 m 缓冲值
- 预览相机角度

### 实测产物规模

Voimatalo `input.glb`：969,568 字节，12,520 三角面 / 8,242 顶点（从 385,685 面中选出），8192×4096 贴图（未降采样，只遮罩 + 重压缩，保留像素 715,363 / 33,554,432 ≈ 2.1%）。**非闭合**——175 个连通体、3,690 条边界边、零条真正 non-manifold 边。

### 换场景要改多少

| 场景 | 改动量 |
|---|---|
| 同城市同格式换一栋楼 | **不用改代码**，只写一份新的 `selection.json` |
| 新城市、同为摄影测量 PLY/网格 | 裁剪/掩码/导出/预览/查看页逻辑与格式无关，可复用约七至八成；但坐标配准必须为新城市**重新人工推一遍**（代码不做任何通用 CRS 处理，未引入 pyproj） |
| **CityGML LoD2 带纹理** | 需新写加载器（仓库零 CityGML 代码）。但 CityGML 按 WallSurface/RoofSurface 语义分件，**footprint 裁剪这一步可以整个跳过**，`mesh_observation.py` 已支持多 mesh part |
| OBJ + MTL | trimesh 原生支持，只需替换 GLB 专属 I/O，其余整段复用 |
| **3D Tiles b3dm** | 需新写二进制分块解析（feature table + batch table + 嵌入 glTF）。更重要的是 b3dm 的 batch table 通常已带逐建筑 feature ID，**应直接按建筑 ID 取，而不是套用「footprint + 缓冲」这套几何裁剪判据**——那是给「没有语义 ID、只有连续摄影测量表面」的 SUM 数据设计的临时手段 |

香港 glTF 是另一种来源，不能套用上述“恰好一个 Trimesh”的 Voimatalo 裁剪入口：先保留完整 scene、全部节点变换/网格/材质与贴图，再按建筑对象打包。09-18 香港脚本曾只导首网格，具体损失见顶部转换核查。

### 依赖现状（已实测）

已声明且可用：numpy 2.4.4、Pillow 12.2.0、shapely 2.1.2（用到 2.x 专属的 `contains_xy`）、trimesh 4.11.5、scipy 1.17.1。

**未装**：pyproj、GDAL/osgeo、geopandas、fiona、open3d、pygltflib。

**已装但未在 `[project.dependencies]` 声明**：requests 2.33.1（只是其他包的传递依赖，`fetch_samples.py` 用到）、**lxml 6.1.0**（传递依赖）。

这意味着 CityGML 路线的接入成本比预想低：解析 XML 有 lxml，装配网格有 trimesh，贴图有 Pillow。**而且很可能不需要坐标重投影**——单栋建筑直接在源坐标系里取、把原点局部化即可，这正是 `prepare_samples.py` 已在做的事。

### Agent 侧的读取前提

[mesh_observation.py](../../../src/agent/geometry/mesh_observation.py)（1017 行）提供正交软渲染、像素查三维点、表面方向证据。**不要求网格闭合**，但对输入有硬性前提：

- GLB 自包含（拒绝外部 URI）
- 无 `KHR_texture_transform`
- 采样器必须是默认 REPEAT（**10497**）
- 材质单一不透明 baseColor，有透明度或 MultiMaterial 直接报错
- 必须有 UV 贴图

⚠️ **这是 CityGML 路线一个未验证的拦路石**：CityGML 惯用逐面小贴图，转换器很可能产出 `CLAMP_TO_EDGE`，那样会被直接拒掉。代码那一侧是读原文核实的硬事实，转换器实际产出什么是推断，**没跑过**。

[mesh_bim_frame.py](../../../src/agent/geometry/mesh_bim_frame.py)（144 行）只做人工 BIM 到网格的显式刚体对帧与 X 光叠图，`fidelity` 字段固定写死 `not_evaluated`——**没有任何自动拟合、ICP、配准或评分**。扩展到新建筑时对帧仍需人工提供 yaw 与 translation。

## 五条路线的裁决

### 路线 A：CityGML/语义模型 → 按建筑 ID 取 → 转 GLB

**推荐试。** 单体本来就是独立对象，配准和裁剪这两个最人工的环节直接消失。

现成转换工具（均未实跑验证）：

- [PLATEAU GIS Converter](https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter)——开源 Rust + Tauri，CityGML 直接转 glTF/OBJ/3D Tiles 等，**最轻**
- [cjio](https://github.com/cityjson/cjio)——Python CLI，`cjio x.json export --format glb`，配合 CityJSON 原生数据最顺手
- 3DCityDB + citygml4j——功能最全但要先导入 PostgreSQL，较重
- FME——商业，文档最完整

风险见上面的采样器问题。

### 路线 B：实景网格 + 轮廓裁剪（现有）

**保留，并优先试市方原件。** SUM 网格是赫尔辛基实景网格的下游，SUM 不是自己采的，而是在市方实景数据上做语义标注。直接从市方取官方 OBJ，可以：

1. 让新样本直接使用市方声明 CC BY 4.0 的上游原件，而不把市方许可推定给现有 2021 SUM C6 包；既有文档所谓“三处 SUM 许可矛盾”混用了 2021 SUM、2025 SUM Parts 与论文许可，已在 [sources.md](sources.md) 拆清
2. 删掉 `prepare_samples.py` 的去语义标签环节——市版 OBJ 本来就没有标注

证据强度不均：「覆盖赫尔辛基约 4 km²、公开可得」来自 2021 SUM 论文摘要；「7.5 cm GSD / 12 km² / ContextCapture / 250 m 瓦片」在 09-18 记录中只来自搜索摘要，不按实测引述。09-20 已实际打开[市方 OBJ ZIP 目录](https://3d.hel.ninja/data/mesh/Helsinki3D-MESH_2017_OBJ_2km-250m_ZIP/)并对一份 ZIP 做 HEAD（200、支持 Range），可先定位目标片，之后以正立面判窗/层线。

补样建议：**可先在已有可读片区附近横向找少数单体**，复用坐标系和工具；候选用途不能凭位置推定，须另找独立来源核实。市方 OBJ 的片号、源纹理与现有 SUM 包的对应仍需核对，裁新楼也需要新轮廓和立面检查；换城市通常还需重做配准。

### 路线 C：自采

**不作主路**，作为不在任何白名单内建筑的兜底。详见 [sources.md](sources.md) 自采一节。

### 路线 D：Google / 街景

**彻底封死，可以从设计里划掉。** 条款禁止 `by hand or machine` 提取、禁止截图、禁止离线，且明文写适用于学术项目、无研究豁免。不必再论证或找变通方式。

### 路线 E：渲染开放 IFC 当合成输入（**09-18 用户已登记为待议路径，尚未展开**）

拿有 BIM 真值的建筑（buildingSMART Duplex/Office、BIMData 汇总的 40 个项目 100 个 IFC、Auckland Open IFC Repository、慕尼黑工大 GNI 数据集），用 IfcOpenShell 渲成带贴图 GLB 喂给 Agent，再把推断出的空间块/边界/门窗与原 IFC **逐项对账**。

价值有三点：

1. 若原 IFC 有可靠的空间/开口对象，可做较明确的逐项定量对账；真实网格也能对外壳、可见开口做定量比较，只是缺失的真实内部通常没有同等真值。当前 `mesh_bim_frame.py` 的 `fidelity` 固定为 `not_evaluated`，该接口本身未做评分
2. 经核实许可和几何内容后，可构造较纯净的 L0/L1 合成输入，用来定位工具/接口问题；能否代表摄影测量贴图质量与实际推断难度，仍需真实样本检验
3. 不依赖城市摄影测量包，但每份 IFC 的权利、再分发范围和渲染所用贴图仍须单独核实；不能预设“完全无需许可”或“今天就能跑通”

许可：GNI 数据集为 CC BY 4.0（含改编权，可商用可公开发表，说法来自仓库描述，**未逐条打开 LICENSE 核实**）；其余库许可各异未逐一核实。

**状态：09-18 用户确认「这个路径登记一下，回头再聊」。已登记，本轮不展开，未选型、未下载、未实验。**

## 下一步：两个便宜的验证实验

**贴图能不能看清窗和楼层线，仍须在候选单体上逐立面实测。** 已有 [Voimatalo 西立面](../../logs/experiments/2026-09-10_showcase_textured_mass/facade_views/west.png)可辨多排窗与层间带，但香港旧预览因转换错误不能用于判断原始采集质量。柏林 CityGML 航拍纹理窗检测研究（arXiv 1812.08095）指出单张贴图裁片曝光与尺寸不规整，提示要连同视角、表面几何、遮挡评估路线 A，不能以图集总像素判断。

### 实验一：标定分辨率基线（建议先做）

优先用已有可读正对照 Voimatalo 和修复后的香港四视图做同尺度目视核查；若两者不足以覆盖普通建筑，再试赫尔辛基市方原件或墨尔本小分区。里昂公布的 **5.5 cm**、墨尔本 2020 公布的 **2 cm** 都是源影像 GSD，不能直接换算成立面模型每米有效像素或判窗阈值；香港旧脚本的“21–105 像素/米”同样不是该阈值。候选是否可用取决于实际原件立面的窗列、层间带、入口与缺面范围。

可把 [CMP Facade Database](https://cmp.felk.cvut.cz/~tylecr1/facade/)（已纠正立面和 window/door 等人工标注）当感知工具的辅助对照，但它不是摄影测量三维网格，不能用其二维图像阈值直接反推各来源 GSD 最低要求。

### 实验二：30 分钟跑通路线 A

下载鹿特丹 CityJSON 带纹理包（JSON 仅 2.7 MB + 纹理 ZIP）→ `cjio export --format glb` → 直接丢给 `mesh_observation.py`。一次回答两个问题：CityGML 系贴图能不能看清窗，以及转换产物过不过 `mesh_observation` 那五道门槛（尤其采样器那条）。成本几乎为零，但结论决定路线 A 值不值得投。

## 公开策略

公开前按每份来源核对原件、改编产物与分析展示各自权利，保留要求的署名。原始网格暂不放进公开仓库；只发衍生 BIM 也不能自动解决香港改编边界或其它来源的授权问题，见 [sources.md](sources.md)。
