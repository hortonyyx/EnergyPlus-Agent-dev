# 裁决书 · 拆 `SM25_DEFERRED_CAVITY_COUNT` 为 per-cause 两个钉（GLM 家族跨家族复核）

**APPROVE-WITH-FINDINGS · 阻断 0 · 不阻断 3**

- **复核方**：GLM 家族 · **被审 commit**：`883d4e51`（单段提交，改动面 `tests/` 三文件 `+97/−14`）· **工作目录**：`/tmp/split_pin_review_glm`
- **复核单**：`AI_agent/logs/reviews/request/2026-09-07b_split_deferred_pin_crossreview.md`
- **施工方**：Claude 家族 orchestrator 本人（主控自改，用户 2026-09-07 当场授权）
- **必读三件**（复核单 + 立债裁决书 `2026-09-05l` + G-c 中断状态档）均按主树绝对路径读过。

---

## 头条结论

**A-11-d2 这笔债被如约清偿，且清偿动作与立债裁决书给出的机械处方逐项吻合**：
拆成 per-code 两个钉、总数改派生、两个消费者文件各自加上 per-cause 断言、
未删未降级任何既有断言。三条复核（基线复现 / 改动后红且指名 / 自造构成矩阵）全部独立通过；
§三 四问逐条**量的**（不是转引施工方推理）；**§四 的对称差被直接量出来 = 0.000000**，
主控「真退休、非回归」的判断没有被证伪，反而从「推」升级成「量」——管理文档不需要改。

头号提问「它验的是哪一半」的答案：**施工方自测的三种构成（2+2/3+1/2+0）都是「数据侧动、钉不动」的半边**；
我补上了另外两个半边——「钉侧动、数据不动」（钉漂移方向，880 格枚举，有牙）与
「数据与钉都没动但身份动了」（计数锁的固有边界，见不阻断-2，非洞）。

---

## 自检（§〇）

```
$ cd /tmp/split_pin_review_glm && git log --oneline -1
883d4e51 09.07g_split_deferred_pin: 拆 SM25_DEFERRED_CAVITY_COUNT 为 per-cause 两个钉（A-11-d2 到期）
$ python -c "import tests.deferred_projection_ledger as m; print(m.__file__)"
/tmp/split_pin_review_glm/tests/deferred_projection_ledger.py     # ⭐ 落在本树
```
全量跑完后再核一次 `__file__`，仍落本树（见「全量读数」）。未跑任何写 `site-packages` 的命令；跑测一律 `-n 6`。

## 是否改过被审对象（如实披露）

- §三-4 的「临时改钉」五个变异按复核单建议的方法**临时**改 `tests/deferred_projection_ledger.py`
  的常量值、每个变异跑完即还原，全部变异结束后 `git status --short` 与 `git diff --stat` 均为空。
- 基线复现用独立 worktree `/tmp/split_pin_base_check`（`git worktree add --detach 883d4e51^`），
  复核结束后已 `git worktree remove` 清理（worktree 清单已确认不在）。
- `/tmp/gc_snap_ladder` 全程**只读**（只跑 python 复刻脚本，零写入；HEAD 仍 `f2188df5`）。
- 主树 `/workspaces/EnergyPlus-Agent-dev` 只写本裁决书这一份文件。

---

## §二-1 改动前复现得出 ✅（在 `883d4e51^` 上，旧钉确实不红）

方法：先在本树真实跑 `reconcile_boundary_basis` 校准 failure 串的**真实生产者格式**
（`code:view:cavity:<hash>[:zone:symdiff]`，四条原始串全部拿到），再按构成拼装 `FakeAudit`
（`pairings/paired_edges/rows/exclusions` 等补齐使**非钉断言全绿**），
monkeypatch 两个消费者模块的 `reconcile_boundary_basis`，**直接调用两个真实测试函数**
（比「消费者所用的断言形式」更强的形态）：

```
基线 883d4e51^（/tmp/split_pin_base_check，import 校验落该树）：
  2+2 基准     : test_f156... GREEN    test_boundary... GREEN
  3+1 (反例)   : test_f156... GREEN    test_boundary... GREEN    ⭐ 旧钉不红
  1+3 (互换)   : test_f156... GREEN    test_boundary... GREEN
  0+4 (总数不变): test_f156... GREEN   test_boundary... GREEN
  2+0         : RED @test_f156:107 / test_boundary:143（总数行——旧钉唯一可见的方向）
  2+2+第三code : RED @failures_not_from 行（零阈值半边）

旧钉函数直读：
  3+1: len(deferred_cavities)=4  ==SM25_DEFERRED_CAVITY_COUNT(4)? True   failures_not_from == []?
```

**缺陷确实存在，不是被描述出来的**：`3×F-157 + 1×F-153B` 下旧世界两个消费者测试**通过**。

## §二-2 改动后复现不出 ✅（同一构成在 `883d4e51` 上红、且指名哪一支）

```
本树 883d4e51，同一注入：
  3+1 : RED @test_f156_ring_from_intersection.py:117 -> assert (len(deferred_cavities_by_code(audit, F157_UNAVAILABLE_CODE))
        RED @test_boundary_condition_facts.py:154     -> assert (len(_deferred_cavities_by_code(audit, F157_UNAVAILABLE_CODE))
  1+3 : 同上（红行相同）
  0+4 : 同上
```
红行表达式里带着 `F157_UNAVAILABLE_CODE / SM25_DEFERRED_F157_UNAVAILABLE_COUNT` —— **指名是哪一支**。
F153B 行（f156:119 / bcf:156）单独红由跨 code 重叠形态补证（格 15b）：
`b=2,c=3,d=1` 时总数对、F157 对、F153B 错 ⇒ RED @f156:119 / bcf:156（`F153_FORM_B_CODE` 行）。
**三个钉各自的红都有测试级证据**：A 行（格 4/5）、B 行（格 2/3/9/10）、C 行（格 15b）。

## §二-3 自造构成矩阵（18 格 + 钉漂移枚举，⛔ 不止复核单给的三种）

函数级（A=总数钉，B=F157 钉，C=F153B 钉，D=零阈值半边 `failures_not_from_deferred_cavities==[]`）：

| # | 构成 | A | B | C | D | 判 |
|---|---|---|---|---|---|---|
| 1 | 2+2 基准（真实构成） | 绿 | 绿 | 绿 | 绿 | 基准 |
| 2 | 3+1（裁决书反例） | **绿** | 红 | 红 | 绿 | ⭐ 总数钉瞎的方向被 B/C 接住、指名 |
| 3 | 1+3（总数不变双向互换） | **绿** | 红 | 红 | 绿 | 同上 |
| 4 | 2+0（一支归零另一支不变） | 红 | 绿 | 红 | 绿 | 指名 F153B |
| 5 | 0+2（镜像） | 红 | 红 | 绿 | 绿 | 指名 F157 |
| 6 | 4+4（两支同向增加） | 红 | 红 | 红 | 绿 | |
| 7 | 1+1（两支同向减少） | 红 | 红 | 红 | 绿 | |
| 8 | 0+0（两支全零） | 红 | 红 | 红 | 绿 | |
| 9 | 0+4（一支吃掉另一支，总数不变） | **绿** | 红 | 红 | 绿 | ⭐ 最阴格：总数完全不红 |
| 10 | 4+0（镜像） | **绿** | 红 | 红 | 绿 | |
| 11 | 2+5（单支增加） | 红 | 绿 | 红 | 绿 | |
| 12 | 5+2（镜像） | 红 | 红 | 绿 | 绿 | |
| 13 | 2+2+第三 code×1 | 绿 | 绿 | 绿 | **红** | 由 amnesty 半边接住（不阻断-1） |
| 14 | 2+2+KNOWN_DEFECT×1 | 绿 | 绿 | 绿 | 绿 | 归 o21d 锁，声明范围外 |
| 15 | 跨 code 重叠（2+2 其中 1 对同 identity） | **红** | 绿 | 绿 | 绿 | 并集去重 ⇒ A 响亮红（§三-2） |
| 15b | b=2,c=3,d=1（总数对、C 错） | 绿 | 绿 | **红** | 绿 | C 行单独红的补证 |
| 16 | 同支重复串（F157 两条同 identity）+2 | 红 | 红 | 绿 | 绿 | 集合语义，旧版同样去重 |
| 17 | F157 延伸 code（`_unavailable_extra`）+2+2 | 红 | 红 | 绿 | 绿 | startswith 前缀语义，旧版同样计入 |
| 18 | 身份迁移（2+2 但 F153B 两个 hash 换人） | 绿 | 绿 | 绿 | 绿 | 计数锁不锁身份（不阻断-2） |

「cause 构成变了而**全部断言**绿」的格子：**0 个**（格 14 是别的锁的声明范围、格 18 不是 cause 构成变化）。
字面上「三个钉全绿」的格子有两个（13、18），逐个交代于不阻断-1 / 不阻断-2。

复核单清单（§二-3 要求的六种）全覆盖：同增=格 6、同减=格 7、一支归零另一支不变=格 4/5、
总数不变双向互换=格 2/3（外加更阴的 9/10）、两支全零=格 8、第三 code=格 13。
**清单之外我补的形态**：钉漂移方向（数据×钉 880 格枚举，§三-1）、跨 code 重叠（15/15b）、
同支重复（16）、code 延伸（17）、段数不足病态串（两版同样 IndexError，非本单引入）、拼错 code 查询（§三-3）。

---

## §三 四问逐条作答（每条注明：量 / 推）

### 1. 总数从字面量改派生——削弱了吗？【量的】

**不削弱，实测 + 枚举双重确认**：
- **实测「钉被改错」场景**（施工方自述的推理「会被 per-code 断言自己接住」，复核单要求别转引、要实测）：
  临时把钉改成 `F157=3 + F153B=1`（数据仍 2+2，派生总数恰仍 4）⇒ 两个消费者各红 1 条，
  红在 **F157 per-code 行**，pytest assert-rewrite 原文：
  `AssertionError: assert 2 == 3 + where 2 = len({('plan-F1','cavity:8bd127719198fd63'), ('plan-F2','cavity:495501ce9b36f0f3')})`。
  钉改成 `0+4` 同样红在 F157 行（`assert 2 == 0`）。**施工方的推理这次量出来是对的**。
- **枚举**：数据 `(b,c,d∈重叠)` ∈ 0..4 三维，钉 15 种组合，共 **880 格**。「旧红 ∧ 新全绿」
  （= 削弱的定义）出现的 8 个格子**全部是钉与数据逐支相等的格子**（`0+0/0+2/1+1/2+0/2+3/3+2/3+3/4+4`
  且钉=数据）——那是 readout 的**合法更新**（docstring 原话「update them here, once, in the same
  commit as the fix」），旧世界在这些格红只因旧钉 4 未跟着改。**不存在「数据变了而新锁全绿」的削弱格**。
- 反向（拆分的价值，量出来）：数据 3+1/1+3/0+4/4+0 钉 2+2 ⇒ 旧绿、新红。
- 数学旁注（**推**，与枚举互证）：新全绿 ⇒ `b=B钉 ∧ c=C钉 ∧ b+c−d=B钉+C钉`，严格强于旧全绿
  （只要求 `b+c−d=4`）。

### 2. `deferred_cavities()` 求并——语义变了没有？【量的】

**逐位相同**。旧版模块源码 `exec` 进独立命名空间，对 **26 种输入**（真实 audit + 16 种计数组合 +
空 + 跨 code 重叠 + 同支重复 + 第三 code + KNOWN_DEFECT + 非 cavity 段格式 + occupies_multiple +
大写变体 + mismatch 串）逐位比较 `deferred_cavities` 与 `failures_not_from_deferred_cavities`
两版输出：**0 不一致**。段数不足串两版同样 `IndexError`（非本单引入）。
- **去重**：跨 code 重叠（格 15）实测 A 红（3≠4）、B/C 绿——**响亮的失败，不是洞**。三个理由：
  ① 旧版在同一输入上同样 `len=3≠4` 红（上述等价实验覆盖此输入），**不是本单引入的行为**；
  ② 生产者路径上两个 code 对同一 cavity **结构互斥**（`answer_compiler.py:1364-1369` unavailable
  分支 `continue` 在对称差比较之前，同一 cavity 不可能同时产出两条 code），跨 code 同 identity
  意味着矛盾数据，红了正确；③ 红的读数恰好暴露「重叠」本身（总数与分项之差）。
  施工方问「有意保留的响亮失败还是没想到的洞」——判：**不是洞**（无论是否有意，行为正确且与旧版一致）。
- **前缀污染**：`DEFERRED_PROJECTION_CODES` 两个 distinct code 互不为前缀（机械两两检查 False）。
  F157/F153B 两个常量的值就是元组内那两个串（我检查脚本里报的 4 条 ⚠ 是列表未去重导致的
  重复元素自反命中，不是前缀对——如实说明）。

### 3. `deferred_cavities_by_code` 的 ValueError 守卫必要吗？【量的】

**必要，不是多余防御**。实测三件：
- 拼错 code（`converter→convertor`）：有守卫 ⇒ `ValueError`，消息指名声明点在 `DEFERRED_PROJECTION_CODES`；
- 同一查询在**去掉守卫的进程内副本**上 ⇒ 静默返回 `set()`；
- ⭐ 关键形态：**某支退休、钉更新为 0 之后**，拼错 code 的查询 `len(set())==0 == 0` ⇒ **静默绿**。
  复核单的反论证「返回空集 ⇒ 0 != 2 ⇒ 本来就会红」只在钉 >0 时成立；钉=0 的支
  （正是 G-c 即将带来的终态 `0+2`）上反论证失效。守卫把「查询了声明表外的 code」从计数巧合
  变成结构错误。判：**保留正确**，它让失败**可读**的同时也挡住了一种**可发生的静默 0**。

### 4. 两个消费者的断言真的被执行到了吗？【量的】

五个临时变异（⛔ 不靠「测试绿了」证明；改后即还原，`git status --short` / `git diff --stat` 均空）：

| 变异 | 结果（两个消费者测试各红 1 条） |
|---|---|
| 钉 B（F157）2→3 | RED @总数行 `assert 4 == 5`（两文件） |
| 钉 C（F153B）2→5 | RED @总数行 `assert 4 == 7`（两文件） |
| 钉 A 派生→独立字面量 7 | RED @总数行 `assert 4 == 7`（两文件） |
| 钉 B=3 且 C=1（派生总数恰=4） | RED @**F157 per-code 行**（两文件），`where` 子句给出 per-code 集合 |
| 钉 B=0 且 C=4（同上） | RED @F157 per-code 行 `assert 2 == 0`（两文件） |

- **A 行（总数断言）被执行**：前三个变异证明——红在预期文件的预期行。
- **B 行（F157 断言）被执行**：第四/五个变异证明——总数巧合对上时恰好红在 B 行。
- **C 行（F153B 断言）被执行**：格 15b 注入证明——RED @f156:119 / bcf:156（`F153_FORM_B_CODE` 行）。
- 附带发现（不阻断-3）：派生结构下**单独**改任何一个 per-code 钉会先红在总数行——
  信号没丢，但「哪一支」的直接指名只在总数恰好对上时出现在 per-code 行。

**消费者清单机械核实**：全仓 `grep` 这些名字的消费者**恰好两个文件**（第四个命中
`AI_agent/logs/experiments/2026-09-01c_.../rebuild_sm25_facts_staging.py` 是同名**局部变量**，
非 import）——「拆分必须 touch 两个消费者」的约束没有被第三处遗漏。

---

## §四 证伪「F-153 form B 真退休」——直接量对称差【量的】

前提钉死：两树 `src/agent/judge/answer_compiler.py` **逐字节相同**（`diff -q` IDENTICAL；
G-c 的源码改动只在 `as_measured.py` / `tarch_normalize.py`，与中断档记载相符）——两树对比是纯输入侧差异。

在 `/tmp/gc_snap_ladder`（分支 `09.07_Gc_snap_ladder`，HEAD `f2188df5`，只读）上，
逐行复刻 `answer_compiler.py:1312-1377` 的生产者定义（同一 `_projected_facts_ring`、同一
`_world_point_to_ingest_grid`、同 `zone.polygon_m.exterior.vertices` 来源、同 occupied/covers
配对路径），对**每个 cavity** 直接算 `projected.symmetric_difference(zone_polygon).area`：

- **G-c 树**：`F1-z5`（cavity:59e1722cb0…）= **0.000000**；`F1-z4`（cavity:d512e5edea…）= **0.000000**；
  其余全部 cavity 也是 0；两个 F-157 cavity 仍是 `adjacent_projected_support_lines_are_parallel`
  （投影不可得）。该树 audit 只剩 2 条 F-157（`8bd127719198fd63` plan-F1 + `495501ce9b36f0f3`
  plan-F2），pairings=27 / paired_edges=108 / accounted 29/29 / exclusions=[]。
- **复刻自证**（⛔ [[recompute-gate-must-mirror-producer-definition]]：复刻若走样，量出的 0 不算数）：
  同一把尺子在**主树 `883d4e51`** 上量出 `F1-z4/z5 = 1182000.000000`，与生产者写进 failure 行的
  `symmetric_difference_units2=1182000` **逐位一致**——复刻若错，不可能恰好量出这个数。
  同一复刻在 G-c 树上量出 0。

**判定：主控的结论成立，未被证伪。** 对称差精确等于 0（不是「行没出 ⇒ 推差为 0」）。
附带交叉验证：G-c 树上 z4/z5 的 cavity hash 与主树不同（三件套重出、内容哈希变了），
与复核单证据链「F1-z4/F1-z5 仍在 pairings 里」相容（pairings 是 zone 级）。

---

## §五 停报条件核对（均未命中）

1. `__file__` 落点 ✅ 本树。
2. 构成清单外延：我**扩了**五种形态（钉漂移、跨 code 重叠、同支重复、code 延伸、身份迁移），
   全部实测、无一成为洞——清单可扩但**不是错的**（其六种必覆盖形态全被接住），不构成停报。
3. 题面：债到期属实（G-c 已让 F153B 支 2→0 而主线仍是 2+2；主树真实 audit 校准确认
   `2×_is_not_the_converter_zone + 2×_unavailable`），拆法与立债裁决书的机械处方一致。题面成立。
4. §四 判断未被推翻（量出 0.000000）。
5. 全量红：见下节——0 failed，无无法归因的红。

---

## 全量读数

```
$ python -m pytest -q -n 6 -p no:cacheprovider        # 于 /tmp/split_pin_review_glm（883d4e51）
3989 passed, 2 skipped, 13 xfailed, 211 warnings in 490.82s (0:08:10)      (exit 0)

$ python -c "import tests.deferred_projection_ledger as m; print(m.__file__)"   # 跑后复核
/tmp/split_pin_review_glm/tests/deferred_projection_ledger.py
```

与主控参照读数（**3989 passed / 0 failed / 2 skipped / 13 xfailed**，`-n auto` 916.88s）
**逐位一致** ✅。用时 490.82s 更短属 `-n 6` 与 `-n auto` 的并行度/负载差异，不影响读数。

---

## 阻断（0 项）

无。「cause 构成变了而锁没看见」的形态：0。

## 不阻断（3 项）

### 不阻断-1：「第三 code」形态下三个钉全绿——判据两处条款的解读张力，已按判据主句裁定

格 13：出现不在 `DEFERRED_PROJECTION_CODES` 里的新 code 时 A/B/C 全绿、由 D（amnesty 半边）红，
且 D 的返回值带新 code 原文（可指名）。复核单判据主句「**至少有一条断言红、且红的那条能指名**」
与简写条款「三个钉全绿 ⇒ 阻断」在字面上冲突；按主句解读该形态被接住（D 与三个钉在**同一条测试函数**
里、是同一裁决的零阈值半边，docstring 明言「no new unexplained failure may hide behind the declared
deferrals」）。结构上，一个声明表外的 code 不可能被 per-code 计数钉看见——若按简写条款读，
任何拆法都注定阻断，与立债方向矛盾。**建议**：以后写这类判据时把「一条断言」的辖域写死
（是「三个钉」还是「该测试函数的全部断言」）。

### 不阻断-2：计数读出锁不锁「身份」——同支计数不变、cavity 换人时四条断言全绿

格 18 实测：2+2 构成不变、F153B 两个 cavity hash 换人 ⇒ 两个消费者测试 GREEN。
这是**计数锁的固有边界**，不是本单的洞：A-11-d2 的口径是「构成变化可归因到 cause」（计数级），
docstring 声明的也是计数（"2 of each"）；且真实流程里 cavity hash 是内容哈希，三件套重出时身份
本来就会变（G-c 树 z4/z5 的 hash 就换了），若锁身份反而会误伤合法重出。旧求和钉同样盲。
登记为边界说明。

### 不阻断-3：派生总数使「钉错」的信号最先落在总数行（断言顺序效应）

变异 1/2 显示：单独改钉 B 或钉 C，两个消费者先红在 A 行（`assert 4 == 5`），per-code 行未到达
（测试在第一条红处停）。信号没有丢（B/C 行被执行已由变异 4/5 与格 15b 证明；「哪一支」的指名
在总数恰好对上时直接出现），枚举也不存在削弱格（§三-1）。这只是**读红时的呈现顺序**：
A 红时归因要看 per-code 钉与数据的对账——而这正是拆分本身提供的诊断路径。登记为使用注意点。

---

## 未复现项清单

- 无（本单复核范围内的事项全部实测）。

## 你自己造的同形输入是什么、为什么它同形

1. **真实格式校准的注入集**（§二/§三 全部实验）：failure 串先用真实 `reconcile_boundary_basis`
   校准（拿到四条原始串的精确格式），再按构成拼装，`FakeAudit` 补齐 `rows/pairings/exclusions`
   使非钉断言全绿——所以「红不红」只取决于钉本身。同形之处：喂的是**消费者真实测试函数**本体
   （不是复述断言），与施工方矩阵讨论的是同一个不变量。
2. **数据×钉 880 格枚举**（§三-1）：施工方与复核单都只测了「数据动、钉不动」半边；我枚举了钉侧
   （含钉漂移、readout 更新终态 `0+2`）——「旧红∧新全绿」当且仅当钉=数据逐支相等，削弱不存在。
3. **跨 code 重叠 / 同支重复 / code 延伸 / 段数不足 / 拼错 code**：复核单清单之外、同一病族
   （「identity 与计数的解耦方式」）的五种形态，全部实测且无洞（行为与旧版逐位一致或响亮红）。
4. **两树同尺直算对称差**（§四）：复刻自证（主树 1182000.000000 = 生产者行内数）后，
   同一尺子在 G-c 树量出 0.000000。
