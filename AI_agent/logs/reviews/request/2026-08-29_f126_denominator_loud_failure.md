# 派工单 · F-126：reading 判分的分母不许静默返回空

- **日期**：2026-08-29
- **派工方**：orchestrator（Claude 主控）
- **施工席位**：Claude 执行档
- **复核席位**：GLM（跨家族，⛔ 与施工方不同厂商）
- **档位**：**工程档**（碰 `src/agent/judge/`，属成绩产出路径）⇒ gate① + 全量绿 + 跨家族审
- **基线 commit**：`4efb959`（分支 `08.23_AsDrawnReading`）

---

## 〇、⛔ 先读这三条（读完再动手）

1. **本单只做 F-126 一条。**⛔ 不要顺手改正交吸附（那是 F-129，已改判为**能力缺口**、排期归 C2）；
   ⛔ 不要顺手改事实层 / 出模形式（那是 ②-1，另有包）。
2. ⛔ **绝对不许跑 `pip install -e .` 或任何写 `site-packages` 的命令** —— venv 全机器共享，
   2026-08-27 出过 `.pth` 被改指导致一次权威全量读数作废的事故。
3. **停下上报触发器是【分层】的**：
   - **承重前提错**（下面任何一条「已实测」的事实你复现不出来）⇒ **停下，上报，别猜着改**
   - **外围数值错**（行号偏了、计数差一个）⇒ **记一行，继续做**，交件时一并说

---

## 一、缺陷是什么（已由 orchestrator 独立复现，2026-08-29）

`denominator()`（[`src/agent/judge/as_drawn/denominator.py:107`](../../../../src/agent/judge/as_drawn/denominator.py#L107)）
在拿到一份**被上游门挡下**的 DXF 时，会**正常返回一个全空的分母**，不报错、不降级、不留痕。

**实测（两份 DXF 同在 `case_tests/test_baseline/gt_sources/sm25-L_anchor/`，视图 `plan-F1`）**：

| 喂什么 | targets | opening_targets | wall_layer_segments_collected |
|---|---|---|---|
| `sm25-L_t3.dxf`（签字件） | 110 | 31 | 225 |
| `sm25-L_t3_as_received.dxf` | **0** | **0** | **0** |

**真因不是几何**：[`tarch_normalize.py:706`](../../../../src/agent/judge/tarch_normalize.py#L706) 有一道源图哈希门 ——
`actual_sha != request.source_dxf_sha256`（或 request 自哈希不符、或 ownership 不符）⇒ 记一条
`tarch_input_source_hash_mismatch`（severity = **BLOCK**）并在
[`:710`](../../../../src/agent/judge/tarch_normalize.py#L710) **return 全空 `P1PlanViewGeometry`**，一行几何都不跑。

⛔ **而 `denominator()` 的返回值里根本没有诊断字段**。实测顶层键**恰好 9 个**：
`allowed_not_required / floor_id / ledger / opening_ledger / opening_targets / params / rule_version / targets / view_id`
⇒ **那条 BLOCK 诊断被丢掉了。**

**危害**：分母为 0 的判分，与「产物全对」「本来就无题可判」在**产物上不可区分** ——
下游会把"尺子没量"读成"被测对象差"。同族 F-64「零产出不报红」。

---

## 二、要做什么（三条，⛔ 逐条都要有对应的锁）

### R1 · `denominator()` 必须把诊断透出来

返回值增加一个 **`diagnostics`** 顶层键，承载 `geo.diagnostics` 的内容（至少 `code` + `severity`）。
⛔ 不许只在日志里打印。

### R2 · 空分母一律**响亮失败**，⛔ 不许返回 `targets: []`

**两种失败必须可区分**（⛔ 不许压成同一个出口 —— [[absence-conflates-causes-in-observables]]）：

| 情形 | 期望行为 |
|---|---|
| **上游有 BLOCK 诊断**（哈希门 / S0 失败等）| 响亮失败，**错误信息里点名那些诊断码** |
| **几何跑通了、但目标数为 0** | 也响亮失败，但**理由不同**（"几何跑通但零目标"）|

**「响亮失败」的形式由施工方定**（raise 或返回带显式失败状态的结构），
但必须满足：**调用方不可能把它当成一份正常的分母继续用下去**。
⚠️ 现有调用方只有本文件的 `main()`（[`:315`](../../../../src/agent/judge/as_drawn/denominator.py#L315)）
与实验档 `run_all.py`；**tests/ 里零调用**（见 §三）。

### R3 · 被 D1 丢弃的**非正交线段**要出账

`ledger.excluded_non_orthogonal` **已经在计数**，但它只是个数字。
⇒ 补上**被丢弃线段的清单**（至少 axis/const/lo/hi 或原始端点），让"丢了什么"可点名。
⛔ **本条只做「出账」，⛔ 不改丢弃行为本身**（改行为 = F-129，不在本单）。

---

## 三、⭐⭐ 这一单同时是这两个文件的**第一把锁**

**已实测**：`grep -rln "as_drawn.denominator\|as_drawn.reading_grade" tests/` ⇒ **0 个文件**。
⇒ `src/agent/judge/as_drawn/denominator.py` 与 `reading_grade.py` **全仓零测试锁**。
⚠️ 含义：**「全量绿」对这两个文件没有任何保护力**，回归不会被现有测试抓到。

### 锁的最低要求（⛔ 每条都要有夹具，⛔ 不许只有负向断言）

| 锁 | 夹具 | 判据 |
|---|---|---|
| **L1 好输入仍然正常** | `sm25-L_t3.dxf` + `request.json` + `plan-F1` | targets == 110 · opening_targets == 31 · `wall_layer_segments_collected` == 225 |
| **L2 坏输入响亮失败** | `sm25-L_t3_as_received.dxf` + **同一份** `request.json` + `plan-F1` | 必须失败；失败信息里**出现 `tarch_input_source_hash_mismatch`** |
| **L3 诊断真的透出来了** | 同 L2 | 返回/异常里能取到诊断码，⛔ 不是只在 stdout |
| **L4 非正交出账** | 见下 | 被丢弃线段清单**非空且条目数 == `ledger.excluded_non_orthogonal`** |

⭐ **L2/L4 的夹具是仓库里现成的真货**（一好一坏就摆在同一个目录），⛔ 不要自己造合成 DXF。

⚠️ **L4 的夹具方向**：签字件的 `excluded_non_orthogonal` **实测 = 0** ⇒ 拿它当夹具**这条锁没有牙**。
必须用**在那个方向上真有存货**的输入。已实测：`_as_received.dxf` 在**绕过哈希门后**
`excluted_non_orthogonal = 1`（orchestrator 用改签哈希的临时 request 探得，探针在 scratchpad、未入库）。
⇒ **施工方需要自己解决"怎么让 L4 有存货"**：可以为测试构造一份声明了正确哈希的 request，
也可以直接对 `denominator()` 内部的那段逻辑做单元级夹具。**⛔ 无论哪种，不许把 `_as_received.dxf`
或任何新 DXF 写进 `gt_sources/` 或 `gt/`**（那是受保护的答案根）。
⚠️ 同族教训 [[gate-teeth-direction-follows-fixture-inventory]]：**病灶方向上没存货的锁 = 全绿骗过**。

---

## 四、验收（⛔ 逐条都要能不通过）

1. **L1–L4 四把锁全部新增并通过**；⭐ 交件时**逐把说明「不加这处改动，这把锁会不会红」** ——
   答不出"会红"的那把锁等于没有分辨力（[[gate-with-only-negative-assertions-is-unobservable]]）。
2. **主控权威全量之外，施工方自己先跑一次全量**：`pytest -n 6`（⛔ 不加 `-m`，⛔ 不用 `-n auto`）。
   贴**汇总行原文**，⛔ 不许用 `| tail` 之类会吞掉退出码的写法。
3. **`.pth` 前后哨兵**：跑测前后各记一次 editable 装机文件的哈希，**两次相同才算数**。
4. ⛔ **不许扩范围**：交件时贴 `git diff --numstat` **原文**；预期只碰
   `src/agent/judge/as_drawn/denominator.py` + 新增的测试文件。碰到别的文件 ⇒ 说明理由。

---

## 五、⭐ 给复核方（GLM）的三问

1. **再找一种能骗过这四把新锁的真实错误形态。**（⛔ 不是造一个合成 bug，是"哪种真实改法会让它们全绿"）
2. **L4 那把锁的存货方向对吗？** 施工方给它造的夹具，是不是也落在"病灶方向上没存货"的坑里？
3. **「响亮失败」真的响亮吗？** 换一份同形输入（另一个 case / 另一个 view），这条路**仍然走不通**吗 ——
   还是只在 sm25 `plan-F1` 这一个例子上修好了？（[[rework-review-needs-the-same-shape-input]]）
