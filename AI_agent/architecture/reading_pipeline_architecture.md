# 图纸路线：观测到几何

实现核对基线：`461dfc98`。本文说明现有代码，下一步工作看 [计划](../plan.md)。

## 当前入口真正做什么

`run_stage.py` 的 `_draw_reading` 是手工产物入口：读取并检查预先生成的 `*_view.json`，不负责调用视觉模型从原图生成观测。因此只有 `flow` 命令不等于完成冷启动识图；上游观测生成需要另行执行和记录。
[reading 目录](../../src/agent/reading/) 保存识别、隔离工具、CV 处理与观测类型，当前尚不能把这些模块的存在等同于一个完整自动入口。

`_w1_route_correction` 按观测契约选择 legacy 或 as-drawn 路径。当前 plan v2 和 elevation v0 可适配；旧 plan v0 不能因为 schema 可读就宣称生产链已消费。具体分类看 [vector_contract.py](../../src/agent/reading/vector_contract.py)。

## 处理职责

| 层次 | 职责与限制 |
|---|---|
| 原始素材/观测 | 保留图像、可见线条、尺寸文字、标定和引用；观测与解释分开 |
| reading 检查 | as-drawn 走契约、标定与尺寸链检查，旧字段逐项 NA；来源引用还需由校正等消费者验证，独立像素自检未全部自动接入 |
| correction | 从证据产生坐标、整合冲突、多层协调；有图纸尺寸和纯像素等不同证据条件，不能把某一种精度强加所有输入 |
| as-drawn 接线 | CLI 已调用多层校正、补窗及 finalization；“CLI 零接线”“仍然全部 windows=[]”已过时 |
| 窗与门 | 当前补窗可生成 window；门等未分类对象留台账，不能宣称已完整生成通用 BIM 开口 |
| 朝向 | 现有逻辑能接受候选或明确假设；manifest 的枚举槽不等于多源自动识别/仲裁已实现 |
| 输出 | `CorrectedGeometry`/V3 交给确定性几何内核；质量仍取决于输入完整性和未解决冲突 |

实现入口：[CLI](../../scripts/tool_scripts/run_stage.py)、[pipeline.py](../../src/agent/pipeline.py)、[correction](../../src/agent/correction/)、[as_drawn_windows.py](../../src/agent/correction/as_drawn_windows.py)。

## 保留与演进

既有观测产物可用于工程重放，报告要区分这与新模型从原始图纸生成。图纸路线的 schema 是可复用资产，外部体量和 CAD 无需伪装成平立面观测。
新增输入在自己的适配器处理原始信息，再进入共同的坐标、几何、来源与假设表达。不要把 GT 编译/精修工具写成生产输入的前置。
当前 projection bridge 的 outer_skin 分支尚未实现，几何 complete 也不证明房间全部读出；窗位置路线②的 citation 仍有 shadow 阶段，不能把整份旧提案当成已接通。
完整操作与前置见 [case 指南](../guides/new_case_guide.md)，当前 case 数量、失败和下一步只维护在计划。
