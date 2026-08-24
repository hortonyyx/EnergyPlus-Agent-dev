# 跨家族裁决：as-drawn reading 工具箱转正进 `src/`（GLM，2026-08-25b）

> **审阅方** GLM · **日期** 2026-08-25 · **施工方** Claude 家族
> **被审对象** `/workspaces/ep_toolbox_transplant` 上 `2b01ca6..283e868`
> **送审书** [`../request/2026-08-25b_toolbox_transplant_crossreview_glm.md`](../request/2026-08-25b_toolbox_transplant_crossreview_glm.md)
>
> ⚠️ 本文件随查随写（第一次审阅被 timeout 掐断零产出的教训）。
> 每条结论附我自己跑的命令与真实输出；未完成的条目标 ⏳。

---

## 〇、总裁决

# ✅ **APPROVE**

**被审对象**：`/workspaces/ep_toolbox_transplant` 上 `2b01ca6..283e868`（纯搬运，13 文件 +3741/−11）。

**理由**（全部有我自己的命令与输出，见下文各节）：

| 验收面 | 结果 |
|---|---|
| 三 view 产物逐字节（唯一硬验收） | ✅ 我独立重跑三份 `cmp -s` 全过；基线证来自 `2b01ca6`、未被本提交或任何运行碰过（mtime 08-24）⇒ 非自比 |
| 零夹带 | ✅ 8 文件逐 diff，全部差异=import 路径/目录深度；`_plan_ink`/`reading_grade`/`render_reading_grade` 逐字节相同；注释零删除 |
| 11 门状态不变 | ✅ 33 项逐项一致；sm24 三道非绿原样保留 |
| 判分数字不变 | ✅ 原路径（2b01ca6 代码）对照组与新路径深度逐字段 0 差异；数字=派工单验收值（99.2/97.8/97.9…门窗 31:31·30:30·20:21） |
| 夹具矩阵活着 | ✅ `run_all.py` 两版 rc=0，全 neuter 矩阵红绿模式一致，drift guard 过 |
| gt 隔离（唯一获准的新锁） | ✅ 行为锁（fresh subprocess 真 import + 扫 sys.modules）；变异红/撤销绿对称验证有分辨力 |
| 不加新锁 | ✅ 仅 gt 隔离锁（派工单 §五#7 明文允许）；`affected_tests_rules.yaml` 10 条是台账登记非锁，且反向验证（删登记→门红）证明必要 |

**随裁决登记的五笔债/更正**（不阻塞，各有归属）：
1. **过计更正**（施工方→请求方记账）：「7 项皆前置」→「4 前置 + 2 worktree 环境产物 + 1 未复现」。
2. **双份债**：`tools/` 原件与 `src/` 新件并存（§四① 裁定 (a)），合并后限期退役（夹具改模块加载，另开单）。
3. **环境缺陷**：stale editable `.pth` 硬编码主树——**合并回主线前必须处理**（届时踩坑从响亮失败
   变静默串台）；受影响面已实测三项（探针/inspect_dxf 两测试/reading_toolbox 裸跑）。
4. **自述更正**（施工方）：`checks/as_drawn` 改动「4 行」→实为 5 处 import。
5. **待请求方执行**：裁决后重跑 `run_all.py` 刷新陈旧的 `RESULTS_v2.json`（送审书 §五#1 已认领）。

**范围确认**：本裁决只审「搬运是否改变行为」，不判 §五#2 声明的那些探索档数字可否记成绩
（不可——按 §0.2 反向铁律，探索档产物永远不得记成绩，与数字好坏无关）。

---

## 一、§三 六个攻击面逐条复验

### #1 ⭐⭐ 「逐字节相同」是不是自己跟自己比 —— ✅ **不是自己跟自己比，验收成立**

**基线未被本提交改动**（worktree 干净 + diff 只碰 `tools/run_all.py`）：

```
$ git -C /workspaces/ep_toolbox_transplant status --porcelain        → (空)
$ git diff --stat 2b01ca6 283e868 -- AI_agent/logs/experiments/
  .../tools/run_all.py | 28 +++++++++++++---------
  1 file changed, 17 insertions(+), 11 deletions(-)        # experiments/ 下只有这一个文件被碰
```

**基线三版本（git `2b01ca6` / worktree 工作区 / git `283e868`）sha256 完全一致**：

```
sm25_1f_v2.json: 2b01ca6 == worktree == 283e868  (2a563149…93c57)
sm25_2f_v2.json: 2b01ca6 == worktree == 283e868  (bdf9a6fb…774d9e2)
sm24_1f_v2.json: 2b01ca6 == worktree == 283e868  (dd611578…e0718c8)
```

mtime 全部停在 **2026-08-24 12:07–12:08**（早于本次提交 `283e868`，无被近期运行重写的痕迹）。

**防串台检查**（§四③ 的 stale `.pth` 隐患——确认我跑的是 worktree 的代码）：

```
$ cd /workspaces/ep_toolbox_transplant && python3 -c "import src.agent.reading.as_drawn.as_drawn_v2 as m, ..."
as_drawn_v2 -> /workspaces/ep_toolbox_transplant/src/agent/reading/as_drawn/as_drawn_v2.py
checks      -> /workspaces/ep_toolbox_transplant/src/validator/checks/as_drawn.py
denominator -> /workspaces/ep_toolbox_transplant/src/agent/judge/as_drawn/denominator.py
```

**我的独立重跑**（输出到 `/tmp/glm_toolbox_review/`，⛔ 不落 `out/`）：

```
$ for nv in sm25_1f:cfg_1f_full sm25_2f:cfg_2f_full sm24_1f:cfg_sm24; do
    python3 -m src.agent.reading.as_drawn.as_drawn_v2 "$T/$cfg.json" "/tmp/glm_toolbox_review/${name}_v2.json"; done
cfg_1f_full  face_lines= 49 runs= 134 gaps=  85 cand= 374 faces_with_cand= 49 pairs=22 families=4/4
cfg_2f_full  face_lines= 46 runs= 133 gaps=  87 cand= 303 faces_with_cand= 46 pairs=21 families=4/4
cfg_sm24     face_lines= 98 runs= 185 gaps=  87 cand=1185 faces_with_cand= 98 pairs=8  families=3/3
（三个 rc=0）

$ cmp -s 基线 /tmp/glm_toolbox_review/*  →
sm25_1f_v2.json: BYTE-IDENTICAL ✔
sm25_2f_v2.json: BYTE-IDENTICAL ✔
sm24_1f_v2.json: BYTE-IDENTICAL ✔
```

**结论**：基线是 `2b01ca6` 提交在案的历史产物（08-24 生成后未被任何运行覆盖），
我用新路径独立重跑的输出与之逐字节相同。请求方 §二#1 的验收**真实成立**，非自比。

### #2 ⭐⭐ gt 隔离是真锁还是词法锁 —— ✅ **行为锁，有分辨力（红绿对称实测）**

**锁的构造**（`tests/test_gt_discipline.py` 新增的
`test_pipeline_import_closure_excludes_gt_and_as_drawn_judge`，+40 行；旧词法扫描未动）：
fresh `subprocess` 真 `import src.agent.pipeline`，然后扫 `sys.modules` 里有没有
`src.agent.judge.gt` 或 `src.agent.judge.as_drawn*`。**不是词法 grep**——间接 import /
别名 / re-export 只要真加载进 `sys.modules` 都会现形。

**独立复跑**：

```
$ cd /workspaces/ep_toolbox_transplant && python3 -m pytest tests/test_gt_discipline.py -q
12 passed in 6.75s                        # 请求方 §二#3 ✓
```

**闭包内容独立复验**（请求方 §二#2）：

```
$ python3 -c "import sys; import src.agent.pipeline; print([m for m in sys.modules if '.judge' in m])"
['src.agent.judge', 'src.agent.judge.executor', 'src.agent.judge.retry', 'src.agent.judge.verdict']
→ 无 gt、无 as_drawn ✓（与请求方所报一致）
```

**分辨力验证**（⛔ 在 /tmp 副本做，未碰被审树；`cp -a src tests pyproject.toml` 到 `/tmp/glm_mut`，
清 `__pycache__` 防陈旧 pyc 干扰）：

```
基线（未变异）探针                        → []
变异：pipeline.py 末尾加
  `import src.agent.judge.as_drawn.denominator`
  探针                                    → ["src.agent.judge.as_drawn","src.agent.judge.as_drawn.denominator"]
  pytest 该锁                             → 1 failed（assert hits == [] 抓到 2 项）
撤销变异 → pytest 该锁                    → 1 passed
```

红绿对称成立 ⇒ 这把锁**摘掉被测对象真的会红**，非恒绿锁、非词法锁。

（过程备注：首次变异跑的 traceback 显示了 worktree 路径——是 `cp -a` 带来的陈旧
`__pycache__` 里 `co_filename` 的显示问题；清 pyc 重跑后路径与行为均正确，结论不受影响。）

### #3 ⭐⭐ 有没有夹带「改进」 —— ✅ **零夹带；施工方自述有一处轻微少报（非夹带）**

方法：`git show 2b01ca6:<tools 原件>` 导出到 `/tmp/glm_orig/`，对 `283e868` 的新件逐文件 `diff -u`。

| # | 原件 @2b01ca6 | 新件 @283e868 | diff 结果 | 自述 |
|---|---|---|---|---|
| 1 | `tools/as_drawn_v2.py` | `src/agent/reading/as_drawn/as_drawn_v2.py` | 仅 import 区：删 `sys.path.insert` + 两条 `plan_ink`/`ink_palette` 导入改为包路径（-3/+2） | 「2 行 import」✓ |
| 2 | `tools/ink_palette.py` | `…/as_drawn/pens.py` | 仅 import 区 2 行（-2/+1） | 「2 行」✓ |
| 3 | `tools/plan_ink.py` | `…/as_drawn/_plan_ink.py` | **逐字节相同**（diff rc=0） | 「0 行」✓ |
| 4 | `tools/checks_as_drawn_v2.py` | `src/validator/checks/as_drawn.py` | import 区 4 行（-4/+3）**加函数体内 1 处局部导入**（`from as_drawn_v2 import _ink_groups` → `from src.agent.reading.as_drawn.as_drawn_v2 import _ink_groups`，-1/+1） | 「4 行」→ **实际 5 处，漏报了函数体内那处** |
| 5 | `tools/denominator.py` | `src/agent/judge/as_drawn/denominator.py` | 仅 2 处 `parents[5]→[4]`（目录深度变化的等价换算） | 「2 处」✓ |
| 6 | `tools/reading_grade.py` | `src/agent/judge/as_drawn/reading_grade.py` | **逐字节相同** | 「0 行」✓ |
| 7 | `tools/render_reading_grade.py` | `scripts/tool_scripts/render_reading_grade.py` | **逐字节相同** | 「0 行」✓ |
| 8 | `tools/reading_toolbox.py` | `scripts/tool_scripts/reading_toolbox.py` | 仅 1 处 import（-2/+1） | 「1 行」✓ |

所有差异**全部是 import 路径/目录深度**，无一涉及阈值、分支、默认值、逻辑。
**注释零删除**——diff 中无任何注释行变动；三个逐字节相同的大件（`_plan_ink` 808 行 /
`checks` 除 import 外 / `reading_grade` / `render_reading_grade`）里的实测记录注释原样保留
（如 `MIN_RUN_COVERAGE = 0.80  # a stroke must sit on real ink; swept in the README` 在 diff 上下文中可见、未动）。

两个新 `__init__.py`（8+7 行）是纯 docstring（含 gt 隔离声明与来源指针），无代码。

**CLI 契约**（派工单 §七#2「六个子命令名与输出格式一个字不许变」）：

```
$ python3 tools/reading_toolbox.py --help        （原件）
$ PYTHONPATH=<worktree> python3 scripts/tool_scripts/reading_toolbox.py --help （新件）
→ cmp -s 两份 help：BYTE-IDENTICAL ✔（pens/ruler/faces/pairs/gaps/build 六命令+尾注全同）
```

（注：新件裸跑会踩 §四③ 的 `.pth` 坑而 `ModuleNotFoundError`——这正 §四③ 已登记的
环境缺陷的受影响面之一，非本节问题。）

**唯一出入**：`checks/as_drawn.py` 的自述「4 行」漏了函数体内第 5 处 import 改动
（上面表中 #4）。性质相同（纯路径）、非夹带，但自述不精确，如实记录。

### #4 ⭐ sm24 三道非绿有没有被顺手修绿 —— ✅ **没有修绿，33 项门状态逐项一致**

**基线（2b01ca6 提交在案的 `out/*_checks_v2.json`）门状态**：

```
sm25_1f / sm25_2f：11 道门全 green
sm24_1f：pair_hypothesis_reconciles_with_observations: degraded
         pair_spacing_explicable_by_callouts:        red
         forward_ledger_structural_ink_claimed:      degraded   ← 与派工单 §三#2 记载一致
```

**我的独立重跑**（新路径 `python3 -m src.validator.checks.as_drawn`，对 §三#1 里我自己
生成的三个 `*_v2.json` 跑，checks 落 `/tmp`）：

```
$ python3 -m src.validator.checks.as_drawn <product> <cfg> <out_checks>   ×3 → rc=0
--- sm25_1f: 11/11 一致
--- sm25_2f: 11/11 一致
--- sm24_1f: 11/11 一致
    非绿项: {'pair_hypothesis_reconciles_with_observations': 'degraded',
             'pair_spacing_explicable_by_callouts': 'red',
             'forward_ledger_structural_ink_claimed': 'degraded'}
ALL MATCH
```

三道非绿**原样保留**（基线与新路径逐项一致），没有被顺手修绿。

### #5 ⭐ 回归夹具矩阵还活着吗 —— ✅ **活着：`run_all.py` 跑通，全矩阵红绿模式与原路径逐字段一致**

**方法**：⛔ 不能在 worktree 里跑（会重写 `out/` 基线）。我在 `/tmp/glm_exp_run` 搭了等价环境
（`src`/`case_tests`/`tests` symlink 指向 worktree 真身 + 实验档拷贝，`REPO` 逐级推回
`/tmp/glm_exp_run`），跑了**两遍全套**：
- 新路径版：worktree 的 `run_all.py`（`-m src.…` 调用新址）→ `RESULTS_newpath`；
- 对照组：`git show 2b01ca6:…/run_all.py`（原路径调用 `tools/` 原件）→ `RESULTS_origpath`。

```
两遍 rc=0；elevation honest 24/24、11 门 discriminating_power 全 ok
两份 RESULTS 深度逐字段对比 → 实质差异条数: 0
drift guard（陈旧产物拒绝）：两份 glm_rework 均为本轮新鲜产出，无 error
```

**关键段落抽查（新路径 RESULTS，与原路径逐字段相同）**：
- 判分数字（= 派工单 §三#3 验收值逐项吻合）：
  `sm25_1f 画对99.2/错切0/多画0.722/门窗31:31 · sm25_2f 97.8/1/0.524/30:30 · sm24_1f 97.9/1/5.786/20:21`
- 第三轮作弊 5 项**每项都有非绿门**（`missing_wall_middle`→spanacct+runs 红；
  `one_pixel_actual_schema`→recompute+gaps+spanacct 红 …）
- 感知夹具 5 个错误认知**每个都被拦**（配对错→reconcile 红；窗叫家具→openrole+opennaming 红 …）
- `gate_discriminating_power`：11 门全部 seen green+red（或含 degraded），verdict=ok

**一个必须写清的事实**：基线 `out/RESULTS_v2.json`（08.24n 提交）里的旧数字
（C2=98.6/97.0/97.5）与新跑数字（99.2/97.8/97.9）**不同**——这不是搬运造成的：
那是请求方 08-25c（`81ec264`，**在 2b01ca6 里、搬运之前**）改 `denominator.py`/`reading_grade.py`
后未重跑所致（送审书 §五#1 已自我披露）。我用**同代码原路径对照组**证明：
同一份代码从 `tools/` 原路径跑出的数字与新路径**完全相同**（深度对比 0 差异）
⇒ 数字差异全部来自请求方的（搬运前）改动，搬运本身零行为改变。

### #6 ⭐ 那 7 个全量红是不是本来就有的 —— ⚠️ **部分不是：4 项前置成立，2 项确证为 worktree 环境产物（非前置、非搬运引入），1 项无法复现**

我在 worktree 独立复现与对照主树的结果：

| 项 | worktree | 主树 | 定性 |
|---|---|---|---|
| `test_elevation_score_bindings…fingerprint` | FAILED（`assert 0 != 0`） | FAILED（同） | **前置**（锁陈旧，见 §七②；diff 13 文件不含 builder/gt/该测试） |
| `test_reading_typed_score_f67` × 3 | ERROR（同三 项） | ERROR（**逐项完全相同**） | **前置** |
| `test_inspect_dxf…cli_exit_and_json_contract` | FAILED | **passed** | **worktree 环境产物**（见下） |
| `test_gt_from_dxf…build_only_cli_round_trips…` | FAILED | **passed** | **worktree 环境产物**（同根因） |
| `test_zone_agent`（openai 依赖） | **passed**（单独 `-n0`、`-n auto` 均过） | passed | **无法复现**——两树多模式全过，施工方报告的此项我拿不到证据 |

**DXF 两项的根因实测**（这就是 §四③ 那个 stale `.pth`，与搬运无关、与「前置」也无关）：

```
$ pytest tests/test_inspect_dxf.py::test_manifest_inspector_cli_exit_and_json_contract  (worktree)
E   AssertionError: assert (3 == 2)
    stderr='inspection error: gt_vg_config_path_forbidden'
```

守卫在 `src/agent/judge/gt_manifest.py:277`：`vg_path.resolve() != (REPO_ROOT / "src/configs/correction.yaml").resolve() → raise`。
`inspect_dxf.py` 以**脚本**方式裸跑时 `sys.path[0]`=脚本目录（非 cwd），worktree 根不在 path 上 ⇒
`import src…` 沿 venv 的 `_editable_impl_energyplus_agent.pth`（内容硬编码 `/workspaces/EnergyPlus-Agent-dev`）
**从主树**解析 `gt_manifest` ⇒ 其 `REPO_ROOT`=主树 ≠ 传入的 worktree 路径 ⇒ raise。复刻验证：

```
$ cat /tmp/glm_probe_script.py   (import gt_manifest 并打印来源；脚本放 /tmp、cwd=worktree)
sys.path[0]: /tmp
gt_manifest loaded from: /workspaces/EnergyPlus-Agent-dev/src/agent/judge/gt_manifest.py   ← 主树！
REPO_ROOT: /workspaces/EnergyPlus-Agent-dev

$ cat /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
/workspaces/EnergyPlus-Agent-dev                                                               ← 硬编码主树
```

（对照：`-c`/`-m` 模式 sys.path[0]=''/cwd ⇒ worktree 根优先 ⇒ 正常解析 worktree；主树上脚本目录与 .pth 同树 ⇒ 绿。）

**⇒ 施工方「7 项皆在父提交上同样失败」是过计**：那 2 项 DXF 在父提交（主树）上是绿的，
不是「前置失败」，是 worktree 环境产物。请求方的解读方向正确，且我给出了精确机制。
第 7 项（zone_agent）我复现不出，不下结论（不影响过计判定——只要有一项不是前置，「皆前置」就不成立）。

---

## 二、§四 三个决定的裁定

### ① 「复制」而非「移动」（tools/ 原件全部还在）—— 裁定：**(a) 接受双份 + 登记为已知债，限期退役；理由如下**

**施工方理由属实**（我逐个查了加载方式）：
```
glm_cheats.py:38 / glm_probes.py:31 / glm_sweeps.py:38:
    spec_from_file_location(name, T / f"{name}.py")          ← 按文件路径加载 tools/ 原件
glm_rework.py:47/98/365:
    from glm_cheats import RG…  /  from as_drawn_v2 import _profile
    from plan_ink import load_rgb                              ← 同目录 import，同样钉死 tools/
```
⇒ 删原件 ⇒ 派工单 §二「⛔ 必须继续能跑」的回归矩阵**全炸**。在「不许改夹具（改夹具=改回归矩阵=超范围）」
的前提下，**复制是唯一同时满足两项要求的做法**。

**裁定**：(a)，但附两个条件——
1. **登记为已知债**（双份并存 =「日后改一份忘另一份」的定时隐患；派工单与本单裁决即登记处）；
2. **限期退役**：主树合并后应尽快把夹具改为按模块加载并清掉 tools/ 原件（那正是选项 (b)，
   是新工作、须另开单——本单明令不含）。退役前若两份漂移，`run_all.py` 的矩阵用的是
   `tools/` 原件（按路径）+ `src/` 新件（-m）**混跑**，这一点要在债的描述里写明。

（不推荐 shim 转发方案：夹具用 `spec_from_file_location` 时 shim 内 `import src` 需要
REPO 在 `sys.path`，而夹具只 insert 了 tools 目录——引入新的隐性失败模式，比双份更糟。）

### ② `affected_tests_rules.yaml` 加 10 条豁免 —— 裁定：**如实登记真实缺口，不是夹带**

**事实**：
- 10 条 `uncovered_allowlist` 与 10 个新 py 文件（src 8 + scripts 2）**一一对应**，无多余条目；
- 每条都写明来源（哪个 tools 原件）、为何无覆盖（判分器 judge-only/CLI 无测试驱动/纯搬运未接线）、
  以及验证方式（cmp -s 逐字节、11 门红绿模式）；
- `uncovered_allowlist` 是**既有机制**（该 yaml 里此前已有 `src/database/datatools/*` 同类登记）。

**我的实测**：
```
$ pytest tests/test_affected_tests_map.py            (worktree，登记在)  → 15 passed
$ /tmp 副本删掉 10 条登记后同一测试 →
  FAILED test_every_production_module_is_mapped_or_honestly_allowlisted   ← 门会如实报红
```
反向验证成立 ⇒ 登记是让守门继续工作所**必需**的如实记录；若不登记，门就红着——
那才是「搬运把全量搞红」。不登记、也不删文件的第三条路不存在。

**裁定**：这是「如实向覆盖率台账登记一个真实缺口」。**不是夹带**——夹带指私改行为/阈值/分支，
此处零行为改动，且施工方主动申报。（债的后续：这 10 个文件日后该有真测试，届时登记应移除——
每条理由里已自带这个语义「no project-side test … yet」。）

### ③ stale `.pth` 环境隐患的处置 —— 裁定：**处置正确（范围克制）；该隐患应登记为独立缺陷，同意请求方**

**隐患三重实测成立**（全部我自己跑的）：
```
① 探针脚本模式（脚本放 /tmp、cwd=worktree）：
     gt_manifest loaded from: /workspaces/EnergyPlus-Agent-dev/src/…   ← 从主树解析！
   .pth 实物：_editable_impl_energyplus_agent.pth 内容 = /workspaces/EnergyPlus-Agent-dev（硬编码）
② worktree 上 test_inspect_dxf / test_gt_from_dxf 两项红（主树绿）：
     gt_vg_config_path_forbidden —— REPO_ROOT 错树所致（详见 §一#6）
③ 新搬的 CLI 裸跑即踩：
     $ python3 scripts/tool_scripts/reading_toolbox.py pens
     ModuleNotFoundError: No module named 'src.agent.reading.as_drawn'
   （裸脚本模式 sys.path[0]=脚本目录，src 走 .pth → 主树 → 主树没有 as_drawn → 响亮失败）
```

**处置裁定**：施工方只给自己动的入口（`run_all.py` 的 `run()`）改 `-m`+`cwd` 防御、
不给其他脚本加防御——**正确**。理由：加防御=改行为=「改进」，派工单 §一明令
「本单不含任何新能力/不重构」；若它顺手给 3 个脚本都加了防御，那才是 §三#3 要抓的夹带。

**登记缺陷**：同意，且应比请求方的表述更尖锐——当前主树没有 `src.agent.reading.as_drawn`，
所以踩坑表现为**响亮的 ModuleNotFoundError**（尚可排查）；**一旦本分支合并回主线**，
同样的裸跑会**静默用主树的代码**（连报错都没有）——那才是这个 .pth 真正的引爆点。
受影响面已实测三项（上述①②③）。修复方向（合并前处理）：worktree 里禁用/修正该 venv 的
editable `.pth`，或所有工具统一走 `-m`/`PYTHONPATH`。**这是环境债，不是本次搬运引入的，
不应记在施工方头上。**

---

## 三、§七 两条补充的裁定

### ① 「7 项 vs 4 项」的过计判断 —— ✅ **请求方判断成立：施工方「7 项皆前置」是过计（虽非虚报）**

我的独立复现（详见上面 §一#6 的表）：

- 与主树相同的 4 项（fingerprint ×1 + f67 ×3）⇒ 前置成立（f67 两树**逐项相同**，我并排跑过）；
- 多出的 DXF 2 项 ⇒ 我在 worktree 复现红、主树绿，根因**确证**为 stale `.pth` 串台
  （脚本模式 `sys.path[0]`=脚本目录 ⇒ `src` 从主树解析 ⇒ `REPO_ROOT` 错树 ⇒ 路径守卫 raise）。
  它们**不是前置失败**（父提交上不红），也**不是本次搬运引入**（diff 未碰相关文件——
  机制在 §四③ 的环境隐患里，该隐患在搬运之前就存在）。
- 第 7 项（`test_zone_agent` openai）⇒ 两树单独/并行**全部通过**，我复现不出；
  施工方此项报告存疑，但无论真假都不改变过计判定。

⇒ 「7 项皆前置」不成立（至少 2 项不是）；准确表述应为
「4 项前置 + 2 项 worktree 环境产物（stale .pth）+ 1 项未能复现」。
这与请求方 §七① 的解读一致，且机制已由我定位到具体守卫与 .pth 文件。

### ② ⭐ F-93 那条推论（锁陈旧 vs 回归）—— ✅ **推论成立（独立证据链完整）；附一处事实核对**

**推论内容**：那 4 项红的根因 = gt 于 `e982eba`(08-23 07:02) 重签使两层指纹一致，
而锁建于 `96604c9`(08-22 14:41)、预设指纹不一致 ⇒ 锁陈旧非回归；
且「orchestrator 08-25 用该生成器建的六图绑定合法」。

**我的独立证据链**：

1. **锁的意图（读锁与生成器原文，非请求方转述）**。
   `tests/test_elevation_score_bindings.py:341` 断言 builder 对 sm25 必须 `returncode != 0`；
   builder 的 fail-closed 分支（`build_score_view_bindings.py:130-142`）是
   **`len(fingerprints) != 1 or len(extents) != 1` 才拒**，错误信息原文写着
   *"S1 (dispatch §五) is ratified as a gt-generator fix — identical multi-floor outlines
   must carry bit-identical fingerprints — and this builder refuses to paper over the
   disagreement"*。`96604c9` 提交信息亦明确：「任一分歧 fail closed」+
   「⭐ GPT 推论已并入 S1 要求：只统一指纹不够，必须同时统一 world_along_interval 的浮点值」
   +「sm25 六图判分仍被 S1 阻塞，待另一批」——即 **S1 本来就是 gt 侧修复要求，修好后锁的前提消失**。

2. **历史 gt 指纹实测**（`git show <c>:gt.json` 逐版本提取）：

```
96604c9 (08-22 锁落地): 四族全部 跨层不一致 ['36fb25250aad8972…', 'fbfc5e046f79633…']  ← 锁当时绿
e982eba (08-23 gt重签): 四族全部 一致 52f382ee6abb40bc…                              ← 锁从此红
HEAD                  : 四族全部 一致 52f382ee6abb40bc…
```

   且我实测当前 gt 两层 extent 也逐位一致（含 North 的 `15.000000000000002` 浮点值逐位相同）。

3. **失败模式**（我在主树独立复跑）：

```
$ pytest tests/test_elevation_score_bindings.py::test_generator_fails_closed_on_sm25_multi_floor_fingerprint -q -n0
E assert 0 != 0   ← builder 对当前 gt 成功退出 0（指纹一致 ⇒ 不拒），锁要求它必须拒
```

   红因是**前提消失**，不是防线被拆。

4. **防线未被削弱**：`git log e982eba..HEAD -- scripts/tool_scripts/build_score_view_bindings.py`
   → **空**（gt 重签后 builder 零改动）。搬运 diff（283e868）也不含
   builder / gt / 该测试文件（13 个文件全是工具箱搬运）⇒ 与本次搬运无关。
   （我还尝试过用「篡改 gt 指纹」的变异验证拒路径仍可达，但被更早的 gt 身份校验
   `score_gt_identity_invalid` 拦下——gt 防篡改在工作；改用历史版本比对完成证明。）

5. **推论落点——08-25 的六图绑定**（`run_2026-08-25_c2_rescore_R0/_run/judge_score_bindings.json`，
   在 `2b01ca6` 提交在案）：

```
六条绑定 = 2 plan (1f/2f) + 4 elevation (East/North/South/West, floors=[F1,F2])
四个立面绑定嵌的指纹 = 52f382ee… = 当前 gt 指纹（逐位）
$ builder --run-dir R0 --gt 当前gt --out /tmp/… → rc=0
在案(08-25建) == builder 复产 : True        ← 逐字段一致
```

   （顺带核了 run_all.py BIND 指向的 H2_fullcase 那份 08-23 的旧绑定：同样与 builder 复产
   `True`。两份都合法。）

**裁定**：请求方的判断**成立**——锁陈旧、非回归；08-25 六图绑定由该生成器在当前 gt 上产出、
逐字段可复现、指纹同步 ⇒ **合法**。C2 评估结论不需要因这条作废。
该锁红着的正确处置是「锁跟着 gt 走」（改写为用**合成的不一致夹具**而非真 gt，或明确退役），
这是 F-93 已登记的债，不是本次搬运的事。

---

## 四、送审书本身的前提核查（若有错误前提 / 互相矛盾，在此指出）

**无推翻裁决的错误前提**。送审书 §二「我已亲手复跑过的三条」我**全部独立复验成立**
（逐字节 ✓ / 闭包内容 ✓ / 12 passed ✓）；§七② 的推论成立（见上）。发现的小出入：

1. **施工方「7 项皆前置」过计**（§七① 的怀疑正确）：2 项 DXF 在父提交上**不红**，
   是 worktree 环境产物（stale `.pth`）；1 项（zone_agent）两树全过、**我复现不出**。
   记账应改为「4 前置 + 2 环境产物 + 1 未复现」。
2. **施工方自述「checks/as_drawn 4 行」不精确**：实际 5 处 import 改动
   （漏报函数体内 `from as_drawn_v2 import _ink_groups` 那处）。性质纯路径、非夹带。
3. **派工单 §五#6「全量绿」与基线现状不符**：主树基线本身红着 4 项（F-93），
   「全量绿」在当前基线上不可能达成。派工单自带「实际数以施工时为准」的活口，
   且 F-93 与搬运无关（§七② 已证）——属理想化表述，不算矛盾，但请求方裁决后应把
   基线口径修成「4 项已知红（F-93）」。
4. **基线 `RESULTS_v2.json` 的数字不能当对照**（98.6/97.0/97.5 ≠ 99.2/97.8/97.9）：
   送审书 §五#1 已自我披露（08.25c 改了判分器未重跑）——我证实该差异**全部来自请求方
   搬运前的改动**（原路径同代码对照 0 差异），与搬运无关。请求方裁决后须重跑补上。

（总裁决见文件开头 §〇。）
