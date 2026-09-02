# 跨家族复核裁决 · F-156 第四轮 + ②-1d 同修（GPT）

- 日期：2026-09-02
- 被审 commit：`bbeab77`
- 开工 HEAD：`cf1bd0d`
- 复核方：GPT 家族
- 裁决：**REWORK**
- 计数：**阻断 2 / 不阻断 0**
- 请求方已登记的 N-1 / N-2：已核实但**不作为新发现重复计数**。

## 一、裁决

### 阻断 1：`excluded > paired` 会把诚实的按阈值排除判红

新增门把所有 exclusion 混成一个数量，包括由请求阈值和 raw cavity 面积独立证明的
`below_request_area_threshold`。这不是 producer 自写 loss，不能当作灌证。实测只在真实 sm25
报告中新增真实低面积 shaft zones，不删除 facts edge、不写 loss：生产阈值为 `5.0 m²`，每个新增
zone 约 `0.0282268 m²`，10 个均被消费端正确认作
`below_request_area_threshold`；但 `plan-F1` 从诚实基线的 `11 paired / 2 excluded` 变为
`11 paired / 12 excluded` 后仍被新增门判红。

结论：1:1 是没有结构依据的领域阈值，疑点 1 **证实为真实假红**。它不能靠把 `>` 改成
`>=` 或换一个百分比修好；至少必须先把独立可证的 by-design threshold exclusions 与
producer 自写的 `registered_ring_loss` 分开。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_crossreview_gpt_probe.py::test_honest_below_threshold_population_is_false_red
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_crossreview_gpt_probe.py::test_honest_below_threshold_population_is_false_red
  /tmp/joint_review_gpt/tests/test_crossreview_gpt_probe.py:243: UserWarning: {'view': 'plan-F1', 'production_threshold_m2': 5.0, 'added_zone_areas_m2': [0.028226799999999955, 0.028226799999999955, 0.028226800000000156, 0.028226800000000156, 0.028226799999999944, 0.028226799999999944, 0.028226800000000114, 0.028226800000000114, 0.028226800000000114, 0.028226799999999268], 'paired': 11, 'baseline_excluded': 2, 'honest_added_excluded': 10, 'final_excluded': 12, 'gate_codes': ['boundary_exclusions_exceed_pairings_in_view:plan-F1:paired=11:excluded=12'], 'added_evidence': ['below_request_area_threshold']}
    warnings.warn(repr({

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 1 warning in 3.16s
```

夹具规则：从真实 raw cavities 中按 `area < request.min_room_area_m2` 选存货，把每个真实
`0.0576 m²` 小腔分成两个互不重叠的 shaft zone；新增数量按
`paired - baseline_excluded + 1` 计算，未钉 view/cavity id。临时探针在最终全量前已删除，未提交。

### 阻断 2：同一阈值又放过 `excluded == paired` 的大量灌证

请求书要求另找一种能骗过新判据的真实错误形态。实测在没有基线 exclusion 的 `plan-F2`，
producer 把 14 个真实 pairing 中恰好 7 个改写成“面积等于原腔、reason 合法”的 loss；最终
`7 paired / 7 excluded`，新增门没有任何 failure。一个 view 有整整一半 zone 未被验证，已是
大量灌证；而“例外不得变成常规”的文字也不能支持“例外与常规一样多仍绿”。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_crossreview_gpt_probe.py::test_balanced_flood_equal_to_pairings_bypasses_new_gate
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_crossreview_gpt_probe.py::test_balanced_flood_equal_to_pairings_bypasses_new_gate
  /tmp/joint_review_gpt/tests/test_crossreview_gpt_probe.py:302: UserWarning: {'view': 'plan-F2', 'dropped_true_looking_losses': 7, 'remaining_pairings': 7, 'exclusions': 7, 'gate_codes': []}
    warnings.warn(repr({

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 1 warning in 3.25s
```

修复不能只是继续调比例。对 producer 自写的 `registered_ring_loss`，需要能逐条证明其 applicability
的独立证据，或对未获独立证明的 loss fail-loud；否则任何有限配额内的灌证仍然合法。

## 二、重点疑点 2：reason 准入表

结论：**没有发现一张可观察的 reason 准入表仍缺失；疑点 2 被证伪。**

仅说“`Literal[8]` 会拒绝任意字符串”确实不足以回答“闭集里的每项是否有资格”。但这里的字段不是
通用 reason：它属于 `AsMeasuredBoundaryRingLossV1`，该类型的对象语义就是“above-threshold cavity
that yielded no edges”；生产者的八个构造分支也分别只在无法产出 ring 时创建这个类型。因此当前
八个值全部有资格表达“为什么没有 logical ring”。若消费端再列同样八个值，schema-合法输入上的行为
不会改变。

消费端逐值实测命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_crossreview_gpt_probe.py::test_every_closed_reason_is_admitted_by_the_consumer
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_crossreview_gpt_probe.py::test_every_closed_reason_is_admitted_by_the_consumer
  /tmp/joint_review_gpt/tests/test_crossreview_gpt_probe.py:283: UserWarning: {'non_axis_segment': (['non_axis_segment'], []), 'owner_count': (['owner_count'], []), 'classify_illogical': (['classify_illogical'], []), 'merged_lt_3': (['merged_lt_3'], []), 'endcap_const_not_a_measured_parallel_face': (['endcap_const_not_a_measured_parallel_face'], []), 'adjacent_support_lines_parallel': (['adjacent_support_lines_parallel'], []), 'intersection_ring_invalid': (['intersection_ring_invalid'], []), 'merged_span_has_no_supporting_witness': (['merged_span_has_no_supporting_witness'], [])}
    warnings.warn(repr(admitted))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 1 warning in 3.34s
```

类型与生产分支核实命令原文：

```bash
nl -ba src/agent/judge/as_measured.py | sed -n '415,444p' && nl -ba src/agent/judge/as_measured.py | sed -n '1658,1865p' | rg -n "AsMeasuredBoundaryRingLossV1|reason="
```

输出原文：

```text
   415 class AsMeasuredBoundaryRingLossV1(_StrictModel):
   416     """Stored readout for an above-threshold cavity that yielded no edges.
   417
   418     The value is still a pure derivation of the other measured geometry.  It is
   419     persisted here for the narrower reason that the as-measured draft must
   420     acknowledge its own gaps: a missing logical ring must not disappear as an
   421     unobservable absence.  This is not a rule that derived values in general
   422     belong in the facts layer.
   423     """
   424
   425     cavity_id: StableId
   426     area_units2: StrictNonNegativeInt
   427     span: AsMeasuredBoundaryFailureSpanV1
   428     reason: Literal[
   429         "non_axis_segment", "owner_count", "classify_illogical", "merged_lt_3",
   430         "endcap_const_not_a_measured_parallel_face",
   431         "adjacent_support_lines_parallel", "intersection_ring_invalid",
   432         "merged_span_has_no_supporting_witness"]
   433     owner_count: StrictNonNegativeInt | None = None
   434
   435     @model_validator(mode="after")
   436     def _owner_count_matches_reason(self):
   437         if (self.reason == "owner_count") != (self.owner_count is not None):
   438             raise ValueError("as_measured_boundary_loss_owner_count_mismatch")
   439         if self.area_units2 <= 0:
   440             raise ValueError("as_measured_boundary_loss_area_not_positive")
   441         return self
   442
   443
   444 class AsMeasuredNonOrthogonalLineV1(_StrictModel):
10:  1667                 fatal_loss = AsMeasuredBoundaryRingLossV1(
13:  1670                     reason="non_axis_segment")
26:  1683                 fatal_loss = AsMeasuredBoundaryRingLossV1(
28:  1685                     span=failure_span, reason="owner_count",
43:  1700                     fatal_loss = AsMeasuredBoundaryRingLossV1(
50:  1707                         reason="endcap_const_not_a_measured_parallel_face")
114:  1771                 losses.append(AsMeasuredBoundaryRingLossV1(
116:  1773                     span=local_failures[0], reason="classify_illogical"))
119:  1776                 losses.append(AsMeasuredBoundaryRingLossV1(
125:  1782                     reason="merged_lt_3"))
133:  1790             losses.append(AsMeasuredBoundaryRingLossV1(
139:  1796                 reason="adjacent_support_lines_parallel"))
153:  1810             losses.append(AsMeasuredBoundaryRingLossV1(
159:  1816                 reason="intersection_ring_invalid"))
197:  1854             losses.append(AsMeasuredBoundaryRingLossV1(
204:  1861                 reason="merged_span_has_no_supporting_witness"))
```

注意：这只说明“准入子集”不缺，不证明 producer 对某个 cavity 写的 reason 为真；后者仍是阻断 2
所述的独立 applicability 问题。

## 三、派工单 §五六项验收

### 1. 大量灌证必须红：通过现有验收

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py::test_flooding_the_loss_ledger_cannot_waive_the_majority_of_a_view
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
1 passed in 3.18s
```

### 1b. 单 view 集中 flood：通过现有验收，但未覆盖阻断 2 的等量 flood

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py::test_a_flood_in_one_view_reddens_where_a_global_count_would_stay_green
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
1 passed in 3.21s
```

### 2. 撤证方向原 11 条锁：通过

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py -k "not flooding_the_loss_ledger_cannot_waive_the_majority_of_a_view and not a_flood_in_one_view_reddens_where_a_global_count_would_stay_green"
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

...........                                                              [100%]
11 passed in 3.41s
```

新判据未把原锁变成恒真：原 11 条分别仍锚定 re-derive 禁令、ledger citation、schema identity、
未声明 structural、撤 licence、共享 cavity overlap、threshold exit 等独立条件；新增聚合 failure 只被加入
该文件 branch code 的完整枚举。它们的定向输出仍是 11/11 绿。

### 3. 新判据能绿、能红，摘掉实现会失牙：通过

探针以 AST 只删除 `paired_per_view` 起至 `mismatches` 前的新增聚合块；其余函数逐字复用。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_crossreview_gpt_probe.py::test_acceptance_3_gate_red_green_and_stripped_mutation
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
=============================== warnings summary ===============================
tests/test_crossreview_gpt_probe.py::test_acceptance_3_gate_red_green_and_stripped_mutation
  /tmp/joint_review_gpt/tests/test_crossreview_gpt_probe.py:190: UserWarning: {'honest_gate_codes': [], 'flooded_gate_codes': ['boundary_exclusions_exceed_pairings_in_view:plan-F1:paired=1:excluded=12'], 'stripped_gate_codes': [], 'victim': 'plan-F1', 'current_paired': 1, 'current_excluded': 12}
    warnings.warn(repr({

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 1 warning in 3.17s
```

### 4. 奇数 interzone 厚度响亮 NA：通过

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_f156_ring_from_intersection.py::test_odd_interzone_thickness_is_declined_loudly_not_silently_truncated
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
1 passed in 3.24s
```

实现先拒绝 odd interzone thickness，再使用 `// 2`；测试自行从偶数存货构造 `+1` 后证明
`odd / 2 - odd // 2 == 0.5`，并要求精确 reason
`wall_axis_falls_between_storage_units`。这与生产者的整数存储纪律一致。

### 5. 全量：通过

最终权威全量在删除临时探针后运行。

命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
```

结论相关输出原文摘录（中间进度点与 211 条既有 warning 不承重；下列行未改写）：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
3635 passed, 13 xfailed, 211 warnings in 530.97s (0:08:50)
```

## 四、环境红归属核实

`test_zone_agent.py` 不直接 import `answer_compiler`，被审 diff 也不含该文件；注入主树 `.env` 后
该文件独立为绿。因此请求书 §三所述红不记施工方账。

静态核实命令原文：

```bash
python - <<'PY'
import ast
from pathlib import Path
path = Path('tests/test_zone_agent.py')
tree = ast.parse(path.read_text())
imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.extend(alias.name for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        imports.append(node.module)
print('direct_imports=', sorted(imports))
print('imports_answer_compiler=', any(name == 'src.agent.judge.answer_compiler' for name in imports))
PY
```

输出原文：

```text
direct_imports= ['src.agent.nodes.zone', 'src.agent.state']
imports_answer_compiler= False
```

定向测试命令原文：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_zone_agent.py
```

输出原文：

```text
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
1 passed in 6.83s
```

## 五、开工与 diff 自证

命令原文：

```bash
git -C /tmp/joint_review_gpt rev-parse --short HEAD && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)"
```

输出原文：

```text
cf1bd0d
/tmp/joint_review_gpt/src/agent/judge/answer_compiler.py
```

命令原文：

```bash
git diff --name-only bbeab77^ bbeab77 && git diff --name-only bbeab77^ bbeab77 -- tests/test_zone_agent.py
```

输出原文：

```text
AI_agent/logs/reviews/execution/2026-09-02_f156r4_o21d_joint_claude.md
src/agent/judge/answer_compiler.py
tests/test_f156_ring_from_intersection.py
tests/test_o21d_exclusion_gap.py
```

第二个 `git diff` 无输出。whitespace 核实命令原文：

```bash
git show --check --oneline --no-renames bbeab77
```

输出原文（无 whitespace error）：

```text
bbeab77 09.02_F156r4_O21d_JointRework_FloodingTeeth_AndOddThicknessNA
```

## 六、返工验收边界

1. 不把 `below_request_area_threshold` 计入 producer-loss flooding 配额；它已有 raw area + request
   threshold 的独立证明。
2. 对 `registered_ring_loss` 建立逐条独立 applicability 证明或 fail-loud，不能再用任意比例代替真伪。
3. 新锁至少覆盖本裁决两种相反形态：诚实 `excluded > paired` 必须绿；`excluded == paired` 的
   true-looking ledger flood 必须红。
4. 保留 odd-thickness 响亮 NA、原 11 条撤证锁和全量绿。
