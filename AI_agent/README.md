# 轻量 BIM 项目文档

项目目标是把图纸、带表皮体量和后续 CAD 等混合输入转成可用的轻量 BIM。每次会话从 [Agent.md](Agent.md) 开始。

| 要找什么 | 文档 |
|---|---|
| 做什么、做到什么程度 | [产品目标](project/goal.md) |
| 现在做到哪里、下一步做什么 | [路线与当前任务](project/roadmap.md) |
| 图纸路线的工作包、复杂度递进与自动验收 | [详细执行计划](project/drawing_reconstruction_plan.md) |
| 已经确定的选择和原因 | [关键决策](project/decisions.md) |
| 两路输入如何组成同一个产品 | [系统设计](design/architecture.md) |
| 历史好读图如何复用、reading/correction 如何接线 | [读图与校正设计依据](design/reading_correction.md) |
| 共同模型、单位、坐标和编辑对象 | [轻量建筑模型](design/model.md) |
| 已有代码、接口和真实能力缺口 | [现有实现](design/implementation.md) |
| 怎样判断输出有用、完整和可信 | [验证与评价](design/evaluation.md) |
| 怎样开发、维护文档和收工 | [工作方式](workflow/development.md) |
| 用什么模型、哪些调用需要同意 | [模型与费用](workflow/models.md) |
| 怎样启动和检查一个 case | [运行 case](workflow/run_case.md) |
| 怎样让每次会话加载同一上下文 | [会话设置](workflow/session_setup.md) |

`project/` 管目标和推进，`design/` 管系统与实现，`workflow/` 管操作方法。
[logs/](logs/README.md) 保存工作交接、实验和实际运行证据；[archive/](archive/README.md) 集中保存历史原稿、记忆和旧资产。历史资料不参与当前排期。
