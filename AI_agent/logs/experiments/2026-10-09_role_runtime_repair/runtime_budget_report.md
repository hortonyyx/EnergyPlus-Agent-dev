# runtime 预算与异常诊断修复报告

状态：实现与定向离线验证完成；未调用 work model、模型 API 或 DeepSeek。

## 目标

1. 当累计请求时间预算只因兄弟任务的在途预留暂时占满时，等待容量释放后重试 admission；真实累计预算耗尽或墙钟 deadline 到达时仍终止。
2. non-idempotent write 在 durable intent 后抛异常时，继续阻断不确定写入和截断执行，同时将原始异常的类型、运行阶段与安全诊断写入 durable 事件，避免只剩 `unknown_write_outcome`。

## 已知根因

- `sm25_role_v53` 的 `plan_f1b` 在根累计请求时间已结算 `10250.128s`、兄弟任务在途预留 `549.872s` 时看到可用量为零并永久终止；该兄弟请求随后只结算 `33.156s`，释放 `516.716s`。
- `plan_f1` 的第三次 `trial_plan_bim` 在 durable intent 后、进入 MCP 写调用前抛出 `builtins.StopIteration`；现有 unknown execution 记录丢失异常类型和阶段。

## 实际改动

- `src/agent_runtime/loop.py`
  - 每个共享 root journal 在当前 event loop 内维护一个轻量容量信号和实际在途 reservation id 集合。
  - 只有 root 累计请求秒数可用量为零、child 自身累计秒数与墙钟均未耗尽，并且至少一个未结算 reservation 仍对应实际在途请求时，兄弟任务才等待容量变化。
  - 等待队列使用明确 FIFO；等待前释放 dispatcher lease，请求结算后只唤醒队首，并在有等待者时 `await asyncio.sleep(0)` 让队首先重新 admission，避免刚结算的任务同步抢回全部释放量。
  - 正常 admission、temporary-rate redispatch、普通 retry 的 backoff 前后均调用同一异步等待 helper；若已无后续请求，最终失败原因会忽略临时兄弟 hold，避免把真实模型失败误报为 root time 耗尽。
  - 等待始终受当前任务墙钟剩余量约束。超时返回 task wall-clock 的 `child_time_budget_exhausted`；无在途请求可释放、已结算秒数到顶、child 累计预算到顶时直接返回原有累计预算停止原因。
  - 不改变 seconds 上限和 reservation/settlement 计算；不加最小剩余秒数门槛。正数残余即使只有 `0.001s`，仍原样作为 request timeout。
- `src/harness_contracts/events.py`、`src/harness_contracts/__init__.py`
  - `ToolExecutionPayload` 新增可选 `ToolFailureDetails`：全限定异常类型、`tool:<tool_name>` 阶段和最多 2 KB 的安全诊断。
  - 新增 `BudgetWaitPayload`：`begin/end` 共享 `wait_id`，记录原因、活跃 hold id、root/task 可用量和墙钟余量；`end` 强制记录 elapsed 和 `capacity_changed / wall_deadline_exhausted / cancelled`。进程中断时允许仅有 begin，表示 unfinished。
  - 字段可选，因此既有无 failure 字段的 journal 可由新代码读取；成功结果禁止携带 failure。
- `src/agent_runtime/failures.py`
  - 任意异常消息都可能携带工具输入、URI userinfo 或 token，因此非空正文一律不持久化；仅保存类型、阶段和固定安全诊断。
  - `str(exc)`、类型名和 UTF-8 规范化均有异常保护；非法 Unicode 用 `backslashreplace/replace` 处理，不会因诊断失败再次丢掉 unknown-write 事件。
  - 空消息异常保留明确诊断 `exception carried no message`，可识别本次 `builtins.StopIteration`。
- `tests/test_agent_runtime.py`
  - 覆盖在途 root seconds 预留释放、FIFO 队首机会、真实已结算耗尽、等待期间 child 墙钟到期、`0.001s` 正残余 timeout、retry backoff 期间被兄弟占满后继续、wait 事件配对、ConnectionError/StopIteration、非法 Unicode 与异常 `__str__`。

明确不改：`src/agent_runtime/context.py`、`src/agent_runtime/anthropic.py`、`scripts/dev/observe_run.py`、`src/agent/runtime_roles/**`、全局项目文档与版本注册。

## 实施与验证

- Python：复用主仓库 `.venv/Scripts/python.exe`。
- 环境：`PYTHONPATH=D:\EnergyPlus-Agent-worktrees\runtime-budget-20261009`、`PYTHONUTF8=1`、`OPENBLAS_NUM_THREADS=1`。
- 导入确认：`src.agent_runtime.loop.__file__` 指向本工作树。
- 必要核心回归：93 passed
  - `tests/test_agent_runtime.py`
  - `tests/test_runtime_budget.py`
  - `tests/test_runtime_budget_integration.py`
  - `tests/test_runtime_child_tasks.py`
  - `tests/test_runtime_time_settlement.py`
  - `tests/test_runtime_recovery_edges.py`
  - `tests/test_harness_core_contracts.py`
- 截断、billing 与订阅预算：29 passed。
- dispatcher：14 passed。
- 新增极小正残余验证：1 passed，adapter 实收 timeout 大于 0 且不超过 `0.001s`。
- 独立审查补修后文件级回归：`tests/test_agent_runtime.py` 加 retry/redispatch 相关 dispatcher 用例共 42 passed。
- 全部 pytest 均为 `-n0 -p no:cacheprovider`，`--basetemp` 位于本工作树 `AI_agent/archive/local_backup/` 下；测试门禁报告本进程 0 次 billed provider call。
- `ruff` 未执行：复用的 `.venv` 未安装该模块。`git diff --check` 通过。
- `tests/test_runtime_parallel_delegation.py` 以及 coordinator 的 2 项集成用例在初始化阶段按预期被现有 runtime v1 文件哈希门禁拒绝；本任务按分工不改全局版本注册。主助手登记新 runtime 版本后应统一重跑这些集成用例。

## 兼容性边界

- 等待逻辑仅处理已证的累计请求 `seconds` 在途预留。model-call reservation 结算后仍计 1，不会释放；tool call 没有这类请求时间 reservation；token 估计虽可能在结算后释放，但本轮没有已证永久停止根因，未顺带扩展等待语义。
- 容量信号是单进程、单 event loop 内的活跃状态。EventStore 本身只允许一个 run writer；进程重启后没有仍在执行的旧请求，因此历史未结算 reservation 继续按保守耗尽处理，不会无限等待。
- FIFO 只规定已进入容量等待队列的先后顺序，不保证某个任务获得固定秒数。最终是否 admission 仍按 durable ledger 的即时可用量决定；新任务不能把等待事件当作预算配额。
- `unknown_write_outcome`、state inspection 和禁止重试语义未变；截断响应仍在工具执行前被丢弃。新增 failure 只增加安全诊断，不把未知写入改判为失败或成功。
- 新 failure 字段属于 runtime event contract 的向后读取兼容扩展；旧 runtime 不保证能读取含该字段的新 journal。合入时需要由主助手登记新 runtime 版本并完成版本门禁后的集成回归。
