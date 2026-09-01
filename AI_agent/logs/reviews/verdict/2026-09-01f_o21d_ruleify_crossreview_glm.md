# 跨家族复核裁决 · ②-1d exclusion 锁「规则化」交付件（GLM）

- 日期：2026-09-01
- 复核方：GLM 家族（worktree `/tmp/o21d_review_glm`，detached `967de36`）
- 被审 commit：**`5ac0885`**（被审文件自 `5ac0885` 起至 HEAD 零 diff，`git diff --stat` 为空，实测确认）
- 裁决：**REWORK**
- 计数：**阻断 1 / 不阻断 4**
- ⛔ 声明：孤儿件（`2026-09-01_gpt_filter_orphan_o21d_review/`）**全程未读、未复用任何一段**；本文所有探针由我从零实现，构造方式与代码附在 §2.4。

---

## 1. 裁决

**阻断 B1（= 攻击面 1，主控假说证实）**：F-156 v3 阻断 1 的「25 腔均衡攻击」**原样穿过全部 11 条规则锁**（`11 passed`，无一变红）。被审文件第一行 docstring 声称 *"the boundary-basis exclusion branch is no longer an unbounded hole"*——实测在它自己声称负责的那个分支上，这个声称不真：丢掉 25/29 个本应成环的腔（86%）、让答案区 27/29 个 zone 走 exclusion、审计**仍然满分通过**（`passed=True / exclusions=27 / accounted=29/29 / structural=[]`），11 条锁全绿。

它缺的判据（复核单点名三选，**三条全缺**）：

| 缺口 | 实测证据 |
|---|---|
| **① reason 准入表** | 攻击用 `merged_span_has_no_supporting_witness`（真实 sm24 活体的 producer reason）；测试夹具自己用 `merged_lt_3` 也获准。**任何字符串 reason + 台账有条目 ⇒ 合法 exclusion**。消费端没有一张表说哪些 reason 有资格豁免一个房间 |
| **② 数量 / 占比上限** | 27/29（93%）zone 走 exclusion，`accounted == converter_zones` 仍逐字节相等（那条"规则"断言无感） |
| **③ ring / paired 覆盖率下限** | `paired_edges` 100 → 8、ring 腔 27 → 2，无任何下限判据 |

**修复归属提示（不改变本件裁决）**：根因在消费端 `reconcile_boundary_basis`（`answer_compiler.py`）——「台账有条目」被当成充分证明，而台账的**唯一写作者就是刚失败的 producer**。这与 F-156 v3 阻断 1 是**同一个洞的两个面**（那边 producer 写 loss 无准入，这边 loss 即免责），大概率应与 F-156 第四轮返工同修。但本件 docstring 的「no longer an unbounded hole」声称要么修出真上限、要么先收窄——声称与实测矛盾这一点归本件。

**结构定性（比缺口清单更重）**：11 条锁的牙**全部朝向「撤证」方向**（撤 loss ⇒ 必须红：`test_removing_the_licence_...` / `test_deregistering_...`；未申报码 ⇒ 红：`test_honest_substrate_...`）。攻击来自**镜像方向**——「灌证」：producer 大量写 loss，每条都真、reason/area 都对。②-1d 把锚从「producer 重导」（同因）换到「producer 写的台账」（**同作者**）——挡住了「门自己编造 licence」，没挡住「producer 编造 licence」。哈希覆盖只防篡改，不防作者自己写。这回答了复核单的「牙放对地方了吗」：**没有——两个有牙的方向都是撤证方向，灌证方向零牙**。

**不阻断 4**：见 §3。

---

## 2. ⭐⭐⭐ 攻击面 1 读数（本单必答题）

### 2.1 攻击底料构造（从零自研，零生产代码改动）

GPT 在 F-156 v3 的攻击是**生产变异**（让 merge 后复分类返回 `logical=False` ⇒ 走 loss 分支）。我不复刻它的生产内路径，而是构造**文档层等价终态**——这更强：不依赖生产代码的哪个具体 bug，任何写 loss 的路径走到这个终态，锁就是这个读数。

- 丢的 25 个腔 = **每 view 保留 1 个 paired 腔之外的全部 paired 腔 + 两个走廊腔**（plan-F1: 10 paired + 走廊 `8bd1277…` = 11；plan-F2: 13 paired + 走廊 `495501c…` = 14）。丢走廊腔后 F-157 的两条 deferred structural 码随之消失 ⇒ `structural=[]`、`passed=True`（这正是 GPT「均衡」的本质）。
- 每个被丢的腔：`boundary_edges` 删干净 + `boundary_ring_losses` 加一条（area = 腔真实面积，reason = `merged_span_has_no_supporting_witness`）——即「producer 刚刚失败时真的会写下的那条 loss」。
- **as_measured 与 as_signed 两份文档同步攻击**（忠实于真实传播：producer 先写 as_measured、as_signed 派生自带同 views）——否则 `test_reading_the_ledger_...` 的两文档一致性断言会造出真实世界不存在的红。

### 2.2 攻击读数（先证明底料本身是攻击）

```
$ python /tmp/o21d_attack1/attack_substrate.py
dropped 25 {'plan-F1': 11, 'plan-F2': 14}
AUDIT passed True paired_edges 8 exclusions 27 accounted 29 / 29 structural []
evidence breakdown Counter({'registered_ring_loss': 27})
```

与 F-156 v3 裁决原文逐字段一致（`passed=True / paired_edges=8 / exclusions=27 / accounted=29`）。基线（未攻击）同树读数 `passed False paired_edges 100 exclusions 2 structural [两条 projected_unavailable]` 亦与该裁决一致——两棵树的 facts 无漂移。

### 2.3 ⭐ pytest 原文（`__file__` 哨兵与 pytest 同一条命令）

均衡版（GPT 攻击形态）：

```
$ python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && PYTHONPATH=/tmp/o21d_attack1 python -m pytest -p attack_plugin -q -n 6 tests/test_o21d_exclusion_gap.py 2>&1 | tail -12
/tmp/o21d_review_glm/src/agent/judge/answer_compiler.py


[attack_plugin] substrate: 25 cavities dropped+licensed (F1=11, F2=14); patched fixture source on: ['test_o21d_exclusion_gap']


[attack_plugin] substrate: 25 cavities dropped+licensed (F1=11, F2=14); patched fixture source on: ['test_o21d_exclusion_gap']

bringing up nodes...
bringing up nodes...

...........                                                              [100%]
11 passed in 4.00s
```

**11 条全绿。主控假说证实。** 核心锁 `test_every_exclusion_is_licensed_by_evidence_it_actually_points_at` 的三句断言逐句核对：① `_exclusion_branch_failures == []` 过（`structural=[]`）② `accounted == converter_zones` 过（29==29）③ 每条 exclusion 引的 loss 在台账且 reason/area 相等——**过**（台账里那 25 条正是攻击加的，reason/area 是台账自己的值）。逐条锁的空转机制：3 条（互斥/两文档一致）在「丢的腔没 edges、两份文档同步灌」下天然成立；6 条自造夹具（`_strip_ring` 等）与底料无关照常工作；唯一有潜在牙的 `test_honest_substrate_...` 只挡「未申报码」，均衡攻击什么码都没让它看见。

**对照实验（闭合证据链——排除「底料没喂进去」的假象）**：非均衡版（F1 的 edges 清空；GPT 顺序丢 25 的形态，audit `passed=False` + `facts_boundary_edges_empty:plan-F1`）：

```
$ python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && O21D_ATTACK_MODE=unbalanced PYTHONPATH=/tmp/o21d_attack1 python -m pytest -p attack_plugin -q -n 6 tests/test_o21d_exclusion_gap.py 2>&1 | tail -12
/tmp/o21d_review_glm/src/agent/judge/answer_compiler.py
                       if not item.startswith(EXCLUSION_BRANCH_CODES)
                       and not item.startswith(CODES_OWNED_BY_ANOTHER_LOCK)]
>       assert unaccounted == []
E       AssertionError: assert ['facts_bound...mpty:plan-F1'] == []
E         Left contains one more item: 'facts_boundary_edges_empty:plan-F1'

tests/test_o21d_exclusion_gap.py:318: AssertionError
=========================== short test summary info ============================
FAILED tests/test_o21d_exclusion_gap.py::test_honest_substrate_raises_no_unaccounted_structural_failure
1 failed, 10 passed in 3.98s
```

⇒ 同一插件、同一喂入机制：非均衡版红（`facts_boundary_edges_empty` 是 undeclared code，`test_honest_substrate_...` 哨兵有牙），均衡版全绿。**读数不是假象；均衡攻击恰好穿过所有缝。**

### 2.4 复现用完整代码（探针在 /tmp 会话结束即失，故全文附此）

`attack_substrate.py`：

```python
from src.agent.judge.answer_compiler import (
    read_facts_for_compilation as _orig_read,
    reconcile_boundary_basis,
    _footprint_polygon, _wall_region, _cavity_id)
from src.agent.judge.tarch_converter_schema import ConversionReportV1
from src.agent.judge.gt_schema import REPO_ROOT

CASE = "sm25-L_anchor"
SM25_GT = REPO_ROOT / "case_tests/test_baseline/gt" / CASE
SPAN = {"axis": "y", "const": 1, "lo": 0, "hi": 1000, "side": 1,
        "p1": [1, 1000], "p2": [1, 0]}
REASON = "merged_span_has_no_supporting_witness"

def _cavity_areas(signed):
    areas = {}
    for view in signed.views:
        footprint, _ = _footprint_polygon(view)
        geometry = footprint.difference(_wall_region(view))
        for part in getattr(geometry, "geoms", [geometry]):
            if part.geom_type == "Polygon" and not part.is_empty and part.area > 0:
                areas[(view.view_id, _cavity_id(view.view_id, part))] = part.area
    return areas

def _attacked(doc, drop_pairs, areas):
    raw = doc.model_dump(mode="json")
    for view in raw["views"]:
        drop = {cid for (vid, cid) in drop_pairs if vid == view["view_id"]}
        if not drop:
            continue
        view["boundary_edges"] = [e for e in view["boundary_edges"]
                                  if e["cavity_id"] not in drop]
        view["boundary_ring_losses"] = view["boundary_ring_losses"] + [
            {"cavity_id": cid, "area_units2": int(areas[(view["view_id"], cid)]),
             "span": SPAN, "reason": REASON, "owner_count": None}
            for cid in sorted(drop)]
    return type(doc).model_validate(raw)

_measured, _ledger, _signed = _orig_read(CASE)
_report = ConversionReportV1.model_validate_json(
    (SM25_GT / "review/conversion_report.json").read_bytes())
_baseline = reconcile_boundary_basis(_signed, _report)
_areas = _cavity_areas(_signed)
_drop_pairs = []
for view_id in {p.view_id for p in _baseline.pairings}:
    keep = min((p for p in _baseline.pairings if p.view_id == view_id),
               key=lambda p: sum(1 for e in next(v for v in _signed.views
                       if v.view_id == view_id).boundary_edges
                       if e.cavity_id == p.cavity_id))
    _drop_pairs += [(p.view_id, p.cavity_id) for p in _baseline.pairings
                    if p.view_id == view_id and p.cavity_id != keep.cavity_id]
_drop_pairs += [("plan-F1", "cavity:8bd127719198fd63"),
                ("plan-F2", "cavity:495501ce9b36f0f3")]

import os as _os
if _os.environ.get("O21D_ATTACK_MODE") == "unbalanced":
    _drop_pairs = [(p.view_id, p.cavity_id) for p in _baseline.pairings
                   if p.view_id == "plan-F2"][:13]
    _drop_pairs += [("plan-F1", "cavity:8bd127719198fd63")]
    _f1_ringed = [e.cavity_id for e in next(
        v for v in _signed.views if v.view_id == "plan-F1").boundary_edges]
    _drop_pairs += [("plan-F1", cid) for cid in sorted(set(_f1_ringed))]
    _drop_pairs = sorted(set(_drop_pairs))

ATTACKED_MEASURED = _attacked(_measured, _drop_pairs, _areas)
ATTACKED_SIGNED = _attacked(_signed, _drop_pairs, _areas)

def attacked_read(case):
    return ATTACKED_MEASURED, _ledger, ATTACKED_SIGNED

if __name__ == "__main__":
    audit = reconcile_boundary_basis(ATTACKED_SIGNED, _report)
    print("dropped", len(_drop_pairs),
          {v: sum(1 for (vid, _) in _drop_pairs if vid == v) for v in {"plan-F1", "plan-F2"}})
    print("AUDIT passed", audit.passed, "paired_edges", audit.paired_edges,
          "exclusions", len(audit.exclusions), "accounted", audit.accounted_converter_zones,
          "/", audit.converter_zones, "structural", audit.structural_failures)
```

`attack_plugin.py`（喂入机制：收集后、fixture 运行前，把测试模块命名空间里的 `read_facts_for_compilation` 换成攻击版——**锁代码零改动，只换输入**）：

```python
import sys

def pytest_collection_modifyitems(session, config, items):
    import attack_substrate
    patched = []
    for name, mod in list(sys.modules.items()):
        if "test_o21d_exclusion_gap" in name and hasattr(mod, "read_facts_for_compilation"):
            mod.read_facts_for_compilation = attack_substrate.attacked_read
            patched.append(name)
    print(f"\n[attack_plugin] substrate: 25 cavities dropped+licensed "
          f"(F1=11, F2=14); patched fixture source on: {patched}\n",
          file=sys.stderr)
```

跑法：`PYTHONPATH=<探针目录> python -m pytest -p attack_plugin -q -n 6 tests/test_o21d_exclusion_gap.py`（非均衡加 `O21D_ATTACK_MODE=unbalanced`）。

---

## 3. 攻击面 2 / 3 / 4 实测结论

### 攻击面 2 · 绿锚真的挪走了吗 —— **是，零处人质**（不阻断）

```
$ grep -n "passed" tests/test_o21d_exclusion_gap.py | grep -E "assert|\.passed"
38:deliberately does ⛔ NOT assert ``audit.passed``, ...        (docstring)
49:``assert not audit.passed`` lines in the red halves below ... (docstring)
384:    assert not unlicensed.passed
418:        assert not audit.passed
459:    ⛔ This deliberately does not assert ``not audit.passed`` (docstring)
553:    assert not fail_loud.passed
580:    assert not audit.passed
```

**零处正向 `assert audit.passed`**。留着的 4 处全是红半边 `assert not X.passed`——它们的问题方向不是「人质」（别人的缺陷让我的绿锚红），而是「整份审计现在本来就 False ⇒ 恒真 ⇒ 零分辨力」。docstring L48-53（Corollary 段）已如实声明这一点并把牙放在 NAMED structural failure 上；L459 那条明确拒绝加 `not audit.passed`（零分辨力的断言不如不加）。判定：**设计自洽，可接受**；F-157 落地后这些断言自动重获分辨力。

「4/5 死于 `assert audit.passed`」自报数核实（在 `5ac0885^` 上，原路径临时 checkout 旧版、跑完 `git checkout HEAD --` 还原）：

```
$ python -m pytest -p no:cacheprovider -q -n 0 --tb=line tests/test_o21d_exclusion_gap.py
5 failed, 2 passed
失败断言行：92 / 111 / 138 / 219 / 241
```

| 行 | 断言 | 死因 |
|---|---|---|
| 92 | `assert audit.passed` | `.passed` ✓ |
| 111 | `assert reconcile_boundary_basis(signed, report).passed` | `.passed` ✓ |
| 138 | `assert audit.passed` | `.passed` ✓ |
| 219 | `assert aligned.passed` | `.passed` ✓ |
| 241 | `assert 'facts_boundary_ring_missing:...8bd...:F1-z0' in structural` | 命名断言（期望旧码，实际 F-157 两码） |

⇒ **自报 4/5 准确**。旧版名单式确认：写死 `CAVITY_88/CAVITY_SHARED/CAVITY_70` 三个腔 id、`(29, 29)`、正向 `assert audit.passed`。

### 攻击面 3 · 存货与恒绿锁 —— **存货 2 非空转；「CANNOT GO RED」理由成立**（不阻断 ×2）

a) `test_deregistering_each_live_registered_exclusion_reddens` 的真实存量：

```
$ python /tmp/o21d_attack1/probe_stock.py
exclusions_total 2
live_registered 2
LIVE plan-F1 cavity:04e1293098b1a95a F1-z4 endcap_const_not_a_measured_parallel_face 2868321200
LIVE plan-F1 cavity:04e1293098b1a95a F1-z5 endcap_const_not_a_measured_parallel_face 2868321200
ledger [('plan-F1', 'cavity:04e1293098b1a95a', 'endcap_const_not_a_measured_parallel_face')]
```

**遍历到 2 个 exclusion**（F1-z4 / F1-z5 共指台账同 1 条 loss——「disjoint rooms share one licensed cavity」的真实活体）。非 0 非 1，不空转；与 `_strip_ring` 自造存货夹具的互补关系成立（且施工方执行档 §八已如实自认「两条里至少一条有存货」没有机械保证——诚实）。

b) `test_a_cavity_is_never_both_ringed_and_registered_as_a_loss` 的「schema 造不出」理由——实测成立：

```
（probe_shapes.py 内：向有 ring 的腔同加一条 loss → AsSignedV1.model_validate）
FORGE edges+loss: REJECTED
```

`AsSignedV1.views: list[AsMeasuredViewV1]`（`gt_revisions.py:255`）直接复用 `AsMeasuredViewV1` 的校验器，`as_measured_boundary_cavity_has_edges_and_loss`（`as_measured.py:722`）在 AsSigned 层同样生效。**理由成立，tripwire 该留**：它守的是「schema 校验器被放松」这件事，成本一行；按施工方自己的标注 ⛔ 不计入 exclusion 分支覆盖。判：保留正确。

### 攻击面 4 · 施工方没停报 —— **判它判得对**（不阻断，给出判例条件）

事实链：派工单 §九 写「其余各条（`test_deregistering_...` / `test_above_threshold_...`）本来就是规则式，⛔ 不受 F-156 影响、不用改」——实测 5 条红里 4 条恰死于 `assert .passed`（含 §九 点名「不用改」的 `test_deregistering_...`，行 111），**该句被施工方当场证伪**（主控已认账 #65）。施工方继续做完而非停报。

按 [[stop-and-report-catches-dispatcher-errors]] 分层判：这是「**外围事实断言错**」而非「承重前提错」，理由三条——
1. **修复方向不受影响**：§九 的改法（规则+读数拆分）本身是对的，错的只是「哪些文件要改」的范围估计；攻击面 2 实测确认绿锚收窄是正确修复。
2. **树内先例**：绿锚收窄抄的是 F-156 v3 自己立的 `DEFERRED_PROJECTION_CODES`（同两个码、同理由），不是新拍口径。
3. **诚实上交**：执行档 §七逐条记录派工单错误、§八点名「这是本轮唯一的判断类决定，请复核方重点打」——不停报的代价（单人论证）被显式移交复核。

⇒ **判例**：「记一条继续做」成立的三条件 = 修复方向不受影响 + 树内先例 + 诚实上交复核；三者齐 ⇒ 不停报不违纪。本次三条全齐，且本复核单攻击面 1/2 恰好接管了它上交的那两处。

---

## 4. 三格读数表

| 格 | 输入 | 实测 |
|---|---|---|
| ① | `5ac0885^` 旧锁 + 当前生产 | `5 failed, 2 passed`；旧锁名单式确认（3 个腔 id + `(29,29)` + 正向 `assert audit.passed`）；4 死于 `.passed`、1 死于命名断言 |
| ② | `5ac0885`（= HEAD 零 diff） | `11 passed` |
| ③ ⭐ | **同形换输入 = 25 腔均衡攻击底料**（§2） | **`11 passed` 全绿**（⇒ 阻断 B1）；对照非均衡版 `1 failed, 10 passed`（红在 undeclared-code 哨兵）——证明底料进锁、锁活着、均衡攻击恰好穿过 |

③ 的读数说明：①② 证明「名单式改成了规则式」（判据不再钉住现状——达成）；③ 证明规则式判据**在载体被换掉时分辨力为零**——台账正是被灌的那一侧，而锁的牙全在撤证方向。判据写法的病（钉住现状）与 GPT 攻击的病（exclusion 无准入）不是同一个病，前者修好不覆盖后者。

---

## 5. 复现命令 · 哨兵 · 状态

```bash
cd /tmp/o21d_review_glm
git log --oneline -1                      # 967de36
git status --porcelain                    # （见下，交件读数）
python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)"
# /tmp/o21d_review_glm/src/agent/judge/answer_compiler.py  （全程每次取读数都贴，见 §2.3）

python -m pytest -p no:cacheprovider -q -n 6 tests/test_o21d_exclusion_gap.py      # 三格②：11 passed
git checkout 5ac0885^ -- tests/test_o21d_exclusion_gap.py
python -m pytest -p no:cacheprovider -q -n 0 --tb=line tests/test_o21d_exclusion_gap.py   # 三格①：5 failed, 2 passed
git checkout HEAD -- tests/test_o21d_exclusion_gap.py        # ⚠️ 必须带 HEAD（裸 `checkout -- <f>` 只还原工作树不还原 index）
PYTHONPATH=/tmp/o21d_attack1 python -m pytest -p attack_plugin -q -n 6 tests/test_o21d_exclusion_gap.py       # 攻击面1均衡：11 passed
O21D_ATTACK_MODE=unbalanced PYTHONPATH=/tmp/o21d_attack1 python -m pytest -p attack_plugin -q -n 6 tests/test_o21d_exclusion_gap.py  # 对照：1 failed, 10 passed
python /tmp/o21d_attack1/probe_stock.py    # 攻击面3a：live_registered 2
python /tmp/o21d_attack1/probe_shapes.py   # 攻击面3b：FORGE REJECTED
```

⚠️ 工程坑一条（供主控立规）：`git checkout <commit> -- <file>` 同时改 **index 与工作树**；还原用裸 `git checkout -- <file>` 会留下 index 里的旧版（我第一次还原后 `git status` 仍显示 `M`，已用 `git checkout HEAD -- <file>` 修复并核实零 diff）。复核单 §五.1 的还原指令照原文执行会踩同一个坑。

**哨兵（.pth，按 §一降级口径：只记不停）**：

```
开工时未单独读 .pth（按 §一新口径，承重判据改用 __file__，全程已贴）。
攻击实测后首次读数：1c1e3df0f8fa4000d583fd9afc59e0b71a9b2f4b6b5a0c7a2bf47f777d77167d
                    （内容 = /tmp/o21d_review_glm，即 §一预言的「席位启动即改指本 worktree」已知机制）
交件前读数：        1c1e3df0f8fa4000d583fd9afc59e0b71a9b2f4b6b5a0c7a2bf47f777d77167d（两次一致）
```

**交件前 `git status --porcelain`（本 worktree）**：空（干净；本席位全程未在该树留下任何改动——所有探针在 `/tmp`，两次临时 checkout 均已还原并核实）。

---

## 6. 主控这份单子哪里写错了

1. **身份错位（B 层）**：攻击面 1 通篇「**你自己**在 F-156 v3 裁决里打穿的攻击」——F-156 v3 裁决方是 **GPT**（`2026-09-01d_f156v3_crossreview_gpt.md`，署名「复核方：GPT 家族」）。把 GPT 的裁决安到 GLM 头上。不影响实质（该攻击我已完整重跑并逐字段复现，见 §2.2），但「⚠️ 转引你的读数」那句的「你」指错了席位。
2. **引用位置错（B 层）**：攻击面 4 说「派工单 §九 说『这 5 条红的根源是判据写法错了，不是代码错了』」——§九 无此原文（`grep 根源|判据写法` 零命中）；§九 真正被证伪的句子是「其余各条本来就是规则式、不受 F-156 影响、不用改」。前者出自执行档 §零 的转引（「派工单说：…」），原话可能来自未归档的交接 prompt。
3. **单内自相矛盾（B 层）**：§一已把 `.pth` 哨兵降级为「读到不符只记一条、不必停报」并预言了改指机制，§五.5 却仍写「应为 `58f547fa…`」——漏改。我实测读到 `1c1e3df0…`（指向本 worktree），按 §一口径只记不停。
4. 小（仅记）：§一说被审对象「`tests/test_o21d_exclusion_gap.py` +466/−128」——数字准确（实测 `1 file changed, 466 insertions(+), 128 deletions(-)`），但被审 commit 还含实验档 4 文件 + 执行档（过程痕迹，合理），且「零生产代码改动」属实（`git diff 5ac0885^ 5ac0885 -- src/` 为空）。

除以上四处外，本单的四个攻击面设计、环境判据改写（`__file__` 承重）、三格判据、并发条款均经实测成立。攻击面 1 的假说设计尤其准确——它是本单唯一真正要紧的事，也是唯一落成阻断的事。
