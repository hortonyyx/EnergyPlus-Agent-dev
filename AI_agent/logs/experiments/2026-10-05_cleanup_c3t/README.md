# C3-T：保存结果契约、返回瘦身、报错修正

状态：A–D 已实施并完成历史重放；E 版本与综合核验进行中。基线 `a5baa32d`，工作分支 `dev/astra-c3t-20261005`。按 [派工单](brief.md) 与 [验收 A–E](../../../project/unified_agent_acceptance.md#清理包-c3-t保存结果契约返回瘦身报错修正第二次完整审查后10-05-派出astra) 执行。

全程离线，模型请求 0 次，不用 DeepSeek；仅本分支小步提交，不合入、不推送。历史输入只从证据分支解到本工作树临时目录，原件不改。最终版本与全量合并核对由 Opus 负责。

## 文件边界

本包修改工具脚本（不含 `bim_agent_budget.py`、`bim_agent_guidance.py` 中 C3-R 所属两句时间指引），以及 `runtime_context` 当前稿选择、`runtime_coordinator` 源稿/观察应用/恢复、`runtime_behaviour`、`runtime_tools` 的结果元数据与工具名表、版本登记及对应检查。不修改 C3-R 所属底座、检查点、配置与旧检查。

共享接口核对：底座 `ToolExecutionPayload` 规定正常返回的写调用必须有 `applied_write_id`；这个字段确认持久写入（包括事务审计），不等于几何应用。本包保留该契约，用 `save_effects.audit_written` 与 `save_effects.geometry_applied` 区分，只有后者登记/恢复 `applied-observation`。无需越界改 `src/harness_contracts/` 或 C3-R 检查点；合并时请保留这一区分。

## 验收进度

| 项目 | 实施与核验 | 状态 |
| --- | --- | --- |
| A 保存结果契约 | `saved_candidate`＋`save_effects` 共用契约；事务复用普通修订反馈与图像，状态读取及源稿计数共用兼容读取器。成功、全部失败、部分成功、真实压缩再恢复及纯备注不算几何应用反例通过 | 已实现，综合核验待 E |
| B 冗余返回 | 去 schema title；剖面/修订/高度覆盖/精度摘要，全文可读回；历史源、图像与完整诊断核对一致（仅新增保存契约与变化标记） | 历史重放通过 |
| C 报错修正 | 对象、缺失字段与最小格式；A1 sm25 第 69/71/73/81 步定位 D2_pass 缺 z，原有编译错误保留 | 四次重放通过 |
| D 三列口径 | 调用报错／领域未成功／可用源稿；两次 27B 重算为 2／3／6 与 0／2／1 | 通过 |
| E 版本与检查 | 保留旧登记；两底座三例逐字节核对；引用改动模块的全部检查 | 待做 |

## 检查与提交

启动检查：工作树干净，分支和基线正确；C3-R 独立工作树存在。已阅读 `AI_agent/Agent.md` 与完整派工单，继续加载指定项目上下文和审查证据。

后续在此记录实际命令、结果、字符数、提交与未完成项，不以离线通过宣称真实模型质量已验证。

- A 定向检查：`PYTHONPATH=/root/worktrees/astra-c3t python -m pytest -n 2 -s --basetemp=.tmp_c3t/pytest_contract3 tests/test_bim_cleanup_c3t.py tests/test_bim_claim_transactions.py tests/test_stage1_behaviour.py`，**26 通过，8.42 秒**（[日志](validation/contract3.log)）。
- 五份历史运行已解到 `.tmp_c3t/history/`，压缩包及 **10,230 文件**哈希全部核对；索引见 [evidence_sources.json](evidence_sources.json)。原证据未改。
- B/C 和追加边界检查：定向 35 项通过；补充精度变化保存、物理连接签名后，含委派检查共 44 通过、10 因尚未登记新版本被保护性拒绝。登记后重新跑引用改动模块的整文件集合。

## 返回字符数

字符按 Unicode 计；同一重放脚本、同一序列化口径比较 `a5baa32d` 与本包。修订与剖面统计完整 MCP 文本，精度段统计紧凑 JSON。详见 [comparison.json](comparison.json)、[before.json](before.json)、[after.json](after.json)。

| 项目 | 改前 | 改后 |
| --- | ---: | ---: |
| 系统指引 | 9,610 | 9,606 |
| 全部 43 工具说明 | 16,329 | 16,688 |
| 全部参数结构 | 16,561 | 11,792 |
| 常用参考说明 | 15,706 | 15,693 |
| 四项合计 | **58,206** | **53,779** |
| 默认 32 工具四项合计 | 53,121 | 49,767 |
| A4-T sm25 第 118 步 revise_bim | 65,788 | 44,875 |
| 27B A2 后 34 次剖面合计 | 185,429 | 80,065 |
| 新底座 GLM sm24 精度 | 1,493 | 781 |
| 新底座 GLM sm25 精度 | 7,762 | 6,163 |
| Claude Code GLM sm24 精度 | 1,495 | 782 |
| 27B 首轮 sm24 精度 | 1,494 | 772 |
| 27B A2 后 sm24 精度 | 1,494 | 772 |
| 五份精度合计 | **13,738** | **9,270** |

剖面的阈值、实际候选、空结果诊断和计数仍返回，重复说明移入工具说明，辅助区间进可读回全文。修订只列变化对象/字段；同提交完全一致的操作不再回显。高度覆盖只省略“没有依据、也没有独立问题”的逐项重复，未绑定总数保留。精度报告按异常/新增/不变/已解决分组，共用墙线表；取消原来 8 项异常与 4 项墙位置截断，所有异常可见。历史缺少父稿精度报告时明确写未比较，不臆造变化。

三列报告见 [首轮](behaviour/sm24_qwen27b_paratera/timeline.md) 与 [A2 后](behaviour/sm24_qwen27b_after_a2/timeline.md)，生成脚本调用现有生产报告模板。部分事务可同时贡献“领域未成功”和实际保存稿，调用报错不重复计入领域未成功。
