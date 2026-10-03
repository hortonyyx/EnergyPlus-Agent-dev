# R1 整案实测配置

R1 只准备、校验运行入口，不执行整案。统一入口是
`python -m src.agent.runtime_r1_preparation`：`check` 只检查模型档案、输入、预算、
凭据引用和路径；`command --case ...` 输出准确启动命令；`launch --case ...` 才会
把当前进程替换成真实入口。配置保留 `approval_required_before_launch=true`，供
项目的整案批次批准流程核对，不在准备阶段自动调用模型。

迁移对照走 `runtime_entry` 单工作模型：sm24 五张原图、与 10-02 GLM 基线
逐字相同的任务正文、冻结指引和工具、3000 秒、24 候选，无委派、重试或回退。
型号固定为 Paratera 的 `GLM-5.3-Flash`。旧订阅路径只有 Claude Code
`effort=medium` 记录，没有它翻译到上游参数的回执；新路径显式用上游支持的
`high`，并把这一差异写入配置。订阅路径也未报告 temperature，新路径依上游
评测值固定 1.0。因此这是尽量对齐、但不能宣称推理参数逐字相同的对照。

首批两例走阶段 3 外层 MCP 协调路径：Astra/Codex 在外层使用冻结建模工具，
Qwen3.8-27B 只做只读局部观察。sm24 与 Voimatalo 各自 6600 秒（110 分钟）
硬停；仍按原方案各一次冷启动、最多三轮有依据修订、每个子任务最多 3 请求／
6 工具／100,000 token／600 秒、无自动重试或换模。两例各有独立持久请求票据，
失败和超时同样占票。外层 Codex 的私有请求与 token 仍标“未获取”。

配置在 `AI_agent/logs/experiments/2026-10-03_runtime_r1/configs/`。两例的
`outer_coordinator_instruction` 是启动 MCP 后必须交给外层协调者的任务补充；
它不会偷偷进入局部角色请求。迁移对照预计约 45 请求、264 万 provider token，
依据 10-02 基线 44 轮与完整输入／缓存读／输出总量；硬停为 60 请求、400 万。
首批 sm24 预计 24 请求／36 万 token，硬停 30／50 万；Voimatalo 预计
32／52 万，硬停 40／75 万。后两项是按阶段 3 小测平均量与案例复杂度做的
规划估计，不是账单承诺；实际以统一事件日志和 Paratera usage 为准。
