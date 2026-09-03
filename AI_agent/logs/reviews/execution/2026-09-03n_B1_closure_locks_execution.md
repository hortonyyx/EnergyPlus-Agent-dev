# B1 收口补锁 · 执行档

- **日期**：2026-09-03
- **施工方**：GPT 家族施工席
- **任务书**：[`../request/2026-09-03n_B1_closure_locks_dispatch.md`](../request/2026-09-03n_B1_closure_locks_dispatch.md)
- **出处**：[`../verdict/2026-09-03f_B1_projection_bridge_crossreview_claude.md`](../verdict/2026-09-03f_B1_projection_bridge_crossreview_claude.md)
- **权威口径**：[`../../../proposals/correction_projection_bridge.md`](../../../proposals/correction_projection_bridge.md) v7

## 〇、开工自检（原命令 + 原输出）

```text
$ pwd && git log --oneline -1 && git status --porcelain
/tmp/b1_locks_gpt
c32fdb6 09.03n_B1_closure_locks_dispatch
```

`git status --porcelain` 无输出。

```text
$ python -c "import src.agent.correction.projection_bridge as m; print(m.__file__)"
/tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
```

自证落在指定工作树；全程未进入或修改 `/workspaces/EnergyPlus-Agent-dev`。

## 一、T4 先判归属：应在 B1 强制，未触发 A 层停报

设计稿 §四使用的 profile 值域是 `strict | exploratory`，对应当前接线参数
`evidence_chain_profile`，不是另一套 `exploratory | golden | regression` 的
`run_profile`。在 `run_correction` 读回 envelope 时，以下三样仍同时可得：

1. 调用方要求的 evidence-chain profile；
2. envelope 的 `completion` 与具名悬端债务；
3. outcome 最终 provisional 的绑定哈希。

这里也是 B1 将裸 geometry 返回、从而可能流向后续 gate/judge 前的最后边界。若把规则推给 B5，
当前函数仍会先泄漏 degraded geometry，正是 F-6 点名的缺门。因此归属判定为 **B1**：先做消费侧
hash 绑定校验，再在 `strict + degraded` 时响亮 `RuntimeError`；envelope 已落盘并保留作审计，
`exploratory + degraded` 仍按设计允许返回。

实现位置：`src/agent/pipeline.py:1433-1458`。

## 二、四项施工结果

| 项 | 落地 | 锁 |
|---|---|---|
| **T1 / F-3** | 保留消费侧 `source_resolved_sha256 == final_provisional_sha256` 硬校验 | `test_switch_on_rejects_a_tampered_projection_binding` 在 producer 落盘后、consumer 读回前篡改 envelope；不是只断言正常路径两值碰巧相等 |
| **T2 / F-2** | 生产接线继续显式传 `resolution_m=0.0`，source 串声明 `floating-point metres` + `no declared quantisation` | `test_switch_on_returns_the_projected_geometry` 同时钉数值和来源串 |
| **T3 / F-5** | 几何算法未改；补宿主 0/2 主混厚锁、真产物宿主库存锁、真产物“延伸只扩不缩”锁 | `test_mixed_thickness_opening_with_{no,two}_owner_is_loud`、`test_real_sm25_host_inventory_is_unique_but_has_no_refusal_stock`、`test_real_sm25_inward_candidates_exist_but_extensions_never_shorten` |
| **T4 / F-6** | 在 B1 consumer boundary 实现 strict 拒绝 degraded | `test_strict_profile_rejects_real_degraded_projection_before_judge`；同时正常 success 锁明确钉住 exploratory 可返回真实 degraded |

本单只改 `src/agent/pipeline.py` 与两个 B1 测试文件；没有改几何桥算法、`as_measured.py`、
任何 gt/baseline/hash 产物，也没有碰 `tests/conftest.py`。

## 三、T3 真产物库存（原命令 + 原输出）

```text
$ python - <<'PY'
from tests.test_b1_projection_bridge_production_loader import _real_artifact, _all_keep_compilation
from src.agent.correction.projection_bridge import opening_spans_from_artifact, cut_lines_from_wall_compilation
artifact = _real_artifact()
compilation = _all_keep_compilation(artifact)
spans = opening_spans_from_artifact(artifact)
owners = {}
for wall in compilation.walls:
    for ref in wall.source_refs:
        owners.setdefault(ref.observation_id, []).append(wall.wall_id)
counts = [len(owners.get(span.face_observation_id, ())) for span in spans]
lines, _ = cut_lines_from_wall_compilation(compilation.walls, spans)
resolution = 0.0
outward = []
inward = []
for line in lines:
    for other in lines:
        if other.axis == line.axis:
            continue
        crosses = (other.along_lo_m - line.half_thickness_m - resolution <= line.pos_m <= other.along_hi_m + line.half_thickness_m + resolution)
        if not crosses:
            continue
        for label, end, is_outward in (
            ('lo', line.along_lo_m, other.pos_m < line.along_lo_m),
            ('hi', line.along_hi_m, other.pos_m > line.along_hi_m),
        ):
            in_band = abs(end - other.pos_m) <= other.half_thickness_m + resolution
            if in_band:
                row = (line.origin_id, label, other.origin_id, end, other.pos_m)
                (outward if is_outward else inward).append(row)
print('WALLS', len(compilation.walls))
print('SPANS', len(spans))
print('OWNER_COUNT_HISTOGRAM', {n: counts.count(n) for n in sorted(set(counts))})
print('LINES', len(lines))
print('OUTWARD_CANDIDATES', len(outward))
print('INWARD_OR_EQUAL_CANDIDATES', len(inward))
print('INWARD_STRICT', sum(end != pos for _,_,_,end,pos in inward))
print('INWARD_STRICT_SAMPLE', [r for r in inward if r[3] != r[4]][:5])
PY
WALLS 22
SPANS 87
OWNER_COUNT_HISTOGRAM {1: 87}
LINES 143
OUTWARD_CANDIDATES 59
INWARD_OR_EQUAL_CANDIDATES 56
INWARD_STRICT 56
INWARD_STRICT_SAMPLE [('wall_14734d790a55d6242de7bef35444acd1a5acd51b9c6c9f1426c35eaf9f26df7f', 'lo', 'wall_603ffaad369af9467b8c264e44d4c8f5ddd8468b818e8303f04af94cad1199fe', 0.0054, 0.1253), ('wall_149f24005ee3767b273f56f7d33a5681d316584760be4bac1112a5df2d3a43ef', 'lo', 'wall_603ffaad369af9467b8c264e44d4c8f5ddd8468b818e8303f04af94cad1199fe', 0.0054, 0.1253), ('wall_459c98dd9411896300bd375b27128d705727a7c01cc62ba51a72797ab42b4aac', 'hi', 'wall_14734d790a55d6242de7bef35444acd1a5acd51b9c6c9f1426c35eaf9f26df7f', 14.2273, 14.118200000000002), ('wall_603ffaad369af9467b8c264e44d4c8f5ddd8468b818e8303f04af94cad1199fe', 'lo', 'wall_14734d790a55d6242de7bef35444acd1a5acd51b9c6c9f1426c35eaf9f26df7f', 14.0091, 14.118200000000002), ('wall_603ffaad369af9467b8c264e44d4c8f5ddd8468b818e8303f04af94cad1199fe', 'lo', 'wall_5175cf1179cfb74bf95a4efa8b5dedc5b61d187d408d585544a37c2e58559113', 16.0596, 16.0651)]
```

结论按 `[[gate-teeth-direction-follows-fixture-inventory]]` 明说：

- **宿主唯一性**：真产物 87/87 都是恰好 1 主；成功方向有存货，0 主/2 主拒绝方向**没有真产物存货**，
  所以那两向必须由合成锁承重。本单把合成锁换到既有同图 90/150/300/370 混厚数据上；没有在
  几何派生代码或新断言中引入长度/厚度阈值。
- **延伸外向限定**：真产物有 56 个严格向内候选，库存充足；新锁直接在真实 143 条 cut line 上断言
  每条输出区间包含输入区间。低端或高端任一外向判断被摘，都会在真产物上红。

## 四、验牙：逐项摘实现（原命令 + 原始失败读数）

每个变异只改一处；命令把 `__file__` 与 pytest 放在同一条命令。以下逐字摘录 traceback 的承重
失败行与 pytest summary；每次记录后均逐字恢复。

### M1 · T1：删消费侧绑定判断

变异：`if envelope.source_resolved_sha256 != ...` → `if False and ...`。

```text
$ python -c "import src.agent.correction.projection_bridge as m; import src.agent.pipeline as p; print('BRIDGE', m.__file__); print('PIPELINE', p.__file__)" && python -m pytest tests/test_o22m7_evidence_wiring.py::test_switch_on_rejects_a_tampered_projection_binding -q -n 6 -p no:cacheprovider
BRIDGE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
PIPELINE /tmp/b1_locks_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
E       Failed: DID NOT RAISE <class 'RuntimeError'>
FAILED tests/test_o22m7_evidence_wiring.py::test_switch_on_rejects_a_tampered_projection_binding
1 failed in 4.54s
```

### M2a · T2：生产 resolution 偷换成 `0.0218`

```text
$ python -c "import src.agent.correction.projection_bridge as m; import src.agent.pipeline as p; print('BRIDGE', m.__file__); print('PIPELINE', p.__file__)" && python -m pytest tests/test_o22m7_evidence_wiring.py::test_switch_on_returns_the_projected_geometry -q -n 6 -p no:cacheprovider
BRIDGE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
PIPELINE /tmp/b1_locks_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
>       assert envelope.tolerance_resolution_m == 0.0
E       AssertionError: assert 0.0218 == 0.0
FAILED tests/test_o22m7_evidence_wiring.py::test_switch_on_returns_the_projected_geometry
1 failed in 4.49s
```

### M2b · 验收 #6 的不同形攻击：数值不动，只抹掉来源声明

变异：保留 `resolution_m=0.0`，把 source 串中的 `floating-point metres, no declared quantisation`
换成不再作这两项声明的文字。这与跨审 N1 的“换数值”是不同攻击面。

```text
$ python -c "import src.agent.correction.projection_bridge as m; import src.agent.pipeline as p; print('BRIDGE', m.__file__); print('PIPELINE', p.__file__)" && python -m pytest tests/test_o22m7_evidence_wiring.py::test_switch_on_returns_the_projected_geometry -q -n 6 -p no:cacheprovider
BRIDGE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
PIPELINE /tmp/b1_locks_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
>       assert "floating-point metres" in envelope.resolution_source
E       AssertionError: assert 'floating-point metres' in 'production evidence chain: as-drawn *_m fields, binary coordinates without a declared grain (N-3 redeclared at the wiring)'
FAILED tests/test_o22m7_evidence_wiring.py::test_switch_on_returns_the_projected_geometry
1 failed in 6.63s
```

### M3a · T3：删宿主恰好唯一判断

变异：`if len(owners) != 1` → `if False and len(owners) != 1`。

```text
$ python -c "import src.agent.correction.projection_bridge as m; print('FILE', m.__file__)" && python -m pytest tests/test_b1_projection_bridge_production_loader.py::test_mixed_thickness_opening_with_no_owner_is_loud tests/test_b1_projection_bridge_production_loader.py::test_mixed_thickness_opening_with_two_owners_is_loud -q -n 6 -p no:cacheprovider
FILE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
bringing up nodes...
bringing up nodes...

FF                                                                       [100%]
E           IndexError: tuple index out of range
E       Failed: DID NOT RAISE <class 'src.agent.correction.projection_bridge.ProjectionBridgeError'>
FAILED tests/test_b1_projection_bridge_production_loader.py::test_mixed_thickness_opening_with_no_owner_is_loud
FAILED tests/test_b1_projection_bridge_production_loader.py::test_mixed_thickness_opening_with_two_owners_is_loud
2 failed in 2.75s
```

### M3b/M3c · T3：允许低端/高端向内缩

低端变异：`other.pos_m < lo` → `other.pos_m != lo`。

```text
$ python -c "import src.agent.correction.projection_bridge as m; print('FILE', m.__file__)" && python -m pytest tests/test_b1_projection_bridge_production_loader.py::test_real_sm25_inward_candidates_exist_but_extensions_never_shorten -q -n 6 -p no:cacheprovider
FILE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
>           assert after.along_lo_m <= before.along_lo_m
E           AssertionError: assert 0.1253 <= 0.0054
FAILED tests/test_b1_projection_bridge_production_loader.py::test_real_sm25_inward_candidates_exist_but_extensions_never_shorten
1 failed in 2.96s
```

高端变异：`other.pos_m > hi` → `other.pos_m != hi`。

```text
$ python -c "import src.agent.correction.projection_bridge as m; print('FILE', m.__file__)" && python -m pytest tests/test_b1_projection_bridge_production_loader.py::test_real_sm25_inward_candidates_exist_but_extensions_never_shorten -q -n 6 -p no:cacheprovider
FILE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
>           assert after.along_hi_m >= before.along_hi_m
E           AssertionError: assert 14.118200000000002 >= 14.2273
FAILED tests/test_b1_projection_bridge_production_loader.py::test_real_sm25_inward_candidates_exist_but_extensions_never_shorten
1 failed in 2.96s
```

### M4 · T4：关掉 strict+degraded 门

变异：profile 判断前加 `False and`。

```text
$ python -c "import src.agent.correction.projection_bridge as m; import src.agent.pipeline as p; print('BRIDGE', m.__file__); print('PIPELINE', p.__file__)" && python -m pytest tests/test_o22m7_evidence_wiring.py::test_strict_profile_rejects_real_degraded_projection_before_judge -q -n 6 -p no:cacheprovider
BRIDGE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
PIPELINE /tmp/b1_locks_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
E       Failed: DID NOT RAISE <class 'RuntimeError'>
FAILED tests/test_o22m7_evidence_wiring.py::test_strict_profile_rejects_real_degraded_projection_before_judge
1 failed in 5.10s
```

全部恢复后的机械核对：

```text
$ git status --porcelain && git diff --exit-code && git diff --cached --exit-code
```

无输出。

## 五、验收 §四六条逐项报告

| # | 结论 | 证据 |
|---|---|---|
| **1 每条新锁有牙** | ✅ | §四：T1 1 红；T2 数值 1 红、来源串 1 红；T3 宿主 2 红、低/高端外向各 1 红；T4 1 红；恢复后三个 git 检查无输出 |
| **2 T3 真产物库存** | ✅ 已明说 | 宿主成功方向 87/87 有货，0/2 主拒绝方向无货；外向限定有 56 个严格向内候选，真产物锁有货，见 §三 |
| **3 T4 明确归属** | ✅ B1 强制 | §一给出理由；`run_correction` 在返回 geometry 前拒绝 `strict + degraded`，不是默认下游兜住 |
| **4 既有 24+12 不退化** | ✅ | 原桥核心 `acceptance + fixtures` 精确 24 passed；历史第二轮净增 12 = production loader +10、终点锁替换净 +2，全部包含在恢复后的 B1 76 passed 中。本单新增 6 个测试实例，未删除旧锁 |
| **5 全量绿 `-n 6`** | ✅ | 3714 passed / 2 skipped / 13 xfailed / 0 failed，见 §七 |
| **6 不同形攻击** | ✅ | M2b 不改 resolution 数值、只抹 provenance 声明，也使新锁红；另有 T1 的落盘后篡改 envelope 与 T3 高端向内缩攻击 |

## 六、B1 定向回归（原命令 + 原输出）

既有桥核心 24 条：

```text
$ python -c "import src.agent.correction.projection_bridge as m; print('FILE', m.__file__)" && python -m pytest tests/test_b1_projection_bridge_acceptance.py tests/test_b1_projection_bridge_fixtures.py -q -n 6 -p no:cacheprovider
FILE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
bringing up nodes...
bringing up nodes...

........................                                                 [100%]
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
24 passed in 2.97s
```

B1 跨审同口径全集（原 70 + 本单 6）：

```text
$ python -c "import src.agent.correction.projection_bridge as m; import src.agent.pipeline as p; print('BRIDGE', m.__file__); print('PIPELINE', p.__file__)" && python -m pytest tests/test_b1_projection_bridge_acceptance.py tests/test_b1_projection_bridge_fixtures.py tests/test_b1_projection_bridge_production_loader.py tests/test_o22m7_evidence_wiring.py tests/test_b1_prime_failopen_defaults.py tests/b1_gt_reconciliation.py -q -n 6 -p no:cacheprovider
BRIDGE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
PIPELINE /tmp/b1_locks_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

........................................................................ [ 94%]
....                                                                     [100%]
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
76 passed in 5.73s
```

## 七、权威全量（环境自证与 pytest 同一条命令）

```text
$ python -c "import src.agent.correction.projection_bridge as m; import src.agent.pipeline as p; print('BRIDGE', m.__file__); print('PIPELINE', p.__file__)" && python -m pytest tests/ -q -n 6 -p no:cacheprovider
BRIDGE /tmp/b1_locks_gpt/src/agent/correction/projection_bridge.py
PIPELINE /tmp/b1_locks_gpt/src/agent/pipeline.py
bringing up nodes...
bringing up nodes...

........................................................................ [  1%]
```

中间逐点进度与 211 条 warnings 不重复铺陈；终段原文：

```text
..............................                [100%]
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
3714 passed, 2 skipped, 13 xfailed, 211 warnings in 554.80s (0:09:14)
```

跨审冻结树为 3708 passed；本单新增恰好 6 个测试实例，所以 3714 = 3708 + 6，零红闭合。

## 八、分段提交纪律

三段代码/锁提交均用明确路径 `git add`，提交前先看 `git diff --cached --numstat`：

```text
49	0	tests/test_o22m7_evidence_wiring.py
[wt/09.03n_b1_locks 965303b] 09.03_B1_projection_binding_locks
 1 file changed, 49 insertions(+)
```

```text
117	0	tests/test_b1_projection_bridge_production_loader.py
[wt/09.03n_b1_locks 743abb6] 09.03_B1_host_extension_locks
 1 file changed, 117 insertions(+)
```

```text
18	1	src/agent/pipeline.py
57	1	tests/test_o22m7_evidence_wiring.py
[wt/09.03n_b1_locks 02e6367] 09.03_B1_strict_degraded_gate
 2 files changed, 75 insertions(+), 2 deletions(-)
```

全程未执行 `pip install -e .`、`git add -A` 或跳 hook。

## 九、我认为最薄弱的一处

**最薄弱 = T4 的锁虽然使用了真实生产帧产生的 degraded envelope，但 strict consumer 场景需要在测试中
隔离上游 profile。** 真 sm25 帧在决策前仍有 unresolved wall choices，直接以 strict 驱动上游编译会先在
wall compiler 响亮终止，天然到不了“success + degraded”的 B1 消费分支。新锁因此让真实上游先按
exploratory 产出真实 envelope，再把同一 envelope 交给请求 strict 的 `run_correction` consumer，锁住本单
真正缺失的边界规则；它没有手造 envelope，但仍不是一条自然 strict 端到端路径。

这不削弱硬规则的归属或实现，但若后续出现一份“strict 决策循环可成功、投影仍 degraded”的真实产物，
应追加不隔离 profile 的端到端锁。相比之下，T1/T2 都走自然生产接线，T3 外向限定也在真产物有 56 个
直接攻击库存，承重更实。

## 十、停报与 B 层记录

- **A 层**：零触发。T4 判归 B1 并已强制；无需触碰任何 §二 禁令；未改已落库/已签字产物的哈希或基线。
- **B 层新缺陷**：零。T3 的宿主 0/2 主在真产物无库存是任务书已点名的测试覆盖事实，本档明确量化，
  不另冒充新缺陷。
