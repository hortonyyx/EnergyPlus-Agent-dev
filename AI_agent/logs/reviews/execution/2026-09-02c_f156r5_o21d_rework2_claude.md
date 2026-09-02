# 执行档 · F-156 第五轮 / ②-1d 第三轮返工（Claude 施工席）

- 日期：2026-09-02 · 施工方：Claude 家族施工席 · 派工单：[`request/2026-09-02c_f156r5_o21d_rework2_dispatch.md`](../request/2026-09-02c_f156r5_o21d_rework2_dispatch.md)
- 开工 HEAD：`2e840f6` · 被动对象：`src/agent/judge/answer_compiler.py` 的 `reconcile_boundary_basis`（exclusion 消费端）
- **结论先行**：⛔ **触发派工单 §六 A 层③，停下上报，未改任何生产代码。** 见 §四。
  - 单子两条阻断我**均实测复现**（§一）。
  - 病根定性（§二，「把两种性质不同的东西数进同一个数」）**我实测确认成立**，不反驳。
  - blocker 1（below_request 假红）的修法**干净、可实现**。
  - blocker 2（registered_ring_loss 灌证在 `excluded == paired` 点必须红、⛔ 不许用比例）
    —— **在消费端做不到「逐条独立证明」，而 blanket fail-loud 会永久判红真实 sm25 的合法 endcap loss** ⇒ 正是 A③。
  - ⭐ 我**找到了 A③ 让我报的「第三条路」**（reason 逐条几何复核 + 其余 reason fail-loud），但它是一个**承重设计岔口**（在消费端重实现生产者的几何、7/8 reason 无夹具存货、要重写 11 条锁的夹具），**需你/派工方裁一刀**，⛔ 我不单方面拍。

---

## 〇、开工自检（三条全过）

命令原文：
```bash
git -C /tmp/joint_rework_claude rev-parse --short HEAD
ls AI_agent/logs/reviews/request/2026-09-02c_f156r5_o21d_rework2_dispatch.md
python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)"
```
输出原文：
```text
2e840f6
AI_agent/logs/reviews/request/2026-09-02c_f156r5_o21d_rework2_dispatch.md
/tmp/joint_rework_claude/src/agent/judge/answer_compiler.py
```
环境自证（与后续探针同一 shell，注入主树 `.env`）：
```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
python -c "import src.agent.judge.answer_compiler as m; print('MODULE', m.__file__)"
```
```text
MODULE /tmp/joint_rework_claude/src/agent/judge/answer_compiler.py
```
`m.__file__` 落在本 worktree ⇒ 承重不变量成立（§5#8.6：cwd 胜过 `.pth`）。

---

## 一、两条阻断均实测复现

### 阻断 2（先报，最硬）：`excluded == paired` 的均衡灌证原样穿过

`answer_compiler.py:1428` = `if excluded > paired:`。取真实 sm25，drop 每个 view 一半 pairing 的
`boundary_edges`、按 cavity 自身面积补 `registered_ring_loss` 台账（合法 reason、合法 span）：

命令原文（关键片段，完整脚本见本档 §六附录）：
```python
# 每 view drop k=n//2 个 pairing -> paired=n-k, excluded=k；n 偶数时 paired==excluded
```
输出原文：
```text
BLOCKER 2 (balanced flood):
  plan-F1: paired=6 excluded=7
  plan-F2: paired=7 excluded=7
  flood gate codes: ['boundary_exclusions_exceed_pairings_in_view:plan-F1:paired=6:excluded=7']
  # true-looking losses granted as exclusions: 14
```
⇒ **plan-F2 在 `paired=7 / excluded=7` 上没有任何 flood code**：7 个真实房间被伪造台账灌成
exclusion，门全绿放行。**阻断 2 属实。**

### 阻断 1：诚实的 below_request 排除被计入配额 ⇒ 假红

`answer_compiler.py:1422-1424` 的 `for exclusion in exclusions:` **不区分 evidence 类型**，把
`below_request_area_threshold` 也计进 `excluded_per_view`。真实 sm25 每个 view 有 6 个 `0.0576 m²`
子阈值 raw cavity（可各拆 2 个不重叠 shaft zone = 12 个诚实排除）：

命令原文：
```bash
python -c "... 打印 min_room_area_m2 与每 view 子阈值 raw cavity 数 ..."
```
输出原文：
```text
min_room_area_m2 = 5.0
plan-F1 sub-threshold raw cavities: 6 areas_m2 [0.0576, 0.0576, 0.0576, 0.0576, 0.0576, 0.0576]
plan-F2 sub-threshold raw cavities: 6 areas_m2 [0.0576, 0.0576, 0.0576, 0.0576, 0.0576, 0.0576]
```
plan-F1 现约 12 paired；12 个诚实 below_request 排除即把 `excluded` 顶到 ≈paired 之上。复核方已独立
跑通同形夹具（裁决 §一，`11 paired / 12 excluded` 假红，`test_..._is_false_red` 1 passed）。
机制在代码里一目了然（1422 行无 evidence 过滤）。**阻断 1 属实。**

---

## 二、病根定性：实测确认，不反驳

单子 §二：「门把两种性质完全不同的东西数进了同一个数」。**成立。**
- `below_request_area_threshold` = **独立可证**：raw cavity 面积由门自己从 `footprint − wall_region`
  重算，阈值来自 **request（另一个作者）**。二者都不是 producer 说了算。
- `registered_ring_loss` = **producer 自写台账**（`view.boundary_ring_losses`），哈希只防篡改、不防作者自己写。

真实 sm25 台账当前只剩 **1 条**（F-156 v3 后 3→1）：
```text
VIEW plan-F1 | cavity cavity:04e1293098b1a95a | reason endcap_const_not_a_measured_parallel_face | area 2868321200
   span: axis=y const=52401 lo=99430 hi=100630 side=-1 p1=[52401,100630] p2=[52401,99430]
         nearest_same_axis_wall_face_const=52400 delta=1
```
它承载 **2 个 converter zone**（共用/欠切分腔，z4/z5），门里已 `passed=False`（唯一红码是 F-157 延迟的
`facts_projected_ring_unavailable ×2`，属 `CODES_OWNED_BY_ANOTHER_LOCK`）。

---

## 三、blocker 2 的核心：为什么消费端做不到「逐条独立证明」（逐个候选实测否掉）

单子 §三#2 + 硬边界：registered_ring_loss 要么**逐条独立 applicability 证明**，要么 **fail-loud**；
⛔ 不许比例。我把所有能想到的「逐条独立证明」候选都实测了，**每一个都不干净**：

### 候选 A：span 落在 raw cavity 边界上（跨「门重算的几何」对账 producer 的 span）
- 真实 endcap loss 的 span 两端点到 raw cavity 边界 **距离 = 0.0**；裁决/单子用的
  `SYNTHETIC_SPAN`（p1=[1,1000]）距离 **78909 单位** ⇒ 能抓合成 span 的灌证。
- ⛔ **但被「引用真实边」的灌证击穿**：拿一个真实 paired 房间的 raw cavity 的**真实一条边**当 span、
  合法 reason，实测——
  ```text
  real edge p1 (147600.0, 119400.0) p2 (147600.0, 112600.0) axis? y-const
  after real-edge flood of 1 cavity: exclusions 3 granted for target? True
  span p1 dist to its raw cav boundary: 0.0
  ```
  **exclusion 照样授予**。⇒ span-on-boundary 是 [[proxy-mistaken-for-the-thing]]：「span 在边界上」≠
  「这腔真的成不了环」。⛔ 不承重。

### 候选 B：raw cavity 与 converter zone 的对称差 / 「腔里含几个 zone」
- 实测对称差比：诚实 endcap 腔 0.565、真实 paired 腔 0.10~0.27 ⇒ **这是个阈值**（硬边界禁），
  且被 F-157 的基准错位（wall_axis vs outer_skin 差半墙厚）污染，真实 paired 房间本就不为 0。
- 「含 ≥2 zone」：诚实 endcap 腔含 2 zone，**但一个真实 paired 走廊腔含 6 zone** ⇒ 也不干净，
  且 zone 数 ≠ 环推导失败，仍是代理量、且可被 converter 过切分绕过。⛔ 不承重。

### 候选 C：逐 reason 复核（endcap = 「附近无平行量测墙面」）+ 其余 fail-loud（= 「第三条路」）
- endcap 这一条 reason **可以**在消费端独立核（拿门自己的墙面几何验「span 处确无平行量测面」，
  真实房间的边一定有平行面 ⇒ 能否掉「拿真实边灌 endcap」）。
- ⇒ 于是可以：**能核的 reason 逐条核、不能核的 reason 一律 fail-loud（红）**。这**同时满足** §五 全部六条
  （诚实 endcap 绿、任何灌证红含 `excluded==paired`、无比例、可红可绿）。
- ⛔ **但它是一个承重设计岔口，代价我不该单方面吞：**
  1. **在消费端重实现生产者的几何判定**（`_boundary_parallel_measured_faces` 那套）——正是
     [[recompute-gate-must-mirror-producer-definition]] / [[deterministic-input-does-not-imply-correct-derivation]]
     反复咬人的地方：差一点就把**唯一一份诚实 endcap loss 判红**，而我只有这**一个**真实样本可回归。
  2. **8 个 reason 里 7 个没有夹具存货**（真实 sm25 只用了 endcap）⇒ 那 7 条 fail-loud 分支
     [[gate-teeth-direction-follows-fixture-inventory]] 无法证明分辨力，等于凭空造 7 条不可证的机器。
  3. 现有 11 条锁的夹具（`_strip_ring` 用 `SYNTHETIC_SPAN` + reason `merged_lt_3`）在此方案下**全部 fail-loud 变红**，
     必须**重写夹具**成「可核的 endcap loss」。§五#1 确实授权重建夹具，但这是一次**大改**。

### 为什么 blanket fail-loud（不搞候选 C）会让 sm25 「整份不可用」
把所有 registered_ring_loss 一律判红 ⇒ 真实 sm25 那条**合法** endcap loss（一个真实的、确实成不了
逻辑环的墙端头空腔）永远红。exclusion 机制的**全部意义**就是合法地容纳这种腔；把它判红 ⇒ 即便
F-157 落地、其余全绿，sm25 **也永远过不了这道门** ⇒ 单子 §六 A③ 说的「fail-loud 会让真实 sm25 整份不可用」成立。

---

## 四、⛔ 触发 §六 A 层③，停下上报

A③ 原文：「『逐条独立证明』在结构上做不到，而 fail-loud 会让真实 sm25 整份不可用（⇒ 这说明还有第三条路
我没想到，停下来告诉我那条路）。」

**两个条件我都实测坐实**：
1. 消费端**干净的**逐条独立证明**做不到**（候选 A 是代理量被真实边击穿；候选 B 是禁用的阈值+被 F-157 污染）。
2. blanket fail-loud **永久判红** sm25 的合法 endcap loss ⇒ 整份不可用。

**⭐ 我把 A③ 要的「第三条路」找出来了 = 候选 C**（能核的 reason 逐条核 + 其余 fail-loud）。它技术上能满足
六条验收，但**代价是三条承重取舍**（消费端重实现生产者几何 · 7/8 reason 无存货 · 重写 11 条锁夹具），
**这三条里任何一条都可能让本轮再被 REWORK**（尤其第 1 条正撞 recompute-mirror 病族）。⇒ 我不单方面拍，**请裁一刀**：

- **路 C（逐 reason 核 + fail-loud 兜底）**：我照做，接受「消费端重实现几何 + 7 条无夹具 fail-loud + 重写夹具」。
  —— 若选此，请确认：7 个未被真实数据行使的 reason **一律 fail-loud** 是可接受的口径吗？
- **路 D（窄 fail-loud + 把灌证防线上移到签字/事实层）**：消费端只保留 blocker-1 的 below_request 分离
  （诚实不再假红），registered_ring_loss 的**真伪不在消费端判**，改由**产出 as_signed 的那一步**保证
  （台账不能凭空 drop 真实 boundary_edges 再补 loss）。—— 这承认「消费端 gate 不是拦灌证的正确位置」。
- **路 E（重新审视硬边界）**：若逐条独立证明在消费端结构性不可得，是否接受一个**非比例**的聚合口径
  （例如：仅对 registered 方向、且要求每条 registered 排除都带**可机械对账的独立凭据**，凭据缺失即红）——
  但这仍要回答「凭据从哪来」，本质上回到路 C/D。

我的**倾向**：**路 D**。理由：blocker 2 的威胁是「producer 自写台账灌证」，而**能独立核这件事的信息在产出
台账那一步最全**（那时还看得见被 drop 的真实 edges）；消费端 gate 拿到的是**已签字的既成事实**，注定只能
在代理量与 fail-loud 之间二选一。把防线放在源头，符合 [[lexical-guard-cannot-be-completed]] /
[[declare-the-dialect-plus-consumption-ledger]]「边界搬到进程/产出层」。但这**超出本单范围**（要动的不是
`answer_compiler.py` 而是写 `boundary_ring_losses` 的 `as_measured.py` 一线），故按 §六**合法出口**：
写清「哪个文件、为什么绕不开」并停报，⛔ 不硬改。

---

## 五、逐条对 §五 六条验收（现状：全部 blocked-pending-ruling，⛔ 无一实现）

| # | 规则 | 现状 |
|---|---|---|
| 1 | 诚实按阈值排除无论多少都不得判红 | **未实现**。修法干净（count 只计 registered、不计 below_request），但单独做它**不能**修好 blocker 2（见 §三：filter 后 plan-F2 仍 7 registered vs 7 paired，`7>7` 仍 False）。故不单独交。 |
| 2 | producer 台账灌证必须红，含 `excluded==paired` 点 | **未实现 = A③ 阻断本身**。见 §三/§四。 |
| 3 | 新判据能红能绿、摘实现回红 | **未实现**。 |
| 4 | 原 11 条撤证锁 + 奇数 NA 全绿 | **未动**（零代码改动，树干净）。⚠️ 注意：路 C 会要求**重写** 11 条锁的夹具（现夹具在路 C 下 fail-loud 变红），这本身也需你知情。 |
| 5 | 自造不同形状攻击也红 | **未实现**。（§三已附一个「引用真实边」的攻击，正是它击穿了候选 A。） |
| 6 | 全量绿（`-n 6`） | **未跑**：本轮**零生产代码改动**，工作树干净（`git status` 空、`HEAD=2e840f6`），权威全量与基线一致，无 diff 可验 ⇒ 不为 no-op 烧一次全量。 |

---

## 六、附录：探针命令（可复跑）

所有探针在注入主树 `.env` 的同一 shell 内、`m.__file__` 落本 worktree 时运行；均为**只读**，未写树。

1. 真实台账 loss 枚举、span 落界距离、SYNTHETIC 距离、genuine vs paired 对称差、balanced flood、
   real-edge flood、子阈值 cavity 清点 —— 逐条脚本见本执行档对应 §一/§二/§三 输出块上方的命令注释。
2. 关键读数复述：
   - genuine endcap span 到 raw cavity 边界距离 = `0.0`；SYNTHETIC 距离 = `78909.16`。
   - real-edge flood：`granted for target? True`（候选 A 被击穿）。
   - balanced flood：`plan-F2 paired=7 excluded=7`、无 flood code（阻断 2）。
