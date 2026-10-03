# 派工：迁移收尾包 R3（T1 进新底座、登记新 Agent 版本、两底座同一版 Agent）

派工人：Opus 5.5。工作树 `.worktrees/astra-r3`，分支 `dev/astra-r3-20261003`，基于主线（已含 R2、R2b、R2c）。只在本分支小步提交，不合入、不推送；交付后由 Opus 验收合入。

验收标准写在 `AI_agent/project/unified_agent_acceptance.md` 最后一节“迁移收尾包 R3”，按它交付。

## 背景

- T1 是 Opus 在 Claude Code 线上做的工具改进包，分支 `dev/opus-tool-package-20261003`，末提交 `74e27da3`。四项：降报错、时间上限、逐扇核对窗高、逐面清点外墙窗。实现说明见该分支 `AI_agent/logs/experiments/2026-10-03_tool_package_t1/README.md`，GLM 实测结论见同目录 `opus_review.md`。T1 的工具文件与主线自 T1 基点 `e123046d` 以来没有重叠改动。
- 用户定：迁移时 T1 有用的部分合入主线，两个底座用同一版 Agent（工具、指引、任务说明一致），以后的 Agent 改动不能让 Claude Code 这条线跑不起来。
- Opus 核对发现的两处缺口：
  1. T1 的时间提示与楼层覆盖读运行目录 `inputs.json` 的 `deadline_epoch` 与 `floor_plan_images`；新底座 `src/agent/runtime_entry.py` 写的是 `"deadline_epoch": None`，也没写楼层。
  2. T1 到点交出最近一版完整全楼稿的保底（`scripts/tool_scripts/bim_agent_budget.py` 的 `fallback_selection` ＋ `Toolkit.delivery`）只接在 Claude Code 运行器 `run_bim_agent.py` 的收尾里；新底座到点停下后没有交付，迁移对照第 2 次就是评分时拿最后保存的稿子顶替。

## 要做

1. **带入 T1。** 用 `git checkout 74e27da3 -- <路径>` 按路径带入：`scripts/tool_scripts/` 下 T1 改动与新增的 5 个文件，`tests/` 下 5 个测试文件，`AI_agent/logs/experiments/2026-10-03_tool_package_t1/`，`AI_agent/logs/experiments/2026-10-01_behaviour_records/records/2026-10-03_sm24_glm_tools_t1/` 与 `.../2026-10-03_sm25_glm_tools_t1/`。不要整支合并：`2026-10-03_sm24_glm_tools_t1/`、`2026-10-03_sm25_glm_tools_t1/`、`2026-10-03_sm24_glm_tools_t1_setup_failed_no_env/` 三个原始运行目录留在 T1 分支。提交说明写明来源提交。
2. **登记新版本。** `python -m src.agent_runtime.agent_registry register --root . --version <版本号> --add-file tool:scripts/tool_scripts/bim_agent_budget.py …`，三个新工具文件都要显式加入。版本号自定，写明命名规则。冻结 `5bb10538` 保留。
3. **新底座上接通 T1。** 按验收标准 C 做：`deadline_epoch` 与新底座计时同起点；`floor_plan_images` 加显式入口参数和配置字段；到点或未经模型选定就停止时复用 T1 的保底交付；子角色按子任务截止时间写；理清新底座自己的时间/预算提示与 T1 提示的关系。用脚本化模型做离线反例。
4. **两底座一致性核对。** 写一个核对脚本：对 sm24、sm25、sm21 三例，分别取 Claude Code 线准备好的请求（可参考 T1 的 `glm_tests.py prepare`，在模型进程边界拦住，不启动模型）和新底座准备好的请求，逐字节比较系统指引、工具目录、任务正文。不同之处逐项列出理由。Claude Code 运行器的回执里加上当前 Agent 版本号。
5. **检查。** 阶段 0–3、R1、R2 全部检查，加 T1 的工具检查（T1 交付时 `tests/test_bim*.py` 共 215 项＋定向）。原 5 项“与冻结基准一致”的检查按登记版本校验。冻结 75 步回放（`test_runtime_frozen_long_task.py`）写明在新版本下怎样保持有效，不放宽断言。

## 约束

- **主工作树此时正在跑订阅同条件对照**，在用主线的冻结工具。不要动主工作树里的任何文件，不要合入或推 main。
- 0 次模型请求：不调 Paratera、GLM 订阅，不用 DeepSeek。
- 在本工作树跑检查时设 `PYTHONPATH` 指向本工作树，临时目录放在本工作树内，用完删掉；pytest 显式用 2 个 worker。
- 不改几何内核、校正内核；T1 四项的行为不改（漏洞修补留给阶段 4 全楼检查包）。

## 交付

约 90 分钟内完成。最终回复包括：带入的文件与来源；新版本号与登记结果；C 的实现与每个离线反例的实际结果；D 的核对结果（三例逐项）；重跑的检查与结果；新增提交列表；未完成项。交付报告放 `AI_agent/logs/experiments/2026-10-03_runtime_r3/README.md`。
