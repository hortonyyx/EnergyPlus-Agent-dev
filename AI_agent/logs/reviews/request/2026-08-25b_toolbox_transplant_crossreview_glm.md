# 跨家族审阅请求：as-drawn reading 工具箱转正进 `src/`

> **日期** 2026-08-25 · **请求方** orchestrator（Claude Opus 5）· **审阅方** GLM（跨家族，⛔ 施工方是 Claude 家族）
> **被审对象 = 一个 git worktree 里的一次提交，⛔ 不是主树**：
>
> ```
> 工作树   /workspaces/ep_toolbox_transplant
> 分支     toolbox_into_src_08.25
> 提交     283e868   （父提交 2b01ca6 = 主树当时的 HEAD）
> 看 diff  git -C /workspaces/ep_toolbox_transplant diff 2b01ca6 283e868
> ```
>
> ⛔ **裁决出来之前我不动这棵树。** （上一轮的教训：送审期间我还在改树，审阅方只好自己钉冻结副本。）

---

## 一、这次要审的是什么

一次**纯搬运**：把探索档 `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/`
里的 as-drawn reading 工具箱，转正进 `src/` 与 `scripts/`。

**派工单原文** → [`2026-08-25_reading_toolbox_into_src_dispatch.md`](2026-08-25_reading_toolbox_into_src_dispatch.md)
（请以它为准，本文只补充审阅要点）。

**背景架构**（判断"这么放对不对"需要）→
[`../../architecture/reading_pipeline_architecture.md`](../../architecture/reading_pipeline_architecture.md)。

⛔ **本单明令不含任何新能力**：不调阈值、不加分支、不重构、不接线进 `run_pipeline`/gate①。

### diff 规模

```
 .../tools/run_all.py                            |  28 +-   (改指向新址)
 scripts/tool_scripts/affected_tests_rules.yaml  |  52 +     (10 条覆盖率豁免登记)
 scripts/tool_scripts/reading_toolbox.py         | 156 +     (CLI)
 scripts/tool_scripts/render_reading_grade.py    | 226 +
 src/agent/judge/as_drawn/{__init__,denominator,reading_grade}.py | 669 +
 src/agent/reading/as_drawn/{__init__,_plan_ink,as_drawn_v2,pens}.py | 1733 +
 src/validator/checks/as_drawn.py                | 848 +     (11 道门)
 tests/test_gt_discipline.py                     |  40 +     (新增 1 把 gt 隔离锁)
 13 files changed, 3741 insertions(+), 11 deletions(-)
```

---

## 二、我（请求方）已经亲手复跑过的三条

⭐ **⛔ 这三条我没有采信施工方的自述，是我自己在那棵 worktree 里跑的**，请你独立复验，
**⛔ 不要因为我说过就跳过**：

| # | 我跑的 | 我得到的 |
|---|---|---|
| 1 | 用新路径 `python3 -m src.agent.reading.as_drawn.as_drawn_v2` 重跑三个 view，与 `…/out/{sm25_1f,sm25_2f,sm24_1f}_v2.json` 做 `cmp -s` | **三个全部逐字节相同** |
| 2 | `import src.agent.pipeline` 后扫 `sys.modules` | `judge.gt` 与 `judge.as_drawn` **均不在闭包内**；闭包里只有 `judge / executor / retry / verdict` |
| 3 | `pytest tests/test_gt_discipline.py` | 12 passed |

**施工方另称**：全量 3008 通过 / 4 败 / 3 错 / 13 xfail，且那 7 个红"在父提交 `2b01ca6` 上同样失败、与本次搬运无关"。
⚠️ **这一条我尚未独立核实**（主树全量正在跑取基线）。**请你把它当作未经验证的主张对待。**

---

## 三、⭐ 请重点攻的六个面

1. ⭐⭐ **「逐字节相同」是不是自己跟自己比。**
   请确认比对的基线文件 `…/out/*_v2.json` **不是本次运行重新写出来的**
   （即：它来自 `2b01ca6`，未被本提交改动）。若基线被同一次运行覆盖过，这条验收就是空的。
2. ⭐⭐ **gt 隔离是真的还是词法的。** 新加的那把锁是否走**真实入口**（fresh subprocess 真 import），
   摘掉被测对象是否**真的会红**。⛔ 只做词法 grep 的锁不算数（本项目栽过：
   `check_view_manifest_merge` 那次，请求方把 docstring 里的描述当成函数名当实测事实发了三份文档）。
3. ⭐⭐ **有没有夹带「改进」。** 请逐文件 diff 原件与新件，确认除 import/路径深度外**零语义改动**，
   特别是：**注释有没有被删**（那些注释记着每个判据的实测来源）· 阈值 · 分支 · 默认值。
   施工方自称只改了：`as_drawn_v2` 2 行 import · `pens` 2 行 · `_plan_ink` 0 行 ·
   `checks/as_drawn` 4 行 · `denominator` 2 处 `parents[5]→[4]` · `reading_grade` 0 行 ·
   `render_reading_grade` 0 行 · `reading_toolbox` 1 行。**请逐条核。**
4. ⭐ **sm24 那三道非绿有没有被「顺手修绿」。** 基线是
   `pair_hypothesis_reconciles_with_observations`=degraded · `pair_spacing_explicable_by_callouts`=red ·
   `forward_ledger_structural_ink_claimed`=degraded。**这三道是对的**，修绿即违规。
5. ⭐ **回归夹具矩阵还活着吗。** `tools/run_all.py` 应仍跑得通，
   且五轮跨家族审累积的作弊夹具（`glm_cheats.py` / `crossreview_mutate_v2.py` 等）红绿模式不变。
6. ⭐ **那 7 个全量红到底是不是本来就有的**（见 §二末）。

---

## 四、⛔ 三个我拿不准、请你一并裁的决定

施工方主动列出了这三处「任务书没说清、我自己做了决定」。**我认为它的推理都成立，但后果需要第二个人看**：

### ① 「搬」被做成了「复制」而不是「移动」——`tools/` 原件全部还在

**它的理由**：`glm_rework.py` / `glm_cheats.py` / `glm_probes.py` / `glm_sweeps.py` 用
`spec_from_file_location(name, T / "xxx.py")` **按文件路径**加载
`checks_as_drawn_v2.py` / `denominator.py` / `reading_grade.py` / `as_drawn_v2.py`。
删掉原件，这批**任务书明确要求「必须继续能跑」**的回归夹具会全炸。
故只让 `run_all.py`（任务书点名的那个）改指向新址，其余原样保留。

**⛔ 后果**：现在同一套代码有**两份**，与「不两处并存」冲突，且**日后改一份忘另一份**是必然的。
**请裁**：(a) 接受双份并登记为已知债 · (b) 把夹具改成按模块加载再清原件（那是新工作，须另开单）·
(c) 别的做法。

### ② 它改了第 8 个文件之外的一个项目文件

`scripts/tool_scripts/affected_tests_rules.yaml` 加了 **10 条 `uncovered_allowlist`**
（新文件无测试覆盖会让 `test_affected_tests_map.py` 报红）。它主动申报了。
**请裁**：这属于「如实向覆盖率台账登记一个真实缺口」，还是属于**夹带**？

### ③ 一个环境级隐患（它发现的，不是它引入的）

venv 里有个 stale 的 editable-install `.pth` **硬编码指向主树** `/workspaces/EnergyPlus-Agent-dev`。
后果：在 worktree 里**裸跑**任何 `from src.xxx import …` 的脚本（非 `-m`、非 pytest），
若脚本自身目录下无 `src/` 包，会**静默**从**主树**解析 `src` 而不是本 worktree。
它用探针实测复现，并统一改用 `python3 -m` + 显式 `cwd=` 绕开。
**⛔ 它没有给另外 3 个脚本加同款防御**，理由是「那是改进不是搬运」。
**请裁**：这个处置对不对；以及这条是否该单独登记为缺陷（我倾向该登记）。

---

## 五、⛔ 请求方自己的两处已知污点（先声明，免得你当新发现）

1. **`RESULTS_v2.json` 是陈旧的，而且是我造成的**：我 2026-08-25 改过 `denominator.py`
   （T 形接头改成目标带「洞」）与 `reading_grade.py`（覆盖率按 required 长度算），之后**没有重跑** `run_all.py`。
   施工方发现了并**选择不夹带修复**（`git checkout --` 撤回再生文件），我认为处置正确。
   ⇒ **该文件当前不可作为任何数字的依据**，由我在本单裁决后重跑。
2. **本单验收里的那些数字**（画对 99.2 / 97.8 / 97.9 等）来自 orchestrator **手工产出的 perception**，
   且产出前已看过 gt 侧结果 ⇒ **探索档，⛔ 任何分数不得记成绩**。本单只审「搬运有没有改变行为」，
   ⛔ 不审那些数字本身好不好。

---

## 六、裁决请给到这三样

1. **APPROVE / REWORK / REJECT**，以及理由。
2. §三 六个攻击面**逐条**的复验结论（含你自己跑的命令与输出）。
3. §四 三个决定**逐条**的裁定。

⚠️ 请**只看**：派工单 + 本文 + `git diff 2b41cda..283e868`（实际为 `2b01ca6..283e868`）+ 你自己跑出来的输出。
⛔ **不要看施工方的长篇自述**（本项目纪律：复核简报只看原始需求 + diff + 测试输出）。
