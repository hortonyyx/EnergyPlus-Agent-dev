# 执行档 · F-156 第六轮 / ②-1d 第四轮：分离 + fail-loud

- **日期**：2026-09-02 · **施工方**：Claude 家族施工席（同一施工方）
- **派工单**：[../request/2026-09-02f_f156r6_o21d_rework3.md](../request/2026-09-02f_f156r6_o21d_rework3.md)
- **基线（启动提示词点名）**：
  ```
  f3e10ed 09.02j_F156r6_o21d_rework3_SeparateAuthors_FailLoudRegisteredLoss
  74ea447 09.02j_F156r6_o21d_rework3_UpdateBoundaryFactsConsumer
  0bd23fa 09.02j_F156r6_o21d_rework3_RewriteLocks_FailLoud_BelowThreshold_OwnAttack
  ```
- **本轮 diff**（`git diff --numstat HEAD~3 HEAD`）：
  ```
  82	71	src/agent/judge/answer_compiler.py
  25	7	tests/test_boundary_condition_facts.py
  501	390	tests/test_o21d_exclusion_gap.py
  ```
- ⛔ 本轮**未改任何实现**（三个提交在上一场已落，本场只跑测 + 交件）。工作树跑测前后均干净。

---

## 〇、§〇 三路对账 —— 我自己实测对上了（A 层要求「别因为是我说的就信」）

派工单要我亲自核 §〇 那张「这条 loss = F-153 形态 B」的三路对账。实测读数（下面 §六的脚本输出）：

| 对的是什么 | 派工单 §〇 | 我实测 audit 读到的 |
|---|---|---|
| 面积 | `2868321200` units ⇒ 28.683212 m² | ledger `area_units2=2868321200`；`2868321200 × (1e-4 m)² = 28.683212 m²` ✅ |
| 数量 | F-153 三腔 → v3 修掉形态 A 两个 → 剩 1 | as_signed ledger **恰好 1 条** `boundary_ring_losses` ✅ |
| 机制 | endcap（一堵墙坐标差 1 个单位，非几何无环）| ledger `reason=endcap_const_not_a_measured_parallel_face` ✅ |

⚠️ **一处措辞差异（B 层，记录不停报）**：派工单 §〇 把机制写作
`nearest_same_axis_wall_face_const=52400, delta=1`，而产物 ledger 里的 `reason` 字面是
`endcap_const_not_a_measured_parallel_face`。**指的是同一件事**（endcap 常量边不是实测到的平行面），
面积/数量两路都精确对上 ⇒ 我判定 §〇 承重结论成立,不停报。

---

## 一、全量（§五#6 上半）

### 命令原文（环境自证与 pytest 同一条命令，`-n 6`）
```
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && \
  python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider
```

### 输出原文（尾部汇总 + `__file__` 自证）
```
/tmp/joint_rework_claude/src/agent/judge/answer_compiler.py

3659 passed, 13 xfailed, 211 warnings in 507.53s (0:08:27)
```

- ✅ `__file__` 落在本 worktree `/tmp/joint_rework_claude/` ⇒ 测的就是本树代码（承重不变量,`.pth` 代理量之外）。
- ✅ **3659 passed / 13 xfailed / 0 failed**，exit 0。
- 凭据已注入 ⇒ `test_zone_agent.py`（F-158，与本单无关）未红。

---

## 二、§五#6 特别要求 —— 真实 sm25 审计读数逐条列出

### 命令原文（只读诊断脚本，⛔ 不碰实现，跑在 scratchpad 之外的内联脚本）
```python
from src.agent.judge.answer_compiler import reconcile_boundary_basis, read_facts_for_compilation
from src.agent.judge.tarch_converter_schema import ConversionReportV1
CASE = "sm25-L_anchor"
_m,_l,signed = read_facts_for_compilation(CASE)
report = ConversionReportV1.model_validate_json((GT/"review/conversion_report.json").read_bytes())
audit = reconcile_boundary_basis(signed, report)
# 打印 audit.passed / converter_zones / accounted / structural_failures / live ledger
```

### 输出原文
```
passed = False
converter_zones = 29  accounted = 29
n structural_failures = 4
  [0] converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z4:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200
  [1] converter_zone_excluded_by_producer_written_ring_loss:plan-F1:cavity:04e1293098b1a95a:F1-z5:reason=endcap_const_not_a_measured_parallel_face:area_units2=2868321200
  [2] facts_projected_ring_unavailable:plan-F1:cavity:8bd127719198fd63:adjacent_projected_support_lines_are_parallel
  [3] facts_projected_ring_unavailable:plan-F2:cavity:495501ce9b36f0f3:adjacent_projected_support_lines_are_parallel
--- live ledger pairs (as_signed) ---
  plan-F1 cavity=cavity:04e1293098b1a95a reason=endcap_const_not_a_measured_parallel_face area_units2=2868321200
```

### 逐条：红几条、什么码、归谁

真实 sm25：**`passed=False`，共 4 条 structural failure；29/29 个 converter zone 全部 accounted（⛔ 无一被静默吞掉）**。

| # | 码 | 指向的 cavity / zone | 归谁 | 判定 |
|---|---|---|---|---|
| [0] | `converter_zone_excluded_by_producer_written_ring_loss` | `plan-F1` cavity `04e1293098b1a95a`,zone **F1-z4** | **本锁(rework3)** | ✅ **正确的红** = F-153 形态 B(28.68 m² 那个腔,唯一 ledger 项) |
| [1] | `converter_zone_excluded_by_producer_written_ring_loss` | `plan-F1` **同一** cavity `04e1293098b1a95a`,zone **F1-z5** | **本锁(rework3)** | ✅ 同上；**两个 converter zone(F1-z4/z5)共用这一个腔** ⇒ 一条 ledger 项 → 两条 fail-loud 红,均点名到 zone |
| [2] | `facts_projected_ring_unavailable` | `plan-F1` cavity `8bd127719198fd63`(`...parallel_support_lines`) | **F-157**(`CODES_OWNED_BY_ANOTHER_LOCK`) | ⏭ 延后项,非本单;F-157 落地后自动消失 |
| [3] | `facts_projected_ring_unavailable` | `plan-F2` cavity `495501ce9b36f0f3`(`...parallel_support_lines`) | **F-157** | ⏭ 同上 |

**结论**：真实 sm25 上,本锁负责的红 = **2 条**,来源**全部**是 F-153 形态 B 那个 28.68 m² 的腔
(唯一登记的 endcap loss);另 2 条 `facts_projected_ring_unavailable` **不归本锁**,是 F-157 的延后投影红。
⇒ **一条「无来由的常态红」都没有**(§一#3 非谈判项):每条红都能指名 cavity + 证据指纹(reason+area),
且 F-153 形态 B 一修好、ledger 一空,那 2 条本锁红就自动不再出现(见 §三#3 的
`test_deregistering_each_live_loss_clears_exactly_its_own_red`,遍历 ledger、无写死 id/面积)。

---

## 三、逐条对 §五 六条报

### 跑本单两个测试文件（verbose）
```
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a && \
  python -m pytest tests/test_o21d_exclusion_gap.py tests/test_boundary_condition_facts.py -v -p no:cacheprovider
```
输出尾行：
```
============================== 28 passed in 7.71s ==============================
```

### #1 诚实的按阈值排除,无论多少个,都不判红 —— ✅ 绿
`below_request_area_threshold` 独立可证(门自己重算 raw cavity 面积、阈值来自 request 这个另一个作者),
⛔ 不进灌证配额。覆盖锁(均 PASSED)：
- `test_below_threshold_exclusions_never_redden_no_matter_how_many` —— 按数量放大仍不红
- `test_disjoint_rooms_may_share_one_below_threshold_cavity`
- `test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold` —— 没有 request 阈值时它**不是**合法出口(反向)
- `test_above_threshold_unlicensed_cavity_still_reddens_even_with_the_threshold` —— 超阈值的无照腔即便带阈值仍红

### #2 任何 producer 自写台账都红,含 `excluded == paired` 这个点 —— ✅ 绿(单独一条锁)
- `test_a_single_balanced_producer_loss_still_reddens` —— **这就是上一轮漏的 `excluded == paired` 点的单独锁**：
  丢 1 个 paired 腔并发一条 producer loss(最均衡的灌证),rework2 的 per-view 配额只在 `excluded > paired` 触发、
  放它过去;fail-loud 不看均衡,一条伪造 loss = 一条点名红。
- `test_flooding_the_loss_ledger_is_fail_loud_per_loss` —— 每视图留一个 paired、其余全灌成 loss:
  红条数 == 伪造 loss 条数,⛔ 无一被静默豁免(治复核方那条「均衡丢 25 腔穿过配额」)。
- `test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion`

### #3 那条红能指名来源,且 F-153 形态 B 修好后自动不再红 —— ✅ 绿(§一#3 非谈判项)
- `test_honest_substrate_branch_reds_are_exactly_the_known_defect` —— **规则非字面**：branch 判红的 cavity 集合
  必须**恰等于** facts 层真实登记 loss 的 cavity 集合(`red_pairs == _ledger_pairs(signed)`);ledger 一空两边同为空集,锁保持绿、无需改一字。
- `test_deregistering_each_live_loss_clears_exactly_its_own_red` —— 遍历真实 ledger,逐条撤销 ⇒ 只清掉该条红、留下其余;⛔ 全程无 cavity id / 面积字面。
- `test_reading_the_ledger_the_gate_consumes_is_the_ledger_the_facts_layer_stores` —— READING(非规则):
  对两份独立解析的文档(`as_measured.json` vs `as_signed.json`)比 ledger,只在两者不一致时红 ⇒ **暴露会漂的数而不钉死它**。
- ⛔ 未把「28.68 那个腔」写死进任何锁([[acceptance-bar-must-not-be-written-from-the-result]])。

### #4 原 11 条撤证锁(夹具可重写)+ 奇数 NA 全绿 —— ✅ 绿
- 原用 `_strip_ring` + `SYNTHETIC_SPAN` + `reason=merged_lt_3` 的撤证锁在此方案下全部改判为 **fail-loud 变红**,
  已按 §二授权重写(`tests/test_o21d_exclusion_gap.py` 501+/390−,整体重写)。
  重写后**没把它们变成恒真**：新锁全部走「真实 substrate + 按规则挑夹具 + 断言具体红码/绿码」,
  例如 `test_stripping_a_ring_with_a_producer_loss_is_fail_loud_not_a_green_exclusion` 同时断言
  green anchor(诚实 substrate 不点名该腔)+ red(撤环+loss ⇒ fail-loud)+ 第二种红(撤环无 loss ⇒
  `facts_boundary_ring_missing`,两个作者仍可区分),⇒ 绿锚锚在本锁负责的那段、非「整份全绿」。
- 奇数厚度 NA(§四「已过审、不动」)：本轮未触碰,随全量 3659 passed 一并绿。

### #5 我自己再造一种不同形状的攻击,判据也必须红 —— ✅ 绿
- `test_own_attack_a_producer_loss_cannot_masquerade_as_a_below_threshold_drop` ——
  **新攻击(非灌证复跑)**：把 producer loss 瞄准一个**真·亚阈值** shaft 腔并同时供上 request 阈值,
  赌门对「无环 + 有阈值」宽松、让 loss 静默混入 `below_request_area_threshold` 豁免。
  实测必红：**producer-author 分支在 threshold 分支之前判**,同一腔同一阈值**不带**伪造 loss 是合法静默出口
  (control 断言 `evidence == below_request_area_threshold` 且无红)⇒ 证明画红的是伪造 loss 而非几何。
- `test_two_zones_overlapping_inside_one_below_threshold_cavity_reddens` —— 另一形状:两 zone 在同一亚阈值腔内重叠 ⇒ 红。

### #6 全量绿(`-n 6`)+ 真实 sm25 审计读数逐条 —— ✅ 见 §一 与 §二

---

## 四、停下上报（分层）—— 无 A 层触发

- **A 层**：① §〇 三路对账我亲自实测**对得上**(§〇),不停报;② 未动 §四 任何禁令(未改实现、未动 `as_measured.py`)。⇒ **无 A 层停报。**
- **B 层（记录继续）**：§〇 机制字面 `nearest_same_axis_wall_face_const=52400` vs 产物 `endcap_const_not_a_measured_parallel_face` 措辞不同(同一件事,面积/数量精确对上)——已记录于 §〇。

---

## 五、交件后动作
- 只 `git add` 本交件明确路径,⛔ 未用 `git add -A`。
- ⛔ 全程未 `pip install -e .` / 未写 site-packages。
