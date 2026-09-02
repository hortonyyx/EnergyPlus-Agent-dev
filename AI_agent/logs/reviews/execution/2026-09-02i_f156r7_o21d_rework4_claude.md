# 执行档 · F-156 第七轮 / ②-1d 第五轮：修三条阻断（Claude 施工席）

- 日期：2026-09-02（同日第二程） · 施工方：Claude 家族施工席（第三轮）
- 基线 commit：`abec1cd`（启动提示词点名） · 工作目录：`/tmp/f156r7_claude`（worktree，分支 `wt/09.02i_f156r7`）
- 交付两笔提交：
  - `881f55d` —— T1/T2/T3 + 两条新回归锁（core）
  - `ba12057` —— T4 docstring（反向 sweep 说明）
- 手法自述见各条；⛔ 未推倒主修法，全部在现有实现上补三处 + 修注释。

---

## 〇、开工自检（命令原文 + 输出原文）

```bash
pwd && git log --oneline -1 && git status --porcelain && python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && ls AI_agent/logs/reviews/request/2026-09-02i_f156r7_o21d_rework4.md
```
```text
/tmp/f156r7_claude
abec1cd 09.02i_F156r7_o21d_rework4_dispatch
（git status 干净，无输出）
/tmp/f156r7_claude/src/agent/judge/answer_compiler.py
AI_agent/logs/reviews/request/2026-09-02i_f156r7_o21d_rework4.md
```
✅ 工作目录、import 落点、任务书三项全在 `/tmp/f156r7_claude` 下。

---

## 一、手法与为什么这么选（逐 T）

### T1（阻断 2）—— ledger 反向逐条核销 / **出口全检**
**手法**：在 `reconcile_boundary_basis` 的每个 view 体末尾，新增一段**以 ledger 为遍历起点**的反向 sweep：
遍历 `view.boundary_ring_losses`，凡**前向 zone 路径没有名到**的 loss（用一个 per-view 集合
`losses_reddened_via_zone` 记录前向已名的 cavity），一律具名红
`producer_ring_loss_unrepresented_by_any_converter_zone:<view>:<cavity>:reason=<r>:area_units2=<a>`。

**为什么这么选（而非改前向）**：病根是「遍历起点是 zone，不是 ledger」（入口收窄）。
最小且对味的解 = **让 ledger 自己成为遍历起点**（出口全检），而不是给前向再加分支。
我选**加法式**（保留前向 zone 红 + 补反向 sweep 覆盖前向漏掉的），而不是把 ledger 设成唯一红源，
理由有二：① **真实 sm25 读数逐字不变**（那条唯一 loss 被 z4/z5 两个 zone 消费，前向已名 ⇒ 反向 sweep 跳过它，
不增不减）⇒ 干净回答 §三；② 前向红带 `zone_id`（哪个 zone 消费了它），信息更足，不该丢。
两条合起来 = 每条 loss 都被观察**恰好一次**，且 sm25 读数不动。

### T2（阻断 1）—— 拆掉两条来源锁对「台账非空」的依赖
**手法**：把两条锁**拆成两半**（按任务书解法形状）：
- `test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion`：
  删掉 `assert _ledger_pairs(signed)`；**规则半**改用自造夹具 `_strip_ring(licensed=True)`（永远有存货、与真实台账无关）
  证明「构造出的 producer loss ⇒ 具名 fail-loud 红、非 exclusion」；**读数半**只读真实台账、⛔ 不断言非空
  （台账空 ⇒ 循环空转 ⇒ 绿）。读数半同时接受前向码或反向 sweep 码（`UNCONSUMED_LOSS_CODE`）。
- `test_deregistering_each_live_loss_clears_exactly_its_own_red`：删掉 `assert live`；台账空 ⇒ 循环空转 ⇒ 绿。
  该方向的 fail-loud 牙口由自造夹具（`test_stripping_...`）承担。

**为什么这么选**：F-153 形态 B 一修好，真实台账就 3→1→0，两条锁的**读数半**会跟着到 0。
把「非空」写进断言 = 判据钉住了缺陷本身的存在（`[[acceptance-bar-must-not-be-written-from-the-result]]`）。
规则/读数拆开后，**牙口锚在自造夹具（永远有存货），读数锚在真实台账（空就是空）**，互不牵连。

### T3（阻断 3）—— 给恒绿锁装牙
**手法**：把 `test_a_cavity_is_never_both_ringed_and_registered_as_a_loss` 从「在真实 substrate 上断言不相交」
（结构上恒真、无牙）改成：BY RULE 取一个当前**有 ring** 的 cavity（保证存货），在**未校验载荷**里给它塞一条 loss
（造出「同 cavity 既有 edge 又有 loss」这个**本不该通过校验**的对象），断言
`AsSignedV1.model_validate` 抛**精确**错误 `as_measured_boundary_cavity_has_edges_and_loss:[<cavity>]`。

**为什么这么选**：任务书 §T3 显式授权用未校验载荷造非法对象。`AsSignedV1.views: list[AsMeasuredViewV1]`，
`model_validate` 会触发 `AsMeasuredViewV1._ledger_identity`（`as_measured.py:717-723`）的 raise ⇒
牙口是**schema 的**，摘掉 validator 该锁必红（实测见 §二）。

### T4（不阻断 1）—— 修陈旧注释
**手法**：① 修 `answer_compiler.py:1158` 那段把 producer ledger 说成 "licenses that exclusion" 的注释，
改写为「⛔ NO LONGER a licence，每条 entry fail-loud（前向名被消费的、反向 sweep 名其余的）」；
② 在函数 docstring 里那段「无 ring 的处置 = 遍历 converter zone」框架下补一句反向 sweep（否则下轮维护者会照它
重建「loss 只在 zone 消费时才被观察」的错误前提）。
**范围界**：只改与本轮机制**直接矛盾**的描述。grep 全仓 `licence/license` + `ledger.*(empty|toward 0|shrink)` 后，
其余 `licence` 命中（166-190 / 1084-1103）**都已是 rework3 的新机制、无矛盾**，⛔ 未改；其余 `ledger empty` 命中
（score_schema / interval_ledger 等）与本机制无关，⛔ 未动。

---

## 二、验收（§四 八条，逐条报）

**环境（两条，贴原文）**：所有跑测同一 shell 先 `set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a`，
且 `python -c "import ... print(m.__file__)"` 与 `pytest` **写在同一条命令里**，`__file__` 均落在 `/tmp/f156r7_claude`。

### #1 台账每条 loss 无论有无 zone 踩到都具名判红 —— ✅ 通过
新锁 `test_a_producer_loss_no_converter_zone_consumes_is_still_fail_loud`：BY RULE 取一个
「无 ring、无既有 loss、无前向 zone 命中」的 raw cavity（实测 substrate 有 12 个这类腔，见 §三；
⛔ 未写死 `cavity:1bf74ff8…`），塞一条合法 loss、⛔ 不新增 zone ⇒ 红
`producer_ring_loss_unrepresented_by_any_converter_zone:<view>:<cavity>:reason=…:area_units2=…`（带 cavity+reason+area 指纹）。
**变异实测**（把反向 sweep 的 append 摘成 `pass`）：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE:',m.__file__)" && python -m pytest -q -n0 -p no:cacheprovider "tests/test_o21d_exclusion_gap.py::test_a_producer_loss_no_converter_zone_consumes_is_still_fail_loud" "tests/test_o21d_exclusion_gap.py::test_own_attack_unconsumed_losses_do_not_ride_the_below_threshold_amnesty"
```
```text
MODULE: /tmp/f156r7_claude/src/agent/judge/answer_compiler.py
...
FAILED tests/test_o21d_exclusion_gap.py::test_a_producer_loss_no_converter_zone_consumes_is_still_fail_loud
FAILED tests/test_o21d_exclusion_gap.py::test_own_attack_unconsumed_losses_do_not_ride_the_below_threshold_amnesty
2 failed
```
摘牙即红 ⇒ 反向 sweep 是真牙。恢复后工作树净（`git checkout`/Edit 回原文，见 §四）。

### #2 台账为空时两条来源锁绿（且 fail-loud 方向仍有牙）—— ✅ 通过
直接以**清空全部 `boundary_ring_losses`** 的 substrate 调这两条锁：
```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE:',m.__file__)" && python - <<'PY'
import tests.test_o21d_exclusion_gap as T
... (raw['views'][*]['boundary_ring_losses']=[] -> empty AsSignedV1)
T.test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion((empty,request,report))
T.test_deregistering_each_live_loss_clears_exactly_its_own_red((empty,request,report))
PY
```
```text
MODULE: /tmp/f156r7_claude/src/agent/judge/answer_compiler.py
empty-ledger producer/unconsumed reds: []
LOCK1 (fail_loud_source) GREEN on empty ledger + constructed-fixture teeth still fired
LOCK2 (deregistering_source) GREEN on empty ledger (vacuous)
```
空台账 ⇒ 两锁绿；LOCK1 内自造夹具的 fail-loud 断言仍触发（该测试整体通过即证）⇒ 方向仍有牙。

### #3 ring+loss 互斥锁有牙 —— ✅ 通过
**校验器在场**：`AsSignedV1.model_validate` 抛精确错误（新锁断言
`as_measured_boundary_cavity_has_edges_and_loss` + 该 cavity 均在错误串里）⇒ 单跑该锁绿（见 §四全量内）。
**摘 validator 变异**（`as_measured.py:720-723` 的 raise → `pass`）：
```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE:',m.__file__)" && python -m pytest -q -n0 -p no:cacheprovider "tests/test_o21d_exclusion_gap.py::test_a_cavity_is_never_both_ringed_and_registered_as_a_loss"
```
```text
MODULE: /tmp/f156r7_claude/src/agent/judge/answer_compiler.py
E       Failed: DID NOT RAISE <class 'ValueError'>
FAILED tests/test_o21d_exclusion_gap.py::test_a_cavity_is_never_both_ringed_and_registered_as_a_loss
1 failed
```
摘校验器即 `DID NOT RAISE` ⇒ 红。**恢复 + 工作树核净**：
```bash
git checkout src/agent/judge/as_measured.py && git status --porcelain
```
```text
Updated 1 path from the index
 M src/agent/judge/answer_compiler.py
 M tests/test_o21d_exclusion_gap.py
```
（`as_measured.py` 已回原文，只剩两个目标文件的改动。）

### #4 诚实按阈值排除、无论多少都不判红 —— ✅ 未退化
`test_below_threshold_exclusions_never_redden_no_matter_how_many` 等 below-threshold 绿集在全量内逐条仍绿（§四）。
T1 未触碰 below_request 分支（反向 sweep 只处理 `boundary_ring_losses`，与阈值 amnesty 正交）。

### #5 定向绿集 + fail-loud neuter 红集 + 奇数 NA 逐条仍成立 —— ✅ 通过
**前向 fail-loud neuter**（把 `loss is not None` 分支的 append+add 摘成 `pass`，复刻 GPT §4.2）：
```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE:',m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py
```
```text
MODULE: /tmp/f156r7_claude/src/agent/judge/answer_compiler.py
FAILED ...::test_honest_substrate_branch_reds_are_exactly_the_known_defect
FAILED ...::test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion
FAILED ...::test_stripping_a_ring_with_a_producer_loss_is_fail_loud_not_a_green_exclusion
FAILED ...::test_own_attack_a_producer_loss_cannot_masquerade_as_a_below_threshold_drop
FAILED ...::test_a_single_balanced_producer_loss_still_reddens
FAILED ...::test_flooding_the_loss_ledger_is_fail_loud_per_loss
6 failed, 11 passed
```
6 条精确转红，与 GPT §4.2 同族（fail-loud / 来源对账 / flood / balanced / own-attack / 完整性）⇒ 接线是真牙。
恢复后工作树净（`git status --porcelain` 空，见 §四结尾）。奇数厚度 NA（`test_odd_interzone_thickness_is_declined_loudly_not_silently_truncated`）在全量内绿。

### #6 自造不同形状攻击也必须红 —— ✅ 通过
新锁 `test_own_attack_unconsumed_losses_do_not_ride_the_below_threshold_amnesty`（**与 #1 不同形**）：
把 loss 塞到**真正 sub-threshold** 的未消费腔上、**并供上 production 阈值**，赌反向 sweep 继承 below_request 静默 amnesty；
且**一次灌一个 view 里全部未消费腔**（证明 sweep 是**穷举**、非只名第一个）。判据必红（amnesty 只活在前向 zone 路径）。
变异实测同 #1（摘反向 sweep ⇒ 该锁红，见 #1 输出）。

### #7 全仓不再有与本轮机制相反的描述 —— ✅ 通过
grep 命令 + 结论见 §一 T4。改前/改后逐条：
- `answer_compiler.py:1158-1164`：改前「ONLY the `boundary_ring_losses` ledger … **licenses that exclusion**」；
  改后「⛔ producer ledger **NO LONGER a licence**：every entry FAIL-LOUD（前向名被消费的、反向 sweep 名其余的）…
  唯一静默出口 = below-threshold by-design drop」。
- `answer_compiler.py:1084-1099`（函数 docstring registered_ring_loss 项末尾）：补「⭐ rework4 T1：ledger 从 ledger 侧
  **穷举** sweep，⛔ 不只在遍历 converter zone 时；无 zone 消费的 loss 同样 fail-loud
  （`producer_ring_loss_unrepresented_by_any_converter_zone`）。ledger、⛔ 非 converter-zone 群，才是遍历起点」。
- 测试注释：`test_..._fail_loud_...` 原「stays true as the ledger shrinks toward 0」紧跟 `assert 非空` 的矛盾 →
  改为两半（规则半自造夹具 / 读数半不断言）；`test_deregistering_...` 原「neither reddens nor needs editing when
  stock reaches 0」紧跟 `assert live` 的矛盾 → 删断言、docstring 标 READING/空台账空转。
- 其余 `licence`（`BoundaryBasisExclusionV1` docstring 166-190 / 函数 docstring below_request 项）**本就是新机制、无矛盾**，⛔ 未改。

### #8 全量绿（`-n 6`）+ 真实 sm25 审计读数 —— ✅ 通过（全量 3666 passed / 0 failed，见 §四.3）
**真实 sm25 审计读数**（最终代码）：
```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import ... print(m.__file__)" && python - <<'PY' (reconcile_boundary_basis + Counter) PY
```
```text
MODULE: /tmp/f156r7_claude/src/agent/judge/answer_compiler.py
passed= False
accounted=29/29 paired_edges= 100 exclusions= 0 reds= 4
codes= {'converter_zone_excluded_by_producer_written_ring_loss': 2, 'facts_projected_ring_unavailable': 2}
  RED: converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z4:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200
  RED: converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z5:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200
  RED: facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel
  RED: facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel
```
**逐条归属**：
| 红 | 码 | 归谁 |
|---|---|---|
| plan-F1 cavity:04e…a95a F1-z4 | `converter_zone_excluded_by_producer_written_ring_loss` | **F-153 形态 B**（已登记未修；该腔 28.683212 m² 的唯一 loss 被 z4/z5 两个 zone 消费 ⇒ 两条红）|
| plan-F1 cavity:04e…a95a F1-z5 | 同上 | 同上 |
| plan-F1 cavity:8bd…fd63 | `facts_projected_ring_unavailable` | **F-157**（投影 ring 不可用，另有单）|
| plan-F2 cavity:495…f0f3 | `facts_projected_ring_unavailable` | **F-157** |
⇒ 4 红全部有归属，**无第五条无出处常态红**；**T1 反向 sweep 未增红**（唯一 loss 被前向消费）。

---

## 三、§三 必答：**T1 会不会改变真实 sm25 的读数？**

**答：不会 —— 逐字不变。** 见 §二#8 读数与本档最初/最终两次审计输出：
改前改后都是 `reds=4`、codes 相同、四条文本逐字相同。原因：真实 sm25 台账**唯一**那条 loss（cavity:04e…a95a）
**被 converter zone z4/z5 消费**，前向路径已把它具名红 ⇒ 反向 sweep 记它「已名」而跳过，不增不减。

⇒ 因此**三个引用文件**（`test_boundary_condition_facts.py` / `test_f156_ring_from_intersection.py` /
`test_o21d_exclusion_gap.py`）**无一条期望值需要改**（除本单主动重写的 o21d 三条锁 + 两条新锁）。
三文件合跑 43 passed（见 §四）。

**⛔ 未触及任何已签字 / 已落库产物的哈希或基线**（`content_sha256` / `record_baseline` / gt 三件套皆未动）⇒
**不构成 §三/§五 A 层停报**。我实测的证据：substrate 只读、audit 读数不变、`git status` 只有两个源/测文件。

**实测确认 substrate 存货**（§五#3 要求我自己复现，别只信转述）：真实 sm25 有 **12 个** 未被前向消费的 raw cavity
（plan-F1 / plan-F2 各 6 个，均 0.058 m² 的 below-threshold 小腔，**含 GPT 点名的 `cavity:1bf74ff81b6b39bb`**）
⇒ 新锁的 BY RULE 夹具有保证存货。命令与输出（forward 方向 zone 命中判定）已在会话内跑过，摘要：
```text
view plan-F1 UNCONSUMED(no ring/no loss/not forward-zone-target): 6
view plan-F2 UNCONSUMED(no ring/no loss/not forward-zone-target): 6
```

---

## 四、全量与工作树净证

### 4.1 复刻 GPT §4.2 前向 neuter 恢复后工作树净
（见 §二#5；恢复后：）
```bash
git status --porcelain
```
```text
（空 —— 两笔已提交，neuter 已回原文）
```

### 4.2 目标文件 + 两关联文件合跑
```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE:',m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py tests/test_f156_ring_from_intersection.py tests/test_boundary_condition_facts.py
```
```text
MODULE: /tmp/f156r7_claude/src/agent/judge/answer_compiler.py
...........................................                              [100%]
43 passed in 4.20s
```

### 4.3 权威全量（`-n 6`）

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE_ATTEST:',m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
```
```text
MODULE_ATTEST: /tmp/f156r7_claude/src/agent/judge/answer_compiler.py
........................................................................ [ ... ]
3666 passed, 13 xfailed, 211 warnings in 477.67s (0:07:57)
```
✅ **3666 passed / 13 xfailed / 0 failed**，exit 0，`__file__` 落在本 worktree。
F-158 环境红未出现（`.env` 已 source）。（较 GPT 那轮 3659 多 +2 新锁 + 基线自然位移；⛔ 0 failed。）

---

## 五、停报 / B 层记录

- **A 层**：无。§三未撞「重做已签字基线」（读数不变、未动哈希/基线）；T3 的临时 neuter 已授权；
  未发现复核方 §二/§三/§4.3 有不成立之处（三条阻断我均独立复现：T1 静默、T2 两断言与注释相反、T3 摘校验器仍绿）。
- **B 层（记一条继续，无阻断）**：
  1. T1 采**加法式**（前向红 + 反向 sweep），非「ledger 唯一红源」——后者会把 sm25 由 4 红降为 3 红（唯一 loss 由 z4/z5
     两条并成一条），改动三文件期望且丢 zone_id 信息。加法式保读数不变、信息更足，是我的手法选择，供复核方评判。
  2. 反向 sweep 码 `producer_ring_loss_unrepresented_by_any_converter_zone` 已并入
     `EXCLUSION_BRANCH_CODES`（完整枚举），故 `test_honest_substrate_branch_reds_are_exactly_the_known_defect`
     的完整性判据仍能兜住它（真实 substrate 上它不触发，因唯一 loss 被前向消费）。
