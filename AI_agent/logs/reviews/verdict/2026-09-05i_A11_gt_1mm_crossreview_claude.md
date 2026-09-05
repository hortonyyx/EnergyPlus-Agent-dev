# 裁决书 · A-11 gt 按 1 mm 规整入库 跨家族复核（Claude 家族）

**REWORK + 阻断 1（含 2 个独立根因）/ 不阻断 3**

- **复核方**：Claude 家族 · **被审 commit**：`83326ba6`（基点 `c7c6831a`）· **工作目录**：`/tmp/a11rw_review_claude`
- **复核单**：`AI_agent/logs/reviews/request/2026-09-05i_A11_gt_1mm_crossreview.md`

---

## 头条结论

**⛔⛔ 复核单 §四 要求的独立全量，红了：`5 failed, 3858 passed, 2 skipped, 13 xfailed`**（`-n 6`，489s）。
这不是并行假红——同 5 条在串行 `-p no:cacheprovider`（无 `-n`）下**同样失败**；用同一份诊断命令在
**独立 worktree**（`/tmp/a11_basepoint_check`，基点 `c7c6831a`，全程未碰被审 worktree）上跑，**全部 5 条通过**。
⇒ **确认是本单引入的真回归，不是环境噪声**。已定位两个独立根因（见 §一 之后的「阻断」小节）。
按复核单口径「⛔ 它红了本单就不能合并」——**本单目前不能合并，需返工**。

**逐位闭合**：基点 `3850+2+13=3865` 项；本单新增 12 项（`test_a11_gt_1mm_ingest_resolution.py`，
`11 def + 1 参数化 = 12`，独立 `--collect-only` 核实）+ 1 项（`test_gt_facts_staging_sm25.py::test_3`
拆成两条，净增 1）= `3865+12+1=3878`；本仓 `--collect-only` 实测 **3878**，与
`3858 passed + 5 failed + 2 skipped + 13 xfailed = 3878` 吻合。**闭合成立，红的 5 条不是「多算出来的」。**

---

## 是否改过被审对象（如实披露）

**是，短暂地，已完全恢复。** 排查回归根因时，我在诊断基点行为时误用了
`git checkout c7c6831a -- .`（意图是切到基点核对，实际把**当前 worktree 的所有跟踪文件**回退成了基点内容）。
**立即发现并处理**：`git checkout HEAD -- .` 恢复全部跟踪文件到 `83326ba6`；此前 `git stash -u`
保存的 untracked 复核单文件用 `git stash pop` 找回。**收尾核验**：`git diff HEAD --stat` 为空、
`git status` 干净、`git rev-parse HEAD == 83326ba6`——工作树与被审 commit 逐字节一致。
之后所有基点对比改用**独立 worktree**（`git worktree add --detach /tmp/a11_basepoint_check c7c6831a`），
不再触碰被审对象。§二 B 的「摘牙」实验全部用**进程内 monkeypatch**（`pytest.MonkeyPatch.context()`），
不落盘、不改被审文件。

---

## §一 三条复核（⭐⭐⭐ 缺一不合格）

### 1. 改动前复现得出 74 ✅

不转引施工方/主控的数字,自己独立算：用**当前提交的** `scan_ingest_resolution_violations`
扫**基点** `c7c6831a` 的 `git show` 原始 `as_measured.json`（未落盘改动被审对象，只读 `git show` 取字节）：

```
$ python3 -c "... scan_ingest_resolution_violations(pre_a11_doc) ..."
pre-A11 as_measured -> 100 violations   （74 核心桶 + 26 派生桶，见下）
pre-A11 as_signed   -> 100 violations
```

**再用完全独立于施工方产物的从零脚本**，只看 `face_lines/const/along_min/along_max`、
`walls/along_min/along_max`、`openings/*`、`evidence` 四类字段（不用施工方的分桶函数）：

```
face_lines 46  walls 11  openings 10  evidence 7   total = 74
```

与主控读数、施工方交件的四桶分布**逐位吻合**。✅

### 2. 改动后复现不出（0）✅

同一独立扫描脚本，指向**被审 commit**当前落盘的 `as_measured.json` / `as_signed.json`：

```
post-A11 as_measured -> 0 violations
post-A11 as_signed   -> 0 violations
```
✅

### 3. 换同形输入仍然成立（自己造的对抗输入）✅

直接对 `snap_to_ingest_resolution` 做**穷举 + 边界**测试（不经过施工方任何测试文件）：

```python
# 穷举 -50m..+50m 每一个格点：0 处 identity 失败
for v in range(-500000, 500001, 10): assert snap(v) == v          # 0 fails

# 半格进位方向（.5mm = 5 units）+ X999.9/X000.1 + 负坐标
9999  -> 10000   (X999.9 贴上)
10001 -> 10000   (X000.1 贴下)
5     -> 0       (恰好半格,quotient=0偶,banker's停在偶数)
15    -> 20       (恰好半格,quotient=1奇,进到偶数20)
25    -> 20       (恰好半格,quotient=2偶,停在20)
-5    -> 0        (负数半格,同规则)
-15   -> -20
-9999  -> -10000
-10001 -> -10000
```
全部符合 banker's rounding、且与 `to_units` 声明的同一惯例一致。**半格进位方向已声明、已验证、确定性成立**。✅

**结论：§一 三条全部独立复现通过。**

---

## §二 五处判定

### A ⭐⭐⭐ 规整作用域 —— ✅ 通过，且比字面要求更牢

`_geom_units` docstring 逐条列出「调用点 → 文档字段」的坐标外延，`INGEST_NON_COORDINATE_PATHS`
豁免表逐条带理由。**独立验证**：

1. 新事实层文档里 `/generator/tolerances/*` 子树**实测 0 条路径**（遍历全文档 JSON 树逐叶验证）——
   施工方「新层无该子树，无从被触」的说法核实为真。
2. **更强的证据**（不只是「今天没有」）：`scan_ingest_resolution_violations` 的扫描核心
   `_iter_int_leaves` **只遍历 Python `int` 叶子**，float 天然不进入检查——构造一份含
   `{'generator': {'tolerances': {'eps_a': 1e-6, 'eps_b': 1e-9}}}` 的合成 payload（连同正常的
   1mm 对齐坐标）喂给扫描器，**返回 `[]`**。⇒ 就算这类配置量将来**重新出现**在文档里，只要它是
   float（该类量本来就是 float），扫描器**结构上看不见它**，不是「今天恰好没有」的运气。

### B ⭐⭐⭐ 判据能变红 —— ✅ 独立复现（不用施工方的测试文件）

自己在**进程内**用 `pytest.MonkeyPatch` 把 `_geom_units` 换回 `to_units`（关掉唯一的 snap 门），
重建 sm25 as-received：

```
violations with snap removed: 100
violations with snap intact:  0
```
判据能红能绿，不是恒绿的摆设。✅

### C ⭐⭐ 哈希/基线连带更新 —— ✅ 通过

`grep -rn "ddaaae15"` 全仓（排除 `.git`）：**只出现在 `AI_agent/logs/reviews/` 下的历史裁决/交件 md
文件**（08-24、09-05 两份历史记录，属于「记录当时发生了什么」的档案，不是活判据），**没有任何
`.py`/`.json`/测试断言里还钉着旧哈希**。自己重算 `content_sha256`（`sha256(canonical json)`）核对
`case_tests/.../as_measured.json`：`2456a7ff...`，与 `revisions.json` 里的
`as_measured_content_sha256` 字段**逐位相等**。✅

### D ⭐ `as_measured.py` 单位段落 —— ✅ 通过

原文（79-107 行）已读——两句话都在且不矛盾：「存储单位 0.1mm 整数，⛔ 不是 snap」+
「入库分辨率 1mm，**是**一道 snap，A-11 用户终裁」。`to_units` 自己的 docstring 也补了一句
「no snap inside」并指向 `_geom_units` 是第二步。文档没有说谎。✅

### E 单一声明点 —— ✅ 通过

`grep -rn "INGEST_RESOLUTION_UNITS\|GROUP_QUANT"`：`INGEST_RESOLUTION_UNITS = 10` **只在**
`as_measured.py:169` 声明一次，`answer_compiler.py` 通过 `from .as_measured import
INGEST_RESOLUTION_UNITS` 引用同一个名字（不是复制字面量 `10`）；`GROUP_QUANT = 3` 独立存在于
`denominator.py`，两者互相不复用，`as_measured.py:164` 有正面的「不要混淆」声明。✅

---

## §二之二 范围长大了一圈 —— 判定：zone 侧规整**必须做**，但**暴露了一个未被处理的真缺陷**

### 1. zone 侧是否必须一起规整？—— ✅ 是，实测证实（不是「顺手做」）

用进程内 monkeypatch 把 `_world_point_to_ingest_grid` 换回不做 A-11 对齐的 `_world_point_to_units`
（即撤销 §二之二 的 zone 侧改动，facts 侧的核心规整原样保留），重跑
`reconcile_boundary_basis`：

```
WITH zone snap（当前提交状态）:    2 条 residual（F1-z4/z5，各 1182000 units²）
WITHOUT zone snap（monkeypatch撤销）: 4 条 residual：
    F1-z5: 1221400   （比有snap时的1182000更大——0.1mm代表性噪声叠加在真差上）
    F1-z4: 1221400
    F1-z10: 157600   （纯代表性噪声，有snap后完全消失）
    F1-z11: 157600   （同上）
```
**结论**：不做 zone 侧规整，`test_projected_ring_identity_holds_with_no_tolerance_at_all` 的红
不是变少而是**变多**（4 条而非 2 条），且残留的真差被噪声污染放大。zone 侧规整确有必要，
判别法则成立：不做它，代表性噪声会冒充/放大几何差。

### 2. ⛔⛔ 但即使做了 zone 侧规整，测试仍然是红的 —— 这是本单最大的问题

**独立全量已经显示**：`test_f156_ring_from_intersection.py::test_projected_ring_identity_holds_with_no_tolerance_at_all`
**在被审 commit 上失败**（`residuals == []` 断言，实际 `residuals` 有 2 条 1182000 units² 的真几何差）。
执行文档 §二#4 承认这个差「保留并点名」，但**没有意识到（或没有报告）它让这条零阈值断言变红**——
交件的「受影响链」命令表**没有包含** `test_f156_ring_from_intersection.py` 这个文件，因此从未被跑过。

**更严重的是内部矛盾**：同一批改动里，`tests/test_boundary_condition_facts.py` 的
`test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches` **被更新**为接受
`deferred cavities == 4`（含这 2 条 1182000 的残差，作为「已知延后」处理，且该测试**当前通过**）——
但覆盖**同一份数据、同一个不变量**的 `test_f156_ring_from_intersection.py` **没有被同步更新**，
仍断言这两条残差不可以存在。**一个文件把它当「已知可接受的延后项」，另一个文件把它当「零容忍红线」**，
这是同一次改动留下的自相矛盾，只因为交件的受影响链选择漏了后一个文件才没被发现。

### 3. 「把期望值改成先贴格点再比」是否把判据调松 —— ❌ 未发现调松（独立验证）

对 `test_answer_compiler_profiles.py` 改后的断言做**自己的变异测试**（不用施工方的锁）：
直接调用编译器拿到 `answer.views[*].zones[*].vertices`（真实 sm25 数据），人为把第一个顶点分别
偏移 0.3/0.6/1.0/2.0/5.0 mm，重跑改后的「贴格点再比」逻辑：

```
baseline（无扰动）: 25 checked, 0 failed
偏移 0.3mm: 25 checked, 1 failed   ← 抓住了
偏移 0.6/1.0/2.0/5.0mm: 均 1 failed
```
**即使 0.3mm 这样接近 1mm 网格宽度一半的扰动也被抓住**，回答复核单的问题
「改后的断言在什么情况下会不通过」——**答案不是「几乎不会」**，这条判据的判别力没有被调松。
✅ 不阻断（`test_denominator_from_facts.py` 同一模式，结构相同，未重复做变异测试，但代码路径
一致，判定同理适用）。

### 4. `gt/*/gt.json` 一字未动 —— ✅ 确认

`git diff c7c6831a..83326ba6 --stat -- 'case_tests/test_baseline/gt/*/gt.json'`：**空输出**，
`--stat -- 'case_tests/test_baseline/gt/'` 整个目录也是空输出。零改动，字面属实。✅

---

## §三之二 台账 5→3 —— 独立复核通过，但发现一个未被文档化的结构性风险

### 1. 独立复核旧台账 5 条全 unsigned/action=null —— ✅ 确认

自己 `git show c7c6831a:.../revisions.json` 打印全部 5 条：`rev-13ac/13ad/13ae/13af/160a`，
**逐条** `verdict='unsigned'`, `action=None`, `signed_by=None`, `signed_at=None`。零已签字记录。
新台账（3 条）：`13ac`/`160a` 消失（候选 `delta=-2 units=-0.2mm`，规整后 before/after 同值，
探测器判定「no field differs」，机制成立）；`13ad`/`13ae` 浮现为 `const -30`（3.0mm）；
`13af` 原样保留（非正交归类问题，与规整无关）。与执行文档描述完全吻合。✅

### 2. 重出台账是否等价于「签字流程之外写台账」—— 判定：不违反，是合法的候选刷新

`gt_revisions.py` 模块本身**不写文件**（"this module never touches a filesystem path"），
`detect_translate_candidates` 是**已有的**（先于 A-11 存在，`test_gt_revisions_and_as_signed.py`
里早有覆盖）机器探测器，其输出只能是 `verdict=unsigned`/`action=None`（类型层强制：
`action` 只能在已签字且 `verdict=="drawing_error"` 时非空）。重跑探测器、拿新的 as_measured
重新生成候选列表，不会、也不能产生一条自称已签字的记录。**这不是「签字流程之外写台账」**，
是候选探测器对新输入的正常重跑。✅ 不阻断。

### 3. ⚠️ 「将来遇到已签字记录会怎样」—— 交件没写，且找到一个真实的结构性空当

去检查实际写盘函数 `gt_facts_staging.py::write_facts_candidate`：**它只验证「新的三件套内部自洽」
（`verify_as_signed_reproduction`），不检查「即将被覆盖的旧 `revisions.json` 里是否有已签字记录」**——
是**无条件覆盖写**（`_write_atomic(out_dir / "revisions.json", ...)`）。今天这个方向零存货
（`find case_tests -iname "revisions.json"` 全仓只有 sm25-L/sm24 两份，且模块自己的 docstring
声明 staging 目录「按设计只应该装 unsigned 记录，签字流程另有归处」）——**所以今天不出事，
但这是这个目录/写函数本来就有的性质，不是 A-11 新引入的漏洞**。
**记为 B 层**：不阻断本单（不是本单引入、今天零存货、且模块设计契约声明了这个方向不该发生），
但**执行文档应当写这一句而没写**——复核单明确要求「请要求交件写明处置方式」，交件没有。
建议：下一次涉及 `write_facts_candidate` 的改动，把「拒绝覆盖含已签字记录的旧文件」补成
一条显式前置校验（哪怕今天用不上），比继续靠「今天零存货」撑着更安全。

---

## §三 sm21 / sm24 范围复核

### sm21 无法重出 —— ✅ 独立复核确认

`find case_tests -iname "request*.json"`：只命中 `sm24_anchor/request.json` 与
`sm25-L_anchor/{request.json,request_as_measured.json}` 两处；`sm21_anchor/` 目录下
`ls` 只有 `source.dxf`。施工方拒绝为 sm21 现造 request.json 的判断成立，B 层记录合理。✅

### sm24 facts 首次生成算不算 A-11 范围 —— 判定：算，不是 G-a

派工单 §一「三个 case（sm21 / sm24 / sm25）的 facts 全部重出」与派工单 §五#4「三个 case 都要
重出（sm21 旧层本来就 0 个偏移，新层需另量）」**明文要求三个 case 都要有新层 facts**。
sm24 首次生成新层 facts 三件套是**派工单字面要求的一部分**，不是超出范围的自选动作；
`revisions.json` 空台账（`"revisions":[]`）核实为真（零签字记录，未破「只有签字流程能写
revisions」的字面——因为它压根没有非空内容）。**不需要挪到 G-a**（G-a 特指 sm25 gt **答案根**
的整份重做重签，与 gt_staging 的事实层首次建仓是两件事）。

---

## §〇之二 · 2 施工方在没有全量的情况下改了 9 个测试文件读数 —— 判定见上，汇总如下

| 文件 | 判定 |
|---|---|
| `test_answer_compiler_profiles.py` | ✅ 未调松（自己变异测试验证，0.3mm 即抓住） |
| `test_denominator_from_facts.py` | ✅ 同构未调松（同一贴格点模式，代码路径一致） |
| `test_boundary_condition_facts.py` | ⛔⛔ **读数更新本身没错**，但与未同步更新的
  `test_f156_ring_from_intersection.py` 对同一不变量产生矛盾读数——这正是全量红的第二个根因 |
| `test_gt_facts_staging_sm25.py` | ✅ 独立核对 test_6/test_3 变化与 §三之二 台账复核一致 |
| `test_as_measured_facts_layer.py` | 未独立重新推导每个数字（时间所限），但其锁的读数已被独立全量间接验证（该文件本身在全量中通过） |
| `gt_revisions.py` docstring | ✅ 零逻辑改动，纯叙述更新，读过原文属实 |
| `answer_compiler.py` | 见 §二之二（新增函数已验证正确复用单一声明点、未调松判据） |
| `sm25-L_anchor` / `sm24_anchor` facts 三件套 | 见 §一（0 violations 独立复现） |

**结论**：9 个文件里，**8 个文件的读数更新本身站得住**；**问题不在任何一个文件内部改错了什么，
而在“受影响链”的选择范围本身没有覆盖到所有共享同一几何不变量的兄弟测试文件**，
导致一个真实存在的新缺陷（F-153 form B 的 1182000 units² 真几何差）在一处被妥善处理为
「已知延后」，在另一处被放着刺穿零阈值红线，而这个矛盾只有在真正跑全量时才会现形。

---

## ⛔ 阻断（1 项，含 2 个独立机制的根因）

### 阻断-1：独立全量红 `5 failed`，两个根因均确认为本单引入的真回归

**根因 A**（3 条：`test_b1_projection_bridge_fixtures.py::{test_fixture2_two_unit_remainder_still_red,
test_fixture5_removed_wall_red_at_reconciliation_only, test_4b_counts_equalised_attack_red_only_on_2_and_3}`）：
这三个测试的「注入缺陷」逻辑依赖**硬编码的字面墙 ID 字符串**（如
`w_x_99430_100630_52401_88800`、`w_y_50000_52400_121599_140000`），这些 ID 里嵌着 A-11 之前
sm25 真实数据中那批**0.1mm 代表性残差**本身（`52401`、`121599` 这些数字**正是**被 A-11 规整掉的
74 个数之一）。A-11 重出 facts 后，这些墙的坐标被 snap 成 `52400`/`121600`，**它们的 ID 也跟着变了
（ID 是坐标派生的字符串）**。三个测试的「查找该 ID 并修改/删除它」逻辑因此**匹配不到任何墙**，
静默变成 no-op ——本该注入的缺陷从未真正被注入，测试断言（针对「缺陷被注入后的红」）落空。
**独立验证**：`facts["views"][...]["walls"]` 里逐一 `grep` 确认目标 ID 已不存在，近似 ID 变体
（`...52400...`、`...121600...`）确实存在。

**根因 B**（2 条：`test_f156_ring_from_intersection.py::{test_projected_ring_identity_holds_with_no_tolerance_at_all,
test_moving_one_converter_edge_by_a_tenth_of_a_millimetre_reddens}`）：见 §二之二 之 2——
一个真实几何差（F-153 form B，1182000 units²）因 A-11 的规整+ring闭合而首次可见，
`test_boundary_condition_facts.py` 被更新去接受它（`deferred==4`），但**位置更靠近**这个不变量的
零阈值测试 `test_f156_ring_from_intersection.py` **没有被同步更新**，两者现在断言矛盾。

**为什么记为阻断**：复核单 §〇之二明文写着「全量从未跑过 ⇒ 这一格由你填 ⇒ 它红了本单就不能合并」——
这不是我加的门槛，是本单自己的准入条件。两个根因都独立可复现（基点 `c7c6831a` 干净的独立
worktree 上跑同 5 条全绿），排除环境噪声。

**建议修法**（不代做，留给返工）：
- 根因 A：三个 fixture 测试改成**通过语义定位墙**（比如按 `axis`+已知的 face_lo/face_hi+相对位置
  找墙），而不是硬编码历史坐标派生的 ID 字符串；或者如果测试的本意就是要固定死某个特定 handle，
  改用 DXF handle（如 `13AD`/`160A` 这类，A-11 不改 handle，只改坐标）而不是坐标派生 ID。
- 根因 B：让 `test_f156_ring_from_intersection.py` 的两条测试与 `test_boundary_condition_facts.py`
  对 F1-z4/F1-z5 这两个「已知延后」的 cavity 采用**同一套排除口径**（比如都通过
  `DEFERRED_PROJECTION_CODES` 显式豁免，而不是一处硬编码 `residuals == []`、另一处放行）——
  这本质是「F-153 form B 到底算不算这批的已知债」需要一次正面裁决，而不是两个文件各自表态。

---

## 不阻断（3 项）

1. **§三之二 #3**：`write_facts_candidate` 无条件覆盖 `revisions.json`、不检查旧文件是否含已签字
   记录——今天零存货、非本单引入，但执行文档未按复核单要求写明处置方式，建议下次触碰该函数时
   补一条显式前置校验。
2. **§二之二 的「两个 zone 侧真几何差如何最终定性」尚未拍板**：1182000 units² 的 F-153 form B
   差异本身是真实缺陷（不是本单造成的，是本单让它第一次可见），阻断-1 的根因 B 修完后，
   这条差异该记入哪个既有单子（F-153 后续 / 新债）需要主控裁定，不属于 A-11 施工方能自行决定的事。
3. **`test_as_measured_facts_layer.py` 的读数未逐条重新独立推导**：时间所限，只确认该文件在全量
   里通过，未像 §二之二/§三之二那样做变异测试验证判别力；不阻断,但下一轮返工审可以补做。

---

## 未复现项清单

- `test_as_measured_facts_layer.py` 三处读数变更（split 2/4→0/0、missing 11→9、edges 171→179）
  的**判别力**未独立变异验证（见不阻断-3）。
- sm24 首次 facts 生成的坐标层未做与 sm25-L 同等深度的「换同形输入」对抗测试（§一#3 只在
  `snap_to_ingest_resolution` 纯函数级别做了穷举，未针对 sm24 的具体 DXF 数据重跑一遍）——
  时间所限，判断为可接受（sm24 本来就 0 违规、规整前后 sha 逐位相同，是最强的「什么都没做错」
  证据，且不在阻断范围内）。

---

## 给返工的话

**不需要重新论证走乙、不需要重新推翻 74 个数的规整机制本身**——§一/§二 A-E 全部独立复现通过，
核心机制是对的。**唯一要修的是阻断-1 的两个根因**：把 `test_b1_projection_bridge_fixtures.py`
三个测试的墙定位方式从「硬编码坐标派生 ID」改成不受 1mm 规整影响的锚点；把
`test_f156_ring_from_intersection.py` 与 `test_boundary_condition_facts.py` 对 F1-z4/z5
两个 cavity 的处理口径统一。修完后**必须自己跑一次本单要求的独立全量**（`-n 6`），
不能只跑受影响链子集——这正是本单第一次栽跟头的原因。
