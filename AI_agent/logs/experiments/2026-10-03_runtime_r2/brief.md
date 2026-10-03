# 派工：迁移跟进包 R2（截断补救、输出上限、图片记账、Agent 版本登记）

派工人：Opus 5.5（项目经理，负责验收与质量）。R1 已于 10-03 验收合入（`2b94a160`）。本包由你（Astra）牵头，内部分工和子代理自己定。

## 起因

用户已批准迁移对照。第 1 次运行（sm24，GLM-5.3-Flash 经 Paratera，冻结工具）在第 12 次请求时停跑：模型思考了 16,377 token，把 16,384 的输出上限全部用完（finish_reason=length），没有发出工具调用。`adapter.py` 把这种情况判为 `incomplete_response`，主循环随即停掉了整个运行。Claude Code 基线的单次输出上限是 32,000，基线本身也有一轮思考约 1.96 万 token。被截断的思考是连贯的分析，模型正准备一次发出 5 个工具调用。另外，账单核对发现 Paratera 返回的用量不含图片 token，账单却照收。详见 `AI_agent/logs/experiments/2026-10-03_migration_comparison/README.md`。第 2 次对照只把输出上限改为 32,000，正在主工作树跑。

## 先读

1. `AI_agent/Agent.md`（10-03 新增 Paratera 开发期额度 50 元，由 Opus 调度）。
2. `AI_agent/project/unified_agent_acceptance.md` 最后一节：**R2 验收标准，按它交付**。该文件由 Opus 维护，你不要改。
3. 迁移对照记录与第 1 次运行：`AI_agent/logs/experiments/2026-10-03_migration_comparison/`（README、`evaluation_attempt_01.json`、`paratera_bill_2026-10-03.csv`），运行目录 `AI_agent/logs/experiments/2026-10-03_runtime_r1/runs/migration_sm24_glm_paratera/`（未入库，在主工作树，只读引用，不要复制进仓库）。
4. `AI_agent/workflow/models.md` 开头：账单单价与记账口径差。

## 工作位置

- 工作树 `/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-r2`，分支 `dev/astra-r2-20261003`，基于主线上加入本派工单的提交。
- 只在该工作树内改动，小步提交（英文 commit message）。不合入 main，不 push。
- Opus 正在主工作树用主线代码跑迁移对照第 2 次；另一个工作树 `.worktrees/opus-tools-t1` 在跑 GLM 测试。不要动这两处。

## 任务

按验收标准 A–E 交付，优先顺序 1 → 4 → 2 → 3：

1. **截断补救**（A）：输出截断不再整轮停掉；有界、有记录、不执行半截工具调用；子角色同样处理。用第 1 次的真实截断回复做离线反例。
2. **Agent 版本登记**（D）：登记表、运行时记录版本、替换那 5 项“与冻结基准逐字节一致”的检查、登记新版本的命令；冻结基准保留为历史版本。目的是之后工具改进包合入主线时，两个底座跑同一版 Agent。
3. **输出上限默认值**（B）：在模型档案里写明建议的最小输出上限及依据；配置低于该值时检查拒绝，写明理由可显式放行。
4. **图片记账**（C）：按型号估算图片 token，用账单表和既有事件里实际发出的图片校准，不新增请求；计入预算，回执给出实报、图片估算和人民币估算。

## 可改范围

- 可改：`src/agent_runtime/`、`src/agent/runtime_*.py`、阶段 0–3 的契约与测试（需要时）、`AI_agent/design/` 下的运行底座说明、`AI_agent/logs/experiments/2026-10-03_runtime_r2/` 下的交付材料（本派工单除外）、`AI_agent/logs/worklog/` 下的开发记录。
- 不改：`scripts/tool_scripts/`、`src/agent/geometry/`、`src/agent/correction/`、现有 `src/agent/execution/` 模块（冻结基准）；`AI_agent/Agent.md` 与 `AI_agent/project/`；R1 的历史配置；本派工单。
- 新证据按哈希引用仓库里已有的字节，不重复打包；新增证据尽量控制在 2 MB 以内。

## 模型、子代理与外部调用

- 子代理按 `AI_agent/workflow/models.md` 的偏好自选，开发记录写明型号、推理档和用途。
- Paratera 最多 5 次请求，只用于真实截断补救的小测（例如用很小的输出上限故意截断，看补救后能否继续），另立账本，失败与超时也计入次数。凭据只读引用主工作树 `.env`，不打印、不入仓。事后报用量。
- 不跑整案；不用 DeepSeek；GLM 订阅不接自有底座。

## 时限

本次运行有 2 小时硬上限（Claude Code 后台任务）。请在约 90 分钟内收尾，每完成一项就提交。到时还没做完，就提交已完成的部分，把续接点写进交付目录的 README，并在最终回复里列清剩余项。

## 交付（最终回复）

最终回复就是交付报告，中文、白话，约 1500–2500 字，包括：
- 做成了什么、在哪些文件；
- 对照 R2 验收标准 A–E 逐条自评，附证据；
- 截断补救小测的实际过程和用量；
- 图片 token 估算公式、校准依据与误差；
- 提交列表、改动文件名单、实际跑过的测试及结果；
- 未决技术问题和需要用户拍板的事，分开列；
- 子代理及其用量。

不确定的写“未核实”。会改变范围的决定写进报告，不要自行扩大范围；能做完的部分照常做完并提交。
