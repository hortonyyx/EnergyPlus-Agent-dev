# 派工单 · 立面洞口「载体方言层」（F-65 修复 + 拓展性改造）

> **席位**：施工 = **sol**（GPT 家族）· 跨家族审 = **GLM** · 主控 = Claude（出单 / 审裁决 / 轻门全量）
> **档位**：**工程档**（碰答案产出路径）⇒ gate① + 全仓绿 + 只锁契约与几何不变量
> **前序**：`b2460bb` 转换器多层化（同一函数族，刚改过，先读那次 diff）
> **登记**：[plan.md](../../../plan.md) F-65

---

## 0. 一句话

立面洞口的提取现在**把「图怎么画」烤死在代码里**（只认直线）；本批把它改成
**「画法由请求声明、代码只做匹配与执行」的方言层**，并加一道**清点对账门**，
让「没见过的画法」必然报红且指名道姓，而不是静默少几扇窗。

---

## 1. ⭐ 硬约束：拓展性与适配性（用户 2026-08-20 当面提，本批第一约束）

用户原话（转述）：**「这部分要兼顾各种各样的图，因为画图习惯不一样，使用的图块、或者手工的画法也不一样，
这些可能也需要判断，不是一套机械方法可以全部搞定的……这个也要注意拓展性和适配性，
因为后续 CAD 模态作为主线接入也需要相似的这个环节。」**

⇒ 本批**不是**「给 sm25 补两个 if 分支」。验收时会按下面三条判：

1. **加一种新画法 = 加一条规则实现 + 请求里声明一条规则，⛔ 不得修改任何已有分支。**
   （审阅方会拿一种本批未实现的画法当思想实验：比如「窗 = 一个 HATCH」或「窗 = 带弧的多段线」，
   问「接它要动几处已有代码」，答案必须是 0 处已有分支。）
2. **代码不得推断画法**：不许出现「看起来像窗」「大概是门」这类启发式。
   认不认得出，只取决于请求里声明了什么；认不出就报红。
3. **这一层是 CAD 模态主线的同一个环节**：把任意 DXF 实体归类成语义构件（墙/窗/门/其他）。
   设计与命名要能直接搬过去，⛔ 不要把 `tarch` / 天正专有词烤进通用结构里
   （方言**内容**可以是天正的，方言**机制**不能是）。
   参考不变量 #6（[CLAUDE.md §1.5](../../../CLAUDE.md)）：**纯只适用当前一份图的方案没有意义。**

---

## 2. 现状（主控实测 · ⚠️ 可能有错，见 §7）

### 2.1 缺陷本体

[`src/agent/judge/tarch_normalize.py:1694`](../../../../src/agent/judge/tarch_normalize.py#L1694)：

```python
lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer in view.window_selector.layers and _inside(...)]
```

- **`window_selector.entity_types` 全文从未被读取**（已 grep 全仓确认：唯二引用点是 schema 定义与本行的 `.layers`）。
  ⇒ schema 里那个字段是**摆设**，声明什么都不影响行为。
- 提不出东西时**不产任何诊断**（空列表就是空列表）⇒ 静默零，F-64 同族。
- 门那条路（1700–1754）要求洞口轮廓必须是**一条闭合 LWPOLYLINE**。
- 门规则取自 `request.plan_views[0].dialect_rules`（**又一个 `[0]`**，与上一轮刚修掉的多层缺陷同形）。

### 2.2 sm25 立面实况（`case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf`）

| 视图框 | 图名 | 窗载体 | 门 |
|---|---|---|---|
| `382` | 西立面 | INSERT `$EWDLib$00000533` ×4 | INSERT `$EWDLib$00000621` ×2 |
| `384` | 南立面 | INSERT `$EWDLib$00000533` ×7 | — |
| `386` | 北立面 | INSERT `$EWDLib$00000533` ×6 + **闭合 LWPOLYLINE ×2** | — |
| `388` | 东立面 | **闭合 LWPOLYLINE ×12** | INSERT `$EWDLib$00000621` ×2（相邻，合成 1 樘 1600 双开）|

**应得答案 = 31 扇窗 + 3 樘门。当前跑出 0 扇窗 + 21 条 `door_block_drift` 误报。**

⭐ **注意北立面**：**同一图层上两种载体混用** ⇒ 规则表必须允许多条规则命中同一图层。

### 2.3 两个块定义（主控已拆开看过）

- **窗块 `$EWDLib$00000533`**（8 条 LINE，无 LWPOLYLINE）：
  外框 `(0,0)-(1200,600)` = 句柄 `316`/`317`/`319`/`31B`；内框 `(50,50)-(1150,550)` = 窗扇线。
  **洞口 = 外框那 4 条 LINE。**
- **门块 `$EWDLib$00000621`**（1 LWPOLYLINE + 19 LINE + 1 CIRCLE）：
  外框 `(0,0)-(1200,2100)` = 句柄 `35E`/`35F`/`360`/`361` = **洞口**；
  那条 LWPOLYLINE `34E` 是**未闭合的门扇轮廓**（`30..1170 × 0..2070`，比洞口窄 60、矮 30）。
  ⇒ **现行「structural_outline 必须是闭合 LWPOLYLINE」的约定在这份图上门也走不通**，不只是窗。

⇒ **洞口轮廓必须允许「一组 LINE」**，门窗共用同一条放宽。

---

## 3. 交付物

### D1 · 洞口载体规则（schema，新增，请求级）

新增一张**载体规则表**，门窗共用。建议形状（命名可改，语义不可改）：

```python
class OpeningCarrierMatchV1(_StrictModel):
    entity_type: TarchEntityType                     # LINE / LWPOLYLINE / INSERT / ...
    layers: list[str]                                # 排序去重
    block_name_exact: str | None = None              # 仅 INSERT
    block_definition_sha256: Hex64 | None = None     # 仅 INSERT：钉死块定义，一改必红

class OpeningOutlineV1(_StrictModel):
    kind: Literal["closed_polyline_rect",            # 实体本身即闭合矩形
                  "connected_line_group_rect",       # 同层连通直线组围成矩形（sm24 原路）
                  "block_entity_rect"]               # 块内指定实体经插入变换后围成矩形
    block_entity_roles: list[BlockEntityRoleV1] | None = None   # 仅 block_entity_rect

class OpeningCarrierRuleV1(_StrictModel):
    carrier_id: StableId                             # 稳定名，进 source_map 当证据
    opening_kind: Literal["window", "door"]
    match: OpeningCarrierMatchV1
    outline: OpeningOutlineV1
```

- `block_entity_roles` 沿用现行 `entity_roles` 的形态（逐句柄 `structural_outline` / `nonstructural_detail`），
  但**放宽为「`structural_outline` 可以是 1 条闭合 LWPOLYLINE，或 N 条 LINE」**；
  N 条 LINE 走 `_rect_from_lines` 成矩形，成不了 ⇒ 红。
- 规则表挂**请求级**（不是 `plan_views[0]`）。⛔ 顺手把 1701 行那个 `plan_views[0]` 一起干掉。

### D2 · 通用解析器（代码）

一个 `_resolve_opening_carriers(view, rules, msp, tols)`，返回
`[(carrier_id, opening_kind, rect, consumed_handles, structural_handles)]` + 诊断。

- 三种 `outline.kind` 各是一个**独立小函数**，登记在一张 `dict[kind, fn]` 表里。
  **新画法 = 表里加一项 + schema 的 Literal 加一个值，⛔ 不动已有项。**（= §1#1 的验收点）
- `connected_line_group_rect` **必须复用**现有 `_line_components` + `_rect_from_lines`，
  ⛔ 不许另写一份连通/成矩形逻辑（sm24 产物要逐字段不变）。
- `block_entity_rect` 变换用 `ins.matrix44()`，与门那条路一致（含镜像/旋转/非等比缩放，sm25 全都有）。
- 门的**多模块合并**（同 z 带相邻 → 一樘）**保持现状语义不变**，只是输入换成通用解析器的产出。
  ⭐ 东立面那两片就是靠它合成 1 樘 1600 双开门 —— **这是必须保住的既有正确行为**。

### D3 · ⭐ 清点对账门（本批的安全网，与方言无关）

立面框内、**所有洞口规则声明过的图层**上的每一个实体，必须恰好落入以下之一：

| 归属 | 说明 |
|---|---|
| 被某条规则消费 | 记进该洞口的 `raw_handles` |
| 落在显式忽略声明里 | 请求里新增 `ignore_selector`（图层+类型），用于装饰/标注类 |
| **其余** | ⇒ **红** `tarch_elevation_entities_unconsumed`，诊断里**逐句柄列出** |

外加两条：
- **同一实体被两条规则消费 ⇒ 红** `tarch_elevation_entity_double_consumed`（sm25 北立面混载体的直接风险）。
- 诊断必须带**视图 id + 句柄清单**，让人照着补规则。

> 这条门是「适配性」的兑现方式：换一份画法没见过的图，系统说
> 「这 12 个句柄我不认识」，而不是给出一个少 12 扇窗、却一路绿到签字页的答案。

### D4 · sm24 请求同步升级到新规则表

- sm24 的请求文件（`tests/fixtures/sm24_review/**/request_v3*.json` 与 `gt_sources/sm24_anchor/` 侧）
  改写成新表：窗 = `connected_line_group_rect`，门 = `block_entity_rect`。
- **⛔ 唯一路：不保留旧字段的第二条执行路径。** 旧字段可留作 schema 层的迁移入口，但**执行只走新表**。
- **等价性由 D5 的锁证明**，不靠肉眼。
- ⚠️ sm24 已签字件的溯源戳本来就已失配（plan.md 已登记，用户允诺重签）⇒ **本批不重签、不晋升**，只证明产物不变。

---

## 4. ⛔ 明确不做

- 不动平面侧提取（本批只碰立面洞口这一段）。
- 不动判卷 / gt schema / 晋升与签字链路。
- 不实现本批用不到的画法（HATCH / 弧 / POLYLINE）——**只把接口留出来**，实现留给遇到时。
- 不做画法**自动识别**（不许写「猜这是窗」的启发式）。
- 不碰 guard 围栏、不补与本批无关的锁与审。

---

## 5. 锁（跟契约走，⛔ 不给脚手架配锁）

| # | 锁 | 判据 |
|---|---|---|
| L1 | **sm24 立面产物逐字段不变** | 新旧两条路对同一份 sm24 输入，`_ElevationRecord` 全字段 + 规范化 DXF 内容逐字段相同 |
| L2 | **must-red：撤掉 D2 的载体扩展** | 把 sm25 那三种载体喂进去 ⇒ 必须红（⛔ 不许靠「删代码看它红」，要**结构性**必红：见 [[gate-with-only-negative-assertions-is-unobservable]] 的反面——先证明**不加改动时这门本来是绿的**）|
| L3 | **must-red：删掉任意一条窗规则** | 对账门必须报 `entities_unconsumed` 并列出正确句柄数 |
| L4 | **must-red：篡改块定义** | `block_definition_sha256` 失配 ⇒ 红 |
| L5 | **双重消费必红** | 构造两条命中同一实体的规则 ⇒ `entity_double_consumed` |

⚠️ **L2/L3 的前置**：每条 must-red 必须先断言**「不施加该扰动时这条用例是绿的」**，
否则是恒红 = 结构上不可观测（同 [[regression-case-must-prove-its-own-premise]]）。

---

## 6. 验收（施工方自跑，主控复跑）

1. 全仓 `pytest -n auto`：**≥ 2917 绿 + 14 xfail**，零红零闪，**连跑两次**。
2. L1–L5 五把锁全绿。
3. 拿 sm25 的 DXF 走一遍立面提取（可用最小请求片段，不需要完整 16KB 请求），
   产出 **31 扇窗 + 3 樘门**，且**对账门零剩余**。
   ⇒ 逐视图报数：西 4 窗 2 门 · 南 7 窗 · 北 8 窗 · 东 12 窗 1 门。
4. §1 的三条拓展性判据，用**文字**回答一遍（审阅方会照着挑）。

---

## 7. ⚠️ 本单里可能错的前提（请主动证伪，别继承）

主控上一轮的「停下上报」记录是 **3/3 全是派工方（我）的题出错**，累计 15/15。
以下每一条都是我的**观测或判断**，不是事实基线：

1. §2.2 的窗/门计数（31/3）与逐视图分布 —— 我用 ezdxf 实测 + 变换矩阵算的，**请独立复算**。
   ⭐ 我在这一批里**已经错过一次**：先前拿图块的**插入点**当外包框，误报「东立面两门块重合」，
   实算后是相邻双开门 —— 参见 [[proxy-mistaken-for-the-thing]]。同类错误可能还有。
2. §2.3 说「洞口 = 外框 4 条线」是我看坐标推的，**没有人确认过这份图的画图约定**。
   若你判定洞口应取内框或别的，**停下上报**。
3. §3 的 schema 形状是建议。**若有更能满足 §1 三条判据的形状，改它并说明理由** —— 我的形状不是判据。
4. 我假设「门的多模块合并语义保持不变」是安全的。若你发现新解析器下它会误合并 sm25 西立面那两樘
   （相距约 10m，理论上不该合并），**停下上报**。
5. 我假设平面侧不受影响。若发现 `dialect_rules` 提升到请求级会牵动平面路径，**停下上报**。

**⛔ 停下上报不扣分。** 派工方的题错了 15/15 次，这些都是停下来才捞回来的。
凡「一律 / 全部 / 共 N 处」这类断言，逐处列值对账后再动手。

---

## 8. 交付形式

- `git diff` + 全量测试输出（两次）+ §6.3 的逐视图报数 + §6.4 的文字回答。
- ⛔ 不写长篇自述：复核只看原始需求 + diff + 测试输出。

---

## 9. sol 执行护栏（规约 §5 硬条款，本单适用）

sol 原则上不当执行器；本单由用户当轮拍板派 sol，故三条护栏**逐条生效**：

1. **删除 / 覆盖 / 推送 / 外发一律单独授权** —— ⛔ 不得 `git push`、不得 `commit`、
   不得删除或整体重写既有测试文件；改既有文件只用最小 diff。提交由主控做。
2. **每阶段给可验证证据**：测试输出原文 / `git diff` / 实际产出数字。
   ⛔ 「已完成 / 已验证 / 应该没问题」这类自述不算证据（本项目实犯过：
   [[self-report-more-compliant-than-artifact]]）。
3. **限单次变更范围**：一个工作包做完停下来重看计划，⛔ 不要一口气推到底。
   建议切三个包：**① schema + 解析器骨架 → ② 三种载体实现 + sm24 等价 → ③ 对账门 + 五把锁**。

**沙箱**：`danger-full-access`（本机 read-only/workspace-write 会静默回退去读远端 @main，行号不可信）。
