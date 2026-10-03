# R1 实施与交付入口

派工人 Opus；Astra 牵头，基准 `e123046d`，工作分支 `dev/astra-r1-20261003`。
2026-10-03 05:41 UTC 开始，按约 100 分钟收尾；本目录不会改变正式验收记录。

本包已完成，Astra 自评 A–E 达到派工交付条件，等待 Opus 验收。完整说明见
[交付报告](delivery_report.md)。本轮只做派工单 A–E，没有运行整案、合入 main 或 push。

| 工作项 | 当前状态 |
| --- | --- |
| A 格式补救 | 同一子任务最多一次额外请求；真实旧失败双反例、无预算、恢复和串引用拒绝均通过，见[报告](format_repair.md) |
| B 同时派发 | 默认并发 4，可配置；冻结工具串行，失败隔离、根账上限、最终收据及旧结果拒绝均通过 |
| C 四立面对照 | 9 请求、126,977 token；并发 190.234 秒、依次 479.117 秒；两组窗高 11/11、数窗 4/4，见[结果](facade_report.md) |
| D 实测准备 | GLM 校准 5 请求、6,359 token；两份配置就绪；输入上界覆盖不代表含思考的总量覆盖，见[限制与配置](preparation.md) |
| E 联合回归 | 短联合 252、长故障 10、真实工具 75 步相关 3 项，共 265 项通过，见[验证清单](validation.json) |

原始运行已无损保存到 [compact 归档](facade_evidence.compact.tar.xz)，464,716 bytes。
原图按仓库路径和哈希引用；[独立审计](facade_evidence_verification.json)核对完整事件、
父子关系、9 次预留/结算、请求原字节、图像、票据以及从原答案重算的评价。
两个原始 run_id 同名，按独立归档根联合标识，原事件未改写。临时运行和测试目录已清理。
开发子代理三名，均 `gpt-5.6-sol/high`；用量接口未提供。Astra 负责并发实现、集成、实测组织和交付核对。

本批请求账本在立面 9/20、GLM 校准 5/5 处结束，不得追加抽样。后续仅由 Opus
验收本包，再提请用户批准迁移对照或首批整案。GLM 的总输出计量问题、长上下文
覆盖不足和部署参数差异见交付报告；没有未完成的本包实现项。

删除临时目录后仍可完全离线复核（从归档读取原票据，不调用模型）：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r1/verify_evidence.py \
  --archive AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_evidence.compact.tar.xz \
  --out AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_evidence_verification.json
```

[全部改动文件](changed_files.txt)；[实现与验证提交](commits.txt)。
