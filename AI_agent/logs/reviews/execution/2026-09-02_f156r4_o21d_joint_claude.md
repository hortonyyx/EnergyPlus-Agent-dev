# 执行档 · F-156 第四轮返工 ＋ ②-1d 返工【同修】（Claude 施工席）

- 日期：2026-09-02 · 施工：Claude 家族席（worktree `/tmp/joint_rework_claude`，开工 HEAD `a003542`）
- 派工单：[`request/2026-09-01i_f156r4_o21d_joint_rework_dispatch.md`](../request/2026-09-01i_f156r4_o21d_joint_rework_dispatch.md)
- 改动文件（⛔ 只 add 这三个）：
  - `src/agent/judge/answer_compiler.py`（+53/−1）
  - `tests/test_f156_ring_from_intersection.py`（+67）
  - `tests/test_o21d_exclusion_gap.py`（+103）

---

## 一、做了什么（两处一起改，一次交件）

### A. 灌证方向的牙（阻断甲＋阻断乙 = 同一个洞的镜像面）

`reconcile_boundary_basis`（`answer_compiler.py`）末尾、reverse pass 之后新增一条**聚合、按 view** 判据：

```python
    for view_id in sorted(set(paired_per_view) | set(excluded_per_view)):
        paired = paired_per_view.get(view_id, 0)
        excluded = excluded_per_view.get(view_id, 0)
        if excluded > paired:
            structural.append(
                f"boundary_exclusions_exceed_pairings_in_view:{view_id}:"
                f"paired={paired}:excluded={excluded}")
```

**为什么是这一个量（§三.1 允许换，交件写明）**：先实测了每腔的结构 ——
灌证 exclusion 与合法 exclusion **逐腔完全一样**（raw cavity 都在、都无 stored ring、台账都有条目、
reason 取自 schema 的 8 值闭集、area 等于腔自身面积）⇒ **信号只在聚合里**。三条缺口收敛成一个量：

| 复核方点名的缺口 | 我的处置 |
|---|---|
| **② 数量/占比上限** | = 本判据（exclusion 不得多于 pairing）|
| **③ ring/paired 覆盖率下限** | = 本判据的另一面（waive 多于 validate 即红）；②③ 是同一比例的两面，合并成一个量 |
| **① reason 准入表** | ⭐ **已由 producer 的 schema 关死**：`AsMeasuredBoundaryRingLossV1.reason` 是 `Literal[8]`（`as_measured.py:428-432`）⇒「任何字符串 reason」在 `model_validate` 处就被拒（攻击底料自己也要过这道校验）。在消费端复制一份 = gate 侧 8 值集，与 schema 等价 ⇒ **schema-合法输入永远红不了它 = 不可观测**（[[gate-with-only-negative-assertions-is-unobservable]]）⇒ **故意不加**。#1b 的「从没出现过但合法的 reason」这一形态因此**不存在**；灌证只能用集内 reason，而集内 reason 的灌证正是本判据抓的。|

**判据不是数据里读出来的阈值**：cut = 仪器自身定义（validation 实例不得少于 waive，即「例外不得变成常规」）——
唯一无需领域签字的结构切分；⛔ 不是「≤10%」这类照数据设的百分比。
**按 view 不按全局**：灌证若集中在一个 view，全局计数会绿（见 §二 测试 2 实证）。

### B. 阻断丙（重算门没复刻生产者定义）—— 我判：**采用 730 的奇数 NA 纪律**

`_projected_facts_ring`（`answer_compiler.py`）在算 offset 前加一道守卫：

```python
        if edge.boundary_condition == "interzone" and thickness % 2:
            return None, "wall_axis_falls_between_storage_units"
```

**判定理由（§二 最后一行要我判完写清）**：
1. 单位 = 10000/m（`as_measured.py:137`），1 unit = 0.1mm，存储为**整数**。奇数 interzone 厚度 ⇒ wall-axis 落在**半个 unit** = 存储格之间。
2. 生产者的**编译器**（`answer_compiler._the_compiler`，改动前 730 上方 723-729）对奇数厚度**已经**响亮 NA `wall_axis_falls_between_storage_units`——它**从不**产出半单位 wall-axis 环。`_offset_for`（`tarch_normalize.py:1402`）的 `/ 2.0` 是**底层 float 助手**，编译器用那道奇数守卫把它包住；⇒ **在存储单位层，生产者的定义就是「偶=半、奇=NA」，不是「600.5」**。「mirror producer definition」= mirror 这道纪律。
3. GPT 阻断 2 建议的 `/ 2.0` 会产出**分数** support（600.5），而对照的 converter zone 经 `_world_point_to_units` **恒取整** ⇒ 分数环永远 ≠ 整数环 ⇒ **对正确的奇数答案假红**。旧的 `// 2` 则静默截断（丢 0.5，实测环落在 `160600`）。**只有 NA 既不假红也不静默**，且与 730 一致。
4. `_projected_facts_ring` 做的正是 730 那件事（把 wall-axis 边内移半厚到 support），同一半单位不可表示性适用 ⇒ 一致性要求同样 NA。

`// 2` 保留（此后只在偶数下执行 = 精确），注释更新说明它精确是因为奇数已在上游被 NA。

---

## 二、逐条对 §五 报（红/绿都报）

**环境自证（每次跑测同一条命令）**：`python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)"`
每次都打印 `/tmp/joint_rework_claude/src/agent/judge/answer_compiler.py`（落在本 worktree，✅）。

### §五#1 灌证方向有牙（producer 大量写真 loss ⇒ 审计必须红）—— ✅ 绿（判据红）

`test_flooding_the_loss_ledger_cannot_waive_the_majority_of_a_view`：按规则「每 view 只留 1 个 paired、其余全 license 成 loss」
（⛔ 未写死 25 腔）复现均衡灌证 ⇒ 每个 view 都 `boundary_exclusions_exceed_pairings_in_view` NAMED、`not passed`。
改动前实测该攻击 `passed=True / exclusions=27 / structural=[]`（scratch 探针）。

### §五#1b 另造一种不同形状的灌证 —— ✅ 绿（判据红）

`test_a_flood_in_one_view_reddens_where_a_global_count_would_stay_green`：**集中灌证**（只灌 pairing 较少的那个 view、留 1、另一个 view 原样）。
实测该形态 **全局 `exclusions(≤) pairings`**（全局计数会绿），而 per-view 精确点名受灾 view。
⇒ 证明修法**没有过拟合到均衡那一种**，且**证明了 per-view 是必要的**（全局判据在此漏）。

### §五#2 撤证方向既有牙一条没变弱（原 11 条全绿 + 不变恒真）—— ✅ 绿

原 11 条 o21d 锁 + 新加，`tests/test_o21d_exclusion_gap.py` 全绿。逐条不变恒真的理由：
- 新码只在 `excluded > paired` 时发射；11 条锁的夹具**都不灌证**（诚实底料 per-view paired 25 >> excluded 2；单腔 strip/license 后仍 paired>>excluded）⇒ **新码在它们的夹具上从不发射** ⇒ 它们的断言与改动前逐字相同求值。
- 断 NAMED 码的锁（removing licence→`facts_boundary_ring_missing`、overlap、below-threshold、deregister）：新码是**另一个码**，不重叠、不发射 ⇒ 牙仍是各自的 NAMED 码。
- 断 `_exclusion_branch_failures==[]` / `test_honest_substrate...unaccounted==[]` 的锁：新码**已加进 `EXCLUSION_BRANCH_CODES` 枚举**（测试文件），故若误发射会被 #4 抓到；实测不发射 ⇒ `==[]` 仍成立且**仍有意义**（不是恒真）。
- `assert not X.passed` 那几条红半边：本就因 F-157 免费为真（复核方 §五 已声明），新码不碰它们。

### §五#3 新判据能红也能绿 + 摘掉实现回到红 —— ✅ 绿（变异实测）

**灌证牙**（MUTATION-A：`if excluded > paired` → `if False and ...`）：

```
$ python -c "import ... m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py -k flood
/tmp/joint_rework_claude/src/agent/judge/answer_compiler.py
2 failed in 3.44s
FAILED ...::test_flooding_the_loss_ledger_cannot_waive_the_majority_of_a_view
FAILED ...::test_a_flood_in_one_view_reddens_where_a_global_count_would_stay_green
```

**奇数-NA 守卫**（MUTATION-B：守卫条件前加 `False and`）：

```
$ python -c "import ... m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_f156_ring_from_intersection.py -k odd_interzone
/tmp/joint_rework_claude/src/agent/judge/answer_compiler.py
1 failed in 3.46s
E  assert <POLYGON ((50000 200000, 50000 160600, 0 160600, 0 200000, 50000 200000))> is None
```

（`160600` = `// 2` 静默截断值，正是旧门的病）两处变异均已**精确还原**，`grep MUTATION` 零命中，`git diff` 只剩目标改动。

### §五#4 奇数厚度重算门（逐位一致 或 730 响亮 NA）—— ✅ 绿（选 NA，夹具自造并自证）

`test_odd_interzone_thickness_is_declined_loudly_not_silently_truncated`：
sm25 墙厚全偶（实测：所有 interzone edge thickness=1200 units）⇒ **无活体存货**。
夹具按规则挑「首个能出环且含 interzone edge 的腔」，**自证偶数存货**（`even_thickness % 2 == 0`），
把该边厚度 +1（→ 1201 奇），**自证造出**（`odd % 2 == 1` 且 `odd/2 - odd//2 == 0.5`），
`_projected_facts_ring` 返回 `(None, "wall_axis_falls_between_storage_units")`（响亮 NA）；偶数控制组仍出环。

### §五#5 全量绿（`-n 6`）—— 🟡 3634 passed / 1 failed，唯一红是**环境缺 OPENAI_API_KEY**（B 层，非本单回归）

```
$ python -c "import ... m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
/tmp/joint_rework_claude/src/agent/judge/answer_compiler.py
1 failed, 3634 passed, 13 xfailed, 211 warnings in 476.15s (0:07:56)
FAILED tests/test_zone_agent.py::test_zone_agent_creates_two_zones - openai.O...
```

隔离复跑该红：

```
$ python -m pytest -q -n0 -p no:cacheprovider "tests/test_zone_agent.py::test_zone_agent_creates_two_zones"
E  openai.OpenAIError: The api_key client option must be set either by passing api_key
   to the client or by setting the OPENAI_API_KEY environment variable
/opt/venv/lib/python3.12/site-packages/openai/_client.py:587: OpenAIError
```

**核实**：报错在 OpenAI 客户端构造处（本席位环境无 `OPENAI_API_KEY`）；`test_zone_agent.py` 是**下游 LLM agent 测试**、
**不 import `answer_compiler`**，与本单改动无因果。基线权威全量 `3632 passed`（`0fda81f`）测于有该 key 的环境。
⇒ 「全仓绿是【树+启动器+这段时间的环境】的属性」的又一例（[[green-suite-is-a-property-of-tree-and-launcher]]）。
本单去掉这条环境红：**3634 passed + 3 条新增全过**（= 3632 基线 + 本单 3 条）。

受影响子集（GPT 裁决 §6 列的显式集 + 本单两文件）单独跑：

```
$ python -c "import ... m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_answer_compiler_closure.py ... tests/test_o21d_exclusion_gap.py
/tmp/joint_rework_claude/src/agent/judge/answer_compiler.py
188 passed in 12.25s
```

---

## 三、B 层：派工方说的 vs 我实测的

| # | 派工方（§二 承重前提）| 我实测 | 结论 |
|---|---|---|---|
| 1 | `answer_compiler.py:998` = `"interzone": lambda thickness: thickness // 2` | 改动前确在该处 | ✅ 属实 |
| 2 | `730` 上方有 `if thickness % 2: return NA(wall_axis_falls_between_storage_units)`；奇数是响亮拒绝 | 确在（改动前 723-730）| ✅ 属实，正是我采用它的依据 |
| 3 | 生产者原式 `tarch_normalize.py:1402-1403` `return thickness if basis=="outer_skin" else thickness/2.0` | 确在 1402-1403 | ✅ 属实（但它是 float 助手，编译器另包奇数守卫，见 §一B）|
| 4 | §五#4 活体数「1201 ⇒ 600.5 / 旧门 600 / symdiff 85801」| 未逐位复现 85801（我选 NA 分支，不产环故无 symdiff）；但复现了 `600.5 vs 600` 的半单位丢失（`odd/2-odd//2==0.5`，环落 `160600`）| ✅ 方向属实，NA 分支下 symdiff 不适用 |

§二 四行承重前提全部实测成立（无 A 层停报触发）。仅 §五#5 一条环境红，B 层记录、不停报。

---

## 四、承重不变量自证 · 交件前状态

- 全程 `m.__file__` = `/tmp/joint_rework_claude/src/agent/judge/answer_compiler.py`（每条跑测命令首行）。
- `.pth` 哈希按 §一新口径降级为只记（未作承重判据）。
- 交件前 `git status` 只含本单三个明确路径 + 本执行档；⛔ 未 `git add -A`。
