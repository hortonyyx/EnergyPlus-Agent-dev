# 交件 · A-11 返工 1（GLM 家族施工席）

- **施工方**：GLM · **工作目录**：`/tmp/a11_rework_glm` · **分支**：`wt/09.05k_a11_rework`
- **基点**：`83326ba6`（上一轮 HEAD）· **本轮 commit**：`580f8b67`（根因 A）→ `8d925e4f`（根因 B）→ 本交件
- **派工单**：`AI_agent/logs/reviews/request/2026-09-05k_A11_rework1_dispatch.md`
- **上一轮裁决**：`AI_agent/logs/reviews/verdict/2026-09-05i_A11_gt_1mm_crossreview_claude.md`

## 头条：独立全量绿

```
$ cd /tmp/a11_rework_glm && python -c "import src.agent.judge.as_measured as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
/tmp/a11_rework_glm/src/agent/judge/as_measured.py
3863 passed, 2 skipped, 13 xfailed, 211 warnings in 476.53s (0:07:56)
```

- `m.__file__` 落在本工作目录（承重不变量成立；`.pth` 只是只记一条的代理量）。
- **收集数自己数的**（⛔ 没照抄派工单推算）：`--collect-only` → **3878 tests collected**。
  逐位闭合：3863 + 2 + 13 = 3878 ✓。本单零增删测试（f156 一条测试**改名**不改变计数；
  `tests/deferred_projection_ledger.py` 无 `test_` 前缀不被收集）。
- 交叉验证：上一轮 3858 passed + **5 failed** + 2 + 13 = 3878 ⇒ 本轮修好恰好那 5 条（+5 passed）。

## 病族正面回应（派工单原话要求）

> 「把坐标编进标识符，坐标一动，锁就悄悄失效——ID 是坐标的**影子**，不是被守的那件事。
> 失效方式还是**静默的**（no-op，不报错）。」

接受这个命名，并且本轮把它的两个半边都处理了：

1. **影子半边**：锚从「坐标的影子」（id 字符串里嵌的 `52401`/`121599`）换成「被守的那件事
   自己的身份」——DXF face-line handle（`13AE`/`13AD`、`136F`/`1371`）。A-11 只改坐标、
   ⛔ 不改 handle，所以锚不再随规整漂移。
2. **静默半边**：`_wall_by_face_lines` **断言恰好命中 1 条**——锚失效时的形态不再是 no-op，
   而是响亮的 `AssertionError`（「the fixture is broken, not the data」）。**变异实测**：把锚
   指向不存在的 handle（`DEAD`/`BEEF`），fixture2 立即红：
   ```
   AssertionError: face-line lookup (('DEAD',), ('BEEF',)) matched 0 walls (expected exactly 1)
   ```
   即「这类缺陷修好了」的证据不止是三个例子变绿——是**静默失效这条路本身被堵死**
   （失配必响）。

## 一、根因 A（3 条红）：修法与注入证明

改动全部在 `tests/test_b1_projection_bridge_fixtures.py`（59+/26−，commit `580f8b67`）：

- `B1_WALL`（坐标嵌 id）→ `B1_WALL_FACE_LINES = (("13AE",), ("13AD",))`；fixture 5 的
  `w_y_50000_52400_121599_140000` → `W2_WALL_FACE_LINES = (("136F",), ("1371",))`。
- 新增 `_wall_by_face_lines(view, face_lines)`：按 `face_line_ids_lo/hi` 匹配，**断言恰好
  1 条**；无 face line 的墙（合成 ghost probe）用 `.get(..., ())` 安全不匹配。
- 新增 `_restamp_wall_id(wall)`：改坐标后按生产者自己的 id 规则重派生标签（消灭手写
  `f"w_x_99430_100630_{...}_88800"` 半硬编码）。
- `_f1_with_endpoint_remainder` 改为 `wall["along_min"] += remainder_units`（在数据当前值
  上加，连 `52400` 这个数都不再钉死）。

### 验收 #2：注入的缺陷**真的被注入了**（⛔ 不是「测试绿了」）

三重证据，全部机械可查：

1. **读回证明**：fixture2 现在从**构造出的墙**上读回 `along_min` 再过判据——
   ```python
   view, upm = _f1_with_endpoint_remainder(2)
   moved = _wall_by_face_lines(view, B1_WALL_FACE_LINES)["along_min"]
   assert abs(moved - 51200) == 1202 > 1200 + 1  # the criterion, mechanically,
   # read off the CONSTRUCTED wall -- proof the +2 remainder was really injected
   ```
   这条断言**只有在 +2 真的落进数据**时才可能通过（读回的就是被改的字段）。
2. **命中证明**：三处定位共用 `_wall_by_face_lines` 的 `len(hits) == 1` 断言——目标墙没
   找到时是 KeyError 级的红，no-op 在结构上不可达。
3. **变异证明**（见上）：故意弄断锚 → 响亮红。上一轮的失效模式（静默 no-op）已无法再现。

本文件 16 passed。附带说明：fixture1 的两条测试上一轮虽绿、但其注入同样 no-op
（remainder=1 时改空），是**同形假绿**——helper 修好后一并恢复真实语义（52401/52400
两版都 cut 14 的对照仍然成立）。

## 二、验收 #3：全仓同形扫描（命令 + 原文输出）

病族操作定义：**用「坐标派生的标识符」或「坐标字面量」定位对象**。先盘点生产侧 id 派生
规则确定外延，再逐一扫。

### 命中与判读

```
=== 1) coordinate-stamped WALL id literals anywhere in tests/ + scripts/ + src/ ===
$ grep -rnE "w_[xy]_[0-9]+_[0-9]+_[0-9]+_[0-9]+" tests/ scripts/ src/ --include="*.py"
tests/test_o21d_exclusion_gap.py:24:  ``w_x_99430_100630_52401_88800``, delta=1) -- so reddening it is CORRECT, and
tests/test_b1_projection_bridge_fixtures.py:134:#: suite used before (``w_x_99430_100630_52401_88800``) has the coordinates
tests/test_b1_projection_bridge_fixtures.py:143:#: ``w_y_50000_52400_121599_140000`` snapped ``121599 -> 121600``).
tests/test_as_measured_facts_layer.py:1063:    good = dict(id="w_x_0_1200_0_1000", axis="x", face_lo=0, face_hi=1200,
```

4 命中全非活定位：前两条是**注释里的叙述**（o21d 记录 A-11 前的缺陷形状 / 本轮新写的
锚定纪律说明），第三条是**合成构造**（id 与字段同源自洽、不查找任何数据对象）。

```
=== 3) hardcoded OPAQUE ids (sha256-of-coordinates, prefix:16hex) ===
$ grep -rnE "\"(cavity|line|edge|ring|room|zone|face|footprint):[0-9a-f]{16}\"" tests/ scripts/ src/ --include="*.py"
（零输出，exit=1）
=== 3b) any 16-hex-char quoted literal ===
（零输出）
```

cavity / boundary-edge id 是坐标的 sha256[:16]（`_boundary_opaque_id`，坐标的哈希=隐性
坐标派生）——**没有任何测试硬编码它们**。这正解释了为什么 o21d/f156 的老规矩是
「⛔ No cavity id appears in any criterion」：那条纪律早就防住了这个病族的哈希分支。

```
=== 4) consumers that LOCATE an object by comparing id against a STRING LITERAL ===
$ grep -rnE "\.id == \"|\.id != \"|\[\"id\"\] == \"|\[\"id\"\] != \"|origin_id == \"|cavity_id == \"|edge_id == \"|zone_id == \"|id == f\"w_" tests/ src/ scripts/ --include="*.py"
（70+ 命中，全文见上轮执行记录；逐条判读后分三类——）
  · 语义名：z1 / G5 / G8 / G10 / plan-F1 / W-F1-N-1 / O1 / wall-partition / w_right / w_mid_h
    / F1-z3 / L012 / L00 / South_view / F1_A —— 测试自造或数据声明的语义标签，不含坐标；
  · DXF handle：test_gt_revisions_and_as_signed.py 的 "1A3"/"1A2"（AsMeasuredFaceLineV1.id
    的类型就是 DxfHandle，schema 原文 "the DXF handle; unique within a view"）——
    这正是本轮采纳的正确形态；
  · handle 派生 revision id：test_gt_facts_staging_sm25.py / test_answer_compiler_profiles.py
    的 "rev-13ad" 等 —— handle 前缀，且用 next() 无默认定位，失配 = StopIteration 响亮红，
    ⛔ 不是静默 no-op（且这两个文件上一轮已随 A-11 更新并经复核确认）。
```

```
=== 6) coordinate-stamped ids inside test JSON fixtures ===
$ find tests -name "*.json" -exec grep -lE "w_[xy]_[0-9]+_[0-9]+_[0-9]+_[0-9]+" {} +
（零输出，exit=1；tests/ 下共 24 个 json fixture）
=== 8) LOCATING real-data objects by COORDINATE literals (not ids) ===
$ grep -rnE "\[\"(along_min|along_max|face_lo|face_hi|const)\"\] == [0-9]+|\.(along_min|face_lo|const) == -?[0-9]" tests/ --include="*.py"
tests/test_gt_revisions_and_as_signed.py:192:    assert h3.const == 2010          # 2000 + 10
tests/test_gt_revisions_and_as_signed.py:193:    assert h2.const == 1240          # untouched
tests/test_gt_revisions_and_as_signed.py:715:    assert face.axis == "x" and face.const == 5000, (
（3 命中全是 handle 定位之后的【读数断言】——定位键分别是 "1A3"/"1A2"/"1A1"，坐标比较
  是在已找到的对象上验证值，⛔ 不是用坐标找对象）
=== 10) coordinate TUPLE literal locators ===
$ grep -rnE "next\([^\n]*== \(-?[0-9]+, ?-?[0-9]+\)" tests/ --include="*.py"   （零输出）
$ grep -rnE "(if|while) [^\n]*== \(-?[0-9]+, ?-?[0-9]+\)" tests/ --include="*.py" （零输出）
```

### 扫描结论

**活的同形缺陷 = 0**（除本单已修的三处）。两项**非缺陷近邻**具名登记（B 层）：

1. `tests/test_o21d_exclusion_gap.py:24` docstring 叙述的是 A-11 **前**的真实 substrate 形态
   （「sole surviving ledger entry … 28.683212 m² … delta=1」）。A-11 后该 ledger 已空
   （实测见 §三），叙述陈旧但锁本身是 RULE 型（fixture 自造、不读那个 ledger 条目），
   全量绿。下次触碰该文件时补一句「A-11 后注」即可。
2. `tests/test_as_measured_facts_layer.py:1063` 合成墙 dict 的 id 与字段一致性靠手维护
   ——是构造不是定位，无失效面；仅记录存在。

## 三、根因 B（2 条红）：正面裁决 + 单一声明点

### 正面裁决：F-153 form B **是本批已知债**，不是规整暴露出的真错 —— 不触发停下上报

裁决依据是**两侧实测**（不是转述复核方）：

```
PRE-A11  (git show c7c6831a:.../facts/as_measured.json):
  B-1 wall along_min = 52401（0.1 mm off siblings）
  boundary_ring_losses = 1 条:
    {"reason": "endcap_const_not_a_measured_parallel_face",
     "span": {"axis": "y", "const": 52401, ...}, "area_units2": 2868321200}
POST-A11 (83326ba6 落盘):
  B-1 wall along_min = 52400, boundary_ring_losses = 0 条
  reconcile_boundary_basis -> 2 条 facts_projected_ring_is_not_the_converter_zone
    (F1-z4 / F1-z5, symmetric_difference_units2=1182000 each)
```

同一个 endcap 几何差：A-11 前让 286.8 m² 腔**无法成环**（producer-written loss，由
`tests/test_o21d_exclusion_gap.py` fail-loud 锁着——其 docstring 明文认领「the sole
surviving ledger entry is F-153 form B … delta=1」）；A-11 把墙端贴上 1 mm 格点后腔闭合成
两个真房间、环**可比了**，同一差以 2×1182000 units² symdiff 浮现。**同一缺陷、可见度
升级**——snap 没有制造它，只是把「无法比较」换成「比较后不等」。

### 单一声明点：`tests/deferred_projection_ledger.py`（新建，111 行）

裁决全文（是不是已知债 / 谁销 / 什么条件下销 / membership 按当次 run 计算 ⛔ 不是名单）
全部写在该模块 docstring 与常量注释里。两个测试文件**只 import、零本地定义**：

- `SM25_DEFERRED_CAVITY_COUNT = 4`（= 2×F-157 `..._unavailable` + 2×F-153 form B
  `..._is_not_the_converter_zone`）——读数钉；任一上游修复落地时它红（4→2→0），在**同一
  commit** 里更新此处一次。
- `deferred_cavities(audit)`：membership 从**当次 audit 自己的 structural_failures** 计算，
  修复落地自动清空。
- `failures_not_from_deferred_cavities(audit)`：零阈值半边——豁免之外**一个新 failure 都
  不许有**。

### 验收 #4：改后两处原文

`tests/test_f156_ring_from_intersection.py`（零阈值测试，原 `residuals == []`）：

```python
    audit = reconcile_boundary_basis(facts, report)
    deferred = deferred_cavities(audit)
    assert len(deferred) == SM25_DEFERRED_CAVITY_COUNT  # 2 F-157 + 2 F-153 form B
    assert failures_not_from_deferred_cavities(audit) == []  # nobody else is
    # merely "close enough"                                          -- ⛔ no band
    assert audit.mismatches == []
    # and the comparison really ran on real rooms, ⛔ not on an empty set
    assert len(audit.pairings) == 27
    assert audit.paired_edges == 108
```

`tests/test_boundary_condition_facts.py`（原 `assert len(deferred) == 4`）：

```python
    deferred = _deferred_cavities(audit)
    assert len(deferred) == SM25_DEFERRED_CAVITY_COUNT
    assert _failures_not_from_deferred_cavities(audit) == []
```

两处 import 自同一模块（f156 里原先**定义了但从未使用**的 `_deferred_cavities` 死 helper
已删——它正是两文件漂移的机制：改一个文件时另一个文件的本地副本看起来已经「有口径」）。

### 判别力未调松（变异实测，双向）

- 少一个：把钉改成 `SM25_DEFERRED_CAVITY_COUNT - 1` → `AssertionError: assert 4 == (4-1)` 红。
- 多一个：对干净 zone 注入 1 mm 扰动（第 5 条 projected-ring failure）→ `deferred == 5 ≠ 4` 红，
  且 `failures_not_from_deferred_cavities` 仍为空（新差不会被误报成「未解释」也不会藏进豁免）。

### 牙测试的步长：0.1 mm → 1 mm（改名 `..._by_one_millimetre_reddens`）

原测试扰动 1 unit（0.1 mm）期待变红。**实测：0.1 mm 扰动后 `named == 0`**——A-11（用户
终裁）把比较搬到 1 mm ingest 网格上，zone 顶点先贴格点再比，0.1 mm 的移动在比较域
**不可表示**（这正是 snap 的语义，⛔ 不是容差）。最小**可表示**的扰动是一个格步 = 1 mm：
`step = 10.0 / UNITS_PER_METRE`，实测 1 mm 扰动 → `named == 1` 红。测试名与 docstring 同步
改（名字不再说谎）；「若门容忍任何东西，最小可表示扰动就会通过」的判别力语义原样保留。

## 四、验收 #5：上一轮已过审的七件不退化

机械证据：`git diff 83326ba6..HEAD -- src/ case_tests/` **零字节改动**；改动面 =
4 个文件、全在 `tests/`（`deferred_projection_ledger.py` 新建 111 行 +
`test_b1_projection_bridge_fixtures.py` 85± + `test_boundary_condition_facts.py` 60± +
`test_f156_ring_from_intersection.py` 74±，`--stat` 原文见 commit `8d925e4f`）。⇒

| 已过审件 | 证据 |
|---|---|
| 规整作用域（几何坐标 vs 配置量） | `as_measured.py` 零改动（`_geom_units`/豁免表原样） |
| 判据能变红（摘 snap 即红） | snap 门零改动；上轮复核的 monkeypatch 路径不受 tests 改动影响 |
| 哈希/基线连带更新 | `case_tests/` 零改动 ⇒ `as_measured.json`/`revisions.json`/`content_sha256` 原样 |
| `as_measured.py` 单位段落 | 文件零改动 |
| 单一声明点 `INGEST_RESOLUTION_UNITS` | 文件零改动（本单新增的是**测试侧** deferred 声明点，两者不相干） |
| zone 侧规整（必须做、未调松） | `answer_compiler.py` 零改动；`_projected_facts_ring` 比较路径原样 |
| sm21 拒做 / sm24 facts 首次生成 | `case_tests/` 零改动（sm21 仍无 request.json、sm24 三件套原样） |

## 五、验收 #6：无占位符

本交件逐段落盘、零 `<!-- ...PLACEHOLDER -->`、零「待补」；全量数字来自本轮真实运行
（任务输出原文已贴 §头条）。硬纪律对账：未跑 `pip install -e .`（`m.__file__` 落本树为证）、
未 `git add -A`（逐文件 add + `--cached --numstat` 核对）、未碰 `score_service.py` /
旧层 `gt/*/gt.json` / `src/agent/correction/`（diff 为空为证）、分段提交三段
（`580f8b67` 根因 A → `8d925e4f` 根因 B → 本交件）。

## 最薄弱一处

**`SM25_DEFERRED_CAVITY_COUNT = 4` 把两个不同成因（F-157 ×2 与 F-153 form B ×2）压进了
同一个计数钉。**取舍是故意的（单一数字 = 两文件不可能再各自表态），但它有一个已知的
退化面：上游只修**其中一个**成因时，这条锁红的是「4 变 2/3」，**不直接告诉你是哪个成因
销的**——分辨要靠 structural_failures 里的 code 前缀，而那一步是人工的。若要更细可拆成
`per-code` 两个钉（`..._unavailable == 2` 与 `..._is_not_the_converter_zone == 2`），
代价是把「4 = 2+2」的构成也写死、将来每次修复要改两处读数。本轮维持单钉 + 声明点内
写明构成与销账条件；若复核方认为 per-code 更值得，改动只在 `deferred_projection_ledger.py`
一个文件内。次薄弱（一并交代）：`_wall_by_face_lines` 的 handle 锚在「转换器未来重写
DXF、handle 重新分配」的世界里也会失效——但那时它是响亮的红（已变异验证），不是静默
no-op，属于锚的寿命问题而非病族复发。
