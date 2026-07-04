# 判卷 + 画法 统一模型（定稿规格）

> 状态：**用户逐轮共定、2026-07-04 收敛完成**，作为 Codex 重构 scorer+renderer 的权威 build spec。
> 取代 `2026-07-03_elevation_grade_proposal.md` 的 §3–§9 画法细节（该文动机/红线/协作仍有效）。
> 覆盖 reading grade + correction grade，平面 + 立面。

---

## 0. 底层原则（红线，最重要）

**判卷图 = ① 先用 gt 画一层灰色真值底 → ② 把 reading/correction 按它们自己的坐标如实叠上去 → ③ 按重合关系给产品上色。**

- **红线精确表述（审 #2 采纳）**：① **产品几何绝不从 gt 合成或搬移**；② gt 只可用于**灰真值底** + **显式 miss 注记**；③ **miss 注记不是产品几何**，必须画成**虚线**、不得被误认成产品。
  - 即：**extra = 产品元素**（画在产品坐标、红实线）；**miss = gt 派生的判卷注记**（画在 gt 坐标、红虚线，是上面②的显式例外，不算"拿 gt 画产品"）。
- 推论：**scorer 必须把产品的真实几何全带出来**（墙的坐标 + 两端、窗的 span、立面窗的盒、产品横线），renderer 只从 sidecar（=产品）画产品、从 gt 画灰底 + miss 注记。
- 这条同时从根上修掉现 bug：`render_grade` 画平面墙长度借 gt zone → 墙画短看不见。改成产品自画，短墙就画短。
- **立面翻转是唯一允许的坐标归一（审 #6 采纳）**：立面 reading 是 image-local，scorer 会在 aligned / 关于面中心反射(flipped) 两个朝向里择优，`product_box` = **产品几何归一到"判卷 facade 坐标系"后的盒**（**保留 `source_span`/原始几何供审计**）。这是**单次、全局、声明式**的朝向归一（z 从不翻），**报告 orientation=aligned/flipped/ambiguous**，与"移动几何伪造命中"是两回事；correction 已是世界系、**从不翻转**。renderer 画归一后的 `product_box` 并**在选了 flip 时给可见提示**。

**两条贯穿性澄清（用户 2026-07-04）：**
- **灰真值是永远的底、永不上色、不用单独"补"。** gt 全画灰、始终在最底层；产品没完全盖住时灰**自然漏出来**，漏出的灰就是"缺/没对齐"的指示。不为任何档特意补灰。
- **产品永远按真实坐标如实画；阈值只决定颜色、不改位置。** 差一丁点也如实叠（旁边漏一丝灰）；`complete_eps` / `overlap_complete` 等**只判这块产品上什么颜色**（够近仍标绿），**绝不移动产品的画的位置**。几何永远诚实，阈值只管上色。

---

## 1. 统一三档颜色（所有元素通用）

**颜色只上在产品身上**（gt 永远灰底）。语义按**每段**（平面线性 §2）或**每盒**（立面窗 §3）套用：

| 档 | 产品颜色 / 线型 |
|---|---|
| **完全命中** | **绿色实线**（边界元素加粗） |
| **容差内命中** | **橙色**（产品/差异段 + **橙色容差带**） |
| **未命中（容差外 / 没配上）** | **红色**：**miss=虚线，extra=实线** |

- 语义定死：**绿=完全对，橙=在容差内（可接受但不精确），红=没对上**。**灰=gt 真值**（永远的底，漏出即差异，不算一档颜色）。
- **缺（missing）永远虚线**（容差内=橙虚、容差外=红虚）；**多（extra）永远实线**（容差内=橙实、容差外=红实）。**全元素通用、不因橙红而变线型**。
- 容差带=橙色（形状见 §2b）。

---

## 2. 平面线性元素（墙 / 窗）—— 分段（piece-level）+ 灰真值打底

**为什么分段而不整条一色**：画对的元素 = 一整条干净绿（不碎）；**只有真有错才"碎"，那时碎正是诊断**（错在哪截、缺还是多）。灰真值底给完整轮廓，颜色给 diff → 读起来像 diff，不是散。

**两阶段判定：先位置关联，再 interval-set 比长度（审 #4/#8 采纳）**

1. **位置关联（横向）**：
   - **墙**：按 `(朝向, 横向坐标簇)` 分组——同朝向、横向坐标在 `position_tol` 内的 read/gt 墙归入同一坐标簇。
   - **平面窗**：先归到某 facade 车道（沿边界就近提取），再在该车道上按沿面 1D 比。（平面窗**不吃** `position_tol` 的横向门，避免与墙口径混。）
   - 一个坐标簇/车道里若 read 无、gt 有 → 整条 **miss(gt 红虚注记)**；gt 无、read 有 → 整条 **extra(red 红实产品)**。
2. **长度（纵向）= interval-set 比，不做逐记录一一配**（审 #4：避免"一条产品墙跨过 gt 缝 → 既算 extra 又把下一段算 miss"的双计）：
   - 同一坐标簇内，把**产品区间的并集** vs **gt 区间的并集**做集合差：
     - 交集（都在）→ **命中段·绿**；
     - gt 并集 − 产品并集（gt 有产品没够到）→ **缺·虚线**（偏 ≤ `extent_tol` = 橙虚、> = 红虚）；
     - 产品并集 − gt 并集（产品多出）→ **多·实线**（≤ `extent_tol` = 橙实、> = 红实）。
   - 画短 / 画长 / 长度对但整体偏 —— 同一套集合差。
3. **颜色分档必须同时看两根轴（修 B，2026-07-04 用户定）**：横向位置偏移**也要进** complete/within_tol，不能只看长度：
   - **complete**：横向 |delta| ≤ `complete_eps` **且** 两端都在 `complete_eps` 内 → 整条绿实线，**抑制 sub-`complete_eps` 碎段**（审 #5）。
   - **within_tol**：横向 |delta| ≤ `position_tol` **且** 端点偏 ≤ `extent_tol`，但未达 complete → 橙（碎段按缺/多出）。
   - 否则超容差 → 红。
   - （旧 bug：长度完全对但整条横移 0.2m 被判 complete 绿；修后 = 橙。杜绝"墙整体歪一点看不出"的各向异性。）

**渲染**：灰 gt 线打底（完整轮廓）→ 叠产品分段（绿/橙虚·橙实/红虚·红实）+ within_tol 时橙容差带（§2b）。**miss/缺段=gt 派生注记(永远虚线)、extra/多段=产品(永远实线)**（§0/§1）。

### 2b. 容差带形状（用户 2026-07-04 定）—— 橙带 = 该元素的"验收区域"

橙色容差带画成 gt 元素周围的**验收区域**（产品落进去就算 within_tol），形状**随哪根轴出偏自适应**：
- **只横向偏**（位置问题）→ 带 = **横移范围**：沿 gt 墙线的垂直方向 ±`position_tol` 的条带（宽 2·position_tol，长 = gt 墙长）。
- **只长度偏**（顺墙两端点没对齐）→ 带 = **端点长度范围**：在偏了的端点处沿墙方向 ±`extent_tol`（把带在该端延长 extent_tol）。
- **两者都偏**（但都在容差内）→ 带 = **横移 + 长度容差的并集**（gt 墙横向撑 ±position_tol、纵向两端各延 ±extent_tol 的矩形区域），**落进去就算**。
- 立面窗类比：within_tol 的橙容差带 = 满足两侧覆盖率 ≥ `overlap_accept` 的验收带（沿两轴的容差区域）。

---

## 3. 立面窗（2D 盒）—— 重合面积比整盒判（不分段）

2D 盒去拆成 L 形反而丑，故立面窗**整盒按重合面积分档**。**用两侧覆盖率、不用"交集/较小面积"（审 #1 采纳）**——后者会让"小窗套在大 gt 里"或"大窗盖住小 gt"都判成 1.0 完全命中（尺寸全错却绿）。改为**两侧都要够**：

```
gt_cov      = 交集面积 / gt 盒面积
product_cov = 交集面积 / 产品盒面积
```

| 条件 | 档 | 产品盒画法 |
|---|---|---|
| min(gt_cov, product_cov) ≥ `overlap_complete`(0.95) | 完全命中 | 绿实描边盒 |
| min(gt_cov, product_cov) ≥ `overlap_accept`(0.75) | 容差内 | 橙盒（+ 橙容差带） |
| 否则 | 未命中 | **read 盒红实(extra) + gt 处红虚(miss)** |

（"两侧都要 ≥ 阈"同时堵死 tiny-inside 与 huge-cover；along/sill/head/宽 delta 仍作证据、不再当判据。灰 gt 盒永远在底、按 §0 自动漏出。）

---

## 4. 边界 / 楼层横线

- **立面竖边界（左右=该面两端）**：命中绿加粗 / miss 红虚。**修映射并显式序列化进 sidecar（审 #7）**：N/S 面 L=W 边、R=E 边；E/W 面 L=S 边、R=N 边；产品坐标=该 boundary 的 read 坐标；**无 boundary 数据→灰参考、非绿非红**（renderer 不再从 plan 记录 + 规则里现推）。
- **立面横线（地面 z=0 / 楼板线 z=z_floor / 屋顶 z=top）—— 完整 diff 模型（审 #3 采纳）**：把 backlog 的屋顶/地面判定一起做。sidecar 每面带 `product_floor_lines`（reading 从 wall_fill 的 z 边界、correction 从 floor z_floor + 顶）+ `gt_floor_lines` + 匹配记录 + **未匹配的产品 extra 线**：
  - gt 线有匹配产品线（≤ `floor_line_tol`）→ 命中绿加粗（偏一点=橙）；gt 线无产品匹配 → **miss 红虚**；产品线无 gt 匹配 → **extra 红实**。
  - **no-data 与 miss 分开**：缺立面视图 = no-data；有视图但**无 wall_fill 等产品横线源** = **显式 no-data**（不是 miss，不能没源就判漏）。
- **平面 footprint 四边**：命中绿加粗 / miss 红虚（现役 `_draw_plan_boundary` 已在，保持）。

---

## 5. 容差参数（全进逐 run `grade:` 配置，reading/correction 两把独立尺）

| 参数 | 默认 | 用途 |
|---|---|---|
| `position_tol_m` | 0.30 | 平面线元素横向关联（沿用 wall_tol） |
| `extent_tol_m` | 0.30 | 平面线元素纵向长度（从 gt 两端） |
| `complete_eps_m` | 0.05 | "完全命中 vs 容差内"的 ≈0 判定 |
| `overlap_accept` | 0.75 | 立面窗可接受重合率 |
| `overlap_complete` | 0.95 | 立面窗完全命中重合率 |
| `floor_line_tol_m` | 0.30 | 立面横线 z 容差 |

- 独立于 `correction.yaml`（那是确定性核坍缩生产尺）。进 `score_vs_gt.json` sidecar `tolerances`，`SCORER_SCHEMA` 递增，改容差不复用旧分。
- reading 尺是准确度真闸门，别比 correction 松。
- **`GradeConfig` 校验序（审 #5）**：`0 ≤ complete_eps_m ≤ extent_tol_m`、`0 ≤ overlap_accept ≤ overlap_complete ≤ 1`、其余非负，非法即报错。

---

## 6. scorer 改动（为 §0 + §2 长度轴）

- **平面墙**：保留两端坐标（现在被压成一个坐标、丢了），输出 read/gt 墙的 [坐标, 起, 止] + 分段测量（命中/缺/多 长度）。
- **平面窗**：输出 read/gt 完整 span + 沿面分段测量。
- **立面窗**：输出 read/gt 完整盒 + **重合率**（替代四轴 delta 判 placed）。
- **立面横线**：产品 band 边 z vs gt 楼层 z。
- 新档：每元素 status 由分段/重合率派生（complete / within_tol / miss+extra），带足够几何供 renderer 纯产品作画。
- 全 judge-side，`test_gt_discipline` 覆盖新件、须绿。

---

## 7. renderer 改动

- **产品一律从 sidecar（产品几何）画**，gt 只画灰底 + 参考线（floor lines 灰）。删掉所有"产品借 gt 几何"路径（`_interior_coords` 借 gt 墙长、窗借 gt 高等）。
- 平面：灰 gt 底 + 产品分段（§2）。立面窗：灰 gt 盒底 + 产品盒按重合率档（§3）。边界/横线：§4。
- 图例更新：绿=完全命中 / 橙=容差内(含橙容差带) / 红虚=miss / 红实=extra / 灰=gt 真值。

---

## 8. 非目标 / 保持 / v1 范围

- 不世界解算、不碰 `derive_facade_frame`、不改 reading/correction schema 契约、不进 StageVerdict、不碰 gate①。
- 关联=纯几何（画错的窗照着谁画没意义、不纳入）。
- 平面窗**不引入立面那种重合率**——平面用分段（线性）；立面用重合率（面）。两者各自最自然。
- **v1 范围显式声明（审 #9）**：平面墙 = 从矩形 gt zone 取的**轴对齐极大区间**；立面 = **cardinal 正交立面矩形**（N/S 用 footprint 宽、E/W 用深）。**斜/曲/非正交立面、非矩形分区**需未来 segment/polyline 模型，本版不支持——守不变量 #6 是"留接缝、不烤死"，非"已支持"。

---

## 9. 审阅采纳记录（Codex 方案审 2026-07-04，APPROVE-WITH-CHANGES，10 findings 全采纳）

`logs/review/review/2026-07-04_grade_visual_model_spec_review.md`。已折进上文：#1 两侧覆盖率(§3)·#2 miss 注记例外(§0/§1)·#3 横线 extra/no-data/序列化(§4)·#4 interval-set 拓扑(§2)·#5 容差序 + complete 抑制(§2/§5)·#6 翻转归一(§0)·#7 竖边界序列化(§4)·#8 平面窗车道口径(§2)·#9 v1 范围(§8)·#10 renderer 红线测试(Batch 2)。Batch 1 需按 #1/#3/#4/#5/#6/#7 返工。
