# 对抗复审裁决 · 判卷器「数值身份 + 计分度量」返工 r2

- 日期：2026-07-27
- 被审对象：`cc07997`、`32c173a`、`7c17998`（基于 `29a1ce0`）
- 裁决：**REWORK**
- 本轮 findings：**2 BLOCKER / 2 MAJOR**
- 独立全仓：**1715 passed / 10 xfailed / 150 warnings**
- neuter 副本：`/tmp/judge-sol-r2.gjx9Jr/repo`；收工 `git status --short` 为空

## 1. 总裁决

返工有真实进展，不能把本轮概括成“锁全是假”：

1. 上轮 B-1 的 4 m 活体反例现在会响亮拒绝
   `score_identity_support_ambiguous`，不再出现 `8/8 pass`。摘掉多支撑线拒绝后，
   第二道防线仍只给 `4 m passing + 4 m miss`，没有复发 8 m 记功。
2. A8 联合建池锁、overlong `0.2 m extra` 锁、GT 精确 side-code 锁均经本审
   `/tmp` 指定 neuter 证实会红。
3. W5 两端确已接线；独立 neuter 得到生产侧 `8 failed / 1 passed`，判卷相关
   子集 `25 failed / 18 passed`。严格拆开，其中 1 红是共享 helper 直调单测，
   其余 24 红才经过 segment extraction；“25 判卷路径红”的简报口径略宽，
   但两端接线本身成立。
4. `score_service.py:230` 的 facade map 断线后，新 N-1 测试确实 1 红。
5. 全仓结果与施工简报逐字对齐。

但仍不能批准。r2 为修 R-4 把 advisory 配对提到正交拓扑门之前，制造了主控
点名的经典换位：一个本应 A2/identity-red 的真实拓扑缝，只要同时沾上一条
未配对 advisory 边，就被提前洗成 capability NA，整轮不出分。这个混合缺陷
在生产校验五项全绿的正式 `CorrectedGeometryV3` 上可达，并非 helper 幻想输入。

此外，上轮 BLOCKER B-2 的来源身份合同并未按死骨架落地；代码仍把全层坐标
展平成 `Iterable[float]`，来源索引在进入 `_cluster_axis` 前已经丢失。非相邻
重复顶点、自触环和同 owner 反向配对可被静默接受，合同版本不匹配码只有登记、
没有任何运行时发射路径。

## 2. Findings

### BLOCKER R2-B1 · advisory 提前执行会把既有真红洗成 capability NA

位置：

- [segment_score.py:375](../../../../src/agent/judge/segment_score.py#L375)
  `_pair_advisory_edges`
- [segment_score.py:402](../../../../src/agent/judge/segment_score.py#L402)
  未配对即抛 `score_unsupported_combination`
- [segment_score.py:452](../../../../src/agent/judge/segment_score.py#L452)
  advisory-before-tile 顺序

独立活体由三个 cell 构成：

- footprint：`[0,4] × [0,10]`
- A：右边为 near-vertical advisory，底 `x=2.0`、顶 `x=2.0+5e-10`
- B：右半区下段，`y=[0,5]`
- C：右半区上段，`y=[5+1e-9,10]`

其中 B/C 之间的 `1e-9` 缝就是 A2 已钉的“必须 identity red”形态；面积只有
约 `2e-9 m²`，低于上游 coverage 面积容差，且 A 的边仍被生产共享判据认作
合法。因此 `validate_corrected_geometry` 五项全部 GREEN。

实测：

```text
TRUE_GAP_ONLY
production_all_green = True
judge = score_product_identity_invalid /
        scoring.input_identity /
        invalid_interior_edge_pair

TRUE_GAP_PLUS_ADVISORY
production_all_green = True
judge = score_unsupported_combination /
        scoring.capability /
        near_orthogonal_advisory_unpaired
```

只在 `/tmp` 把两行顺序换成 tile-before-advisory，同一个
`TRUE_GAP_PLUS_ADVISORY` 立即恢复：

```text
production_all_green = True
judge = score_product_identity_invalid /
        scoring.input_identity /
        exterior_duplicate_owner
```

所以变化不是“同一错误换了文案”，而是门从 `scoring.input_identity` 被降级成
`scoring.capability`：本该判红的产品可以通过附加一条未配对 advisory 边取得
整轮 NA。这就是主控点名的假绿/免判换位。

还有一处同源缺口：`_log_advisory_hit` 在配对成功之后才调用。真正触发
unsupported 的未配对 advisory 不进入这条结构化日志，因此“两次真实 run
零 advisory hit 后翻 blocking”的计数也看不见最需要被计数的命中。

可复现探针（核心构造）：

```python
cells = [
    CellV3(id="A", role="office", x=[0., 2. + 5e-10], y=[0., 10.],
           polygon=[[0., 0.], [2., 0.], [2. + 5e-10, 10.], [0., 10.]]),
    CellV3(id="B", role="office", x=[2., 4.], y=[0., 5.],
           polygon=[[2., 0.], [4., 0.], [4., 5.], [2., 5.]]),
    CellV3(id="C", role="office", x=[2., 4.], y=[5. + 1e-9, 10.],
           polygon=[[2., 5. + 1e-9], [4., 5. + 1e-9], [4., 10.], [2., 10.]]),
]
floor = FloorV3(
    id="F", name="F", z_floor=0., ceiling_height=3.,
    footprint=FootprintRing(vertices=[[0., 0.], [4., 0.], [4., 10.], [0., 10.]]),
    cells=cells,
)
geom = CorrectedGeometryV3(
    schema_version="3", footprint_x=[0., 4.], footprint_y=[0., 10.],
    floors=[floor],
)
assert all(f.ok for f in validate_corrected_geometry(geom))
with pytest.raises(ScoreContractError) as exc:
    extract_correction_plan_segments(geom)
assert exc.value.code == "score_unsupported_combination"  # 当前错误结果
```

验收锁必须是混合缺陷优先级锁：保留同一份 `1e-9` 真缝，再分别加/不加未配对
advisory；两者都不得被降级成 capability NA。

### BLOCKER R2-B2 · B-2 来源身份合同仍未实现，合同④与版本门有活体漏口

位置：

- [segment_score.py:78](../../../../src/agent/judge/segment_score.py#L78)
  `_cluster_axis(raw_values: Iterable[float], ...)`
- [segment_score.py:133](../../../../src/agent/judge/segment_score.py#L133)
  `_build_floor_identity` 只保留点值
- [segment_score.py:187](../../../../src/agent/judge/segment_score.py#L187)
  `_points` 只查相邻坍缩
- [segment_score.py:344](../../../../src/agent/judge/segment_score.py#L344)
  reverse owner 配对未拒绝同一 owner
- [score_schema.py:60](../../../../src/agent/judge/score_schema.py#L60)
  `score_identity_contract_mismatch` 仅登记

返工单 §2 的死骨架是：

```text
polygon 顶点来源 = (floor_id, zone_id, vertex_index)
boundary 端点来源 = (floor_id, segment_id, endpoint_side)
reading 端点同理
```

当前没有任何上述来源键进入 `_cluster_axis`；每个 floor 的点被直接展开成
x/y 浮点序列。代码因此仍无法执行“同来源全部出现值直径”合同，也没有一个
可传入或可验证的身份合同版本。

更直接的合同④活体：

```python
ring = [
    (0., 0.), (4., 0.), (4., 4.), (0., 4.),
    (0., 2.), (2., 2.), (0., 2.),
]
floor = SimpleNamespace(
    id="F",
    footprint=SimpleNamespace(
        exterior=SimpleNamespace(vertices=[(0., 0.), (4., 0.), (4., 4.), (0., 4.)]),
    ),
    boundary_segments=(),
    zones=[SimpleNamespace(
        id="Z", polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=ring)),
    )],
)
segments = extract_gt_plan_segments(SimpleNamespace(floors=[floor]))
```

`(0,2)` 是非相邻重复顶点；`(0,2)→(2,2)→(0,2)` 同时形成自触/回折边，
两条反向边由同一个 zone `Z` 拥有。当前没有拒绝，而是产出：

```text
NONADJ_DUP_ACCEPTED
[((0.0, 2.0), (2.0, 2.0), zone_ids=("Z", "Z"), exterior=False)]
```

这一次同时证明三个点：

1. 非相邻重复顶点未检查；
2. 归并/环处理后的自触未检查；
3. owner 重数合同允许同一个 owner 与自己“配成内墙”。

合同版本同样未闭环：

```text
$ rg -n 'score_identity_contract_mismatch' src tests
src/agent/judge/score_schema.py:60: ... "score_identity_contract_mismatch" ...
```

只有码表一处，没有 raise、输入版本或负锁。

R-5 上下文也不完整。reading `(0,0)→(5e-13,0)` 现在会正确拒绝，但 context
只有 `v1_hex/v2_hex`，缺返工单点名的 `diameter/diameter_hex`；boundary
collapse 同型，boundary duplicate-after-merge 连原始两对端点也没有。

直径阈降到 `1e-12`、相邻 polygon collapse、boundary/reading 零长拒绝都是真
进展，但不能代替上面未实现的来源合同、非相邻/自交/owner 门和版本门。

### MAJOR R2-M1 · B-1 活体已修，但“负 extra 必抛”的守恒硬门仍留容差窗

位置：

- [segment_score.py:641](../../../../src/agent/judge/segment_score.py#L641)
  `_assert_obs_conservation`
- [segment_score.py:760](../../../../src/agent/judge/segment_score.py#L760)
  extra 计算

大额重复记功已经堵住；sol 的 4 m 活体当前响亮拒绝。指定 neuter 也是真锁：

```text
摘掉 >=2 support-line raise：
1 failed / 2 passed
活体输出（不再抛错时）= passing 4.0 / miss 4.0，非 8.0

摘掉 _assert_obs_conservation raise：
1 failed / 2 passed
```

但返工单还明确要求“负 extra 必须抛错，不许静默归零”。当前先允许
`covered <= obs_length + 1e-9`，随后直接：

```python
extra = obs.length - covered
if extra > claim_complete_epsilon_m:
    ...
```

于是容差窗内的负数仍按 r0 的同一种形状被吞掉。完整 match 活体：

```python
targets = (
    PlanSegment("t1", "F", (0., 0.), (2., 0.), exterior=False),
    PlanSegment("t2", "F", (2. - 5e-10, 0.), (4., 0.), exterior=False),
)
obs = (PlanSegment("o", "F", (0., 0.), (4., 0.), exterior=False),)
rows, _ = match_plan_segments(targets=targets, observations=obs, config=cfg)
```

实测：

```text
NO_RAISE
obs_length = 4.0
covered    = 4.0000000005
extra_rows = 0
delta      = 5.000000413701855e-10
```

这不是再现 8 m 大洞，但确实没有交付死骨架所要求的硬不变式。现有锁直接调用
helper，只钉 `8.0 > 4.0 + tol`，没有走 `match_plan_segments` 钉负 extra，
也没有显式的 per-target `passing + failing == target.length` raise 锁。

### MAJOR R2-M2 · N-1 的 `:230` 接线锁为真，但“多段 facade → host claim”仍是假完整链

位置：

- [score_service.py:104](../../../../src/agent/judge/score_service.py#L104)
  `_resolve_facade_product_to_gt`
- [score_service.py:230](../../../../src/agent/judge/score_service.py#L230)
  facade map 接线
- [test_c2_b5_parent_and_verts.py:1194](../../../../tests/test_c2_b5_parent_and_verts.py#L1194)
  `_n1_gt`
- [test_c2_b5_parent_and_verts.py:1235](../../../../tests/test_c2_b5_parent_and_verts.py#L1235)
  新 N-1

正面证据先说清：外部把 `product_to_gt.update(...)` 改成只调 helper、不 update，
新锁会在 `assign_openings` 处以 `score_product_segment_unresolved` 变红：

```text
test_n1_facade_update_feeds_window_host_resolution_e2e
1 failed
```

因此它是 `:230 → assign_openings` 的真接线锁。

但它没有交付返工单反复点名的另外两半：

1. `_n1_gt` 明写把 bundle 的 4 个 facade segment 包回 GT；四个分别是
   North/South/East/West。窗口只在唯一 South segment 上，仍是单段包含，
   不是“同一 facade 多 GT span / 产品 span 跨段”的新夹具。
2. 测试只断言 `result.payload.extras == ()`，没有断言 host claim row 为
   `complete`，所以只能证明 opening 被 assignment 接走，不能证明
   `build_correction_host_resolver / claim` 的结果。

两个独立 neuter：

```text
# A：让 host resolver 对所有窗口恒回 "miss"
test_n1_facade_update_feeds_window_host_resolution_e2e
1 passed

# B：把唯一候选门 len(candidates) == 1 弱化为 if candidates
tests/test_judge_identity_metric.py
+ tests/test_c2_b5_parent_and_verts.py
= 82 passed
```

B 的行为差异恰好只在 `len(candidates) > 1` 时出现；相关测试全绿说明没有任何
夹具真正走到多 candidate 分支。旧所谓 straddle 夹具用相邻 `[0,2]/[2,4]`
对产品 `[0,4]`，在“完整包含”候选定义下其实是 **0 candidate**，不是
`>1 candidate`。

关于施工方主动披露的 renderer stub：**stub 本身可以接受**。host resolution
与 claim scoring 在 [score_service.py:278](../../../../src/agent/judge/score_service.py#L278)
已经执行，payload 在 :308 构造，renderer 到 :320 才调用；画图不会反向参与
`:230`、assignment 或 host 判定。它只意味着这条测试不钉最终 PNG。锁效力
真正被削弱的原因是单段夹具和 `extras == ()` 弱断言，不是 renderer stub。

## 3. 上轮 7 findings 闭环表

| 上轮 finding | 本轮结论 | 独立证据 |
|---|---|---|
| BLOCKER B-1 一墙赚两墙 | **PARTIAL** | 点名 4 m 活体已响亮拒绝；摘拒绝后也只有 4 pass + 4 miss；但负 extra 的 `1e-9` 容差窗仍静默吞，见 R2-M1 |
| BLOCKER B-2 C-1″ 合同 | **FAIL** | source identity 未进入聚类；非相邻重复/自触/同 owner 内墙活体静默接受；contract mismatch 无发射路径 |
| MAJOR M-1 A8 false-lock | **PASS** | 联合建池 neuter 后 A8 红，bytes 在 index 6 为 `fb` vs `f8` |
| MAJOR M-2 overlong false-lock | **PASS** | 覆盖过 target 即丢 overshoot 后，精确 `0.2 extra` 锁红；对照 W4 锁仍绿 |
| MAJOR M-3 W5 未接线 | **PASS（接线）/ 新 BLOCKER** | 两端 helper neuter 均红；但 advisory-before-tile 新造混合缺陷洗成 NA，见 R2-B1 |
| MAJOR M-4 精确码/自查不实 | **PASS** | GT side code 换成 product 后新 M4 锁红；自查表本轮数字基本可复算 |
| MINOR N-1 完整窗链锁 | **PARTIAL** | `:230` 断线锁已真；多段 candidate 与 host claim 仍未钉，见 R2-M2 |

## 4. `/tmp` neuter 独立复算

| neuter | 独立结果 | 裁断 |
|---|---:|---|
| B-1 conservation raise → false | `1 failed / 2 passed` | 真锁，但只钉大额 helper 输入 |
| B-1 `len(eligible_lines)>=2` → false | `1 failed / 2 passed`；活体 `4 pass + 4 miss` | 真锁，且第二防线有效 |
| A8 注入 GT+产品联合建池 | `1 failed`，denominator bytes 不同 | 真锁 |
| 覆盖过任一 target 即丢全部 overshoot | `1 failed / 1 passed` | 真锁 |
| GT identity code 三处换成 product code | `1 failed / 1 passed` | 真锁 |
| `edge_is_axis_aligned` 首行 raise | `8 failed / 1 passed` | 生产真接线 |
| `classify_edge_orthogonality` 首行 raise | `25 failed / 18 passed` | 24 条 extraction + 1 条 helper 单测 |
| `score_service:230` 只调用、不 update | N-1 `1 failed` | `:230→assignment` 真接线 |
| host resolver 恒回 `"miss"` | N-1 `1 passed` | host claim 假锁 |
| `len(candidates)==1` → `if candidates` | 两个相关文件 `82 passed` | 多 candidate 分支未钉 |

所有变异均只在 `/tmp/judge-sol-r2.gjx9Jr/repo`；每轮用反向
`apply_patch` 还原，收工 `git diff --check` 与 `git status --short` 均为空。

## 5. 全仓、受保护输入与工作树纪律

定向：

```text
pytest -q \
  tests/test_judge_identity_metric.py \
  tests/test_c2_b4b_phase_b.py \
  tests/test_c2_b5_parent_and_verts.py

109 passed in 9.57s
```

全仓：

```text
pytest -n auto
1715 passed, 10 xfailed, 150 warnings in 256.86s (0:04:16)
```

GT 树对象：

```text
29a1ce0:case_tests/test_baseline/gt = 09fd16c92482dae405c4d0cc4e69588548c33781
7c17998:case_tests/test_baseline/gt = 09fd16c92482dae405c4d0cc4e69588548c33781
worktree SHA-256 manifest digest = d0e8b0140b2a6cf3585c6499eba84a722e15a8f523e4efcad2f4a1fa8e158ea5
```

本审未改 `case_tests/test_baseline/gt/**`、`AI_agent/CLAUDE.md` 或生产/测试代码；
主工作树审前为空，落卷后只新增本裁决书。

## 6. REWORK 必做出口

1. 修混合错误优先级：同一 floor 同时有真 topology/identity break 与 advisory
   不可测形态时，advisory 不得抢先把整轮降成 capability NA。补本裁决书
   `1e-9 gap + 5e-10 lean` 活体锁；同时让未配对 advisory 进入可计数运行时产物。
2. 按 r1 §2 真正传递和验证来源身份；补非相邻重复顶点、归并后自交/自触、
   同 owner 反向配对、boundary/reading 完整 context 与合同版本不匹配的运行时门。
   `score_identity_contract_mismatch` 不能继续只存在于码表。
3. B-1 增加完整 match 级守恒锁：任何 `covered > observation.length` 和任何负
   extra 都必须响亮拒绝；补 per-target `passing + failing == target.length`
   代码硬门，不以 helper 直调代替接线锁。
4. N-1 新造真正同 facade 多 span 的正式 `VerifiedWindowHostProof` 窗夹具，
   经过 `score_typed_attempt → assign_openings → build_correction_host_resolver
   → score_opening_claims_v3`，逐字断言 host claim 为 `complete` 或点名的
   fail-closed 结果。必须使“唯一候选门弱化”和“host resolver 恒 miss”各自变红。

结论：**REWORK**。
