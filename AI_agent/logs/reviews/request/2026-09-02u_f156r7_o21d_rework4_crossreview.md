# 跨家族复核请求 · **F-156 第七轮 / ②-1d 第五轮**（返工第四轮）

- **日期**：2026-09-02 · **请审方**：orchestrator
- **复核方**：⛔ **原派 GPT，2026-09-03 改派【GLM 家族】**（协议 §1.1 的默认值）——
  ⭐ 改派理由**不是**质量问题：GPT 席位那一轮**零交付**，因为 codex 的沙箱在本容器里起不来
  （`bwrap: No permissions to create a new namespace`，它的每条 shell 命令都失败）。
  ⭐ 该席位**拒绝拿施工方自述代替实测、也没有据此擅下裁决** —— 行为正确，⛔ 别记成失职。
  ⇒ 本单改由 GLM 审（GLM **不是**本单施工方，`谁写谁不批` 成立）。
- **被审 commit**：`e065aeb`（分支 `08.23_AsDrawnReading` 顶；施工方原件 `f735461`，`cherry-pick -x` 落地）
- **上一轮裁决**：[REWORK / 阻断 3 / 不阻断 1](../verdict/2026-09-02g_f156r6_o21d_crossreview_gpt.md)
- **本轮任务书**：[2026-09-02i](2026-09-02i_f156r7_o21d_rework4.md)
- **施工方交件**：[执行档](../execution/2026-09-02i_f156r7_o21d_rework4_claude.md)

## 一、diff 范围（`git diff --numstat abec1cd..e065aeb`，⛔ 只列代码）

```
39	5	src/agent/judge/answer_compiler.py
227	37	tests/test_o21d_exclusion_gap.py
```
（其余为管理文档、两份主控探针档、两个席位启动器，与本单无关。）

## 二、施工方的主张（⚠️ 请你自己验，⛔ 别照抄）

| | 主张 |
|---|---|
| **T1（阻断 2）** | 加了**出口侧穷举 sweep**：遍历起点从 converter zone 换成**台账本身**，新码 `producer_ring_loss_unrepresented_by_any_converter_zone` |
| **T2（阻断 1）** | 两条来源锁拆成**规则半（自造夹具供货）+ 读数半（只读不断言非空）**；清空全台账后两锁**绿**，牙口仍在 |
| **T3（阻断 3）** | 恒绿锁改用**未校验载荷**造「同 cavity 既有 edge 又有 loss」，断言 `AsSignedV1.model_validate` 抛精确错误；摘 validator ⇒ `DID NOT RAISE` 红 |
| **T4** | 修了把 producer ledger 说成 licence 的注释 |
| **§三 必答** | **不改真实 sm25 读数** —— 改前改后都是 `reds=4`（2 条 F-153 形态 B + 2 条 F-157）**逐字相同** ⇒ 三个引用文件无一期望值需改，**未动任何已签字哈希/基线** |
| **全量** | `3666 passed / 13 xfailed / 0 failed`（`-n 6`，`__file__` 落在其 worktree）|

## 三、⭐ 主控已自查、**⛔ 不必重做**的三条（我逐条查过，全部**不成立**）

1. ~~「台账里同一 cavity 有两条 loss 时，按 `cavity_id` 记的 skip set 会把第二条一起跳掉」~~
   ⇒ ⛔ 不成立：[`as_measured.py:715`](../../../src/agent/judge/as_measured.py#L715) 已强制
   `as_measured_boundary_ring_loss_cavity_not_unique`。
2. ~~「footprint 解析失败会跳过整个 view，sweep 跑不到」~~
   ⇒ ⛔ 不成立：该分支**不 `continue`**，只把 `raw_cavities` 置空后继续
   （[`answer_compiler.py:1176`](../../../src/agent/judge/answer_compiler.py#L1176)）⇒ 此时反向 sweep 会把**全部**台账条目判红，正是想要的行为。
3. ~~「view 体里有 early exit 绕过 sweep」~~
   ⇒ ⛔ 不成立：`1204/1217/1224` 三处 `continue` **全在 zone 循环内**，view 体必达 sweep。

## 四、⭐⭐ 主控点名的**一条活疑点**（⛔ 写成假说，未代判，请实测）

> **H-a：这次「换了遍历起点」，但换成的是【哪一份台账】？**
>
> 新 sweep 读的是 `view.boundary_ring_losses`，而 `view` 来自 **`as_signed`**。
> **如果一条 loss 在 `as_measured` 里存在、却被 `revisions` 改掉或删掉，sweep 就看不见它。**
> ⇒ 请实测：**能不能构造一条 revision，让一条真实的 producer loss 在 as_signed 里消失，
> 从而既不被正向 zone 命中、也不被反向 sweep 抓到？**
> 若能 ⇒ 载体又被换掉了一次（[[gate-measures-right-but-carrier-gets-swapped]]，本项目该病族第八轮），
> 只是这回换的是**台账的版本**而不是遍历起点。

## 五、⛔ 本轮**必须**包含的第三条判据（返工审硬规矩）

⛔ 只验「①旧 commit 复现得出 + ②新 commit 复现不出」**不够**——那只证明「这个例子修好了」。
**必须加第三条：⭐ 换一个【同形但不同】的输入，缺陷仍然走不通。**
（立此条的事实依据：2026-08-27 实测，①② 两条全绿而第三条**一次抓出全部 3 条阻断**。）

⇒ 具体到本单，至少要各造一个**与施工方夹具不同形**的：
- T1 方向：**另一种**「没有 zone 踩到的 producer loss」形状
- T2 方向：**另一种**让台账归零的路径
- T3 方向：**另一种**同 cavity 既 ring 又 loss 的构造

## 六、验收对照（施工方须逐条已答，请你逐条验）

见任务书 §四 八条。⭐ 特别注意 **#5**：上一轮已成立的定向绿集 / fail-loud neuter 红集 / 奇数 NA
**不许因为换了遍历起点就变成恒真**。

## 七、环境

本 worktree 无 `.env`。跑全量前同一 shell 先
`set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a`，否则 `test_zone_agent.py` 必红一条
（**F-158，与本单无关**）。环境自证与 pytest 必须同一条命令：
`python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest ...`
跑测用 **`-n 6`**（同机有别的席位）。

## 八、交件

`AI_agent/logs/reviews/verdict/2026-09-02u_f156r7_o21d_rework4_crossreview_glm.md`：
裁决 + 阻断数/不阻断数，逐条对 §二 / §四 / §五 报；凡下结论处贴命令原文 + 输出原文。
⛔ 不许 `pip install -e .`；⛔ 不许 `git add -A`。
