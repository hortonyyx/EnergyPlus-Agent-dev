# sm25 第二轮手动调度准备（3／4 档，未启动）

## 结论

第二轮不再做“4 档独立整案”。建议由根 dev model 手动担任调度员，复用当前 `RoleSession` 作为读图员执行接口：平面读图员固定使用 **4 档 `Qwen3.8-27B`**，立面读图员固定使用 **3 档 `Qwen3.8-Flash`**。调度员模型请求为 0；根 dev model 亲自决定任务、读取产物、一步建楼、检查、返工与交付。

选择理由：

- `Qwen3.8-27B` 符合项目的 4 档和未来本地部署级主力方向，已有图像、工具调用、sm24 整案和读图员实际证据；平面是当前最难部分，优先给 27B。
- `Qwen3.8-Flash` 属于项目定义的 3 档，项目已有图像／工具接续证据，历史速度约 90–100 token/s，且输入、缓存、输出价格均低于 27B，适合四个立面读图员。
- Haiku 依赖当前不可用的 Claude 账号；GPT mini 没有本项目已接通、带完整事件和人民币费用保护的产品线路，因此都不作为本次可执行首选。

## 当前可用性与费用口径

2026-10-09 对 Paratera `GET /v1/models` 做了 **一次只读目录请求**，没有推理、没有重试、没有输出凭据。目录共 86 项，`Qwen3.8-27B`、`Qwen3.8-Flash` 和备用 `Qwen3.5-35B-A3B` 均存在。目录存在只证明当前可选，不证明余额、长期稳定性或 sm25 质量。

项目最新可核记录是 10-07：追加 50 元后，扣除当晚 27B 读图员摸底的已知约 5.91 元，**项目账本约余 58 元，以供应商账单为准**；该次另有一个超时请求用量未知。10-08 与 10-09 记录的 Paratera 产品调用均为 0，所以项目账本没有后续扣款。`/models` 不提供实时余额，本次没有供应商余额／账单接口证据，不能把约 58 元写成平台实时余额。

10-03 实际账单反推价（元／百万 token）：

| 模型 | 文本输入 | 图片另收 | 缓存输入 | 输出 |
|---|---:|---:|---:|---:|
| Qwen3.8-27B | 3 | 3 | 0.6 | 12 |
| Qwen3.8-Flash | 1 | 1 | 0.1 | 3 |

Qwen 回执里的 input 已包含图片 token，但历史账单又单列图片输入收费，因此图片按额外一遍计费。候选配置使用已有 runtime 价格表复现此口径。

本次建议 **20 元硬封顶**，约为项目账本余量的三分之一，给未知超时账单与后续工作留余地。保护同时存在于：

1. 根 `RunLimits.money_cny=20`，每次请求按模型、缓存和额外图片收费预留；余量不足时 HTTP 前停止。
2. 包装器在 adapter 发送前重算当前估算费用；费用变为不可核或已到 20 元时拒绝发送。
3. 只允许配置中固定的 Paratera 线路；重试仍是同型号同线路，最多 2 次。无 provider/model fallback。
4. 配置和包装器都拒绝 DeepSeek、Claude 及非 Paratera reader 线路。DeepSeek 任何探测仍为 0。

## 包装入口

[manual_dispatch.py](manual_dispatch.py) 提供五个命令：

- `validate`：只读验证当前 runtime/domain 登记、输入、模型配置、价格表和费用上限；不读 API key，不建 run，不调用模型。
- `self-test`：用本地假 adapter 直接验证显式 `task_id → role_id → 固定线路` 授权；覆盖正确 plan／elevation、未列任务、coordinator 和线路错配，完全不读凭据、不联网。
- `init`：只有显式带 `--after-first-run-complete` 才建立独立冷启动 run。这个开关是顺序闸门，需根在第一轮 GPT-6 Sol 完整结束后使用。
- `delegate`：读取根 dev model 当时编写的任务 JSON，通过 `RoleSession.delegate_many` 运行读图员。首次任务必须显式覆盖配置中两张平面图和所有 cardinal 立面图；若 runtime 将自动补任务，包装器在任何 HTTP 前拒绝，避免隐藏派工。
- `tool`：零模型调用地执行调度员工具，如 `role_state`、`read_role_artifact`、`assemble_from_readers`、`review_role_assembly`、`edit_bim`、检查和 `finish_bim`。禁止从这里调用 `delegate_readers` 或会启动隐藏 Claude 的 `review_detail`。
- `status`：读取产物注册表、完整根事件账本及分角色费用。

每次 reader 请求和响应、公开思考、工具调用、原始回执、usage、预算预留／结算与失败进入同一个 `EventStore`。包装器另保存每次人工 `delegate`／`tool` 动作及参数文件 SHA-256；读图产物由 `ArtifactRegistry` 做哈希核验。恢复时重新打开同一 journal 和 task checkpoint，不新建 run、不换线路。

`RoleSession` 的模型绑定按角色固定，不能在同一 run 中逐任务随意换型号。本方案是 plan=27B、elevation=Flash；如根之后要改变绑定，必须在 `init` 前改候选配置并重新 `validate`，不能在已初始化 run 中切换。

## 精确命令（当前只执行了前两条）

在仓库根目录 PowerShell：

```powershell
.\.venv\Scripts\python.exe -m py_compile AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py validate --config AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/tier4_candidate.json
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py self-test --config AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/tier4_candidate.json
```

第一轮 GPT-6 Sol 完整结束后，根 dev model 才执行：

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py init --config AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/tier4_candidate.json --after-first-run-complete
```

根根据原图和第一轮行为诊断另写任务文件；任务文件只含本轮原图派工，不复制第一轮答案、历史答案、GT、旧尺寸、旧计数或旧几何。运行：

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py delegate --config AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/tier4_candidate.json --tasks <根审核后的任务JSON>
```

任务 JSON 是数组或 `{"tasks": [...]}`。每项使用现有 `TASK_SCHEMA`：必填 `task_id`、`role_id`、`image`、`target`；首次派工建议显式写共同 `origin`。可选 `instructions` 最多 400 字符，只放图纸事实或具体返工问题；可选 `budget` 仍受根 20 元、180 请求、700 工具调用和 10,800 秒上限约束。

读取状态与产物、一步建楼分别使用根审核的参数文件：

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py status --config AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/tier4_candidate.json
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py tool --config AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/tier4_candidate.json --name read_role_artifact --arguments <读取参数JSON>
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py tool --config AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/tier4_candidate.json --name assemble_from_readers --arguments <装配参数JSON>
```

运行中的只读观察和结束后的评价：

```powershell
.\.venv\Scripts\python.exe scripts/dev/observe_run.py AI_agent/archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25
.\.venv\Scripts\python.exe scripts/dev/evaluate_run.py AI_agent/archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25 --case sm25
```

评价只在运行结束后执行；参照答案不会进入 reader task、run inputs 或人工调度依据。

## 已验证与未验证

已做：脚本 Python 编译、CLI help、`validate` 和本地 adapter factory `self-test` 全部通过；factory 只使用显式任务角色映射，不依赖 child 路径或运行时文件；不带顺序确认的 `init` 按设计报错，且复核候选输出仍不存在；当前登记为 runtime v2 / domain v56；sm25 原始输入 7 个文件存在；模型请求 0。未做：`init`、reader 调用、工具写操作、费用消费、第一轮结果读取、任务设计、第二轮评价。也没有修改生产代码或全局项目文档。

需要注意：

- 27B 历史平面读图员在 60 分钟内未交出；即便给 20 元和更长根保护线，也不能保证完成。失败仍是诊断证据，不能自动换 Flash、GLM、Claude 或 DeepSeek 补跑。
- `init` 后 10,800 秒墙钟开始计时，任务 JSON 应先由根审核好，再紧接着初始化和派工。
- 首次派工必须把计划使用的两张平面和四张立面一次列全，避免 RoleSession 的首批自动补任务改变根的分工。
- 包装器保存完整产品侧 usage 和估算费用；Paratera 最终实际金额仍需账单核对。
