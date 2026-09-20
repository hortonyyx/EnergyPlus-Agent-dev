# 带贴图三维模型：输入格式支持路线图

**09-20 接手说明：** 本页保留09-18格式调研结果，本轮未逐格式复验，不代表当前生产支持清单。香港实际问题是丢场景节点/网格，完整转换现已修复；能力以具体代码和实测为准，见[素材复核](../../logs/experiments/2026-09-20_hongkong_material_audit/README.md)。

2026-09-18 调研 + 本地实测。入口见 [体量输入调研](../textured_mass_route.md)，来源见 [sources.md](sources.md)，获取路线见 [acquisition.md](acquisition.md)。

本页回答「**可以做到支持哪些格式**」，不是「现在支持哪些」。产品投入使用后素材由用户自带（见 [goal.md](../../project/goal.md) 09-18 确认），所以读取侧要能兼容用户可能拿来的东西。

标注约定：**【实测】**指在本仓库环境里实际跑过；**【已核实】**指打开了源码或官方文档；其余为搜索摘要级，选用前需自行再确认。

## 出口是唯一的：自包含 GLB v2

所有格式最终都要落到 `mesh_observation.py` 能吃的形态。它的硬门槛在 `_validate_self_contained_glb()` 与 `_material_texture()` 里写死：

| 检查 | 要求 |
|---|---|
| 容器 | 二进制 glTF v2，magic `glTF`，声明长度与文件大小一致，首块为 JSON |
| buffers / images | **不得有外部 URI**，只允许内嵌或 `data:` |
| 扩展 | 不得使用 `KHR_texture_transform` |
| 采样器 | wrapS / wrapT **必须为 10497（REPEAT）** |
| 材质 | 单一不透明 baseColor + UV 贴图；有透明度或 MultiMaterial 直接报错 |

## ⚠️ 现存隐患：压缩几何静默失败

**【实测】** trimesh 4.11.5 **没有** `KHR_draco_mesh_compression` 的导入支持（**【已核实】** 其扩展注册表只有 `KHR_materials_pbrSpecularGlossiness` 与 `EXT_texture_webp` 两项；Draco 只有导出侧代码，容易被误读成也支持导入）。但它**读 Draco GLB 时不报错**，而是返回一个几何全零的空壳：

| | 原始 | Draco 压缩后读出 |
|---|---|---|
| 面数 | 8148 | 8135（看着正常） |
| 包围盒 | 47.9 × 71.5 × 91.0 m | **[0, 0, 0]** |
| 表面积比 | — | **0.0** |
| UV 范围 | 0.062–0.978 | 退化成 0–1 |

**更关键的是这个 GLB 能通过 `mesh_observation` 的校验**——校验不查压缩扩展。实测 `MeshObservation` 接受它、`describe()` 返回 `bounds: [[0,0,0],[0,0,0]]`，全程零异常。

这与格式路线无关，现在就成立，应优先补一道拒绝或解压。`EXT_meshopt_compression` 同理（**【已核实】** trimesh 源码对 meshopt 零匹配）。

## 第一档：已能吃，或顺手就能加

| 格式 | 状态 | 要做什么 |
|---|---|---|
| glTF / GLB（自包含） | ✅ 原生 | 无 |
| **OBJ + MTL + 贴图** | ✅ **【实测】零障碍** | 无。trimesh 读→导 GLB，4096×1024 贴图完整保留，**产物直接过 `mesh_observation` 校验** |
| DAE / COLLADA（+ .zae） | ✅ 原生 | 无。底层 pycollada（BSD-3-Clause） |
| **KMZ / KML + COLLADA** | 🟡 **几乎免费** | **【已核实】** pycollada 本身已支持 kmz，只是 trimesh 的 `_collada_loaders` 字典里没注册该扩展名。可能只需调用时指定 `file_type="zae"`（其实现就是「在 zip 里找第一个 .dae」，与 kmz 内部结构一致） |
| PLY / 3MF / OFF / STEP | ✅ 原生 | 无。⚠️ PLY 若是纯顶点色则过不了「必须有 UV 贴图」这关 |
| **b3dm（3D Tiles）** | 🟡 **【实测】可行** | 28 字节头 + feature/batch table 之后即完整 GLB。手写约 30 行即可，也可换 **py3dtiles**（Apache-2.0，活跃，**【已核实】** 其 `b3dm.py` 正确解析并交给 pygltflib） |
| 3D Tiles 1.1 直出 glTF | ✅ | 复用现有 GLB 路径 |

## 第二档：值得做，工作量中等

| 格式 / 问题 | 路径 | 成本与风险 |
|---|---|---|
| **GLB + KTX2 贴图** | **【实测】** Khronos KTX-Software（Apache-2.0）的 `ktx` CLI + `gltf-transform ktxdecompress`。纯 Python 方案不存在（pyktx 也只是原生库绑定） | 装一个二进制，固化成脚本。**这是香港 3D Tiles 的实际情况** |
| **Draco / meshopt** | 用 gltf-transform 预处理解压（`gltf-transform copy` 即可去压缩） | 一个脚本，与 KTX2 同构 |
| **KHR_texture_transform** | 现在是直接拒绝。补 UV 仿射变换即可 | 几十行，无新依赖。**不补会持续挡掉正常 Blender 图集导出的模型** |
| **IFC** | IfcOpenShell（LGPL-3.0，pip 有 3.10–3.14 wheel），`IfcConvert` 直接导出 GLB | 装库 + 一行命令。⚠️ **产出贴图的上限很低**——OSArch 社区讨论称纹理是 IFC 里「最模糊、实现最有漏洞」的部分，多数公开 IFC 只有面颜色。**能转格式 ≠ 能出贴图** |
| **Rhino 3DM** | rhino3dm（MIT，纯 wheel，McNeel 官方维护，8.35.0） | 装库 + 自写胶水。仅当源文件勾选了「嵌入贴图」才有贴图 |
| **FBX** | 无干净的纯 Python 路径：Autodesk SDK 绑定是非开源 EULA 且官方 wheel 只到 Python 3.10（本项目 3.12）；pyassimp 不活跃且不自带二进制。最现实是 **FBX2glTF**（BSD-3-Clause）专用 CLI，或 Blender 无头 | 装二进制。**香港单体化模型给的三种格式之一** |
| **OSGB** | ⚠️ 无干净路径。**【已核实】** OSG 的 glTF 插件 PR#686 于 2019 年关闭未合并，项目已进维护模式。候选 fanvanzh/3dtiles（Apache-2.0，活跃）但**贴图保真度无人实测** | 装二进制 + **必须先跑一次小样本实测**，不能只信 README |
| **CityJSON** | cjio（MIT）能导 GLB——但 **【已核实】** 其 `convert.py` 的 `to_glb()` 只按对象类型赋 10 种纯色，JSON 骨架里完全没有 images/textures/samplers，**现有导出丢掉全部纹理** | 需在 cjio 上二次开发一两百行 |
| **USD / USDZ** | `usd-core`（pip，支持到 Python 3.14）**只是数据模型库，没有现成的导出 glTF 函数**，要自写一两百行遍历；或走 Blender 原生导入。trimesh 不支持 | 中等。**USDZ 是 iPhone Object Capture 的默认产物**，消费级用户最可能带来 |

## 第三档：结构性做不到，应在用户指引里直接劝退

- **CityGML** —— 格式本身能带纹理（TexCoordList 逐面 UV + 外部图片），但唯一核实到能保真转 glTF 的路径是 **3DCityDB，要先装 PostgreSQL/PostGIS 导入再导出**；其它工具（mago-3d-tiler 等）明确不转贴图。与轻量 Python 管线不匹配。
- **.MAX / RVT** —— 私有格式，无可靠开源读取路径。rvt-rs 是唯一非商业选项但自述「还不是完整的 Revit 读取器」。
- **Shapefile multipatch** —— Esri 官方文档原文 `Colors or textures can't be saved with multipatch shapefiles`。源头就没有贴图。
- **STL / Alembic** —— 格式里没有贴图概念。
- **点云（LAS/LAZ / E57 / PTS / PCD）** —— 读取不难（laspy BSD-2、pye57 MIT、Open3D），但**规范层面只有逐点 RGB，没有 UV+贴图**。Poisson 重建产出顶点色网格，顶点色分辨率受点密度限制，**结构上表达不了窗框细节**。pymeshlab 的顶点色转贴图滤镜有已知卡死 issue，且是 **GPL3**。这是格式硬限制，不是库没做好。
- **3DGS 原始格式（.ply 变体 / .splat / .spz / .ksplat）** —— 逐点球谐椭球，无面无 UV，「贴图」概念不适用。**但用户若已自行跑完 SuGaR 拿到 OBJ+贴图，那就是零成本的现有路径**——应写进获取指引。
- **SKP** —— 唯一候选 openskp 元数据可疑（PyPI 显示发布日期即调研当天、仅约三个月历史、单人维护、存在多个同源 fork），贴图保真度无任何第三方验证。要用必须先自建回归测试。

## 结构建议：先写「GLB 归一化」层，而不是某个格式的解析器

所有格式最终汇到同一出口，所以该先写的是一层与源格式无关的归一化：

1. 解压 Draco / meshopt / KTX2
2. 烘焙 `KHR_texture_transform` 进 UV
3. 采样器改写为 REPEAT
4. `alphaMode` 归一为 OPAQUE（**【实测】** 香港瓦片是 `MASK`，贴图实为 RGB 无 alpha，属名义性声明）
5. 外部 URI 内联为自包含
6. **读完检查几何非退化**——即上面那个 Draco 静默失败的防线

写一次，之后每加一个格式只剩「转成 GLB」这一步。

## 关于「万能方案」

**Blender 无头**（`blender --background --python`）一套脚本可覆盖 FBX / DAE / OBJ / USD / USDZ / 3DS / .blend / Alembic 七八种，边际成本远低于逐格式找库，代价是部署一个数百 MB 的二进制。当前容器未装；仓库配置的 blender MCP 也处于连接失败状态（ENOENT，指向 Windows 路径），与「未部署成功」一致。

## 依赖可得性（已查 PyPI）

均有 wheel：ifcopenshell 0.8.5、py3dtiles 12.1.1（Apache-2.0）、cjio 0.10.1（MIT）、rhino3dm 8.35.0（MIT）、pygltflib 1.16.5、laspy 2.7.0（BSD-2）、open3d 0.20.0、pyproj 3.8.0、usd-core 26.8、meshio 5.3.5。**pymeshlab 2025.7 是 GPL3**，产品化需注意。pyassimp 仅源码分发且维护不活跃。

当前环境已有：trimesh 4.11.5、shapely 2.1.2、Pillow 12.2.0（**【实测】自带 webp 与 avif 解码**）、numpy、scipy、lxml、Node 24 + npm。未装：pyproj、GDAL、open3d、pygltflib、assimp、blender、meshlab。
