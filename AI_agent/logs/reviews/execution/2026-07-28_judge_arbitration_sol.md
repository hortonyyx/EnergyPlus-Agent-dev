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

---

## 10. Slice 1 · 来源图与身份合同（C）

### 10.1 提交与范围

- Slice 1 源码/锁提交：
  `c59e4bce048e963b7590580271210e9fef7643b8`
- 提交标题：`7.28_JudgeArbitrationSlice1SourceIdentity`
- 生产改动：
  - 新建 `src/agent/judge/identity_provenance.py`；
  - `segment_score.py` 的 GT / correction / reading 三类正式入口改为
    `SourceGeometryDocument -> IdentityInputEnvelope -> CoordinateOccurrence`；
  - `_AxisIdentity.rep` 的正式路径按 `CoordinateSourceKey` 查询；
  - 落 exact-version、same-source、结构 alias、exact ring/segment topology 与
    `(owner_kind, owner_id)` owner 合同。
- 新增 `tests/test_judge_identity_provenance.py`，17 条锁。
- 未进入 Slice 2；没有新增 `certifier.py`，没有改变 A 的仲裁行为。
- 未进入 Slice 3；没有改变 interval ledger 或 conservation 行为。
- 未进入 Slice 4；没有 bump helper/cache identity。

### 10.2 `git status --short` 首尾快照

Slice 1 开始（源码改动前）：

```text
?? AI_agent/logs/reviews/request/2026-07-28_judge_arbitration_construction_dispatch.md
```

Slice 1 源码提交后、追加本日志前：

```text
?? AI_agent/logs/reviews/request/2026-07-28_judge_arbitration_construction_dispatch.md
```

该 untracked 文件为主控拥有的 dispatch order，本轮未加入提交。两快照逐字节相同。

### 10.3 Slice 0 锁的合法状态迁移

| 锁 | Slice 1 后 | 证书 |
|---|---|---|
| A-L3 | RED | 仍为 `score_unsupported_combination`，留给 Slice 2 |
| A-L9 | RED | 仍为 `ModuleNotFoundError: src.agent.judge.certifier`，留给 Slice 2 |
| B-L4 | RED | 仍为原 1-ulp `score_denominator_nonconserving`，留给 Slice 3 |
| C-L1 | **GREEN** | 三类正式 adapter 送入的均为 occurrence；rep key 为 source key |
| C-L7 | **GREEN** | 非相邻重复/自触由 exact 通用 ring checker 产完整 certified witness |
| C-L11 | **GREEN** | builder 对 contract version 做 exact-string `"1"` 门；`"2"` 与 `2` 均拒绝 |

C-L1/C-L7/C-L11 已由行为级 neuter 重新证明，不再依赖 Slice 0 时的
`ModuleNotFoundError` 或“未来 guard”弱信号。

### 10.4 最终全仓

命令：`pytest -q`（仓库默认并行）。

尾部原文：

```text
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red
FAILED tests/test_judge_arbitration_slice0.py::test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths
FAILED tests/test_judge_arbitration_slice0.py::test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger
3 failed, 1745 passed, 10 xfailed, 150 warnings in 259.81s (0:04:19)
```

状态守恒：

- clean-tree baseline：`1725 passed, 10 xfailed`；
- Slice 0：六锁红，`1725 passed`；
- Slice 1：17 条新锁 + 三条转绿 C 锁 = 新增 20 passed；
- 实测 `1745 - 1725 = 20`；
- 除 A-L3/A-L9/B-L4 三条计划内红外，没有其他测试改变状态。

B-L4 的失败仍发生在原 `_assert_obs_conservation`：

```text
obs_length = 20.861502717932574
covered    = 20.861502717932577
if covered > obs_length:
    raise ScoreContractError("score_denominator_nonconserving", ...)
```

相对 `d20daef` 的 diff 中，`_SUBINTERVAL_SUM_TOL`、
`_assert_target_conservation`、`_assert_obs_conservation`、`covered > obs_length`
均无增删行；Slice 1 只因前方来源身份代码增加而把原函数移动到约第 1402 行，行为未改。

### 10.5 sm24 受保护树 SHA-256 比较

命令：

```bash
find case_tests/test_baseline/gt/sm24_anchor -type f -print0 \
  | sort -z | xargs -0 sha256sum
git diff --quiet -- case_tests/test_baseline/gt AI_agent/CLAUDE.md
```

Slice 1 结束 manifest 与 Slice 0 起始 manifest 逐项相同：

```text
5a8dcba5ab4f5b2b5dc30df91896eeee50e01f9a5bf06ec1b379101a4d16d420  gt.json
7d4c1ed09f31377253838445733a130c11ff2fedf5ca95ddcdd231a7439abe03  renders/gt_elev.png
2ba9dd15497dc935e9a5e6499ef632ae0034179edb0b44164bfbc5025e655bd7  renders/gt_plan.png
135e2995a07e5acf6ed5d878f7e7d0acfc1baef1fdc3e8a687dd8fada705c675  renders/overlay_1f_view.png
ae69b4276567305dfc9b9145a9a1f2b28593b399a28090d09004a626bd6ed366  renders/overlay_East_view.png
d4a99cca3128e0335fed6bc7f76bb6c9bd700ab155a61eda7f2de5b8ed7be957  renders/overlay_North_view.png
0e66297543fcaecb0899018af25715197538b37373d555c0fc47a46b3f83302e  renders/overlay_South_view.png
a782dd82fa4c309c0893cdf16b8b1dd6a917825ba4ea0dde37ab893d6eba6375  renders/overlay_West_view.png
25e7d077c169eb087f1c3b477a1f919e1d8d4a4ad76b3d4931c0894ce125873e  review/conversion_report.json
bd1d7efea498e50ca47dd0144a0c9a1720d68f72e97fda3cd4faf78cf7fb6b70  review/opening_elevation_audit.json
f602d80287e64264df2c724dcd9941c29aec93c920c38ece91d885df1ad7e470  review/review_ack.json
9341cd4ee2fd122a27d41c75a03b92cb15b31f7e474334c1c57f07854c76e457  review/review_annotations.json
edb99f09f97348a29d414d6bee81ac946a1afc619d297d6b88d0036d03413030  review/review_index.json
b76c35c4ed215814f1f1a1c70e2cfeda65efc9e3b0f53054f48f082c97291a89  score_inputs/view_bindings.json
```

`git diff --quiet` 退出码为 `0`；`case_tests/test_baseline/gt/` 与
`AI_agent/CLAUDE.md` 均零字节变化。

## 11. Slice 1 实际执行的 neuter self-check

所有 mutation 均只施加在
`/tmp/judge-slice1-neuters.FqY44q/repo` 副本；工作树没有 neuter 状态。
下表的“红数”是对应命令的真实 pytest 结果，不是源码目测。

| 锁 | 实际 mutation | 真实结果 |
|---|---|---:|
| C-L1 | `_build_floor_identity` 退回 `_cluster_legacy_axis(float)` | 1 failed |
| C-L2 | same-source 聚合键退回 raw value | 1 failed |
| C-L3 | `_cluster_axis` 在正式入口剥离 occurrence | 1 failed |
| C-L4 | `certify_alias` 对全部结构关系返回 `None` | 3 failed |
| C-L5 | 无证书也连 candidate adjacency | 1 failed |
| C-L6 | 跳过 post-merge ring validator | 1 failed |
| C-L7 | ring validator 退回“只查相邻坍缩” | 1 failed |
| C-L8 | exact edge-intersection predicate 恒 false | 1 failed |
| C-L9 | 删除 `left_owner != right_owner` 守卫 | 1 failed |
| C-L10 | boundary duplicate key 改用归并前 raw geometry | 1 failed |
| C-L11 | 忽略 envelope version | 2 failed |
| C-L12 | 给 duplicate reading id 放行 | 1 failed |
| C-L13 | 相交检查限定为 H/V | 1 failed |
| C-L14 | 在 matching 中非法联合 GT/product 坐标池 | 1 failed |
| C-L15 | 把 sm21 legacy grade dispatch 接入新 adapter | 1 failed |
| §8 owner 同名锁 | owner identity 退化为只剩 `owner_id` | 1 failed |

合计：19 个真实 red test instances。

一个重要的 mutation 观察：第一次只删除 C-L7 的“非相邻重复顶点”分支时，
exact non-adjacent edge intersection 仍独立报同一固定冲突，故锁仍为
`1 passed`；这不是完整的指定 neuter。把 validator 完整退化为“只保留相邻坍缩检查”
后才得到 `1 failed`。表中记录的是后者。

### 11.1 可执行 mutation patches

以下 patch 均以 `c59e4bc` 为基线，可在独立 `/tmp` 副本用
`apply_patch <<'PATCH' ... PATCH` 执行；每段后运行表中的单锁命令。

#### C-L1 · 正式 builder 退回裸 float

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
-    x_id = _cluster_axis(
-        x_occurrences, side=envelope.side, floor_id=envelope.floor_id, axis="x",
-        topology=envelope.topology,
-    )
-    y_id = _cluster_axis(
-        y_occurrences, side=envelope.side, floor_id=envelope.floor_id, axis="y",
-        topology=envelope.topology,
-    )
+    x_id = _cluster_legacy_axis(
+        (item.value for item in x_occurrences),
+        side=envelope.side, floor_id=envelope.floor_id, axis="x",
+    )
+    y_id = _cluster_legacy_axis(
+        (item.value for item in y_occurrences),
+        side=envelope.side, floor_id=envelope.floor_id, axis="y",
+    )
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_arbitration_slice0.py::test_c_l1_formal_adapters_preserve_source_keys_through_axis_identity`
；实测 `1 failed`。

#### C-L2 · same-source 聚合键退回 raw value

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
-        grouped.setdefault(key, []).append(occurrence)
+        grouped.setdefault(occurrence.value, []).append(occurrence)
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l2_same_source_spread_rejects_with_hex_and_diameter`
；实测 `1 failed`。

#### C-L3 · 正式 `_cluster_axis` 剥离 occurrence

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
     materialized = tuple(raw_values)
+    if topology is not None:
+        materialized = tuple(item.value for item in materialized)
     if topology is None:
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l3_guard_band_names_both_source_keys`
；实测 `1 failed`。

#### C-L4 · 拒绝所有结构 alias

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/identity_provenance.py
@@
-    if left.axis != axis or right.axis != axis:
-        return None
-    return topology.certificates.get(_pair_key(left, right))
+    return None
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l4_sm24_drift_has_paired_certificate_and_extracts tests/test_judge_identity_provenance.py::test_c_l4_formal_reverse_edge_alias_is_structural_not_distance`
；实测 `3 failed`。

#### C-L5 · 近邻即 alias

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
                 certificate = certify_alias(left_key, right_key, axis, topology)
+                adjacency[left_key].add(right_key)
+                adjacency[right_key].add(left_key)
                 if certificate is not None:
-                    adjacency[left_key].add(right_key)
-                    adjacency[right_key].add(left_key)
                     accepted.append(certificate)
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l5_unrelated_submerge_sources_reject_without_structural_relation`
；实测 `1 failed`（DID NOT RAISE）。

#### C-L6 · 跳过 post-merge ring validator

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
     out = tuple(_identify_point(point, x_id, y_id) for point in source_vertices)
     raw = tuple(point.raw_point for point in source_vertices)
+    return out
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l6_postmerge_ring_validator_is_independently_load_bearing`
；实测 `1 failed`（DID NOT RAISE）。

#### C-L7 · 退回只查相邻坍缩

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
-    for first in range(ring_n):
+    return out
+    for first in range(ring_n):
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_arbitration_slice0.py::test_c_l7_nonadjacent_duplicate_self_touch_is_certified_red`
；实测 `1 failed`。

#### C-L8 · exact intersection 恒 false

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
 def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
+    return False
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l8_bow_tie_from_formal_adapter_is_certified_red`
；实测 `1 failed`。

#### C-L9 · 删除 owner 不同守卫

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
-    if left_owner == right_owner:
+    if False and left_owner == right_owner:
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l9_same_owner_reverse_atom_is_contract_conflict`
；实测 `1 failed`（DID NOT RAISE）。

#### C-L10 · duplicate key 改用归并前几何

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
-            geom = (floor.id, min(q1, q2), max(q1, q2))
+            geom = (
+                floor.id,
+                min(source_segment.p1.raw_point, source_segment.p2.raw_point),
+                max(source_segment.p1.raw_point, source_segment.p2.raw_point),
+            )
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l10_boundary_duplicate_after_merge_carries_four_raw_endpoints`
；实测 `1 failed`（DID NOT RAISE）。

#### C-L11 · 忽略 exact-string version

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/identity_provenance.py
@@
-    if (
+    if False and (
         type(envelope.contract_version) is not str
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_arbitration_slice0.py::test_c_l11_typed_envelope_version_two_is_rejected_by_version_one_builder tests/test_judge_identity_provenance.py::test_c_l11_contract_version_is_exact_string_without_coercion`
；实测 `2 failed`。

#### C-L12 · 放行 duplicate reading id

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/identity_provenance.py
@@
-    if len(ids) != len(set(ids)):
+    if False and len(ids) != len(set(ids)):
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l12_duplicate_reading_id_rejects_in_adapter`
；实测 `1 failed`。

#### C-L13 · 相交检查退化为 H/V only

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
 def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
+    if (
+        a[0] != b[0] and a[1] != b[1]
+        and c[0] != d[0] and c[1] != d[1]
+    ):
+        return False
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_provenance.py::test_c_l13_generic_nonorthogonal_concave_passes_and_bow_tie_rejects`
；实测 `1 failed`。

#### C-L14 · 非法联合答案/产品池

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
     target_list = tuple(sorted(targets, key=_canonical_geometry))
     obs_list = tuple(sorted(observations, key=_canonical_geometry))
+    product_x = {v for o in obs_list for v in (o.p1[0], o.p2[0])}
+    product_y = {v for o in obs_list for v in (o.p1[1], o.p2[1])}
+    def pooled(point):
+        xs = [v for v in product_x if abs(v - point[0]) < _COORDINATE_MERGE_THRESHOLD]
+        ys = [v for v in product_y if abs(v - point[1]) < _COORDINATE_MERGE_THRESHOLD]
+        return min([point[0], *xs]), min([point[1], *ys])
+    target_list = tuple(
+        PlanSegment(row.key, row.floor_id, pooled(row.p1), pooled(row.p2),
+                    row.zone_ids, row.source_ids, row.exterior)
+        for row in target_list
+    )
*** End Patch
PATCH
```

命令：
`pytest -q tests/test_judge_identity_metric.py::test_a8_answer_denominator_independent_of_product`
；实测 `1 failed`（两次 denominator binary64 不同）。

#### C-L15 · 把 sm21 legacy dispatch 接入 adapter

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: scripts/tool_scripts/run_stage.py
@@
 def _grade_attempt_artifacts(
@@
 ) -> dict:
     from src.agent.execution.manifest import attempt_index_of, hash_text
+    from src.agent.judge import segment_score as provenance_segment
@@
     if stage not in {"0_reading", "1_correction"}:
         return {"score_vs_gt": None, "grade": None, "score_criteria": []}
+    provenance_segment.adapt_reading_floor("legacy-neuter", ())
*** End Patch
PATCH
```

命令：
`pytest -q -n0 tests/test_judge_identity_provenance.py::test_c_l15_sm21_score_pixels_and_dispatch_do_not_instantiate_new_adapter`
；实测 `1 failed`，bomb 在 adapter 调用处触发；未写入工作树。

#### §8 owner 同名锁 · owner identity 退化为裸 id

```bash
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/agent/judge/identity_provenance.py
@@
     @property
     def owner(self) -> OwnerIdentity:
-        return self.owner_kind, self.owner_id
+        return "", self.owner_id
*** End Patch
PATCH
```

命令：
`pytest -q -n0 tests/test_judge_identity_provenance.py::test_owner_identity_uses_kind_and_id_when_cell_id_equals_floor_id`
；实测 `1 failed`，footprint/cell 同名被错误判为 duplicate owner。

## 12. 两项边界审计

### 12.1 保留的 legacy float 路径不是一个封闭的长期合同

本轮使用的枚举方法是仓库范围的静态文本调用点枚举：

```bash
rg -n "_cluster_axis\\(" --glob '*.py' --glob '!tests/**' --glob '!AI_agent/**'
```

实测只有：

```text
segment_score.py:387  def _cluster_axis(...)
segment_score.py:419  x_id = _cluster_axis(...)
segment_score.py:423  y_id = _cluster_axis(...)
```

即当前仓库内所有静态 production direct call 都汇聚到 `_build_floor_identity`，而该 builder
只从 exact-version envelope 拆 occurrence，并显式传 `topology`。C-L1 spy 和
`test_production_adapters_never_enter_legacy_float_cluster` 又覆盖了当前三类 adapter。

但这不是 AST/call-graph 证明，也不能阻止未来代码直接调用
`_cluster_axis(floats, topology=None)`；该测试只覆盖本轮已知且已接线的三类正式 adapter。
因此保留的 legacy 分支是明确的再入口风险，不应宣称“总锁已封闭”。

保留它的唯一原因是硬约束要求不重写已有裸 helper 测试。建议在主控允许迁移旧测试时：

1. 把三条旧裸 float 历史夹具全部改成正式 source/topology C-L4 夹具；
2. 删除 `_LegacyAxisIdentity`、`_cluster_legacy_axis` 和 `_cluster_axis` 的 union/dispatch；
3. 令 `_cluster_axis` 的唯一签名为 occurrence + non-null topology；
4. 加 AST 锁：production AST 中 `_cluster_axis` 的每个 call 必须传 `topology`，且参数来源于
   `IdentityInputEnvelope.occurrences`；同时禁止 `float(...)` generator 作为该调用实参。

### 12.2 B conservation 零行为变化

Slice 1 没有改 `_SUBINTERVAL_SUM_TOL` 或两个 conservation helper 的任何一行。
使用相对 Slice 0 日志提交 `d20daef` 的 diff 过滤：

```bash
git diff d20daef -- src/agent/judge/segment_score.py \
  | rg '^[+-].*(_SUBINTERVAL_SUM_TOL|def _assert_target_conservation|def _assert_obs_conservation|covered > obs_length|abs\\(accounted - length\\))'
```

输出为空。最终 B-L4 也仍以原始 1-ulp 原因在原条件
`covered > obs_length` 上红，不是来源改造造成的新错误。

## 13. 写锁时新增暴露的欠规格边界

1. **C-L6 与 C-L5 的先后语义存在文字张力。** C-L5 要求无结构证书的不同来源 sub-merge
   在提交 representative 前拒绝；C-L6 又要求“既有相邻坍缩”由 post-merge validator
   承重。一个普通短边的方向轴两端没有 C-3a–d alias 证书，因此严格执行 C-L5 时会先在
   alias 门拒绝，不能自然到达 post-merge collapse。本实现：
   - 正式入口对该形状发稳定的 `score_identity_merge_collapse` certified witness；
   - 另加一个强制 representative collision 的独立 C-L6 锁，证明 post-merge checker
     自身承重。
   后续设计应明确“candidate merge 会坍缩 declared edge”是 C-3 前的独立合同 witness，
   还是新增一种结构证书后再由 C-4 拒绝；不能让施工者自行选择。
2. **C-4 claim 到 A 的过渡尚无 Slice 1 可用调用面。** 设计要求 topology/owner detector
   产 claim 并交 §4 certifier，但 `certifier.py` 明定在 Slice 2 才落。Slice 1 对不含 capability
   依赖的 exact 重复、自交、owner 冲突直接生成统一 flat certified context；capability-contingent
   pairing 仍保留旧行为，等待 Slice 2 接管。该片间 seam 必须在 Slice 2 明确收口，避免形成
   第二条本地 severity 路径。

## 14. Slice 1 边界结论

Slice 1 完成并停止。A-L3/A-L9/B-L4 保持计划内红；未开始 Slice 2。

---

# Slice 2 · 证明式仲裁（A）

## 15. 提交与工作树边界

Slice 2 主体提交：

```text
0b62a49656023060cab394188045308353464181
7.28_JudgeArbitrationSlice2ProofArbitration
```

本 slice 开工前 `git status --short`：

```text
?? AI_agent/logs/reviews/request/2026-07-28_judge_arbitration_construction_dispatch.md
```

收工（本日志提交后复核）`git status --short`：

```text
?? AI_agent/logs/reviews/request/2026-07-28_judge_arbitration_construction_dispatch.md
```

两份快照逐字相同。派工单是主控在开工前已有且本轮追加 §9 的 untracked 文件；施工未修改、
未暂存、未提交该文件。`case_tests/test_baseline/gt/` 与 `AI_agent/CLAUDE.md` 均无 diff。

## 16. Slice 2 实施面

本轮只实施设计 §7 Slice 2：

1. 新增 `src/agent/judge/certifier.py`：闭合四态 `ProofStatus`、typed
   `ConflictWitness`/`JudgeDiagnostic`/`CapabilityEnvelope`、有限 phase-ranked fact DAG、
   五个首批 predicate evaluator、请求级 root selection 与唯一 severity 出口。
2. pairing 不再只传 `category/reason`；每条 source half-edge 保留 edge id、vertex ids、
   owner、locus、ring 相邻关系，并据此形成 witness。
3. W5 unpaired advisory 形成 exact small-axis enclosure；依赖闭包可逐弧回放
   `source_coordinate -> edge_endpoint -> cut_token -> owner_atom`，运行日志带
   `capability_id`。
4. GT/product 正式 score service 共用一个 `AnalysisCollector`，两侧报告完成后只调用一次
   `certify_and_arbitrate_request`；兼容 extract wrapper 在全部 floor 后调用同一 arbiter。
5. missing evaluator 按 canonical
   `(diagnostic_id, predicate, predicate_schema_version)` 去重，逐项事件与零命中也发的 summary
   均由 `finally` 保证；注册 evaluator 返回闭集外值会抛 `ValueError`。
6. §9.2 的静态门覆盖 `identity_provenance.py`、`segment_score.py` 与
   `score_service.py`：除主控明确延期至 Slice 4 删除的 `_cluster_legacy_axis` 外，
   `scoring.input_identity` 不存在直接 `ScoreContractError` raise；所有新评分身份严重度均由
   arbiter 决定。

没有实施 Slice 3；`_SUBINTERVAL_SUM_TOL`、两个 conservation helper 与
`covered > obs_length` 未改。

## 17. A 锁实测

命令：

```bash
python -m pytest -q \
  tests/test_judge_certifier.py \
  tests/test_judge_arbitration_slice0.py \
  -k 'not b_l4'
```

最终窄测：`16 passed`。逐锁结果：

| 锁 | 实测 | 证书出口 |
|---|---|---|
| A-L1 | GREEN | advisory-only 为 NA；context 带 `w5:*` capability、complete enclosure 和 seed→相邻 endpoint→cut→owner atom arcs；derivative audit 为 `CONTINGENT` |
| A-L2 | GREEN | 1e-9 真缝为 `missing_reverse_owner / CERTIFIED_CONFLICT`；fixed edge 不含 A advisory，capability 依赖为空 |
| A-L3 | GREEN | A/B 满幅 duplicate 为 `owner_multiplicity / CERTIFIED_CONFLICT`；最小固定核心只列 A/B，不含 C |
| A-L4 | GREEN（2 参数实例） | advisory 与 duplicate 各自交换 cell 顺序，完整错误 context 字节不变 |
| A-L5 | GREEN | F1 advisory + F2 duplicate 两种楼层顺序均为 F2 identity red |
| A-L6 | GREEN | 无 witness 为 `diagnostic_evidence_incomplete / missing_witness` NA，missing-evaluator count 为 0 |
| A-L7 | GREEN | `caused_by` 去掉 dangling 派生节点；detector 顺序不改变 located root |
| A-L8 | GREEN | 最终 red 仍保留 unpaired advisory 日志的 floor、endpoint hex、capability id |
| A-L9 | GREEN | unknown evaluator 的 NA/red/registered 三路分别为 count 1/1/0；item 与 summary 均实发 |

附加绑定锁：

| 锁 | 实测 |
|---|---|
| 注册 evaluator 返回值为闭合四态；垃圾值必须 raise | GREEN |
| 五个首批 `(predicate, "1")` evaluator 精确注册 | GREEN |
| identity `ScoreContractError` 单一 raise origin AST 门 | GREEN |

Slice 0 六锁在 Slice 2 结束时：

| 锁 | 状态 | 原因 |
|---|---|---|
| A-L3 | GREEN | 固定核心 evaluator 已落地，无关 C capability 不能污染 A/B |
| A-L9 | GREEN | certifier 模块、registry 缺口计数、item/summary telemetry 均已落地 |
| B-L4 | RED | 仍为 Slice 3 的原始 1-ulp `observation_cover_exceeds_length` |
| C-L1 | GREEN | Slice 1 来源 occurrence 路径保持 |
| C-L7 | GREEN | Slice 1 ring identity checker 保持，且 predicate 精确为 `ring_identity_conflict` |
| C-L11 | GREEN | Slice 1 exact-string contract version 保持 |

因此本 slice 合法转绿的是 A-L3、A-L9；C 三锁是上个 slice 已转绿并保持；B-L4 未提前处理。

## 18. 全仓实测与回归修正

第一次全仓在主体收敛前实测：

```text
4 failed, 1755 passed, 10 xfailed, 150 warnings in 265.49s (0:04:25)
```

除计划内 B-L4 外，三条既有 B5 admission 锁因 context 从历史
`{"reason": ...}` 被扩成证书 context 而失败：

```text
tests/test_c2_b5_parent_and_verts.py::test_judge_official_score_service_requires_verified_artifact_input
tests/test_c2_b5_parent_and_verts.py::test_judge_rejects_verified_output_hash_different_from_product_identity
tests/test_c2_b5_parent_and_verts.py::test_judge_rejects_payload_different_from_verified_output
```

修正方式不是恢复本地 severity：这三条纯 schema/cryptographic admission fact 仍调用同一
arbiter，但 arbiter 按既有合同保留 reason-only context。三条及全部新锁窄回归：

```text
19 passed
```

修正后第二次全仓最终 tail：

```text
=========================== short test summary info ============================
FAILED tests/test_judge_arbitration_slice0.py::test_b_l4_three_adjacent_spans_do_not_false_red_and_have_exact_ledger
1 failed, 1758 passed, 10 xfailed, 150 warnings in 259.00s (0:04:19)
```

B-L4 的 verbatim 数值与失败条件：

```text
obs_length = 20.861502717932574
covered    = 20.861502717932577
if covered > obs_length:
    raise ScoreContractError(
        "score_denominator_nonconserving",
        "scoring.denominator_totality",
        context={
            "reason": "observation_cover_exceeds_length",
            ...
            "excess": 3.552713678800501e-15,
        },
    )
```

相对 Slice 1 `3 failed, 1745 passed, 10 xfailed`：

- A-L3、A-L9 从 failed 转 passed；
- 新增 11 个 Slice 2 测试实例全部 passed；
- B-L4 保持同原因 failed；
- 其余 1745 个既有 passed 与 10 个 xfailed 均未改变状态。

## 19. `/tmp` neuter 自检

执行副本：

```text
/tmp/judge-slice2-neuters.XBHh6A/repo
```

该副本从 `0b62a49656023060cab394188045308353464181` clone；每项 patch 后只跑指定锁，
随后 `git restore`。全部执行结束后副本 `git status --short` 为空，工作树从未带入 neuter
状态。

### 19.1 A-L1 · 切断相邻 endpoint / T-junction cut 传播

实际执行 patch：

```diff
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
     endpoint_ids: list[tuple[object, ...]] = []
     for edge_id, endpoint, seed, value in endpoint_rows:
         fact_id = ("edge_endpoint", edge_id, endpoint, small_axis)
+        operands = (seed,) if edge_id == claim.edge_id else ()
         graph.add(
             FactNode(
                 fact_id,
                 "edge",
-                (seed,),
+                operands,
                 enclosure,
             )
         )
*** End Patch
```

命令：

```bash
python -m pytest -q -n0 \
  tests/test_judge_certifier.py::test_a_l1_advisory_derivative_is_contingent_with_replayable_fact_arcs
```

实测：`1 failed`；失败在
`assert ("edge_endpoint", "cut_token") in tags`，实际只剩
`source_coordinate -> edge_endpoint`。

### 19.2 A-L2/A-L3 · 同 floor 任一 capability 污染所有 witness（共享 guard）

实际执行 patch：

```diff
*** Begin Patch
*** Update File: src/agent/judge/certifier.py
@@
     dependent = _dependent_facts(capabilities)
+    if capabilities:
+        return ProofStatus.CONTINGENT
@@
 def evaluate_owner_multiplicity(
@@
     dependent = _dependent_facts(capabilities)
+    if capabilities:
+        return ProofStatus.CONTINGENT
*** End Patch
```

命令：

```bash
python -m pytest -q -n0 \
  tests/test_judge_certifier.py::test_a_l2_fixed_gap_witness_is_disjoint_from_advisory_enclosure \
  tests/test_judge_arbitration_slice0.py::test_a_l3_genuine_duplicate_with_unrelated_advisory_is_certified_red
```

实测：`2 failed`；两锁都从预期 identity red 退化为
`score_unsupported_combination`。按设计如实记为一个局部污染 guard，不虚报两个独立机制。

### 19.3 A-L4 · 恢复 detector/list 首项决定证书

实际执行 patch：

```diff
*** Begin Patch
*** Update File: src/agent/judge/certifier.py
@@
-    ordered_diagnostics = tuple(sorted(diagnostics, key=_diagnostic_sort_key))
+    ordered_diagnostics = tuple(diagnostics)
@@
-            selected = min(roots or [item for item, _ in certified], key=_diagnostic_sort_key)
+            selected = (roots or [item for item, _ in certified])[0]
*** Update File: src/agent/judge/segment_score.py
@@
-    selected = tuple(sorted(claims, key=lambda item: repr(item.edge_id)))
+    selected = tuple(claims)
*** End Patch
```

命令：

```bash
python -m pytest -q -n0 \
  tests/test_judge_certifier.py::test_a_l4_cell_order_does_not_change_selected_certificate
```

实测：`2 failed`；advisory 与 duplicate 两个参数实例的完整 context 都随 cell 顺序变化。

### 19.4 A-L5 · 恢复 floor loop 内立即仲裁

实际执行 patch：

```diff
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
         analysis.extend(
             (item.as_judge_diagnostic() for item in diagnostics),
             capabilities,
         )
+        certify_and_arbitrate_request(
+            diagnostics=analysis.diagnostics,
+            capabilities=analysis.capabilities,
+            evaluator_registry=DEFAULT_EVALUATOR_REGISTRY,
+            request_key=("neuter", "per-floor"),
+            identity_code="score_product_identity_invalid",
+        )
         for p1, p2, owners in pairs:
*** End Patch
```

该 patch 实际施加于 `extract_correction_plan_segments` 的 product block。命令：

```bash
python -m pytest -q -n0 \
  tests/test_judge_certifier.py::test_a_l5_all_floors_report_before_request_arbitration
```

实测：`1 failed`；F1 先出现时立即抛 NA，洗掉 F2 的认证 duplicate。

### 19.5 A-L6 · 无 witness 默认定罪

实际执行 patch：

```diff
*** Begin Patch
*** Update File: src/agent/judge/certifier.py
@@
             witness = diagnostic.witness
             if witness is None:
-                uncertain.append(diagnostic)
+                raise ScoreContractError(
+                    diagnostic.requested_code,
+                    diagnostic.gate_id,
+                    context={"reason": diagnostic.reason},
+                )
*** End Patch
```

命令：

```bash
python -m pytest -q -n0 \
  tests/test_judge_certifier.py::test_a_l6_missing_witness_is_na_without_missing_evaluator_count
```

实测：`1 failed`；实际 code 从预期 unsupported 变成
`score_product_identity_invalid`。

### 19.6 A-L7 · 删除 caused-by root 消解并恢复列表首项

实际执行 patch：

```diff
*** Begin Patch
*** Update File: src/agent/judge/certifier.py
@@
 def _root_diagnostics(
     certified: list[JudgeDiagnostic],
 ) -> list[JudgeDiagnostic]:
-    ids = {item.diagnostic_id for item in certified}
-    derivative_ids = {
-        item.diagnostic_id
-        for item in certified
-        if any(parent in ids for parent in item.caused_by)
-    }
-    return [item for item in certified if item.diagnostic_id not in derivative_ids]
+    return certified
@@
-    ordered_diagnostics = tuple(sorted(diagnostics, key=_diagnostic_sort_key))
+    ordered_diagnostics = tuple(diagnostics)
@@
-            selected = min(roots or [item for item, _ in certified], key=_diagnostic_sort_key)
+            selected = (roots or [item for item, _ in certified])[0]
*** End Patch
```

命令：

```bash
python -m pytest -q -n0 \
  tests/test_judge_certifier.py::test_a_l7_caused_by_root_is_stable_under_detector_order
```

实测：`1 failed`；交换输入后 root 从 located conflict 变为 dangling derivative。

### 19.7 A-L8 · 丢弃 unpaired advisory 运行日志

实际执行 patch：

```diff
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
 def _log_advisory_hit(
@@
 ) -> None:
@@
-    event = "near_orthogonal_advisory_unpaired" if unpaired else "near_orthogonal_advisory_hit"
+    if unpaired:
+        return
+    event = "near_orthogonal_advisory_unpaired" if unpaired else "near_orthogonal_advisory_hit"
*** End Patch
```

命令：

```bash
python -m pytest -q -n0 \
  tests/test_judge_certifier.py::test_a_l8_red_request_keeps_advisory_log_with_capability_id
```

实测：`1 failed`；结构化 event 列表为空。

### 19.8 A-L9 · missing evaluator 只 NA、不累计也不发逐项事件

实际执行 patch：

```diff
*** Begin Patch
*** Update File: src/agent/judge/certifier.py
@@
             evaluator = evaluator_registry.get(key)
             if evaluator is None:
-                missing.append((diagnostic, key[0], key[1]))
                 uncertain.append(diagnostic)
@@
-                _logger.info(
-                    "judge_certifier_missing_evaluator",
-                    extra={
-                        "event": "judge_certifier_missing_evaluator",
-                        "request_key": request_key,
-                        "side": diagnostic.side,
-                        "floor_id": diagnostic.floor_id,
-                        "diagnostic_id": diagnostic.diagnostic_id,
-                        "predicate": key[0],
-                        "predicate_schema_version": key[1],
-                        "requested_code": diagnostic.requested_code,
-                        "resolution": "diagnostic_evidence_incomplete",
-                    },
-                )
                 continue
*** End Patch
```

命令：

```bash
python -m pytest -q -n0 \
  tests/test_judge_arbitration_slice0.py::test_a_l9_missing_evaluator_is_counted_for_na_red_and_registered_paths
```

实测：`1 failed`；逐项事件从 1 变 0。此为行为级 neuter，已消除 Slice 0
`ModuleNotFoundError` 弱信号。

### 19.9 闭 enum、五 evaluator 与单一 raise origin 附加门

闭 enum neuter：

```diff
*** Begin Patch
*** Update File: src/agent/judge/certifier.py
@@
     except (TypeError, ValueError) as exc:
-        raise ValueError(f"registered evaluator returned invalid proof status: {value!r}") from exc
+        return ProofStatus.UNPROVEN
*** End Patch
```

命令：
`python -m pytest -q -n0 tests/test_judge_certifier.py::test_registered_evaluator_result_is_a_closed_enum`
；实测 `1 failed`，垃圾状态降为 unsupported，没有抛预期 `ValueError`。

五 evaluator registry neuter：

```diff
*** Begin Patch
*** Update File: src/agent/judge/certifier.py
@@
-    ("segment_merge_conflict", "1"): evaluate_segment_merge_conflict,
*** End Patch
```

命令：
`python -m pytest -q -n0 tests/test_judge_certifier.py::test_first_five_predicate_evaluators_are_registered`
；实测 `1 failed`，缺少 `segment_merge_conflict`。

单一出口 AST neuter：

```diff
*** Begin Patch
*** Update File: src/agent/judge/segment_score.py
@@
 def _arbitrate_pairing_diagnostics(diagnostics: list[_PairDiagnostic], *, identity_code: str) -> None:
@@
+    if diagnostics and diagnostics[0].category == "identity":
+        raise ScoreContractError(
+            identity_code,
+            "scoring.input_identity",
+            context=diagnostics[0].context,
+        )
     claims = tuple(
*** End Patch
```

命令：
`python -m pytest -q -n0 tests/test_judge_certifier.py::test_identity_scorecontracterror_has_one_raise_origin_except_slice4_legacy`
；实测 `1 failed`，AST 精确报出额外
`("segment_score.py", "_arbitrate_pairing_diagnostics")`。

## 20. sm24 受保护树 manifest

命令：

```bash
find case_tests/test_baseline/gt/sm24_anchor -type f -print0 \
  | sort -z | xargs -0 sha256sum
git diff --quiet -- case_tests/test_baseline/gt AI_agent/CLAUDE.md
```

Slice 2 结束值与 Slice 0/1 起始 manifest 逐项相同：

```text
5a8dcba5ab4f5b2b5dc30df91896eeee50e01f9a5bf06ec1b379101a4d16d420  gt.json
7d4c1ed09f31377253838445733a130c11ff2fedf5ca95ddcdd231a7439abe03  renders/gt_elev.png
2ba9dd15497dc935e9a5e6499ef632ae0034179edb0b44164bfbc5025e655bd7  renders/gt_plan.png
135e2995a07e5acf6ed5d878f7e7d0acfc1baef1fdc3e8a687dd8fada705c675  renders/overlay_1f_view.png
ae69b4276567305dfc9b9145a9a1f2b28593b399a28090d09004a626bd6ed366  renders/overlay_East_view.png
d4a99cca3128e0335fed6bc7f76bb6c9bd700ab155a61eda7f2de5b8ed7be957  renders/overlay_North_view.png
0e66297543fcaecb0899018af25715197538b37373d555c0fc47a46b3f83302e  renders/overlay_South_view.png
a782dd82fa4c309c0893cdf16b8b1dd6a917825ba4ea0dde37ab893d6eba6375  renders/overlay_West_view.png
25e7d077c169eb087f1c3b477a1f919e1d8d4a4ad76b3d4931c0894ce125873e  review/conversion_report.json
bd1d7efea498e50ca47dd0144a0c9a1720d68f72e97fda3cd4faf78cf7fb6b70  review/opening_elevation_audit.json
f602d80287e64264df2c724dcd9941c29aec93c920c38ece91d885df1ad7e470  review/review_ack.json
9341cd4ee2fd122a27d41c75a03b92cb15b31f7e474334c1c57f07854c76e457  review/review_annotations.json
edb99f09f97348a29d414d6bee81ac946a1afc619d297d6b88d0036d03413030  review/review_index.json
b76c35c4ed215814f1f1a1c70e2cfeda65efc9e3b0f53054f48f082c97291a89  score_inputs/view_bindings.json
```

比较结论：manifest byte-identical；保护树和 `AI_agent/CLAUDE.md` 均未修改。

## 21. 写锁时暴露的欠规格边界

1. **既有 B5 admission error 的 context 与 §8 flat identity context 的适用域有冲突。**
   三条不可改旧锁逐字要求 `{"reason": ...}`，而 §8.4 说 identity raise 的 minimum fields
   必须集中定义且 raise 时完整。实际施工只能同时保住“单一 severity 出口”和旧锁：
   schema/cryptographic admission fact 仍由 arbiter raise，但 arbiter 对这三条保留 exact
   reason-only context；拓扑/owner/scoring-identity 证书出口继续强制完整 flat key set。
   设计稿没有明确 admission fact 是否属于 §8.4 的“identity-class”范围；本轮不静默扩大旧
   context，需主控裁定长期是否把 admission 与 scoring-identity evidence 分成两个命名合同。
2. **“所有 floor 先报告”对 C-0..C-3 纯输入合同失败的继续扫描边界没有写清。**
   pairing/C-4 的所有 floor 及正式 GT+product 已先报告后仲裁；但 adapter version、来源碰撞、
   护带等纯输入合同 fact 在 helper 内会立即调用同一个 arbiter，不会在一个已经不可重建的
   floor 上继续跑后续 detector。severity 决定仍只有 arbiter 一处，因此不构成第二条本地
   severity 路径；但若“所有 floor”也要求在 C-0..C-3 失败后容错扫描剩余 floor，则需要设计
   一个 typed abort/report boundary，不能让施工者猜测是否在不完整 source document 上继续。
3. **§9.2 AST 门与 §9.1 legacy float 延期存在有意例外。** 当前 AST 明确只放行
   `_cluster_legacy_axis` 的 direct identity raises，并把例外写进测试说明；它不是已解决。
   Slice 4 必须按主控 deadline 迁移三条历史锁、删除整个 legacy type/dispatch，再把 AST 预期
   收紧为零例外。

## 22. Slice 2 边界结论

Slice 2 完成并停止。A-L1 至 A-L9 及 §9 附加门全部承重；B-L4 保持 Slice 3 原始红。
未开始 Slice 3，等待主控 light gate。
