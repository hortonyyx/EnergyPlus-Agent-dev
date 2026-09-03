# 跨家族复核请求 · **B1：投影桥核心 + 接线**

- **日期**：2026-09-03 · **请审方**：orchestrator · **复核方**：**Claude 家族**（⛔ 不得 GLM —— 施工方是 GLM 席）
- **被审 commit**：`6f43041`（分支 `08.23_AsDrawnReading`；施工分支 `wt/09.02aj_b1_bridge`，`--no-ff` 合并）
- **派工单**：[2026-09-02ad](2026-09-02ad_B1_projection_bridge_core_dispatch.md) ·
  **权威口径**：[设计稿 v7](../../proposals/correction_projection_bridge.md)（四轮跨家族审）·
  **交件**：[执行档](../execution/2026-09-02aj_B1_projection_bridge_execution.md)

## 一、diff（⛔ 只列代码）

```
919	0	src/agent/correction/projection_bridge.py   ← 桥本体
204	27	src/agent/pipeline.py                       ← 接线
12	0	src/agent/correction/decision_executor.py
159	11	tests/test_o22m7_evidence_wiring.py         ← ⭐ 那把 EvidenceChainTerminal 的锁被改写
178	0	tests/b1_gt_reconciliation.py
205	0	tests/test_b1_projection_bridge_acceptance.py
577	0	tests/test_b1_projection_bridge_fixtures.py
373	0	tests/test_b1_projection_bridge_production_loader.py
```

## 二、⛔⛔ 本单最要紧的背景：**「谁写谁不批」那道防线今天缺了半边**

**测试与实现是同一个席位（GLM）写的。** 24+ 条绿完全可能是**照着实现的形状长出来的**。
⇒ ⭐⭐⭐ **本轮复核的第一职责不是读代码，是【独立做变异实测】**：
**摘掉实现里的关键判断，看那些测试是不是真的会红。**
施工方自报做了 M1–M6（摘轴向映射 5 红 · 摘宿主唯一性 2 红 · 摘纪律 1 红 · 摘 sink 1 红 ·
摘 §9.1 补线 1 红 · 摘延伸规则 23 红）—— ⛔ **请你自己重做，并【另造至少两个它没试过的摘法】。**

## 三、⭐⭐⭐ 施工方**自报的最薄弱处**（请当第一攻击面）

> **生产链读数与夹具读数对不上，三个数都没归因**：
> **16 vs 15 面 · 316.70 vs 279.26 m² · 16 vs 0 悬端**。
> 线索：生产侧 **22 墙 / 87 opening 候选**，而 gt facts 是 **53 墙 / 30 opening**。
> 16 个悬端里 **13 个是厘米级真差、仅约 3 个是 ulp 级**。

⇒ **请判**：这是**桥的缺陷**、**reading 产物本身的缺口**、还是**两者都有**？
⭐ 判据提示：设计稿 §六 #6 的验收基准是**对 gt 签字 zone 双向逐个位置对账（F1 14 / F2 15）**——
那条在**夹具**上过了；**生产链这一侧过没过？** 若没过，B1 的验收 #6/#7 是否其实只在夹具世界成立？

## 四、⭐⭐ 施工方**点名请人攻**的一条

> 它把**生产侧的坐标 resolution 声明成 `0.0`**，并**拒绝**改用 calibration 的 `m_per_px`。

⚠️ 相关口径：设计稿 **N-3** 已写破「容差的 `units_per_metre` **只在 gt 侧存在**，
生产链是浮点米 ⇒ **接入时必须重新声明粒度来源**，⛔ 不许沿用 1 unit」。
⇒ **请判**：声明 `0.0`（= 精确比较、零容差）在生产链上**站得住吗**？
它会不会正是「16 个悬端里 13 个厘米级真差」的**成因或掩盖**？

## 五、⭐⭐ 主控点名的**一条活疑点**（⛔ 写成假说，未代判）

> **H-a：这算「把桥接上了」，还是「在异常旁边多写了一个文件」？**
>
> 实测：接线之后 `run_correction(evidence_chain=True)` **仍然抛 `EvidenceChainTerminal`**；
> 桥的产物是落盘的 `projection_envelope.json`。⇒ **管线并没有继续走到几何内核。**
>
> 而派工单 §四之二 写的是「本单**必然翻掉**那把锁」，验收 #7 写的是
> 「**单视图产物走到 `CorrectedGeometryV3` 并过 gate①**」。
>
> ⇒ **请判三件**：① 保留 terminal + 落盘 envelope 这个形态，**满不满足** 验收 #7？
> ② 那把被改写的锁（`test_o22m7_evidence_wiring.py` +159/−11）**还守不守得住原来那条纪律**
> —— 「**⛔ 不许把 provisional 当成品往下游送**」？③ 若不满足，**缺的是什么**：
> 是本单漏做，还是「envelope → 几何内核」本来就该是**另一单**（那就该登记，⛔ 不该含糊过去）。

## 六、其余要逐条验的

1. **指南 §十三 三条纪律**：⛔ 几何派生代码里有没有长度/厚度常数 · 夹具墙厚是不是掺了
   **90/150/300/370**（⛔ 不许只有 120/240）· 「正交」假设是不是**局部化 + 有名字**。
2. **验收 #3 的环带判据**：⛔ 有没有拿夹具 #3（厚度报错）的输入去验它的 ✅ 方向（那必假红）。
3. **验收 4b 的双向对账**：③「**每个 face 也必须配到 zone —— 无主面即红**」有没有真落地？
   请**造一个新形的「无主面」攻击**（与施工方夹具不同形）验它仍红。
4. **§9.1 共线缝**：派工单已替它选死 **①（按洞口延续补线）**——落地了吗？

## 七、环境

主控已在合并树上跑权威全量（读数随后附）。你自己跑用 **`-n 6`**；环境自证与 pytest 必须同一条命令：
`python -c "import src.agent.correction.projection_bridge as m; print(m.__file__)" && python -m pytest ...`
⭐ **本树已含 F-158 的出口门** ⇒ 不再需要 source `.env` 才能跑绿（那条已修）。

## 八、交件

`AI_agent/logs/reviews/verdict/2026-09-03f_B1_projection_bridge_crossreview_claude.md`：
裁决 + 阻断/不阻断数，逐条对 §二～§六 报，贴命令原文 + 输出原文。
⛔ 不许 `pip install -e .`；⛔ 不许 `git add -A`。
