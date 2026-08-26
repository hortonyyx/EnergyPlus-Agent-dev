# 施工报告 · F-97 契约判别器（第三轮：跨家族 REWORK 返工完成）

- **日期**：2026-08-27　**施工席位**：Claude 家族　**worktree**：`/tmp/ep_f97`（分支 `wt/08.27_f97_contract`）
- **返工依据**：`../verdict/2026-08-27_f97_contract_discriminator_gpt_verdict.md`（GPT 家族 sol，REWORK / 3 阻断）
  + 派工单末尾「⛔⛔ 返工裁定」整节
- **本轮结论**：**B-01 / B-02 / B-03 三条阻断全部修复，R1–R7 全部实测通过。无第 37 条停下上报。**

> ⚠️ **累计式自包含**。第一轮（停下上报，第 36 条）= 提交 `e08c79b`；第二轮（首次施工）= `8fda4c1`。
> 本文 §八留索引，⛔ 不复述已过判据。

---

## 〇、⛔ 三条阻断：**先独立复现，再动手**

⭐ 我没有照单改，三条都自己跑出来了：

| 阻断 | 我的独立复现读数 |
|---|---|
| **B-01** | `{"schema":"future_reading_contract_v99", strokes:[合法]}` ⇒ 实测 `ContractDecision(contract_id='reading_view_legacy', disposition=CONSUME)` **⇒ 会进提示词** |
| **B-02** | 畸形边车 ⇒ `CheckReport.model_validate` 抛 `ValidationError`，而判别器返回 `stage_check_report/EXCLUDE` **⇒ 坏文件既不红也不进提示词** |
| **B-03** | 顶层 list 的 `1f_view.json` 走真实 `run_correction(..., out_dir=)` ⇒ `AttributeError: 'list' object has no attribute 'get'`，且 `_run/reading_vector_contract_ledger.json` **不存在** |

⇒ 三条**全部成立**，复核方的证据与根因定位准确。

---

## 一、三条阻断的修法

### B-01　显式声明不再无条件回落 legacy

新增 `DECLARED_SCHEMA_VALUES`（本模块登记的全部 schema 值）与 `_declares_unregistered_schema()`。
`_detect_legacy_reading_view` 开头加一条：**声明了「本模块没登记的 schema 值」⇒ 直接不是 legacy。**

⭐ **关键的分寸（R2 的坑，我第一次改就踩了）**：
最初我写的是「有 `schema` 键就不是 legacy」，**当场把双命中打没了** ——
`as_drawn_plan_v2 + strokes` 从 `AMBIGUOUS` 塌成单命中 `as_drawn_plan`。
实测抓到后收窄为「**未登记的**声明才否决」：

- 未登记声明 + legacy 结构 ⇒ `unknown` 响亮红（B-01 修好）
- **已登记**声明 + legacy 结构 ⇒ **仍走双命中路 ⇒ `AMBIGUOUS`**（R2 保住）
- 无 `schema` 键 ⇒ 结构回落照常（328 份历史产物不受影响）

### B-02　边车判据从「键名代理」搬到生产者类型

`_detect_stage_check_report` 改为 **「三键显式存在 **且** `validator/checks/schema.py:CheckReport` 解析成功」**。
⚠️ `CheckReport` 同样字段全有默认值 ⇒ **必须保留三键显式存在**，否则 `{}` 会被吞。

### B-03　分类 + ledger 提到所有 preflight 之前

新增 `_preflight_vector_contracts(vector_dir, out_dir)`，放在 `run_correction` 体内**第一批语句**，
在 `compute_evidence_debt_from_vector_dir`（会解析 `*_view.json`）**之前**：先写 ledger（永不抛），再 `classify_vector_dir` 抛点名异常。
原先那处在提示词组装前的 ledger 写入已删除（避免两处）。

---

## 二、⭐ R1–R7 实测读数（数字全真）

### R1 —— 未登记显式 schema ⇒ unknown 响亮红，且走真实入口

```
classify_vector_json({"schema":"future_reading_contract_v99", "strokes":[...]})
  -> contract_id='unknown', disposition=None
     reason="declares schema='future_reading_contract_v99' but no registered
             contract has that value with a matching key set; top-level keys=[...]"
```
入口锁 3 条，全部经 **真实 `_build_correction_messages`**（⛔ 不是只测判别函数）：
`test_r1_unregistered_schema_is_unknown_not_legacy` ·
`test_r1_unregistered_schema_fails_loudly_through_the_real_entry`（断言报文含 `2f_view.json` + 该 schema 值）·
`test_r1_unregistered_schema_never_reaches_the_prompt`。

### R2 —— 双命中仍 AMBIGUOUS（回归，没改坏）

```
{"schema": as_drawn_v2.SCHEMA, observations/declarations/hypotheses, "strokes":[...]}
  -> unknown, reason="AMBIGUOUS: matches 2 declared contracts at once:
                      reading_view_legacy (...), as_drawn_plan (...)"
```
另加 `test_r2_undeclared_legacy_still_recognized` 守住反方向（无 `schema` ⇒ 仍 legacy）。

### R3 —— 畸形边车红；43 份真边车全绿

| 项 | 实测 |
|---|---|
| 畸形夹具 `{"stage":7,"results":"not-a-result-list","report_schema_version":{...}}` | `unknown` ⇒ 真实入口响亮红并点名 `1f_view_checks.json` ✅ |
| **现存历史边车走 EXCLUDE** | **43 / 43** ✅（且逐份 `CheckReport.model_validate` 不抛） |
| **现存历史 legacy 走 CONSUME** | **328 / 328** ✅ |

⇒ **收紧零代价**：兼容面一份没丢，与复核方「43/43 都能过更严的路」的实测一致。
这两条已写成断言（`test_r3_every_real_sidecar_still_parses_as_the_producer_type` 硬断言 `== 43`；
`test_r3_all_real_legacy_views_still_consumed` 硬断言 `== 328`），⛔ 不再只是手量。

### R4 —— 真实 `run_correction` 入口：点名异常 + ledger 确实在盘上

两种负例（参数化），**都走真实 `run_correction(vdir, "{}", out_dir=stage_dir)`**：

| 负例 | 异常 | ledger 在盘上？ |
|---|---|---|
| 顶层 list `[1, 2, 3]` | `UnconsumableVectorFile`，含 `1f_view.json` + `unknown contract` ✅ | ✅ `_run/reading_vector_contract_ledger.json` 存在，`files[0].contract == "unknown"`，`consumed == []` |
| 非法 JSON `{not json at all` | `UnconsumableVectorFile`，含 `1f_view.json` + `invalid JSON` ✅ | ✅ 同上 |

⇒ **旧的 `AttributeError` 不再出现**；F-b 的点名异常与 F-c 的失败对账**同时**成立。

### R5 —— B1′ 字节比对回归（收紧后重跑）

```
dirs measured           : 56
bytes IDENTICAL         : 49
bytes CHANGED           : 7
loudly RAISED           : 0
total bytes removed     : 170455
```
⇒ **与返工前逐字相同**，B-01/B-02 的收紧**没有误伤任何真实历史产物**。

### R6 —— 全量 `-n 6`

```
3070 passed, 13 xfailed, 211 warnings in 441.75s (0:07:21)
```
⭐ 对账：基线 **3035** + 本单累计新增 **35**（上一版 23 + 本轮 12）= **3070**，`xfailed` 13 一致，`failed` **0**。

⚠️ 这一跑是在**最终 shipped 树**上跑的：上一次 R6 跑完后我又包了一行过长的测试 assert，
所以**重跑了一次**，⛔ 不拿旧数字充当新树的读数。

### R7 —— neuter **逐条**，每条都跑全量

| neuter | 结果 | 红的是谁 |
|---|---|---|
| **B-01**（去掉未登记声明否决） | `3 failed, 3067 passed, 13 xfailed` | 恰好 R1 三条，**零附带** |
| **B-02**（`CheckReport` 校验去掉，退回只看键名） | `2 failed, 3068 passed, 13 xfailed` | 恰好 R3 两条畸形锁，**零附带**（43 份真边车锁仍绿 ⇒ 说明它测的是畸形，不是兼容） |
| **B-03**（把分类/ledger 挪回 preflight 之后） | `3 failed, 3067 passed, 13 xfailed` | 恰好 R4 三条（两条参数化 + 顺序锁），**零附带** |

⇒ 三次 `passed + failed` 均 = **3070**，**定向变红成立、互不外溢**，且红的全部经真实入口。

---

## 三、改了哪些文件（本轮返工）

| 文件 | 改动 |
|---|---|
| `src/agent/reading/vector_contract.py` | +81/−16：`DECLARED_SCHEMA_VALUES` + `_declares_unregistered_schema` + `_detect_stage_check_report` 复用 `CheckReport` + 模块 docstring 增第 5 条纪律 |
| `src/agent/pipeline.py` | +32/−?：新增 `_preflight_vector_contracts`，在 `run_correction` 首批语句调用；删除原先偏后的 ledger 写入 |
| `tests/test_f97_vector_contract.py` | +192：R1(3) · R2(2) · R3(4) · R4(3) = **12 条新锁**，共 35 条 |

⛔ **不做清单全部遵守**：`wall-centerline` 两句 diff 零命中 · as-drawn 未接线 ·
未碰 F-95 邻域（`validator/data_model.py`/`checks/kernel.py`/`test_f95_*`/`test_f13_*`）· 未碰 `src/agent/judge/` ·
未追 F-106 · **未动 N-01 / N-02** · **未回退那 4 条 allowlist 删除**。

---

## 四、⭐ 关于派工方三条题面错的处理

1. **`as_drawn_plan_v2` 份数**：⭐ **我第一轮实测就是 77**（32 读图产物 + 45 checks 报告），
   是被派工单「132 份」带着改过去的。**本轮已改回实测值**；as-drawn 家族合计 **85**（77+4+4）。
   ⇒ 教训我照单收下：**派工方给的数与我的实测冲突时，以实测为准并当场顶回来**，⛔ 不许默默对齐。
2. **allowlist 4 条**：按裁定**不回退**。我上轮自陈的「行为没覆盖」是事实但归为 N-01，⛔ 本单不做，
   也⛔ 没有靠往不可达集合塞已可达模块来假装修好。
3. **`stage_check_report` 签名**：B-02 正是我上轮 §八#3 自陈「弱的那个是这一个」的地方 ——
   ⭐ **我识别出了它弱，却没有去修**。这条比阻断本身更值得记：**自陈不确定 ≠ 已处理**。

---

## 五、⭐ 我自己认为最可能塌的地方（必答）

1. **⭐ 最不确定：`DECLARED_SCHEMA_VALUES` 是本模块自己维护的第二处清单。**
   `as_drawn_plan_v2` 那个值来自 import（对），但**「哪些值算已登记」这份集合是我手写的** ——
   将来往 `CONTRACTS` 里加一条契约却忘了同步这个 frozenset，
   就会出现「已登记的契约被 B-01 判成未登记」的静默错配。
   ⭐ 严格更优的做法是**从 `CONTRACTS` 自动派生**该集合，但 `CONTRACTS` 的 detect 是闭包、
   schema 值没有以数据形式暴露在 `ContractSpec` 上 —— 要改就得动 `ContractSpec` 的形状。
   我判断这属于本轮范围外（三条阻断都不要求），**故留着并在此点名**。
   **这是本轮我最可能被推翻的一处**，且它是 F-97 同型（「第二个定义」）的第三次现形。
2. **`_preflight_vector_contracts` 现在做了两遍分类**（这里一遍、`_build_correction_messages` 里一遍）。
   行为上确定性一致，但**「两处各自分类」本身就是我上一条担心的形状**：
   将来若有人只改其中一处的过滤口径，两者会静默分叉。
3. **R3 的两条硬断言（`== 43` / `== 328`）会随仓库内容变化而红。**
   它们现在守的是兼容面，但**任何人新增一份 `0_reading/*.json` 都会让它们红** ——
   这可能被后来者当成「误报」而放宽，从而悄悄丢掉兼容面守卫。⚠️ 我没有给它们写「为什么是这个数」的出口。
4. **B-02 用 `CheckReport` 做信任根，但我没有验证「生产者写盘时用的就是这个类型」**，
   只验证了「43 份现存产物能被它解析」。⇒ 这仍是**产物侧**证据，不是**代码侧**证据
   （`validation_run.py:292 _write(rdir/..., rep)` 我没有回溯 `rep` 的构造类型）。
   同族 [[is-this-conclusion-product-side-or-code-side]]。
5. **本轮跑测纪律**：⭐ 三次 neuter 全量 + 两次干净全量，**全程没有在跑测时动树**（上轮踩过一次，这轮没再犯）。
   但每次 neuter 我都是**手工 patch/还原**，靠 `cp` 备份；若某次还原不全，
   后续读数就会带着残留 —— 我用最终 `git diff` 与全量 3070 交叉核对过，但这条链**依赖我自己不出错**。
