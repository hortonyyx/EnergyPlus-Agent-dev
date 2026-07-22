> ⚠️ **本文件 = 双独立出案之一（opus 稿），不是施工基线。**
> 施工基线 = [tarch_to_gtv3_converter_plan.md](tarch_to_gtv3_converter_plan.md)（主控综合裁决稿）。
> 本稿的算法主干**已被裁定为基线正文**，但基线 §2 有 7 条来自 sol 稿的具约束力增补/修订
> （厚度证据六来源取代墙厚区间兜底 / 面积阈值纪律 / outer skin 改无界 flood-fill / 自由端证明式处理 / source_map 等），
> **冲突处以基线为准**。

# 方案：天正真实建筑图 DXF → GT v3 可消费几何 的转换器

> **状态** 设计出稿（2026-07-21，Opus 规划子代理，双独立出案之一，未参考另一方稿件）
> **派单** [`logs/reviews/request/2026-07-21_tarch_to_gtv3_converter_planning_brief.md`](../logs/reviews/request/2026-07-21_tarch_to_gtv3_converter_planning_brief.md)
> **事实底座** [`logs/experiments/2026-07-21_sm24_gt_extraction/SURVEY.md`](../logs/experiments/2026-07-21_sm24_gt_extraction/SURVEY.md)（本稿 §2 对其中三处做了实测修订）
> **本稿不含生产代码。** 稿中所有"实测"数字均由本轮只读探针在 `work/sm24_source.dxf` 上跑出，探针留在
> 会话 scratchpad、**不进仓库**（按派单 §1），其算法已在 §4 完整规格化，执行者据 §4 重写即可。

---

## 0. 结论先行

**核心架构一句话**：不改 v3 提取器本体、不做双线成对匹配，转换器走
**「墙面域重建 → 洞口补齐 → 腔体拓扑 → 逐边外扩到混合基准框」**，
把天正双线墙折成 v3 要的单线区划边界，以**追加图层**（而非重写 DXF）的方式落盘，
全程由九道 fail-closed 自校验闸门守，其中 **G8 反演重建门**（由输出反算墙体域并与实测墙体域对账）
是"绝不静默出错答案"的主保险。

**可行性已实测坐实**（本轮探针，非推断）：

| 环节 | 实测结果 |
|---|---|
| 洞口解析（块 bbox × 墙垛端头双证） | **21/21 全解析**，零未决、零歧义 |
| 补洞后墙线拓扑 | faces=51，**dangles=0 / cuts=0 / invalid=0** |
| 面域守恒 | 全部面面积和 = **200.00 m²** = 外皮外包 10×20，**零残差** |
| 腔体（净房间）识别 | **8 个** > 2 m²，与用户拍板的 sm24=8 区一致 |
| **L 走廊** | **天然单一面**（净腔 30.82 m²），转换器未在拐角引入任何切分线 |
| 腔体→区（逐边外扩） | 8 区，∑面积 = 200.000 m²，与外包**对称差 0.000000 m²**，两两重叠 **0.0 m²** |
| 墙体材料域 | 20.84 m²（= 200.00 − 179.16 净腔） |

**我认为最脆的一环**：不是几何算法，是 **§4 S6 的"区划意图从哪来"** ——
种子点若由转换器自己的面导出，"每面恰含一个种子"这条 v3 校验就退化成**自证同义反复**（tautology），
一个被错误切开的走廊会带着两个自产种子一路绿灯到底。本稿用
**人写的房间数/房名（非坐标）+ 机器产的坐标** 拆开这个环（§5.5、§7 G6），
但这条防线的强度**取决于人是否认真填那一行数字**，是全链唯一非机械的一步。

---

## 1. 问题陈述

### 1.1 两种"图"的定义冲突

| | v3 提取器要什么 | 天正图形导出给什么 |
|---|---|---|
| 墙 | **单线**区划边界，相邻房间共享一条线 | **双线**（外墙 240 / 内墙 120，见 §2.1） |
| 洞口 | 边界连续不断开 | 门窗洞处墙线**断开**，洞里放门窗块 |
| 拓扑 | polygonize 后每面正好一个房间，dangles=cuts=invalid=0 | 双线夹层自成细长面；外轮廓因洞口不闭合 |

直喂的实测后果（SURVEY §3，本轮复现）：全墙线 polygonize → 23 个面全是双线夹层（0.5–1.5 m²），
房间面根本没围出来；仅外皮线 polygonize → **0 面**。

### 1.2 为什么不能绕开

- **不能让人手画区划线**：用户 2026-07-21 已否决。复杂建筑手画不可行且**容易画错**，
  画错的是**答案**——错答案会把对的产物判成错且无人发现。只对简单建筑成立 ⇒ 违反不变量 #6。
- **不能退回老提取器 v2**：v2 是"坐标聚类 + 横墙分带 + 带内竖墙切格"的**矩形网格法**，
  硬假设房子是矩形网格。sm24 的 L 形走廊会被分带切格切成两块矩形，
  而**这正是本 case 要考的缺陷本身** —— 等于把缺陷写进标准答案，判出来永远满分。

### 1.3 本转换器的定位

它是 **judge 侧的答案生成器**。这决定了两条压倒性的设计取向：

1. **错答案 ≫ 崩溃**。一次崩溃是一条诊断；一次静默错答案会污染此后所有基于该 gt 的判卷结论，
   且会以"产物错了"的面目出现，几乎不可能被下游发现。⇒ 所有可疑点一律 fail-closed。
2. **答案必须可被人核**。人核不了的答案不算答案 ⇒ 每次转换必出 overlay 渲染件（§8.4）。

---

## 2. 实测底座：与 SURVEY / 派单假设的出入（**必读**）

派单 §2 说"已实测，勿重复勘查"，但同时鼓励亲跑复核。我复核了，**发现四处需要修订**。
这几处都不是小数点问题——**每一条若照原假设施工都会造出错答案**。

### D1（重）SURVEY §5 线索 3「本图墙厚统一 240」——**不成立**

实测竖墙 x 聚类（mm）：

```
23057.6 23297.6 | 23597.6 25097.6 25197.6 | 27177.6 27297.6 | 27457.6 27597.6 27717.6
28497.6 28657.6 | 28817.6 28937.6 | 31017.6 31617.6 32517.6 | 32817.6 33057.6
相邻差： 240 …… 120 …… 120 …… 240
```

- 外墙 = **240**（23057.6→23297.6；32817.6→33057.6）
- 内墙 = **120**（27177.6→27297.6；28817.6→28937.6；横向同样存在多处 120 带）

⇒ **sm24 本身就是墙厚不统一的图**。任何"恒定偏移配对双线"的做法当场失效。
这反而是好消息：不变量 #6 要求的"不许烤死统一墙厚"，在 sm24 上就有真实反例可回归。
SURVEY §2.4 说的"墙厚 240"仅对**外墙**成立，§5 线索 3 把它推广到全图是错的。

### D2（重）派单 §5 Q2「门窗块 bbox 精确等于洞口」——**对窗成立，对门不成立**

实测（`bbox.extents` 展开虚拟实体）：

| 块 | 句柄 | bbox 宽×高 (mm) | 是否等于洞口 |
|---|---|---|---|
| `$TCHSYS$WIN2D`（窗）×11 | AE1…AFF | 如 4800×240 / 240×1500 | ✅ **精确等于洞口**（洞宽 × 墙厚） |
| `$DorLib2D$00000002`（外门） | AC3 | 1600×**780** | ❌ 含开启扇，法向越出墙体 |
| `$DorLib2D$00000002`（外门） | AC9 | **780**×1600 | ❌ 同上 |
| `$DorLib2D$00000001`（内门）×5+ | ACC… | 877.5×900 | ❌ bbox 从**墙轴线**起算 + 开启扇 877.5 |

例：AC3 bbox = x[23597.6, 25197.6] y[46445.2, **47225.2**]，而北外墙外皮 y=46565.2
—— bbox 向建筑**外部**越出 660 mm。若照"块 bbox = 洞口"直接补洞，会在北墙外糊一块 1600×780 的假墙。

SURVEY §5 线索 1 原文只说"**窗**块 bbox 精确等于洞口"，是对的；派单把它概括成"门窗块"时失真。
⇒ **门的洞口必须只取沿墙方向的跨度，法向范围另由墙体自身给定**（§4 S3）。

### D3 SURVEY §3.1 报的 `dangles=1` 是**零长度线**，不是真悬空

实测该 dangle 的两端点相同：`(28817.6, 42565.2) → (28817.6, 42565.2)`。
这是一根退化 LINE（图纸噪声），坐标量化后自然消失。⇒ 不必为"1 个悬空线头"设计任何补救逻辑，
但**必须显式登记并计数**（诊断码 `tarch_wall_degenerate_line`，INFO 级），不能默默吞掉。

### D4 v3 拒 INSERT 只针对**边界选择器**，开口路径**明确支持 INSERT**

SURVEY §3.3 说"`_entity_points` 只吃 LINE/LWPOLYLINE/POLYLINE，INSERT 直接 fail ⇒ 门窗块不能直接进边界选择器"
—— 前半句对，后半句的推论范围要收窄。读码确认：

- `_entity_points`（边界选择器路径）确实拒 INSERT → `dxf_entity_type_unsupported`；
- 但开口路径 `_bbox_for_locators` 有独立分支 `geometry_mode="virtual_entity_bbox"`，
  **要求实体必须是 INSERT**，走 `ezdxf.bbox.extents` 展开虚拟实体取 bbox。

⇒ 派单 Q2 的问法（"块被炸成线的图怎么办 / 补齐策略"）需要重新分解：
**洞口本身不需要把块转成线**，v3 已能直接吃块；需要转换的是**墙线在洞口处的连续性**。
这两件事被派单合并成一件了。本稿据此分开处理（§5.2）。

### D5 内部洞口在 v3 中**不可表达**

v3 的 `boundary_segments` 只由 `vg_for_direction(footprint 外环)` 导出 = **只有外围段**。
任何绑到内墙的开口都会在 `opening_segment_assignment_no_candidate` 处崩。
实测 sm24 的 21 个洞口中：**外围 14 个**（11 窗 + 3 外门 AC3/AC9/ADE），内部 7 个（内门）。
⇒ 转换器必须把洞口分成外围/内部两类，只把外围类写进 manifest，
内部类记进转换报告的排除表（带原因），**分类不出来的一律 fail**。

**副产的免费不变量**：实测外皮四条线的缺口数 = 西 5 + 东 4 + 南 3 + 北 2 = **14**，
与外围洞口数 **14 精确相等** ⇒ 这是一条零成本、强独立的守恒检查（§7 G4）。

### D6 `gt_from_dxf.py` 的保护路径与 bundle 约定**互相打架**

`scripts/tool_scripts/gt_from_dxf.py::_protected_dxf_source` 会对位于
`case_tests/test_baseline/gt/`、`gt_sources/`、任一 case 的 `case_data/` 之下的 DXF
抛 `gt_dxf_source_protected_path`；而 `cad_to_gt_extraction_plan.md` §3 的逐 case bundle 约定是
`source.dxf` 放 `gt/<case>/`。⇒ **gt bundle 内的 source.dxf 无法被直接重建**。
这不是本轮要修的 bug，但施工 SOP 必须写死：**转换与构建一律在 staging 工作目录跑，
人核通过后再晋升产物进 bundle**（§8.5）。若不写死，执行者第一次跑就会撞墙并可能"顺手放宽"保护。

### D7 派生实体导致 gt 内的溯源指针**指向派生件而非原始墙线**

`GtEntityRefV3.entity_handle` 记的是被选中的边界实体句柄。转换器产出的是**新实体**，
所以 gt.json 里 zone/footprint 的 `source_refs` 会指向 `GTV3_*` 图层的派生线，
**原始天正墙线句柄不进 gt.json**。这是"不改 v3 本体"这个接缝的固有代价，必须明示：
留痕靠**转换报告**（派生句柄 → 贡献的原始句柄 + 规则 ID），且报告 sha256 必须进 provenance（§8.2）。

### D8（次要）v3 的 `boundary_reference` / `default_wall_thickness_m` 是**声明字段，不参与计算**

读码确认：`boundary_reference` 只在 `_check_input` 里被断言 `== "outer_skin"`（否则
`dxf_centerline_unsupported_in_phase_b`），几何计算完全不读它；
`default_wall_thickness_m` 在**整个生产代码里从未被读取**（全仓 grep 仅见于 manifest 定义与测试夹具）。
⇒ 派单 Q1 问的"与 `boundary_reference: outer_skin` 如何自洽"，答案在**声明层**而非计算层（§5.1）。

### 复核确认无误的部分

SURVEY 的其余实测我均复核通过：`proxy_entity_count=0`、`$INSUNITS=0`(unitless, mm)、
图层分布（WALL 132 LINE / WINDOW 21 INSERT / edge 5 LWPOLYLINE 视图框）、
平面外包 10000×20000 外皮、132 墙线 67 竖 65 横零斜线、
窗 11 / 门 10、视图框方案有效（"点在框内"确定判定）。**视图框约定建议保留**，它是本转换器的前置便利。

---

## 3. 架构与接缝选择

### 3.1 采用的接缝

```
天正图形导出 DXF (源)
   │
   ├─(只读)──────────────────────────────────────────────┐
   ▼                                                      │
[转换器 tarch→gtv3]                                        │ 原实体全部原样保留
   │  S0 体检 → S1 量化 → S2 墙线归集 → S3 洞口解析补齐      │ （句柄不变）
   │  S4 拓扑闭合 → S5 腔体 → S6 意图绑定 → S7 逐边外扩      │
   │  S8 九门自校验 → S9 落盘                              │
   ▼                                                      ▼
规范化 DXF = 源文档 + 追加图层 GTV3_FOOTPRINT / GTV3_ZONE / GTV3_OPENING
   +  转换报告 conversion_report.json（留痕/诊断/闸门结果）
   +  manifest 草稿 manifest_draft.json
   +  overlay 渲染件（人核）
   │
   ▼
[现有 v3 提取器 gt_from_dxf.py，本轮零改动]  →  gt.json (candidate)
   │
   ▼
[人核 overlay + render_gt] → verified
```

**三个关键选择**：

**(A) 不改 v3 提取器本体。**
v3 是判卷信任根，B4a/B4b/B5 已在其上压了 1456 绿的回归面与六件套冻结契约。
把"天正方言"耦合进信任根 = 让最不该动的东西承担最脏的启发式。
转换器失败只会少一份 gt；v3 被改错会让**所有** gt 悄悄偏移。
**唯一例外见 §11-U1（回字形 profile 扩展），那是 v3 侧的独立工作项，不由本转换器夹带。**

**(B) 追加图层，不重写 DXF。**
转换产物 = 源文档 + 新图层。收益是**全部原始句柄保持有效**：
洞口块（`virtual_entity_bbox`）、立面 E_WINDOW 线组（`grouped_line_bbox`）、
`edge` 视图框、图名文字 —— manifest 里这些绑定**一个字都不用改**，
转换器只需负责 `footprint_boundary` / `zone_boundaries` 两个选择器指向的新图层。
代价见 D7（溯源指针指向派生件），由转换报告补偿。

**(C) 转换器同时产出 manifest 草稿。**
v3 的 manifest 要 8 个 zone_seeds、14 个开口绑定、仿射变换、视图 clip box……
纯手写不现实且极易写错（写错的还是答案）。转换器把**一切机械可导出的**都填好，
只把**意图性字段**（房间名/用途/房间数）留给人（§5.5）。

### 3.2 被否决的方案及理由

| # | 方案 | 否决理由 |
|---|---|---|
| 1 | 让用户手画一层区划线 | 用户 2026-07-21 已否。复杂建筑手画不可行且易画错；错的是答案；只对简单建筑成立 ⇒ 违反不变量 #6 |
| 2 | 退回老提取器 v2（矩形网格法） | 烤死"房子是矩形网格"，L 走廊被分带切格切成两块——**正是本 case 要判的缺陷**，等于把缺陷写进答案 |
| 3 | 改 v3 提取器让它直接吃双线 | 见 (A)。信任根不承担方言启发式；且 v3 的 strict/fail-closed 风格与"猜墙"根本冲突 |
| 4 | **双线成对匹配**（找相距 t 的平行线配对成墙） | 实测 sm24 就是 240/120 混用（D1），"恒定偏移"当场失效；且丁字/十字接头处一条线同时参与多道墙，配对本身歧义。**这是最诱人也最危险的方案** |
| 5 | 形态学闭合（buffer + / buffer −） | 引入非正交坐标与浮点污染，直接撞 v3 的 `dxf_nonorthogonal_edge`（1 mm 正交容差）；且会抹掉 120 内墙这种细部 |
| 6 | 只用块 bbox 补洞、不做几何交叉验证 | 门块 bbox 含开启扇（D2），直接用必造假墙。**必须双证** |
| 7 | 用 LLM/VLM 识别墙与房间 | 答案生成必须确定性。gt 铁律 + "judge 以 gt 为权威"；把不确定性引入答案端等于自毁标尺 |
| 8 | 最近腔体划分墙体域（Voronoi 式） | 想法优雅（内墙自动得轴线、外墙自动得外皮），但**接头方块处会切出 45° 对角线** ⇒ 撞 `dxf_nonorthogonal_edge`。改用逐边支撑线外扩 + 相邻支撑线求交（§4 S7） |

---

## 4. 算法分步规格

> 记号：源单位 mm；`τ_node` = `dxf_node_join_tolerance_m`(1e-3 m = 1 mm)，
> `τ_axis` = `dxf_axis_alignment_tolerance_m`(1 mm)，`τ_area` = `dxf_topology_area_tolerance_m2`(1e-6 m²)。
> **不新造任何容差**（派单 §5 Q3 硬要求），全部取自 `src/configs/judge_gt.yaml`，
> 由 `load_gt_tooling_config` 解析并把 `judge_config_sha256` 记进转换报告。

### S0 输入体检（gate 前置）

1. `ezdxf.readfile`；断言 `proxy_entity_count == 0`（否则 `tarch_source_proxy_present`：用户没走"图形导出"）。
2. 读 `$INSUNITS`；unitless 按 `metres_per_unit` 由 case intent 显式给定（sm24 = 0.001），**不猜**。
3. 视图框：`edge` 层闭合 LWPOLYLINE + 框内唯一图名 TEXT → 平面视图 clip box。
   框内文字数 ≠ 1 → `tarch_view_frame_ambiguous`。（此约定 SURVEY §2.3 已验证，保留）
4. 取平面框内、`WALL` 层的 LINE 全集。任一线段非轴平行（|dx|>τ_axis 且 |dy|>τ_axis）
   → `tarch_wall_nonorthogonal`（本轮范围外，明确拒收而非近似）。

### S1 坐标量化（**没有这一步后面全崩，实测教训**）

原始坐标带亚微米噪声（如 y=46565.23354697024）。本轮探针在**未量化**时，
即使补齐全部 14 个外皮缺口，`polygonize` 仍给出 **0 个内部面**（角点差 1e-11 就不成环）；
量化后立刻闭合。v3 内部有 `_snap_segments` 做同样的事，但转换器在 polygonize **之前**就需要闭合拓扑，
不能依赖下游。

- 量化步长 `q = τ_node / 10`（= 0.1 mm）。**派生量，不是新配置项。**
- 每个坐标 `v → round(v/q)*q`。
- **G2 守恒检查**：若两个原本相距 > `τ_node` 的坐标落到同一格点 → `tarch_quantization_conflict`（fail）。
  即量化只许消噪，不许合并真实差异。
- 量化后首尾相同的线段 → 计入 `tarch_wall_degenerate_line`(INFO) 并丢弃（实测 sm24 有 1 根，即 D3）。

### S2 墙线归集与墙垛端头识别

- 按方向分桶：竖线 `(x, y0, y1)`、横线 `(y, x0, x1)`。
- **墙垛端头（jamb cap）** = 长度在 `[t_min, t_max]` 的短线，作为"墙带横截面"的证据。
  `t_min/t_max` **不是容差、是建筑域的合法墙厚区间**，写进 case intent（默认 `[0.06, 0.50]` m），
  超出区间的墙厚必须由人显式声明 ⇒ 不烤死墙厚，也不放任乱猜。
  实测 sm24：竖向端头 34 根 / 横向端头 39 根，覆盖 240 与 120 两种厚度。

### S3 洞口解析与补齐（双证据，缺一不填）

对每个 `WINDOW` 层 INSERT（平面门窗；块名判别：`$TCHSYS$WIN2D`=窗，`$DorLib2D$*`=门）：

1. 取 `bbox.extents([insert])` → 量化 bbox `(x0,y0,x1,y1)`。
2. 对 `axis ∈ {x, y}` 试解：令 `(lo,hi)` = bbox 在该轴的范围；
   在**垂直于该轴**的端头集合中找位于 `lo` 与 `hi` 的两根端头，且两根的横截区间 `[c1,c2]` **完全相同**；
   再要求块 bbox 在法向的区间与 `[c1,c2]` **有正重叠**（这一条把门的开启扇排除在判定之外，
   同时把东/西墙同 y 位置的镜像窗区分开——实测这两个坑都真实存在）。
3. **恰好一个解** → 洞口矩形 = `[lo,hi] × [c1,c2]`（沿墙跨度取自块，法向取自墙体本身，D2 的修正）。
   零解 → `tarch_opening_block_unresolved`；多解 → `tarch_opening_block_ambiguous`。**都 fail，不猜。**
4. 把该矩形的四条边加入线集（补齐墙线在洞口处的断开）。

**实测：sm24 21/21 全解析，零未决零歧义**，且解出的矩形与墙带精确贴合
（例：AC3 → `[23597.6,46325.2]–[25197.6,46565.2]`，正是 240 厚北墙上的 1600 洞，
而**不是**块 bbox 的 1600×780）。

**"块被炸成线"的图怎么办**（派单 Q2 后半问）：
退到**纯几何续接规则** —— 墙带两侧支撑线在缺口两端**各自续接**（缺口前后同一条 x/y 上都还有墙线），
且缺口两端各有端头。我实测了这条规则：在 sm24 上给出 **12 个候选、零假阳性**，
但**只覆盖 21 个洞口中的 12 个**（漏掉的是被丁字接头打断了侧线连续性的那些）。

⇒ 定性结论：**纯几何续接规则是高精度、低召回的证人，不能当主证据**。因此：
- 有块 → 块为主证，续接规则为**独立复核证人**（两者都成立时必须给出同一矩形，否则
  `tarch_opening_fill_conflict` fail）；
- 无块（炸开图） → 续接规则只能提候选，**剩余未归属缺口一律 fail**（`tarch_skin_gap_unattributed`），
  由人在 case intent 的 `overrides.openings` 里显式补声明。
- **绝不允许"自动猜一个洞口把图补闭合"** —— 那正是静默错答案的经典入口。

### S4 拓扑闭合与面域分解

- 线集 = S2 全部墙线 + S3 全部洞口矩形边。
- `polygonize_full(unary_union(lines))`。
- **G5**：`dangles / cuts / invalid` 必须全 0；且 `Σ面积` 必须等于外皮外包面积（对称差 ≤ τ_area）。
  实测 sm24：faces=51，三项全 0，Σ面积 = **200.00 m²** 精确等于 10×20。
- 残留悬空 → `tarch_wall_free_end`，payload 给出坐标；这通常意味着图上有**自由端墙**
  （伸进房间不到头的隔断）。v3 无法表达"半开放房间"，所以这里必须停下让人决定
  （当洞口处理 / 当延伸到对墙 / 改图），**不许自动延伸**——自动延伸会横切走廊，正是 Q5 明令禁止的事。

### S5 腔体（净房间轮廓）识别

- 面按面积二分：`> A_room` 为**腔体**，其余为**墙体材料面**。
  `A_room` 取自 case intent（默认 2 m²），**是建筑域参数不是容差**；
  它只用于分桶，误分会立刻被 G6（腔体数 vs 声明数）和 G7（铺砌）抓住，不是静默风险点。
- `WallRegion = unary_union(墙体材料面)`；`Footprint = unary_union(全部面)`。
  实测：墙体域 20.84 m²，腔体 8 个合计 179.16 m²，Footprint 200.00 m²。
- **`Footprint.interiors` 非空 ⇒ 回字形带洞** → `tarch_profile_hole_unsupported`（见 §11-U1）。
- **L 走廊在这一步天然是一个面**（实测净腔 30.82 m²，bounds x[27298,32818] y[30065,42445]），
  因为真实图纸在走廊拐角处**本来就没有墙**，转换器也不引入任何线。这是"不改画图习惯"的直接红利。

### S6 意图绑定（腔体 → 区）

见 §5.5。产出：每个腔体 ↔ 一个 `RoomIntent(zone_id, name, role)`，或被显式声明为 `void`（天井/中庭）。
未被认领的腔体 → `tarch_cavity_unclaimed`（fail）。

### S7 逐边外扩到混合基准框（腔体 → 区多边形）

对每个腔体多边形（先去共线冗余顶点、定向为 CCW）：

1. **逐边测厚**：对每条边，向外法向做射线，求射出 `WallRegion` 的距离 `d`。
   正交矩形域下这是**精确事件计算**（取 `WallRegion` 在该法向上的边坐标），
   不需要步进采样，**无采样参数**。
2. **远端分类**：射出点若落在 `Footprint` 外环上 ⇒ 该边背靠**外墙** ⇒ 外扩量 = `d`（落到**外皮**）；
   否则背靠**内墙** ⇒ 外扩量 = `d/2`（落到**墙轴线**）。
3. **沿边一致性**：在该边的所有"事件坐标"（`WallRegion` 顶点在该边上的投影）处分段测厚。
   若一条边跨越墙厚变化，则**按段拆边**，各段各自外扩（产生真实的墙垛错台，是正确几何）。
   任一段短于 `τ_node` 或分类不一致无法拆 → `tarch_edge_thickness_inconsistent` / `tarch_edge_far_side_ambiguous`（fail）。
4. **重建多边形**：正交多边形的边严格 H/V 交替，新顶点 = 相邻两条**外扩后支撑线**的交点
   （x 取自竖边、y 取自横边）。这一步天然处理 L 角 / 丁字 / 十字 / 凹角，
   **不需要任何"延伸与裁剪"特例代码**（派单 Q3 的接头问题在这里被结构性消解）。

**实测结果（决定性）**：8 个腔体外扩后，
∑面积 = **200.000 m²**，与 Footprint **对称差 0.000000 m²**，两两重叠 **0.0 m²**，
顶点数 4/4/8/6/4/4/4/4（两个非矩形区 = L 形走廊与另一凹形区，`_canonical_polygon` 可直接消费）。

### S8 九门自校验

见 §7。**任一门不过 = 不落盘几何**，只落转换报告 + 诊断 overlay。

### S9 落盘

见 §8。

---

## 5. 派单 §5 八个设计问题的正面回答

### 5.1 Q1 双线 → 单线：配对、非统一墙厚、基准、与 `outer_skin` 自洽

**不做"配对"。** 双线成对匹配是本题最诱人的陷阱（§3.2 #4）：墙厚不统一（D1 实测 240/120 混用）
让"恒定偏移"失效，接头处一条线同时属于多道墙让配对本身歧义。

**改为面域法**：墙线围出的**面**就是墙体材料；房间腔体就是墙体域的补集。
墙厚从不需要被"识别"，它是**逐边测出来的局部量**（S7-1），
每条边独立取值，因此 240/120/200 混用、甚至同一道墙中途变厚，都无需特殊代码。
**"墙厚统一"这个假设在本设计里根本不存在，无从烤死。**

**基准 = 混合框：外包取外皮，内墙取轴线。** 理由三条：

1. **v3 的铺砌约束逼出来的**：`dxf_zone_tiling_mismatch` 要求 `∪zones ≡ footprint`。
   若内墙取内皮，墙带会变成区与区之间的空隙，铺砌必然失败；
   一道内墙必须塌缩成**一条**线，而"两侧等分"是唯一各向同性、误差有界（≤ t/2）的取法。
2. **与已拍板方向一致**：`dimension_basis_and_wall_thickness_direction.md` §2 定的正是
   「外皮外包 + 内墙轴线」混合框，且 `zone_frame` 默认倾向 `axis`。
   ⇒ gt 与管线内核同框，判卷零换算（现 W5 的 t/2 shim 不再介入 zone 边界）。
3. **误差结构最优**：外包被外皮锁死（立面/总链/gt 三路可观测），
   内墙误差 ≤ t/2 且笔笔可审计（转换报告逐边记 basis 与 thickness）。

**与 `boundary_reference: "outer_skin"` 的自洽性**：**声明层自洽，且不是含糊其辞**。
读码确认（D8）该字段不参与任何几何计算，仅被断言等于 `outer_skin`；
它在语义上描述的是 **footprint 的基准**，而我们的 footprint 正是外皮 ⇒ 声明为真，**不是撒谎**。
内墙取轴线这件事 v3 wire 目前**无处声明**（`PlanViewBindingV1` 是 `extra="forbid"` 严格模型），
所以：
- 本轮记入**转换报告**的逐边 `basis: outer_skin | wall_axis` 字段（机器可查、可回归）；
- 登记 v-next 字段请求 `zone_boundary_reference: "wall_axis"`（§11-U2），
  避免这个语义永远只活在文档里。
- **绝不**改用 `boundary_reference: "centerline"` —— 那会直接撞 `dxf_centerline_unsupported_in_phase_b`，
  且语义也不对（footprint 不是中心线）。

### 5.2 Q2 洞口补齐

**先拆题**（D4）：派单把两件事合并了。

- **洞口本身不需要转换**。v3 的 `virtual_entity_bbox` 明确要求 INSERT，
  门窗块可以**原样**被 manifest 绑定。这也是"追加图层不重写 DXF"的直接收益。
- 需要补齐的是**墙线的连续性**：洞口处墙线断开 ⇒ 外皮不闭合 ⇒ polygonize 出 0 面。

**补齐策略 = 双证据**（S3）：沿墙跨度取自块 bbox，法向范围取自墙体自身的端头横截区间。
**不能整块 bbox 直接用**——门块 bbox 含开启扇（D2，AC3 越出外墙 660 mm）。
实测 21/21 解析成功，零歧义。

**块被炸成线的图**：退到几何续接规则，但实测证明它**高精度低召回**（12/21，零假阳性），
所以它只做**独立复核证人**（有块时必须与块给出同一矩形，否则 fail）与**候选提示**，
永远不做唯一依据；未归属缺口一律 fail 并要求人显式声明。
**关键纪律：宁可停在"这里有个缺口我不知道是什么"，也不自动补一个洞把图凑闭合。**

**额外收益（G4）**：外皮缺口数必须等于外围洞口数（实测 14 == 14）。
这条守恒式独立于上面两种证据，能抓住"多补一个洞"和"漏一个洞"两个方向的错误。

### 5.3 Q3 接头（丁字/十字/L 角/自由端）与容差来源

**丁字 / 十字 / L 角：不需要任何延伸与裁剪代码。**
这些接头在面域法里只是 `WallRegion` 的一部分；区多边形的角点由
**相邻两条外扩支撑线求交**得到（S7-4），拓扑上自动正确。
这正是面域法相对配对法的结构性优势：接头是配对法的噩梦，在面域法里根本不是一个 case。

**墙自由端（端头封口）：fail-closed，不自动处理。**
自由端会在 S4 留下悬空（`tarch_wall_free_end`），意味着"房间没围住"。
v3 无法表达半开放空间；而**自动把自由端延伸到对面墙，会横切走廊**——
恰恰是派单 Q5 明令禁止的事。所以这里必须停下由人裁决，三个出路写进诊断的 remedy：
①声明为洞口（两侧连通，合并成一个区）；②声明延伸目标（人给意图）；③改图。

**容差来源：只用 `judge_gt.yaml` 已有的七个，零新增。**

| 用途 | 取值 |
|---|---|
| 量化步长 | `dxf_node_join_tolerance_m / 10`（派生量，非配置项） |
| 节点合并 / 分段最小长度 | `dxf_node_join_tolerance_m` |
| 正交性判定 | `dxf_axis_alignment_tolerance_m` |
| 面积残差（铺砌门 G7 / 反演门 G8 / 细片） | `dxf_topology_area_tolerance_m2` |
| 开口→边界距离 | `opening_boundary_max_distance_m`（见下） |

**关于 `opening_boundary_max_distance_m`(0.4 m) 的一个隐藏脆点**（本轮实测发现，值得记账）：
v3 用**块 bbox 中心**到边界段的法向距离做归属判定。门块 bbox 含开启扇 ⇒ 中心被推离墙体。
实测外门 AC9：bbox 中心距东外皮 **270 mm**，仅剩 130 mm 余量；开启扇更深的门会直接超 400 mm 而 fail。
⇒ **本方案顺手消解掉它**：转换器在 `GTV3_OPENING` 层输出**干净洞口矩形**（S3 的产物）作为闭合 LWPOLYLINE，
manifest 用 `closed_outline_bbox` 绑它而**不绑原始块**。这样中心落在墙带正中，
距外皮 = t/2 = 120 mm，余量充裕且与开启扇画法无关。原始块句柄记进转换报告做溯源。
（这也顺带让炸开图与带块图走同一条下游路径。）

### 5.4 Q4 凹角与非凸轮廓（L / U / 回字）

**L 形（sm25）与 U 形（sm26）：本设计与 v3 均已支持，无需扩展。**
- 转换器侧：面域法 + 逐边外扩对凹角无特殊性；实测 sm24 已产出 8 顶点与 6 顶点的凹形区。
- v3 侧：`_canonical_polygon` 接受任意简单正交环；
  `vg_for_direction` 是为**遮挡可见性**设计的（凹形才需要它），读码确认它消费单个外环并做 skyline 计算，
  凹角是其正常工作域。
- **保证"面与设计意图一致"的机制不是几何巧妙，而是 §7 的 G6 + G7 + G8 三重门**：
  腔体数必须等于人声明的房间数（抓错切/错并）、区必须精确铺砌外包（抓错位）、
  反演重建必须还原墙体域（抓基准错）。几何算法可以有 bug，这三道门让 bug 变成红灯而不是错答案。

**回字形（sm27，带洞）：转换器能算，但 v3 profile 挡住，本轮明确 fail-closed。**
- `Footprint.interiors` 非空即检出，抛 `tarch_profile_hole_unsupported`。
- **需要新 profile**：是的。缺口不止一处，需当独立工作项排（§11-U1）：
  ① `geometry_profile` 增枚举值（如 `c2_orthogonal_with_holes`）；
  ② `_canonical_polygon` 目前对 `poly.interiors` 直接 `dxf_polygon_profile_unsupported`；
  ③ `validate_gt_v3` 的 `gt_profile_holes_unsupported`；
  ④ **最实质的一条**：`vg_for_direction` 只吃单个外环，
     朝向内院的立面段将完全不可见 ⇒ 内院窗的可见性/立面绑定会错。这是几何内核级扩展，不是加个枚举。
- 附带的意图问题：内院腔体与房间腔体在平面上**无法几何区分**（都是被墙围住的空腔）。
  必须由人在 case intent 的 `voids` 里显式声明 ⇒ 未声明的内院会撞 `tarch_cavity_unclaimed` 而红，
  **不会被静默当成一个房间**。这条在 sm27 之前就该生效，不需要等 profile 扩展。

### 5.5 Q5 区划意图从哪来（**全链最脆一步**）

**先说清风险**：如果种子点由转换器从自己算出的面导出，那么 v3 的
"每个面恰含一个种子"+"种子并集覆盖 footprint" 就变成**自证同义反复**：
走廊被错切成两片 → 自动产出两个种子 → 两个面各含一个种子 → **全绿**。
这就是 false-green 的教科书形态，必须结构性拆开。

**拆法：坐标归机器，身份归人。**

| 字段 | 来源 | 理由 |
|---|---|---|
| 种子**坐标** | 机器（腔体 `representative_point`，并校验距边界 > `τ_node` 以避开 `dxf_zone_seed_near_boundary`） | 人写坐标又慢又易错，且坐标错会被 overlay 与 G7 抓住 |
| 种子**数量 / 名称 / 用途** | **人** | 这是意图，机器无从得知；也正是能抓住"走廊被切开"的那一维 |

**两个意图源，同一内部结构 `RoomIntent`：**

- **源 A（sm24，图上无房名）**：case intent 文件显式声明
  ```yaml
  rooms:
    expected_count: 8          # 必填，非空
    list:
      - {zone_id: z_corridor, name: "走廊", role: circulation}
      - ...                    # 共 8 条
  ```
  转换器把腔体按**规范顺序**（(min_x, min_y) 字典序）与 list 一一配对，
  并把配对结果画进 overlay 让人核。`expected_count` ≠ 腔体数 ⇒ `tarch_cavity_count_mismatch`（fail）。
- **源 B（sm25 起，CAD 标房间名）**：读指定图层的 TEXT/MTEXT 插入点。
  要求**每个腔体恰含一个标签、每个标签恰落在一个腔体内**（双向单射）。
  违反 ⇒ `tarch_cavity_multi_label` / `tarch_cavity_unclaimed`。
  此时数量校验**自动成立**且强度更高（还校验了身份与位置），`expected_count` 可选。

**对 L 走廊的直接效力**：用户拍板 sm24 = 8 区、L 走廊算 1 个热区。
转换器天然不在拐角引线（S5 实测），若将来某个改动引入了拐角切分线，
腔体会变 9 个 ≠ 声明的 8 ⇒ **当场红**。这就是把"最该有人看着的一维"交给人的价值。

**残留诚实说明**：这条防线的强度取决于人是否认真填那个数字/那组房名。
它不是机械的。缓解措施是把它做成**必填且无默认值**（不填不跑），
并在 overlay 上把每个区的名字直接标在图上，让"填错"在人核环节可见。

### 5.6 Q6 失败诊断的可定位性

**设计原则**：诊断必须让人**不看代码就能走到图上那个点**。三件套缺一不可：

1. **稳定诊断码**（`tarch_*` 前缀，见 §6 表），进转换报告的 `diagnostics[]`；
2. **可定位载荷**：`source_point_mm`（源坐标系原值，人可直接在天正里输入定位）
   + `entity_handles[]`（原始句柄，可 `SELECT` 选中）+ `layer` + `view_id`；
3. **诊断 overlay**：一张与平面图同框的渲染件，把每条诊断标在出事位置（红圈 + 码）。
   这一张图是"人拿到诊断能做什么"的实际载体。

**闭环**（每个码在 §6 表里都必须填 remedy 列，无 remedy 的码不许上线）：

```
转换失败 → 报告 + 诊断 overlay
   ├─ 图纸问题（漏画/错画/自由端）      → 用户改图 → 重跑（转换器确定性，同输入同输出）
   ├─ 意图缺失（房间数/内院/自由端裁决）→ 填 case intent 的 rooms / voids / overrides → 重跑
   └─ 转换器能力不足（新画法/回字形）    → 落成 backlog 工作项，附最小复现夹具
```

**反 false-green 纪律**：诊断**只允许**出现在"未产出几何"的路径上。
**禁止**任何 `WARN 但继续` 的降级路径。一旦允许 warn-continue，
gt 就可能带着已知瑕疵出厂，而下游没有任何机制知道这件事。

### 5.7 Q7 验收：如何证明转换正确 + 泛化证据

**五层，逐层独立**：

1. **sm24 真图端到端**（必要非充分）：转换 → v3 → gt candidate → overlay 人核 → verified。
   断言本稿 §0 表里的每一个实测数字（8 区 / 200.00 m² / 对称差 0 / 走廊单面）为回归基线。
2. **合成夹具矩阵**（覆盖设计空间，非样本空间）。参数化生成"天正画法"DXF（双线 + 洞口断开 + 块），
   覆盖：统一 240 / 混合 240+120+200 / 同墙中途变厚 / L 形外轮廓 / U 形 / 回字（**期望红**）/
   丁字 / 十字 / L 角 / 自由端（**期望红**）/ 洞口贴角 / 洞口占满整道墙 / 炸开无块（**期望红或需声明**）/
   无归属缺口（**期望红**）/ 内外门混合。
   **每个诊断码至少一个必红夹具** —— 没有必红夹具的码等于没上线（这是 C2 历次审计反复抓到的 false-lock 形态）。
3. **不变量 / 变形测试**（真正的泛化证据，因为它不依赖具体图）：
   - 平移、90°/180°/270° 旋转、镜像整张图 ⇒ 区多边形**同变**，区数与邻接关系**不变**；
   - 改内墙厚度 t → t' ⇒ 区边界沿法向移动恰 `(t'-t)/2`，拓扑不变；
   - 移动/增删洞口 ⇒ 区拓扑**完全不变**（洞口不参与区划）；
   - 打乱 DXF 实体顺序 ⇒ 输出字节级相同（确定性）。
4. **sm21 差分锚（独立回归锚，成本极低，强烈建议做）**：
   sm21 已有人核过的 gt（老 v2 路线产出）。sm21 是矩形网格建筑 ⇒ 两条完全不同的算法应给出同一答案。
   拿本转换器跑 `gt/sm21_anchor/source.dxf`（注意 D6：需先拷进 staging），
   对账 footprint / zone 划分 / 窗 openings。**不一致必须逐条解释**，
   这是唯一一个"用历史人核结论检验新算法"的机会。
5. **运行时反演门 G8**（不依赖任何测试覆盖的兜底）：见 §7。
   测试覆盖不到的图，G8 仍然逐图起作用 —— 这是应对"sm24 通过 ≠ 泛化"的**结构性**答案，
   而不是靠多写几个 case。

**明确承认**：以上都不能证明"对任意天正图正确"。目标不是证明正确，
而是**保证不正确时会红**。这是答案生成器唯一站得住的验收哲学。

### 5.8 Q8 房间用途 role 的演进（有标签/无标签都要能跑）

**统一抽象 `RoomIntentSource`，两个实现**（§5.5 源 A/源 B），
上游算法**完全不感知**用的是哪个源 ⇒ sm25 起在 CAD 标房间名，只是换一个实现类，转换器主干零改动。

**sm24（无标签，role 不作判分项）的处理**：
`ZoneSeedV1.role` 是必填 `StableId`，无法留空。方案：
- 填哨兵值 `unspecified`；
- 转换报告记 `role_source: "declared_absent"`；
- **登记一个真实缺口**：v3 wire 没有"role 未知"的表达，判卷侧无从区分
  "role 是 unspecified" 与 "role 真的叫 unspecified"。⇒ §11-U3：
  要么在 gt v-next 加 `role_known: bool`，要么在 judge 侧建立 `unspecified` 保留字约定并机械守。
  **本轮不夹带这个改动，但必须登记**，否则 sm25 上线时会有人把 `unspecified` 当成一个真用途去判分。

**sm25 起（CAD 标房间名）**：标签同时提供 name + role + 计数校验 + 位置校验（四合一）。
role 从标签文本经**显式映射表**（case intent 里的 `role_map`，如 `办公 → office`）转换，
**未在映射表中的文本一律 fail**（`tarch_role_unmapped`）——不做模糊匹配、不做 LLM 归类。
答案端的每一个字都必须可追溯到人的显式声明或图纸的确定性内容。

---

## 6. 失败诊断码表

**约定**：`severity` 只有 `BLOCK`（不出几何）与 `INFO`（记账，不影响出件）两级。
**没有 WARN**——见 §5.6 反 false-green 纪律。
每条 BLOCK 必须带 `source_point_mm` 与/或 `entity_handles`，且必须有 remedy。

| 码 | 级 | 触发 | 载荷 | remedy（人拿到能做什么） |
|---|---|---|---|---|
| `tarch_source_proxy_present` | BLOCK | `proxy_entity_count > 0` | 句柄 | 天正里重走「图形导出」而非另存 |
| `tarch_units_undeclared` | BLOCK | unitless 且 case intent 未给 `metres_per_unit` | — | 在 intent 里显式写单位换算 |
| `tarch_view_frame_missing` | BLOCK | `edge` 层无框 / 框不闭合 | 框句柄 | 补画视图框（约定见 SURVEY §2.3） |
| `tarch_view_frame_ambiguous` | BLOCK | 框内图名文字数 ≠ 1 | 框句柄 + 文字句柄 | 一框一图名 |
| `tarch_wall_nonorthogonal` | BLOCK | 墙线非轴平行（超 `τ_axis`） | 线句柄 + 两端点 | 本轮范围外；改图或登记扩展需求 |
| `tarch_wall_degenerate_line` | INFO | 量化后首尾同点 | 线句柄 + 点 | 记账即可（sm24 实测 1 根） |
| `tarch_quantization_conflict` | BLOCK | 两个相距 > `τ_node` 的坐标落同格点 | 两点 | 图纸精度异常，需人查 |
| `tarch_opening_block_unresolved` | BLOCK | 块找不到匹配墙垛端头对 | 块句柄 + bbox | 补画墙垛端头 / 在 `overrides.openings` 显式给洞口矩形 |
| `tarch_opening_block_ambiguous` | BLOCK | 匹配到多组墙带 | 块句柄 + 各候选 | 同上，用 override 指定 |
| `tarch_opening_fill_conflict` | BLOCK | 块证据与几何续接证人给出不同矩形 | 块句柄 + 两矩形 | 查图（通常是块被移动过 / 墙被改过） |
| `tarch_skin_gap_unattributed` | BLOCK | 补齐后仍有未归属缺口 | 缺口两端点 | 该处是洞口就声明；是自由端见下条 |
| `tarch_wall_free_end` | BLOCK | S4 出现悬空 | 悬空端点 | 三选一：声明为洞口 / 声明延伸目标 / 改图。**转换器绝不自动延伸** |
| `tarch_topology_residual` | BLOCK | `dangles/cuts/invalid` ≠ 0 或面积和 ≠ 外包 | 各残留几何 | 看诊断 overlay 定位 |
| `tarch_cavity_count_mismatch` | BLOCK | 腔体数 ≠ `expected_count` | 各腔体重心 + 声明数 | 核对房间数；**这是抓"走廊被切开"的主门** |
| `tarch_cavity_unclaimed` | BLOCK | 腔体无 seed/label 且未声明为 void | 腔体重心 + 面积 | 补房名 / 在 `voids` 声明为天井 |
| `tarch_cavity_multi_label` | BLOCK | 一腔体含多个房名标签 | 腔体 + 标签句柄 | 删多余标签 / 该处确实是两个房间则补墙 |
| `tarch_role_unmapped` | BLOCK | 房名文本不在 `role_map` | 文本 + 句柄 | 补映射表条目。**不做模糊匹配** |
| `tarch_edge_thickness_inconsistent` | BLOCK | 一条边跨墙厚变化且无法按事件坐标拆段 | 边 + 各段厚度 | 查图；通常是墙未对齐 |
| `tarch_edge_far_side_ambiguous` | BLOCK | 外扩远端分类（外皮/内墙）不唯一 | 边 + 射线出点 | 查图 |
| `tarch_zone_tiling_residual` | BLOCK | G7 铺砌对称差 > `τ_area` 或区间重叠 | 残差几何 | 转换器 bug，落最小复现夹具 |
| `tarch_reconstruction_residual` | BLOCK | G8 反演墙体域对不上 | 残差几何 + 涉及边 | 同上，**最高优先级**（说明基准记错） |
| `tarch_profile_hole_unsupported` | BLOCK | footprint 有内环（回字形） | 内环 | 等 §11-U1 profile 扩展；本轮明确不支持 |
| `tarch_interior_opening_excluded` | INFO | 洞口归属内墙，不写入 manifest | 块句柄 | 记账（sm24 实测 7 个） |
| `tarch_opening_skin_gap_mismatch` | BLOCK | 外皮缺口数 ≠ 外围洞口数 | 两个计数 + 差集位置 | 查漏补缺（sm24 实测 14==14） |
| `tarch_v3_precondition` | BLOCK | G9 预演时 v3 抛任何 `ExtractionError` | 原始 v3 码 + 上下文 | 按 v3 码查；**转换器不 catch、不改写、不吞** |

---

## 7. 自校验闸门（fail-closed 的实体）

> 这一节是本方案对"绝不静默出错答案"这条硬约束的**机械答复**。
> 九门全过才落几何；任一门红 = 只落报告与诊断 overlay。

| 门 | 检查什么 | 为什么它是**独立**证人 | sm24 实测 |
|---|---|---|---|
| **G1** 输入体检 | proxy=0 / 正交 / 单位 / 视图框 | 上游前提，与算法无关 | 通过 |
| **G2** 量化守恒 | 量化不得合并 > `τ_node` 的真实差异 | 只看坐标，不看拓扑 | 通过 |
| **G3** 洞口双证 | 块证据 ↔ 几何续接证人一致 | 两条**不同信息源**（块 vs 墙线） | 12 处双证全一致，余 9 处单证 |
| **G4** 缺口守恒 | 外皮缺口数 == 外围洞口数 | 计数式，绕开所有几何细节 | **14 == 14** |
| **G5** 拓扑闭合 | dangles/cuts/invalid = 0 且 Σ面积 == 外包 | 面积是全局量，局部错误无法互相掩盖 | 51 面，三项全 0，**200.00 m²** |
| **G6** 腔体认领 | 每腔体恰一个 seed/label；数量 == 人声明 | **人写的数字**，是唯一非机器证人 | 8 == 8 |
| **G7** 铺砌 | ∪zones ≡ footprint 且两两不重叠 | v3 也会再查一遍（`dxf_zone_tiling_mismatch`），此处提前 | 对称差 **0.000000 m²**，重叠 **0.0** |
| **G8** **反演重建** | 由输出 zones + 逐边 basis/thickness **反算**墙体域，与 G5 实测墙体域对账 | **逆向**计算路径，与正向不共享代码 | 待施工（正向侧墙体域 = 20.84 m²） |
| **G9** v3 预演 | 直接跑 `inspect_extraction_inputs` + `extract_gt_v3` | 下游真实消费者 | 待施工 |
| **G10** 人核 | overlay 比对 + 签字才 candidate→verified | 人 | 流程门 |

**G8 是主保险，值得展开**：
G7 只能证明"区之间不打架"，**不能**证明"区放在了正确的地方"——
如果每条边的基准都统一错了（例如把内墙也当外墙外扩满厚度），
区之间依然能严丝合缝地铺满一个**错误的** footprint。
G8 反过来走：拿输出的区多边形和逐边记录的 `basis/thickness`，重建每道墙的实体带，
与 S5 直接量出的 `WallRegion` 求对称差。基准记错 ⇒ 重建出的墙厚不对 ⇒ 对称差爆掉。
它是唯一一道能抓"系统性基准错误"的门，也是应对"测试覆盖不到的新图"的结构性兜底。

**反 false-lock 纪律**（C2 历次审计的血泪）：
每一道门都必须有**至少一个必红夹具**（故意造错 → 断言该门红）。
只断言"正常输入过门"的测试是 false-lock：门可能根本没接线，而测试永远绿。

---

## 8. 数据结构与产物格式

### 8.1 规范化 DXF（追加图层）

源文档原样 + 三个新图层（名字进常量，不散落）：

| 图层 | 内容 | 被 manifest 的谁消费 |
|---|---|---|
| `GTV3_FOOTPRINT` | 1 条闭合 LWPOLYLINE = 外皮外环 | `footprint_boundary` 选择器 |
| `GTV3_ZONE` | N 条 LINE = 内部区划边界（轴线框，已去重、已按平面图打断） | `zone_boundaries` 选择器 |
| `GTV3_OPENING` | M 条闭合 LWPOLYLINE = 干净洞口矩形（仅外围洞口） | `plan_openings` 的 `closed_outline_bbox` |

要点：
- 坐标为量化后的精确值 ⇒ v3 的 `_snap_segments` 在其上是恒等映射，不会二次改动几何。
- 全部新实体严格落在平面视图 clip box **内部**（不触边），避开 `dxf_entity_clip_boundary`。
- 选择器用 `handle_mode: "only_listed"` 钉死句柄，避免"图层里多一根线"悄悄改变答案。
- 原实体一个不动 ⇒ 立面绑定、`edge` 框、图名文字、洞口块句柄全部继续有效。

### 8.2 转换报告 `conversion_report.json`（严格 pydantic，`extra="forbid"`）

```jsonc
{
  "report_version": 1,
  "status": "PASS" | "BLOCKED",
  "case": "sm24_anchor",
  "source_dxf_sha256": "...",              // 原始天正导出件
  "normalized_dxf_sha256": "...",          // 派生件（= manifest.source_dxf_sha256）
  "case_intent_sha256": "...",             // 人写的意图文件
  "judge_config_sha256": "...",            // judge_gt.yaml，经 load_gt_tooling_config
  "converter_sha256": "...",               // 转换器实现哈希
  "quantization_step_m": 0.0001,
  "walls":    [{"band_id":"w_012","axis":"y","coord_mm":42505.2,
                "span_mm":[27298,32818],"thickness_mm":120.0,
                "source_handles":["1A3","1A4"]}],
  "openings": [{"opening_id":"op_ae1","kind":"window","classification":"exterior",
                "rect_mm":[27717.6,46325.2,32517.6,46565.2],
                "evidence":{"block_handle":"AE1","block_name":"$TCHSYS$WIN2D",
                            "jamb_handles":["...","..."],"geometric_witness":true},
                "derived_handle":"<GTV3_OPENING 实体句柄>"}],
  "cavities": [{"cavity_id":"c_03","area_m2":30.82,"vertices_m":[[...]],
                "claimed_by":"z_corridor","claim_source":"intent_file"}],
  "zones":    [{"zone_id":"z_corridor","name":"走廊","role":"unspecified",
                "role_source":"declared_absent",
                "seed_point_world_m":[x,y],"polygon_m":[[...]],
                "edges":[{"p1":[...],"p2":[...],"basis":"wall_axis",
                          "thickness_m":0.12,"offset_m":0.06,
                          "derived_handle":"...","source_handles":["1A3"]}]}],
  "gates":    [{"id":"G5","passed":true,
                "evidence":{"faces":51,"dangles":0,"cuts":0,"invalid":0,
                            "sum_area_m2":200.0,"footprint_area_m2":200.0}}],
  "diagnostics": [{"code":"tarch_interior_opening_excluded","severity":"INFO",
                   "source_point_mm":[28877.6,41375.2],"entity_handles":["AD2"],
                   "context":{"reason":"opening hosts an interior wall band"}}]
}
```

**`zones[].edges[].basis` 是 D7 的补偿件也是 G8 的输入**：
gt.json 里存不下"这条边取的是外皮还是轴线"，报告里必须存，
且报告 sha256 要能被 gt 侧引用（挂在 gt bundle 内，随 gt 一起归档）。

### 8.3 case intent 文件（人写，唯一非机器输入）

```yaml
case: sm24_anchor
metres_per_unit: 0.001
wall_thickness_range_m: [0.06, 0.50]     # 合法墙厚域，非容差
min_room_area_m2: 2.0                    # 腔体/墙面分桶阈，非容差
floors: [{id: f1, name: "1F", z_floor_m: 0.0, ceiling_height_m: 4.5}]
plan_view: {id: plan_f1, floor_id: f1, frame_title: "1f平面图"}
rooms:
  source: intent_file                    # 或 cad_labels（sm25 起）
  expected_count: 8                      # 必填、无默认
  list: [{zone_id: z_corridor, name: "走廊", role: unspecified}, ...]
role_map: {}                             # cad_labels 时必填，未映射即 fail
voids: []                                # 天井/中庭腔体显式声明（回字形用）
overrides:
  openings: []                           # 炸开图 / 疑难洞口的显式矩形
  free_ends: []                          # 自由端裁决
```

### 8.4 人核件

- `overlay_plan.svg/png`：原平面 PNG 底图 + 区多边形（半透明填色 + 区名）+ 洞口矩形 + 外皮外环；
- `overlay_diagnostics.svg/png`：失败时出，把每条诊断标在出事坐标；
- 之后接现有 `render_gt.py` 出 gt 直渲件。
- **G10 未签字前，gt 只能是 `verification.status = "candidate"`**（v3 已机械守此字段）。

### 8.5 目录与纪律

```
AI_agent/logs/experiments/<date>_<case>_gt/work/     ← staging，转换与构建都在这里跑
    source.dxf  normalized.dxf  conversion_report.json  manifest.json  overlays/
case_tests/test_baseline/gt/<case>/                  ← 人核通过后晋升
    gt.json  source.dxf  normalized.dxf  conversion_report.json  renders/
```

- **必须在 staging 跑**：`gt_from_dxf.py::_protected_dxf_source` 拒绝从 `gt/` 下读 DXF（D6）。
- 归属：库 `src/agent/judge/tarch_normalize.py`（judge 侧），CLI `scripts/tool_scripts/normalize_tarch_dxf.py`。
- **gt 铁律**：`src/validator/checks/*` 与 `src/agent/pipeline.py` 绝不 import；
  `tests/test_gt_discipline.py` 需扩三条：①新模块进 runtime 禁 import 面；
  ②CLI 不被任何 runtime 模块 import；③`case_data/` 下无 `.dxf/.dwg`（已有，确认覆盖 `normalized.dxf`）。

---

## 9. 测试与验收策略

| 层 | 内容 | 判据 |
|---|---|---|
| L1 单元 | S1 量化 / S2 端头 / S3 双证 / S7 外扩几何（含凹角、厚度突变） | 逐函数确定性断言 |
| L2 合成夹具 | §5.7-2 矩阵（含**每个诊断码一个必红夹具**） | 期望绿的绿、期望红的**红在指定码上** |
| L3 不变量 | 平移/旋转/镜像/改厚/移洞/乱序 | 同变或不变，字节级确定性 |
| L4 sm24 端到端 | 真图 → gt candidate → overlay | §0 表全部数字为回归基线 |
| L5 sm21 差分锚 | 新转换器 vs 已人核 gt | 不一致必须逐条解释 |
| L6 纪律 | `test_gt_discipline` 三条扩展 | 机械守 |

**验收出口（不达不进下一批）**：
1. L1–L4 全绿且 sm24 gt 经人核晋升 verified；
2. 每个 §6 诊断码都有必红夹具（无夹具的码视为未上线，从表里删掉而不是留着）；
3. L5 差分锚跑过且差异清零或有书面解释；
4. 全量测试零回归（当前基线 1456 绿）。

---

## 10. 分阶段落地

| 阶段 | 交付 | 出口判据 |
|---|---|---|
| **P1** 骨架 | 报告 schema + case intent schema + CLI + S0/S1 + G1/G2 | 跑 sm24 出报告（无几何），单位/框/正交/量化全过 |
| **P2** 洞口 | S2/S3 + G3/G4 | sm24 21/21 解析，14==14 守恒 |
| **P3** 拓扑 | S4/S5 + G5 | faces=51，三项 0，Σ=200.00 m²，8 腔体，走廊单面 |
| **P4** 区划 | S6/S7 + G6/G7/G8 + 落规范化 DXF | 8 区，对称差 0，反演门过 |
| **P5** 接线 | manifest 草稿 + G9 | sm24 端到端出 gt candidate |
| **P6** 人核 | overlay 双件 + G10 + 晋升 SOP | sm24 gt verified |
| **P7** 泛化 | L2/L3/L5 全套 | §9 验收出口四条 |
| **P8** 爬坡 | sm25(L) 实战 → sm26(U) | 各自端到端 + 人核 |
| **P9** 回字 | 触发 §11-U1（v3 侧独立工作项） | 单独立项，不由本转换器夹带 |

P1–P6 是一条依赖链，建议单批施工；P7 可与 P6 并行；P8 起按 C2 路线排。

---

## 11. 风险与未决项

### U1（必须单独立项）回字形 profile 扩展 —— 不是加个枚举

本转换器能算出带洞 footprint，但 v3 侧四处挡住：
`geometry_profile` 枚举 / `_canonical_polygon` 拒 `poly.interiors` /
`validate_gt_v3` 的 `gt_profile_holes_unsupported` /
**`vg_for_direction` 只吃单个外环**（朝内院的立面段将完全不可见 ⇒ 内院窗可见性与立面绑定会错）。
第四条是几何内核级工作。**sm27 之前必须立项**，本轮 fail-closed 挡住。

### U2 内墙基准在 v3 wire 无处声明

`boundary_reference` 是视图级、且只描述 footprint（D8）。
"内墙取轴线"目前只活在转换报告与文档里。建议 v-next 加 `zone_boundary_reference`。
风险：不加的话，将来换基准（`zone_frame: exterior` 档）时 gt 与产物会静默错框。

### U3 role 未知在 gt v3 无表达

`unspecified` 哨兵与真用途无法区分（§5.8）。sm25 上线前必须解决，
否则会有人把 `unspecified` 当成一个真用途去判分。

### U4 溯源指针指向派生件（D7）

gt.json 的 `source_refs` 指向 `GTV3_*` 派生线，不指向原始天正墙线。
缓解：转换报告逐边记 `source_handles`。**残留风险**：若有人只拿 gt.json 不拿报告，
就失去了回到原图的能力 ⇒ 报告必须与 gt.json 同 bundle 归档，且 sha 进 provenance。

### U5 `opening_boundary_max_distance_m` 余量（已在本方案内缓解）

原始门块 bbox 中心离外皮 270 mm（实测 AC9），仅剩 130 mm 余量。
本方案绑干净洞口矩形而非原始块（§5.3），余量恢复到 120 mm/400 mm。
**残留风险**：若将来有人图省事改回绑原始块，这个坑会重现且表现为"某些门莫名 fail"。
建议在报告里断言 `plan_openings` 全部绑 `closed_outline_bbox`。

### U6 意图源是全链唯一非机械环节

`expected_count` / 房名由人填。填错 ⇒ G6 失效。缓解：必填无默认 + overlay 上标区名让人核。
**这是本方案最脆的一环，已在 §0 明示，不掩饰。**

### U7 本轮范围外（明确不做，且不烤死）

斜墙/曲墙/非正交（S0 明确拒收）；多层跨层对齐（数据结构按多楼层设计，**不假设共用 footprint**——
v3 现有 `dxf_profile_floor_footprint_mismatch` 要求各层 footprint 相同，
这是**v3 的**现有限制，转换器不额外加码，登记为跨层批次的已知约束）；
CAD 作为产品输入模态的方言适配层（属 `cad_to_gt_extraction_plan.md` §10 的另一侧，
本转换器是"我们说了算的 gt 来源"这一侧，不需要归一化层）。

### U8 派单本身的错处（按派单 §7 要求登记）

§2 的四条修订 D1/D2/D3/D4 中，**D2 与 D4 出自派单正文而非 SURVEY**：
- 派单 §5 Q2 称"实测门窗块 bbox 精确等于洞口"——对门不成立（SURVEY 原文只说窗，派单概括时失真）；
- 派单 §5 Q2 以"v3 的 `_entity_points` 拒绝 INSERT"为前提问补齐策略——
  该拒绝只在边界选择器路径成立，开口路径明确支持 INSERT，问题需重新分解。

D6（`_protected_dxf_source` 与 bundle 约定打架）是既有仓库内部的不一致，不是派单的错，但会绊倒执行者。

---

## 12. 施工自检清单（新执行者只读本稿能否动手）

- [ ] 我知道产物是什么：规范化 DXF（三个追加图层）+ 转换报告 + manifest 草稿 + 两张 overlay（§8）
- [ ] 我知道算法每一步：S0–S9（§4），且每步的失败码在 §6 表里
- [ ] 我知道容差从哪来：`judge_gt.yaml` 七个，零新增；量化步长是派生量（§5.3）
- [ ] 我知道基准怎么定：外包外皮 / 内墙轴线，逐边测厚（§5.1）
- [ ] 我知道洞口怎么补：块给沿墙跨度、墙体给法向，双证据（§5.2）
- [ ] 我知道意图从哪来：人给数量与名字，机器给坐标（§5.5）
- [ ] 我知道什么时候必须停：§6 全部 BLOCK 码，且**没有 warn-continue 路径**
- [ ] 我知道怎么证明没错：九门（§7）+ 六层测试（§9），每门每码都有必红夹具
- [ ] 我知道 sm24 应该跑出什么：§0 表（8 区 / 200.00 m² / 对称差 0 / 走廊单面 / 14==14 / 21/21）
- [ ] 我知道在哪跑：staging 工作目录，不在 `gt/` 下（§8.5，D6）
