# A-6 返工 1（阻断②：consume() 跨行不变量重检）跨家族复核裁决 · Claude 家族

## 头条结论

**APPROVE-WITH-FINDINGS · 阻断 0 · 不阻断 2**

- 复核方：Claude 家族，独立于施工方（GPT 家族 `gpt-6-astra`）。
- 工作目录：`/tmp/a6rw1_review_claude`，detached HEAD `e89908cd`（基点在 A-11 合并之前，全量口径为
  `3894`，与主树当前 `3863` 不可直接比——这是预期的，本裁决不把它当异常）。
- 审阅范围：`94e899e5..e89908cd`（`5daa395a`/`38bd8f5f`/`4c223571`/`e89908cd` 四段提交）。
- 复核单：[`request/2026-09-06b_A6_rework1_crossreview.md`](../request/2026-09-06b_A6_rework1_crossreview.md)。
- 独立证据目录：[`experiments/2026-09-06b_A6_rework1_crossreview_claude/`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/)。

阻断②要求的核心交付物——「`submit()` 做过的每一项检查，`consume()` 各自重做了没有」——本轮交件的
17 项表**经两套互不依赖的口径独立复算，逐项对上，零遗漏、零多余**。攻击（区间倒置）改前复现成立、
改后被具名出口拒绝；我方自造的两条同形但不同的输入（PLAN 侧 lo/hi 走真实 `consume()`、跨代退债重放
攻击）均被正确拒绝；对 #3/#16/#17 的三项对抗检验（含对 #17 可证伪理由的直接替换实测）全部证实施工方
的论证成立；抽取的三条最承重锁做变异测试全部真红、复原后全绿；全量测试独立复算 `3894 passed / 0
failed`，逐位闭合 `3877+17=3894`，无一条既有测试被改动。

两条不阻断记录见下文（防御深度不对称 + 退债复核对会话历史完整性的依赖，均为施工方或本裁决自己指出、
且不构成当前正确性缺口的观察）。

## 独立读数（§五）

```
/tmp/a6rw1_review_claude/src/agent/correction/tick_claim.py
/tmp/a6rw1_review_claude/src/agent/correction/opening_adjudication.py
3894 passed, 2 skipped, 13 xfailed, 211 warnings in 514.84s (0:08:34)
EXIT_CODE=0
```

- `m.__file__`/`a.__file__` 跑前跑后各打印一次，均落在本工作目录 `/tmp/a6rw1_review_claude`——承重不变量成立。
- 独立 `python -m pytest -q -n 6 -p no:cacheprovider` 跑出 **3894 passed / 2 skipped / 13 xfailed / 0 failed**，
  与施工方交件读数**完全一致**。原文见 [`full_suite_claude.txt`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/full_suite_claude.txt)。
- 基线独立复核：`git show 94e899e5:AI_agent/logs/experiments/2026-09-05j_A6_tick_claim/full_suite.txt` 尾行
  = `3877 passed, 2 skipped, 13 xfailed`。`--collect-only tests/test_tick_claim_consumption_recheck.py`
  独立数出 **17 tests collected**。**3877 + 17 = 3894，逐位闭合，差额 0。**
- **既有测试有没有被改动（放水检查，必查）**：
  ```sh
  git diff --name-status 94e899e5 e89908cd -- src tests case_tests
  ```
  ```
  M   src/agent/correction/opening_adjudication.py
  M   src/agent/correction/tick_claim.py
  A   tests/test_tick_claim_consumption_recheck.py
  ```
  **只有两个源码文件被改、一个全新测试文件被加，`tests/` 目录下没有任何既有文件被修改**——
  施工方「本轮新锁没有打红任何既有测试」的主张（3877 条全部仍绿）经独立核验成立，不是放水。

## §一 独立枚举 `submit()` 检查 + 与施工方 17 项表的差集

完整方法与逐行/逐 code 原文见独立文档
[`independent_submit_consume_enumeration.md`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/independent_submit_consume_enumeration.md)，
以下是结论摘要。

**口径 A（逐行读 `94e899e5` 版本 `submit()` 全文，标号每一个 `if`/`raise`/赋值/字典构造）**：
不含被调用的 `evaluate()`/`_chain_records()`/`require_chain()`/`units()` 内部检查（这些是 submit/consume
共享调用的同一份代码，不构成 submit 独有的检查），标出 **18 个标号（A1-A18）**，其中 A16/A17/A18
是提交副作用（批次落定/历史追加/退债弹出），其余 15 个是检查/构造。

**口径 B（不依赖阅读顺序：`submit()` 能抛出的全部具名 code 集合，对旧/新 `consume()` 做差集）**：
`grep -n 'TickClaimError(' src/agent/correction/tick_claim.py` 分别对 `94e899e5` 与当前树跑，取
`submit()`/`consume()` 各自函数体自己抛出的 code 集合做差集。

**差集结果**：两套口径**完全收敛**，且都与施工方 17 项表逐项一一映射——A1↔#1、A2/A4↔#2/#4、A3↔#3、
A6/A7↔#5、A8↔#6、A9↔#7、A10↔#8/#9、A11/A12↔#10/#11、A13↔#12、行内字段来源↔#13、A14↔#14、
A15↔#15、A16/A17↔#16、A18↔#17。**两套口径都没有发现施工方表格之外的遗漏项，17 项表是完整的。**

**唯一值得记录的非阻断观察（防御深度不对称，不是正确性缺口）**：`opening_adjudication.py:177-178`
只对 PLAN 的 `along_lo_m/along_hi_m` 装配点加了「万一主防线未来回归」的第二层拦截
（`TICK_PLAN_INTERVAL_NOT_ORDERED`），**没有**对 `_elevation_document()`（122-131 行，装配
`x_range_m`/`z_range_m`）做对称的第二层。核实这**不是当前的正确性缺口**——主防线
`_require_ordered_intervals` 是 `TickSession.consume()` 内部的通用函数，PLAN 会话和 ELEVATION 会话
调用的是**同一个** `consume()` 实现，我方 `own_probe_1`（见 §三）独立证实 PLAN 侧这条主防线真实生效，
施工方与上一轮复核方的探针证实 ELEVATION 侧同一防线生效——**两侧今天都被同一把主锁挡住，没有谁在
裸奔**。差别只在于「万一主防线未来回归」这一档的第二层测试只覆盖了 PLAN 路径。记为不阻断，
详见「最薄弱一处」。

## §二 对抗检验：#3 / #16 / #17

命令与完整原始输出见 [`adversarial_16_and_3.py`/`.txt`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/adversarial_16_and_3.txt)
与 [`own_probe_2_cross_generation_debt_replay.py`/`.txt`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/own_probe_2.txt)。

### #16（`digest(record)→current` 提交副作用不重做；claim「无封印无私有名字屏障」）—— 实测证实

- `s._current = TickBatch(forged_id, forged_bytes)` 直接属性赋值，**无任何报错**（`assignment executed
  without raising: True`）；`isinstance(_current, TickBatch)`/`type(...) is TickBatch` 赋值前后均为真——
  **一道纯类型检查会对这份伪造内容照单全收**。
- 但 `consume()` 在**内容全检**处拒绝：`TICK_VALUE_RECOMPUTE_MISMATCH`。
- **结论：挡住伪造的是内容重推导，不是类型/身份封印**——与模块 docstring 自己的表态（「ordinary API
  encapsulation, not a defence against Python reflection」）及 09-05 B2 收口证明的口径（「入口收窄不是
  有效解，出口全检才是」）一致。**实测证实，不阻断。**

### #17（`_retirement_context` 重放历史而非用提交后活字典；claim「用活字典会误拒合法批次」）—— 实测证实（直接替换法）

不满足于重新推导代码逻辑，改用**直接替换法**：把 `TickSession._retirement_context` 猴子补丁为
`lambda self, current_record: dict(self._previous_debts)`（即施工方声称「会误拒」的那个朴素实现），
在一个**真实合法**的退债批次（`batch1b`，`gen0` 建债 → `reconsider` → `gen1` 用链档合法退债提交）上
分别跑「朴素版」与「真实版」：

```
naive post-commit-map consume(): REJECTED TICK_ROW_RECOMPUTE_MISMATCH  <-- false rejection of a LEGITIMATE batch
real _retirement_context consume(): ACCEPTED, 4 facts
```

**朴素实现真的会误拒这个合法批次，真实实现真的接受它**——这不是重新读一遍代码逻辑得出的推论，是
**用施工方声称会出问题的那个实现直接跑一遍**得到的结果。**claim 成立，不阻断。**

同一探针的 Part 1 另附一条我方自造的跨代攻击（见 §三），进一步证明 `_retirement_context` 对「跨代双重
退债」伪造同样有效拦截，不是只对施工方自己的单代测试有效。

### #3（`current` 必须尚未终结——consume 侧对应形态：「current 被普通 bug 改坏，后面内容全检接住」）—— 实测证实

构造一个**类型完全正确**（`TickBatch` 实例，非某种类型绕过）但**内容被「普通 bug」改坏**的 `_current`
（source_sha 被替换，模拟「不经过 submit() 的一次错误恢复/缓存回填」），直接赋值：

```
consume() REJECTED the corrupted-by-ordinary-bug current: TICK_BATCH_SOURCE_MISMATCH
```

**结论：即使类型检查会通过，consume() 的内容全检（`source_sha` 比对）仍然拦下——挡住的机制与 #16
同源（内容而非类型/身份），claim 成立，不阻断。**

## §三 三条复核（缺一不合格）

### 1. 改动前复现得出 —— 独立复现成立

不检出旧代码到工作树，而是把 `94e899e5` 版本的 `tick_claim.py` 通过 `git show` 读入内存、编译进一个
独立模块命名空间（`load_module_from_commit`），在**同一进程**里对旧模块与新模块分别跑同一份攻击，
避免 checkout 造成的树污染风险。完整脚本与原文见
[`replay_attack_before_after.py`/`.txt`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/replay_attack_before_after.txt)。

```
BEFORE (94e899e5): FORGED consume() result: x0=30000 x1=0  inverted=True
CONFIRMED: consume() accepts an interval-INVERTED chain-backed batch.
```

### 2. 改动后复现不出 —— 独立复现成立

```
AFTER (current tree): consume() REJECTED forged batch: TICK_INTERVAL_NOT_ORDERED
```

两段在同一进程、同一脚本、同一断言里完成，`assert` 校验「before 必须 ACCEPTED、after 必须以
`TICK_INTERVAL_NOT_ORDERED` 拒绝」，脚本以 0 退出——不是分别跑两次各自观察，是一次运行里对比双向结果。

### 3. 换同形但不同的输入，仍然走不通 —— 自造两条，均不同于施工方与原探针

**同形定义**：「跨行/跨批次不变量在 `consume()` 处缺失」这一类，不是「区间倒置」这一个症状。
两条均**不同于**施工方自己的两条同形输入（`vertical_inversion` 用 ELEVATION z_low/z_high、
`duplicate_choice_owner` 用跨边 choice 标签错配），也不同于原探针（ELEVATION x0/x1 借用同边候选）。

**同形输入 #1：PLAN 侧 lo/hi 借用「本边自己」的候选、走真实 `TickSession.consume()`（非
`opening_adjudication` 的冗余第二层、非 monkeypatch）**——脚本
[`own_probe_1_plan_interval_real_consume.py`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/own_probe_1.txt)：

```
P:run0:lo legitimate candidate values (u): [0, 10000, 20000, 30000]
P:run0:hi legitimate candidate values (u): [0, 10000, 20000, 30000]
legit rows (lo, hi): 10000 20000
direct `_current = <forged TickBatch>` assignment: succeeded (no error)
consume() REJECTED forged plan-schema batch: TICK_INTERVAL_NOT_ORDERED
```

**为什么同形而不同**：症状同属「区间倒置」，但走的是 **PLAN schema 分支**（`_raw_edges` 里
`as_drawn_plan_v0` 分支，`_require_ordered_intervals` 里 `":lo"/":hi"` 的字符串切片分支，与 ELEVATION
分支代码路径不同），且施工方测试套件里**唯一**的 PLAN 侧区间测试
（`test_plan_assembly_checks_intervals_even_if_tick_consumer_regresses`）是**猴子补丁掉 `consume()`**
去测 `opening_adjudication` 自己的冗余层，从未真正驱动过 `TickSession.consume()` 在 PLAN 文档上处理一份
真实伪造 `_current`——这是此前完全没被驱动过的代码路径。变异测试（§四变异 A）额外证明：把
`_require_ordered_intervals(rebuilt)` 禁用后，这条探针从 REJECTED 变成 `UNEXPECTED ACCEPT`，
证明它精确命中这条锁本身（原探针受 response 残留字段掩护，同一变异下反而被另一条检查挡住，见变异日志）。

**同形输入 #2：跨代双重退债重放**——脚本
[`own_probe_2_cross_generation_debt_replay.py`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/own_probe_2.txt)：
建债（gen0）→ 补证退债（gen1，合法关闭）→ 再次 reconsider（gen2，与该债无关的普通复议）→ 伪造 gen2
批次，声称它「也」退掉了 gen0 那笔**早已在 gen1 合法关闭**的旧债：

```
gen0 debt_id for A:x0: 6cc4fc5a...
gen1 A:x0 retired_debt_id: 6cc4fc5a...  (should equal gen0 debt: True)
gen2 A:x0 retired_debt_id (legit, should be None): None
consume() REJECTED double-retirement-across-generations forgery: TICK_ROW_RECOMPUTE_MISMATCH
```

**为什么同形而不同**：施工方自己的退债测试
（`test_consuming_retirement_replays_precommit_debt_without_retiring_twice`）只测了单代内的
「不二次退债」与幂等重复消费，从未测试「跨越两次以上世代边界、把一笔早已关闭的旧债伪造进一份
无关批次」这种边界情形——直接命中 `_retirement_context` 里 `if raw == current_record: break` 这一
历史重放停止条件的边界正确性。

## §四 分辨力：抽 3 条最承重的新锁做变异，确认真红、复原后全绿

命令与完整原文见 [`mutation_log_claude.txt`](../../experiments/2026-09-06b_A6_rework1_crossreview_claude/mutation_log_claude.txt)。

| 变异对象 | 变异内容 | 目标测试 | 结果 |
|---|---|---|---|
| `consume()` 出口 `_require_ordered_intervals(rebuilt)`（572 行，阻断②本体） | 注释掉调用 | `test_consume_rechecks_decision_invariants[vertical_inversion-...]` | **1 failed**（DID NOT RAISE）；同一变异下我方 `own_probe_1` 也变 `UNEXPECTED ACCEPT` |
| `_retirement_context`（482-503 行，item #17） | 替换为朴素 `return dict(self._previous_debts)` | `test_consuming_retirement_replays_precommit_debt_without_retiring_twice` | **1 failed**（`TICK_ROW_RECOMPUTE_MISMATCH`，合法批次被误拒） |
| `consume()` 全行内容比对 `if freeze(actual) != freeze(row): raise TICK_ROW_RECOMPUTE_MISMATCH`（570-571 行） | 加 `False and` 使其恒不触发 | `unearned_retirement`/`changed_witness`/`wrong_debt` | **3 failed**（均 DID NOT RAISE） |

三次变异均已 `git checkout -- src/agent/correction/tick_claim.py` 复原，复原后 `git status --short src/
tests/` 为空，重跑三个相关测试文件 = **44 passed**，与变异前一致。**结论：三条锁均有真实牙齿，
不是恒红/无观测力的结构，且抽取的三条覆盖了本轮阻断②的三个不同层次（跨行不变量本体、退债时序、
内容比对总闸）。**

## 未复现项清单

- 未运行真实模型（reading VLM / correction LLM）对刻度做认领决策；本单证据全部为诊断 fixture，
  与执行档的边界声明一致。
- 未逐条重新执行施工方 `probe_own_inputs.py` 里另外十种构造的原始运行（`response_subset` 等 8 项）——
  已核对其在新测试文件 `test_tick_claim_consumption_recheck.py` 中的参数化用例与断言码一致（12 组
  `CASES` 逐条对上执行档 own_after 引用的输出），未逐条重新独立运行这 8 条（已运行的是本裁决自己
  设计的 §四 变异测试，间接覆盖了其中 3 条的判定逻辑）。
- 未对 `opening_adjudication.py` 的四分类（①②a②b③）本身做变异测试——本轮阻断②的改动完全落在
  `tick_claim.py` 内（`opening_adjudication.py` 只新增一行防御性断言），四分类逻辑本身不在本单改动范围。
- 未验证「跨进程」场景（本单契约本身也明确声明不覆盖，与上一轮裁决一致）。
- 未重新审阅阻断①的销账（复核单明确该项在本单范围外，且复核单本身未提出对该销账的异议）。

## 是否改过被审对象

**改过，且已复原，如实披露**：§四变异测试对 `src/agent/correction/tick_claim.py` 做了三次临时字符级
修改（详见 `mutation_log_claude.txt`），每次修改后立即运行目标测试观察失败，随后立即
`git checkout -- src/agent/correction/tick_claim.py` 复原。三次复原后均执行 `git status --short src/
tests/` 确认无残留改动。除这三次变异-复原循环外，未对被审对象做任何其它修改；未修改任何执行档、
测试文件或契约正文。

## 最薄弱一处

不是施工方自己在执行档 §四点名的那处（退债复核对会话历史完整性的依赖——本裁决 §三同形输入 #2
已经专门针对这一点做了跨代攻击测试，结果显示它在「跨代双重退债」这个具体维度上是健壮的，施工方的
自我评估准确但略保守），而是 §一发现的**防御深度不对称**：

`opening_adjudication.py:177-178` 的 `TICK_PLAN_INTERVAL_NOT_ORDERED` 只覆盖 PLAN 侧的
`along_lo_m/along_hi_m` 装配点作为「万一 `TickSession.consume()` 未来回归」的第二层拦截，
**没有对 `_elevation_document()`（122-131 行）的 `x_range_m`/`z_range_m` 装配点做对称的第二层**。
今天两侧都被同一把主锁（`_require_ordered_intervals`）稳稳挡住，不构成当前的正确性缺口——但如果
未来一次重构不小心削弱或删除了 `TickSession.consume()` 里的这条主锁（这正是本单出现的病根：上一版
`consume()` 就是这样悄悄丢了跨行检查），PLAN 侧的测试套件会立刻发现（`test_plan_assembly_checks_
intervals_even_if_tick_consumer_regresses` 会变红），而 ELEVATION 侧目前**没有任何测试**会发现——
倒置的假窗洞坐标会无声流入 `synthesize_openings()`。这是一处**低成本、可以在下一次经过这段代码时
顺手补上**的对称性缺口（在 `_elevation_document()` 里加一行 `if facts[f"{oid}:x0"].value_u >=
facts[f"{oid}:x1"].value_u: raise ...` 及配套测试即可），但不构成本单阻断——阻断②要求的是
consume() 出口有真实拦截，这一点已经独立证实成立。

---

**分段提交说明**：证据目录（`experiments/2026-09-06b_A6_rework1_crossreview_claude/`）与本裁决文档
分两段提交——第一段提交独立探针脚本、原始输出与全量日志，第二段提交本裁决文档本身。
