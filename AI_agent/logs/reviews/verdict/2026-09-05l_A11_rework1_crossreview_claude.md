# 裁决书 · A-11 返工 1 跨家族复核（Claude 家族）

**APPROVE-WITH-FINDINGS · 阻断 0 · 不阻断 2**

- **复核方**：Claude 家族 · **被审 commit**：`3a017e11`（基点 `83326ba6`）· **工作目录**：`/tmp/a11rw1_review_claude`
- **复核单**：`AI_agent/logs/reviews/request/2026-09-05l_A11_rework1_crossreview.md`
- **施工方**：GLM 家族 · **审阅范围**：`83326ba6..3a017e11`（`580f8b67` 根因A → `8d925e4f` 根因B → `3a017e11` 执行文档）

---

## 头条结论

**上一轮（`2026-09-05i`）提的两个根因阻断，本轮全部真实修复并独立验证通过。** 独立全量
`3863 passed / 2 skipped / 13 xfailed / 0 failed`（`-n 6`，468.58s），逐位闭合
`3863+2+13=3878`，与独立 `--collect-only` 实测 `3878 tests collected` 吻合。**本单可以合并。**

同时，本轮复核**自己造的对抗实验**在两处根因里各挖到一个真实但非阻断的缺口：
① 根因 A 的 DXF handle 锚在「handle 被重新分配给另一个真实对象」这个特定子场景下**仍会静默指错墙**
（不是 0-hit no-op，而是 1-hit-但-指错对象）；② 根因 B 的 `SM25_DEFERRED_CAVITY_COUNT` 是一个
**被我独立构造反例证实的代理量**——两个成因反向变化、总数不变时，锁不会红。两者都不推翻本单的
核心修复，但都值得记录并要求后续动作，故判 **APPROVE-WITH-FINDINGS** 而非纯 APPROVE。

---

## 是否改过被审对象（如实披露）

**否。** 全程只读被审 commit（`3a017e11`），未 checkout、未 stash、未落盘改动。所有对抗实验
（handle 冲突模拟、`SM25_DEFERRED_CAVITY_COUNT` 反例）均用**进程内构造的 dict / 假 `FakeAudit` 对象**
完成，不写文件、不碰 `git`。基点复现（改动前应红）用**独立 worktree**
`/tmp/a11rw1_basepoint_check`（`git worktree add --detach 83326ba6`），复核结束后已
`git worktree remove --force` 清理。`git status --short` 全程只有会话开始前就存在的那份
未跟踪复核单文件，无其他改动。

---

## §一 三条复核（⭐⭐⭐ 缺一不合格）—— 全部独立通过

### 1. 改动前复现得出 ✅

独立 worktree `/tmp/a11rw1_basepoint_check`（基点 `83326ba6`，从未接触被审 worktree）：

```
$ cd /tmp/a11rw1_basepoint_check && python -m pytest -q -p no:cacheprovider \
    tests/test_b1_projection_bridge_fixtures.py::test_fixture2_two_unit_remainder_still_red \
    tests/test_b1_projection_bridge_fixtures.py::test_fixture5_removed_wall_red_at_reconciliation_only \
    tests/test_b1_projection_bridge_fixtures.py::test_4b_counts_equalised_attack_red_only_on_2_and_3 \
    tests/test_f156_ring_from_intersection.py::test_projected_ring_identity_holds_with_no_tolerance_at_all \
    tests/test_f156_ring_from_intersection.py::test_moving_one_converter_edge_by_a_tenth_of_a_millimetre_reddens
...
FAILED tests/test_b1_projection_bridge_fixtures.py::test_4b_counts_equalised_attack_red_only_on_2_and_3
FAILED tests/test_b1_projection_bridge_fixtures.py::test_fixture2_two_unit_remainder_still_red
FAILED tests/test_b1_projection_bridge_fixtures.py::test_fixture5_removed_wall_red_at_reconciliation_only
FAILED tests/test_f156_ring_from_intersection.py::test_projected_ring_identity_holds_with_no_tolerance_at_all
FAILED tests/test_f156_ring_from_intersection.py::test_moving_one_converter_edge_by_a_tenth_of_a_millimetre_reddens
5 failed in 10.39s
```
✅ 同 5 条，在干净基点上确实红。

### 2. 改动后复现不出 ✅

在被审 commit（`3a017e11`，本工作目录）上，跑同 5 条（后两条已改名，用新名）：

```
$ python -c "import src.agent.judge.as_measured as m; print(m.__file__)"
/tmp/a11rw1_review_claude/src/agent/judge/as_measured.py
$ python -m pytest -q -p no:cacheprovider \
    tests/test_b1_projection_bridge_fixtures.py::test_fixture2_two_unit_remainder_still_red \
    tests/test_b1_projection_bridge_fixtures.py::test_fixture5_removed_wall_red_at_reconciliation_only \
    tests/test_b1_projection_bridge_fixtures.py::test_4b_counts_equalised_attack_red_only_on_2_and_3 \
    tests/test_f156_ring_from_intersection.py::test_projected_ring_identity_holds_with_no_tolerance_at_all \
    tests/test_f156_ring_from_intersection.py::test_moving_one_converter_edge_by_one_millimetre_reddens
.....                                                                    [100%]
5 passed in 10.58s
```
✅

### 3. 换同形但不同的输入，仍然走不通 —— ⭐⭐⭐ 自己造，见下

**这是本轮的重点，也是全裁决书里唯一给出「阻断/不阻断」判断依据的部分。** 没有只重跑施工方的
5 条测试，而是针对两个根因各自的**修复机制本身**构造了独立的对抗输入：

#### 3a（根因 A 的机制）：handle 锚在什么条件下仍会静默失效？

用真实 sm25 facts（`_facts()` 加载的原始 JSON，不是施工方任何测试里的合成数据），直接调用
`_wall_by_face_lines` 做三组实验：

```python
# 场景1：handle 被重新分配为一个不存在的值（模拟"转换器重写 DXF"）
wall["face_line_ids_lo"] = ["ZZZZ"]
_wall_by_face_lines(view, B1_WALL_FACE_LINES)
# → AssertionError: face-line lookup (('13AE',), ('13AD',)) matched 0 walls
#   （响亮红，与施工方 DEAD/BEEF 实验一致）

# 场景2：两堵墙的 handle 被同时改成同一个值（handle 冲突）
# → AssertionError: face-line lookup (('1379',), ('137B',)) matched 2 walls
#   （响亮红）

# 场景3 ⭐⭐⭐ 施工方没有测过的方向：handle churn 把 B1_WALL 的旧锚值
# （'13AE'/'13AD'）整体挪给了另一堵真实存在的墙，B1_WALL 自己拿到新 handle
for wall in view4["walls"]:
    if wall["id"] == orig["id"]:
        wall["face_line_ids_lo"] = ["9999"]; wall["face_line_ids_hi"] = ["9998"]
    elif wall["id"] == other["id"]:
        wall["face_line_ids_lo"] = ["13AE"]; wall["face_line_ids_hi"] = ["13AD"]
hit = _wall_by_face_lines(view4, B1_WALL_FACE_LINES)
# 结果：hit.id == 'w_x_0_2400_52400_86400'（"victim" 墙），
#       orig.id == 'w_x_99430_100630_52400_88800'
#       hit.id == orig.id ？ False
```

**结果：`len(hits)==1`，测试静默通过，锚指向了错误的墙，零任何信号。**
这与施工方在交件里的原话——「转换器未来重写 DXF、handle 重新分配时，是响亮的红，不是静默
no-op」——**不完全一致**：只有当重分配导致「旧 handle 字符串不再命中任何墙」（0 hits）或
「两堵墙撞车」（>1 hits）时才响亮；当重分配恰好是**两个对象互换/单向转移了 handle 字符串**
（1 hit，但是错的对象）时，**这条锚和被替换掉的坐标 ID 锚犯的是同一类错误**——只是触发条件
从「A-11 每次都触发」收窄成了「未来 DXF 重写时的一种特定子场景」。

**判定**：不阻断本单——① 触发概率被压得很低（4 位十六进制 handle 空间里精确对撞需要
DXF 重导出恰好把旧 handle 挪给另一个真实几何相邻的实体，且施工方已经把「A-11 这次改动」
这个**唯一已知、100% 会触发**的失效源头堵死了）；② 这是「未来会不会失效」的问题，不是「今天
是否有效」的问题，今天的 5 条真回归确实被修复。**但这是「立门三问②」的一个真实反例**，
不能用「已变异验证」一笔带过——**变异过 0-hit/多-hit，没变异过 1-hit-但-错对象**这个方向。
记为不阻断-1，建议见文末。

#### 3b（根因 B 的机制）：`SM25_DEFERRED_CAVITY_COUNT` 是不是代理量？—— ⭐⭐⭐ 三问逐句作答

按复核单原话构造反例：**总数仍是 4，但两个成因的构成已经变了**。

```python
class FakeAudit:
    def __init__(self, failures): self.structural_failures = failures

# 今天的真实构成：2 x F-157(unavailable) + 2 x F-153 form B(is_not_the_converter_zone)
real_shape = [... 2 unavailable, 2 is_not_the_converter_zone ...]
# len(deferred_cavities(real_shape)) == 4  ✓，failures_not_from_deferred_cavities == []

# 构造的反例：3 x F-157(unavailable) + 1 x F-153 form B —— 两个成因反向各移动一条，
# 总数仍是 4，但"两个成因各自都还在"已经不成立（form B 从 2 条变成了 1 条）
composition_changed = [... 3 unavailable, 1 is_not_the_converter_zone ...]
len(deferred_cavities(composition_changed))                    # → 4
len(deferred_cavities(composition_changed)) == 4                # → True（锁判定"通过"）
failures_not_from_deferred_cavities(composition_changed)        # → []（零阈值半边也不报警）
```

**结果：不红。** 三句自查话术逐句作答：

1. **这个数达标了，那件事就一定成立吗？** —— **不成立**。`count==4` 只保证「结构性失败总数
   落在两个 DEFERRED_PROJECTION_CODES 前缀之下」，**不保证**「F-157 与 F-153 form B 各自的
   计数没有变」——上面的反例机械证明了这一点。
2. **这个数是对着谁达标的？** —— 对着 `audit.structural_failures` 里以
   `DEFERRED_PROJECTION_CODES` 两个字符串前缀开头的条目**总数**，不区分具体是哪个前缀。
3. **我拿来比的这两个东西本来就该一样吗？** —— 不该。声明点 docstring 说的是「2×F-157 的
   `..._unavailable` + 2×F-153 form B 的 `..._is_not_the_converter_zone`」——**两个独立、
   互不相关的几何缺陷各自的计数**；而代码实际检验的是「两者之和」。**docstring 描述的不变量
   比代码实际检验的不变量更强**，这正是「代理量」的定义。

**这不是转引施工方的自我批评——是我独立构造反例、独立跑通、独立确认「不红」的结果。**
另外用真实数据核实了**今天**的构成确实是诚实的 2+2（不是已经出问题了）：

```python
audit = reconcile_boundary_basis(signed, report)   # 真实 sm25-L_anchor 数据
Counter(code breakdown): {'facts_projected_ring_is_not_the_converter_zone': 2,
                           'facts_projected_ring_unavailable': 2}
```
今天的读数没有说谎；这个代理量目前只是「有牙但不够利」，不是「现在已经在骗人」。

**⭐ 单钉够不够、要不要拆——可机械执行的结论**：**要拆，且拆分动作不止改
`deferred_projection_ledger.py` 一个文件**（这一点比施工方自己在「最薄弱一处」的估计更严格）。
施工方原话「改动只在 `deferred_projection_ledger.py` 一个文件内」只对**声明新常量**成立；
若不在两个消费者文件（`test_boundary_condition_facts.py` / `test_f156_ring_from_intersection.py`）
里也加上按 code 前缀分别计数的断言，新常量只是摆设、不会被任何测试执行到。
**结论**：
```
tests/deferred_projection_ledger.py 新增：
    SM25_DEFERRED_F157_UNAVAILABLE_COUNT = 2
    SM25_DEFERRED_F153_FORM_B_COUNT = 2
    deferred_cavities_by_code(audit, code) -> set(...)   # 按单一前缀过滤的版本
两个消费者各加一行：
    assert len(deferred_cavities_by_code(audit, "facts_projected_ring_unavailable")) \
        == SM25_DEFERRED_F157_UNAVAILABLE_COUNT
    assert len(deferred_cavities_by_code(audit, "facts_projected_ring_is_not_the_converter_zone")) \
        == SM25_DEFERRED_F153_FORM_B_COUNT
SM25_DEFERRED_CAVITY_COUNT 保留（= 两者之和，向后兼容现有断言），不必删。
```
不阻断本单（今天的数据诚实、本单要修的两个真回归已经修好），但**登记为必须在下一次
任一成因发生任何变化（F-157 或 F-153 form B 谁先修复、或谁又多冒出一条）之前完成**——
否则那次变化极可能被这个代理量悄悄吞掉。记为不阻断-2。

---

## §二 根因 A 逐条核

### 1. 病族命名正面回应 ✅ 接受，且已实测验证「静默半边」被堵死（见 §一-3a，附带一个未覆盖方向）

### 2. 反查「哪个方向没有锁」✅ 已答（§一-3a 场景3：1-hit-但-错对象 方向没有锁）

### 3. fixture1 同形假绿 —— ✅ 独立复现确认属实

```
$ cd /tmp/a11rw1_basepoint_check && python -m pytest -q -p no:cacheprovider \
    "tests/test_b1_projection_bridge_fixtures.py::test_fixture1_remainder_one_unit_both_versions_cut_14" \
    "tests/test_b1_projection_bridge_fixtures.py::test_fixture1_red_before_tolerance_zero_is_a_loud_zero_face_layer"
3 passed in 7.64s
```
并用**独立脚本**直接验证注入是否真的发生：

```python
v0, _ = _f1_with_endpoint_remainder(0)   # "fixed" 版本
v1, _ = _f1_with_endpoint_remainder(1)   # "defective" 版本
matches = [w for w in v0["walls"] if w["id"] == B1_WALL]   # B1_WALL = 旧硬编码字面量
len(matches)      # → 0   （在基点上，旧字面量已经匹配不到任何墙）
v0 == v1          # → True （remainder=0 和 remainder=1 产出完全相同的 view！）
```
**v0 == v1 逐字节相等，证明两个参数化用例在基点上跑的是完全相同的输入**——「defective」
和「fixed」两个标签下事实上测的是同一件事，是彻头彻尾的同形假绿。施工方这条声称成立，
且**是本轮独立复现出来的，不是转引**。⇒ 上一轮裁决书确实漏了这两条（当时只锁定了全量红的
5 条，没有意识到还有绿但是假绿的）。**如实记入本裁决书**（复核单 §二#3 要求）。

### 4. 注入是否真的生效 ✅ 逐条用「读回构造出的数据」验证，不依赖"测试变红"

```python
# fixture1/2/4b 共用的注入路径
w0.along_min=52400, w1.along_min=52401, w2.along_min=52402   # 三个不同 remainder 产出三个不同值
v0==v1? False   v0==v2? False                                 # 确实互不相同（对照基点的 True）

# fixture5 的删除注入
w2 = _wall_by_face_lines(view, W2_WALL_FACE_LINES)             # 定位到 'w_y_50000_52400_121600_140000'
len(view["walls"])==55 → len(dropped["walls"])==54             # 墙数真的减了 1
any(w["id"]==w2["id"] for w in dropped["walls"]) → False        # 目标墙真的不在了
```
✅ 三个注入点全部独立验证：不是「测试红了所以推断注入生效了」，是直接读构造出的数据字段。

---

## §三 全仓同形扫描 —— 自己跑一遍 + 自己设计对照口径

### 3a：原样重跑施工方给出的命令 —— 输出逐字符匹配

```
$ grep -rnE "w_[xy]_[0-9]+_[0-9]+_[0-9]+_[0-9]+" tests/ scripts/ src/ --include="*.py"
tests/test_o21d_exclusion_gap.py:24: ...
tests/test_b1_projection_bridge_fixtures.py:134: ...
tests/test_b1_projection_bridge_fixtures.py:143: ...
tests/test_as_measured_facts_layer.py:1063: ...
```
4 命中，与交件贴的原文逐字一致；已逐条重新判读（非转引）：前三条是注释/docstring 叙述，
第四条是纯合成 dict（`id`、`axis`、`face_lo` 等字段互相自洽构造，不查找任何真实对象）——判定
与施工方一致：**均非活的定位**。

```
$ grep -rnE "\"(cavity|line|edge|ring|room|zone|face|footprint):[0-9a-f]{16}\"" ...   → 空
$ find tests -name "*.json" -exec grep -lE "w_[xy]_..." {} +                          → 空
```
✅ 与交件一致。

### 3b ⭐⭐⭐ 自己设计的第二套扫描口径（不依赖字面 `w_[xy]_` 命名规则）

施工方的扫描本质上是「按 ID 字符串的命名规则找」——这个规则本身就是一个**假设**（假设所有
坐标派生 ID 都长这个样子）。换一个不依赖命名规则的角度：**直接从 A-11 之前的真实原始数据里
把所有"非 1mm 整数倍"的坐标字段值抽出来，逐个去全仓搜这些具体数字**，不管它们出现在什么
样的字符串里：

```python
# 从 git 历史里的 PRE-A11 原始 as_measured.json 提取 along_min/along_max/face_lo/face_hi/const
# 四类坐标字段中所有非 10 的倍数的值（0.1mm 代表性残差本体）：
bad = [52399, 52401, 78399, 88439, 96399, 96439, 99401, 99999, 100601,
       103599, 103639, 111639, 121599, 159396, 159946, 160596]   # 16 个（sm25-L 单个视图截面）

for v in bad:
    grep -rln "\b{v}\b" tests/ src/ scripts/ --include="*.py"
```

命中：`52401`（`test_b1_projection_bridge_fixtures.py` + `tests/deferred_projection_ledger.py`，
均为注释/docstring）、`121599`（`test_b1_projection_bridge_fixtures.py`，注释）、`159396`
（`test_gt_revisions_and_as_signed.py` + `src/agent/judge/gt_revisions.py`，均为**历史缺陷
docstring 叙述**，实际测试逻辑用的是合成 `_minimal_doc()`，与真实数据的这个具体值无关）。
**零新增活命中**——这套完全不同角度（按"A-11 实际改掉的具体数值"反查,而不是按"ID 命名规则"
正查）的扫描与施工方的扫描**结论一致**。

另外做了「第三种形态」检查（按下标/排序位置/浮点相等定位）：扫了所有对真实 sm25/sm24
facts 做 `walls[0]`、`walls[-1]`、`sorted(...)[k]` 式索引的位置，逐个读上下文——命中的用例
（`test_b1_projection_bridge_production_loader.py`、`test_as_measured_facts_layer.py:1091`）
均是「拿任意一个合法值做占位符」（不关心具体是哪一个），或作用于**合成**（`smix_view()`）
而非受 A-11 影响的真实数据，**均非同病族**。浮点相等定位（`== 数值.数值`）扫描同样零命中
落在真实 sm25 数据上。

**结论：两套独立设计的扫描口径命中集合一致，活的同形缺陷 = 0（除已修的 3 处）。**

---

## §四 独立读数（⛔ 未引用施工方的数字）

```
$ python -c "import src.agent.judge.as_measured as m; print(m.__file__)"
/tmp/a11rw1_review_claude/src/agent/judge/as_measured.py

$ python -m pytest -q -n 6 -p no:cacheprovider
... 3863 passed, 2 skipped, 13 xfailed, 211 warnings in 468.58s (0:07:48)

$ python -c "import src.agent.judge.as_measured as m; print(m.__file__)"   # 跑测后再核一次
/tmp/a11rw1_review_claude/src/agent/judge/as_measured.py

$ python -m pytest --collect-only -q -p no:cacheprovider
3878 tests collected in 3.62s
```

**逐位闭合**：`3863 + 2 + 13 = 3878`，与独立 `--collect-only` 的 `3878` 完全吻合，**一条不差**。
`m.__file__` 跑前跑后均落在本工作目录 `/tmp/a11rw1_review_claude` 内（承重不变量成立；
另一个并行 Claude 席位在 `/tmp/a6_review_claude` 工作，`.pth` 是否被它翻动未知也无关紧要——
`__file__` 才是承重的那个量）。**与施工方交件的读数完全一致，独立验证通过。**

---

## §五 上一轮「不阻断 3 项」处置核查

```
$ git diff 83326ba6..3a017e11 --stat -- src/ case_tests/
（空输出）
```
本轮 diff 只涉及 `tests/` 下 4 个文件（3 改 1 新），**零字节触碰 `src/` 或 `case_tests/`**——机械确认。

1. **`write_facts_candidate` 无条件覆盖 `revisions.json`**：`src/` 零改动 ⇒ 该函数逻辑原样，
   交件也没有声称已修复。✅ 与预期一致（本单未要求修，也没有假装修了）。
2. **F-153 form B 该记入哪个既有单子**：交件全程**没有**把这条读成"已解决/已关闭"——
   `deferred_projection_ledger.py` docstring 用的是"退休时机未到"的语气（"the two F-153 form
   B rows retire when the upstream converter endcap geometry fix lands"），仍是待修的已知债，
   ✅ 未被交件当成已解决。（本单被派工单要求做的是"是不是已知债"这一步判断，不是"归哪个具体
   工单号"——两者是不同的问题，前者属于本单范围，已完成；后者仍待主控裁定。）
3. **`test_as_measured_facts_layer.py` 读数未逐条独立推导**：本单**未触碰**该文件（不在改动
   文件列表内），派工单原话是"本轮可补做"（非强制）。**仍未做**，本轮同样未补——如实记入
   未复现项清单，非阻断（同上一轮判定）。

---

## 阻断（0 项）

无。本单要求修复的两个根因均已确认真实修复，独立全量绿，逐位闭合。

---

## 不阻断（2 项）

### 不阻断-1：DXF handle 锚在「handle 被转移给另一真实对象」场景下仍会静默指错墙

**证据**：§一-3a 场景3（独立构造，非转引）。施工方的原始声称——"handle 重新分配时是响亮的红"
——只在**部分**重分配模式下成立（handle 消失/handle 冲突两种都已变异验证、确实响亮）；
"handle 整体转移给另一个真实实体、原实体拿到全新 handle"这一种子模式**没有被验证过**，
且实测确实静默（1 hit，指错对象，零信号）。

**为什么不阻断**：① 今天的 5 条真回归（A-11 每次都 100% 触发的坐标漂移）已经被这个锚彻底堵死；
② 新暴露的方向要求"未来 DXF 重写 + 恰好把旧 handle 挪给另一实体"这种特定组合，发生概率远低于
旧方案"任何一次 A-11 式坐标微调都 100% 触发"；③ 不是本单引入的新问题，是**旧问题的收窄**
（收窄本身是净改善）。

**建议**（不代做）：`_wall_by_face_lines` 除了断言 `len(hits)==1`，可以再加一条**廉价的第二特征
校验**（比如同时核对 `axis`/`face_lo`/`face_hi` 这类不太可能被 handle churn 一起带走的字段），
把"1-hit-但-错对象"这个方向也变成能被观测到的信号。下次触碰这个 helper 时补。

### 不阻断-2：`SM25_DEFERRED_CAVITY_COUNT` 是被独立反例证实的代理量，且拆分成本比施工方自估更高

**证据**：§一-3b（独立构造 `FakeAudit`，非转引）。**机械结论**：拆成 per-code 两个钉
（`SM25_DEFERRED_F157_UNAVAILABLE_COUNT` / `SM25_DEFERRED_F153_FORM_B_COUNT`），且该拆分
**必须同时touch两个消费者文件**（不只是声明点一个文件——声明新常量若无人引用只是摆设）。

**为什么不阻断**：今天的真实数据构成诚实验证为 2+2（与声明点一致），当前不存在"已经被骗"
的情况；本单要修的两个真回归已经修复，全量已绿。

**要求**：登记为必须在**下一次任一成因（F-157 / F-153 form B）单独发生变化之前**完成的
前置动作——否则那次变化的"退休"或"再扩大"都可能被这个代理量悄悄吞掉，回到上一轮"两个文件
各说各话"的同一类风险（只是换了个更隐蔽的载体）。

---

## 未复现项清单

- `test_as_measured_facts_layer.py` 的读数仍未逐条独立变异验证（本单未触碰该文件，上一轮
  已记为不阻断，本轮同样未补做，非强制项，结转）。
- `_wall_by_face_lines` 在"1-hit-但-错对象"这个具体子方向上的判别力仍是**已证实的缺口**
  而非"未测"——已单独列为不阻断-1，不重复计入本清单。

---

## 你自己造的同形输入是什么、为什么它同形

1. **handle 冲突/转移三件套**（§一-3a）：与施工方唯一做过的"handle 指向不存在值"（DEAD/BEEF）
   同属"DXF handle 未来可能变化"这一个假设空间，但覆盖了施工方**没有**覆盖的子象限——
   handle 精确转移到另一真实实体。同形之处：都是"这个锚失效的具体机制"，用真实 sm25 数据
   （不是任何测试文件里的合成数据）构造，直接调用被测的 `_wall_by_face_lines` 函数本体。
2. **`FakeAudit` 成因构成反例**（§一-3b）：与施工方"per-code 拆分"的备选方案讨论的是同一个
   不变量（"两个成因各自都还在"），但施工方只是**叙述**了这个退化面存在，没有**构造**一个
   会触发它的具体输入去验证"锁到底红不红"。我构造的输入满足复核单原话的要求——"count 仍是
   4、但成因组合已经变了"——直接调用 `deferred_cavities`/`failures_not_from_deferred_cavities`
   两个真实生产函数（不是重新实现一遍逻辑去验证逻辑，是拿真实函数喂假数据）。
3. **反查坐标数值本体的全仓扫描**（§三-3b）：与施工方的"按 ID 命名规则 `w_[xy]_...` 正查"
   同属"找同一病族的其他受害者"这个目标，但换成完全不依赖该命名假设的角度——直接用 A-11
   实际改掉的 16 个原始坐标数值反查全仓——如果施工方的正查漏掉了某种不遵循 `w_[xy]_` 命名
   规则的坐标派生 ID（比如某处直接拼 `f"{axis}{const}"` 不加 `w_` 前缀），这套反查能抓到，
   而施工方的正查抓不到。两套口径命中集合一致，互相印证。
