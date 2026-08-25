# 跨家族复核请求 · F-95 顶点规范化收窄为「有序简单环」

- **日期**：2026-08-27　**复核席位**：**GLM 家族**（`scripts/glm_code.sh`，`glm-5.3`）
- **施工席位**：**GPT 家族 `gpt-5.6-sol`**（独立 worktree `/tmp/ep_f95`）⇒ ⛔ 谁写谁不批，本单必须由 GLM 出裁决
- **被审 commit**：`5b7a3a8`（`08.26_F95_CanonicalizerNarrowedToOrderedSimpleRings_AdjacencyPreservedInsteadOfResorted`）
- **当前分支 HEAD**：`ed0ba09`（分支 `08.23_AsDrawnReading`）
- **原派工单**：[`2026-08-26_f95_concave_canonicalization_dispatch.md`](2026-08-26_f95_concave_canonicalization_dispatch.md)
- **施工方自述**：`AI_agent/logs/reviews/execution/2026-08-26_f95_concave_canonicalization_construction_report.md`
  （⚠️ **只作线索，不作证据** —— §5#8：施工席自述一律以 `git diff` 为准）

## 〇、你的工作目录（⛔ 写死，不许改）

```
/tmp/ep_f95_review        ← 已由 orchestrator 建好的独立 worktree，detached 在 ed0ba09
```

- ⛔ **不许在 `/workspaces/EnergyPlus-Agent-dev`（主树）改任何文件、不许在主树跑全量。**
  主树上 orchestrator 正在并行派另外两个施工席位，动主树会互相污染。
- 跑全量：在你的 worktree 里 `python -m pytest -q -n auto`（`pyproject` 的 `pythonpath=["."]`
  会让 pytest 取**你这棵树**的 `src`）。
  ⛔ **裸跑脚本**（`python somescript.py`）会因共享 venv 里的 editable `.pth` 硬编码主树
  而**静默串到主树代码**（= 已登记的 F-94 / 债 D-2）⇒ 一律 `python -m <module>` 或 pytest。
- 探针/临时脚本落你 worktree 的 `AI_agent/logs/` 下，⛔ 不落仓库根目录。
- 开工先自检：`git -C /tmp/ep_f95_review log --oneline -1` 应为 `ed0ba09`；
  `grep -c '' AI_agent/CLAUDE.md` 应为 **447**。对不上就停下上报（说明 worktree 建错了）。

## 一、这件事在盘面上的位置

用户 2026-08-26 定的四步：**① 把判分修好 → ② 按新方案改造 reading+correction 的 harness →
③ 产出新产物 → ④ 一步步验证**。当前在 **①**。
① 的两半 = **多层**（F-90，已 APPROVE）+ **C2 非方形**（= 本单）。
⛔ **本单与任何 case 产物无关**：它是纯实现缺陷，有离线夹具矩阵可证。
⛔ 不要去跑 case、不要碰 gt、不要读 `case_tests/test_baseline/gt/`。

## 二、改了什么（据 commit message + diff stat，请你自己看 diff 核）

`canonicalize_ring_vertices`（`src/validator/data_model.py`）原用**绕质心极角排序**重排环 ——
对某些凹多边形还原成**另一个形状**（sm25 走廊 14 顶点：面积 `97.731 → 226.457`，而规范化后的环
仍 `is_valid=True` ⇒ 只有面积对账抓得住）。

改法：**不再排序**，改为「必要时整体**反向** + **旋转起点**」（保序）；
**输入契约收窄为「有序简单环」**，自交/非简单环以 `canonicalize_ring_vertices.non_simple_ring` **响亮拒绝**；
docstring 里那句过度承诺（`any input order, including scrambled / self-intersecting`）一并改掉。
kernel 与 validator **仍共用同一实现**（不拆两套，F-13 不变式保持）。

diff 范围（7 文件 / +531 −66）：

```
src/validator/data_model.py                        | 112 ++++++-----
src/validator/checks/kernel.py                     |   7 +-
src/agent/geometry/build.py                        |   5 +-
tests/test_f95_concave_canonicalization.py         | 137 +++++++++++++   (新增)
tests/test_f13_kernel_canonical_vertex_order.py    |  16 +-
AI_agent/logs/experiments/2026-08-25_kernel_probe_from_gt/tools/concave_canonicalization_matrix.py | 103 ++++--
AI_agent/logs/reviews/execution/2026-08-26_f95_concave_canonicalization_construction_report.md     | 217 +++++ (新增)
```

⭐ **这份范围清单抄自 `git show --stat 5b7a3a8`，⛔ 不是从派工单抄的。**
这是 orchestrator 本轮明知故犯的一处：08-26 GLM 已点名过「把复核单的范围清单照着实际 diff 写
⇒ 有没有超范围永远不可能不通过」。本单的诚实处置是：**范围一致性这条判据本轮作废，别判它**；
你要判的是下面 §三的实质问题。（原派工单在上面给了链接，你若愿意自己对一遍，属于额外收获。）

## 三、⭐ 请你重点打的四处（按我判断的价值排序）

### 3.1 ⭐⭐⭐ 「4 failed / 2 passed」里的那 2 格

施工方自述：「旧实现变异下新锁 **4 failed / 2 passed**，新实现全绿 ⇒ 锁有分辨力」。
⭐ **`2 passed` 的意思是：有两格变异，新锁抓不住。**
请查清那两格分别是什么形状，并回答：
- 它们是**真盲区**（新锁对这两种破坏没有分辨力），还是**这两格本来就不该红**（旧实现在它们上就是对的）？
- 如果是前者，本单是否应当 REWORK。

⚠️ 这条是 orchestrator 读施工自述读出来的，**没有独立核实**。若自述里根本没有这句或数字不同，
以 diff / 你自己跑出来的为准，并把这条记成我方的错。

### 3.2 ⭐⭐⭐ 收窄契约有没有踩到真实调用方

新实现**拒绝**自交/非简单环。旧 docstring 承诺过能吃乱序输入。
- orchestrator 的核查（**只到 grep 级，⛔ 没做行为验证，这是我方最弱的一点**）：
  `canonicalize_ring_vertices` 的全部调用点 = `geometry/build.py:79`（每个面）、
  `build.py:85`（每扇窗）、`validator/data_model.py:1374`、`validator/checks/kernel.py:399`，
  四处的输入都由内核自己按序产出 ⇒ **看起来**没有调用方依赖那句承诺。
- ⭐ **请你把它升级成行为验证**：真的没有任何真实路径会给出非简单环吗？
  特别是**跨层切分产生的碎片**（= 已登记的 F-96「跨层碎片无守卫」）与**退化环**
  （重合点 / 共线三点 / 零面积）会不会现在从「被悄悄修好」变成「响亮拒绝整份产物」。
  ⇒ ⭐ 判据不是「拒绝对不对」，而是「**这次收窄有没有把一条原本能跑通的路变成崩溃**」。

### 3.3 ⭐⭐ 「非简单环」的判定本身会不会误拒

拒绝判定用的是什么？数值容差是多少？
- 一份**合法**的正交环，若两条边在拐角处共线/端点重合到浮点末位，会不会被判成自交？
- 同族教训 [[recompute-gate-must-mirror-producer-definition]]：一个重算式判据把**一份对的产物**
  判红过（诚实 sm24 偏 1.480 px、门是 1.5 px）。⇒ 请给出**误拒余量**的实测数字，不是「看起来没问题」。

### 3.4 ⭐ F-13 那四把锁被动过

`tests/test_f13_kernel_canonical_vertex_order.py` 有 16 行变化。
施工方自述「只把变量名 `scrambled` 改成 `ordered_different_start`，**断言一个没动**」。
⇒ **请以 diff 为准逐行核**。若有任何断言被削弱，那是阻断项
（同族 [[lock-must-exercise-real-entry-point]]：锁改弱了跟没锁一样）。

## 四、验收判据（每条我都自查过「什么情况下它会不通过」）

| # | 判据 | 什么情况下会红 |
|---|---|---|
| A1 | 你独立跑全量：`python -m pytest -q -n auto`，三数报出来 | 有回归 / 有环境红（`test_zone_agent.py` 缺 API 凭据是**已知环境坑**，不算回归）|
| A2 | 摘掉 `data_model.py` 的修复（复原极角排序），`tests/test_f95_*` 必须**红**，且**只红它**（定向变红）| 新锁没分辨力，或连带把无关测试打红 |
| A3 | §3.1 那两格变异查清并给出定性 | 是真盲区且未补锁 |
| A4 | §3.2 行为验证给出结论 | 存在真实路径会被新契约拒掉 |
| A5 | §3.4 F-13 断言逐行核 | 任一断言被削弱 |

⛔ **不要**把「全量绿」单独当通过标志 —— 全量在缺陷存在时也曾全绿（F-95 本身就是：
凹多边形被毁一个月，已有的 L 形锁没有分辨力，因为 L 形恰好是无损的那一半）。

## 五、⛔ 停下上报触发器（任一命中就停，⛔ 不许自行扩路）

1. 你发现 §二 / §三 里 orchestrator 陈述的任何一条事实不成立；
2. 你发现除「收窄契约 + 响亮拒绝」外还有**严格更优**的第三条路
   —— ⭐ **这条明确算触发器**：派工单的选项清单本身就是个没人签字的前提，
   本项目累计已有 **35 次**「停下上报」全部是派工方题错；
3. 要动被审范围以外的文件才能完成本单；
4. 你判断本单应当 REWORK 但把握不足 —— 直接把证据摆出来交 orchestrator，⛔ 不要替我们下结论。

## 六、交件形式

写成一份裁决文件，放你 worktree 的
`AI_agent/logs/reviews/verdict/2026-08-27_f95_concave_canonicalization_glm_verdict.md`，
然后把**全文贴回**给 orchestrator（worktree 会被回收，别只留在盘上）。

必含：**总判**（APPROVE / APPROVE-WITH-FINDINGS / REWORK / REJECT）· §四五条判据逐条读数 ·
§三四处的实测结论 · findings 分「阻断 / 不阻断」两栏 · 你自己跑的全量三数 ·
⭐ **以及「你认为本单里 orchestrator 题面写错的地方」**（有就写，没有就写「无」）。
