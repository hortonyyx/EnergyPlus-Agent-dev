# G-a 机器那半：sm25-L gt 重做重签 —— 机器能做的已经做完，签字那半今天在代码层面走不通

> **档位 = 探索档**（[CLAUDE.md §0.2](../../../CLAUDE.md)）。⛔ 本目录不产成绩，只产读数与结论。
> **日期 = 2026-09-06（UTC）**。⚠️ 本目录原名 `2026-09-07a_Ga_machine_half` —— 那是宿主会话按
> **北京时间**取的名，与仓库通用的 UTC 日期惯例（`2026-09-06b_authoritative_suite` 等）差一天，
> 且会与明天真正的 09-07 撞车 ⇒ **已改名为 `2026-09-06d_`**，内容未改。

## 0. 这一程是怎么开始的（⭐ 关于那张没有 README 的 PNG）

`worklist_annotated.png` 是 **2026-09-06 17:05 UTC** 落到工作树里的，比第七程收工提交
（`da241814`，16:08 UTC）晚一小时，且当时**没有任何 README 或其他产物伴随** ——
按 [CLAUDE.md §5#8.7](../../../CLAUDE.md) 它长得就像一件「席位撞额度留下的静默孤儿件」。

**它不是。** 主控查了会话记录，找到了产出方：

| | |
|---|---|
| 会话 | `62867848-ff54-446a-a6ec-1a786a4be348` |
| 记录位置 | `~/.claude/projects/**c--Users-Horton-Desktop-EnergyPlus-Agent-dev**/` |
| cwd | `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev`（**Windows 宿主，不是容器**）|
| 存活 | 16:50 → 17:09 UTC，**用户只发过一句 `@AI_agent/CLAUDE.md 开工`** |
| 结束方式 | 正常收尾，末尾向用户提议「先重开进容器再落档」 |

⇒ 它**不是** orphan，是一段**被主动挂起、等重开容器**的会话。
⭐ 它挂起的原因本身值得记：**项目记忆按 cwd 路径做 key** ——
宿主那个 key 下 0 个条目，容器那个 key 下 157 个条目，
所以那一程**整程没有项目记忆**（文件一个没丢，只是寻址不到）。

⚠️ **本 README 里的每个数字都是主控在容器里【重新量的】**，⛔ 不是转引那一程的自述
（[[citing-someone-elses-fact-does-not-transfer-responsibility]]）。
复量的结果：**它的结论条条成立**，且其中一条可以量得更准（见 §2）。

⚠️ **一笔留在宿主上的账**：那一程为了跑验证，在 **Windows 宿主上自建了一个容器 `ep_agent_dev`**
（现成 devcontainer 镜像 + 绑同一个工作区）。容器内看不到它（本容器无 docker 客户端），
**需要用户在宿主上 `docker rm -f ep_agent_dev` 收掉**。

## 1. 机器那半：✅ 早就落地了，且是【当前的】

| 查的事 | 读数 |
|---|---|
| trio 在不在 | `case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/{as_measured,revisions,as_signed}.json` 三件齐 |
| 是哪次产的 | `f4a5e726`「09.05g_a11_reemit_facts: sm25-L + sm24 staging trios on the 1mm grid」= **A-11 合并时已按 1 mm 重出** |
| 还成不成立 | `tests/test_gt_facts_staging_sm25.py` **9 passed**（主树，`m.__file__` 落在 `/workspaces/EnergyPlus-Agent-dev/`）|

⇒ **G-a 的「机器那半」不需要重做** —— A-11 那次已经连带做了。
⛔ 别把它读成「09-05 跑过一次、可能过期」：上面那 9 条锁就是在**今天的 HEAD** 上重新对账的。

### ⚠️ plan.md 里「那 5 条线」已经过期 —— 现在是 3 条

`CHANGED_HANDLES = ("13AD", "13AC", "13AF", "160A", "13AE")` 是 08-28 用户裁定进 `revisions` 的那 5 条。
**A-11 的 1 mm 入库规整把 13AC / 160A 的差额吸收成表示残差**（实测：这两条在两份图上都是
`|dx| = 0.000u` 的正交线，差额落在 1 mm 格以下）⇒ 现在只剩 **3 条**：`13AD` / `13AE` / `13AF`。

- 现行锁写死的就是 3：`tests/test_gt_facts_staging_sm25.py:71` `assert len(recomputed) == 3`。
- ⚠️ **09-01 的建库脚本已经陈旧**：`logs/experiments/2026-09-01c_f156v3_baseline/rebuild_sm25_facts_staging.py:79`
  仍 `assert len(candidates) == len(CHANGED_HANDLES)`（=5），今天跑必红。⛔ 它不是生产路径，只是账要记着。

## 2. ⭐⭐⭐ 本程最硬的一条：这 3 条记录是【同一次刚体旋转】，而台账只会写「平移」

跑 [`measure_the_one_wall.py`](measure_the_one_wall.py) 复现下面每一个数。

**病灶 = 1F 一道 120 mm 厚隔墙，整体绕东端转了 329 角秒（0.0914°）。**

| 证据 | 读数 |
|---|---|
| 三条线各自偏离最近坐标轴 | 13AD / 13AE / 13AF **全部 = `1.595743326e-03` rad** |
| 三条之间的差 | **1.3e-14 rad** ⇒ 一次刚体旋转，⛔ 不是三个独立的画图错误 |
| 旋转中心（由 as_received→signed 的 Δy 对 x 回归求 Δy=0）| x = **89999.229u** |
| 隔壁墙 13AA / 160C 的交点 | x = **89999.785u**，y = **99998.638u** |
| 两者差 | **0.556u = 0.0556 mm** ⇒ 旋转中心就是那个交点 |
| 西头因此高了多少 | 同一条线内坡度 **58.084u = 5.81 mm**；相对签字图西头要降 **59.998u = 6.00 mm** |

⇒ **修法是「把这堵墙绕 (89999.785, 99998.638) 转正 329 角秒」**，一个动作，不是三个。

### ⛔ 而台账今天只有 `translate` 一种动作

`TranslateActionV1`（[`gt_revisions.py:150`](../../../../src/agent/judge/gt_revisions.py)）
只能对**一个面线的一个标量字段**（`const` / `along_min` / `along_max`）加一个整数。
于是同一个缺陷被拆成三条互不相干的记录，而且**每条记的量都不是这个缺陷的真实量**：

| 记录 | 台账写的 | 实际是什么 |
|---|---|---|
| `rev-13ad` | `const` 平移 **−30**（−3.0 mm）| **两种拉直法之差**：机器把歪线拉直到**自己的中点**（100629.596→存 100630），签字图拉到**隔壁墙轴线** y=9.99986 m（存 100600）。⛔ 不是「墙偏了 3 mm」|
| `rev-13ae` | `const` 平移 **−30** | 同上（南面）|
| `rev-13af` | `candidate_action = null` | 西端头帽。⛔ **一次旋转无法表达成任一标量字段的平移** —— 台账自己在 `detail` 里写了「needs an action kind ①'s '遇到再加' has not implemented yet」|

⭐ **自查话术**：`−3.0 mm` 这个数**是真的**（两份图确实差这么多），但它**回答的不是「这堵墙错了多少」**
—— 它是「两种拉直法差多少」。[[proxy-mistaken-for-the-thing]] 的又一例。

## 3. ⛔⛔ 签字那半今天走不通 —— 卡的是代码，不是用户

跑 [`probe_can_a_human_sign_today.py`](probe_can_a_human_sign_today.py) 复现。
三次尝试，每次都是一个**真人真会做的动作**：

| 尝试 | 结果 |
|---|---|
| **A. 只签 13AD**（= 现有 committed 锁覆盖的那一半）| ⛔ `as_signed_wall_face_hi_disagrees_with_its_face_lines: wall w_x_99430_100630_52400_88800 reports face_hi=100630 but face_line_ids_hi=['13AD'] actually sit at const=[100600]` |
| **B. 13AD + 13AE 一起签**（两个面一起动 = 人真正会做的）| ⛔ `as_signed_wall_face_lo_disagrees_with_its_face_lines: … reports face_lo=99430 but … actually sit at const=[99400]` |
| **C. 三条全签** | ⛔ 连 ledger 都构不出：`rev-13af` 没有 `candidate_action` 可提升 |

⭐⭐⭐ **B 这一格是关键，而现有锁没走过它**：`derive_as_signed` 会把面线平移，
**但压根不更新 `walls` 上的 `face_lo` / `face_hi` / `thickness` / `along_*`**，
于是 `_verify_walls_still_match_their_face_lines`（F-137 那道门）必然响亮拒绝。
两个面同向同量一起动**也救不了**——墙的自述数字一个都没跟着动。
⇒ ⭐ 又一次印证「[[rework-review-needs-the-same-shape-input]]：交件自带的证据覆盖了哪一半」——
committed 的锁只签了一条面线，**恰好没碰到「签一堵墙」这个真实动作**。

## 4. 一起量出来的四个洞（全部实测，⛔ 非推断）

| 编号 | 洞 | 证据 |
|---|---|---|
| **G-a-d1** | **`derive_as_signed` 不更新 `walls`** ⇒ 任何真实签字都被 F-137 门拒 | §3 的 A/B 两格 |
| **G-a-d2** | **旋转类修订无法表达** ⇒ `rev-13af` 永远签不了；13AD/13AE 就算能签也签的是错误的量 | §2 |
| **G-a-d3** | **没有任何 CLI 能写 / 签 `revisions.json`** | `revisions.json` 唯一写者 = `gt_facts_staging.py:273`（产**未签**草案）；`scripts/tool_scripts/gt_review_sign.py` 签的是 **review bundle**（`tarch_review_bundle`），不是台账；唯一建库入口在 `logs/experiments/2026-09-01c_f156v3_baseline/rebuild_sm25_facts_staging.py`（实验脚本，且已陈旧）|
| **G-a-d4** | **`CompiledAnswerV1` 在 `answer_compiler.py` 之外零消费者**，`gt.json` 仍走老路径 | `grep -rn CompiledAnswerV1 src/ scripts/` 全部落在 `answer_compiler.py` 内 |

⚠️ **另一条别读错的**：设计稿 §四 那道 **reading 侧容差门不存在** ——
`POS_TOL_M` 只活在判分侧（`as_drawn/reading_grade.py:47` + `flow_wiring.py:177`）。
本例 3.0 mm / 0.19 mm 远小于 80 mm 的带宽，**就算那道门存在也不会响** ⇒
⛔ **别把台账的沉默读成「查过了」**（[[absence-conflates-causes-in-observables]]）。

## 5. ⚠️ 新登记的缺陷：A-11 的 1 mm 入库规整把「非正交」的证据抹掉了（**A-11-d3**）

`as_measured` 存的 13AF：`p0=[52400, 100660]`，`p1=[52400, 99460]` —— **两个端点 x 相同**。
也就是说 `converter_readouts.non_orthogonal_lines` 里这一行
**一边声称「这条线既不水平也不垂直」，一边展示一条完全垂直的线**。

裸 `ezdxf` 量的原值：x **52400.742 → 52398.827**（dx = 1.915u = **0.1915 mm** 的倾斜）。

⭐ **这不是「A-11 没想到」，是【同一个论证做了一半】**：
`as_measured.py:236` 那张 A-11 逐调用点列明的表，**明写** `non_orthogonal_lines[*].p0/.p1` 走量化；
而同文件 `:323` 的豁免表给 `axis_snapped_lines[*].before_p0/.before_p1` 写的理由是
> "RAW pre-snap observation -- evidence, quantising it falsifies it"

**一模一样的理由，一字不差地适用于 `non_orthogonal_lines[*].p0/.p1`，但没被应用。**
⇒ [[enumerate-the-class-not-the-example-found-six-more]] 的同型：按症状只修了一个字段族。

## 6. 结论与去向

- **G-a 机器那半 = ✅ 完成**（A-11 已连带做完，今天在 HEAD 上重新对账过）。
- **G-a 签字那半 = ⛔ 被代码挡住**，⛔ 不是等用户 —— 先修 **G-a-d1 / G-a-d2**，用户才有得签。
- 这四个洞全在 [`src/agent/judge/`](../../../../src/agent/judge/)，按 [CLAUDE.md §0.4#3](../../../../AI_agent/CLAUDE.md)
  **须派工 + 换人审**，⛔ 主控不能自己动。派工表 → 见 [plan.md](../../../plan.md) G-a 行。

## 产物清单

| 文件 | 是什么 |
|---|---|
| [`measure_the_one_wall.py`](measure_the_one_wall.py) | §1/§2/§5 每个数字的复现脚本（只读，不改产物）|
| [`probe_can_a_human_sign_today.py`](probe_can_a_human_sign_today.py) | §3 三次签字尝试的复现脚本 |
| [`worklist_annotated.png`](worklist_annotated.png) | 宿主那一程画的标注图：左 = plan-F1 全部 224 条面线里这堵墙的位置；右 = 西头放大，3.0 mm 与 0.19 mm 只在这一格看得见 |
