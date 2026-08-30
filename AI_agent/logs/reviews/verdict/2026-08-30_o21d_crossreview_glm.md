# 跨家族裁决 · ②-1d（edge `boundary_condition` 字段化 + 对账门 + F-150 换锁）

- **日期**：2026-08-30 · **审阅方**：GLM 家族 · **施工方**：GPT 家族 · **请求方**：orchestrator
- **送审对象** = `8442442` · **基线** = `54e3633`（全部以 `git diff 54e3633..8442442` 核）
- ## 裁决：**REWORK**（阻断 **1** 条 · 不阻断 **5** 条）

---

## 〇、环境与读数复核

- 分支 `08.23_AsDrawnReading` · HEAD `2be082d`（=发单读数）· `.pth` sha256
  `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43` 内容 `/workspaces/EnergyPlus-Agent-dev`（=发单读数，**自己重量**）。
- 受影响子集（施工方 10 文件清单）主树重跑：**`157 passed in 23.53s`（`-n 6`，exit 0）** = 施工方读数 ✅。
- 主树出现 3 个被改文件（`src/agent/reading/as_drawn/as_drawn_v2.py` 等）——
  **并发 Claude 席位的工作，非本审改动**；本审全程只写 `/tmp/o21d_rev/`（`git archive 8442442` 副本）与本裁决书。
- 所有探针留档可复现：`/tmp/o21d_rev/probe1_residuals.py`（残差分布）、
  `probe2_mutations.py`（E1–E5）、`probe4_e2e_supply.py`（端到端管井）、
  `probe5_diagonal.py`（E6 斜边）。跑法一律 `cd /tmp/o21d_rev && PYTHONPATH=/tmp/o21d_rev python <probe>.py`。
- 主控已复核的两件（权威全量 3385 / 答案根零改动）未重复。

---

## 一、逐攻击面结论

### A1 · 两列独立性 —— **✅ 独立非恒等，请求书最重的担忧不成立**

追了事实层字段的算者：`derive_boundary_edges`（[`as_measured.py:1314`](../../../../src/agent/judge/as_measured.py#L1314)）
→ `_classify_boundary_fact`（[`as_measured.py:1215`](../../../../src/agent/judge/as_measured.py#L1215)）。
它与转换器 `basis` 判定（[`tarch_normalize.py:1804-1806`](../../../../src/agent/judge/tarch_normalize.py#L1804)）**四点实质不同**：
出射点（`farthest_face+1` vs `mid + n×thickness_native`）、判据（零容差 covers vs 带 `node_join_native` 容差距离）、
值域（4 档 vs 2 档）、附加通道（wall_region covers / 恰一 cavity ⇒ interzone / unclaimed_void）。
`derive` 全程不读任何 stored `basis`（测试另断言 `"basis" not in edge.model_dump()`）。

两个方向的实证：

1. **改 converter 列单条 basis**（`probe2` E1）：F1-z3 edge0 `wall_axis→outer_skin` ⇒
   `passed=False, mismatches=1`，只点名 `boundary-edge:4e610f9475db71b9`。**门真的在读 converter 列。**
2. **天然分歧形态**（`probe5`，E6）：把 plan-F1 外轮廓北边一个顶点下压 1 m（真实斜切/倒角形态）⇒
   facts 侧 re-derive 得 **102 条（`unknown: 2`）**、两个北排 ring 变 5 边 ⇒ reconcile 响亮红：
   `boundary_edge_count_mismatch:plan-F1:…:facts=5 converter=4`（×2）。

⇒ **A1.3 的答案**：`100/100 全同` 是 **sm25 语料性质**（25 个 ring 全是 4 边轴对齐矩形、墙厚声明与实测一致），
两个谓词在这种语料上**碰巧不可能不同**；斜外轮廓形态即天然分歧且门会报。施工方读数真实、非恒等式。

### A2 · 门的分母 —— ⛔ **找到三个静默形态，其中一个构成本单唯一阻断**（见 §二 B1）

`reconcile_boundary_basis`（[`answer_compiler.py:965`](../../../../src/agent/judge/answer_compiler.py#L965)）的迭代以
**facts 侧 `boundary_edges` 为主**，`paired_edges` 的分母完全由被测方（facts 生产者）自供，**无任何总数断言**。实测：

| 变异 | 结果 | 判 |
|---|---|---|
| E1 改 converter 列单条 basis | 红、只红 1 条 | ✅ 有牙 |
| E5 删 ring 中 1 条边（sequence 断） | 红 `facts_boundary_sequence_not_contiguous` | ✅ 有牙 |
| E2b converter 同位重复 zone | 红 `converter_zone_pairing_not_unique`（len=2） | ✅ 有牙 |
| **E3 facts 侧删整个 ring（4 条）** | **`passed=True, paired=96, structural=[]`** | ⛔ 静默 |
| **E4 facts 侧 `boundary_edges` 全空** | **`passed=True, paired=0, mismatches=0`** | ⛔ 静默 |
| **E2c converter 多一个 zone（平移 50 m，不被任何 facts cavity covers）** | **`passed=True, paired=100, structural=[]`** | ⛔ 静默 |

静默形态**不是捏造的**，各有真实触发路径（均已实测）：

- **E4 型**：`_boundary_footprint`（[`as_measured.py:1163`](../../../../src/agent/judge/as_measured.py#L1163)）在
  exterior ring ≠ 1 或 polygon 无效时静默返回空 ⇒ `derive_boundary_edges` 返回 `[]` ⇒
  **门 0 配对 0 不一致全绿**。exterior ≠ 1 = **多栋楼图纸；sm24（本批验收 case）就是两栋楼**。
- **E3 型**：ring 内任何一条边 `_boundary_owners` 返回 ≠1（角缝/无主段）或被判 junction fragment
  （`logical=False`）⇒ **整 ring `continue` 静默丢弃**。实测两个真实形态：
  ① 我把 plan-F1 footprint 一个顶点挪 2 m（图纸毛刺级别）⇒ **整层 44 条全部消失，门仍 `passed=True`（paired=56）**；
  ② 端到端管井夹具（probe4）：两面 L 形搭接墙围 0.52×0.52 m 井（< 5 m² 阈值）⇒ 2 条边已正确判出
  `unclaimed_void`，但相接处 2 条 4 cm 内角边被判 junction fragment ⇒ **整 ring 连同 2 条正确分类一起被吞**。
- **E2c 型**：converter 幻觉出的 zone 只要不被任何 facts cavity 的 representative covers，**完全不进任何对账**。

另核了请求书点名的「改证据不改结论」：`reconcile` 不读 evidence；编译器 `_project_span`
（[`answer_compiler.py:660-676`](../../../../src/agent/judge/answer_compiler.py#L660)）只核 `stored.boundary_condition`
并**全程用自己重算的 evidence**（stored 证据既不核对也不搬运）⇒ 造假证据无处消费，**这条打不穿**（问对了但无害）。

### A3 · 改宽的门 —— **✅ 改宽正确、无顺手放行**

`test_r2_the_three_forbidden_fields_are_absent` → `test_r2_projection_fields_are_absent_but_boundary_condition_is_first_class`
（`tests/test_as_measured_facts_layer.py`）。① 原禁 5 个字面量（`"basis"`/`"boundary_condition"`/`"offset_m"`/`"outer_skin"`/`"zone_edges"`）
现在仍禁 **4 个**；② 放行理由落在派工单 R1 + 指南（boundary_condition 是投影前事实、非 S7 投影选择），
且模块 docstring 同步改写（"Three things it deliberately does NOT store" → "Projection choices…"）；
③ **没有放行第二个**，且新增**正向断言**（`'"boundary_condition"' in text` + 总数 `== 100`）——门从纯负向变成有正向读数。

### A4 · R3 合成供货 —— **🟡 谓词级真实、落库级从未行使**（不阻断，见 N1）

两个供货的形态论证**成立**（管井/风道/电梯井 < `min_room_area_m2`；轴对齐墙面向斜切外轮廓——都是真实图纸形态），
且**不靠 monkeypatch**（直接调生产谓词 `_classify_boundary_fact`）。
我的端到端实验补了一层执行档没说的：谓词在生产参数下**确实**判出 `unclaimed_void`（probe4 调试输出 2 条），
但**最朴素的真实管井（两面墙 L 形搭接）会让整 ring 被 junction-fragment 规则吞掉**，
`unclaimed_void` 到不了落库那一步——「schema 四档有谓词级供货」与「事实层能落库这两档」是两种能力，后者仍为零。

### A5 · F-150 新锁 —— **✅ 三方向全过**（遗留边界见 N3）

- **清空反事实进了锁**（上一轮复核方的更强反事实）：`test_r4_...` 第 1 层 = 清空 6 个判断字段 ⇒ form B bit-equal。
  **非平凡**：sm25 上该 6 字段中 5 个非空（F1/F2 合计 diagnostics 31、gates 8、split_const 2、
  jamb_cap_bands_missing 18、axis_snapped 2）——清空确实证明了这些判断不改变编译输出。
- **换名载体**：注入 `classification_hint`（不含 `basis` 字样）经派工单预裁的 `diagnostics[].context` 通道 ⇒ 生产仍 bit-equal ✅。
- **摘锁实验（E7b）**：往 `/tmp` 副本 `src` 里种入真实病——`_stored_boundary_for_span` 真消费 `classification_hint` ⇒
  `test_r4` **红**（`BoundaryConditionMismatchError: stored=interzone recomputed=exterior`）✅ 新锁有牙。
  （第一次实验 8 全绿是**我自己的种病代码写错**（dict 当属性访问），修正后复现红——不构成对锁的指控。）
- 旧词法 scrub 锁已删、无并存 ✓；执行档未发现第二条自由 dict 通道，我复核 `extra="forbid"` 后同意。

### A6 · 自报薄弱处 —— **🟡 0.5 m 上限无签字方且语义混同**（不阻断，见 N2）

- 实测（probe1）：**25 个 ring 的选中解 max residual 全部非零**，min 2473.86 / max 3394.11 units
  （0.247–0.339 m），最近替代解 19547–38875 units。非零残差的根源 = **两个表示的基准差**
  （facts 边 = 腔体内皮；converter zone 边 = 墙中线，`offset_m` 0.06–0.24 m，端点两方向各差半墙厚，
  最差 ring 实测 `hypot(2400,2400)=3394`）。⇒ `BOUNDARY_PAIRING_MAX_RESIDUAL_UNITS = 5_000`
  （[`answer_compiler.py:66`](../../../../src/agent/judge/answer_compiler.py#L66)）量的不是「同一条边的舍入余量」
  而是「两种基准差 + 错配防护」的混合量；它比 sm25 最大系统差只大 47%，**没人签过字**
  （派工单只写「残差硬上限」未定数；执行档自己承认是「当前批次安全栏」）。
- 厚墙方言即假红：外墙 offset 0.36 m（公共建筑常见）⇒ 两方向各 0.36 ⇒ `hypot(0.36,0.36)=0.509 > 0.5` ⇒
  正确配对被判 `boundary_pairing_residual_exceeds_hard_limit`。fail-loud 方向，不危险，但**下一份语料前必须重签或参数化**。
- **近似对称 ring**：实测风险低——正方形的 4 次旋转对称会被基准差打破（旋转错配的残差是边长级 ≫ 基准差级），
  sm25 上 alt_min 一致为选中解的 6–11 倍。此项**不构成**发现。
- **重复/缺失血缘**：血缘列以 `source_handle_matches` 最大为先、几何解平手裁决，且两列必须同解
  （`boundary_geometry_and_ancestry_pairing_disagree` 有锁）；E1/E5 实测失败半径确未扩散。

---

## 二、Findings

### 阻断（1 条）

**B1 · 对账门的分母由被测方自供，配对集静默缩水时门照绿——0 配对也绿。**
四个完整性方向里两个无锁（facts ring 整缺 E3 / facts 全空 E4），一个方向完全不查（converter 多余 zone E2c），
且 `paired_edges` 数量无任何断言。这不是「门没承诺的完整性」：`passed=True` 与「一次配对都没发生」并存
（E4），即门在自己的主声称（两列互证）上可被无声绕过——正是请求书引的病族第七轮候选「它量的那个东西能不能被换掉」：
**能，配对集就是被换掉的那个东西**。而 E4 的触发条件（多 exterior ring）在下一份验收语料 sm24（两栋楼）上即为常态，
E3 的触发条件（角缝/无主段/junction fragment ⇒ 整 ring 丢弃）在带管井的真实图纸上即为常态（probe4 已实证）。

返工要求（**纯门侧，⛔ 仍不许修任何一列**，与派工单 §四预裁 1 一致）：
让以下每个变异**必须红**、正常 sm25 仍 100/100 绿：
① E3（facts 删一个 ring）⇒ 红；② E4（facts `boundary_edges` 全空）⇒ 红；
③ E2c（converter 多一个未被认领的 zone）⇒ 红——即 facts cavity ↔ converter zone **双向全集对账** + 非空断言
（或把「本视图无 boundary_edges」显式列为带理由的结构失败/声明盲区，⛔ 不许静默）。
复现：`cd /tmp/o21d_rev && PYTHONPATH=/tmp/o21d_rev python probe2_mutations.py`。

### 不阻断（5 条）

- **N1（A4）**：R3 供货是谓词级、**落库级零行使**；且 L 形搭接管井（最朴素真实形态）整 ring 被 junction-fragment
  规则吞（probe4：2 条已正确判出的 `unclaimed_void` 随整 ring 丢弃）。执行档 §六自己点名的边界实测是
  「误吞的是整 ring 而不只是 unknown 边」。与 B1 同根（ring 被吞后门不红），B1 修复后此条自动降级为
  已知边界，但在层契约里应写成「unclaimed_void/unknown 落库级存货 = 0」而不是暗示四档可产。
- **N2（A6）**：`5_000` units 上限无签字方、语义混同（系统基准差 vs 错配防护）。实测选中解残差 0.247–0.339 m
  全为基准差；外墙 offset ≥ 0.36 m 的方言 ⇒ 正确配对假红。下一份真实语料前重签或 per-case 参数化。
- **N3（A5）**：新锁覆盖面是**列举式**的（6 个字段名 + `diagnostics[].context` 通道）。其余 13 个 readouts 字段中
  6 个判断产物字段被 ledger 恒等式锁**完整性**（清空即 `as_measured_wall_line_ledger_broken`，我实测），
  但「不被编译器消费」因此**不可测**——未来新增第 4 个消费点不会自动入锁。现状安全（grep 实证编译器只消费
  3 个字段、全在清空列表内：`answer_compiler.py:540/741/1207`）。登记为锁形态的已知边界即可。
- **N4**：`reconcile_boundary_basis` **零生产接线**（grep 全仓仅测试调用）。「不一致 = 必须有人看的观测量」，
  但没有任何自动红的位置——下一站走查若不手动调它，B1 修好了也不会响。建议随 B1 一并接进 staging/走查工具链
  （本单派工未要求接线，故不入阻断）。
- **N5**：`derive_boundary_edges` 的三个静默出口（exterior≠1 / polygon 无效 / `min_room_area_m2=None` 直通）
  均无 diagnostics。与 B1/E4 同根，B1 的非空断言落在 reconcile 侧即可兜住读数，此条仅要求实现时不留新的静默出口。

---

## 三、攻击面本身的勘误（请求书邀请的第 ⑦ 次）

- A2 候选「改证据不改结论」**问错了对象**：编译器对 stored 证据既不核对也不搬运（全程重算），
  造假证据无处消费。正确的问法是 **B1 的问法**——「配对集本身可不可以被静默缩水」，答案是可。
- A6 候选「近似对称 ring」实测**风险很低**（基准差打破旋转对称，替代解残差是选中解的 6–11 倍）；
  该项自报薄弱处可销。真正的薄弱处是 **0.5 m 上限的语义**（N2）。

---

## 四、给主控的一句话

施工质量高于本轮门槛：两列独立是真的、三个正面验收方向（A1/A3/A5）全部实证通过、单边/单列突变的失败半径
确实收敛到一条。唯一阻断是**对账门的分母**——sm25 上读数 100/100 真实，但这道门在「一侧整列被抹掉」时安静通过
（`paired=0` 仍 `passed=True`），而那恰是下一份语料（sm24 两栋楼、或任何带管井的图纸）的常态形态。
返工量小（纯门侧双向对账 + 非空断言，不碰任何一列的值），验收标准我已写成可机械执行的三个「必须红」。
