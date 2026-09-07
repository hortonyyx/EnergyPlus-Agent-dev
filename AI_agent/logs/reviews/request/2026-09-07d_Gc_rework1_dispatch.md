# 派工单 · G-c 返工 1：rebase 到主线 + 收掉 6 条红 + 补交件

> **施工 = GPT-6 Astra**（经 codex CLI）· **复核 = GLM 跨家族**（用户 2026-09-07 指定，⛔ 不改）
> **档位 = 工程档**（碰 `src/agent/judge/` 与判分锁）⇒ gate① + **全量绿**是硬验收。

## 〇 与安全攻防无关的声明

本单全部内容是**建筑 CAD 图纸的几何入库与单元测试维护**。文中的
「锁 / 门 / 攻击 / 负样本 / 存货」是本项目对**单元测试判据**的固定叫法，
⛔ 与网络安全、攻防、漏洞利用**无任何关系**。若你的策略层对某个词敏感，
请把它读作「测试断言 / 测试用例 / 反例夹具」。

---

## 一 你是谁、在哪、审什么

- **你是施工方。** 上一任施工席（Claude）在这条分支上做完 8 段提交后**撞月度支出上限中断**，
  ⛔ 不是它判断做完了。**它的活没有丢**：8 段全部落库、工作树干净、零孤儿件。
- **工作目录 `/tmp/gc_rework_astra`**（分支 `wt/09.07d_gc_rework`，从 `09.07_Gc_snap_ladder` 切）。
  ⛔ 不要动主树 `/workspaces/EnergyPlus-Agent-dev`、⛔ 不要动 `/tmp/gc_snap_ladder`。
- **必读（⛔ 一律用主树绝对路径读 —— 本单在被审提交之后写的，按构造不在你树里）**：
  - 本单：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/request/2026-09-07d_Gc_rework1_dispatch.md`
  - 原派工单：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/request/2026-09-07a_Gc_snap_ladder_dispatch.md`
  - 中断状态档：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-09-07b_Gc_interrupted_state/README.md`
  - 拆钉裁决书（类 B 的前置）：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/verdict/2026-09-07c_split_deferred_pin_crossreview_glm.md`

### 开工先自检（⛔ 不做，后面所有读数都不作数）

```sh
cd /tmp/gc_rework_astra
git log --oneline -1
python -c "import src.agent.judge.tarch_normalize as m; print(m.__file__)"
# ⭐ 必须落在 /tmp/gc_rework_astra。⛔ 落别处 = 你测的不是这棵树，停下上报。
```

⚠️ 共享 venv：⛔ **绝不许跑 `pip install -e .` 或任何写 `site-packages` 的命令。**
⚠️ 跑测一律 **`-n 6`**，⛔ 不用 `-n auto`（同机可能有别的席位）。

---

## 二 ⭐⭐⭐ 派工方已核过什么、⛔ 【没核】什么

**这一节是给你和复核方看的：⛔ 别把「主控审过」当成整块都审过了。**

| 我审过（逐行读了实现） | 结论 |
|---|---|
| `9f9f2ae7` 阶梯内核（`_ladder_verdict` / `_anchor_end` / `_axis_snap_cap_native` / `_anchor_candidates_are_indistinguishable`）| ✅ 忠实于用户四条口径、**零新阈值**；退化线守卫（`atan2(噪声,噪声)`）写得对 |
| `b5c62bf0` `as_measured.py` 的 A-11-d3 豁免 + 档 2 仲裁台账 | ✅ 与债的原文逐字对应；仲裁台账是个具名容器，⛔ 没让「45° 真斜线」和「0.4° 不该拉平」塌成同一个缺席 |
| 全 4 个测试文件的**测试函数名增删对账**（机械） | ✅ 「零删除、零降级」自述**属实**：14 个消失的名字全部对得上替代物 |

| ⛔ 我**没有**逐行审的（= 你和复核方要盯的那一半） | 体量 |
|---|---|
| `d9d859e0` 端点被移动后共用它的笔画跟着走 | 席位自补的缺口，**主控设计没写过** |
| `161e5f61` 两个 case 的 facts 三件套重出 | 6 个 json + 一个重出脚本 |
| `b068bc8a` / `c893c5ef` / `8fb770a9` / `f2188df5` 四段锁重推 | **约 1340 行测试改动** |

---

## 三 任务（⭐ 严格按此顺序，⛔ 不许跳）

⭐⭐ **本单说的 6 条红 + 三分类，是派工方在 `f2188df5` 上【本轮重新跑出来的】**（⛔ 非转引上一程的记录）：

```
python -m pytest -q -n 6 -p no:cacheprovider \
  tests/test_answer_compiler_profiles.py tests/test_as_drawn_denominator_f126.py \
  tests/test_a11_gt_1mm_ingest_resolution.py tests/test_f156_ring_from_intersection.py \
  tests/test_boundary_condition_facts.py
⇒ 6 failed, 47 passed in 5.84s
FAILED test_answer_compiler_profiles.py::test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na   [类A]
FAILED test_as_drawn_denominator_f126.py::test_l4_discarded_non_orthogonal_segments_are_itemised                            [类A]
FAILED test_a11_gt_1mm_ingest_resolution.py::test_external_quantities_are_bit_identical                                     [类A]
FAILED test_a11_gt_1mm_ingest_resolution.py::test_the_scan_goes_red_when_the_snap_is_removed                                [类C]
FAILED test_f156_ring_from_intersection.py::test_projected_ring_identity_holds_with_no_tolerance_at_all                     [类B]
FAILED test_boundary_condition_facts.py::test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches                       [类B]
```

⭐ **一律用测试函数名定位，⛔ 别用行号**（行号会漂；本单给的行号只作参考，已逐条核过）。

### T0 · rebase 到主线（⭐ 先做，因为它会改变类 B 的题面）

```sh
git rebase fde2f24c        # 主线 HEAD，含 883d4e51「拆钉」
```

⭐ **派工方已预判：两边改动面零重叠，应当无冲突。**
⛔ **若真出冲突 ⇒ 停下上报**（说明我这条预判错了，那是承重前提错）。

⭐ rebase 之后**先跑一次全量、把读数原样记下来**，⛔ 不要先动手改。
类 B 那 2 条红的**面目会变**，你要基于变化之后的面目施工。

---

### T1 · 类 B（2 条）—— ⭐⭐⭐ 现在它会自己告诉你是哪一支

两条 = `test_f156_ring_from_intersection.py::test_projected_ring_identity_holds_with_no_tolerance_at_all`
与 `test_boundary_condition_facts.py::test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches`。
rebase 前是 `assert 2 == 4`（`SM25_DEFERRED_CAVITY_COUNT`，看不出是哪一支变的）。
rebase 后主线已把它拆成 per-cause 两个钉 ⇒ **红的那条会指名 `SM25_DEFERRED_F153_FORM_B_COUNT`**。

**已经查实的事实（⛔ 不需要你重新论证，但你可以证伪）**：
- **变的是 F-153 form B 那一支：2 → 0。F-157 那一支纹丝不动（2 → 2，同样两个 cavity id）。**
- **这是真退休，⛔ 不是回归**：GLM 跨家族复核逐行复刻生产者定义量出
  G-c 树 `F1-z4`/`F1-z5` 对称差 = **`0.000000`**；同一把尺子在主树量出 **`1182000.000000`**，
  与生产者写进 failure 行的数逐位一致（复刻自证）。

**修法**：
1. `tests/deferred_projection_ledger.py` 里 `SM25_DEFERRED_F153_FORM_B_COUNT` **2 → 0**。
   ⭐ 该模块 docstring 已明写「when a fix lands it reddens — update it here, once,
   **in the same commit as the fix**」⇒ **这就是那个 commit**。
2. ⭐⭐⭐ **同时把 docstring 里的裁决正文改成「F-153 form B 已退休」，并写清是被什么修好的**
   （阶梯把吸附锚点从中点改成接头端 ⇒ 接头闭合 ⇒ 投影环与 zone 逐位重合）。
   ⛔ **不许只改数字不改叙述** —— 那会留下一份「叙述说它是已知欠债、代码说它是 0」的自相矛盾档案。
3. `SM25_DEFERRED_CAVITY_COUNT` 是**派生值**，⛔ 不要手改它（它会自己变成 2）。
4. ⛔ **不许动 `SM25_DEFERRED_F157_UNAVAILABLE_COUNT`**（那一支没变，动它就是掩盖）。

⚠️ **顺带核一件事**：`tests/test_o21d_exclusion_gap.py` 的 docstring 说
「the sole surviving ledger entry is F-153 form B」。**派工方已实测：主树与 G-c 树的
producer-written `boundary_ring_losses` 存货【都是 0】**（A-11 就已清零，⛔ 非 G-c 造成），
且该文件的 `test_deregistering_each_live_loss_clears_exactly_its_own_red` **自己声明**了
「存货到 0 时本 loop 自然空转，牙在构造夹具那条上」⇒ **⛔ 不是洞、⛔ 本单不修**。
但那句 docstring 的**叙述**已经过时 ⇒ **只改叙述、⛔ 不动断言**，并在交件里写一句。

---

### T2 · 类 A（3 条）—— 存货被这次修复消灭了，⛔ 修法不是改期望值

| 测试（函数名）| 断言（行号仅供参考，已核）| 为什么坏 |
|---|---|---|
| `test_answer_compiler_profiles.py::test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na` | `:62` `{…unresolved_revisions} >= {'rev-13ad','rev-13ae','rev-13af'}` | 台账清零 ⇒ 这三条 revision 不存在了；**该锁整个是靠「台账里有这三条」立着的** |
| `test_as_drawn_denominator_f126.py::test_l4_discarded_non_orthogonal_segments_are_itemised` | `:260` `{BLOCK 诊断码} == {'tarch_wall_free_end'}` | 13AF 成了面线 ⇒ 那堵墙不再有自由端 ⇒ 该诊断消失 |
| `test_a11_gt_1mm_ingest_resolution.py::test_external_quantities_are_bit_identical` | `:295` 身份串比对 | 三件套重出 ⇒ 身份串变了 |

⭐ **这一族的名字**：**存货是【检查形态】的函数，不是给定的**
（[[gate-teeth-direction-follows-fixture-inventory]]）。

**修法 = 给这些锁重建负样本**，⛔ **不是**把期望值改成新数字、⛔ **不是**删锁、⛔ **不是**降级。
⭐ **上一任席位在它自己动过的 4 个文件里已经这么做了**，提交信息 `8fb770a9` 逐字写着
「阶梯把这份锁的唯一负样本修好了 ⇒ **重建负样本，⛔ 不是删锁**」——
**这 3 条只是它还没走到的同一件事，请照同一个做法办。**

⭐⭐⭐ **每条改完必须能回答**：「**不加这处改动，这门本来红不红？**」
（[[gate-with-only-negative-assertions-is-unobservable]]）——
即：你重建的负样本，**必须实测它在正确代码下变红**，⛔ 不许只断言它会红。

---

### T3 · 类 C（1 条）—— 基线数要重新推导，⛔ 不是把 46 改成 48

`test_a11_gt_1mm_ingest_resolution.py::test_the_scan_goes_red_when_the_snap_is_removed`
（`:220` 的 `assert buckets[bucket] == expected`）：`face_lines: 48 != dispatch baseline 46`。
13AF 现在是面线了 ⇒ 面线桶多一条。

⛔ **不许直接把 46 改成 48。** 要做的是**重新推导这个基线钉的是什么**，并把推导写进 docstring：
它钉的是「某次派工单声明的数」，还是「这份图纸按当前口径应有的面线条数」？
⭐ 若它钉的是前者，那它本来就该跟着口径走 ⇒ **改数并写清新数的来源**；
⭐ 若是后者，⇒ **给它一个能自证的推导**（从图纸/事实层算出来，⛔ 不是抄一个观测值）。

---

### T4 · ⭐⭐⭐ 枚举这一类，⛔ 不要只修这 6 个例子

**本项目 2026-09-06 的硬教训**：复核方按症状只找到 1 个洞，**逐项枚举找出另外 6 个**
（[[enumerate-the-class-not-the-example-found-six-more]]）。

⇒ **T1–T3 收完之后，逐项枚举**（⛔ 不许只按「哪个测试红了」找）：
仓库里**还有哪些锁的存货，是被这次阶梯改动消灭或改变的**？
候选检索面至少包括：钉着 `13AD` / `13AE` / `13AF` 的 · 钉着 `rev-` 台账条目数的 ·
钉着 `axis_snapped_lines` / `non_orthogonal_lines` 条数的 · 钉着面线/墙条数基线的 ·
钉着 `AXIS_SNAP_MAX_ANGLE_DEG` 或已作废的 10 mm 的。

⭐ **对照表本身就是交付物**：逐条列「这把锁 → 它的存货是什么 → 阶梯之后还在吗 → 结论（无需动 / 需重建负样本 / 需重推）」。
⚠️ **这张表的外延是你自己划的** —— 请在交件里写清**你是怎么划的、可能漏掉哪一类**。

---

## 四 硬纪律

1. ⭐⭐⭐ **分段提交**（本项目已第四次靠它避免丢活）：**每完成一个 T 就 commit**，
   ⛔ 不要攒到最后。上一任正是撞上限中断，靠这条**一行代码没丢**。
   提交信息格式 `<月.日>_<英文标签>`，body 含 ①改动 ②为何此刻 ③影响（**实测数字，⛔ 非估算**）。
2. ⛔ **禁 `git add -A`**（同机有别的席位）；只 add 明确路径，commit 前必看 `git diff --cached --numstat`。
3. ⛔ **禁** force push / `reset --hard` / 跳 hook / 动 `git config`。
4. ⭐ **改→量→写，不许换序**：写进提交信息 / 交件的每个数字，必须是你**跑出来**的，
   ⛔ 不许估算、⛔ 不许从上游推断（[[verify-the-number-before-writing-it-into-a-load-bearing-place]]）。
5. ⛔ **不要在 `.py` 的字符串常量（docstring 也算）里写带仓库根前缀的生产文件路径**
   （`src/agent/...` 这种）——依赖图会因此造出一条真实的边，把无人测试的模块静默标成「已覆盖」。
   用不带前缀的相对写法或点号模块名。

---

## 五 停下上报（⭐ 分层，⛔ 不是无差别的「有疑问就停」）

**本项目 70/70 的「停下上报」全是派工方的题错，记功不记过。**

**A 类 · 承重前提错（错了整个任务方向作废）⇒ 立刻停，⛔ 不要往下做**：
1. 自检那步 `__file__` 没落在 `/tmp/gc_rework_astra`。
2. **T0 的 rebase 出冲突**（我预判无冲突，出了就是我错）。
3. rebase 后**红的条数/身份与本单描述对不上**（本单说 6 条、分三类）。
4. 你判定 **T1 的「F-153 form B 是真退休」是错的**（那会推翻本单的整个 T1）。
5. 你认为**某一类的修法方向本身就错**（例如你认为某条锁应当删而不是重建负样本）。

**B 类 · 外围数值/论据错（不改变任务方向）⇒ ⭐ 记录并继续做**：
- 本单引用的某个行号、某个数字对不上（记进交件，别停）。
- T4 枚举出的某条你判为「无需动」而我可能不同意（写清理由，继续）。

---

## 六 交件

写到 `/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/execution/2026-09-07d_Gc_rework1_execution.md`
（⭐ 主树绝对路径）。必须含：

1. **逐 T 的改动 + 每条的原始命令与输出**（⛔ 不要只写结论）。
2. **T2 每条重建的负样本，各给一次「它在正确代码下变红」的实测**。
3. **T3 的基线数：新数的推导过程**，⛔ 不是「实测是 48 所以写 48」。
4. **T4 的对照表全文** + 你划外延的方法 + 你认为可能漏掉的那一类。
5. **全量读数**：`python -m pytest -q -n 6 -p no:cacheprovider`，
   跑前跑后各核一次 `python -c "import src.agent.judge.tarch_normalize as m; print(m.__file__)"`。
   ⭐ **参照**：主线 `fde2f24c` = **3989 passed / 0 failed / 2 skipped / 13 xfailed**；
   G-c rebase 前 = `6 failed / 4003 passed / 2 skipped / 13 xfailed`。
   **验收 = 0 failed**，且你要**逐位说明** passed 数的差额是由哪些新增/删除测试构成的。
6. **⭐ 最薄弱的一处**：本轮你自己最没把握的一个判断是什么、它错了会怎样。
