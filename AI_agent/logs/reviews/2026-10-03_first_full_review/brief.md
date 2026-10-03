# 首次完整审查：派工单（两位审查人共用）

派工人：Opus 5.5（项目经理）。依据[定期独立审查](../../../workflow/development.md#定期独立审查10-03用户确认)：用户要求“间隔一堆时间之后，需要独立审查一遍当前 agent，迁移底座完之后还要包括底座，用意主要是为了避免开发迭代造成的整体过度熵增”，并确认“审查最好是两边旗舰各自独立”。时机按 10-03 用户决定：迁移成功后马上做一次。

## 审查对象

主线提交 `99fbf0ef`（R3 合入后，Agent 版本 `t1-20261003-r3`）上的：
1. **建模 Agent**：写给工作模型的系统指引（`scripts/tool_scripts/bim_agent_guidance.py`，图纸指引 10-03 起点 9,179 字符，T1 后 9,668）、工具说明与参数结构（`run_bim_agent.py serve` 暴露的 42 个工具）、任务说明（`bim_agent_inputs.py`、`src/agent/roles.py`）、工具实现（登记表 `src/agent_runtime/agent_versions.json` 当前版本列出的文件）。
2. **新底座**：`src/agent_runtime/`、`src/harness_contracts/`、`src/agent/runtime_*.py`。
3. **测试**：`tests/test_runtime_*.py`、`tests/test_harness_*.py`、`tests/test_bim*.py`，看是否有只为锁住旧行为、已无实际消费者的测试。

## 可用的运行证据

只用已有记录，不新跑模型：
- Claude Code＋GLM 订阅：10-02 sm24 基线 `AI_agent/logs/experiments/2026-10-02_sm24_glm_baseline/`；T1 的 sm24、sm25 行为记录 `AI_agent/logs/experiments/2026-10-01_behaviour_records/records/2026-10-03_sm2{4,5}_glm_tools_t1/`。
- 新底座：迁移对照 Paratera 三次与订阅三次，评分与说明见 `AI_agent/logs/experiments/2026-10-03_migration_comparison/`（`evaluation_*.json`、README）；原始运行目录若不在主工作树，按 README 里的证据分支和哈希清单取用。
- 阶段 0–3、R1、R2、R3 的验收记录：`AI_agent/project/unified_agent_acceptance.md`。

## 固定清单（每次审查同样的指标，便于前后比较）

1. **指引**：总长度（字符数，按 `AI_agent/logs/experiments/2026-10-03_tool_package_t1/measure_instructions.py` 的口径）；重复或互相冲突的要求；过时规则；最近几次改指令是否“替换不追加”。
2. **工具**：数量；功能重叠；在上述运行中的实际使用次数与报错率；从没用过的工具。
3. **代码**：死代码；重复逻辑（同一件事在 Claude Code 运行器与新底座各写一套的地方尤其要看）；只为锁住旧行为的测试。
4. **运行**：最近几次运行的轮数、工具报错数、首稿时刻与总耗时。
5. **底座**：运行开销（底座自身耗时、每轮附加的消息与 token）、没用上的功能、接口复杂度。

## 产出

- 报告写到本目录：Astra 写 `astra.md`，Opus 写 `opus.md`。先给结论，再按清单五项逐项给数字与证据（文件与行号、运行记录路径）。
- 最后给一张“删、并、简化”清单：每条写明改什么、为什么（对应哪项指标或哪次运行的证据）、预计影响（对工作模型、对速度、对维护），以及风险。分“建议马上做”和“可以以后做”两档。
- 不改任何代码、指引或测试；只写自己的报告文件。不调用任何模型（0 请求），不用 DeepSeek。
- **独立性：** 不要读本目录里另一位审查人的报告，也不要读 `summary.md`。Opus 汇总两份结论，分歧单列。
