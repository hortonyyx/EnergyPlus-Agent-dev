# ②-2 模块 5+6 · GPT 跨家族复核裁决

- 日期：2026-09-01
- 被审：GLM 家族未提交工作树
- 口径：派工单（含末尾裁决 §七–§十）+ 已过审设计稿 §6.1/§6.2/§6.3/§9.1
- 审阅输入：原始需求、三份被审文件、git diff/status、定向测试与本席独立反例；未读取施工方 execution 自述

## 裁决

**REWORK — 阻断 4 条，不阻断 3 条。**

主控关于题错 #56 的裁决已遵守：finding 候选生成器不归 executor，本裁决不以其缺失为缺陷。拓扑/围合/洞口 host/跨层检查目前未实现，也按主控 §九登记为不阻断；本席验证了实现确实没有伪造这些检查。

阻断原因不是上述已豁免范围，而是当前三拍机制会：用旧 geometry 的 `accept` 放行新 geometry、跨轮丢掉先前决定、把 strict debt 口径缩成仅 `ambiguous_face`、以及让 opening-host finding 越过 packet 实体闭包。

## 阻断项

### B-1 · `accept` 绑定的是执行前 provisional，却被用于放行执行后新 geometry

设计 §6.3 的成功条件要求模型对**同一个 provisional hash**给出总体 `accept`。当前循环先校验 response 绑定当前 packet（`decision_executor.py:494-508`），再用本轮决定重编译为 `nxt`（`:511-518`），最后直接拿同一个 response 的 `accept` 判 `nxt` 成功（`:539-541`）。没有任何门要求 `packet.provisional_geometry == nxt.content_sha256`，也没有在变更后进入下一轮让模型审新 provisional。

独立读数：单墙 packet 的 provisional 前缀为 `8b2f1ff4c97e`，执行选择后的 final 前缀为 `52552c171f9b`，两者不相等，结果却是 `exit_reason=success`。

这不是测试表述分歧：`tests/test_o22m56_decision_loop.py:565-581` 反而把“同轮 select + accept ⇒ success”锁成了预期，直接锁错了 §6.3 的 hash 绑定语义。

### B-2 · 多轮执行不累计既有决定，第二轮会撤销第一轮结果

每轮 `_validate_response` 只生成本轮 `bindings`，随后 `compile_wall_ir(artifact, decisions=tuple(bindings))` 从 frozen artifact 重建（`decision_executor.py:508-516`）。状态中只累计 `previous` decision hashes（`:476-477,536-537`），没有累计 `FixedDecisionV1`；module 4 的编译器也只应用传入的决定。因此下一轮选择第二个 item 时，第一轮选择会消失。

独立读数：两 item 分两轮各选择一次，round records 确实分别记录两个不同 item，但终点为 `round_budget_exhausted`，残余重新出现第一轮已经关闭的 item：

```text
P1_ACCUMULATION round_budget_exhausted
rounds [(item_A,), (item_B,)]
residual (item_A,)
```

这使“仍有 open item 则进入下一轮”的正常多轮路径无法收敛；当前 30 条测试只测了一轮全选或两轮退出，没有一条要求两轮选择最终同时保留。

### B-3 · strict residual debt 被错误收窄为仅 `ambiguous_face`

`_succeeded` 的第四项只检查 residual debt 对应的 kind 是否为 `ambiguous_face`（`decision_executor.py:565-583`），并把所有 `missing_channel` 一概解释为可成功。可是契约的 debt 封闭值域还有 `pairs_selection_absent`、`zero_payload_channel`、`other_known_missing`（`evidence_contract.py:454-461`）；设计 §6.1 又明确规定 pairs selection 缺失应走 `reperception_required`，不能由 correction 自行补墙。

独立反例使用 `pairs=None + pairs_status=ABSENT_NO_MODEL_SELECTION`，两条 face 均诚实记为 non-wall，使 open item 为零。strict 下仍带 `pairs_selection_absent`、`missing_channel(walls)` 等债务，一份空决定 `accept` 被判成功：

```text
P4_STRICT_DEBT_SUCCESS success
open ()
debts [... ('debt_pairs_absent_pairs_debt_probe', 'pairs_selection_absent'),
       ... ('debt_missing_walls_pairs_debt_probe', 'missing_channel')]
```

结论：施工方“strict 不允许的 residual debt = ambiguous_face”这个自定读法**不成立**。不是要求所有 `missing_channel` 无差别阻断；正确实现需要显式的 profile × debt kind/channel policy。至少 `pairs_selection_absent` 与 strict 的 walls 缺失不能沿当前 blanket exemption 成功。

### B-4 · opening-host 的 packet 实体闭包可被绕过，且真实 opening 根本不在 packet

`ReviewOpeningHostEffectV1` 声明了 `opening_entity_id` 与 `candidate_wall_entity_ids`（`decision_schema.py:193-201`），但 `_effect_entities` 只收集 subject/reference/wall-item 和单个 opening id，漏掉全部 `candidate_wall_entity_ids`（`decision_executor.py:353-363`）。因此一个 packet 外虚构 wall id 会被接受并进入 `pending_findings`。

同时 packet builder 的实体表只收 resolved walls、auto-action scope 和 open-item ids（`:153-160`），既没有 opening claims，也没有实体 kind。真实产物实测：

```text
sm25_1f_v2.json openings 85 indexed_openings 0
sm25_2f_v2.json openings 87 indexed_openings 0
sm24_1f_v2.json openings 87 indexed_openings 0
```

另一独立反例把一个真实 packet wall id 冒充 `opening_entity_id`，再给出 `wall_invented_outside_packet` 作为候选 host；executor 无报错并原样携带。故五种 effect 虽在 schema 层可构造，`review_opening_host` 的实体语义在执行层既不能合法使用、又能非法绕过，违反 §6.2“所有 entity/ref 已在 packet 中”及“packet 内 opening id / candidate wall ids”。这与“候选由 opening resolver 生成、不归本单”无关：本项只要求本单已经认领的接收/校验/携带闭包正确。

## 不阻断项

### N-1 · 四类检查未实现，但“未伪装”自称属实

`ConsistencyResultV1.check` 只允许 `collinear_wall_overlap | unshared_tail_coverage`（`decision_schema.py:79-89`）；`run_consistency_checks` 也只返回这两项（`decision_executor.py:192-257`）。独立构造 `check="enclosure"` 得 `literal_error`，证明不存在假绿的 enclosure 名目。

盲区同样真实：一份仅有 1 堵墙、显然不能形成围合的 provisional，两项检查均绿且当前实现可判 success。读数：`checks=['collinear_wall_overlap','unshared_tail_coverage'], walls=1, success=True`。依主控 §九，此项登记、不阻断，随模块 4 扩面另单解决。

### N-2 · no-progress / decision-cycle 的优先级可解释，但 hash 不是“集合”哈希

当前规则是：当前 `item_decisions` hash 已见过则先报 cycle；否则不移动 geometry 连续两轮报 no-progress（`decision_executor.py:505-550`）。这个互斥优先级本身可接受，四种出口也都可达。

但 `decision_hash` 直接 hash 原数组顺序（`:324-332`）。同一批 item/reason 仅反转数组顺序，两个 hash 不同，结果从应有的 repeated decision set 分类成 `no_progress`。独立读数：`P6_REORDER False no_progress`。它仍在第二轮响亮退出、残余未丢，故本轮记不阻断；建议按 item id/action/candidate/reason 做 canonical sort，并明确 whole-building review 是否属于 decision hash，避免 exit reason 被表示顺序替换。

### N-3 · 零接线两锁满足派工字面形状，但可被真实 lazy/dynamic import 同时骗过

当前两份生产源码没有 `import_module`/`__import__`，静态 import 均在白名单，import-time pipeline∪judge 差集也为零，故当前代码确实未接线。

但反例模块保留 allowlisted `evidence_contract` 静态 import，并在函数体用 `importlib.import_module('src.agent.pipeline')`：AST 锁只看到 allowlisted 静态边，import-time 差集仍与 baseline 相等；调用函数后 pipeline 实际进入 `sys.modules`。实测：

```text
L8_DYNAMIC_AST_EXTERNALS ['src.agent.correction.evidence_contract']
L8_DYNAMIC_IMPORT_LOCK_EQUAL True EDGE_AFTER_CALL True
```

因此 `tests/test_o22m56_decision_loop.py:773-829` 证明的是静态/import-time 边，不是任意真实 wiring edge。当前源码无该形态，且派工明确要求的两把锁均已落，记不阻断；锁文案不应再声称“任何新 wiring edge 都会红”。

## §四验收表逐项读数

| # | 裁决 | 本席读数 |
|---|---|---|
| 1 | **PASS** | 新文件测试 30/30；独立把改名后的数值字段 `desired_offset=3.25` 塞入 effect 深层，类型层返回 `extra_forbidden`。递归 response 类型树无 `int/float` leaf。拒绝不依赖字段名。 |
| 2 | **PASS** | 上一轮 hash 回复下一轮得到 `stale_packet`、`success=False`、残余 open item 非空。 |
| 3 | **PASS** | 合法字符串形状但不在 item 候选集的 id 得 `UNKNOWN_RESPONSE_CANDIDATE`；unknown/duplicate item 也响亮。 |
| 4 | **PASS（附 N-2）** | no-progress / decision-hash cycle / stale packet / round-budget exhausted 四夹具均命中；非成功 outcome 均 `success=False` 且有 open/debt/finding 至少一种残余。表示顺序会改变前两者分类，见 N-2。 |
| 5 | **FAIL** | 虽有四个“单项证伪”测试，但 accept/hash 项锁反（B-1），debt 项只测 ambiguous 并漏过 `pairs_selection_absent`（B-3）。 |
| 6 | **FAIL** | 五 kind、逐 kind extra、sixth kind 的 schema 测试均绿；但 opening-host 的 packet 实体闭包失败，且真实 opening 0 个进入 packet（B-4）。 |
| 7 | **PASS** | `git diff 58bb59f -- wall_compiler.py evidence_contract.py evidence_adapters.py window_sources.py | wc -c` = **0**。 |
| 8 | **PASS（附 N-3）** | 交付了差集 + AST 两把指定形状及静态 turn-red 夹具；当前源码零 pipeline/judge 接线。动态边可绕过，见 N-3。 |
| 9 | **PASS** | 同 bundle/response 两次逐字节相同；另以 `PYTHONHASHSEED=1` 与 `999` 两个独立进程运行，均得 outcome hash `0fb3fd8b92dbdea4feecee34c292cf8b8febf0bc663e997a040c5c394a390b13`，JSON 逐字相同。 |
| 10 | **PASS** | `test_o22m56_decision_loop.py`: **30 passed**；模块 1: **53 passed**；模块 2: **33 passed**；模块 3: **21 passed**；模块 4: **22 passed**。均 `pytest -n 4`、exit 0。 |
| 11 | **PASS** | 被审改动路径恰为 3 个未跟踪新文件：`decision_schema.py`、`decision_executor.py`、`test_o22m56_decision_loop.py`；未 add/commit。 |

## 复现命令

### 定向测试（逐文件）

```bash
pytest -n 4 tests/test_o22m56_decision_loop.py -q
pytest -n 4 tests/test_o22m1_as_drawn_producer_types.py -q
pytest -n 4 tests/test_o22m2_evidence_contract.py -q
pytest -n 4 tests/test_o22m3_evidence_adapters.py -q
pytest -n 4 tests/test_o22m4_wall_compiler.py -q
```

### B-1 / B-2 / B-4 与 no-progress/cycle 反例

```bash
python - <<'PY'
import runpy
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx = ns['dx']; Response = ns['CorrectionDecisionResponseV1']
Item = ns['ItemDecisionV1']; Whole = ns['WholeBuildingReviewV1']
Finding = ns['FindingV1']; Opening = ns['ReviewOpeningHostEffectV1']

art = ns['_two_pair_artifact'](); _, p0 = ns['_packet_round0'](art)
ids = sorted(i.item_id for i in p0.open_items)
r0 = ns['_select'](ids[0], p0)
p1 = ns['_round1_packet'](art, r0)
r1 = ns['_select'](ids[1], p1)
out = dx.run_decision_loop(art, responses=(r0, r1))
print('P1_ACCUMULATION', out.exit_reason,
      [r.selected_item_ids for r in out.rounds], out.residual_open_item_ids)

art = ns['_one_pair_artifact'](); _, p0 = ns['_packet_round0'](art)
out = dx.run_decision_loop(
    art, responses=(ns['_select'](p0.open_items[0].item_id, p0),))
print('P2_UNREVIEWED_SUCCESS', out.exit_reason,
      p0.provisional_geometry, out.final_provisional_sha256,
      p0.provisional_geometry == out.final_provisional_sha256)

art = ns['_one_pair_artifact'](); _, p0 = ns['_packet_round0'](art)
item = p0.open_items[0]; wall = item.scope_entity_ids[0]
resp = Response(
    packet_hash=p0.packet_hash,
    item_decisions=ns['_select'](item.item_id, p0).item_decisions,
    whole_building_review=Whole(verdict='findings', findings=(Finding(
        finding_id='f_fake_host', kind='opening_host',
        affected_entity_ids=(wall,),
        requested_effect=Opening(
            kind='review_opening_host', opening_entity_id=wall,
            candidate_wall_entity_ids=('wall_invented_outside_packet',)),
        rationale='probe'),)))
out = dx.run_decision_loop(art, responses=(resp,))
print('P3_FAKE_OPENING_HOST_ACCEPTED',
      out.pending_findings[0].requested_effect.model_dump())

art = ns['_two_pair_artifact'](); _, p0 = ns['_packet_round0'](art)
ids = sorted(i.item_id for i in p0.open_items)
def rejects(packet, reverse=False):
    seq = list(reversed(ids)) if reverse else ids
    return Response(
        packet_hash=packet.packet_hash,
        item_decisions=tuple(Item(item_id=i, action='reject_all',
                                 reason_code='same') for i in seq),
        whole_building_review={'verdict':'accept'})
a = rejects(p0); p1 = ns['_round1_packet'](art, a); b = rejects(p1, True)
out = dx.run_decision_loop(art, responses=(a, b))
print('P6_REORDER', dx.decision_hash(a) == dx.decision_hash(b),
      out.exit_reason)
PY
```

### B-3 strict debt 反例

```bash
python - <<'PY'
import runpy
ns = runpy.run_path('tests/test_o22m56_decision_loop.py')
dx, wc = ns['dx'], ns['wc']
Response = ns['CorrectionDecisionResponseV1']
doc = ns['_doc'](
    [ns['_face']('F01','col','x',100,[[10,100]]),
     ns['_face']('F02','col','x',112,[[10,100]])], [],
    non_wall={'F01':'text','F02':'text'})
doc['hypotheses']['pairs'] = None
doc['hypotheses']['pairs_status'] = 'ABSENT_NO_MODEL_SELECTION'
art = ns['_adapt'](doc, 'pairs_debt_probe')
comp = wc.compile_wall_ir(art, profile='strict')
packet = dx.build_decision_packet(comp, round_index=0)
response = Response(packet_hash=packet.packet_hash,
                    whole_building_review={'verdict':'accept'})
out = dx.run_decision_loop(art, profile='strict', responses=(response,))
print(out.exit_reason, out.residual_open_item_ids,
      [(d.debt_id, d.kind) for d in art.bundle.evidence_debts])
PY
```

### 真实 opening 未进入 packet

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
    packet = build_decision_packet(comp, round_index=0)
    indexed = {e.entity_id for e in packet.entity_to_source_refs}
    print(name, len(openings), len(openings & indexed))
PY
```

### 模块 4 零改动与改动路径

```bash
git diff 58bb59f -- \
  src/agent/correction/wall_compiler.py \
  src/agent/correction/evidence_contract.py \
  src/agent/correction/evidence_adapters.py \
  src/agent/correction/window_sources.py | wc -c
git status --short -- \
  src/agent/correction/decision_schema.py \
  src/agent/correction/decision_executor.py \
  tests/test_o22m56_decision_loop.py
```

## 返工边界

最小返工应只动本单三份被审文件：

1. 累计并重放所有已接受的 fixed decisions，确保多轮决定单调保留；
2. geometry 一旦因决定改变，本轮 review 不得放行新 hash，必须构造下一 packet 再取得对该 hash 的 accept；
3. 把 strict residual debt 改为显式 profile policy，至少封住 `pairs_selection_absent` 与 walls 缺失；
4. packet 收录真实 opening 实体并带实体 kind，opening-host 校验 opening 类型及全部 candidate wall ids 的 packet 成员资格；
5. 为上述四项各补 turns-red 反例，尤其补“两 item 分两轮最终成功”与“select 后必须下一轮 accept 新 hash”。

不要求在本次返工中实现 finding 候选生成器，也不要求补拓扑/围合/洞口 host/跨层四类检查。
