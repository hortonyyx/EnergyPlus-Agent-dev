# C3-T：保存结果契约、返回瘦身、报错修正

状态：**A–E 离线验收全部通过，交付完成**。最终 Agent 版本 `t1-20261005-c3t.3`；53 个检查文件共 505 项全部通过，无失败或跳过。基线 `a5baa32d`，工作分支 `dev/astra-c3t-20261005`。按 [派工单](brief.md) 与 [验收 A–E](../../../project/unified_agent_acceptance.md#清理包-c3-t保存结果契约返回瘦身报错修正第二次完整审查后10-05-派出astra) 执行。

全程离线，模型请求 0 次，未用 DeepSeek；仅本分支小步提交，未合入、未推送。历史输入只从证据分支解到本工作树临时目录，结束时已再次核对全部原件哈希并删除临时副本。合并后的全量核对及共同版本登记由 Opus 负责。本包没有待补实现，不以离线检查宣称真实模型出模质量已验证。

## 文件边界

本包修改工具脚本（不含 `bim_agent_budget.py`、`bim_agent_guidance.py` 中 C3-R 所属两句时间指引），以及 `runtime_context` 当前稿选择、`runtime_coordinator` 源稿/观察应用/恢复、`runtime_behaviour`、`runtime_tools` 的结果元数据与工具名表、版本登记及对应检查。不修改 C3-R 所属底座、检查点、配置与旧检查。

共享接口核对：底座 `ToolExecutionPayload` 规定正常返回的写调用必须有 `applied_write_id`；本包保留这个运行层回执，不把它当作几何应用证据。工具层另用 `save_effects.audit_written` 与 `save_effects.geometry_applied` 区分审计和实际应用，只有后者登记/恢复 `applied-observation`。无需越界改 `src/harness_contracts/` 或 C3-R 检查点；合并时请保留这一区分。函数边界、C3-R 的预算文件与整个 `FINISHING` 段未改，见 [边界与登记核对](validation/delivery.json)。

## 验收 A–E

| 项目 | 实施与核验 | 状态 |
| --- | --- | --- |
| A 保存结果契约 | 八个保存入口统一 `saved_candidate`＋`save_effects`；事务复用普通修订反馈与图像，当前稿、调度源稿及行为计数共用兼容读取器。成功、全部失败、部分成功、真实压缩再恢复反例通过；纯备注、用途和朝向证据变化不消费观察，实际几何/连接/角度变化会应用 | 通过 |
| B 冗余返回 | 去 schema title；剖面/修订/高度覆盖/精度摘要，全文可读回；历史源、图像与完整诊断核对一致（仅新增保存契约与变化标记） | 历史重放通过 |
| C 报错修正 | 对象、缺失字段与最小格式；A1 sm25 第 69/71/73/81 步定位 D2_pass 缺 z，原有编译错误保留 | 四次重放通过 |
| D 三列口径 | 调用报错／领域未成功／可用源稿；两次 27B 重算为 2／3／6 与 0／2／1 | 通过 |
| E 版本与检查 | `.3` 登记 57 个文件，旧版本全部保留；sm24/sm25/sm21 两底座逐字节一致；相关 53 文件 505 项全部通过；模型请求 0 次 | 通过 |

## 检查与提交

启动时工作树干净，分支和基线正确；已完整阅读项目上下文、最新交接、派工单及指定审查。开工初稿先提交，随后分步更新。

- **最终整文件检查：53 文件、505 项通过，0 失败、0 跳过，pytest 274.65 秒（含启动 275.45 秒）**。按改动模块名检索，并加入全部 BIM 检查及精度内核检查，范围和命令保存在 [selected_tests.json](validation/selected_tests.json) 与 [结果](validation/related_final.json)；[完整日志](validation/related_final.log.gz)、[JUnit](validation/related_final.xml)。统一 `PYTHONPATH=/root/worktrees/astra-c3t`、`pytest -n 2 -s`，临时目录均在本树。
- **两底座三例一致**：[runner_parity.json](runner_parity.json)。核对系统指引、默认及完整工具目录、名称/说明/参数、任务正文、图像哈希；同范围同起点时间的输入清单除 `provider` 路由字段外逐字节相同。Claude 启动点拦截，新底座使用脚本适配器，真实模型进程与请求均为 0。
- **历史重放**：[comparison.json](comparison.json) 核对源文件、返回图像、全文诊断与剖面分页读回。五份精度输入均与原 `delivery.json` 选中的最终稿相同，见 [delivery.json](validation/delivery.json)。
- **原始证据**：五份压缩包及 **10,230 文件**初始核对、交付前复核均通过；[索引](evidence_sources.json)。原件和证据分支未修改，临时解包及基线代码已清理。
- 最终登记：[registered_final.json](validation/registered_final.json)，源代码提交 `e9c15bba`；`.1`、`.2` 和此前全部版本均保留。

提交顺序：`9db7aac5` 初稿；`82e20098` 保存契约；`8f76e083` 返回瘦身、报错与重放；`4533f79f` 首次登记和底座核对；`5efe898f` 只读读回与历史兼容；`e9c15bba` 朝向依据不冒充几何应用；最终登记、验收证据和本报告随交付收尾提交。

## 返回字符数

字符按 Unicode 计；同一重放脚本、同一序列化口径比较 `a5baa32d` 与本包。修订与剖面统计完整 MCP 文本，精度段统计紧凑 JSON。详见 [comparison.json](comparison.json)、[before.json](before.json)、[after.json](after.json)。

| 项目 | 改前 | 改后 |
| --- | ---: | ---: |
| 系统指引 | 9,610 | 9,606 |
| 全部 43 工具说明 | 16,329 | 16,664 |
| 全部参数结构 | 16,561 | 11,792 |
| 常用参考说明 | 15,706 | 15,693 |
| 四项合计 | **58,206** | **53,755** |
| 默认 32 工具四项合计 | 53,121 | 49,743 |
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

综合检查首轮 **417 项，411 通过、6 失败，278.16 秒**。五项剖面检查仍断言内联辅助区间，一项高度覆盖仍断言无依据开口逐行返回，均按 B 的新呈现契约改为摘要计数＋哈希校验全文读回，原有像素/区间/错误诊断断言保留。由此发现并补上只读测量服务的同一个 `read_candidate_items` 入口；读写两边使用同一实现，无新增写权限。修正后的相关 **61 项全部通过，45.10 秒**。

同时补齐历史兼容边界：旧返回只给稿号时，从保存报告恢复领域失败判定；旧事务仅有 `applied` 标签时，核对实际保存的前后几何再恢复“观察已应用”，纯备注不消费观察。所有读取仍归同一个保存契约模块。

最终补核朝向：角度不变而补写来源/确定程度，不算几何应用；真实角度变化仍算。`.3` 在此修正后重新完成 505 项整文件检查、两底座三例核对及全部历史重放。

## 复现入口

所有脚本均在本实验目录，不修改原始运行，不调用模型。先 `prepare.py` 解包；改前运行 `replay.py before` 时 `PYTHONPATH=/root/worktrees/astra-c3t/.tmp_c3t/baseline:/root/worktrees/astra-c3t`，其余统一 `PYTHONPATH=/root/worktrees/astra-c3t`。依次执行 `replay.py after`、`compare.py`、`behaviour.py`、`compare_runners.py`、`checks.py`、`validate_delivery.py`。底座核对使用当前登记，不重新登记旧版本。重放完成后可删除本树 `.tmp_c3t/`。
