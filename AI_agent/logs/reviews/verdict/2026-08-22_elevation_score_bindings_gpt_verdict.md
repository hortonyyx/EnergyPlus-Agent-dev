# 跨家族复核裁决 · 立面判卷绑定（2026-08-22）

**复核席位**：GPT 家族（gpt-5.6-sol）  
**依据**：原始派工单、当前未提交 diff、新增测试、权威实现路径，以及本席独立实测。  
**未读取/未采信**：施工方执行日志 `2026-08-22_elevation_bindings_glm_execution.md`。

## 裁决：**REWORK**

**0 BLOCKER · 2 MAJOR · 2 MINOR**。

sm24 主目标本身成立：生成器重产的 5 条绑定与既有参照 5/5 相等；真实判卷入口得到
`kind=c2_scored`、elevation `applicable`、`window_elevation_geometry=44/44 pass`；镜像门在正常产物和
独立构造的非镜像产物上沉默、在反射坏夹具上报红；全量也与声称的 3006/13 完全对账。

不能 APPROVE 的原因是：显式的 pending-S1 旗标会以 exit 0 产出一份通过 frozen loader 和 GT companion
validator、但被权威 Va 消费者拒收的绑定；同时 `along_origin` 的跨层并集算法不满足 Va 的逐层严格相等契约。
这两项应修后复核。

---

## Findings

### MAJOR-1 · `--elevation-fingerprint-union-pending-s1` 会成功写出不可用绑定

该旗标把未拍板的“指纹集合哈希”写进一个普通 `Hex64` 字段，产物里没有可机器识别的 pending 状态；CLI
exit 0、stderr 为空。冻结加载器和 `validate_score_view_bindings_against_gt` 都接受它，直到权威 Va
`derive_reference_ledger` 才报 `va_projection_frame_invalid`。若不显式给 `--out`，它还会直接覆盖 run 的
`_run/judge_score_bindings.json`。这正是一条“成功产出、延后失败”的静默不可用路径。

实测命令：

```bash
python scripts/tool_scripts/build_score_view_bindings.py \
  --run-dir case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H2_fullcase \
  --gt case_tests/test_baseline/gt/sm25-L_anchor/gt.json \
  --elevation-fingerprint-union-pending-s1 --out /tmp/judge_score_bindings.json
# 随后用 load_score_view_bindings、validate_score_view_bindings_against_gt、
# derive_reference_ledger 依次消费同一文件。
```

输出：

```text
CLI returncode= 0
CLI stdout= {"bindings": ["1f_view", "2f_view", "East_view", "North_view", "South_view", "West_view"],
 "content_sha256": "c1690d6f9acddec33046d8d65d08eee870d7139f55dbfdc7db24a18a01623974", ...}
CLI stderr= <empty>
frozen loader=PASS
GT companion validator=PASS
authoritative Va consumer=FAIL FacadeApplicabilityInvariantError
  va_projection_frame_invalid: {'input_id': 'South_view', 'floor_id': 'F1'}
```

默认路径确实 fail closed：

```text
sm25_default build=REFUSED error= East_view: 'East' facade floors ['F1', 'F2'] carry DIFFERENT
footprint fingerprints [...] which one ... is dispatch §五 S1 and is NOT yet ratified
```

建议：在 S1 拍板且下游契约能消费前删除该旗标，或至少让它拒绝写出正式
`JudgeScoreViewBindingsV1`。仅在 help/docstring 写 “pending” 不足以使产物安全。

### MAJOR-2 · P4 不成立：跨层并集 `along_origin` 与 Va 的逐层契约不等价

`build_score_view_bindings.py:124-139` 对所有楼层的 segment 求 union；但校正侧
`window_sources.py:1200-1208` 先要求每层完整 extent 全部相等，再从那一个 extent 取端点；Va
`facade_applicability.py:462-465` 则对每个 opening 的宿主层重新取端点并用严格 `==` 比较。单层时两者一致是
必然退化，不是算法等价的证据。

独立枚举 sm25 每层 extent、生成器 origin 与 Va 期望：

```text
East  sign= 1  per_floor_extents={'F1': (-3.552713678800501e-15, 19.999999999999996),
                                  'F2': (-3.552713678800501e-15, 19.999999999999996)}
      builder_union_origin=-3.552713678800501e-15  all_match=True
North sign=-1  per_floor_extents={'F1': (0.0, 25.0),
                                  'F2': (-3.552713678800501e-15, 24.999999999999996)}
      builder_union_origin=25.0
      Va_expected_origins={'F1': 25.0, 'F2': 24.999999999999996}  all_match=False
South sign= 1  per_floor_extents={'F1': (0.0, 25.0),
                                  'F2': (-3.552713678800501e-15, 24.999999999999996)}
      builder_union_origin=-3.552713678800501e-15
      Va_expected_origins={'F1': 0.0, 'F2': -3.552713678800501e-15}  all_match=False
West  sign=-1  ... all_match=True
```

这不是只由 MAJOR-1 的指纹旗标造成的：若后续 S1 仅把近等 footprint 的指纹规范化为一致、却保留当前
`world_along_interval` 浮点值，默认生成器就会越过指纹门，继续产出 North/South 的无效 origin。

建议：像 `materialize_current_ring_va_elevation_bindings` 一样先构造 per-floor extents，并在不一致时
fail closed；至少也必须证明 sign 所选端点在每层逐位相同。不要用跨层 union 冒充校正侧算法。

### MINOR-1 · P6 的 schema 理由字面不成立（本批生成值仍正确）

sm24/sm25 manifest 的四个立面确实都是 `direction_semantics=building_axis`，GT 也确实是
`north_axis_deg=None / coordinate_frame=building_axis_world_m`；生成器写两字段为 `None` 是正确结果。
但 `ElevationScoreViewBindingV1._frame_source_contract` 用
“`orientation_output_hash` 与 `adapter_version` **同时**非空”定义 `has_orientation`，所以 manifest 路径
只填一个字段时 schema 会接受，judge 侧 `validate_score_view_bindings` 也会接受；是 Va 后面才拒绝。

实测：

```text
P6 one-sided manifest orientation: JudgeScoreViewBindingsV1=ACCEPTED
P6 one-sided manifest orientation: validate_score_view_bindings=PASS
P6 one-sided manifest orientation: Va live path=FAIL FacadeApplicabilityInvariantError
  va_direction_unresolved: {'input_id': 'East_view'}
```

这是原有 schema/premise 缺口，不会改变本批生成器两字段都为 `None` 的正确性。建议后续把“两字段成对出现”
和 manifest 路径“两者必须 None”直接锁在 schema/judge validator。

### MINOR-2 · `test_va_neuter_removes_the_sign_wiring` 没有测试 live wiring

该测试 monkeypatch `fa._validate_bindings` 后直接调用同一个已 monkeypatch 的 helper；它从未调用
`derive_opening_claim_applicability`。因此真实入口摘线后，它仍然绿。好消息是相邻的
`test_va_rejects_flipped_sign_through_real_entry` 确实能抓住摘线，功能锁网没有漏。

本席临时把 `facade_applicability.py` 真实入口中的：

```python
bindings = _validate_bindings(manifest, elevation_views)
```

改成：

```python
bindings = {binding.input_id: binding for binding in elevation_views}
```

同时跑两条测试，输出：

```text
.F
FAILED test_va_rejects_flipped_sign_through_real_entry
  Failed: DID NOT RAISE FacadeApplicabilityInvariantError
1 failed, 1 passed in 6.30s
```

其中那个 `1 passed` 正是名为 `test_va_neuter_removes_the_sign_wiring` 的测试。恢复后同命令：

```text
..  2 passed in 6.10s
```

建议把 neuter 测试的最后一步改为调用真实 `derive_opening_claim_applicability`，而不是直接调用被替换的 helper。

---

## 六条重点证伪结论

### 1. 镜像门：通过

用真实 sm24 入口分别跑正常产物、独立构造的“East 窗整体平移 +0.2 m（非镜像）”产物，以及完整反射坏夹具：

```text
GOOD kind=c2_scored channels={'plan': 'applicable', 'elevation': 'applicable'}
  window_elevation_geometry=(44.0, 44.0, 'pass') mirror_criteria=[] strict_reason=None
CONSTRUCTED_NON_MIRRORED_SHIFT kind=c2_scored mirror_criteria=[] strict_reason=None
  window_elevation_geometry=(44.0, 44.0, 'pass')
MIRRORED_BAD kind=c2_scored channels={'plan': 'applicable', 'elevation': 'applicable'}
  window_elevation_geometry=(32.0, 44.0, 'fail')
  mirror_criteria=[('fail', {'East_view': 3})]
  strict_reason=elevation_mirror_disagreement
```

真实 strict `run_stage` 路径也验证了 commit-then-raise：

```text
GOOD strict_outcome=RETURNED artifact_committed=True mirror_criteria=[]
MIRRORED_BAD strict_outcome=RAISED:elevation_mirror_disagreement artifact_committed=True
  mirror_criteria=[('fail', {'East_view': 3})]
```

### 2. neuter：生产接线均会红；一个测试自身有 MINOR 缺口

所有改动都只摘调用接线、保留 helper/机制；每次跑完立即反向 patch 恢复。

| 临时改动 | 实测输出 |
|---|---|
| builder 的 elevation 分支不再调用 `_elevation_binding_fields`，改为响亮退出 | `test_generator_reproduces...` 红：`returncode 1`, `East_view: elevation binding wiring neutered` |
| builder 不再调用 `_elevation_source_fingerprint`，临时取首段指纹 | sm25 fail-closed 锁红：预期非零但实际 `returncode 0` |
| Va 真实入口不再调用 `_validate_bindings` | 方向反转真实入口锁红：`DID NOT RAISE` |
| assembly 不再调用 `elevation_mirror_flip_witnesses`，临时置 `mirror_witnesses=()` | 镜像坏夹具锁红：`assert found`, 实际 `[]` |
| strict helper 不再映射 mirror criterion（临时 `if False and (...)`） | regression 坏夹具 `RETURNED_WITHOUT_STRICT_ERROR`，但 FAIL criterion 仍在 |

恢复后的文件 sha256 与开始审阅时一致：

```text
35aedd6cf96e91513977cf2ab4ff9f63b4a692f2a46b51a46f0632204761edce  scripts/tool_scripts/build_score_view_bindings.py
691c0c4cda04d5d1cefe44641a76fce516f2349346879212abe85d935b05b1f5  src/agent/correction/facade_applicability.py
1d2882148b25ebf7a55a25dbf97070a6cee63a07aa19149e69135f5546e08146  src/agent/judge/reading_typed_score.py
e4fe85e59eabfdc477b3b154312331aed7c5320e073670287a611ff41c4811b3  src/agent/judge/score_service.py
```

### 3. `along_origin`：不通过，见 MAJOR-2

单层相等只是退化；North/South 多层实测不等。派工单 P4 是第二条错误 premise。

### 4. `mirrored=False`：通过

命令：

```bash
python AI_agent/logs/experiments/2026-08-22_elevation_mirror_convention/verify_mirror_convention.py
```

关键输出：

```text
sm25: East/North/South/West predicted 与 observed 全部 OK
sm24: East/North/South/West predicted 与 observed 全部 OK
=== 8/8 facades agree across 2 buildings ===
cross-check facade_convention: 8/8 OK
=> drawings follow the declared convention UN-MIRRORED
```

另测：`normalize_mirror_flag('unknown')` 输出
`UnresolvedMirrorError: unresolved mirror flag: 'unknown'`，所以这里确实是有据选择，不是默认猜测。

### 5. pending-S1 旗标：不通过，见 MAJOR-1

它确实形成一条 exit 0、正式 sidecar 可加载、Va 才失败的路径。

### 6. `affected_tests_rules.yaml` 豁免删除：通过

```text
python -m pytest -q tests/test_affected_tests_map.py::test_every_production_module_is_mapped_or_honestly_allowlisted
→ 1 passed in 7.64s

affected_tests(['scripts/tool_scripts/build_score_view_bindings.py']):
scope=SUBSET
tests=('tests/test_elevation_score_bindings.py',)
explanation=tests/test_elevation_score_bindings.py --string-path-->
            scripts/tool_scripts/build_score_view_bindings.py
allowlisted=False
```

新测试已经通过 string-path 图覆盖 builder，旧豁免必须删除；不是为了压掉锁。

---

## P1–P8 独立复核

| 前提 | 结论 | 证据摘要 |
|---|---|---|
| P1 | 成立 | `elevation_score.py:103-105` 实际计算 `origin + sign * lo/hi` |
| P2 | 成立 | `facade_convention` 是 gt-free 单一真源，judge 明确为允许消费者；生成器通过函数调用取 axis/sign |
| P3 | 成立 | Va `_validate_bindings` 重算 axis/sign；反转 sign 真实入口拒收，摘 live call 后 `DID NOT RAISE` |
| P4 | **不成立** | 校正侧先要求 per-floor extents 唯一；生成器却取 union；sm25 North/South 实测不匹配（MAJOR-2） |
| P5 | 成立 | 两个 GT 的 segment 字段实测含 `facade_family/outward_normal/world_along_interval/source_footprint_fingerprint/projection_surface_keys`；每族 keys/normals 可达 |
| P6 | 部分成立 | 两案确走 building-axis 且生成值正确；“schema 强制两字段都 None”字面错误（MINOR-1） |
| P7 | **不成立** | companion validator 不比指纹，但 Va 逐 opening 严比；本席复现 `GT validator=PASS / Va=FAIL` |
| P8 | 成立 | 证据脚本 8/8、两栋楼一致，且 sm24 真实评分 44/44 |

---

## 三项必须实测

### 端到端 sm24

通过真实 `_grade_typed_attempt_artifacts` 入口、真实 sm24 sidecars/GT，输出：

```text
kind=c2_scored
channel_applicability={'plan': 'applicable', 'elevation': 'applicable'}
window_elevation_geometry=(44.0, 44.0, 'pass')
```

生成器独立重产对账：

```text
sm24 binding equality count=5/5
1f_view=True East_view=True North_view=True South_view=True West_view=True
```

### 全量

命令：

```bash
python -m pytest -q -n auto
```

输出：

```text
3006 passed, 13 xfailed, 212 warnings in 692.91s (0:11:32)
```

与声称的 `3006 passed / 13 xfailed` 完全一致，相对施工前 `2996 / 13` 恰增加 10 passed。

### neuter

见上方 §2 表。全部临时改动已恢复；`git diff --check` exit 0。本席没有给 `src/`、`scripts/`、`tests/`
留下任何额外修改；这些目录当前仅保留审阅开始时已有的施工 diff/新增测试。

---

## 复核结论

sm24 立面绑定、真实计分、镜像可见性门、方向反转拒收、单一约定源、镜像证据、affected-tests 映射以及全量
回归均成立。请先：

1. 删除或封死会产出正式不可用 sidecar 的 pending-S1 旗标；
2. 把 `along_origin` 改为与校正侧/Va 一致的 per-floor compatibility 检查后再取端点；
3. 建议顺手修 P6 成对字段验证与 Va neuter 测试。

完成前裁决为 **REWORK**。
