# 执行档 · T4-a「债的 obligation 升为正式字段」—— **T0 已交付，T1–T5 A 层停报**

- **日期**：2026-09-04 · **施工方**：GLM 家族施工席 · **工作目录**：`/tmp/t4a_glm` · **分支**：`wt/09.04b_t4a`
- **任务书**：[`2026-09-04b_T4a_debt_obligation_schema`](../request/2026-09-04b_T4a_debt_obligation_schema.md)
- **结论先行**：T0（量代价）按单完成并单独成笔（`7ff5d50b`，全量 **0 红**、基线逐位吻合）。
  **T1–T5 停报**：任务书四个条目（T3、T4、验收 #2、验收 #3）的改造与证明对象
  **`DEBT_REDEMPTION_REGISTRY` 不在本单指定基点上**——它在 `wt/09.03ag_b4` 分支
  （`85fb915a…19996872`），裁决已登记主线（`61ccdd40`）但**代码未合并**。
  ⛔ 我不 merge（超授权）、不造占位注册表（任务书禁占位符/禁预留无人使用的槽，
  且会与 B4 分支已锁的注册表 import 期牙冲突成第二真相源）、不交「只加字段不加兑现检查」
  的形态（任务书 ⭐ 第 4 条点名 = 白做）。详见 §三。

## 一、环境自证 + T0 全量原文

**命令原文**（与 pytest 同一条，按任务书 §四）：

```bash
cd /tmp/t4a_glm && \
python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```

**开工自证输出原文**：

```text
/tmp/t4a_glm
1c8a36c3 09.04ab_dispatch_B2_rework1_and_T4a
(git status --porcelain 为空)
/tmp/t4a_glm/src/agent/correction/evidence_contract.py
```

**T0 改动**（`src/agent/correction/evidence_contract.py`，`EvidenceDebtV1` 尾部 +8 行）：

```python
    description: str
    #: ⭐ T0 (2026-09-04, dispatch T4-a): a COST PROBE, deliberately loose.
    #: The approved end state is a Literal enum minted as REQUIRED by every
    #: producer; shipping it first as ``str | None = None`` exists only to
    #: MEASURE what tightening costs (which tests break, and whether by
    #: ``content_sha256`` churn or by required-field absence).  ⚠️ It rides
    #: inside ``_sorted_bundle``'s dump, so every freshly finalized bundle
    #: hash changes shape -- that measured blast radius is the point.
    obligation: str | None = None
```

烟测（strict 模式行为确认）：

```text
default obligation = None
non-str rejected: ValidationError
```

**T0 全量输出原文**（`-n 6`，473.42s，有 summary 行 ⇒ 非同机竞争假红）：

```text
3756 passed, 2 skipped, 13 xfailed, 211 warnings in 473.42s (0:07:53)
exit=0
```

### ⭐ T0 的三个数

| # | 数 | 读数 |
|---|---|---|
| ① | 红了几条 | **0** |
| ② | 哪些文件 | 无 |
| ③ | 红的原因（哈希变了 / 必填缺失） | 无红可归因。**0 红的机理逐条核实如下**，⛔ 不是「跑了没炸」的印象 |

**0 红机理（四条证据，全部本树实测）**：

1. **仓库无 golden bundle 哈希**：`grep -rln "correction_evidence_bundle_v1" case_tests/`
   = **0 个文件**。case_tests 里含 `debt_id`/`evidence_debts` 的历史 run 产物实测
   **90 个**（任务书粗量 109，以实测为准），抽查全部是**旧格式**
   `evidence_debt.json`（`schema_version: 2`，producer = `src.agent.execution.evidence_preflight`）
   与 correction_geometry/corrections 等旧产物——**与 `EvidenceDebtV1` 是两个 schema，零交集**，
   加字段碰不到它们 ⇒ 「case_tests 历史 run 产物对账红」这条停报门槛**从结构上就够不着**。
2. **同字节双跑一致性锁两侧同变仍绿**：`tests/test_o22m2_evidence_contract.py:1054`
   `assert first.bundle.content_sha256 == second.bundle.content_sha256` 在本轮全量内
   （两侧都在新字段下重算，哈希同变，断言不破）。
3. **分辨力锁未受影响**：`test_o22m2_evidence_contract.py:1070`（不同字节 ⇒ 哈希不同）照常绿。
4. **可选字段不触发必填缺失**：全仓构造点（实测 `EvidenceDebtV1(` 共 23 处：src 10 +
   tests 13；任务书粗量 24 含 `class EvidenceDebtV1` 定义行本身）全为 kwargs 调用，
   缺省即 `None`，无一处因新增字段报错。

⇒ **未触发 A 层停报门槛**（0 ≤ 20 且无 case_tests 红）。T0 单独成笔：

```text
7ff5d50b T4-a T0: obligation cost probe -- optional str|None field, full suite measured 0 red
(git show --stat: 1 file changed, 8 insertions(+))
```

## 二、§四 验收六条逐条对账

| # | 规则 | 状态 | 证据 / 原因 |
|---|---|---|---|
| **0** | 代价已实测并报数 | ✅ | §一：`7ff5d50b` + 全量原文 + 三个数 + 0 红机理四条 |
| **1** | `obligation` 是枚举不是自由字符串 | ⛔ 未做 | 停报（§三）。当前树上形态仍是 T0 探针 `str \| None`；烟测已证 strict 模式拒非 str，但「喂未定义枚举值必被 schema 拒」待 T1 |
| **2** | 接线不再靠前缀 | ⛔ **对象不在基点** | 接线判据 = `opening_synthesis.py`（b4 分支）`debt.debt_id.startswith(prefix)`；该文件不在 `61ccdd40`（见 §三事实链）⇒ 无接线可改、无变异可测 |
| **3** | 「有义务的债必须能被兑现」validator 有牙 | ⛔ **对象不在基点** | 「对应处理器」= `DEBT_REDEMPTION_REGISTRY`（b4 分支）；本树上没有处理器注册表，造一个即占位符 |
| **4** | ⛔ 没碰 B4 的源绑定 | ✅ | `git diff 61ccdd40..HEAD --stat` = 两份派工单 md（`1c8a36c3` 派工时带入，非施工改动）+ `evidence_contract.py` +8 行；`affected_refs` 逻辑（validator 内 7 处引用）一字未动 |
| **5** | 全量绿（`-n 6`）· 逐位闭合 | ✅ | 3756 passed / 0 failed，= 基线 3756 + 本分支新增 0（本单新增测试 0，因 T1–T5 未施工）；exit 0 |

## 三、⛔ A 层停报：T3/T4/验收#2/#3 的对象不在指定基点上

### 事实链（每条都可复跑）

```text
$ git merge-base --is-ancestor 85fb915a HEAD || echo "85fb915a NOT in HEAD"
85fb915a NOT in HEAD

$ git merge-base HEAD wt/09.03ag_b4 | xargs git log --oneline -1
afa467e9 09.03ag_dispatch_B4_opening_synthesis     ← 两分支在此分叉

$ grep -rn "DEBT_REDEMPTION_REGISTRY\|opening_synth\|OpeningSynthesis" src/ tests/ --include="*.py"
（零命中）                                          ← 本树上无 B4 代码

$ git show 61ccdd40 --stat --format="%s"
09.03alam_verdicts_B2_REWORK_and_B4_rework1_APPROVE
 .../verdict/2026-09-03al_B2_crossreview_gpt.md     | 131 +++++
 .../verdict/2026-09-03am_B4_rework1_crossreview_claude.md | 122 +++++
（只带进两份 verdict md，没有代码）
```

B4 的真实接线形态（`git show wt/09.03ag_b4:src/agent/correction/opening_synthesis.py`，
T3 要改的就是它，此处存档供派工方直接使用）：

```python
DEBT_REDEMPTION_REGISTRY: dict[str, DebtRedemption] = {
    "debt_elevation_chain_span_unchecked_": DebtRedemption(
        premise=ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
        gate=span_equality_gate,
    ),
}
# 销账侧（同文件）：
matches = [prefix for prefix in DEBT_REDEMPTION_REGISTRY
           if debt.debt_id.startswith(prefix)]   # ← T3 要换掉的判据
```

**任务书里依赖这个对象的四个条目**：T3（换注册表键）、T4（validator 兑现检查——
「对应处理器」就是这个注册表）、验收 #2（前缀改无关名字接线仍工作）、验收 #3
（指向无处理器的债响亮失败）。任务书 §一 粗量表量了哈希测试/构造点/case_tests 产物，
但**没有量「B4 是否已在基点上」**；单子通篇默认它在。

### 为什么三条路我都不能自行走

1. **⛔ merge `wt/09.03ag_b4` 进来再改**：任务书写死基点 `61ccdd40`；合并编排是主控的
   （B2 rework 正由 Claude 席位在 `/tmp/b2_rework_claude` 做，B4/B2/B5 的合并次序主控有
   全盘计划）。我擅自 merge 会让本单全量读数混入 B4 的 20+2 个测试、不可与基线 3756
   逐位闭合，且可能与主控合并撞车。
2. **⛔ 在本树上把注册表搬进 `evidence_contract`、留待 B4 合并时迁移**：B4 分支上的
   注册表已带 rework1 刚锁好的 import 期牙（`DEBT_REGISTRY_HANDLER_MISSING` /
   `DEBT_REGISTRY_PREFIX_AMBIGUOUS` / `DEBT_TYPE_AMBIGUOUS`）。我在另一棵树上立第二张表
   = 两个真相源 + 一笔「拆了又合」的新债；且「处理器」的真实身份（`span_equality_gate`）
   不在本树上，登记不了真名 ⇒ 只能造空表或占位行，违反「⛔ 不许留占位符」
   「⛔ 不许预留没人用的槽」。
3. **⛔ 只交 T0–T2（类型层先行）**：任务书 ⭐ 第 4 条点名「⛔ 只加字段不加这条 = 白做」。
   枚举立好、生产者必填、但兑现检查与接线证明全缺 ⇒ 交付的正是被点名的白做形态。

### ⭐ 附带一个直接打到「拍板时机」上的事实：哈希翻搅次数

任务书拍板做案 A 的理由是**时机**（「三个 case 的 gt 与 pipeline 本来就要按新格式全部重做，
现在做代价最小」）。但**今天这个基点上没有 B4**，若现在做 T1/T2：

- 所有带 `obligation` 非空的 bundle（今天 = 每个带 span 债的立面 run）`content_sha256`
  **翻搅第一次**；
- T3 接线时枚举值要与 B4 侧 `premise`/`gate` 的语义对齐定名——我在**看不到 B4 合并版**
  的情况下定的名字，到接线时若有出入（很可能：枚举值语义锚在 B4 的 gate 上），
  **翻搅第二次**。
- 等 B4 合并后一口气 T1–T4 ⇒ **只翻搅一次**。

即：**「现在做代价最小」在「基点含 B4」的前提下成立；在今天的基点上做半个，
反而可能比等合并多做一次翻搅。** 这个事实请派工方一并过目再拍次序。

### 给派工方的两条出路（我不预判，也不预设只有这两条）

- **出路一（若拍「等合并」）**：本单以 T0 收口（已成立、已提交）；T1–T5 待
  `wt/09.03ag_b4` 合入主线后**在含 B4 的基点上重派**，届时四个条目的对象都在场，
  本档 §一的 0 红机理与 §三的注册表形态存档可直接复用。
- **出路二（若拍「类型层先行」）**：本单显式缩为 T0–T2 + 验收 #1/#4/#5，T3/T4/验收 #2/#3
  **逐字搬进 B4 合并单的验收表**（⛔ 不许只留一句「后续处理」——B3 v2 的教训），
  并接受 §三「翻搅次数」段落的第二次哈希翻搅风险。

### T1 原料已备好（停报不空手）

今天真实存在的债类型（`evidence_adapters.py` 全部 mint 点实测盘点，枚举值从这里取，
⛔ 不预留无人使用的槽）：

| mint 点（行号） | debt_id 模板 | kind | 今天有处理器吗 | T2 应填 |
|---|---|---|---|---|
| :762 | `debt_elevation_chain_span_unchecked_{input_id}` | `other_known_missing` | **有**（B4 注册表唯一条目） | **枚举值**（唯一非 None） |
| :338 | `debt_pairs_absent_{input_id}` | `pairs_selection_absent` | 无 | `None` |
| :468 | `debt_amb_{input_id}_{n}` | `ambiguous_face` | 无 | `None` |
| :499/:513/:523 | `debt_missing_{walls,plan_openings,…}_{input_id}` | `missing_channel` | 无 | `None` |
| :789/:804 | `debt_missing_elevation_openings_{input_id}` 等 | `missing_channel` | 无 | `None` |
| :935/:945 | `debt_missing_walls_{input_id}` 等（legacy 侧） | `missing_channel` | 无 | `None` |

⇒ **今天真实需要的枚举值恰好 1 个**（对应 span 债；定名建议与 B4 侧
`ELEVATION_CHAIN_SPANS_WHOLE_BUILDING` premise 对齐，由派工方在含 B4 的上下文里拍）。
其余全部 `None` = 无下游义务。这个「1 个」本身是重要读数：枚举面今天极小，
正好印证「不预留」。

## 四、⛔ 明确不做条款的执行记录

- `multifloor.py` / `run_multifloor_correction`：**零触碰**（diff 只有 evidence_contract.py）。
- B4 的 `affected_refs` 源绑定：**零触碰**（见验收 #4）。
- `case_tests/` 历史 run 产物：**零触碰**。
- `pip install -e .`：未跑（全程未动 `site-packages`）。
- `git add -A`：未用（T0 提交为逐路径 `git add src/agent/correction/evidence_contract.py`）。
- 分段提交：已兑现（T0 单独一笔 `7ff5d50b`；本档为第二笔）。

## 五、最薄弱一处

**T0 的「0 红」只覆盖了「加可选字段」这一半代价**。真正要拍的代价——T2 把
`obligation` 升必填 + T4 接上兑现检查——**在本基点上量不了**（对象不在场）。
我给出的是「探针松口的代价 = 0」+「拧紧代价的结构性预判」（§三翻搅段），
后者是论证不是实测。若派工方拍出路二，第一动作应是先在含 B4 的树上把 T2 的
必填形态跑一次全量再动生产者。
