# B3 as-drawn 立面腿 · 执行档（v2 派工单）

- **日期**：2026-09-03 · **施工**：GLM 家族施工席 · **工作目录**：`/tmp/b3_r2_glm` · **分支**：`wt/09.03v_b3_r2`
- **派工单**：[`2026-09-03v_B3_as_drawn_elevation_leg_dispatch_v2.md`](../request/2026-09-03v_B3_as_drawn_elevation_leg_dispatch_v2.md)
- **本轮提交**（基点 `431c44b`，三笔、每笔独立成立）：
  - `2cba7ca` T0 恢复（revert of revert，+1190/−25，单独一笔）
  - `6df6660` T6 第三条线登记为有意的（test_o22m1，+106/−12）
  - `e299a9d` T7 真入口接线 + 两把锁（pipeline.py + test_b3，+145/−6）

---

## 〇、开工自检（三条全过）

```
$ pwd && git log --oneline -1 && git status --porcelain
/tmp/b3_r2_glm
431c44b 09.03v_dispatch_B3_v2_and_F158_rework_crossreview
（porcelain 空）

$ python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)"
/tmp/b3_r2_glm/src/agent/correction/evidence_contract.py
```

⇒ 目录、基点、树、模块解析四项全对。**无 A/B 层停报事件**——T7 那四行派工方静态读得**完全正确**（见 §三实测）。

---

## 一、T0 —— 恢复被回退的那份

### 命令与输出原文

```
$ git revert --no-edit f16f9a2
[wt/09.03v_b3_r2 2cba7ca] Revert "Revert "09.03s_merge_B3_as_drawn_elevation_leg (GLM seat, incomplete)""
 Date: Thu Sep 3 12:25:29 2026 +0000
 8 files changed, 1190 insertions(+), 25 deletions(-)
 create mode 100644 tests/test_b3_elevation_leg.py
```

（`+1190/−25` 与回退那笔 `f16f9a2` 的 `+25/−1190` 正好互逆。）

### §〇 自证（验收 #0）

```
$ git diff 59a682b -- src/agent/correction/evidence_adapters.py \
    src/agent/correction/evidence_contract.py src/agent/reading/vector_contract.py \
    tests/test_b3_elevation_leg.py tests/test_f97_vector_contract.py \
    tests/test_o22m2_evidence_contract.py tests/test_o22m4_wall_compiler.py \
    tests/test_o22m7_evidence_wiring.py; echo "EXIT=$?"
EXIT=0
```

**空输出、退出码 0** ⇒ 恢复出来的 8 文件与 `59a682b` 当初那份**逐字节相同**。
revert 自动成笔（`2cba7ca`），未混入任何其它改动 ⇒ 「T0 单独一笔提交」满足。

---

## 二、T0 之后 T1–T5 的实际状态（逐条核对，⛔ 不默认恢复=完整）

**结论：T1–T5 全部由 T0 恢复带回，本轮零补写。** 依据（每条都是本轮在恢复态树上重新量的，非记忆）：

| # | 状态 | 本轮实测依据 |
|---|---|---|
| T1 disposition→`ADAPT` | ✅ 恢复带回 | `vector_contract.py:282-283`（ContractSpec 注册处，含 2026-09-03 B3 改 disposition 的注释）；分类器实测见 §三 |
| T2 `adapt_as_drawn_elevation` + `elevation_openings` 通道 + `channel_status` | ✅ 恢复带回 | `evidence_adapters.py:609`（函数）、`:753-782`（通道路由：present/absent + debt） |
| T3 `z_range_m` 带引用证据 | ✅ 恢复带回 | `evidence_adapters.py:695-707`：`z_low_ref`/`z_high_ref` = 指回冻结字节的 `_pointer`，`source_ref` = `_observation_ref`（含像素证人、`resolution` 标注）；现场解引用演示见 §六#2 |
| T4 楼层线 = 可判定规则 | ✅ 恢复带回 | `evidence_contract.py:577` `FLOOR_LEVEL_SELECTION_RULE = "every structure line with constant_quantity == 'z'"`（**谓词**，非名单）；`FloorLevelClaimV1.z_ref` 带字节出处 |
| T5 四立面全进 bundle + 哈希逐位可复现 | ✅ 恢复带回 | 常驻锁 `test_real_facade_classified_adapt_and_bundle`（四立面参数化）+ `test_content_sha256_reproduces`；现场演示见 §六#4 |
| T5-b 坏输入响亮失败 | ✅ 恢复带回 | 三个具名错误码 + 常驻锁五条（`test_z_missing_is_loud` / `test_chain_not_closed_is_loud` / `test_chain_values_do_not_sum_is_loud` / `test_degenerate_ladder_is_loud` / validator 侧三条换载体锁）；现场演示见 §六#5 |

**T5-b 第三项「尺寸链总长与外皮跨度对不上」的归属说明**（复核方请重点看这条）：
该对账需要**平面产物在场**（外皮跨度在平面侧），属跨视图相等门 = **B4 的设计归属**（派工单 §四明确 B4 另有单、本单不做洞口合成/跨视图配对）。本腿单源可见的两半已全部响亮：①标定链闭合（零阈值**重算**，`_require_chain_closed`，⛔ 不信产物自报）②z 方向跨不满整栋的形态 = `FLOOR_LADDER_DEGENERATE`。论证写在 `evidence_adapters.py:546-558`：单份立面字节里**没有**「外皮跨度」这个量可对；若对结构线墨覆盖设阈值，实测抖动 0.01–0.5 px ⇒ 那会是一个没人签字的阈值（⛔ 本腿拒绝伪造这个检查）。

---

## 三、T7 前置实测 —— 派工方那四行读对了（免责条款的验证）

先核派工方静态读的两处：

- `vector_contract.py:530-541`：`ADAPT` 分支台账确实印「recognized; wired to the correction evidence adapter (module 7)」——对立面契约同样印。
- `pipeline.py:1094-1127`（改动前）：if/elif 只认 `as_drawn_plan` 与 `reading_view_legacy`，else 抛 `EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED`。

**实测**（分类器判定 + 真入口喂真字节，恢复态、加分支之前）：

```
$ python -c "
from src.agent.reading.vector_contract import classify_vector_json
import json
p = 'AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_east_as_drawn.json'
doc = json.loads(open(p, encoding='utf-8').read())
d = classify_vector_json(doc)
print('contract_id =', d.contract_id)
print('disposition =', d.disposition)
print('reason      =', d.reason)
"
contract_id = as_drawn_elevation_v0
disposition = Disposition.ADAPT
reason      = None

$ python -c "
from pathlib import Path
from src.agent.pipeline import run_correction_evidence_chain
try:
    run_correction_evidence_chain(
        Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out'),
        'sm25_east_as_drawn.json',
        out_dir=Path('/tmp/b3_t7_probe'),
    )
    print('RESULT: NO-RAISE')
except Exception as exc:
    print('RESULT: RAISED')
    print('type:', type(exc).__name__)
    print('str :', exc)
"
RESULT: RAISED
type: EvidenceContractError
str : EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED: {'file': 'sm25_east_as_drawn.json', 'contract': 'as_drawn_elevation_v0', 'reason': None, 'wired': ['as_drawn_plan', 'reading_view_legacy']}
```

⇒ **证实**：台账自称 wired，真入口拒收 ⇒ 「已接线」确实是一句没兑现的声明。**未触发 A-④停报**，按单施工。

### ⚠️ 事故自报：T7-a 加分支后的两次验证无意出网

我在加分支后验证时两次调用 `run_correction_evidence_chain` **都没给 `fixed_responses`** ⇒ decision loop 走 provider 模式**真调了模型**（每次 2 轮、共约 6 次调用；模型返回合法空 accept，链以 `decision_hash_cycle` 诚实退出）。产物落在 `/tmp/b3_t7_probe*`，未进仓库。额度损失（GLM 订阅制）可忽略，但流程上不该。**教训已直接转化为 T7-b 锁的形态：两把锁全部走 `fixed_responses` 免模型出口，并在锁里断言 `response_source` 以 `fixed_responses` 开头**（防今后任何人把锁改回花钱形态）。

### T7-a 参数决定（派工单要求说明理由）

- **`view_type="elevation"` 硬编码**：立面契约的产物按契约定义就是立面视图，没有第二种可推断，故不推断。
- **`facade_ref` 优先级 = 调用方显式 `floor_ref` > 产物自报的 `facade_label` > 文件名 stem 兜底**。四立面实测 `facade_label` 为 `'East'/'West'/'North'/'South'`（互不相同 ⇒ 满足 `("elevation", facade_ref)` 唯一性槽）；从被处理的数据里取，⛔ 不从文件名猜（除非产物什么都没声明）。

---

## 四、T6 —— 第三条线登记为【有意的】（提交 `6df6660`）

改 `tests/test_o22m1_as_drawn_producer_types.py`。**⛔ 不只是把集合改大**，做了四件事：

1. **登记表 + 判据成文**（T6-b）：`_ADAPTING_WIRES = {CONTRACT_AS_DRAWN_PLAN: "adapt_as_drawn_plan", CONTRACT_AS_DRAWN_ELEVATION_V0: "adapt_as_drawn_elevation"}`，注释写明这是**规则非流水账**、准入判据 = 「该契约的字节有真实 `adapt_*` 入口」、以及 elevation 这条线**为什么有意**（立面字节是窗 z 半边与楼层梯子的**唯一**来源，平面族对两者零来源）。legacy 有入口却留在 CONSUME 的特例也写明（`_NON_ADAPTING_ENTRY_POINTS`，理由：拆旧腿另有单）。
2. **两道机械对账**（把判据从散文变成断言）：
   - 主锁 `test_every_adapt_wire_is_a_registered_contract_with_a_real_entry_point`：disposition 表与登记表**精确相等**（第四个契约悄悄转 ADAPT ⇒ 红；注册项丢 disposition ⇒ 也红）+ 登记表每个入口在 `evidence_adapters` 里**存在且可调用**（登记不许烂成指认已死函数的流水账）。
   - 入口侧 `test_every_public_adapt_entry_point_is_accounted_for`：`evidence_adapters.__all__` 的 `adapt_*` 公开面 == 登记表 ∪ legacy 特例（**精确相等**）——新入口不注册就出现 ⇒ 红。
3. **改名**（T6-c）：`test_only_the_two_named_contracts_hold_wires` → `test_every_adapt_wire_is_a_registered_contract_with_a_real_entry_point`（旧名在「consuming 1 + adapting 2 = 三个」之下说谎；新名与它守的规则一致）。
4. **常驻变异锁**（T6-d）：`test_a_fourth_contract_quietly_turning_adapting_goes_red`（monkeypatch 塞第四个 `ADAPT` 契约进 `CONTRACTS`，判据经同一 `_wire_sets` helper 必须 `AssertionError`——照抄 test_o22m7 4b 形态，⛔ 非断言复写）。

### 牙齿实测（提交前当场做，两个方向各一次）

```
方向A: 断言确实红（锁有牙）   ← monkeypatch 塞 contract_x 转 ADAPT 后，adapting != 登记表
方向B: 断言确实红（锁有牙）   ← __all__ 悄悄加 "adapt_smuggled_new_leg" 后，入口面 != 登记表∪特例
```

```
$ python -m pytest -q tests/test_o22m1_as_drawn_producer_types.py -p no:cacheprovider
55 passed in 5.48s
```

---

## 五、T7 —— 「已接线」在真入口兑现（提交 `e299a9d`）

### T7-a：pipeline.py 只加一支（+ 该支自己的接线：函数内 import 两行、docstring 路由句、UNWIRED 的 `wired` 名单）

`pipeline.py:1108-1125` 新分支（摘录）：

```python
elif decision.contract_id == CONTRACT_AS_DRAWN_ELEVATION_V0:
    # ⭐ B3 (2026-09-03): the elevation branch.  An elevation has no
    # floor, so the semantic slot's second coordinate is the FACADE, ...
    adapter_name = "adapt_as_drawn_elevation"
    if floor_ref is None:
        facade_label = doc.get("facade_label")
        floor_ref = (
            facade_label
            if isinstance(facade_label, str) and facade_label
            else Path(product_filename).stem
        )
    artifact = adapt_as_drawn_elevation(
        raw, input_id=Path(product_filename).stem,
        facade_ref=floor_ref, view_type="elevation",
    )
```

**边界说明（复核方请核）**：派工单放开的是「pipeline.py:1093-1120 那个 if/elif 加立面分支」。我改了同函数的三处**配套**：①函数内 import 块加两个名字（分支的必要接线）②docstring 的路由句补立面一支（⛔ 不改则 docstring 对新行为说谎——与 T6-c 同一精神）③else 抛 UNWIRED 时携带的 `wired` 名单加立面契约 id（否则错误信息指错路）。**pipeline.py 其余任何行零改动**（`git diff` 可核：仅上述三块）。

### T7-b：两把走真入口的锁（⛔ 都不是直接调 adapter）

**绿锁** `test_real_entry_point_takes_real_elevation_bytes`：真 east 字节 → `pipeline.run_correction_evidence_chain`（`fixed_responses` 免模型）→ 出 `DecisionLoopOutcomeV1`；断言 route record：`contract == "as_drawn_elevation_v0"`、`adapter == "adapt_as_drawn_elevation"`、`response_source` 以 `fixed_responses` 开头。

**常驻 neuter 锁** `test_real_entry_point_without_the_branch_goes_red_unwired`：rebind `vector_contract.CONTRACT_AS_DRAWN_ELEVATION_V0` ⇒ 分支条件永不可达（≡ 物理摘除分支）⇒ 同样的真字节必须抛 `EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED`。前提由绿锁孪生证明（分支在时同调用不抛 ⇒ 这里的红只可能是分支没了）。

### 物理摘除验证（验收 #7-② 的字面形态，源码级）

```
$ git checkout HEAD~1 -- src/agent/pipeline.py && \
    python -m pytest -q tests/test_b3_elevation_leg.py::test_real_entry_point_takes_real_elevation_bytes \
    tests/test_b3_elevation_leg.py::test_real_entry_point_without_the_branch_goes_red_unwired -p no:cacheprovider
1 failed, 1 passed in 6.09s        ← 绿锁 FAILED（红在 pipeline.py:1119）、neuter 锁照常绿

（摘除态下绿锁的完整报错：）
>               raise EvidenceContractError(
                    "EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED",

$ git checkout HEAD -- src/agent/pipeline.py && git status --porcelain
（空）                             ← 恢复干净（验收 #7-③）
```

```
$ python -m pytest -q tests/test_b3_elevation_leg.py -p no:cacheprovider
29 passed in 5.77s                 ← 27 恢复带回 + 2 把新锁
```

---

## 六、§三 单外对撞 —— 逐名词 grep 原文与逐处结论

**方法**：对本单新增/改名的每个名词 `grep -rn` 全仓 `src/ tests/`（py），逐处回答「这里握着一份名单吗？本轮改动会不会让它过时？」

### 名词 1：`CONTRACT_AS_DRAWN_ELEVATION_V0` / `as_drawn_elevation_v0`（21 处 py）

```
$ grep -n "CONTRACT_AS_DRAWN_ELEVATION_V0\|as_drawn_elevation_v0" \
    src/agent/pipeline.py src/agent/reading/vector_contract.py \
    src/agent/correction/evidence_contract.py src/agent/correction/evidence_adapters.py \
    tests/test_f97_vector_contract.py tests/test_o22m7_evidence_wiring.py
src/agent/pipeline.py:1047:    ``as_drawn_elevation_v0`` product takes the as-drawn adapter (elevation,
src/agent/pipeline.py:1079:        CONTRACT_AS_DRAWN_ELEVATION_V0,
src/agent/pipeline.py:1108:        elif decision.contract_id == CONTRACT_AS_DRAWN_ELEVATION_V0:
src/agent/pipeline.py:1152:                        CONTRACT_AS_DRAWN_ELEVATION_V0,
src/agent/reading/vector_contract.py:80:AS_DRAWN_ELEVATION_V0_SCHEMA = "as_drawn_elevation_v0"
src/agent/reading/vector_contract.py:85:CONTRACT_AS_DRAWN_ELEVATION_V0 = "as_drawn_elevation_v0"
src/agent/reading/vector_contract.py:282:        CONTRACT_AS_DRAWN_ELEVATION_V0,
src/agent/correction/evidence_contract.py:146:    CONTRACT_AS_DRAWN_ELEVATION_V0,
src/agent/correction/evidence_contract.py:161:SOURCE_CONTRACT_AS_DRAWN_ELEVATION = CONTRACT_AS_DRAWN_ELEVATION_V0
src/agent/correction/evidence_adapters.py:108:    CONTRACT_AS_DRAWN_ELEVATION_V0,
src/agent/correction/evidence_adapters.py:647:    _require_contract(doc, raw, input_id, CONTRACT_AS_DRAWN_ELEVATION_V0)
tests/test_f97_vector_contract.py:17:    CONTRACT_AS_DRAWN_ELEVATION_V0,
tests/test_f97_vector_contract.py:277:        "schema": "as_drawn_elevation_v0",
tests/test_f97_vector_contract.py:282:    assert classify_vector_json(elev_v0).contract_id == CONTRACT_AS_DRAWN_ELEVATION_V0
tests/test_f97_vector_contract.py:712:    "as_drawn_elevation_v0",
tests/test_f97_vector_contract.py:723:    ("as_drawn_elevation_v0", {}),
tests/test_f97_vector_contract.py:724:    ("as_drawn_elevation_v0", {"openings": []}),
tests/test_f97_vector_contract.py:735:    ("as_drawn_elevation_v0", {"openings": [], "structure_lines": []},
tests/test_f97_vector_contract.py:736:     CONTRACT_AS_DRAWN_ELEVATION_V0),
tests/test_o22m7_evidence_wiring.py:664:    vc.CONTRACT_AS_DRAWN_ELEVATION_V0,
```

逐处结论：
- `pipeline.py:1047/1079/1108/1152` —— 本轮 T7-a 改动本体 ✅
- `vector_contract.py:80/85/282` —— 定义 + ContractSpec 注册（T1 恢复带回）✅
- `evidence_contract.py:146/161` —— SOURCE_CONTRACT 别名（恢复带回）✅
- `evidence_adapters.py:108/647` —— adapter 的契约校验（恢复带回）✅
- `test_f97:282` —— disposition 断言（恢复带回、上一轮已同步）✅
- `test_f97:709-736` 三张名单（`_REGISTERED_VALUES` / `_MALFORMED_DECLARATIONS` / `_COMPLETE_DECLARATIONS`）—— 我逐一看过上下文：它们锁的是**分类器映射**（schema 值 ↔ 契约 id ↔ BLK-A 畸形形态），**与 disposition、与接线正交** ⇒ 立面接线不让它们过时 ✅
- `test_o22m7:664` —— `_ADAPTING_SET`（恢复带回，§三表 #2 上一轮已改）✅
- 其余 py 外出现（proposals / experiments README / 产物 JSON）为叙述与数据，非名单。

### 名词 2/3：通道名 `elevation_openings` / `floor_levels`

```
$ grep -rn '"elevation_openings"' src/ tests/ --include="*.py" | grep -v test_b3 | grep -v evidence_adapters.py
src/agent/correction/evidence_contract.py:451/459/914 + tests/test_o22m2…:91/1274/1351/1356/1448/1958
+ tests/test_o22m4…:988
$ grep -rn '"floor_levels"' （同上）
src/agent/correction/evidence_contract.py:452/460/915 + test_o22m2…:91/1274/1448/1958 + test_o22m4…:988
```

逐处结论：全部是**恢复带回**的名单（§三表 #4 o22m2 四处、#5 o22m4 一处、#6 ChannelName Literal + payload members 表），上一轮已同步纳入两通道；**本轮没有引入第三个通道、没有改任何通道名单** ⇒ 不过时 ✅

### 名词 4：`Disposition.ADAPT` 的集合持有者

```
$ grep -rn "Disposition.ADAPT\b" src/ tests/ --include="*.py" | \
    grep -v "test_b3_elevation_leg\|test_o22m1\|test_o22m7\|vector_contract.py"
tests/test_o22m2_evidence_contract.py:1761:    assert spec.disposition is Disposition.ADAPT
tests/test_o22m3_evidence_adapters.py:608:    assert spec.disposition is Disposition.ADAPT
```

逐处结论（看过上下文）：两处都是 `test_as_drawn_plan_is_adapt_not_consumed`——**plan 契约的单点断言**（模块 7 接线时翻的），⛔ 不是「只有 plan 是 ADAPT」的集合断言 ⇒ 立面加入不使它们过时 ✅

### 名词 5：`adapt_as_drawn_elevation`（入口名）

出现于 6 个 py 文件：pipeline.py（本轮 T7-a）· evidence_adapters.py（定义，恢复带回）· vector_contract.py:282 附近 describe 文本（恢复带回）· test_o22m1（本轮 T6 登记表）· test_b3（恢复带回 + T7-b）· test_f97:284（**注释**里提及，恢复带回）。逐处结论：无一处握「会被本轮改动作废的名单」✅

### 名词 6：`facade_label`（本轮新读的字段）

```
$ grep -rn "facade_label" src/ tests/ --include="*.py" | grep -v test_b3_elevation_leg
src/agent/pipeline.py:1111/1118/1120/1121   ← 全部是本轮 T7-a 分支本体
```

⇒ 全仓唯一生产读者就是新分支本身；test_b3 的合成夹具构造该字段（数据侧）✅

### 名词 7：被替换的旧测试名（改名最怕悬空引用）

```
$ grep -rn "test_only_the_two_named_contracts_hold_wires" src/ tests/ --include="*.py"
（空 ⇒ py 侧零悬空引用）
```

该名字仅存于历史文档（plan.md / CLAUDE.md 收工记录 / 派工单 / 2026-09-02 裁决与执行档）——历史叙述按项目惯例不追改 ✅

### §三总结

派工单 §三 表 7 处 + 我本轮扫描确认的额外出现处（test_f97 三张分类器名单、test_o22m2:1761 / test_o22m3:608 单点断言、facade_label、旧测试名）**逐处核毕，无需第 8 处改动**。

---

## 七、§五 三条纪律核对

1. **⛔ 无长度/高度常数**：
   ```
   $ git diff 431c44b..HEAD -- src/ | grep -E "^\+" | grep -oE "\b[0-9]+\.?[0-9]*\b" | sort -u
   0 0.01 0.5 03 08 09 1 2 2026 3 3.2 3.3 31 7 7.2
   ```
   逐个核语境：`3.2/3.3/4.2/7.2` = 设计稿**章节号**（design §3.3 / §7.2）；`0.01/0.5` = **注释里的实测记录**（「墨覆盖抖动 0.01–0.5 px ⇒ 拒绝设阈值的理由」）；其余为版本号/日期/索引。**判定代码里零长度常数**；sm25 读数（3600/3.6/7200/7.2 m 等）grep 生产四文件零命中。
2. **夹具不止 sm25**：恢复带回的合成夹具 = 三层、层高 **2.9/3.3/4.2 混排**（`test_three_storey_mixed_heights_select_their_own_ladder`）+ 重塑梯子（`test_reshaped_ladder_selects_the_new_ladder`）+ 竖线永不入选（`test_vertical_structure_lines_are_never_levels`）+ 无窗立面诚实零跑。验收 #5 现场演示的坏输入夹具也全部以合成梯子为基底。
3. **「横跨整栋」假设局部化 + 有名 + 不成立响亮**：前提名字 = `ELEVATION_CHAIN_SPANS_WHOLE_BUILDING`（`evidence_adapters.py:559`，注释明写「这批图纸的画法性质，⛔ 不是定理」及其单源可查的两半）；不成立的 z 向形态 = `FLOOR_LADDER_DEGENERATE` 具名错误（adapter 侧 `:711` + 校验器侧 `evidence_contract.py:1315`，常驻锁 `test_degenerate_ladder_is_loud`）。

---

## 八、§六 十条验收逐条报

| # | 规则 | 证据（上文详录） | 判定 |
|---|---|---|---|
| 0 | 恢复的就是当初那份 | §一：`git diff 59a682b` 空输出、EXIT=0 原文 | ✅ |
| 1 | 四份真实立面全分类 `as_drawn_elevation_v0` 并走 adapter（⛔ 用分类器） | §三：分类器实测 east=`as_drawn_elevation_v0`/`ADAPT`；常驻锁 `test_real_facade_classified_adapt_and_bundle` 四立面参数化、先 `classify_vector_json` 后 adapter，且断言楼层梯 == 规则从同字节选出的集合 | ✅ |
| 2 | 每个 z / 每个楼层标高可解引回冻结字节 | 常驻锁 `test_every_z_and_level_points_at_its_frozen_byte` 是**全量**解引用（四立面 × 每个 z × 每个 level，比抽 3 强）；现场随机演示（随机立面=south、随机抽 3）：`O06:z_low 4.5809==解引用` · `O01:z_high 6.2053` · `level:S04 7.1935`，3/3 相等且 `source_output_sha256` 全锚定本字节 | ✅ |
| 3 | 楼层线挑选是规则非名单 | `FLOOR_LEVEL_SELECTION_RULE` 谓词；换层数/换层高的合成夹具选对自己的梯子（§七.2）；生产代码 grep 零 sm25 标高 | ✅ |
| 4 | bundle 逐位可复现 | 常驻锁 + 现场演示：四立面 × 跑两次，`content_sha256` 逐位相同（east `19818171…`/west `b476f756…`/north `1276292c…`/south `50d0bfa8…` 各两次全同） | ✅ |
| 5 | 坏输入响亮失败（各造一个） | 现场演示三发三中：z 缺失→`ELEVATION_OPENING_Z_MISSING`；链 overall 篡改→`CALIBRATION_CHAIN_NOT_CLOSED`（零阈值重算抓到 10400≠10401）；局部立面→`FLOOR_LADDER_DEGENERATE`。x 向跨视图对账归 B4（§二归属说明） | ✅ |
| 6 | 第三条线是被签字的 | ①名字与规则一致（T6-c 改名）②登记表 = 规则形态 + 判据（有真实 `adapt_*` 入口）+ 为什么有意成文（T6-b）③第四契约悄悄转 ADAPT ⇒ 常驻锁必红（T6-d，牙齿两方向实测） | ✅ |
| 7 | 「已接线」在真入口兑现 | ①真字节 → 真入口 → outcome + route record 点名 elevation adapter（绿锁，`fixed_responses` 免模型）②物理摘除分支 ⇒ 绿锁红成 `EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED`（源码级 checkout 验证原文在 §五）③恢复后 porcelain 空 | ✅ |
| 8 | §三规则自己走了一遍 | §六：7 个名词 × grep 原文 × 逐处结论 | ✅ |
| 9 | 全量绿（`-n 6`） | 见下 | ✅ |

### #9 全量读数（`__file__` 与 pytest 同一条命令）

```
$ python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
/tmp/b3_r2_glm/src/agent/correction/evidence_contract.py
…
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. …
3748 passed, 2 skipped, 13 xfailed, 211 warnings in 456.62s (0:07:36)
```

（exit 0；`m.__file__` 落在 `/tmp/b3_r2_glm/` ✅）

**逐位闭合**：

```
3717（基线 861176e，回退后权威读数）
+ 27  = T0 恢复带回 tests/test_b3_elevation_leg.py（文件在基线不存在；def 数 27，
        collect 27——无参数化展开）
+ 2   = T6 在 tests/test_o22m1 的净增（def 19→21：原 1 个锁换成
        主锁+入口对账锁+变异锁 3 个）
+ 2   = T7-b 在 tests/test_b3 的净增（绿锁 + neuter 锁；def 27→29）
= 3748 ✓ 与读数逐位相等
```

佐证（恢复不改其它文件条数）：`git diff 861176e..59a682b -- test_o22m2/o22m4/o22m7/f97` 中 `parametrize|def test_` 行零变动（纯断言/名单改动）；三 commit 点 def 数对账原文：

```
tests/test_o22m2_evidence_contract.py  基线=36 59a682b=36 当前=36
tests/test_o22m4_wall_compiler.py      基线=30 59a682b=30 当前=30
tests/test_o22m7_evidence_wiring.py    基线=31 59a682b=31 当前=31
tests/test_f97_vector_contract.py      基线=50 59a682b=50 当前=50
tests/test_o22m1_as_drawn_producer_types.py  基线=19 59a682b=19 当前=21
```

（`2 skipped / 13 xfailed` 与基线口径一致，非本轮引入。）

---

## 九、自查三问

### 我自己认为最薄弱的一处

**T7-b neuter 锁的「摘分支」是常量重绑定模拟，不是源码删除**。monkeypatch `CONTRACT_AS_DRAWN_ELEVATION_V0` 使分支条件永假，语义上 ≡ 分支不存在，且我用源码级 checkout 做过一次物理摘除验证（绿锁真红了）。但**常驻锁本身**锁的是「条件可达性」这一面；如果未来有人把分支改成不经过这个常量比较（比如换成一个 dispatch 表、或比较 `decision.contract_id == "as_drawn_elevation_v0"` 字面量），neuter 锁会静默失效（patch 的常量不再被读 ⇒ 分支照走 ⇒ 锁假绿）。入口侧 `test_every_public_adapt_entry_point_is_accounted_for`（T6）能拦「入口消失」，但拦不住「分支换了一种写法而常量重绑定够不着」。补强方向（本轮未做，属 B4/拆旧腿时可一并考虑）：给 route record 的 `wired` 名单或 dispatch 结构本身立一把锁。

### 希望复核方重点打哪里

1. **§二的 T5-b 第三项归属论证**（「尺寸链总长 vs 外皮跨度」归 B4 而非本腿造一个单侧阈值）——这是我按恢复带回的代码注释复述并认可的论证，请独立判它是否成立，还是应该在 B3 里就做某种单侧检查。
2. **T7-a 的边界**：pipeline.py 我改了分支本体之外的三小块（函数内 import / docstring 路由句 / UNWIRED 的 wired 名单）。判断它们是否属于「分支自己的接线」（我的立场：是，且不改则文档对新行为说谎），还是越过了「只加这一处分支」的红线。
3. **T6 登记表形态**：`_ADAPTING_WIRES` 仍是一个手写字典（值被机械验证存在+可调用、键与 disposition 表精确对账）。请判它是否达到了「规则非名单」的门槛，还是应该进一步从某处推导（我权衡过：contract id ↔ 入口名之间不存在可靠的无表映射——`as_drawn_elevation_v0` ↔ `adapt_as_drawn_elevation` 不含 v0——强行推导会造出更脆的字符串拼接）。
4. **§三出网事故**的定性（§三末）：流程瑕疵已自报并转化为锁的形态，请判是否需要额外处置。
