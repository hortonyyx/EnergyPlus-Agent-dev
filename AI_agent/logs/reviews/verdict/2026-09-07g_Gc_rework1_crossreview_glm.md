# 跨家族复核裁决 · G-c 返工 1（GLM 家族，2026-09-07）

**施工方 = GPT-6 Astra**（`codex exec`，effort `xhigh`）· **复核 = GLM `glm-5.3`**（用户指定）
工作目录 `/tmp/gc_rw1_review_glm`（detached HEAD `f0437dba`，全程未动）。
审阅范围 `fd5c3388..f0437dba`（T1–T4 五段 + 自审补强）。

## 裁决：**APPROVE** · 阻断 0 / 不阻断 3

三条复核全过；名单内 6 把锁 + T4 额外三处共 9 把锁，我用**与施工方不同的变异**
（5 处临时改生产源码 + 4 处 runtime 扰动，各跑 2 次）逐一确认有牙；T3 的语义更正
经独立推导成立；交件抽查 3 处逐字对上；独立全量与主控参照逐位一致。

---

## 〇 开工自检

```
$ git log --oneline -1
f0437dba 09.07_Gc_rework_T2_room_completeness
$ python -c "import tests.deferred_projection_ledger as m; print(m.__file__)"
/tmp/gc_rw1_review_glm/tests/deferred_projection_ledger.py
```

前提核对：`git diff --name-only fd5c3388..HEAD` = 9 个文件**全部在 `tests/`**
（8 个 .py + 新增 `tests/gc_rework1_inventory.md`），生产源码零差异 ⇒
「恢复这 8 个 .py 到 fd5c3388 版本」在数学上等价于「在 fd5c3388 上跑测」。
未跑任何写 `site-packages` 的命令；跑测一律 `-n 6`。

## 一 §三 三条复核（原始命令与输出）

**1) 改动前复现得出**（恢复 fd5c3388 测试 → 跑派工单同 5 文件 → `git checkout HEAD -- tests/` 还原）：

```
$ python -m pytest -q -n 6 -p no:cacheprovider tests/test_answer_compiler_profiles.py \
    tests/test_as_drawn_denominator_f126.py tests/test_a11_gt_1mm_ingest_resolution.py \
    tests/test_f156_ring_from_intersection.py tests/test_boundary_condition_facts.py
第 1 次 ⇒ 6 failed, 47 passed in 5.70s
第 2 次 ⇒ 6 failed, 47 passed in 5.90s
```
6 条失败名与派工单逐条一致（1b / L4 / external / scan / f156 / r2）。✅

**2) 改动后复现不出**（f0437dba 原样）：

```
$ python -m pytest -q -n 6 -p no:cacheprovider <同上 5 文件>
⇒ 53 passed in 6.83s          （47+6 对账吻合）
```
✅（另：全量 0 failed，见 §五）

**3) 换同形但不同的输入仍走不通** —— 施工方两个变异脚本全文取出重跑 +
9 处自造变异，见 §二。✅

## 二 §四-1 牙是不是真的（头号任务）

### 2a. 施工方脚本重跑（⛔ 未转引；从交件 §复现脚本原文 取出，写入 /tmp/gc_rw1_evidence/ 在本树跑）

```
$ python -m pytest -q -n 6 -p no:cacheprovider /tmp/gc_rw1_evidence/seat_test_T2_red.py /tmp/gc_rw1_evidence/seat_test_T4_sensitivity.py
⇒ 6 failed in 5.09s
FAILED seat_test_T2_red.py::test_unsigned_sample_is_red        （unsigned revisions remain + NaRecordV1('rev-13ad'…propagated_from=['13AD'])）
FAILED seat_test_T2_red.py::test_missing_itemisation_is_red    （assert set() == {'194E'}）
FAILED seat_test_T2_red.py::test_changed_identity_is_red       （identity strings moved）
FAILED seat_test_T4_sensitivity.py::test_newly_exempted_after_p1 （exemption …after_p1 swallows coordinate path）
FAILED seat_test_T4_sensitivity.py::test_ignoring_one_missing_snap（DID NOT RAISE）
FAILED seat_test_T4_sensitivity.py::test_losing_block_readouts （At index 4 diff: … != 'tarch_wall_free_end'）
```
失败信息与交件逐条一致。✅（贴的失败行号 `:113/:265/:323` 在本树漂为
`:126/:263/:379`——本树在 f0437dba、后续提交继续改了这些文件，属预期，见不阻断 F-1。）

### 2b. 我自造的 9 处变异（⛔ 每处与施工方不同；各跑 2 次、红 2 次）

源码类 = 临时改生产源码 → 跑目标锁 → `git checkout -- <file>` 还原（逐处做完即还原，最终 `git status --porcelain` 为空）。
runtime 类 = monkeypatch 扰动放 /tmp（不进树），try/except 捕「锁断言红」为通过。

| # | 锁 | 我怎么变的（与施工方的差异） | 红了没有（×2 次） |
|---|---|---|---|
| M1 | `test_1b_…_names_unsigned_na` | **生产侧**：`answer_compiler.py` `_compile_view` 的 `unresolved_handles` 置空集 = compiler 对 unsigned 完全不传播 NA（施工方只从外面喂损坏产物测 `_assert_no_unsigned_geometry`；我测传播这半区） | ✅ 红 `test_answer_compiler_profiles.py:109` `assert actual_na == incident`（空集≠4 房间） |
| M2 | `test_l4_…_itemised` | **生产侧**：`denominator.py:691` 诊断过滤掉全部 BLOCK = 成功路径吞 BLOCK（施工方测 items 空；我测 BLOCK 透传政策这半区） | ✅ 红 `test_as_drawn_denominator_f126.py:261` BLOCK 集合断言 |
| M3 | `test_external_quantities_are_bit_identical` | runtime：snapped 的 `converter_readouts.dangles += 1` = **豁免整数叶**被移动（施工方只测身份串半区，这半区它没碰） | ✅ `external_leaves` 断言红（"an exempt quantity outside the boundary derivation moved"） |
| M4 | `test_the_scan_goes_red…` | runtime：豁免表临时吞掉整个 `views[*].walls[*]` 子树 = 扫描器对 10 个墙坐标失明（**施工方根本没给这把锁造过变异**） | ✅ `Counter(violations) == expected` 对账红 |
| M5b | `test_projected_ring_identity…` | **生产侧**：`answer_compiler.py:1365` unavailable 的 cavity 静默 `continue` 不上报 = F157 deferred 消失 | ✅ 红 `assert 0 == 2`（总数行，deferred 空集） |
| M6 | `test_r2_real_sm25_pairs…` | **生产侧**：reconcile 配对循环 `if not rows: continue` = 配对行被丢弃 | ✅ 红 `assert 0 == 108`（paired_edges，`test_boundary_condition_facts.py:134`） |
| M7 | `test_the_exemption_table…` | runtime：豁免表加 `views[*].walls[*].face_lo`（施工方加的是 after_p1；不同 pattern、不同生产者家族） | ✅ 红 "exemption 'views[*].walls[*].face_lo' swallows coordinate path 'views.0.walls.2.face_lo'" |
| M8 | `test_r2_readouts_are_the_converters_own_numbers` | runtime：`_readout_records` 诊断**乱序** + 首条 gate `passed` 翻转（施工方是删 BLOCK；我测逐位/逐序对账） | ✅ 红 `test_as_measured_facts_layer.py:761` code 列表比对（At index 0 diff） |
| M9 | `test_o21bs_deleting_a_snap_entry…` | **生产侧**：`as_measured.py` `_axis_snap_ledger_has_teeth` 开头 `return self` = 校验器整体失效（施工方是 schema 侧 len==2 跳过） | ✅ 红 `DID NOT RAISE`（`test_as_measured_facts_layer.py:692`） |

（M5 过程披露：我先试了「禁用 `if projected is None` 分支」，红落在
`answer_compiler.py:1370` 的 `AttributeError`（None 进 symdiff）而非断言——
换了 M5b「静默跳过」形态后拿到干净的 `assert 0 == 2`。两形态都让锁 FAILED，
但 M5b 才是有意义的退化形态。）

**结论：9/9 有牙。** 名单 6 把 + T4 三处全覆盖，无一空转。

## 三 §四-2 T3 的基线是推导还是抄观测值（独立判断：**席位的更正成立**）

**判断：那个桶数的是「非网格整数坐标的出现次数」，不是面线条数。48 是对的；46→48 的 +2 正是 13AF 的两个端点。** 派工单把桶语义读成条数（「13AF 现在是面线了 ⇒ 面线桶多一条」）是**错的**，席位更正正确，⛔ 不是阻断。

依据（全部是我自己跑的，两条独立路径 + 定点归因）：

```
路径 A（生产扫描器分桶）: scan_ingest_resolution_violations(plain) 里 ".face_lines." 违规 = 48
路径 B（我自己写的对象层枚举，不用测试模块的 oracle）:
  48 = plan-F1 42 + plan-F2 6；按字段 const 14 / along_min 17 / along_max 17
  （与交件「F1: 12+15+15，F2: 2+2+2」逐项一致）
面线【条数】实测 = plan-F1 225 + plan-F2 222 = 447 ⇒ 「桶=条数」显然不成立
定点归因：13AF 在 plain 构建贡献恰 2 个 off-grid（along_min=99401, along_max=100601）；
  从 face 集合剔除 13AF 后桶 = 46（= 旧基线数）⇒ +2 归因闭合；
  且 99401/100601 正是 13AE/13AD 的 const（= 跟随接头重定位的端点，与 T1 叙述一致）；
  snapped 构建里三线全部上网格（99400/100600），scan 总违规 = 0。
```

所以 T3 的修法满足派工单要求：不是把 46 改成 48，而是给了可执行推导
（`_unsnapped_coordinate_inventory` 遍历 facts 字段，不调用扫描器/walker/豁免
matcher，且要求 path/value **多重集合**精确相等——漏一个不能用多计一个抵消），
docstring 写清了语义。交件同段「100→104 不只是 face 桶 +2（walls 11→10、
evidence 7→8、derived 26→28）」与我重跑的推导命令读数（derived 28 / evidence 8 /
face 48 / openings 10 / walls 10，总 104）一致。

## 四 §四-3 T4 三处额外修复（逐条：**均为真缺陷，非自造工作量**）

| 处 | 不修它会漏掉什么（量的证据） | 判断 |
|---|---|---|
| after_p1 豁免方向 | 旧锁（fd5c3388 实读）钉的代表路径是 `("views","0","non_orthogonal_lines","0","p1","0")`——**漏了 `converter_readouts` 层**，该路径在序列化文档里根本不存在（真实路径是 `views[*].converter_readouts.non_orthogonal_lines[*].p1`），那颗牙**恒绿空转**；且 G-c 已把非正交端点判为 RAW/应豁免（`as_measured.py:344-347`），旧方向与所有权裁定相反。新锁钉真实 post-snap 端点 `after_p1`。施工方变异（加 after_p1 豁免）与我的 M7（加 walls.face_lo 豁免）双双红。 | **真缺陷**（是） |
| facts 成功路径 BLOCK 库存 | 实测当前真实 as-received 构建成功路径诊断 = `plan-F1 {'INFO': 17}`、`plan-F2 {'INFO': 14}`，**BLOCK=0**、G5 全 True ⇒ 旧锁的「含 BLOCK 透传」比较两侧同时无 BLOCK，「readout 记录丢 BLOCK」的变异不红（施工方 T4 前 `3 passed` 实测）。不修 = F-B 政策（成功路径 BLOCK 必须透传）失去全部检测。新锁用孤立笔画夹具重建真实 BLOCK+G5=False 库存，我的 M8（乱序+翻转）红。 | **真缺陷**（是） |
| 每次仅删一条 snap | 旧锁代码 `snapped[:1]`（3 条时一次删 2 条）注释却写 "drop one"——**锁的实际行为与声明不符**：「校验器只抓缺≥2条」的退化不红。新锁逐 handle 每次删一条；我的 M9（校验器整体禁用）DID NOT RAISE 红、施工方 len==2 变异红。 | **真缺陷**（是） |

## 五 §四-4 交件原始输出抽查（3 处，**全对上**）+ §六 全量

1. T1 归因命令逐字重跑 ⇒ `f153 []` / `f157 [('plan-F1','cavity:8bd127719198fd63'),('plan-F2','cavity:495501ce9b36f0f3')]` / `paired zones 27 paired edges 108 mismatches []` / `boundary_ring_losses 0` —— 与交件逐字一致。【量】
2. T3 推导命令逐字重跑 ⇒ `DERIVED BUCKETS {'derived': 28, 'evidence': 8, 'face_lines': 48, 'openings': 10, 'walls': 10} TOTAL 104` —— 逐字一致。【量】
3. T1 后三文件 ⇒ `43 passed in 3.96s`（交件 `4.06s`）——条数一致。【量】

独立全量（§六，前后各核 `__file__`）：

```
跑前: /tmp/gc_rw1_review_glm/src/agent/judge/tarch_normalize.py
$ python -m pytest -q -n 6 -p no:cacheprovider
⇒ 4009 passed, 2 skipped, 13 xfailed, 211 warnings in 465.20s (0:07:45)
跑后: /tmp/gc_rw1_review_glm/src/agent/judge/tarch_normalize.py
       /tmp/gc_rw1_review_glm/tests/deferred_projection_ledger.py
```
与主控参照 `4009 / 0 / 2 / 13`（469.38s）**逐位一致**。✅

## 六 §四-5 施工方自认最薄弱处的独立意见

它说：最薄弱 = T4 外延——「若某个动态 helper 间接读了当前 facts 而源码看不出这层
依赖，仍可能漏掉另一把空转锁；全量绿不能替代这层判断」。

**我同意，且认为这个风险是真实的**：token/AST 扫描只能看见源码里字面出现的
关键词；本项目夹具普遍直接喂真实 facts，一个 helper 若从真实产物取数，源码里
只有 `view.face_lines` 这类字段访问、没有 13AD/rev-/axis_snapped 字样，静态扫描
对这类锁**结构性失明**。它没有拿全量绿冒充外延完备、并在对照表外写了「可能
漏掉的类别」——态度诚实。

**便宜的可观测化办法（一次全量的代价，零新基建）：产物探针 run。**
把真实构建产物里这次修复消灭的存货（例如 `axis_snapped_lines` 三行之一，或
13AF 那条面线）临时改成哨兵值/删掉，跑一次全量，把**变红集合**与对照表对账：
- 表外却变红 ⇒ 表漏了它（间接读的直接证据，补外延方向）；
- 表内声称依赖却不变红 ⇒ 该锁存货描述错误（补牙方向，交 §四-1 型变异处理）。
它测的是**运行时真依赖**而非源码字面，恰好补上静态扫描的盲区。局限也要写明：
探针只暴露「对被扰动字段敏感」的读；「读了但恒绿」的空转锁仍需逐锁变异（本轮
§四-1 已对名单内 9 把做过）。完整解 = 扰动探针（外延）+ 逐锁变异（牙）。

## 七 不阻断 findings（3）

- **F-1** 交件贴的 T2 变异失败行号（`:113/:265/:323`）与本树重跑（`:126/:263/:379`）
  不同：行号跨提交漂移（本树含 T3/T4/补强提交），失败信息逐条一致。非缺陷，记录。
- **F-2** 交件 T2 段「真实 clean 输出为 13+14 个 projectable 房间，构造后为 9+14」
  这组数字我**未单独核对**；由房间完整性断言全绿（§三-2 的 53 passed 内）+ M1
  传播变异红间接覆盖。记录为未逐数复核项。
- **F-3** M4/M7 证明锁对「整类坐标失明」会红，但 15 条 coordinate_paths 我只抽查
  2 条的吞没问题（walls.face_lo、after_p1）；其余 13 条靠锁的笛卡尔积结构同构成立
  ——**未逐条对 schema 验存在性**（旧 non_orthogonal 那条的教训正是路径不存在）。
  这是我的复核自己的留白，见 §八。

## 八 我自己最薄弱的一处判断

**对「名单之外的锁」我只信了主控的外延核实，没有自己重扫。** 复核单 §二 左栏
写主控已用独立 token 扫描核实对照表外延零缺口，我没有用第三种走法（例如上文的
产物探针 run）独立证伪它。若主控的扫描与施工方的检索犯**同一类**盲（都只扫
tests/ 源码字面、都漏掉间接读），一份有空转锁的对照表会在这轮复核里双绿通过。
本轮名单内 9 把锁的牙是实测的，这部分不受影响；受影响的是「名单完备性」这一层
——它靠的是两个静态扫描的一致，而非运行时证据。若要关闭，用 §六 的探针 run
一次即可。

## 九 过程披露

- 为变异实验临时改过 3 个生产文件（`answer_compiler.py` ×4 轮、`denominator.py`
  ×2 轮、`as_measured.py` ×2 轮），**每轮跑完立即 `git checkout -- <file>` 还原**；
  结束时 `git status --porcelain` 为空、HEAD 仍 `f0437dba`。⚠️ 中途有一次 M1/M2
  的验证 grep 模式写错（`^tests.*AssertionError` 匹配不到绝对路径前缀的
  `--tb=line` 输出）导致两个 0 计数，立即用 `FAILED` 行重验——两次均确认红，
  未据此下过任何结论。
- runtime 变异与施工方脚本副本只写 `/tmp/gc_rw1_evidence/`（仓库外）。
- 未动主树任何代码（只写本裁决书）；未动 `/tmp/gc_rework_astra`、`/tmp/gc_snap_ladder`。
- 跑测一律 `-n 6`（runtime 变异文件仅 4 条用例用 `-n 4`，全量与基线回放均 `-n 6`）。
