# C3-T：保存结果契约、返回瘦身、报错修正

状态：开工初稿，尚未验收。基线 `a5baa32d`，工作分支 `dev/astra-c3t-20261005`。按 [派工单](brief.md) 与 [验收 A–E](../../../project/unified_agent_acceptance.md#清理包-c3-t保存结果契约返回瘦身报错修正第二次完整审查后10-05-派出astra) 执行。

全程离线，模型请求 0 次，不用 DeepSeek；仅本分支小步提交，不合入、不推送。历史输入只从证据分支解到本工作树临时目录，原件不改。最终版本与全量合并核对由 Opus 负责。

## 文件边界

本包修改工具脚本（不含 `bim_agent_budget.py`、`bim_agent_guidance.py` 中 C3-R 所属两句时间指引），以及 `runtime_context` 当前稿选择、`runtime_coordinator` 源稿/观察应用/恢复、`runtime_behaviour`、`runtime_tools` 的结果元数据与工具名表、版本登记及对应检查。不修改 C3-R 所属底座、检查点、配置与旧检查。

共享接口核对：底座 `ToolExecutionPayload` 规定正常返回的写调用必须有 `applied_write_id`；这个字段确认持久写入（包括事务审计），不等于几何应用。本包保留该契约，用 `save_effects.audit_written` 与 `save_effects.geometry_applied` 区分，只有后者登记/恢复 `applied-observation`。无需越界改 `src/harness_contracts/` 或 C3-R 检查点；合并时请保留这一区分。

## 验收进度

| 项目 | 实施与核验 | 状态 |
| --- | --- | --- |
| A 保存结果契约 | `saved_candidate`＋`save_effects` 共用契约；事务复用普通修订反馈与图像，状态读取及源稿计数共用兼容读取器。成功、全部失败、部分成功、真实压缩再恢复及纯备注不算几何应用反例通过 | 已实现，综合核验待 E |
| B 冗余返回 | 去 schema title；剖面/修订/高度覆盖/精度摘要，全文可读回；四项文字及三类历史返回字符数 | 待做 |
| C 报错修正 | 对象、缺失字段与最小格式；A1 sm25 四次修订重放 | 待做 |
| D 三列口径 | 调用报错／领域未成功／可用源稿；两次 27B 重算（A2 后预期 0／2／1） | 待做 |
| E 版本与检查 | 保留旧登记；两底座三例逐字节核对；引用改动模块的全部检查 | 待做 |

## 检查与提交

启动检查：工作树干净，分支和基线正确；C3-R 独立工作树存在。已阅读 `AI_agent/Agent.md` 与完整派工单，继续加载指定项目上下文和审查证据。

后续在此记录实际命令、结果、字符数、提交与未完成项，不以离线通过宣称真实模型质量已验证。

- A 定向检查：`PYTHONPATH=/root/worktrees/astra-c3t python -m pytest -n 2 -s --basetemp=.tmp_c3t/pytest_contract3 tests/test_bim_cleanup_c3t.py tests/test_bim_claim_transactions.py tests/test_stage1_behaviour.py`，**26 通过，8.42 秒**（[日志](validation/contract3.log)）。
- 五份历史运行已解到 `.tmp_c3t/history/`，压缩包及 **10,230 文件**哈希全部核对；索引见 [evidence_sources.json](evidence_sources.json)。原证据未改。
