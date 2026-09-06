# 独立枚举 `submit()` 检查 —— 两套互不依赖的口径

复核单 §一要求：不许照着施工方的 17 项表核，要自己用两套口径独立枚举一遍。以下是两套口径的
原始产出，以及它们与施工方交件表（`AI_agent/logs/experiments/2026-09-06a_A6_rework1/submit_consume_checks.md`）
的差集。

## 口径 A：逐行读 `94e899e5` 版本 `submit()` 全文，标号每一个 `if`/`raise`/赋值/字典构造

来源：`git show 94e899e5:src/agent/correction/tick_claim.py`，`TickSession.submit`（旧行号 426-491）。

逐行标号（只标 `submit()` 自己函数体里的检查/构造，不含被调用的 `evaluate()`/`_chain_records()`/
`require_chain()`/`units()` 内部检查——这些是 submit 和 consume 共享调用的同一份代码，不构成
submit 独有的检查）：

| 标号 | 行 | 内容 |
|---|---|---|
| A1 | 427-428 | `self._blocked` 非空 → 拒绝（pending/耗尽状态） |
| A2 | 429-430 | `type(response) is not TickResponse or response.packet_id != self._packet.packet_id` → `STALE_TICK_RESPONSE` |
| A3 | 431-432 | `self._current is not None` → `BATCH_ALREADY_DECIDED_USE_RECONSIDER` |
| A4 | 433 | `response = TickResponse.model_validate(response.model_dump(mode="python"))`——强制重新触发 pydantic 校验（含 `TickChoice.choice_shape` 的 `CHOICE_CANDIDATE_SHAPE`/`CHOICE_REASON_REQUIRED`，以及 `extra="forbid"`/`strict=True`） |
| A5 | 434 | `choices = {c.edge_id: c for c in response.choices}`——构造，不是检查本身 |
| A6/A7 | 435-437 | `len(choices) != len(response.choices)`（无重复）或 `set(choices) != {e.edge_id for e in edges}`（全集覆盖）→ `TICK_DECISION_COVERAGE_MISMATCH` |
| A8 | 438-439 | 任一 `choice.action == "reperceive"` → `RETURN_TO_READING` |
| A9 | 446-448 | `select` 动作时 `candidate is None`（候选须属于该边自己的 `edge.candidates`）→ `UNKNOWN_TICK_CANDIDATE` |
| A10 | 449-451 | `evaluate(candidate.expression, ...)`——调用共享求值函数（内部签名/域/资格检查见下方注） |
| A11 | 453-455 | `pixel_pending_evidence` 且 `not edge.missing_chains` → `EVIDENCE_DEBT_WITHOUT_MISSING_SOURCE` |
| A12 | 456-457 | `debt = digest(freeze(dict(image=, edge=, missing=)))`——debt_id 构造 |
| A13 | 464-467 | `retired_debt_id` 赋值条件：`tier=="chain_backed" and not edge.missing_chains and edge_id in previous_debts and previous_debts[edge_id][1]==source_sha` |
| A14 | 469-480 | `by_id` 循环：`x0<x1`/`z_low<z_high`/`lo<hi` 顺序检查 → `RETURN_TO_STEP_ONE_INTERVAL`（触发 `reconsider`） |
| A15 | 481-485 | `record = freeze(dict(schema=, packet_id=, source_sha=, image_id=, generation=, response=, output_precision=, rows=))`——记录构造 |
| A16 | 486 | `self._current = TickBatch(digest(record), record)`——批次落定 |
| A17 | 487 | `self._history.append(record)`——历史追加（副作用） |
| A18 | 488-490 | 成功后从 `_previous_debts` 弹出已退债的 edge_id（副作用） |

**与施工方 17 项表比对**：A1↔#1，A2/A4↔#2/#4，A3↔#3，A6/A7↔#5，A8↔#6，A9↔#7，A10↔#8/#9，
A11/A12↔#10/#11，A13↔#12，（行内字段各自来源）↔#13，A14↔#14，A15↔#15，A16/A17↔#16，A18↔#17。
**逐项对上，零遗漏、零多余。**

## 口径 B：不依赖阅读顺序——`submit()` 能抛出的全部具名 code 集合，对旧/新 `consume()` 做差集

```sh
grep -n 'TickClaimError(' src/agent/correction/tick_claim.py   # 对 94e899e5 与当前树分别跑
```

**旧 `submit()` 函数体自己抛出的 code**（不含共享的 `evaluate`/`_chain_records`/`require_chain`/`units`）：
`<self._blocked 的值>`、`STALE_TICK_RESPONSE`、`BATCH_ALREADY_DECIDED_USE_RECONSIDER`、
`TICK_DECISION_COVERAGE_MISMATCH`、`RETURN_TO_READING`、`UNKNOWN_TICK_CANDIDATE`、
`EVIDENCE_DEBT_WITHOUT_MISSING_SOURCE`、`RETURN_TO_STEP_ONE_INTERVAL`。

**旧 `consume()`（493-526）自己抛出的 code**：`TICK_BATCH_INVALIDATED`、`TICK_BATCH_NOT_CURRENT_DECISION`、
`TICK_BATCH_SOURCE_MISMATCH`、`TICK_DECISION_COVERAGE_MISMATCH`（部分）、`TICK_CHOICE_RECORD_MISMATCH`、
`TICK_TIER_INVALID`、`TICK_VALUE_RECOMPUTE_MISMATCH`。

**差集（submit 有、旧 consume 无对应机制）**：`self._blocked` 状态判断、`STALE_TICK_RESPONSE`/schema 复验、
`BATCH_ALREADY_DECIDED_USE_RECONSIDER`（结构性不适用）、`RETURN_TO_READING`（action 判断）、
`EVIDENCE_DEBT_WITHOUT_MISSING_SOURCE`、`RETURN_TO_STEP_ONE_INTERVAL` 对应的跨行不变量。
**这个差集与口径 A 的结论完全一致**，且与施工方表中标注「没有」/「部分」的各行一一对应。

**新 `consume()`（530-581）新增的 code**：`TICK_BATCH_RECORD_INVALID`、`TICK_BATCH_METADATA_MISMATCH`、
`TICK_BATCH_RESPONSE_INVALID`、`TICK_ROW_RECOMPUTE_MISMATCH`（替代旧 `TICK_CHOICE_RECORD_MISMATCH`/
`TICK_TIER_INVALID`，一次全行内容比对覆盖二者）、`TICK_BATCH_RESPONSE_MISMATCH`、`TICK_INTERVAL_NOT_ORDERED`
（新增独立函数 `_require_ordered_intervals`，submit/consume 共用）。**差集清零**——旧差集里的每一项在新
`consume()` 里都能指到具体承接它的机制。

## 结论：17 项表是完整的，两套口径都没有发现遗漏

两套口径彼此独立（一套按代码顺序逐行标号，一套按错误码集合做差集，不参考代码位置），
结果完全收敛，且都与施工方表格一一映射，未发现被换掉的外延。

## 唯一值得记录的非阻断观察：防御深度不对称，不是正确性缺口

`opening_adjudication.py:177-178` 只对 **PLAN** 的 `along_lo_m/along_hi_m` 装配点加了第二层
（`TICK_PLAN_INTERVAL_NOT_ORDERED`，防「万一 `TickSession.consume()` 未来回归」），
**没有**对 `_elevation_document()`（122-131 行，装配 `x_range_m`/`z_range_m`）做对称的第二层。

**核实这不是当前的正确性缺口**：主防线 `_require_ordered_intervals` 是 `TickSession.consume()`
内部的通用函数，对 `:x0/:x1`、`:z_low/:z_high`、`:lo/:hi` 三种后缀一视同仁，PLAN 会话和
ELEVATION 会话调用的是同一个 `consume()` 实现——我方 `own_probe_1_plan_interval_real_consume.py`
独立证实了 PLAN 侧这条主防线真实生效（`TICK_INTERVAL_NOT_ORDERED`），施工方与上一轮复核方的探针
证实了 ELEVATION 侧同一防线生效。**两侧今天都被同一把主锁挡住，没有谁在裸奔。**

差别只在于：`test_plan_assembly_checks_intervals_even_if_tick_consumer_regresses` 这条「万一主防线未来
回归」的第二层测试，只覆盖了 PLAN 路径，没有对称覆盖 ELEVATION 路径（`_elevation_document`）。
若 `TickSession.consume()` 的区间检查未来被误删，PLAN 侧仍有第二层拦截，ELEVATION 侧会直接
无声流入 `synthesize_openings()`。**记为「最薄弱一处」的候选，不阻断**（详见裁决书正文）。
