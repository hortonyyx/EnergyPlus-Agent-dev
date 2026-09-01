# 跨家族复核裁决 · 模块 4 返工件

- 日期：2026-09-01
- 施工方：GLM 家族
- 复核方：GPT 家族
- 被审 commit：`a13120d`
- 审查范围：`src/agent/correction/wall_compiler.py`、`tests/test_o22m4_wall_compiler.py`

## 1. 裁决

**REWORK（阻断 1 条 / 不阻断 1 条）**。

原阻断 M7 已被有效补上：在父提交上摘掉 `_compile_single_face` 的 open item 仍是
`43 passed`，在返工提交上同一变异精准使 5 条新增测试全红；三种
`counterface_state`、有候选、无候选、候选 provenance、显式 decision 半边均已有实测牙。

但是返工单验收 3 的“候选被筛成唯一时仍开项”没有被永久夹具量到。
提交内 B 锁实际造的是“一种厚度值、正负两个候选”，不是“一个候选”。我注入真正的
`len(candidates) == 1 => 静默自动执行` 后，提交内 27 条仍全绿；同一实现配上复核方临时的
“枚举器只返回一个候选”夹具后才变红。代理量没有证明目标量，因此本件不能批准。

### 阻断 F-1 · B 把“唯一厚度值”当成“唯一候选”

提交内 B 的产品事实是：

```text
thickness values = {0.2}
symbolic operations = {OFFSET_POSITIVE, OFFSET_NEGATIVE}
candidate count = 2
```

承重变异（在 `_compile_single_face` 生成 `wall` 后注入）：

```python
if len(candidates) == 1:
    chosen = candidates[0]
    wall = wall.model_copy(update={
        "resolved_centerline": _support_line(
            axis, chosen.preview_constant_pos_m, along
        ),
        "output_basis": "wall_axis",
        "resolved_thickness_m": chosen.thickness_source.value_m,
    })
    return wall, [], []
```

提交内全文件实测原文：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
bringing up nodes...
bringing up nodes...

...........................                                              [100%]
27 passed in 9.58s
```

所以 B 的“单尺度”读数达标，不能推出“单候选仍开项”。修法很小：永久加入一条真实量
`len(item.candidates) == 1` 的夹具（可以让被测枚举器在该测试中提供一候选），断言 item 仍开、
墙仍无轴/厚度/output basis、无 auto action；并用上面的变异证明它红。

复核方临时精确夹具的正反读数：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6 \
    -k crossreview_genuinely_single_candidate_stays_open
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
1 passed in 4.91s
```

加上同一 `len(candidates) == 1` 静默自动执行变异后：

```text
FAILED tests/test_o22m4_wall_compiler.py::test_crossreview_genuinely_single_candidate_stays_open
1 failed in 6.08s
```

临时夹具和生产变异均已按文件名还原，未留在树上。

### 不阻断 N-1 · `why_not_auto_resolved` 的两支解释无牙

把 `_compile_single_face` 的 `if candidates:` 反成 `if not candidates:`，有候选 item 得到
“NO thickness scale”，无候选 item 得到“symbolic offsets are enumerable”，但全部测试仍绿：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
bringing up nodes...
bringing up nodes...

...........................                                              [100%]
27 passed in 9.50s
```

核心状态边界、候选集和合法退出行为已有牙，因此本条不单独阻断；建议在修 F-1 时给两支各加一条
对 `why_not_auto_resolved` 的语义断言，避免 decision packet 携带事实相反的解释。

## 2. 三格读数

| 格 | 输入/变异 | 结果 | 结论 |
|---|---|---|---|
| ① 历史前提 | `a6f5383` 的旧测试 + M7 摘开项 | `43 passed` | 缺陷当时真实存在 |
| ② 返工样例 | `a13120d` + 同一 M7 | `5 failed, 22 passed`，五条新增锁全红 | 原例已修 |
| ③ 复核方同形输入 | `observed_unclaimed` 指向 `ambiguous` disposition，`exploratory` 编译 | 原码 `1 passed`；M7 后 `1 failed` | 另一合法进入形态也守住状态边界 |

### 格 ① · 父提交

```text
$ git checkout a6f5383 -- tests/test_o22m4_wall_compiler.py
$ # _compile_single_face: return wall, [item], [] -> return wall, [], []
$ python -m pytest tests/test_o22m4_wall_compiler.py \
    tests/test_o22m3_evidence_adapters.py -q -n 6
bringing up nodes...
bringing up nodes...

...........................................                              [100%]
43 passed in 10.92s
$ git checkout -- src/agent/correction/wall_compiler.py
$ git checkout HEAD -- tests/test_o22m4_wall_compiler.py
```

### 格 ② · 返工提交

```text
$ # 同一 M7
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
bringing up nodes...
bringing up nodes...

....................FFFFF..                                              [100%]
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_without_any_scale_opens_with_empty_candidates
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_real_l012_opens_axis_item_with_both_offset_families
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_observed_unclaimed_counterface_still_no_silent_axis
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_unique_thickness_scale_still_requires_a_decision
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_ink_present_unpromoted_witness_still_no_silent_axis
5 failed, 22 passed in 9.60s
$ git checkout -- src/agent/correction/wall_compiler.py
```

五条失败都发生在新增区，既有 22 条仍绿。

### 格 ③ · 复核方自己找的形态

我没有复用 D1 的 `non_wall` counterface，而是造合法的
`counterface_state="observed_unclaimed"` +
`counterface_disposition_status="ambiguous"`，用 `exploratory` 越过该 ambiguous debt 的 strict gate。

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6 \
    -k crossreview_alt_single_face_with_ambiguous_counterface
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
1 passed in 5.01s
```

同一 M7 后：

```text
FAILED tests/test_o22m4_wall_compiler.py::test_crossreview_alt_single_face_with_ambiguous_counterface
1 failed in 5.47s
```

这条临时测试也已还原。

## 3. 四条通道的承重不变量变异

统一命令：

```text
python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
```

| 通道 | 承重变异 | 实测原文 | 结论 |
|---|---|---|---|
| `_compile_paired` | 中线由 `(pos_a + pos_b) / 2` 改取 `pos_a` | `FAILED ...::test_paired_face_unshared_tail_survives_as_single_face_fragment` / `1 failed, 26 passed in 9.72s` | 有牙 |
| `_compile_solid_band` | 中线由 `(lo + hi) / 2` 改取 `lo` | `FAILED ...::test_sm24_four_solid_bands_become_walls_without_fake_faces` / `1 failed, 26 passed in 9.53s` | 有牙 |
| `_compile_single_face` | `return wall, [item], []` 改为 `return wall, [], []` | 五条新增测试全红 / `5 failed, 22 passed in 9.60s` | 有牙 |
| `_compile_legacy_trace` | structured centerline 的 `output_basis="wall_axis"` 改成 `None` | `FAILED ...::test_structured_centerline_is_the_one_legal_identity` / `1 failed, 26 passed in 9.51s` | 有牙 |

所有变异后均立即执行：

```text
git checkout -- src/agent/correction/wall_compiler.py
```

没有使用 `git checkout -- .`。

## 4. 至少 5 条新增锁的独立变异实测

以下不是只数 22→27；每条都反掉它声称保护的量。

### A · 真实 L012 候选 provenance

变异：single-face sources 的 `declared_callout` 改为 `matched_label`。

```text
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_real_l012_opens_axis_item_with_both_offset_families
1 failed, 26 passed in 9.67s
```

失败断言原文：

```text
assert all(c.thickness_source.provenance == "declared_callout"
           for c in item.candidates)
E assert False
```

### B · 单尺度不得静默执行（提交内锁实际能量到的形态）

变异：当所有候选共享一个 thickness value 时，静默选正向候选并返回，无 open item。

```text
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_unique_thickness_scale_still_requires_a_decision
1 failed, 26 passed in 9.78s
```

该锁对“单尺度启发式自动执行”有牙；但它不是验收要求的“单候选”，故仍有 F-1。

### C · 空候选不得静默退出

变异：`if not candidates: return wall, [], []`。

```text
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_ink_present_unpromoted_witness_still_no_silent_axis
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_without_any_scale_opens_with_empty_candidates
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_observed_unclaimed_counterface_still_no_silent_axis
3 failed, 24 passed in 9.30s
```

### D1 · `observed_unclaimed` 不得分叉成静默路径

变异：该状态直接 `return wall, [], []`。

```text
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_observed_unclaimed_counterface_still_no_silent_axis
1 failed, 26 passed in 9.27s
```

### D2 · `ink_present_unpromoted` 不得分叉成静默路径

变异：该状态直接 `return wall, [], []`。

```text
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_ink_present_unpromoted_witness_still_no_silent_axis
1 failed, 26 passed in 9.32s
```

### 横切锁 · `IDENTITY_BAN`

变异：single-face item 的 `exclusions=(IDENTITY_BAN,)` 改为 `exclusions=()`。

```text
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_observed_unclaimed_counterface_still_no_silent_axis
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_real_l012_opens_axis_item_with_both_offset_families
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_ink_present_unpromoted_witness_still_no_silent_axis
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_unique_thickness_scale_still_requires_a_decision
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_without_any_scale_opens_with_empty_candidates
5 failed, 22 passed in 9.68s
```

## 5. 施工方点名两处的逐条结论

### 5.1 D 夹具的“手换”性质

结论：**作为 compiler 契约形态测试有效，但不是 producer/adapter 端到端可达性证明。**

- D1、D2 都先由 adapter 产出合法 bundle，再只替换 single-face claim，并重新
  `finalize_bundle`；`validate_evidence_bundle` 通过。
- 对两个状态分别注入静默分叉后，各自精准 1 红，说明不是只改了测试名字。
- D1 的 `non_wall` 形态之外，我另造 `ambiguous` disposition，同样原码绿、M7 红。
- D2 的 witness 只证明 schema 要求的 pointer 可解析；它指向现有 face 的 `runs_px`，不证明
  当前 producer 真能结构化地产生“未晋升 counterface ink”。施工方已如实自报，且 producer
  reachability 不在本次仅补 compiler 测试的范围，因此不另计阻断。

另核实：契约现在是三种 `counterface_state`，不是早期设计的两种；A/B/C 覆盖
`not_in_observations`，D1/D2 覆盖另外两种。

### 5.2 “前提复现逐字对齐 260/16/0/35”

结论：**独立复跑属实。** 我没有采用执行档的同进程 monkeypatch，而是在四个生产入口临时写入
进程安全的小行标记，以 `-n 6` 跑两个定向文件，随后 `sort | uniq -c`；每次立即还原源文件。

父提交测试库存原文：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py \
    tests/test_o22m3_evidence_adapters.py -q -n 6
...........................................                              [100%]
43 passed in 10.25s
$ sort /tmp/o22m4_gpt_channel_probe_old_20260901c.log | uniq -c
     35 _compile_legacy_trace
    260 _compile_paired
     16 _compile_solid_band
```

`_compile_single_face` 没有任何标记行，即 **0**。读数为 **260 / 16 / 0 / 35**。

返工提交库存原文：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py \
    tests/test_o22m3_evidence_adapters.py -q -n 6
................................................                         [100%]
48 passed in 10.17s
$ sort /tmp/o22m4_gpt_channel_probe_20260901c.log | uniq -c
     35 _compile_legacy_trace
    302 _compile_paired
      8 _compile_single_face
     16 _compile_solid_band
```

与执行档的 **302 / 16 / 8 / 35** 也一致。第一次用直写 `open(` 的探针按预期触发了既有
“模块不得文件 I/O”源码扫描锁（`1 failed, 47 passed`）；我先查 status、只还原
`wall_compiler.py`，再改用不含该禁词的等价临时探针取得上面的全绿读数。该红是探针自诱发，
不是本件回归。

## 6. 复现命令

机械前提与基线：

```bash
git log --oneline -1
git status --porcelain
git rev-parse --short a13120d^
git diff --stat 636ce56..a6f5383 -- src tests
git diff --stat 636ce56..a6f5383 -- \
  src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
git diff --stat a6f5383..a13120d -- \
  src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
git diff --stat a13120d..HEAD -- \
  src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
git show a6f5383:tests/test_o22m4_wall_compiler.py | rg -c '^def test_'
git show a13120d:tests/test_o22m4_wall_compiler.py | rg -c '^def test_'
python -m pytest tests/test_o22m4_wall_compiler.py \
  tests/test_o22m3_evidence_adapters.py -q -n 6
sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
```

每个生产变异都按 §3/§4 所列精确替换一处，然后运行：

```bash
python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
git checkout -- src/agent/correction/wall_compiler.py
```

历史格还原命令：

```bash
git checkout a6f5383 -- tests/test_o22m4_wall_compiler.py
# 临时施加 M7，然后跑两个文件
python -m pytest tests/test_o22m4_wall_compiler.py \
  tests/test_o22m3_evidence_adapters.py -q -n 6
git checkout -- src/agent/correction/wall_compiler.py
git checkout HEAD -- tests/test_o22m4_wall_compiler.py
```

终验：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py \
    tests/test_o22m3_evidence_adapters.py -q -n 6
bringing up nodes...
bringing up nodes...

................................................                         [100%]
48 passed in 10.33s
```

全程未跑全量、未用 `-n auto`、未运行任何 `pip install`、未改 site-packages。

## 7. 哨兵与工作树

开工哨兵：

```text
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
```

交件前哨兵：

```text
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
```

写裁决前：

```text
$ git status --porcelain
（空）
```

写裁决后、最终交件前：见下方最终状态块。

```text
$ git status --porcelain
?? AI_agent/logs/reviews/verdict/2026-09-01c_o22m4_rework_crossreview_gpt.md
```

模块 4 两文件终验仍零 diff：

```text
$ git diff --stat a13120d..HEAD -- \
    src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
（空）
```

## 8. 这份复核单哪里写错了

**无。** 当前版本点名的 commit、父提交、链路、文件、`+264`、22→27、启动 HEAD、模块 4
两文件零 diff 与哨兵均亲手核过并吻合。原返工单沿用“两种 `counterface_state`”是旧口径偏差，
施工执行档已经按当前契约的三种值补齐；这不是当前复核单的新错误。

## 附：开工机械核验原文

```text
$ git log --oneline -1
3f455da 09.01o_Error66_EveryGitDerivedFactInADispatchMustBeRunFirst
$ git status --porcelain
（空）
$ git rev-parse --short a13120d^
a6f5383
$ git diff --stat 636ce56..a6f5383 -- src tests
（空）
$ git diff --stat 636ce56..a6f5383 -- \
    src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
（空）
$ git diff --stat a6f5383..a13120d -- \
    src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
 tests/test_o22m4_wall_compiler.py | 264 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 264 insertions(+)
$ git diff --numstat a6f5383..a13120d -- \
    src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
264	0	tests/test_o22m4_wall_compiler.py
$ git show a6f5383:tests/test_o22m4_wall_compiler.py | rg -c '^def test_'
22
$ git show a13120d:tests/test_o22m4_wall_compiler.py | rg -c '^def test_'
27
```
