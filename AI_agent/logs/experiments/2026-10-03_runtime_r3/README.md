# R3 交付：T1 接入新底座与两底座 Agent 一致性

执行人 Astra，派工人 Opus 5.5。依据 [派工单](brief.md) 与 [验收标准最后一节](../../../project/unified_agent_acceptance.md)。工作树 `/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-r3`，分支 `dev/astra-r3-20261003`，起点 `0b883a41`。本包只在本分支提交，没有合入或推送；主工作树未写入任何文件。真实模型/API/订阅请求 **0**，DeepSeek **0**，子代理 **0**。

T1 已按路径带入，新 Agent 为 **`t1-20261003-r3`**。新底座已接上统一起止时间、显式楼层范围、子任务独立截止时间，以及复用 T1 的停跑交付；Claude Code 请求和回执也记录该 Agent 版本。sm24、sm25、sm21 的准备请求核对通过，**563 项不同检查全部通过**。这是离线迁移验证，不是新的整案建模成绩。10-03 UTC 约 15:08 开工，16:07 全套检查完成，在约 90 分钟上限内交付。

## A. 带入文件与范围

导入提交 `21243528` 明确记录来源 **`74e27da3`**，使用按路径取文件，共 39 个文件，导入时逐字节相同：

- 工具 5 个：`scripts/tool_scripts/bim_agent_budget.py`、`bim_agent_facade_checks.py`、`bim_agent_feedback.py`、`bim_agent_guidance.py`、`run_bim_agent.py`。
- 测试 5 个：`tests/test_bim_agent_tools.py`、`test_bim_facade_counts.py`、`test_bim_located_heights.py`、`test_bim_time_budget.py`、`test_bim_tool_feedback.py`。
- [T1 汇总目录](../2026-10-03_tool_package_t1/README.md)，以及行为记录目录下 [sm24](../2026-10-01_behaviour_records/records/2026-10-03_sm24_glm_tools_t1/timeline.md)、[sm25](../2026-10-01_behaviour_records/records/2026-10-03_sm25_glm_tools_t1/timeline.md) 各自的压缩记录、摘要和时间线。

三个 T1 原始运行目录没有带入。导入后仅在 `run_bim_agent.py` 加三行读取/记录 Agent 版本；其余导入文件继续与 T1 来源逐字节相同，T1 四项行为没有改写。几何、校正、旧执行内核与全局项目文件未改。最终 [范围核验](scope_audit.json) 列出每个导入文件的字节数、SHA256、证据体积和主工作树冻结文件的只读核对结果。

最终证据总量约 **1.5 MB**，低于约 2 MB 的要求。主工作树 45 个冻结登记文件经只读哈希核对全部相同。本包临时目录、三例准备请求临时目录和 75 步回放临时目录已清理。

## B. 登记版本

命名规则为 `t1-<T1 纳入日期 YYYYMMDD>-<集成包>`，表示工具包与迁移批次，不是工作模型型号。登记共 **48 个文件**，三个新工具模块都显式加入。登记时源码提交为 `cdf60d38d6aa03009a3361aec971fdee082bb2a4`；登记提交 `091c9d7f`。当前版本指向新版，历史 `5bb10538` 的登记对象完整保留。

实际使用的命令：

```bash
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 python -m src.agent_runtime.agent_registry register --root . --version t1-20261003-r3 \
  --add-file tool:scripts/tool_scripts/bim_agent_budget.py \
  --add-file tool:scripts/tool_scripts/bim_agent_facade_checks.py \
  --add-file tool:scripts/tool_scripts/bim_agent_feedback.py
```

| 工具目录 | SHA256 |
|---|---|
| coordinator | `e4457f336289acaea95910ef576f1befeb4ea1af71238f7844495fb842772c8a` |
| coordinator_mesh | `6a47b4727d3fce38388451039e8e76353f987087fc95d1891637f2b477270da8` |
| readonly | `1d59fcd48bd4ee21bfba42c5b41aa0d1e30af1a94d994a8a760e547cc2182b57` |
| readonly_mesh | `79caa2a12054e23c129a965a9a97c1c553b6b34cf860123f4b7458bdecb2828f` |

已有登记校验继续核对全部文件；改文件即拒绝的参数化反例从 5 项扩展为 8 项，包含本次三个新模块。另保留“明确登记新版后可通过”、未登记依赖和工具目录变动被拒的检查。旧版记录不变由范围核验再次确认。

## C. T1 在新底座的接线与离线反例

`runtime_entry.execute` 在准备输入和工具服务前取一次启动时间，写进 `bim/inputs.json` 的 `started_epoch`、`time_budget_seconds`、`deadline_epoch`，并传给运行循环。准备服务所用时间计入总时限；恢复仍使用原有时间，不重新获得一轮预算。运行回执记录相同起点与截止时间。

单模型入口和外层协调入口都支持可重复的 `--floor-plan-image`；运行配置支持 `floor_plan_images` 列表，必须引用已准入的输入文件。没有显式声明时，沿用 T1 的数字楼层文件名提示；无可靠范围则不声称完整。旧运行配置不改写。

例如双层案例在该 case 配置中加 `"floor_plan_images": ["1f_view.png", "2f_view.png"]`，生成启动参数 `--floor-plan-image 1f_view.png --floor-plan-image 2f_view.png`。这声明预期楼层对应的输入图，不提供房间、窗数或几何答案。

`runtime_delivery.py` 直接调用现有 `fallback_selection` 和 `Toolkit.delivery`，不另写挑选、完整性或查看器规则。在正常结束、模型/工具预算停止、时间停止等运行收尾前完成交付，并把 JSON/HTML 计入最终产物。到点时按 T1 优先选最近完整全楼稿；未到点且模型已选定时保留其选择；没有选定则执行保底。外层协调服务结束或到点也执行相同收尾。没有保存稿、交付失败分别明确记录，不伪造成功。

子角色各自使用证据包内原图和独立只读工具服务，目录位于子任务下；截止时间取子时限与父任务剩余时限的较小值。启动子服务消耗子预算；父目录不改写，兄弟任务不互改时间或量测附属文件。原有统一工具锁保留，工具动作仍串行执行，模型请求的并发机制不变。

时间提示的关系：T1 工具回包负责同一套已用/剩余分钟与阶段提醒，文本没有修改。新底座的模型/工具/token 额度是执行层硬限制，不向根模型再加一套倒计时文字；已有状态消息仍保存原任务。子角色原有 `task_limits` 和 `remaining_budget` 状态采用本次实际子时限，并使用 T1 的只读提醒，不要求只读角色保存全楼稿。

反例使用脚本模型、合成平面与真实 FastMCP/T1 工具实现，仅替换通信传输和时钟；没有把真实模型或历史答案接入生成。所有新反例在 `tests/test_runtime_r3.py`，实际结果由 [counterexamples](counterexamples/) 及 [R3 检查记录](validation/r3.json) 保存：

| 情形 | 断言的实际行为 |
|---|---|
| 100 分钟预算，起点 1000，过半到 4000 | 返回“时间已过半”，列出未出草稿的 `plan.png, upstairs.png` |
| 剩余不足 15%，时刻 6101 | 返回原 T1 文本“停止新的读图，只修已列出的问题并交付” |
| 工具调度与执行之间跨到截止 7000 | 工具拒绝写入，记录 `Run deadline reached` 及“时间上限已到”；候选数为 0，底座以时间耗尽停止 |
| 完整稿 03 后又保存并选定部分稿 04，然后到点 | 实际交付 03；标记 `latest_complete_fallback_not_agent_selected`，记录最新保存稿仍是 04 |
| 完整稿 03 后保存部分稿 04，未选择就正常结束／用尽模型次数 | 两种情况都交付 03，说明是保底选择 |
| 只有部分稿 01 后到点 | 仍交付 01 和 HTML；`complete_building=false`，明确缺 `upstairs.png` |
| 未到点，模型明确选择部分稿 01，另有完整稿 03 | 保留 01，`selection_origin=agent_selected`，不把不完整标记抹掉 |
| 准备工具耗时 600 秒 | 回执已用时间含这 600 秒，截止仍为 7000 |
| 子预算 30 秒、父剩余 100 秒 | 子截止为 1030；90% 时显示只读提醒，父输入字节不变 |
| 子预算 300 秒、父剩余 100 秒 | 子截止截到 1100；只读提醒按实际 100 秒计算，父输入字节不变 |
| 外层协调器到点 | 使用相同部分稿交付逻辑，源模型字节保持不变 |
| Claude Code 的已过期运行 | 不启动模型进程，回执仍带新版 Agent 标识 |

“完整”沿用 T1，只表示声明的楼层覆盖，不能替代建筑几何和原图质量验收。

## D. 两底座逐例核对

[核对脚本](compare_runners.py) 先用 T1 的案例参数准备 Claude Code 请求，在 `Popen` 模型进程边界拦住，再启动本地 MCP 读取目录。新底座通过普通入口和脚本适配器截取真正准备发送的请求；其任务独立取自各例历史基准，只把 3000 秒改为共同的 6000 秒，不把刚准备的 Claude 请求复制过去。实时 HTTP 发送也被阻断。

| 案例 | 系统指引 | MCP 目录及名称/说明/参数 | 任务正文 | 楼层范围 |
|---|---|---|---|---|
| sm24 | 9668 字节相同 | 42 工具相同 | 1360 字节相同 | `1f_view.png` 相同 |
| sm25 | 9668 字节相同 | 42 工具相同 | 1360 字节相同 | `1f_view.png, 2f_view.png` 相同 |
| sm21 | 9668 字节相同 | 42 工具相同 | 1360 字节相同 | `1f_view.png, 2f_view.png` 相同 |

三例原图哈希也逐项相同，均为 6000 秒、24 候选。工具目录按相同规范序列化后逐字节比较，另比较新底座实际函数包装中的名称、说明和参数结构。[完整结果](runner_parity.json) 保存逐项哈希、字节数、任务来源以及全部附加状态消息。

差异逐项保留：① Claude Code 使用 Anthropic/MCP 名称空间，新底座使用 OpenAI 函数包装，线路与协议不同；② 新底座已有额外的当前状态 user 消息，保留原任务和来源；③ Claude Code `effort=medium` 到上游的映射未捕获，订阅新底座不发送未经核实的思考参数，默认输出上限 32000；④ 两次顺序准备的绝对时间、输出路径、provider/input_mode 不同，但时长和楼层范围相同。没有启动 Claude Code，因而不声称其私有 HTTP 上下文或两协议上游行为已被证明相同。

可重复核对，不会请求模型：

```bash
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 python AI_agent/logs/experiments/2026-10-03_runtime_r3/compare_runners.py
```

## E. 验证与历史基准

所有 pytest 调用显式 `-n 2 -s`，`PYTHONPATH` 指向本工作树，临时文件放本工作树；`-s` 避免本环境匿名捕获文件的 truncate 故障，与 T1 原有做法一致。每组保存命令、JUnit、测试 ID、源码 SHA256，五组均确认运行期间相关源码未改变。另实际检查入口、运行循环和 T1 工具的 Python 导入路径，均来自本工作树。

| 检查组 | 本轮结果 |
|---|---|
| 阶段 0–3、R1、R2 短联合（原 319＋新增 3 个模块篡改反例） | **322 通过**，284.32 秒 pytest 墙钟 |
| 长任务故障矩阵 | **10 通过**，1692.07 秒 pytest 墙钟 |
| 真实工具 75 步回放及相关检查 | **3 通过**，790.40 秒 pytest 墙钟 |
| T1 `tests/test_bim*.py` | **216 通过**，304.95 秒 pytest 墙钟 |
| R3 新离线反例 | **12 通过**，105.59 秒 pytest 墙钟 |

合计 **563 个不同测试 ID**，无失败、错误或跳过。各组完整记录：[短联合](validation/short.json)、[长任务](validation/long.json)、[75 步回放](validation/frozen.json)、[T1](validation/t1.json)、[R3](validation/r3.json)。这里的时间是离线检查耗时，不是产品整案出模时长。

冻结 75 步仍加载 run99 不变的历史参数、原始证据与脚本回复，实际执行新版 T1 工具。原有 75 次工具调用、76 次请求、预期错误、图片哈希、源版本、状态覆盖、压缩与重新取图断言全部保留；只改测试文件开头的解释文字。范围核验还把基点和当前测试的整份可执行 AST 对比，不能靠删断言通过。T1 增加的反馈文字允许变化，既有语义断言照常要求满足。T1 时间边界另由本包反例验证，历史回放不冒充新模型建模。

首轮短联合为 317 通过、5 失败，保留在 [first_short](validation/first_short/short.json)。其中三项是阶段 0 样例声明源码版本 `5bb10538`，却按当前工具文件解析旧哈希；修正生成器与核验器，从该样例声明的提交读取代码，历史样例 JSON 和哈希不改。另两项是直接调用 `_stop` 的测试夹具未初始化新增启动时间；只补齐夹具，预算断言不改。新反例开发时的纯静止模拟时钟也曾造成零耗时记账校验失败，夹具改为保留极小正向单调时间，没有为此改生产记账。

重跑一组的命令如下，组名还可为 `long`、`frozen`、`t1`、`r3`；每次会创建并清理本树内的专用临时目录：

```bash
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 python AI_agent/logs/experiments/2026-10-03_runtime_r3/validate.py short
```

## 提交与交接边界

| 提交 | 内容 |
|---|---|
| `21243528` | 按路径导入 `74e27da3` 的 T1 工具、测试和压缩证据 |
| `c58f4700` | 新底座时间、子角色独立服务和共用交付收尾 |
| `cdf60d38` | R3 离线反例、两底座核对脚本与版本篡改覆盖 |
| `091c9d7f` | 登记 `t1-20261003-r3`，保留冻结历史版本 |
| `3cfa6d56` | 按已记录提交解析历史样例，补齐测试夹具，独立准备任务核对 |
| `97257568` | 保存三例一致性、时间/交付反例与已完成检查的证据 |
| 本报告所在提交 | 最终两组长回放、范围核验、全部交付结论 |

本包必做项无未完成，等待 Opus 验收并决定合入；本分支不合入、不推送。未开展订阅同条件整案、阶段 4 或首批整案；T1“一条定位依据绑多扇也算通过”的已知漏洞按派工保留给阶段 4。本包不宣称恢复模型质量，也不把楼层覆盖等同于完整建筑质量。
