# 对抗审裁决 · 判卷器「数值身份 + 计分度量」施工批

- 日期：2026-07-27
- 被审对象：commit `29a1ce0a1b19740f69713353648bcec4cd05ec95`（`7.27_JudgeIdentityMetricV2`）
- 裁决：**REWORK**
- findings：**2 BLOCKER / 4 MAJOR / 1 MINOR**
- 审阅纪律：只审不修；生产码与既有测试未改。所有 neuter 均在 `/tmp/judge-sol-probes.APFg5l/` 副本完成。

## 1. 总裁决

本批的三个主方向都有真实进展：三个既有浮点表示反例能通过，长度分母的 A4 三个点名值正确，GT/产品身份池在当前实现中也确实分离。独立全仓为 `1706 passed, 10 xfailed`。

但不能批准。首要原因是 W3 新匹配器存在可直接造出总分 false-green 的核心错误：同一条 4 m 产品墙可以同时覆盖两道不同支撑线上的 4 m 答案墙，最终得到 `8/8 pass`，且 extra/duplicate 均不响。其次，C-1″ 的四条输入合同并未被运行时完整执行；实现只有“看相邻数值距离猜意图”，没有表达或验证“同一意图/不同意图”的信息，能静默分裂同一意图，也能静默焊接不同意图。

验锁同样未过关：A8、P-1(b)、A2-GT 精确码、A7 窗口消费接线均已用 `/tmp` neuter 证明 false-green；执行日志“21 条锁全部经 neuter、零 false-lock”的结论不成立。

## 2. Findings

### BLOCKER B-1 · 一条产品墙可同时赚取两道平行答案墙的全部长度

位置：[segment_score.py:516](../../../../src/agent/judge/segment_score.py#L516) 至 [segment_score.py:574](../../../../src/agent/judge/segment_score.py#L574)。

`match_plan_segments` 逐 target 独立遍历所有 observation。只要 observation 对某 target 通过位置容差，就会在该 target 上再次增加 coverage；`obs_covered` 也是跨 target 直接求和，而不是 observation 几何的并集。因此“联合切点”只在单个 target 内成立，没有先把产品墙单向注册到唯一答案支撑线，也没有守恒 `covered_product_length <= product_length`。

活体夹具：

- GT footprint：`[0,2] × [0,4]`
- GT 三个相邻 zone 的 x 区间：`[0,1] / [1,1.2] / [1.2,2]`
- 因而答案有两道 4 m 内墙：`x=1.0`、`x=1.2`
- 产品只有两个 zone，唯一内墙为 `x=1.1`、长度 4 m
- `plan_position_tol_m = 0.3`

实测：

```text
rows = [
  (target x=1.0, within_tolerance, eligible_units=4.0),
  (target x=1.2, within_tolerance, eligible_units=4.0),
]
observation_map = {single_product_wall: (left_target, right_target)}
walls_complete = denominator 8.0 / passing 8.0 / failing 0.0 / pass
no_extra_walls = NA
no_duplicate_wall_strokes = NA
```

这不是边界舍入：只把产品墙从 `x=1.1` 改为 `x=0.8`，同一夹具立即变成 `passing=4.0 / failing=4.0 / fail`。

可复现锁：

1. 在 `tests/test_judge_identity_metric.py` 新增上述三 zone → 两 zone 完整提取夹具。
2. 断言一条 4 m observation 不能贡献 8 m passing；至少须拒绝、唯一注册到一道支撑线，或产生 4 m miss。
3. 当前实现该断言变红；现有 1706 测试全绿。

这是判卷器直接给错误答案的 false-green，阻断批准。

### BLOCKER B-2 · A9/C-1″ 只实现了聚类守卫，没有执行四条输入合法性合同

位置：[segment_score.py:61](../../../../src/agent/judge/segment_score.py#L61)、[segment_score.py:170](../../../../src/agent/judge/segment_score.py#L170)、[segment_score.py:353](../../../../src/agent/judge/segment_score.py#L353)、[segment_score.py:431](../../../../src/agent/judge/segment_score.py#L431)。

合同 ①/② 需要知道两个出现值是“同一意图”还是“不同意图”。当前输入和 `_cluster_axis` 都没有这个信息；代码只是按距离反过来猜意图，因而无法在运行时验证所依赖的前提。这是循环假设，不是合同执行。

四个独立反例：

1. 三个相邻值的 gap 都 `< merge`，但总直径为 `1.8003376567321538e-12 > merge=1e-12`。当前全部静默合成一个原子，因为直径守卫被放到 `1e-11`；违反合同 ① 仍 GREEN。
2. 两条 fixture 明确声明为同一连续 boundary 意图，接点为 `2.0` 与 `2.0+2e-11`。当前静默分裂并返回两条带缝 boundary segment；没有响亮拒绝。
3. 两条 fixture 明确声明为不同 boundary 意图，x 为 `1.0` 与 `1.0+5e-13`。当前静默焊成完全相同的两条 segment，`unique_geometry == 1`；违反合同 ②/owner 冲突仍 GREEN。
4. `coerce_plan_observations` 输入一条 `(0,0) → (5e-13,0)` reading segment。归并后得到 `(0,0) → (0,0)`、`length=0.0`，没有合同 ④ 的响亮拒绝。

合同 ④ 目前只检查 polygon 的相邻顶点坍缩；没有覆盖 boundary segment、reading segment、非相邻重复顶点、归并后环自交，也没有完整的归并致 owner 重数冲突检查。合同版本不匹配路径亦不存在。

错误分类学也未按 R-5 落地：

- `STABLE_ERROR_CODES` 没有新增非有限/护带/链桥/坍缩/版本不匹配的分码；
- A3/A9 只把差异放在 `context["reason"]`，顶层 `ScoreContractError.code` 仍统一为 `score_gt_identity_invalid` 或 `score_product_identity_invalid`；
- edge-collapse 上下文只记代表点的一个 x hex，没有记录被合并的原始 binary64 对与精确直径。

可复现锁：把上述四个输入各包在 `pytest.raises(ScoreContractError)` 中，当前四条均直接变红（都没有抛错）。把反例 4 的 `5e-13` 改为 `3e-12` 后才因护带响亮拒绝，证明现有锁只钉了距离分支，没有钉语义合同。

要通过，必须先使“意图组/合同版本”成为可验证输入，或给出等价且可机械验证的来源身份；不能继续以数值距离本身充当被验证的意图真值。

### MAJOR M-1 · A8 是 false-lock：禁止的联合建池下原测试仍绿，且 `approx` 放过字节污染

位置：[test_judge_identity_metric.py:257](../../../../tests/test_judge_identity_metric.py#L257)。

当前测试有三个独立缺口：

1. `targets = extract_gt_plan_segments(gt)` 在两种产品之外只提取一次；所谓“GT atom set 相同”只是随后再次对同一 GT 调同一函数并与自身相等。
2. 两种产品拓扑虽不同，但它们提供给联合池的相关坐标值相同；没有产品端点落在 GT 端点的 merge 邻域内。即使实现非法联合建池，这个夹具也不会移动答案代表值。
3. 分母用 `pytest.approx`，不符合 C-1′ 的 binary64/逐字节相同要求。

`/tmp` neuter：

- 在 `match_plan_segments` 的 target/observation materialization 后插入真实的 GT+产品联合 `_build_floor_identity`，并把 target 也映射到联合代表；
- 原 `test_a8_answer_denominator_independent_of_product`：**1 passed**；
- 增加第二产品端点 `4.0-5e-13`：
  - 产品 A 分母：`4.0` / hex `0x1.0000000000000p+2` / bytes `4010000000000000`
  - 产品 B 分母：`3.9999999999995` / hex `0x1.ffffffffffb9ap+1` / bytes `400ffffffffffb9a`
  - `pytest.approx` 仍通过，`struct.pack(">d", a) == struct.pack(">d", b)` 变红。

必须改为两种产品携带不同的 sub-merge 近邻值，并比较答案原子序列的规范字节及 denominator binary64 字节；只比数值近似和重复提取不构成 A8 锁。

### MAJOR M-2 · P-1(b) 删除了既有 overlong extent 锁，新语义没有接手；集合断言也无理由弱化

位置：[test_c2_b4b_phase_b.py:166](../../../../tests/test_c2_b4b_phase_b.py#L166)。

P-1(a) 的下游语义有别处接手：`test_w4_extra_and_duplicate_walls_split_into_separate_criteria` 会断言 `no_duplicate_wall_strokes.failing_units == 2.0`，因此“重笔可全链静默通过”这一点没有成立。

P-1(b) 则确认有缺口：

- 原 `long: [2,3.2]` 对 target `[2,3]` 的 fixture 被删除；
- 新测试只放了独立 offset 和完全断开的 extra；
- 注释声称“target complete + overshoot 0.2 extra”，却没有任何断言执行这句话；
- 当前实测状态集合恰好就是四项，没有新增状态，`==` 改成 `<=` 没有实现需要。

`/tmp` neuter：把 [segment_score.py:571](../../../../src/agent/judge/segment_score.py#L571)

```python
extra = obs.length - obs_covered[obs.key]
```

改为“observation 只要覆盖过任一 target，就丢弃全部 overshoot；完全断开的 extra 仍保留”。结果：

```text
tests/test_judge_identity_metric.py
+ 两条改写后的 phase_b 测试
= 23 passed
```

新增精确夹具断言 `[("complete",1.0), ("extra",0.2)]` 才会变红。故这是已复现的 false-lock，不是单纯测试风格问题。

### MAJOR M-3 · W5 “共享正交判据”未接入生产或判卷决策，advisory 也没有运行时出口

位置：[orthogonality.py](../../../../src/agent/correction/orthogonality.py)、[cell_geometry.py:158](../../../../src/agent/correction/cell_geometry.py#L158)、[segment_score.py:327](../../../../src/agent/judge/segment_score.py#L327)。

全仓引用核：

- 生产端 `cell_geometry` 只 import 了常量，仍自行执行 `dx > _EPS and dy > _EPS`；
- 判卷端对共享模块零 import；
- `classify_edge_orthogonality` 与 `edge_is_axis_aligned` 的生产调用数和判卷调用数均为 0；
- 所谓 advisory 没有被记录、传播或写入任何运行时结果。

`/tmp` 将 `classify_edge_orthogonality` 首行改为 `raise AssertionError("reached")` 后：

```text
test_l_b_typed_correction_fp_sum_not_false_red                 PASS
test_y1_nonorthogonal_exact_reverse_paired_not_false_red       PASS
```

只有直接调用这个共享 helper 的新增单元测试会红，证明锁没有焊住生产↔判卷接缝。

另有现实可达 R-4 反例：

- cell A 的共享边：底 x=`0.5`、顶 x=`0.5+5e-10`
- cell B 的反向共享边：底 x=`0.5`、顶 x=`0.5+4e-10`
- `validate_corrected_geometry` 五项全 GREEN；
- scorer 报 `score_product_identity_invalid / exterior_duplicate_owner`。

只把 B 顶点改为与 A 相同的 `0.5+5e-10`，生产仍五项 GREEN，scorer 转为正常抽出 1 条内墙。前一形态即使判卷器选择不量，也应走 unsupported/NA，而不是宣判产品 identity invalid/broken。

### MAJOR M-4 · A2-GT 精确码锁与 A11 neuter 自查声明不实

A2 当前生产行为本身是：GT 与产品两侧的 `1e-9` 缝都会红，当前顶层 side code 也恰好正确。但答案侧没有按派工单钉 `ScoreContractError.code`：

- 新 `test_a2_identity_splits_1e9_gap` 只断言 `_cluster_axis` 返回两个原子，不走响亮拒绝路径；
- 既有 `test_l_c_1e9_endpoint_gap_still_red` 只断言 `context["reason"]`，不检查 code。

`/tmp` 把 GT `_pair_interior_edges(... identity_code=...)` 从 `score_gt_identity_invalid` 改为 `score_product_identity_invalid`：

```text
施工方两条 A2 测试 + 既有 GT 1e-9 测试 = 3 passed
新增 assert caught.value.code == "score_gt_identity_invalid" = FAIL
```

执行日志称“21 条锁全部经 neuter、零 false-lock”，但本审实际矩阵为：

| neuter | 施工锁结果 | 真正反例锁 |
|---|---:|---:|
| 禁止的 GT+产品联合建池 | A8 仍绿 | 逐 binary64 比较红 |
| 丢弃 overlap observation 的 overshoot | 相关 23 条仍绿 | overlong 0.2 extra 锁红 |
| GT 1e-9 改成 product 错码 | 相关 3 条仍绿 | GT 精确 code 锁红 |
| 断开 facade map 到窗口消费端 | 新增 21 条全绿 | 完整窗口接线锁应红 |

这不是“共用守卫已披露”可以覆盖的情况，而是 A11 所要求的指定 neuter 没有真正执行到验收出口。

### MINOR N-1 · P-3 的架构理由成立，但 §5-B 出口 2 仍未交付

独立核验结果：

- 实际 correction interior key 形如 `F1:interior:(...)`；
- materialized facade id 形如 `F1:facade:<sha256>`；
- 实测二者集合交集为空；
- `bind_correction_window_segment` 与 `build_correction_host_resolver` 最终查的是 `geometry.facade_segments` 中的 facade id，不查 interior key；
- facade map 在 `product_to_gt` 中后写入，也会覆盖理论上的同名项。

因此施工方“interior 多段覆盖条目进不了正式 correction 窗口宿主 lookup”的理由成立，P-3 不升级为 BLOCKER。

但现有 `test_b_facade_multi_span_straddle_fails_closed_not_first` 只直接调用 `_resolve_facade_product_to_gt`，夹具里没有 window，也没有经过 `assign_openings`、`build_correction_host_resolver` 或 Va。把 [score_service.py:230](../../../../src/agent/judge/score_service.py#L230) 的 `product_to_gt.update(...)` 改成只调用 helper、不把结果接入消费端后，新增 `tests/test_judge_identity_metric.py` **21 条仍全绿**。

故派工单要求的“新增多段覆盖窗夹具”确实未完成；应补正式 correction window → facade multi-span → opening assignment → host resolver/claim 的完整锁。

## 3. A1–A11 独立验收表

| 出口 | 裁断 | 独立证据 |
|---|---|---|
| A1 | PASS | 真实 sm24 `8.059999999999999↔8.06`、typed correction `0.1+0.2↔0.3` 的既有活体提取锁均绿；r2 nextafter 量子边界对绿 |
| A2 | **FAIL（锁）** | 双侧当前行为红，但 GT 顶层精确码可被改错而三条相关测试全绿 |
| A3 | **FAIL（分码）** | 护带会响亮拒绝且有 hex；但只在 `context.reason` 分型，没有 R-5 要求的稳定顶层分码 |
| A4 | PASS（点名三值） | `0/4`、`4/4`、`2/4` 均独立复算正确；但不覆盖 B-1 的跨支撑线双重记功 |
| A5 | PASS | 见 §5，父提交/目标提交/工作树逐文件 SHA-256 清单完全相同 |
| A6 | PASS | sm21 reviewer-canonical score bytes、legacy PNG hash、legacy dispatch 三项父提交与目标提交一致 |
| A7 | **FAIL（锁）** | P-3 interior 理由成立，但没有完整多段窗夹具；消费端断线时新增 21 锁全绿 |
| A8 | **FAIL** | 联合池 neuter 下原锁绿；近邻产品使答案分母 binary64 改变而 `approx` 仍绿 |
| A9 | **FAIL** | 合同 ①/② 无意图输入；合同 ④ 只覆盖 polygon 相邻坍缩；版本不匹配缺失 |
| A10 | PASS | `segment_scorer` v1→v2 的常量、Literal、service、两测试已同步；config 未变，G-b 确实未撞 |
| A11 | **FAIL** | 四组独立 false-lock neuter，见 M-4 |

## 4. R-2 / R-4 独立核

### R-2 阈值

未采信执行日志数字，直接读取受保护 sm24 GT：

```text
raw vertices = 50
unique x = 4
unique y = 8
相邻非等值且 diff < 1e-6 的 pair = 0
sm24 活体漂移 = 1.7763568394002505e-15
typed 0.1+0.2 漂移 = 5.551115123125783e-17
ulp(20.0) = 3.552713678800501e-15
```

独立余量：

```text
merge / sm24 max drift = 562.949953421312×
merge / ulp(20m)       = 281.474976710656×
1e-9 / split           = 100×
```

施工日志的算术与两侧余量准确。`merge=1e-12` 与旧 quantum 数字相同本身不足以证明“先定数字后补论证”；在可复算余量成立的前提下，本审不单独据此出 finding。真正失败点是 B-2：`diam=1e-11` 允许直径已经超过合同 merge 上限的链静默合并。

### R-4 口径

W5 没有真实接线，且上文生产五项 GREEN / scorer `score_product_identity_invalid` 的活体反例证明“生产判合法、判卷只判能否量”的拆分尚未兑现。此项归入 M-3。

## 5. 独立测试、GT hash 与工作树纪律

全仓独立运行：

```text
pytest -n auto
1706 passed, 10 xfailed, 150 warnings in 250.58s (0:04:10)
```

GT 字节核：

```text
case_tests/test_baseline/gt 文件数：
parent 24 / commit 24 / worktree 24

三份逐文件 SHA-256 清单摘要：
d0e8b0140b2a6cf3585c6499eba84a722e15a8f523e4efcad2f4a1fa8e158ea5
```

两次 `diff -u` 均为空。

sm21 legacy 独立父提交↔目标提交对照：

```text
reviewer-canonical score JSON:
d291e945efd1ec9f4b5340f825d49eddfee652e84e41b5fbede5adb1cfc3c64e
bytes = 7328（两边相同）

legacy grade PNG:
c44204353979bd390112b47b1d60317adb0d809a1002816126d954c8b7c36a30
pixel(300,300) = (238,238,234)
pixel(50,900)  = (150,150,145)

score_attempt_service:
typed_request=None 时两边均只调用注入的 legacy_evaluator
```

审毕主工作树的 tracked diff 为空；保留的未跟踪输入只有审前已有的两份 request 文档，另新增本裁决书。`case_tests/test_baseline/gt/**` 与 `AI_agent/CLAUDE.md` 均未触碰。

## 6. REWORK 必做

1. 修复 B-1：先建立产品墙到答案支撑线的单向、守恒注册；一条产品几何不得在不同平行支撑线上重复赚取长度。补窄房间活体锁与 `covered_product_length <= product_length` 守恒锁。
2. 重新设计并真正执行 C-1″：让同意图/异意图与合同版本成为可验证输入；覆盖 boundary、reading、polygon 的坍缩、重复、自交、owner 冲突。
3. 按 R-5 增加稳定分码及完整 binary64/直径上下文；A2 两侧分别钉顶层精确 code。
4. 重写 A8：近邻产品夹具 + 答案原子规范字节 + denominator binary64 字节精确相等；联合池 neuter 必须使锁变红。
5. 恢复 P-1(b) overlong 语义锁与精确状态集合；不得以注释代替 `complete + 0.2 extra` 断言。
6. W5 的共享判据必须由生产和判卷真实调用，advisory 必须有运行时产物；判卷不能把“量不了”报成产品几何 broken。
7. 补正式多段 facade window 的 assignment + host resolver + Va e2e 锁，并重做 A11 neuter 表；不得继续宣称当前锁零 false-lock。
