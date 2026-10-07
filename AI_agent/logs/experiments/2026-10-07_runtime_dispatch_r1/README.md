# RT1 执行报告

状态：A–E 离线验收完成，待 Opus 统一登记及集成；临时目录清理被执行策略拒绝。基准 `9480a704`，工作树 `rt1`，执行方 Astra；本包由执行方独立完成，未派子代理。

迭代范围：仅 runtime（`src/agent_runtime/`）、runtime 相关检查与本实验目录。影响单模型和分工模式的请求派发、用量与运行记录；domain、模型请求内容和 Agent 版本登记保持原样。

## 验收进度

- A：已实现共享排队、自适应并发和独立排队时间，模拟验证通过。
- B：已实现明确拒绝的限流请求零用量；其他未知读数仍未知。真实 sm21 事件的离线投影可完整汇总。
- C：每个任务的时间分布、根任务等待子任务时间、最晚结束的子任务及后续根任务耗时已验证。
- D：模拟、拒绝后中断恢复、Chat / Messages 单模型请求字节对照、三例离线贯通均通过。
- E：首批 558 项通过、52 项被正式登记拦截；临时登记下最终定向 161 项全部通过，覆盖全部 52 个拦截项。始终 `-n 2`，未跑仓库全量，未提交 Git。

## 执行边界

开工已完整读取 Agent.md、产品目标、当前任务、工作方式、名词规范和最新 10-07 交接，并核对干净分支及工作树。仅只读访问已有整案记录；本包真实模型请求 0 次（Paratera 0、DeepSeek 0）。临时输出限定在 `AI_agent/archive/local_backup/rt1/`；检查、复现命令、限制与建议提交分组见下文。最终范围、LF、代码哈希和检查覆盖核对见 [verification.json](verification.json)。

## 实现与边界

`dispatch.py` 按线路在同一 asyncio 事件循环中共享队列，覆盖调度员、读图员及不同根运行。入队发生在请求预算预留之前，避免等待者占住请求时间预算。收到明确临时限流后，同时请求上限减一，最低一；被拒请求回到队首，不消耗普通失败重试次数，但实际发送次数和总时限保护仍然有效。槽位在请求返回时释放，不占用工具执行或等待子任务的时段。

`route_dispatch.json` 对两条 GLM 订阅线路设置初始 5、最大 8；拒绝后采用共享的 1 秒起步、最高 30 秒冷却，连续 60 秒没有拒绝后在成功返回时逐次增加一档。依据是本次白天接住 5 路、昨晚能接住 6–8 路的记录，不是服务商承诺。未配置线路继续直接发送。不同进程或不同事件循环不共享这个内存队列；重启从配置初始档恢复。

请求正文和参数的构造未变；排队、请求耗时、工具耗时、并发档位变化均存为已有事件的附加来源记录，不扩展 domain 或公共事件契约。拒绝重发的关联同时写入日志与检查点，恢复时识别已记录的明确拒绝，保留零用量，不误算普通失败重试。未知网络结果、模糊 429、额度耗尽、部分用量读数均不推定为零。

新回执的 `timing.by_task` 包含起止、请求数、模型、排队及工具时间。根任务的等待按子任务生命周期与根工具调用的重叠区间求并集；并发的子任务不会重复累计。工具独占时间扣除这段等待。`critical_path` 给出最晚结束的子任务和根任务后续耗时，不声称重建了任意任务依赖图。其余时间包含准备、上下文处理、日志写入、普通重试退避与恢复停机。

历史回执投影只读事件和内容寻址文件，不打开日志写入器、不改原预算台账。旧工具记录使用调用/执行事件的时间差，包含当时未单独测量的少量转换开销；旧记录没有排队测量时标为 `null` 且完整性为 false。

另补齐了几处恢复和计时边界：预算缩小输出并重新准备请求时保留先前排队时间；超过截止时间后的回执保留实际历时；重发成功响应落盘后中断，恢复时清除旧队首重发标记；只剩执行意图、工具结果未知时，不把恢复停机时间算成已测量的工具时间，而是标记工具计时不完整。

## 模拟前后

[simulation.json](simulation.json) 由 [simulate.py](simulate.py) 生成。模拟服务容量固定为 5，同时收到 6 个请求：

| 场景 | 成功 | 拒绝 | 服务内最大并发 | 第六个请求 |
| --- | ---: | ---: | ---: | --- |
| 直接派出首轮 | 5 | 1 | 5 | 收到 429 |
| runtime 先排队 | 6 | 0 | 5 | 等待约 62 毫秒后成功 |

另外用可控时钟验证上限 `5 → 4 → 5 → 6 → 7 → 8`：拒绝后立即降档，30 秒时不恢复，61 秒后才逐次增加；队首重发、取消/过期等待者不漏槽位也已覆盖。服务耗时是人为设置的 50 毫秒，这些数字仅证明派发行为，不预测整案加速幅度；直接派出一栏不包括原有后续重试。

## sm21 分工真实事件的回执示例

只读来源：主树 `AI_agent/archive/local_backup/cmp3/sm21_role`。完整结果见 [sm21_timing_usage.json](sm21_timing_usage.json)，复现入口为 [analyze_sm21.py](analyze_sm21.py)。源 events、receipt、journal 在分析前后哈希一致。

原回执根级合计为 113 次请求、用量不完整，token 总量为空。五次明确拒绝都在 `plan_f1`，发生于根任务开始后 130.949、135.546、144.357、161.036、194.151 秒。依新规则投影后：**113 次请求，5 次明确拒绝计零，已报告 token 合计 4,759,925，用量完整**。预算口径另含成功请求的图像估计，合计 5,456,600；订阅费用仍不换算成人民币，不将估计称作账单。

时间单位为分钟，起止是相对根任务开始的偏移；全部旧排队时间均未知，未填零。

| 任务 | 起止 | 请求数 | 总历时 | 模型 | 工具独占 | 等子任务 | 其余 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| coordinator | 0.00–47.51 | 26 | 47.51 | 10.51 | 1.61 | 29.78 | 5.61 |
| elev_west | 1.69–4.35 | 5 | 2.66 | 2.38 | 0.02 | 0.00 | 0.26 |
| elev_east | 1.69–4.23 | 7 | 2.54 | 2.01 | 0.04 | 0.00 | 0.49 |
| elev_south | 1.68–8.07 | 6 | 6.39 | 5.67 | 0.05 | 0.00 | 0.67 |
| elev_north | 1.68–5.95 | 7 | 4.27 | 3.60 | 0.06 | 0.00 | 0.60 |
| plan_f1 | 1.67–26.23 | 30 | 24.56 | 18.03 | 0.88 | 0.00 | 5.65 |
| plan_f2 | 1.68–23.52 | 22 | 21.85 | 18.24 | 0.83 | 0.00 | 2.77 |
| elev_west_r2 | 29.86–35.08 | 10 | 5.22 | 2.69 | 0.23 | 0.00 | 2.30 |

第一轮最晚结束的是 `plan_f1`；整个运行最后结束的子任务是后续返工 `elev_west_r2`，之后根任务还运行 **12.43 分钟**。根任务等子任务合计 **29.78 分钟**。这说明历史运行的时间分布，不代表 RT1 已在真实整案中提速。

## 检查与登记

所有 pytest 均从工作树根目录激活 Windows 环境，明确 `-n 2`。首轮选择 `test_runtime*.py`、`test_role*.py`、`test_agent_runtime.py`，未执行仓库全量。

已确认现有正式登记仍包含 `src/agent_runtime/loop.py`，当前仅这一项哈希发生差异。按派工要求不改正式登记，也不放宽校验；后续检查通过既有 `BIM_AGENT_REGISTRY_PATH` 机制使用本包临时登记副本。四组工具目录沿用正式哈希并由原检查验证，未跳过目录/文件校验。集成运行前须由 Opus 在统一版本登记中处理 loop.py 的新哈希。

| 批次 | 结果 | 范围与证据 |
| --- | --- | --- |
| 首轮限定检查 | 558 通过，52 拦截，610 项 | 52 项全部为正式登记的 loop.py 哈希不匹配；不是其他功能失败。[checks_initial.json](checks_initial.json) |
| 最终定向复验 | **161 通过，0 失败，0 跳过** | 覆盖全部 52 个拦截项，以及最终改动涉及的恢复、时间结算、预算、失败分类、原生协议和三例角色贯通。[checks_followup.json](checks_followup.json) |
| 其中新增行为检查 | **14 通过** | 共用容量、队首重发、降档/恢复、取消/过期、拒绝用量、两次中断恢复、普通失败重试历史、预算重新准备、两种协议字节一致性及计时边界 |
| 真实工具历史回放 | **75 个工具调用、76 个脚本化响应通过** | 没有真实模型调用；历史参数重放不冒充冷启动整案。[frozen_replay_check.json](frozen_replay_check.json) |

三例 `sm21 / sm24 / sm25` 的脚本化工作模型加真实工具贯通全部通过；读图员试拼装后恢复、全部读图员完成后恢复、`build_plan_bim` / `claim_transaction` 内部回执后恢复均通过。派工单注明的试拼装恢复偶发点本次复验一次通过，无需重复。三例单模型首请求逐字节一致性检查也通过。

最终复验期间 runtime 代码哈希不变、正式登记文件不变，证据内保留了代码哈希和逐项结果。首轮已通过的长任务恢复检查复用；最后收口的计时和拒绝恢复改动由最终定向复验覆盖。首轮 pytest 用时 2461.99 秒，最终复验 657.69 秒；这些是检查耗时，不是产品整案性能。

复现最终定向检查（从工作树根目录执行；只读正式登记，在本包临时目录创建副本）：

```powershell
. .\scripts\activate_windows.ps1
python AI_agent/logs/experiments/2026-10-07_runtime_dispatch_r1/run_checks.py `
  --failed-from AI_agent/logs/experiments/2026-10-07_runtime_dispatch_r1/checks_initial.json `
  tests/test_runtime_dispatch.py tests/test_runtime_recovery_edges.py `
  tests/test_runtime_c1.py tests/test_runtime_a2r_failures.py `
  tests/test_runtime_time_settlement.py tests/test_runtime_r3.py `
  tests/test_runtime_budget_integration.py tests/test_runtime_r2_output_limits.py `
  tests/test_runtime_anthropic.py tests/test_role_end_to_end.py
```

模拟与真实事件投影也从同一已激活环境运行：

```powershell
python AI_agent/logs/experiments/2026-10-07_runtime_dispatch_r1/simulate.py
python AI_agent/logs/experiments/2026-10-07_runtime_dispatch_r1/analyze_sm21.py `
  'C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\cmp3\sm21_role'
```

## 清理与剩余工作

完整首轮 JUnit 已移入本包临时目录，报告保留精简结果和原始文件哈希。**自动审批拒绝递归清理，理由为 `blocked by policy`。** 批量清理被拒后，先只读确认固定目录 `pytest-dispatch` 位于本工作树、不是重解析点、没有 `.git`，再缩小到该目录尝试，仍被同一理由拒绝。没有换解释器或其他接口绕过。

因此 `AI_agent/archive/local_backup/rt1/` 下的 pytest 临时目录、`frozen-replay`、`registry`、`tmp` 和原始检查日志仍保留，均不在建议提交范围内。首轮检查的 `pytest/popen-gw0/test_explicit_storage_root_can0/other/.git` 是隔离检查创建的标记文件；清理时按用户要求保持所有 `.git` 只读，未删除它。

后续由 Opus 审查、统一登记并集成，在允许清理的环境中处理本包临时产物。本包未验证真实服务下的整案提速或质量；未调用真实模型、不改 domain，也未影响主树的三例对照。

## 建议提交分组

1. `runtime: add route admission, refusal accounting and task timing`：本包全部 `src/agent_runtime/` 改动与 `tests/test_runtime_dispatch.py`，作为可独立运行的完整实现提交。
2. `docs: record RT1 offline validation and integration notes`：本实验目录内的模拟、分析、复验入口、证据和报告。

本工作树不执行暂存、提交或推送，不改 Agent 正式版本登记。
