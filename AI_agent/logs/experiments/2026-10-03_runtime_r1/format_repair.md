# R1 A：子角色输出格式补救

日期：2026-10-03

开发：gpt-5.6-sol，high

开发模型用量：未获取

外部模型调用：0

## 结果

子角色最终答案现在先经过原有 `hydrate_observation` 校验。首次校验失败时，运行器在同一个子任务内记录一条补救请求，把原始校验错误原样回给同一模型，并只允许再发一次模型请求。第二次答案仍走同一个校验器；改对才收下，仍错则以 `answer_validation_failed` 拒收。运行器不删字符、不替换引用，也不放宽任何字段、定位或引用规则。

补救请求使用原子任务的模型、上下文、token、模型调用数和时间账本。预算不足时只记录补救请求，不发送第二次模型调用。补救请求不提供工具定义；即使模型自行返回工具调用，也会直接拒收，不执行工具、不发送第三次请求。传输错误也不会给补救回合增加重试。

## 审计与恢复

新增 `answer_repair` 事件：

- `request` 阶段保存原始模型响应事件、原答案完整 capture 和原校验错误。
- `result` 阶段再次保存原答案、补救后答案、第二个模型响应、是否通过及第二次校验错误。
- 事件契约限制每个 task 只能有一条补救请求、每条请求只能有一个结果，并核对 invalid/request/repaired/adapter request 全部属于同一个 task 且先后次序正确，防止并发兄弟任务串答案。

补救状态进入 checkpoint。离线故障注入覆盖“第二次模型响应和用量已落盘、补救结果事件尚未完成”边界；恢复会重放已保存响应，不会再调用模型，也不会重复追加补救事件。另覆盖补救 `adapter_request` 已落盘而响应未知的边界：即使一般传输重试上限仍有余额，也以 `resume_request_outcome_unknown` 停止，绝不重发补救。补救待处理期间也不会插入上下文摘要请求。

## 阶段 3 真实反例

测试从既有归档 `AI_agent/logs/experiments/2026-10-02_harness_stage3/evidence_all.compact.tar.xz` 直接读取最终批 `role_case.json`，同时核对归档对象哈希和答案 UTF-8 哈希，不重造近似失败文本：

| 最终批运行 | 原答案 SHA-256 | 真实错误 | 开发提供的离线第二答案 | 结果 |
|---|---|---|---|---|
| `final_02_27b` | `e83002fc70f0ca1dfbd0b48344f27a85baba4231032014c2eae32609b2fe8999` | 完整 JSON 后真实多出一个 `}` | 只去掉该尾随字节 | 收下 |
| `final_02_flash` | `7dd0427bac016a658b386df45efabae4be9fdd129ab769dbd5b3f177e1ddf08c` | `int_chain_left/right` 解释编号填入观察引用栏 | 改为真实 `obs_left_chain/right` | 收下 |

两条原答案各另测一次“第二答案保持原错”，均在恰好两次模型请求后拒收。另测模型调用预算只够首次答案，补救请求有记录但第二次没有发送；以及补救答案返回工具调用时工具调用数保持 0、总模型请求数保持 2。

## 并发账本顺手修正

按 R1 B 的并发接入要求，`Runtime` 在结算、预算停止判断和最终收据前从共享事件日志刷新根账，避免并发子任务使用发送前缓存的余额。适配器内部 timeout 与外层 `asyncio.wait_for` 现在共同取本任务剩余墙钟和本次根/子账实际预留秒数的较小值，避免请求超过根账为它预留的时间。根 `seconds` 仍表示各模型请求实际耗时的累计额度；单个 task 的 `_remaining()` 仍是该 task 的独立墙钟截止时间。

## 修改文件

- `src/agent/runtime_delegation.py`
- `src/agent_runtime/loop.py`
- `src/harness_contracts/events.py`
- `src/harness_contracts/validation.py`
- `src/harness_contracts/__init__.py`
- `tests/test_runtime_delegation.py`
- `tests/test_agent_runtime.py`
- 本报告

没有修改冻结工具、几何、校正、原执行模块、指引、`Agent.md`、项目文件或派工单。

## 离线验证

工作树导入均显式使用：

```text
PYTHONPATH=/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-r1
```

- 格式补救、真实反例、无预算、工具调用拒绝和恢复边界：`19 passed in 7.48s`，`pytest -n 2`。
- 契约核心、恢复边界、时间结算和本项联合：`52 passed in 11.09s`，`pytest -n 2`。
- 运行时、委派、预算、父子任务周边联合：`69 passed in 27.14s`，`pytest -n 2`（在最后的补救工具调用封口前运行；其受影响路径随后由上述 18 项覆盖）。
- `compileall` 与 `git diff --check`：通过。

所有测试均用 `ScriptedAdapter`，修正版答案由开发测试桩提供；没有调用 Paratera、GLM、Claude、DeepSeek 或其他外部模型。

## 未决项

本项没有需要用户拍板的产品决定。最终全短检查、两组长故障矩阵和真实冻结工具 75 步由 R1 主任务统一执行，本分项不重复长测。
