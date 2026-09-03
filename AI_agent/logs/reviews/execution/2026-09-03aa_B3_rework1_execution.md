# B3 立面腿 返工 1 · 执行档

- **日期**：2026-09-03 · **施工方**：GLM 家族施工席（同一施工方）
- **返工单**：[`2026-09-03aa`](../request/2026-09-03aa_B3_rework1.md)
- **上一轮裁决**：[`2026-09-03z`](../verdict/2026-09-03z_B3_v2_crossreview_gpt.md)（REWORK / 阻断 3 / 不阻断 1）
- **工作目录**：`/tmp/b3_r2_glm` · **分支**：`wt/09.03v_b3_r2`
- **基线**：`917df4b`（09.03v_T8_execution_report）→ **本轮终态**：`abbf771`
- **分段提交**（返工单 §五）：

| commit | 内容 |
|---|---|
| `2346961` | B-1：主锁读调用时 `CONTRACTS`，变异测试真调主锁（R1-a/b/c）|
| `d6c30f0` | B-2：span 等值缺口成为随 bundle travel 的命名债（R2-b/c）|
| `7c63216` | B-3：两把 T7 锁机械守住免模型出口（R3-a/b）|
| `abbf771` | 补强：span 债指针必须解回冻结产物节点（见「最薄弱一处」）|

**开工自证**（返工单「开工自检」节，原文输出）：

```text
$ cd /tmp/b3_r2_glm && pwd && git log --oneline -1 && git status --porcelain
/tmp/b3_r2_glm
917df4b 09.03v_T8_execution_report
A  AI_agent/logs/reviews/request/2026-09-03aa_B3_rework1.md
$ python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)"
/tmp/b3_r2_glm/src/agent/correction/evidence_contract.py
```

（暂存的新文件 = 主控预置的返工单本身，随第一个工作 commit `2346961` 落库。）

---

## §六 #1 · 主锁自己会红（B-1 / R1-a · R1-b · R1-c）

**改动**（`tests/test_o22m1_as_drawn_producer_types.py`，commit `2346961`）：

1. **R1-a** `_wire_sets` 去掉默认参数，签名改为 `_wire_sets(contracts)`，docstring
   逐字抄了参照锁警告的那句「为什么」：

   ```python
   def _wire_sets(contracts: tuple[ContractSpec, ...]) -> tuple[set, set]:
       """...
       ⚠️ Explicit parameter, NO default -- a module-level default would bind
       ``CONTRACTS`` at def time and neuter the monkeypatch the mutation test
       relies on (the exact trap the reference lock ``_wiring_sets`` in
       ``test_o22m7_evidence_wiring`` warns about in its docstring; B-1 of the
       2026-09-03 rework was this file copying that lock's shape but re-importing
       the very defect its docstring was written to prevent)."""
   ```

   主锁第一行改为 `_wire_sets(vector_contract.CONTRACTS)` —— **调用时**取模块属性。
2. **R1-c** 常驻变异测试删掉另抄的相等式，改为**直接调用主锁**：

   ```python
   monkeypatch.setattr(
       vector_contract, "CONTRACTS", vector_contract.CONTRACTS + (smuggled,)
   )
   with pytest.raises(AssertionError):
       test_every_adapt_wire_is_a_registered_contract_with_a_real_entry_point()
   ```

**R1-b 独立变异读数**（复核方同型手法：塞第四个 `ADAPT` 契约、直接跑主锁；
命令与输出原文）：

```text
$ python - <<'EOF'
import importlib.util
import src.agent.correction.evidence_contract as m
print("MODULE_FILE=", m.__file__)
assert m.__file__.startswith("/tmp/b3_r2_glm/"), "WRONG TREE"

import src.agent.reading.vector_contract as vector_contract
from src.agent.reading.vector_contract import ContractSpec, Disposition

spec = importlib.util.spec_from_file_location(
    "t_o22m1", "tests/test_o22m1_as_drawn_producer_types.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

T.test_every_adapt_wire_is_a_registered_contract_with_a_real_entry_point()
print("MAIN_LOCK_ON_REAL_CONTRACTS=GREEN (premise holds)")

smuggled = ContractSpec(
    "contract_smuggled_fourth_wire", Disposition.ADAPT,
    lambda raw: False, "fourth ADAPT mutation probe")
vector_contract.CONTRACTS = vector_contract.CONTRACTS + (smuggled,)
try:
    T.test_every_adapt_wire_is_a_registered_contract_with_a_real_entry_point()
    print("MAIN_LOCK_AFTER_FOURTH_ADAPT_MUTATION=GREEN  <-- B-1 STILL BROKEN")
except AssertionError as e:
    print("MAIN_LOCK_AFTER_FOURTH_ADAPT_MUTATION=RED")
    print("ASSERTION_MESSAGE=", str(e)[:200])
EOF
MODULE_FILE= /tmp/b3_r2_glm/src/agent/correction/evidence_contract.py
MAIN_LOCK_ON_REAL_CONTRACTS=GREEN (premise holds)
MAIN_LOCK_AFTER_FOURTH_ADAPT_MUTATION=RED
ASSERTION_MESSAGE= evidence chain quietly grew: {'contract_smuggled_fourth_wire', 'as_drawn_plan', 'as_drawn_elevation_v0'} vs registered {'as_drawn_plan', 'as_drawn_elevation_v0'} -- every wire must be registered in _ADAPTING_WIRES...
```

主锁对真实 `CONTRACTS` 绿（前提自证），第四 `ADAPT` 变异下**主锁本体**红。
对照上一轮复核读数 `MAIN_LOCK=GREEN_AFTER_FOURTH_ADAPT_MUTATION` —— 已翻红。

---

## §六 #2 · 主锁读的是调用时的 `CONTRACTS` + 同型扫描

见 §一 R1-a：⛔ 默认参数已不存在，取值点是 `vector_contract.CONTRACTS`（模块属性，
monkeypatch 可达）。

**顺手 grep**（返工单验收 #2 第二半），两层：

```text
$ grep -rn "def [a-zA-Z_]*(.*=[^)]*CONTRACTS" tests/ src/ --include="*.py"
（无输出，exit 1 —— 全仓零命中）
```

⇒ 「默认参数绑死 `CONTRACTS`」在全仓是**唯一一处**（即 B-1 修掉的那处）。
第二层扫其余「默认参数引用模块级名字」的形态（标量/哨兵类）：

```text
$ grep -rn "def [a-zA-Z_]*([^)]*= *[A-Z_][A-Z_0-9.]*\b" tests/*.py | grep -v "\.patch\|None\|True\|False"
tests/test_c2_vg_visibility.py:669:    def expect(code, ring, direction=SOUTH, tol=TOL):
tests/test_checks_reading_correction.py:941:def _clean_plan_payload(scale_origin=_OMIT) -> dict:
tests/test_checks_reading_correction.py:960:def _clean_plan(scale_origin=_OMIT) -> ReadingView:
tests/test_f51_single_frame.py:311:    def _passthrough_no_resize(path, tier: str = DEFAULT_VISION_RESIZE_TIER) -> ...
tests/test_isolation.py:1680:def _direct_command(args: str = _DIRECT_PROBE_ARGS) -> str:
tests/test_tarch_converter_p1_geometry.py:50:def _make_dxf(path, *, window_block: str = WINDOW_BLOCK, ...)
tests/test_tarch_elevation_must_red.py:37:def _run(tmp_path, request, source=SOURCE):
```

逐一排除：这些名字**无一**被 monkeypatch（`monkeypatch.setattr` 的目标集合里只有
`GT_SOURCES_ROOT` 与它们撞名，而 `GT_SOURCES_ROOT` 从不出现在任何 def 默认参数里
——`grep -rn "def .*GT_SOURCES_ROOT" tests/ src/` 零命中）⇒ 绑死无害。
**结论：同型缺陷无第二处。**

---

## §六 #3 · 缺口成了产物里的显式债（B-2 / R2-b · R2-c）

**停报条款核对**（§七 A-②）：`EvidenceDebtV1.kind` 的既有枚举里
`other_known_missing` 正是「accounted known-missing that travels with the
artifact」（`decision_executor.py` 处置矩阵原文，**block nowhere**）——
机制在现有 schema 里**有位置**，未触发停报，未发明任何新字段。

**改动**（`src/agent/correction/evidence_adapters.py`，commit `d6c30f0`）：
`adapt_as_drawn_elevation` 的每个 bundle 现在携带

```python
EvidenceDebtV1(
    debt_id=f"debt_elevation_chain_span_unchecked_{input_id}",
    kind="other_known_missing",
    channel=None,   # 所有权主张，⛔ 不是通道豁免
    affected_refs=(_pointer(input_id, contract, sha, "/calibration"),),
    description=(
        "the elevation chain's total length is NOT reconciled "
        "against the plan side's outer-skin span on this leg: that "
        "equality needs the plan input (a different product "
        "family) and is B4's zero-parameter equality gate, loud on "
        "mismatch; this adapter must not fake it with a threshold "
        "against structure-line ink coverage (measured 0.01-0.5 px "
        "jitter on the real four facades -- that would be a "
        "nobody-signed threshold, not an equality).  Named premise: "
        f"{ELEVATION_CHAIN_SPANS_WHOLE_BUILDING}.  Owner: B4."
    ),
)
```

**R2-c**：命名前提 `ELEVATION_CHAIN_SPANS_WHOLE_BUILDING` 原位保留
（`evidence_adapters.py:559` 定义不动），且现在**随债进产物**（description 引它）。

**「下游只读产物」的机械形式**：锁（`tests/test_b3_elevation_leg.py`）只读
`artifact.bundle.evidence_debts`，不碰源码注释：

- `test_span_equality_gap_travels_as_a_named_debt`（四立面参数化）：债必在、
  `kind == "other_known_missing"`、`channel is None`、description 含 `"B4"`
  **和**命名前提原文、`affected_refs` 解回冻结产物的 `/calibration` 节
  （commit `abbf771` 补强）、带债产物整体 `validate_evidence_bundle` 仍通过。
- `test_the_span_debt_is_a_property_of_the_family_not_the_fixture`：合成三层
  立面同样带债（家族性质，⛔ 不依赖四份真字节）。

**neuter 读数**（证明锁的牙：退回 HEAD 版 adapter——没有这条债——锁必须红；
命令与输出原文）：

```text
$ cp src/agent/correction/evidence_adapters.py /tmp/evidence_adapters.py.r2b \
  && git checkout HEAD -- src/agent/correction/evidence_adapters.py \
  && python -m pytest "tests/test_b3_elevation_leg.py::test_span_equality_gap_travels_as_a_named_debt" \
      "tests/test_b3_elevation_leg.py::test_the_span_debt_is_a_property_of_the_family_not_the_fixture" \
      -q -p no:cacheprovider
FAILED tests/test_b3_elevation_leg.py::test_span_equality_gap_travels_as_a_named_debt[west]
FAILED tests/test_b3_elevation_leg.py::test_span_equality_gap_travels_as_a_named_debt[south]
FAILED tests/test_b3_elevation_leg.py::test_span_equality_gap_travels_as_a_named_debt[east]
5 failed in 5.80s
$ cp /tmp/evidence_adapters.py.r2b src/agent/correction/evidence_adapters.py \
  && python -m pytest （同两条锁）
5 passed in 5.42s
```

对照上一轮复核读数 `SPAN_MISMATCH=ACCEPTED`——那半条现在不再靠注释推走：缺口
以 `debt_id` 可点名的方式随 bundle 冻结 travel（`content_sha256` 覆盖
`evidence_debts`），等值门本身归 B4（R2-a，派工方已改单）。

**哈希影响自查**（§七 A-③）：加债会改变 bundle 的 `content_sha256`（债在哈希
覆盖面内）。核对结果：B3 的 bundle 是测试内从冻结字节**现算**的，仓库无 golden
bundle 哈希；同字节双跑一致锁（acceptance 4 `test_content_sha256_reproduces`）
两侧同加债仍一致，全量绿。**未触及任何已落库/已签字产物的哈希或基线。**

---

## §六 #4 · 两把 T7 锁都守得住免模型出口（B-3 / R3-a · R3-b）

**改动**（`tests/test_b3_elevation_leg.py`，commit `7c63216`）：

- **共用 booby-trap**（复核方给的路子之二）：monkeypatch
  `pipeline._make_decision_response_provider`，被替换工厂返回的 provider 一被
  loop 调用即炸。⭐ 挂点安全性：`monkeypatch.setattr` 默认要求属性存在，
  pipeline 将来若重构改名，锁自身红（setup error），⛔ 不会静默失效。
- **正向锁**（`test_real_entry_point_takes_real_elevation_bytes`）：保留复核方
  实测有牙的 `response_source.startswith("fixed_responses")` 断言，**加** booby-trap。
- **反向锁**（`test_real_entry_point_without_the_branch_goes_red_unwired`）：
  `UNWIRED` 在 adapt link 抛、route 记录不存在 ⇒ `response_source` 在此路径
  **不可读**（B-3 根因）。改用复核方点名的**调用参数校验**：wrapper 只记录
  kwargs、原样转发真实入口（被测动作仍是公开入口），断言
  `seen_kwargs.get("fixed_responses") == []`；**加** booby-trap。

**变异读数**（验收 #4「各自去掉 `fixed_responses` ⇒ 都必须红」；备份-变异-跑-还原，
输出原文）：

```text
# 变异 1：正向锁删去 fixed_responses=[...] 实参
MUTATION1_APPLIED=forward lock without fixed_responses
E       AssertionError: MODEL SEAT OCCUPIED: this lock must stay model-free (fixed_responses is the sanctioned escape hatch; a green here must never cost a billed call)
1 failed in 5.62s

# 变异 2：反向锁删去 fixed_responses=[] 实参
MUTATION2_APPLIED=negative lock without fixed_responses
E       AssertionError: the refusal was proven on a call WITHOUT the model-free hatch (kwargs seen: ['out_dir']) -- this lock must keep calling the real entry WITH fixed_responses, or it proves nothing about the model-free exit (B-3)
1 failed in 5.82s
```

⭐ 变异 1 的雷在**出网之前**炸（provider 座位被 trapped 版替换，真 provider 从未
构造）。对照上一轮复核读数 `NEGATIVE_LOCK_WITHOUT_FIXED_RESPONSES=GREEN` —— 已翻红。

---

## §六 #5 · 执行档两处措辞更正（N-1）

1. **「两把锁都在锁内断言 `response_source`」——与源码不符，更正**：
   上一版执行档写作此句时，**只有正向锁**断言 `response_source`；反向锁当时对
   免模型出口**没有任何机械断言**（`UNWIRED` 在 route 记录生成前抛出，
   `response_source` 在该路径不可读——这正是 B-3）。本轮之后的事实：
   正向锁 = `response_source` 断言 + booby-trap；反向锁 = 调用参数校验
   + booby-trap（⛔ 仍非 `response_source` 断言——它在这条路径上读不到）。
2. **T0 计数更正**：上一版「def 数 27、collect 27、无参数化展开」有误，应为
   复核方独立计数「**18 个 `def test_`、参数化展开后 27 项**」（复核时点文件为
   20 def / 29 项）。本轮改动后当前文件为 **22 def / 34 项**
   （`grep -c "^def test_"` = 22；`--collect-only -q` = `34 tests collected`）。
   总量等式与回归结论不受影响。

---

## §六 #6 · 上一轮已过审的四项逐条不退化

| 过审项 | 本轮证据 |
|---|---|
| 数据承载（z 半 + 楼层梯）| acceptance 1/2/3 全量绿；新 span 债锁对四立面重新 `validate_evidence_bundle` |
| 来源引用（解回冻结字节）| `test_every_z_and_level_points_at_its_frozen_byte` 全量绿；span 债自身的 `affected_refs` 亦解回冻结字节（`abbf771`）|
| 楼层线谓词（⛔ 非名单）| acceptance 3 三锁（合成层高/重塑梯/竖线永不入选）全量绿 |
| T7 走公开入口 | 反向锁改写后**仍从 `pipeline.run_correction_evidence_chain` 断言 `EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED`**（分支 neuter 的常驻形态，wrapper 只记录参数、原样转发）；全量绿 |

---

## §六 #7 · 全量绿（`-n 6`）

**环境自证与 pytest 同一条命令**（返工单 §六 模板），对最终 HEAD `abbf771`
（输出原文；两次全量同读数，454s 次为终态树）：

```text
$ python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)" \
  && python -m pytest -q -n 6 -p no:cacheprovider
/tmp/b3_r2_glm/src/agent/correction/evidence_contract.py
3753 passed, 2 skipped, 13 xfailed, 211 warnings in 454.22s (0:07:34)
```

（第一次全量在 `7c63216` 后的树上：`3753 passed, 2 skipped, 13 xfailed, 211
warnings in 534.85s`；`abbf771` 只加锁内断言、不增减测试项，两次读数逐位相同。
均有 summary 行 ⇒ 非同机竞争假红。）

**逐位闭合**：

```text
3748  复核方基线（2026-09-03z）
+   5  本单新增：span 债锁 4（四立面参数化）+ 1（synthetic 家族锁）
= 3753  （B-1/B-3 均为改写，不增减项数）
```

目标三文件（B3 + o22m1 + o22m7）：`120 passed in 5.37s`。

---

## 我自己认为最薄弱的一处

**B-2 债的「归 B4」只落在自由文本 `description` 里，没有结构化字段。**
`EvidenceDebtV1` 没有 owner/归账字段，§七 A-② 又明确不许发明新字段，所以
「B4 能凭它点名」里**机器可读**的部分只有 `debt_id` 前缀
（`debt_elevation_chain_span_unchecked_`）；锁断言的 `"B4" in debt.description`
锁的是**字样**而非结构。若 B4 将来按字段（而非 id 前缀/字样）对账，这条债需要
schema 升级——届时是派工方的决定，⛔ 不是本席能单方面扩的。
次弱一处（已补强但性质仍在）：债的 `affected_refs` 不在 validator 的 scoped-ref
校验面内（该校验只覆盖 `zero_payload_channel`），`/calibration` 指针的正确性
目前由**锁内解回断言**（`abbf771`）持有——「锁在测」而非「validator 在管」，
若未来有第二个 `other_known_missing` 债的生产者，它没有义务被同样检查。
