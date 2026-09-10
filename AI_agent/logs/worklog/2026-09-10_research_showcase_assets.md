# 课题汇报：sm25 与 Voimatalo 展示资产

用户认可七页安排后，要求先制作两个可嵌入 HTML 成果；进一步明确选 Voimatalo，主助手 SOTA 直接试做，按相对高精度 BIM 的目标探索。已完成[资产入口](../../../showcase/2026-09-11-research-report/assets.html)，完整 slides 仍待制作。

## 交付

- [sm25](../../../showcase/2026-09-11-research-report/demos/sm25/sm25_showcase.html)：基于既有辅助模型，29 空间/31 窗/30 门。二层两条观察经展示复核解释为同一门的两侧，增加一樘 0.8067 m 门洞，完整落在两个实际共墙宿主并各扣除 1.69407 m²。保留原 31 窗、29 门、原始未建记录与 severe 状态，单独记录人工展示修订。
- [Voimatalo](../../../showcase/2026-09-11-research-report/demos/textured-mass/index.html)：直接判读真实 GLB/UV，经量测立面生成外壳与楼层版（12 空间体）和较细的内部推理方案（164 空间体），均有八层主楼及 316 窗组。真实贴图、BIM、同坐标叠合可切换；可看典型层、展开、量测和源 JSON。
- [旧展示](../../../showcase/previous-showcase/prototype/index.html)：从 `AI_agent/archive/showcase_animation/` 整体迁入 `showcase/previous-showcase/`，内容不改。入口与当前索引引用更新。

## 实验性质与边界

sm25 是既有辅助成果的展示副本，不能计自动冷启动成功。Voimatalo 是主助手直接判读加确定性代码的高细度探索，内部为明确假设，不能说恢复了 164 个真实房间；门窗细节、屋顶曲面、坡地及遮挡仍有近似。端部缺失网格没有被当作无窗证据，模型以 unknown 灰色边界保留。模型目标是较高信息质量，但没有独立精度或仿真评价证明达到用户的研究目标。

Voimatalo 本次未调用其他产品模型、订阅或付费模型 API，不涉及 DeepSeek。sm25 与目录页由 Terra 开发子助手按项目模型分配偏好制作，主助手复核后纠正过一次错误的三宿主门解释。该委派不属于生产 Agent 实验。本次用户对 SOTA 的选择仅适用于展示探索，不改变 Sonnet 级生产运行上限。

## 验证与后续

sm25 离线检查已实际验证旋转、楼层过滤、两种展开、门洞宿主和面积扣除；详见[证据](../experiments/2026-09-10_showcase_sm25/README.md)。Voimatalo 两版源几何/接触/门窗宿主无严重问题，仅有明确未知围护 warning；七个截面覆盖方案轮廓一致。两版打包页面离线加载完整贴图，模式切换、典型层楼板显示、展开与工具面板通过，无页面异常或外部请求，见[探索记录](../experiments/2026-09-10_showcase_textured_mass/README.md)。这些是几何自洽和展示检查，不等于实际建筑保真或仿真通过。

此次未改产品核心、GT、原始模型输入或历史运行产物，正常还原主线保持 run13 的交接状态。下一步可将两份资产嵌入已认可的七页汇报；第六页用 Voimatalo 表达真实体量输入到可查看/可修改空间模型的探索，明确内部分隔是推理方案。EnergyPlus 在总架构中可标已有接通经验，本次资产没有新 EP 运行，不能宣称当前两份源 BIM 已直接通过仿真。
