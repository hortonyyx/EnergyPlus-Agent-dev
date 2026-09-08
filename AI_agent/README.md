# 项目文档入口

本目录承载整套项目管理方案和所有助手共享的项目记忆。每次会话从 [Agent.md](Agent.md) 开始；当前做什么只看 [plan.md](plan.md)。

## 现行管理

| 入口 | 内容 |
|---|---|
| [初始上下文](Agent.md) | 项目协作、Git 权限、记忆同步与收工约定 |
| [管理体系](management.md) | 文档职责、任务推进、更新和归档方法 |
| [产品范围](project_scope.md) | 通用轻量 BIM、两路输入、混合入口及协作边界 |
| [当前计划](plan.md) | 当前阶段、已有证据、下一步和具体阻塞 |
| [关键决策](decision_log.md) | 已确认选择与后续建议的区别 |
| [操作指南](guides/README.md) | 开发、跑 case、模型配置偏好和会话加载 |

## 技术与证据

| 目录 | 使用方式 |
|---|---|
| [架构](architecture/README.md) | 现有代码链、坐标几何、评测边界；设计建议明确标注 |
| [能力](capability/README.md) | 已有能力和实际缺口，不以测试数替代可用性 |
| [提案](proposals/README.md) | 尚未实现的设计选择；旧规格仅留兼容跳转 |
| [技术参考](reference/README.md) | 可复用方法与源码入口 |
| [暂缓事项](deferred/README.md) | 有明确重启条件的候选工作 |
| [日志](logs/README.md) | 工作交接、实验、审计与原始证据 |
| [归档](archive/README.md) | 已替代文档、历史记忆及回退索引 |

`showcase_animation/` 是演示资产，`backup/` 是本地历史副本，二者不管理研发排期。旧日志保留其当时叙述，不覆盖现行文件。
本轮逐份核对和处置结果见 [管理体系重建记录](logs/worklog/2026-09-08_management_rebuild.md)。
