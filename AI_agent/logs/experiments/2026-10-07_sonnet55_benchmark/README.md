# Sonnet 5.5 标杆（10-07 夜，Opus）

**依据：** 用户 10-07 晚：“先让Sonnet5.5在domain上做一次（可以让它自由调度haiku来做role方案），有了一个标杆才好往上靠，但是要区分模型本身能力部分和方法论部分；另外每一次测试，你作为dev model都要仔细观察全流程的工作模式”。计划（用户同意）：A1 单模型 → A2 可自由派 Haiku 4.5，另跑 GLM 在 Claude Code 上的对照 A0；Sonnet 用 Claude 订阅，可与 GLM 同时跑；每次 1 小时保护线。

**迭代范围：** 不改 domain。runtime 只动 Claude Code 线路（`t1-20261007-cc1.1`，提交 `4b009ec7`）：Windows 上 CLI 需要的系统变量（迁移后这条线路其实起不来：隔离环境没带 `SystemRoot`，CLI 无法联网）；可选主型号 `claude-sonnet-5-5`（默认仍是 `claude-sonnet-5`）；可选 Haiku 子代理（开放 Claude Code 自带的 `Agent` 工具，只定义一个 `worker`，型号 `claude-haiku-4-5-20251001`，拿到同一份指引与同一套 BIM 工具；内置的其他子代理全部禁用）；关掉 CLI 的附带调用（标题用的 Haiku、自动更新），免得混进计量和型号核对。单模型首请求不变（四个工具目录指纹与 n1.1 相同）。

**环境：** 独立 CLI 由 2.1.280 升到 2.1.292（2.1.280 不认识 Sonnet 5.5 的型号元数据：报 unrecognized_model、按 20 万上下文处理；2.1.292 认作 100 万）。旧版本保留在 `~/.local/share/claude/versions/`。升级前后各做了极小探测：Sonnet 5.5 与 Haiku 4.5 实际回执型号正确；`Agent(worker)` 放行规则拦不住内置子代理，改用逐个禁用规则后内置的 general-purpose 被拒、worker 正常；Windows 冒烟测试（Sonnet 5.5 low 调一次 `inputs`，再派 worker 调一次）28 秒通过，回执无型号漂移。

**条件：** [bench.json](bench.json)，由 [launch.py](launch.py) 在 D 盘固定提交的运行工作树 `runs-cc`（`4b009ec7`）启动。案例 sm25（两层、29 间、61 个门窗，GLM 两种模式都出过房间划分错误），只给原图，任务说明与三例对照 `sm25_single_cmp` 相同（只把预算改为 3600 秒；A2 把“工作组织”一句换成可派 Haiku 子代理）；思考档 medium；候选上限 64。

| 编号 | 线路 | 主型号 | 子代理 | 对照意义 |
|---|---|---|---|---|
| A1 | Claude 订阅 | Sonnet 5.5 | 无 | 模型能力（同 domain、同底座） |
| A2 | Claude 订阅 | Sonnet 5.5 | Haiku 4.5，自由调度 | 强模型自己设计的分工方式与 Haiku 能接什么活 |
| A0 | GLM 订阅（Claude Code） | glm-5.3-flash | 无 | 与 A1 同底座同 domain，只换模型 |

参照：09-26 Sonnet 5 同案单模型 run53：7.4 分钟、工具调用 34 次、看图 7 次、第 4.3 分钟首次建模；10-07 GLM 新底座单模型 130.5 分钟、86 次请求、二层东段约 10 m 走廊漏建。

**顺序：** A1 先跑（21:31 开始）；看过 A1 的用量与结果再跑 A2；A0 是 GLM，排在 GLM 串行队列（sm25 分工合入效果、sm24 分工全 low）之后，不与其他 GLM 整案同时跑。

## 结果

（运行后填写）

## 行为观察

（运行后填写：时间线、请求数与每次用时、工具构成、时间花在哪、错误最早出现在哪一稿哪一步；A2 另记派了哪些活、Haiku 做得怎样）
