# 单张照片到 BEM：Fig. 15 截图记录

记录日期：2026-10-11。证据范围：用户截图、作者官方网站摘要与公开配图、官方配套仓库。已确认截图对应的研究，尚未取得论文全文。此图不在同次提供的 [Lee & Yoon PDF](../lee-yoon-2026-agentic-bem/README.md) 中。

## 原件与出处核实程度

- 本地图片：[figure-15.png](figure-15.png)，1,320,952 bytes，逐字节保存用户附件；只在本地保留。
- SHA-256：`4f24dd51e949bcd24596468c4fbcec9b8c63fb18fff6aaa67241be58bff5b597`。
- 对应论文为 Shikang Wen; Qingyan Chen，**An AI-assisted workflow for generative building design and energy modeling: Converting natural language design intent and images into 3D building energy model inputs**。
- [DOI：10.1016/j.aei.2026.105313](https://doi.org/10.1016/j.aei.2026.105313)；[出版社页面](https://www.sciencedirect.com/science/article/pii/S1474034626010050)。
- 已从 [Crossref 元数据](https://api.crossref.org/works/10.1016%2Fj.aei.2026.105313) 核实题名、作者和 DOI；[Elsevier 元数据](https://api.elsevier.com/content/article/PII:S1474034626010050?httpAccept=text/xml) 核实题名、期刊 *Advanced Engineering Informatics*、PII 和标注刊期 January 2027。刊期不等于在线发表日期，当前未核实后者。
- [作者论文页面](https://shikangwen2000.github.io/publication/2026-ai-generative-building-design)已直接读取，题名、作者、DOI 及摘要对应；其引用信息为 *Advanced Engineering Informatics*, 77 (2027), 105313。网站源文件的记录日期为 2026-09-22，不能单独代替出版社在线发表日期。
- 已通过浏览器查看[作者公开的校园建筑重建图](https://shikangwen2000.github.io/images/projects/ai-generative-design/campus-reconstruction.png)：建筑、步骤、颜色标注及两侧 WWR/GFA/EUI 与用户截图一致，确认研究身份。作者公开图不带底部 Fig. 15 图注，正文图号及页码仍待 PDF 核对。
- [官方配套仓库 AI-BEM-Workflow](https://github.com/ShikangWen2000/AI-BEM-Workflow)明确列出该论文题名与作者。本轮通过 GitHub API 核验 main 文件树，只有 `Readme.md`，没有代码、数据或 PDF，不能称为已取得可复现实现。

## 全文查找状态

2026-10-11 已检查出版社文章/PDF 入口、作者网站与公开文件树、官方仓库、OpenAlex 和 Semantic Scholar。两种学术索引提供的开放获取链接均指向出版社，没有独立 PDF 地址；作者网站只提供摘要与 DOI 链接。尚未发现可直接下载的作者稿。

ScienceDirect 的普通请求返回 403，浏览器实际页面显示“Are you a robot?”及人机验证提示，未显示论文正文。没有操作验证挑战、登录、购买或联系作者。公开 Elsevier API 的 PDF 请求返回 406，先前书目读取不含正文。ResearchGate 与 PolyU 检索入口本轮也未成功读取，不能据此断言其中不存在全文。

**当前结果：已确认论文身份与官方入口，尚未下载全文。** 原始 PDF 文件没有创建。下一步可以由用户在[出版社页面](https://www.sciencedirect.com/science/article/pii/S1474034626010050)完成网站验证后获取 PDF，或提供已持有的对应全文。

## 作者摘要与仓库可确认的新增信息

- 摘要确认使用 ChatGPT-image、Hunyuan3D-2.1 及 mesh-to-EnergyPlus 转换；仓库具体提到 GraphSAGE 构件分割。
- 摘要提到用 13,000 栋合成建筑训练网格面分类器，并在多种轮廓、三种尺度及五个中国气候区评估。
- 摘要明确提到通过确定性标定使 GFA/WWR 接近预设目标，但没有给出足以核实 Fig. 15 案例全部输入和标定细节的信息。

上述信息来自作者摘要和仓库说明，不能替代方法、实验与局限章节的全文阅读。

## 截图本身能确认的内容

图示以香港一栋校园办公楼为例，展示以下顺序：

1. 建筑原照片。
2. ChatGPT 去除背景、树木、周边建筑与阴影，并对遮挡部分作生成式补全。
3. ChatGPT 用指定颜色区分窗与外墙：窗 RGB(0, 100, 240)，墙 RGB(255, 30, 45)。
4. Hunyuan3D-2.1 生成三维网格。
5. BEM transformation 转为自动重建的 EnergyPlus 模型。
6. 与手工重建的 EnergyPlus 模型对照。

截图中的提示词是研究材料，不是本项目本轮执行指令。

| 指标 | 图示手工/原设计一侧 | 图示自动重建一侧 |
|---|---|---|
| WWR | 0.56 | 0.56 |
| GFA | 16,315 m² | 16,315 m² |
| EUI | 278.2 kWh/m² | 287.4 kWh/m² |

按图示数值计算，EUI 相对差为 `(287.4 - 278.2) / 278.2 ≈ 3.31%`。该数值只描述图中两个模拟模型的差异，不是实测能耗误差，也不能据此认定几何误差为 3.31%。

## 尚需全文回答的问题

- GFA、WWR、真实尺度、层数分别是输入、人工补充、生成结果还是事后标定？两侧指标相同不能证明从照片自动识别准确。
- BEM transformation 如何分层、识别语义面、闭合空间、处理曲面、修正窗墙与尺度？哪些步骤由规则或学习模型完成？
- 屋顶、背面、遮挡和内部空间采用了哪些推断？如何处理生成图像与原照片不一致？
- 展示结果是否经过人工筛选或多轮重试？样本范围、失败案例、运行时间、成本和输入随机性是什么？
- 模型用于整体热工体量还是房间级源 BIM？相同的 GFA/WWR 与相近 EUI 如何对应到几何、拓扑及空间布局质量？

## 对纯照片路线的初步判断（项目建议，尚未定案）

**2026-10-11 后续讨论：** 用户倾向先由照片生成 textured mesh，再复用成熟的 mesh 处理方法，以降低直接从照片编写 BIM 的能力要求。信息较少时可考虑一层一个源空间块。用户随后明确将照片路线及细度调整留待讨论；这不是本轮默认政策或实现要求，未调用生成服务，也未改变现有规整/空间合并规则。当前决策与待讨论项见 [项目策略](../../AI_agent/project/model_and_input_strategy.md)。下文保留初步技术分析，不据此开启另一套生产流程。

“纯照片”描述输入模态，不自动表示全部内容都需要推断。照片中的轮廓、层线、窗型和重复关系仍是观测依据；绝对尺度、背面、遮挡与内部布局可能需要外部信息或明确假设。多视角输入也会改变可约束的范围。

建议将任务暂称为**照片约束下的建筑推断与参数化建模**。原图及其观测持续保留；补全图和生成网格是建筑假设，后续转换不能把它们的全部细节重新解释为实测证据。

可在独立原型中比较两种实现方法，之后按表现选择或组合：

- 直接路线：照片观察 → 建筑形态与空间假设 → 参数化源 BIM → 原图视角/几何/关系核验。
- 经过 mesh 的路线：照片生成候选 mesh → 复用稳定后的 mesh 分析方法 → 参数化源 BIM → 同类核验。

生成 mesh 可以帮助形成复杂外形候选，但不是所有照片输入的必经阶段。摄影测量/实景 mesh 与生成 mesh 可以共用几何工具，证据来源与尺度可信度仍须保留。简单形体可能直接参数化更快、更可控，具体收益需要实测。

先追求一个合理、完整、可编辑且与已知信息一致的源 BIM；对关键且证据不足的选择记录假设，必要时再提供少量方案。照片约束、推断合理性、结构有效性和下游结果分别评价，避免只用渲染观感或 EUI 接近作为总验收。

当前开发顺序沿用本轮已达成的共识：图纸是 harness 的主验证输入；textured mesh 先独立收敛，再接入并尝试混合输入。本轮照片资料用于讨论，不启动第三套生产流程。
