# 09-09 开工：图纸重建计划

## 本轮范围与结果

用户要求正式推进两条路线中相对精准建模的一条，先梳理计划；现有项目库作为资产，不必拘泥，不重复造轮子，疑点允许实验推进。

本轮完成启动阅读、代码与样本定向核对，形成 [图纸重建计划](../../project/drawing_reconstruction_plan.md)，同步当前任务、决策与总目录。未修改业务代码，未运行新 case、模型调用或 EP 实验。

## 核对依据

- 开工主树 `main`，HEAD `fa5c13d2`，工作区干净；仅一个 worktree，近期提交为管理整理与交接。
- 已完整读取 Agent、目标、roadmap、开发方式；按目录读取架构、模型、实现、评价、case 运行与模型费用约定。
- 代码确认 `run_stage._draw_reading` 检查预生成观测，`_draw_modelling` 调用内核；build 已含切配，`_draw_split_pairing` 重新构建并核对序列化。
- 读图工具箱已有 pens/ruler/faces/pairs/gaps/build；CV 有裁图、标定、墙/层线及窗候选工具。隔离执行器有 build/spawn/merge，启动逻辑使用 Claude CLI；未验证其当前工具依赖和 as-drawn 整体兼容。
- 直接读取 sm25 旧 `building_geometry.json`，字段计数为 27 zones、27 zone_meta、208 surfaces、31 windows；checks 的两个失败面及 0.065 m 短边与交接一致。检查实现定位到 `src/validator/interzone.py`，本轮未验证 EP 是否拒绝该几何。
- sm25 原始输入为两张平面及四张立面，sm24 为一张平面及四张立面。sm25 声明的 `thermal_zones` 为 14/15，sm24 为 8；这不直接证明源房间分母，须结合图纸逐对象核对。未向生产生成器输入 GT。
- 现有查看器是离线 HTML 生成器；本轮只核对源码，没有生成或浏览新模型，也没有宣称编辑回写已实现。

## 验证与下一步

本轮仅文档变更，验证范围为 diff、受影响 Markdown 本地链接和 Git 状态，不运行 pytest 全量。已检查六份变更文档的 60 个本地链接，均可解析到现有路径。新计划区分已实现资产、实施建议、历史重放与尚待实验结论。

下一步从 sm25 可视基线和对象去向核对开始，再做目标档读图实验。阶段交付、实验条件和完成依据集中在计划正文，不在此复制任务清单。
