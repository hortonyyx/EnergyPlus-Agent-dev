# 复核 · W-1 的 T3 抢救半成品（主控审）

> **被审对象** = `9d79dfe7`（主控抢救落库，⛔ 非施工方交付），基线 `56714187`，
> 分支 `wt/09.07h_w1_flow`，worktree `/tmp/w1_flow_glm`。
> **审阅 = Claude 家族 orchestrator**（⚠️ 抢救提交也是我做的，但那一笔**零内容改动**、
> 只是 `git commit` 一堆别人写的行 ⇒ 不构成「谁写谁不批」的自审）。
> **口径** = 拍板书 `2026-09-07i_W1_T2_ratification.md` §四 + 派工单 §四。

## 裁决：**REQUEST-CHANGES**（4 条阻断 · 2 条不阻断）

⚠️ 施工方是**撞额度被打断**的，⛔ 不是交件。所以下面的阻断**大半是「没走到」而不是「做错了」**——
写出来是为了让接手方拿到一份**完整题面**，⛔ 不是给缺席的席位记过。

---

## 一 ✅ 已落地**且已接线**的两块地基

### ① 足迹跨层吸附（`multifloor.py` +367 行）—— **BLK-1 已实测解除**

拍板书 §一 要的那条读数，我拿**真产物**跑出来了：

```
sm25_1f_v2.json: bound_x=8.2425 mm  bound_y=7.2703 mm  cap=60.00 mm
sm25_2f_v2.json: bound_x=7.1949 mm  bound_y=6.4351 mm  cap=60.00 mm
noise_bound = 20.6435 mm
cap         = 60.0000 mm
TOLERANCE   = 20.6435 mm   ← 管事的是 noise 支
```

- ⭐ **管事的是 noise 支、不是 cap** ⇒ 派生式**真的在决定行为**，⛔ 不是「把 cap 当成换了名字的常数」。
  这正是 BLK-1 原本要治的病（发明的 50 mm 兜底把派生项架空）。
- 实测残差 7–12 mm ⇒ 余量 **1.7–3×**。够，且不夸张。
- 那条**零阈值自报漂移校验**（`abs(recomputed − declared) > 0.0`）在两份真产物上**都通过**
  ⇒ ⛔ 不会在生产里假红。这一条我特意验了，因为浮点零阈值是常见的翻车点。
- 拒绝路径也对：超容差 ⇒ **原样放行**，交给既有的 `PER_FLOOR_FOOTPRINT_MISMATCH` 大声拒绝，
  ⛔ 没有在这里吞掉真退台。

**已接线**：`pipeline.py:1735` 在 `run_multifloor_correction` 里调用。

### ② 角点环 `_corner_only_ring`（`projection_bridge.py` +61 行）

零容差删共线点（`cross != 0.0`），并按面积符号翻成 CCW。**已接线**：`project_cut_lines`。

---

## 二 ⛔ 阻断（4 条）

### BLK-A ⭐⭐⭐ · **拍板书接受 T2-⑤ 所依据的那件事，代码里不存在**

拍板书 §二 T2-⑤ 那一格，我当时写的通过理由**原文**是：

> 席位没有把它做成静默 —— 显式登记 `WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER`
> （exploratory FLAG / strict 挡）⇒ **把缺席变成了信号**。

实测：

```
$ grep -rn "WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER" --include=*.py .
src/agent/correction/window_sources.py:1144:  ...docstring...
src/agent/correction/window_sources.py:1242:  ...docstring...
```

**只在两处 docstring 里，零处代码。**

⇒ 用户拍板**接受**「新腿上那条 legacy 窗证据门暂时没牙」这个代价，
**前提就是「缺席被显式变成了信号」**。当前交付里**那个信号不存在**
⇒ 空窗目录目前是**静默**的，接受前提**当前为假**。

⭐ 这是本次审最重要的一条，且**形状值得记**：我在拍板书里转引了交件对自己的描述，
把「方案里写了要登记」读成了「登记这件事成立」。
按 [[citing-someone-elses-fact-does-not-transfer-responsibility]]：
**写进承重位置（拍板书的通过理由）前，我本该自己 grep 一遍。**

**要求**：把这条债做成**代码里的登记**（走既有 `EvidenceDebt` 机制，
`pipeline.py:55-59` 已有 `EvidenceDebt / write_evidence_debt / project_evidence_debt`），
并加一条锁：**exploratory 出 FLAG、strict 挡住**。

### BLK-B · **as_drawn 那条腿的窗输入构建器是死代码**

`build_verified_window_inputs_as_drawn` —— 全仓**外部引用 0 处**（只有自己模块内的
docstring 提及和自身定义）。而它正是 T1 撞出的 **B2 阻断**（`finalize.py:117` 对 V3
强制要 `verified_window_inputs`）的修法。

⇒ **写好了、没插上 ⇒ 端到端仍然过不去。**
按 [[neuter-proves-wiring-not-discriminating-power]] 的反向：**能力 ≠ 接线**。

### BLK-C ⭐⭐ · **生产入口一行没接 —— 这才是 W-1 的正题**

```
pipeline.py:2383   run_pipeline  → run_correction(...)   ⛔ 仍不传 evidence_chain
scripts/tool_scripts/run_stage.py                        ⛔ 本次零改动（git diff --stat 为空）
run_stage.py:457   flow CLI      → run_correction(...)   ⛔ 仍是 legacy 参数表
```

⇒ 用户的验收口径**「整个架构通、别需要现手搓」尚未兑现**：
今天要走新腿跑一个 case，**仍然只能手写脚本直调**，`flow` 到不了它。
这与 09-07 通查 §3.2 记的盘面**一模一样，没有推进**。

### BLK-D · **零测试**

634 行新代码，`git diff --stat -- tests/` **为空**。
按派工单 §四，每条新行为都要有锁；且按 [[gate-with-only-negative-assertions-is-unobservable]]，
新写的拒绝路径（`PLAN_CALIBRATION_MISSING` / `..._SUMMARY_DRIFT` /
`FOOTPRINT_RING_DEGENERATE` / `SNAP_DECLARATION_COUNT_MISMATCH` / 超容差 `refused`）
**一条都没有被行使过**——它们现在是「没尺子量」型潜伏
（[[two-kinds-of-latency-no-ruler-vs-never-reached]]）。

---

## 三 🟡 不阻断但要改（2 条）

### N-1 ⭐ · **叙述滞后于代码，而且就在本次新写的代码里**（G-g 同型）

`multifloor.py` 新注释用来论证「必须用 Hausdorff」的理由是：

> 两层环带着**不同数量**的共线细分顶点（sm25 上 94 vs 86）⇒ 逐顶点对应结构上不可能

但**同一笔提交**里新加的 `_corner_only_ring` 已经把环降成**角点环**——
`projection_bridge.py` 自己的注释写着 **「94 → 8 vertices」**。
⇒ 吸附实际看到的是 **8 vs 8**，那句「94 vs 86」描述的是**降维之前**的形态。

⚠️ **做法仍然对**（Hausdorff 比逐顶点稳，且对未来不等顶点数的输入更安全），
但**它给出的理由已经不成立**。这正是今天刚登记 **G-g** 的形状：
**同一份文件里叙述滞后于代码**，而 docstring 常被当契约读。

**要求**：改成按现状陈述（「环已在上游降为角点环；Hausdorff 是为了不依赖顶点数相等这个
上游可能变化的性质」），⛔ 不要留着一个会被后人当事实引用的过期读数。

### N-2 · **死参数造成「它也检查了产物」的错觉**

`_check_direction_facts_as_drawn(manifest, facts, raw_reading_artifacts)` ——
`raw_reading_artifacts` **只出现在签名里，函数体零使用**。

legacy 的 `_check_direction_facts` 是**要读产物**的（走 `parse_reading_view`）；
as_drawn 版**故意不读**、改钉 `_resolve_facade_flip_fields(None)` 的默认值——
**这个决定本身 docstring 已写清，我认可**（as_drawn 产物被 `ReadingView` 静默解析成空壳，
再去读它反而是假覆盖）。问题只在于：**保留一个同名不用的参数**，
会让读者以为这条腿也消费了产物。

**要求**：删掉该参数，或显式改名并写明「本腿不消费产物，理由见 docstring」。

---

## 四 ⛔ 我这次审的方法边界（如实登记）

| | |
|---|---|
| **实测过的** | BLK-1 的容差取值（真产物跑通，读数见 §一）· 四个新符号的调用者计数 · `tests/` 改动量 · 死参数 · 两个生产入口的调用参数 |
| **没实测的** | 吸附在真实两层几何上的**实际 Hausdorff 读数**（要跑模型链，成本高）· 全量（**另跑，见下**） |

⚠️ **关于「两次同族核实」**：BLK-A / BLK-B 我用的是**源码字面扫描**，与施工方的自检同族。
但这两条问的是**存在性**（「这个符号有没有调用者」「这个字符串在不在代码里」），
**字面扫描恰好是对该问题有分辨力的尺子**（零命中 = 真的没有）
⇒ ⛔ 不适用 [[two-checks-of-the-same-kind-are-not-two-checks]] 的告警。
反之 N-1 那种「注释说的还成不成立」**不能**靠字面扫描，我是逐段读出来的。

## 五 接手放行条件

1. **先 BLK-A**（把缺席变成真信号），再 BLK-B（接线），再 BLK-C（生产入口），BLK-D 随每段走。
2. ⭐ **每完成一段就提交** —— 上一轮 T3 段没执行分段提交纪律，634 行差点全丢。
3. 总验收不变：**一串命令序列，从 `0_reading` 到出分，全程标准入口、零现场手写脚本，
   逐字写进交件、任何人照抄能重跑。**
