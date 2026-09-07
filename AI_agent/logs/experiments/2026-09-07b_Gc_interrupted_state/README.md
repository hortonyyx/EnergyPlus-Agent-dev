# G-c 施工席位撞月度上限中断 —— 落地状态与接手指南

> **档位 = 探索档**。本文是**主控实测的状态档**，⛔ 不是交件（交件席位没来得及写）。
> **分支 `09.07_Gc_snap_ladder`（工作树 `/tmp/gc_snap_ladder`）⛔ 未合并、⛔ 不绿。**

## 0. 一句话

**8 段提交全部落库、工作树干净、零孤儿件**；全量 **`6 failed / 4003 passed / 2 skipped / 13 xfailed`**。
6 条红**全在席位没动过的文件里**，且**分成三类，其中一类是一笔早就登记过、这次正好到期的债**。

## 1. 中断的情形

| | |
|---|---|
| 席位 | Claude 施工（主控 2026-09-07 派出，单号 [G-c](../../reviews/request/2026-09-07a_Gc_snap_ladder_dispatch.md)）|
| 结束方式 | **撞月度支出上限**（`rate_limit / HTTP 429`），⛔ 非它自己判断做完了 |
| 中断时它在做什么 | 自述最后一句：「6 remaining failures in other files. Let me diagnose each.」|
| **未提交半成品** | ⭐ **零**（`git status` 干净）—— **分段提交纪律第四次兑现** |
| 交件 | ⛔ **没写**（`2026-09-07a_Gc_snap_ladder_execution.md` 不存在）|

⇒ ⭐ 按 [CLAUDE.md §5#8.7](../../../CLAUDE.md) 收到席位失败先 `git status`（含 worktree）——**做了，结果是零丢失**。

## 2. 它落库了什么（8 段，⚠️ **提交信息是它的自述，主控只核过改动面与测试读数，⛔ 未逐行审 diff**）

```
f2188df5  台账清零后，四条靠「台账里有记录」立着的锁改用自造存货
8fb770a9  阶梯把这份锁的唯一负样本修好了 ⇒ 重建负样本，⛔ 不是删锁
c893c5ef  facts 层锁重推 + A-11-d3 与档 2 台账的合成夹具
b068bc8a  11 条毫米门锁按阶梯重新推导 + 四档合成夹具（⛔ 零删除、零降级）
161e5f61  两个 case 的 facts 三件套重出（sm25 台账清零、sm24 只是序列化变了）
d9d859e0  补上锚端规则的另一半 —— 端点被移动，共用它的笔画要跟着走
b5c62bf0  补上 A-11 漏掉的同族豁免 + 档 2 仲裁台账
9f9f2ae7  S1 换成用户定的四档阶梯 + 锚端规则（10mm 作废、1°→5°）
```

**改动面（主控实测 `git diff --numstat`）**：源码 2 个文件
（`tarch_normalize.py` **+597/−180** · `as_measured.py` **+192/−8**）· 测试 4 个文件 ·
两个 case 的三件套 · 一个重出脚本。**净增测试约 20 条**（`4003+6+2+13 = 4024` vs 基线 `4004`）。

⭐ **`d9d859e0` 那一段是它自己发现的补漏**：主控的设计只写到「锚哪一端」，
**没写「转平之后，共用那个端点的笔画怎么办」**。若 diff 属实，这是派工单的一个真缺口。

## 3. ⭐⭐⭐ 6 条红的分类（**主控自己跑出来的断言原文**，⛔ 非转引席位自述）

### 类 A · **存货被这次修复消灭了**（3 条）—— 预期内，但⛔ 修法不是改期望值

| 测试 | 断言 | 为什么 |
|---|---|---|
| `test_answer_compiler_profiles.py:62` | `assert set() >= {'rev-13ad','rev-13ae','rev-13af'}` | **台账清零了** ⇒ 这三条 revision 不再存在。该锁靠「台账里有这三条」立着 |
| `test_as_drawn_denominator_f126.py:260` | `assert set() == {'tarch_wall_free_end'}` | **13AF 成了面线** ⇒ 那堵墙不再有自由端 ⇒ 该诊断消失 |
| `test_a11_gt_1mm_ingest_resolution.py:295` | `identity strings moved` | 三件套重出 ⇒ 身份串变了 |

⭐ 这一类**正是 [[gate-teeth-direction-follows-fixture-inventory]] 的形状：存货是【检查形态】的函数，不是给定的。**
⛔ **修法不是把期望值改成新数字**，而是**给这些锁重建负样本**——
席位在它动过的 4 个文件里已经这么做了（`8fb770a9` 的提交信息逐字写着
「阶梯把这份锁的唯一负样本修好了 ⇒ **重建负样本，⛔ 不是删锁**」），
**这 3 条只是它还没走到的同一件事。**

### 类 B · ⭐⭐⭐ **`SM25_DEFERRED_CAVITY_COUNT` 从 4 掉到 2** —— **A-11-d2 这笔债正好在这次到期**（2 条）

| 测试 | 断言 |
|---|---|
| `test_f156_ring_from_intersection.py:107` | `assert len(deferred) == SM25_DEFERRED_CAVITY_COUNT` ⇒ `assert 2 == 4` |
| `test_boundary_condition_facts.py:143` | 同一个常数，同一个断言 ⇒ `assert 2 == 4` |

⛔⛔ **这不是「期望值过期了」，这是一笔【写明过硬排期约束的债】被跨过去了。**
`SM25_DEFERRED_CAVITY_COUNT = 4` 的构成是 **`2 × F-157` + `2 × F-153 form B`**，
而 A-11 合并时（2026-09-06）已经**用独立反例坐实它是代理量**并写下约束：

> **硬排期约束：下一次任一成因（F-157 / F-153 form B）单独发生变化【之前】**，
> 必须先拆成 per-code 两个钉，且**拆分必须同时 touch 两个消费者文件**。

⇒ **这次没有先拆。** 于是现在 **从数字上看不出是哪一支变了**：
是那 2 个 F-153 form B 被阶梯修好了？还是 2 个 F-157？还是各修一个？
⭐ **这正是当初判它是代理量时预言的失效方式**（[[proxy-mistaken-for-the-thing]]）。

⇒ ⭐⭐⭐ **接手第一件事 = 先把这个常数拆成 per-code 两个钉，再看 4→2 是哪一支**，
⛔ **不许直接把 4 改成 2**（那等于把这次变化永久吞掉，且下一次同样看不见）。
⭐ **拆完之后才谈得上判断这 2 条是「修好了」还是「回归」** —— 主控**尚未判定**，⛔ 不要读成已判。

### 类 C · **基线数要重新推导**（1 条）

`test_a11_gt_1mm_ingest_resolution.py:220`：`face_lines: 48 != dispatch baseline 46`。
13AF 现在成了面线 ⇒ 该扫描的面线桶基线要按阶梯重新推导。
⛔ 同类 A 的纪律：**重新推导它钉的是什么**，⛔ 不是把 46 改成 48 了事。

## 4. 接手指南（下一程）

1. **⛔ 不要合并这条分支** —— 它不绿。
2. **第一件事 = 拆 `SM25_DEFERRED_CAVITY_COUNT`**（类 B），⛔ 不是修那 6 条红。
3. 类 A / 类 C 的 4 条：**按「重建负样本 / 重新推导钉什么」处理**，
   ⛔ 不许改期望值了事、⛔ 不许删或降级。
4. 全量绿之后才谈交件与跨家族复核（**复核仍派 GLM**，用户 2026-09-07 指定）。
5. ⚠️ **主控尚未逐行审过这 8 段 diff** —— 复核前主控要先自己过一遍
   （[CLAUDE.md §5#8](../../../CLAUDE.md)：施工席自述一律以 `git diff` 为准）。

## 5. 复现命令

```sh
cd /tmp/gc_snap_ladder
python -c "import src.agent.judge.tarch_normalize as a; print(a.__file__)"   # 必须落在 /tmp/gc_snap_ladder
python -m pytest -q -n 6 -p no:cacheprovider                                  # 6 failed / 4003 passed
```

⚠️ 若工作树已被清掉：`git worktree add /tmp/gc_snap_ladder 09.07_Gc_snap_ladder`（分支仍在）。
