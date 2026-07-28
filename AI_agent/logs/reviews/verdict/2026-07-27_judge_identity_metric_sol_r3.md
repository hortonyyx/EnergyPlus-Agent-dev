# 对抗复审裁决 · 判卷器「数值身份 + 计分度量」返工 r3

- 日期：2026-07-27
- 被审对象：`b005004`（r3 WIP）+ `15eb89e`（r3 收尾），基于 `7c17998`
- 复审依据：r2 裁决 + r3 主控派工单；施工日志仅作线索
- 裁决：**REWORK**
- 本轮 findings：**2 BLOCKER / 1 MAJOR**
- 独立全仓：**1725 passed / 10 xfailed / 150 warnings**
- neuter 副本：`/tmp/judge-sol-r3.xaaMAA/repo`；收工 `git status --short` 为空

## 1. 总裁决

r3 有三块真实进展：

1. r2 的 `1e-9` 真缝 + 未配对 advisory 活体现在保持
   `score_product_identity_invalid / scoring.input_identity`；把仲裁优先级反转后，
   正式混合活体锁与 helper 仲裁锁均会红。
2. 未配对 advisory 已进入结构化、可计数的运行时日志；独立活体捕获到
   `near_orthogonal_advisory_unpaired`、`unpaired=True`、floor 与两端点 hex。
3. R2-M1 的大额过计锁已经走真 `match_plan_segments` 接线；M2 新增的
   `>1 candidate` 与 host-result 局部锁也都能在各自指定 neuter 下变红。

但不能批准。

第一，B1 仲裁器并没有实现派工单的绝对规则“任何 identity/topology 诊断都高于
capability”。它只把 `_REAL_BREAK_REASONS` 中两种 reason 当作 real break；
同样被收集成 `category="identity"` 的 `exterior_duplicate_owner` 会在存在
advisory 时被 capability 分支抢先掩盖。独立正式 `CorrectedGeometryV3`
活体五项生产校验全绿；只加一条未配对 advisory，就能把原本的 duplicate-owner
identity 红洗成 capability NA。这是 R2-B1 同型漏洞的第三张脸。

第二，主控点名的零容差风险成立。三个严格相邻、不重叠的 GT span 被一条产品墙
完整覆盖时，合法的三个 `(b-a)` 顺序累加可比同一并集的端点直差大 1 ulp。
当前 `_assert_obs_conservation` 因 `covered > obs_length` 精确硬拒而假红。
活体已走 GT/correction 两侧 extraction、正式 correction 五项全绿以及真实
`match_plan_segments`，不是直调 helper 幻想值。

第三，M2 的替代方案只证明了若干局部函数各自有效，没有把它们连接成派工单要求的
正式多-span `VerifiedWindowHostProof → score_typed_attempt → host claim`
闭环。只在 `score_typed_attempt` 内把传给 v3 scorer 的 resolver 换成恒
`"miss"`，N-1 e2e 与四条新增/既有局部锁合计 **5 passed**。原缺口仍可在全部
替代锁全绿时断线，故仍属打折。

## 2. Findings

### BLOCKER R3-B1 · `_REAL_BREAK_REASONS` 白名单仍允许 identity 被 advisory 洗成 NA

位置：

- [segment_score.py:321](../../../../src/agent/judge/segment_score.py#L321)：
  `exterior_duplicate_owner` 被收集为 `category="identity"`
- [segment_score.py:557](../../../../src/agent/judge/segment_score.py#L557)：
  `_REAL_BREAK_REASONS` 只含
  `exterior_interior_topology_conflict` 与 `invalid_interior_edge_pair`
- [segment_score.py:591](../../../../src/agent/judge/segment_score.py#L591)：
  `real_breaks` 又按上述 reason 白名单过滤
- [segment_score.py:598](../../../../src/agent/judge/segment_score.py#L598)：
  capability 在剩余 identity 的 catch-all 之前裁决

派工单的硬规则是“只要存在任何 identity 类诊断，整轮必须 identity 红”。
当前实际顺序却是：

```text
白名单内 identity
    > capability
    > 白名单外 identity（包括 exterior_duplicate_owner）
```

独立生产可达活体：

- footprint：`0.1 m × 0.1 m`
- cell A、B：都等于完整 footprint
- cell C：左半幅梯形，右边从 `x=.05` 斜到 `x=.05+5e-10`
- 上游 coverage 的 overlap 为 `0.015 m²`，低于现行
  `coverage_area_tol_m2=0.05`

实测：

```text
DUPLICATE_ONLY_CONTROL
production_all_green = True
judge = score_product_identity_invalid /
        scoring.input_identity /
        exterior_duplicate_owner

DUPLICATE_PLUS_UNPAIRED_ADVISORY
production_all_green = True
judge = score_unsupported_combination /
        scoring.capability /
        near_orthogonal_advisory_unpaired
```

因此这不是抽象的分类争议：同一个生产接受的 duplicate-owner 红，只要再加入
一条未配对 advisory，就变成整轮 NA。当前诊断 context 只有 reason/floor，
没有足够的 span/provenance 信息去区分“advisory 扰动的派生 duplicate”与
“独立、真实的 duplicate”；把整类 reason 放到 capability 后面并不满足死骨架。

可复现核心：

```python
W = H = .1
lean = 5e-10
fp = [[0., 0.], [W, 0.], [W, H], [0., H]]
cells = [
    CellV3(id="A", role="office", x=[0., W], y=[0., H], polygon=fp),
    CellV3(id="B", role="office", x=[0., W], y=[0., H], polygon=fp),
    CellV3(
        id="C", role="office", x=[0., .05 + lean], y=[0., H],
        polygon=[[0., 0.], [.05, 0.], [.05 + lean, H], [0., H]],
    ),
]
floor = FloorV3(
    id="F", name="F", z_floor=0., ceiling_height=3.,
    footprint=FootprintRing(vertices=fp), cells=cells,
)
geom = CorrectedGeometryV3(
    schema_version="3", footprint_x=[0., W], footprint_y=[0., H],
    floors=[floor],
)
assert all(f.ok for f in validate_corrected_geometry(geom))
with pytest.raises(ScoreContractError) as exc:
    extract_correction_plan_segments(geom)
assert exc.value.code == "score_unsupported_combination"  # 当前错误结果
```

验收必须增加“genuine `exterior_duplicate_owner` + unrelated unpaired advisory”
的生产五项全绿混合锁；不能只把 reason 塞进 `_REAL_BREAK_REASONS`，因为那会把
既有 R4 的合法 advisory 派生形态重新误判为 identity 红。实现需要保留足够的
诊断来源/几何关系，真正区分独立破裂与派生症状。

### BLOCKER R3-B2 · observation 守恒零容差对合法相邻分段产生 1-ulp 假红

位置：

- [segment_score.py:784](../../../../src/agent/judge/segment_score.py#L784)：
  target 账本使用 `_SUBINTERVAL_SUM_TOL=1e-9`
- [segment_score.py:804](../../../../src/agent/judge/segment_score.py#L804)：
  observation 账本使用零容差
- [segment_score.py:923](../../../../src/agent/judge/segment_score.py#L923)：
  `obs_covered[obs.key] += b - a`
- [segment_score.py:958](../../../../src/agent/judge/segment_score.py#L958)：
  多 target 累加值进入精确硬门

施工论证只证明了实数几何不等式：

```text
disjoint covered intervals 的并集长度 <= observation 投影 <= observation.length
```

它没有证明逐项 binary64 减法和顺序加法会与另一次端点减法得到同一 bit pattern。
独立活体用三个严格相邻的 GT span：

```text
x0 = 0.6615103026426206
x1 = 10.189556344280527
x2 = 16.84636437455466
x3 = 21.523013020575195
```

GT 上方一个长 zone、下方三个相邻 zone，因 T-junction 得到三段目标墙；
correction 上下各一个长 cell，得到一条完整产品墙。三段两两满足
`previous.p2 == next.p1`，零缝、零重叠。correction 生产五项全部 GREEN。

两侧 extraction 后实测：

```text
target lengths =
  9.528046041637907
  6.656808030274133
  4.676648646020535

covered sequential sum =
  20.861502717932577
  0x1.4dc8b712eef7fp+4

observation.length =
  20.861502717932574
  0x1.4dc8b712eef7ep+4

excess =
  3.552713678800501e-15
  0x1.0000000000000p-48

judge =
  score_denominator_nonconserving /
  scoring.denominator_totality /
  observation_cover_exceeds_length
```

这正是主控点名的假红：合法并集只因舍入多 1 ulp 被当成“一墙赚两墙”。
Sterbenz 不能证明跨多个 target 的顺序和与端点直差逐 bit 相等。

`_SUBINTERVAL_SUM_TOL` 与 observation 零容差的拆分不自洽。两层都在累加
由浮点端点相减得到的子区间；target 层承认累加漂移，observation 层却用实数
几何不可能性推出 binary64 精确不可能性。前者的 `1e-9` 不会保护后者。

同时，新增的大额真过计锁本身是真锁：

```text
禁用 _assert_obs_conservation：
test_b1_conservation_over_charge_raises_through_match_path  RED
test_b1_obs_conservation_equality_boundary_does_not_fire   RED
```

返工不能退回旧的固定 `+1e-9` 吞窗。验收需要同时钉住：

1. 重叠 target 导致的真实 `6 > 4` 仍响亮拒绝；
2. 上述三段合法铺满活体不拒绝；
3. 判别依据应是结构性区间重叠、精确浮点端点算术，或有证明的 ulp/error bound，
   不能再在任意固定容差和逐位零容差之间摆动；
4. 负 extra 的处理必须与同一判别一致，不能静默吞真实过计，也不能拒绝合法舍入。

### MAJOR R3-M1 · M2 替代锁各自为真，但正式多-span host-claim 链仍未被锁住

正面证据：

```text
_resolve_facade_product_to_gt:
  len(candidates) == 1 -> if candidates
  multi-candidate helper 1 RED；N-1 e2e 仍 GREEN

bind_correction_window_segment:
  len(candidates) == 1 -> if candidates
  temporary-binding helper 1 RED

resolve_correction_window_host 末端恒 "miss":
  v3 host-result lock  RED
  plan host-result lock RED
  N-1 e2e             GREEN
```

所以施工方声明的两条指定 neuter 确实各有锁会红，不能说这些新增测试是全假。
但它们没有覆盖原 finding 点名的组合出口：

1. multi-candidate 两锁都由 helper/SimpleNamespace 构造，不经过
   `VerifiedWindowHostProof` 或 `score_typed_attempt`；
2. v3 host-result 锁手工构造
   `mapping = {product_segment.id: target.boundary_segment_id}`，绕过
   `_resolve_facade_product_to_gt` 与 `score_service:230`；
3. N-1 仍是固定 4×4 盒上的唯一 South span，且 manifest 使 host claim
   `not_applicable`，仍只断言 `extras == ()`。

决定性集成 neuter 只改生产接线：

```diff
 rows = score_opening_claims_v3(
     ...,
-    host_resolver=host_resolver,
+    host_resolver=(lambda target, observation: "miss"),
 )
```

在 `/tmp` 副本同时运行：

```text
test_n1_facade_update_feeds_window_host_resolution_e2e
test_b_facade_multi_candidate_gt_span_is_not_mapped
test_b_facade_multi_candidate_window_temporary_binding_fails_closed
test_b4b_r2m2_v3_host_claim_complete_pinned_through_score_opening_claims_v3
test_b4b_r1_real_correction_host_resolver_scores_and_rejects_zero_multi_adjacency

=> 5 passed
```

也就是说，真正的 `score_typed_attempt → host_resolver → v3 host claim` 接线坏掉时，
替代锁可以全部绿。固定 4×4 bundle 是现有 fixture 的限制，不是降低派工单
出口的依据；本项已是同一出口第三次打折，仍按 MAJOR 保留。

验收仍需正式 `VerifiedWindowHostProof` 多-span fixture，走
`score_typed_attempt → assign_openings → build_correction_host_resolver →
score_opening_claims_v3`，并逐字断言 host claim 结果；上述集成 neuter必须红。

## 3. r2 四条 findings 闭环表

| r2 finding | r3 判定 | 独立证据 |
|---|---|---|
| R2-B1 advisory 掩盖 identity | **PARTIAL / 未闭环** | 指定 1e-9 四锁通过，优先级 neuter 真红，日志已补；但 genuine `exterior_duplicate_owner` 仍可被 advisory 洗成 NA，见 R3-B1 |
| R2-B2 来源身份合同 | **移出本批，且未半做** | `_cluster_axis` 仍只收 `Iterable[float]`；零来源 key/版本门；合同码仍只在码表一处；旧非相邻重复/同 owner 活体仍静默接受 |
| R2-M1 守恒容差窗 | **REOPEN / 未闭环** | 真过计锁已走接线；但零容差制造合法 1-ulp 假红，见 R3-B2 |
| R2-M2 多-span host claim | **PARTIAL / 未闭环** | 两类局部锁均真；正式组合接线 neuter 仍 5 绿，见 R3-M1 |

### R2-B2 未碰确认

审查 `b005004` 与 `15eb89e` 后，没有任何来源身份 tuple、vertex index、
endpoint side 或身份合同版本进入聚类器。`_pair_general_edges` 因 B1 被改成
“收集诊断而非立即 raise”，但 owner/source 语义未扩张，没有出现危险的半成品
来源传递。

当前仍是：

```text
$ rg -n 'score_identity_contract_mismatch' src tests
src/agent/judge/score_schema.py:60: ...
```

旧活体复跑仍输出：

```text
NONADJ_DUP_ACCEPTED
[((0.0, 2.0), (2.0, 2.0), zone_ids=("Z", "Z"), exterior=False)]
```

符合主控“本批不要碰”的范围裁定；严重性不在本轮重复计入 findings。

## 4. 四验收锁、排序与原测试复核

### R2-B1 四锁

| 锁 | 独立结果 |
|---|---|
| 只有 `1e-9` 真缝 | identity 红；code/gate/reason 逐字正确 |
| 真缝 + 未配对 advisory | 仍 identity 红；生产五项全绿 |
| 只有未配对 advisory、无真缝 | 既有双-cell 生产五项全绿活体为 capability NA |
| capability-first neuter | 正式混合锁 + helper 仲裁锁 **2 failed** |

新增的单-cell“advisory only”锁本身没有断言生产 coverage；但既有
`test_r4_live_counterexample_is_unsupported_not_identity_invalid` 用两 cell、
五项生产全绿的 mismatch advisory 覆盖了同一合法出口，因此这里不另立 finding。

### 未配对 advisory 运行时产物

双-cell mismatch 活体捕获两条有向未配对记录，每条均含：

```text
event = near_orthogonal_advisory_unpaired
unpaired = True
floor_id = F
p1_hex / p2_hex
```

已可计数；本项闭环。

### `_REAL_BREAK_REASONS` 排序反转

AST 独立统计：

- `7c17998` 上实际有 **9** 个包含 `invalid_interior_edge_pair` 断言的测试；
- 当前 head 为 **12** 个，新增 3 个来自 r3 B1 锁。

在 `/tmp` 把排序退回旧序，并运行原 9 个测试：

```text
1 failed / 8 passed
```

唯一失败正是
`test_b4b_r1_gt_interior_pairing_and_invariant_raises`，其余 gap/overlap/dangling
夹具零误伤。因此两种 real-break reason 内部的排序修复成立；R3-B1 指控的是
这个二元素白名单没有覆盖全部 identity 类，不是否定该二者的相对顺序。

### 原失败测试未被改动

`test_b4b_r1_gt_interior_pairing_and_invariant_raises` 在 `7c17998` 与
`15eb89e` 的函数体：

```text
bytes = 1743 / 1743
sha256 =
c82b85c49efc8fc0dfef9ccdbe00c50f326afb59aff3f78e5f22e726a9b022b5
```

逐字相同。`test_c2_b4b_phase_b.py` 的 diff 只来自 import 与新增 host-result 锁。

## 5. neuter 与全仓

全部 neuter 仅在 `/tmp/judge-sol-r3.xaaMAA/repo`：

| neuter | 结果 |
|---|---:|
| `_REAL_BREAK_REASONS` 退回旧序，跑原 9 锁 | 1 failed / 8 passed |
| capability 提到 real break 之前 | R2-B1 正式混合锁 + helper 锁 2 failed |
| 禁用 observation 守恒门 | match-path + boundary 2 failed |
| 禁用 per-target 守恒门 | 1 failed |
| facade unique candidate 弱化 | helper 1 failed；N-1 1 passed |
| temporary bind unique candidate 弱化 | helper 1 failed |
| low-level host resolver 恒 miss | v3 + plan 2 failed；N-1 1 passed |
| 仅切断 `score_typed_attempt` 的 host-resolver 接线 | M2 相关 5 passed |

副本全部反向 patch 后：

```text
$ git status --short
# empty
$ git diff --exit-code
# exit 0
```

独立全仓：

```text
1725 passed, 10 xfailed, 150 warnings in 264.18s (0:04:24)
```

全仓绿证明常见夹具未回归，不能覆盖两个新活体和 M2 集成断线。审查前主工作树
为空；被审两笔提交自身未改 `gt/` 或 `AI_agent/CLAUDE.md`。本审只新增本裁决书。

## 6. 返工出口

1. **B1 仲裁**：不得以 reason 白名单把任一 genuine identity 诊断放到
   capability 之后；补正式五绿的 duplicate + advisory 混合锁，并保住既有
   合法 advisory-only NA 锁。
2. **M1 数值守恒**：同时钉真实重叠过计红与三相邻 span 的 1-ulp 合法绿；
   使用结构性或有误差证明的判别，不得再在固定 `1e-9` 与零容差之间换位。
3. **M2 完整链**：交付正式多-span `VerifiedWindowHostProof` e2e，逐字断言
   v3 host claim；`score_typed_attempt` 内恒 miss 接线 neuter 必须红。
4. R2-B2 继续按主控裁定保持独立立项，本批不得顺手半做。
