# ②-2 模块 5+6 第一轮返工 v2 · GPT 跨家族复核裁决

- 日期：2026-09-01
- 被审代码冻结点：`a13120d`；复核时 HEAD：`f9bac1e`
- 口径：v2 复核单、原派工单 §四、上一轮四条阻断、已过审设计稿 §6.1–§6.3
- 写面：只审 `decision_schema.py`、`decision_executor.py`、`test_o22m56_decision_loop.py`

## 1. 裁决

**APPROVE-WITH-FINDINGS — 阻断 0 条，不阻断 4 条。**

B-1/B-2/B-3 的单点逆向变异都精确复现上一轮缺陷；当前树的原例与本席另造同形输入均封住。B-4 的“真实 opening 未入 packet”也由单点逆变精确回到 85/87/87→0；“虚构 candidate wall 被接收”当前则有 membership 与 entity-kind 两道独立门，撤掉任一道仍由另一道拒绝，因此无法诚实写成“一个单点逆变即可复现整个复合缺陷”。上一轮 B-4 本身不推翻：当时两道门均不存在，原反例确实被接收；本轮读数说明返工把它做成了冗余防御，修复不能再归因到其中任一单点。

四条不阻断 finding：

1. **F-1 · B-3 端到端锁量到两个 blocker 的并集。** 单独把 strict 的 `pairs_selection_absent(walls)` policy 格改为 allow，`test_pairs_absent_blocks_success_in_both_profiles` 仍 1 passed，因为同夹具还带 `missing_channel(walls)`；精确逐格锁会红（1 failed / 29 passed），故总体不变量仍受保护，但端到端测试名不能证明该单格独立承重。
2. **F-2 · B-4 的 candidate closure 已是双门，单点逆变不可独立归因。** 撤 `_effect_entities` 的 candidate 收集仍报 `FINDING_ENTITY_WRONG_KIND`；撤 kind-map 的 candidate 格仍报 `FINDING_ENTITY_NOT_IN_PACKET`。这不是当前绕过，而是 v2 第①格对冗余修复的归因边界。
3. **F-3 · N-2 的影响面扩大到下一 packet 身份/固定响应回放。** 同一决定集合 AB/BA 得不同 decision hash、不同下一 packet hash；两条仍都 `success` 且 final provisional 相同，暂不阻断。canonical sort 的建议比上一轮更重要。
4. **F-4 · N-3 锁文案仍过强。** 未修属于返工边界外，边界判断成立；当前源码确实无 dynamic wiring，仍不升级阻断。

## 2. B-1…B-4 三格读数

### B-1 · accept 必须绑定被放行的同一个 provisional

| 格 | 命令/变异 | 实测输出原文 | 结论 |
|---|---|---|---|
| ① 逆向变异 | 在 `_succeeded` 仅删除 `and packet.provisional_geometry == compilation.content_sha256`，运行上一轮 `P2_UNREVIEWED_SUCCESS` 形状；随后立即 checkout | `B1_MUTANT success 8b2f1ff4c97e 52552c171f9b False` | 精确复现：旧 provisional 的 accept 放行了新 geometry。 |
| ② 当前树 | 同一 probe，不改源码 | `B1_CURRENT round_budget_exhausted 8b2f1ff4c97e 52552c171f9b False` | 原例已封住；决定落地但没有对新 hash 的 accept，不能 success。 |
| ③ 自找同形输入 | 自造 `GX1/GX2`、坐标/长度/spacing 均不同的一墙 artifact，再做同轮 select+accept | `B1_SAME_SHAPE round_budget_exhausted False 8f8c9b9ed6d4 dfd8b66b03d6 ()` | 同族错误走不通。 |

复现主体：

```bash
python - <<'PY'
import runpy
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx = ns['dx']
art = ns['_one_pair_artifact'](); _, p0 = ns['_packet_round0'](art)
out = dx.run_decision_loop(
    art, responses=(ns['_select'](p0.open_items[0].item_id, p0),))
print(out.exit_reason, p0.provisional_geometry[:12],
      out.final_provisional_sha256[:12],
      p0.provisional_geometry == out.final_provisional_sha256)
PY
```

### B-2 · 多轮决定累计

| 格 | 命令/变异 | 实测输出原文 | 结论 |
|---|---|---|---|
| ① 逆向变异 | 仅把 loop 的 `decisions=tuple(accumulated)` 改回 `decisions=tuple(bindings)`；运行上一轮两 item/两轮 probe；立即 checkout | `B2_MUTANT round_budget_exhausted [('item_66eb5a8f54d6112db76a1f1b75a83889b6ca86c330eb9cf401e5d34c961c0b4d',), ('item_89897de52e872552d28d41c0fd4d8aa438a6fe289e75247d299a4d9a728446a4',)] ('item_66eb5a8f54d6112db76a1f1b75a83889b6ca86c330eb9cf401e5d34c961c0b4d',)` | 精确复现：第二轮重开第一轮 item。 |
| ② 当前树 | 同一两轮 probe | `B2_CURRENT round_budget_exhausted [('item_66eb5a8f54d6112db76a1f1b75a83889b6ca86c330eb9cf401e5d34c961c0b4d',), ('item_89897de52e872552d28d41c0fd4d8aa438a6fe289e75247d299a4d9a728446a4',)] ()` | 两轮 response 用完所以仍是 budget exit，但关键读数已变为 residual 空；第一轮决定没有消失。 |
| ③ 自找同形输入 | 自造三堵互不重叠墙，三轮分别决定一个 item，第四轮纯 accept | `B2_SAME_SHAPE success True [('item_61df7753159bf01402258c0a7e7f9139c7de9d4a37fdd647364bbf12acc72d0e',), ('item_997fca56a56a9e853a287c8eb6472d4a5a1dfa23d3339d15769725ed9a8982b6',), ('item_d39a5dd1f46209e1a353baedf1486bf6c17bc0a50480787b4900cb059957ac5b',), ()] () 4` | 三轮累计全部保留并成功，类缺陷封住。 |

复现主体：

```bash
python - <<'PY'
import runpy
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx = ns['dx']
art = ns['_two_pair_artifact'](); _, p0 = ns['_packet_round0'](art)
ids = sorted(i.item_id for i in p0.open_items)
r0 = ns['_select'](ids[0], p0)
p1 = ns['_round1_packet'](art, r0)
r1 = ns['_select'](ids[1], p1)
out = dx.run_decision_loop(art, responses=(r0, r1))
print(out.exit_reason, [r.selected_item_ids for r in out.rounds],
      out.residual_open_item_ids)
PY
```

### B-3 · strict residual debt 显式 policy

| 格 | 命令/变异 | 实测输出原文 | 结论 |
|---|---|---|---|
| ① 逆向变异 | 在 `_succeeded` 仅把 `_debt_blocks_success(...)` 调用改回 `debt_info[debt_id][0] == "ambiguous_face"`；跑上一轮 pairs-absent probe；立即 checkout | `B3_MUTANT success () [('debt_dimensions_pairs_debt_probe', 'missing_channel', 'dimensions'), ('debt_elevation_openings_pairs_debt_probe', 'missing_channel', 'elevation_openings'), ('debt_missing_plan_openings_pairs_debt_probe', 'missing_channel', 'plan_openings'), ('debt_missing_walls_pairs_debt_probe', 'missing_channel', 'walls'), ('debt_pairs_absent_pairs_debt_probe', 'pairs_selection_absent', 'walls'), ('debt_room_roles_pairs_debt_probe', 'missing_channel', 'room_roles')]` | 精确复现：pairs 缺失与 walls 缺失被洗成 success。 |
| ② 当前树 | 同一 probe | `B3_CURRENT round_budget_exhausted () [('debt_dimensions_pairs_debt_probe', 'missing_channel', 'dimensions'), ('debt_elevation_openings_pairs_debt_probe', 'missing_channel', 'elevation_openings'), ('debt_missing_plan_openings_pairs_debt_probe', 'missing_channel', 'plan_openings'), ('debt_missing_walls_pairs_debt_probe', 'missing_channel', 'walls'), ('debt_pairs_absent_pairs_debt_probe', 'pairs_selection_absent', 'walls'), ('debt_room_roles_pairs_debt_probe', 'missing_channel', 'room_roles')]` | 原例已封住。 |
| ③ 自找同形输入 | 不用 pairs-absent；自造 `walls=present`、零 wall claims、显式 `zero_payload_channel(walls)` 的合法 artifact | `B3_SAME_SHAPE round_budget_exhausted False () [('missing_channel','dimensions'), ('missing_channel','elevation_openings'), ('zero_payload_channel','walls'), ('missing_channel','plan_openings'), ('missing_channel','room_roles')]` | 主体通道“已接线但零产出”也不能被空 accept 洗白。 |

上一轮原例命令：

```bash
python - <<'PY'
import runpy
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx, wc = ns['dx'], ns['wc']; Response = ns['CorrectionDecisionResponseV1']
doc = ns['_doc'](
  [ns['_face']('F01','col','x',100,[[10,100]]),
   ns['_face']('F02','col','x',112,[[10,100]])], [],
  non_wall={'F01':'text','F02':'text'})
doc['hypotheses']['pairs'] = None
doc['hypotheses']['pairs_status'] = 'ABSENT_NO_MODEL_SELECTION'
art = ns['_adapt'](doc, 'pairs_debt_probe')
comp = wc.compile_wall_ir(art, profile='strict')
packet = dx.build_decision_packet(comp, bundle=art, round_index=0)
response = Response(packet_hash=packet.packet_hash,
                    whole_building_review={'verdict':'accept'})
out = dx.run_decision_loop(
    art, profile='strict', responses=(response,))
print(out.exit_reason, out.residual_open_item_ids,
      [(d.debt_id, d.kind, d.channel)
       for d in art.bundle.evidence_debts])
PY
```

### B-4 · opening-host packet 实体闭包

| 格 | 命令/变异 | 实测输出原文 | 结论 |
|---|---|---|---|
| ①a 逆向变异：opening 入表 | 仅把 `for opening in bundle.bundle.opening_claims` 改成 `for opening in ()`；跑三份真实产物；立即 checkout | `B4_INDEX_MUTANT sm25_1f_v2.json 85 0` / `sm25_2f_v2.json 87 0` / `sm24_1f_v2.json 87 0` | 精确复现上一轮“真实 opening 全未入 packet”。 |
| ①b 逆向变异：candidate membership | 仅把 `_effect_entities` 的候选 tuple 改回只含 `opening_entity_id`；跑虚构 candidate 原例；立即 checkout | `B4_MUTANT_EFFECT_ENTITIES FINDING_ENTITY_WRONG_KIND {'finding_id': 'f_fake_host', 'role': 'candidate_wall_entity_ids', 'entity_id': 'wall_invented_outside_packet', 'expected_kind': 'wall', 'actual_kind': None}` | **没有复现接收**：新加的 kind 门仍拒绝。不能糊成“单点复现成功”。 |
| ①c 逆向变异：candidate kind | 仅删除 `_EFFECT_ENTITY_KINDS` 的 `candidate_wall_entity_ids→wall` 格；跑同一原例；立即 checkout | `B4_MUTANT_KIND_MAP FINDING_ENTITY_NOT_IN_PACKET {'finding_id': 'f_fake_host', 'entity_id': 'wall_invented_outside_packet'}` | **仍没有复现接收**：membership 门仍拒绝。原接收缺陷需两处同时退回才会出现，v2 禁止这样量并集。 |
| ② 当前树 | 原虚构 candidate probe + 三份真实 opening 统计 | `B4_CURRENT FINDING_ENTITY_NOT_IN_PACKET {'finding_id': 'f_fake_host', 'entity_id': 'wall_invented_outside_packet'}`；`B4_CURRENT_INDEX sm25_1f_v2.json 85 85` / `sm25_2f_v2.json 87 87` / `sm24_1f_v2.json 87 87` | 当前两个子缺陷都封住。 |
| ③ 自找同形输入 | candidate wall 槽不用虚构 id/open-item id，而放真实 opening id `op01` | `B4_SAME_SHAPE FINDING_ENTITY_WRONG_KIND {'finding_id': 'f_opening_probe', 'role': 'candidate_wall_entity_ids', 'entity_id': 'op01', 'expected_kind': 'wall', 'actual_kind': 'opening'}` | 成员真实但角色错误的另一载体也走不通。 |

真实 opening 统计命令：

```bash
python - <<'PY'
import runpy
from src.agent.correction.wall_compiler import compile_wall_ir
from src.agent.correction.decision_executor import build_decision_packet
m3 = runpy.run_path('tests/test_o22m3_evidence_adapters.py')
for name, floor in [('sm25_1f_v2.json','1f'),
                    ('sm25_2f_v2.json','2f'),
                    ('sm24_1f_v2.json','1f')]:
    art = m3['_adapts'](name, floor)
    openings = {o.opening_id for o in art.bundle.opening_claims}
    try:
        comp = compile_wall_ir(art, profile='strict')
    except Exception:
        comp = compile_wall_ir(art, profile='exploratory')
    packet = build_decision_packet(comp, bundle=art, round_index=0)
    indexed = {e.entity_id for e in packet.entity_to_source_refs
               if e.entity_kind == 'opening'}
    print(name, len(openings), len(openings & indexed))
PY
```

## 3. §三三处待裁

### 3.1 `zero_payload_channel(walls)` 是否该在表、值是否正确

**应该在表；strict/exploratory 都填 BLOCK，当前值正确。**

它不是把所有 `zero_payload_channel` 一律阻断：support channel 的同 kind 仍 allow。`walls` 是产品主体；`missing_channel(walls)` 与 `zero_payload_channel(walls)` 分别表达“没接到”与“接了但本轮零产出”，若后一格不进表，空 provisional + 空 accept 可因载体从 absent 换成 present/zero 而洗成 success。本席自找的合法 zero-payload artifact 实测为 `round_budget_exhausted False`，验证该格对着“主体墙产物是否存在”达标，而不是只对着 debt 条数达标。

### 3.2 opening refs 丢 `observation_id`

**对当前下游消费者是可接受投影，不是本轮缺陷。**

下游实际读取方式是：

- `_packet_entity_index` 把 ref 化为 `(input_id, source_contract_id, source_output_sha256, json_pointer)` 四元组；
- `_validate_finding` 也用同一四元组校验 `FindingV1.source_refs`；response schema 本来就声明 `ArtifactPointerV1`，不接受 `ObservationRefV1` 的扩展字段；
- opening 身份由 `EntitySourceRefsV1.entity_id` 携带，而 evidence contract 已验证 `opening.opening_id == opening.source_ref.observation_id`。

原始读数：

```text
OPENING_PROJECTION op01 False op01 /hypotheses/opening_candidates/0 ['f_opening_probe']
```

即 packet ref 本身无 `observation_id`，但 entity id=`op01`，源 observation id=`op01`，合法 finding 仍按当前消费者完成校验并进入 `pending_findings`。若未来消费者要直接从 ref 恢复 pixel witness/native handle，应另行扩 schema；当前不能以未来未存在的读法判缺陷。

### 3.3 packet 平行推导会否分叉、是否静默

**当前没有分叉；若 helper 漏推累计，生产实现会响亮 `stale_packet`，不会静默成功。**

三轮 helper response 的 packet hash 与生产 loop 的 `RoundRecordV1.packet_hash` 逐轮相等：

```text
PACKET_DERIVATION [(True, '87f300236ded', '87f300236ded'),
                   (True, '1132183d9c38', '1132183d9c38'),
                   (True, '1c6dbdaf6eb6', '1c6dbdaf6eb6')] success
```

故意在第三轮平行推导里只保留第二轮决定、漏掉第一轮累计：

```text
PACKET_DIVERGENCE_PROBE 9ede33f78061 stale_packet False ()
```

风险是测试 helper 与生产规则重复、未来变更时可能造成假红和维护成本；但由于 response 必须绑定生产 packet hash，分叉不能静默冒充成功。无需阻断，也不强制再加一把复制实现的锁。

## 4. §四三条读数

### 4.1 N-2 · 非集合 decision hash 的影响面

**影响面变大，但仍不阻断。** B-1 后 geometry-changing round 不能直接成功，必须再建下一 packet；`previous_decision_hashes` 进入 packet hash，因此 item array 的表示顺序现在直接改变下一 packet 身份和固定响应回放链。

```text
N2_SUCCESS_AB 3143381cb3d2 bf247cd2c5ea success d0d3c3ba2744
N2_SUCCESS_BA 245ccc3149ca 62b27c059b54 success d0d3c3ba2744
N2_REORDER False no_progress False ('item_66eb5a8f54d6112db76a1f1b75a83889b6ca86c330eb9cf401e5d34c961c0b4d', 'item_89897de52e872552d28d41c0fd4d8aa438a6fe289e75247d299a4d9a728446a4')
```

AB/BA 的 decision hash 和 packet hash 不同，但两条合法完整路径仍 success，final provisional 完全相同。当前后果仍是 lineage/replay/exit-reason 对表示顺序敏感，没有观测到错误 geometry 被成功放行；维持不阻断，建议按 item/action/candidate/reason canonical sort。

### 4.2 N-3 · 锁文案未修的边界

**认同“不在本轮四条阻断返工边界”的判断。** 上一轮 N-3 本来就是不阻断建议，返工边界明确只要求 B-1…B-4；未改不构成漏返工。原文案若声称能拦“任何真实 wiring edge”仍不准确，dynamic/lazy import 反例仍成立，登记 F-4。

### 4.3 锁 30→73：五条变异实测

不是用 73 这个数代替语义。抽取的五个对象分别对着五个承重不变量；其中第 3 个还暴露了端到端夹具量到并集的问题。

| # | 摘掉的不变量 | 定向命令（均 `-n 6`） | 实测输出原文 | 对着谁达标 |
|---|---|---|---|---|
| 1 | 删除 B-1 provisional 等式 | `pytest -n 6 tests/test_o22m56_decision_loop.py::test_select_round_cannot_succeed_on_its_own_accept -q` | `FAILED ... AssertionError: assert 'success' == 'round_budget_exhausted'`；`1 failed in 5.23s` | accept 是否审过最终 geometry，不是“有 accept”条数。 |
| 2 | 累计改回只传本轮 bindings | `pytest -n 6 tests/test_o22m56_decision_loop.py::test_two_items_decided_across_two_rounds_both_survive -q` | `FAILED ... AssertionError: assert 'stale_packet' == 'success'`；`1 failed in 5.93s` | 前轮决定是否进入后轮编译，不是 round record 是否有两个 item。 |
| 3 | strict `pairs_selection_absent(walls)` 改为 allow | 先跑 end-to-end，再跑 `pytest -n 6 tests/test_o22m56_decision_loop.py::test_debt_policy_cell_by_cell -q` | end-to-end：`1 passed in 6.51s`；逐格：`FAILED ... assert False is True`，`1 failed, 29 passed in 5.18s` | end-to-end 对着两种 debt 的并集；真正对着该单格达标的是逐格锁。 |
| 4 | 跳过 opening_claims 入表 | `pytest -n 6 tests/test_o22m56_decision_loop.py::test_packet_indexes_real_openings_with_kind -q` | `FAILED ... assert {} == {'op01': 'opening'}`；`1 failed in 5.47s` | packet 是否真的含源 bundle 的 opening，不是 bundle 自身 opening 条数。 |
| 5 | 删除 `opening_entity_id→opening` kind 格 | `pytest -n 6 tests/test_o22m56_decision_loop.py::test_wall_id_cannot_impersonate_an_opening -q` | `FAILED: DID NOT RAISE DecisionLoopError`；`1 failed in 8.25s` | opening 角色是否为 opening kind，不是 id 是否存在于 packet。 |

五次变异后均立即执行：

```bash
git checkout -- src/agent/correction/decision_executor.py
git status --porcelain -- src/agent/correction/decision_executor.py
```

每次均输出 `<无输出；已还原>`。

当前树定向回归：

```text
$ pytest -n 6 tests/test_o22m56_decision_loop.py -q
73 passed in 11.75s

$ pytest -n 6 tests/test_o22m1_as_drawn_producer_types.py -q
53 passed in 4.72s
$ pytest -n 6 tests/test_o22m2_evidence_contract.py -q
33 passed in 7.28s
$ pytest -n 6 tests/test_o22m3_evidence_adapters.py -q
21 passed in 7.95s
$ pytest -n 6 tests/test_o22m4_wall_compiler.py -q
27 passed in 9.92s
```

模块 4 的 27 是当前冻结树读数：`a13120d` 在该测试文件新增 5 条；返工执行档里的 22 是更早树读数，不记为本模块回归。

## 5. 可 copy-paste 的复现命令

### 5.1 开工前提

```bash
git log --oneline -1
sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
git diff faf071c..f9bac1e -- \
  src/agent/correction/decision_schema.py \
  src/agent/correction/decision_executor.py \
  tests/test_o22m56_decision_loop.py
git diff --stat a13120d..f9bac1e
```

实测：HEAD=`f9bac1e`；哨兵=`58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43`；三文件 diff 无输出；`a13120d..f9bac1e` 仅 9 份 md。

### 5.2 四个单点逆变 patch

每次只应用其中一个 patch，运行 §2 对应 probe/§4 对应单测，然后立即 checkout；不得合并应用。

```diff
# M1 / B-1
-        and packet.provisional_geometry == compilation.content_sha256
```

```diff
# M2 / B-2
-            artifact, profile=profile, decisions=tuple(accumulated)
+            artifact, profile=profile, decisions=tuple(bindings)
```

```diff
# M3 / B-3
-            _debt_blocks_success(
-                debt_info[debt_id][0], debt_info[debt_id][1], profile
-            )
+            debt_info[debt_id][0] == "ambiguous_face"
```

```diff
# M4a / B-4 opening 入表
-    for opening in bundle.bundle.opening_claims:
+    for opening in ():
```

```diff
# M4b / B-4 candidate membership（单点实测不会复现接收，见 F-2）
-    for name in ("opening_entity_id", "candidate_wall_entity_ids"):
+    for name in ("opening_entity_id",):
```

```bash
git checkout -- src/agent/correction/decision_executor.py
git status --porcelain -- src/agent/correction/decision_executor.py
```

### 5.3 第③格同形输入与 B-4 closure probes

```bash
# B-1：不同 face ids / 坐标 / span / spacing 的一墙输入
python - <<'PY'
import runpy
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx = ns['dx']
doc = ns['_doc'](
    [ns['_face']('GX1','col','x',340,[[20,160]]),
     ns['_face']('GX2','col','x',354,[[20,160]])],
    [ns['_pair']('GX1','GX2',14.0)])
art = ns['_adapt'](doc, 'gpt_b1_new_carrier')
_, p0 = ns['_packet_round0'](art)
resp = ns['_select'](
    p0.open_items[0].item_id, p0, reason='gpt_new_carrier')
out = dx.run_decision_loop(art, responses=(resp,))
print('B1_SAME_SHAPE', out.exit_reason, out.success,
      p0.provisional_geometry[:12], out.final_provisional_sha256[:12],
      out.residual_open_item_ids)
PY
```

```bash
# B-2：三堵墙分三轮决定，第四轮 accept
python - <<'PY'
import runpy
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx, wc = ns['dx'], ns['wc']; Response = ns['CorrectionDecisionResponseV1']
faces = [
 ns['_face']('A1','col','x',100,[[10,60]]),
 ns['_face']('A2','col','x',112,[[10,60]]),
 ns['_face']('B1','col','x',220,[[70,130]]),
 ns['_face']('B2','col','x',232,[[70,130]]),
 ns['_face']('C1','row','y',360,[[140,210]]),
 ns['_face']('C2','row','y',372,[[140,210]]),
]
pairs = [ns['_pair']('A1','A2',12.0),
         ns['_pair']('B1','B2',12.0),
         ns['_pair']('C1','C2',12.0)]
art = ns['_adapt'](ns['_doc'](faces, pairs), 'gpt_b2_three_rounds')
responses=[]; decisions=[]; hashes=[]
for idx in range(3):
    comp = wc.compile_wall_ir(art, decisions=tuple(decisions))
    packet = dx.build_decision_packet(
        comp, bundle=art, round_index=idx,
        previous_decision_hashes=tuple(hashes))
    item = sorted(packet.open_items, key=lambda i: i.item_id)[0]
    resp = ns['_select'](item.item_id, packet, reason=f'gpt_round_{idx}')
    responses.append(resp); hashes.append(dx.decision_hash(resp))
    d = resp.item_decisions[0]
    decisions.append(wc.FixedDecisionV1(
        item_id=d.item_id, candidate_id=d.candidate_id))
comp = wc.compile_wall_ir(art, decisions=tuple(decisions))
packet = dx.build_decision_packet(
    comp, bundle=art, round_index=3,
    previous_decision_hashes=tuple(hashes))
responses.append(Response(
    packet_hash=packet.packet_hash,
    whole_building_review={'verdict':'accept'}))
out = dx.run_decision_loop(art, responses=tuple(responses))
print('B2_SAME_SHAPE', out.exit_reason, out.success,
      [r.selected_item_ids for r in out.rounds],
      out.residual_open_item_ids, len(out.rounds))
PY
```

```bash
# B-3：walls present 但合法零产出，不借用 pairs-absent 载体
python - <<'PY'
import runpy
m2 = runpy.run_path('tests/test_o22m2_evidence_contract.py')
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx = ns['dx']; Response = ns['CorrectionDecisionResponseV1']
art = m2['_empty_artifact']().model_copy(deep=True)
art.bundle.evidence_debts.append(m2['EvidenceDebtV1'](
    debt_id='debt_gpt_zero_walls', kind='zero_payload_channel',
    channel='walls', description='walls adapter ran and returned no claims'))
art = m2['_refinalize'](art)
comp = dx.compile_wall_ir(art, profile='strict')
packet = dx.build_decision_packet(comp, bundle=art, round_index=0)
out = dx.run_decision_loop(
    art, profile='strict', responses=(Response(
        packet_hash=packet.packet_hash,
        whole_building_review={'verdict':'accept'}),))
print('B3_SAME_SHAPE', out.exit_reason, out.success,
      out.residual_open_item_ids,
      [(d.kind,d.channel) for d in art.bundle.evidence_debts])
PY
```

```bash
# B-4：原虚构 candidate + 自找的“真实 opening 冒充 candidate wall”
python - <<'PY'
import runpy
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx = ns['dx']
art, packet = ns['_opening_packet'](); walls = ns['_packet_wall_ids'](packet)
for label, candidates in (
    ('B4_CURRENT', walls + ['wall_invented_outside_packet']),
    ('B4_SAME_SHAPE', ['op01']),
):
    response = ns['_opening_host_response'](
        packet, opening_id='op01', candidate_ids=candidates)
    try:
        dx.run_decision_loop(art, responses=(response,))
    except dx.DecisionLoopError as exc:
        print(label, exc.code, exc.context)
    else:
        print(label, 'ACCEPTED')
PY
```

### 5.4 定向测试

```bash
pytest -n 6 tests/test_o22m56_decision_loop.py -q
pytest -n 6 tests/test_o22m1_as_drawn_producer_types.py -q
pytest -n 6 tests/test_o22m2_evidence_contract.py -q
pytest -n 6 tests/test_o22m3_evidence_adapters.py -q
pytest -n 6 tests/test_o22m4_wall_compiler.py -q
```

## 6. 哨兵两次读数 + 交件前状态

开工前：

```text
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
```

交件前：

```text
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
```

交件前 `git status --porcelain`：

```text
?? AI_agent/logs/experiments/2026-09-01b_f156v2_measurements/
?? AI_agent/logs/reviews/verdict/2026-09-01b_o22m56v2_rework_crossreview_gpt.md
```

其中 `src/agent/correction/` 与 `tests/` 必须无输出；本席所有逆向变异均已还原。并发席位若留下其它路径，按 v2 §六只如实列出，不归本模块。

## 7. 复核单写错处

**无 A 层题错。** v2 已正确修复上一版不可执行的历史样本要求，三项冻结前提全部成立。

有一处非阻断的表达边界：§二把每条阻断的第①格写成“返工那一处”单点逆变后必须复现；B-4 的 candidate closure 返工实际增加 membership 与 entity-kind 两道独立门，任一单点退回都由另一门继续拒绝。严格遵守“不许量并集”时，不能同时满足“单点”与“必须复现整个旧接收”。本报告按 v2 自己要求记录为重要发现，没有为凑三格而做双点回退。
