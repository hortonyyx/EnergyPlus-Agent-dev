# ②-1b 跨家族对抗审裁决书（GLM · 升一档）

- **日期**：2026-08-29 · **审阅方**：GLM 家族（glm-5.3）· **请求书**：`AI_agent/logs/reviews/request/2026-08-29_o21b_crossreview_glm.md`
- **送审对象**：`9f0266b`（主）+ `2196723`（补记），基线 `a40d56d`。**审的是 `git diff a40d56d..2196723`，不是工作树**；`db091be`（主控纯文档）不在范围。
- **方法**：所有 RESULTS 独立对夹具重跑；引用行号全部回文件 `grep -n` 核过；验锁实验在 `/tmp` 副本（`PYTHONPATH` 隔离防 editable `.pth` 串台）做；行为判定均有对照跑。

---

## 裁决：**REWORK**（阻断 **1** 条，范围窄：`gt_revisions.py` 一个文件内的两处小修 + 两句 docstring 对齐，不需要动架构）

读数复核先行：**全仓独立复现 `3292 passed / 13 xfailed / 0 failed`**（`python -m pytest -p no:cacheprovider -q -n 6`，985.65s），
`.pth` 哨兵跑前跑后同为 `58f547fa…`（内容指主树）；受影响子集（`affected_tests.py --changed` 五文件）`385 passed / 1 xfailed`；
新增 39 条计数精确对上（23 + 5 + 4 + 7）。范围干净：src 5 + tests 4 + 落盘 3 + 实验脚本 + 执行报告，与请求书 §一 一致。

---

## 一、阻断（1 条）

### B-1 ·【= 请求书 A6，⭐ 升格为阻断】`derive_as_signed` 后墙与面线静默失同步，且 `AsMeasuredWallV1` 的 docstring 逐字声称存在一道全仓无代码的检查

**独立复现**（纯内存，未写树；比主控的实测多抓了 docstring 与 `_ledger_identity` 检查面两条）：

```python
from src.agent.judge.gt_facts_staging import read_facts_candidate
from src.agent.judge.gt_revisions import *
am, revs, asg = read_facts_candidate("sm25-L_anchor")     # plan-F1: face_lines=222, walls=54
# 签 translate: face_line "1379"(被墙 w_x_0_2400_52400_86400 真实引用, lo 桶), field=const, delta=500
```

实测输出：

```
=> derive_as_signed 成功，没有 raise
面线 1379 const: 0 -> 500
墙自报 face_lo/hi/thickness: 0/2400/2400 (0.1mm) = 240.0mm
它引用的面线实际 const: lo=[500] hi=[2400]   ⇒ 实际间距 1900 = 190.0mm
as_signed hash moved: True
```

三条定性证据：

1. **代码面**：`gt_revisions.py:317-320` 只重写 `view.face_lines`，`walls`/`openings` 经 `view.model_dump(mode="json")` 原样带过。
2. **检查面**：`AsMeasuredViewV1._ledger_identity`（`as_measured.py:377-429`）查台账恒等式、id 唯一、悬空引用、三桶互斥并集——
   **没有任何一条**比对 `wall.face_lo / face_hi / thickness` 与它引用面线的实际 `const`。`AsSignedV1` 复用同一 view 类型 ⇒ 派生后同样不查。
3. **文档面**（本条的升格理由）：`as_measured.py:211-214` 逐字写着
   「stored as the INTEGER DIFFERENCE OF THE TWO STORED FACES, so "recompute it from the two faces
   and compare bit-for-bit" **is a real check**」——**这道"真的检查"全仓没有任何代码做它**。
   唯一相近的 `_thickness_is_the_difference`（`as_measured.py:247-249`）只查墙自报三字段间自洽
   （`thickness == face_hi - face_lo`），与面线无关——改一面线的 `const` 它毫无反应。

**处置判断**（请求书 A6 三问）：

- ① 复现得出（如上，逐位与主控实测一致）。
- ② **正确处置 = 加一道一致性门、对不上就响亮失败**；**不是**「派生后重跑配对」。重跑配对会把配对职责从
   `denominator` 的 D1–D5 挪进派生器，违背「walls 不是第二份什么算墙面的实现」（flow map §1.2），
   且 wall id 会变、依赖闭包全乱。一致性门 ~15 行：对每堵墙断言
   `face_lo == min(引用面线 const)`、`face_hi == max(引用面线 const)`、`thickness == face_hi - face_lo`，
   放进 `derive_as_signed` 尾部或 `verify_as_signed_reproduction`——**docstring 已替你把这道检查的规格写好了，代码补上即可**。
- ③ **该在 ②-1b 返工里解，不随 ②-1c**。理由：(a) 门守的是 `as_signed` 派生本身，属本单交付物职责，不是 AnswerCompiler 的；
   (b) 修法独立、小、不动架构；(c) 「文字声称的检查没有代码」是指南 §五#1「⛔ 文字不许跑在实现前面」的直接违例——
   本批两轮跨家族 REJECT 的同一病根，不能在自己交付的 docstring 里再过一次。

**同单须对齐的第二处过强文档**（= 请求书 A5 的实测结果，并入本阻断的文档项）：
`gt_revisions.py` 模块 docstring 称 `candidate_action`「**never read by derive_as_signed**」。实测
（改 `rev-13ac.candidate_action.delta_0p1mm` 从 -2 到 -999）：

```
candidate_action=-2   ⇒ as_signed hash 4fec6ef6…
candidate_action=-999 ⇒ as_signed hash d2548ba0…   （hash 移动）
几何内容逐位相同: True    （face_lines 全字段不变）
顶层差异: ['derivation']，动的键: ['revisions_content_sha256']
```

即 advisory 字段的内容经 `canonical_revisions_bytes → revisions_content_sha256 → derivation` **确实进入 as_signed 的字节与哈希**。
这不是几何绕过（A5 的结构门成立：unsigned 带不上 `action`，`derive_as_signed` 只读 `.action`，几何逐位不动），
但「never read」应改写为「never **applied to geometry**」——它与「整份 revisions 哈希进派生键」（ledger §七，设计使然）字面矛盾。

---

## 二、不阻断 findings

### N-1 ·【= 请求书 A1】F-D legacy 豁免集合无锁——独立证实，且升级证明：**无需捏造，既有单成员豁免今天就足以把 sm25 的真实实现漂移洗白成 `reproduced`**

**复现①（施工方自测的独立证实，对照法）**：`/tmp` 干净副本与「塞入捏造哈希 `fab0fab0…`」副本跑同一组测试
（`test_gt_raw_layer.py + test_gt_promotion_path.py + test_tarch_converter_reproducibility.py`），
读数**逐字相同**（两副本均为 26 failed / 80 passed；失败均为副本环境夹具缺失，与豁免集合无关）⇒
**捏造哈希的边际效应 = 0 条测试变化**。根因在测试层：`test_f_d_d_known_pre_fix_values_are_pinned_not_recomputed`
只断言「sm25 值 `in` 集合 ∧ sm24 值 `not in`」——对**额外成员零分辨力**。

**复现②（升级：真实漂移被既有豁免洗白）**：在 `/tmp` 副本对闭包成员 `tarch_converter_schema.py` 追加一个真实行为语句
（`DRIFT_PROBE_NEW_STATEMENT = 1`，widened 指纹随之翻转至 `fabf3fbb…`），然后：

```
python: verify_raw_layer_reproduction("sm25-L_anchor")  ⇒ status=reproduced, drifted=()
python: verify_raw_layer_reproduction("sm24_anchor")    ⇒ status=implementation_drift,
                                                        drifted=('converter_sha256','vg_implementation_sha256')
```

主树基线（无漂移）同样是 sm25 `reproduced` / sm24 `implementation_drift`。
⇒ **请求书 A1 的两项核实均通过**：sm24 不豁免是真的，且与 sm25 走同一段代码路径（`gt_raw_layer.py:431 _expected_converter_sha256`，
sm24 的 recorded 不在集合 ⇒ expected=current_wide ⇒ 不等 ⇒ drift；F-132 保持可见）。
⇒ 同时证明：sm25 的**转换器实现指纹信号已死亡**（直到重签）——实现闭包怎么漂，只要几何输出不动，sm25 永远 `reproduced`。

**严重性判断**：不阻断。与历史那次「以向后兼容为名加回旧口径、6 锁全绿骗过」**同形但轻一档**：
那次信任根静默挂回可清理目录（实害即发）；这次是**单 case、有 docstring 命名、有重签出口**的 named gap，
且几何 content diff 兜底仍在（漂移若改 sm25 几何输出，content 比对会红）。真正的风险是**集合可无声扩员**。

**最小修法（两层，一行 + 一断言）**：
1. `test_f_d_d` 的断言从 `in`/`not in` 改为**集合整体相等**：`assert tn.KNOWN_PRE_F_D_CONVERTER_SHA256 == frozenset({sm25_report["converter_sha256"]})` ——额外成员立即红；
2. （加强）豁免值溯源到 git 对象：断言 `sha256(git show a40d56d:src/agent/judge/tarch_normalize.py 的字节)` == 豁免值
   ——把「谁有权宣布豁免」从代码作者手里拿走，锚到不可变对象。docstring 已写明来源 commit，这条断言只是把它变成可执行的。

### N-2 ·【= 请求书 A3】守恒面选错——复现成立，且**第三笔点名 + 修法比主控判的更近**

**复现**（`build_as_measured(gt_sources/sm25-L_anchor/sm25-L_t3_as_received.dxf, request_as_measured.json)`）：

```
[plan-F1] all_wall_handles=226  wall_lines_total=223  face_lines=222  non_orthogonal=1  degenerate_in_wall_lines=0
          consumed_wall_handles 长度=0        ⇒ 恒等式 222+1+0==223 全绿，226−223=3 笔无声离开
[plan-F2] all_wall_handles=222  wall_lines_total=222  差 0
```

**比主控多抓的三件事**：

1. **离开记录的 3 笔点名**：`13AD`、`13AE`（斜线，S1 丢弃）+ **`13DC`（零长线，start==end）**。
   第三笔主控未点名，且机制不同——不是非正交丢弃，是退化丢弃。
2. **转换器的忠实读数已在盘上、只是恒等式不用它**：`converter_readouts.degenerate_line_count = 1`（=13DC，搬运的），
   而 `_ledger_identity` 用的 `degenerate_in_wall_lines = 0` 是 `_face_line_records`（`as_measured.py:684-693`）**从 `geo.wall_lines` 重算**的——
   而 `geo.wall_lines` 里根本不可能有零长线（转换器 `tarch_normalize.py:396-400` 已滤掉）⇒
   **`degenerate_in_wall_lines` 结构上恒 0**（[[gate-with-only-negative-assertions-is-unobservable]]）。
   flow map §1.2「转换器自己的读数逐字搬运，⛔ 一个几何值都不重算」在此处被违反。
3. **修法已在盘上凑齐**：diagnostics 里 `tarch_wall_nonorthogonal` 的 handles 恰为 `[['13AD'],['13AE']]`、
   `tarch_wall_degenerate_line` 恰为 `[['13DC']]`、`degenerate_line_count=1`。**正确守恒面**：

   ```
   len(all_wall_handles) == wall_lines_total + <S1 非正交丢弃数> + degenerate_line_count
   226 == 223 + 2 + 1   （plan-F1 逐位成立；plan-F2: 222 == 222 + 0 + 0）
   ```

   一条恒等式 + 三个已在 `converter_readouts` 里的数，**不用改转换器**。
   附：`consumed_wall_handles` 全仓零赋值（`tarch_normalize.py:229` 定义、无写入点）⇒ 恒空，「空列表」与「确实没被消费」在产物上分不开——要么删字段，要么让转换器真填。

**归属**：②-1a 遗留（F-136 已登记），②-1b 未动这些行。但 **②-1b 把 `as_measured` 变成了 revisions 的绑定根**——
第一批真签字将签在漏账的事实上。鉴于 sm25 重签是「走查」且 F-136 已登记在案，不构成本单阻断；
**修法应排在重签之前**（见 §五 丙 的顺序）。

### N-3 ·【= 请求书 A4】两把非正交尺子——复现成立，判断：**该显式命名、不该合并、丢弃类该 itemize**

复现数字（as-received 原生 mm）：`13AD dx=3639.90 dy=−5.81`、`13AE dx=3640.10 dy=−5.81`（两腿都超 `tau_axis=1mm`
⇒ `tarch_normalize.py:384` 丢弃，仅留 diagnostic）；`13AF dx=0.19 dy=120.00`（放行）⇒ 量化到 0.1mm 后
`p0=[52401,…] p1=[52399,…]`，x 两格点不等 ⇒ `as_measured.py:688` 判非正交，进 `non_orthogonal_lines`。

- **该命名**：一个是「容差内当它直」的连续量阈值（`tau_axis`，原生 mm，两腿**都**超才丢），
  一个是量化格点上的离散性质（0.1mm 整数相等）。语义不同层，今天的名字（`tarch_wall_nonorthogonal` vs `non_orthogonal_lines`）却像同一把尺子。
- **不该合并**：合并即把「3639mm 的斜线」与「0.2mm 的格点不齐」混为一谈——前者是图纸方言，后者是表示性质。
- **丢弃类该 itemize**：与 N-2 的守恒式是同一件事——S1 丢弃清单（13AD/13AE）与零长清单（13DC）进 `converter_readouts`，13AF 已在 `non_orthogonal_lines`。
- ⭐ 顺带一个实测细节：13AF 的 `0.19mm` 量化后变成 `0.2mm` 的不齐——**量化把亚格点偏差放大到整格**，这正是它进非正交桶而 13AD/13AE 进垃圾桶的机制分岔点，命名时应把这点写进两个名字的 docstring。

### N-4 ·【= 请求书 A2】`gt_staging/` 无写保护——施工方建议方向对但只盖一半；今天实际暴露面 ≈ 0

`write_facts_candidate` 的 docstring 明写**不跑** `verify_as_signed_reproduction`（「caller is expected to have already proven」）——
即连施工方自己建议的「写前强制 verify」也**尚未实施**。判断：
- write 侧强制 verify（建议）：便宜、防手误，**采纳**；
- read 侧：`read_facts_candidate` 本身不验，但 `tests/test_gt_facts_staging_sm25.py::test_3_the_staged_trio_reproduces_bit_for_bit`
  每次全仓跑都是「读盘 + verify」——**今天已有一条随全量跑的读侧锁**，绕开 write 函数直接写坏的文件会被它抓红；
- 真正的缝在**未来晋升实现**若「整目录拷贝且不跑门」——那属晋升单，ledger §八已写明「晋升前先跑可复现门，不过不许晋升」。
  接法应是「读出 → verify → 拷**内容**」而非拷文件句柄。
⇒ 不阻断；建议 write 侧补 verify（一行）+ 未来晋升按「读+verify」接。

### N-5 ·【= 请求书 A7】B1 两条事实核查属实；「计算方法可审计」**不算**外部获授权锚——施工方的自判成立，R3 结论不需重推

复核：① `HumanReviewAckV1`（`tarch_converter_schema.py:1124-1133`）字段 =
reviewer/signed_at/decision/source_dxf_sha256/request_sha256/overlay_sha256/review_index_sha256/near_threshold_confirmed——**确无实现指纹槽位** ✓；
② `git config commit.gpgsign` 未设置（exit 1）、`HEAD` 的 `%G?` = `N`（无签名）✓。

判断：B1 的要害是「实现的身份锚在实现**之外**的东西上」。13 文件 AST 闭包哈希解决的是**范围**（1→13）与**噪声**（注释不动），
不解决**授权**——改实现的人同时改指纹，指纹跟着实现走；N-1 已实证「旧产物上的指纹可被豁免集合放行」。
故「方法可审计」≠「外部获授权」。但本单约束下（无签字载体、无签字事件、⛔ 不许改已签字件哈希）该退化**诚实声明了**
（docstring 明写 NOT human-signed + named hook + future work）⇒ 不阻断，B1 保持显式债务。
⚠️ **一处文档矛盾须修**：flow map §1.4:107 仍写「转换器实现指纹 = sol 的 B1，**未解**」，
而 §1.8:180 写「B1 指纹锚 ✅ 已落地」——两行打架。统一为「指纹字段已填（方法可审计）、外部锚仍缺」。

### N-6 ·【⭐ 本轮新击穿的错误形态】**换轴语义漂移被 `detect_translate_candidates` 伪装成合法 translate——所有门都在对数字，没有门在看语义**

**可复现**：`python /tmp/probe_axis_swap.py`（脚本已留档；构造 before 的 handle `1A1` 为
`axis="y", const=1000`，after 的同 handle 变为 `axis="x", const=990`）：

```
detect 报出: rev-1a1 | check: face_line_field_changed | candidate_action: translate, field=const, delta=-10
   axis(before)= y → axis(after)= x —— finding 里提到 axis 吗: False
签字后 1A1: axis= y, const= 990   （一条 y 走向线的 x 截距被改成 after 那条横线的 y 截距）
=> 换轴语义漂移以 translate 身份进入 as_signed，全链无一处红
```

**机制**：`gt_revisions.py:335 _FACE_LINE_SCALAR_FIELDS = ("const","along_min","along_max")` 只比三个数值，
**完全不看 `axis` 与 `layer`**。`const` 在 y 轴线与 x 轴线上是**不同坐标轴上的截距**，数值比较在换轴时是类型错误，
而 detect 把它当成同量纲的平移报出；finding.detail 只字不提轴。人签下去 ⇒ `as_signed` 里一条竖线的 x 截距
被赋予横线的 y 截距数值 ⇒ **几何语义全错，且 `verify_as_signed_reproduction` 照样全绿**（as_signed 确实是 am+revs 的机械派生——
门只验「机械」，不验「语义」）。与 [[representation-collapse-manufactures-unrelated-errors]] /
[[observation-named-as-fact-travels-as-fact]] 同族，与五审 band_collapse（数值全真、优于诚实、八门全绿）同性质：**判据锚的字段集合漏了语义字段**。

**真实性**：sm25 今天不触发（13AD/13AE 被 S1 丢弃走 `classification_changed` 分支、诚实无候选），
但触发形状就在下一栋楼里——「把斜线拉直」恰是台账未来的高频操作（本单 docstring 自己点名 3/5 条是这种），
斜线拉直方向由人定；偏差略小于 1mm 的斜线会被收进 `face_lines` 且 axis 按主导腿判定，
两份图主导腿相反时即产出换轴候选。**最小修法（5 行）**：`detect_translate_candidates` 比数值前先比
`axis`（与 `layer`），不一致 ⇒ `candidate_action=None` + detail 点名 `face_line_axis_changed`——与 B-1 同文件同型，返工顺手带上。

### N-7 ·（小）`_index_face_lines_by_handle`（`gt_revisions.py:338`）对跨视图同名 handle 静默取最后一个视图

`AsMeasuredViewV1._ledger_identity` 只查**view 内** id 唯一（`as_measured.py:393-395`），跨视图无约束。
sm25 实测 F1∩F2 face_line 交集 = **0**（不触发），但这是数据巧合不是结构保证——两个 plan view 的 clip 框若有重叠
（同一条线两端点同落两框），字典推导静默覆盖 ⇒ diff 打在错误的视图版本上。修法一行：索引时遇重复 handle 直接 raise。
不阻断（无现实触发件），登记防未来。

### N-8 ·（顺带核实，非 finding）A4 之外的两份 request 仿射逐字段相同

`request_as_measured.json` 与 `request.json` 的 `world_from_source_m` 四矩阵逐字段相同
（plan-F1 `m02=30.469` / plan-F2 `m02=-24.5118`，两份一致）⇒ `detect` 的 before/after 在同一世界系，
无「仿射差混入 candidate delta」风险。这是数据事实而非结构保证——若未来两份 request 标定不同，此处会成为第二个语义混源，随 N-6 一并防御（比 delta 前断言两 doc 仿射相同）。

---

## 三、A1–A7 逐条结论

| 攻击面 | 结论 | 严重性 | 处置 |
|---|---|---|---|
| **A1** legacy 豁免集合无锁 | **证实 + 升级**：捏造哈希零变红（对照副本读数逐字同）；既有豁免已把 sm25 真实漂移洗白成 `reproduced`；sm24 有牙、同一路径核实 | 不阻断 | 集合整体相等断言（一行）+ git 对象溯源断言 |
| **A2** gt_staging 无写保护 | write 侧连建议的 verify 都没跑；但 `test_3` 每次全量都是读侧锁 ⇒ 今天暴露面≈0；真缝在未来晋升「拷目录不跑门」 | 不阻断 | write 侧补 verify；晋升走「读+verify+拷内容」 |
| **A3** 守恒面选错 | **证实 + 补名**：226−223 = 13AD+13AE+**13DC(零长)**；`degenerate_line_count=1` 已在盘、恒等式却用恒 0 的 `degenerate_in_wall_lines`；`consumed_wall_handles` 全仓零赋值 | 不阻断 | 恒等式换面：`len(all) == total + S1丢弃 + degenerate_line_count`（226=223+2+1 逐位成立） |
| **A4** 两把非正交尺子 | 证实；13AF 是量化把 0.19mm 放大成 0.2mm 格点不齐 | 不阻断 | 显式命名、不合并、S1/零长丢弃 itemize（与 A3 同一修） |
| **A5** candidate_action | 几何层**结构性成立**不可绕；哈希层**确实影响** as_signed（经派生键）；docstring「never read」过强 | 并入 B-1 文档项 | 改「never applied to geometry」 |
| **A6** translate 失同步 | 复现成立；`_ledger_identity` 无数值比对；docstring 声称的检查无代码 | ⛔ **阻断** | 一致性门 ~15 行，**②-1b 返工解**，不随 ②-1c |
| **A7** B1 外部锚 | 两条事实核查属实；「方法可审计」≠「外部授权」；施工方自判诚实 | 不阻断 | 保持显式债务；修 flow map §1.4:107 vs §1.8:180 矛盾 |

---

## 四、本轮新找到的错误形态（请求书 ⭐ 最重要一条的答复）

**换轴语义漂移伪装成 translate**（详 N-6）：所有已交付的判据——schema 结构门、恒等式、`verify_as_signed_reproduction` 的逐字节重算——
**全部锚在数值字段上，没有一条看语义字段（axis/layer）**。一个 axis 翻转 + 数值巧合的 before/after 对，
产出一条「看起来完全合法」的 translate 候选，detail 无任何线索，签字后进入 `as_signed` 且复现门全绿。
这是「产物里没有一个假数，但语义在表示层被换了」——五审 band_collapse 的直系亲属，本次以不同通道（候选生成器而非判分器）再次命中。
修法与 B-1 同单（`gt_revisions.py` 一处比对、5 行）。

---

## 五、请求书 §四 的意见：正交吸附 **甲 / 乙 都不选，存在严格更优的第三条（丙）**

先复述判题基础（主控实测，我方独立复核同数字）：签字件 plan-F1 face_lines=225，as-received=222(+1 非正交)，
逐视图差集恰为 `13AD/13AE/13AF` ⇒ `as_signed` 结构上比签字图少 3 条 ⇒ ②-1c 原定头号验收「形式 B 复现今天签字的 gt.json」结构上过不了。

**否决乙**：请求书的批评成立——「把哪条斜线吸到哪根轴」本身就是吸附规则，把它实现成一种 `action`
= 把吸附实现进台账 = 同一件事做两遍，且每签一条拉直都要人手拍板一次本可机械决定的轴归属。

**甲方向对但不完整**：吸附进转换器（`tau_axis` 从「容差内当它直、只收主导腿」升级为「容差内收成轴对齐」）
是正解的一半——它让 13AD/13AE/13AF 自动变成轴对齐面线，根本不需要 revision。但**裸甲有一个 A3 同族的代价**：
若吸附不 itemize，`as_measured` 会**静默丢失「原图是歪的」这个事实**（13AD 歪 5.81mm 的信息消失）——
这次不是「墨迹离开记录」而是「修正离开记录」，与 ledger §一「忠实性」相悖。

**⭐ 丙（推荐）= 甲 + 三件配套**：

1. **吸附决策 itemize 进 `converter_readouts`**：每条被吸直的线记（handle、原斜率两腿、吸到哪根轴、位移量）——
   与「量化在收线时就做了」同地位（flow map §1.2 先例），吸附不是暗改而是显式记录的转换器行为；
2. **同修 A3 守恒式**：吸附后 S1 丢弃清零，守恒式变为 `len(all_wall_handles) == wall_lines_total + 吸附清单 + degenerate_line_count`——
   13DC 那笔零长同被点名；
3. **先补 A1 的锁再动转换器**：吸附必然翻转 F-D 指纹 ⇒ sm25/sm24 的旧报告处理会再次走到 legacy 豁免——
   **如果 A1 的集合锁（整体相等断言）还没补，这次翻转就是「往集合里塞值」的第二次实弹**。顺序必须是：补 A1 锁 → 吸附 → 重签。

**甲所列两项代价的再评估**：「F-D 指纹会翻转」是设计内行为（指纹的用途就是记录实现变化），且用户已拍板
「sm25 gt 整份重做重签后移到改造之后」——「重跑全部签字件对照」的代价与既定路线重合，边际成本≈0；
②-1c 的头号验收应从「复现**今天的** gt.json」改为「复现**重签后的** gt.json」（后者本来就要做）。
附带收益：指南 §十「正交吸附在今天的判分上不承重」被 F-138 推翻后，丙直接兑现它新承重的地位。

---

## 六、附录：复现命令清单

| Finding | 命令/脚本 |
|---|---|
| 全仓读数 | `python -m pytest -p no:cacheprovider -q -n 6` ⇒ `3292 passed, 13 xfailed`；`.pth` 哨兵 `sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth` 跑前后同 `58f547fa…` |
| 受影响子集 | `python scripts/tool_scripts/affected_tests.py --changed <五文件>` 后整串跑 ⇒ `385 passed, 1 xfailed` |
| B-1 / A6 | `python`（见 §一 阻断栏代码；签字 1379 const+500 ⇒ 无 raise、240.0 vs 190.0） |
| N-1 / A1 | `/tmp` 双副本对照（干净 vs 塞 `fab0fab0…`，读数逐字同）+ 漂移实验（`tarch_converter_schema.py` 追加语句 ⇒ sm25 `reproduced` / sm24 `implementation_drift`） |
| N-2 / A3 | `python`（`build_as_measured` 两视图 + diagnostics 点名 `13AD/13AE` `13DC`；226==223+2+1） |
| N-3 / A4 | 同上 + `ezdxf` 读原实体：13AD `dx=3639.90 dy=-5.81`；13DC `start==end` |
| N-5 / A7 | `grep -n "class HumanReviewAckV1" -A 10 src/agent/judge/tarch_converter_schema.py`；`git config commit.gpgsign`(exit 1)；`git log -1 --format=%G? HEAD` ⇒ `N` |
| N-6 新形态 | `python /tmp/probe_axis_swap.py`（脚本随档留存） |

— GLM 跨家族审阅席位 · 2026-08-29
