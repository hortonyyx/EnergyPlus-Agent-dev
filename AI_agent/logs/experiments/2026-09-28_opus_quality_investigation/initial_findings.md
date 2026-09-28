# 初步发现（阅读 Astra 归因记录之前写成）

调查者：Opus 5.5（claude-opus-5-5，max），2026-09-28 10:25–10:45 UTC，基准 ceb8b1df，分支 dev/opus-quality-20260928。
材料仅为各 run 的 inputs / agent_request / agent_receipt / tools.jsonl / 公开流事件（跳过 thinking 块）/ plan_drafts / candidate / evaluation 下由既有评价器生成的 GT 比对文件，以及原图。此时尚未读 run 目录 README、manual_review、behavior_audit、object_traces 及 worklog。

说明：本树检出时为空工作树（仅建了稀疏规则、没有检出文件），我用 `git read-tree -mu HEAD` 在本工作树按既有稀疏规则检出，未改主树。

## 可复现脚本与输出（本目录）

| 文件 | 作用 |
|---|---|
| `survey_runs.py` → `runs_survey.json/.md` | run53–83 请求/回执/工具动作/交付计数/GT 分区与窗比对汇总 |
| `reevaluate_partitions.py` → `partition_tolerance_reevaluation.json` | 用**未改动**的 `src/agent/judge/source_partition.compare_partitions`，把 sm21 所有候选按 0.02/0.10/0.30 m 容差重算；内墙线比较照抄 `partition_evidence.py` 的构造 |
| `sm24_sm25_evaluation.json` | 同法重算 sm24/sm25 交付件，并读取已有原图分区比对 |
| `public_actions.py` | 只抽公开 text / tool_use / tool_result，跳过 thinking/redacted_thinking |
| `behavior_table.json`、`first_declaration_basis.json` | 每 run 参考读取、首建时间、像素工具量、首份声明的定位依据 |

## 1. 事实（有直接证据）

**F1 请求端控制很干净。** run57、run58、run81 的 `agent_request.json` 整文件 sha256 相同（44ee38d1…）；三者 CLI 2.1.280、模型 claude-sonnet-5/medium、36 个 MCP 工具名集合相同（init 事件），图像 hash 相同，`plan_partition` 参考文本 hash 相同。后续版本为 39 个工具，系统提示改动只涉及房间用途、候选配额、证据 view_id、命名（run57→run83 diff 32 句），没有新增“像素/灰填判墙”指引。产品运行每次在新的 `/tmp/bim-agent-cwd-*` 启动、独立 auto-memory 路径，仓库根无 CLAUDE.md/AGENTS.md。

**F2 sm21 的“severe”大多是 2 cm 评价容差造成的，不是拓扑退步。** 评价器 `partition_evidence.py` 把任何超过 0.02 m 的内墙线差异整段记为 missing+extra 并判 severe。重算（交付件）：

| 类别 | run | 最大边界偏差 | 说明 |
|---|---|---|---|
| 好结果 | 57, 58 | 0.003 / 0.012 m | 隔墙按尺寸链放在双线中线 |
| 仅偏移 ≤0.11 m，0.10 m 容差下零差异 | 73, 79, 80, 81 | 0.027–0.107 m | 例如 run81 二层走廊墙 y=2.942/5.058（=3.0/5.0 ∓ 0.058，约半个 120 mm 隔墙厚）；原图左侧尺寸链 3000/400/1200/400/3000（中线），右侧 2940/340/1200/340/2940（墙面），两种参照面图上都有 |
| 偏移 0.19–0.22 m，拓扑对 | 69（70 由 69 候选续做，几何相同，非独立样本）, 71, 76 | 0.19–0.22 m | 0.30 m 容差下零差异 |
| 偏移 0.56 m，拓扑对 | 74 | 0.558 m | 0.30 m 容差下仍差 6.9 m 墙线 |
| **对象级错误** | 72 | 5810 m | 锚点写成毫米（x_anchors [[425,0],[1816,15000]]），整栋放大 1000 倍，工具源校验照样 pass |
| | 75 | 10 m | 一层南北各 3 间办公室被声明成 2 个 open office（首稿只有 2 条走廊墙） |
| | 83 | 7.5 m | 二层两间会议室被声明成一个 hall |
| | 82（429 中断） | 0.2 m | vertical_extent_changed |

同一把尺子下，**好结果本身也不全是“minor”**：sm25 run53/54 严格 GT 为 severe（最大偏移 0.179/0.166 m，0.30 m 容差下零差异）；sm24 run55/56 严格 GT 为 severe（0.05 m），原图分区参照为 minor。即“好”在 sm21 是亚厘米，在 sm25 是 ~0.18 m 偏移。

**F3 对象级错误在首份声明即进入，此后没有被纠正。** 逐候选重算：run83 candidate_01（一层）拓扑正确，candidate_02（二层首建）即出现 merge，03/04 延续；run75 candidate_01（一层首建）即 3 个空间，二层首建正确，交付件保留一层错误；run72 从 candidate_01 起即 1000 倍。

**F4 模型看到了正确证据，但用错判据否定它。** 原图 2f_view.png（sha d7cd58d3…）上两间会议室之间是清楚的双细线隔墙、两侧各一扇门；全图**所有内隔墙都是不填灰的双细线**，只有外墙填灰。run83 二层声明原文：“North half … is ONE open conference hall: the thin non-filled vertical line near x=718 has no gray fill and no wall-thickness pixel support”，此前它用 rgb [140,140,140] 灰色剖面在 y=700–720 行得到 0 像素。同一份声明里其它同样不填灰的隔墙却被接受。run75 一层：“no full-height partition found between desk bays: pixel profile at the exterior wall row showed only a weak partial nib”——探测位置在外墙行，本身就测不到内隔墙。随后两 run 的 `check_source_space_relation` 都只是按模型自己给的 expected（same_space）确认“consistent_with_supplied_expectation”，工具返回里 `drawing_fidelity: not_evaluated`、`coverage: caller_selected_point_pairs_only`。

**F5 行为分水岭：直接读图+尺寸链 vs 像素剖面主导。**

| 组 | reconstruction 参考 | 首建时刻 | 首建前像素工具 | 首份声明依据 |
|---|---|---|---|---|
| run53–59、61、62（11 次冷启动，含 6 次好结果） | 0/11 读取 | 93–259 s | 0（仅 58 有 8 次） | 全部写“尺寸链 + 画线中线/外墙面”，无 pixel/ink 字样 |
| sm21 run69–83 冷启动 12 次 | 11/12 读取（80 未读） | 487–849 s | 2–36 | 9/12 写 pixel/ink/墙厚实测 |

用户提示原文要求 “Read reconstruction, plan_partition and plan_assembly”，好结果 57/58 实际没读 reconstruction 和 plan_assembly；同请求的旧树 run81 读了。该参考要求“双线墙测两个墙面并显式选代表面”“用 view_pixel_profile 读支撑区间”“两条峰不一定是墙面”“家具也有边”。后续声明中的“墙面测量/约 120 mm 隔墙厚/灰色像素区域”与此一致。

**F6 窗高：好结果按窗分族，后续常整层套一族。** run57 一层 7 扇窗分三族（1.0–2.6 ×5、南侧小窗 1.5–2.1、东窗 1.0–2.8），GT 15/15 complete。run79/83 一层 7 扇全用 1.0–2.6；run69 全用 0.9–2.1；run80 一层全用 1.6–2.6（7 个 miss）；run81 像素测得 1.04–2.69 等（2 miss、4 within_tol）。

**F7 时间线与范围。** 468d83f7 提交于 09-26 16:41，run57 于 16:11 启动（早于该提交 30 分钟，src 是否完全等同未核），run58 于 09-27 02:43（之间 src 无提交）。第一个出问题的 sm21 冷启动 run69 在 09-27 07:24，之前有 dc1213e9…b79d7adf 六个生产提交。sm25 在 run54 之后**再没有**跑过；sm24 冷启动 59/61/62 拓扑全对（偏移 0.06–0.18 m）；sm24 run60、63–68 是带 seed 的续做/用途任务，几何继承 run59/62，不是独立几何样本；run77/78 为 0 token 的 429；run76/82 为 429 中断（run82 交付件非模型自选收尾）。

## 2. 假设与目前证据强度

| 编号 | 假设 | 状态 |
|---|---|---|
| H1 | 相当一部分“退步”是评价口径：2 cm 容差把参照面/像素量测偏差判成 severe，且好结果跨例口径不一 | **直接证据**（重算） |
| H2 | 真实几何退步集中在“隔墙存在性判断”：模型用像素/灰填判据否定明显的细双线隔墙；relation 检查只做自洽确认，无法纠错 | run75/83 **直接证据**；发生率仅 2/12，样本小 |
| H3 | 从“直接读图+尺寸链”转向“像素剖面主导”是好坏行为的主要分水岭，与是否读取 reconstruction 方法参考高度相关 | **相关性强**（11/11 vs 11/12），同请求 run58 vs run81 也分属两侧；run80 未读仍走像素路线、run58 用了 8 次像素仍精确，是反例/边界；因果**未证** |
| H4 | 生产代码改动（09-27 六个提交）是主因 | **证据弱**：旧树 run81 同样出现慢/像素主导/面偏移；但 81 没有对象级错误，n=1，不能排除代码让坏行为更易出现 |
| H5 | 同一请求下模型行为在 09-27 前后发生了服务端漂移 | **不能判定**：只有 57/58 vs 81 一组对照，无法区分漂移与抽样方差 |
| H6 | 毫米单位错误（run72）是工具缺少物理尺度合理性检查 | **直接证据**（15 km 建筑 source_validation pass） |

## 3. 证据缺口

- 旧树仅 1 次复跑；没有“强制读/不读 reconstruction”或“去掉像素工具”的对照；sm24/sm25 在新版本下没有冷启动整案（77/78 为 0 token）。
- 窗高错误只做了族统计，未逐窗追到证据动作。
- 用户级 CLI 全局配置（~/.claude）未记录在 run 产物中，按本次边界未读取，是残余未控变量。
- run57 启动时刻早于 468d83f7，其 src 与 468d83f7 是否逐字节一致未核（请求文件一致）。
