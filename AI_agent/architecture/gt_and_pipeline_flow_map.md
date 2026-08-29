# gt 链 与 pipeline 链：**目标态说明书** + 每格今天到哪

> **用途**：用户 2026-08-29 令「把 gt 流程（每个流程的产物）和 pipeline（主要是 reading 和 correction）
> 详细梳理一下」，并当场校准重心 —— **「咱主要是关注目标态，现状本身就是施工中」**。
> ⇒ **本文主体 = 目标态：每一步谁跑、吃什么、吐哪个文件、那个文件里装什么。**
> **现状只当一列状态标记**（✅ 已落地 · 🟡 有代码没接线 · ❌ 没有），集中在每部分末尾的一张表里。
>
> ⛔ **本文不放口径也不放待办**：分工与硬纪律 → [`../guides/reading_correction_split_guide.md`](../guides/reading_correction_split_guide.md)（**冲突时以它为准**）·
> gt 三截与签字流程 → [`gt_revision_ledger.md`](gt_revision_ledger.md) · reading 形态 → [`reading_pipeline_architecture.md`](reading_pipeline_architecture.md) ·
> 判分画法规格 → [`judge_grade_model.md`](judge_grade_model.md) · 观测层书写权与成绩闸 → [`as_drawn_layer_contract.md`](as_drawn_layer_contract.md) ·
> 管线逐段契约与磁盘布局 → [`pipeline_stage_contracts.md`](pipeline_stage_contracts.md)。
>
> **状态标记的实测基准**：分支 `08.23_AsDrawnReading`、commit `866d518`、2026-08-29；
> 目录清点对象 = 真实在库的 `case_tests/test_baseline/gt/sm25-L_anchor/`。

---

# 第一部分 · gt 链的目标态：**一份事实 + 一个派生器出多个出口**

## 1.1 全链

```
我们画的 CAD ──→ source.dxf  （⭐ as-received：真正未经手改的那份）
                    │
                    │  转换器：0.1 mm 量化 · ⭐正交吸附 · 配面线成墙 · 量厚度 · 解析洞口 · 闭合外轮廓
                    ↓
        ┌───────────────────────────────────────────────┐
        │  as_measured.json     ⛔ 永不修改             │  机器量到的事实
        │        ⊕                                      │
        │  revisions.json       ← ⭐ 人在这里逐条签字   │  每条：原值→新值→理由→签字
        │        ‖                                      │
        │  as_signed.json       ⭐ 机械派生 + 落盘      │  = as_measured ⊕ revisions
        └───────────────────────────────────────────────┘
                    │
                    │  ⭐ 一道【显式的】确定性派生步骤：AnswerCompiler(profile)
                    ↓
   ┌────────────────┬──────────────────┬──────────────────┬────────────────┐
 reading 题目册      形式A 多边形        形式B 多边形        净空面积表
 （该画哪些面线）    全中轴              外墙外皮+内墙中轴   （派生量，⛔ 不是出模档位）
        ↑                  ↑                    ↑
   reading grade      correction grade（run config 选哪个是正式成绩）
```

**三条规矩**（指南 §〇之二）：
① 改**事实** ⇒ **必须重签** · ② 改**派生规则** ⇒ 不重签，但**必须逐位可复现** ·
③ ⭐ **一份事实多个出口，⛔ 不做两条并列生产线**（并列必各自漂移 = **F-130** 的形状）。

## 1.2 事实层 `as_measured` 装什么

**原料 = P1（S0–S4）的输出，⛔ 不是 S7 的 `ZoneExpansion`。**
这条是 **F-122** 换来的：现有逐边正式字段**已经是扩张后的答案边**
（实测 `offset == (t if outer_skin else t/2)` **136/136**、272 个端点全部离开原 cavity 0.06–0.34 m）
⇒ **事实必须在扩张【之前】截取**。

| 字段 | 装什么 | 为什么是这个形状 |
|---|---|---|
| `face_lines[]` | 每条墙**面线**：`id`(DXF handle) · `layer` · `axis`(线**沿着**哪根轴走) · `const` · `along_min/max` | ⛔ 这里**没有「墙的哪一面」** —— 那是引用它的墙说的，不是线自己说的 |
| `walls[]` | 一堵墙 = **两条配对面线** + 沿墙区间：`face_line_ids_lo/hi` · `face_lo/hi` · `thickness`(= `face_hi - face_lo`) · `along_min/max` | ⭐ 走 `denominator.face_line_targets` 的**同一遍 D1–D5**，⛔ 不是第二份「什么算墙面」的实现；⛔ **零厚度阈值**（按声明厚度筛正是 sm24 整批 120 隔墙被静默丢掉的机制）|
| `openings[]` | 洞口 + `carrier_wall_ids` | 落位靠沿墙区间 |
| `footprint` | 外轮廓，逐环整数点 | —— |
| `converter_readouts` | 转换器**自己的**读数逐字搬运：`dangles/cuts/invalid` · `jamb_cap_bands` · `non_orthogonal_lines` · 三个消费桶 | ⛔ 一个几何值都不重算 —— 2026-08-29 的教训是「转换器早算好了、消费者扔了」，修法是**运输**不是**第二意见** |

**三条结构性质，⛔ 都不是纪律而是形状**：

1. ⭐ **坐标一律 0.1 mm 整数**（`units_per_metre = 10000`）。
   ⛔ 这不是吸附也不是容差，是**存储类型** —— 量化在转换器收线时就做了，
   之后「DXF 原生 → 世界米」的仿射变换才是末位噪声（`12.999999999999996`，1e-15 m）的来源，
   **加第二道吸附治不了它**（吸附完仍是浮点）。⇒ 换表示，F-98 一并根治。
2. ⭐ **接头存【线】不存【端点】**。实测 sm25 **54 个正交接头 100% 一致**：
   墙线画到**被撞那堵墙的近侧面**为止 ⇒ 角部方块两堵墙都不认领。
   存逐边端点 = 把某一种接头解法冻进记录，会让 **F-134 从「S7 已解」退回「未解」**。
   ⇒ **沿墙区间只用于分母与洞口落位，⛔ 不用于决定多边形角点。**
3. ⭐ **两道消费对账**（不是范围校验，是「每一笔都得有人认领」）：
   `wall_lines_total == face_lines + non_orthogonal + degenerate`，
   且 `paired / jamb_cap / unpaired` **三桶互斥、并集 = 全集**。
   ⛔ 这道防的是 **225 条面线里只有 110 条可配对**那个陷阱：全配 ⇒ 幽灵墙回来，
   少记 ⇒ 「故意排除」和「悄悄丢了」长得一样。

## 1.3 `revisions` 台账装什么

一条 revision = `target`（打在哪条线/哪个洞口）+ `finding`（哪道检查、量级、detail）
+ `verdict` + `action` + `reason` + `signed_by` / `signed_at`。

| `verdict` | 含义 | 产出 |
|---|---|---|
| `drawing_error` | 图画错了 | 带 `action` ⇒ **改 `as_signed`** |
| `as_designed` | 本该如此 | ⛔ **不改几何**，但**记账** ⇒ 下次不再问同一处；⭐ **照报但标「已确认」，⛔ 不从清单里删** |
| `producer_defect` | 不是图的错，是**工序缺守卫** | ⛔ 不改几何 ⇒ 出一条**缺陷登记草稿**进 plan.md |

**四条已拍板**：`action` **先只实现 `translate`**（其余遇到再加，且每加一种必须能说清「它是 `as_measured` 上的一个确定性操作」）·
作废半径用 **sol 的 B6 依赖闭包**（⛔ 不是「层」也不是「边」）· **只有签字流程能写 `revisions`** ·
`as_designed` 记账后照报。

⭐ sm25 那 **5 条线**（`13AD 13AC 13AF 160A 13AE`，最大约 6 mm）**就是台账的第一批住户**。

## 1.4 `as_signed`：派生的，但要落盘

**为什么落盘而不是每次现算**：判分器要读它，且要能对它做哈希与信任根。
**落盘的代价用一道门抵掉**：

> ⭐ **`as_signed` 必须能从 `as_measured` + `revisions` 逐位重算出来**，不一致 ⇒ 响亮失败。

**信任根三层**（⛔ 别把派生件当有独立信任根的东西）：

| 层 | 信任根 |
|---|---|
| `as_measured` | `source.dxf` 哈希 + `request` 哈希 + **转换器实现指纹** ⚠️ **字段已填但【外部锚未解】**（②-1b 把它从 `None` 填成 13 文件 AST 闭包哈希，⛔ 仍是「代码算自己」；sol 的 **B1** 要的外部授权锚**未解**，施工方自认、GLM 复核确认）|
| `revisions` | ⭐ **人的签字**（逐条）；整份 revisions 的哈希**进 `as_signed` 的派生键** |
| `as_signed` | ⛔ **无独立信任根**（它是派生的），⭐ 但必须可复现 |

⭐ 这条顺带把 **F-130 解掉**：两把尺子都从落盘的事实层派生 ⇒ **一起冻住**。

## 1.5 AnswerCompiler：四个出口，两种出模形式

| | 外墙 | 内墙 | 用途 |
|---|---|---|---|
| **形式 A：中轴** | 中轴 | 中轴 | 能耗建模常见口径 |
| **形式 B：外包** | **外皮** | **中轴** | 建筑轮廓 / 面积口径 |
| ~~形式 C：净空~~ | — | — | ⛔ **不做出模形式**（A 东面 x=5.00、B 西面 x=5.24 ⇒ **两面配不上对** ⇒ InterZone 门红，绕过去则**相邻传热断了** = 跑得通但物理错的）|

**⭐ 内墙只能中轴，理由是硬的**：EnergyPlus 里相邻两房间中间那面墙必须是**一对几何重合的面**
（顶点一一对应、法线相反）才配得成 InterZone。
**⭐ 外墙外包不破坏配对**：它只把最外一圈往外推，内墙一动不动。
**⭐ 净空不丢**，它是**派生量** —— 房间使用面积本就是净空口径，事实层存了 `(两端点, basis, thickness)` 随时算得出。

**⛔ 「两种形式」本身不足以定死答案，实测补三条**：

| | 补什么 | 立此条的实测 |
|---|---|---|
| **6a** | **形式 A 必须配顶点去重** | 形式 A 下台阶归零 ⇒ 两顶点重合 ⇒ `cell_polygon` 抛 `polygon edge is degenerate` |
| **6b** | **基准按【墙线】定，⛔ 不按【边的角色】定** | 同一堵 240 墙一段外墙一段内墙，形式 B 中途换基准 ⇒ **120 mm 台阶**，且那条边**不对应图上任何一堵墙** |
| **6c** | **接头处传播【线】⛔ 不传播端点，端点由相邻两条线求交算出** | S7 [`s7_expand_zones`](../../src/agent/judge/tarch_normalize.py#L1388) 已经是这么做的（docstring 明写 L/T/十字/凹角**都不需要特例代码**）|

**局部计分**（用户 08-28 定）：一条坏边 ⇒ **受依赖闭包影响的指标 NA，其余指标照常出读数**，⛔ 不是整层 NA。
⛔ 两条硬线：不得破坏几何不变量 · **不得因缺失而缩分母获益**（缺掉的目标仍进分母，只是那项记 NA）。

## 1.6 gt 侧确定性配对的**准入条件**（指南 §十二，⛔ 不是某一次的验收项）

指南 §一定死「哪两条线是一堵墙 = 配对，**归模型**」。gt 侧**必须**有配对（否则 reading 的配对无从判分），
它与那条口径不冲突 —— **但承重理由只能是「在外部可证伪 + 不含被禁机制」，⛔ 不是「输入是确定的」**
（②-1a 自己就是反例：确定性 DXF + 确定性代码，产出 **33 条虚构的墙**）。

| # | 准入条件 |
|---|---|
| 1 | **厚度值集可对原图核验** —— 锁写成 `set(直方图) ⊆ set(request 声明的墙厚)`，⛔ 不写死 `{120,240}` |
| 2 | **消费对账**：每条面线必落进 {被墙引用 / jamb cap 排除 / 落单} **恰好一桶** |
| 3 | **第二栋楼**：换一栋真图跑同一套判据 |
| 4 | **幽灵形状的回归锁**：「把旧的 band 源接回去 ⇒ 幽灵必须回来」 |
| 5 | ⛔ **零厚度阈值** |

⇒ 这五条**要以测试函数名清单的形式落**，⛔ 不写成散文纪律。

## 1.7 签字流程与晋升

```
1. 转换器跑 as-received source.dxf ──→ as_measured.json
2. 一致性检查（⛔ 无阈值 · 互为最近邻）─→ 清单
3. 复原式渲染（⛔ 只照搬不推导）─────→ 标注图
   ──── orchestrator 反复空跑到清单稳定，⛔ 不占用户时间 ────
4. 【预览】用户只判「检查类别够不够」，⛔ 不签字
5. 【正式签】用户逐条判 drawing_error / as_designed / producer_defect ─→ revisions.json
6. 机械派生 ──→ as_signed.json ──（选形式）──→ gt.json
```

⛔ **第 4 步与第 5 步必须分开**。实证：同一个一致性检查 orchestrator 连错三版
（面线比面线 625 条 → 墙比墙仍爆炸 → 互为最近邻 1 条）——**尺子没定型就请人签，同一处会被叫去签三遍。**

**晋升接法**：`promote_gt_v3` 现拷 `gt.json` + renders + review 五件 + `source.dxf`/`request.json`
⇒ **新增 `facts/` 三份一并拷**，且**晋升前先跑 §1.4 那道可复现门，不过不许晋升**；
顺带处理 **F-128**（回滚不对称：`except` 只清 `gt/` 侧、不清 `gt_sources/` 侧）。

## 1.8 gt 侧：目标 vs 今天

| 目标态的件 | 今天 | 出处 / 实测 |
|---|---|---|
| 转换器 S0–S4 / S5–S7 / G1–G10 · 0.1 mm 量化 · 签字晋升入库 | ✅ | [`tarch_normalize.py`](../../src/agent/judge/tarch_normalize.py) · [`tarch_review_bundle.py`](../../src/agent/judge/tarch_review_bundle.py) · [`gt_promotion.py`](../../src/agent/judge/gt_promotion.py) |
| `AsMeasuredV1` schema + builder + 两道消费台账 + 0.1 mm 整数 | ✅ **产物已落盘** | [`as_measured.py`](../../src/agent/judge/as_measured.py)；②-1b（`9f0266b`）起落在 **`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/`**，⛔ **不是 `gt/` 答案根**（晋升接法未做，见下一行）。⚠️ **F-136**：消费台账守的是「收集到的」不是「看见的」 |
| as-received 图 + 专用 request | ✅ | `gt_sources/sm25-L_anchor/` 有 `sm25-L_t3_as_received.dxf` + `request_as_measured.json` |
| `walls` 走面线配对（⛔ 不用 `wall_bands`） | ✅ | ②-1a-R；旧 band 仍逐字留作 `converter_readouts.jamb_cap_bands` |
| `revisions.json` 台账 + `as_signed.json` + 可复现门 + B1 指纹**字段** | ✅ **已收口**（GLM 复审 APPROVE-WITH-FINDINGS / 阻断 0）| ②-1b `9f0266b`+`2196723`；权威全量 **3292 passed / 13 xfailed / 0 failed**（`.pth` 哨兵前后同）。②-1b-R（`201f47f`+`f140708`）已修 F-137 / F-139 / A1 集合锁 / F-136 守恒面；主控权威门 **3305 passed / 13 xfailed / 0 failed**（哨兵前后同 · HEAD 前后同 · **树跑前跑后皆空**）。⚠️ 仍开着（**全部不阻断**）：**F-140**（一致性门灵敏度 **[0.1,0.9+] mm 位置依赖**、无锁）· **F-141**（换图层伪装）· **F-142**（split-const 登记 stale）· `gt_staging/` 无写保护 · **B1 外部锚未解** |
| 晋升接法（`promote_gt_v3` 拷 `facts/` + 晋升前跑可复现门）+ **F-128** | ❌ | 随 gt 重做重签；②-1b 只留了接缝说明 |
| `AnswerCompiler(profile)` + 两种出模形式 + 6a/6b/6c + 依赖闭包/局部计分 | ❌ | = **②-1c** |
| 逐边 `boundary_condition` | ❌ | = **②-1d**（F-121） |
| **正交吸附**（转换器把画歪的线吸到轴上） | ✅ **已落地并收口**（②-1b-S `22202c1`；GLM **APPROVE-WITH-FINDINGS / 阻断 0**）；⛔ **上限阈值待用户签字（F-143）**，且复核方已证**绝对毫米是错的形状**（角度含义随线长漂 ~120 倍）⇒ 推荐**双门限** | 今天两套处置：算轮廓走**吸附**（[`gt_extraction.py:283`](../../src/agent/judge/gt_extraction.py#L283)）· 收墙线走**整条丢弃**（`tarch_wall_nonorthogonal` + `continue`，[`tarch_normalize.py:383-387`](../../src/agent/judge/tarch_normalize.py#L383)）；共用容差 1 mm。实测 as-received `plan-F1` 面线 **222→224** · 墙 **54→55（= 签字件）** · 吸附清单 `['13AD','13AE']` · `plan-F2` 逐位不变。<br>⭐ 原判「理由是不变量 #6 可扩展性，⛔ 不是今天的判分缺陷」—— ⛔ **已被 F-138 推翻**：`as_measured` 改从 **as-received** 出之后歪线进了事实层输入，实测签字件 225 面线 / as-received 222(+1)，差集恰为 `13AD/13AE/13AF` |
| 净空面积表 | ❌ | 派生量，随 ②-1c |
| **今天的 `gt.json` 仍是「那张确定的图」** | ⚠️ | 实测：`zones` 只有 `id/name/polygon/role/source_refs`；`boundary_segments` **8 条、厚度值集 `{0.24}`** ⇒ **内墙 120 的厚度 gt 里没有**（= **R-6**）。S7 逐边量到的 `basis`/`thickness` 在序列化那步全丢 |

---

# 第二部分 · pipeline 链的目标态

```
截屏图 → 0_reading → 1_correction → 2_modelling + 3_split_pairing → 4_mep → 5_intakeoutput
        (模型看图)   (模型判断)      (纯代码)                        (模型)   (代码)
```

## 2.1 四刀分工（⛔ 已定死，不再讨论）

| 干什么 | 谁 | 例 |
|---|---|---|
| **量** | **代码** | 分族（⏳ 特征要**声明化**，⛔ 不绑死颜色 = **F-131**）· 面线位置 · 真实连续区间 · 空档剖面 · 尺寸链拟合 |
| **认** | ⭐ **模型（在 reading）** | 哪族是墙/门窗/标注 · 门还是窗 · **哪两条线是一堵墙** · **允许说「认不出来」** |
| **对账** | **代码门** | 指派的族在吗 · 引用的观测在吗 · 每条面线都归桶了吗 |
| **装配** | **correction** | 见 §2.3 |

⭐ **感知就是语义**（不变量 #1）⇒ ⛔ 语义不许搬去 correction、不许写死、**也不许「搬进配置逐图声明」**（还是人工填，一样不泛化）。

## 2.2 0_reading 的目标态：三层产物 + 六桶 perception

| 层 | 是什么 | 判分地位 |
|---|---|---|
| `observations` | 尺子在像素上量到的 | ⭐ **唯一可评分层** |
| `declarations` | 图纸/配置**声称**的，逐字转录 | 只比字面 |
| `hypotheses` | ⭐ **模型认出来的**，带证据引用 | ⛔ 不直接计分、**可整层丢弃** |

**硬性质**：**只拿前两层，下游必须能重新推出第三层。** 做不到 ⇒ 该字段偷藏了判断。
**硬边界**：⛔ **reading 不写厚度、不写中线、不判内外。**
（墙厚归属：观测层**没有厚度字段** · 声明层 `thickness_callouts_mm` **只比字面** ·
假设层带 `spacing_m`（观测量）+ `matched_declared_mm` · **模数吸附归 correction**。
⭐ 这固化的是 **F-78**：叫 `thickness` 就以事实身份往下游走，实测那两个「墙厚」是 **0.49 像素**噪声。）

**「认」的产物 = 一份独立文件 `perception/<case>.json`**，由做识别的那一方产出，配置里只写一句指针：

| 桶 | 是什么 | ⛔ 为什么必须有 |
|---|---|---|
| `family_roles` | 哪个**被发现的**族是墙/标注/家具/门窗 | 族编号跨图不稳定（sm25 1f 墙=F0、**2f 墙=F1**）|
| `wall_pairs` | 哪两条面线是一堵墙（从代码穷举的候选里选）| —— |
| `solid_band_walls` | 哪条面线**自己就是一堵墙**（实心带方言）| 一堵墙不一定是两条线 |
| `unpaired_wall_faces` | 是墙面、但另一面没进观测 | ⛔ 不许硬配 |
| `non_wall_face_lines` | 不是墙，**并说明是什么** | 沉默 = 静默丢失 |
| ⭐ `ambiguous_face_lines` | **「我认不出来」** | **模型必须被允许这么答**；逼它表态就是把桌子边读成墙 |

**代码侧三条硬规矩**：① 候选穷举 ⛔ **不设间距阈值** · ② 没有 perception ⇒ **响亮降级**（`ABSENT_NO_MODEL_SELECTION`），⛔ 绝不拿代码规则冒充模型的答案 · ③ **完备性对账**：每条面线都必须落进某个桶，否则门红。

**⛔ 不看 gt 的 11 道自检门**（问的是「你说的和原图对不对得上」）：
`reverse_ledger_no_phantom_ink` · `observations_recomputable_from_own_pixels` ·
`gap_evidence_recomputable_from_original_image` · `face_span_fully_accounted_by_runs_or_gaps` ·
`support_strip_is_one_stroke` · `runs_match_the_strip` · `opening_role_matches_where_the_ink_sits` ·
`opening_naming_supported_by_ink` · `pair_hypothesis_reconciles_with_observations` ·
`pair_spacing_explicable_by_callouts` · `forward_ledger_structural_ink_claimed`。
⭐ **最后一条是泛化性的兑现口**：图上每一笔结构墨都要有人认领，**没认领的点名报红**
⇒ 换一张用没见过的画法画窗的图，**门变红**，而不是静默少读一扇窗。

**更远的目标形态** = reading 是**一个 agent**（SOP + 判例库 + 工具箱，内部自带回叠原图的循环），
量具归代码、工序归模型、出口归代码且产出方碰不到。⭐ **本批不做 agent 化施工，做的是拆管子。**
全档 → [`reading_pipeline_architecture.md`](reading_pipeline_architecture.md)。

## 2.3 1_correction 的目标态：第四刀「装配」，三拍循环

```
① 代码：拿 reading 的观测 + 语义，尽最大努力算出一份几何，
        并把【所有算不下去的地方】列成待裁决清单（现象 + 候选处置 + 各自代价）。
        ⛔ 没有歧义的自动处置掉【并记账】，只把真歧义送上去。

② 模型：a) 逐条裁决（选哪个候选，或「都不对，因为 X」）
        b) ⭐ 总体把控：这份几何作为一栋楼讲不讲得通

③ 代码：执行裁决 → 出几何 → 重跑一致性检查；还有新的不一致就回 ②（有限轮）
```

- ⭐ **铁律：模型输出「决定」，代码输出「坐标」。** 模型说「这里该接上」，代码算接在哪 ⇒ 不变量 #1 不破。
- ⭐ **职责是【收束】，⛔ 不是【补漏】。** ⛔ 别再把完备性负担全压给 reading（「读得够好就不需要 correction」= **分工塌了**）。
- ⭐ **模数吸附归它**（3637 → 3600）；**gt 只声明分辨率**，⛔ 两边不共用实现（共用会一起错 = F-95 的形状）。
- **为什么「总体把控」是模型独有的**（有实证）：走廊幻墙 2.1 m · Z 形凹口没分段 · 内墙画穿多段 ——
  **逐条都「合法」**（坐标在范围内、线是直的、长度是正的），任何确定性检查都抓不到；
  做总体把控的模型会看出「这堵墙横穿走廊」「这个房间没围合」。

**输入形态（②-2 的本体）**：correction 改成吃「**带原始引用的【多形态】墙证据**」——
六形态 `paired_faces` · `solid_band` · `single_face` · `axis_trace` · `ambiguous` · `non_wall`。
⛔ **只接受「两条面线」的接口是错的**（`sm24_1f_v2.json` 就有 4 个 `solid_band_walls`，会被迫丢墙或伪造第二张面）。
⛔ **「写个转换层把两条面线塌成中线」也是错的** —— 那是在 reading 侧偷偷替 correction 做基准统一。
⭐ **中线只允许在 correction 内部由代码派生**，⛔ 不回写 reading、⛔ 不覆盖面线。

## 2.4 2–5 段（本批不动，列出来是为了对账产物）

| 段 | 谁 | 产物 |
|---|---|---|
| **2_modelling** | 代码 | `building_geometry.json` · `kernel_gate_report.json`（**block 关口**）· `kernel_checks.json` |
| **3_split_pairing** | 代码 | `geometry_specs.md`（序列化的 zone / surface / fenestration specs） |
| **4_mep** | 模型 | `mep_output.json`（只产 8 个非几何字段）· `mep_checks.json` |
| **5_intakeoutput** | 代码 | `intake_output.json`（**11 字段交接契约**）· `contract_issues.json` · `assembly_checks.json` · `output_coordinate_contract.json`/`_snapshot.json` |

## 2.5 pipeline 侧：目标 vs 今天

| 目标态的件 | 今天 | 出处 / 实测 |
|---|---|---|
| 三层产物 · 族发现（不写死颜色）· 语义指派外置 · 9 个可单独调用的工序函数 | ✅ 代码在 `src/` | [`reading/as_drawn/as_drawn_v2.py`](../../src/agent/reading/as_drawn/as_drawn_v2.py) + CLI [`reading_toolbox.py`](../../scripts/tool_scripts/reading_toolbox.py) |
| 11 道不看 gt 的自检门 | 🟡 **代码在 `src/`，零消费者** | [`src/validator/checks/as_drawn.py`](../../src/validator/checks/as_drawn.py) |
| 分族**特征声明化**（⛔ 不绑死颜色） | ❌ | **F-131**；今天唯一特征是色度（[`pens.py:59`](../../src/agent/reading/as_drawn/pens.py#L59)），单色图退化成一族并显式降级 |
| ⛔ **新 reading 接进管线** | ❌ **零接线** | `vector_contract.py` 认得出 as-drawn 但判 `KNOWN_NOT_CONSUMED` = **响亮拒绝**（[:213](../../src/agent/reading/vector_contract.py#L213)）；管线今天吃的是 legacy `*_view.json` 的 `strokes` |
| correction 吃多形态墙证据 | ❌ | = **②-2** |
| ⛔ 改掉提示词里的 `wall-centerline` | ❌ | 两句仍在：[`pipeline.py:367`](../../src/agent/pipeline.py#L367) 与 [:370](../../src/agent/pipeline.py#L370) |
| **三拍循环** | ❌ | 今天是**单次出 `CorrectedGeometry` → 确定性核吸附 → gate①**（失败走 `feedback` 重抽），**没有「待裁决清单」这个产物** |
| 厚度活到 correction 这一层（R-6） | ❌ | 实测判分产物里 `thickness`/`role`/`basis` **各出现 0 次** ⇒ **F-133**（同层真实台阶被静默合并）与 **F-135**（`gap_close` 第三条路径）今天分不开 |

---

# 第三部分 · 判分的目标态：两把尺子，对**同一份 gt 的两个出口**

| | **reading grade** | **correction grade** |
|---|---|---|
| 问什么 | ⭐ **描得像不像**（对原图的忠实度） | ⭐ **画得对不对**（收束后的几何/语义） |
| 对什么 | **事实层派生的题目册** | **形式 A/B 的房间多边形** |
| 参照 | ⭐ **同一份 gt**（08-29 用户撤销「修正前/修正后两层」） | ⭐ **同一份 gt** |
| judge 的动作 | 对 gt 判，**并决定要不要重抽** | 对 gt 判 |
| 分数怎么用 | ⛔ **不纠结数字**，主要看 **grade 图**一眼判画崩/一般/好 | **正经成绩** |
| 容差 | 位置 **80 mm**（`POS_TOL_M`）—— ⭐ **靠容差，⛔ 不靠「是否正交」** | 确定性层判 |
| grade 图 | as-drawn 那张：原图叠底 + **绿=画对 / 红=漏画 / 琥珀=答案自己留白（不要求也不罚） / 品红=多画** + 洞口逐个方框 + 底部四行数 | 灰真值底 + 绿/橙/红三档（[`judge_grade_model.md`](judge_grade_model.md)） |

⛔ **两者都只判【答案】、不判【过程】。** 裁决记录仍然留，但它是**改进 harness 的证据**，⛔ 不进判分。
⛔ **成绩闸**（[`as_drawn_layer_contract.md`](as_drawn_layer_contract.md) §三）：在 `span_min` 签字 + 冷启读图器首考完成前，
**as-drawn 层任何分数不得记成绩**。

**今天**：reading 侧**两套并存** —— 旧 `judge/reading_score.py`（读 `gt.json`，✅ 接在 `run_stage`）
+ 新 [`judge/as_drawn/reading_grade.py`](../../src/agent/judge/as_drawn/reading_grade.py)（🟡 零调用者，且题目册**现跑转换器** = F-130）。
correction 侧 `score_service` → `score_vs_gt.json` → `render_grade.py`（⚠️ 平面面板 scale 变负，已登记小单）。

---

# 第四部分 · ⭐ 目标态里**还悬着、需要你拍板**的

| # | 悬着的东西 | 为什么必须你签 | 现在拦住了什么 |
|---|---|---|---|
| 1 | **`span_min` 签字** | 它等价于宣布「**一堵墙漏画多少算漏**」。⚠️ 实测：诚实 sm25 1F 有 **7 个目标的覆盖恰在 0.841**，而现行阈值 **0.80** —— **悬崖离诚实值只有 0.04** | as-drawn 层**任何分数不得记成绩** |
| 2 | **冷启隔离读图器首考**（要花钱） | 「认」这一刀至今**没有任何模型真跑过**，都是主控手填，且手填者**产出前已看过 gt 侧结果** ⇒ **「模型能不能做到」没有回答** | 同上 |
| 3 | **分级的弃权预算** | 它是**领域参数**，⛔ 不许就地发明；⛔ 也不能拿看过 gt 分数的 perception 回填。（`ZERO-WALL` 无阈值可立 —— 一堵墙都没认出来 = 自信的零） | 「49/49 全说认不出来」今天能全绿走过去 |
| 4 | **模数吸附的分辨率参数** | ⭐ **今天它没有名字、没人签字**。口径已定：gt **声明**分辨率 → 跑前抄进配置 → 判分侧核对一致，不一致响亮失败 | ②-4 |
| 5 | **sm25 gt 整份重做重签的时点** | 已定 = **排到这批改造完成之后**（⛔ 不提前签）。不占你时间的准备（事实层落库 / 一致性检查 / 渲染标注 / 派生器）照常推进 | —— |
| 6 | **正交吸附的排期** | 已定归属（gt 侧转换器）与理由（**不变量 #6 可扩展性**，后面要解锁非正交）；⛔ 它在今天的判分上**不承重**（签字件一条歪线都没有） ⇒ 排期归 **C2 那条线**，不是判分缺陷 | —— |
