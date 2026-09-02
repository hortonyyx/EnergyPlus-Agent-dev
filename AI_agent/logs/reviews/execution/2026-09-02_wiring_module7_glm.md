# 执行档 · 接线（模块 7 上半）· GLM 施工席 · ⛔ A 层停报（未施工）

- 派工单：[`../request/2026-09-01i_wiring_module7_dispatch.md`](../request/2026-09-01i_wiring_module7_dispatch.md)
- 树：`/tmp/wiring_glm` · HEAD `a003542` · **工作树零改动**（本档除外，未动任何生产代码/测试）
- 结论先行：**A 项触发 §四 A 层 4（现有枚举表达不了「交给 correction adapter」，必须新增枚举值），
  且 A 是 B 项验收 1 的硬依赖 ⇒ 按「立刻停，不要绕」全单停，未写任何实现代码。**

---

## 0. 开工自检（三条全过）

```
$ git -C /tmp/wiring_glm rev-parse --short HEAD
a003542

$ ls AI_agent/logs/reviews/request/2026-09-01i_wiring_module7_dispatch.md
/tmp/wiring_glm/AI_agent/logs/reviews/request/2026-09-01i_wiring_module7_dispatch.md

$ python -c "import src.agent.correction.evidence_adapters as m; print(m.__file__)"
/tmp/wiring_glm/src/agent/correction/evidence_adapters.py
```

---

## 1. §〇 承重前提逐行复核（派工方说的 vs 我实测的）

| # | 派工方说的 | 我实测的 | 判 |
|---|---|---|---|
| 1 | 新链生产侧零消费者（grep ⇒ 空） | `grep -rn 'evidence_contract\|evidence_adapters\|wall_compiler\|decision_schema\|decision_executor' --include=*.py src/ scripts/` ⇒ **非空**，7 行命中全部落在 `src/agent/correction/` **五个新链模块内部互引**；`src/agent/pipeline.py` 与 `scripts/` **零命中** ⇒ 「生产侧（pipeline 入口）无消费者」实质成立 | ✅（B 层记一条：grep 字面读数非空，见 §4）|
| 2 | `pipeline.py:452` 把识图 JSON 原文贴进提示词 | `pipeline.py:452-453`：`for fname in vector_files: chunks.append(f"\n[reading vector] {fname}:\n```json\n{_read(vector_dir / fname)}\n```\n")`；`vector_files` 来自 `pipeline.py:427-429` `classify_vector_dir(vector_dir, discover_vector_files(vector_dir)).consumed` | ✅ |
| 3 | ①→②→③ 在真实 sm25 新格式产物上通（22 claims + 49 dispositions → 22 墙 degraded 3 债 → 出包 134 entity→source） | 本树自跑（命令与完整输出见 §2）：`claims=22 dispositions=49 debts=3 openings=85` → `walls=22 completion=degraded open_items=22 residual_debts=3` → `packet hash=6aedb54131f4 entities=134 consistency=2` | ✅ |
| 4 | ①→②→③ 旧格式也通但更差 | 未重跑（seam probe 档 `2026-09-01i_wiring_seam_probe/` 已在 `1303e8a` 量过；非本单停报的承重行） | 未核（B 层记录，不停）|
| 5 | 新格式产物 22 份、含 sm25 两层 | 逐份 `AsDrawnPlanV2.model_validate`（注意：类型在 `src/agent/reading/as_drawn/schema.py:339`，**不在** `vector_contract` 里）：**恰好 22 份通过**，含 `sm25_1f_v2.json` / `sm25_2f_v2.json` / `sm24_1f_v2.json` | ✅ |
| 6 | as-drawn 合同 disposition = `KNOWN_NOT_CONSUMED` | `vector_contract.py:252`：`ContractSpec(CONTRACT_AS_DRAWN_PLAN, Disposition.KNOWN_NOT_CONSUMED, ...)` | ✅ |

§〇 复核命令原文（行 5）：

```
$ python - <<'EOF'
import json, glob, os
from src.agent.reading.as_drawn.schema import AsDrawnPlanV2
d = "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
ok = []
for p in sorted(glob.glob(os.path.join(d, "*.json"))):
    try:
        with open(p) as f:
            obj = json.load(f)
        AsDrawnPlanV2.model_validate(obj)
        ok.append(os.path.basename(p))
    except Exception:
        pass
print("passed AsDrawnPlanV2:", len(ok))
for n in ok: print(" ", n)
EOF
passed AsDrawnPlanV2: 22
  sm24_1f_GLM_launder_non_wall.json
  sm24_1f_GLM_midline_thin.json
  sm24_1f_v2.json
  sm25_1f_CROSS_all_ambiguous.json
  ...（22 行全列，含 sm25_1f_v2.json / sm25_2f_v2.json / sm24_1f_v2.json）
```

---

## 2. ⛔⛔ A 层停报：A 项（§一 A）触发 §四 A 层 4

### 2.1 停报句

**现有 `Disposition` 枚举没有任何一个值能表达「交给 correction adapter」；A 项要落在设计稿 §9.1 第 7 步
的 `ADAPT` 就必须新增枚举值 —— 这正是派工单 §四 A 层 4 预留的停报条件。**

### 2.2 证据一：枚举全集（`src/agent/reading/vector_contract.py:90-105`）

```python
class Disposition(str, Enum):
    """What 1_correction does with a file of this contract."""

    CONSUME = "consume"
    """Pasted into the correction prompt (today: legacy reading views only)."""

    KNOWN_NOT_CONSUMED = "known_not_consumed"
    """Recognized contract that this stage has no wire for ⇒ loud failure. ..."""

    EXCLUDE = "exclude"
    """Declared non-input that lives in the same directory ⇒ dropped ..."""
```

三个值逐一对照「交给 correction adapter」：

| 值 | 机器效果（`_classify_rows`，`vector_contract.py:492-520`） | 能否表达「交给 adapter」 |
|---|---|---|
| `CONSUME` | 进 `consumed` 列表 ⇒ `pipeline.py:427-429` 取 `.consumed` ⇒ `pipeline.py:452-453` **整份贴进旧 prompt** | **否，且方向相反**（见 2.3） |
| `KNOWN_NOT_CONSUMED` | 进 offenders ⇒ `classify_vector_dir` raise `UnconsumableVectorFile`（`vector_contract.py:540-548`）——即**现状**，改了等于没改 | 否（这就是「没有 wire」的记账） |
| `EXCLUDE` | 丢弃但记 ledger，语义 = "declared non-input" | 否 |

### 2.3 证据二：改 `CONSUME` 不是可选项 —— 机器效果与设计稿正面对撞

`CONSUME` 的全部机器效果就是「被旧路贴进 prompt」：

```
$ grep -n 'classify_vector_dir\|consumed' src/agent/pipeline.py | head
62:from src.agent.reading.vector_contract import classify_vector_dir
427:    vector_files = classify_vector_dir(
429:    ).consumed
452:    for fname in vector_files:
453:        chunks.append(f"\n[reading vector] {fname}:\n```json\n{_read(vector_dir / fname)}\n```\n")
```

若把 `CONTRACT_AS_DRAWN_PLAN` 那一行改成 `CONSUME`：

1. **新链关闭（= 现行默认）时**，任何 run 目录里出现一份新格式平面产物 ⇒ 它被**整份贴进旧 prompt**。
   今天同一场景是响亮 `UnconsumableVectorFile`。这是把「响亮失败」换成「静默贴原文」——
   即 F-97 要消灭的形态在**新格式**上复活，方向与本单初衷相反。
2. 与设计稿 §8.1 正面打架：**「不允许：…correction 直接把某类源 JSON 整份 paste 给模型的执行方式…
   也不允许发现新 plan 不好处理后静默回退旧 plan」**。
3. 现有锁会红（它们属于验收 2 的「3632 条」）：
   - `tests/test_o22m1_as_drawn_producer_types.py:396` `test_as_drawn_is_still_known_but_not_consumed`
   - `tests/test_o22m1_as_drawn_producer_types.py:401` `test_no_new_contract_became_consumable`
     （`assert consuming == {CONTRACT_READING_VIEW_LEGACY}`）
   - `tests/test_o22m2_evidence_contract.py:1744`、`tests/test_o22m3_evidence_adapters.py:598`
     （同名 `test_as_drawn_is_still_not_consumed`）、`tests/test_f97_vector_contract.py:170/210` 等

   ⚠️ 这些锁的 docstring 都写明「this pin flips the day module 7 registers the adapter -- that
   flip must be an on-purpose change」——**翻 pin 本身是预期内的**，我停报不是因为「锁不许动」，
   而是**翻成的目标值在枚举里不存在**。

### 2.4 证据三：设计权威自己的目标态就是一个新值

设计稿 §8.2 第 7 条（已过审，本单 §口径来源指定节）：

> 分类结果从今天的 `CONSUME / KNOWN_NOT_CONSUMED / EXCLUDE` 收窄为
> **`ADAPT(adapter_id) / KNOWN_NOT_ADAPTED / EXCLUDE`**；不存在"分类成功所以可直接贴 prompt"。

`ADAPT` 不在现有枚举里 ⇒ 落到派工单 §四 A 层 4 的原文：「现有枚举表达不了『交给 correction
adapter』，A 项必须新增枚举值」⇒ **立刻停，不要绕**。

同时注意：新增枚举值不是加一行就能闭合的——`_classify_rows`（`vector_contract.py:479-521`）是
`CONSUME / EXCLUDE / KNOWN_NOT_CONSUMED / else→error` 四分支穷举，`ADAPT` 文件既不该进
`consumed`（不给旧路贴）也不该进 offenders（不是失败），必须有第五条分支与配套 ledger 行为
—— 这已经碰到派工单 §一 A 明令「本单不做」的「ledger 重排」的边缘。**这条边界画在哪，
是收窄工程的范围决策，不该由施工席自决。**

### 2.5 证据四：A 是 B 项的硬依赖（所以全单停，不是只停 A）

`run_correction` 的**第一拍**就是合同 preflight（`pipeline.py:765`）：

```
$ sed -n '759,765p' src/agent/pipeline.py
    # F-97 (F-c, B-03): classify and FILE THE LEDGER FIRST -- ...
    _preflight_vector_contracts(vector_dir, out_dir)

$ sed -n '722,726p' src/agent/pipeline.py
    try:
        names = discover_vector_files(vector_dir)
    except FileNotFoundError:
        return  # "no *.json at all" is an existing, separately-reported failure
    classify_vector_dir(vector_dir, names)
```

`vector_dir` 里放一份 as_drawn 新格式产物（验收 1 的前提）⇒ 今天必被
`KNOWN_NOT_CONSUMED → offenders → UnconsumableVectorFile` 拒掉，**在任何新链代码跑到之前**。
即：不先拍板 A，B 项的验收 1（「真实 sm25 新格式平面产物走完 A→C」）结构性走不通；
绕过/放宽 preflight = 动 F-97 的门 = 既不是「只改 disposition 的值」，也撞 §一 A 的禁令边界。
⇒ 按 §四 A 层「立刻停，不要绕」，**B/C/D 一并停**（实现本体虽不依赖 A，但验收 1 依赖，
先做等于赌派工方的拍板方向）。

---

## 3. 停报前已验证「随时可开工」的事实（供派工方拍板用）

①→②→③ 新格式链在本树自跑（未动任何代码）：

```
$ python - <<'EOF'
from pathlib import Path
from src.agent.correction.evidence_adapters import adapt_as_drawn_plan
from src.agent.correction.wall_compiler import compile_wall_ir
from src.agent.correction.decision_executor import build_decision_packet

raw = Path("AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_1f_v2.json").read_bytes()
art = adapt_as_drawn_plan(raw, input_id="sm25_1f", floor_ref="1f", view_type="plan")
print("① bundle ok: claims=%d dispositions=%d debts=%d openings=%d" % (
    len(art.bundle.wall_claims), len(art.bundle.face_dispositions),
    len(art.bundle.evidence_debts), len(art.bundle.opening_claims)))
comp = compile_wall_ir(art, profile="exploratory")
print("② compile ok: walls=%d completion=%s open_items=%d residual_debts=%d" % (
    len(comp.walls), comp.completion, len(comp.open_items), len(comp.residual_debt_ids)))
pkt = build_decision_packet(comp, bundle=art, round_index=0)
print("③ packet ok: hash=%s open_items=%d entities=%d consistency=%d" % (
    pkt.packet_hash[:12], len(pkt.open_items), len(pkt.entity_to_source_refs), len(pkt.consistency_results)))
EOF
① bundle ok: claims=22 dispositions=49 debts=3 openings=85
② compile ok: walls=22 completion=degraded open_items=22 residual_debts=3
③ packet ok: hash=6aedb54131f4 open_items=22 entities=134 consistency=2
```

与派工单 §〇 行 3 读数一致（22 claims / 49 dispositions / 22 墙 / degraded / 3 债 / 134 entity→source）。
B/C/D 的承重前提没有塌，停报**只因 A 项枚举缺值**。

另：新链五个入口签名确认（`adapt_as_drawn_plan` evidence_adapters.py:207 ·
`adapt_legacy_reading_view` :520 · `compile_wall_ir` wall_compiler.py:1138 ·
`build_decision_packet` decision_executor.py:138 · `run_decision_loop` :524，
后者今天只吃调用方给的固定 `responses: Sequence[CorrectionDecisionResponseV1]` = C 项要补的正是生成它们的模型拍）。

---

## 4. B 层清单（记一条，不停）

1. §〇 行 1 的 grep 读数：按单子原文命令跑**非空**（7 行），但全部是新链模块内部互引；
   「生产侧零消费者」按 `pipeline.py` 零引用理解成立。派工方若原意是「grep 字面为空」，读数不符。
2. §〇 行 4（旧格式 ①→②→③）与行 6（case_tests 368 份全旧格式）本轮未重跑，沿用 seam probe 档。
3. 派工单 §〇 表「22 条 thickness_resolution 待裁决」：我读到的对应量为 `open_items=22`
   （`WallCompilationV1.open_items`；`thickness_resolution` 是 `ResolvedWallV1` 内字段，计数口径以 packet `open_items` 为准）。

---

## 5. 需要派工方拍的一件事（唯一）

**A 项 disposition 落在哪个值：**
- (a) 新增 `ADAPT` 枚举值（设计稿 §8.2 目标态）——则需要明确：`_classify_rows` 第五分支的
  ledger 行为（ADAPT 文件不进 `consumed`、不当 offender）算不算本单可动的范围，
  以及上面 2.3 列的既有「pin 锁」是否随翻；
- (b) 临时落 `CONSUME` —— 我方证据显示它与设计稿 §8.1 正面打架且会让新格式文件在旧路上被整份
  贴 prompt（把今天的响亮失败换成静默贴原文），**不建议**；
- (c) A 项整体推到收窄工程单 —— 则 B 项验收 1 需要改口径（新格式产物从哪进 `run_correction`
  而不撞 preflight）。

拍板后 B/C/D 可立即开工（前提已全部验证，见 §3）。

---

## 6. 本轮改动清单

仅本文件。无生产代码、无测试改动（`git status` 干净，除本档新增）。
