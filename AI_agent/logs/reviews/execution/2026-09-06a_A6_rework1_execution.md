# A-6 返工 1 执行档（2026-09-06，GPT）

工程档 / 科研 P0。工作树 `/tmp/a6_tickclaim_astra`，分支 `wt/09.05j_a6_tick_claim`，返工基点 `94e899e5`。
本单只处理派工单阻断②；阻断①已由主控销账，E-a 接线与三项不阻断发现均未扩入施工。没有 rebase，没有修改 `src/agent/judge/` 或旧签字产物。

## 一、改动与拒绝边界

修法是消费出口完整重检：`tick_claim.py:436` 的 `_checked_choices`、`:449` 的 `_decision_rows` 由 submit/consume 共用；`:572` 重检所有 x、z、plan 区间，`:574` 核整份响应与各行选择的对应关系。
`opening_adjudication.py:177` 在平面洞口端点装配处另以 `TICK_PLAN_INTERVAL_NOT_ORDERED` 拒绝倒置/塌缩。这一道是纵深，主拒绝发生在 TickSession.consume。

未更名或禁止赋值 `_current`，未添加私有构造器、minter、入口类型封印或针对探针值的黑名单。复核探针的直接赋值仍然执行成功，随后由数值和关联校验拒绝输出；全部事实只在 `tick_claim.py:579` 统一返回。消费失败不修改轮次或退债状态，调用方仍可显式 reconsider；submit 的原有 `RETURN_TO_STEP_ONE_INTERVAL` 行为保持在第 516—517 行。

## 二、submit() 检查逐项对照表

以下包含原 submit 的拒绝检查、条件落值和账字段构造；提交副作用也列明，避免以“不是 if”漏掉约束。表的独立已提交版本为 [submit_consume_checks.md](../../experiments/2026-09-06a_A6_rework1/submit_consume_checks.md)。
所有旧/新行号均指 [src/agent/correction/tick_claim.py](../../../../src/agent/correction/tick_claim.py)，旧版本为 `94e899e5`，修后为 `38bd8f5f`。锚点从版本文件和当前文件用 `rg -n -F` 取，未按 diff 计行。

| # | submit 检查/强制构造及旧位置 | 旧 consume 是否重做 | 修后 submit / 共用强制行 | 新 consume 重做位置、拒绝或结构理由 |
|---|---|---|---|---|
| 1 | pending/耗尽状态不接受决定（427） | 没直接核 blocked；通常由 current=None 间接挡住（495） | 506—507 | 537—538 直接复核；即使错误恢复 current，仍走原具名 pending 出口。current 已为空时先由 532 拒绝。 |
| 2 | 响应类型与 packet_id 对应本包（429） | 501 只核 record 顶层 packet/source，没有核 response | 508—509、438—440 | 558/560 从两个 JSON 响应视图恢复严格模型，563/573 均调用 438；顶层源另由 547 核。不靠调用方的对象类型标签承诺内容。 |
| 3 | current 必须尚未终结（431） | **结构上不应照搬**，消费要求已有 current（495） | 510—511 | 532—536 要求当前、预期 ID、字节与摘要一致。重复提交被 510 挡；消费若错拿另一批次，535 挡；若 current 本身被普通 bug 改坏，后面的内容全检接住。消费不承担再次提交。 |
| 4 | 响应 strict/extra forbid；action、candidate_id 形状、非空 reason（433→106—125） | 没重验响应，行 choice 只取 candidate_id | 440，共用原 107/115/117/123 | 558、560 严格 JSON 复验，再经 563/573→440；格式错误为 TICK_BATCH_RESPONSE_INVALID，合法 JSON 中的不完整决定仍由后续集合检查拒绝。 |
| 5 | 每边一项、无重复、完整 choices 集合（435—437） | **部分**：504 仅校 rows 长度/集合 | 442—444 | 555 校 rows；563 校逐行 choice 组成的全集；573 校整份 response 全集；574 比两份选择内容。重复认领、漏响应、行/响应不一致分别拒绝。 |
| 6 | reperceive 不能冻结为事实（438—439） | 没核 action；特定链行可能碰巧因 candidate 不符失败 | 445—446 | 563/573 复用 445；RETURN_TO_READING，579 尚未返回任何事实。 |
| 7 | select 的 candidate 必须属于该边（443—448） | 有（510—514），但只依 tier 找 ref，不核 action 对应 | 455—460 | 564→459 重新校候选；570 逐字节比较重建行，使 action/tier/candidate/边身份一起绑定。 |
| 8 | 一档 evaluate：同源、域、轴、声明资格、运算基数/算术（449—451→223） | 有（515），保留 | 461—463→evaluate | 564 共用同一 evaluate；568 比实际值，570 比完整行。没有改 evaluate 的已签运算口径。 |
| 9 | 二档由原 pixel 按本会话出口精度 HALF_UP，tier=pixel_only（458—459） | 有重算数值（518），但没核与 action 的绑定 | 470—471 | 564 同式重算；568、570 核值及 action/tier；549—553 另核记录中的精度声明。 |
| 10 | pixel_pending_evidence 必须有 missing_chains（453—455） | 没有 | 465—467 | 564→466 重做；EVIDENCE_DEBT_WITHOUT_MISSING_SOURCE，不允许仅改 action 就创造补证债。 |
| 11 | debt_id 按本图/边/缺链集合生成；正常 pixel/select 无新债（445、456—457、463） | 没有；525 原样导出 debt_id | 457、468—475 | 564 重造并由 570 比完整行；TICK_ROW_RECOMPUTE_MISMATCH。假债不会进入返回的 TickFact（579）。 |
| 12 | retired_debt_id 仅同源同边、无缺链且新一档（464—467） | 没有；也不导出 retired 字段 | 476—479 | 482—503 从既有历史重建提交前债状态；564 用同一条件推导，570 比对。凭空退债仍拒绝，不能因该字段未进入 TickFact 就漏校批次账。 |
| 13 | 每行 axis/pointer/witness/candidate/choice 来自对应源边（460—463） | **部分**：candidate/值重算；其余没有逐项核 | 472—475 | 564 重建全部字段，570 作 canonical bytes 比对；错边认领先被 563 集合校验挡，元数据变化由 TICK_ROW_RECOMPUTE_MISMATCH 挡。 |
| 14 | x0<x1、z_low<z_high、plan lo<hi（469—480） | **没有，阻断②** | 514→400—406；失败仍由 516—517 保留原同图回裁行为 | 572→400—406 全部重检；TICK_INTERVAL_NOT_ORDERED。出口读操作不自动增加重裁轮数；坏事实在 579 返回前被拒，调用方仍可显式 reconsider。 |
| 15 | schema、source、image、generation、response、output_precision 与 rows 冻结同一记录（481—485） | 部分：501 源/包、504 rows；没核其余及 response↔rows | 518—522 | 547 源/包、549—553 元数据、555/563/573 三个全集、574—576 两份选择一致、577 顶层字段集合；额外坐标或另一份响应不能混入。 |
| 16 | digest(record)→current 与追加 history（486—487） | 498 已核当前字节和摘要 | 523—524 | 535 保留字节/摘要核验；**不重复写 current/history**。这是提交副作用而非可重复执行的验证；改坏 current 的普通赋值仍可进行，内容出口会重检，未新增封印或私有名字屏障。 |
| 17 | 成功提交后从待退债集合移除已 retired 项（488—490） | 不执行退债副作用 | 525—527 | **不再次 pop**；482 重建提交前上下文、570 校原退债条件。若直接拿已清空的提交后 map 重放，会误拒合法批次，所以重检前提而不重做副作用。重复消费/后续重裁控制见测试第 118—137 行。 |


第 3、16、17 项没有机械照搬提交阶段副作用：消费必须已有 current，不能每次读都再记提交或再次退债。它们对应的内容条件仍全检。退债资格从第 482—503 行的提交前历史状态重建，再走相同 predicate；不会用已经 pop 过的提交后 map 错拒合法批次。

## 三、三条验收：命令与原始输出

证据目录：[2026-09-06a_A6_rework1](../../experiments/2026-09-06a_A6_rework1/README.md)。以下 probe 不调用模型，均为普通软件诊断输入。

### 验收①：改前必须复现

在源码仍为 `94e899e5` 时，从对象库取原探针，未进入复核方 worktree：

```sh
git show 6ffb1429:AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/attack_probe_2_chain_reorder.py > AI_agent/logs/experiments/2026-09-06a_A6_rework1/attack_probe_2_chain_reorder.original.py
python AI_agent/logs/experiments/2026-09-06a_A6_rework1/replay_review_probe.py
```

原文件 SHA256 为 `3d30afde38df3340a4f7657f7ceff735eb76c8e8af9e57f8d1c62515929015d1`，另核过与 Git 对象逐字节相等。runner 只把两处 `/tmp/a6_review_claude` 重定位到本工作树；打印两个模块实际导入路径，探针逻辑未改。这是 B 层运行路径适配，不是修改反例。

[reviewer_before.txt:9](../../experiments/2026-09-06a_A6_rework1/reviewer_before.txt#L9) 原文：

```text
O02:x0 legitimate candidate values (u): [0, 10000, 20000, 30000]
O02:x1 legitimate candidate values (u): [0, 10000, 20000, 30000]
legit submit() rows (x0,x1): [('O02:x0', 10000), ('O02:x1', 20000)]
FORGED consume() result: x0=30000 x1=0  inverted=True
CONFIRMED: consume() accepts an interval-INVERTED chain-backed batch built
from two individually-legitimate, pre-existing candidates of each edge.
```

### 验收②：改后同一探针具名拒绝

```sh
python AI_agent/logs/experiments/2026-09-06a_A6_rework1/replay_review_probe.py
```

[reviewer_after.txt:12](../../experiments/2026-09-06a_A6_rework1/reviewer_after.txt#L12) 原文：

```text
consume() REJECTED forged batch: TICK_INTERVAL_NOT_ORDERED
```

拒绝来自 `tick_claim.py:572 → :405—406`。原探针同时留下旧整份 response，因此另有 response/rows 不一致；本次在该比较之前已经独立咬住区间条件，未拿“旧响应”拒绝冒充区间重检。

### 验收③：至少两条自设同形输入

同形指“每行局部合法仍不足以证明整个决定合法”。本轮两条主要输入由 [test_tick_claim_consumption_recheck.py:48](../../../../tests/test_tick_claim_consumption_recheck.py#L48) 和第 52 行构造：

1. **vertical_inversion**：换成 z 轴，链节点 `[0,650,2100,3050] mm`；把 z_low 选成合法 node3=30500u、z_high 选成合法 node1=6500u。每行 candidate 属于该边，而且同步更新整份 response，排除“只是旧响应”的干扰。基点放行，修后 `TICK_INTERVAL_NOT_ORDERED`。
2. **duplicate_choice_owner**：四个数仍为 `[7500,20000,6500,21000]u`，x/z 区间都严格递增，四行 edge_id 与行数也完整。仅把 x0 行 choice 的 owner 改成 x1，整份 response 同步更新，形成两次选择 x1、遗漏 x0。基点放行，修后 `TICK_DECISION_COVERAGE_MISMATCH`。这一条不是另一种区间倒置，而是跨行身份/全集约束。

两者都直接安装记录并重算 batch ID，越过入口，但没有改变源包或 candidates。检查是关于源实体集合、边关联和区间关系的通用 predicate，与这两组数值无关。

实际命令原文：

```sh
python AI_agent/logs/experiments/2026-09-06a_A6_rework1/probe_own_inputs.py --baseline
python AI_agent/logs/experiments/2026-09-06a_A6_rework1/probe_own_inputs.py
```

`--baseline` 从 `git show 94e899e5:src/agent/correction/{tick_claim,opening_adjudication}.py` 加载旧模块到这个诊断进程的内存，与修后调用同一个输入构造函数；没有 checkout/rebase 或改写旧源码。原探针改前验收①已经是在真实未修改工作树上跑过，两种证据不混称。

[own_before.txt:4](../../experiments/2026-09-06a_A6_rework1/own_before.txt#L4) 与 [own_after.txt:4](../../experiments/2026-09-06a_A6_rework1/own_after.txt#L4) 原文：

```text
vertical_inversion ACCEPTED [('O:x0', 7500, None), ('O:x1', 20000, None), ('O:z_low', 30500, None), ('O:z_high', 6500, None)]
duplicate_choice_owner ACCEPTED [('O:x0', 7500, None), ('O:x1', 20000, None), ('O:z_low', 6500, None), ('O:z_high', 21000, None)]
vertical_inversion REJECTED TICK_INTERVAL_NOT_ORDERED
duplicate_choice_owner REJECTED TICK_DECISION_COVERAGE_MISMATCH
```

同一探针还覆盖另外十种构造。修后原文（own_after 第 6—15 行）：

```text
response_subset REJECTED TICK_DECISION_COVERAGE_MISMATCH
response_row_disagreement REJECTED TICK_BATCH_RESPONSE_MISMATCH
extra_row_with_full_coverage REJECTED TICK_DECISION_COVERAGE_MISMATCH
pending_without_missing_source REJECTED EVIDENCE_DEBT_WITHOUT_MISSING_SOURCE
unearned_retirement REJECTED TICK_ROW_RECOMPUTE_MISMATCH
wrong_debt REJECTED TICK_ROW_RECOMPUTE_MISMATCH
changed_witness REJECTED TICK_ROW_RECOMPUTE_MISMATCH
changed_generation REJECTED TICK_BATCH_METADATA_MISMATCH
response_extra_coordinate REJECTED TICK_BATCH_RESPONSE_INVALID
reperceive_cannot_be_a_fact REJECTED RETURN_TO_READING
```

其中 `extra_row_with_full_coverage` 在旧实现已经被行数检查拒绝；`reperceive_cannot_be_a_fact` 的这一特定链行在旧实现碰巧被 candidate 检查拒绝。两者是保留已有保护的控制，不冒称新发现。其余修前输出完整保留于 own_before。

健康控制：两个版本的正常批次 SHA256 均为 `0461de0422b2dfbf253532b16da904af566ac4769e7f7ee343ecee39ffe0f76b`，四个事实也逐位相同（own 日志第 2—3 行）。测试第 106 行允许仅改变 rows 的物理顺序，按 edge_id 关联而不拿序列顺序冒充几何。第 118 行锁正常退债重复消费及下一轮不重复退债；第 147 行故意模拟消费方回归，倒置/塌缩仍由 O:177 独立拒绝。

## 四、最薄弱一处

最薄弱的是**退债复核对会话历史完整性的依赖**。当前 `tick_claim.py:482` 重放已有批次和 RETURN_TO_STEP_ONE 事件，重建“该次提交之前”的债上下文；这样才能在已经退债、post-commit map 清空后仍验证合法批次。测试锁了正常退债、重复消费、下一轮不重复退债与凭空造 retired 字段，但没有建设独立的历史认证或跨进程恢复协议。

给定源包、精度与会话历史仍是这个普通 API 的上下文；本单没有声称同时替换全部上下文仍能证明原决定。它保证绕过 submit 写入坏 current 时，逐值、全集、响应/行关联、区间及退债条件仍在出口重检。该边界没有用入口封装替代出口检查，也没有将阻断①的 E-a 接线重新揽入本单。


## 五、完整跑测与逐位闭合

实现提交 `38bd8f5f` 后运行一次完整全量；运行期间只提交检查表和收集日志（`4c223571`），源码/测试相对实现提交没有后续差异。双哨兵及完整原文位于 [full_suite.txt](../../experiments/2026-09-06a_A6_rework1/full_suite.txt)，首两行为导入路径，第 442 行为汇总、第 444 行为退出码。

实际命令原文：

```sh
cd /tmp/a6_tickclaim_astra && python -c "import src.agent.correction.tick_claim as m; print(m.__file__); import src.agent.correction.opening_adjudication as a; print(a.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
```

输出原文：

```text
/tmp/a6_tickclaim_astra/src/agent/correction/tick_claim.py
/tmp/a6_tickclaim_astra/src/agent/correction/opening_adjudication.py
3894 passed, 2 skipped, 13 xfailed, 211 warnings in 540.28s (0:09:00)
EXIT_CODE=0
```

定向验证的命令和原文（[targeted.txt:8](../../experiments/2026-09-06a_A6_rework1/targeted.txt#L8)）：

```sh
python -c "import src.agent.correction.tick_claim as m; print(m.__file__); import src.agent.correction.opening_adjudication as a; print(a.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_tick_claim_a6.py tests/test_opening_adjudication_a6.py tests/test_tick_claim_consumption_recheck.py
```

```text
44 passed in 8.87s
EXIT_CODE=0
```

原有两文件 27 条，加本轮 17 条，定向为 44。基点数量从版本日志读取，没有把用户给的推算当作验证：

```sh
git show 94e899e5:AI_agent/logs/experiments/2026-09-05j_A6_tick_claim/full_suite.txt
python -m pytest --collect-only -q -n 6 -p no:cacheprovider tests/test_tick_claim_consumption_recheck.py
```

基点日志汇总原文：`3877 passed, 2 skipped, 13 xfailed, 211 warnings in 508.38s (0:08:28)`。
新增收集原文在 [test_collection.txt:1](../../experiments/2026-09-06a_A6_rework1/test_collection.txt#L1)：第 1—12 行是十二种消费变异；第 13—15 行是只读消费、合法退债、blocked 状态三项；第 16—17 行是平面装配倒置/塌缩两项。独立解析以 `tests/` 开头且含 `::` 的 nodeid 并去重，结果 17/17，末行 `17 tests collected in 1.65s` 相符。

| 结果位 | 基点 | 新增 | 相加 | 全量实际 | 差额 |
|---|---:|---:|---:|---:|---:|
| passed | 3877 | 17 | 3894 | 3894 | 0 |
| skipped | 2 | 0 | 2 | 2 | 0 |
| xfailed | 13 | 0 | 13 | 13 | 0 |
| failed | 0 | 0 | 0 | 0 | 0 |
| 所有结果合计 | 3892 | 17 | 3909 | 3909 | 0 |

没有改动旧测试，无旧测试被打红；新检查也没有要求变更基线或既存输入产物。211 warnings 原样保留，不属于测试条数。全量判定依据是以上完整汇总，不是进度点号或单独的退出码文件。

## 六、提交与范围核对

- `5daa395a`：保留原探针、仅路径重定位 runner、94e899e5 的改前复现。
- `38bd8f5f`：出口全检、平面装配检查、17 条新测试、前后探针及定向原文。
- `4c223571`：17 项检查对照表及独立测试收集原文。
- 最终交件提交包含本执行档、证据 README 补充与完整全量原文；按确切路径暂存并检查 `git diff --cached --numstat`。

`git diff 94e899e5 -- src/agent/judge case_tests` 为空；源码只动两个 correction 模块，测试只新增 `test_tick_claim_consumption_recheck.py`。旧 gt、as_measured、score_service、answer_compiler 入库格点及 B2/B4/T4-a 既有文件未改；没有安装依赖、写 site-packages、使用 git add -A 或去其他 worktree 写入。开工即存在的未跟踪派工单保持原样，未混入施工提交。

A 层核查：原探针改前确实成立，全部旧测试保持绿，未发现必须改禁区/旧签字产物的承重前提冲突；没有触发停报。B 层仅原探针的固定工作树路径按当前目录重定位。交件送 Claude 家族复核，施工方不自签 APPROVE、不合并。
