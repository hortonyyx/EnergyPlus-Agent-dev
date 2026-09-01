# 执行档 · 模块 4 第二轮返工（F-1 候选数夹具 + N-1 解释锁）

- 日期：2026-09-01 · 施工方：**GLM 家族**（模块 4 原席位）
- 派工单：[../request/2026-09-01e_o22m4_rework2_candidate_count.md](../request/2026-09-01e_o22m4_rework2_candidate_count.md)
- 裁决：[../verdict/2026-09-01c_o22m4_rework_crossreview_gpt.md](../verdict/2026-09-01c_o22m4_rework_crossreview_gpt.md)（REWORK / 阻断 1 / 不阻断 1）
- 启动 HEAD：`a6990be`（与启动 prompt 一致）· 交件时**未 commit**（按单，交主控）

---

## 〇、开工自检三件（全过）

```text
$ git log --oneline -1
a6990be 09.01q_M4Rework2Dispatch_FixtureMustBuildTheTargetQuantityItself
$ git status --porcelain
（空）
$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
```

派工单头部 git 事实逐条复核（全部一致）：

```text
$ git rev-parse --short a13120d^
a6f5383
$ git diff --numstat a6f5383..a13120d -- src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
264	0	tests/test_o22m4_wall_compiler.py
$ git show a6f5383:tests/test_o22m4_wall_compiler.py | grep -c '^def test_'
22
$ git diff --stat a13120d..HEAD -- src/agent/correction/wall_compiler.py tests/test_o22m4_wall_compiler.py
（空输出，符合单上「应为空」）
$ git show a13120d:tests/test_o22m4_wall_compiler.py | grep -c '^def test_'
27
```

## 〇-b、§一 阻断读数独立复现（全过）

基线（当前 HEAD = a13120d 的两文件零 diff，即同一份代码）：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
bringing up nodes...
bringing up nodes...

...........................                                              [100%]
27 passed in 11.02s
```

注入复核方的承重变异（`_compile_single_face` 内 `wall` 构造后、逐字复刻裁决 §F-1 原文）：

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

实测：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
bringing up nodes...
bringing up nodes...

...........................                                              [100%]
27 passed in 9.87s
```

⇒ **与裁决逐字一致：27 条仍全绿**，F-1 当时真实存在。变异后 `git checkout -- src/agent/correction/wall_compiler.py` 还原（全程只点名本文件，从未 `git checkout -- .`）。

---

## ① 改了什么

**只改了 `tests/test_o22m4_wall_compiler.py`（+3 个 `def`，27 → 30）与两处 md；生产代码零改动**（④ 见下）。

1. **新永久夹具 `test_single_face_genuinely_single_candidate_stays_open`**（治 F-1）：
   - 用 `monkeypatch.setattr(wc, "_offset_candidates", …)` 把**真实的**枚举器收窄到「只留它自己产出的第一个候选」（候选的 id / preview / source record 全部是真实枚举器造的，不手工捏）——这是「候选被筛成唯一」的目标形态；
   - 走**真实入口** `compile_wall_ir(art, profile="strict")`；
   - **先自证目标量**：断言该 wall 的 axis item 在 `open_items` 里恰好一条、且 `len(item.candidates) == 1`（断言消息写明退化后果）；
   - **再断言仍开项**：复用 `_assert_axis_item_open_not_silent`（item kind / IDENTITY_BAN 排除 / 无 axis / 无厚度 / 无 output_basis / 无 auto action / `completion="degraded"`）；
   - 附带「门没焊死」证明：对这个唯一候选发一次显式 `FixedDecisionV1`，断言 axis / `output_basis="wall_axis"` / 厚度逐项落地、item 关闭——显式决定仍是唯一 closer。
2. **N-1 两条锁**（复核方建议、主控采纳的任务 4）：
   - `test_single_face_why_not_names_enumerable_offsets_when_candidates_exist`：有候选支的解释必须说「offsets are enumerable」、⛔不得声称「candidate set is empty」；
   - `test_single_face_why_not_names_the_empty_set_when_no_scale_exists`：空候选支的解释必须声称「candidate set is empty」、且点名法定出口（"re-perception"）。
   - 两条都先断言自己那条支的前提（候选数 >0 / ==()），锁写成「解释与其 item 自己的候选集状态一致」的规则，不钉实现文本全文。
3. 文件头 docstring 补「Rework 2」段（说明 F-1 的代理量教训与本轮锁）。
4. 实验目录 `AI_agent/logs/experiments/2026-09-01e_o22m4_rework2_glm/`：存货普查插件 `o22m4_channel_probe.py`（见验收 5）。

## ② 验收 1–6 逐条读数

### 验收 1 ⭐⭐⭐ 存在永久夹具，产品事实 `len(candidates)==1` 且仍开项 —— ✅

夹具原码单独跑：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6 -k "genuinely_single_candidate"
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
1 passed in 5.06s
```

夹具**先断言候选数再断言开项**（tests/test_o22m4_wall_compiler.py:1357–1375）：

```python
opened = [i for i in comp.open_items if i.scope_entity_ids == (wall.wall_id,)]
assert len(opened) == 1, ("the axis item vanished from open_items -- ...")
assert len(opened[0].candidates) == 1, ("fixture premise broke: candidate count != 1 -- ...")
item = _assert_axis_item_open_not_silent(comp, wall)
```

### 验收 2 ⭐⭐⭐ 变异 `len(candidates)==1 ⇒ 静默自动执行` ⇒ 必须红，且红的是验收 1 那条 —— ✅

注入前（原码，全文件）：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
bringing up nodes...
bringing up nodes...

..............................                                           [100%]
30 passed in 9.98s
```

注入变异（§〇-b 同一段，逐字）后：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
...
>       assert len(opened) == 1, (
            "the axis item vanished from open_items -- a silent auto-execute "
            "path closed it (F-1's mutation does exactly this)"
        )
E       AssertionError: the axis item vanished from open_items -- a silent auto-execute path closed it (F-1's mutation does exactly this)
E       assert 0 == 1
E        +  where 0 = len([])

tests/test_o22m4_wall_compiler.py:1363: AssertionError
=========================== short test summary info =================FAILED tests/test_o22m4_wall_compiler.py::test_single_face_genuinely_single_candidate_stays_open
1 failed, 29 passed in 9.53s
```

⇒ **红的就是验收 1 那条**，失败断言正是「axis item 从 open_items 消失」。其余 29 条仍绿（含上一轮 B 锁——它的候选数是 2，变异不触发，再次印证 F-1 机理）。

### 验收 3 ⭐ 反向变异 ⇒ 必须有锁红 —— ✅（按两种解读各实测一次）

派工单这句「把『开项』改成对**所有**候选数都开项」我读出两种含义，**都做了**（⑥ 有记）：

**解读 A（夹具形态退化）**：临时把夹具的收窄放宽（去掉 `[:1]` ⇒ 夹具退化成「对所有候选数都断言开项」= B 锁替身形态）：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6 -k "genuinely_single_candidate"
...
E       AssertionError: fixture premise broke: candidate count != 1 -- one thickness value still enumerates both signs; this lock must measure the TARGET, not that proxy
E       assert 2 == 1
...
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_genuinely_single_candidate_stays_open
1 failed in 5.79s
```

⇒ **自证前提断言红**（`assert 2 == 1`）：夹具无法悄悄退回代理形态。随后用 Edit 恢复 `[:1]`（测试文件含正式改动，⛔ 未用 git checkout），恢复后 3 条新锁 `3 passed`。

**解读 B（生产侧推广静默）**：把「len==1 静默」推广为「对所有候选数（有候选即）静默自动执行」（`if len(candidates) == 1:` → `if candidates:`）：

```text
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_genuinely_single_candidate_stays_open
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_real_l012_opens_axis_item_with_both_offset_families
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_why_not_names_enumerable_offsets_when_candidates_exist
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_unique_thickness_scale_still_requires_a_decision
4 failed, 26 passed in 9.10s
```

⇒ 「开项」这个行为在 1 候选 / 2 候选形态下都有锁红；0 候选形态的锁（`without_any_scale` 等 3 条）在该变异下不触发（`if candidates:` 对空集为假），它们由验收 5 的 M7 变异守着。

### 验收 4 `why_not_auto_resolved` 两支各一条锁，各自变异红 —— ✅

注入 N-1 原变异（`if candidates:` → `if not candidates:`，两支互换）：

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
...
E       assert 'candidate set is empty' in "one observed face: neither the wall's side nor its thickness is in the evidence; only symbolic offsets are enumerable (design §5.2)"
...
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_why_not_names_enumerable_offsets_when_candidates_exist
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_why_not_names_the_empty_set_when_no_scale_exists
2 failed, 28 passed in 9.57s
```

⇒ **两条 N-1 锁各自红**（一条抓「有候选 item 拿到空集故事」，一条抓「空候选 item 拿到可枚举故事」，失败断言原文可见）。

### 验收 5 ⭐ 上一轮已过的一条不退 + 存货普查 + 四通道承重变异 —— ✅

**M7 变异**（`return wall, [item], []` → `return wall, [], []`）：

```text
FAILED ...::test_single_face_observed_unclaimed_counterface_still_no_silent_axis
FAILED ...::test_single_face_real_l012_opens_axis_item_with_both_offset_families
FAILED ...::test_single_face_ink_present_unpromoted_witness_still_no_silent_axis
FAILED ...::test_single_face_unique_thickness_scale_still_requires_a_decision
FAILED ...::test_single_face_without_any_scale_opens_with_empty_candidates
FAILED ...::test_single_face_genuinely_single_candidate_stays_open
FAILED ...::test_single_face_why_not_names_the_empty_set_when_no_scale_exists
FAILED ...::test_single_face_why_not_names_enumerable_offsets_when_candidates_exist
8 failed, 22 passed in 9.72s
```

⇒ 上一轮 5 条全红（一条不退），新增 3 条也红。

**四通道承重变异**（每个变异后立即 `git checkout -- src/agent/correction/wall_compiler.py`）：

| 通道 | 变异 | 实测原文 | 结论 |
|---|---|---|---|
| `_compile_paired` | 中线 `(pos_a+pos_b)/2` → `pos_a` | `FAILED ...::test_paired_face_unshared_tail_survives_as_single_face_fragment` / `1 failed, 29 passed` | 有牙 |
| `_compile_solid_band` | 中线 `(lo+hi)/2` → `lo` | `FAILED ...::test_sm24_four_solid_bands_become_walls_without_fake_faces` / `1 failed, 29 passed` | 有牙 |
| `_compile_single_face` | M7 摘开项（上表） | `8 failed, 22 passed` | 有牙 |
| `_compile_legacy_trace` | structured centerline 的 `output_basis="wall_axis"` → `None` | `FAILED ...::test_structured_centerline_is_the_one_legal_identity` + `FAILED ...::test_unselected_dangling_candidate_is_caught_by_compiler_walk` / `2 failed, 28 passed` | 有牙 |

（legacy 变异我处比裁决多红一条 `test_unselected_dangling_candidate…`——其 control 段断言 `completion` 间接受累；更多红，不 weaker。）

**存货普查**（方法=外部 `-p` 插件包计数器，不触生产源码——复核方第一支直写探针曾触发模块 4 的「源码禁 `open(`」扫描锁，本插件在 `src/` 之外故不可能触发；插件归档于 `AI_agent/logs/experiments/2026-09-01e_o22m4_rework2_glm/o22m4_channel_probe.py`）：

```text
$ O22M4_PROBE_LOG=/tmp/o22m4_probe_r2.log \
  PYTHONPATH=…/2026-09-01e_o22m4_rework2_glm \
  python -m pytest tests/test_o22m4_wall_compiler.py \
      tests/test_o22m3_evidence_adapters.py -q -n 6 -p o22m4_channel_probe
bringing up nodes...

...................................................                       [100%]
51 passed in 11.11s
$ sort /tmp/o22m4_probe_r2.log | uniq -c
     35 _compile_legacy_trace
    302 _compile_paired
     12 _compile_single_face
     16 _compile_solid_band
```

⇒ 判据「`single_face` 命中 > 0 且四通道承重变异均有牙」：**12 > 0** ✅、四通道 1/1/8/2 红 ✅。数字不写死进任何断言（单上要求）。与上一轮 302/16/8/35 对比：single_face 8 → 12，增量 = 新夹具 2 次编译（无 decision + 显式 decision）+ N-1 两锁各 1 次，精确闭合；其余三通道逐位相同。

### 验收 6 受影响子集 `-n 6` 全绿 —— ✅

```text
$ python -m pytest tests/test_o22m4_wall_compiler.py tests/test_o22m3_evidence_adapters.py -q -n 6
...................................................                       [100%]
51 passed in 10.23s
```

路径显式列出：`tests/test_o22m4_wall_compiler.py`、`tests/test_o22m3_evidence_adapters.py`。全程未跑全量、未用 `-n auto`、未 `pip install`、未写 site-packages。

## ③ 新夹具的产品事实原文（能看见 `candidate count == 1`）

独立脚本（收窄真实枚举器 → 真实入口 → 逐项打印）：

```text
claim_kind              = single_face
thickness values        = [0.2]
symbolic operations     = ['OFFSET_POSITIVE']
candidate count         = 1
item kind               = axis_offset_undetermined
item still open         = True
wall resolved_centerline= None
wall output_basis       = None
wall resolved_thickness = None
auto actions on wall    = []
completion              = degraded
```

对照上一轮 B 锁（裁决 §F-1 量到的产品事实）：`thickness values={0.2}`、`ops={OFFSET_POSITIVE, OFFSET_NEGATIVE}`、**`candidate count = 2`**。本轮夹具 `candidate count = 1` 且 item 仍开、无任何静默产物。

## ④ 生产代码改动说明

**零生产代码改动。** `git diff --stat a13120d..HEAD`（两文件）开工时已核为空；本单全部变异均已逐个还原（只点名 `src/agent/correction/wall_compiler.py`）。`len(candidates)==1` 形态用测试侧 monkeypatch 收窄真实枚举器达成，无需为造夹具动生产代码——当前合法输入到不了单候选（正负两族总被同时枚举）是设计使然，锁保护的是「未来任何路径把候选筛成唯一后，编译器仍不得静默执行」这一不变量，不改变枚举规则本身。

## ⑤ 哨兵两次读数

```text
开工：58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
交件：58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
```

两次相同。交件前 `git status --porcelain`：

```text
 M src/agent/correction/evidence_contract.py
 M tests/test_o22m2_evidence_contract.py
 M tests/test_o22m4_wall_compiler.py
?? AI_agent/logs/experiments/2026-09-01e_o22m4_rework2_glm/
```

⚠️ **`evidence_contract.py` 与 `tests/test_o22m2_evidence_contract.py` 不是我改的**——本单开工时树是干净的，这两处修改在我工作期间由**并行席位**写入（单上预告「另有席位在飞」的 absent-with-payload 返工，diff 含 "Rework-3 (2026-09-01) -- absent while the payload rides along"）。我未触碰它们。本单全部读数（含 51 passed 全绿）均在此并行状态下取得，不受影响；主控合并时请与该席位协调归属。

我的写面仅：`tests/test_o22m4_wall_compiler.py`（+3 个 `def`，27→30）、`AI_agent/logs/experiments/2026-09-01e_o22m4_rework2_glm/`、本执行档。

## ⑥ 我认为本单哪里写错了（或含糊）

1. **验收 3 的表述有歧义**：「把『开项』改成对**所有**候选数都开项」按字面读是现状（编译器本就对所有候选数开项），字面变异不可能红。我按两种可行解读各实测一次（② 验收 3 的 A/B），两者都满足「必须有锁红」。建议下一版把这句改写成可机械执行的变异描述。
2. 小项：单上「验收 3 …否则你只是把门焊死了」与「⛔ 别用『一律开项』蒙混过关」两处括号，我理解为对夹具退化形态的警告（解读 A），与任务 2 的括号（「否则下一次实现一变，它又悄悄退回去测别的东西」）同旨。

## ⑦ 我自认最薄弱的一处

**N-1 两条锁锚在解释文本的判别子串上**（`"enumerable"` / `"candidate set is empty"` / `"re-perception"`）。它对「两支互换」这个被点名的变异有实证的牙（2 failed），但若未来有人**重写**这两句解释（语义不变、用词变），锁会假红；反过来若有人写出「同时含两个锚词」的解释，第一支的 `not in` 断言也可能假红。更稳的形态是把「候选集状态」做成 `OpenItemV1` 上的结构化字段（解释文本退居注释）——那是生产 schema 改动，超出本单写面，如实留报。次要薄弱处：`_compile_legacy_trace` 通道同样消费 `_offset_candidates`、同样有两支 `why_not_auto_resolved`，本单未给它 len==1 夹具与解释锁（N-1 变异当时打在 single_face）——同类缺口，建议下一单顺手补，不阻断。

---
交件清单：`tests/test_o22m4_wall_compiler.py`（改）· `AI_agent/logs/experiments/2026-09-01e_o22m4_rework2_glm/o22m4_channel_probe.py`（新）· 本执行档（新）。未 `git add` / 未 `commit`，交主控。
