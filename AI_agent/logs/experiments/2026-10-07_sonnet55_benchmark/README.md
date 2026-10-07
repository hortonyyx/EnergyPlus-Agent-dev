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

| 运行 | 用时 | 轮数 | 空间 | 实质错误 | 门窗位置 ≤5／5–10／10–30／>30 cm | 房间边界 | 外墙高度 | CLI 估价（非账单） |
|---|---|---|---|---|---|---|---|---|
| A1 第一次 | 9.2 分钟中断 | 30 | — | — | — | — | — | 1.75 美元 |
| A1 重跑 | 9.2 分钟被 Claude 会话额度打断，按最近完整稿兜底交付 | 29 | 29/29/29 | 无 | 60／1／0／0 | 22／0／7／0 | 34/34 在 5 cm 内 | 2.09 美元 |
| **A2** | **12.2 分钟，自己交付** | 37 | 29/29/29 | **无** | **61／0／0／0** | 22／0／7／0 | **34/34** | 2.76 美元 |
| **A0**（GLM，同线路同 domain 同 1 小时预算） | 56.4 分钟，自己交付 | 64 | 29/29/29 | 漏 2 扇、多 1 扇、1 扇挂错 | 34／17／2／5 | 3／13／11／2 | 29/34 在 5 cm 内（1 扇 >30 cm） | 6.00 美元（按 GLM 线路，非账单） |
| 参照：GLM 分工（合入后，同晚） | 54.8 分钟 | 107 次请求 | 29/29/29 | 二层走廊被拆 | 43／15／2／0 | 2／15／9／3 | 34/34 | — |
| 参照：GLM 单模型（10-07 下午） | 130.5 分钟 | 86 次请求 | 漏走廊 | 有 | 49／7／1／4 | — | 31/34 | — |

- **A1 第一次失败是我方线路的问题：** Claude Code 线路迁到 Windows 后没真正跑过，CLI 拉起的工具服务按 GBK 读 UTF-8 文件，所有建模工具报 `'gbk' codec can't decode`（11 次）。修复（`81a6cc69`）后用这次的真实平面稿按同一隔离环境确定性重放，保存正常。我先做的冒烟测试只调了 `inputs`、没建模，所以没测出来。
- **A1 重跑被额度打断：** 第 9.2 分钟收到 “You've hit your session limit”，这是 Claude Plus 的 5 小时会话额度，与 Opus 主会话共用；此前已建出两层完整稿，评价用的是兜底交付的候选 6。
- **A2 没有派 Haiku：** 子代理可用（冒烟测试已证实 Haiku 能调同一套工具），但 Sonnet 5.5 自己判断不需要，原话 “I did not use the Haiku worker; all reading and building was done directly”。所以 A2 事实上是一次完整的单模型标杆；“强模型自己会怎样分工”这一问没有得到答案，只说明在现有 domain 上做 sm25 这种规模它不觉得分工划算。
- 房间边界 10–30 cm 的 7 处两次相同，待看是否为外皮／中线等约定差（不影响实质判断）。

成果查看（A2）：[平面图 F1](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/display/plan_F1.png)、[F2](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/display/plan_F2.png)；回叠图 [平面 F1](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/overlays/plan_F1.png)、[F2](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/overlays/plan_F2.png)、[北](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/overlays/elevation_North.png)、[南](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/overlays/elevation_South.png)、[东](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/overlays/elevation_East.png)、[西](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/overlays/elevation_West.png)；[BIM 查看页](../../../archive/local_backup/bench/A2_sonnet55_haiku_workers/dev_evaluation/display/viewer.html)。A1 重跑与 A0 的同名文件分别在 `bench/A1_sonnet55_single/dev_evaluation/`、`bench/A0_glm_single_cc/dev_evaluation/` 下。

## 行为观察

**A2 的做法（36 次工具调用，`scripts/dev/observe_run.py`）：**
1. 盘点输入，看两张平面整图，读平面格式参考（第 0–1 分钟）。
2. 按块放大逐块看：一层 6 块、二层 5 块，每块约 500×400 像素、放大 3 倍；**一次像素剖面都没用**。四个立面各看一次整图。
3. 用外轮廓总尺寸 25000×20000 定比例（每轴两个锚点），外墙取外皮、隔墙取中线，一次写出整层：第 4.1 分钟建一层、4.7 分钟建二层，都是一次建成；第 4.9 分钟总装出 29 个空间、61 个门窗。
4. 高度：读依据参考，放大一处立面细节，按立面的标注尺寸链（1000/1600/1000 等）分 3 批写入全部 34 个外墙门窗高度，每个立面画一次回叠图核对（第 6–10 分钟）。
5. 一次批量设房间用途、改一条说明，第 11.6 分钟交付。

**与 GLM 的差别：** GLM 分工的平面读图员每层用 21–22 次像素剖面、第 24 分钟才首次试建；GLM 单模型第 38 分钟才首次建模（看图 56 次、剖面 49 次）。Sonnet 第一眼读得准，又按“整图 → 分块放大 → 一次写全 → 建 → 回叠核对 → 成组写高度”的顺序干脆地做完。前者是模型能力，后者是方法，可以写进 domain 给小模型用：提速包 D1l 按这个顺序改写平面读图员的做法；配合 Q1 的墨线对齐与尺寸链，读图员只需给出大致位置，由代码对准。

**A0（GLM）对照：** 同线路、同 domain、同 1 小时预算，只换模型。第 31.5 分钟才首次建成平面（此前建平面、改平面报错 29 次：墙线压外轮廓、悬线、两个房间种子落在同一空间、参数缺字段等），第 54.7 分钟总装、55.5 分钟交付；工具调用以改平面 20、看图 16、剖面 10 为主。用时约为 Sonnet 的 4.6 倍，门窗位置与高度明显更差，房间划分这次全对。**模型能力与方法分开看：** 同一方法下 Sonnet 12 分钟全对、GLM 56 分钟有门窗错误，差距来自模型（第一眼读准与按格式一次写对）；方法上可借鉴的是 Sonnet 的顺序（见上）。**预算的影响：** GLM 单模型在新底座上给 3 小时预算时用了 130.5 分钟，这次给 1 小时就在 56 分钟内交付，房间划分反而全对，说明告诉模型的预算会改变它的节奏，值得在提速中利用（读图员与调度员的预算按角色给）。

**副作用：** 每写一批高度就存一份候选，A2 共存 38 份（上限 64），是 10-06 登记待议的“单模型存档改法”问题，这次没有超限。
