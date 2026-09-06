# submit → consume 检查对照（A-6 返工 1）

基点 `94e899e5`，修后实现 `38bd8f5f`。本表只审阻断②，不重做已通过的 R-1…R-4 或阻断①。
表中旧/新行号都指 `src/agent/correction/tick_claim.py`，分别用 `git show 94e899e5:... | rg -n -F` 与当前文件 `rg -n -F` 取锚点；没有按 diff 计行。
“旧 consume”针对原第 493—526 行；“新 consume”针对第 530—581 行。

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

## 覆盖的方向与边界

所有影响事实/账的决定约束均在消费出口重新验证；仅“提交前必须没有 current”和“提交写 current/history/退债”保留各自阶段语义。没有把 `_current` 改名、封装赋值或添加 minter；复核原探针仍能直接赋值，再由出口内容校验拒绝。

第二道几何检查在 `src/agent/correction/opening_adjudication.py:177`，组装端点前以 `TICK_PLAN_INTERVAL_NOT_ORDERED` 拒绝倒置/塌缩。测试第 147 行主动模拟 tick 消费方回归，证明这道检查自身生效；它不替代第 572 行的第一道出口检查。

`consume` 复核完之前没有返回任何部分 facts，也不写 history、current 或待退债集合。合法行的物理排列顺序不被当成几何关系；按 edge_id 关联后校验。测试第 106 行验证正常重复消费和仅倒序序列化 rows 仍通过。

最薄弱的局部是退债复核对本会话 `_history` 完整性的依赖：本轮重放其已有事件，不新建跨进程恢复或独立账本认证。给定的源包、精度与会话历史仍是正常 API 的上下文；没有声称同时任意替换全部上下文仍能证明原决定。该边界不妨碍对不经 submit 设置的坏 current 做数值、全集、关联及退债条件全检。
