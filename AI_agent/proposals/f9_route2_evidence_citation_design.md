# F-9 治本设计稿 · 路线②：模型只指认证据，代码做换算与校验

> # ⛔⛔ 本稿（v1）已被交叉审判 **REWORK** —— **不得据此施工**
>
> **裁决**：[`logs/reviews/verdict/2026-08-09_f9_route2_design_crossreview_sol.md`](../logs/reviews/verdict/2026-08-09_f9_route2_design_crossreview_sol.md)
> （`gpt-5.6-sol` / effort max）= **REWORK**，3 BLOCKER / 5 MAJOR / 1 MINOR。
> **三条 BLOCKER 的承重命题已由 orchestrator 逐条独立核实，全部成立**：
> - **B1** —— 本稿会把一道**现存且有真实夹具证明**的交叉校验（`window_host.py:832`
>   的 `source_geometry_mismatch`，真实事故见 `tests/test_f9_window_host_crash.py:174`）
>   改成**恒真式**：从被引 stroke 派生 span 再与同一 stroke 比较。**§0/§2/§4/§7 据此全部失效。**
> - **B2** —— §2 的派生入口写错：现行强制契约由 `existence.source_ids` 驱动，不是 `along`；
>   且 `CORRECTION_DRAW_DERIVED`（F-16 那套）**做不了外部证据派生**（`span` 需要 manifest／
>   raw reading／方向 binding／ring，schema validator 拿不到）。**§1 末尾「已有现成机制」失效。**
> - **B3** —— ⛔ **§1 的核心论断「缺的只是让确定性结果当权威」是错的**：
>   `_advisory_elevation_world_frame` 的 advisory 标记**有明确、可追溯的原因** ——
>   引入它的提交 `99d9521` 说明逐字写着「**B3 的同义反复风险已避开**：该区间标注为 advisory，
>   **绝不进任何强制路径**」，并当场登记了 `lo==0` 只是假设。实证代价：advisory 给
>   `[11.36,13.76]`，权威 current-ring 给 `[11.24,13.64]` ⇒ **0.12 m**。**提权即引入静默错误。**
>
> **另 4 条 MAJOR 级事实错误**（均已核实）：镜像约定实际**至少 4 份**（漏 `facade.py::_CONVENTION`，
> 且它真接在 `envelope.py:222` 生产路径上，**故 §1「3 份」与 §3 S1 的盘点不完整**）·
> §2 写的模型证据格式 `src:<input_id>:<observation_id>:<sha256>` **模型算不出**
> （其合法输出是 `North_view/S7`，由代码翻译）· **§3 的 S1–S4 不可独立验收**
> （S3 单独落地会产生「错引证据 ⇒ 合法但错误的窗位」的危险中间态）·
> §2 指定复用的 `VaElevationViewBindingV1` **要求各层 footprint 指纹与 extent 完全一致**
> ⇒ **退台当场违反铁律 #6**（§7 的可扩展性声称不成立）。
>
> **sol 给的安全顺序**（v2 起点）：
> `S0（证据身份门 + raw/hydrated/full 三阶段合同）→ S1（gt-free 单一 convention）
> → shadow projector（保留旧 span 对照）→ S4 detector/routing → S3 cutover`。
>
> **⚠️ 返工纪律**：v1 由 orchestrator 亲手出稿并被判 REWORK
> ⇒ **v2 不宜再由 orchestrator 亲手写**（同一个人同一个盲区）。
> **⏸ 用户 2026-08-09 定：本轮只登记，返工单独开一批。**
>
> **⛔ 以下正文保留为 v1 原文（含已被证伪的论断），仅供返工时对照，⛔ 不是可施工规格。**

> **状态**：设计稿 v1（orchestrator 出稿，2026-08-09）· **⛔ REWORK，不得施工**
> **拍板依据**：[decision_log §5.15](../decision_log.md)（用户 2026-08-09 拍板走路线②——**路线选择本身未被推翻**，被推翻的是这份实现设计）
> **前置**：⛔ 本条是 **reading 重启的前置** —— reading 一出真产物，1_correction 被真跑，这条路立刻现形。

---

## 0. 一句话

**把 `Window.span`（沿立面的世界区间）从「模型写」改成「代码从模型指认的那条证据算」**，
模型的输出面只剩「哪张图、哪条笔画」。

---

## 1. 现状（已核实，非推断）

| 事实 | 位置 |
|---|---|
| `Window.span` = **沿立面世界区间**，**模型直接写** | `schema.py:214` |
| 确定性换算**已经存在**，但**只当 advisory** | `window_sources.py:469` `_advisory_elevation_world_frame`，`:490` 逐字写着 "advisory prompt content only (never authoritative)" |
| 确定性帧参数**已经算出来了**（`world_axis`/`sign`/`along_origin`/`frame_transform_sha256`） | `VaElevationViewBindingV1`，`window_sources.py:1193` 一带 |
| 模型指认证据的通道**已经存在** | `provenance.<claim>.source_ids` = `source_locator(input_id, observation_id, output_sha256)` |

**⇒ 路线②需要的零件基本都在，缺的是「让确定性结果当权威」。**
这与 F-16 的修法同形（`floor` 由模型写 → 代码从 `floor_id` 派生），且**已有现成机制**：
`CORRECTION_DRAW_DERIVED` 标记 + 从给模型的 JSON Schema 里机械剥除。

### ⛔ 一个必须一并处理的轴 B 问题

`_BASE_SIGN`（立面朝向的镜像符号）**声明了 3 份**：

```
src/agent/correction/facade_applicability.py:44
src/agent/correction/window_sources.py:42
src/agent/judge/score_inputs.py:35        ← ⛔ judge 侧自带一份
```

翻转公式 `flip = mirrored ^ (local_x_positive == "image_right_to_left")` 亦重复 ≥4 处。

**judge 侧那份最危险**：判卷方与生产方各持一份约定 ⇒ **可以各自漂**，
届时「判卷说错了」与「生产真的错了」无法区分。
⇒ **合成单一来源是本设计的组成部分，不是可选清理。**
（这正是轴 B 第五次现形：F-13 代码vs代码 · F-15② schema vs 门 · F-16 模型输出内部 ·
F-18 同一输出内两份表示 · **本条 = 生产 vs 判卷**。）

---

## 2. 目标形态

```
模型输出（v3 window）：
  provenance.along.source_ids = [ src:<input_id>:<observation_id>:<sha256> ]   ← 只有这个
  ⛔ 不再写 span

代码（确定性，单一实现）：
  1. 按 source_id 取回那条笔画的【局部】坐标（立面 local_x / 平面世界 x,y）
  2. 取该视图的 VaElevationViewBindingV1（world_axis / sign / along_origin）
  3. world = along_origin + sign * local        ← 唯一换算点
  4. 写入 Window.span，打 CORRECTION_DRAW_DERIVED
```

**平面来源的窗**：平面笔画本就是世界坐标，第 2–3 步退化为恒等；**但仍走同一条代码路径**
（⛔ 不许因为「平面不用换算」就另开一条分支 —— 那就是第二处实现）。

---

## 3. 分解（可独立验收的四步）

| 步 | 内容 | 依赖 |
|---|---|---|
| **S1** | **合成 `_BASE_SIGN` 与 flip 公式为单一来源**（含 judge 侧那份），配「两处引用同一常量」的恒等锁 + **断言等于手算值**的正确性锁 | 无 |
| **S2** | 把 `_advisory_elevation_world_frame` 从 advisory 提为**权威换算函数**，返回值进入强制路径；保留其 advisory 用法（提示词）但**同一份实现** | S1 |
| **S3** | `Window.span` 打 `CORRECTION_DRAW_DERIVED` + 从给模型的 schema 机械剥除 + 代码派生填充 | S2 |
| **S4** | 「模型引错证据」的冲突出口：走**结构化拒绝 + 归档重抽**（⛔ 不得升级为不变量硬崩，用户拍板边界） | S3 |

**⛔ S1 必须最先做**：后面三步都要引用那个唯一来源，先做 S1 才不会边改边漂。

---

## 4. ⛔ 已写死的边界（用户拍板，不得漂移）

1. 模型**不得**产出任何世界坐标或换算结果；输出面只有「证据指认」。
2. 换算、镜像符号、区间落位、冲突判定**全在代码**，且**只有一份实现**。
3. **「模型引错证据」是正常业务冲突**，走结构化拒绝 + 归档重抽；⛔ 不得升级为不变量硬崩。
   （与 F-18 那道 `invariant_no_geometry_commit` 的语义要分清：**那道是防篡改，这条是业务错**。）

---

## 5. 锁的形态（写死，防假锁）

- **⭐ 手性锁（最重要）**：北立面（`sign=-1`）的窗，其世界区间必须落在**自己**的平面声明上，
  ⛔ 不许落在镜像搭档上。**用 08-06 实测的那四组真实数字当夹具**
  （`W-F1-N-1` 平面 `[1.24,3.64]` / 立面换算曾错命中 `[11.24,13.64]`）。
  **⛔ 南立面不能当唯一夹具** —— `sign=+1` 时错误策略恰好等价于正确答案，**南立面永远绿**
  （这正是该缺陷藏了很久的原因）。
- **⛔ 对称载荷不算数**：夹具必须**手性不对称**，否则镜不镜像逐字节相同、零分辨力
  （08-05 已坐实）。
- **判无害必须逐属性**：两窗互换房间时集合相同、`host_zone_id` 不同 ⇒
  ⛔ 不许用「集合相同」判等价。
- **S1 的锁必须两把**：恒等锁（两处引用同一常量）**+** 正确性锁（断言等于手算值）——
  **恒等锁不证明这套规范是对的**（F-13 教训：两边用同一函数一起挑错角时照样绿）。

---

## 6. ⚠️ 已知风险与未决

1. **`source_ids` 的粒度够不够**：现在是 per-claim（`along` / `width` / `sill` …）。
   若某扇窗的 `along` 证据缺失（模型没指认），代码无从派生 ⇒ 需定义**降级策略**
   （拒绝？还是回落平面？）。**未决，需在 S3 前定。**
2. **legacy（v1/v2）产物**：`span` 仍由模型写。**方案 = 按 schema 版本分支，v3 派生、v1/v2 原样**
   —— 与 F-16 同样的兼容处理。
3. **0.12 m 尺寸基准残差**（07-08 登记的既有债）：立面外皮 vs 世界内皮。
   本设计**不解决它**，但换算变确定性之后，该残差会从「藏在 LLM 心算里」变成
   **一个可测的系统性偏移** ⇒ 反而更容易收口。**登记，不并入本批。**
4. **判卷侧改动的权属**：`judge/score_inputs.py` 属 gate② judge harness。
   S1 要动它 —— **需确认这不触发「判卷方不得被生产方影响」的隔离原则**。
   orchestrator 判断：合成常量**不改变判卷逻辑**、只消除漂移，应属合法；**但请用户确认**。

---

## 7. 这条设计如何满足铁律 #1

> 「LLM 只做 感知 + 校正判断 + 物理语义；代码做所有几何。」

- 模型「指认哪条笔画」= **感知**（它看图，它知道哪条线是这扇窗）✅
- 「局部坐标 → 世界坐标」= **几何换算** ⇒ 归代码 ✅
- 「引的证据对不对」= 代码可校验的业务冲突 ✅

**⇒ 路线②不是路线①的妥协版，它在分工上更准**：
路线①把「哪条笔画是这扇窗」也收归代码，而那恰恰是**感知**、是 LLM 该做的部分。
