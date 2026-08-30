# ②-1d 返工执行档：boundary 对账门双向全集闭合

- 日期：2026-08-30
- 施工家族：GPT
- 返工对象：`8442442`
- 实际开工 HEAD：`684859caaf502d2982fe617a14b580b4cf21c239`
- 结论：**B1 已修；E3 / E4 / E2c 三条必须红均红，正常 sm25 仍 100/100 绿**

## 一、环境重核与开工漂移

按返工单要求依次完整读完返工单、GLM 裁决书、原派工单后再量环境。分支仍是
`08.23_AsDrawnReading`，工作树开工时干净；实际 HEAD 不是发单正文写的 `6e1b9f8`，
而是后续 rebaseline commit `684859c`。核 `git show 684859c`：它只把返工单基线文字
从 `90e0429` 更正为 `6e1b9f8`；再核：

```text
git diff --name-status 8442442..684859c -- src tests scripts case_tests/test_baseline/gt
<空>
```

因此代码面仍与权威 3385 绿的 `8442442` 相同，不触发停报。没有建 worktree、没有切
分支、没有执行 `pip install -e .`，也没有读取被隔离的 o22m1 半成品目录。

## 二、修法：全集不是“只有 paired rows”

`reconcile_boundary_basis` 现在有三层账：

1. **stored ring 完整性**：从 facts 几何独立重导 logical ring 身份；仍能导出的 ring
   若从 stored `boundary_edges` 消失，报
   `facts_boundary_ring_missing:<view>:<cavity>:converter=<zone>`。
2. **facts → converter**：保留原逐 ring 的全方向/全旋转几何解、独立血缘解、残差
   上限与逐边 basis 对账；不改任一列。
3. **converter → facts**：每个 converter zone 必须落到 facts cavity。能形成 logical
   ring 的 cavity 必须有 stored ring；不能形成 logical ring 的既有 NA cavity 只能作为
   具名 `exclusion`，不得冒充 paired edge；落不到任何 cavity 的 zone 报
   `converter_zone_unclaimed_by_facts`。

另加逐 view 非空断言 `facts_boundary_edges_empty:<view>`。正常 sm25 的全集账为：

```text
passed=True
paired_edges=100
converter zones accounted=29/29
mismatches=[]
structural_failures=[]
exclusions=plan-F1/F1-z0,F1-z4,F1-z5 + plan-F2/F2-z0
```

即 25 个 logical ring 的 100 条边逐边对账，4 个既有 NA cavity 逐项声明；没有把 4 个
exclusion 伪报成“配对成功”。

## 三、三条必须红与失败半径

### 3.1 机械读数

| 变异 | 修前 | 修后 | 修后具体红项 |
|---|---|---|---|
| 正常 sm25 | 100/100 绿 | **100/100 绿**，zones 29/29 | 无 |
| E3：删 F1-z3 整 ring | `passed=True, paired=96` | **红，paired=96，zones 29/29** | 仅 `facts_boundary_ring_missing:plan-F1:cavity:19ce2896d9112b53:converter=F1-z3` |
| E4：两 view 的 `boundary_edges=[]` | `passed=True, paired=0` | **红，paired=0，zones 29/29** | 2 条 `facts_boundary_edges_empty` + 25 条逐 cavity `facts_boundary_ring_missing` |
| E2c：复制 F1-z3 并平移 50 m | `passed=True, paired=100` | **红，paired=100，zones 29/30** | `converter_zone_facts_cavity_pairing_not_unique:plan-F1:F1-phantom-50m:[]`；`converter_zone_unclaimed_by_facts:F1:F1-phantom-50m` |

E4 的 25 条缺失不是整份 NA：F1 精确点名 z1/z2/z3/z6–z13 共 11 个 logical ring，
F2 精确点名 z1–z14 共 14 个 logical ring；正常已有的 F1-z0/z4/z5、F2-z0 仍是 4 条
exclusion，不被错误升级成 paired，也不被此次变异伪装成新失败。

`BoundaryBasisAuditV1.assert_consistent()` 对上述每个红 audit 均抛
`BoundaryBasisMismatchError`；三种变异的 `mismatches=[]`，说明红的是集合/结构账，
没有把独立两列的值改成互相迎合。

### 3.2 验收 3：真实 sm25 的 2 m 顶点毛刺

用真实 `sm25-L_anchor` facts，在 `plan-F1` exterior footprint 中把既有顶点
`[50000, 40000]` 改为 `[50000, 60000]`。facts 单位是 0.1 mm，差值 20,000 units
= 2 m；随后走生产 `derive_boundary_edges`，不是手工清空列表。

修前门实跑原文：

```text
real_vertex_2m True 56 [0, 56] []
```

即 F1 的 44 条全部静默消失、F2 保留 56 条，而门仍绿。修后同形输入：

```text
passed=False, paired=56, converter zones accounted=15/29
facts_boundary_edges_empty:plan-F1
facts_boundary_footprint_unusable:plan-F1:
  answer_compiler_footprint_is_not_a_valid_polygon:plan-F1
converter_zone_facts_cavity_pairing_not_unique:plan-F1:F1-z0..F1-z13:[]
converter_zone_unclaimed_by_facts:F1:F1-z0..F1-z13
```

所有红项都限定在被毛刺破坏的 `plan-F1`；测试另断言结构失败中没有 `plan-F2`。
永久锁：
`test_rework_real_sm25_two_metre_footprint_vertex_spike_reddens_the_lost_view`。

### 3.3 验收 3b：multi-exterior 零真实存货

已在层契约 §5.1 明写：现有全部可走语料中 `exterior ring != 1` 为**零真实存货**；
sm24、sm25 signed/as-received 都是一个 exterior ring，sm21 无 request。永久锁
`test_rework_e4_multi_exterior_branch_has_an_explicit_synthetic_lock` 是向 sm25 view
人工追加第二个 exterior ring 的**合成夹具**，测试名、docstring 与层契约均明确写
“synthetic”，没有把它冒充真实覆盖。该锁得到：

```text
paired=56
facts_boundary_edges_empty:plan-F1
facts_boundary_footprint_unusable:plan-F1:
  answer_compiler_requires_one_exterior_ring:plan-F1:2
```

## 四、N1–N5 逐项处置

| 项 | 处置 |
|---|---|
| N1 | **改了契约**：sm25 落库存货明确为 exterior 32 / interzone 68 / unclaimed_void 0 / unknown 0；后两档只有谓词级合成供货，禁止再说“真实 facts 覆盖四档”。 |
| N2 | **不改数值，明确待签**：`5_000` units 仍只表示跨表示配对残差护栏，混合了内皮/墙中线的系统基准差与错配防护；sm25 0.247–0.339 m、offset ≥0.36 m 可能假红均落层契约。下一方言前必须 per-case 参数化或用户签定；本单没有发明新数。 |
| N3 | **不扩锁，登记边界**：F-150 当前是 6 字段 + `diagnostics[].context` 的列举式锁；现有消费面安全，未来新增消费点不会自动入锁，届时必须同步扩。 |
| N4 | **已接 staging**：官方 `build_sm25_facts_staging.py` 在写三件套前加载 converter report、运行 `reconcile_boundary_basis` 并 `assert_consistent()`；实跑输出 `boundary_basis paired=100 zones=29/29`。不碰 `promote_gt_v3`。 |
| N5 | **纯门侧兜住，未增静默出口**：既有 exterior≠1 / polygon invalid / `min_room_area_m2=None` 直通均不改生产列；非空 + 双向全集门把其后果具名变红。 |

## 五、验收 5：两列判据逐字节不变

执行：

```text
git diff 8442442 -- \
  src/agent/judge/tarch_normalize.py \
  src/agent/judge/as_measured.py
<空>
```

因此转换器 `basis` 判据所在的整个 `tarch_normalize.py` 与 facts
`boundary_condition` 谓词所在的整个 `as_measured.py` 相对送审对象均零字节改动；
本单只改对账门、测试、staging 接线与契约。

## 六、测试、答案根与环境哨兵

影响分析器对一等 Python 改动给出：

```text
SCOPE: SUBSET
tests/test_answer_compiler_closure.py
tests/test_answer_compiler_exit_gate.py
tests/test_answer_compiler_profiles.py
tests/test_boundary_condition_facts.py
```

运行命令与结果：

```text
python -m pytest -p no:cacheprovider -q \
  tests/test_answer_compiler_closure.py \
  tests/test_answer_compiler_exit_gate.py \
  tests/test_answer_compiler_profiles.py \
  tests/test_boundary_condition_facts.py -n auto

29 passed in 11.64s
```

另实跑 staging producer，读数 `paired=100 zones=29/29`，重生成后三件套零字节 diff；
受影响 Python 文件 `compileall` 成功，`git diff --check` 为空。权威全量按分工留给主控。

前后哨兵原文：

```text
HEAD before = 684859caaf502d2982fe617a14b580b4cf21c239
HEAD after  = 684859caaf502d2982fe617a14b580b4cf21c239

.pth path   = /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
.pth before = 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
.pth after  = 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
.pth content before/after = /workspaces/EnergyPlus-Agent-dev

git diff --quiet -- case_tests/test_baseline/gt
exit 0
```

答案根 `case_tests/test_baseline/gt/` 零字节改动。

## 七、改动路径

```text
AI_agent/architecture/as_drawn_layer_contract.md
AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/build_sm25_facts_staging.py
AI_agent/logs/reviews/execution/2026-08-30_o21d_rework_execution.md
src/agent/judge/answer_compiler.py
tests/test_boundary_condition_facts.py
```

## 八、最薄弱处与复核请求

我认为最薄弱的一处是**4 个正常 exclusion 的边界**：门已把它们显式列出而不再静默，
但 logical-ring 完整性复算仍调用同一生产 `derive_boundary_edges`。如果未来出现“原始 cavity
仍有效、producer 与复算同因漏掉 logical ring”的共同模式，它可能被归入 exclusion；当前
真实 2 m 毛刺因 footprint unusable 会响亮红，但这不等于所有同因缺陷都已穷尽。

希望复核方重点攻击：把幻觉 zone 放进 F1-z4/z5 共用的非 logical cavity、构造有效 footprint
且让 owner/junction 判定整 ring 同因消失、以及同一 floor 有多个 plan view 时全集归属是否仍
唯一；同时复核 4 个 exclusion 是否都保持“具名 NA”，不会在后续语料里膨胀成静默白名单。
