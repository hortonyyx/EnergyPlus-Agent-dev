# 执行档 · T4-a v2「`obligation` 升为正式字段」（基点已含 B4）

- **日期**：2026-09-04 · **施工方**：GLM 家族施工席 · **工作目录**：`/tmp/t4a_v2_glm` · **分支**：`wt/09.04e_t4a_v2`
- **任务书**：[`2026-09-04e_T4a_v2`](../request/2026-09-04e_T4a_v2.md)
- **结论先行**：T1–T5 全部按单完成，四个条目的对象（B4 注册表）都在本基点上，未停报。
  提交链 3 笔（T0 落地 → T1+T2 → T3+T4）+ 本档。全量
  **`3781 passed / 2 skipped / 13 xfailed / 0 failed`（exit 0）**，
  逐位闭合 = 基线 **3778** + 本单新增验收锁 **3**。

## 一、开工自证 + 全量原文

**命令原文**（与任务书 §四 同一条）：

```bash
cd /tmp/t4a_v2_glm && \
python -c "import src.agent.correction.evidence_contract as c, src.agent.correction.opening_synthesis as o; print(c.__file__); print(o.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```

**开工自证输出原文**：

```text
/tmp/t4a_v2_glm
e5b0d7d5 09.04e_dispatch_T4a_v2 (基点已含 B4)
(git status --porcelain 为空)
/tmp/t4a_v2_glm/src/agent/correction/evidence_contract.py
/tmp/t4a_v2_glm/src/agent/correction/opening_synthesis.py
```

**全量输出原文**（`-n 6`，461.18s，**有 summary 行 ⇒ 非同机竞争假红**）：

```text
3781 passed, 2 skipped, 13 xfailed, 211 warnings in 461.18s (0:07:41)
exit=0
```

**逐位闭合**：`3778（主控基线，含 B4）+ 3（本单新增测试，见 §二 #1/#2/#3 的三把新锁）= 3781`。
既有测试全部为改造而非新增（B4 的 4 处红全部随换键更新，语义见 §二 #6）。

## 二、§四 验收七条逐条对账

| # | 规则 | 状态 | 证据 |
|---|---|---|---|
| **1** | `obligation` 是枚举不是自由字符串 | ✅ | `evidence_contract.py:502` `DebtObligationV1 = Literal["elevation_chain_spans_whole_building"]`（strict `_CFG` 拒一切未定义值）。锁 `tests/test_o22m2_evidence_contract.py:2143` `test_obligation_is_a_closed_enum_not_a_free_string`：一字之差的 typo / 任意串 `"owner_b4"` / 非字符串 `1` / 缺字段全部 `ValidationError`，并从类型本身断言整个值域恰好 1 值 |
| **2** | 接线不再靠前缀 | ✅ | 锁 `tests/test_b4_opening_synthesis.py:1111` `test_obligation_not_prefix_is_the_wiring_criterion` 两方向：**A** `debt_id` 改成 `zz_irrelevant_identifier_zz`（与前缀完全不相干）、`obligation` 正确 ⇒ 销账 + synthesis 照常 retired；**B** `debt_id` 保留历史前缀逐字、`obligation=None` ⇒ 销账空 + retired 空。**机械证据**：生产代码债匹配零 `startswith`（全 src 只剩 `opening_synthesis.py:369` 键空间自检牙与 `evidence_contract.py:810` json-pointer 校验两处，均非债匹配）；匹配判据 = `redeemable_debt_ids` 内 `debt.obligation` 精确等键 |
| **3** | 「有义务的债必须能被兑现」有牙 | ✅ | T4 三层：**import**（`opening_synthesis.py:379/388` 域牙两向，见 #6 的 (5)(6) 触发）+ **运行时** `assert_obligations_backed`（`:485`，synthesis 入口 fail-fast）+ `redeemable_debt_ids` 内再查（直连路径躲不掉）。锁 `tests/test_b4_opening_synthesis.py:1170` `test_unbacked_obligation_fails_loudly`：三个入口（standalone / 直连销账 / synthesis）全部 `OBLIGATION_UNBACKED`（`:1190/:1196/:1207`），且带健康注册表控制组（同债正常销账 ⇒ 红是牙的不是输入的）。⚠️ 「造一张指向没有处理器的债」经 monkeypatch 删行到达——schema 拒绝枚举外值后，这是该状态**唯一**剩余的到达路径（与 B4 既有 `PREMISE_GATE_UNWIRED` 的 delitem 触发同型） |
| **4** | ⛔ 没碰 B4 的源绑定 | ✅ | `git diff e5b0d7d5..HEAD` 中 `binds` / `ElevationSourceIdentity` **零改动行**（grep `-+` 无命中）；src 下 `affected_refs` 仅 1 行 docstring 措辞变化（"actually passed"→"has actually passed"，模块 docstring 重排所致）。`ElevationSourceIdentity.binds` 与销账的 binds 检查段一字未动（T5） |
| **5** | 枚举面 = 今天真实需要的 | ✅ | 本分支（含 B4）mint 点盘点，`evidence_adapters.py` 全部 10 处 `EvidenceDebtV1(`：span 债（`:762` 一带，`debt_elevation_chain_span_unchecked_{input_id}`）填枚举值——**唯一非 None**；其余 9 处（`debt_pairs_absent_` / `debt_amb_` / `debt_missing_{walls,plan_openings,…}` 平面+立面+legacy）全 `None`。值域恰好 1 值，锁在 #1 的测试里从 `get_args` 断言。`evidence_adapters.py` diff **纯增 0 删** |
| **6** | 三道 import 期牙换键后仍有牙 | ✅ | `tests/test_b4_opening_synthesis.py` `test_registry_rows_are_wiring_not_decoration` **逐道重造触发**：**(1c) `DEBT_REGISTRY_HANDLER_MISSING`**（`:795`）——行内 `gate=None`，牙在行的 gate 列上，与键型无关，原样咬人；**(4) `DEBT_REGISTRY_PREFIX_AMBIGUOUS`**（`:874`）——注入键 `"elevation_chain_spans"`（是 `"elevation_chain_spans_whole_building"` 的真前缀）⇒ 键空间结构检查照咬；**TYPE `DEBT_TYPE_AMBIGUOUS`**（`:900`）——注入第二行（键 `"elevation_chain_height_spans_building"`、**共享同一 premise**）⇒ 销账侧响亮。⚠️ 旧触发（一张 `debt_id` 匹配两个前缀）在精确匹配下**结构性死亡**（dict 键不可重复）——这正是 T3 买到的；牙保护的语义（「这张债该由哪个 gate 兑现」不确定 ⇒ 响亮）由「两行声称同一 premise」这一换键后**真实可达**的等价形态继续承载，且与 import 期 `PREMISE_AMBIGUOUS` 牙构成执行侧/销账侧一对。另加两道新域牙触发：**`:918` `KEY_NOT_OBLIGATION`**（域外键=死接线）、**`:930` `OBLIGATION_UNCOVERED`**（可 mint 的义务无行=空头承诺） |
| **7** | 全量绿 · 逐位闭合 | ✅ | §一：`3781 = 3778 + 3`，exit 0，`-n 6`，有 summary 行 |

## 三、任务项执行记录（提交链）

```text
cb66ba90 T4-a T0 (rebased onto B4 base): obligation cost probe -- optional str|None field
         ↑ 任务书 §一：旧分支 7ff5d50b 的 8 行探针逐字照搬，作为本单第一笔提交
2a9d44b0 T4-a T1+T2: obligation is a required closed Literal enum, every mint fills it
ee86f5e1 T4-a T3+T4: registry keyed by obligation, unbacked obligations loud, domain teeth
```

- **T0**：8 行探针（`str | None = None` + 原注释）照搬落地。代价不在本分支重量（任务书 ⛔ 别再量一遍；
  原测量 = 旧分支 `7ff5d50b` 全量 0 红、基线逐位吻合）。
- **T1**：`Literal["elevation_chain_spans_whole_building"]` —— **定名 = B4 premise 常量
  `ELEVATION_CHAIN_SPANS_WHOLE_BUILDING` 的 lower-case snake 同名形**（`evidence_adapters.py:559`
  定义、注册表行 `premise=` 引用的正是它）。语义对齐是**机械可查的**：注册表键（=本枚举值）所在行的
  `premise` 字段就是那个常量，且 import 域牙锁住键域与枚举域互相覆盖——枚举值不可能漂离 premise 语义。
  不预留没人用的槽：值域 1 值 = 盘点表的唯一非 None（§二 #5）。
- **T2**：字段必填（无默认）——mint 必须显式决定（枚举值或 `None`）；10 个生产 mint 点全部显式填写；
  缺字段被 schema 拒（#1 锁内含此断言）。
- **T3**：注册表键 `debt_elevation_chain_span_unchecked_` → `elevation_chain_spans_whole_building`；
  销账判据 `startswith` → obligation 精确等键；`ExecutedRedemption.prefix` 字段随键语义改名 `.obligation`；
  牙函数局部变量与错误上下文键名 `prefix*` → `key*`（名词改诚实；**错误码名一字未动**——三道牙按码名是过审资产）。
- **T4**：兑现检查三层（import 域牙两向 + 入口 fail-fast + 直连路径再查），错误码
  `OBLIGATION_UNBACKED` / `DEBT_REGISTRY_KEY_NOT_OBLIGATION` / `DEBT_REGISTRY_OBLIGATION_UNCOVERED`。
- **T5**：`affected_refs` 源绑定逻辑零触碰（§二 #4）。

## 四、⛔ 明确不做条款的执行记录

- `multifloor.py` / `run_multifloor_correction`：**零触碰**（`git diff e5b0d7d5..HEAD --name-only | grep -c "multifloor"` = 0）。
- B4 的 `affected_refs` 源绑定：**零触碰**（§二 #4）。
- `case_tests/` 历史 run 产物：**零触碰**（同上 grep `case_tests` = 0；bundle `content_sha256` 变化为预期内——
  任务书 §五 A-③ 明示不算触发；仓库无 golden bundle 哈希，T0 已量）。
- `pip install -e .`：未跑。
- `git add -A`：未用（每笔逐路径 add，`git show --stat --cached` 前核过）。
- 分段提交：已兑现（3 笔 + 本档为第四笔）。
- 占位符：无（所有检查/测试均为完整实现，无 TODO / pass / 待办标记）。

## 五、停下上报核对

- A-①（动 §三 禁令）：未触发。
- A-②（枚举定名与 premise 语义对不上）：未触发——同名异形 + 域牙机械锁（§三 T1）。
- A-③（改已落库产物哈希/基线）：未触发——`case_tests` 零触碰；bundle 哈希变化为预期内。
- B 层记录：无。

## 六、最薄弱一处

**#6 的 `DEBT_TYPE_AMBIGUOUS` 触发条件被我做了载体搬移**。旧触发（一张 `debt_id`
同时匹配两个前缀）在换键后的世界里**结构性不可达**——精确相等 + dict 键唯一使「一债多命中」
在类型层消失，这恰是 T3 的目的。我把这道牙继续挂在它保护的**语义**（「这张债该由哪个 gate
兑现」不再唯一 ⇒ 销账侧响亮）上，触发形态换成「两行声称同一 premise」。
若审阅方认为验收 #6 要求的是**字面形态**（一债多处理器命中）原样可触发，则这条属于解释性
满足而非原样保留——我的反驳是字面形态在 T3 的目标世界里连构造都构造不出来，「牙必须能响」
只能落在等价可达形态上；但这是本单最依赖论证而非机械保持的一条，请复核方独立判。

次薄弱（一并请审）：验收 #3 的「造一张指向没有处理器的债」由 monkeypatch 删行到达——
schema 收紧枚举后「义务无处理器」在**静态代码**里已被 import 域牙拦死，运行时删行是唯一
剩余入口，今天没有真实代码路径会运行时改表；该牙的真实价值是防「将来扩枚举忘接线」
（会先撞 `OBLIGATION_UNCOVERED` import 牙）与防运行时表损坏。
