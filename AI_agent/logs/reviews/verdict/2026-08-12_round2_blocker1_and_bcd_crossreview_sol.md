# 第二轮跨家族复审裁决 — sol

- 日期：2026-08-12
- 审阅对象：未提交工作树（unstaged diff + untracked files）
- 总判定：**CHANGES REQUIRED**
- 审阅状态：**已触发“前提错误即停”，不是完整复审**

## 1. 结论

本轮先坐实了请求书 §1 的一个错误前提：

> `position_evidence_pair_mismatch` 没有 mutual-nearest 就结构上不可能触发。

这句话不成立。当前没有实现全 catalog mutual-nearest 的 shadow decision，仍会在至少两条已实例化路径返回该码：

1. cited plan/elevation 的 endpoint distance 超过 pairing tolerance；
2. cited elevation 的 z-scope 唯一解析到与 window 不同的楼层，即使 along distance 仍在 tolerance 内。

本席对这两条路径作了动态验证，均真实返回 `position_evidence_pair_mismatch`。因此请求书用该错误码的“可否触发”来证明 mutual-nearest 是否存在，判据无效。

这项前提错误不改变范围裁定：**mutual-nearest 属于 S2；当前摊 B 不能按完整 S2 验收。** 设计稿 §5.3 把唯一 mutual-nearest、ambiguity margin 和全 draw source 不复用列入同一个 pairing decision 的通过条件；§10 S2 明令实现 `pairing decision`，S3 只是冻结 citation 规则并把 **S2 decision** 升成 blocking gate；§12.2 又把“删 mutual-nearest 后专用夹具转红”写进 Pair positive 锁。因此把 mutual-nearest 推给 S3 与已批准设计不相容。

当前 shadow 用 `accepted` / `PASS` 表达只覆盖部分判据的结果，产物又没有机器可读的 coverage/未实现条件，确实会把结论说得比证据更强。**要把本批次作为 S2 关闭，必须补齐 §5.3 条件 2/3/4。** 若派工方选择不扩大本批次，则“显式部分实现标记”可以止住语义误导，但只能把交付改名为 partial telemetry milestone，不能仍宣称 S2 完成：

- 不得继续输出无修饰的 `PASS` / `accepted`；
- 必须结构化记录 decision/ruleset version、`evaluated_conditions` 与 `unevaluated_conditions`，不能只写自由文本备注；
- S3 的 consumer 必须 fail closed，拒绝把 coverage 不完整的 decision 升为 gate。

请求书还把当前实现概括为“6 条里的 3 条”。本席在停止点前没有完成逐条件、跨层校验链的行为归因，因此**不签这个精确数量**。已证明的是“覆盖不完整且无披露”，不是恰好覆盖三条。

按照请求书 §5.4 的硬纪律，发现岔口/分类/数量前提错误后必须停止上报。本席因此没有继续审 BLOCKER-1、摊 C/D、上一轮七条未裁定项，也没有用未完成的检查给它们签关闭。

## 2. 停止触发证据

运行：

```text
tests/test_f9_route2_s2_authoritative_projector.py::test_f9_oracle_w_f1_n1_hand_computed_numbers_match_design_doc
tests/test_f9_route2_s2_authoritative_projector.py::test_east_view_wrong_floor_citation_rejected_by_zscope_not_by_distance
```

结果：

```text
2 passed in 9.66s
rc=0
```

第一条用真实 F-9 fixture：错误 twin 的 endpoint distance 为 `10.00 m`，返回 `position_evidence_pair_mismatch`。第二条把 floor-1 window 引到 floor-2 elevation source；along distance 仍小于 `0.300 m`，仅 z-scope 不同，同样返回该码。第二条直接给 decision 的只是 cited plan 与 cited elevation，不存在 mutual-nearest 候选排名可供执行。

独立日志：

```text
/tmp/sol_round2_premise_pair_mismatch_20260812.out
/tmp/sol_round2_premise_pair_mismatch_20260812.rc
```

## 3. 本轮逐项状态

| 项目 | 本轮判定 | 说明 |
|---|---|---|
| **BLOCKER-1** — 无条件确定性核印章 + 判卷验印 | **未裁定；不能确认关闭** | 在触发停止前尚未完成五类路径、第六类搜索、`boundary=None` 下游传播、伪造与 hash/批准链行为验证。按审计状态继续保留上一轮 open，直到一次完整复审确认关闭。 |
| **§1 / 摊 B：mutual-nearest 范围** | **属于 S2；当前未完成** | §5.3、§10 与 §12.2 三处合同一致；S3 消费并升格 S2 decision，不负责事后补全 decision。 |
| **§1 / 摊 B：部分判据却报 PASS** | **未关闭，必须改** | 当前产物没有具名 coverage，`PASS`/`accepted` 语义过强。完整 S2 要补条件 2/3/4；部分里程碑只能输出显式 incomplete/partial 状态并阻止 S3 承重。 |
| **摊 C：标注法观测量** | **未裁定** | 停止后未审四态、真实接线及第三方向 neuter。 |
| **摊 D：F-23 测本次运行副作用** | **未裁定** | 停止后未独立复现两个 `/tmp` 隔离仓旧失效模式，也未裁“一次性纪律检查烤成永久测试”的定性。 |
| **F-24：sidecar cache key 不含印章** | **未裁定** | 未审 cache hit/miss 行为与 schema 10 入口。 |
| **F-25：两个 `SCORER_SCHEMA`** | **未裁定** | 未判两者是否表达同一事实，也未做行为错配实验。 |

## 4. 上一轮七条 finding

| Finding | 本轮状态 |
|---|---|
| **MAJOR-1** — resolver artifact / raw context 认证绑定不足 | **未裁定，未签关闭** |
| **MAJOR-2** — decision preimage / `accepted` 语义过弱 | **未裁定，未签关闭** |
| **MAJOR-3** — facade convention 未完整接线、锁可绕 | **未裁定，未签关闭** |
| **MINOR-1** — 阈值先 round 再比较 | **未裁定，未签关闭** |
| **MINOR-2** — 测试标题强于判别力 | **未裁定，未签关闭** |
| **MINOR-3** — 两套 legacy mirror coercion 并存 | **未裁定，未签关闭** |
| **NIT-1** — 旧文案 | **未裁定，未签关闭** |

“未裁定”既不表示代码仍错，也不表示已经关闭；它表示本席遵守停止纪律，没有拿任务书陈述或施工自测代替独立复审。

## 5. 新发现

### MAJOR-B1 — S2 decision 缺少已冻结的 mutual-nearest / ambiguity / source-allocation 判据

当前实现主动省略 §5.3 条件 2/3/4，却仍把结果建模为完整 `accepted` 并向外呈现 PASS。它既不符合 S2 的设计范围，也为 S3 留下把不完整判断直接升成阻断门的接口陷阱。

最低修复口径如 §1：要么补齐后按 S2 验收；要么把本轮降格为具名 partial telemetry，产物机器可读地披露覆盖缺口、不得 PASS，且 S3 对 incomplete coverage fail closed。

### REVIEW-PREMISE-1 — `position_evidence_pair_mismatch` 的分支分类错误

该码不是 mutual-nearest 专属码。当前代码已把 endpoint 超带与已解析 z-scope 错楼层映射到同一码；设计稿 §12.2 的 F-9 mirror negative 也明确要求超带返回该码。后续请求书不能再用“该码能触发”作为 mutual-nearest 已实现的证据，必须用有未引用、更近候选或同分候选的反事实夹具行为验证。

## 6. 未验证项

因停止纪律，除 §2 两条最小反证外，以下均未验证：

- BLOCKER-1 印章是否对所有 v3 完成路径无条件写入；缺失、`None`、未知版本、畸形、伪造及潜在第六类路径；
- 判卷拒判是否可能经 `boundary=None`、空集合或其他 consumer 退化成零缺陷/全对；
- 印章加入后对既有 artifact hash、sidecar、批准链与 replay 的影响；
- 摊 B 的 stepwise/integrated/第三入口真实接线、18 把 must-red、unavailable 第三态及全量行为；
- 摊 C 四态与摊 D 两种旧失效模式；
- 上一轮七条 finding 的任何 hostile / neuter 复审；
- F-24、F-25；
- 2539 passed / 10 xfailed 权威全量基线、compileall、`git diff --check` 的最终门。

本席没有执行任何 git 写操作，没有修改施工代码，也没有在工作树做 neuter。本裁决书是本席唯一的工作树写入。
