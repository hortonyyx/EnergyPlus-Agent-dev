# 裁决 · NF-1 交付件跨家族复核（GLM）

- **日期**：2026-09-01 · **复核方**：GLM 家族 · **施工方**：Claude 家族施工席 · **被审 commit**：`3cdbaf1`
- **单子**：[request/2026-09-01b_nf1_crossreview_glm.md](../request/2026-09-01b_nf1_crossreview_glm.md)
- **执行档**：[execution/2026-09-01_nf1_execution.md](../execution/2026-09-01_nf1_execution.md)

---

## 1. 裁决

# ✅ **APPROVE** —— 阻断 **0** 条 / 不阻断 **4** 条

**先行声明（行使复核单 §〇 的「无维持一致义务」）**：NF-1 这条 finding 与 `/tmp` 处方是我们家族上一轮出的。
本裁决**不是**「按我说的做了就该过」——三格、两向变异、面查全部**独立重测**后过。
复核后我**维持**该 finding 与处方本身：缺键（生产者 `as_drawn_v2.py:599` 无条件写 `face_lines`，本席 grep 亲核）
与空列表（诚实读空图）确实该有相反裁决；交付忠实执行了处方且把两半都上了锁。

一句话结论：**行为变化面 = 恰好一格**（缺 `face_lines` 键：as_drawn_plan → 响亮 UNKNOWN），
其余一切同形输入（含空列表、三键全空、元素空对象、null、错版本号、checks 侧车 50 个）新旧两树行为**逐一同**。
两个方向的变异都有锁红；翻掉的两条 pin 每条都翻对了；全仓无一处剩余代码依赖旧行为。

---

## 2. 三格读数表

环境自检：开工 HEAD=`f9bac1e`、`git status --porcelain` 干净（开工时）、`.pth` 哨兵 = `58f547fa…`（两次读数一致，见 §6）。
另：复核单写「当前树 `a13120d`」，实际 HEAD 已是 `f9bac1e`（多一个 md 类 commit）；
本席对**整个** `3cdbaf1..HEAD` 核了写面：`src/agent/reading/`、`tests/test_f97_vector_contract.py`、
`tests/test_o22m1_as_drawn_producer_types.py` **零 diff** ⇒ 「与本件写面不相交」的断言对 f9bac1e 也成立（B 层记录）。

### ① `3cdbaf1^`（= `58bb59f`）——缺陷当时真的在 ✅

```bash
rm -rf /tmp/nf1_g1 && mkdir -p /tmp/nf1_g1
git -C /workspaces/EnergyPlus-Agent-dev archive 58bb59f | tar -x -C /tmp/nf1_g1
cd /tmp/nf1_g1 && python - <<'EOF'
from src.agent.reading.vector_contract import classify_vector_json
d = classify_vector_json({"schema": "as_drawn_plan_v2", "observations": {},
                          "declarations": {}, "hypotheses": {}})
print(d.contract_id, "/", d.disposition)
EOF
```
```
as_drawn_plan / Disposition.KNOWN_NOT_CONSUMED        ← 缺键骨架当时被认成合法产物
```
（import 解析已验证指向 `/tmp/nf1_g1/src/...`，非主树。）

### ② 当前树（HEAD=`f9bac1e`）——这个例子修好了 ✅

```bash
python - <<'EOF'
from src.agent.reading.vector_contract import classify_vector_json
for name, doc in [
    ("缺键骨架", {"schema": "as_drawn_plan_v2", "observations": {}, "declarations": {}, "hypotheses": {}}),
    ("空列表  ", {"schema": "as_drawn_plan_v2", "observations": {"face_lines": []}, "declarations": {}, "hypotheses": {}}),
]:
    d = classify_vector_json(doc)
    print(f"{name} -> {d.contract_id} / {d.disposition}\n   {(d.reason or 'None')[:110]}")
EOF
```
```
缺键骨架 -> unknown / None
   declares schema='as_drawn_plan_v2' but no registered contract has that value with a matching key set; ...
空列表   -> as_drawn_plan / Disposition.KNOWN_NOT_CONSUMED
   None
```

### ③ 自己找的同形输入（两树对照，当前树 / 58bb59f）✅

| 同形输入 | 58bb59f | 当前树 | 应然 | 判 |
|---|---|---|---|---|
| 缺 `declarations` 键 | unknown | unknown | unknown（三层键早在模块 1 锁住）| ✅ 不变 |
| 缺 `hypotheses` 键 | unknown | unknown | 同上 | ✅ 不变 |
| 缺 `observations` 整层 | unknown | unknown | 同上 | ✅ 不变 |
| 三键全在 + `face_lines: []` + 层内全空 | **as_drawn_plan** | **as_drawn_plan** | as_drawn_plan（诚实读空图完整形态）| ✅ 不变 |
| schema 写错版本 `as_drawn_plan_v3` | — | unknown | unknown（未注册声明）| ✅ |
| `face_lines: [{}]`（元素空对象）| unknown | unknown | unknown（元素结构有牙，模块 1 已立）| ✅ 不变 |
| `face_lines: null` | unknown | unknown | unknown | ✅ 不变 |
| `face_lines: "oops"`（类型错）| — | unknown | unknown | ✅ |
| 50 个 `*_checks*.json` 侧车（顶层借用 `schema="as_drawn_plan_v2"` 但无三层）| **50/50 unknown** | unknown | 本单不该碰它们 | ✅ 零变化 |
| 模块 1 五种引用完整性破坏（悬空 face_b / 桶键悬空 / 重复 id / gap_index 越界 / pair_candidates 悬空，真实 sm25_2f 基底）| 全 PASS | **仍全 PASS**（as_drawn_plan / KNOWN_NOT_CONSUMED）| 本单范围外 | → 不阻断 finding 1 |

⇒ **本单的行为变化面 = 恰好一格**：`observations` 缺 `face_lines` 键（含其 hybrid 变体从 AMBIGUOUS → malformed-UNKNOWN，
同一格的必然后果）。没有第二个形态被顺带改变。

---

## 3. §三 三种变异实测（全部在 /tmp 副本做，主树零接触）

副本 = `git archive HEAD` 导出，基线先跑：`python -m pytest -n 6 tests/test_f97_vector_contract.py
tests/test_o22m1_as_drawn_producer_types.py -q` ⇒ **`134 passed in 6.82s`**（与执行档自报一致）。

### 变异 1 · 逆向（把修法改回去：`face_lines` 加回 `= Field(default_factory=list)`）⇒ ✅ 3 红

```
FAILED tests/test_f97_vector_contract.py::test_nf1_missing_face_lines_key_is_a_loud_unknown
FAILED tests/test_o22m1_as_drawn_producer_types.py::test_the_declared_skeleton_is_now_a_loud_unknown
FAILED tests/test_o22m1_as_drawn_producer_types.py::test_an_empty_skeleton_hybrid_that_looks_legacy_is_loud_unknown_not_consumed
3 failed, 131 passed in 5.71s
```
含**新锁本身**红（与 commit message 主控自报一致，本席独立复现）。
且另一半 `test_nf1_empty_face_lines_list_is_still_as_drawn_plan` **没有红**——改回默认不影响「空列表合法」，
方向正确，两把锁量的真是两个不同的量。

### 变异 2 · 过头（`face_lines` 改 `= Field(min_length=1)`，空列表也被拒）⇒ ✅ 2 红

```
FAILED tests/test_f97_vector_contract.py::test_nf1_empty_face_lines_list_is_still_as_drawn_plan
FAILED tests/test_o22m1_as_drawn_producer_types.py::test_assemble_accepts_an_honest_product
2 failed, 132 passed in 7.16s
```
第二条是**预期外的加分**：`test_assemble_accepts_an_honest_product`（`test_o22m1:262`）喂无面线 percept、
`assemble()` 产出 `face_lines: []` ⇒ 「空列表能出生产者」是**既有出口承诺**——
「空列表合法」这半不是本单新发明，是把既有承诺钉住了。
⇒ **§一 的两半都锁住了**：收严空列表 ⇒ 2 红；放回缺键 ⇒ 3 红。

### 两条 pin 逐条判定（§三.1：原钉的行为该消失还是该保留？）

**pin #1** `test_the_declared_skeleton_is_still_recognised`（58bb59f 原文断言骨架 → `CONTRACT_AS_DRAWN_PLAN`）：
钉的行为 = 「空骨架被认出」。NF-1 裁定这个行为本身**该消失**（生产者造不出缺键产物）。
翻转后新断言 = UNKNOWN + disposition None + reason 点名 schema —— **消失得对**；变异 1 证明翻过的 pin 有牙。
原 docstring 里「F-97 的 R5 歧义锁依赖它」这半的接替者见下面实测。

**pin #2** `test_a_hybrid_..._is_still_ambiguous_not_consumed`：拆成两半——
- **承重半（必须保留）**：`contract_id == CONTRACT_UNKNOWN` + **不被 CONSUME**（F-97 不重开）⇒ 新测试**原样保留**
  （`disposition is not Disposition.CONSUME` + unknown）。✅
- **reason 半（该消失）**：`AMBIGUOUS` + legacy 点名。空骨架不再是合法 as-drawn 匹配 ⇒ 双匹配前提没了 ⇒
  走 BLK-A（`vector_contract.py:316`：唯一 legacy 匹配且带 `schema` 键 ⇒ malformed UNKNOWN）。**消失得对**
  ——AMBIGUOUS 的语义是「两个 detector 都说 yes」，现在 as-drawn detector 诚实地说 no，报 malformed 比报 AMBIGUOUS 更准确。
- **类覆盖接替（施工方自认最薄弱处，本席实测）**：「真·双匹配 → AMBIGUOUS 且不被 CONSUME」仍有走真实入口的锁：

```bash
python - <<'EOF'   # 真实产物 sm25_2f_v2.json + strokes ⇒ 当前树
hybrid["strokes"] = [{"id": "s1", "pen": "wall", "geometry": {}}]   # base = 真产物 deepcopy
# -> contract_id=unknown disposition=None
#    AMBIGUOUS in reason: True   legacy named: True   consumed: False
EOF
```
⇒ **翻 pin 没有换走覆盖**，且接替锁的载荷是**真实产物**（生产者真能造出的形状），比原 pin 的手造骨架更强。

### 条数代理量自查（复核单 §三 的两句）

- 「134 passed 达标 ⇒ 修好了成立吗？」——不靠条数：行为由**逐输入实测**（§2 表）+ **两向变异**（本节）背书。
- 「这些数是对着谁达标的？」——缺键锁对着生产者造不出的形态（`as_drawn_v2.py:599` 亲核）；
  空列表锁对着 `assemble()` 的既有出口（变异 2 的第二红即其证）。

---

## 4. §四 两处的逐条结论

### 4.1 「旧行为在别处还有没有锁依赖它」——面查全（本席做的，不止 4 个文件）

三面 grep（`"observations": {}` 全仓 py / `AsDrawnPlanV2` 使用者 / `classify_vector_json` 使用者）：

- **剩余 6 处 `"observations": {}` 逐一核**：`test_f97:187`（新锁，断言 UNKNOWN）·
  `test_f97:699/700`（**故意残缺** malformed 夹具，断言非法——派工单禁令 3 保护对象，内容逐字未变）·
  `test_o22m1:424/444`（两条翻过的 pin，断言 UNKNOWN）。**无一处依赖旧行为。**
- **src 侧消费者 2 个**：`correction/evidence_adapters.py:150`（classify != expected ⇒ raise，收紧方向）·
  `correction/evidence_contract.py:924`（finalize 分三档 raise，缺键骨架现在走
  `MALFORMED_DECLARED_CONTRACT` 响亮红）。**行为变化对两个生产消费者 = 安全收紧，无依赖旧行为的路径。**
- **JSON 夹具面**：全仓 `schema=="as_drawn_plan_v2"` 的 JSON = 38 个带 `face_lines` 键（含 `_TRACKED` 三件套）+ 50 个
  `*_checks*.json` 侧车（借用 schema 值但无三层结构，**58bb59f 上 50/50 本来就 unknown** ⇒ 零变化）。
- **受影响子集**（静态快照上跑，避开另两席并发写树）：
  `pytest -n 6 tests/test_f97_vector_contract.py tests/test_o22m1_... tests/test_o22m2_... m3 m4 m56
  tests/test_a8_evidence_routing.py -q` ⇒ **`300 passed in 12.62s`**，零红。

### 4.2 同步改过期 docstring 算不算超范围？——**独立判：不算，且是必要的**

1. 原文断言「the historical "declared skeleton" … **still validates**」在修后是**假话**；留着 = 文档钉住一个已删除的行为
   ——与 NF-2 三处同错（`schema.py:339` 等）同族的「叙述与代码不符」，方向相反、错误等价。**不改才该记 finding。**
2. 派工单五条禁令逐条对撞：F-97 断言（零变动，本席 `git diff 58bb59f..3cdbaf1 -- tests/test_f97… | grep '^-' | grep -c assert`
   = **0**）· 空列表（未拒，有正例+出口锁）· `:629/:630` 夹具（逐字未变，行号平移属「只记不停」）· git/跑测（未违）·
   已落库产物与 `canonical_bytes` 面（**`canonical_bytes` 哈希的是产物字节链**（`window_position.py:238/249` 等），
   **不含 schema.py 源码**，docstring 改动不进任何哈希）⇒ **无一触碰**。
3. 新 docstring 是新边界的显式声明（REQUIRED + 为什么 + 「量到零归判分」），正是本仓库「边界要说出来」的口径。

---

## 5. 复现命令（逐条可 copy-paste）

```bash
# 第①格（旧树缺陷）
rm -rf /tmp/nf1_g1 && mkdir -p /tmp/nf1_g1
git -C /workspaces/EnergyPlus-Agent-dev archive 58bb59f | tar -x -C /tmp/nf1_g1
cd /tmp/nf1_g1 && python -c "
from src.agent.reading.vector_contract import classify_vector_json as c
print(c({'schema':'as_drawn_plan_v2','observations':{},'declarations':{},'hypotheses':{}}))"
# → as_drawn_plan / KNOWN_NOT_CONSUMED

# 第②格（当前树）+ 两半
python -c "
from src.agent.reading.vector_contract import classify_vector_json as c
print(c({'schema':'as_drawn_plan_v2','observations':{},'declarations':{},'hypotheses':{}}).contract_id)   # unknown
print(c({'schema':'as_drawn_plan_v2','observations':{'face_lines':[]},'declarations':{},'hypotheses':{}}).contract_id)  # as_drawn_plan"

# 真·双匹配接替锁（真实产物 + strokes ⇒ AMBIGUOUS）
python -c "
import json, copy
from pathlib import Path
from src.agent.reading.vector_contract import classify_vector_json as c
b = json.loads(Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json').read_text())
b['strokes'] = [{'id':'s1','pen':'wall','geometry':{}}]
d = c(b); print(d.contract_id, 'AMBIGUOUS' in (d.reason or ''), d.disposition)"
# → unknown True None

# 两向变异 + 受影响子集（在 /tmp 快照副本里做）
rm -rf /tmp/nf1_cur && mkdir -p /tmp/nf1_cur
git -C /workspaces/EnergyPlus-Agent-dev archive HEAD | tar -x -C /tmp/nf1_cur
cd /tmp/nf1_cur
# 变异1: schema.py 里 "    face_lines: list[FaceLineV2]\n" → "= Field(default_factory=list)" ⇒ 3 failed
# 变异2: 同锚点 → "= Field(min_length=1)" ⇒ 2 failed（重新导出副本后再做）
python -m pytest -n 6 tests/test_f97_vector_contract.py tests/test_o22m1_as_drawn_producer_types.py -q   # 基线 134 passed
python -m pytest -n 6 tests/test_f97_vector_contract.py tests/test_o22m1_as_drawn_producer_types.py \
  tests/test_o22m2_evidence_contract.py tests/test_o22m3_evidence_adapters.py tests/test_o22m4_wall_compiler.py \
  tests/test_o22m56_decision_loop.py tests/test_a8_evidence_routing.py -q                    # 300 passed
```

---

## 6. 哨兵两次读数 + 交件前 `git status --porcelain`

```
开工前: 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/.../_editable_impl_energyplus_agent.pth
交件前: 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  （两次一致 ✅）
```
```
$ git status --porcelain        # 交件前（写本裁决之前）
?? AI_agent/logs/experiments/2026-09-01b_f156v2_measurements/
?? AI_agent/logs/reviews/verdict/2026-09-01b_o22m56v2_rework_crossreview_gpt.md
```
两个 `??` 是**另两席在飞的活**（Claude 席 F-156 v2 测量目录 / GPT 席 o22m5-6 返工裁决），**非本席产物**。
本席全程零主树写入：所有变异在 `/tmp/nf1_g1`、`/tmp/nf1_cur` 副本做（每次变异前重新导出干净快照），
src/ 与 tests/ 在 porcelain 中零条目 ⇒ **无变异留在树上**。本裁决 md 是本席唯一写入的文件。
未跑全量；全部跑测 `-n 6`；未 `pip install -e .`。

---

## 7. 不阻断 findings（4 条）

| # | 现象 → 本席复现 | 影响 | 建议 |
|---|---|---|---|
| **NF-1-R1** | **模块 1 五种引用完整性破坏（悬空 face_b / 桶键悬空 / 重复 id / gap_index 越界 / pair_candidates 悬空，真实 sm25_2f 基底）当前树仍全部 PASS**（`as_drawn_plan / KNOWN_NOT_CONSUMED`，逐条实测）——与 08-30 时行为一致 | 已知已登记的 **NF-4** 范畴（模块 1 裁决已把它折进模块 2 派工单；模块 2 已收口、`absent` 带载荷又立新单）——**非本单修法的缝**，本单范围只有缺键/空列表一对，判不阻断 | 归属既定，无需动作；提醒后续席位别把「仍 PASS」误读成本单回归 |
| **NF-1-R2**（观察记录）| 50 个 `*_checks*.json` 侧车**顶层借用源产物的 `schema` 值**（声明了一个它自己不是的契约）；改前改后均 unknown（BLK 拦住），零行为变化 | 无实害（分类器一直正确拒绝）；但「侧车借用本体声明值」是个潜在混淆源，哪天有人给 checks 契约注册同名值会静默改变这 50 个文件的分类 | 记录在案即可，不立案 |
| **复核单 B 层** | 复核单「当前树 `a13120d`」实为 `f9bac1e`（成文后主控又提了一个 commit） | 无——本席已对整个 `3cdbaf1..HEAD` 核过写面零相交 | 无 |
| **复核单事实错（→ §8 详述）** | §二第③格线索句把两批不同的破坏混成一批 | 已被本席绕开（第③格照做且做满），未造成漏审 | 见 §8 |

---

## 8. ⭐ 复核单哪里写错了（§七.7）

**§二第③格的线索句有一处事实错误**：

> 「模块 1 审的时候你们家族做过一轮『5 种结构合法但语义假』的破坏，当时全部 PASS …… **本单只处理了其中『缺键』那一种** ⇒ 另外几种今天是什么行为？」

对照我们家族自己的模块 1 裁决（`2026-08-30_o22m1_crossreview_glm.md` §二.A4）：那 **5 种全是引用完整性/身份唯一性**
（`pairs[0].face_b` 悬空 · 桶键悬空 · 重复 id · `gap_index` 越界 · `pair_candidates[0].face_b` 悬空），
**其中没有一种是「缺键」**。缺键骨架（NF-1）是同裁决 B1/B2/B3 的**独立发现**，另一批。
⇒ 「本单只处理了其中那一种」这句把两批混为一谈。**后果无害**：本席把两批都重测了（§2 ③ 表末行 + §7 NF-1-R1），
且该事实错不影响第③格实质要求的正确性（同形输入照找照喂）。

其余：复核单 §四.2 已自判「docstring 不算超范围」，本席独立复核同判（§4.2）；派工单与复核单无自相矛盾；
未见其它错。

---

**交件**：GLM 家族跨家族复核席 · 2026-09-01 · 未 commit（按单）。
