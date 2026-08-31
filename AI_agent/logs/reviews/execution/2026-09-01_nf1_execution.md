# 执行档 · NF-1：空骨架产物不再被认成合法 as-drawn 计划

- **日期**：2026-09-01 · **施工方**：Claude 家族施工席 · **单子**：[`request/2026-08-30_nf1_empty_skeleton_micro_dispatch.md`](../request/2026-08-30_nf1_empty_skeleton_micro_dispatch.md)
- **基线**：`58bb59f`（未提交，按禁令 4）
- **改动路径（3 个，⛔ 均未提交）**：
  - `src/agent/reading/as_drawn/schema.py`（+18 / -5）
  - `tests/test_f97_vector_contract.py`（+77 / -6）
  - `tests/test_o22m1_as_drawn_producer_types.py`（+31 / -13）
  - ⚠️ `git status` 另有两个 `??`：`src/agent/correction/decision_executor.py` / `decision_schema.py` —— **GLM 席位在飞的活，我没碰、不提交**（禁令：别碰别人的文件）。

---

## 〇、开工自检（单子要求）

### 1. HEAD
```
$ git rev-parse HEAD
58bb59f28d785139b48df642783db2c4db7ab537   ✅ = 58bb59f
```

### 2. 复核方三条读数——我自己复现（⛔ 未转引）

**复现方式**：先只做「schema 改必填 + test_f97 六处注入面线」，**未翻 pin、未加我的两条新测**，此时跑两个文件：

```
$ python -m pytest -n 4 tests/test_f97_vector_contract.py tests/test_o22m1_as_drawn_producer_types.py -q
130 passed, 2 failed
FAILED tests/test_o22m1_...::test_the_declared_skeleton_is_still_recognised
FAILED tests/test_o22m1_...::test_a_hybrid_that_also_looks_legacy_is_still_ambiguous_not_consumed
```

- **(a) 79 F-97 全绿（130 passed）** —— ✅ 复现。130 passed 正是此中间态；`test_f97` 当时 79 条全绿（我事后加 2 条 NF-1 正例 ⇒ 现 81 条，见下）。
- **(b) 唯二红 = 自钉的两条 pin** —— ✅ 复现。两条红都在**模块 1 自己的测试文件**里、都是作者钉死旧边界的 `..._is_still_...` 测试；**都是「翻 pin」的预期红，不是撞锁**：其中第二条的承重断言 `contract_id == CONTRACT_UNKNOWN` **本来就已经绿**，只有陈旧的 `reason` 断言（`AMBIGUOUS` / legacy）失败。
- **(c) 裸骨架 → 响亮 UNKNOWN** —— ✅ 复现，reason 逐字一致：
  ```
  $ python -c "...classify_vector_json({'schema':'as_drawn_plan_v2','observations':{},'declarations':{},'hypotheses':{}})"
  skeleton -> unknown / None
  reason: declares schema='as_drawn_plan_v2' but no registered contract has that value with a matching key set; top-level keys=[...]
  ```

三条全部自证成立 ⇒ 不触发 §五「必停」，继续施工。

---

## 一、逐条施工 + 读数

### schema.py（承重改动）
`ObservationsV2.face_lines` 由 `= Field(default_factory=list)` 改为**必填无默认**（`face_lines: list[FaceLineV2]`）。
- **键必须在**（生产者 `assemble()` 无条件写它 ⇒ 缺键只可能是手造/损坏 ⇒ 响亮 UNKNOWN）；
- **空列表仍合法**（`face_lines: []` = 诚实读空图，仍路由成 `as_drawn_plan`）。
- 同步改了 `AsDrawnPlanV2` 里那句「空骨架 still validates」的**过期 docstring**（原文断言骨架仍合法，现已不成立）。

行为验证（⛔ 分类只跑 `AsDrawnPlanV2.model_validate` 这一层类型）：
```
skeleton {observations:{}}            -> unknown / None            （响亮，reason 点名 schema）
empty    {observations:{face_lines:[]}} -> as_drawn_plan / KNOWN_NOT_CONSUMED
```

### test_f97_vector_contract.py（我拥有的文件）
- 新增模块级 `_min_observations()`：一条 **14 字段最小真实面线**（`gaps: []`、两条 run、区间全钉长度 2）。
- **6 处** `"observations": {}` → `_min_observations()`（这些夹具断言的是**识别/歧义**，需要生产者能真产出的载荷）：
  `test_b3_as_drawn_plan_is_known_but_not_consumed` · `test_b3_as_drawn_raises_and_says_known_not_unknown` · `test_b3_double_match...` · `test_b3_ambiguous_file_fails_loudly` · `test_r2_registered_schema_plus_legacy...` · `_COMPLETE_DECLARATIONS` 里 `as_drawn_plan_v2` 那格。
- **新增 2 条 NF-1 正例**（锁 §四 验收 1 的两半、互为对撞）：
  `test_nf1_missing_face_lines_key_is_a_loud_unknown`（缺键→UNKNOWN）· `test_nf1_empty_face_lines_list_is_still_as_drawn_plan`（空列表→仍 as_drawn）。
- ⛔ **未动 `:699/:700`（原 `:629/:630`）两处故意残缺的 malformed 夹具**——它们内容逐字未变（`{"observations": {}}` / `{"observations": {}, "declarations": {}}`），只因我在文件上方加了行、行号平移（§五「只记不停」项）。

### test_o22m1_as_drawn_producer_types.py（模块 1 自建，§二.3 授权翻 pin）
- **翻 pin #1**：`test_the_declared_skeleton_is_still_recognised` → `test_the_declared_skeleton_is_now_a_loud_unknown`，断言骨架 → UNKNOWN 且 reason 点名 schema。
- **翻 pin #2**：`test_a_hybrid_..._is_still_ambiguous_not_consumed` → `test_an_empty_skeleton_hybrid_that_looks_legacy_is_loud_unknown_not_consumed`。**承重不变量原样保留**（空骨架 hybrid 仍 ⛔ 不被 CONSUME，F-97 未重开），只把已过期的 `AMBIGUOUS/legacy` reason 断言换成新路径（BLK-A malformed → UNKNOWN）。真·双匹配歧义（**真实产物** + `strokes`）的覆盖仍锁在 test_f97 的 R2/R5/double-match（现带真实面线）。

### 全绿
```
$ python -m pytest -n 4 tests/test_f97_vector_contract.py tests/test_o22m1_as_drawn_producer_types.py -q
134 passed
```
（134 = 翻 pin 前 132 + 我的 2 条 NF-1 正例。）

---

## 二、验收对账（§四 四项）

| # | 验收项 | 结果 |
|---|---|---|
| 1 | 缺键→UNKNOWN 响亮；空列表→仍 `as_drawn_plan` | ✅ 两半各一条测试锁死，互为对撞（拒空列表则第二条红；放行骨架则第一条红）|
| 2 | 两文件 F-97 侧全绿、翻完 pin 全绿 | ✅ `134 passed`（`-n 4`）|
| 3 | `git diff --numstat` 证 F-97 文件无一行断言改动 | ✅ 见下 |
| 4 | 列全改动路径（⛔ 不提交）| ✅ 见抬头三条 |

**§四.3 机械证据**——test_f97 文件里被删/改的 `assert` 行 = **0**：
```
$ git diff -- tests/test_f97_vector_contract.py | grep '^-' | grep assert
  (无)
$ git diff --numstat -- src/.../schema.py tests/test_f97... tests/test_o22m1...
18  5   src/agent/reading/as_drawn/schema.py
77  6   tests/test_f97_vector_contract.py
31  13  tests/test_o22m1_as_drawn_producer_types.py
```
test_o22m1 被删的 3 条 assert 全是**两条 pin 的翻转**（§二.3 授权），不是 F-97 断言。

**禁令自查**：① F-97 断言零改动 ✅ ② 空列表未被拒（有正例锁）✅ ③ 699/700 未动 ✅ ④ 无 git add/commit、无 `pip install -e .`、无 `-n auto`、无全量、跑测全 `-n 4` ✅ ⑤ 未碰已落库产物 / `canonical_bytes` schema 面（schema.py 是 reading 侧类型、不进哈希；三件套跟踪产物本就带 `face_lines`，o22m1 对三者的校验全绿 = 字节仍可验）✅ ⑥ 未碰 judge/correction/case_tests ✅。

**旁证无隐红**：`test_o22m2/m3/m4` 一并跑过 `76 passed`（它们引用本 schema/detector）——我这次 schema 改动**没有把既有锁弄红**。

**计数与裁决书出入（§五「只记不停」）**：单子 §二说「test_f97 里 6 处 + 模块 1 自建 2 处」注入面线；我实际 = **test_f97 注入 6 处 + 模块 1 注入 1 处（426 那条 hybrid 我选择保留为真双匹配→注入）+ 模块 1 翻 pin 2 处**。差异根因见下「最薄弱处」。行号也因加行整体平移（629/630→699/700）。

---

## 三、我自认最薄弱的一处 + 希望复核方重点打哪

**最薄弱**：模块 1 第二条 pin（原 `..._hybrid_..._is_still_ambiguous`）我选择**翻成「空骨架 hybrid → malformed UNKNOWN」**，而不是像 test_f97 那样**注入真实面线保住一条 o22m1 自己的真·歧义测试**。我的判断是：真·双匹配（真实 as_drawn 产物 + legacy）→ AMBIGUOUS 的覆盖已在 test_f97 的 R2/R5/double-match 里（且我已给它们注入真实面线），所以 o22m1 翻这条不丢全局覆盖。但这是个判断，不是机械事实。

**请复核方重点打三处**：
1. **覆盖是否真没丢**：翻完两条 pin 后，「真 as_drawn 产物 + strokes → AMBIGUOUS 且不被 CONSUME」这条不变量，是否仍有至少一条**走真实入口**的锁把它咬住？（我认为 test_f97 R5 `test_r5_complete_declaration_plus_legacy_is_still_ambiguous` 带注入面线后仍锁着，请核。）
2. **空列表正例有没有牙**：`face_lines: []` 会不会太平凡、是「band_collapse 式」的假绿（没真正区分「缺键 vs 空列表」）？对撞检查：把 schema 改回带默认，`test_nf1_missing_face_lines_key_is_a_loud_unknown` 是否立刻变红？（我本地口算会红——因为骨架又会被认成 as_drawn；请复核方实测这条变异。）
3. **最小面线是否只是「过了类型、过不了门」**：它满足 `FaceLineV2`（strict + extra=forbid）但我**没让它过 `validator/checks/as_drawn.py` 那 11 道门**。分类路径只跑类型不跑门 ⇒ 我判定无害；但若有任何被我漏看的消费者会拿这条夹具去跑门，就会暴露。请核这条面线是否会流到跑门的路径上。

**另**：我**没跑全量**（禁令）。「缺键骨架被认成 as_drawn」这个旧行为是否在**别处**还有锁依赖它（我只查了 tests/ 里引用 schema/detector 的 4 个文件），需要有全量权限的复核方兜一次底。
