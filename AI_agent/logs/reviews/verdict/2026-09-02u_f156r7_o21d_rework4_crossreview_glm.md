# 跨家族复核裁决 · F-156 第七轮 / ②-1d 第五轮（返工第四轮）· GLM

- 日期：2026-09-03
- 被审 commit：`e065aeb`（冻结 worktree `/tmp/f156r7_review_gpt`，detached HEAD）
- 复核方：GLM 家族（原派 GPT 因沙箱起不来零交付、行为正确，本单改派；GLM 非本单施工方，`谁写谁不批` 成立）
- 裁决：**APPROVE**
- 计数：**阻断 0 / 不阻断 1**

## 〇、开工自检（命令原文 + 输出原文）

```bash
pwd && git log --oneline -1 && git status --porcelain
python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)"
```

```text
/tmp/f156r7_review_gpt
e065aeb 09.02i_F156r7_o21d_rework4: execution log (Claude seat)
?? AI_agent/logs/reviews/request/2026-09-02i_f156r7_o21d_rework4_claude.md
?? AI_agent/logs/reviews/request/2026-09-02u_f156r7_o21d_rework4_crossreview.md
/tmp/f156r7_review_gpt/src/agent/judge/answer_compiler.py
```

✅ 工作目录、被审 commit、模块落点三项全落在冻结 worktree。所有 pytest 均按硬纪律：
`set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a` + `__file__` 自证与 pytest 同一条命令 + `-n 6`。
本树无 F-158 出口门 ⇒ `.env` 已 source，全量中 F-158 环境红未出现。

---

## 一、对请求书 §二：施工方六项主张逐条实测（⛔ 全部自己跑，未照抄自述）

### T1（阻断 2）出口侧穷举 sweep —— ✅ 成立

代码层（`git diff abec1cd..e065aeb -- src/agent/judge/answer_compiler.py`）：view 体末尾新增
`for loss in view.boundary_ring_losses: if loss.cavity_id in losses_reddened_via_zone: continue
⇒ producer_ring_loss_unrepresented_by_any_converter_zone:<view>:<cavity>:reason=<r>:area_units2=<a>`，
遍历起点确为台账本身；前向命中的 cavity 记入 `losses_reddened_via_zone`（per-cavity，非 per-view）。

行为层（我的探针，不复用施工方夹具；探针为 heredoc 内联脚本，未落盘）：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE:', m.__file__)" && python - <<'PY'
# 摘要：自己按规则找「无 ring、无既有 loss、无前向 zone 命中」的 raw cavity（实测 12 个：F1/F2 各 6），
# 然后四个变体分别塞 loss 跑 reconcile_boundary_basis（完整脚本见本席会话记录）
PY
```

输出原文（四个变体，baseline_reds=4）：

```text
[A] GPT-r6 attack reproduced on cavity:e7c9a04459f8d03b: baseline_reds=4 attacked_reds=5
   NEW RED: producer_ring_loss_unrepresented_by_any_converter_zone:plan-F1:cavity:e7c9a04459f8d03b:reason=endcap_const_not_a_measured_parallel_face:area_units2=5760000
[B] same shape, other view / biggest cavity cavity:33d69d403440a842: attacked_reds=5
   NEW RED: producer_ring_loss_unrepresented_by_any_converter_zone:plan-F2:cavity:33d69d403440a842:reason=merged_lt_3:area_units2=5760000
[C] ghost cavity id: attacked_reds=5
   NEW RED: producer_ring_loss_unrepresented_by_any_converter_zone:plan-F1:cavity:deadbeefdeadbeef:reason=merged_lt_3:area_units2=12345
[D] mixed same view (real consumed 04e... + forged unconsumed): forward_reds=2 reverse_reds=1
   REVERSE: producer_ring_loss_unrepresented_by_any_converter_zone:plan-F1:cavity:e7c9a04459f8d03b:reason=merged_span_has_no_supporting_witness:area_units2=5760000
```

⇒ [A] 上一轮复核方的原始攻击在本 commit 上被抓住（+1 具名红，带 cavity+reason+area 指纹）；
[B] 换 view、换腔（我按最大面积优先，施工方锁按最小优先——选腔规则不同）；[C] 幽灵 cavity_id
（根本不在 raw_by_id 里）也红——sweep 不依赖 cavity 存在性；[D] 前向已名与反向补名在同一 view 并存互不干扰。

变异实测（临时改 src、跑完恢复、`git status` 核净，见 §四）：

```bash
# Neuter A：把 sweep 的 `for loss in view.boundary_ring_losses:` 改 `for loss in []:`
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE:', m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py
```

```text
FAILED tests/test_o21d_exclusion_gap.py::test_own_attack_unconsumed_losses_do_not_ride_the_below_threshold_amnesty
FAILED tests/test_o21d_exclusion_gap.py::test_a_producer_loss_no_converter_zone_consumes_is_still_fail_loud
2 failed, 15 passed in 3.45s
```

⇒ 摘 sweep 即 2 条新锁精确红。**T1 真牙。**

### T2（阻断 1）拆规则半/读数半 + 空台账两锁绿 —— ✅ 成立

我走的是**与施工方不同的一条归零路径**（见 §三 T2 方向）：不是手改 as_signed JSON，而是在
**as_measured 层清空 ledger → `derive_as_signed` 机械派生 → `verify_as_signed_reproduction` 通过**，
然后直接调用两条来源锁（pytest fixture 参数手动传入）：

```text
[T2-alt] as_measured-ledger zeroed -> derive_as_signed -> as_signed ledger entries = 0
[T2-alt] audit on zeroed-ledger signed: reds=4
    facts_boundary_ring_missing:plan-F1:cavity:04e1293098b1a95a:converter=F1-z4
    facts_boundary_ring_missing:plan-F1:cavity:04e1293098b1a95a:converter=F1-z5
    facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel
    facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel

[T2-alt] calling the two source locks on the zeroed substrate:
   LOCK1 test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion -> GREEN
   LOCK2 test_deregistering_each_live_loss_clears_exactly_its_own_red -> GREEN
```

⇒ 台账归零（且走完整机械链）后两锁**绿**；规则半的牙口由 Neuter B 证明（6 红里含 LOCK1）。
⚠️ 值得记录的读数：归零底座上 audit **换码红**（那条真实 loss 消失后 cavity:04e… 变
`facts_boundary_ring_missing` ×2，zone 仍踩着它）——**删 loss 洗不白**，删了 loss 换来另一条红。

### T3（阻断 3）互斥锁装牙 —— ✅ 成立

**校验器在场，反方向构造**（施工方是「给有 ring 的腔塞 loss」，我是「给有 loss 的腔塞 edge」——
同形但不同构造）：

```text
[T3-alt] REVERSED construction (edge onto loss cavity cavity:04e1293098b1a95a): RAISE precise=True
```

**摘 validator 变异**（`as_measured.py` 的 `if both_edges_and_loss: raise …` 改 `if False and …`，
跑后 `git checkout` 恢复，`git status --porcelain src/agent/judge/` 为空）：

```text
E       Failed: DID NOT RAISE <class 'ValueError'>
tests/test_o21d_exclusion_gap.py:455: Failed
FAILED tests/test_o21d_exclusion_gap.py::test_a_cavity_is_never_both_ringed_and_registered_as_a_loss
1 failed in 3.21s
```

⇒ 摘校验器即 `DID NOT RAISE` 红。**T3 真牙。**

### T4（不阻断 1）陈旧注释 —— ✅ 成立

diff 里两处矛盾注释已改（`answer_compiler.py:1165-1173` 的「NO LONGER a licence…」、
函数 docstring 的 reverse-sweep 段）。全量 grep 残留核对：

```bash
grep -rn "licence\|licenses" src/agent/judge/answer_compiler.py tests/test_o21d_exclusion_gap.py
```

10 处命中逐条读过：`173/186/1108/1166/1226/1237` 与测试侧 4 处均与「producer ledger 不再是 licence、
唯一 licence = below_request_area_threshold」的新机制一致；`1085` 见 §五不阻断观察。

### §三必答：真实 sm25 读数逐字不变 —— ✅ 成立

改前 = 临时 worktree 检出 `abec1cd`（`git merge-base --is-ancestor abec1cd e065aeb` 通过，
取证后 `git worktree remove` 已删）；改后 = 本树 `e065aeb`。同一命令、同一 request/report：

```text
（两边输出逐字相同）
passed=False / accounted=29/29 / paired_edges=100 exclusions=0 reds=4
converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z4:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200
converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z5:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200
facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel
facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel
```

⇒ 逐条归属：2 条 F-153 形态 B（同一条 loss 被 z4/z5 消费）+ 2 条 F-157，无第五条无出处红。
三个引用文件无一期望值需改（三文件合跑 43 passed，见 §四）。
未动任何已签字哈希/基线（探针只读磁盘三件套，`git status` 全程只有两条 untracked 请求书）。

### 全量 —— ✅ 成立

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE_ATTEST:', m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
```

```text
MODULE_ATTEST: /tmp/f156r7_review_gpt/src/agent/judge/answer_compiler.py
3666 passed, 13 xfailed, 211 warnings in 566.50s (0:09:26)
```

exit 0，与施工方主张（3666 / 13 / 0）一致。

---

## 二、对请求书 §四：活假说 H-a —— **不成立**（实测三层证据）

> H-a：新 sweep 读 as_signed 的台账 ⇒ 若一条 loss 在 as_measured 里存在、却被 revisions 改掉或删掉，
> sweep 就看不见它。

**第一层（类型层，实测）**：`RevisionV1.action` 的唯一类型 `TranslateActionV1.field` 是
`Literal["const", "along_min", "along_max"]`——只能平移 face line 的三个自有标量；
`derive_as_signed` 对 view 的其余字段（含 `boundary_ring_losses`）从 `model_dump` 原样透传。
实测（构造一条签字 `drawing_error` translate revision，目标选「不属于任何 wall 的 face line」
`plan-F1 handle=1380`，加进真实 revisions ledger 后派生）：

```text
live ledger in as_signed (from disk): [('plan-F1', 'cavity:04e1293098b1a95a', 'endcap_const_not_a_measured_parallel_face', 2868321200)]
translate target (wall-free face line): view=plan-F1 handle=1380 axis=x
after ONE signed translate revision: ledger in derived as_signed = [('plan-F1', 'cavity:04e1293098b1a95a', 'endcap_const_not_a_measured_parallel_face', 2868321200)]
LEDGER UNCHANGED BY REVISION: True
audit on revised as_signed: reds=4 forward_loss_reds=2 reverse_loss_reds=0
```

⇒ 一条合法签字 revision 应用后 ledger 逐字不变，audit 4 红不变。

**第二层（派生层，代码依据）**：「translate 让 loss 的 cavity 重新成 ring」这条路也不通——
`refresh_boundary_edges` 开头 `if not view.boundary_edges: return view`，docstring 明言
"Revision actions cannot re-pair walls or invent cavities"，它只重算**已有 edges 的 view**；
若未来真出现同 cavity 既 edge 又 loss，`_ledger_identity` 在 `AsMeasuredViewV1.model_validate`
处 raise（且 T3 的锁现在有牙盯着它）——是炸，不是静默消失。

**第三层（读入层，实测）**：`read_facts_for_compilation` 的两条路径（答案根三件套 / staging）
都**每读必跑** `verify_as_signed_reproduction`。实测「删了 loss 的 as_signed 副本 + 真 measured + 真 revisions」：

```text
TAMPERED as_signed (loss deleted) REJECTED by verify_as_signed_reproduction:
   AsSignedReproductionError: as_signed_does_not_reproduce_from_as_measured_plus_revisions: recomputed content_sha256=daa5ff62ef66a8826156810939af12fa63a8a106e71421a12100...
```

**边界记录（不构成 H-a 成立）**：producer 重写 as_measured 删 loss（不走 revision）时，
只要 zone 仍踩在那个腔上，audit 换码红（§一 T2 的 `facts_boundary_ring_missing` ×2），不静默。
真正静默的只剩「无 ring、无 loss、也无 zone 命中」的三无腔——那是 audit 对账面
（converter zones × ledger）的既定边界，上一轮已被接受，不属本单。

⇒ **H-a 证伪**：这不是「又换了一次载体」——这回载体换不掉是因为那条路**在类型层不存在**
（action 闭集 + 机械透传 + 每读重产校验三层叠加），正是 `[[gate-measures-right-but-carrier-gets-swapped]]`
记的有效解形态。

---

## 三、对请求书 §五：第三条判据（同形但不同的输入）—— ✅ 三个方向各造一个，缺陷均走不通

| 方向 | 施工方的形 | 我的同形不同输入 | 读数 |
|---|---|---|---|
| **T1** | 最小未消费腔（F1，`unconsumed[0]`）塞一条 loss | §一 [B] 另一 view（F2）最大腔；[C] 幽灵 cavity_id；[D] 与已消费 loss 混合同 view | 三个变体全部 +1 具名反向红 |
| **T2** | 手改 as_signed JSON 清空 ledger | **as_measured 层清空 → derive_as_signed 机械派生**（含 verify 通过）再直调两锁 | 两锁绿；audit 换码红非静默 |
| **T3** | 给有 ring 的腔塞 loss（model_validate ⇒ raise） | **反向构造**：给有 loss 的腔塞 edge | RAISE precise=True（同一精确错误码） |

外加 Neuter A/B/C 三个变异（§一、§四）——「摘哪个机制、哪组锁红」一一对位，无恒真。

---

## 四、对请求书 §六 / 任务书 §四 八条验收对照

| # | 规则 | 结论 | 证据 |
|---|---|---|---|
| 1 | 每条 loss 无论有无 zone 踩到都具名红 | ✅ | §一 T1 [A]–[D]；Neuter A 2 红；⛔ 锁内无 cavity id 字面量（grep 唯一命中是 docstring 里「没有写死」那句） |
| 2 | 台账空时两锁绿 + fail-loud 方向仍有牙 | ✅ | §一 T2（机械链归零两锁绿）；Neuter B 中 LOCK1 红 |
| 3 | 互斥锁有牙（精确错误 + 摘 validator 必红） | ✅ | §一 T3（双向构造 + DID NOT RAISE）；恢复后 `git status --porcelain src/agent/judge/` 空 |
| 4 | 诚实按阈值排除无论多少不红 | ✅ | 定向绿集 18 passed（含 below-threshold 绿集）；diff 未触碰阈值分支 |
| 5 | 定向绿集 + neuter 红集 + 奇数 NA 不变恒真 | ✅ | `tests/test_o21d_exclusion_gap.py` + odd NA 锁 = **18 passed**（GPT r6 的 16 + 2 新锁）；Neuter B = **6 failed, 11 passed**（与 GPT §4.2 / 施工方 #5 同列同条）；Neuter A = 2 failed |
| 6 | 自造不同形状攻击也红 | ✅ | 施工方 `test_own_attack_unconsumed…`（Neuter A 中红）+ 本席 §三 三方向变体 |
| 7 | 全仓无与机制相反的描述 | ✅ | §一 T4 逐条核对（10 处命中） |
| 8 | 全量绿 + 真实 sm25 读数逐条 | ✅ | 3666 passed / 13 xfailed / 0 failed；reds=4 逐条归属（§一 §三必答） |

定向读数命令（#5）：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && python -c "import src.agent.judge.answer_compiler as m; print('MODULE:', m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_o21d_exclusion_gap.py "tests/test_f156_ring_from_intersection.py::test_odd_interzone_thickness_is_declined_loudly_not_silently_truncated"
```

```text
MODULE: /tmp/f156r7_review_gpt/src/agent/judge/answer_compiler.py
..................                                                       [100%]
18 passed in 7.54s
```

Neuter B（前向 `loss is not None` 分支的 append+add 摘成 `pass`，复刻 GPT §4.2 手法）：

```text
FAILED tests/test_o21d_exclusion_gap.py::test_honest_substrate_branch_reds_are_exactly_the_known_defect
FAILED tests/test_o21d_exclusion_gap.py::test_stripping_a_ring_with_a_producer_loss_is_fail_loud_not_a_green_exclusion
FAILED tests/test_o21d_exclusion_gap.py::test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion
FAILED tests/test_o21d_exclusion_gap.py::test_own_attack_a_producer_loss_cannot_masquerade_as_a_below_threshold_drop
FAILED tests/test_o21d_exclusion_gap.py::test_a_single_balanced_producer_loss_still_reddens
FAILED tests/test_o21d_exclusion_gap.py::test_flooding_the_loss_ledger_is_fail_loud_per_loss
6 failed, 11 passed in 3.51s
```

（每个 Neuter 跑后即恢复原文并 `git status` 核净；本席全量结束时的最终 `git status --porcelain`
仅两条 untracked 请求书，与开工时一致。）

---

## 五、不阻断 1 条

**`answer_compiler.py:1085`「accounted for by WHO authored the licence」**——「licence」这个词还留着
统摄两类，但紧接着的展开已把 `registered_ring_loss` 明确写成 "can no longer silently waive -- it is
FAIL-LOUD"，语义无矛盾，仅措辞比 `186` 行「The only licence an exclusion may carry」旧半拍。
按任务书 T4 范围界（只改直接矛盾的描述）不改是合规的；记一条，供下一位维护者顺手统一，
⛔ 不必为此返工。

另记两条**观察**（不计数）：①台账归零底座上 audit 换码红（ring_missing）——设计正确的表现，
删 loss 洗不白；②Neuter B 时两条新锁不红、Neuter A 时那 6 条不红——前向与反向两组锁各自锚定
自己的机制、互为冗余兜底，这正是加法式实现的预期性质。

---

## 六、裁决

**APPROVE · 阻断 0 / 不阻断 1。**

- 上一轮三条阻断（T1 静默 / T2 钉死缺陷存在 / T3 恒绿）逐条实测确认修复且各有真牙（Neuter A/B/C）。
- 主控活假说 H-a 实测**不成立**：sweep 的载体（as_signed 的台账）在类型层换不掉。
- 返工审第三条判据（同形不同输入）三个方向全部通过。
- 真实 sm25 读数改前改后逐字相同，未动任何已签字哈希/基线；全量 3666 passed / 0 failed。
- 施工方六项主张全部与实测一致，自述无失实。

环境与纪律：全程未改 `src/` 与 `tests/`（三个 Neuter 均当场恢复并核净）；未跑
`pip install -e .`；未用 `git add -A`（仅 add 本裁决文件）；跑测一律 `-n 6`；临时
baseline worktree `/tmp/f156r7_before_abec1cd` 取证后已 `git worktree remove`。
