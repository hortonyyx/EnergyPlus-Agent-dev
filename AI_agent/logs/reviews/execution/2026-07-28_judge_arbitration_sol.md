# 执行日志 · 判卷器「诊断仲裁 + 守恒判据 + 来源身份」施工（Slice 0）

- 日期：2026-07-28
- 施工席位：sol
- 本次范围：仅设计稿 §7 Slice 0；未开始 Slice 1
- 基线 HEAD：`cce6e832047198912812294439589f6bc896adc9`
- Slice 0 红锁提交：`7071892944947e74f5687d87e9d2ae34fc80a6b9`
- 提交标题：`7.28_JudgeArbitrationSlice0RedLocks`
- 新增锁文件：`tests/test_judge_arbitration_slice0.py`

## 1. 开工 / 收工状态

开工时实际执行 `git status --short`，原文：

```text
?? AI_agent/logs/reviews/request/2026-07-28_judge_arbitration_construction_dispatch.md
```

收工时实际执行 `git status --short`，原文：

```text
?? AI_agent/logs/reviews/request/2026-07-28_judge_arbitration_construction_dispatch.md
```

两份快照逐字相同。派工单是开工前已有的 user/controller untracked 文件，本次未修改、未提交。
锁与本日志均已提交，故不留在收工 short status 中。

## 2. sm24 受保护树 SHA-256 manifest

施工前：

```text
5a8dcba5ab4f5b2b5dc30df91896eeee50e01f9a5bf06ec1b379101a4d16d420  case_tests/test_baseline/gt/sm24_anchor/gt.json
7d4c1ed09f31377253838445733a130c11ff2fedf5ca95ddcdd231a7439abe03  case_tests/test_baseline/gt/sm24_anchor/renders/gt_elev.png
2ba9dd15497dc935e9a5e6499ef632ae0034179edb0b44164bfbc5025e655bd7  case_tests/test_baseline/gt/sm24_anchor/renders/gt_plan.png
135e2995a07e5acf6ed5d878f7e7d0acfc1baef1fdc3e8a687dd8fada705c675  case_tests/test_baseline/gt/sm24_anchor/renders/overlay_1f_view.png
ae69b4276567305dfc9b9145a9a1f2b28593b399a28090d09004a626bd6ed366  case_tests/test_baseline/gt/sm24_anchor/renders/overlay_East_view.png
d4a99cca3128e0335fed6bc7f76bb6c9bd700ab155a61eda7f2de5b8ed7be957  case_tests/test_baseline/gt/sm24_anchor/renders/overlay_North_view.png
0e66297543fcaecb0899018af25715197538b37373d555c0fc47a46b3f83302e  case_tests/test_baseline/gt/sm24_anchor/renders/overlay_South_view.png
a782dd82fa4c309c0893cdf16b8b1dd6a917825ba4ea0dde37ab893d6eba6375  case_tests/test_baseline/gt/sm24_anchor/renders/overlay_West_view.png
25e7d077c169eb087f1c3b477a1f919e1d8d4a4ad76b3d4931c0894ce125873e  case_tests/test_baseline/gt/sm24_anchor/review/conversion_report.json
bd1d7efea498e50ca47dd0144a0c9a1720d68f72e97fda3cd4faf78cf7fb6b70  case_tests/test_baseline/gt/sm24_anchor/review/opening_elevation_audit.json
f602d80287e64264df2c724dcd9941c29aec93c920c38ece91d885df1ad7e470  case_tests/test_baseline/gt/sm24_anchor/review/review_ack.json
9341cd4ee2fd122a27d41c75a03b92cb15b31f7e474334c1c57f07854c76e457  case_tests/test_baseline/gt/sm24_anchor/review/review_annotations.json
edb99f09f97348a29d414d6bee81ac946a1afc619d297d6b88d0036d03413030  case_tests/test_baseline/gt/sm24_anchor/review/review_index.json
b76c35c4ed215814f1f1a1c70e2cfeda65efc9e3b0f53054f48f082c97291a89  case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json
```

施工后复算与上表逐行一致；`git diff -- case_tests/test_baseline/gt/` 为空。该目录未改一字节。

## 3. Slice 0 六锁现码实测

受影响子集由规定工具计算：

```text
$ python scripts/tool_scripts/affected_tests.py --changed tests/test_judge_arbitration_slice0.py --explain
SCOPE: SUBSET
python -m pytest -p no:cacheprovider -q tests/test_judge_arbitration_slice0.py
跑测声明：受影响子集 = tests/test_judge_arbitration_slice0.py（依据 affected_tests.py --changed tests/test_judge_arbitration_slice0.py）
EXPLAIN: tests/test_judge_arbitration_slice0.py: changed test file
```

汇总实测：

```text
FFFFFF                                                                   [100%]
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_c_l7_nonadjacent_duplicate_self_touch_is_certified_red
FAILED tests/test_judge_arbitration_slice0.py::test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths
FAILED tests/test_judge_arbitration_slice0.py::test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder
FAILED tests/test_judge_arbitration_slice0.py::test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red
FAILED tests/test_judge_arbitration_slice0.py::test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity
FAILED tests/test_judge_arbitration_slice0.py::test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger
6 failed in 8.64s
```

六把锁全部 RED；没有任何意外 GREEN，故未触发派工单的停工条件。

### 3.1 A-L3 · genuine duplicate + unrelated advisory

- 现码结果：**RED**
- 生产五项：锁内精确断言 `len(findings) == 5` 且全部 `ok`，已通过
- 失败含义：现码仍把独立 A/B duplicate 被 C advisory 洗成 capability NA
- 单锁命令：
  `pytest -q tests/test_judge_arbitration_slice0.py::test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red`

失败输出原文：

```text
_____ test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red _____
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

        error = caught.value
>       assert error.code == "score_product_identity_invalid"
E       AssertionError: assert 'score_unsupp...d_combination' == 'score_produc...ntity_invalid'
E
E         - score_product_identity_invalid
E         + score_unsupported_combination

tests/test_judge_arbitration_slice0.py:204: AssertionError
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red
```

### 3.2 A-L9 · missing evaluator 请求级计数

- 现码结果：**RED**
- 失败含义：现码没有 predicate registry/certifier，更没有 item + summary 计数产物
- 锁同时钉三条路径：仅 unknown ⇒ NA/count=1；unknown + unrelated certified duplicate
  ⇒ RED/count=1；临时注册 evaluator ⇒ count=0
- 单锁命令：
  `pytest -q tests/test_judge_arbitration_slice0.py::test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths`

失败输出原文：

```text
____ test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths ____
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

caplog = <_pytest.logging.LogCaptureFixture object at 0x74e8279abf80>

    def test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths(caplog):
        """A-L9: missing predicate evaluators are fail-safe but never invisible."""
>       certifier = importlib.import_module("src.agent.judge.certifier")
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_judge_arbitration_slice0.py:221:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

name = 'src.agent.judge.certifier'
import_ = <function _gcd_import at 0x74e8886cc0e0>

>   ???
E   ModuleNotFoundError: No module named 'src.agent.judge.certifier'

<frozen importlib._bootstrap>:1324: ModuleNotFoundError
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths
```

### 3.3 B-L4 · 三相邻 span 的 1-ulp 假红

- 现码结果：**RED**
- GT：真实 `GroundTruthV3` 嵌套模型，走 `extract_gt_plan_segments`
- correction：真实 `CorrectedGeometryV3`，生产五项全绿，走
  `extract_correction_plan_segments`
- 三个目标 span：`[x0,x1] / [x1,x2] / [x2,x3]`，共享端点逐位相同
- 失败含义：现码顺序累加比 observation 端点直差多 1 ulp
- 单锁命令：
  `pytest -q tests/test_judge_arbitration_slice0.py::test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger`

失败输出原文：

```text
____ test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger _____
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

obs_key = 'F:interior:(0.6615103026426206, 1.0):(21.523013020575195, 1.0)'
obs_length = 20.861502717932574, covered = 20.861502717932577

        if covered > obs_length:
>           raise ScoreContractError("score_denominator_nonconserving", "scoring.denominator_totality",
                context={"reason": "observation_cover_exceeds_length", "observation": obs_key,
                         "obs_length": obs_length, "covered": covered, "excess": covered - obs_length})
E           src.agent.judge.score_schema.ScoreContractError: score_denominator_nonconserving at scoring.denominator_totality

src/agent/judge/segment_score.py:823: ScoreContractError
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger
```

精确复算值：

```text
covered sequential sum = 20.861502717932577 = 0x1.4dc8b712eef7fp+4
observation.length      = 20.861502717932574 = 0x1.4dc8b712eef7ep+4
excess                  = 3.552713678800501e-15 = 0x1.0000000000000p-48
```

### 3.4 C-L1 · 三类正式 adapter 的 source key

- 现码结果：**RED**
- GT：`make_b4b_gt_document()` 返回真实 `GroundTruthV3`
- correction：真实 `CorrectedGeometryV3`
- reading：正式 `coerce_plan_observations` dict wire
- 失败含义：spy 实测三类入口进入 `_cluster_axis` 前均已展平为裸 float
- 单锁命令：
  `pytest -q tests/test_judge_arbitration_slice0.py::test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity`

失败输出原文：

```text
_____ test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity _____
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

        assert captured_occurrences
>       assert all(
            hasattr(occurrence, "source_key")
            and hasattr(occurrence, "value")
            and occurrence.value_hex == float(occurrence.value).hex()
            for occurrence in captured_occurrences
        ), "C-L1: raw floats reached _cluster_axis before source identity was preserved"
E       AssertionError: C-L1: raw floats reached _cluster_axis before source identity was preserved
E       assert False
E        +  where False = all(<generator object test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity.<locals>.<genexpr> at 0x762819bac3c0>)

tests/test_judge_arbitration_slice0.py:469: AssertionError
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity
```

### 3.5 C-L7 · 非相邻重复顶点 + 自触

- 现码结果：**RED**
- 输入：真实 `CorrectedGeometryV3`，ring =
  `(0,0),(4,0),(4,4),(0,4),(0,2),(2,2),(0,2)`
- 失败含义：现码静默接受，未发任何 `ScoreContractError`
- 单锁命令：
  `pytest -q tests/test_judge_arbitration_slice0.py::test_c_l7_nonadjacent_duplicate_self_touch_is_certified_red`

失败输出原文：

```text
_________ test_c_l7_nonadjacent_duplicate_self_touch_is_certified_red __________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

>       with pytest.raises(ScoreContractError) as caught:
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE <class 'src.agent.judge.score_schema.ScoreContractError'>

tests/test_judge_arbitration_slice0.py:532: Failed
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_c_l7_nonadjacent_duplicate_self_touch_is_certified_red
```

### 3.6 C-L11 · identity contract 版本门

- 现码结果：**RED**
- 锁要求 typed `IdentityInputEnvelope(contract_version="2")` 进入只支持 `"1"` 的 builder
  后发 `score_identity_contract_mismatch / identity_contract_version_mismatch`
- 失败含义：现码连 provenance/envelope 模块都不存在
- 单锁命令：
  `pytest -q tests/test_judge_arbitration_slice0.py::test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder`

失败输出原文：

```text
___ test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder ___
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder():
        """C-L11: a typed adapter cannot feed contract v2 into the v1 identity builder."""
>       provenance = importlib.import_module("src.agent.judge.identity_provenance")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_judge_arbitration_slice0.py:548:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

name = 'src.agent.judge.identity_provenance'
import_ = <function _gcd_import at 0x71f3893c40e0>

>   ???
E   ModuleNotFoundError: No module named 'src.agent.judge.identity_provenance'

<frozen importlib._bootstrap>:1324: ModuleNotFoundError
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder
```

## 4. 指定 neuter 的可执行 patch

### 4.1 使用约束与当前状态

这些 patch 是 **后续 Slice 实现后的结构 neuter**。Slice 0 生产 guard 尚不存在，故本轮不能诚实
声称“已运行并使锁转红”；DoD #16 仍标 PARTIAL。为消除“到时再猜删哪一行”，后续实现须在下列
精确 guard 周围保留稳定 marker：

```text
# NEUTER:<LOCK>:BEGIN
...
# NEUTER:<LOCK>:END
```

下列每段都是可直接执行的 fail-closed mutation program：marker 缺失、重复或文件路径不符会
立即失败，不会静默声称 neuter 完成。执行步骤一律是：

```bash
neuter_repo="$(mktemp -d)"
git archive HEAD | tar -x -C "$neuter_repo"
cd "$neuter_repo"
# 只在这里执行下面某一 patch，再运行点名锁；不回写工作树。
```

### 4.2 A-L3 · 把局部依赖退化为“同请求有 capability 即全部 contingent”

目标文件：`src/agent/judge/certifier.py`

```bash
python - <<'PY'
from pathlib import Path
p = Path("src/agent/judge/certifier.py")
s = p.read_text()
begin = "# NEUTER:A-L3:BEGIN\n"
end = "# NEUTER:A-L3:END\n"
assert s.count(begin) == s.count(end) == 1
before, rest = s.split(begin)
_, after = rest.split(end)
replacement = (
    begin
    + "    # neuter: any capability contaminates every witness in the request\n"
    + "    proof_status = \"CONTINGENT\" if capability_closure.capability_ids else evaluator(\n"
    + "        diagnostic.witness, fact_graph, capability_closure\n"
    + "    )\n"
    + end
)
p.write_text(before + replacement + after)
PY
pytest -q tests/test_judge_arbitration_slice0.py::test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red
```

预期：A-L3 RED（整请求被错误降为 NA）。这就是设计稿 A-L2/A-L3 共用“局部而非整层污染”守卫
的 A-L3 方向；A-L2 的另一方向在 Slice 2 才落锁。

### 4.3 A-L9 · missing evaluator 只返回 NA，跳过 accumulator/emitter

目标文件：`src/agent/judge/certifier.py`

```bash
python - <<'PY'
from pathlib import Path
p = Path("src/agent/judge/certifier.py")
s = p.read_text()
begin = "# NEUTER:A-L9:BEGIN\n"
end = "# NEUTER:A-L9:END\n"
assert s.count(begin) == s.count(end) == 1
before, rest = s.split(begin)
_, after = rest.split(end)
replacement = (
    begin
    + "        # neuter: preserve fail-safe NA but erase operational visibility\n"
    + "        pass\n"
    + end
)
p.write_text(before + replacement + after)
PY
pytest -q tests/test_judge_arbitration_slice0.py::test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths
```

预期：A-L9 RED；至少 item/count/histogram/final-red 保留计数断言失败。

### 4.4 B-L4 · 把 atom ledger 退回顺序 float covered + strict 比较

目标文件：`src/agent/judge/segment_score.py`

marker 块的作用域合同：`observation` 为当前 observation，`observation_atoms` 为按 cut 排序的
原子，atom 暴露 `length_exact` 与 `target_ids`。

```bash
python - <<'PY'
from pathlib import Path
p = Path("src/agent/judge/segment_score.py")
s = p.read_text()
begin = "# NEUTER:B-L4:BEGIN\n"
end = "# NEUTER:B-L4:END\n"
assert s.count(begin) == s.count(end) == 1
before, rest = s.split(begin)
_, after = rest.split(end)
replacement = (
    begin
    + "        # neuter: retired scalar conservation path\n"
    + "        covered = 0.0\n"
    + "        for atom in observation_atoms:\n"
    + "            if atom.target_ids:\n"
    + "                covered += float(atom.length_exact)\n"
    + "        _assert_obs_conservation(observation.key, observation.length, covered)\n"
    + end
)
p.write_text(before + replacement + after)
PY
pytest -q tests/test_judge_arbitration_slice0.py::test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger
```

预期：复现本日志 §3.3 的 1-ulp `score_denominator_nonconserving`，B-L4 RED。

### 4.5 C-L1 · adapter 在进入聚类前剥离 occurrence

目标文件：`src/agent/judge/segment_score.py`

marker 块的作用域合同：`occurrences` 为本轴的 `CoordinateOccurrence` tuple，`side/floor_id/axis`
为现有聚类上下文。

```bash
python - <<'PY'
from pathlib import Path
p = Path("src/agent/judge/segment_score.py")
s = p.read_text()
begin = "# NEUTER:C-L1:BEGIN\n"
end = "# NEUTER:C-L1:END\n"
assert s.count(begin) == s.count(end) == 1
before, rest = s.split(begin)
_, after = rest.split(end)
replacement = (
    begin
    + "    # neuter: restore the provenance-destroying float generator\n"
    + "    axis_identity = _cluster_axis(\n"
    + "        (float(occurrence.value) for occurrence in occurrences),\n"
    + "        side=side, floor_id=floor_id, axis=axis,\n"
    + "    )\n"
    + end
)
p.write_text(before + replacement + after)
PY
pytest -q tests/test_judge_arbitration_slice0.py::test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity
```

预期：spy 捕获裸 float，C-L1 RED。

### 4.6 C-L7 · ring validator 退回只查相邻坍缩

目标文件：`src/agent/judge/identity_provenance.py`

marker 块的作用域合同：`ring/topology/diagnostics` 是当前 ring 的完整来源拓扑与诊断列表。

```bash
python - <<'PY'
from pathlib import Path
p = Path("src/agent/judge/identity_provenance.py")
s = p.read_text()
begin = "# NEUTER:C-L7:BEGIN\n"
end = "# NEUTER:C-L7:END\n"
assert s.count(begin) == s.count(end) == 1
before, rest = s.split(begin)
_, after = rest.split(end)
replacement = (
    begin
    + "    # neuter: only adjacent collapse remains; repeated non-neighbours/self-touch vanish\n"
    + "    diagnostics.extend(_check_adjacent_ring_collapses(ring, topology))\n"
    + end
)
p.write_text(before + replacement + after)
PY
pytest -q tests/test_judge_arbitration_slice0.py::test_c_l7_nonadjacent_duplicate_self_touch_is_certified_red
```

预期：输入再次静默接受或产 `zone_ids=("Z","Z")`，C-L7 RED。

### 4.7 C-L11 · 忽略 envelope version

目标文件：`src/agent/judge/identity_provenance.py`

marker 块的作用域合同：`envelope` 是 builder 收到的 typed `IdentityInputEnvelope`。

```bash
python - <<'PY'
from pathlib import Path
p = Path("src/agent/judge/identity_provenance.py")
s = p.read_text()
begin = "# NEUTER:C-L11:BEGIN\n"
end = "# NEUTER:C-L11:END\n"
assert s.count(begin) == s.count(end) == 1
before, rest = s.split(begin)
_, after = rest.split(end)
replacement = (
    begin
    + "    # neuter: accept every declared identity contract version\n"
    + "    pass\n"
    + end
)
p.write_text(before + replacement + after)
PY
pytest -q tests/test_judge_arbitration_slice0.py::test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder
```

预期：version `"2"` 不再发 `score_identity_contract_mismatch`，C-L11 RED。

## 5. 全仓测试

命令：`pytest`（仓库默认并行，16 workers）。

全仓尾部原文：

```text
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red
FAILED tests/test_judge_arbitration_slice0.py::test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths
FAILED tests/test_judge_arbitration_slice0.py::test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger
FAILED tests/test_judge_arbitration_slice0.py::test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity
FAILED tests/test_judge_arbitration_slice0.py::test_c_l7_nonadjacent_duplicate_self_touch_is_certified_red
FAILED tests/test_judge_arbitration_slice0.py::test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder
===== 6 failed, 1725 passed, 10 xfailed, 150 warnings in 259.86s (0:04:19) =====
```

与 `cce6e83` 基线 `1725 passed, 10 xfailed, 0 failed` 对照：

- passed：不变（1725）
- xfailed：不变（10）
- 新增 failed：恰好六把 Slice 0 锁
- 其他既有测试：零状态变化

## 6. 写锁时暴露的设计稿欠规格边界

以下不是生产机制方向争议，而是把语义写成可执行锁时必须选定、设计稿未给文件/签名/序列化形状
的接口边界。本轮没有假装它们“设计稿早已定死”：

1. **A-L9 certifier 调用面未定。** §2.3/§4.3 定了 typed witness 与 registry 语义，但没有定
   模块路径、请求函数签名、evaluator 返回协议。锁选择
   `src.agent.judge.certifier.certify_and_arbitrate_request`，registry 为
   `(predicate, version) -> callable`，evaluator 返回四个 proof-status 字符串。
2. **成功态 exact ledger audit 的暴露方式未定。** B-L4 要断言 production ledger 的
   `covered_exact == domain_exact`，但现有 `match_plan_segments` 只返回 `(rows, map)`，设计稿
   没定 audit 返回面。锁选择 production 在 `segment_score` 暴露实际调用的
   `_build_observation_ledger` seam，ledger 暴露 `observation_key/domain_exact/covered_exact/
   extra_exact/atoms`。锁先无 instrumentation 跑一次，确保当前 RED 来自真实 1-ulp 路径。
3. **C 的模块与 envelope 构造签名未定。** 锁选择
   `src.agent.judge.identity_provenance`，并把 `IdentityInputEnvelope` 的最小构造字段钉为
   `contract_version/source_schema/side/floor_id/occurrences/topology`；
   `SourceTopologyIndex.empty(side, floor_id)` 是空正式拓扑的构造面。
4. **A-L3/C-L7 的错误 context 容器形状未定。** §2.4 只列最低语义字段，没有定 flat/nested。
   锁选择现有 `ScoreContractError.context` 的 flat 兼容形态，精确键为
   `authority/proof_status/predicate/predicate_schema_version/owner_ids/source_edge_ids/
   source_vertex_ids/depends_on_capability_ids`。
5. **footprint source key 的 `owner_id` 未定。** §2.1 dataclass 要求 `owner_id`，§3.2 表中的
   footprint tuple 却没有 owner id。C-L1 因而只对无歧义的 GT zone、correction cell、reading
   endpoint 钉完整 key；未擅自决定 footprint owner id。该点应在 Slice 1 轻门前由主控确认。
6. **neuter 的精确行在 guard 不存在时不可实跑。** 本日志把后续 guard marker 与作用域合同钉死，
   给出 fail-closed 可执行 mutation；但本轮不伪造“已经在不存在的实现上执行”。DoD #16 保持
   PARTIAL，须在相应 Slice 落码后只在 `/tmp` 副本逐个实跑并回填真实红数。

## 7. §10 DoD 16 条 Slice 0 自评

| # | 状态 | Slice 0 证据 / 卡点 |
|---:|---|---|
| 1 | PARTIAL | 已落 A-L3/A-L9/B-L4/C-L1/C-L7/C-L11 共 6 锁；其余 29 锁属 Slice 1–4 |
| 2 | PARTIAL | A-L3 与 B-L4 已钉当前错误方向；advisory derivative 与最终合法计分待后续实现 |
| 3 | PARTIAL | A-L3 已要求 fixed core 仅 A/B；A-L1 capability replay 未落 |
| 4 | PARTIAL | A-L9 已同时写 NA/RED/registered 三路径；生产 registry/telemetry 未落 |
| 5 | PARTIAL | C-L1 已钉来源；三历史 alias 与无关系 sub-merge 属 Slice 1 |
| 6 | PARTIAL | C-L1 spy 已禁止生产调用点裸 float；alias certifier API/AST 门待 Slice 1 |
| 7 | PARTIAL | 本 Slice 只落合法相邻 B-L4；B-L2/B-L3 overlap 门待 Slice 3 |
| 8 | PARTIAL | 尚未删除旧 `extra = length - covered` |
| 9 | PARTIAL | canonical observation cut id 尚未实现 |
| 10 | PARTIAL | C-L7 已钉非相邻重复/自触；其余完整 context 锁待 Slice 1 |
| 11 | PARTIAL | C-L11 已钉版本 raise；same-source/unproven alias 路径待 Slice 1 |
| 12 | PARTIAL | helper identity bump 按设计在 Slice 4，本 Slice 未动生产身份 |
| 13 | PARTIAL | 本 Slice 未落顺序置换全矩阵 |
| 14 | PARTIAL | 全仓已跑；真实 sm24 改造前后逐行 diff 须在生产改造后 Slice 4 执行 |
| 15 | PARTIAL | 旧套件状态零变化；性能实测须在 exact/topology 实现存在后执行 |
| 16 | PARTIAL | 六个 neuter 已写成 fail-closed executable patch；生产 guard 尚不存在，未伪造实跑 |

## 8. D-1 / D-2 状态

- **D-1 真实 sm24 逐行 diff：PARTIAL / 尚不可执行。** Slice 0 没有生产改造，“new” 侧不存在；
  将在 Slice 4 按 §8.3 真实 `score_typed_attempt` 正门生成并逐行 diff。
- **D-2 性能实测：PARTIAL / 尚不可执行。** exact ledger/topology 结构尚未实现；将在对应结构
  存在后对真实最大 fixture 测时间与内存，不以盒子数量估算代替。

## 9. Slice 边界结论

Slice 0 完成并停止。未修改生产代码，未开始 Slice 1。等待主控对
`7071892944947e74f5687d87e9d2ae34fc80a6b9` 做轻门。
