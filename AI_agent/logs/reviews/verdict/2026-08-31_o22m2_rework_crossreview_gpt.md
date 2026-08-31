# 跨家族返工审裁决 · ②-2 模块 2（F-1 / F-2 结构不变量）

- **裁决：REWORK**
- **阻断：2**
- **不阻断：0**
- **送审对象**：`bb91f77`；**基线**：`31f873d`
- **审阅范围**：`git diff 31f873d..bb91f77 -- src/agent/correction/evidence_contract.py tests/test_o22m2_evidence_contract.py`
- **环境纪律**：两个 commit 均由 `git archive` 解到 `/tmp/o22m2_gpt_review.IzZ9QC/`；所有变异仅在临时副本；pytest 均使用 `-n 4`；未跑全量，采信主控 `6637f38 = 3494 passed / 13 xfailed / 0 failed`。

## 一、结论

F-2 已补实：跨 `input_id` 门位于生产校验器中，并覆盖 `paired_faces / solid_band / single_face / legacy_wall_trace` 四种 claim。F-1 的原始“全局零载荷”反例也已从放行变为响亮，正常产物与显式零载荷出口未误杀。

但 F-1 仍只检查 bundle **全局**有没有某类 payload，不检查 payload 是否来自该 channel 声明的 `source_input_ids`。因此可以让状态行指向合法空产物，再用另一份、未声明为该通道来源的产物载荷把门洗绿；`walls` 与 `plan_openings` 两路都复现。另有三个根本没有 payload 成员的通道可用 `zero_payload_channel` debt 把 `present` 洗绿，直接违背返工单“只能 `absent+debt`”的边界。核心结构不变量尚未闭合，故判 `REWORK`。

## 二、阻断项

### B-1 · F-1 仍可被跨来源 payload 洗绿（施工方未覆盖的同形破坏）

- **现象**：bundle 同时冻结 `tiny`（有 wall/opening payload）与 `empty_plan`（合法空产物）。把 `channel_status.walls.source_input_ids` 或 `channel_status.plan_openings.source_input_ids` 单独改成 `("empty_plan",)`，载荷仍全部来自 `tiny`；`validate_evidence_bundle` 两种形态都放行。原因是 `_channel_has_payload()` 在 `evidence_contract.py:679-691` 只做 `bool(bundle.wall_claims or bundle.face_dispositions)` / `bool(bundle.opening_claims)`，完全不与 `status.source_input_ids` 相交或对账。
- **我的复现命令与读数**：临时独立探针为 `/tmp/o22m2_gpt_review.IzZ9QC/new/tests/test_gpt_independent_rework_probes.py`，每个变异都重新 `finalize_bundle`，并以 `pytest.raises(EvidenceContractError)` 期待结构门拒绝：
  ```text
  cd /tmp/o22m2_gpt_review.IzZ9QC/new
  PYTHONPATH=$PWD python -m pytest tests/test_gpt_independent_rework_probes.py -n 4 -q --tb=short -ra
  # 3 failed, 4 passed in 2.43s
  # FAILED ...payload_must_come_from_the_channel_declared_source[walls]
  #   Failed: DID NOT RAISE EvidenceContractError
  # FAILED ...payload_must_come_from_the_channel_declared_source[plan_openings]
  #   Failed: DID NOT RAISE EvidenceContractError
  ```
  同一轮的 4 个 PASS 是 F-2 四种 wall claim 的跨来源 ref 拒绝探针，故这里的红不是临时工厂整体失效。
- **影响**：`channel_status` 仍不能证明“载荷随该通道所列来源而来”。adapter 把来源表写成空楼层/空产品、却把别处 payload 塞入 bundle 时，门仍绿；这正是上一轮点名的 `gate-measures-right-but-carrier-gets-swapped` 家族，只是从“全局空载荷”换成了“错误来源载荷”。接线后会让 source routing 审计失真。
- **建议方向**：对两条有载荷通道建立来源闭合。至少要求每个 wall claim/face disposition 的来源属于 `walls.source_input_ids`，每个 opening claim 的来源属于 `plan_openings.source_input_ids`；同时明确反向关系——状态列出的每个来源若本次无载荷，应有**按来源定域**的 zero-payload debt。当前 debt 只有 channel 粒度，若允许多来源部分空跑，需要增加可校验的 source/input 定域，不能用一条全局 debt 覆盖整路。

### B-2 · 无 payload 载体的三个通道可被 zero-debt 洗成 `present`

- **现象**：`dimensions`、`room_roles`、`elevation_openings` 在本 bundle 类型中没有对应 payload 成员。返工单与上一轮裁决明确给出的边界是它们“只能 `absent+debt`，`present` 无意义”；但当前逻辑在 `_channel_has_payload()` 返回 `False` 后，只要 bundle 任意位置存在同 channel 的 `zero_payload_channel` debt 就跳过报错。因此 `dimensions=present + zero_payload_channel(dimensions)` 被放行。
- **我的复现命令与读数**：与 B-1 同一临时探针、同一 `-n 4` 命令：
  ```text
  FAILED ...test_f1_channel_without_any_payload_carrier_can_never_be_present
    Failed: DID NOT RAISE EvidenceContractError
  # 总读数仍为 3 failed, 4 passed in 2.43s
  ```
  另行对撞 debt 选择性：`walls` 空载荷配 `zero_payload_channel(plan_openings)` 得 `PRESENT_CHANNEL_WITHOUT_PAYLOAD`；配 `zero_payload_channel(walls)` 则放行。说明它不是“任意 debt”误命中，而是当前代码有意把 matching debt 当通行证；问题在于把该通行证也开放给了永远无法携带 payload 的通道。
- **影响**：状态可声称 dimensions/room roles/elevation openings 已 `present`，但类型层没有任何字段能见证该事实；显式 debt 只把矛盾命名，不能让 `present` 变真。下游若按 `present` 分流，会把“通道不存在”误判为“通道已接、恰好本次为零”。
- **建议方向**：在这些通道获得真实 payload 成员前，校验器应拒绝其任何 `present` 状态，只允许 `absent + missing_channel debt`。`zero_payload_channel` 出口仅适用于本层能检查 payload 的 `walls` / `plan_openings`，并按 B-1 建议补来源定域。

## 三、不阻断项

**无。** 本轮未发现仅需记账而不影响返工目标的新增缺陷；施工方自报的命名选择不单列 finding。

## 四、返工审三条逐项读数

### ① `31f873d` 上两种旧形态仍复现

- **F-1 精确零 debt 形态**：从合法空产物构造 artifact，只保留 `walls=present` 状态并清空全部 debt；以旧副本作为 `PYTHONPATH`：
  ```bash
  cd /tmp/o22m2_gpt_review.IzZ9QC/old
  PYTHONPATH=$PWD python - <<'PY'
  import runpy
  ns = runpy.run_path("../new/tests/test_o22m2_evidence_contract.py")
  art = ns["_empty_artifact"]()
  art.bundle.channel_status = [s for s in art.bundle.channel_status if s.channel == "walls"]
  art.bundle.evidence_debts = []
  art = ns["_refinalize"](art)
  ns["validate_evidence_bundle"](art)
  print("OLD: VALIDATES", f"total_debts={len(art.bundle.evidence_debts)}")
  PY
  # OLD: VALIDATES total_debts=0
  ```
- **F-2 跨楼层 paired claim**：planA/1F 的 `face_a_ref` 与 planB/2F 的 `face_b_ref`，其余引用均可解：
  ```bash
  cd /tmp/o22m2_gpt_review.IzZ9QC/old
  PYTHONPATH=$PWD python - <<'PY'
  import runpy
  ns = runpy.run_path("../new/tests/test_o22m2_evidence_contract.py")
  art = ns["_cross_input_artifact"]("face_b")
  ns["validate_evidence_bundle"](art)
  claim = art.bundle.wall_claims[0]
  print("OLD F2: VALIDATES", claim.face_a_ref.input_id, claim.face_b_ref.input_id)
  PY
  # OLD F2: VALIDATES planA planB
  ```

结论：上一轮两洞在基线真实存在，不是返工测试虚构。

### ② `bb91f77` 上两种已知形态都红，且既有正例未误杀

直接探针读数：

```text
F1 REJECTS PRESENT_CHANNEL_WITHOUT_PAYLOAD {'channel': 'walls'}
F2-face_b REJECTS CLAIM_REFS_SPAN_MULTIPLE_INPUTS {... 'input_ids': ['planA', 'planB']}
F2-hypothesis REJECTS CLAIM_REFS_SPAN_MULTIPLE_INPUTS {... 'input_ids': ['planA', 'planB']}
```

定向及单文件测试：

```text
PYTHONPATH=/tmp/o22m2_gpt_review.IzZ9QC/new python -m pytest \
  tests/test_o22m2_evidence_contract.py::test_f1_present_channel_requires_payload_or_an_explicit_debt \
  tests/test_o22m2_evidence_contract.py::test_f2_claim_refs_must_share_one_input_id -n 4 -q
# 2 passed in 3.35s

PYTHONPATH=/tmp/o22m2_gpt_review.IzZ9QC/new python -m pytest \
  tests/test_o22m2_evidence_contract.py -n 4 -q
# 30 passed in 4.62s
```

30/30 包含旧 28 条、三份真实产物、同源正常 claim、`walls/plan_openings` 的目标负例以及 matching 显式零载荷 debt 的指定正例。`git diff --check 31f873d..bb91f77 -- <两文件>` 无输出。

### ③ 换同形输入仍走不通：未满足

- F-2 换形成功封堵：把跨来源 ref 放在共有的 `perception_source_ref` 上，分别撞四种 claim，临时探针 **4/4 PASS**，均得到 `CLAIM_REFS_SPAN_MULTIPLE_INPUTS`。`_claim_source_input_ids()` 的分支确实覆盖全部四种 claim，不只 `paired_faces`。
- F-1 换形失败：B-1 的 walls/openings 跨来源载荷均放行；B-2 的无载荷载体通道也可被 matching zero-debt 放行。故第三条不成立，这是本裁决阻断依据。

## 五、主控点名的 neuter 机械对撞

做法：分别从两个 commit 新建归档副本，在 `validate_evidence_bundle()` docstring 后插入立即 `return None`，其余代码与测试不改；均以副本为 `PYTHONPATH`、`-n 4 -q --tb=no -ra` 跑单文件。

### `31f873d` no-op 读数

```text
11 failed, 17 passed in 3.53s
```

精确 11 条：

1. `test_inv1_every_ref_resolves_in_the_frozen_bytes`
2. `test_inv2_every_face_line_has_exactly_one_disposition`
3. `test_inv3_paired_faces_consistency`
4. `test_inv4_claimed_ids_exist_and_witnesses_are_complete`
5. `test_inv5_one_source_per_semantic_slot`
6. `test_inv6_one_file_matching_two_contracts_is_loud`
7. `test_inv7_declared_but_malformed_never_falls_back_to_legacy`
8. `test_inv8_canonical_order_and_content_hash`
9. `test_n1_the_sixth_state_is_constructible_with_a_witness`
10. `test_observed_unclaimed_carries_the_counterfaces_disposition`
11. `test_nf4_4_opening_gap_index_out_of_range`

### `bb91f77` no-op 读数

```text
13 failed, 17 passed in 3.46s
```

精确集合 = 上述 11 条原样 +：

12. `test_f1_present_channel_requires_payload_or_an_explicit_debt`
13. `test_f2_claim_refs_must_share_one_input_id`

结论：施工方所报 **11 → 13** 与名单完全属实；两条新增测试确实能摘动生产 `validate_evidence_bundle`，不是只在测试工厂里造红。该硬证据通过，但不能抵消 B-1/B-2 的同形绕过。
