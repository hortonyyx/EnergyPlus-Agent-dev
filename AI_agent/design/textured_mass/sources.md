# 带贴图单体建筑：素材来源目录

2026-09-18 调研。入口见 [体量输入调研](../textured_mass_route.md)，获取路线见 [acquisition.md](acquisition.md)，选样梯度见 [case_ladder.md](case_ladder.md)。

**09-20 素材复核：** 香港 15 栋旧 GLB 导出仅取首网格、丢父节点矩阵，导致全批竖轴错误，两栋另共丢 62 面；旧预览与按旧高度划分的类型/复杂度不能用于质量结论。现已保留完整 scene 重新转换并生成四视图，修复产物 14/15 可由现有观察器读取，剩余一例含观察器尚不支持的 `alphaMode=BLEND`，源本身不能因此删面。来源、质量与许可判断见[本轮选样复核](../../logs/experiments/2026-09-20_hongkong_material_audit/source_review.md)和[转换核查](../../logs/experiments/2026-09-20_hongkong_material_audit/conversion_audit.md)；下文保留 09-18 调研线索，遇到冲突以复核实证为准。

本页只记录来源事实与许可，不重复产品目标。**每条都标注核实程度**：「已核实」指实际打开页面读到原文，「摘要级」指只有搜索摘要，「未核实」指没查到。摘要级和未核实的不能当作已确认，选用前必须自己再开一次页面。

## 先看这一条：LoD2 不等于带贴图

本轮最大的认知纠正。**「CityGML LoD2」这个词本身不保证有真实照片贴图。** 已核实无贴图的包括：德国国家标准 LoD2-DE（柏林、汉堡、莱比锡、林茨、巴伐利亚、北威等州级开放数据）、维也纳、苏黎世、3D BAG（荷兰全国）、海牙、纽约、英戈尔施塔特 LoD3。CityJSON 官方数据集清单逐条标了 Textures 列，其中七个城市全是 None。

很多城市（柏林最典型）**几何版和贴图版是两个完全独立发布的数据集**，名字还高度相似——香港同时有 Individualised / Tile-based / Non-textured 三条线，波尔多有 `bati3d` 和 `bati3d_nt`（nt = no texture）。选错了会静默丢掉贴图，而模型照样能打开。

判据：在页面上读到 texture / Textur / texturé 字样，或者直接下小样打开看。

## 优先调查：覆盖和取件路径较明确

这两条是本轮已找到较直接按建筑或图幅定址的开放源；是否适合作为案例，还须逐栋检查用途、立面和可见范围。

### 香港 · 可視化三維地圖（單體化模型）

| 项 | 内容 |
|---|---|
| 出品 | 地政总署（LandsD） |
| 覆盖 | **全港**，2025-03 起完整覆盖，超过 22 万栋建筑及基建 |
| 贴图 | **有真实照片贴图**。官方 FIG 论文原句 `Photorealistic textures accurately attached on all class types`，LOD3 级 |
| 单体 | **逐栋独立建模**，建筑/基建/植被/水体/地形/其它分六类对象 |
| 格式 | MAX / FBX / glTF |
| 精度 | 建模粒度 0.5 m；绝对精度水平 0.3 m、垂直 1 m；相对精度 0.2 m（官方 FIG 论文 2022 定稿规格，基准 1:1000） |
| 许可 | CSDI 与 data.gov.hk 两处条款原文均为 `You are allowed to browse, download, distribute, reproduce, hyperlink to and print the Data for both commercial and non-commercial purposes on a free-of-charge basis`。免费、商用非商用皆可，须署名并承认政府所有权 |
| 入口 | [CSDI 数据集页](https://portal.csdi.gov.hk/csdi-webpage/dataset/landsd_rcd_1671676915450_88604) · [data.gov.hk 镜像](https://data.gov.hk/) · 3d.map.gov.hk 下载界面 |
| 条款原文 | https://portal.csdi.gov.hk/csdi-webpage/doc/TNC （注意：不是 `/csdi-webpage/tnc`，那个 404） |

**本项目已按此源取得 15 栋候选素材**，见 [case_tests/textured_mass/hongkong/](../../../case_tests/textured_mass/hongkong/README.md)：按建筑 ID 用 HTTP Range 从图幅 ZIP 中只取目标条目（15 栋合计传输 24.2 MB，对应图幅总量 10.3 GB），逐文件 CRC32 校验。09-18 的“15/15 通过观察器”针对丢节点矩阵/部分网格的旧 GLB，只证明旧导出形式能读；全 scene 重转后 14/15 可读，另一例因源透明材质遭观察器拒绝，均不等于立面可判读。

**怎么取到指定那一栋**（已核实，与早期说法不同）：

- ❌ **流式瓦片 API 取不到单体化模型**。[3D Visualisation Map API 文档](https://portal.csdi.gov.hk/csdi-webpage/apidoc/3d-visualisation-map-api) 原文写明它提供的是 Tile-based 连续 mesh（`data.map.gov.hk/api/3d-data/3dtiles/f2/tileset.json`，f2 免 key 可用，f1/f3–f6 返回 401）。3d.map.gov.hk 的下载界面前端代码里也只有 `f2_group`（瓦片式）与 `f10_group`（无纹理）两个产品码，**没有单体化的入口**。
- ✅ **单体化模型的实际入口在 CSDI**（已实跑）。CSDI 的 geoportal 元数据 API 里有一个 `file-api`，返回**全港 3456 个图幅的 GeoJSON 索引**，每幅属性直接带三种格式的下载直链：

  ```
  SHEETNO      = 11-SW-8D            （中环）
  REVISIONDATE = 20260828
  Format_glTF  = https://download.map.gov.hk/api/3d-zip/GLTF/11-SW-8D.zip?key=<公开key>
  Format_FBX / Format_MAX = 同上，换格式
  ```

  索引地址：`https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=landsd_rcd_1671676915450_88604&format=geojson&layer_name=Individualised_models`。
  **URL 里的 key 是内置在官方查看器 `setting.js` 里的公开 key，不需要申请。**
- **包内结构**：`BUILDING / TERRAIN / VEGETATION / INFRASTRUCTURE / GENERIC` 分目录，每栋建筑一个以建筑 ID 命名的文件夹，含独立 `.gltf + .bin + 贴图`。**地形与植被与建筑分开，不存在粘连。**
- **不必下整幅**：一幅 ZIP 是 1–2.6 GB（中环 11-SW-8D 含 781 栋 / 2.46 GB），但服务器支持 `Accept-Ranges`。先读 ZIP 尾部的中央目录，再按建筑 ID 用 HTTP Range 只取目标条目即可，逐文件 CRC32 可校验。实测单栋中位 1.46 MB。
- 09-18 记录的 **21–105“像素/米”不是立面实测分辨率**：旧脚本以首网格的一张贴图总像素数除以表面积再开方，未计多网格/多贴图、UV 占用与拉伸、摄影角度或模糊，不能换算成 1.5 m 窗的有效像素，也不能与航摄 GSD 直接比较。旧“高/中/低”依据文件字节密度或主观判断，尚未逐立面标注窗和层线可读性。
- 源为 glTF 2.0，普通不透明部分可由观察器处理，但**不是全批“无 alphaMode、零改动”**：B342 源另有 `alphaMode=BLEND` 的 8 面及透明贴图；新 GLB 保留它们后观察器明确拒绝。原转换对全部 15 栋丢节点矩阵，B342 和 B416 还因只取首网格共丢 62 面。应修观察/显示层的兼容，不能为了过门槛删掉源面。

**一个许可待确认项**：[CSDI 条款](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC)列出 browse / download / distribute / reproduce / hyperlink / print，未明确写 modify / adapt / derivative works。单体模型改编及派生 BIM 的公开发布是否在授权内，本轮不能据此断定；产品化或公开派生文件前宜向发布方确认。

**另一份补充**：规划署[香港三維實景模型](https://www.pland.gov.hk/pland_en/info_serv/3D_models/download.htm)，2017-03 与 2018-03 航拍，OSGB/OBJ/Cesium 3D Tiles，地图框选区域下载，免费。但只覆盖港岛部分与九龙半岛（**不含新界**），影像更旧，且页面只有免责声明式条款（`for reference only`），没有明确的四项授权原文。作交叉验证可以，不作首选。

### 里昂大都会 · Photomaillage 3D

| 项 | 内容 |
|---|---|
| 出品 | Métropole de Lyon 测绘服务 |
| 覆盖 | 里昂大都会全域 |
| 贴图 | **有**，2023 年夏航摄，描述为 `textured and photorealistic` |
| **源影像分辨率** | 发布资料列 5.5 cm；这是采集 GSD，不等于各立面有效像素，也不能单靠它推算 1.5 m 窗在模型上可辨 |
| 格式 | 3D Tiles |
| 单体 | ❌ **连续 mesh，不是单体对象**。取单栋要自己做空间裁切，建筑与地面/邻楼在拓扑上连续 |
| 许可 | Licence Ouverte / Open Licence 2.0（Etalab）——通用条款允许复制、再分发、**改编**、商用，仅要求署名。正好补上香港条款缺的改编权 |
| 入口 | [data.gouv.fr 镜像页](https://www.data.gouv.fr/datasets/) · data.grandlyon.com |

核实程度：镜像页已核实（publisher、航摄日期、5.5 cm 像素、`textured and photorealistic`、3D Tiles、许可名称）。**未核实**：data.grandlyon.com 下载页实际交互（SPA 取不到正文）、单幅文件大小、是否需注册、Etalab OL 2.0 原文未逐条重读。

## 第二档：有贴图但要碰运气或有缺项

| 来源 | 贴图 | 覆盖 | 许可 | 要注意什么 |
|---|---|---|---|---|
| **日本 PLATEAU** | LOD2 有，来自航拍照片投影 | 约 300 城市（2027 目标约 500） | CC BY 4.0，**明确授予改编权** | 国交省官方原文 `LOD2では特定のエリア`——**贴图只覆盖各城市部分示范街区**，东京 23 区仅约 32 km²。目标楼不在整备区就只有无贴图 LOD1 方块。下载单位是约 1 km 三次网格，要「地址→坐标→网格→文件内按建筑 ID 二次提取」 |
| **赫尔辛基实景网格** | 有，源影像 GSD 约 7.5 cm（此前摘要级） | 全市，2 km 包内含 250 m 子瓦片 | CC BY 4.0 | 连续 mesh 要裁切。[官方 OBJ ZIP 目录](https://3d.hel.ninja/data/mesh/Helsinki3D-MESH_2017_OBJ_2km-250m_ZIP/) 于 09-20 已打开，示例 ZIP 用正常 TLS 做 HEAD 返回 200 且支持 Range；先定位目标片号，勿下大包。市方还说明带纹理 LoD2 CityGML 可在地图下载服务选择，具体纹理窗质量未验 |
| **墨尔本 Photomesh 2020** | 有，官方列 **2 cm 源影像 GSD**，不能直接当竖墙有效分辨率 | 全市 | CC BY 4.0（已核实 discover.data.vic.gov.au 许可字段） | 连续 mesh；SLPK + OBJ/MTL/JPG；两份约 31–33 MB 的分区 ZIP 于 09-20 HEAD 200，实际窗可读性待验 |
| **柏林 3D-Meshmodell** | 有 | 全市 | **dl-de/zero-2.0**（近 CC0，无 share-alike，允许商用） | 连续 mesh；GSD 未查到 |
| **卢森堡 BD-L-BATI3D 2023** | 有，2023 夏倾斜航拍 | **全国**（占地 >20 m²） | **CC0** | LoD2.2 CityGML + jpg，每对象唯一 ID，按市镇打包 105 个文件，EPSG:2169。⚠️ 不要与另一份 2017 年 LoD2.3 试点数据混淆，那份只有 3 km² 且**无纹理** |
| **Namur（比利时）** | 有，页面原文 `Toutes les faces de bâtiments sont texturées en couleurs` | 全市，200 m 方格 | 未核实 | 方格小，裁单栋的工作量接近现有流程 |
| **鹿特丹** | 有——CityJSON 官方清单里**唯一**标 Textures 的 | 市域 | 随源 | JSON 仅 2.7 MB + 纹理 ZIP，是最便宜的试水样本 |
| **TUM2TWIN（慕尼黑）** | LoD2 带纹理 + **LoD3** + 无人机实景网格，**同一坐标系** | 慕尼黑市中心约 100,000 m² | CC BY 4.0 | 32 个子集约 767 GB，要 Git LFS 克隆；投入前先确认能否只取单个瓦片。**LoD3 的门窗是真实几何**，可作开口推断的参照 |
| 波尔多 / 蒙特利尔 | 有 | 瓦片级 / 市中心部分 | 未核实 | 数据较旧（2012 / 2016） |

另有 TU Delft 维护的 [开放三维城市清单](https://github.com/tudelft3d/website/blob/main/_data/opendatacities.yml)（41 条机读 YAML，每条带 `texture: yes/no` 字段），从中另捞出八个带贴图城市：Bordeaux、Montréal、Adelaide、Philadelphia、Espoo、Vantaa、Fredericton、Dresden。**一条都没单独核实**，且清单已陈旧（年份跨 2009–2023，把 2023 版带贴图的卢森堡标成 `texture: no`）。只能当线索池，不能当结论。

## 第三档：亚洲其它地区，基本不可用

| 地区 | 结论 |
|---|---|
| **新加坡** | **不可用**，三条独立证据一致：① OneMap 条款 3(b) 明文把 modify / adapt / publicly display 列入禁止，且 3(a) 授予的许可是 **revocable**；② NUS 城市分析实验室（本地权威中立信源）原文 `the data cannot be downloaded (and thus it isn't open data)`；③ 3D Singapore Sandbox 是要亲赴新加坡 GeoWorks 预约 3 小时时段、逐案审批的实体设施。OneMap3D Developer Programme 要签 NDA，条款因此不公开；已入项目的开发者自述模型是 `handcrafted through some modelling software`、纹理 `can be inconsistent / repetitive`，像人工/程序化贴图而非逐栋摄影贴图。唯一真正开放的是 NUS 做的全岛组屋 LoD1 体量——**无贴图**，且只有组屋 |
| **台湾** | 全国建物模型只有 LOD1 无贴图；台北示范区约 1290 公顷据称有真实纹理（**未核实**）；下载要自然人/工商凭证，海外用户是否可行不明 |
| **韩国** | 全国 LOD1 无贴图；带纹理的「实感」数据在国土地理情报院规定中属**限制资料**需申请；V-World 的 3D Open API 已关闭 |
| **中国大陆** | 「实景三维中国」确有省级公开成果目录（如广西 19 个测区共 662.68 km²，2018–2020，OSGB/OBJ/3D Tiles），但走全国地理信息资源目录服务系统的**注册审批**（需说明单位与用途），不是开放许可下载；未发现任何城市有按地址取单栋的公众入口。另外还涉及测绘资质与涉密成果管理，本轮完全没展开——若目标建筑在大陆，本页结论覆盖不全 |
| 印度 / 泰国 / 马来西亚 / 迪拜 / 以色列 | 均未发现开放的真实贴图三维建筑数据 |

## 地图平台：没有合规的 Google Earth 平替

**带真实贴图的，条款全部封死：**

| 平台 | 条款原句 |
|---|---|
| Google Maps Platform / Photorealistic 3D Tiles | 禁止 `image analysis`、`machine interpretation`、`object detection or identification`、`geodata extraction or resale`、`offline uses`；3D 物体不得 `by hand or machine` 提取或派生。Street View 另禁止截图与描摹，且**明文写适用于学术、非营利和商业项目，无研究豁免** |
| Bing Maps | 禁止 `copy, store, archive...Content`（仅许本地存 geocode）；禁止 `tracing or extracting features...to create a new work` |
| Apple Maps | 禁止 `cache, pre-fetch or store any part of the Service`；禁止 `copy, extract, scrape...training of any model`。且无任何导出通道 |

这是**合同条款而非版权许可**，没有「学术研究」的豁免口子。此前「不从中提取」的判断不仅正确，还应扩展成**连人工参考描摹和截图留存都不行**。

**条款宽松的，全都没有真实贴图**（均已核实为几何挤出 + 程序化材质）：Mapbox（官方文档 `without any baked-in lighting or material maps`）、Cesium OSM Buildings、Esri Living Atlas OSM 3D Buildings、F4Map、OSM2World、高德。贴图诉求本身不成立，条款细节不必再查。

Cesium ion 与 ArcGIS 里唯一带真实贴图的城市级资产，是**转授权的 Google Photorealistic 3D Tiles**，条款附录写死与 Google 平台条款一致，绕不开。另：Cesium 的 Bing 数据 **2026-09 起停止提供**。

唯一在设计上匹配「指定建筑」的是 **HERE Premier 3D Cities**（官网原文 `The structures are indexed and addressed. Developers can search and address individual buildings`），但贴图真实性、亚洲覆盖、价格、合规条款**四项全部未核实**，只能算「该去谈合同的候选」。

## 商业供应商：窗口很窄但真实存在

**AccuCities（英国）是唯一核实到有真实单栋成交案例的**：

- 支持**在地图上画圈**定制下单，官网原文 `Custom 3D models can be ordered in any shape – simply draw a map mark-up`，最小 0.1 km²（约 330×330 m，够框一栋）
- 真实案例：利物浦 Cathedral Church of Christ，0.15 km² 定制模型，**£750 + VAT，6 天交付**
- 报价：Level 2 最小 0.1 km² 约 £500+VAT；Textured London £4,000+VAT/km²，最小 0.25 km² £1,000+VAT（5 年许可）；非商业与学生项目最高 8 折优惠
- 许可已核实：授予 Derived products（渲染/动画）、Incorporated products（集成到自有软件）、In-house work、3D 打印；**但明文禁止再分发原始三维模型文件本身**
- 覆盖严格限于伦敦 60 km²、伯明翰 7、布里斯托 4、卡迪夫 4、都柏林 12、底特律 9 km²；另称定制航拍覆盖英国 98.5%
- 有免费样例瓦片可先试

其余供应商都要人工询价且条款未核实：**Aerometrex**（美国 10 个片区 2–5 cm，MetroMap 支持画图/上传 GeoJSON 圈地）、**Nearmap**（网格顶点间距 15 cm、影像 5.5–7.6 cm，覆盖澳美加新西兰；⚠️ 条款摘要出现「仅限内部非商业使用」字样，必须逐字核）、**Vexcel**（60+ 城市含东京，7.5 cm，疑似整片交付）、**CyberCity3D**（产品线天然支持单栋定制贴图）、**HxGN Content Program**（官网 403 打不开，可信度最低）。

**可排除**：Maxar/Vantor（0.5 m 分辨率、最小订单 100 km²）、PhotoSat（做地形高程不做贴图建筑）、Bentley/Cesium（是软件与托管平台，不是数据源）。

询价时把「能否公开展示衍生分析结果」和「能否公开展示或重新发布原始三维模型文件」**当两个独立问题分别问**——AccuCities 对这两者宽严就不同（前者允许、后者禁止），其余供应商大概率类似。

## 自采：兜底手段，不作主路

- **手机 app**（Polycam / Scaniverse / RealityScan）：成本近零、半天可完成，但**看不到屋顶和高层立面**，只适合周边开阔的低层建筑。Polycam 免费层只能导 GLTF，Pro 约 $26.99/月；Scaniverse 本地扫描免费；RealityScan 移动端完全免费。室外与玻璃/反光表面回落到摄影测量精度，严重依赖光照与重叠率
- **开源全流程**：COLMAP（本身不含贴图网格环节）、Meshroom/AliceVision、OpenDroneMap/WebODM（产出 `odm_texturing/odm_textured_model.obj`），需 CUDA GPU、处理 2–4 小时
- **无人机**：绕飞参数可查（45° 倾斜、70–85% 重叠、离立面 6–30 m），但密集城区几乎必撞合规墙——美国人行道上空默认禁飞、欧盟城区多需 Specific 类别、中国执照 8000 元以上加逐次空域报备（2026 起强制实名激活）。**居住类建筑另有隐私法约束，正撞酒店/公寓/宿舍这个重点类型**
- **3DGS → mesh**（SuGaR / 2DGS / GOF）：仍是研究代码，窗户与楼层线可读性完全未经验证
- **只用地面照片**：拍不到屋顶，对第 1–4 级简单平屋顶影响不大，对退台屋顶不够用

判断：**这是对不在任何白名单里的建筑的唯一可靠兜底**，版权最干净，但应作为「补充采集」环节单独评估预算与合规，不作为规模化补样的主路。

## 模型库与数据集：只能补个别样本

已核实：**Sketchfab** 有零散 CC 建筑扫描但需逐个人工核验、无法批量（Download API 只返回 glTF/GLB/USDZ）；**Objaverse-XL** 真实摄影测量扫描占比不到 1%；**Poly Haven / ambientCG** 已确认无完整建筑外观模型；**RWTT** 是 568 个雕塑日用品等通用物体（OBJ+PNG，CC BY-SA 4.0），**不是建筑数据集，应从候选清单移除**；学术数据集里 Building3D 纯 LiDAR 无纹理、ScanNet++ 纯室内、UrbanScene3D 与 Mill19 是园区/工业区尺度需自行裁切且部分带非商业限制。

另外两类遗产/众包来源：**Open Heritage 3D**（CyArk 等，按 CC 系列许可，FAQ 原文 `Most datasets require attribution`，但多为点云且未核实有多少是完整建筑外壳）、**Polycam Explore**（社区可保存内容按 CC 4.0 授权，但具体是哪个变体未查到，官方页 403）。

## 许可三档速查

针对本项目链路（下载 → 离线保存 → 派生单栋 GLB → AI 分析 → 生成 BIM → 论文/仓库/汇报公开展示，可能产品化）：

**较明确的开放许可，仍按具体作品核对**：卢森堡 CC0、墨尔本 CC BY 4.0、PLATEAU（Public Data License 1.0，兼容 CC BY 4.0）、德国 DL-DE-BY-2.0、里昂 Licence Ouverte 2.0、美国联邦数据（17 U.S.C. §105，仅限联邦雇员职务作品，不能推广到州/市或学术机构）、OSM（仅用于裁剪不重新发布时算 Produced Work，署名 `© OpenStreetMap contributors`）。香港 CSDI/data.gov.hk 条款明确允许多种使用，但**改编及派生公开权利待确认**，不能并入“全部场景可放心”。

**第二档，只能非商业研究**：

- ⚠️ **区分 2021 SUM C6 与 2025 SUM Parts**：本项目 Voimatalo 使用的是[2021 SUM Helsinki C6](https://3d.bk.tudelft.nl/projects/meshannotation/)下游包；其独立权利说明本轮未确认，勿把市方 CC BY 4.0 自动套到这一包。另一个[2025 SUM Parts GitHub](https://github.com/tudelft3d/SUM-Parts-Benchmarks)称软件和数据为 GPL-3.0，[SUM Parts Hugging Face 数据卡](https://huggingface.co/datasets/gwxgrxhyz/SUM-Parts/blob/main/README.md)称数据为 CC BY-NC 4.0，二者需按具体文件与发布关系澄清。[arXiv SUM Parts 页](https://arxiv.org/abs/2503.15300)显示的是论文许可，不是数据集 CC BY-NC-ND 授权。开发可继续保留本地评测原件；公开转发 2021 C6 原始/派生网格前需确认其权利说明。
- **Mapillary** CC BY-SA：「仅作参考重建是否构成改编」这个问题连 Creative Commons 官方 FAQ 自己都承认定义模糊。

**第三档，不可使用**：Google Maps Platform 全线。

**公开前按来源分别核对**：原始三维模型先不放进公开仓库；衍生 BIM 与分析结果能否公开也要按原许可、改编权和署名要求核查。香港的改编边界尚未明确，AccuCities 付费许可另有限制，不能把“只发衍生物”视作同时解决三种许可问题。

**署名怎么落地**（四处）：① 仓库 README 或论文「数据来源」章节列表，含名称、许可全称与版本、链接、访问日期；② 派生 GLB/BIM 旁放 SOURCES.txt 或写入 glTF 的 `asset.copyright` 字段，随文件走；③ 公开展示的每张含原始贴图的截图按 CC 推荐的 TASL 四要素（Title / Author / Source / License）标注；④ 明确写「已裁剪/重建/经 AI 推断处理，非原发布方制作」，满足 PLATEAU、DL-DE-BY-2.0 等条款对修改的注明要求。

## 本页的边界

- 全部结论为调研性质，**不构成法律意见**。产品化前尤其针对 SUM/SUM Parts 和任何 CC BY-SA 来源，建议另行寻求知识产权律师复核。
- 政府开放政策与无人机法规变化快，落地前必须重查当次官方渠道，不能引用本页作为合规依据。
- 09-18 调研时尚无逐立面可读性复核；09-20 已有 Voimatalo 可辨窗列与层间带的对照，香港 15 例在修复转换后仍须逐栋复核。发布方的航摄 GSD 和旧脚本的图集像素密度均不等于立面可读性，见 [acquisition.md](acquisition.md)。
- 09-18 外部来源调研未额外下载新数据集、注册账号或提交申请；本项目先前已取得 SUM 瓦片和 Voimatalo 输入，09-18 香港另取得 15 栋候选，09-20 对已有原件做转换与检查。
