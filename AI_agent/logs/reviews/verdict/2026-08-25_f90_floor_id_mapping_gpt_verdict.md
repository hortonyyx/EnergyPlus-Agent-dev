# GPT 跨家族复核裁决 · 楼层 id 映射层（F-90）

- **被审 commit**：`3f6731f`（已随分支合入 `main`）　**审阅方**：**GPT 家族**（`gpt-5.6-sol` / effort `xhigh`）
- **日期**：2026-08-25（裁决落库 2026-08-26 会话）
- 请求单 → [`../request/2026-08-25_f90_crossreview_gpt.md`](../request/2026-08-25_f90_crossreview_gpt.md) ·
  派工单 → [`../request/2026-08-25_f90_floor_id_mapping_dispatch.md`](../request/2026-08-25_f90_floor_id_mapping_dispatch.md) ·
  施工报告 → [`../execution/2026-08-25_f90_floor_id_mapping_construction_report.md`](../execution/2026-08-25_f90_floor_id_mapping_construction_report.md)

## ⭐ 结论：**REJECT**

> 处置按请求单预先约定：**在 `main` 上另开修复单，⛔ 不回退历史**。

## 〇、orchestrator 的独立复验（⛔ 不照抄裁决）

复核方只审不改：主树 `git status --porcelain` 为空、`git worktree list` 无残留
（它的 `/tmp/f90-gpt-review` 已 `remove --force`）。orchestrator 亲自复跑了两条最关键的：

**① 阻断 finding 1（第 6 处）—— 复现成功，数字逐位相同**：

```text
target_floor_ids ['F1']
obs_floor_ids ['f1']
same_geometry True
before [('extra',4.0)×4, ('miss',4.0)×4]
after  [('complete',4.0)×4]
```

⇒ **同一份几何，只把楼层名从 `f1` 翻成 `F1`，就从「16 m 多画 + 16 m 漏画」变成「16 m 全对」。**

**② 阻断 finding 4（`src:<64hex>` locator 被错拒）—— 代码层坐实**：
[`window_sources.py:952-957`](../../../../src/agent/correction/window_sources.py#L952) 白纸黑字写着
**两种合法形式**（`src:<64hex>` 直通 / `<view>/<obs>`），而新映射器
[`score_service.py:200`](../../../../src/agent/judge/score_service.py#L200) 一律 `split("/", 1)[0]`
⇒ 合法的 hash 形式整串被当成 `input_id`，落进 `window_host_source_not_a_registered_plan_input`。

**③ ⭐⭐ 对 orchestrator 自己那条「最不确定」的回答**：请求单第 2 条问「只有一条判据 eligible、
且那条全 fail，算不算真判出分」。复核方的答案比我猜的更糟——**那条 fail 本身就是第 6 处缺陷的读数**，
不是产物的错。⇒ 我拿到的十判据读数，**九条没判 + 一条判的是我自己的 bug**。

---

## 以下为复核方裁决正文（逐字，未改）

REJECT

复现统一前置：

```bash
git worktree add --detach /tmp/f90-gpt-review 3f6731f
cd /tmp/f90-gpt-review
# 全部实验完成后：
git worktree remove --force /tmp/f90-gpt-review
```

所有改动实验均在 `/tmp` worktree；主树最终为 clean，未 add/commit/push/stash/切分支。

## 一、五条重点

### 1. 「同根因 5 处」是否成立

结论：列出的五个语义消费者都真实存在，第 4 处影响也真实；但"共 5 处"作为穷举结论不成立，至少漏了第 6 处 plan-segment matcher。

五处代码证据：

1. plan source：`src/agent/judge/score_service.py:431-464`
2. facade span：`src/agent/judge/score_service.py:149-180`
3. absence `floor_refs`：`src/agent/judge/opening_claim_score.py:313-329`
4. opening assignment：`src/agent/judge/opening_claim_score.py:340-364`
5. zone mapping：`src/agent/judge/opening_claim_score.py:130-163`

第 3、4 处实际共用 `score_service.py:464` 的 `OpeningObservation.floor_id` 转换，并非两段独立补丁。

#### 第 4 处单独摘除实验

实验中另外显式中和两个独立问题：

- 把 correction plan segments 的 floor id 映到 `F1`，避免下述第 6 处干扰；
- 给 assignment 传入合法 binding bridge `plan → gt-plan`，避免真实 source-ref 问题干扰。

使用原测试生成的合法 B5 proof、bindings 和 `f1`/`F1` 异名 fixture。对照摘除只做：

```diff
-from dataclasses import dataclass
+from dataclasses import dataclass, replace
@@
-floor_id=product_floor_to_gt_floor[window.floor_id]
+floor_id=window.floor_id
@@
-unmatched = opening_assignment.unmatched_observations
+unmatched = tuple(
+    replace(item, floor_id=product_floor_to_gt_floor[item.floor_id])
+    if item.floor_id in product_floor_to_gt_floor else item
+    for item in opening_assignment.unmatched_observations
+)
```

最后一段专门保留第 3 处 absence 修复，因此只摘掉 assignment 的第 4 处效果。

实测基线：

```text
BASELINE c2_scored extras 0
boundary_complete pass 16.0 0.0 16.0
windows_placed pass 1.0 0.0 1.0
window_plan_geometry pass 2.0 0.0 2.0
plan_claims [('existence', 1.0, 0.0, 1.0),
             ('host', 1.0, 0.0, 1.0),
             ('along', 1.0, 0.0, 1.0),
             ('width', 1.0, 0.0, 1.0)]
```

单独摘掉第 4 处：

```text
ABLATE_4 c2_scored extras 1
boundary_complete pass 16.0 0.0 16.0
windows_placed fail 0.0 1.0 1.0
window_plan_geometry fail 0.0 2.0 2.0
plan_claims [('existence', 0.0, 1.0, 1.0),
             ('host', 0.0, 1.0, 1.0),
             ('along', 0.0, 1.0, 1.0),
             ('width', 0.0, 1.0, 1.0)]
```

判断：

- "所有 window plan claims 静默变成 miss"属实；
- 若"全部 miss/判零"指整份十判据，则是夸大：`boundary_complete` 仍为 pass；
- 施工原 fixture 本身没有证明这一点，以上增强对照才证明。

#### 漏掉的第 6 处

`score_typed_attempt` 在 floor bridge 尚未建立前就调用 plan matcher：`src/agent/judge/score_service.py:389`；bridge 到 `:431` 才生成。matcher 仍直接比较字符串：

- `src/agent/judge/segment_score.py:1751`
- `src/agent/judge/segment_score.py:1895`

复现：

```bash
python - <<'PY'
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from tests import test_c2_b5_parent_and_verts as t
from src.agent.judge.segment_score import (
    extract_correction_plan_segments, extract_gt_plan_segments, match_plan_segments,
)
from src.agent.judge.score_config import load_judge_score_config

with TemporaryDirectory(dir="/tmp") as td:
    b = t._bundle(Path(td))
    gt = t._f90_gt(b.result.geom, floor_id="F1")
    targets = extract_gt_plan_segments(gt)
    obs = extract_correction_plan_segments(b.result.geom)
    cfg = load_judge_score_config("src/configs/judge_score.yaml")
    before, _ = match_plan_segments(targets=targets, observations=obs, config=cfg)
    after, _ = match_plan_segments(
        targets=targets,
        observations=tuple(replace(x, floor_id="F1") for x in obs),
        config=cfg,
    )
    print("same_geometry", [(x.p1,x.p2) for x in targets] == [(x.p1,x.p2) for x in obs])
    print("before", [(x.status,x.eligible_units) for x in before])
    print("after", [(x.status,x.eligible_units) for x in after])
PY
```

输出：

```text
same_geometry True
before [('extra', 4.0), ('extra', 4.0), ('extra', 4.0), ('extra', 4.0),
        ('miss', 4.0), ('miss', 4.0), ('miss', 4.0), ('miss', 4.0)]
after [('complete', 4.0), ('complete', 4.0),
       ('complete', 4.0), ('complete', 4.0)]
```

同一几何仅改 floor id 后从 `16m extra + 16m miss` 变为 `16m complete`。因此 F-90 至少有第 6 处未修。

### 2. 十判据读数是否公允

结论：不算"真的判出分"，属于另一种"没判"。

复现施工 fixture：

```bash
python - <<'PY'
# 用 tests/test_c2_b5_parent_and_verts.py::_bundle/_f90_gt/_f90_bindings
# 原样调用 score_typed_attempt，并打印 claim_summaries/score_criteria。
PY
```

实测关键输出：

```text
kind c2_scored extras 0 claims 7 segments 8
existence denominator_units=0.0 na_reasons={'unobserved': 1}
host      denominator_units=0.0 na_reasons={'unobserved': 1}
along     denominator_units=0.0 na_reasons={'unobserved': 1}
width     denominator_units=0.0 na_reasons={'unobserved': 1}

boundary_complete True  fail            0.0 32.0 32.0
windows_placed    False not_applicable  0.0  0.0  0.0
其余八条          False not_applicable  0.0  0.0 0.0
```

原因有两层：

- `_f90_gt` 明确构造 `source_refs=()`，见 `tests/test_c2_b5_parent_and_verts.py:1455-1472`，所以所有 opening claims 都是 `unobserved`；
- 唯一 eligible 的 `boundary_complete` 又因上述第 6 处 floor-id 直比被错误判为 `0/32`。

锁只断言：

```python
assert result.payload.kind == "c2_scored"
assert result.payload.extras == ()
```

见 `tests/test_c2_b5_parent_and_verts.py:1512-1514`，没有断言任一 criterion eligible/pass，也没有断言 opening match/claim denominator。`c2_scored` 只说明组装函数返回了 payload，不能替代"判出分"。

### 3. 四个边界是否响亮失败

结论：四个都确实抛 `ScoreContractError`，没有返回默认值。

复现：

```bash
python - <<'PY'
from types import SimpleNamespace as NS
from src.agent.correction.claims import CLAIM_HOST
from src.agent.judge.score_schema import ScoreContractError
from src.agent.judge.score_service import _derive_window_floor_plan_sources

def w(wid, floor, ids):
    return NS(id=wid, floor_id=floor,
              provenance={} if ids is None else {CLAIM_HOST: NS(source_ids=ids)})
def bs(*ids):
    return NS(bindings=tuple(NS(kind="plan", input_id=x) for x in ids))

cases = {
 "missing": (NS(windows=(w("w1","product_F1",None),)), bs("plan_a")),
 "ambiguous": (NS(windows=(w("w1","product_F1",
                              ("plan_a/W1","plan_b/W1")),)), bs("plan_a","plan_b")),
 "unregistered": (NS(windows=(w("w1","product_F1",("ghost/W1",)),)), bs("plan_a")),
 "contradictory": (NS(windows=(
     w("w1","product_F1",("plan_a/W1",)),
     w("w2","product_F1",("plan_b/W2",)))), bs("plan_a","plan_b")),
}
for name, (geometry, bindings) in cases.items():
    try:
        print(name, _derive_window_floor_plan_sources(
            geometry=geometry, score_bindings=bindings))
    except ScoreContractError as exc:
        print(name, "RAISED", exc.code, exc.gate_id, exc.context)
PY
```

输出：

```text
missing RAISED score_view_binding_invalid scoring.view_bindings
 {'reason': 'window_host_claim_missing_source_ids', ...}

ambiguous RAISED score_view_binding_invalid scoring.view_bindings
 {'reason': 'window_host_claim_ambiguous_source',
  'candidate_inputs': ['plan_a', 'plan_b'], ...}

unregistered RAISED score_view_binding_invalid scoring.view_bindings
 {'reason': 'window_host_source_not_a_registered_plan_input',
  'input_id': 'ghost', ...}

contradictory RAISED score_view_binding_invalid scoring.view_bindings
 {'reason': 'floor_id_maps_to_multiple_plan_inputs',
  'input_ids': ['plan_a', 'plan_b'], ...}
```

对应实现为 `src/agent/judge/score_service.py:184-218`。本条通过。

### 4. 「立面不需要处理」是否成立

结论：就 F-90 的 `WindowV3.floor_id → GT floor_id` 映射而言，成立；但"从不比较 window.floor_id"若按字面理解则过宽。

复现检索：

```bash
rg -n "window\.floor_id|observed\.floor_id|observation\.floor_id" \
  src/agent/judge/elevation_score.py \
  src/agent/judge/score_service.py \
  src/agent/judge/opening_claim_score.py
```

关键输出：

```text
opening_claim_score.py:63: segment.floor_id == window.floor_id
opening_claim_score.py:81: item.id == window.floor_id
opening_claim_score.py:363: target.floor_id ... != observed.floor_id ...
score_service.py:464: floor_id=product_floor_to_gt_floor[window.floor_id]
elevation_score.py:106: floor_id=observation.floor_id
```

`opening_claim_score.py:63,81` 的比较发生在同一 product geometry 内，是合法的 product/product 比较；`elevation_score.py:95-107` 只校验 input binding/facade 并透传 typed observation 的 floor id，不接触 `WindowV3`。

此外 correction geometry 分支在 `score_service.py:443-468` 把 WindowV3 只构造成 `channel="plan"` 的 observation；elevation typed normalization 属于 `geometry is None` 的 reading 路径。没有发现把 correction `window.floor_id` 与 `ElevationScoreViewBindingV1.floor_ids` 直接比较的路径。

因此 F-89 与 F-90 的范围划分没有因立面 floor-id 比较而划错；但评分侧 facade resolver 实际是 floor + family + interval containment，并非仅凭"指纹"。

### 5. F-99 的 0.12m 归因

结论：8/16 facade span 不归位及约 0.12m 缺口确实在正确 floor bridge 已建立后仍存在，和楼层 id 映射独立；但它不是修完本单后的唯一剩余阻塞。

复现：

```bash
python - <<'PY'
from pathlib import Path
from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.judge.score_schema import (
    JudgeScoreViewBindingsV1, load_score_gt_identity,
)
from src.agent.judge.score_service import (
    _derive_window_floor_plan_sources, _resolve_facade_product_to_gt,
)

run = Path("case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0")
geom = CorrectedGeometryV3.model_validate_json(
    (run/"1_correction/attempts/001/output.json").read_text())
_, gt = load_score_gt_identity(
    Path("case_tests/test_baseline/gt/sm25-L_anchor/gt.json"))
bindings = JudgeScoreViewBindingsV1.model_validate_json(
    (run/"_run/judge_score_bindings.json").read_text())

floor_source = _derive_window_floor_plan_sources(
    geometry=geom, score_bindings=bindings)
i2g = {x.input_id:x.floor_id for x in bindings.bindings if x.kind == "plan"}
bridge = {floor:i2g[source] for floor,source in floor_source.items()}
resolved = _resolve_facade_product_to_gt(
    geometry=geom, gt=gt, product_floor_to_gt_floor=bridge)
print("bridge", bridge)
print("facades", len(geom.facade_segments),
      "resolved", len(resolved),
      "unresolved", len(geom.facade_segments)-len(resolved))
PY
```

输出：

```text
bridge {'floor_1': 'F1', 'floor_2': 'F2'}
facades 16 resolved 8 unresolved 8
```

逐段最近 GT 区间输出包括：

```text
North product (14.88,24.89) gt (15.00,25.00) outside 0.120000...
South product (0.12,5.13)   gt (0.00,5.00)   outside 0.130000...
East  product (5.88,19.88)  gt (6.00,20.00)  outside 0.120000...
West  product (0.12,14.12)  gt (0.00,14.00)  outside 0.120000...
```

两层相同，共八段。产物证据见：

- `case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0/1_correction/attempts/001/output.json:4525-4572`
- 同文件 `:4641-4687`
- GT 对应区间在 `case_tests/test_baseline/gt/sm25-L_anchor/gt.json:1`

正确 bridge 下仍发生几何包含失败，故 0.12m 不是 F-90 残留。直接调用当前 `score_typed_attempt` 的真实 case 实测：

```text
ScoreContractError score_product_segment_unresolved
gate=scoring.matching context={'source_view_id': '1f_view'}
```

但第 6 处 plan matcher、source-view bridge 和缓存身份问题仍会在 F-99 之后继续阻塞，故不能称 F-99 为唯一剩余缺陷。

## 二、验收判据

### 1. 全量

命令：

```bash
python -m pytest -n auto
```

实测：

```text
1 failed, 3018 passed, 13 xfailed, 211 warnings in 335.63s
```

唯一失败：

```text
FAILED tests/test_zone_agent.py::test_zone_agent_creates_two_zones
openai.OpenAIError: The api_key client option must be set ...
```

环境核验：

```bash
OPENAI_API_KEY=unset
DEEPSEEK_API_KEY=unset
```

失败点为 `tests/test_zone_agent.py:30`，与任务书已知环境坑完全一致；不记作 `3f6731f` 回归。排除该环境项后，全量代码回归绿。

### 2. 范围

命令：

```bash
git diff-tree --no-commit-id --name-only -r 3f6731f
```

输出：

```text
src/agent/judge/opening_claim_score.py
src/agent/judge/score_service.py
tests/test_c2_b5_parent_and_verts.py
tests/test_judge_identity_metric.py
```

范围判据通过；未碰 pipeline、交接契约、validator、GT 或 scripts。

### 3. 锁能变红

绿色：

```bash
python -m pytest -q tests/test_c2_b5_parent_and_verts.py -k f90
```

```text
2 passed in 7.48s
```

两份涉及文件全跑：

```bash
python -m pytest -q \
  tests/test_c2_b5_parent_and_verts.py \
  tests/test_judge_identity_metric.py
```

```text
100 passed in 7.47s
```

在临时 worktree 将新 bridge 恢复为旧 `plan_sources.get(window.floor_id)` 后：

```text
FF

test_f90_window_floor_id_and_gt_floor_id_are_independent_namespaces
ScoreContractError: score_view_binding_invalid at scoring.view_bindings

test_f90_window_without_plan_host_reference_fails_closed_not_silently
AssertionError: None == 'window_host_claim_missing_source_ids'
context == {'floor_id': 'f1'}

2 failed
```

红的方向正确：正向锁重新命中旧崩溃；负向锁证明旧实现没有结构化 reason。但锁的断言内容仍不足以证明"真的判出分"，见阻断 finding。

## 三、必答

### 施工上报的两条「派工方题错」

1. "派工单只点名 1 处，因此题错"：不认同。派工单明确写了候选清单可能不完备，并授权继续找；发现更多消费者不是推翻派工前提。更重要的是，施工自己的"五处"仍漏了第 6 处。

2. "修好 F-90 就能让 sm25 判出分"的前提不成立：认同事实，不认同用它豁免验收的处置。F-99 的独立 0.12m 缺口确实存在；这应导致停下上报/验收未满足，而不是用自造 fixture 替代派工单明确点名的真实 case。

### 是否有第 3 条

有：派工候选暗含"合法 host `source_ids` 总能按 `<input_id>/<observation_id>` 拆出 input id"，该前提不完整。

`src/agent/correction/window_sources.py:953-982` 明确允许两种合法形式：

- `<expected_output_id>/<observation_id>`
- 已解析的 `src:<64hex>` locator

而新 mapper 在 `src/agent/judge/score_service.py:200` 一律 `split("/", 1)[0]`。实测一个带合法 `src:<hash>` host 引用的 B5 bundle 成功生成 `VerifiedWindowHostProof`，随后 scorer 却拒绝：

```text
B5_PROOF VerifiedWindowHostProof
host_source_ids ['src:d2cf...3009']

SCORER_RAISED ScoreContractError score_view_binding_invalid
{'reason': 'window_host_source_not_a_registered_plan_input',
 'input_id': 'src:d2cf...3009'}
```

这不是坏输入，而是当前 B5 明示支持的兼容形式。映射必须利用已验证 proof/catalog 将 locator 解析回 source input，不能把 hash 当 input id。

### 自造 fixture 达成、真实 case 未达成，算满足还是绕过

直说：算绕过，不满足验收判据。

派工单要求的是"跑 sm25 那份现成产物、十判据有实际结果"。真实 case 当前仍无 criterion；施工 fixture 又只有一条 eligible 且错误全 fail。自造 fixture 可作为单元级补充证据，不能替代被明确点名的真实验收对象，也不能把"停报"改写成"验收通过"。

## Findings

### 阻断

1. **同根因第 6 处未修：plan segment floor namespace。**
   位置：`src/agent/judge/score_service.py:389,431`；`src/agent/judge/segment_score.py:1751,1895`。
   复现：见 §一.1，同几何 `f1/F1` 为 `16m extra + 16m miss`，仅翻译 floor id 后变成 `16m complete`。
   建议：在 plan matching 前建立显式 bridge，并只在 judge normalization boundary 重键 product `PlanSegment.floor_id`；新增锁要求异名 fixture 的 `boundary_complete` 为 pass。

2. **正向锁没有证明"判出分"。**
   位置：`tests/test_c2_b5_parent_and_verts.py:1452-1472,1497-1514`。
   复现：九条 NA，唯一 eligible 的 `boundary_complete=0/32`；测试只断言 `kind` 和 `extras`。
   建议：GT 提供真实 source refs；断言 `windows_placed`、`window_plan_geometry`、`boundary_complete` 均 eligible/pass，并断言 existence/host/along/width denominator 非零、complete 等于 denominator。

3. **correction assignment 没有接 score binding 的 source-view bridge，会在真实 GT refs 上静默 miss。**
   位置：`src/agent/judge/score_service.py:469-470`；`src/agent/judge/opening_claim_score.py:351-364`。正确接法已有先例：`src/agent/judge/reading_typed_score.py:512-534`。
   复现：

   ```text
   target_source_refs ['gt-plan'] product_source plan
   without_binding_bridge matched 0 target_miss 1 observation_unmatched 1
   with_binding_bridge    matched 1 target_miss 0 observation_unmatched 0
   ```

   建议：correction 路径同样传入 `input_id → gt_source_view_ids`；锁中禁止 `source_refs=()` 绕过该过滤。

4. **合法 `src:<hash>` host reference 被新 mapper 错拒。**
   位置：`src/agent/correction/window_sources.py:953-982`；`src/agent/judge/score_service.py:184-211`。
   复现：见"三、第 3 条"，B5 proof 成功、scorer 报 unregistered plan input。
   建议：从已复验的 `window_host_proof/window_resolver_inputs` catalog 解析 locator；同时锁住 human-readable 与 hashed 两种合法形式。

5. **评分语义改变但缓存 identity 未改变，旧 sidecar 会继续命中。**
   位置：`src/agent/judge/score_service.py:269-278`；`src/agent/judge/score_schema.py:1665-1691`；`scripts/tool_scripts/run_stage.py:2176-2181`。
   实测真实 R0：

   ```text
   live       not_applicable unsupported_view_contract
   cache_hit  True
   cached     rejected score_view_binding_invalid
   same_identity True
   ```

   即 live scorer 已走到 F-99，但官方 run-stage 会保留修前的 `score_view_binding_invalid` sidecar。
   建议：给 correction floor/source normalization 增加版本化 helper identity，或提升相应 scorer helper/schema；新增旧 sidecar 必须 cache miss 的回归锁。

6. **派工单最硬的真实-case 验收未满足。**
   位置：真实产物 `.../run_2026-08-25_c2_rescore_R0/1_correction/attempts/001/output.json:4494-4957`。
   复现：直接 scorer 报 `score_product_segment_unresolved`；官方 total boundary 为 `not_applicable unsupported_view_contract`，零 criteria。
   建议：F-99 可另单修，但在 F-99、第 6 处、source-view bridge 及缓存身份收口后，必须重跑同一 accepted product 并贴十判据，而不是再用替代 fixture。

### 不阻断

1. **四个指定失败 reason 都响亮抛错。**
   位置：`src/agent/judge/score_service.py:196-217`。
   处置：保留；补齐四个 reason 的参数化正式测试，目前仅 missing-source 有锁。

2. **F-99 的约 0.12m 几何归因成立。**
   位置：`src/agent/judge/score_service.py:171-178`；真实产物 `output.json:4525-4687`。
   处置：独立修复，不以容差遮盖；但它仍是"真实 case 判出分"验收阻塞。

3. **不需要给 correction WindowV3 再做 elevation-binding floor 映射。**
   位置：`src/agent/judge/elevation_score.py:80-107`；`src/agent/judge/score_service.py:443-468`。
   处置：维持 F-89/F-90 边界；文档避免使用"从不比较 floor_id"这种过宽表述。

4. **提交范围符合派工限制。**
   复现：`git diff-tree --no-commit-id --name-only -r 3f6731f` 仅四个允许文件。
   处置：无需动作。

5. **全量唯一失败是已知凭据环境项。**
   位置：`tests/test_zone_agent.py:30`。
   处置：不记回归；在具备相应密钥的 CI 再确认即可。
