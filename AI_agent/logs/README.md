# 工作记录与运行证据

当前任务看 [路线与任务](../project/roadmap.md)，运行方法看 [case 指南](../workflow/run_case.md)。这里保留实际执行证据，历史要求不自动生成新任务。

- [worklog](worklog/README.md)：按日期保存交接和变更理由。
- [experiments](experiments/)：输入分析、诊断、运行产物、历史审计与当前实验。
- [reviews](reviews/)：旧请求/执行/裁决及相关证据，不要求新任务沿用这套角色结构。
- `runtime/`：主程序的运行日志目录，按实际运行产生。
- [下游修改历史](downstream_agent_changes.md)：按需查证历史实现。

保留 logs 的依据是内容和实际消费者：主程序在此写运行日志，多项测试/GT 工具读取 experiments，个别回归读取 reviews 下的 JSON。它们不是旧管理入口的兼容壳，移动这些数据需要单独处理真实代码依赖。
新记录足以定位输入、版本、命令/配置、模型与人工参与、结果和未验证范围即可。重要产物保持原样，不为整理导航改写过去的运行结果。
