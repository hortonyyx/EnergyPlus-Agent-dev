# 部分推理素材来源与选样复核（2026-09-20）

范围：只核已有文档、选样/下载记录、两张现有预览和官方发布页；没有下载新模型、运行 BIM 或调用模型。15 栋的逐立面视觉复核由本轮另一项工作承担。此处的结论不能替代那份复核。

## 当前 15 栋能证明什么

- 香港地政总署的[单体化模型数据集](https://portal.csdi.gov.hk/csdi-webpage/dataset/landsd_rcd_1671676915450_88604)官方确认为覆盖全港、含几何与纹理影像，区分建筑等地物。项目的 [香港素材 README](../../../../case_tests/textured_mass/hongkong/README.md) 和逐栋 `record.json` 证明已按建筑 ID 取出 15 份文件、CRC 校验、转换成 GLB，15/15 通过 `mesh_observation` 读取。**这些只证明下载和格式可读，不证明哪栋的窗、楼层线、外壳完整。**
- [selection.py](../../../../case_tests/textured_mass/hongkong/selection.py) 的“高”实例理由直接使用 JPEG 文件 KB/m²，“低”也用该值；“中”没有统一阈值或标注方法。它没有逐立面可辨窗数、层界、遮挡/缺面、独立复查记录。把这批标签写作“素材质量高/中/低”会误导；目前只可称为**候选时的文件密度分组**。`README.md` 已承认用途未逐栋核实，选样脚本里的“办公、商业、唐楼、工业”等很多是地区和形态推测，不能作为建筑用途真值。
- L0–L5 主要由尺寸、面数、外形粗判，尚未逐栋核实实际楼层、平面凹凸、退台、内环，更没有 P（内部组织）、E（立面形式）、S（采集缺失）分轴实测。`case_ladder.md` 的 L 定义中 L1 是**可推的多层层界**，L2 是**自遮挡的凹面**，L5b 是**中心核心筒带内环**；仅凭“21 面、15.3m 高”或“高层办公”不能落定这些级别。尤其 L0 的“独栋村屋”记录高度 8.0m，不宜未经楼层核实称单层基线。现有 15 栋是形体尺寸梯度候选，不是已验收的 L/P/E/S 案例梯度。
- [09-18原fetch_buildings.py](received_2026-09-18/fetch_buildings.py) 的 `texture_px_per_m = sqrt(texture_width * texture_height / mesh.area)`（第 143 行）只取 `list(scene.geometry.values())[0]` 的第一份 geometry（第 132 行）及其一张 `baseColorTexture`。例如 [B416…记录](../../../../case_tests/textured_mass/hongkong/single_buildings/B416111881201063A0/record.json) 列了四张 JPEG，却只记录一张 4096×4096 和 104.8 px/m。即使只有一张图集，该公式也默认所有像素均匀铺满全表面；未计 UV 空白/重复、局部缩放、遮挡、重压缩、不同立面和原摄影角度。**不能由 21–105 px/m 推出“1.5m 窗最差也有 31 个可用像素”，更不能据此判窗可读。** 多 geometry/多贴图是否真的被转换时丢失，需另项转换核查；此处仅指出代码和记录没有覆盖它们。
- 已打开一张香港“高”例 `B416…/view.png`：呈分散构件/顶视状态，当前预览无法判窗列或层线；一张“低”例 `B338311…/view.png` 可见大面纹理但无可确认窗列。这不代表原件必然差，也不能把预览问题直接归咎采集。15 栋应逐一用正确竖直轴、正立面、同等目标像素尺度查看**源 glTF 与转换 GLB**；对同一处窗比对，才能分开源质量、转换损失、相机问题。

## 更有证据的选材关卡

先选少量**已核实用途**的普通办公、住宿或商业单体，且尽量从规则外形、可见标准层开始。每栋保存建筑身份/用途来源、原文件及哈希、转换前后立面图和实际相机；至少记录两面立面的窗列是否可逐个辨、层间带是否可辨、底层入口是否可辨，以及贴邻/树木/缺面范围。等级以实际判读任务定义：可用＝至少目标立面的窗列和层界可独立指出，局部不清的区域显式标未知；受限＝只可读形体或部分开口；不可作首批＝关键立面不可读、严重缺失，或转换后与源差异无法说明。独立观察者复核争议处。缺乏真实内部资料时，不能给“推断内部正确”打真值分。可保留难例，但不要让采集缺陷冒充建筑复杂度。

已有正对照：[Voimatalo 西立面原网格观察图](../2026-09-10_showcase_textured_mass/facade_views/west.png)的多排窗、层间水平带肉眼可辨；[单体输入说明](../../../../case_tests/textured_mass/single_buildings/voimatalo/README.md)记载其从已取 Helsinki/SUM 瓦片裁出、用途由公开建筑资料核实、GLB 可查看。它形体复杂且源为 SUM 下游，不宜继续充当简单首例，但足以作为本项目“可读立面”的最低视觉对照。该图本身仍有屋顶和边界扫描残缺，不能代替建筑真值。

## 接下来两条可执行的获取路线

1. **赫尔辛基市原件：先在已知可读街区找较简单单体。** [市官方 Helsinki 3D](https://www.hel.fi/en/decision-making/information-on-helsinki/maps-and-geospatial-data/helsinki-3d)明确提供 CC BY 4.0 的实景贴图 OBJ/3MX 下载，另有可选纹理的 LoD2 CityGML，后者每栋有独立 ID。官方链接实际通向[OBJ ZIP 目录](https://3d.hel.ninja/data/mesh/Helsinki3D-MESH_2017_OBJ_2km-250m_ZIP/)，本次已打开目录并对其中一份 10,895,783 字节的 ZIP 做 HEAD，返回 200、支持 Range；目录里也有大型 2km 包，因此要先定位片号，避免随意下整幅。先在已知 Voimatalo 所在片区的官方 OBJ/城市模型下载界面定位一栋用途有公开依据、两面可见且外形简单的建筑；只取对应小区/片，再按现有轮廓法裁单体并做源/转换立面比对。若选择带纹理 CityGML，按 building ID 取对象，需新转换与读取检查；CityGML 纹理是否足以读窗**尚未验证**。市方明确反光表面在实景网格中可能失真。现有 SUM 网格虽出自该市实景数据的下游，市方许可不能自动覆盖手上的 SUM 文件；新样本应直接从市方取原件。
2. **墨尔本 2020 Photomesh：按小区域下载并目视过关后再裁单体。** [市官方数据页](https://data.melbourne.vic.gov.au/explore/dataset/city-of-melbourne-3d-textured-mesh-photomesh-2020/)确认 OBJ/MTL/JPG、点击区域得到 `Download_URL`，以及 2020 年航摄的 2cm *ground sample distance*；[州政府目录](https://discover.data.vic.gov.au/dataset/city-of-melbourne-3d-textured-mesh-photomesh-2020)将许可列为 CC BY。仓库已有 [区域索引](../../../../case_tests/textured_mass/melbourne_regions.json)与 [HEAD 探测](../../../../case_tests/textured_mass/melbourne_download_probe.json)；本次再次对 `A1-11.zip`、`A1-12.zip` 做 HEAD，均 200、支持 Range、大小分别 33,443,435/30,910,544 字节。可先下载**一块**，在官方区域视图中挑普通建筑，打开源 OBJ 正立面，满足上面的可读性关卡才继续。这条目前仅证明“可获取且有纹理”，**未证明 A1-11/A1-12 含合适建筑，更未证明竖墙有 2cm 有效像素或窗可数清**；2018 年数据页写的是 7.5cm，不可混用。

香港数据可保留为“按栋取件”的压力/失败样本池；15 例经过源与转换双视图复核后，若有少数确实可读，再选 1–2 栋即可。没有必要为凑满 L0–L5 继续扩大数量。

## 许可与出处边界

[香港 CSDI 条款原文](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC)授权浏览、下载、分发、复制、链接和打印，并要求署名；条文**未明确写改编**。因此当前文档“许可干净/可放心用于全部场景”过强，派生 BIM 的再发布/产品化权利仍需确认；此处只记录条文，不给法律结论。Helsinki 和 Melbourne 的上述许可来自各自官方页面。香港官方页证实覆盖和纹理，不保证单栋的窗/层线品质。

现有 `sources.md` 把“SUM / SUM Parts 三处官方渠道许可矛盾”合并成一句，需要拆开核实：仓库实际使用的是 [2021 SUM Helsinki C6](https://3d.bk.tudelft.nl/projects/meshannotation/) 的下载，而[GitHub GPL 声明](https://github.com/tudelft3d/SUM-Parts-Benchmarks)与[Hugging Face CC BY-NC 声明](https://huggingface.co/datasets/gwxgrxhyz/SUM-Parts/blob/main/README.md)明确针对**2025 SUM Parts**；[arXiv SUM Parts 页](https://arxiv.org/abs/2503.15300)的“view license”是该论文页面的许可，不足以证明数据集为 CC BY-NC-ND。两种 SUM 不能混同，论文页许可也不是数据许可。2021 C6 原始包的独立权利说明本次仍**未确认**，因此保守不公开转发其原始/派生网格，同时优先直接取市方原件。以上官方页均于 2026-09-20 重新打开；未访问的二级来源/供应商，不作为本次建议的证据。
