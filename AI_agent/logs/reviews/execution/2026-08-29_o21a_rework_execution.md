# 施工记录 · ②-1a-R 返工：`walls` 改从**面线两两配对**推

- **日期**：2026-08-29 · **施工**：Claude 执行档 · **返工单**：[`request/2026-08-29_o21a_rework_walls_from_face_pairing.md`](../request/2026-08-29_o21a_rework_walls_from_face_pairing.md)
- **上一轮**：[`execution/2026-08-28_o21a_execution.md`](2026-08-28_o21a_execution.md)
- **是否触发「停下上报」**：**否**。§五那个开放问题我判**不冲突**（理由见 §七，⛔ 不是照抄派工方的判断）；
  另有 **2 条题面问题**（§六），两条都是**外围**（其中一条还对我们有利），按分层口径**记账继续**。

---

## 〇、开工自检五条（实测原文）

```
$ git rev-parse --abbrev-ref HEAD && git log --oneline -1
08.23_AsDrawnReading
5357db3 08.29a_ReworkOrder_O21aR_WallsFromFacePairing

$ git status --porcelain
(空)

$ ls AI_agent/logs/reviews/request/2026-08-29_o21a_rework_walls_from_face_pairing.md
-rw-r--r-- 1 root root 9355 Aug 29 03:43 .../2026-08-29_o21a_rework_walls_from_face_pairing.md

$ grep -c "gt 铁律" AI_agent/CLAUDE.md
2
```

⭐ 顺带核过：`5357db3` 相对基线 `9977c26` 只多一份文档，**代码零差**，故代码基线就是 `9977c26`：

```
$ git diff --numstat 9977c26 HEAD
171	0	AI_agent/logs/reviews/request/2026-08-29_o21a_rework_walls_from_face_pairing.md
```

**基线全量**（改动前，⛔ 无 `-m`、⛔ 非 `-n auto`）：

```
========== 3244 passed, 13 xfailed, 212 warnings in 934.76s (0:15:34) ==========
```

⚠️ **如实记录一处过程事故**：这次基线全量我起过**两次**。第一次跑到 97% 时我的连接被中断，
我据此以为它死了、又起了第二次；随后发现**第一次其实正常跑完了**（上面那条汇总行就是它的），
于是把第二次 `TaskStop` 掉。⇒ **贴出来的这条汇总行是第一次跑的完整输出**，⛔ 不是拼接的，
第二次没有产生任何读数。

---

## 一、病灶复核（⛔ 我自己复现，不采信派工单的数）

### 1.1 旧代码（`9977c26`）确实产出幽灵墙

⛔ 用 `git archive 9977c26` 解到 `/tmp/.../old_9977c26`（**不新建 worktree**），
`PYTHONPATH` 强制指向那份树，并让探针**自报 `CODE_FROM`** —— 否则 editable `.pth` 会让它静默落回主树、
变成「自己比自己」（上一单复核方栽的就是这处）：

```
CODE_FROM_as_measured = /tmp/.../old_9977c26/src/agent/judge/as_measured.py
signed   plan-F1: walls= 45 thickness_mm={100: 1, 120: 5, 240: 7, 296: 1, 300: 16, 304: 1, 356: 1, 360: 11, 364: 1, 500: 1}
                  GHOST thicknesses (not 120/240): [100, 296, 300, 304, 356, 360, 364, 500]
signed   plan-F2: walls= 39 thickness_mm={100: 2, 120: 4, 240: 5, 260: 1, 300: 16, 360: 11}
as-recv  plan-F1: walls= 44 thickness_mm={100: 1, 120: 4, 240: 7, 296: 1, 300: 16, 303: 1, 356: 1, 360: 11, 364: 1, 500: 1}
as-recv  plan-F2: walls= 39 thickness_mm={100: 2, 120: 4, 240: 5, 260: 1, 300: 16, 360: 11}
```

✅ 与返工单 §1.1 **逐个数吻合**（签字 F1 的十个厚度值、`300` 出现 16 次）。

### 1.2 ⚠️ 轴向约定相反 —— 这条是**两边都踩过**的，我把它写进了代码和测试

- `denominator` 的 `axis` = **常数落在哪个轴**（竖线 ⇒ `axis="x"`）
- `as_measured` 的 `axis` = **线朝哪个方向走**（竖线 ⇒ `axis="y"`）

⇒ `den_axis = "y" if am_axis == "x" else "x"`。
我在 `_pair_face_lines_into_walls` 里**只翻一次**，并加了一条**能红的**测试
（`test_r1_the_wall_axis_and_its_face_lines_agree_after_the_one_flip`）：
它断言每堵墙引用的面线 `face.axis == wall.axis`；**把那次翻转去掉，四个视图全红**。
⛔ 我没有把它只写成注释 —— 注释不会变红。

---

## 二、做了什么（⛔ 三个文件，一件事）

### R1 · `walls` 改从面线两两配对

**⭐ 复用而不是重写**：把 `denominator()` 里的 D1–D5 那段**原地抽成一个纯函数**
`face_line_targets(geo, affine, *, t_max_m, merge_m)`，`denominator()` 改成调它，
`as_measured.build_view()` 也调它。⇒ **一份实现、两个调用方**，⛔ 不是「照着抄一套筛选」。

**⛔ 我怎么证明这次抽取没有改变 `denominator()` 的行为**：抽取前把四个夹具
（签字/as-received × F1/F2）的 `denominator()` 完整返回值 dump 成 JSON，抽取后再 dump 一次，
**逐字段比对**：

```
denominator() output IDENTICAL once the two new additive keys are removed: True
handles on targets: 642   handles on allowed_not_required: 249
```

两个新键都是**只增不改**的：
- `targets[i]["handles"]` —— 这条 run 由哪些笔画合并而来。
  ⛔ **必须有**：D3 按 **1 mm** 分组、而笔画存的是 **0.1 mm**，实测签字 `plan-F1` 有 2 个组的成员
  坐标与组坐标差 0.1 mm ⇒ **按坐标反查会静默丢掉它们**。
- `allowed_not_required[i]["handle"]` —— 被 D2 剔除的那笔是哪一笔（消费台账要用）。

⭐ 这次比对**当场抓到一个真错**：`perp_reach` 继承了 `groups` 的 span 元组，
我把 span 从 2 元组改成 3 元组后它 `too many values to unpack` 直接炸了。
⇒ 那条「逐字段比对」不是走过场，它有牙。

**配对规则**（⛔ 无厚度阈值）：同轴 + 沿墙方向重叠 > 0 + 取**最近的一条**作对面，每条面线只被消费一次。
⛔ 按声明厚度筛正是 sm24 整批 120 mm 隔墙被静默丢掉的机制（本批指南 §一），所以这里一个阈值都没有。

### ⛔⛔ 225 ≠ 110 这个坑：我把它变成了**结构性**的，不是靠我记得

返工单用加粗警告的那件事，我加了**两道**东西：

1. **消费台账**（`AsMeasuredViewV1` 的 model validator）：每一条 `face_lines`
   必须**恰好**落在三个桶之一 —— 被某堵墙引用 / 被 D2 当 jamb cap 剔除 / 可配对但没配上。
   三个桶两两不交、并集等于全集，否则报
   `as_measured_face_line_consumption_ledger_broken` 或 `as_measured_face_line_in_two_buckets`。
   实测四个视图**全部闭合**：

```
signed      plan-F1: paired=160 + caps=65 + unpaired=0 == face_lines=225
signed      plan-F2: paired=162 + caps=60 + unpaired=0 == face_lines=222
as-received plan-F1: paired=158 + caps=64 + unpaired=0 == face_lines=222
as-received plan-F2: paired=162 + caps=60 + unpaired=0 == face_lines=222
```

2. **一条把坑本身当被测对象的测试**
   （`test_r1_pairing_every_collected_face_line_puts_the_ghost_walls_back`）：
   拿**全部** face_lines 去配对（= 跳过 D2），断言厚度直方图**必须**出现 120/240 之外的值。
   ⇒ 证明**剔除**才是修法的承重件，⛔ 不是那两行配对循环。

### R2 · `wall_bands` 留着，但不叫 `walls`

45 条 band **原样搬**进 `converter_readouts.jamb_cap_bands`（转换器自己的 native mm 浮点，
按既定口径 `converter_readouts` 是全文档唯一允许浮点的子树），docstring 逐字写明
**它们是按 jamb cap(S2) 分组的、⛔ 不是墙**。
`walls_missing_a_face_line` 随之改名 `jamb_cap_bands_missing_a_face_line`
（它描述的是 band 不是 wall），**读数一个没变**：9 / 7 / 11 / 7。

### ⭐ 顺带做实的一件事：faceless wall 现在**造不出来**

`AsMeasuredWallV1.face_line_ids_lo/hi` 改成 `Field(min_length=1)`。
⇒ 返工单验收③「零幽灵」不是一条**扫描**，是**schema 层面的不可能**：
以后谁忘了跑过滤器也复现不了这一类。（`test_r1_a_wall_cannot_be_built_without_ink_on_both_faces`
先断言合法值确实能构造，再证两个方向各自被拒 —— ⛔ 否则这断言可能只是「我写错了字段名」。）

### ⚠️ 一处我自己做的裁断，请复核：`face_lo` / `face_hi` 存的是 **1 mm 的组坐标**

配对的单位是 D3 的「组」，而 D3 按 `GROUP_QUANT = 1 mm` 分组（它的 docstring 里写着理由：
同一条面线的碎片会量化到 9.9399 与 9.9400 两个值）。我把墙的两个面存成**组坐标**，
因为那是**生产者自己**对「哪些笔画是一条面线」的回答（[[recompute-gate-must-mirror-producer-definition]]），
并且这样 `thickness` 才**恰好**是 1200 / 2400。

⛔ 但它确实比笔画自身的 0.1 mm **粗**。我没有让这 0.1 mm 消失：
- 笔画的精确坐标原样躺在 `face_lines` 上，墙**按 handle 引用**它们；
- 两者不一致的组**逐条点名**在 `converter_readouts.face_groups_with_a_split_const`
  （实测：签字 F1 有 4 条 target / 2 个组，另外三个视图 0）。

⇒ **若口径要求墙的面坐标必须是笔画的精确 0.1 mm，这一处要改**，
而那时得先回答「一个组里有两个 0.1 mm 值时取哪个」—— 我没有权限替口径定这件事。

### ⚠️ 被 R1 逼出来的一处 schema 改动：`carrier_wall_id` → `carrier_wall_ids`（复数）

**返工单没预见到这条，但它是 R1 的必然后果**：D4 **从不**跨洞口合并 run，
所以「墙」变成 run 之后，**洞口落在同一堵墙的两段 run 之间**，而不在任何一段里面。
先按原来的「唯一候选」规则跑，结果 **31/30/31/30 个洞口全部变成 `ambiguous`** —— 全丢。

⛔ 我没有靠调规则把它糊过去。先量结构，四个视图**读数完全一致**：

```
signed   plan-F1: openings=31  按【接触】算候选: {2: 31}  按【严格重叠】算: {0: 31}  候选跨越的 face-pair 数: {1: 31}
signed   plan-F2: openings=30  {2: 30}  {0: 30}  {1: 30}
as-recv  plan-F1: openings=31  {2: 31}  {0: 31}  {1: 31}
as-recv  plan-F2: openings=30  {2: 30}  {0: 30}  {1: 30}
```

⇒ 每个洞口**恰好**接触 2 段 run、**严格重叠 0 段**，而那 2 段**永远同属一个 face-pair**。
**「是哪堵墙」完全无歧义；有歧义的只有「是它两段 run 里的哪一段」，而那个问题没有答案。**
⛔ 从两段对称的 run 里挑一段写进 `carrier_wall_id`，等于往记录里写一句假话
（「这个洞口在那一段里面」）——[[observation-named-as-fact-travels-as-fact]]。
⇒ 改成复数，并加断言：每个洞口**必须**恰好 2 个 carrier、且它们的 face-pair 必须**唯一**、
且等于洞口自己的 `(axis, cross_lo, cross_hi)`。实测 `unresolved_opening_carriers` 四个视图**全 0**。

---

## 三、返工单 §三 六条验收 · 逐条实测原文

### ① ⭐⭐ 厚度直方图（**四组全贴**）

```
signed      plan-F1: walls= 55  thickness_mm={120: 28, 240: 27}
signed      plan-F2: walls= 53  thickness_mm={120: 28, 240: 25}
as-received plan-F1: walls= 54  thickness_mm={120: 27, 240: 27}
as-received plan-F2: walls= 53  thickness_mm={120: 28, 240: 25}
```

✅ 签字 `plan-F1` = **`{120: 28, 240: 27}` 共 55 堵**，与返工单要求逐字相同。
✅ 四个视图**都只有 120 与 240**，⛔ 100/296/300/304/356/360/364/500 一个都没有。

### ② `thickness == face_hi - face_lo` 逐条成立
`test_r2_every_wall_thickness_recomputes_from_its_two_stored_faces` 保留并通过；
且 `thickness` 是**两个已存整数的差**，比较是精确的，⛔ 没有容差可躲。

### ③ ⭐ 零幽灵
`face_line_ids_lo/hi` 现在是 `min_length=1`，**造不出**没有面线引用的墙 ⇒ 结构性成立。
四视图另有正向断言 `all(w.face_line_ids_lo and w.face_line_ids_hi)`。**⛔ 未触发停下上报。**

### ④ ⭐ 反空转（把配对改回 `wall_bands` 必须红）

```
旧源（wall_bands 映射，签字 plan-F1）: {100:1, 120:5, 240:7, 296:1, 300:16, 304:1, 356:1, 360:11, 364:1, 500:1}
  -> set(hist) - {120,240} 非空 ⇒ 同一条厚度断言在旧源上【红】
新源（面线配对，签字 plan-F1）      : {120: 28, 240: 27}          ⇒ 绿
```

⭐ 我把旧源的映射**留在测试文件里**（`_thicknesses_from_wall_bands_mm`，⛔ 不在 `src` 里），
它唯一的作用就是**证明这条验收能红**。
⭐ 另一个方向（更强）：跳过 D2 把 225 条全配对，同样红（见 §二）。

### ⑤ 上一轮验收八条 —— **逐条重跑重贴**（⛔ 没有写「同上一轮」）

**5.1 签字哈希逐位不变**（规范哈希 + 文件字节哈希，两半都贴）：

```
sm25 request   recomputed=d738d0ac230f21ae20f477b1cc084549f1308bff295a3f6de8956da98d25a135
sm24 request   recomputed=ae0fec087ef2a04814f3dbffc31553b25ea8e1c1d98eedf0b4ae383a7d4ac8a2
request.json (sm25)  e635ab116e21407734a093d2dc07194899a901d801d3d57624b3fa908d9396df
request.json (sm24)  34b7d74959e8a8c644d7082d952fddcf9a16bb9407c620ad1dfa303cff1e23b9
manifest.json(sm24)  4daca5539e77fe11521b5f14b45acf7cff321f99c1139457b7f625784ec289bc
sm25-L_t3.dxf        1251f65153829c9c4502e401b7962a22172e3b636732d4ddf91a40a7b049f8b9
..._as_received.dxf  4a94922489d391692da20a3b081511ab268d707fa7b61ae4413aae5268753245
```

✅ 与 ②-1a 交件里的**七个值逐位相同**；`git status --porcelain` 全程只有三个 ` M`，⛔ 签字件一个字节没被写过。

**5.2 as-received 跑通 + 与 F-129 吻合**：

```
drawing      view      faces  walls  open  wl_tot  nonorth  dangle  thickness_mm
as-received  plan-F1     222     54    31     223        1       4  {120: 27, 240: 27}
as-received  plan-F2     222     53    30     222        0       0  {120: 28, 240: 25}
signed       plan-F1     225     55    31     225        0       0  {120: 28, 240: 27}
signed       plan-F2     222     53    30     222        0       0  {120: 28, 240: 25}

SIGNED      plan-F1: targets= 110 opening_targets= 31 segments= 225 total_len_m=  282.28 faces_after_grouping=44
SIGNED      plan-F2: targets= 106 opening_targets= 30 segments= 222 total_len_m=  289.04 faces_after_grouping=44
AS-RECEIVED plan-F1: targets= 108 opening_targets= 31 segments= 223 total_len_m=  275.00 faces_after_grouping=44
AS-RECEIVED plan-F2: targets= 106 opening_targets= 30 segments= 222 total_len_m=  289.04 faces_after_grouping=44
```

✅ F-129 那组数**逐位未动**：F1 `110 → 108`、长度 `282.28 → 275.00`（差 7.28 m = 3.64 × 两面）、
**F2 两侧完全相同** ⇒ 五条手改线全在 1F。⛔ 不触发「对不上 ⇒ 停下上报」。
⭐ `walls` 一列是**本单唯一变的**（45/39/44/39 → 55/53/54/53），正是要变的那一列。

**5.3 逐位可复现，⛔ 未设 `PYTHONHASHSEED`**（三个全新进程，每次自报种子）：

```
PYTHONHASHSEED = <unset>
CODE_FROM=/workspaces/.../as_measured.py hash_randomization=True str_hash= 8144629022936378705 bytes=114392 sha256=c833adef1146ad5296b1b2a37dc400f4a7587df9d7d7d064f27ac24b686abdf1
CODE_FROM=/workspaces/.../as_measured.py hash_randomization=True str_hash= 3091929633164205918 bytes=114392 sha256=c833adef1146ad5296b1b2a37dc400f4a7587df9d7d7d064f27ac24b686abdf1
CODE_FROM=/workspaces/.../as_measured.py hash_randomization=True str_hash= 4686913375284636762 bytes=114392 sha256=c833adef1146ad5296b1b2a37dc400f4a7587df9d7d7d064f27ac24b686abdf1
```

三个种子互不相同 ⇒ 随机化确实开着，「三次相同」⛔ 不是恒真。

**5.4 反空转（内容 2 个方向 + 顺序 4 个缝 + 1 个新方向）**：

```
baseline                                  sha256=c833adef1146ad5296b1b2a37dc400f4a7587df9d7d7d064f27ac24b686abdf1
after moving ONE face line by 0.1 mm     sha256=00206194de68182eae878c71444c5613c753a46747294481f266235bd913a496   CHANGED=True
after moving ONE converter readout       sha256=ad1466ca7061a4a88738b7815125a0b98ff82550b1193444d4686f6b419b3f61   CHANGED=True
reversed-input order-independence (NO neuter): identical=True
neuter _face_line_sort_key    -> reversed input now DIFFERS: True  (must be True)
neuter _band_sort_key         -> reversed input now DIFFERS: True  (must be True)
neuter _opening_sort_key      -> reversed input now DIFFERS: True  (must be True)
neuter _sorted_handles        -> reversed input now DIFFERS: True  (must be True)
neuter _wall_sort_key         -> walls NO LONGER totally ordered: True  (must be True)
```

⚠️⚠️ **这里有一处我必须点名的口径变化，⛔ 不是我把测试改绿**：
`_wall_sort_key` **在「反转输入」这个方向上失去了牙**。原因是真的：②-1a 的 walls 直接来自
`geo.wall_bands` 的上游顺序，所以那把 sort 就是撑住可复现性的东西；现在 walls 来自
`face_line_targets`，**它自己已经 `sorted(groups.items())`** ⇒ 反转输入后墙序不变，
把 `_wall_sort_key` neuter 掉也不变 ⇒ 留在 `_ORDERING_SEAMS` 里那条测试会**诚实地红**。

⇒ 我做了两件事，⛔ 而不是删掉它：
1. `_ORDERING_SEAMS` 里换成 `_band_sort_key`（`geo.wall_bands` 仍按上游顺序送进来，
   探针会反转它 ⇒ 这个槽位的「反转」牙是**真的**，实测 neuter 后变红）；
2. `_wall_sort_key` 换到**它现在真正撑着的方向**去量 ——
   `test_r3_the_wall_sort_key_is_what_makes_walls_totally_ordered`：
   neuter 它 ⇒ **文档承诺的全序被破坏**（实测 True）。
   [[moving-a-gate-to-a-new-measurement-point]]：搬判据要把旧判据覆盖的形态重新问一遍。

**5.5 零 S7 依赖**（对模块源码 grep）：

```
$ grep -n "ZoneEdgeReportV1\|ZoneExpansion\|s7_expand_zones\|run_p2_conversion\|extract_gt_v3\|ZoneEdge" src/agent/judge/as_measured.py
(无输出)   grep exit=1  （1 = 零命中）
```

⚠️ 本单新增了 `from .as_drawn.denominator import MERGE_M, face_line_targets`，
我**专门核过它不违反 `judge/as_drawn` 的准入规矩**：`tests/test_gt_discipline.py` 那条**行为**门管的是
**`src.agent.pipeline` 的 import 闭包**，实测 `as_measured` **不在**该闭包里
（闭包里的 judge 模块只有 `judge / executor / retry / verdict`），改完后该测试仍绿。

**5.6 坐标全整数**（遍历整棵序列化树，⛔ 不是我挑的几个）：

```
floats outside converter_readouts' verbatim subtrees: 0  []
```

**5.7 / 5.8 numstat + 全量 + `.pth` 哨兵**：见 §五。

---

## 四、⭐⭐⭐ 返工审三条（⛔ 缺第三条不算做完）

| | 结论 | 证据 |
|---|---|---|
| ① 旧 commit `9977c26` 上病灶**复现得出** | ✅ | §一.1，四个视图全部长出幽灵厚度；签字 F1 十个厚度值与返工单逐个吻合。`CODE_FROM` 自证代码来自解出来的旧树 |
| ② 新 commit 上**复现不出** | ✅ | §三.① 四组直方图只含 120/240 |
| ③ ⭐⭐ **换同形输入仍走不通** | ✅ **三份输入，都过** | 下面三小节 |

### ③-a  as-received sm25（另一份图，同一栋楼）
`{120: 27, 240: 27}` / `{120: 28, 240: 25}` —— 只含真值。

### ③-b  ⭐⭐ sm24：**另一栋楼**（⚠️ 返工单说它会 BLOCK，实测**不会**）

```
request declares: sm24_source.dxf 92885d52340af72e views= ['plan-F1']
  source.dxf:     sha256=92885d52340af72e matches_request=True
  normalized.dxf: sha256=8416e908065989bf matches_request=False
  source.dxf plan-F1: walls=35 thickness_mm={120: 17, 240: 18}  ghosts=[]
  normalized.dxf: BLOCKED -> AsMeasuredUnavailable[upstream_identity_block] (BLOCK: tarch_input_source_hash_mismatch)
```

⇒ 返工单 §三 写「sm24 已知会 BLOCK（F-132 晋升件漂移）」。**实测不成立**：
请求书声明的 `source_dxf_label` 是 `sm24_source.dxf`、盘上文件叫 `source.dxf`，
**但身份门比的是字节哈希、不是文件名**，而字节是对的 ⇒ sm24 跑得通。
（真会 BLOCK 的是 `normalized.dxf`，那是另一份文件。）
⭐ 这是三份输入里**最强**的一份：sm24 完全没有被本单调过。
⭐ 而且它的 **17 堵 120 mm 隔墙全在** —— 正是本批指南 §一 那条「按声明厚度配对会把这一族静默丢掉」
所指的族，本单的配对没有任何厚度阈值，它们一个没丢。

### ③-c  ⭐⭐ 我自己造的合成夹具（**答案由构造决定**，⛔ 不是从产物读出来的）

10 × 6 m 房间、240 mm 外墙一圈、中间一堵 120 mm 隔墙、隔墙上开一樘门 ⇒
门把隔墙的两个面各切成两段 run，门洞两侧各有一条 **120 mm 长的 jamb cap**
（正是在 sm25 上造出 16 条「300 mm 墙」的那个形状）。

```
build_view(synthetic) -> thickness_mm == {120: 2, 240: 4}          （6 堵，构造时就知道）
                         face_lines_excluded_as_jamb_caps == ["C1","C2"]   （两条 jamb 被 D2 剔除）
                         face_lines_not_paired_into_a_wall == []
                         两段隔墙 run 的 along = (2400,20000) 与 (29000,57600)  ⇒ 没有跨门洞焊死
反方向（跳过 D2，全配对）-> 直方图出现 900 mm 的幽灵墙（两条 jamb cap 互相配对）
```

⭐ 这一份的价值和另外两份不同：它能**主动把陷阱摆进去**，所以它回答的是
「**这一类**缺陷修好了吗」，而不是「这个例子修好了吗」。
⛔ 两条断言都是**双向**的：正向证明真墙全出来了，反向证明**剔除**才是承重件。

---

## 五、numstat · 全量 · `.pth` 哨兵

**`git diff --numstat` 原文**：

```
116	41	src/agent/judge/as_drawn/denominator.py
291	56	src/agent/judge/as_measured.py
402	40	tests/test_as_measured_facts_layer.py
```

**两次全量汇总行原文**（⛔ 无 `-m`、⛔ 非 `-n auto`、⛔ 不看退出码）：

```
基线（5357db3 == 代码 9977c26，改动前）：
========== 3244 passed, 13 xfailed, 212 warnings in 934.76s (0:15:34) ==========

改动后：
========== 3253 passed, 13 xfailed, 212 warnings in 964.76s (0:16:04) ==========
```

**差值对账**：``3244 -> 3253`：**+9 passed, +0 xfailed, 0 failed**。`tests/test_as_measured_facts_layer.py` 单跑 = **45 passed**（本单前 36）⇒ **增量逐个对上**，⛔ 没有「顺手修好了别的红」或「顺手压住了别的红」。`

**`.pth` 哨兵（基线跑前 / 基线跑后 / 改动后跑前 / 改动后跑后，四次全同）**：

```
5198f6f9bf773d07373faa57a16e9564  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
a47a5925858b447ef52e3461fd6543e8  /opt/venv/lib/python3.12/site-packages/_virtualenv.pth
c767f0a08a993aec12f4a381d492dca2  /opt/venv/lib/python3.12/site-packages/sphinxcontrib_jsmath-1.0.1-py3.7-nspkg.pth
```

⛔ 全程没有 `pip install -e .`，没有任何写 `site-packages` 的命令。
⛔ 两次全量**跑测期间都没有动树**（本记录是跑完之后才写的）。

⭐ **顺带补做一件返工单没要求、但 [[upstream-change-voids-the-earlier-sweep]] 要求的事**：
`merge_m` 原本只决定**计分目标**，现在它同时决定**一堵墙被切成几段** ⇒ **旧的那次扫描不覆盖新用途**。
重扫（签字件）：

```
  signed plan-F1 merge_m=0.40/0.50/0.60/0.70/0.80: walls=55, {120: 28, 240: 27}   （五档全同）
  signed plan-F2 merge_m=0.40/0.50/0.60/0.70/0.80: walls=53, {120: 28, 240: 25}   （五档全同）
```

⇒ 洞口门 + 墙落点门把它托平了，`merge_m` 在新用途上**同样不承重**。⛔ 这是量出来的，不是推出来的。

---

## 六、我认为题面错 / 不全的地方

### 1 ⚠️ **`sm24 已知会 BLOCK（F-132 晋升件漂移）` —— 实测不成立**（对我们有利）

见 §四.③-b。身份门比**字节哈希**、不比文件名，`source.dxf` 的字节是对的 ⇒ sm24 跑得通，
`{120: 17, 240: 18}`、零幽灵。⇒ 返工审第三条拿到了**一栋完全没被本单碰过的楼**做证据，
比返工单预备的退路（as-received + 合成夹具）强。**建议登记为派工方题错 #46。**

### 2 ⚠️ **R1 有一个没预见到的必然后果：洞口的 carrier 全部失效**

见 §二末尾。返工单只说了「walls 改从面线配对」，没说这会让**洞口不再落在任何一段墙里面**
（D4 从不跨洞口合并 ⇒ 洞口在两段 run 之间）。按原 schema 跑，31/30/31/30 个洞口**全部**变
`ambiguous`。我按实测结构改成了复数引用并加了断言，**但这是我替口径做的一次裁断，请复核**。
**建议登记为 #47。**

### 3 ⚠️ 一处措辞会把人带偏（不影响结论）

返工单写「参考实现仓库已有（**`denominator()` 用的就是它**，全天诊断也在用）」。
⛔ 严格说 `denominator()` **并不配对** —— 它只产出面线 target；那套「同轴+重叠+最近」的配对
实际躺在 `AI_agent/logs/experiments/2026-08-29_gt_consistency_preview/consistency_probe.py::walls()`。
照字面去 `denominator.py` 里找配对代码是找不到的。⇒ **能复用的是【剔除+分组+合并】，配对要照探针写。**
我按这个理解做的：剔除复用（抽成共享纯函数），配对按探针的规则实现在事实层。

### 4 ✅ §六 那条「引用标识符前先查定义」我照做了
`face_line_ids_lo/hi`、`WallBand.band_id`、`ResolvedOpening.cross_section_mm`、`Affine2D` 的六个系数
都是先 `grep` 定义再引用的；本轮**没有**出现凭记忆写字段名的情况。

---

## 七、§五 那个开放问题 —— 我的判断：**不冲突**（⛔ 但理由和派工方给的不完全一样）

**结论：不冲突，⛔ 不触发停下上报。**

**⛔ 我不接受「gt 侧输入是 DXF、实体与图层都是确定的」这个理由本身。**
它不够：②-1a 的幽灵墙**也**是在确定性的 DXF 上产生的，照样凭空造出 33 堵墙。
**输入是确定的，并不使一个推导是对的** —— 这正是让 ②-1a 过关的那种推理。

**真正让它安全的是【外部可核对】，不是【输入确定】**：

1. **立那条口径的实证是什么** —— sm24 上「**按声明厚度**配对」把整批 120 mm 隔墙静默丢了。
   被禁的是**那个机制**：拿厚度当筛子。
2. **本单的配对里没有那个机制** —— 一个厚度阈值都没有；替代物是结构性的
   「每条面线只被它最近的、有重叠的对面消费一次」。
3. ⭐ **而且我能在【立规则的那个案子本身】上给出反证**：sm24 现在跑出 **17 堵 120 mm 隔墙，一堵没丢**
   （§四.③-b）。⇒ 那条口径所防的失效**在这里没有发生**，这是实测，不是援引权威。
4. **口径管的是「谁来答」，而 gt 是【标准答案】** —— 若 gt 对「哪两条线是一堵墙」没有意见，
   reading 的配对就**无从判分**。所以 gt 必须有一个配对；「归模型」只能是指
   **reading 那条道**上不许由代码把配对塞给模型、且模型有权「认不出来」。

**⚠️ 但这个「不冲突」是有条件的，请连条件一起收下**：
它成立，是因为 gt 侧的配对**今天是可被外部事实证伪的** —— 厚度直方图对着原图真有的墙族、
消费台账、以及换一栋楼（sm24）复现。**这三样是【现有检查】的性质，不是定理。**
⇒ 若日后有人削弱它们（比如把厚度直方图那条验收去掉），
gt 就变成一个**没人能证伪的**配对意见，而 reading 要照它扣分 —— **那时冲突是真的**。
⇒ 建议把「厚度直方图 + 消费台账 + 第二栋楼」写成 gt 侧配对的**准入条件**，而不是本单的一次性验收。

---

## 八、我没做到的（如实）

1. ⛔ **`as_measured.json` 仍然没有作为文件落进 `gt/`** —— 归 ②-1b（返工单 §四 明令不做）。
2. ⛔ **B1 转换器实现指纹仍是显式 `None`** —— 归 ②-1b。
3. ⛔ **没有把 reading 判分器改读事实层** —— 事实层落库之后的下游接线，不在本单。
4. ⛔ `revisions` / `as_signed` / `AnswerCompiler` / 出模形式 / `boundary_condition` —— §四 明令不做，**未做**。
5. ⚠️ **`face_lo`/`face_hi` 存的是 1 mm 组坐标而不是笔画的 0.1 mm**（§二）。
   我给了理由、留了 handle 引用、把不一致的组点了名，**但这仍是一次口径裁断，我没有权限终审**。
6. ⚠️ **`carrier_wall_id` → `carrier_wall_ids` 是我替口径做的裁断**（§二末尾、§六.2）。
   实测四个视图恒为「恰好 2 段、同一 face-pair」，但**「恰好 2」是这四个视图的性质**，
   ⛔ 不是我证明过的定理；换一张图若出现 3 段（一堵墙上两樘挨着的门），断言会红 ——
   **那是我希望的行为**（红总比静默好），但请知悉。
7. ⚠️ **只在 sm25（两图两视图）+ sm24（1 个视图）+ 1 份合成夹具上验过。** sm21 没有 `request.json`，未验。
8. ⚠️ **`face_line_targets` 的抽取我只证明了「四个夹具上输出逐字段相同」**，
   ⛔ 没有证明它在所有可能输入上等价（例如退化线段：四个夹具的 `degenerate_in_wall_lines` 实测全是 0，
   ⇒ **这条路本轮没有被走到**，属于 [[two-kinds-of-latency-no-ruler-vs-never-reached]] 的第二种潜伏）。

---

## ⭐ 主控权威全量 + 独立复核（orchestrator，2026-08-29）

```
========== 3253 passed, 13 xfailed, 212 warnings in 969.15s (0:16:09) ==========
EXIT=0    (-n 6，⛔ 无 -m)
.pth 前后哨兵 ✅ 完全相同 · HEAD 跑前跑后同为 af7c64d · 工作树全程 0 脏路径
算术 3244(基线) + 9(新测试) = 3253 ✅
```

**独立复现（⛔ 未采信执行记录任何自述）**：四组厚度直方图逐字相同 ·
签字哈希 `d738d0ac…`/`ae0fec08…` 逐位不变 · `denominator` plan-F1 仍 110 目标 ·
sm24 用 `source.dxf`（字节匹配 `92885d52…`）跑通、`{120:17, 240:18}` 零幽灵 ·
31 个洞口全部各引 2 堵墙且均为同一对面线的两段。

## ⚠️ orchestrator 自认与采纳

1. **题错 #46**：返工单写「sm24 已知会 BLOCK（F-132）」是**错的**。那道门**按字节哈希**，
   `source.dxf` 正好匹配；BLOCK 的是 `normalized.dxf`。⇒ 返工审第三条因此拿到了一栋**真正的第二栋楼**。
   ⭐ 且其 **17 堵 120 隔墙全部找回** —— 那正是「配对归模型」口径的原始案例（代码按声明厚度配对丢光它们）。
2. ⭐⭐⭐ **施工方驳回了 orchestrator 在返工单 §五 给的理由，orchestrator 采纳其措辞。**
   原理由「gt 侧安全，因为 DXF 输入是确定的」**不充分** —— ②-1a 也是在确定的 DXF 上产出 33 条虚构墙。
   真正让它安全的是 gt 配对**在外部可证伪**（厚度直方图对原图真实墙型 + 消费对账 + 第二栋楼），
   而**那是当前这些检查的性质、不是一条定理**。
   ⇒ **建议采纳**：把这三样定成 gt 侧确定性配对的**准入条件**，⛔ 不是这一次的验收项。
3. **#47 复数承载墙**：✅ 同意（二选一等于偷设一个没人签字的选择）。
   ⭐ 根治是「墙段→墙线」合并（那两段本就是同一堵墙），归 **②-1c**。
4. ⏳ **`face_lo/face_hi` 存 1 mm 分组坐标**：**先不签** —— 与用户 08-29「坐标存 0.1 mm 整数」有张力，
   已点名进跨家族复核请求书。
