# 派工单 · **F-154 重发**：墙端头不是任何墙的「面」⇒ 整间房的边界环丢失（**授权重做基线**）

- **日期**：2026-09-01 · **派工方**：orchestrator · **施工方**：**GPT 家族** · **审**：**GLM 家族**（跨家族）
- **基线**：**`58bb59f`** · **权威全量**：**3519 passed / 13 xfailed / 0 failed**（12m14s、`-n auto`、exit 0，四项哨兵全干净）
- **本单是重发**：上一版 [`2026-08-31_f154_wall_endcap_unowned_dispatch.md`](2026-08-31_f154_wall_endcap_unowned_dispatch.md)
  被施工方按停报触发器**正确地中止**，裁决在该单 §七–§九。
  ⭐ **本单累计式自包含**，⛔ 不要去读旧单来补全任务项；旧单只作历史与实验读数的出处。

---

## 〇、⛔ 排程（同机三席，家族各一）
GPT = **本单**（写 `src/agent/judge/as_measured.py` + `case_tests/test_baseline/gt_staging/` + 两个测试文件）·
GLM = 模块 5+6（写 `src/agent/correction/decision_schema.py` / `decision_executor.py` 两个**新文件**）·
Claude 席 = NF-1 微单（写 `src/agent/reading/as_drawn/schema.py` + `tests/test_f97_vector_contract.py`）。
⇒ ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量；跑测 **`-n 4`**；
`git status` 不干净是正常的，**别碰别人的文件**；若你的测试因别人的改动变红 ⇒ **停下上报，别去修**。

---

## 一、承重前提（**主控亲手量的**，⛔ 请自己复核，不符就停下上报）

F-153 已把「静默吞掉」改成「点名记账」（`boundary_ring_losses` 已进事实层）。
**但三间房仍然丢** —— `boundary_edges` 数量前后不变（F1 44→44 / F2 56→56）。本单要修的是**它们为什么丢**。

### 1. 三个失败 span **长度全是 1200 单位 = 120 mm = 一堵墙的厚度**
```
plan-F1 cavity:8bd127719198fd63  88.27 m²  span axis=y const=98800 [160000,161200]  最近同轴墙面 delta=-11200 (1120 mm)
plan-F1 cavity:04e1293098b1a95a  28.68 m²  span axis=y const=52401 [ 99430,100630]  最近同轴墙面 delta=+1     (0.1 mm)
plan-F2 cavity:495501ce9b36f0f3  70.34 m²  span axis=x const=60000 [110000,111200]  最近同轴墙面 delta=+20000 (2000 mm)
```

### 2. ⭐⭐⭐ 三条 span **各自恰好是某堵【垂直】墙的端头**（主控实测 3/3）
```
span (y,98800,[160000,161200]) ← w_x_160000_161200_61600_98800  along_max == 98800
span (y,52401,[ 99430,100630]) ← w_x_99430_100630_52401_88800   along_min == 52401
span (x,60000,[110000,111200]) ← w_y_110000_111200_60000_68400  along_min == 60000
三条的【同轴面认领数】全部 = 0   ← 这正是 _boundary_owners 找的东西
```
⇒ `_boundary_owners`（`as_measured.py:1183`）判据 = `const in (group.face_lo, group.face_hi)`
—— 它找的是墙的**侧面**。**端头不是任何墙的侧面 ⇒ 永远 owners=0 ⇒ `ring_is_logical=False` ⇒ 整环丢。**

### 3. ⭐⭐⭐ **判别实验：这其实是【两个】病，⛔ 别当一个修**
主控把那 0.1 mm 补上（`52401→52400`，墙 + 两条面线共 3 处），重跑：
```
plan-F1 基线            : edges=44  losses=2   88.27m2 | 28.68m2
plan-F1 补上 0.1 mm 之后 : edges=52  losses=1   88.27m2      ← 28.68 那间【活过来了】，+8 条边
plan-F2                 : 无 52401/52399 端点，不受影响
```
⇒ **28.68 m² 那间的病因是 0.1 mm 端点错位**（上游画法/吸附/修订那条线，**⛔ 不在本单**）；
⇒ **88.27 + 70.34 两间才是本单要修的「端头无人认领」** —— 补 0.1 mm 对它们**毫无作用**。

### 4. ⭐ 上一轮施工方已跑通的实验读数（**⛔ 线索非证据，本轮仍须你自己复跑**）
```
plan-F1 44/2 → 88/1        plan-F2 56/1 → 91/0（F2 的 loss 清零）
28.68 那间仍在 loss 里、delta 仍为 1
新 content_sha256 = 1e59ecae…（⛔ 不作目标值，你的修法未必产出同一个）
```

---

## 二、任务

### 任务 1 · 让**墙端头**成为可被认领的边界，且**不引入任何阈值**
⭐ **派工方的方向（推荐但不指定）**：`_boundary_owners` 今天只问「哪堵墙的**面**落在这条线上」；
再加一问「哪堵墙的**端头**正好是这条线」——判据是**精确拓扑**
（垂直轴 + `const in (wall.along_min, wall.along_max)` + face 区间与 [lo,hi] 有正长度重叠），**⛔ 无距离容差**。
端头认领出来的边，其 `boundary_condition` 该判成什么，由你按 `_classify_boundary_fact` 的既有语义定，并**说明理由**。

⭐⭐⭐ **第四条路很可能存在而我没想到**：若你找到严格更优的做法，**直接走它并说明**。
⛔ **明确不许的两条**：① 任何形式的距离容差 / 阈值；② 在 `_boundary_owners` 外面加一层「特殊情况」分支去绕过它。

### 任务 2 · ⭐⭐⭐ **重做 sm25 的 staging 基线**（**本单解除「哈希不许变」，这是与上一版最大的不同**）
`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/` 三件套要重生成：
`as_measured.json`（内容变、`content_sha256` 从 **`0d3aefa2…`** 变）·
`revisions.json`（`as_measured_content_sha256` 跟着换）· `as_signed.json`（重新派生）。
⭐ 入口 = `gt_facts_staging.write_facts_candidate(case, as_measured, ...)`。
⚠️ **⛔ 不许手改 JSON** —— 必须**从 DXF + request 重跑生成**，否则就是手搓答案。
⚠️ **⛔ 台账里那 5 条 revision 的内容与 verdict 一个字都不许动**（全部保持 `unsigned`，本轮不签任何字）——
本轮只换它指向的那个哈希。

### 任务 3 · ⭐⭐⭐ **更新被读数钉死的既有断言 —— 但每一处差异必须逐条有出处**
上一轮实测：本修法会让指定四文件从 `84 passed` 变成 `76 passed / 8 failed`。**八条逐一如下**：
```
tests/test_gt_facts_staging_sm25.py::test_1_as_measured_matches_the_as_received_build_bit_for_bit   ← 任务 2 重生成后自愈
tests/test_boundary_condition_facts.py::test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches
tests/test_boundary_condition_facts.py::test_r2_mutating_one_boundary_condition_reddens_only_that_edge
tests/test_boundary_condition_facts.py::test_rework_e2c_converter_zone_fifty_metres_outside_all_facts_is_named
tests/test_boundary_condition_facts.py::test_rework_e3_deleting_one_complete_facts_ring_reddens_only_that_ring
tests/test_boundary_condition_facts.py::test_rework_e4_all_boundary_facts_empty_is_never_zero_comparisons_green
tests/test_boundary_condition_facts.py::test_rework_real_sm25_two_metre_footprint_vertex_spike_reddens_the_lost_view
tests/test_as_measured_facts_layer.py::test_r2_projection_fields_are_absent_but_boundary_condition_is_first_class
```
⭐ **授权**：允许你改这些断言里的**期望读数**（`paired_edges == 100`、那张 4 行排除清单、
`{("exterior","outer_skin"):32, ("interzone","wall_axis"):68}` 这类被钉死的数）。
⛔⛔ **但下面三条是非谈判项**：
1. **每一处改动的差异必须逐条有出处** —— 说清「哪个 cavity / 哪个 converter zone 从排除变成了配对、
   因此这个数从 X 变成 Y」。⛔ **不许「改到绿为止」**，⛔ 不许只写一句「读数更新」。
2. ⭐⭐⭐ **改完必须当场证明这些锁【还能变红】** —— 对每一条被你改过期望值的锁，
   施加**它当初被写出来所针对的那个变异**（名字里就写着：`mutating_one_boundary_condition` /
   `deleting_one_complete_facts_ring` / `converter_zone_fifty_metres_outside` /
   `all_boundary_facts_empty` / `two_metre_footprint_vertex_spike`），**逐条给出它确实变红的读数**。
   ⛔ 只报「现在全绿」不算交付（[[gate-with-only-negative-assertions-is-unobservable]]）。
3. ⛔ **不许改任何断言的【结构】或【语义】** —— 只许改被钉死的期望数值。
   若你发现某条锁的**形状**本身需要改（不只是数值），**停下上报**。

### 任务 4 · **留一条给后来人的账**
在 `as_measured.py` 里写清（docstring 即可）：**端头认领这条路为什么是精确拓扑而不是容差**，
以及**它与「面认领」的关系**。⛔ 别在 `.py` 的字符串里写带仓库根前缀的路径（会造出假的依赖边，F-152）。

---

## 三、⛔ 禁令
1. ⛔ 不许改 `min_room_area_m2`，不许新增任何以米/毫米为单位的阈值常量**而不显式上报**。
2. ⛔ **不许碰那 0.1 mm**（`52401`/`52399`）—— 那是另一条线的活；本单**必须在不补它的前提下**修好另外两间。
3. ⛔ **不许手改 `gt_staging/` 下任何 JSON**（只能由生成器重写）；⛔ **不许动 `gt_sources/`**（DXF 与 request 是输入）。
4. ⛔ **不许签任何 revision**（5 条保持 `unsigned`）。
5. ⛔ 不许动 `answer_compiler.py` / `src/agent/correction/` / `src/agent/reading/`（别的席位在写）。
6. ⛔ 除任务 3 授权的**期望数值**外，不许改任何测试断言；有别的既有锁变红 ⇒ **停下上报**。
7. ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量。

## 四、验收表（⭐ 已按**三格**对撞：①禁令 ②任务项 ③**已落库/已签字产物的既有承诺**）

| # | 验收项 | 对撞检查 |
|---|---|---|
| 1 | **88.27 与 70.34 两间产出 boundary edges**（不再在 loss 里）；⭐ **28.68 那间【仍然】在 loss 里且 delta 仍报 1** | ⭐ 与禁令 2 对撞：**若你顺手把 0.1 mm 也修了，本条必然不通过** |
| 2 | ⭐ **先绿后红/先红后绿自证**：给出改动前后 `edges` / `losses` 的逐 view 读数 | — |
| 3 | ⭐⭐ **端头认领不得放行不该放行的**：造一份合成夹具，让某条 span **既不是任何墙的面、也不是任何墙的端头** ⇒ **必须仍然 owners=0 并记进 loss** | ⛔ 与「不加特殊分支绕过」对撞：**若你把端头做成兜底放行，本条必然不通过** |
| 4 | ⭐⭐ **端头唯一性**：造一份两堵墙端头**落在同一条 span** 的夹具 ⇒ **必须仍然失败**（`len(owners)!=1` 的既有语义不许被稀释） | 与任务 1「精确拓扑」一致 |
| 5 | ⭐⭐⭐ **新旧哈希都给出来**：旧 `0d3aefa2…` → 新 `<x>`，且 `revisions.json` 与 `as_signed.json` **都指向新值**、三者自洽 | ⭐ **第三格对撞：本条【故意要求哈希变】** —— 与上一版那单**正好相反**，因为本单授权重做基线 |
| 6 | ⭐⭐⭐ **重生成是机械可复现的**：同一份 DXF + request 跑两次 ⇒ 三件套**逐字节相同** | ⛔ 与禁令 3 对撞：**若你手改过 JSON，这条必然不通过** |
| 7 | 台账 5 条 revision 的**内容与 verdict 逐字未变**（给 diff 证明只有那一个哈希字段变了） | 与禁令 4 对撞 |
| 8 | ⭐⭐⭐ **任务 3 的三条非谈判项逐条兑现**：差异逐条有出处 · **每条被改过期望值的锁都当场证明还能变红** · 断言结构未变 | ⭐ 与禁令 6 对撞：**若你改了断言的形状而不只是数值，本条必然不通过** |
| 9 | `pytest -n 4 tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py` **全绿**（基线 84 passed，主控 2026-09-01 实测复核过） | 与禁令 6 一致 |
| 10 | ⭐ **换同形输入**：在 **sm24** 上跑同一套探针（`build_as_measured` 内存复测即可，⛔ 不建 staging），报出它那 2 个 cavity（**23.1672 / 30.8464 m²**）改动后是活了还是仍在 loss | ⛔ 不要求 sm24 也修好；只要求**你去看了并报了** |
| 11 | 列全改动路径（⛔ 不提交） | 与禁令 7 一致 |

## 五、停下上报（分层）
**必停**：§一 任一实测复现不出来 · **除任务 3 那 7 条之外**还有既有锁变红 · 某条锁需要改**形状**而不只是数值 ·
任务项与禁令自相矛盾 · 重生成出来的三件套**与旧的除预期差异外还有别的不同**（那说明生成链不确定）。
**只记不停**：面积末位 · sm24 的结果 · 端头边的 `boundary_condition` 取名分歧。

⭐⭐⭐ **累计 54 次停报，54 次都是派工方的题错 —— 放心停。**
⭐ **上一轮你停的那次就是对的**，裁决已认账：派工方把「必然改哈希」写成了禁令。
本单已按同一教训做过第三格对撞，**并因此发现任务 3 那 7 条行为断言也会互斥** —— 故本单显式授权并加了三条约束。

## 六、交付
代码（⛔ 不提交）+ 执行档 `AI_agent/logs/reviews/execution/2026-09-01_f154_reissue_execution.md`，
逐条给命令+读数、**你自己认为最薄弱的一处**、希望复核方重点打哪里。

---

# ⭐ 裁决（2026-09-01 · 回应施工方的第二次强制停报）

## 七、**停报成立**（主控已独立复现，⛔ 不是转引）

施工方报：端头修法在**条数**上达标，但两个救回来的腔**环自交**，正式落库门拒绝
（`facts_boundary_ring_invalid`）⇒ 与任务 3「只改期望数值、⛔ 不改断言结构」结构性互斥。

**主控独立探针复现**（⛔ 用的是我自己的环重建方式，不是它的）：
```
plan-F1  健康的 11 个腔  各 4 条边  全部 valid
         救回来的那个     44 条边   Self-intersection
plan-F2  健康的 14 个腔  各 4 条边  全部 valid
         救回来的那个     35 条边   Self-intersection
```
F2 的自交点位与席位报的**逐字一致**；F1 略有出入（重建方式不同）⇒ **结论对重建方式不敏感**。
⇒ 席位的实现已按纪律撤下树、保全进
[`logs/experiments/2026-09-01_f154_endcap_selfintersection/`](../../experiments/2026-09-01_f154_endcap_selfintersection/README.md)（**线索非证据**）。

## 八、⚠️ **派工方题错 #57（累计 57，仍 57/57）：我把【代理量】写进了验收的承重位置**

验收 1 我写的是「**两间产出 boundary edges（不再在 loss 里）**」——
**那是边的条数与 loss 条数，不是环成不成立。** 正式消费者要的是**有效简单多边形**。
⇒ 上一轮施工方给的 `44/2 → 88/1` 我在 §一.4 里正确地标了「线索非证据」，
**却在验收 1 里把它的结论当成了「修法有效」这个承重前提**
（[[citing-someone-elses-fact-does-not-transfer-responsibility]] + [[proxy-mistaken-for-the-thing]]）。

⭐ **为什么上一轮没撞到**：那轮被「哈希不许变」挡在正式落库门**之前**就停了，自交环在门后
⇒ [[probe-past-the-blocker-to-find-hidden-walls]]：**「卡在 X」≠「X 之后没问题」**。

⭐ **配套解（本轮起执行）**：**验收项不许用代理量代替本体。**
写下每一条验收时问一句「**这个数达标了，那件事就一定成立吗？**」——
「边数变了」不等于「环成立」，正如「EP 0 Severe」不等于「物理输入对」。

## 九、⭐⭐⭐ 更要紧：**F-154 这个题面本身低了一层**

自交的两个腔是**走廊形状、几十个 T 接头**（44 / 35 条边），健康的矩形腔（4 条边）全部有效。
⇒ 病灶不在「端头能不能被认领」，在**环是怎么造出来的**：
`derive_boundary_edges` 把 **span 的端点首尾接起来**，接头一多必然拼不拢。

⭐⭐⭐ **而这正是用户 2026-08-29 已经签字的那条口径**
（[指南 §十.6c](../../../guides/reading_correction_split_guide.md)）：
> **接头处传播【线】，⛔ 不传播端点；端点由相邻两条线求交算出。**
> gt 侧 `s7_expand_zones` 已经这么做，⛔ 但另一侧没有这一步，
> **事实层存逐边端点后它会【从已解变成未解】。**

`s7_expand_zones` 的 docstring 逐字为证：「rebuild the zone polygon from **offset support-line corners**」
+「**L/T/cross/re-entrant joints need no special-case code**」。
⇒ **那句预言应验了，而且 gt 侧就是它的存在性证明。**

## 十、⇒ 下一张单的题面（⛔ 不是 F-154 的第三次重发）

**⛔ 别再往「端头认领」上加东西。** 新题面 = **把边界环改成从支撑线求交重建**，
与 gt 侧 `s7_expand_zones` 同一机制。
⚠️ **但这是【猜测方向】，不是已证结论** —— 新单必须先做一步**判别实验**：
拿那两个走廊腔，按求交方式重建一次环，**证明它 valid**，再谈施工。
⛔ 若求交方式也拼不拢，说明还有第三层，⛔ 别硬修。

⭐ **端头认领要不要保留，等判别实验之后再定** —— 若环从支撑线求交重建，
「某条 span 有没有 owner」可能整个不再是问题（⛔ 也可能仍然是，别预设）。
