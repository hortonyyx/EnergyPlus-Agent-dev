# 图纸 → 建筑模型生成：研究现状、业界做法与"伪建模 vs 真三维"路径

> **术语对照（2026-06-10 改名后）**：本文历史叙述沿用旧称——phase1=0_reading（识图）/ phase2a=1_correction（校正）/ phase2b 已拆为 2_modelling+3_split_pairing（几何，代码内核）+4_mep（物理）+5_intakeoutput（装配）；代码模块 `src/agent/pipeline.py`（`run_pipeline`）。详见 [pipeline_stage_contracts.md](../architecture/pipeline_stage_contracts.md)。

> **定位**：回答 2026-05-29 用户的研究性提问——目前有没有"给定图纸→生成建筑模型"的相关研究？业界怎么做？本项目本质是"伪建模"，真三维生成的实现路径是什么？这套流程会被快速淘汰吗？
>
> **性质**：外部研究/技术现状参考（不是本项目设计决策）。供定位本项目在研究/业界版图中的坐标、识别可借的现成轮子与可防御的 niche。
>
> _基于 2026-05 web 检索 + 模型知识整理。具体系统名/会议见文末 Sources。_

---

## 0. 先校准用词："伪建模"其实不准

你把当前做法称为"伪建模"，但更准确的说法是：**你在做 BEM（建筑能耗模型），不是在做 BIM（建筑信息模型）。这是两个不同且都合法的目标，不是"真"与"假"。**

| | BEM（你的目标） | BIM / 3D 语义重建（"真三维"） |
|---|---|---|
| 产物 | 热区 + 围护 + 负荷，喂仿真 | 完整几何 + 语义（墙/门/窗作对象）+ IFC |
| 几何精度诉求 | 定性正确 + 面积/WWR ±5%（[capability §1](../capability/recognition_modeling_capability.md)） | 逐构件精确、可施工/可交付 |
| 抽象成积木块 | **正确做法**（EP 本就是热区积木） | 不可——要保留真实构件 |
| 对应你的腿 | **再拓扑 leg** | **忠实建模 leg**（更靠这边） |

所以"积木块抽象"在 BEM 语境下**不是伪，是对的**——这正是 OpenStudio / DesignBuilder 等专业 BEM 工具的标准抽象。把它叫"伪建模"会低估自己。真正的"真三维"是另一个产品目标（BIM 重建），不是"更高级版的你"。

---

## 1. 业界 / 研究的三大流派

### 1.1 CV 几何流水线（raster → vector → 3D）——最成熟

**做法**：栅格平面图 → 语义分割（墙/门/窗/房间）→ 矢量化 → 多边形/图 → 升起 3D。

- **数据集**：CubiCasa5K（5000 张平面图，SVG 矢量标注，80+ 语义类，源自芬兰房产图）；R2V；FloorPlanCAD。
- **方法演进**：Raster-to-Vector（Liu, ICCV 2017）→ DeepFloorplan → Floor-SP → **HEAT**（CVPR 2022，先检测角点再分类边，缺角/缺边导致房间多边形不闭合）→ **RoomFormer**（CVPR 2023，Transformer 双层 query，单阶段同时输出多个角点序列）→ **PolyRoom**（ECCV 2024，room-aware Transformer，均匀采样表示解决闭合性）→ **FRI-Net**（ECCV 2024，room-wise 隐式表示）。亦有"Automatic Reconstruction of Semantic 3D Models from 2D Floor Plans"（2023）。

> **关键对照**：这条线本质是"**感知 → 矢量化 → 升起**"——和你的两步法（phase1 矢量 + phase2 建）**同构**。你不是落后于主流，你的两步结构就是主流结构。

**局限**：在**干净、风格单一**的图（如房产标准图）上训练；对**杂乱/异风格/噪声/非标准**真实图纸泛化弱；**不做尺寸链仲裁**，也**不产仿真合法几何**（输出是矢量平面，不保证 EP 水密、不分热区）。

### 1.2 BIM-to-BEM（你真正所在的领域）——工程化成熟但有损

**标准业界管线**："CAD/BIM（Revit）→ gbXML/IFC 导出 → 导入 OpenStudio / DesignBuilder / IES-VE → 热分区 → EnergyPlus IDF"。

- **工具**：OpenStudio（+ FloorspaceJS / geojson 画图入口）、Autodesk Revit → Insight / Green Building Studio、DesignBuilder、各种 gbXML→EnergyPlus translator。
- **已知痛点**（多篇综述/案例实证）：互操作性有损——BEM 体积比 BIM 源**小到 7.5%**、围护构件丢失；需大量手工清理；**热分区仍半人工**。自动热分区（周边/核心、ASHRAE 90.1）是活跃研究题。

> **关键缺口**：成熟管线**从 BIM/CAD（已结构化）起步，不吃 raster 图纸**。"**raw 真实图纸 → BEM**"（跳过 BIM 这步）这一段**少有人好好做**——这是你的 niche（见 §3）。

### 1.3 生成式（text/LLM → floorplan）——不同任务，别混

- HouseGAN / HouseGAN++、HouseTune / HouseLLM（LLM+diffusion，文本→布局，2024-25）、ChatDesign、ZURU（Claude 3.5 Sonnet + Llama 微调做 text-to-floorplan，宣称指令遵从 +109%）。
- 这些是**从文本/约束生成新布局（设计）**，不是**重建已有图纸**。和你的任务（重建一张**已存在**的图）是**不同任务**，别拿来对标。
- **重要 caveat**：有研究实测 GPT-4V / Gemini 在**空间可视化**（地图、平面图）上的物体定位 / 多步空间推理**接近随机**——这是 phase1 用通用 VLM 的真实风险点，值得纳入评测。

---

## 2. "真三维生成"的实现路径（taxonomy）

你问"真正实现三维生成大概什么路径"。澄清四条路，并指出哪条适合**精确量纲**建筑：

| 路径 | 做法 | 适合 | 不适合 |
|---|---|---|---|
| **a. CV 几何流水线（确定性）** | 分割+矢量化+升起 | 干净平面图→3D | 噪声/异风格图、仿真合法性 |
| **b. 程序化/参数化几何内核（CAD kernel）** | 建在 OpenStudio SDK / IFC toolkit / 自写内核上，确定性升起+布尔（intersect/match） | **精确量纲建筑、IFC/BEM** | 需结构化输入（zone/footprint） |
| **c. 扫描→BIM（point cloud）** | 语义分割点云→procedural→IFC（如 Cloud2BIM、ODA Scan-to-BIM SDK） | 实测既有建筑 | 输入是点云不是图纸 |
| **d. 神经 3D 生成（diffusion / NeRF / 3D-GAN）** | 生成 free-form 形状/场景 | 概念/艺术/室内场景 | ❌ **精确量纲建筑（不尊重尺寸）** |

> **必须破除的误解**："真三维生成" ≠ 神经生成（路径 d）。对**精确量纲**的建筑 / BEM，主流"真三维"是 **a + b 的确定性几何路径**（感知 → 矢量 → 程序化升起 + 布尔），**不是** diffusion / NeRF——后者不尊重尺寸，做不了能耗模型或可交付 BIM。
>
> **所以对你的领域，"真三维" = 确定性几何内核——正是你的再拓扑 leg（[geometry_first_zonification.md](../architecture/geometry_first_zonification.md) 路径 b）。你离它不远，它已在你的路线图上。**

---

## 3. 你这套会被快速淘汰吗？（诚实评估）

**架构层面：不会。** 你的两步法（VLM 感知 → 结构化矢量中间层 → 拓扑推理 → 建模）与 CV 主流（raster→vector→3D）**同构**，且 LLM-orchestrated 这条还很新——**你在前沿，不在落后区**。

**会快速变的：phase1 感知这一环。**
- 专用 floorplan 模型（RoomFormer / PolyRoom）在**干净标准图**上已很强；通用 VLM（Claude / GPT）在**杂乱/异风格/真实图**上泛化更好但精度待追。
- phase1 大概率会被"更强的 VLM"或"专用模型"替换——**但两步结构（感知→推理→建）存活**，被换的是组件不是骨架。

**持久的（护城河要素）**：误差预算分离、结构化矢量中间层、确定性几何内核、BEM 热区抽象——全与工业/研究一致，是正确的长期赌注。

**真正的风险不是"架构被淘汰"，而是三点工程现实**：
1. 感知做得不如专用模型 → 要么 VLM 泛化打赢杂图，要么直接接专用模型（如 RoomFormer 起稿 + VLM 补杂图）。
2. 没有确定性几何内核 → **再拓扑 leg 正解此**。
3. 工具生态落后 OpenStudio / Revit → **别重造轮子**，可借 idfpy / OpenStudio SDK 的 intersect-match。

**可防御的 niche（最重要的结论）**：
> **"杂乱真实图纸 → 仿真就绪 BEM"。** CV 重建从干净图做、且不出 BEM；BIM-to-BEM 从已有 BIM 做、不吃 raw 图；生成式做 design 不做 recon。**"raw 真实图 → 仿真合法 BEM"这条几乎没人深耕**——你的"VLM 泛化（吃杂图）+ 尺寸链仲裁（纯 CV 不做）+ 几何内核（出仿真合法几何）"组合正好填这个空。

---

## 4. 对本项目两腿的映射

| | 对应研究流派 | 护城河 | 可借/可对标 |
|---|---|---|---|
| **忠实建模 leg** | floorplan-to-BIM 重建（§1.1） | VLM 对杂乱/异风格/噪声真实图的泛化 + 尺寸链仲裁（纯 CV 不做） | 用 **CubiCasa5K** 等做评测对标；可借 RoomFormer/PolyRoom 思路或模型起稿 |
| **再拓扑 leg** | "真三维"确定性路径 a+b（§2）+ BIM-to-BEM 自动分区（§1.2） | 从 raw 图**自动热分区**（skip BIM） | 借 **OpenStudio SDK intersect/match**、gbXML 工业实践、idfpy 几何 mixin |

---

## 5. 一句话回答你的四问

1. **有相关研究吗 / 怎么做**：有，且成熟。三流派——CV 几何重建（RoomFormer 等，与你同构）、BIM-to-BEM（OpenStudio/gbXML，你的领域，但从 BIM 起步不吃 raw 图）、生成式（text→layout，不同任务）。
2. **"伪建模"准吗**：不准。你做的是 **BEM**，抽象成热区积木**是对的**，不是假。"真三维"是另一目标（BIM 重建）。
3. **真三维实现路径**：对**量纲建筑** = **确定性几何内核**（感知→矢量→程序化升起 + 布尔），**不是**神经生成。正是你的**再拓扑 leg**，你离它不远。
4. **会被快速淘汰吗**：架构不会（与主流同构、属前沿）；会变的是 phase1 感知组件（可换更强 VLM/专用模型），两步结构存活。**可防御 niche = 杂乱真实图 → 仿真就绪 BEM，这块少人深耕。**

---

## Sources

- [RoomFormer (CVPR 2023)](https://github.com/ywyue/RoomFormer)、[Connecting the Dots: Two-Level Queries (CVPR 2023)](https://openaccess.thecvf.com/content/CVPR2023/papers/Yue_Connecting_the_Dots_Floorplan_Reconstruction_Using_Two-Level_Queries_CVPR_2023_paper.pdf)
- [PolyRoom (ECCV 2024)](https://github.com/3dv-casia/PolyRoom)、[FRI-Net (ECCV 2024)](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/04606.pdf)
- [Automatic Reconstruction of Semantic 3D Models from 2D Floor Plans (2023)](https://arxiv.org/pdf/2306.01642)
- [CubiCasa5K 数据集](https://github.com/CubiCasa/CubiCasa5k)、[CubiCasa5K 论文](https://arxiv.org/pdf/1904.01920)
- [BIM↔BEM 互操作性综述](https://www.mdpi.com/2076-3417/11/5/2167)、[BIM→BEM 优化转换](https://www.mdpi.com/2075-5309/14/8/2444)、[开源 gbXML→EnergyPlus translator](https://www.researchgate.net/publication/335680180_A_New_BIM_to_BEM_Framework)
- [什么软件能从 CAD/BIM 生成能耗模型 (Unmet Hours)](https://unmethours.com/question/256/what-software-can-generate-an-energy-model-from-cad-or-bim/)、[Autodesk 把 EnergyPlus 带进 Revit (DOE)](https://www.energy.gov/cmei/buildings/articles/autodesk-brings-detailed-energyplus-hvac-simulation-revit)
- [Procedural Point Cloud Modelling in Scan-to-BIM 综述](https://www.mdpi.com/2220-9964/12/7/260)、[Cloud2BIM 开源点云→IFC (2025)](https://arxiv.org/html/2503.11498v1)
- [HouseTune/HouseLLM: LLM-assisted 两阶段 floorplan 生成 (2024-25)](https://arxiv.org/abs/2411.12279)、[ZURU text-to-floorplan (Claude 3.5 + Llama)](https://www.zenml.io/llmops-database/text-to-floor-plan-generation-using-llms-with-prompt-engineering-and-fine-tuning)、[多模态模型空间可视化理解 (SVG 分解研究)](https://arxiv.org/pdf/2511.03478)
